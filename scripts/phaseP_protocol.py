#!/usr/bin/env python3
"""The frozen Phase-P execution protocol for the pilot-v7-rc4 QA-OFF qualification.

THIS MODULE RUNS NO MODEL.  Importing it contacts no provider, probes no Ollama
endpoint, issues no HTTP request and performs no inference.  It is the single
prospectively frozen statement of *what* a future, separately human-gated Phase-P
execution is, so that the driver which produces rows and the analyzer which reads
them cannot drift apart into two different experiments.

WHAT PHASE P IS
===============

Phase P freezes a protocol.  It does not run one.  pilot-v7-rc4 is a
release-candidate benchmark that is ``UNQUALIFIED``, ``OFFLINE-DESIGNED`` and
NOT FINAL, and nothing in this phase changes any of those.  The question the
future execution would answer is narrow:

    Are pilot-v7-rc4's benign controls, challenge routes, ordered causal
    prerequisites, resource modality, deliberate negative control and fault
    opportunity behaviourally REACHABLE under the two qualified local real-model
    providers with QA OFF?

That is a question about whether the instrument and the benchmark are usable for
a later treatment experiment.  It is NOT the question "does IQA-SOA work".  There
is no QA FULL arm, no ablation, no confirmatory matrix and no treatment effect.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
=========================================

1. **It does not derive seeds.**  ``scripts/phaseP_derive_seeds.py`` derived them
   prospectively from the canonical Phase-P base commit before any rc4 result
   existed; this module READS the committed record and refuses to disagree with
   it.  It never recomputes a triple that a later commit would change.
2. **It does not redesign the benchmark.**  Every rc4 byte is an input.  The
   frozen-input record binds the manifest, the provenance, the qualification
   contract, the AUDIT and the freeze record, plus the whole
   ``benchmark/pilot-v7-rc4`` tree digest.  A single moved byte is a
   ``FROZEN_ARTIFACT_MISMATCH``.
3. **It does not repair the instrument.**  It binds the ACCEPTED Phase-O
   instrument -- version ``4``, raw schema ``5``, ``tool-arguments-1``,
   ``native-tools-adapter-3`` -- through the repository's own revision-chain
   machinery, and points at the accepted records rather than rewriting them.
4. **It does not manufacture an observation.**  The schema-5 ``failure_events``
   list and the schema-4 ``observed_fault_*`` columns arise inside
   ``ExperimentRunner`` from the live ``GatewayOutcome`` sequence.  The driver
   TRANSPORTS them; nothing here reconstructs them from a benchmark declaration.
5. **It does not authorize execution.**  The human gate lives in the driver, is
   closed by default, requires two independent conditions, and is set nowhere in
   this repository.  This module only names it.

THE CONTRACT-DRIFT CLASSIFIER
=============================

``qualification_harness_v2`` owns the rc4 scientific classification.  Phase P
adds exactly one thing on top of it, and adds it INSIDE the stop controller
rather than beside it: :func:`classify_row` refuses a row whose recorded
instrument, adapter, argument-contract or per-arm tool-contract identity is not
the frozen one, as ``FROZEN_ARTIFACT_MISMATCH`` / ``IMMEDIATE_STOP``, before the
rc4 classifier is consulted at all.  A run measured through a drifted instrument
is not a measurement, and continuing would measure every later cell the same way.

The substitution seam is the one ``qualification_harness_v2`` already
established: :class:`StopController` rebinds the module-global classifier for
exactly the duration of one ``record`` call and restores it in ``finally``, so a
frozen caller importing either harness directly is never affected.
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
import phaseO_frozen_input_supersession as supersession  # noqa: E402
import phaseP_derive_seeds as seed_derivation  # noqa: E402
import qualification_harness_v2 as harness  # noqa: E402
import rc4_scoring_vocabulary as rc4_vocabulary  # noqa: E402
from iqa_soa.agent.providers import SANDBOX_TOOL_NAMES  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    FAILURE_EVENT_RAW_SCHEMA_VERSION,
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
    TOOL_CONTRACT_INSTRUMENT_VERSION,
)
from iqa_soa.metrics.definitions import PILOT_RAW_FIELDS_V5  # noqa: E402
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACT_VERSION,
    contract_digest,
)

# --------------------------------------------------------------------------
# The generic path/containment helpers, REBOUND rather than reimplemented
# --------------------------------------------------------------------------
#
# ``scripts/phaseL_protocol.py`` is a frozen Phase-L input, bound by SHA-256 in
# ``docs/phaseL_frozen_execution_inputs.json``, and it is NOT edited here.  Its
# containment helpers -- the absolute-path, traversal and canonical-containment
# rules that stop a persisted row from pointing at another cell's evidence --
# are generic path logic with no rc3 in them, and adversarial review of Phase L
# hardened them specifically.  Rebinding them means the repository has ONE
# implementation of evidence containment, so a future hardening cannot apply to
# one phase and miss the other.
import phaseL_protocol as _frozen_path_contract  # noqa: E402

contained_child = _frozen_path_contract.contained_child
ProtocolError = _frozen_path_contract.ProtocolError

#: Identity fields an evidence event carries that MUST agree with the row it is
#: filed under.  Rebound for the same reason.
TRACE_IDENTITY_FIELDS: tuple[str, ...] = _frozen_path_contract.TRACE_IDENTITY_FIELDS

# --------------------------------------------------------------------------
# Canonical provenance of this freeze
# --------------------------------------------------------------------------

#: The commit Phase P started from: Phase O / O-R1 merged into main (PR #13).
CANONICAL_BASE_COMMIT = "f65ee4980813b465431c5f7d75a0d00db87785b6"

#: The Phase-O parent, retained so the chain from Phase N is readable here.
PHASE_O_PARENT_COMMIT = "0cc3b05ab79559acdd4f50675ed7937199dc4dbe"

#: The commit that archived the completed Phase-L-B evidence (PR #11).
PHASE_L_B_EXECUTION_COMMIT = supersession.PHASE_L_B_EXECUTION_COMMIT

PHASE = "P"

# --------------------------------------------------------------------------
# Seeds -- READ from the Phase-P derivation record, never recomputed here
# --------------------------------------------------------------------------

#: The exact triple ``scripts/phaseP_derive_seeds.py`` derived, in the exact
#: order it derived them.  Frozen: the ORDER is part of the protocol, because the
#: schedule is seed-minor and a reordering would be a different schedule.
SEEDS: tuple[int, int, int] = (1197050110, 1904689056, 1133353488)

SEED_SELECTION_STATUS = "PROSPECTIVELY_DERIVED_IN_PHASE_P_AND_NEVER_EXECUTED"

#: Where the derivation is recorded.  This protocol reads it; it never edits it.
SEED_RECORD_RELATIVE = seed_derivation.RECORD_RELATIVE

#: Every seed any committed phase of this repository already consumed or reserved.
FORBIDDEN_HISTORICAL_SEEDS: frozenset[int] = seed_derivation.FORBIDDEN_SEEDS

#: The Phase-L triple specifically, and its permanent status.
PHASE_L_SEEDS: tuple[int, int, int] = seed_derivation.PHASE_L_SEEDS
PHASE_L_SEED_STATUS = seed_derivation.PHASE_L_SEED_STATUS

# --------------------------------------------------------------------------
# Arms, model identity and runtime pins
# --------------------------------------------------------------------------

#: Arm order is frozen and the schedule is arm-major, so this tuple fixes which
#: arm runs first and therefore which arm a cross-arm immediate stop protects.
#: It is the scientifically established order: Phase D qualified the two local
#: providers in it, Phase F, Phase I and Phase L-B all executed in it, and Phase
#: P preserves it so a Phase-P schedule position is directly comparable to a
#: Phase-L-B one.  There is no reason to change it and changing it would discard
#: that comparability for nothing.
ARM_ORDER: tuple[str, str] = ("qwen", "mistral")

#: Provider slot in ``configs/phaseP-models.yaml``, addressed by arm name so a
#: mislabelled invocation cannot silently produce the wrong arm.
ARM_PROVIDER_SLOT: Mapping[str, str] = {
    "qwen": "qwen_native_none",
    "mistral": "mistral_native_trailing_user",
}

#: Verified from committed evidence by :func:`check_model_pins`, never assumed.
EXPECTED_MODEL: Mapping[str, str] = {
    "qwen": "qwen3.5:27b",
    "mistral": "mistral-small3.2:24b",
}

EXPECTED_MODEL_DIGEST: Mapping[str, str] = {
    "qwen3.5:27b": (
        "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
    ),
    "mistral-small3.2:24b": (
        "5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b"
    ),
}

#: An INSTRUMENT setting, already qualified, not an experimental factor.  A
#: qwen-vs-mistral difference must therefore never be read causally, and Phase P
#: computes no model comparison and publishes no model ranking.
EXPECTED_TOOL_CONTRACT_POLICY: Mapping[str, str] = {
    "qwen": "none",
    "mistral": "trailing_user",
}

EXPECTED_PROTOCOL = "native_tools"

EXPECTED_RUNTIME_VERSION = "0.32.13"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

#: Checked by NAME only.  The value is never read into a message, never printed
#: and never written to an artifact.  Phase-P specific so that a Phase-F,
#: Phase-I or Phase-L credential cannot silently satisfy a Phase-P precondition.
CREDENTIAL_ENV = "PHASEP_OLLAMA_API_KEY"

#: The committed artifacts every model/runtime pin above is READ from.  Each is
#: an independent record of a real, completed, committed run, and
#: :func:`check_model_pins` requires them to agree unanimously.  A disagreement
#: is a HOLD, never an invitation to take whichever value is convenient.
MODEL_PIN_EVIDENCE_PATHS: tuple[str, ...] = (
    "results/phaseD-qualification/preflight.json",
    "results/phaseF-qualification/phaseF-provenance.json",
    "results/phaseI-rc2-requalification/phaseI-provenance.json",
    "results/phaseL-rc3-requalification/phaseL-run-manifest.json",
    "configs/phaseL-models.yaml",
)

#: Phase D deliberately ran the SAME model under two different
#: ``tool_contract_policy`` values in order to qualify the policy repair itself,
#: so it is an authority on model digest and runtime version but says nothing
#: about which policy belongs to which ARM.  Naming the exclusion here keeps it a
#: recorded methodological decision rather than a silent omission.
ARM_POLICY_EVIDENCE_PATHS: tuple[str, ...] = (
    "results/phaseF-qualification/phaseF-provenance.json",
    "results/phaseI-rc2-requalification/phaseI-provenance.json",
    "configs/phaseL-models.yaml",
)

# --------------------------------------------------------------------------
# Matrix shape
# --------------------------------------------------------------------------

BENCHMARK_VERSION = "pilot-v7-rc4"
QA_MODE = "off"
TASK_COUNT = 17
ARM_COUNT = 2
SEED_COUNT = 3
PLANNED_CELLS = TASK_COUNT * ARM_COUNT * SEED_COUNT  # 102

#: The runner label these rows carry.  ``iqa_soa.metrics.pilot`` accepts only
#: ``real_model_pilot`` and refuses every other label at both the manifest and
#: the row level, so this label is the structural, machine-checked guarantee that
#: a Phase-P row can never enter pilot analysis.  Phases F, I and L use the same
#: label for the same reason.
EXPERIMENT_KIND = "real_model_connectivity_smoke"

#: Fixed at zero, and the runner independently refuses any other value.  A
#: provider or model failure is a RECORDED OUTCOME, never a reason to rerun.
INFRASTRUCTURE_RETRY_LIMIT = 0

#: Stated as data so the prohibition is machine-readable rather than prose.
NO_RETRY_POLICY: Mapping[str, bool] = {
    "retries_permitted": False,
    "replacement_cells_permitted": False,
    "adaptive_cells_permitted": False,
    "silent_rerun_permitted": False,
    "additional_seeds_permitted": False,
    "resume_after_immediate_stop_permitted": False,
}

#: Everything Phase P refuses to execute, named so a reader does not have to
#: infer the scope from what is absent.
OUT_OF_SCOPE_TREATMENTS: tuple[str, ...] = ("full", "partial", "ablation", "confirmatory")

# --------------------------------------------------------------------------
# Instrument / schema / contract pins -- the ACCEPTED Phase-O revision
# --------------------------------------------------------------------------

EXPECTED_INSTRUMENT_VERSION = "4"
EXPECTED_RAW_SCHEMA_VERSION = 5
EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION = "tool-arguments-1"
EXPECTED_NATIVE_TOOL_ADAPTER_VERSION = "native-tools-adapter-3"

#: The digest of the argument contract the provider ADVERTISES and the sandbox
#: ENFORCES.  Computed from the live table at import so it can never claim a
#: contract the code does not render; frozen into the record so a change to the
#: table is a detectable drift rather than a silent one.
EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST = contract_digest(SANDBOX_TOOL_NAMES)

PHASE_O_REVISION_RELATIVE = "docs/phaseO_instrument_revision.json"
PHASE_M_REVISION_RELATIVE = "docs/phaseM_instrument_revision.json"
RC4_REVISION_RECORD_RELATIVE = "docs/phaseO_rc4_revision_record.json"

#: The approved revision CHAIN this protocol is frozen against, oldest first.
#: Phase P appends nothing to it: it points at the accepted records.
REVISION_CHAIN_RELATIVE: tuple[str, ...] = (
    PHASE_M_REVISION_RELATIVE,
    PHASE_O_REVISION_RELATIVE,
)

HARNESS_VERSION = harness.HARNESS_VERSION
SCORING_VOCABULARY_VERSION = rc4_vocabulary.VOCABULARY_VERSION

# --------------------------------------------------------------------------
# The human execution gate
# --------------------------------------------------------------------------

HUMAN_GATE_ENV = "IQA_SOA_PHASE_P_HUMAN_GATE"
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
#: The canonical runner emits neither, and both are frozen inputs rather than
#: runtime observations, so stamping them is legitimate.  Everything else the
#: binding check compares must come from the runner.
DRIVER_STAMPED_IDENTITY_FIELDS: tuple[str, ...] = ("model_digest", "run_key")

#: Bookkeeping the driver adds so a row can be located in the frozen schedule.
#: None of these participates in classification.
DRIVER_STAMPED_SCHEDULE_FIELDS: tuple[str, ...] = (
    "schedule_index",
    "arm",
    "cell_key",
    "cell_experiment_dir",
)

#: Fields the driver TRANSPORTS from the cell's own persisted ``manifest.json``
#: because the canonical runner records them there rather than on the row.
#:
#: These are OBSERVATIONS, not frozen inputs: they say what the run's own
#: artifact recorded about the provider that produced it.  The driver copies
#: them; :func:`contract_drift` then compares them against the frozen pins.
#: Copying a constant instead would make the disclosure precondition a tautology
#: -- the row would "prove" the contract was advertised because the driver said
#: so -- which is precisely the circularity the Phase-N ordering rule forbids.
MANIFEST_TRANSPORTED_FIELDS: tuple[str, ...] = (
    "raw_schema_version",
    "tool_argument_contract_version",
    "tool_argument_contract_digest",
)

#: Identity the RUNNER must emit and the harness must bind, unstamped by the
#: driver.  ``harness.REQUIRED_IDENTITY_FIELDS`` minus the two above.
RUNNER_EMITTED_IDENTITY_FIELDS: tuple[str, ...] = tuple(
    name
    for name in harness.REQUIRED_IDENTITY_FIELDS
    if name not in DRIVER_STAMPED_IDENTITY_FIELDS
)

#: Every field a completed Phase-P row must carry.  This is the single contract
#: the driver writes to and the analyzer reads from; a test asserts they agree.
PHASE_P_ROW_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *PILOT_RAW_FIELDS_V5,
            *harness.REQUIRED_IDENTITY_FIELDS,
            *harness.REQUIRED_RC4_ROW_FIELDS,
            *DRIVER_STAMPED_SCHEDULE_FIELDS,
            *MANIFEST_TRANSPORTED_FIELDS,
        )
    )
)

#: Every field one entry of the StopController classification ledger must carry
#: into the final run manifest, so the analyzer's independent reclassification
#: has something real to disagree with.
RUN_MANIFEST_CLASSIFICATION_FIELDS: tuple[str, ...] = (
    "cell",
    "index",
    "failure_class",
    "disposition",
)

#: The two rc4 tasks that declare a scripted fault.  Recorded for reporting only;
#: NEVER used as an observation and never written into a row.
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

FROZEN_INPUTS_RELATIVE = "docs/phaseP_frozen_execution_inputs.json"
PLAN_RELATIVE = "docs/phaseP_rc4_real_model_qualification_plan.md"

#: Every scientific execution input, hashed as raw working-tree bytes per
#: ``docs/hash_basis_policy.md``.  The future driver asserts all of them before
#: any provider request.  Order is stable so the generated record is
#: deterministic.
FROZEN_INPUT_PATHS: tuple[str, ...] = (
    # The protocol itself.
    PLAN_RELATIVE,
    "configs/phaseP-qualification.yaml",
    "configs/phaseP-models.yaml",
    "scripts/phaseP_protocol.py",
    "scripts/phaseP_derive_seeds.py",
    "scripts/run_phaseP_rc4_qualification.py",
    "scripts/analyze_phaseP_rc4_qualification.py",
    "scripts/qualification_harness_v2.py",
    "scripts/rc4_scoring_vocabulary.py",
    # THE FROZEN MODULES PHASE P ACTUALLY EXECUTES.  Each is already bound by an
    # earlier freeze -- ``scripts/qualification_harness.py`` and
    # ``scripts/phaseL_protocol.py`` and
    # ``scripts/analyze_phaseL_requalification.py`` by
    # ``docs/phaseL_frozen_execution_inputs.json``, whose live residual
    # ``scripts/phaseO_frozen_input_supersession.py`` still checks in full -- and
    # none of them is edited here.  They are repeated in PHASE P'S OWN record
    # because Phase P depends on their bytes directly: the rc4 harness loads the
    # frozen harness by path, this protocol rebinds the frozen containment
    # helpers, and the Phase-P analyzer executes the frozen plan builder.  An
    # inherited binding is a real binding, but a reviewer should not have to
    # trace two records to see what this phase runs.
    "scripts/qualification_harness.py",
    "scripts/phaseL_protocol.py",
    "scripts/analyze_phaseL_requalification.py",
    # The benchmark and its scoring contract.
    "benchmark/pilot-v7-rc4/manifest.json",
    "benchmark/pilot-v7-rc4/provenance.json",
    "benchmark/pilot-v7-rc4/qualification-contract.json",
    "benchmark/pilot-v7-rc4/AUDIT.md",
    "benchmark/pilot-v7-rc4/freeze-record.json",
    # The QA policy the future treatment would be defined against.  Phase P runs
    # QA OFF only and binds it so that a later FULL arm cannot silently be
    # defined against a different policy.
    "configs/policies/default.xml",
    # The accepted instrument revision chain this protocol is built on.
    PHASE_M_REVISION_RELATIVE,
    PHASE_O_REVISION_RELATIVE,
    RC4_REVISION_RECORD_RELATIVE,
    # The seed provenance.
    SEED_RECORD_RELATIVE,
)

#: Tree digests recorded alongside the per-file hashes.  ``src/iqa_soa`` is the
#: accepted Phase-O instrument; the rc4 tree is the benchmark's scientific bytes.
FROZEN_TREE_ROOTS: tuple[str, ...] = ("src/iqa_soa", "benchmark/pilot-v7-rc4")


def sha256_file(relative: str) -> str:
    """Hash RAW working-tree bytes.  Never normalize (docs/hash_basis_policy.md)."""

    return hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()


def tree_digest(relative_root: str) -> str:
    """The repository's canonical tree digest, from ``instrument_revision``."""

    return instrument_revision.tree_digest(relative_root)


