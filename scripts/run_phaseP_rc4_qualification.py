#!/usr/bin/env python3
"""Phase-P driver: the frozen 102-cell pilot-v7-rc4 QA-OFF qualification.

**THIS SCRIPT REFUSES TO RUN BY DEFAULT AND AUTHORIZES NOTHING.**

Real-model execution requires BOTH of:

* the command-line flag ``--execute-real-model``; and
* the environment variable ``IQA_SOA_PHASE_P_HUMAN_GATE=AUTHORIZED``, at exactly
  that case.

Neither condition alone is sufficient.  If either is absent the driver exits
non-zero having issued no provider request, no Ollama metadata query, no
inference, no output cell and no results directory.  Neither gate is set
anywhere in this repository, in any test, in any configuration file or in any CI
definition; opening them is a deliberate human act performed once, by a person,
after the Phase-P protocol has been independently reviewed.

Phase P is a BENCHMARK QUALIFICATION, not an experiment.  Its only question is
whether pilot-v7-rc4's intended safe paths, challenge routes, multi-step causal
prerequisites, resource modality, benign controls, deliberate negative control
and fault opportunity are actually REACHABLE under the two qualified local
real-model providers with QA OFF.  It estimates no QA effectiveness, runs no FULL
arm, computes no treatment effect and ranks no model.

WHAT THIS DRIVER DOES, IN ORDER, AND NEVER OUT OF ORDER
=======================================================

0. ``--verify-frozen-inputs``, if given, runs the complete OFFLINE protocol
   validation and exits.  It contacts nothing, creates nothing and needs no gate.
1. **Human gate.**  Both conditions, or nothing whatsoever happens.  This is
   evaluated before the offline preflight, before any configuration is loaded,
   before any provider object exists, before any metadata probe and before any
   directory is created.
2. **Offline preflight** (``scripts/phaseP_protocol.py``).  The frozen plan
   matches its sidecar; every frozen scientific execution input matches its
   recorded SHA-256; the instrument is version ``4`` with raw schema ``5``,
   ``tool-arguments-1`` and ``native-tools-adapter-3``; the ``src/iqa_soa`` tree
   equals the approved Phase-O revision digest and every individually recorded
   Phase-O file matches its own hash; the approved revision CHAIN verifies link
   by link; the historical bound-input audit and the Phase-O supersession both
   pass; the rc4 benchmark bytes are exactly what its freeze record pins; the
   seed triple is exactly what the Phase-P derivation recorded and reuses no
   historical seed; and the model/runtime pins are unanimous in committed
   evidence.  Any mismatch is an IMMEDIATE_STOP before a provider is contacted.
3. **Configuration assertion.**  Each arm's declared model, tool-contract policy,
   protocol, adapter version, argument-contract version and credential
   environment are read from the provider slot and required to equal the frozen
   pins.  This is a local read; it contacts nothing.
4. **Output-namespace precondition.**  A pre-existing raw record is a
   ``PROTOCOL_DEVIATION``: Phase-P evidence is append-only and a run is never
   resumed, repaired or replaced.  Checked before the runtime is probed.
5. **Metadata-only preflight.**  BOTH arms' live model presence, model digest and
   runtime version are probed, and BOTH are required to equal the frozen pins,
   before EITHER arm executes a cell.  A difference is an ``ENVIRONMENT_HOLD``
   with zero cells executed.  This driver never pulls, downloads, updates,
   retags, repairs, substitutes or replaces a model.
6. **The frozen schedule.**  ``phaseP_protocol.StopController`` OWNS advancement:
   the only way to obtain the next cell is its iterator, which terminates the
   moment a stop is armed, so an immediate-stop condition cannot be ignored and
   arm 2 cannot start after arm 1 stopped.  One cell is one invocation of the
   canonical ``ExperimentRunner`` on exactly one (task, seed) pair, so there is
   no parallel loop to bypass.

WHAT THIS DRIVER DOES NOT DO
============================

* It does not retry.  ``infrastructure_retry_limit`` is fixed at ``0`` and the
  runner independently refuses any other value.  A provider or model failure is a
  recorded outcome, never a reason to rerun.
* It does not replace, repair, resume or deduplicate a cell.  Raw evidence is
  append-only, a cell invalidation never deletes its raw trace, and an invalid
  row is never removed.
* It does not manufacture fault provenance or failure events.  The schema-4
  ``observed_fault_*`` columns and the schema-5 ordered ``failure_events`` list
  arise inside ``ExperimentRunner`` from the live ``GatewayOutcome`` sequence.
  This driver TRANSPORTS the row it is given; it reads no benchmark declaration
  and writes no observation.
* It stamps exactly TWO identity fields, ``model_digest`` and ``run_key``, from
  the frozen cell, because the canonical runner emits neither and both are frozen
  inputs rather than runtime observations.  Every other bound identity field --
  ``task_id``, ``seed``, ``model``, ``qa_mode``, ``benchmark_manifest_sha256`` --
  comes from the runner, so the binding check is a real check and not a tautology.
  Three further fields are TRANSPORTED from the cell's own persisted
  ``manifest.json`` -- ``raw_schema_version``, ``tool_argument_contract_version``
  and ``tool_argument_contract_digest`` -- because they are observations the
  runner records there rather than on the row.  Copying a constant instead would
  make the Phase-N disclosure precondition a tautology.
* It computes no verdict.  Scoring is the analyzer's job and is driven by
  ``benchmark/pilot-v7-rc4/qualification-contract.json`` and
  ``scripts/rc4_scoring_vocabulary.py``.

NO PART OF PHASE P ITSELF RUNS THIS DRIVER AGAINST A REAL PROVIDER.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
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

import phaseP_protocol as protocol  # noqa: E402
import qualification_harness_v2 as harness  # noqa: E402
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentConfigError,
    ExperimentRunner,
    load_experiment_config,
    load_provider,
)


@dataclass(frozen=True, slots=True)
class RuntimeMetadata:
    """What a metadata-only probe observed about one model.

    ``model_present`` is carried separately from ``model_digest`` so that "the
    runtime does not have this model" and "the runtime has it under a different
    digest" are two distinguishable environment holds rather than one.
    """

    runtime_version: str
    model_present: bool
    model_digest: str


#: ``(model) -> RuntimeMetadata``.  Injected in tests so the suite can prove the
#: gate and the preflight without contacting anything.
MetadataProbe = Callable[[str], RuntimeMetadata]

#: ``(cell) -> raw row``.  Injected in tests for the same reason.  The default is
#: the real runner-backed executor and is the only path that spends inference.
CellExecutor = Callable[[Any], Mapping[str, Any]]


# --------------------------------------------------------------------------
# 1. The machine-enforced human execution gate
# --------------------------------------------------------------------------


def human_gate_refusal(*, execute_flag: bool, env: Mapping[str, str]) -> str | None:
    """Return the refusal reason, or ``None`` when BOTH gates are open.

    Both conditions are evaluated independently and both are reported, so a
    partial gate can never be mistaken for a near miss that "almost" authorized a
    run.  The environment comparison is EXACT and case-sensitive: ``authorized``,
    ``AUTHORIZED `` and ``Authorized`` are all refusals.
    """

    reasons: list[str] = []
    if not execute_flag:
        reasons.append(f"the {protocol.HUMAN_GATE_FLAG} command-line flag was not given")
    actual = env.get(protocol.HUMAN_GATE_ENV)
    if actual != protocol.HUMAN_GATE_VALUE:
        reasons.append(
            f"{protocol.HUMAN_GATE_ENV} is {actual!r}, it must be exactly "
            f"{protocol.HUMAN_GATE_VALUE!r}"
        )
    if not reasons:
        return None
    return (
        "EXECUTION REFUSED: Phase-P real-model execution requires BOTH the "
        f"{protocol.HUMAN_GATE_FLAG} flag AND "
        f"{protocol.HUMAN_GATE_ENV}={protocol.HUMAN_GATE_VALUE}. "
        + "; ".join(reasons)
        + ". No provider was contacted, no metadata was probed, no inference was "
        "performed, no cell was produced and no results directory was created."
    )


# --------------------------------------------------------------------------
# 3. Configuration assertion -- local reads only
# --------------------------------------------------------------------------


def check_arm_configuration(models_path: Path) -> list[str]:
    """Assert each arm's declared identity from configuration, never assume it.

    ``load_provider`` constructs the provider object and reads its descriptor.
    Constructing an ``OpenAICompatibleProvider`` opens no socket and issues no
    request: the endpoint is a string it stores.  Nothing here contacts a
    runtime.
    """

    failures: list[str] = []
    for arm in protocol.ARM_ORDER:
        slot = protocol.ARM_PROVIDER_SLOT[arm]
        try:
            descriptor = load_provider(models_path, provider_name=slot).descriptor()
        except ExperimentConfigError as exc:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} slot {slot!r} is not loadable: "
                f"{exc}"
            )
            continue
        for key, expected, label in (
            ("model", protocol.EXPECTED_MODEL[arm], "model"),
            (
                "tool_contract_policy",
                protocol.EXPECTED_TOOL_CONTRACT_POLICY[arm],
                "tool_contract_policy",
            ),
            ("protocol", protocol.EXPECTED_PROTOCOL, "protocol"),
            (
                "native_tool_adapter_version",
                protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
                "native_tool_adapter_version",
            ),
            (
                "tool_argument_contract_version",
                protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
                "tool_argument_contract_version",
            ),
            (
                "tool_argument_contract_digest",
                protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
                "tool_argument_contract_digest",
            ),
            ("api_key_env", protocol.CREDENTIAL_ENV, "api_key_env"),
        ):
            actual = descriptor.get(key)
            if actual != expected:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: arm {arm!r} slot {slot!r} declares "
                    f"{label}={actual!r}, the frozen Phase-P pin is {expected!r}"
                )
    return failures


def check_experiment_configuration(config: Any) -> list[str]:
    """The experiment configuration must be exactly the frozen Phase-P matrix."""

    failures: list[str] = []
    if tuple(config.treatments) != (protocol.QA_MODE,):
        failures.append(
            f"PROTOCOL_DEVIATION: Phase P admits exactly one treatment "
            f"{protocol.QA_MODE!r}; the config declares {list(config.treatments)}. "
            f"{list(protocol.OUT_OF_SCOPE_TREATMENTS)} are out of scope."
        )
    if tuple(config.seeds) != protocol.SEEDS:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: Phase-P seeds must be exactly "
            f"{list(protocol.SEEDS)}; the config declares {list(config.seeds)}"
        )
    if config.repetitions != protocol.SEED_COUNT:
        failures.append(
            f"PROTOCOL_DEVIATION: the config declares repetitions="
            f"{config.repetitions}; Phase P executes exactly {protocol.SEED_COUNT} "
            "seeds per (arm, task)"
        )
    resolved_models = Path(config.models_path).resolve()
    expected_models = (PROJECT_ROOT / "configs" / "phaseP-models.yaml").resolve()
    if resolved_models != expected_models:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: the config points at models {resolved_models}, "
            f"Phase P is frozen against {expected_models}. A configuration from a "
            "historical phase is never a Phase-P input."
        )
    return failures


# --------------------------------------------------------------------------
# 4. Output-namespace precondition
# --------------------------------------------------------------------------


def check_output_namespace(output_root: Path) -> list[str]:
    """A Phase-P run is never resumed, repaired, replaced or deduplicated."""

    raw_path = output_root / protocol.RAW_RECORD_NAME
    failures: list[str] = []
    if raw_path.exists():
        failures.append(
            f"PROTOCOL_DEVIATION: {raw_path} already exists; Phase-P raw evidence is "
            "append-only and a run is never resumed, repaired or replaced. No row is "
            "overwritten and no invalid row is deleted."
        )
    for name in (protocol.RUN_MANIFEST_NAME, protocol.PARTIAL_MANIFEST_NAME):
        if (output_root / name).exists():
            failures.append(
                f"PROTOCOL_DEVIATION: {output_root / name} already exists; a completed "
                "or partial Phase-P run is never re-entered"
            )
    cells = protocol.cells_root(output_root)
    if cells.exists() and any(cells.iterdir()):
        failures.append(
            f"PROTOCOL_DEVIATION: {cells} already holds cell evidence; Phase P never "
            "writes into an existing evidence tree"
        )
    return failures


# --------------------------------------------------------------------------
# 5. Metadata-only preflight
# --------------------------------------------------------------------------


def _ollama_get(path: str, timeout: float = 30.0) -> dict[str, object]:
    request = urllib.request.Request(f"{protocol.OLLAMA_BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected payload from {path}")
    return payload


def probe_ollama_metadata(model: str) -> RuntimeMetadata:
    """Return the live local runtime's metadata for one model.

    METADATA ONLY.  ``/api/version`` and ``/api/tags`` describe what is installed;
    neither generates a token, and neither ``/api/chat`` nor ``/api/generate`` nor
    any OpenAI-compatible completion endpoint is used.  This function is never
    called during Phase P: it is reachable only through the dual-gated path, and
    every Phase-P test injects a mock in its place.
    """

    version = str(_ollama_get("/api/version").get("version") or "")
    entries = _ollama_get("/api/tags").get("models")
    present = False
    digest = ""
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("name") == model:
                present = True
                digest = str(entry.get("digest") or "")
                break
    return RuntimeMetadata(
        runtime_version=version, model_present=present, model_digest=digest
    )


def metadata_preflight(
    probe: MetadataProbe,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """ENVIRONMENT_HOLD gate: the live runtime must be the frozen environment.

    EVERY arm is probed exactly once, and EVERY arm is probed before ANY
    inference, so a second-arm environment drift cannot be discovered only after
    the first arm has been spent.  A failure on one arm does not short-circuit the
    other: both are probed, both are reported, and the run stops with zero cells
    executed.

    Returns the failures and what was observed; the observation is recorded in the
    run manifest so a reviewer can see the environment the run actually met.

    Phase P NEVER pulls, downloads, updates, retags, repairs, substitutes or
    automatically changes a model.  There is no environment self-healing path.
    """

    failures: list[str] = []
    observed: dict[str, dict[str, Any]] = {}
    for arm in protocol.ARM_ORDER:
        model = protocol.EXPECTED_MODEL[arm]
        try:
            metadata = probe(model)
        except (
            urllib.error.URLError,
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            failures.append(
                f"ENVIRONMENT_HOLD: cannot probe the local runtime for arm {arm!r}: "
                f"{exc}"
            )
            continue
        observed[arm] = {
            "model": model,
            "runtime_version": metadata.runtime_version,
            "model_present": metadata.model_present,
            "model_digest": metadata.model_digest,
        }
        if not metadata.model_present:
            failures.append(
                f"ENVIRONMENT_HOLD: the local runtime does not have model {model!r} "
                f"for arm {arm!r}; Phase P does not pull, download or install a model"
            )
        expected_digest = protocol.EXPECTED_MODEL_DIGEST[model]
        if metadata.model_digest != expected_digest:
            failures.append(
                f"ENVIRONMENT_HOLD: model {model!r} digest is "
                f"{metadata.model_digest!r} but the frozen pin is {expected_digest!r}; "
                "Phase P does not pull, update, retag, repair or replace a model"
            )
        if metadata.runtime_version != protocol.EXPECTED_RUNTIME_VERSION:
            failures.append(
                f"ENVIRONMENT_HOLD: Ollama runtime version is "
                f"{metadata.runtime_version!r} but the frozen pin is "
                f"{protocol.EXPECTED_RUNTIME_VERSION!r}; the committed experiment "
                "architecture does not permit unreviewed runtime drift"
            )
    missing = [arm for arm in protocol.ARM_ORDER if arm not in observed]
    if missing:
        failures.append(
            f"ENVIRONMENT_HOLD: arms {missing} produced no metadata observation; both "
            "arms must be probed before either arm executes a cell"
        )
    return failures, observed


# --------------------------------------------------------------------------
# 6. One cell
# --------------------------------------------------------------------------


def _row_from_cell_directory(experiment_dir: Path) -> dict[str, Any]:
    lines = [
        line
        for line in (experiment_dir / "runs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(lines) != 1:
        raise ExperimentConfigError(
            f"one cell must produce exactly one raw row, {experiment_dir.name} "
            f"produced {len(lines)}"
        )
    parsed: dict[str, Any] = json.loads(lines[0])
    return parsed


def _manifest_observations(experiment_dir: Path) -> dict[str, Any]:
    """Read the run's OWN persisted manifest for what the row does not carry.

    ``ExperimentRunner`` records ``raw_schema_version`` and the full provider
    descriptor -- including the argument-contract version and digest the provider
    ADVERTISED -- in the cell's ``manifest.json`` rather than on the row.  These
    are observations of the run that happened, read back from its own artifact,
    so transporting them keeps the disclosure precondition a fact about the run
    instead of a constant the driver asserted about itself.

    A missing manifest, a missing field or a stub provider that advertises no
    contract yields ``None``, which the frozen contract-drift check then refuses.
    Nothing here substitutes a default.
    """

    path = experiment_dir / "manifest.json"
    observations: dict[str, Any] = {
        name: None for name in protocol.MANIFEST_TRANSPORTED_FIELDS
    }
    if not path.is_file():
        return observations
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return observations
    if not isinstance(manifest, Mapping):  # pragma: no cover - defensive
        return observations
    observations["raw_schema_version"] = manifest.get("raw_schema_version")
    descriptor = manifest.get("provider")
    if isinstance(descriptor, Mapping):
        for name in ("tool_argument_contract_version", "tool_argument_contract_digest"):
            observations[name] = descriptor.get(name)
    return observations


def make_cell_executor(
    *,
    config_path: Path,
    manifest_path: Path,
    output_root: Path,
    providers: Mapping[str, Any] | None = None,
) -> CellExecutor:
    """Build the real, runner-backed executor for one frozen cell.

    The canonical ``ExperimentRunner.run`` owns its own case x repetition loop and
    derives the seed as ``config.seeds[repetition]``, so a per-cell driver must
    give it a per-cell configuration.  That is what this does: a config whose seed
    tuple is exactly this cell's seed, whose repetition count is one, whose
    treatment set is exactly ``off``, and whose output root is this cell's own
    directory under ``<output_root>/raw/cells/<slug>/`` -- so no cell can
    overwrite, blend into or resume another.

    Nothing about the run is otherwise altered.  The provider, the policy, the
    ablations, the step budget and the frozen benchmark are the frozen ones.

    ``providers`` is an OFFLINE-TEST SEAM.  It exists so a deterministic
    end-to-end regression can drive the real runner, the real frozen cases and the
    real directory layout without inference.  It cannot be used to launder a stub
    into a real-model record: the experiment kind is chosen from the provider type
    below, and ``ExperimentRunner`` independently refuses to label a
    ``DeterministicStubProvider`` run as a real-model experiment.
    """

    from iqa_soa.agent.providers import DeterministicStubProvider  # noqa: PLC0415
    from iqa_soa.benchmark import load_frozen_pilot  # noqa: PLC0415

    frozen_pilot = load_frozen_pilot(manifest_path)
    base_config = load_experiment_config(config_path)
    resolved_providers: Mapping[str, Any] = providers or {
        arm: load_provider(
            base_config.models_path, provider_name=protocol.ARM_PROVIDER_SLOT[arm]
        )
        for arm in protocol.ARM_ORDER
    }
    deterministic = any(
        isinstance(item, DeterministicStubProvider)
        for item in resolved_providers.values()
    )
    experiment_kind = (
        "deterministic_mechanism_validation"
        if deterministic
        else protocol.EXPERIMENT_KIND
    )
    root = protocol.cells_root(output_root)

    def execute(cell: Any) -> Mapping[str, Any]:
        cell_root = root / protocol.cell_slug(cell)
        config = replace(
            base_config,
            output_root=cell_root,
            treatments=(protocol.QA_MODE,),
            repetitions=1,
            seeds=(cell.seed,),
        )
        started = time.perf_counter()
        experiment_dir = ExperimentRunner(
            config, provider=resolved_providers[cell.arm]
        ).run(
            treatments=[protocol.QA_MODE],
            case_ids=[cell.task_id],
            repetitions=1,
            frozen_benchmark=frozen_pilot,
            max_total_runs=1,
            experiment_kind=experiment_kind,
            infrastructure_retry_limit=protocol.INFRASTRUCTURE_RETRY_LIMIT,
        )
        row = _row_from_cell_directory(experiment_dir)
        row["cell_elapsed_ms"] = (time.perf_counter() - started) * 1000.0
        row.update(_manifest_observations(experiment_dir))
        stored = protocol.cell_experiment_dir_value(experiment_dir, output_root)
        # Producer-side half of the containment contract.  The analyzer binds
        # every evidence pointer to its frozen cell; asserting the same thing here
        # means a producer regression fails at the cell that caused it rather than
        # silently at analysis time.
        resolved, reason = protocol.contained_child(
            output_root, stored, label="cell_experiment_dir", must_be_dir=True
        )
        evidence_root = protocol.cell_evidence_root(output_root, cell).resolve()
        if resolved is None or evidence_root not in resolved.parents:
            raise protocol.ProtocolError(
                f"cell {cell.key} produced an evidence pointer that is not beneath "
                f"its own evidence root {evidence_root}: {reason or stored}"
            )
        row["cell_experiment_dir"] = stored
        return row

    return execute


def stamp_frozen_identity(row: Mapping[str, Any], cell: Any) -> dict[str, Any]:
    """Add the two frozen-input identity fields and the schedule bookkeeping.

    ``model_digest`` and ``run_key`` are the only identity fields stamped here,
    and both come from the FROZEN CELL rather than from the run.  A row that
    already carries a conflicting value KEEPS ITS OWN VALUE, so a runner that
    someday emits these fields cannot be silently overwritten into agreement --
    the binding check must see the disagreement.  ``setdefault`` is what makes
    that property true, and a test asserts it directly.

    Nothing in :data:`protocol.MANIFEST_TRANSPORTED_FIELDS` is stamped here: those
    are observations the executor reads from the cell's own manifest, and a
    missing one stays missing so the contract-drift check refuses it.
    """

    stamped = dict(row)
    stamped.setdefault("model_digest", cell.model_digest)
    stamped.setdefault("run_key", cell.run_key)
    stamped["schedule_index"] = cell.index
    stamped["arm"] = cell.arm
    stamped["cell_key"] = cell.key
    stamped.setdefault("cell_experiment_dir", "")
    return stamped


def lost_cell_row(cell: Any, detail: str) -> dict[str, Any]:
    """The record for a cell whose execution raised before producing a row.

    There is no row to transport, so the identity comes from the frozen cell by
    necessity.  ``provider_attempt_count`` is ``0``, which the rc4 classifier
    treats as ``INSTRUMENT_DEFECT`` -> ``IMMEDIATE_STOP``: no attempt was
    preserved at all, so the evidence for this cell is lost and continuing would
    measure with a broken instrument.  The exception text is preserved verbatim
    rather than summarized, and the row is still appended to the raw record.
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
    schedule: Sequence[Any],
    scripted_faults: Mapping[str, Sequence[Any]],
    execute_cell: CellExecutor,
    raw_path: Path,
    partial_manifest_path: Path,
) -> Any:
    """Drive the frozen schedule under machine-enforced stop semantics.

    ``StopController.cells()`` is the ONLY source of the next cell, and it
    terminates the instant a stop is armed.  There is no independent loop, no
    index arithmetic and no early ``continue`` that could step past it, so a
    stop at the final cell of arm 1 leaves arm 2 with zero cells executed.
    """

    controller = protocol.StopController(schedule, scripted_faults=scripted_faults)
    for cell in controller.cells():
        try:
            row = execute_cell(cell)
        except Exception as exc:  # noqa: BLE001 - preserved, never swallowed
            row = lost_cell_row(cell, f"{type(exc).__name__}: {exc}")
        stamped = stamp_frozen_identity(row, cell)
        # Persist BEFORE classifying, so a classifier crash can never erase the
        # observed row and an invalidated cell keeps its raw evidence.
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
    result: Any,
    summary: Mapping[str, Any],
    frozen_inputs: Mapping[str, Any],
    runtime_metadata: Mapping[str, Any],
) -> None:
    payload = {
        "record_kind": "phase_p_run_manifest",
        "phase": protocol.PHASE,
        "benchmark_version": protocol.BENCHMARK_VERSION,
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
        # THE STOPCONTROLLER CLASSIFICATION LEDGER, persisted verbatim.  It is
        # NOT regenerated here: this is the exact ledger the controller produced
        # while recording the actual rows, so the analyzer's independent
        # reclassification has something real to disagree with.  Phase L-A'
        # omitted it, which made that reconciliation vacuous on every real run.
        "classifications": [dict(item) for item in result.classifications],
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
            "Run the complete OFFLINE protocol validation and exit. Contacts no "
            "provider, probes no runtime, creates no directory and executes no "
            "cell. Safe to run at any time and needs no gate."
        ),
    )
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "phaseP-qualification.yaml")
    )
    parser.add_argument(
        "--manifest",
        default=str(
            PROJECT_ROOT / "benchmark" / protocol.BENCHMARK_VERSION / "manifest.json"
        ),
    )
    parser.add_argument(
        "--output-root", default=str(PROJECT_ROOT / protocol.RESULTS_NAMESPACE)
    )
    return parser


