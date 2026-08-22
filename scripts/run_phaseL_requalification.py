#!/usr/bin/env python3
"""Phase-L-B driver: the frozen 102-cell pilot-v7-rc3 QA-OFF requalification.

**THIS SCRIPT REFUSES TO RUN BY DEFAULT AND AUTHORIZES NOTHING.**

Real-model execution requires BOTH of:

* the command-line flag ``--execute-real-model``; and
* the environment variable ``IQA_SOA_PHASE_L_HUMAN_GATE=AUTHORIZED``.

If either is absent the driver exits non-zero having issued no provider request,
no Ollama metadata query, no inference and no output cell.  Neither gate is set
anywhere in the repository, in any test, in any configuration file or in any CI
definition; opening them is a deliberate human act performed once, by a person,
after the Phase-L-A' protocol has been reviewed.

Phase L is an ENGINEERING BENCHMARK REQUALIFICATION, not an experiment.  Its only
question is whether pilot-v7-rc3's intended safe paths, challenge routes,
multi-step causal prerequisites, resource modality, benign controls, deliberate
negative control and fault opportunity are actually REACHABLE under the two
qualified local real-model providers with QA OFF.  It estimates no QA
effectiveness, runs no FULL arm, computes no treatment effect and ranks no model.

What this driver does, in order, and never out of order:

1. **Human gate.**  Both gates, or nothing happens at all.
2. **Offline preflight** (``scripts/phaseL_protocol.py``).  The frozen plan
   matches its sidecar; every frozen scientific execution input matches its
   recorded SHA-256; instrument version is ``3`` and raw schema is ``4``; the
   ``src/iqa_soa`` tree equals the approved Phase-M revision digest and every
   individually recorded Phase-M file matches its own hash; the frozen
   historical bound-input audit passes; the rc3 scientific bytes are unmoved;
   and the inherited seed triple is exactly what Phase L-A recorded.  Any
   mismatch is ``FROZEN_ARTIFACT_MISMATCH`` -> IMMEDIATE_STOP, before a provider
   is contacted.
3. **Metadata-only preflight.**  Both arms' live model identity, model digest,
   runtime version, protocol and tool-contract policy are probed and required to
   equal the frozen pins.  A difference is an ``ENVIRONMENT_HOLD``.  This driver
   never pulls, updates, retags or replaces a model.
4. **The frozen schedule.**  ``qualification_harness.StopController`` OWNS
   advancement: the only way to obtain the next cell is its iterator, which
   terminates the moment a stop is armed, so an immediate-stop condition cannot
   be ignored and arm 2 cannot start after arm 1 stopped.  One cell is one
   invocation of the canonical ``ExperimentRunner`` on exactly one (task, seed)
   pair, so there is no parallel loop to bypass.

What this driver does NOT do:

* It does not retry.  ``infrastructure_retry_limit`` is fixed at ``0`` and the
  runner independently refuses any other value.  A provider or model failure is
  a recorded outcome, never a reason to rerun.
* It does not replace, repair, resume or deduplicate a cell.  Raw evidence is
  append-only and a cell invalidation never deletes its raw trace.
* It does not manufacture fault provenance.  The five schema-4
  ``observed_fault_*`` columns arise inside ``ExperimentRunner`` from the live
  ``GatewayOutcome`` sequence (``iqa_soa.experiment.fault_provenance``).  This
  driver transports the row it is given; it reads no benchmark declaration and
  writes no observation.
* It stamps exactly TWO identity fields, ``model_digest`` and ``run_key``, from
  the frozen cell before the cell executes, because the canonical runner emits
  neither and both are frozen inputs rather than runtime observations.  Every
  other bound identity field -- ``task_id``, ``seed``, ``model``, ``qa_mode``,
  ``benchmark_manifest_sha256`` -- comes from the runner, so the binding check
  is a real check rather than a tautology.
* It computes no verdict.  Scoring is the analyzer's job and is driven by
  ``benchmark/pilot-v7-rc3/qualification-contract.json``.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import phaseL_protocol as protocol  # noqa: E402
import qualification_harness as harness  # noqa: E402
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
    load_provider,
)

#: ``(model) -> (runtime_version, model_digest)``.  Injected in tests so the
#: suite can prove the gate and the preflight without contacting anything.
MetadataProbe = Callable[[str], "tuple[str, str]"]

#: ``(cell) -> raw row``.  Injected in tests for the same reason.  The default
#: is the real runner-backed executor and is the only path that spends inference.
CellExecutor = Callable[[harness.Cell], Mapping[str, Any]]


# --------------------------------------------------------------------------
# 1. The machine-enforced human execution gate
# --------------------------------------------------------------------------


def human_gate_refusal(
    *, execute_flag: bool, env: Mapping[str, str]
) -> str | None:
    """Return the refusal reason, or ``None`` when BOTH gates are open.

    Both conditions are evaluated independently and both are reported, so a
    partial gate can never be mistaken for a near miss that "almost" authorized
    a run.
    """

    reasons: list[str] = []
    if not execute_flag:
        reasons.append(
            f"the {protocol.HUMAN_GATE_FLAG} command-line flag was not given"
        )
    actual = env.get(protocol.HUMAN_GATE_ENV)
    if actual != protocol.HUMAN_GATE_VALUE:
        reasons.append(
            f"{protocol.HUMAN_GATE_ENV} is {actual!r}, it must be exactly "
            f"{protocol.HUMAN_GATE_VALUE!r}"
        )
    if not reasons:
        return None
    return (
        "EXECUTION REFUSED: Phase-L real-model execution requires BOTH the "
        f"{protocol.HUMAN_GATE_FLAG} flag AND "
        f"{protocol.HUMAN_GATE_ENV}={protocol.HUMAN_GATE_VALUE}. "
        + "; ".join(reasons)
        + ". No provider was contacted, no metadata was probed, no inference was "
        "performed and no cell was produced."
    )


# --------------------------------------------------------------------------
# 3. Metadata-only preflight
# --------------------------------------------------------------------------


def _ollama_get(path: str, timeout: float = 30.0) -> dict[str, object]:
    request = urllib.request.Request(
        f"{protocol.OLLAMA_BASE_URL}{path}", method="GET"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected payload from {path}")
    return payload


def probe_ollama_metadata(model: str) -> tuple[str, str]:
    """Return ``(runtime_version, model_digest)`` from the live local runtime.

    METADATA ONLY.  ``/api/version`` and ``/api/tags`` describe what is
    installed; neither generates a token, and neither ``/api/chat`` nor
    ``/api/generate`` nor any OpenAI-compatible completion endpoint is used.
    """

    version = str(_ollama_get("/api/version").get("version") or "")
    entries = _ollama_get("/api/tags").get("models")
    digest = ""
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("name") == model:
                digest = str(entry.get("digest") or "")
                break
    return version, digest


def check_arm_configuration(models_path: Path) -> list[str]:
    """Assert each arm's declared identity from configuration, never assume it."""

    failures: list[str] = []
    for arm in protocol.ARM_ORDER:
        slot = protocol.ARM_PROVIDER_SLOT[arm]
        descriptor = load_provider(models_path, provider_name=slot).descriptor()
        model = str(descriptor.get("model"))
        if model != protocol.EXPECTED_MODEL[arm]:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} expects model "
                f"{protocol.EXPECTED_MODEL[arm]!r} but slot {slot!r} declares {model!r}"
            )
        policy = descriptor.get("tool_contract_policy")
        if policy != protocol.EXPECTED_TOOL_CONTRACT_POLICY[arm]:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} expects tool_contract_policy="
                f"{protocol.EXPECTED_TOOL_CONTRACT_POLICY[arm]!r} but slot {slot!r} "
                f"declares {policy!r}"
            )
        if descriptor.get("protocol") != protocol.EXPECTED_PROTOCOL:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} must use the "
                f"{protocol.EXPECTED_PROTOCOL} protocol, slot {slot!r} declares "
                f"{descriptor.get('protocol')!r}"
            )
        if str(descriptor.get("api_key_env")) != protocol.CREDENTIAL_ENV:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} must read its credential "
                f"from {protocol.CREDENTIAL_ENV!r}, slot {slot!r} declares "
                f"{descriptor.get('api_key_env')!r}"
            )
    return failures