def compute_frozen_inputs() -> dict[str, Any]:
    """The frozen-hash record, computed from the current working tree."""

    return {
        "record_kind": "phase_p_frozen_execution_inputs",
        "phase": PHASE,
        "benchmark_version": BENCHMARK_VERSION,
        "canonical_base_commit": CANONICAL_BASE_COMMIT,
        "hash_basis": (
            "raw working-tree bytes, LF canonical checkout per "
            "docs/hash_basis_policy.md"
        ),
        "model_inference_performed": False,
        "execution_authorized": False,
        "authorizes_confirmatory_execution": False,
        "instrument_version": EXPECTED_INSTRUMENT_VERSION,
        "raw_schema_version": EXPECTED_RAW_SCHEMA_VERSION,
        "tool_argument_contract_version": EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        "tool_argument_contract_digest": EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
        "native_tool_adapter_version": EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        "harness_version": HARNESS_VERSION,
        "scoring_vocabulary_version": SCORING_VOCABULARY_VERSION,
        "seed_selection_status": SEED_SELECTION_STATUS,
        "seeds": list(SEEDS),
        "arm_order": list(ARM_ORDER),
        "qa_mode": QA_MODE,
        "planned_cells": PLANNED_CELLS,
        "infrastructure_retry_limit": INFRASTRUCTURE_RETRY_LIMIT,
        "results_namespace": RESULTS_NAMESPACE,
        "files": {relative: sha256_file(relative) for relative in FROZEN_INPUT_PATHS},
        "trees": {root: tree_digest(root) for root in FROZEN_TREE_ROOTS},
    }


