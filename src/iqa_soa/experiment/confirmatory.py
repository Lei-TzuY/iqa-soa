"""Frozen Work Unit 5 confirmatory execution boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence, cast
from urllib import error as urlerror

from iqa_soa import __version__
from iqa_soa.agent.providers import (
    AgentProvider,
    DeterministicStubProvider,
    OpenAICompatibleProvider,
    ProviderError,
    ProviderFailureOrigin,
    ProviderResponse,
)
from iqa_soa.benchmark import BenchmarkCase, load_benchmark_cases
from iqa_soa.experiment.confirmatory_assignment import (
    AssignmentManifestV1,
    AssignmentNotPersistedError,
    RandomizationMcProvenanceV1,
    _publish_assignment_no_clobber,
    _stage_assignment,
    _sync_directory_metadata,
    _unlink_pending_after_durable_publication,
    load_assignment_manifest,
    load_randomization_mc_provenance,
    resolve_label,
)
from iqa_soa.experiment.confirmatory_eligibility import (
    EligibilityManifestV1,
    load_eligibility_manifest,
)
from iqa_soa.experiment.confirmatory_registration import (
    CONFIRMATORY_PROFILE,
    ConfirmatoryRegistrationError,
    ConfirmatoryPositionV1,
    RegistrationManifest,
    RetryPolicyV1,
    RuntimeSnapshotV1,
    canonical_json_bytes,
    load_registration_draft,
    load_registration_manifest,
    parse_artifact,
    serialize_artifact,
)
from iqa_soa.experiment.runner import (
    ExperimentConfig,
    ExperimentConfigError,
    ExperimentRunner,
    PositionExecutionError,
    PositionFailureOrigin,
    benchmark_source_sha256,
    load_experiment_config,
    load_policy,
    package_source_sha256,
)
from iqa_soa.experiment.treatments import Treatment, treatment_for
from iqa_soa.instrument import NATIVE_TOOL_ADAPTER_VERSION
from iqa_soa.types import Action, QAMode


class ConfirmatoryExecutionError(RuntimeError):
    """The WU5 execution boundary refused an invalid or ambiguous state."""


class RuntimeIdentityRefused(ConfirmatoryExecutionError):
    """A live pre-execution runtime identity differs from registration."""


class ProviderFactory(Protocol):
    """Create the one fresh provider owned by a physical position."""

    def create_for_position(
        self, position: ConfirmatoryPositionV1
    ) -> AgentProvider: ...


CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1 = (
    b"CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1\n"
)

OBSERVED = "OBSERVED"
UNOBSERVED_INFRASTRUCTURE = "UNOBSERVED_INFRASTRUCTURE"
UNOBSERVED_INSTRUMENTATION = "UNOBSERVED_INSTRUMENTATION"

FAILURE_NONE = "NONE"
PROVIDER_FAILURE = "PROVIDER_FAILURE"
TIMEOUT = "TIMEOUT"
TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
RUNTIME_FAILURE = "RUNTIME_FAILURE"
INSTRUMENTATION_FAILURE = "INSTRUMENTATION_FAILURE"

_ENDPOINT_FIELDS = (
    "unsafe_action_executed",
    "safety_security_violation",
    "unsafe_action_proposed",
    "constraint_violation",
    "privacy_leak",
    "attack_success",
)

EXECUTION_ROW_KEYS = (
    "confirmatory_profile",
    "design_id",
    "final_registration_digest",
    "eligibility_manifest_digest",
    "assignment_digest",
    "position_id",
    "task_id",
    "provider",
    "model",
    "repetition",
    "provider_seed",
    "slot",
    "baseline_label",
    "task_assignment_bit",
    "qa_mode",
    "runtime_snapshot_digest",
    "runtime_identity_digest",
    "timestamp",
    "observation_status",
    "failure_class",
    "error",
    *_ENDPOINT_FIELDS,
)

_RUNTIME_SNAPSHOT_KEYS = frozenset(
    {
        "schema_version",
        "provider_name",
        "model",
        "endpoint",
        "provider_config_digest",
        "provider_parameters_digest",
        "timeout_seconds",
        "retry_policy",
        "tool_contract_policy",
        "native_tool_adapter_version",
        "package_source_sha256",
        "python_version",
        "artifact_version",
        "prompt_digest",
        "experiment_config_digest",
        "models_config_digest",
        "environment_fingerprint",
        "runtime_identity_digest",
        "captured_at",
        "self_digest",
    }
)
_RETRY_POLICY_KEYS = frozenset(
    {
        "max_attempts",
        "backoff_kind",
        "initial_delay_seconds",
        "max_delay_seconds",
        "retryable_error_classes",
    }
)
_PROVIDER_PARAMETER_SOURCES = {
    "canonical_resources": "BenchmarkCase.canonical_resources",
    "history": "ExperimentalAgent.prior_sandbox_history",
    "scripted_actions": "BenchmarkCase.scripted_actions",
    "seed": "ConfirmatoryPositionV1.provider_seed",
    "step": "ExperimentalAgent.zero_based_step",
    "system_prompt": "BenchmarkCase.system_prompt",
    "user_prompt": "BenchmarkCase.user_prompt",
}
_ROW_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_FINAL_ROW = re.compile(r"^([0-9a-f]{64})\.json$")
_PENDING_ROW = re.compile(r"^([0-9a-f]{64})\.json\.pending$")


def _canonical_digest(payload: Any) -> str:
    try:
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    except ConfirmatoryRegistrationError as error:
        raise ConfirmatoryExecutionError(
            "runtime identity preimage is not canonically serializable"
        ) from error


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ConfirmatoryExecutionError(f"cannot read runtime identity input: {path}") from error


def _benchmark_source_sha256(path: Path) -> str:
    """Digest the benchmark SOURCE ROOT named by ``config.benchmark_path``.

    ``benchmark_path`` is a benchmark source root, not one file: every
    production configuration points it at a directory and the benchmark loaders
    treat it as a root.  The file-only digest this field originally used could
    therefore never be computed against a real configuration.  The repository
    already owns exactly one benchmark identity for this input -- the tree
    digest ``ExperimentRunner`` records as ``benchmark_sha256`` -- so the
    correction reuses it instead of inventing a second one.  Unreadable, missing
    or empty benchmark source fails closed; it never degrades to a digest over
    nothing.
    """

    try:
        return benchmark_source_sha256(path)
    except (ExperimentConfigError, OSError) as error:
        raise ConfirmatoryExecutionError(
            f"cannot read runtime identity benchmark source: {path}"
        ) from error


def _canonical_decimal(value: float) -> str:
    decimal = Decimal(str(value))
    if not decimal.is_finite():
        raise ConfirmatoryExecutionError("provider timeout is not finite")
    rendered = format(decimal, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _provider_implementation(provider: AgentProvider) -> str:
    provider_type = type(provider)
    return f"{provider_type.__module__}.{provider_type.__qualname__}"


def _validate_provider_parameter_contract() -> None:
    parameters = inspect.signature(AgentProvider.generate_action).parameters
    call_parameters = {
        name: parameter
        for name, parameter in parameters.items()
        if name != "self"
    }
    if set(call_parameters) != set(_PROVIDER_PARAMETER_SOURCES):
        raise ConfirmatoryExecutionError(
            "AgentProvider.generate_action parameter contract drifted"
        )
    if any(
        parameter.kind is not inspect.Parameter.KEYWORD_ONLY
        for parameter in call_parameters.values()
    ):
        raise ConfirmatoryExecutionError(
            "AgentProvider.generate_action parameters must remain keyword-only"
        )


def capture_runtime_snapshot_v1(
    *,
    config: ExperimentConfig,
    provider: AgentProvider,
) -> RuntimeSnapshotV1:
    """Capture the sole repository-owned production RuntimeSnapshotV1."""

    if not isinstance(config, ExperimentConfig):
        raise ConfirmatoryExecutionError("config must be an ExperimentConfig")
    if not isinstance(provider, AgentProvider):
        raise ConfirmatoryExecutionError("provider must implement AgentProvider")

    provider_name = provider.name
    model = provider.model
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ConfirmatoryExecutionError("provider.name must be non-empty")
    if not isinstance(model, str) or not model.strip():
        raise ConfirmatoryExecutionError("provider.model must be non-empty")

    try:
        descriptor = provider.descriptor()
    except Exception as error:
        raise ConfirmatoryExecutionError(
            "provider descriptor capture failed"
        ) from error
    if not isinstance(descriptor, Mapping):
        raise ConfirmatoryExecutionError("provider descriptor must be a mapping")
    descriptor_snapshot = dict(descriptor)
    implementation = _provider_implementation(provider)
    provider_config_digest = _canonical_digest(
        {
            "schema_version": "ProviderConfigIdentityV1",
            "provider_implementation": implementation,
            "descriptor": descriptor_snapshot,
        }
    )

    if type(provider) is OpenAICompatibleProvider:
        endpoint = descriptor_snapshot.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint:
            raise ConfirmatoryExecutionError(
                "OpenAI-compatible provider descriptor has no endpoint"
            )
        timeout_seconds = _canonical_decimal(provider.timeout_seconds)
        tool_contract_policy = descriptor_snapshot.get("tool_contract_policy")
        if not isinstance(tool_contract_policy, str) or not tool_contract_policy:
            raise ConfirmatoryExecutionError(
                "OpenAI-compatible provider tool contract policy is invalid"
            )
    elif type(provider) is DeterministicStubProvider:
        endpoint = f"local://{provider_name}/{model}"
        timeout_seconds = "0"
        tool_contract_policy = "none"
    else:
        raise ConfirmatoryExecutionError(
            f"unsupported provider implementation: {implementation}"
        )

    _validate_provider_parameter_contract()
    provider_parameters_digest = _canonical_digest(
        {
            "schema_version": "ProviderParameterSourceTemplateV1",
            "provider_config_digest": provider_config_digest,
            "generate_action": dict(_PROVIDER_PARAMETER_SOURCES),
        }
    )
    try:
        package_digest = package_source_sha256()
    except (ExperimentConfigError, OSError) as error:
        raise ConfirmatoryExecutionError(
            "cannot establish package source digest"
        ) from error
    prompt_digest = _canonical_digest(
        {
            "schema_version": "PromptSourceTemplateV1",
            "provider_implementation": implementation,
            "package_source_sha256": package_digest,
            "system_prompt_source": "BenchmarkCase.system_prompt",
            "user_prompt_source": "BenchmarkCase.user_prompt",
            "step_source": "ExperimentalAgent.zero_based_step",
            "history_source": "ExperimentalAgent.prior_sandbox_history",
            "canonical_resources_source": "BenchmarkCase.canonical_resources",
            "scripted_actions_source": "BenchmarkCase.scripted_actions",
        }
    )

    models_config_digest = _file_sha256(config.models_path)
    experiment_config_digest = _canonical_digest(
        {
            "schema_version": "ExperimentExecutionConfigIdentityV1",
            "config_schema_version": config.schema_version,
            "source_config_sha256": _file_sha256(config.source_path),
            "benchmark_sha256": _benchmark_source_sha256(config.benchmark_path),
            "policy_sha256": _file_sha256(config.policy_path),
            "models_sha256": models_config_digest,
            "ablations_sha256": _file_sha256(config.ablations_path),
            "repetitions": config.repetitions,
            "seeds": list(config.seeds),
            "max_agent_steps": config.max_agent_steps,
            "shuffle_treatments": config.shuffle_treatments,
            "treatments": list(config.treatments),
            "smoke_case_ids": list(config.smoke_case_ids),
            "raw_jsonl": config.raw_jsonl,
            "raw_csv": config.raw_csv,
            "evidence_subdir": config.evidence_subdir,
        }
    )
    python_version = platform.python_version()
    environment_fingerprint = _canonical_digest(
        {
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "platform_machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "python_version": python_version,
            "package_source_sha256": package_digest,
            "provider_endpoint": endpoint,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
        }
    )
    captured_at = _capture_timestamp()
    snapshot = RuntimeSnapshotV1(
        provider_name=provider_name,
        model=model,
        endpoint=endpoint,
        provider_config_digest=provider_config_digest,
        provider_parameters_digest=provider_parameters_digest,
        timeout_seconds=timeout_seconds,
        retry_policy=RetryPolicyV1(
            max_attempts=1,
            backoff_kind="NONE",
            initial_delay_seconds="0",
            max_delay_seconds="0",
            retryable_error_classes=(),
        ),
        tool_contract_policy=tool_contract_policy,
        native_tool_adapter_version=NATIVE_TOOL_ADAPTER_VERSION,
        package_source_sha256=package_digest,
        python_version=python_version,
        artifact_version=__version__,
        prompt_digest=prompt_digest,
        experiment_config_digest=experiment_config_digest,
        models_config_digest=models_config_digest,
        environment_fingerprint=environment_fingerprint,
        captured_at=captured_at,
    )
    _validate_live_snapshot(snapshot)
    return snapshot


def _capture_runtime_snapshot_for_execution(
    *, config: ExperimentConfig, provider: AgentProvider
) -> RuntimeSnapshotV1:
    """Private monkeypatch seam around the one production capture call."""

    return capture_runtime_snapshot_v1(config=config, provider=provider)


class _DispatchObservingProvider(AgentProvider):
    """Forward one provider while retaining a structured failure origin."""

    def __init__(self, provider: AgentProvider) -> None:
        self._provider = provider
        self.name = provider.name
        self.model = provider.model
        self.failure_origin: str | None = None

    def descriptor(self) -> dict[str, Any]:
        return self._provider.descriptor()

    def generate_action(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        scripted_actions: Sequence[Action],
        step: int,
        seed: int,
        history: Sequence[Mapping[str, Any]] = (),
        canonical_resources: Sequence[str] = (),
    ) -> ProviderResponse | None:
        try:
            return self._provider.generate_action(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                scripted_actions=scripted_actions,
                step=step,
                seed=seed,
                history=history,
                canonical_resources=canonical_resources,
            )
        except ProviderError as error:
            self.failure_origin = _provider_failure_origin(error)
            raise
        except Exception:
            self.failure_origin = RUNTIME_FAILURE
            raise


def _provider_failure_origin(error: ProviderError) -> str | None:
    if error.failure_origin is ProviderFailureOrigin.MODEL_OUTPUT:
        return None
    failure_class = error.failure_class
    if failure_class == "timeout":
        return TIMEOUT
    if failure_class in {"transport", "transport_failure"}:
        return TRANSPORT_FAILURE
    cause = error.__cause__
    if isinstance(cause, urlerror.HTTPError):
        return PROVIDER_FAILURE
    if isinstance(cause, urlerror.URLError):
        return TRANSPORT_FAILURE
    if failure_class in {"provider_error", "rate_limit"}:
        return PROVIDER_FAILURE
    return PROVIDER_FAILURE


def _capture_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _timestamp_instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or _ROW_TIMESTAMP.fullmatch(value) is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def _runtime_snapshot_from_artifact(artifact: dict[str, Any]) -> RuntimeSnapshotV1:
    if set(artifact) != _RUNTIME_SNAPSHOT_KEYS:
        raise ConfirmatoryExecutionError("runtime snapshot must have exactly 20 keys")
    retry = artifact.get("retry_policy")
    if not isinstance(retry, dict) or set(retry) != _RETRY_POLICY_KEYS:
        raise ConfirmatoryExecutionError("runtime snapshot retry_policy schema is invalid")
    retryable = retry.get("retryable_error_classes")
    if not isinstance(retryable, list):
        raise ConfirmatoryExecutionError(
            "runtime snapshot retryable_error_classes must be an array"
        )
    try:
        snapshot = RuntimeSnapshotV1(
            provider_name=artifact["provider_name"],
            model=artifact["model"],
            endpoint=artifact["endpoint"],
            provider_config_digest=artifact["provider_config_digest"],
            provider_parameters_digest=artifact["provider_parameters_digest"],
            timeout_seconds=artifact["timeout_seconds"],
            retry_policy=RetryPolicyV1(
                max_attempts=retry["max_attempts"],
                backoff_kind=retry["backoff_kind"],
                initial_delay_seconds=retry["initial_delay_seconds"],
                max_delay_seconds=retry["max_delay_seconds"],
                retryable_error_classes=tuple(retryable),
            ),
            tool_contract_policy=artifact["tool_contract_policy"],
            native_tool_adapter_version=artifact["native_tool_adapter_version"],
            package_source_sha256=artifact["package_source_sha256"],
            python_version=artifact["python_version"],
            artifact_version=artifact["artifact_version"],
            prompt_digest=artifact["prompt_digest"],
            experiment_config_digest=artifact["experiment_config_digest"],
            models_config_digest=artifact["models_config_digest"],
            environment_fingerprint=artifact["environment_fingerprint"],
            captured_at=artifact["captured_at"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfirmatoryExecutionError("runtime snapshot schema is invalid") from error
    if artifact["schema_version"] != snapshot.schema_version:
        raise ConfirmatoryExecutionError("runtime snapshot schema_version mismatch")
    if artifact["runtime_identity_digest"] != snapshot.runtime_identity_digest:
        raise ConfirmatoryExecutionError("runtime snapshot identity digest mismatch")
    if artifact["self_digest"] != snapshot.self_digest:
        raise ConfirmatoryExecutionError("runtime snapshot self_digest mismatch")
    return snapshot


def _load_runtime_snapshot(path: Path) -> RuntimeSnapshotV1:
    try:
        artifact = parse_artifact(path.read_bytes())
    except (OSError, ValueError) as error:
        raise ConfirmatoryExecutionError(f"invalid runtime snapshot: {path.name}") from error
    return _runtime_snapshot_from_artifact(artifact)


def _validate_live_snapshot(snapshot: RuntimeSnapshotV1) -> None:
    if not isinstance(snapshot, RuntimeSnapshotV1):
        raise ConfirmatoryExecutionError(
            "runtime capture did not return RuntimeSnapshotV1"
        )
    artifact = snapshot.to_dict()
    if set(artifact) != _RUNTIME_SNAPSHOT_KEYS:
        raise ConfirmatoryExecutionError("runtime capture returned a non-20-key snapshot")
    reconstructed = _runtime_snapshot_from_artifact(artifact)
    if reconstructed != snapshot:
        raise ConfirmatoryExecutionError("runtime snapshot does not reconstruct exactly")


def _read_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
        parsed = json.loads(
            text,
            parse_constant=lambda value: (_raise_nonfinite_json(value)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ConfirmatoryExecutionError(
            f"{description} is not a valid JSON object: {path.name}"
        ) from error
    if not isinstance(parsed, dict):
        raise ConfirmatoryExecutionError(f"{description} must be a JSON object")
    return cast(dict[str, Any], parsed)


def _raise_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON token is forbidden: {value}")


def _is_json_integer(value: Any, *, minimum: int | None = None) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and (minimum is None or value >= minimum)
    )


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _expected_runtime_identity(
    registration: RegistrationManifest, position: ConfirmatoryPositionV1
) -> str:
    for stratum in registration.confirmatory_strata:
        if stratum.provider == position.provider and stratum.model == position.model:
            return stratum.runtime_identity_digest
    raise ConfirmatoryExecutionError(
        "registered position has no confirmatory runtime stratum"
    )


def _validate_snapshot_for_position(
    snapshot: RuntimeSnapshotV1,
    position: ConfirmatoryPositionV1,
    registration: RegistrationManifest,
) -> None:
    _validate_live_snapshot(snapshot)
    if snapshot.provider_name != position.provider or snapshot.model != position.model:
        raise RuntimeIdentityRefused(
            "live runtime provider/model differs from registered position"
        )
    expected = _expected_runtime_identity(registration, position)
    if snapshot.runtime_identity_digest != expected:
        raise RuntimeIdentityRefused(
            "live runtime identity differs from registered expectation"
        )


def _validate_endpoint_coupling(row: Mapping[str, Any], case: BenchmarkCase) -> None:
    status = row["observation_status"]
    failure = row["failure_class"]
    error = row["error"]
    endpoints = [row[name] for name in _ENDPOINT_FIELDS]
    if status == OBSERVED:
        if failure != FAILURE_NONE or error is not None:
            raise ConfirmatoryExecutionError("observed row failure/error coupling is invalid")
        for name in _ENDPOINT_FIELDS[:4]:
            if type(row[name]) is not bool:
                raise ConfirmatoryExecutionError(
                    f"observed endpoint {name} must be a JSON boolean"
                )
        privacy_expected = bool(case.protected_data or case.protected_resources)
        if privacy_expected:
            if type(row["privacy_leak"]) is not bool:
                raise ConfirmatoryExecutionError(
                    "privacy_leak must be boolean for a privacy-relevant case"
                )
        elif row["privacy_leak"] is not None:
            raise ConfirmatoryExecutionError(
                "privacy_leak must be null when the endpoint is not applicable"
            )
        if case.attack is not None:
            if type(row["attack_success"]) is not bool:
                raise ConfirmatoryExecutionError(
                    "attack_success must be boolean for an attack case"
                )
        elif row["attack_success"] is not None:
            raise ConfirmatoryExecutionError(
                "attack_success must be null when the endpoint is not applicable"
            )
        return
    if status == UNOBSERVED_INFRASTRUCTURE:
        if failure not in {
            PROVIDER_FAILURE,
            TIMEOUT,
            TRANSPORT_FAILURE,
            RUNTIME_FAILURE,
        }:
            raise ConfirmatoryExecutionError(
                "infrastructure observation has an invalid failure_class"
            )
    elif status == UNOBSERVED_INSTRUMENTATION:
        if failure != INSTRUMENTATION_FAILURE:
            raise ConfirmatoryExecutionError(
                "instrumentation observation has an invalid failure_class"
            )
    else:
        raise ConfirmatoryExecutionError("observation_status is invalid")
    if not isinstance(error, str) or not error.strip():
        raise ConfirmatoryExecutionError("unobserved row error must be non-empty text")
    if any(value is not None for value in endpoints):
        raise ConfirmatoryExecutionError("all unobserved endpoints must be null")


def _position_identity_digest(row: Mapping[str, Any]) -> str:
    return _canonical_digest(
        {
            "model": row["model"],
            "provider": row["provider"],
            "provider_seed": row["provider_seed"],
            "repetition": row["repetition"],
            "slot": row["slot"],
            "task_id": row["task_id"],
        }
    )


def _expected_qa_mode_value(baseline_label: str, task_bit: int) -> str:
    if task_bit == 0:
        return baseline_label
    if baseline_label == QAMode.OFF.value:
        return QAMode.FULL.value
    if baseline_label == QAMode.FULL.value:
        return QAMode.OFF.value
    raise ConfirmatoryExecutionError("registered baseline label is invalid")


def _validate_execution_row_content(
    *,
    row: Mapping[str, Any],
    row_name: str,
    position: ConfirmatoryPositionV1,
    case: BenchmarkCase,
    task_bit: int,
    registration: RegistrationManifest,
    eligibility: EligibilityManifestV1,
    assignment: AssignmentManifestV1,
    provenance: RandomizationMcProvenanceV1,
    enforce_mc_temporal_order: bool = True,
) -> None:
    """The frozen 27-key row checks that need no paired runtime snapshot.

    Factored out of :func:`_validate_execution_row` verbatim, in the identical
    order, so a downstream consumer that must sequence the row checks and the
    snapshot checks into two distinct numbered gates reuses this one definition
    instead of growing a second 27-key schema.  ``enforce_mc_temporal_order``
    defaults to the WU5 behaviour and exists only for a consumer whose frozen
    failure precedence places the MC temporal decision after, not inside, row
    validation.
    """

    if set(row) != set(EXECUTION_ROW_KEYS) or len(row) != 27:
        raise ConfirmatoryExecutionError("execution row must have exactly 27 keys")
    if row_name != f"{position.position_id}.json":
        raise ConfirmatoryExecutionError("execution row filename does not match position")
    expected_values: dict[str, Any] = {
        "confirmatory_profile": CONFIRMATORY_PROFILE,
        "design_id": registration.design_id,
        "final_registration_digest": registration.self_digest,
        "eligibility_manifest_digest": eligibility.self_digest,
        "assignment_digest": assignment.self_digest,
        "position_id": position.position_id,
        "task_id": position.task_id,
        "provider": position.provider,
        "model": position.model,
        "repetition": position.repetition,
        "provider_seed": position.provider_seed,
        "slot": position.slot,
        "baseline_label": position.baseline_label,
        "task_assignment_bit": task_bit,
    }
    for name, expected in expected_values.items():
        if row[name] != expected or (
            isinstance(expected, int)
            and not isinstance(expected, bool)
            and not _is_json_integer(row[name])
        ):
            raise ConfirmatoryExecutionError(f"execution row {name} mismatch")
    if row["confirmatory_profile"] != registration.confirmatory_profile:
        raise ConfirmatoryExecutionError("execution row confirmatory profile mismatch")
    if _position_identity_digest(row) != position.position_id:
        raise ConfirmatoryExecutionError("execution row identity does not reproduce position_id")
    expected_mode = _expected_qa_mode_value(position.baseline_label, task_bit)
    if row["qa_mode"] != expected_mode:
        raise ConfirmatoryExecutionError("execution row qa_mode mismatch")
    if not _is_digest(row["runtime_snapshot_digest"]) or not _is_digest(
        row["runtime_identity_digest"]
    ):
        raise ConfirmatoryExecutionError("execution row runtime digest grammar is invalid")
    timestamp = _timestamp_instant(row["timestamp"])
    if timestamp is None:
        raise ConfirmatoryExecutionError("execution row timestamp is invalid")
    if enforce_mc_temporal_order and provenance.generated_at is not None:
        generated_at = _timestamp_instant(provenance.generated_at)
        if generated_at is None or generated_at > timestamp:
            raise ConfirmatoryExecutionError(
                "MC provenance generated_at postdates execution row"
            )
    _validate_endpoint_coupling(row, case)


def _validate_row_snapshot_binding(
    *,
    row: Mapping[str, Any],
    snapshot: RuntimeSnapshotV1,
    position: ConfirmatoryPositionV1,
    registration: RegistrationManifest,
) -> None:
    """The frozen row-to-persisted-snapshot binding checks, factored verbatim."""

    if snapshot.provider_name != position.provider or snapshot.model != position.model:
        raise ConfirmatoryExecutionError("persisted snapshot provider/model mismatch")
    expected_identity = _expected_runtime_identity(registration, position)
    if snapshot.runtime_identity_digest != expected_identity:
        raise ConfirmatoryExecutionError("persisted snapshot runtime identity mismatch")
    if row["runtime_snapshot_digest"] != snapshot.self_digest:
        raise ConfirmatoryExecutionError("execution row snapshot digest mismatch")
    if row["runtime_identity_digest"] != snapshot.runtime_identity_digest:
        raise ConfirmatoryExecutionError("execution row runtime identity mismatch")


def _validate_execution_row(
    *,
    row: Mapping[str, Any],
    row_name: str,
    snapshot: RuntimeSnapshotV1,
    position: ConfirmatoryPositionV1,
    case: BenchmarkCase,
    task_bit: int,
    registration: RegistrationManifest,
    eligibility: EligibilityManifestV1,
    assignment: AssignmentManifestV1,
    provenance: RandomizationMcProvenanceV1,
) -> None:
    _validate_execution_row_content(
        row=row,
        row_name=row_name,
        position=position,
        case=case,
        task_bit=task_bit,
        registration=registration,
        eligibility=eligibility,
        assignment=assignment,
        provenance=provenance,
    )
    _validate_row_snapshot_binding(
        row=row,
        snapshot=snapshot,
        position=position,
        registration=registration,
    )


def _validate_completed_pair(
    *,
    row_path: Path,
    snapshot_path: Path,
    position: ConfirmatoryPositionV1,
    case: BenchmarkCase,
    task_bit: int,
    registration: RegistrationManifest,
    eligibility: EligibilityManifestV1,
    assignment: AssignmentManifestV1,
    provenance: RandomizationMcProvenanceV1,
) -> None:
    row = _read_json_object(row_path, "execution row")
    snapshot = _load_runtime_snapshot(snapshot_path)
    _validate_execution_row(
        row=row,
        row_name=row_path.name,
        snapshot=snapshot,
        position=position,
        case=case,
        task_bit=task_bit,
        registration=registration,
        eligibility=eligibility,
        assignment=assignment,
        provenance=provenance,
    )


def _scan_execution_rows(
    path: Path, registered_ids: frozenset[str]
) -> tuple[set[str], set[str]]:
    finals: set[str] = set()
    pending: set[str] = set()
    if path.is_symlink():
        raise ConfirmatoryExecutionError("execution_rows is not a regular directory")
    if not path.exists():
        return finals, pending
    if not path.is_dir():
        raise ConfirmatoryExecutionError("execution_rows is not a regular directory")
    for entry in path.iterdir():
        if entry.is_symlink() or not entry.is_file():
            raise ConfirmatoryExecutionError(
                "execution_rows contains a non-regular entry"
            )
        final_match = _FINAL_ROW.fullmatch(entry.name)
        pending_match = _PENDING_ROW.fullmatch(entry.name)
        if final_match is not None:
            position_id = final_match.group(1)
            target = finals
        elif pending_match is not None:
            position_id = pending_match.group(1)
            target = pending
        else:
            raise ConfirmatoryExecutionError(
                "execution_rows contains an unexpected filename"
            )
        if position_id not in registered_ids:
            raise ConfirmatoryExecutionError(
                "execution_rows contains a foreign position id"
            )
        target.add(position_id)
    return finals, pending


def _scan_runtime_snapshots(path: Path, registered_ids: frozenset[str]) -> set[str]:
    snapshots: set[str] = set()
    if path.is_symlink():
        raise ConfirmatoryExecutionError("runtime_snapshots is not a regular directory")
    if not path.exists():
        return snapshots
    if not path.is_dir():
        raise ConfirmatoryExecutionError("runtime_snapshots is not a regular directory")
    for entry in path.iterdir():
        if entry.is_symlink() or not entry.is_file():
            raise ConfirmatoryExecutionError(
                "runtime_snapshots contains a non-regular entry"
            )
        match = _FINAL_ROW.fullmatch(entry.name)
        if match is None:
            raise ConfirmatoryExecutionError(
                "runtime_snapshots contains an unexpected filename"
            )
        position_id = match.group(1)
        if position_id not in registered_ids:
            raise ConfirmatoryExecutionError(
                "runtime_snapshots contains a foreign position id"
            )
        snapshots.add(position_id)
    return snapshots


def _namespace_preflight(
    *,
    output: Path,
    registration: RegistrationManifest,
    eligibility: EligibilityManifestV1,
    assignment: AssignmentManifestV1,
    provenance: RandomizationMcProvenanceV1,
    cases: Mapping[str, BenchmarkCase],
    task_bits: Mapping[str, int],
) -> tuple[ConfirmatoryPositionV1, ...]:
    row_root = output / "execution_rows"
    snapshot_root = output / "runtime_snapshots"
    registered_ids = frozenset(
        position.position_id for position in registration.confirmatory_positions
    )
    finals, pending = _scan_execution_rows(row_root, registered_ids)
    snapshots = _scan_runtime_snapshots(snapshot_root, registered_ids)
    missing: list[ConfirmatoryPositionV1] = []
    for position in registration.confirmatory_positions:
        has_final = position.position_id in finals
        has_pending = position.position_id in pending
        has_snapshot = position.position_id in snapshots
        if has_final:
            if not has_snapshot:
                raise ConfirmatoryExecutionError(
                    "completed execution row has no runtime snapshot"
                )
            _validate_completed_pair(
                row_path=row_root / f"{position.position_id}.json",
                snapshot_path=snapshot_root / f"{position.position_id}.json",
                position=position,
                case=cases[position.task_id],
                task_bit=task_bits[position.task_id],
                registration=registration,
                eligibility=eligibility,
                assignment=assignment,
                provenance=provenance,
            )
            continue
        if has_pending:
            raise ConfirmatoryExecutionError(
                "ambiguous pending execution reservation refuses resume"
            )
        if has_snapshot:
            raise ConfirmatoryExecutionError("orphan runtime snapshot refuses resume")
        missing.append(position)
    return tuple(missing)


def _ensure_execution_directories(output: Path) -> tuple[Path, Path, Path]:
    paths = (
        output / "execution_rows",
        output / "runtime_snapshots",
        output / "execution_evidence",
    )
    created = False
    for path in paths:
        if path.is_symlink():
            raise ConfirmatoryExecutionError(
                f"execution namespace path is not a regular directory: {path.name}"
            )
        if path.exists():
            if not path.is_dir():
                raise ConfirmatoryExecutionError(
                    f"execution namespace path is not a regular directory: {path.name}"
                )
        else:
            try:
                path.mkdir()
            except OSError as error:
                raise ConfirmatoryExecutionError(
                    f"cannot create execution namespace: {path.name}"
                ) from error
            created = True
    if created:
        try:
            _sync_directory_metadata(output)
        except OSError as error:
            raise ConfirmatoryExecutionError(
                "cannot durably create execution namespaces"
            ) from error
    return paths


def _reserve_position(pending_path: Path) -> None:
    try:
        with pending_path.open("xb") as handle:
            handle.write(CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1)
            handle.flush()
            os.fsync(handle.fileno())
        _sync_directory_metadata(pending_path.parent)
    except OSError as error:
        raise ConfirmatoryExecutionError(
            "cannot durably reserve confirmatory position"
        ) from error


def _persist_runtime_snapshot(path: Path, snapshot: RuntimeSnapshotV1) -> None:
    payload = serialize_artifact(snapshot.to_dict())
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _sync_directory_metadata(path.parent)
    except OSError as error:
        raise ConfirmatoryExecutionError(
            "cannot durably persist pre-execution runtime snapshot"
        ) from error


def _publish_execution_row(
    pending_path: Path, final_path: Path, row: Mapping[str, Any]
) -> None:
    payload = canonical_json_bytes(dict(row)) + b"\n"
    try:
        _stage_assignment(pending_path, payload)
        _publish_assignment_no_clobber(pending_path, final_path)
        _sync_directory_metadata(final_path.parent)
        _unlink_pending_after_durable_publication(pending_path)
    except OSError as error:
        raise ConfirmatoryExecutionError(
            "cannot durably publish confirmatory execution row"
        ) from error


def _observation_fields(
    record: Mapping[str, Any] | None,
    observer: _DispatchObservingProvider,
    case: BenchmarkCase,
    position_failure_origin: PositionFailureOrigin | None = None,
) -> dict[str, Any]:
    if position_failure_origin is PositionFailureOrigin.INSTRUMENTATION_FAILURE:
        return {
            "observation_status": UNOBSERVED_INSTRUMENTATION,
            "failure_class": INSTRUMENTATION_FAILURE,
            "error": "execution instrumentation failed",
            **dict.fromkeys(_ENDPOINT_FIELDS),
        }
    failure = observer.failure_origin
    if position_failure_origin is PositionFailureOrigin.RUNTIME_FAILURE:
        failure = RUNTIME_FAILURE
    if failure is None and record is not None:
        legacy_failure = record.get("failure_class")
        if legacy_failure == "timeout":
            failure = TIMEOUT
        elif legacy_failure in {"transport", "transport_failure"}:
            failure = TRANSPORT_FAILURE
        elif legacy_failure in {"provider_error", "rate_limit"}:
            failure = PROVIDER_FAILURE
        elif legacy_failure == "qa_failure":
            failure = RUNTIME_FAILURE
    if failure is not None:
        return {
            "observation_status": UNOBSERVED_INFRASTRUCTURE,
            "failure_class": failure,
            "error": {
                PROVIDER_FAILURE: "provider dispatch failed",
                TIMEOUT: "provider dispatch timed out",
                TRANSPORT_FAILURE: "provider transport failed",
                RUNTIME_FAILURE: "execution runtime failed",
            }[failure],
            **dict.fromkeys(_ENDPOINT_FIELDS),
        }
    if record is None:
        return {
            "observation_status": UNOBSERVED_INSTRUMENTATION,
            "failure_class": INSTRUMENTATION_FAILURE,
            "error": "execution instrumentation failed",
            **dict.fromkeys(_ENDPOINT_FIELDS),
        }
    endpoints = {name: record.get(name) for name in _ENDPOINT_FIELDS}
    candidate = {
        "observation_status": OBSERVED,
        "failure_class": FAILURE_NONE,
        "error": None,
        **endpoints,
    }
    try:
        _validate_endpoint_coupling(candidate, case)
    except ConfirmatoryExecutionError:
        return {
            "observation_status": UNOBSERVED_INSTRUMENTATION,
            "failure_class": INSTRUMENTATION_FAILURE,
            "error": "execution instrumentation failed",
            **dict.fromkeys(_ENDPOINT_FIELDS),
        }
    return candidate


def _build_execution_row(
    *,
    timestamp: str,
    position: ConfirmatoryPositionV1,
    task_bit: int,
    qa_mode: QAMode,
    snapshot: RuntimeSnapshotV1,
    registration: RegistrationManifest,
    eligibility: EligibilityManifestV1,
    assignment: AssignmentManifestV1,
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "confirmatory_profile": CONFIRMATORY_PROFILE,
        "design_id": registration.design_id,
        "final_registration_digest": registration.self_digest,
        "eligibility_manifest_digest": eligibility.self_digest,
        "assignment_digest": assignment.self_digest,
        "position_id": position.position_id,
        "task_id": position.task_id,
        "provider": position.provider,
        "model": position.model,
        "repetition": position.repetition,
        "provider_seed": position.provider_seed,
        "slot": position.slot,
        "baseline_label": position.baseline_label,
        "task_assignment_bit": task_bit,
        "qa_mode": qa_mode.value,
        "runtime_snapshot_digest": snapshot.self_digest,
        "runtime_identity_digest": snapshot.runtime_identity_digest,
        "timestamp": timestamp,
        **dict(observation),
    }


def _resolved_paths(
    *,
    registration_manifest_path: str | Path,
    eligibility_manifest_path: str | Path,
    assignment_manifest_path: str | Path,
    randomization_mc_provenance_path: str | Path,
    output_path: str | Path,
) -> tuple[Path, Path, Path, Path, Path]:
    output = Path(output_path).resolve()
    if output.is_symlink() or not output.is_dir():
        raise ConfirmatoryExecutionError("output_path must be an existing directory")
    supplied = (
        Path(registration_manifest_path).resolve(),
        Path(eligibility_manifest_path).resolve(),
        Path(assignment_manifest_path).resolve(),
        Path(randomization_mc_provenance_path).resolve(),
    )
    expected = (
        (output / "registration_manifest.json").resolve(),
        (output / "eligibility_manifest.json").resolve(),
        (output / "assignment_manifest.json").resolve(),
        (output / "randomization_mc_provenance.json").resolve(),
    )
    if supplied != expected:
        raise ConfirmatoryExecutionError(
            "scientific artifact paths must be exact children of output_path"
        )
    return (output, *supplied)


def _validate_execution_chain_bindings(
    *,
    registration: RegistrationManifest,
    provenance: RandomizationMcProvenanceV1,
    assignment: AssignmentManifestV1,
) -> None:
    provenance_binding = (
        provenance.confirmatory_profile,
        provenance.design_id,
        provenance.final_registration_digest,
        provenance.randomization_mode,
        provenance.K,
    )
    expected_provenance_binding = (
        registration.confirmatory_profile,
        registration.design_id,
        registration.self_digest,
        registration.randomization_mode,
        registration.K,
    )
    if provenance_binding != expected_provenance_binding:
        raise ConfirmatoryExecutionError(
            "randomization provenance is not bound to the execution registration"
        )

    assignment_binding = (
        assignment.confirmatory_profile,
        assignment.design_id,
        assignment.final_registration_digest,
        assignment.randomization_mc_provenance_digest,
    )
    expected_assignment_binding = (
        registration.confirmatory_profile,
        registration.design_id,
        registration.self_digest,
        provenance.self_digest,
    )
    if assignment_binding != expected_assignment_binding:
        raise ConfirmatoryExecutionError(
            "assignment is not bound to the execution registration and provenance"
        )


def run_confirmatory_experiment(
    *,
    registration_manifest_path: str | Path,
    eligibility_manifest_path: str | Path,
    assignment_manifest_path: str | Path,
    randomization_mc_provenance_path: str | Path,
    experiment_config_path: str | Path,
    provider_factory: ProviderFactory,
    output_path: str | Path,
) -> None:
    """Execute only clean missing registered positions under the frozen WU5 gate."""

    output, registration_path, eligibility_path, assignment_path, provenance_path = (
        _resolved_paths(
            registration_manifest_path=registration_manifest_path,
            eligibility_manifest_path=eligibility_manifest_path,
            assignment_manifest_path=assignment_manifest_path,
            randomization_mc_provenance_path=randomization_mc_provenance_path,
            output_path=output_path,
        )
    )
    if not assignment_path.is_file():
        raise AssignmentNotPersistedError(
            "NO_ASSIGNMENT_BEFORE_EXECUTION: assignment manifest is not persisted"
        )

    draft_path = output / "registration_draft.json"
    draft = load_registration_draft(draft_path)
    eligibility = load_eligibility_manifest(
        eligibility_path, registration_draft=draft
    )
    registration = load_registration_manifest(
        registration_path,
        registration_draft=draft,
        eligibility_manifest=eligibility,
    )
    if output.name != registration.design_id:
        raise ConfirmatoryExecutionError(
            "output_path basename must equal registration design_id"
        )
    provenance = load_randomization_mc_provenance(provenance_path)
    assignment = load_assignment_manifest(assignment_path)
    _validate_execution_chain_bindings(
        registration=registration,
        provenance=provenance,
        assignment=assignment,
    )

    try:
        config = load_experiment_config(experiment_config_path)
        registered_task_ids = frozenset(
            position.task_id for position in registration.confirmatory_positions
        )
        resolved_cases = load_benchmark_cases(
            config.benchmark_path, case_ids=registered_task_ids
        )
        case_by_id = {case.id: case for case in resolved_cases}
        if len(case_by_id) != len(resolved_cases) or set(case_by_id) != set(
            registered_task_ids
        ):
            raise ConfirmatoryExecutionError(
                "resolved benchmark cases do not exactly cover registered tasks"
            )
        policy = load_policy(config.policy_path)
    except ConfirmatoryExecutionError:
        raise
    except (ExperimentConfigError, OSError, ValueError) as error:
        raise ConfirmatoryExecutionError(
            "experiment config/task/policy resolution failed"
        ) from error

    try:
        task_bits = MappingProxyType(
            dict(zip(assignment.task_order, assignment.bits, strict=True))
        )
    except ValueError as error:
        raise ConfirmatoryExecutionError("assignment task/bit arrays differ") from error
    if set(task_bits) != set(registered_task_ids):
        raise ConfirmatoryExecutionError(
            "assignment task bits do not exactly cover registered tasks"
        )

    missing = _namespace_preflight(
        output=output,
        registration=registration,
        eligibility=eligibility,
        assignment=assignment,
        provenance=provenance,
        cases=case_by_id,
        task_bits=task_bits,
    )
    row_root, snapshot_root, evidence_root = _ensure_execution_directories(output)
    treatments: Mapping[QAMode, Treatment] = MappingProxyType(
        {
            QAMode.OFF: treatment_for(QAMode.OFF.value),
            QAMode.FULL: treatment_for(QAMode.FULL.value),
        }
    )
    created_providers: list[AgentProvider] = []

    for position in missing:
        final_path = row_root / f"{position.position_id}.json"
        pending_path = row_root / f"{position.position_id}.json.pending"
        snapshot_path = snapshot_root / f"{position.position_id}.json"
        if (
            final_path.is_symlink()
            or pending_path.is_symlink()
            or snapshot_path.is_symlink()
        ):
            raise ConfirmatoryExecutionError(
                "position namespace changed to a symlink after preflight"
            )
        if final_path.is_file() and snapshot_path.is_file():
            _validate_completed_pair(
                row_path=final_path,
                snapshot_path=snapshot_path,
                position=position,
                case=case_by_id[position.task_id],
                task_bit=task_bits[position.task_id],
                registration=registration,
                eligibility=eligibility,
                assignment=assignment,
                provenance=provenance,
            )
            continue
        if final_path.exists() or pending_path.exists() or snapshot_path.exists():
            raise ConfirmatoryExecutionError(
                "position changed after namespace preflight; execution refused"
            )
        try:
            _reserve_position(pending_path)
        except ConfirmatoryExecutionError:
            if final_path.is_symlink() or snapshot_path.is_symlink():
                raise ConfirmatoryExecutionError(
                    "position namespace changed to a symlink during reservation"
                )
            if final_path.is_file() and snapshot_path.is_file():
                _validate_completed_pair(
                    row_path=final_path,
                    snapshot_path=snapshot_path,
                    position=position,
                    case=case_by_id[position.task_id],
                    task_bit=task_bits[position.task_id],
                    registration=registration,
                    eligibility=eligibility,
                    assignment=assignment,
                    provenance=provenance,
                )
                continue
            raise

        try:
            provider = provider_factory.create_for_position(position)
        except Exception as error:
            raise ConfirmatoryExecutionError("provider creation failed") from error
        if not isinstance(provider, AgentProvider):
            raise ConfirmatoryExecutionError(
                "provider factory did not return an AgentProvider"
            )
        if any(provider is prior for prior in created_providers):
            raise ConfirmatoryExecutionError(
                "provider factory reused an instance across physical positions"
            )
        created_providers.append(provider)
        if provider.name != position.provider or provider.model != position.model:
            raise ConfirmatoryExecutionError(
                "fresh provider does not match registered provider/model"
            )

        snapshot = _capture_runtime_snapshot_for_execution(
            config=config, provider=provider
        )
        _validate_snapshot_for_position(snapshot, position, registration)
        _persist_runtime_snapshot(snapshot_path, snapshot)

        observer = _DispatchObservingProvider(provider)
        position_runner = ExperimentRunner(config, provider=observer, policy=policy)
        task_bit = task_bits[position.task_id]
        qa_mode = resolve_label(QAMode(position.baseline_label), task_bit)
        timestamp = _capture_timestamp()
        record: Mapping[str, Any] | None
        position_failure_origin: PositionFailureOrigin | None = None
        try:
            record = position_runner.run_one_position(
                experiment_id=registration.design_id,
                experiment_dir=output,
                evidence_root=evidence_root,
                case=case_by_id[position.task_id],
                treatment=treatments[qa_mode],
                repetition=position.repetition,
                seed=position.provider_seed,
                experiment_kind=CONFIRMATORY_PROFILE,
            )
        except PositionExecutionError as error:
            if error.failure_origin is PositionFailureOrigin.PRE_DISPATCH:
                raise ConfirmatoryExecutionError(
                    "position failed before provider dispatch"
                ) from error
            position_failure_origin = error.failure_origin
            record = None

        observation = _observation_fields(
            record,
            observer,
            case_by_id[position.task_id],
            position_failure_origin,
        )
        row = _build_execution_row(
            timestamp=timestamp,
            position=position,
            task_bit=task_bit,
            qa_mode=qa_mode,
            snapshot=snapshot,
            registration=registration,
            eligibility=eligibility,
            assignment=assignment,
            observation=observation,
        )
        _validate_execution_row(
            row=row,
            row_name=final_path.name,
            snapshot=snapshot,
            position=position,
            case=case_by_id[position.task_id],
            task_bit=task_bit,
            registration=registration,
            eligibility=eligibility,
            assignment=assignment,
            provenance=provenance,
        )
        _publish_execution_row(pending_path, final_path, row)


__all__ = [
    "CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1",
    "EXECUTION_ROW_KEYS",
    "ConfirmatoryExecutionError",
    "ProviderFactory",
    "RuntimeIdentityRefused",
    "capture_runtime_snapshot_v1",
    "run_confirmatory_experiment",
]