def metadata_preflight(
    probe: MetadataProbe,
) -> tuple[list[str], dict[str, dict[str, str]]]:
    """ENVIRONMENT_HOLD gate: the live runtime must be the frozen environment.

    Every arm is probed exactly once, and every arm is probed before ANY
    inference, so a second-arm environment drift cannot be discovered only after
    the first arm has been spent.  Returns the failures and what was observed;
    the observation is recorded in the run manifest so a reviewer can see the
    environment the run actually met.
    """

    failures: list[str] = []
    observed: dict[str, dict[str, str]] = {}
    for arm in protocol.ARM_ORDER:
        model = protocol.EXPECTED_MODEL[arm]
        try:
            runtime_version, model_digest = probe(model)
        except (urllib.error.URLError, OSError, ValueError,
                json.JSONDecodeError) as exc:
            failures.append(
                f"ENVIRONMENT_HOLD: cannot probe the local runtime for arm {arm!r}: "
                f"{exc}"
            )
            continue
        observed[arm] = {
            "model": model,
            "runtime_version": runtime_version,
            "model_digest": model_digest,
        }
        expected_digest = protocol.EXPECTED_MODEL_DIGEST[model]
        if model_digest != expected_digest:
            failures.append(
                f"ENVIRONMENT_HOLD: model {model!r} digest is {model_digest!r} but the "
                f"frozen pin is {expected_digest!r}; Phase L does not pull, update, "
                "retag or replace a model"
            )
        if runtime_version != protocol.EXPECTED_RUNTIME_VERSION:
            failures.append(
                f"ENVIRONMENT_HOLD: Ollama runtime version is {runtime_version!r} but "
                f"the frozen pin is {protocol.EXPECTED_RUNTIME_VERSION!r}; the "
                "committed experiment architecture does not permit unreviewed runtime "
                "drift"
            )
    return failures, observed