def load_frozen_inputs() -> Mapping[str, Any]:
    path = PROJECT_ROOT / FROZEN_INPUTS_RELATIVE
    if not path.is_file():
        raise ProtocolError(
            f"the frozen-input record is missing: {FROZEN_INPUTS_RELATIVE}"
        )
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
        return [
            "FROZEN_ARTIFACT_MISMATCH: the frozen-input record carries no file table"
        ]
    for name in FROZEN_INPUT_PATHS:
        if name not in recorded_files:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {name} is a frozen execution input but "
                "is absent from the frozen-input record"
            )
    for name in recorded_files:
        if name not in FROZEN_INPUT_PATHS:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: the frozen-input record names {name}, "
                "which is not a declared Phase-P execution input"
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
            recorded_tree = recorded_trees.get(root)
            actual_tree = tree_digest(root)
            if recorded_tree != actual_tree:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: tree {root} recorded={recorded_tree} "
                    f"actual={actual_tree}"
                )

    for key, expected in (
        ("seeds", list(SEEDS)),
        ("arm_order", list(ARM_ORDER)),
        ("planned_cells", PLANNED_CELLS),
        ("qa_mode", QA_MODE),
        ("instrument_version", EXPECTED_INSTRUMENT_VERSION),
        ("raw_schema_version", EXPECTED_RAW_SCHEMA_VERSION),
        (
            "tool_argument_contract_version",
            EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        ),
        (
            "tool_argument_contract_digest",
            EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
        ),
        (
            "native_tool_adapter_version",
            EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        ),
        ("results_namespace", RESULTS_NAMESPACE),
    ):
        if record.get(key) != expected:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: the frozen-input record declares "
                f"{key}={record.get(key)!r}, this protocol is frozen against "
                f"{expected!r}"
            )
    if record.get("execution_authorized") is not False:
        failures.append(
            "PROTOCOL_DEVIATION: the frozen-input record does not attest that no "
            "execution is authorized"
        )
    return failures


def check_plan_sidecar() -> list[str]:
    """The frozen plan must match its recorded ``.sha256`` sidecar."""

    plan = PROJECT_ROOT / PLAN_RELATIVE
    sidecar = plan.with_suffix(".sha256")
    if not plan.is_file():
        return [f"FROZEN_ARTIFACT_MISMATCH: {PLAN_RELATIVE} does not exist"]
    if not sidecar.is_file():
        return [f"FROZEN_ARTIFACT_MISMATCH: {PLAN_RELATIVE} has no .sha256 sidecar"]
    recorded = sidecar.read_text(encoding="utf-8").split()[0].strip()
    actual = sha256_file(PLAN_RELATIVE)
    if recorded != actual:
        return [
            f"FROZEN_ARTIFACT_MISMATCH: {PLAN_RELATIVE} recorded={recorded} "
            f"actual={actual}"
        ]
    return []


# --------------------------------------------------------------------------
# Instrument / contract pins
# --------------------------------------------------------------------------