def verify_frozen_inputs() -> tuple[int, list[str]]:
    """The complete static/frozen protocol validation.  ZERO provider contact."""

    failures = list(protocol.offline_preflight())
    try:
        config = load_experiment_config(
            PROJECT_ROOT / "configs" / "phaseP-qualification.yaml"
        )
    except ExperimentConfigError as exc:
        failures.append(f"FROZEN_ARTIFACT_MISMATCH: the Phase-P config is invalid: {exc}")
    else:
        failures.extend(check_experiment_configuration(config))
        failures.extend(check_arm_configuration(config.models_path))
    try:
        benchmark = protocol.load_benchmark()
        protocol.build_phase_p_schedule(benchmark)
    except (protocol.ProtocolError, ExperimentConfigError) as exc:
        failures.append(f"FROZEN_ARTIFACT_MISMATCH: {exc}")
    return (protocol.EXIT_OK if not failures else protocol.EXIT_PREFLIGHT_STOP), failures


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    probe: MetadataProbe | None = None,
    execute_cell: CellExecutor | None = None,
) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    environment = os.environ if env is None else env

    # ---- 0. Offline-only verification. Contacts nothing, needs no gate. ----
    if args.verify_frozen_inputs:
        code, failures = verify_frozen_inputs()
        for failure in failures:
            print(failure, file=sys.stderr)
        print(
            f"Phase-P offline verification: {'PASS' if not failures else 'FAIL'} "
            f"({len(failures)} failure(s)); no provider contacted, no runtime probed, "
            "no directory created"
        )
        return code

    # ---- 1. HUMAN GATE. Nothing whatsoever happens before this passes. ----
    #
    # This is deliberately the FIRST thing after argument parsing: no config is
    # loaded, no provider object is constructed, no metadata is probed and no
    # directory is created until both conditions hold.
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
        schedule = protocol.build_phase_p_schedule(benchmark)
        summary = protocol.protocol_summary()
    except (protocol.ProtocolError, ExperimentConfigError) as exc:
        print(f"IMMEDIATE_STOP: FROZEN_ARTIFACT_MISMATCH: {exc}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 3. Configuration assertion. Local reads only. ----
    try:
        base_config = load_experiment_config(config_path)
    except ExperimentConfigError as exc:
        print(
            f"IMMEDIATE_STOP: FROZEN_ARTIFACT_MISMATCH: {exc}", file=sys.stderr
        )
        return protocol.EXIT_PREFLIGHT_STOP
    config_failures = [
        *check_experiment_configuration(base_config),
        *check_arm_configuration(base_config.models_path),
    ]
    if config_failures:
        for failure in config_failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 4. Output namespace. Refused before the runtime is even probed. ----
    namespace_failures = check_output_namespace(output_root)
    if namespace_failures:
        for failure in namespace_failures:
            print(f"IMMEDIATE_STOP: {failure}", file=sys.stderr)
        return protocol.EXIT_PREFLIGHT_STOP

    # ---- 5. Metadata-only preflight. First and only pre-inference contact. ----
    environment_failures, runtime_metadata = metadata_preflight(
        probe or probe_ollama_metadata
    )
    if environment_failures:
        for failure in environment_failures:
            print(failure, file=sys.stderr)
        print(
            "ENVIRONMENT_HOLD: 0 cells executed. Phase P does not pull, download, "
            "update, retag, repair or substitute a model.",
            file=sys.stderr,
        )
        return protocol.EXIT_ENVIRONMENT_HOLD

    # Credential presence is checked by NAME only.  The value is never read into a
    # message, never printed and never written to an artifact.
    if not environment.get(protocol.CREDENTIAL_ENV):
        print(
            f"STOP: environment variable {protocol.CREDENTIAL_ENV!r} is unset; the "
            "local OpenAI-compatible adapter requires a credential value even when "
            "the local runtime ignores it",
            file=sys.stderr,
        )
        return protocol.EXIT_CREDENTIAL_STOP

    # ---- 6. The frozen schedule, owned by the stop controller. ----
    output_root.mkdir(parents=True, exist_ok=True)
    raw_path = output_root / protocol.RAW_RECORD_NAME
    raw_path.touch()

    print(
        f"Phase-P QA-OFF qualification: benchmark={protocol.BENCHMARK_VERSION} "
        f"manifest_sha256={benchmark.manifest_sha256} treatment={protocol.QA_MODE} "
        f"arms={list(protocol.ARM_ORDER)} tasks={protocol.TASK_COUNT} "
        f"seeds={list(protocol.SEEDS)} cells={len(schedule)} "
        f"instrument={protocol.EXPECTED_INSTRUMENT_VERSION} "
        f"raw_schema={protocol.EXPECTED_RAW_SCHEMA_VERSION} "
        f"arguments={protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION} "
        f"adapter={protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION} retries=0"
    )

    result = run_frozen_schedule(
        schedule=schedule,
        scripted_faults=benchmark.scripted_faults,
        execute_cell=execute_cell
        or make_cell_executor(
            config_path=config_path,
            manifest_path=manifest_path,
            output_root=output_root,
        ),
        raw_path=raw_path,
        partial_manifest_path=output_root / protocol.PARTIAL_MANIFEST_NAME,
    )
    _write_run_manifest(
        output_root / protocol.RUN_MANIFEST_NAME,
        result=result,
        summary=summary,
        frozen_inputs=protocol.load_frozen_inputs(),
        runtime_metadata=runtime_metadata,
    )

    if result.stopped:
        print(
            f"HOLD_POST_FREEZE_DEFECT: stopped at {result.stop_cell} "
            f"({result.stop_failure_class}); {result.executed}/{result.planned} cells "
            f"executed, {len(result.not_started)} never started. There is no "
            "resumption path and no replacement path.",
            file=sys.stderr,
        )
    print(
        f"terminal_status={result.terminal_status} executed={result.executed}/"
        f"{result.planned} invalidated={len(result.invalidated_cells)} "
        f"holds={len(result.hold_reasons)}"
    )
    exit_code: int = result.exit_code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CellExecutor",
    "MetadataProbe",
    "RuntimeMetadata",
    "build_parser",
    "check_arm_configuration",
    "check_experiment_configuration",
    "check_output_namespace",
    "human_gate_refusal",
    "lost_cell_row",
    "main",
    "make_cell_executor",
    "metadata_preflight",
    "probe_ollama_metadata",
    "run_frozen_schedule",
    "stamp_frozen_identity",
    "verify_frozen_inputs",
]