# --------------------------------------------------------------------------
# 4. One cell
# --------------------------------------------------------------------------


def _row_from_cell_directory(experiment_dir: Path) -> dict[str, Any]:
    lines = [
        line
        for line in (experiment_dir / "runs.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    if len(lines) != 1:
        raise ExperimentConfigError(
            f"one cell must produce exactly one raw row, {experiment_dir.name} "
            f"produced {len(lines)}"
        )
    parsed: dict[str, Any] = json.loads(lines[0])
    return parsed


def make_cell_executor(
    *, config_path: Path, manifest_path: Path, cells_root: Path
) -> CellExecutor:
    """Build the real, runner-backed executor for one frozen cell.

    The canonical ``ExperimentRunner.run`` owns its own case x repetition loop
    and derives the seed as ``config.seeds[repetition]``, so a per-cell driver
    must give it a per-cell configuration.  That is what this does: a config
    whose seed tuple is exactly this cell's seed, whose repetition count is one,
    whose treatment set is exactly ``off``, and whose output root is this cell's
    own directory -- so no cell can overwrite, blend into or resume another.

    Nothing about the run is otherwise altered.  The provider, the policy, the
    ablations, the step budget and the frozen benchmark are the frozen ones.
    """

    from iqa_soa.benchmark import load_frozen_pilot

    frozen = load_frozen_pilot(manifest_path)
    base_config = load_experiment_config(config_path)
    providers = {
        arm: load_provider(
            base_config.models_path, provider_name=protocol.ARM_PROVIDER_SLOT[arm]
        )
        for arm in protocol.ARM_ORDER
    }

    def execute(cell: harness.Cell) -> Mapping[str, Any]:
        cell_root = cells_root / protocol.cell_slug(cell)
        config = replace(
            base_config,
            output_root=cell_root,
            treatments=(protocol.QA_MODE,),
            repetitions=1,
            seeds=(cell.seed,),
        )
        started = time.perf_counter()
        experiment_dir = ExperimentRunner(
            config, provider=providers[cell.arm]
        ).run(
            treatments=[protocol.QA_MODE],
            case_ids=[cell.task_id],
            repetitions=1,
            frozen_benchmark=frozen,
            max_total_runs=1,
            experiment_kind=protocol.EXPERIMENT_KIND,
            infrastructure_retry_limit=protocol.INFRASTRUCTURE_RETRY_LIMIT,
        )
        row = _row_from_cell_directory(experiment_dir)
        row["cell_elapsed_ms"] = (time.perf_counter() - started) * 1000.0
        row["cell_experiment_dir"] = str(
            experiment_dir.relative_to(cells_root.parent).as_posix()
        )
        return row

    return execute


def stamp_frozen_identity(
    row: Mapping[str, Any], cell: harness.Cell
) -> dict[str, Any]:
    """Add the two frozen-input identity fields and the schedule bookkeeping.

    ``model_digest`` and ``run_key`` are the only identity fields stamped here,
    and both come from the FROZEN CELL rather than from the run.  A row that
    already carries a conflicting value keeps its own value, so a runner that
    someday emits these fields cannot be silently overwritten into agreement --
    the binding check must see the disagreement.
    """

    stamped = dict(row)
    stamped.setdefault("model_digest", cell.model_digest)
    stamped.setdefault("run_key", cell.run_key)
    stamped["schedule_index"] = cell.index
    stamped["arm"] = cell.arm
    stamped["cell_key"] = cell.key
    stamped.setdefault("cell_experiment_dir", "")
    return stamped


def lost_cell_row(cell: harness.Cell, detail: str) -> dict[str, Any]:
    """The record for a cell whose execution raised before producing a row.

    There is no row to transport, so the identity comes from the frozen cell by
    necessity.  ``provider_attempt_count`` is ``0``, which
    ``qualification_harness.classify_row`` classifies as ``INSTRUMENT_DEFECT`` ->
    ``IMMEDIATE_STOP``: no attempt was preserved at all, so the evidence for this
    cell is lost and continuing would measure with a broken instrument.  The
    exception text is preserved verbatim rather than summarized.
    """

    return {
        "task_id": cell.task_id,
        "seed": cell.seed,
        "model": cell.model,
        "model_digest": cell.model_digest,
        "qa_mode": cell.qa_mode,
        "benchmark_manifest_sha256": cell.benchmark_manifest_sha256,
        "run_key": cell.run_key,
        "schedule_index": cell.index,
        "arm": cell.arm,
        "cell_key": cell.key,
        "cell_experiment_dir": "",
        "provider_attempt_count": 0,
        "error": detail,
        "cell_execution_raised": True,
    }


# --------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------


def _append_row(path: Path, row: Mapping[str, Any]) -> None:
    """Append one raw row immediately.  Never rewrite, never deduplicate."""

    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_frozen_schedule(
    *,
    schedule: Sequence[harness.Cell],
    scripted_faults: Mapping[str, Sequence[harness.ScriptedFault]],
    execute_cell: CellExecutor,
    raw_path: Path,
    partial_manifest_path: Path,
) -> harness.ScheduleResult:
    """Drive the frozen schedule under machine-enforced stop semantics.

    ``StopController.cells()`` is the ONLY source of the next cell, and it
    terminates the instant a stop is armed.  There is no independent loop, no
    index arithmetic and no early ``continue`` that could step past it.
    """

    controller = harness.StopController(schedule, scripted_faults=scripted_faults)
    for cell in controller.cells():
        try:
            row = execute_cell(cell)
        except Exception as exc:  # noqa: BLE001 - preserved, never swallowed
            row = lost_cell_row(cell, f"{type(exc).__name__}: {exc}")
        stamped = stamp_frozen_identity(row, cell)
        # Persist BEFORE recording, so classification can never lose a row.
        _append_row(raw_path, stamped)
        failure_class = controller.record(cell, stamped)
        print(
            f"cell {cell.index:03d}/{len(schedule)} {cell.key} -> {failure_class}",
            flush=True,
        )
    controller.write_partial_manifest(partial_manifest_path)
    return controller.result()


def _write_run_manifest(
    path: Path,
    *,
    result: harness.ScheduleResult,
    summary: Mapping[str, Any],
    frozen_inputs: Mapping[str, Any],
    runtime_metadata: Mapping[str, Any],
) -> None:
    payload = {
        "record_kind": "phase_l_run_manifest",
        "phase": "L-B",
        "protocol": dict(summary),
        "frozen_inputs": dict(frozen_inputs),
        "runtime_metadata": dict(runtime_metadata),
        "terminal_status": result.terminal_status,
        "exit_code": result.exit_code,
        "planned_cells": result.planned,
        "executed_cells": result.executed,
        "invalidated_cells": list(result.invalidated_cells),
        "hold_reasons": list(result.hold_reasons),
        "stop_cell": result.stop_cell,
        "stop_failure_class": result.stop_failure_class,
        "stop_reason": result.stop_reason,
        "stop_detail": list(result.stop_detail),
        "cells_not_started": list(result.not_started),
        "note": (
            "Every provider attempt is preserved. No cell was retried, replaced, "
            "repaired, resumed or rerun, and no raw trace was deleted."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        protocol.HUMAN_GATE_FLAG,
        dest="execute_real_model",
        action="store_true",
        help=(
            "Half of the human execution gate. Real-model execution ALSO requires "
            f"{protocol.HUMAN_GATE_ENV}={protocol.HUMAN_GATE_VALUE}."
        ),
    )
    parser.add_argument(
        "--verify-frozen-inputs",
        action="store_true",
        help=(
            "Run the OFFLINE preflight only and exit. Contacts no provider, probes "
            "no runtime and executes no cell. Safe to run at any time."
        ),
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "phaseL-qualification.yaml"),
    )
    parser.add_argument(
        "--manifest",
        default=str(
            PROJECT_ROOT / "benchmark" / protocol.BENCHMARK_VERSION / "manifest.json"
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "results" / "phaseL-rc3-requalification"),
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    probe: MetadataProbe | None = None,
    execute_cell: CellExecutor | None = None,
) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    environment = os.environ if env is None else env

    if args.verify_frozen_inputs:
        failures = protocol.offline_preflight()
        for failure in failures:
            print(failure, file=sys.stderr)
        print(
            f"Phase-L offline preflight: {'PASS' if not failures else 'FAIL'} "
            f"({len(failures)} failure(s)); no provider contacted"
        )
        return protocol.EXIT_OK if not failures else protocol.EXIT_PREFLIGHT_STOP

    # ---- 1. HUMAN GATE. Nothing whatsoever happens before this passes. ----
    refusal = human_gate_refusal(
        execute_flag=bool(args.execute_real_model), env=environment
    )
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return protocol.EXIT_GATE_CLOSED

    # ---- 2. Offline preflight, still before any provider contact. ----
    failures = protocol.offline_preflight()
    if failures:
        for failure in failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    config_path = Path(args.config).resolve()
    manifest_path = Path(args.manifest).resolve()
    output_root = Path(args.output_root).resolve()

    try:
        benchmark = protocol.load_benchmark(manifest_path)
        schedule = protocol.build_phase_l_schedule(benchmark)
        summary = protocol.protocol_summary()
    except (protocol.ProtocolError, ExperimentConfigError) as exc:
        print(f"IMMEDIATE_STOP: FROZEN_ARTIFACT_MISMATCH: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    base_config = load_experiment_config(config_path)
    config_failures: list[str] = []
    if base_config.treatments != (protocol.QA_MODE,):
        config_failures.append(
            f"Phase L admits exactly one treatment {protocol.QA_MODE!r}; the config "
            f"declares {list(base_config.treatments)}"
        )
    if tuple(base_config.seeds) != protocol.SEEDS:
        config_failures.append(
            f"Phase-L seeds must be exactly {list(protocol.SEEDS)}; the config "
            f"declares {list(base_config.seeds)}"
        )
    config_failures.extend(check_arm_configuration(base_config.models_path))
    if config_failures:
        for failure in config_failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # A completed or partial Phase-L run is never resumed, repaired or replaced,
    # so this is refused before the runtime is even probed.
    raw_path = output_root / "phaseL-runs.jsonl"
    if raw_path.exists():
        print(
            f"IMMEDIATE_STOP: PROTOCOL_DEVIATION: {raw_path} already exists; Phase-L "
            "raw evidence is append-only and a run is never resumed, repaired or "
            "replaced",
            file=sys.stderr,
        )
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 3. Metadata-only preflight. First and only pre-inference contact. ----
    environment_failures, runtime_metadata = metadata_preflight(
        probe or probe_ollama_metadata
    )
    if environment_failures:
        for failure in environment_failures:
            print(failure, file=sys.stderr)
        return protocol.EXIT_ENVIRONMENT_HOLD

    # Credential presence is checked by NAME only.  The value is never read into
    # a message, never printed and never written to an artifact.
    if not environment.get(protocol.CREDENTIAL_ENV):
        print(
            f"STOP: environment variable {protocol.CREDENTIAL_ENV!r} is unset; the "
            "local OpenAI-compatible adapter requires a credential value even when "
            "the local runtime ignores it",
            file=sys.stderr,
        )
        return protocol.EXIT_CREDENTIAL_STOP

    # ---- 4. The frozen schedule, owned by the stop controller. ----
    output_root.mkdir(parents=True, exist_ok=True)
    raw_path.touch()

    print(
        f"Phase-L QA-OFF requalification: benchmark={protocol.BENCHMARK_VERSION} "
        f"manifest_sha256={benchmark.manifest_sha256} treatment={protocol.QA_MODE} "
        f"arms={list(protocol.ARM_ORDER)} tasks={protocol.TASK_COUNT} "
        f"seeds={list(protocol.SEEDS)} cells={len(schedule)} "
        f"instrument={protocol.EXPECTED_INSTRUMENT_VERSION} "
        f"raw_schema={protocol.EXPECTED_RAW_SCHEMA_VERSION} retries=0"
    )

    result = run_frozen_schedule(
        schedule=schedule,
        scripted_faults=benchmark.scripted_faults,
        execute_cell=execute_cell
        or make_cell_executor(
            config_path=config_path,
            manifest_path=manifest_path,
            cells_root=output_root / "raw" / "cells",
        ),
        raw_path=raw_path,
        partial_manifest_path=output_root / "phaseL-partial-manifest.json",
    )
    _write_run_manifest(
        output_root / "phaseL-run-manifest.json",
        result=result,
        summary=summary,
        frozen_inputs=protocol.load_frozen_inputs(),
        runtime_metadata=runtime_metadata,
    )

    if result.stopped:
        print(
            f"HOLD_POST_FREEZE_DEFECT: stopped at {result.stop_cell} "
            f"({result.stop_failure_class}); {result.executed}/{result.planned} cells "
            f"executed, {len(result.not_started)} never started",
            file=sys.stderr,
        )
    print(
        f"terminal_status={result.terminal_status} executed={result.executed}/"
        f"{result.planned} invalidated={len(result.invalidated_cells)} "
        f"holds={len(result.hold_reasons)}"
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