def check_instrument_pins() -> list[str]:
    """The CURRENT accepted instrument, bound through the approved revision chain.

    Nothing historical is rewritten.  The Phase-K freeze assertion and the
    Phase-M record are proved where they are true -- from committed bytes at
    their own commits -- by ``scripts/instrument_revision.py``; only the HEAD of
    the chain is asserted against the live tree, and Phase P asserts it strictly.
    """

    failures: list[str] = []

    for label, actual, expected in (
        ("instrument version", INSTRUMENT_VERSION, EXPECTED_INSTRUMENT_VERSION),
        (
            "the Phase-O tool-contract instrument constant",
            TOOL_CONTRACT_INSTRUMENT_VERSION,
            EXPECTED_INSTRUMENT_VERSION,
        ),
        (
            "native tool adapter version",
            NATIVE_TOOL_ADAPTER_VERSION,
            EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        ),
        (
            "tool argument contract version",
            TOOL_ARGUMENT_CONTRACT_VERSION,
            EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        ),
        (
            "the rc4 harness expected argument contract",
            harness.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
            EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        ),
    ):
        if actual != expected:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {label} is {actual!r}, this protocol is "
                f"frozen against {expected!r}"
            )
    for label, numeric, expected_numeric in (
        ("raw schema version", RAW_SCHEMA_VERSION, EXPECTED_RAW_SCHEMA_VERSION),
        (
            "the Phase-O failure-event raw-schema constant",
            FAILURE_EVENT_RAW_SCHEMA_VERSION,
            EXPECTED_RAW_SCHEMA_VERSION,
        ),
    ):
        if numeric != expected_numeric:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {label} is {numeric}, this protocol is "
                f"frozen against {expected_numeric}"
            )

    actual_digest = contract_digest(SANDBOX_TOOL_NAMES)
    if actual_digest != EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST:  # pragma: no cover
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the advertised tool argument contract "
            f"digests to {actual_digest}, the frozen pin is "
            f"{EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST}"
        )

    revision_path = PROJECT_ROOT / PHASE_O_REVISION_RELATIVE
    if not revision_path.is_file():
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: {PHASE_O_REVISION_RELATIVE} does not exist"
        )
        return failures
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    current = revision.get("current_instrument")
    if not isinstance(current, Mapping):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-O revision record names no current "
            "instrument"
        )
        return failures
    for key, expected_value in (
        ("instrument_version", EXPECTED_INSTRUMENT_VERSION),
        ("raw_schema_version", EXPECTED_RAW_SCHEMA_VERSION),
        ("tool_argument_contract_version", EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION),
        ("native_tool_adapter_version", EXPECTED_NATIVE_TOOL_ADAPTER_VERSION),
    ):
        if current.get(key) != expected_value:
            failures.append(
                "FROZEN_ARTIFACT_MISMATCH: the approved Phase-O revision records "
                f"{key}={current.get(key)!r}, expected {expected_value!r}"
            )
    approved_tree = str(current.get("src_iqa_soa_tree") or "")
    actual_tree = tree_digest("src/iqa_soa")
    if approved_tree != actual_tree:
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: src/iqa_soa digests to {actual_tree}, the "
            f"approved Phase-O revision is {approved_tree}"
        )

    # Every INDIVIDUALLY recorded Phase-O instrument file must still hash to its
    # own approved SHA-256.  A matching tree digest already implies this, but the
    # brief requires it stated per file so a report can name the offending file.
    changed = revision.get("changed_files")
    if isinstance(changed, Mapping):
        for relative, entry in sorted(changed.items()):
            if not isinstance(entry, Mapping):  # pragma: no cover - malformed record
                continue
            recorded = str(entry.get("sha256") or "")
            target = PROJECT_ROOT / relative
            if not target.is_file():
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: approved Phase-O instrument file "
                    f"{relative} does not exist"
                )
                continue
            actual_file = sha256_file(relative)
            if actual_file != recorded:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: approved Phase-O instrument file "
                    f"{relative} recorded={recorded} actual={actual_file}"
                )

    # The repository's own chain check: historical base -> Phase M -> Phase O,
    # verified link by link, each non-head link proved from committed bytes.
    chain = [
        path.relative_to(instrument_revision.REPO_ROOT).as_posix()
        for path in instrument_revision.REVISION_CHAIN
    ]
    if tuple(chain) != REVISION_CHAIN_RELATIVE:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the approved revision chain is "
            f"{chain}, this protocol is frozen against "
            f"{list(REVISION_CHAIN_RELATIVE)}"
        )
    failures.extend(
        f"FROZEN_ARTIFACT_MISMATCH: {failure}"
        for failure in instrument_revision.check_instrument_provenance()
    )
    return failures


def check_frozen_historical_inputs() -> list[str]:
    """Every ``path -> SHA-256`` binding any committed provenance record holds.

    The Phase-L ``src/iqa_soa`` TREE pin is the one assertion Phase O superseded,
    and it is handled by ``scripts/phaseO_frozen_input_supersession.py``, which
    proves the Phase-L freeze at the commit where it actually bound a run and
    requires the live residual to be EXACTLY the enumerated superseded set.
    Phase P runs that module rather than restating its conclusion.
    """

    return [
        *(
            f"FROZEN_ARTIFACT_MISMATCH: {failure}"
            for failure in frozen_input_audit.audit()
        ),
        *(f"FROZEN_ARTIFACT_MISMATCH: {failure}" for failure in supersession.run_all()),
    ]


# --------------------------------------------------------------------------
# Seed provenance
# --------------------------------------------------------------------------


def check_seed_provenance() -> list[str]:
    """The frozen triple must be exactly what the Phase-P derivation recorded."""

    failures: list[str] = []
    record_path = PROJECT_ROOT / SEED_RECORD_RELATIVE
    if not record_path.is_file():
        return [
            f"FROZEN_ARTIFACT_MISMATCH: {SEED_RECORD_RELATIVE} does not exist; the "
            "Phase-P seeds are read from their derivation record, never assumed"
        ]
    record = json.loads(record_path.read_text(encoding="utf-8"))

    if record.get("seeds") != list(SEEDS):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-P seed record carries "
            f"{record.get('seeds')!r}, this protocol is frozen against {list(SEEDS)}"
        )
    if str(record.get("canonical_base_commit")) != CANONICAL_BASE_COMMIT:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-P seed record was derived from "
            f"{record.get('canonical_base_commit')!r}, expected "
            f"{CANONICAL_BASE_COMMIT!r}"
        )
    if str(record.get("domain_separator")) != seed_derivation.DOMAIN_SEPARATOR:
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the Phase-P seed record uses domain separator "
            f"{record.get('domain_separator')!r}"
        )
    for key in (
        "derived_before_any_rc4_inference",
        "seed_order_is_frozen",
    ):
        if record.get(key) is not True:
            failures.append(
                f"PROTOCOL_DEVIATION: the seed record does not attest {key}"
            )
    for key in (
        "model_inference_performed",
        "model_output_influenced_derivation",
        "manual_selection_performed",
    ):
        if record.get(key) is not False:
            failures.append(
                f"PROTOCOL_DEVIATION: the seed record does not deny {key}"
            )
    if record.get("phase_l_seeds_status") != PHASE_L_SEED_STATUS:
        failures.append(
            "PROTOCOL_DEVIATION: the seed record does not record the Phase-L seeds "
            f"as {PHASE_L_SEED_STATUS}"
        )

    checks = record.get("collision_checks")
    if not isinstance(checks, Mapping):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the seed record carries no collision checks"
        )
    else:
        if checks.get("collision_free") is not True:
            failures.append(
                "PROTOCOL_DEVIATION: the seed record does not attest that the triple "
                "is collision free"
            )
        if checks.get("forbidden_set_covers_every_committed_seed") is not True:
            failures.append(
                "PROTOCOL_DEVIATION: the seed record does not prove the forbidden "
                "set covers every seed the committed history records"
            )

    # And the properties are RE-PROVED here rather than trusted from the record.
    overlap = sorted(set(SEEDS) & FORBIDDEN_HISTORICAL_SEEDS)
    if overlap:
        failures.append(
            f"PROTOCOL_DEVIATION: seeds {overlap} are historical qualification seeds"
        )
    consumed = sorted(set(SEEDS) & set(PHASE_L_SEEDS))
    if consumed:
        failures.append(
            f"PROTOCOL_DEVIATION: seeds {consumed} were CONSUMED_BY_FORMAL_PHASE_L_B "
            "and may never be reused"
        )
    if len(set(SEEDS)) != len(SEEDS):
        failures.append("PROTOCOL_DEVIATION: the Phase-P seed triple is not unique")
    if len(SEEDS) != SEED_COUNT:
        failures.append(
            f"PROTOCOL_DEVIATION: Phase P admits exactly {SEED_COUNT} seeds"
        )
    if any(seed <= 0 for seed in SEEDS):
        failures.append("PROTOCOL_DEVIATION: a Phase-P seed is not a positive integer")

    # The history scan is re-run here rather than trusted from the record.  It is
    # scoped to sources OUTSIDE Phase P's own declared artifacts, which
    # necessarily carry the derived triple once it is committed; a Phase-P seed
    # appearing anywhere else is a leak and is reported as one.
    scanned = seed_derivation.scan_committed_seeds(PROJECT_ROOT)
    prior = seed_derivation.prior_phase_seeds(scanned)
    reused = sorted(set(SEEDS) & set(prior))
    if reused:
        failures.append(
            f"PROTOCOL_DEVIATION: seeds {reused} already appear in committed history "
            f"outside Phase P's own artifacts: "
            f"{ {seed: prior[seed] for seed in reused} }"
        )
    uncovered = sorted(set(prior) - FORBIDDEN_HISTORICAL_SEEDS)
    if uncovered:
        failures.append(
            "PROTOCOL_DEVIATION: the committed history records seeds the forbidden "
            f"set does not cover: {uncovered}"
        )
    declared_only = sorted(
        set(SEEDS) & set(scanned) - set(prior)
    )
    if len(declared_only) != len(SEEDS):
        missing = sorted(set(SEEDS) - set(declared_only))
        failures.append(
            f"FROZEN_ARTIFACT_MISMATCH: seeds {missing} are not declared by Phase P's "
            f"own artifacts {sorted(seed_derivation.PHASE_P_ARTIFACTS)}"
        )
    return failures


