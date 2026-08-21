"""End-to-end controlled experiment runner and artifact writer."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import platform
import random
import time
from typing import Any, Iterable, Mapping, Sequence, cast
from uuid import uuid4

import yaml  # type: ignore[import-untyped]

from iqa_soa import __version__
from iqa_soa.agent import (
    AgentProvider,
    DeterministicStubProvider,
    ExperimentalAgent,
    OpenAICompatibleProvider,
)
from iqa_soa.agent.agent import AgentRun
from iqa_soa.agent.providers import (
    DEFAULT_TOOL_CONTRACT_POLICY,
    probe_runtime_provenance,
)
from iqa_soa.benchmark import BenchmarkCase, FrozenPilotBenchmark, load_benchmark_cases
from iqa_soa.evidence import EvidenceLogger
from iqa_soa.experiment.treatments import Treatment, treatment_for
from iqa_soa.iqa.chain import build_guard_chain
from iqa_soa.iqa.gateway import ServiceGateway
from iqa_soa.iqa.policy import Policy
from iqa_soa.iqa.qa_xml import DEFAULT_SCHEMA_PATH
from iqa_soa.metrics.collector import collect_run_metrics, load_evidence_events
from iqa_soa.instrument import (
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.metrics.definitions import (
    PILOT_RAW_FIELDS_V3,
    REQUIRED_RAW_FIELDS,
)
from iqa_soa.tools import SandboxState, ToolRegistry
from iqa_soa.types import QAMode, RuntimeContext


class ExperimentConfigError(ValueError):
    """Experiment configuration is invalid before any run begins."""


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    schema_version: int
    benchmark_path: Path
    policy_path: Path
    models_path: Path
    ablations_path: Path
    output_root: Path
    repetitions: int
    seeds: tuple[int, ...]
    max_agent_steps: int
    shuffle_treatments: bool
    treatments: tuple[str, ...]
    smoke_case_ids: tuple[str, ...]
    raw_jsonl: str
    raw_csv: str
    evidence_subdir: str
    source_path: Path

    def with_overrides(
        self,
        *,
        output_root: str | Path | None = None,
        repetitions: int | None = None,
    ) -> ExperimentConfig:
        if repetitions is not None and repetitions <= 0:
            raise ExperimentConfigError("repetitions override must be positive")
        return ExperimentConfig(
            schema_version=self.schema_version,
            benchmark_path=self.benchmark_path,
            policy_path=self.policy_path,
            models_path=self.models_path,
            ablations_path=self.ablations_path,
            output_root=Path(output_root).resolve() if output_root else self.output_root,
            repetitions=repetitions if repetitions is not None else self.repetitions,
            seeds=self.seeds,
            max_agent_steps=self.max_agent_steps,
            shuffle_treatments=self.shuffle_treatments,
            treatments=self.treatments,
            smoke_case_ids=self.smoke_case_ids,
            raw_jsonl=self.raw_jsonl,
            raw_csv=self.raw_csv,
            evidence_subdir=self.evidence_subdir,
            source_path=self.source_path,
        )


_CONFIG_KEYS = {
    "schema_version",
    "benchmark_path",
    "policy_path",
    "models_path",
    "ablations_path",
    "output_root",
    "repetitions",
    "seeds",
    "max_agent_steps",
    "shuffle_treatments",
    "treatments",
    "smoke_case_ids",
    "raw_jsonl",
    "raw_csv",
    "evidence_subdir",
}


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    source = Path(path).resolve()
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ExperimentConfigError(f"cannot read experiment config {source}: {exc}") from exc
    if not isinstance(data, Mapping):
        raise ExperimentConfigError("experiment config must be a YAML mapping")
    unknown = set(data) - _CONFIG_KEYS
    missing = _CONFIG_KEYS - set(data)
    if unknown or missing:
        raise ExperimentConfigError(
            f"experiment config unknown={sorted(unknown)} missing={sorted(missing)}"
        )
    if data["schema_version"] != 1:
        raise ExperimentConfigError("experiment schema_version must be 1")
    repetitions = _positive_int(data["repetitions"], "repetitions")
    max_agent_steps = _positive_int(data["max_agent_steps"], "max_agent_steps")
    seeds_raw = data["seeds"]
    if not isinstance(seeds_raw, list) or not seeds_raw:
        raise ExperimentConfigError("seeds must be a non-empty list")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in seeds_raw):
        raise ExperimentConfigError("every seed must be an integer")
    if len(set(seeds_raw)) != len(seeds_raw):
        raise ExperimentConfigError("seeds must be unique")
    treatments = _strings(data["treatments"], "treatments")
    for name in treatments:
        treatment_for(name)
    for name in ("raw_jsonl", "raw_csv"):
        value = _nonempty_string(data[name], name)
        if Path(value).name != value:
            raise ExperimentConfigError(f"{name} must be a plain filename")
    shuffle = data["shuffle_treatments"]
    if not isinstance(shuffle, bool):
        raise ExperimentConfigError("shuffle_treatments must be boolean")
    root = _project_root_for(source)

    def resolve(value: Any, name: str) -> Path:
        candidate = Path(_nonempty_string(value, name))
        return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()

    evidence_subdir = _nonempty_string(data["evidence_subdir"], "evidence_subdir")
    if Path(evidence_subdir).name != evidence_subdir:
        raise ExperimentConfigError("evidence_subdir must be one path segment")
    ablations_path = resolve(data["ablations_path"], "ablations_path")
    if not ablations_path.is_file():
        raise ExperimentConfigError(
            f"ablation configuration does not exist: {ablations_path}"
        )
    return ExperimentConfig(
        schema_version=1,
        benchmark_path=resolve(data["benchmark_path"], "benchmark_path"),
        policy_path=resolve(data["policy_path"], "policy_path"),
        models_path=resolve(data["models_path"], "models_path"),
        ablations_path=ablations_path,
        output_root=resolve(data["output_root"], "output_root"),
        repetitions=repetitions,
        seeds=tuple(seeds_raw),
        max_agent_steps=max_agent_steps,
        shuffle_treatments=shuffle,
        treatments=treatments,
        smoke_case_ids=_strings(data["smoke_case_ids"], "smoke_case_ids"),
        raw_jsonl=data["raw_jsonl"],
        raw_csv=data["raw_csv"],
        evidence_subdir=evidence_subdir,
        source_path=source,
    )


class ExperimentRunner:
    """Run every arm in a fresh state and preserve records incrementally."""

    def __init__(
        self,
        config: ExperimentConfig,
        *,
        provider: AgentProvider | None = None,
        policy: Policy | None = None,
    ) -> None:
        self.config = config
        self.provider = provider or load_provider(config.models_path)
        self.base_policy = policy or load_policy(config.policy_path)

    def run(
        self,
        *,
        treatments: Sequence[Treatment | str] | None = None,
        case_ids: Iterable[str] | None = None,
        repetitions: int | None = None,
        frozen_benchmark: FrozenPilotBenchmark | None = None,
        max_total_runs: int | None = None,
        experiment_kind: str | None = None,
        infrastructure_retry_limit: int = 0,
    ) -> Path:
        actual_repetitions = (
            repetitions if repetitions is not None else self.config.repetitions
        )
        if actual_repetitions <= 0:
            raise ExperimentConfigError("repetitions must be positive")
        if infrastructure_retry_limit != 0:
            raise ExperimentConfigError(
                "automatic infrastructure retries are unsupported; preserve each attempt"
            )
        if frozen_benchmark is not None:
            wanted = set(case_ids) if case_ids is not None else None
            if wanted is not None:
                missing = wanted - set(frozen_benchmark.selected_task_ids)
                if missing:
                    raise ExperimentConfigError(
                        f"requested cases are absent from frozen benchmark: {sorted(missing)}"
                    )
            selected_cases = [
                case
                for case in frozen_benchmark.cases
                if wanted is None or case.id in wanted
            ]
            cases = [
                replace(
                    case,
                    budget=frozen_benchmark.resource_budget_policy.effective_budget(
                        case
                    ),
                )
                if frozen_benchmark.resource_budget_policy is not None
                else case
                for case in selected_cases
            ]
        else:
            cases = load_benchmark_cases(self.config.benchmark_path, case_ids=case_ids)
        arms = tuple(
            item if isinstance(item, Treatment) else treatment_for(item)
            for item in (treatments or self.config.treatments)
        )
        if not arms:
            raise ExperimentConfigError("at least one treatment is required")
        if len({item.name for item in arms}) != len(arms):
            raise ExperimentConfigError("treatment names must be unique")

        expected_record_count = len(cases) * actual_repetitions * len(arms)
        if max_total_runs is not None:
            if max_total_runs <= 0:
                raise ExperimentConfigError("max_total_runs must be positive")
            if expected_record_count > max_total_runs:
                raise ExperimentConfigError(
                    "experiment run ceiling exceeded: "
                    f"planned={expected_record_count}, max_total_runs={max_total_runs}"
                )

        resolved_kind = experiment_kind or (
            "deterministic_mechanism_validation"
            if isinstance(self.provider, DeterministicStubProvider)
            else "real_model_pilot"
        )
        if resolved_kind not in {
            "deterministic_mechanism_validation",
            "real_model_connectivity_smoke",
            "real_model_pilot",
            "real_model_ablation_smoke",
        }:
            raise ExperimentConfigError(f"unsupported experiment_kind: {resolved_kind!r}")
        if resolved_kind.startswith("real_model") and isinstance(
            self.provider, DeterministicStubProvider
        ):
            raise ExperimentConfigError(
                "a deterministic provider cannot be labeled as a real-model experiment"
            )
        pilot_schema = frozen_benchmark is not None
        raw_fields = PILOT_RAW_FIELDS_V3 if pilot_schema else REQUIRED_RAW_FIELDS

        experiment_id, experiment_dir = create_experiment_directory(self.config.output_root)
        jsonl_path = experiment_dir / self.config.raw_jsonl
        csv_path = experiment_dir / self.config.raw_csv
        manifest_path = experiment_dir / "manifest.json"
        evidence_root = experiment_dir / self.config.evidence_subdir
        evidence_root.mkdir(parents=True, exist_ok=False)
        manifest = {
            "schema_version": 2 if pilot_schema else 1,
            "raw_schema_version": RAW_SCHEMA_VERSION if pilot_schema else 1,
            # Instrument boundary: see iqa_soa.instrument.  Sources carrying
            # different values must never be pooled analytically.
            "instrument_version": INSTRUMENT_VERSION,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
            "experiment_id": experiment_id,
            "experiment_kind": resolved_kind,
            "created_at": _now(),
            "status": "running",
            "config_path": str(self.config.source_path),
            "benchmark_path": str(self.config.benchmark_path),
            "policy_path": str(self.config.policy_path),
            "ablations_path": str(self.config.ablations_path),
            "provider": self.provider.descriptor(),
            "provider_runtime": self._provider_runtime_provenance(),
            "benchmark_version": (
                frozen_benchmark.benchmark_version if frozen_benchmark else None
            ),
            "benchmark_manifest_path": (
                str(frozen_benchmark.manifest_path) if frozen_benchmark else None
            ),
            "resource_budget_policy": (
                frozen_benchmark.resource_budget_policy.to_dict()
                if frozen_benchmark and frozen_benchmark.resource_budget_policy
                else None
            ),
            "treatments": [item.name for item in arms],
            "repetitions": actual_repetitions,
            "seeds": [self._seed_for(index) for index in range(actual_repetitions)],
            "shuffle_treatments": self.config.shuffle_treatments,
            "case_ids": [case.id for case in cases],
            "expected_record_count": expected_record_count,
            "max_total_runs": max_total_runs,
            "infrastructure_retry_limit": infrastructure_retry_limit,
            "record_count": 0,
            "raw_jsonl": self.config.raw_jsonl,
            "raw_csv": self.config.raw_csv,
            "input_digests": {
                "experiment_config_sha256": _path_digest(self.config.source_path),
                "model_config_sha256": _path_digest(self.config.models_path),
                "ablation_config_sha256": _path_digest(self.config.ablations_path),
                "qa_xml_policy_sha256": _path_digest(self.config.policy_path),
                "qa_xml_schema_sha256": _path_digest(DEFAULT_SCHEMA_PATH),
                "benchmark_sha256": _path_digest(self.config.benchmark_path),
                **(
                    {
                        "benchmark_manifest_sha256": frozen_benchmark.manifest_sha256,
                        "selected_case_set_sha256": _selected_case_set_digest(
                            frozen_benchmark
                        ),
                        "resource_budget_policy_sha256": _resource_budget_policy_digest(
                            frozen_benchmark
                        ),
                    }
                    if frozen_benchmark
                    else {}
                ),
            },
            "software": {
                "artifact_version": __version__,
                "python_version": platform.python_version(),
                "package_source_sha256": _path_digest(
                    Path(__file__).resolve().parents[1],
                    include_suffixes=frozenset({".py"}),
                ),
            },
        }
        _write_manifest(manifest_path, manifest, replace=False)
        # Exclusive-create both raw artifacts before any execution.  Each run is
        # appended immediately, so a later failure cannot erase earlier failures.
        with jsonl_path.open("x", encoding="utf-8", newline="\n"):
            pass
        with csv_path.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=raw_fields)
            writer.writeheader()

        record_count = 0
        for case in cases:
            for repetition in range(actual_repetitions):
                seed = self._seed_for(repetition)
                ordered = self._ordered_treatments(arms, case.id, repetition)
                ordering = [item.name for item in ordered]
                pair_proposals: tuple[str, ...] | None = None
                for treatment_index, treatment in enumerate(ordered):
                    record = self._run_one(
                        experiment_id=experiment_id,
                        experiment_dir=experiment_dir,
                        evidence_root=evidence_root,
                        case=case,
                        treatment=treatment,
                        repetition=repetition,
                        seed=seed,
                        treatment_order=ordering,
                        treatment_index=treatment_index,
                        benchmark_version=(
                            frozen_benchmark.benchmark_version
                            if frozen_benchmark
                            else None
                        ),
                        benchmark_manifest_sha256=(
                            frozen_benchmark.manifest_sha256
                            if frozen_benchmark
                            else None
                        ),
                        experiment_kind=resolved_kind,
                        resource_budget_policy_id=(
                            frozen_benchmark.resource_budget_policy.policy_id
                            if frozen_benchmark
                            and frozen_benchmark.resource_budget_policy is not None
                            else None
                        ),
                    )
                    proposals = tuple(record.pop("_proposed_action_bytes", ()))
                    if isinstance(self.provider, DeterministicStubProvider):
                        if pair_proposals is None:
                            pair_proposals = proposals
                        elif pair_proposals != proposals:
                            record["error"] = _join_error(
                                record.get("error"),
                                "paired proposal invariant failed: deterministic actions differ",
                            )
                    append_raw_record(
                        jsonl_path, csv_path, record, fieldnames=raw_fields
                    )
                    record_count += 1
        manifest.update(
            {
                "status": "complete",
                "completed_at": _now(),
                "record_count": record_count,
            }
        )
        _write_manifest(manifest_path, manifest, replace=True)
        return experiment_dir

    def _run_one(
        self,
        *,
        experiment_id: str,
        experiment_dir: Path,
        evidence_root: Path,
        case: BenchmarkCase,
        treatment: Treatment,
        repetition: int,
        seed: int,
        treatment_order: Sequence[str],
        treatment_index: int,
        benchmark_version: str | None,
        benchmark_manifest_sha256: str | None,
        experiment_kind: str,
        resource_budget_policy_id: str | None,
    ) -> dict[str, Any]:
        run_id = f"{case.id}-r{repetition:03d}-{treatment.name}-{uuid4().hex[:12]}"
        evidence_path = evidence_root / f"{run_id}.jsonl"
        started = time.perf_counter()
        timestamp = _now()
        context = RuntimeContext(
            experiment_id=experiment_id,
            run_id=run_id,
            task_id=case.id,
            category=case.category.value,
            qa_mode=treatment.qa_mode,
            provider=self.provider.name,
            model=self.provider.model,
            repetition=repetition,
            seed=seed,
            user_prompt=case.user_prompt,
            untrusted_content=tuple(
                case.environment.files.get(source, "")
                for source in (case.attack.untrusted_sources if case.attack else ())
            ),
            # Case constraints are runtime inputs, but the evaluator-only unsafe
            # and expected action labels are deliberately absent.
            metadata={
                "benchmark_version": benchmark_version or f"case-schema-{case.schema_version}",
                "requirement_id": f"benchmark:{case.id}",
                "untrusted_sources": (
                    case.attack.untrusted_sources if case.attack else ()
                ),
                "protected_resources": case.protected_resources,
                "protected_data": case.protected_data,
                "forbidden_output_values": case.protected_data,
            },
        )
        state = SandboxState.from_environment(case.initial_state_dict())
        initial_fingerprint = state_fingerprint(state)
        context.metadata["rollback_point"] = f"initial-state:{initial_fingerprint}"
        registry = ToolRegistry.default(state)
        policy = self.base_policy.with_case_constraints(
            allowed_actions=case.allowed_actions,
            forbidden_actions=case.forbidden_actions,
            # The policy model intersects action/resource allowlists. Keeping
            # both preserves the benchmark's two independently controlled axes.
            allowed_resources=case.allowed_resources,
            forbidden_resources=case.forbidden_resources,
            protected_resources=case.protected_resources,
            protected_values=case.protected_data,
            budget=case.budget,
            output_forbidden_values=case.protected_data,
            output_require_evidence=treatment.enabled_guards.get("evidence", False),
        )
        logger = EvidenceLogger(evidence_path, detailed=treatment.detailed_evidence)
        chain = build_guard_chain(treatment.enabled_guards)
        gateway = ServiceGateway(
            registry,
            chain,
            policy,
            logger,
            detailed_evidence=treatment.detailed_evidence,
        )
        # A model-call ceiling is a governance intervention, not a benchmark
        # execution shortcut: OFF and the budget ablation must be able to expose
        # the same over-budget plan. Budget-enabled arms stop before issuing the
        # next provider request.
        max_steps = self.config.max_agent_steps
        if (
            treatment.enabled_guards.get("budget", False)
            and case.budget.max_model_calls is not None
        ):
            max_steps = min(max_steps, case.budget.max_model_calls)
        agent = ExperimentalAgent(
            self.provider,
            gateway,
            system_prompt=case.system_prompt,
            max_steps=max_steps,
        )
        try:
            agent_run = agent.run(
                user_prompt=case.user_prompt,
                scripted_actions=case.scripted_actions,
                context=context,
                canonical_resources=case.canonical_resources,
            )
        except Exception as exc:  # preserve provider/extension failures as rows
            agent_run = AgentRun(
                outcomes=(),
                provider_responses=(),
                proposed_action_bytes=(),
                model_latency_ms=0.0,
                error=f"{type(exc).__name__}: execution failed",
                failure_class="qa_failure",
            )
        if not agent_run.outcomes:
            # QA-IUM represents lifecycle observations, not only tool actions.
            # Preserve a structured terminal fragment for zero-action/provider-
            # failure runs without serializing potentially sensitive exception text.
            logger.append(
                {
                    "event_type": "run_terminal",
                    "experiment_id": context.experiment_id,
                    "run_id": context.run_id,
                    "task_id": context.task_id,
                    "qa_mode": context.qa_mode.value,
                    "action_id": None,
                    "final_decision": "NO_ACTION",
                    "executed": False,
                    "error_present": bool(agent_run.error),
                    "failure_class": agent_run.failure_class,
                    "provider_response_count": len(agent_run.provider_responses),
                    "provider_attempt_count": len(agent_run.provider_attempts),
                    "model_refusal": agent_run.model_refusal,
                    "no_action": agent_run.no_action,
                    "qa_ium_compatible_fragment": True,
                }
            )
        end_to_end_latency_ms = (time.perf_counter() - started) * 1000.0
        context.usage.elapsed_time_ms = max(
            context.usage.elapsed_time_ms, end_to_end_latency_ms
        )
        events = load_evidence_events(evidence_path)
        metrics = collect_run_metrics(
            case=case,
            agent_run=agent_run,
            context=context,
            evidence_events=events,
            end_to_end_latency_ms=end_to_end_latency_ms,
        )
        relative_trace = evidence_path.relative_to(experiment_dir).as_posix()
        controlled_digest = controlled_input_digest(case, self.provider, seed)
        provider_descriptor = self.provider.descriptor()
        final_attempt = (
            agent_run.provider_attempts[-1] if agent_run.provider_attempts else {}
        )
        pair_id = hashlib.sha256(
            json.dumps(
                {
                    "task_id": case.id,
                    "repetition": repetition,
                    "seed": seed,
                    "provider": self.provider.name,
                    "model": self.provider.model,
                    "controlled_input_digest": controlled_digest,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:24]
        return {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "timestamp": timestamp,
            "task_id": case.id,
            "category": case.category.value,
            "repetition": repetition,
            "seed": seed,
            "provider": self.provider.name,
            "model": self.provider.model,
            "experiment_kind": experiment_kind,
            "benchmark_version": benchmark_version,
            "benchmark_manifest_sha256": benchmark_manifest_sha256,
            "resource_budget_policy_id": resource_budget_policy_id,
            "pair_id": pair_id,
            "qa_mode": treatment.qa_mode.value,
            "ablation": treatment.ablation,
            "treatment_order": list(treatment_order),
            "treatment_index": treatment_index,
            "enabled_guards": dict(treatment.enabled_guards),
            "initial_state_fingerprint": initial_fingerprint,
            "final_state_fingerprint": state_fingerprint(state),
            "controlled_input_digest": controlled_digest,
            "system_prompt_sha256": _text_digest(case.system_prompt),
            "user_prompt_sha256": _text_digest(case.user_prompt),
            "policy_sha256": _path_digest(self.config.policy_path),
            "tool_state_sha256": initial_fingerprint,
            "temperature": provider_descriptor.get("temperature"),
            "top_p": provider_descriptor.get("top_p"),
            "max_output_tokens": provider_descriptor.get("max_output_tokens"),
            "provider_seed_supported": provider_descriptor.get("supports_seed"),
            "effective_provider_seed": final_attempt.get("effective_seed"),
            "provider_attempt_count": len(agent_run.provider_attempts),
            "provider_attempts": [dict(item) for item in agent_run.provider_attempts],
            "provider_request_id": final_attempt.get("request_id"),
            "provider_client_request_id": final_attempt.get("client_request_id"),
            "provider_response_id": final_attempt.get("response_id"),
            "effective_model": final_attempt.get("effective_model"),
            "finish_reason": final_attempt.get("finish_reason"),
            "system_fingerprint": final_attempt.get("system_fingerprint"),
            "failure_class": agent_run.failure_class,
            "model_refusal": agent_run.model_refusal,
            "no_action": agent_run.no_action,
            "invalid_action_format": agent_run.failure_class
            in {"invalid_json", "invalid_action_format", "invalid_tool_call"},
            "tool_call_parse_failure": agent_run.failure_class == "invalid_tool_call",
            "instrument_version": INSTRUMENT_VERSION,
            "terminal_no_action": agent_run.terminal_no_action,
            "terminal_no_action_attempts": agent_run.terminal_no_action_attempts,
            "no_action_after_actions": agent_run.no_action_after_actions,
            "provider_multi_tool_call": agent_run.provider_multi_tool_call,
            "provider_max_tool_calls": agent_run.provider_max_tool_calls,
            "queued_action_count": agent_run.queued_action_count,
            "tool_contract_policy": provider_descriptor.get("tool_contract_policy"),
            "tool_contract_regression_detected": (
                agent_run.tool_contract_regression_detected
            ),
            "multi_call_overflow": agent_run.multi_call_overflow,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
            "proposed_action_count": len(agent_run.proposed_action_bytes),
            "proposed_action_digest": _proposal_digest(
                agent_run.proposed_action_bytes
            ),
            "trace_path": relative_trace,
            "error": agent_run.error or _outcome_errors(agent_run.outcomes),
            "_proposed_action_bytes": agent_run.proposed_action_bytes,
            **metrics,
        }

    def _provider_runtime_provenance(self) -> dict[str, Any] | None:
        """Record inference-free provider runtime identity, or None when N/A.

        Phase B could not prove which chat template rendered the frozen runs,
        because nothing captured the runtime's identity.  This closes that gap
        without ever invoking the model, and never fails an experiment.
        """

        if not isinstance(self.provider, OpenAICompatibleProvider):
            return None
        return probe_runtime_provenance(self.provider.endpoint, self.provider.model)

    def _seed_for(self, repetition: int) -> int:
        if repetition < len(self.config.seeds):
            return self.config.seeds[repetition]
        digest = hashlib.sha256(
            f"{self.config.seeds[repetition % len(self.config.seeds)]}:{repetition}".encode()
        ).digest()
        return int.from_bytes(digest[:4], "big")

    def _ordered_treatments(
        self,
        arms: Sequence[Treatment],
        case_id: str,
        repetition: int,
    ) -> tuple[Treatment, ...]:
        ordered = list(arms)
        if self.config.shuffle_treatments:
            # Seed one permutation per complete block, then rotate it.  Every
            # treatment therefore occupies every ordinal position once in each
            # full block while the ordering remains deterministic and recorded.
            block = repetition // len(ordered)
            rotation = repetition % len(ordered)
            block_seed = self._seed_for(block * len(ordered))
            arm_names = ",".join(item.name for item in ordered)
            material = f"{block_seed}:{case_id}:{block}:{arm_names}".encode("utf-8")
            local_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
            random.Random(local_seed).shuffle(ordered)
            ordered = ordered[rotation:] + ordered[:rotation]
        return tuple(ordered)


def load_provider(
    models_path: str | Path, *, provider_name: str | None = None
) -> AgentProvider:
    source = Path(models_path)
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ExperimentConfigError(f"cannot read model config {source}: {exc}") from exc
    if not isinstance(data, Mapping) or set(data) != {
        "schema_version", "default_provider", "providers"
    }:
        raise ExperimentConfigError("models config has an invalid top-level schema")
    schema_version = data["schema_version"]
    if schema_version not in {1, 2} or not isinstance(data["providers"], Mapping):
        raise ExperimentConfigError("models schema_version/providers is invalid")
    name = provider_name or _nonempty_string(data["default_provider"], "default_provider")
    raw = data["providers"].get(name)
    if not isinstance(raw, Mapping):
        raise ExperimentConfigError(f"default provider {name!r} is not configured")
    provider_type = raw.get("type")
    if provider_type == "deterministic_stub":
        unknown = set(raw) - {"type", "model"}
        if unknown:
            raise ExperimentConfigError(f"unknown stub provider fields: {sorted(unknown)}")
        return DeterministicStubProvider(_nonempty_string(raw.get("model"), "model"))
    if provider_type == "openai_compatible":
        unknown = set(raw) - {
            "type",
            "enabled",
            "endpoint",
            "base_url_env",
            "model",
            "model_env",
            "api_key_env",
            "temperature",
            "top_p",
            "max_output_tokens",
            "seed",
            "supports_seed",
            "protocol",
            "timeout_seconds",
            "tool_contract_policy",
        }
        if unknown:
            raise ExperimentConfigError(f"unknown HTTP provider fields: {sorted(unknown)}")
        if raw.get("enabled") is not True:
            raise ExperimentConfigError("HTTP provider must be explicitly enabled in models config")
        endpoint = raw.get("endpoint")
        base_url_env = raw.get("base_url_env")
        model = raw.get("model")
        model_env = raw.get("model_env")
        top_p = raw.get("top_p")
        return OpenAICompatibleProvider(
            endpoint=(
                _nonempty_string(endpoint, "endpoint") if endpoint is not None else None
            ),
            base_url_env=(
                _nonempty_string(base_url_env, "base_url_env")
                if base_url_env is not None
                else None
            ),
            model=_nonempty_string(model, "model") if model is not None else None,
            model_env=(
                _nonempty_string(model_env, "model_env")
                if model_env is not None
                else None
            ),
            api_key_env=_nonempty_string(raw.get("api_key_env"), "api_key_env"),
            temperature=float(raw.get("temperature", 0.0)),
            top_p=None if top_p is None else float(top_p),
            max_output_tokens=(
                None
                if raw.get("max_output_tokens") is None
                else _positive_int(raw.get("max_output_tokens"), "max_output_tokens")
            ),
            seed=raw.get("seed"),
            supports_seed=_boolean(raw.get("supports_seed", True), "supports_seed"),
            protocol=_nonempty_string(raw.get("protocol", "native_tools"), "protocol"),
            timeout_seconds=float(raw.get("timeout_seconds", 60.0)),
            tool_contract_policy=_nonempty_string(
                raw.get("tool_contract_policy", DEFAULT_TOOL_CONTRACT_POLICY),
                "tool_contract_policy",
            ),
        )
    raise ExperimentConfigError(f"unsupported provider type: {provider_type!r}")


def load_policy(path: str | Path) -> Policy:
    """Load QA-XML using the runtime parser; fail before creating run output."""

    source = Path(path)
    if not source.exists():
        raise ExperimentConfigError(f"QA-XML policy does not exist: {source}")
    try:
        from iqa_soa.iqa.qa_xml import parse_qa_xml
    except ImportError as exc:
        raise ExperimentConfigError("runtime QA-XML parser is unavailable") from exc
    try:
        return parse_qa_xml(source)
    except Exception as exc:
        raise ExperimentConfigError(f"QA-XML policy validation failed: {exc}") from exc


def create_experiment_directory(output_root: str | Path) -> tuple[str, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        experiment_id = f"exp-{timestamp}-{uuid4().hex}"
        target = root / experiment_id
        try:
            target.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        return experiment_id, target
    raise FileExistsError("could not allocate a unique experiment directory")


def _write_manifest(
    path: Path, manifest: Mapping[str, Any], *, replace: bool
) -> None:
    """Write the run-state marker without exposing a partially rewritten manifest."""

    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not replace:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
        return
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
    temporary.replace(path)


def append_raw_record(
    jsonl_path: Path,
    csv_path: Path,
    record: Mapping[str, Any],
    *,
    fieldnames: Sequence[str] = REQUIRED_RAW_FIELDS,
) -> None:
    missing = set(fieldnames) - set(record)
    if missing:
        raise ValueError(f"raw record missing required fields: {sorted(missing)}")
    line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    with jsonl_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
    csv_row = {key: _csv_value(record.get(key)) for key in fieldnames}
    with csv_path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=fieldnames).writerow(csv_row)
        handle.flush()


def state_fingerprint(state: SandboxState) -> str:
    observable = {
        "files": state.files,
        "database": state.database,
        "messages": state.messages,
        "api_responses": state.api_responses,
        "api_calls": state.api_calls,
        "shell_history": state.shell_history,
        "robot_position": state.robot_position,
        "robot_holding": state.robot_holding,
        "robot_history": state.robot_history,
        "faults": state.faults,
        "operation_log": state.operation_log,
    }
    raw = json.dumps(observable, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _path_digest(
    path: str | Path, *, include_suffixes: frozenset[str] | None = None
) -> str:
    """Hash a file or a directory tree including stable relative names."""

    source = Path(path)
    files = [source] if source.is_file() else sorted(
        item
        for item in source.rglob("*")
        if item.is_file()
        and (include_suffixes is None or item.suffix in include_suffixes)
    )
    if not files:
        raise ExperimentConfigError(f"cannot hash missing or empty input path: {source}")
    digest = hashlib.sha256()
    for item in files:
        relative = item.name if source.is_file() else item.relative_to(source).as_posix()
        name = relative.encode("utf-8")
        content = item.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def controlled_input_digest(
    case: BenchmarkCase, provider: AgentProvider, seed: int
) -> str:
    """Fingerprint every controlled input other than the QA treatment."""

    projection = {
        "schema_version": case.schema_version,
        "task_id": case.id,
        "category": case.category.value,
        "system_prompt": case.system_prompt,
        "user_prompt": case.user_prompt,
        "environment": case.initial_state_dict(),
        "scripted_actions": [action.to_dict() for action in case.scripted_actions],
        "allowed_actions": [
            {"tool": rule.tool, "resource": rule.resource}
            for rule in case.allowed_actions
        ],
        "forbidden_actions": [
            {"tool": rule.tool, "resource": rule.resource}
            for rule in case.forbidden_actions
        ],
        "allowed_resources": case.allowed_resources,
        "forbidden_resources": case.forbidden_resources,
        "protected_data": case.protected_data,
        "protected_resources": case.protected_resources,
        "budget": case.budget.to_dict(),
        "attack": (
            {
                "type": case.attack.type,
                "payload_location": case.attack.payload_location,
                "untrusted_sources": case.attack.untrusted_sources,
                "description": case.attack.description,
            }
            if case.attack
            else None
        ),
        "fault": (
            {
                "type": case.fault.type,
                "action_id": case.fault.action_id,
                "hard_policy": case.fault.hard_policy,
                "description": case.fault.description,
            }
            if case.fault
            else None
        ),
        "ground_truth": {
            "unsafe_action_ids": case.ground_truth.unsafe_action_ids,
            "expected_action_ids": case.ground_truth.expected_action_ids,
            "task_should_succeed": case.ground_truth.task_should_succeed,
            "expected_output_contains": case.ground_truth.expected_output_contains,
            "safe_block_success": case.ground_truth.safe_block_success,
            "protected_data_must_not_leak": (
                case.ground_truth.protected_data_must_not_leak
            ),
            "forbidden_action_must_not_execute": (
                case.ground_truth.forbidden_action_must_not_execute
            ),
            "fault_must_be_contained": case.ground_truth.fault_must_be_contained,
        },
        "tags": case.tags,
        "seed": seed,
        "provider": provider.descriptor(),
    }
    raw = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _proposal_digest(proposals: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for proposal in proposals:
        encoded = proposal.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _selected_case_set_digest(benchmark: FrozenPilotBenchmark) -> str:
    projection = [
        {
            "task_id": task_id,
            "sha256": benchmark.case_hashes[task_id],
        }
        for task_id in benchmark.selected_task_ids
    ]
    raw = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resource_budget_policy_digest(benchmark: FrozenPilotBenchmark) -> str:
    """Digest the policy that transforms immutable case budgets at runtime."""

    policy = benchmark.resource_budget_policy
    payload: dict[str, object] = (
        policy.to_dict() if policy is not None else {"policy_id": None}
    )
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _project_root_for(config_path: Path) -> Path:
    return config_path.parent.parent if config_path.parent.name == "configs" else config_path.parent


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExperimentConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _strings(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ExperimentConfigError(f"{name} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ExperimentConfigError(f"{name} contains duplicates")
    return tuple(value)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExperimentConfigError(f"{name} must be a positive integer")
    return cast(int, value)


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ExperimentConfigError(f"{name} must be boolean")
    return value


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _outcome_errors(outcomes: Sequence[Any]) -> str | None:
    errors = [str(outcome.error) for outcome in outcomes if outcome.error]
    return "; ".join(errors) if errors else None


def _join_error(left: Any, right: str) -> str:
    return f"{left}; {right}" if left else right


__all__ = [
    "ExperimentConfig",
    "ExperimentConfigError",
    "ExperimentRunner",
    "append_raw_record",
    "create_experiment_directory",
    "controlled_input_digest",
    "load_experiment_config",
    "load_policy",
    "load_provider",
    "state_fingerprint",
]
