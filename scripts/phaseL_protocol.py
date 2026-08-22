#!/usr/bin/env python3
"""The frozen Phase-L execution protocol, shared by the driver and the analyzer.

THIS MODULE RUNS NO MODEL.  Importing it contacts no provider, probes no Ollama
endpoint and performs no inference.  It is the single prospectively frozen
statement of *what* the future Phase-L-B execution is, so that the driver that
produces rows and the analyzer that reads them cannot drift apart into two
different experiments -- which is one of the failure modes the Phase-I post-hoc
protocol audit recorded.

Phase L-A (``eace204``) attempted this freeze and stopped at
``HOLD_PHASE_L_PROTOCOL``: the Phase-K.2 observed-fault provenance contract was
unsatisfiable from anything the canonical instrument persisted for a QA-OFF
cell, so every BUD-016 and FAULT-004 cell would have been invalidated before a
token was generated.  Phase M / M.1 (``1bc5add``) repaired that instrument
defect under an additive, individually hash-pinned revision record
(``docs/phaseM_instrument_revision.json``, instrument version ``3`` / raw schema
``4``).  Phase L-A' is the refreeze that repair authorizes.

Four things this module deliberately does NOT do:

1. **It does not derive seeds.**  The three Phase-L seeds were derived
   prospectively in Phase L-A from the canonical Phase-K commit, before any
   Phase-L model result existed, and no Phase-L inference has ever consumed
   them.  They are carried forward byte-for-byte.  Re-deriving them from the
   Phase-M commit would be post-hoc seed reselection after an instrument repair.
2. **It does not manufacture fault provenance.**  The four ``observed_fault_*``
   fields and the ambiguity counter arise inside ``ExperimentRunner`` from the
   live ``GatewayOutcome`` sequence (``iqa_soa.experiment.fault_provenance``).
   The Phase-L driver TRANSPORTS them.  Nothing here reconstructs them from a
   benchmark declaration, and no function in this module accepts a
   ``BenchmarkCase``, a ``ScriptedFault`` or the qualification contract as an
   input to an observation.
3. **It does not relax the Phase-K/K.2 taxonomy, dispositions or matcher.**
   Those are imported from ``scripts/qualification_harness.py`` unchanged.
4. **It does not authorize execution.**  The human gate lives in the driver and
   is closed by default; this module only names it.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision  # noqa: E402
import phaseM_frozen_input_audit as frozen_input_audit  # noqa: E402
import qualification_harness as harness  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    FAULT_PROVENANCE_INSTRUMENT_VERSION,
    FAULT_PROVENANCE_RAW_SCHEMA_VERSION,
    INSTRUMENT_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.metrics.definitions import (  # noqa: E402
    FAULT_PROVENANCE_TELEMETRY_FIELDS,
    PILOT_RAW_FIELDS_V4,
)

# --------------------------------------------------------------------------
# Canonical provenance of this refreeze
# --------------------------------------------------------------------------

#: The commit Phase L-A' started from: Phase M / M.1 merged into main.
CANONICAL_BASE_COMMIT = "1bc5addf2fe5d83950a5d0ab89aa8188bd1db8b4"

#: The commit Phase L-A derived the seeds from, and stopped at.
PHASE_L_A_SEED_BASE_COMMIT = "beafa5d170659997790e1c3e79086ea05548c094"
PHASE_L_A_HOLD_COMMIT = "eace204d4c27a9ca48d3c0a660832f640b7a900b"
PHASE_L_A_HOLD_STATUS = "HOLD_PHASE_L_PROTOCOL"

# --------------------------------------------------------------------------
# Seeds -- INHERITED, never re-derived
# --------------------------------------------------------------------------

#: The exact triple Phase L-A derived, in the exact order it derived them.
SEEDS: tuple[int, int, int] = (929260329, 1281385038, 978843421)

#: Recorded verbatim so the posture is machine-readable, not only prose.
SEED_SELECTION_STATUS = (
    "PROSPECTIVELY_SELECTED_IN_PHASE_L_A_AND_NEVER_EXECUTED"
)

#: Seeds every committed real-model result in this repository already consumed.
#: They are forbidden for this qualification so that a Phase-L cell can never be
#: confused with, or silently compared against, a historical cell.
FORBIDDEN_HISTORICAL_SEEDS: frozenset[int] = frozenset({1729, 2718, 3141, 5772, 8119})

#: The Phase-F / Phase-I triple specifically, named because the brief names it.
FORBIDDEN_PHASE_F_I_SEEDS: tuple[int, int, int] = (1729, 2718, 3141)

#: Where the derivation is recorded.  Phase L-A' reads it; it never rewrites it.
SEED_RECORD_RELATIVE = "docs/phaseL_rc3_prospective_seed_derivation.json"

# --------------------------------------------------------------------------
# Arms, model identity and runtime pins
# --------------------------------------------------------------------------

#: Arm order is frozen.  The schedule is arm-major, so this tuple fixes which
#: arm runs first and therefore which arm a cross-arm stop protects.
ARM_ORDER: tuple[str, str] = ("qwen", "mistral")

#: Provider slot in configs/phaseL-models.yaml, addressed by arm name so a
#: mislabelled invocation cannot silently produce the wrong arm.
ARM_PROVIDER_SLOT: Mapping[str, str] = {
    "qwen": "qwen_native_none",
    "mistral": "mistral_native_trailing_user",
}

EXPECTED_MODEL: Mapping[str, str] = {
    "qwen": "qwen3.5:27b",
    "mistral": "mistral-small3.2:24b",
}

EXPECTED_TOOL_CONTRACT_POLICY: Mapping[str, str] = {
    "qwen": "none",
    "mistral": "trailing_user",
}

EXPECTED_PROTOCOL = "native_tools"

#: Transcribed from results/phaseF-qualification/phaseF-provenance.json, the same
#: values scripts/run_phaseI_requalification.py already asserts.  A difference is
#: an ENVIRONMENT_HOLD, never something this phase repairs.
EXPECTED_MODEL_DIGEST: Mapping[str, str] = {
    "qwen3.5:27b": "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e",
    "mistral-small3.2:24b": "5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b",
}

EXPECTED_RUNTIME_VERSION = "0.32.13"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

#: Checked by NAME only.  The value is never read into a message, never printed
#: and never written to an artifact.
CREDENTIAL_ENV = "PHASEL_OLLAMA_API_KEY"

# --------------------------------------------------------------------------
# Matrix shape
# --------------------------------------------------------------------------

BENCHMARK_VERSION = "pilot-v7-rc3"
QA_MODE = "off"
TASK_COUNT = 17
ARM_COUNT = 2
SEED_COUNT = 3
PLANNED_CELLS = TASK_COUNT * ARM_COUNT * SEED_COUNT  # 102

#: The runner label these rows carry.  ``iqa_soa.metrics.pilot`` accepts only
#: ``real_model_pilot`` and refuses every other label at both the manifest and
#: the row level, so this label is the structural, machine-checked guarantee
#: that a Phase-L row can never enter pilot analysis.  Phase F and Phase I use
#: the same label for the same reason.
EXPERIMENT_KIND = "real_model_connectivity_smoke"

#: Fixed at zero, and the runner independently refuses any other value.
INFRASTRUCTURE_RETRY_LIMIT = 0

# --------------------------------------------------------------------------
# Instrument / schema pins -- the Phase-M revision this protocol is built on
# --------------------------------------------------------------------------

EXPECTED_INSTRUMENT_VERSION = "3"
EXPECTED_RAW_SCHEMA_VERSION = 4
PHASE_M_REVISION_RELATIVE = "docs/phaseM_instrument_revision.json"

# --------------------------------------------------------------------------
# The human execution gate
# --------------------------------------------------------------------------

HUMAN_GATE_ENV = "IQA_SOA_PHASE_L_HUMAN_GATE"
HUMAN_GATE_VALUE = "AUTHORIZED"
HUMAN_GATE_FLAG = "--execute-real-model"

#: Exit codes.  Distinct so a refusal can never be mistaken for a clean run.
EXIT_OK = 0
EXIT_VERDICT_HOLD = 1
EXIT_PREFLIGHT_STOP = 2
EXIT_SCHEDULE_STOPPED = 3
EXIT_CREDENTIAL_STOP = 4
EXIT_ENVIRONMENT_HOLD = 5
EXIT_GATE_CLOSED = 6

# --------------------------------------------------------------------------
# The prospective raw-row contract
# --------------------------------------------------------------------------

#: Identity the driver stamps from the FROZEN CELL, before the cell executes.
#: The canonical runner emits neither of these, and both are frozen inputs
#: rather than runtime observations, so stamping them is legitimate.  Everything
#: else the binding check compares must come from the runner.
DRIVER_STAMPED_IDENTITY_FIELDS: tuple[str, ...] = ("model_digest", "run_key")

#: Bookkeeping the driver adds so a row can be located in the frozen schedule.
#: None of these participates in classification.
DRIVER_STAMPED_SCHEDULE_FIELDS: tuple[str, ...] = (
    "schedule_index",
    "arm",
    "cell_key",
    "cell_experiment_dir",
)

#: Identity the RUNNER must emit and the harness must bind, unstamped by the
#: driver.  ``harness.REQUIRED_IDENTITY_FIELDS`` minus the two above.
RUNNER_EMITTED_IDENTITY_FIELDS: tuple[str, ...] = tuple(
    name
    for name in harness.REQUIRED_IDENTITY_FIELDS
    if name not in DRIVER_STAMPED_IDENTITY_FIELDS
)

#: Every field a completed Phase-L row must carry.  This is the single contract
#: the driver writes to and the analyzer reads from; a test asserts they agree.
PHASE_L_ROW_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *PILOT_RAW_FIELDS_V4,
            *harness.REQUIRED_IDENTITY_FIELDS,
            *DRIVER_STAMPED_SCHEDULE_FIELDS,
        )
    )
)

#: The schema-4 fault-provenance columns, transported and never manufactured.
FAULT_PROVENANCE_FIELDS: tuple[str, ...] = FAULT_PROVENANCE_TELEMETRY_FIELDS

#: The four the K.2 contract requires, plus the Phase-M ambiguity counter.
REQUIRED_FAULT_PROVENANCE_FIELDS: tuple[str, ...] = (
    harness.REQUIRED_FAULT_PROVENANCE_FIELDS
)
FAULT_IDENTITY_COUNT_FIELD = "observed_fault_identity_count"

#: The only two rc3 tasks that declare a scripted fault.  Recorded for reporting
#: and for the prospective classification statement below; NEVER used as an
#: observation and never written into a row.
FAULT_DECLARING_TASKS: tuple[str, str] = ("BUD-016", "FAULT-004")

#: What a CORRECT observation of each declared fault must classify as, frozen
#: before any inference.  This is an expectation about the harness, checked in
#: tests against synthetic rows; it is not a licence to stamp anything.
PROSPECTIVE_FAULT_CLASSIFICATION: Mapping[str, tuple[str, str]] = {
    "BUD-016": (harness.EXPECTED_SCRIPTED_FAULT, harness.CONTINUE),
    "FAULT-004": (harness.EXPECTED_SCRIPTED_FAULT, harness.CONTINUE),
}

# --------------------------------------------------------------------------
# Frozen scientific execution inputs
# --------------------------------------------------------------------------

FROZEN_INPUTS_RELATIVE = "docs/phaseL_frozen_execution_inputs.json"
PLAN_RELATIVE = "docs/phaseL_rc3_real_model_requalification_plan_v2.md"

#: Every scientific execution input, hashed as raw working-tree bytes per
#: docs/hash_basis_policy.md.  The future driver asserts all of them before any
#: provider request.  Order is stable so the generated record is deterministic.
FROZEN_INPUT_PATHS: tuple[str, ...] = (
    # The protocol itself.
    PLAN_RELATIVE,
    "configs/phaseL-qualification.yaml",
    "configs/phaseL-models.yaml",
    "scripts/phaseL_protocol.py",
    "scripts/run_phaseL_requalification.py",
    "scripts/analyze_phaseL_requalification.py",
    "scripts/qualification_harness.py",
    # The benchmark and its scoring contract.
    "benchmark/pilot-v7-rc3/manifest.json",
    "benchmark/pilot-v7-rc3/provenance.json",
    "benchmark/pilot-v7-rc3/qualification-contract.json",
    "benchmark/pilot-v7-rc3/AUDIT.md",
    "benchmark/pilot-v7-rc3/freeze-record.json",
    # The QA policy the treatment is defined against.
    "configs/policies/default.xml",
    # The approved instrument revision this protocol is built on.
    PHASE_M_REVISION_RELATIVE,
    # The seed provenance, carried forward unchanged.
    SEED_RECORD_RELATIVE,
)

#: Tree digests recorded alongside the per-file hashes.  ``src/iqa_soa`` is the
#: approved Phase-M instrument; the rc3 tree is the benchmark's scientific bytes.
FROZEN_TREE_ROOTS: tuple[str, ...] = ("src/iqa_soa", "benchmark/pilot-v7-rc3")


class ProtocolError(RuntimeError):
    """A frozen Phase-L protocol input is missing or self-inconsistent."""


def sha256_file(relative: str) -> str:
    """Hash RAW working-tree bytes.  Never normalize (docs/hash_basis_policy.md)."""

    return hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()


def tree_digest(relative_root: str) -> str:
    """The repository's canonical tree digest, from ``instrument_revision``.

    Reused rather than reimplemented so the values are directly comparable to
    the pins already committed in the rc2/rc3 freeze records and in the Phase-M
    revision record.
    """

    return instrument_revision.tree_digest(relative_root)


def compute_frozen_inputs() -> dict[str, Any]:
    """The frozen-hash record, computed from the current working tree."""

    return {
        "record_kind": "phase_l_frozen_execution_inputs",
        "phase": "L-A'",
        "canonical_base_commit": CANONICAL_BASE_COMMIT,
        "hash_basis": (
            "raw working-tree bytes, LF canonical checkout per "
            "docs/hash_basis_policy.md"
        ),
        "model_inference_performed": False,
        "execution_authorized": False,
        "instrument_version": EXPECTED_INSTRUMENT_VERSION,
        "raw_schema_version": EXPECTED_RAW_SCHEMA_VERSION,
        "seed_selection_status": SEED_SELECTION_STATUS,
        "seeds": list(SEEDS),
        "planned_cells": PLANNED_CELLS,
        "files": {relative: sha256_file(relative) for relative in FROZEN_INPUT_PATHS},
        "trees": {root: tree_digest(root) for root in FROZEN_TREE_ROOTS},
    }


def load_frozen_inputs() -> Mapping[str, Any]:
    path = PROJECT_ROOT / FROZEN_INPUTS_RELATIVE
    if not path.is_file():
        raise ProtocolError(f"the frozen-input record is missing: {FROZEN_INPUTS_RELATIVE}")
    parsed: Mapping[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return parsed


def check_frozen_inputs() -> list[str]:
    """Every recorded hash must equal the current working-tree bytes."""

    failures: list[str] = []
    try:
        record = load_frozen_inputs()
    except (ProtocolError, json.JSONDecodeError) as exc:
        return [f"FROZEN_ARTIFACT_MISMATCH: {exc}"]

    recorded_files = record.get("files")
    if not isinstance(recorded_files, Mapping):
        return ["FROZEN_ARTIFACT_MISMATCH: the frozen-input record carries no file table"]
    missing = [name for name in FROZEN_INPUT_PATHS if name not in recorded_files]
    extra = [name for name in recorded_files if name not in FROZEN_INPUT_PATHS]
    for name in missing:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: {name} is a frozen execution input but is "
            "absent from the frozen-input record"
        )
    for name in extra:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: the frozen-input record names {name}, which "
            "is not a declared Phase-L execution input"
        )
    for name, recorded in sorted(recorded_files.items()):
        target = PROJECT_ROOT / name
        if not target.is_file():
            failures.append(f"FROZEN_ARTIFACT_MISMATCH: {name} does not exist")
            continue
        actual = sha256_file(name)
        if actual != recorded:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {name} recorded={recorded} actual={actual}"
            )

    recorded_trees = record.get("trees")
    if not isinstance(recorded_trees, Mapping):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the frozen-input record carries no tree table"
        )
    else:
        for root in FROZEN_TREE_ROOTS:
            recorded = recorded_trees.get(root)
            actual = tree_digest(root)
            if recorded != actual:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: tree {root} recorded={recorded} "
                    f"actual={actual}"
                )

    if record.get("seeds") != list(SEEDS):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the frozen-input record does not carry the "
            f"inherited Phase-L seed triple {list(SEEDS)}"
        )
    if record.get("planned_cells") != PLANNED_CELLS:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the frozen-input record does not plan "
            f"{PLANNED_CELLS} cells"
        )
    return failures


def check_plan_sidecar() -> list[str]:
    """The frozen plan must match its recorded ``.sha256`` sidecar."""

    plan = PROJECT_ROOT / PLAN_RELATIVE
    sidecar = plan.with_suffix(".sha256")
    if not plan.is_file():
        return [f"FROZEN_ARTIFACT_MISMATCH: {PLAN_RELATIVE} does not exist"]
    if not sidecar.is_file():
        return [
            f"FROZEN_ARTIFACT_MISMATCH: {PLAN_RELATIVE} has no .sha256 sidecar"
        ]
    recorded = sidecar.read_text(encoding="utf-8").split()[0].strip()
    actual = sha256_file(PLAN_RELATIVE)
    if recorded != actual:
        return [
            f"FROZEN_ARTIFACT_MISMATCH: {PLAN_RELATIVE} recorded={recorded} "
            f"actual={actual}"
        ]
    return []


def check_instrument_pins() -> list[str]:
    """Instrument version, raw schema version and the approved Phase-M revision.

    Phase K's historical ``src/iqa_soa`` pin is NOT updated and NOT relaxed: the
    Phase-K freeze assertion is proved from committed bytes at the Phase-K freeze
    commit, and the CURRENT instrument is bound separately and more strictly, by
    the approved additive revision record.
    """

    failures: list[str] = []
    if INSTRUMENT_VERSION != EXPECTED_INSTRUMENT_VERSION:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: instrument version is {INSTRUMENT_VERSION!r}, "
            f"this protocol is frozen against {EXPECTED_INSTRUMENT_VERSION!r}"
        )
    if FAULT_PROVENANCE_INSTRUMENT_VERSION != EXPECTED_INSTRUMENT_VERSION:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-M instrument constant is "
            f"{FAULT_PROVENANCE_INSTRUMENT_VERSION!r}"
        )
    if RAW_SCHEMA_VERSION != EXPECTED_RAW_SCHEMA_VERSION:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: raw schema version is {RAW_SCHEMA_VERSION}, "
            f"this protocol is frozen against {EXPECTED_RAW_SCHEMA_VERSION}"
        )
    if FAULT_PROVENANCE_RAW_SCHEMA_VERSION != EXPECTED_RAW_SCHEMA_VERSION:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-M raw-schema constant is "
            f"{FAULT_PROVENANCE_RAW_SCHEMA_VERSION}"
        )

    revision_path = PROJECT_ROOT / PHASE_M_REVISION_RELATIVE
    if not revision_path.is_file():
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: {PHASE_M_REVISION_RELATIVE} does not exist"
        )
        return failures
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    current = revision.get("current_instrument")
    if not isinstance(current, Mapping):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-M revision record names no current "
            "instrument"
        )
        return failures
    if str(current.get("instrument_version")) != EXPECTED_INSTRUMENT_VERSION:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the approved revision records instrument "
            f"version {current.get('instrument_version')!r}"
        )
    if current.get("raw_schema_version") != EXPECTED_RAW_SCHEMA_VERSION:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the approved revision records raw schema "
            f"{current.get('raw_schema_version')!r}"
        )
    approved_tree = str(current.get("src_iqa_soa_tree") or "")
    actual_tree = tree_digest("src/iqa_soa")
    if approved_tree != actual_tree:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: src/iqa_soa digests to "
            f"{actual_tree}, the approved Phase-M revision is {approved_tree}"
        )

    # Every individually recorded Phase-M instrument file must still hash to its
    # own approved SHA-256.  A matching tree digest already implies this, but the
    # brief requires it stated per file so a report can name the offending file.
    changed = revision.get("changed_files")
    if isinstance(changed, Mapping):
        for relative, entry in sorted(changed.items()):
            if not isinstance(entry, Mapping):
                continue
            recorded = str(entry.get("sha256") or "")
            target = PROJECT_ROOT / relative
            if not target.is_file():
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: approved instrument file {relative} "
                    "does not exist"
                )
                continue
            actual = sha256_file(relative)
            if actual != recorded:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: approved instrument file {relative} "
                    f"recorded={recorded} actual={actual}"
                )

    # Both halves of the repository's own instrument-provenance check: the
    # permanent Phase-K historical assertion AND the approved current revision.
    failures.extend(
        f"FROZEN_ARTIFACT_MISMATCH: {failure}"
        for failure in instrument_revision.check_instrument_provenance()
    )
    return failures


def check_frozen_historical_inputs() -> list[str]:
    """Every ``path -> SHA-256`` binding any committed provenance record holds."""

    return [
        f"FROZEN_ARTIFACT_MISMATCH: {failure}"
        for failure in frozen_input_audit.audit()
    ]


def check_seed_provenance() -> list[str]:
    """The inherited triple must be exactly what Phase L-A recorded."""

    failures: list[str] = []
    record_path = PROJECT_ROOT / SEED_RECORD_RELATIVE
    if not record_path.is_file():
        return [
            f"FROZEN_ARTIFACT_MISMATCH: {SEED_RECORD_RELATIVE} does not exist; the "
            "Phase-L seeds are inherited, never re-derived"
        ]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("seeds") != list(SEEDS):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-L-A seed record carries "
            f"{record.get('seeds')!r}, this protocol inherits {list(SEEDS)}"
        )
    if str(record.get("canonical_base_commit")) != PHASE_L_A_SEED_BASE_COMMIT:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-L-A seed record was derived from "
            f"{record.get('canonical_base_commit')!r}, expected "
            f"{PHASE_L_A_SEED_BASE_COMMIT!r}"
        )
    if record.get("model_inference_performed") is not False:
        failures.append(
            "PROTOCOL_DEVIATION: the seed record does not attest that it was "
            "derived without inference"
        )
    overlap = sorted(set(SEEDS) & FORBIDDEN_HISTORICAL_SEEDS)
    if overlap:
        failures.append(
            f"PROTOCOL_DEVIATION: seeds {overlap} are historical qualification seeds"
        )
    if len(set(SEEDS)) != len(SEEDS):
        failures.append("PROTOCOL_DEVIATION: the Phase-L seed triple is not unique")
    return failures


def offline_preflight() -> list[str]:
    """Every assertion the driver makes BEFORE it is allowed to touch a provider.

    Contacts nothing.  Returns an empty list when the protocol is intact; every
    entry is prefixed with the taxonomy class it belongs to.
    """

    return [
        *check_plan_sidecar(),
        *check_frozen_inputs(),
        *check_instrument_pins(),
        *check_frozen_historical_inputs(),
        *check_seed_provenance(),
    ]


# --------------------------------------------------------------------------
# The frozen 102-cell schedule
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoadedBenchmark:
    """The frozen rc3 selection, and the fault declarations read from it.

    ``scripted_faults`` is the DECLARATION side of the K.2 proof only.  It is
    handed to the stop controller, which compares it against runtime-observed
    provenance the driver transported; it is never used to produce an
    observation.
    """

    manifest_sha256: str
    task_ids: tuple[str, ...]
    scripted_faults: Mapping[str, tuple[harness.ScriptedFault, ...]]


def load_benchmark(manifest_path: Path | None = None) -> LoadedBenchmark:
    """Load the frozen rc3 benchmark and refuse anything that is not it."""

    from iqa_soa.benchmark import load_frozen_pilot

    path = manifest_path or (
        PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "manifest.json"
    )
    frozen = load_frozen_pilot(path)
    if frozen.benchmark_version != BENCHMARK_VERSION:
        raise ProtocolError(
            f"expected {BENCHMARK_VERSION}, got {frozen.benchmark_version}"
        )
    if len(frozen.cases) != TASK_COUNT:
        raise ProtocolError(
            f"{BENCHMARK_VERSION} must contain exactly {TASK_COUNT} tasks, found "
            f"{len(frozen.cases)}"
        )
    return LoadedBenchmark(
        manifest_sha256=frozen.manifest_sha256,
        task_ids=tuple(frozen.selected_task_ids),
        scripted_faults=harness.scripted_faults_from_cases(list(frozen.cases)),
    )


def build_arms() -> tuple[harness.ArmSpec, ...]:
    """The two frozen arms, in frozen order, each carrying its model identity."""

    return tuple(
        harness.ArmSpec(
            arm=arm,
            model=EXPECTED_MODEL[arm],
            model_digest=EXPECTED_MODEL_DIGEST[EXPECTED_MODEL[arm]],
        )
        for arm in ARM_ORDER
    )


def build_phase_l_schedule(benchmark: LoadedBenchmark) -> list[harness.Cell]:
    """The frozen arm-major / task-major / seed-minor 102-cell schedule.

    Task order is the frozen manifest's own ``selected_task_ids`` order, seed
    order is the inherited Phase-L order, and arm order is ``ARM_ORDER``.  The
    schedule is therefore a pure function of frozen bytes.
    """

    schedule = harness.build_schedule(
        build_arms(),
        benchmark.task_ids,
        SEEDS,
        qa_mode=QA_MODE,
        benchmark_manifest_sha256=benchmark.manifest_sha256,
    )
    if len(schedule) != PLANNED_CELLS:
        raise ProtocolError(
            f"the frozen schedule must be exactly {PLANNED_CELLS} cells, built "
            f"{len(schedule)}"
        )
    keys = [cell.run_key for cell in schedule]
    if len(set(keys)) != len(keys):
        raise ProtocolError("run_key is not unique across the frozen schedule")
    return schedule


def cell_slug(cell: harness.Cell) -> str:
    """A stable, filesystem-safe directory name for one cell's raw evidence."""

    return f"{cell.index:03d}-{cell.arm}-{cell.task_id}-{cell.seed}"