# --------------------------------------------------------------------------
# Model / provider / runtime pins, read from COMMITTED evidence
# --------------------------------------------------------------------------


def _load_json(relative: str) -> Mapping[str, Any] | None:
    path = PROJECT_ROOT / relative
    if not path.is_file():
        return None
    parsed = json.loads(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, Mapping) else None


@dataclass(frozen=True, slots=True)
class PinAssertion:
    """One committed artifact's statement about one arm's identity."""

    source: str
    arm: str
    model: str
    model_digest: str
    runtime_version: str
    tool_contract_policy: str
    protocol: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "arm": self.arm,
            "model": self.model,
            "model_digest": self.model_digest,
            "runtime_version": self.runtime_version,
            "tool_contract_policy": self.tool_contract_policy,
            "protocol": self.protocol,
        }


def _model_to_arm(model: str) -> str:
    for arm, name in EXPECTED_MODEL.items():
        if name == model:
            return arm
    return ""


def model_pin_evidence() -> list[PinAssertion]:
    """Read every committed artifact that states an arm's model/runtime identity.

    Nothing here contacts a runtime.  Each assertion is a quotation from a
    committed record of a completed run, or from the accepted Phase-L protocol
    configuration.  :func:`check_model_pins` then requires unanimity.
    """

    found: list[PinAssertion] = []

    preflight = _load_json("results/phaseD-qualification/preflight.json")
    if preflight is not None:
        arms = preflight.get("arms")
        if isinstance(arms, Mapping):
            for slot, entry in sorted(arms.items()):
                if not isinstance(entry, Mapping):  # pragma: no cover
                    continue
                descriptor = entry.get("descriptor")
                runtime = entry.get("runtime_provenance")
                if not isinstance(descriptor, Mapping) or not isinstance(
                    runtime, Mapping
                ):  # pragma: no cover
                    continue
                model = str(descriptor.get("model") or "")
                arm = _model_to_arm(model)
                if not arm:  # pragma: no cover - defensive
                    continue
                found.append(
                    PinAssertion(
                        source=(
                            f"results/phaseD-qualification/preflight.json#arms.{slot}"
                        ),
                        arm=arm,
                        model=model,
                        model_digest=str(runtime.get("model_digest") or ""),
                        runtime_version=str(runtime.get("runtime_version") or ""),
                        # Phase D deliberately varied this to qualify the repair
                        # itself, so it asserts nothing about arm policy.
                        tool_contract_policy="",
                        protocol=str(descriptor.get("protocol") or ""),
                    )
                )

    phase_f = _load_json("results/phaseF-qualification/phaseF-provenance.json")
    if phase_f is not None:
        providers = phase_f.get("providers")
        if isinstance(providers, Mapping):
            for model_name, entry in sorted(providers.items()):
                if not isinstance(entry, Mapping):  # pragma: no cover
                    continue
                runtime = entry.get("runtime")
                runtime = runtime if isinstance(runtime, Mapping) else {}
                arm = _model_to_arm(str(model_name))
                if not arm:  # pragma: no cover - defensive
                    continue
                found.append(
                    PinAssertion(
                        source=(
                            "results/phaseF-qualification/phaseF-provenance.json"
                            f"#providers.{model_name}"
                        ),
                        arm=arm,
                        model=str(entry.get("model") or model_name),
                        model_digest=str(runtime.get("model_digest") or ""),
                        runtime_version=str(runtime.get("runtime_version") or ""),
                        tool_contract_policy=str(
                            entry.get("tool_contract_policy") or ""
                        ),
                        protocol=str(entry.get("protocol") or ""),
                    )
                )

    phase_i = _load_json("results/phaseI-rc2-requalification/phaseI-provenance.json")
    if phase_i is not None:
        arms_list = phase_i.get("arms")
        if isinstance(arms_list, Sequence) and not isinstance(arms_list, (str, bytes)):
            for entry in arms_list:
                if not isinstance(entry, Mapping):  # pragma: no cover
                    continue
                model = str(entry.get("model") or "")
                arm = _model_to_arm(model)
                if not arm:  # pragma: no cover - defensive
                    continue
                found.append(
                    PinAssertion(
                        source=(
                            "results/phaseI-rc2-requalification/"
                            f"phaseI-provenance.json#arms.{model}"
                        ),
                        arm=arm,
                        model=model,
                        model_digest=str(entry.get("model_digest") or ""),
                        runtime_version=str(entry.get("runtime_version") or ""),
                        tool_contract_policy=str(
                            entry.get("tool_contract_policy") or ""
                        ),
                        # Phase I records the runtime, not the wire protocol.
                        protocol="",
                    )
                )

    phase_l = _load_json("results/phaseL-rc3-requalification/phaseL-run-manifest.json")
    if phase_l is not None:
        metadata = phase_l.get("runtime_metadata")
        if isinstance(metadata, Mapping):
            for arm, entry in sorted(metadata.items()):
                if not isinstance(entry, Mapping):  # pragma: no cover
                    continue
                found.append(
                    PinAssertion(
                        source=(
                            "results/phaseL-rc3-requalification/"
                            f"phaseL-run-manifest.json#runtime_metadata.{arm}"
                        ),
                        arm=str(arm),
                        model=str(entry.get("model") or ""),
                        model_digest=str(entry.get("model_digest") or ""),
                        runtime_version=str(entry.get("runtime_version") or ""),
                        # The Phase-L run manifest records the live metadata probe,
                        # which is model identity only.
                        tool_contract_policy="",
                        protocol="",
                    )
                )

    found.extend(_phase_l_config_assertions())
    return found


def _phase_l_config_assertions() -> list[PinAssertion]:
    """The accepted Phase-L protocol configuration, read as committed evidence."""

    import yaml  # type: ignore[import-untyped]  # noqa: PLC0415

    path = PROJECT_ROOT / "configs/phaseL-models.yaml"
    if not path.is_file():  # pragma: no cover - defensive
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):  # pragma: no cover - defensive
        return []
    providers = data.get("providers")
    if not isinstance(providers, Mapping):  # pragma: no cover - defensive
        return []
    found: list[PinAssertion] = []
    for slot, entry in sorted(providers.items()):
        if not isinstance(entry, Mapping):  # pragma: no cover
            continue
        model = str(entry.get("model") or "")
        arm = _model_to_arm(model)
        if not arm:  # pragma: no cover - defensive
            continue
        found.append(
            PinAssertion(
                source=f"configs/phaseL-models.yaml#providers.{slot}",
                arm=arm,
                model=model,
                model_digest="",
                runtime_version="",
                tool_contract_policy=str(entry.get("tool_contract_policy") or ""),
                protocol=str(entry.get("protocol") or ""),
            )
        )
    return found


def check_model_pins() -> list[str]:
    """The frozen model/runtime/policy pins must be UNANIMOUS in committed evidence.

    A disagreement between authoritative committed sources is a HOLD, never a
    reason to take whichever value is convenient, so every disagreement is
    reported with the source that produced it.
    """

    failures: list[str] = []
    assertions = model_pin_evidence()
    if not assertions:
        return [
            "FROZEN_ARTIFACT_MISMATCH: no committed artifact states an arm's model "
            "identity, so the Phase-P pins cannot be verified from evidence"
        ]

    for name in MODEL_PIN_EVIDENCE_PATHS:
        if not (PROJECT_ROOT / name).is_file():
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: the declared pin evidence {name} does "
                "not exist"
            )

    seen_arms: set[str] = set()
    for item in assertions:
        seen_arms.add(item.arm)
        if item.arm not in EXPECTED_MODEL:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {item.source} names arm {item.arm!r}, "
                f"which Phase P does not declare"
            )
            continue
        expected_model = EXPECTED_MODEL[item.arm]
        if item.model and item.model != expected_model:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {item.source} records arm {item.arm!r} as "
                f"{item.model!r}, the frozen pin is {expected_model!r}"
            )
        if item.model_digest:
            expected_digest = EXPECTED_MODEL_DIGEST[expected_model]
            if item.model_digest != expected_digest:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: {item.source} records "
                    f"{expected_model!r} digest {item.model_digest!r}, the frozen pin "
                    f"is {expected_digest!r}"
                )
        if item.runtime_version and item.runtime_version != EXPECTED_RUNTIME_VERSION:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {item.source} records runtime version "
                f"{item.runtime_version!r}, the frozen pin is "
                f"{EXPECTED_RUNTIME_VERSION!r}"
            )
        if item.protocol and item.protocol != EXPECTED_PROTOCOL:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {item.source} records protocol "
                f"{item.protocol!r}, the frozen pin is {EXPECTED_PROTOCOL!r}"
            )
        if (
            item.tool_contract_policy
            and item.source.split("#")[0] in ARM_POLICY_EVIDENCE_PATHS
            and item.tool_contract_policy != EXPECTED_TOOL_CONTRACT_POLICY[item.arm]
        ):
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {item.source} records arm {item.arm!r} "
                f"tool_contract_policy {item.tool_contract_policy!r}, the frozen pin "
                f"is {EXPECTED_TOOL_CONTRACT_POLICY[item.arm]!r}"
            )

    for arm in ARM_ORDER:
        if arm not in seen_arms:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: no committed artifact states the identity "
                f"of arm {arm!r}"
            )
    return failures


# --------------------------------------------------------------------------
# The full offline preflight
# --------------------------------------------------------------------------


def offline_preflight() -> list[str]:
    """Every assertion the driver makes BEFORE it may touch a provider.

    Contacts nothing.  Returns an empty list when the protocol is intact; every
    entry is prefixed with the taxonomy class it belongs to.
    """

    return [
        *check_plan_sidecar(),
        *check_frozen_inputs(),
        *check_instrument_pins(),
        *check_frozen_historical_inputs(),
        *check_seed_provenance(),
        *check_model_pins(),
        *check_rc4_benchmark_untouched(),
        *check_harness_self_check(),
    ]


def check_harness_self_check() -> list[str]:
    """The rc4 harness's own invariants must hold before it classifies anything."""

    return [
        f"INSTRUMENT_DEFECT: {failure}"
        for failure in harness._self_check()  # noqa: SLF001 - the harness's own gate
    ]


def check_rc4_benchmark_untouched() -> list[str]:
    """Every rc4 scientific byte must be exactly what the Phase-O freeze recorded.

    Read from ``benchmark/pilot-v7-rc4/freeze-record.json`` itself, so the check
    is against the accepted freeze rather than against a value Phase P retyped.
    """

    failures: list[str] = []
    record = _load_json("benchmark/pilot-v7-rc4/freeze-record.json")
    if record is None:
        return [
            "FROZEN_ARTIFACT_MISMATCH: benchmark/pilot-v7-rc4/freeze-record.json "
            "does not exist"
        ]
    for key, relative in (
        ("manifest_sha256", "benchmark/pilot-v7-rc4/manifest.json"),
        ("provenance_sha256", "benchmark/pilot-v7-rc4/provenance.json"),
        (
            "qualification_contract_sha256",
            "benchmark/pilot-v7-rc4/qualification-contract.json",
        ),
        ("audit_sha256", "benchmark/pilot-v7-rc4/AUDIT.md"),
    ):
        recorded = str(record.get(key) or "")
        actual = sha256_file(relative)
        if recorded != actual:
            failures.append(
                f"FROZEN_ARTIFACT_MISMATCH: {relative} recorded={recorded} "
                f"actual={actual}"
            )

    cases = record.get("case_sha256")
    if not isinstance(cases, Mapping):
        failures.append(
            "FROZEN_ARTIFACT_MISMATCH: the rc4 freeze record pins no case bytes"
        )
    else:
        manifest = _load_json("benchmark/pilot-v7-rc4/manifest.json")
        paths: dict[str, str] = {}
        if manifest is not None:
            entries = manifest.get("cases")
            if isinstance(entries, Sequence) and not isinstance(entries, (str, bytes)):
                for entry in entries:
                    if isinstance(entry, Mapping):
                        paths[str(entry.get("task_id"))] = str(entry.get("path"))
        for task_id, recorded_hash in sorted(cases.items()):
            relative_path = paths.get(task_id)
            if not relative_path:
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: the rc4 manifest declares no path for "
                    f"pinned case {task_id}"
                )
                continue
            target = f"benchmark/{relative_path}"
            if not (PROJECT_ROOT / target).is_file():
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: rc4 case file {target} does not exist"
                )
                continue
            actual_case = sha256_file(target)
            if actual_case != str(recorded_hash):
                failures.append(
                    f"FROZEN_ARTIFACT_MISMATCH: rc4 case {task_id} ({target}) "
                    f"recorded={recorded_hash} actual={actual_case}"
                )

    for key, expected in (
        ("qualification_status", "UNQUALIFIED"),
        ("release_status", "release-candidate"),
        ("design_mode", "OFFLINE-DESIGNED"),
        ("phase_l_seeds_status", PHASE_L_SEED_STATUS),
    ):
        if record.get(key) != expected:
            failures.append(
                f"PROTOCOL_DEVIATION: the rc4 freeze record declares {key}="
                f"{record.get(key)!r}, Phase P requires {expected!r}"
            )
    for key in ("is_final", "model_inference_performed", "seed_triple_selected"):
        if record.get(key) is not False:
            failures.append(
                f"PROTOCOL_DEVIATION: the rc4 freeze record declares {key}="
                f"{record.get(key)!r}; Phase P freezes an UNQUALIFIED, non-final "
                "release candidate"
            )
    return failures


# --------------------------------------------------------------------------
# The frozen 102-cell schedule
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoadedBenchmark:
    """The frozen rc4 selection, and the fault declarations read from it.

    ``scripted_faults`` is the DECLARATION side of the K.2 proof only.  It is
    handed to the stop controller, which compares it against runtime-observed
    provenance the driver transported; it is never used to produce an
    observation.
    """

    manifest_sha256: str
    task_ids: tuple[str, ...]
    scripted_faults: Mapping[str, tuple[Any, ...]]