def schedule_digest(schedule: Sequence[harness.Cell]) -> str:
    """A single digest over the whole frozen schedule, for the run manifest."""

    material = "\n".join(
        "|".join(
            [
                str(cell.index),
                cell.arm,
                cell.task_id,
                str(cell.seed),
                cell.model,
                cell.model_digest,
                cell.qa_mode,
                cell.benchmark_manifest_sha256,
                cell.run_key,
            ]
        )
        for cell in schedule
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def protocol_summary() -> dict[str, Any]:
    """A machine-readable statement of the frozen protocol.  Runs no model."""

    benchmark = load_benchmark()
    schedule = build_phase_l_schedule(benchmark)
    return {
        "phase": "L-A'",
        "canonical_base_commit": CANONICAL_BASE_COMMIT,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_manifest_sha256": benchmark.manifest_sha256,
        "qa_mode": QA_MODE,
        "task_count": TASK_COUNT,
        "arm_order": list(ARM_ORDER),
        "seeds": list(SEEDS),
        "seed_selection_status": SEED_SELECTION_STATUS,
        "planned_cells": len(schedule),
        "schedule_digest": schedule_digest(schedule),
        "instrument_version": EXPECTED_INSTRUMENT_VERSION,
        "raw_schema_version": EXPECTED_RAW_SCHEMA_VERSION,
        "human_gate": {"flag": HUMAN_GATE_FLAG, "env": HUMAN_GATE_ENV,
                       "value": HUMAN_GATE_VALUE},
        "infrastructure_retry_limit": INFRASTRUCTURE_RETRY_LIMIT,
        "execution_authorized": False,
        "model_inference_performed": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Report the frozen protocol and the offline preflight verdict."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="emit the protocol summary as JSON"
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    summary = protocol_summary()
    failures = offline_preflight()
    if args.json:
        print(json.dumps({**summary, "failures": failures}, indent=2, sort_keys=True))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
        for failure in failures:
            print(failure)
    print(
        f"Phase-L frozen protocol: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE"
    )
    return EXIT_OK if not failures else EXIT_PREFLIGHT_STOP


if __name__ == "__main__":
    raise SystemExit(main())