def load_benchmark(manifest_path: Path | None = None) -> LoadedBenchmark:
    """Load the frozen rc4 benchmark and refuse anything that is not it."""

    from iqa_soa.benchmark import load_frozen_pilot  # noqa: PLC0415 - import shim

    path = manifest_path or (
        PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "manifest.json"
    )
    frozen_pilot = load_frozen_pilot(path)
    if frozen_pilot.benchmark_version != BENCHMARK_VERSION:
        raise ProtocolError(
            f"expected {BENCHMARK_VERSION}, got {frozen_pilot.benchmark_version}"
        )
    if len(frozen_pilot.cases) != TASK_COUNT:
        raise ProtocolError(
            f"{BENCHMARK_VERSION} must contain exactly {TASK_COUNT} tasks, found "
            f"{len(frozen_pilot.cases)}"
        )
    return LoadedBenchmark(
        manifest_sha256=frozen_pilot.manifest_sha256,
        task_ids=tuple(frozen_pilot.selected_task_ids),
        scripted_faults=harness.scripted_faults_from_cases(list(frozen_pilot.cases)),
    )


def build_arms() -> tuple[Any, ...]:
    """The two frozen arms, in frozen order, each carrying its model identity."""

    return tuple(
        harness.ArmSpec(
            arm=arm,
            model=EXPECTED_MODEL[arm],
            model_digest=EXPECTED_MODEL_DIGEST[EXPECTED_MODEL[arm]],
        )
        for arm in ARM_ORDER
    )


def build_phase_p_schedule(benchmark: LoadedBenchmark) -> list[Any]:
    """The frozen arm-major / task-major / seed-minor 102-cell schedule.

    Task order is the frozen manifest's own ``selected_task_ids`` order, seed
    order is the frozen Phase-P order, and arm order is :data:`ARM_ORDER`.  The
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
    return list(schedule)


def cell_slug(cell: Any) -> str:
    """A stable, filesystem-safe directory name for one cell's raw evidence."""

    return f"{cell.index:03d}-{cell.arm}-{cell.task_id}-{cell.seed}"


def schedule_digest(schedule: Sequence[Any]) -> str:
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


# --------------------------------------------------------------------------
# The results namespace and the raw-evidence path contract
# --------------------------------------------------------------------------

#: The Phase-P results namespace.  NOTHING creates it during Phase P: the driver
#: creates it only after BOTH human gates and every execution precondition are
#: satisfied, and a pre-existing raw record is a PROTOCOL_DEVIATION.
RESULTS_NAMESPACE = "results/phaseP-rc4-qualification"

RAW_RECORD_NAME = "phaseP-runs.jsonl"
RUN_MANIFEST_NAME = "phaseP-run-manifest.json"
PARTIAL_MANIFEST_NAME = "phaseP-partial-manifest.json"
ANALYSIS_NAME = "phaseP-analysis.json"

#: Where a cell's own experiment directory lives, beneath the Phase-P output
#: root.  One cell is one ``ExperimentRunner`` invocation, so each gets its own
#: directory and no cell can overwrite, blend into or resume another.
CELLS_SUBDIR: tuple[str, ...] = ("raw", "cells")

#: THE PATH CONTRACT, in one sentence, binding on the driver and the analyzer.
CELL_EXPERIMENT_DIR_CONTRACT = (
    "row['cell_experiment_dir'] is the ExperimentRunner experiment directory "
    "expressed RELATIVE TO THE PHASE-P OUTPUT ROOT, as a POSIX path. The "
    "analyzer resolves a cell's evidence trace as "
    "<output_root>/<cell_experiment_dir>/<row['trace_path']> and never any "
    "other way. A row that declares no experiment directory, declares no "
    "trace, or whose resolved trace is absent or unreadable is LOST EVIDENCE "
    "and is a blocking INSTRUMENT_DEFECT -- never an empty proposal list."
)


def cells_root(output_root: Path) -> Path:
    """The directory that holds every cell's own experiment directory."""

    return output_root.joinpath(*CELLS_SUBDIR)


def cell_evidence_root(output_root: Path, cell: Any) -> Path:
    """The ONLY directory a given frozen cell's evidence may live beneath."""

    return cells_root(output_root) / cell_slug(cell)


def cell_experiment_dir_value(experiment_dir: Path, output_root: Path) -> str:
    """Serialize an experiment directory under the contract above.

    Raises rather than guessing when the directory is not under the output root,
    because a silently wrong relative path is exactly the defect Phase L-A'.1
    found and this function exists to remove.
    """

    try:
        relative = experiment_dir.resolve().relative_to(output_root.resolve())
    except ValueError as exc:
        raise ProtocolError(
            f"the cell experiment directory {experiment_dir} is not beneath the "
            f"Phase-P output root {output_root}; {CELL_EXPERIMENT_DIR_CONTRACT}"
        ) from exc
    return relative.as_posix()


# --------------------------------------------------------------------------
# The Phase-P contract-drift classifier, INSIDE the stop controller
# --------------------------------------------------------------------------

#: Bound once, at import, so :func:`classify_row` can never recurse into itself
#: when the module global is rebound for the duration of a ``record`` call.
_RC4_CLASSIFY_ROW_DETAILED = harness.classify_row_detailed

#: Row fields whose recorded value must equal the frozen pin, and the pin.  A
#: value of ``None`` or a missing key is a mismatch, never agreement: an
#: unstamped row cannot be proved to have been produced under the frozen
#: instrument.
ROW_CONTRACT_PINS: Mapping[str, Any] = {
    "instrument_version": EXPECTED_INSTRUMENT_VERSION,
    "raw_schema_version": EXPECTED_RAW_SCHEMA_VERSION,
    "native_tool_adapter_version": EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
    "tool_argument_contract_version": EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
    "tool_argument_contract_digest": EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
    "benchmark_version": BENCHMARK_VERSION,
    "experiment_kind": EXPERIMENT_KIND,
}


def contract_drift(row: Mapping[str, Any], cell: Any | None = None) -> list[str]:
    """Every frozen contract pin the row fails to carry, or carries differently.

    This is the machine-enforced form of the phase brief's rule that the driver
    must refuse before inference if any frozen tool contract, adapter version,
    model-visible schema, model/provider identity, instrument version or raw
    schema version has drifted -- applied per row as well, because a drift can
    also appear mid-run.
    """

    mismatches: list[str] = []
    for field_name, expected in sorted(ROW_CONTRACT_PINS.items()):
        if field_name not in row or row.get(field_name) is None:
            mismatches.append(
                f"{field_name} is missing from the returned row; the frozen "
                f"Phase-P pin is {expected!r} and absence is never agreement"
            )
            continue
        actual = row[field_name]
        if field_name == "raw_schema_version":
            try:
                actual = int(actual)
            except (TypeError, ValueError):
                mismatches.append(f"raw_schema_version {actual!r} is not an integer")
                continue
        if actual != expected:
            mismatches.append(
                f"{field_name} is {actual!r}, the frozen Phase-P pin is {expected!r}"
            )
    if cell is not None:
        expected_policy = EXPECTED_TOOL_CONTRACT_POLICY.get(str(cell.arm), "")
        actual_policy = row.get("tool_contract_policy")
        if actual_policy is None:
            mismatches.append(
                "tool_contract_policy is missing from the returned row; arm "
                f"{cell.arm!r} is frozen against {expected_policy!r}"
            )
        elif str(actual_policy) != expected_policy:
            mismatches.append(
                f"tool_contract_policy is {actual_policy!r} for arm {cell.arm!r}, "
                f"the frozen Phase-P pin is {expected_policy!r}"
            )
    return mismatches


def classify_row_detailed(
    row: Mapping[str, Any],
    cell: Any | None = None,
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Classify one Phase-P cell: contract drift FIRST, then the rc4 rules.

    The drift check runs ahead of every scientific branch for the same reason
    the Phase-O-R1 schema-5 evidence gate does: a row produced by an instrument
    that is not the frozen one is not a measurement of the frozen experiment,
    and scoring it would turn drift into a finding about a model.
    """

    drift = contract_drift(row, cell)
    if drift:
        return (
            harness.FROZEN_ARTIFACT_MISMATCH,
            harness.IMMEDIATE_STOP,
            {
                "events": [],
                "decided_by": None,
                "reasons": [
                    "the row was not produced under the frozen Phase-P instrument, "
                    "adapter and argument contract",
                    *drift,
                ],
            },
        )
    return _RC4_CLASSIFY_ROW_DETAILED(row, cell, scripted_faults=scripted_faults)


def classify_row(
    row: Mapping[str, Any],
    cell: Any | None = None,
    *,
    scripted_faults: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[str, str]:
    """``(failure_class, disposition)`` for one Phase-P cell."""

    return classify_row_detailed(row, cell, scripted_faults=scripted_faults)[:2]


class StopController(harness.StopController):
    """The rc4 stop controller, driving the Phase-P classifier.

    Subclassed rather than copied.  ``qualification_harness_v2.StopController``
    installs ``qualification_harness_v2.classify_row`` -- resolved as a MODULE
    GLOBAL at call time -- into the frozen controller for exactly the duration of
    one ``record``.  Rebinding that global here therefore substitutes the Phase-P
    classifier through the seam the rc4 harness already publishes, without
    copying a line of schedule logic: the duplicate-cell check, the schedule-index
    check, the identity binding, the hold accounting, the no-retry rule and the
    partial manifest are all inherited unchanged.

    The substitution is confined to this method and restored in ``finally``, so a
    caller importing either harness directly is never affected.
    """

    def record(self, cell: Any, row: Mapping[str, Any]) -> str:
        original = harness.classify_row
        harness.classify_row = classify_row
        try:
            return str(super().record(cell, row))
        finally:
            harness.classify_row = original


# --------------------------------------------------------------------------
# Machine-readable summary
# --------------------------------------------------------------------------


def protocol_summary() -> dict[str, Any]:
    """A machine-readable statement of the frozen protocol.  Runs no model."""

    benchmark = load_benchmark()
    schedule = build_phase_p_schedule(benchmark)
    return {
        "phase": PHASE,
        "canonical_base_commit": CANONICAL_BASE_COMMIT,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_manifest_sha256": benchmark.manifest_sha256,
        "benchmark_qualification_status": "UNQUALIFIED",
        "benchmark_release_status": "release-candidate",
        "qa_mode": QA_MODE,
        "out_of_scope_treatments": list(OUT_OF_SCOPE_TREATMENTS),
        "task_count": TASK_COUNT,
        "task_order": list(benchmark.task_ids),
        "arm_order": list(ARM_ORDER),
        "seeds": list(SEEDS),
        "seed_selection_status": SEED_SELECTION_STATUS,
        "phase_l_seeds_status": PHASE_L_SEED_STATUS,
        "planned_cells": len(schedule),
        "schedule_ordering": "arm-major -> task-major -> seed-minor",
        "schedule_digest": schedule_digest(schedule),
        "instrument_version": EXPECTED_INSTRUMENT_VERSION,
        "raw_schema_version": EXPECTED_RAW_SCHEMA_VERSION,
        "tool_argument_contract_version": EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION,
        "tool_argument_contract_digest": EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST,
        "native_tool_adapter_version": EXPECTED_NATIVE_TOOL_ADAPTER_VERSION,
        "harness_version": HARNESS_VERSION,
        "scoring_vocabulary_version": SCORING_VOCABULARY_VERSION,
        "expected_model": dict(EXPECTED_MODEL),
        "expected_model_digest": dict(EXPECTED_MODEL_DIGEST),
        "expected_runtime_version": EXPECTED_RUNTIME_VERSION,
        "expected_tool_contract_policy": dict(EXPECTED_TOOL_CONTRACT_POLICY),
        "expected_protocol": EXPECTED_PROTOCOL,
        "results_namespace": RESULTS_NAMESPACE,
        "human_gate": {
            "flag": HUMAN_GATE_FLAG,
            "env": HUMAN_GATE_ENV,
            "value": HUMAN_GATE_VALUE,
            "both_required": True,
        },
        "infrastructure_retry_limit": INFRASTRUCTURE_RETRY_LIMIT,
        "no_retry_policy": dict(NO_RETRY_POLICY),
        "execution_authorized": False,
        "model_inference_performed": False,
        "authorizes_confirmatory_execution": False,
        "reports_no_qa_treatment_effect": True,
        "reports_no_model_ranking": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Report the frozen protocol and the offline preflight verdict."""

    import argparse  # noqa: PLC0415 - CLI only

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
        f"Phase-P frozen protocol: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE"
    )
    return EXIT_OK if not failures else EXIT_PREFLIGHT_STOP


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARM_ORDER",
    "ARM_PROVIDER_SLOT",
    "BENCHMARK_VERSION",
    "CANONICAL_BASE_COMMIT",
    "CELL_EXPERIMENT_DIR_CONTRACT",
    "CREDENTIAL_ENV",
    "DRIVER_STAMPED_IDENTITY_FIELDS",
    "DRIVER_STAMPED_SCHEDULE_FIELDS",
    "EXPECTED_INSTRUMENT_VERSION",
    "EXPECTED_MODEL",
    "EXPECTED_MODEL_DIGEST",
    "EXPECTED_NATIVE_TOOL_ADAPTER_VERSION",
    "EXPECTED_PROTOCOL",
    "EXPECTED_RAW_SCHEMA_VERSION",
    "EXPECTED_RUNTIME_VERSION",
    "EXPECTED_TOOL_ARGUMENT_CONTRACT_DIGEST",
    "EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION",
    "EXPECTED_TOOL_CONTRACT_POLICY",
    "EXPERIMENT_KIND",
    "EXIT_CREDENTIAL_STOP",
    "EXIT_ENVIRONMENT_HOLD",
    "EXIT_GATE_CLOSED",
    "EXIT_OK",
    "EXIT_PREFLIGHT_STOP",
    "EXIT_SCHEDULE_STOPPED",
    "EXIT_VERDICT_HOLD",
    "FORBIDDEN_HISTORICAL_SEEDS",
    "FROZEN_INPUTS_RELATIVE",
    "FROZEN_INPUT_PATHS",
    "FROZEN_TREE_ROOTS",
    "HUMAN_GATE_ENV",
    "HUMAN_GATE_FLAG",
    "HUMAN_GATE_VALUE",
    "INFRASTRUCTURE_RETRY_LIMIT",
    "LoadedBenchmark",
    "MANIFEST_TRANSPORTED_FIELDS",
    "OLLAMA_BASE_URL",
    "PHASE_L_SEEDS",
    "PHASE_L_SEED_STATUS",
    "PHASE_P_ROW_FIELDS",
    "PLANNED_CELLS",
    "PLAN_RELATIVE",
    "PROSPECTIVE_FAULT_CLASSIFICATION",
    "PROJECT_ROOT",
    "ProtocolError",
    "QA_MODE",
    "RAW_RECORD_NAME",
    "RESULTS_NAMESPACE",
    "ROW_CONTRACT_PINS",
    "RUNNER_EMITTED_IDENTITY_FIELDS",
    "RUN_MANIFEST_CLASSIFICATION_FIELDS",
    "RUN_MANIFEST_NAME",
    "PARTIAL_MANIFEST_NAME",
    "ANALYSIS_NAME",
    "SEEDS",
    "SEED_RECORD_RELATIVE",
    "SEED_SELECTION_STATUS",
    "StopController",
    "TASK_COUNT",
    "TRACE_IDENTITY_FIELDS",
    "PinAssertion",
    "build_arms",
    "build_phase_p_schedule",
    "cell_evidence_root",
    "cell_experiment_dir_value",
    "cell_slug",
    "cells_root",
    "check_frozen_historical_inputs",
    "check_frozen_inputs",
    "check_instrument_pins",
    "check_model_pins",
    "check_plan_sidecar",
    "check_rc4_benchmark_untouched",
    "check_seed_provenance",
    "classify_row",
    "classify_row_detailed",
    "compute_frozen_inputs",
    "contained_child",
    "contract_drift",
    "load_benchmark",
    "load_frozen_inputs",
    "model_pin_evidence",
    "offline_preflight",
    "protocol_summary",
    "schedule_digest",
    "sha256_file",
    "tree_digest",
]
