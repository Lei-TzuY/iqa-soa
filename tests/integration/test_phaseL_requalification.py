"""Phase L-A: offline tests for the rc3 QA-OFF requalification protocol freeze.

Phase L-A set out to freeze an execution protocol.  It did not, because the
design surfaced an unresolved harness defect: the Phase-K.2 observed-fault
provenance contract cannot be satisfied from anything the canonical instrument
persists for a QA-OFF cell.  Section 15 of the phase brief requires design
finalization to stop on exactly that discovery, so no Phase-L execution config,
driver or analyzer is frozen and this module tests none.

What it does test is everything that is real and defect-independent:

* the three prospective Phase-L seeds are a deterministic function of the
  canonical base commit, are reproducible from that commit alone, and collide
  neither with each other nor with any historically used seed;
* the 17 x 2 x 3 QA-OFF matrix the future protocol would drive composes to
  exactly 102 cells with unique run keys, in the frozen arm-major/task-major/
  seed-minor order, against the real frozen rc3 manifest;
* the Phase-K stop semantics behave as the protocol requires: a wrong or missing
  identity field stops immediately, a defect in the last cell of arm 1 prevents
  arm 2 from starting, and the partial manifest preserves every completed row;
* THE DEFECT ITSELF, pinned as a regression test, so that the HOLD cannot be
  quietly lost and so that whoever repairs the instrument will see these tests
  fail and must update them deliberately;
* historical immutability: Phase L-A moved no frozen byte.

Every test is synthetic and offline.  No model is run, no provider is contacted,
and no environment probe is performed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.experiment.treatments import treatment_for  # noqa: E402

BENCHMARK_VERSION = "pilot-v7-rc3"
RC3_ROOT = PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION
MANIFEST_PATH = RC3_ROOT / "manifest.json"
CANONICAL_BASE_COMMIT = "beafa5d170659997790e1c3e79086ea05548c094"
#: The commit that archived the Phase-L-A HOLD (PR #8), and the canonical
#: parent of the Phase-M instrument repair.
PHASE_L_A_COMMIT = "eace204d4c27a9ca48d3c0a660832f640b7a900b"
REPORT_PATH = PROJECT_ROOT / "docs" / "phaseL_rc3_requalification_freeze_report.md"
SEED_RECORD_PATH = PROJECT_ROOT / "docs" / "phaseL_rc3_prospective_seed_derivation.json"

#: The exact seeds the derivation yields from the canonical base commit.  They
#: are written out here so a silent change to the derivation is a test failure
#: rather than a quietly different experiment.
EXPECTED_PHASE_L_SEEDS: tuple[int, int, int] = (929260329, 1281385038, 978843421)
HISTORICAL_SEEDS: tuple[int, ...] = (1729, 2718, 3141, 5772, 8119)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


harness = _load_module("phaseL_harness", SCRIPTS_ROOT / "qualification_harness.py")
seedgen = _load_module("phaseL_seedgen", SCRIPTS_ROOT / "phaseL_seed_derivation.py")
reachability = _load_module(
    "phaseL_reachability",
    SCRIPTS_ROOT / "phaseL_fault_provenance_reachability_probe.py",
)


@pytest.fixture(scope="module")
def frozen_rc3() -> Any:
    return load_frozen_pilot(MANIFEST_PATH)


@pytest.fixture(scope="module")
def probe_finding() -> dict[str, Any]:
    """The reachability probe is expensive; run it once for the whole module."""

    return reachability.probe()


# --------------------------------------------------------------------------
# 1. Prospective seed derivation
# --------------------------------------------------------------------------


def test_seed_derivation_is_pinned_to_the_canonical_base_commit() -> None:
    assert seedgen.CANONICAL_BASE_COMMIT == CANONICAL_BASE_COMMIT
    assert seedgen.PURPOSE == "phase-l|pilot-v7-rc3|qa-off-requalification"
    assert seedgen.SEED_COUNT == 3


def test_seed_derivation_yields_the_expected_triple() -> None:
    derived = seedgen.derive_seeds()
    assert tuple(item.seed for item in derived) == EXPECTED_PHASE_L_SEEDS


def test_seed_derivation_matches_the_documented_formula() -> None:
    """Recompute the formula independently rather than trusting the module."""

    for ordinal in (1, 2, 3):
        material = (
            f"{CANONICAL_BASE_COMMIT}"
            "|phase-l|pilot-v7-rc3|qa-off-requalification|seed-"
            f"{ordinal}"
        )
        digest = hashlib.sha256(material.encode("utf-8")).digest()
        expected = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
        derived = seedgen.derive_seed(ordinal)
        assert derived.material == material
        assert derived.digest == digest.hex()
        assert derived.seed == expected


def test_seed_derivation_is_deterministic() -> None:
    assert seedgen.derive_seeds() == seedgen.derive_seeds()


def test_seeds_do_not_overlap_any_historical_qualification_seed() -> None:
    seeds = set(EXPECTED_PHASE_L_SEEDS)
    assert seeds.isdisjoint(HISTORICAL_SEEDS)
    # The Phase-F / Phase-I triple specifically.
    assert seeds.isdisjoint({1729, 2718, 3141})


def test_seed_collision_checks_are_clean_and_do_not_self_repair() -> None:
    report = seedgen.collision_report(seedgen.derive_seeds())
    assert report["collision_free"] is True
    assert report["zero_valued_seeds"] == []
    assert report["internal_duplicate_seeds"] == []
    assert report["historical_seed_overlap"] == []
    assert list(HISTORICAL_SEEDS) == report["historical_seeds_checked_against"]


def test_seed_collision_is_reported_rather_than_repaired() -> None:
    """A colliding derivation must surface, not be silently replaced."""

    colliding = (
        seedgen.DerivedSeed(1, "m", "d", "ffff", 1729),
        seedgen.DerivedSeed(2, "m", "d", "ffff", 1729),
        seedgen.DerivedSeed(3, "m", "d", "0000", 0),
    )
    report = seedgen.collision_report(colliding)
    assert report["collision_free"] is False
    assert report["zero_valued_seeds"] == [0]
    assert report["internal_duplicate_seeds"] == [1729]
    assert report["historical_seed_overlap"] == [1729]


def test_seed_record_artifact_matches_the_live_derivation() -> None:
    assert SEED_RECORD_PATH.is_file(), "the prospective seed record must be committed"
    record = json.loads(SEED_RECORD_PATH.read_text(encoding="utf-8"))
    assert record["canonical_base_commit"] == CANONICAL_BASE_COMMIT
    assert record["seeds"] == list(EXPECTED_PHASE_L_SEEDS)
    assert record["model_inference_performed"] is False
    assert record["collision_checks"]["collision_free"] is True
    assert record == seedgen.build_record()


def test_seed_derivation_cli_exits_zero_and_writes_a_stable_record(
    tmp_path: Path,
) -> None:
    out = tmp_path / "record.json"
    assert seedgen.main(["--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == seedgen.build_record()


# --------------------------------------------------------------------------
# 2. The 102-cell matrix the future protocol would drive
# --------------------------------------------------------------------------


def _phase_l_schedule(frozen_rc3: Any) -> list[Any]:
    arms = [
        harness.ArmSpec("qwen", "qwen3.5:27b", "a" * 64),
        harness.ArmSpec("mistral", "mistral-small3.2:24b", "b" * 64),
    ]
    return harness.build_schedule(
        arms,
        list(frozen_rc3.selected_task_ids),
        list(EXPECTED_PHASE_L_SEEDS),
        qa_mode="off",
        benchmark_manifest_sha256=frozen_rc3.manifest_sha256,
    )


def test_rc3_is_a_release_candidate_with_seventeen_tasks(frozen_rc3: Any) -> None:
    assert frozen_rc3.benchmark_version == BENCHMARK_VERSION
    assert len(frozen_rc3.selected_task_ids) == 17
    provenance = json.loads((RC3_ROOT / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["release_status"] == "release-candidate"
    assert provenance["preregistration_file"] is None
    assert provenance["model_inference_performed"] is False


def test_matrix_is_exactly_seventeen_by_two_by_three(frozen_rc3: Any) -> None:
    schedule = _phase_l_schedule(frozen_rc3)
    assert len(schedule) == 17 * 2 * 3 == 102
    assert {cell.qa_mode for cell in schedule} == {"off"}
    assert {cell.seed for cell in schedule} == set(EXPECTED_PHASE_L_SEEDS)
    assert {cell.benchmark_manifest_sha256 for cell in schedule} == {
        frozen_rc3.manifest_sha256
    }


def test_matrix_ordering_is_arm_major_task_major_seed_minor(frozen_rc3: Any) -> None:
    schedule = _phase_l_schedule(frozen_rc3)
    assert [cell.index for cell in schedule] == list(range(102))
    # Arm-major: the first 51 cells are one arm, the last 51 the other.
    assert {cell.arm for cell in schedule[:51]} == {"qwen"}
    assert {cell.arm for cell in schedule[51:]} == {"mistral"}
    # Seed-minor: the three seeds cycle fastest, in derivation order.
    assert [cell.seed for cell in schedule[:3]] == list(EXPECTED_PHASE_L_SEEDS)
    # Task-major: each task's three seeds are contiguous.
    assert [cell.task_id for cell in schedule[:3]] == [schedule[0].task_id] * 3


def test_every_cell_binds_the_full_identity_set(frozen_rc3: Any) -> None:
    required = set(harness.REQUIRED_IDENTITY_FIELDS)
    assert required == {
        "task_id",
        "seed",
        "model",
        "model_digest",
        "qa_mode",
        "benchmark_manifest_sha256",
        "run_key",
    }
    for cell in _phase_l_schedule(frozen_rc3):
        expectation = cell.expectation()
        assert required <= set(expectation)
        assert all(expectation[name] not in (None, "") for name in required)


def test_run_keys_are_unique_across_the_whole_matrix(frozen_rc3: Any) -> None:
    schedule = _phase_l_schedule(frozen_rc3)
    keys = [cell.run_key for cell in schedule]
    assert len(set(keys)) == len(keys) == 102


def test_run_key_separates_arms_that_share_task_and_seed(frozen_rc3: Any) -> None:
    """Two arms differ in model and digest, so their run keys must differ."""

    schedule = _phase_l_schedule(frozen_rc3)
    by_task_seed: dict[tuple[str, int], list[Any]] = {}
    for cell in schedule:
        by_task_seed.setdefault((cell.task_id, cell.seed), []).append(cell)
    for cells in by_task_seed.values():
        assert len(cells) == 2
        assert cells[0].run_key != cells[1].run_key


# --------------------------------------------------------------------------
# 3. Stop semantics the future driver must inherit
# --------------------------------------------------------------------------


def _clean_row(cell: Any, **overrides: Any) -> dict[str, Any]:
    row = {
        "run_id": f"run-{cell.index}",
        "task_id": cell.task_id,
        "seed": cell.seed,
        "model": cell.model,
        "model_digest": cell.model_digest,
        "qa_mode": cell.qa_mode,
        "benchmark_manifest_sha256": cell.benchmark_manifest_sha256,
        "run_key": cell.run_key,
        "provider_attempt_count": 1,
        "failure_class": None,
    }
    row.update(overrides)
    return row


def test_a_clean_matrix_completes(frozen_rc3: Any) -> None:
    schedule = _phase_l_schedule(frozen_rc3)
    result = harness.run_schedule(schedule, _clean_row)
    assert result.terminal_status == harness.TERMINAL_STATUS_OK
    assert result.exit_code == 0
    assert result.executed == 102
    assert result.not_started == []


@pytest.mark.parametrize(
    "field, value",
    [
        ("model_digest", "0" * 64),
        ("seed", 1729),
        ("qa_mode", "full"),
        ("task_id", "BEN-002"),
        ("benchmark_manifest_sha256", "f" * 64),
        ("run_key", "not-the-frozen-run-key"),
    ],
)
def test_a_wrong_identity_field_stops_immediately(
    frozen_rc3: Any, field: str, value: Any
) -> None:
    schedule = _phase_l_schedule(frozen_rc3)

    def execute(cell: Any) -> dict[str, Any]:
        if cell.index == 5:
            return _clean_row(cell, **{field: value})
        return _clean_row(cell)

    result = harness.run_schedule(schedule, execute)
    assert result.terminal_status == harness.TERMINAL_STATUS_STOPPED
    assert result.stop_failure_class == harness.FROZEN_ARTIFACT_MISMATCH
    assert result.executed == 6
    assert len(result.not_started) == 96


@pytest.mark.parametrize("field", sorted(harness.REQUIRED_IDENTITY_FIELDS))
def test_a_missing_identity_field_stops_immediately(
    frozen_rc3: Any, field: str
) -> None:
    schedule = _phase_l_schedule(frozen_rc3)

    def execute(cell: Any) -> dict[str, Any]:
        row = _clean_row(cell)
        if cell.index == 2:
            row.pop(field)
        return row

    result = harness.run_schedule(schedule, execute)
    assert result.terminal_status == harness.TERMINAL_STATUS_STOPPED
    assert result.stop_failure_class == harness.FROZEN_ARTIFACT_MISMATCH
    assert result.executed == 3


def test_a_defect_in_the_last_cell_of_arm_one_prevents_arm_two_starting(
    frozen_rc3: Any,
) -> None:
    """The exact Phase-I failure pattern, recreated synthetically.

    Phase I discovered a defect after the first arm completed and launched the
    second arm 28.4 seconds later anyway.  Under the Phase-K controller the
    second arm must never begin.
    """

    schedule = _phase_l_schedule(frozen_rc3)
    last_of_arm_one = 50
    assert schedule[last_of_arm_one].arm == "qwen"
    assert schedule[last_of_arm_one + 1].arm == "mistral"
    started: list[str] = []

    def execute(cell: Any) -> dict[str, Any]:
        started.append(cell.arm)
        if cell.index == last_of_arm_one:
            return _clean_row(cell, tool_contract_regression_detected=True)
        return _clean_row(cell)

    result = harness.run_schedule(schedule, execute)
    assert result.terminal_status == harness.TERMINAL_STATUS_STOPPED
    assert result.stop_failure_class == harness.INSTRUMENT_DEFECT
    assert result.executed == 51
    assert "mistral" not in started, "arm 2 must not start after an immediate stop"
    assert len(result.not_started) == 51


def test_a_stopped_schedule_preserves_every_completed_row(frozen_rc3: Any) -> None:
    schedule = _phase_l_schedule(frozen_rc3)

    def execute(cell: Any) -> dict[str, Any]:
        if cell.index == 30:
            return _clean_row(cell, tool_contract_regression_detected=True)
        return _clean_row(cell)

    controller = harness.StopController(schedule)
    for cell in controller.cells():
        controller.record(cell, execute(cell))
    result = controller.result()
    assert result.executed == 31
    assert len(result.completed_rows) == 31
    assert [row["run_id"] for row in result.completed_rows] == [
        f"run-{index}" for index in range(31)
    ]


def test_partial_manifest_records_the_stop_and_the_cells_not_started(
    frozen_rc3: Any, tmp_path: Path
) -> None:
    schedule = _phase_l_schedule(frozen_rc3)

    def execute(cell: Any) -> dict[str, Any]:
        if cell.index == 12:
            return _clean_row(cell, tool_contract_regression_detected=True)
        return _clean_row(cell)

    path = tmp_path / "partial-manifest.json"
    result = harness.run_schedule(schedule, execute, partial_manifest_path=path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["stopped"] is True
    assert payload["planned_cells"] == 102
    assert payload["executed_cells"] == 13
    assert payload["stop_cell"] == schedule[12].key
    assert payload["stop_failure_class"] == harness.INSTRUMENT_DEFECT
    assert payload["stop_reason"]
    assert len(payload["cells_not_started"]) == 89
    assert len(payload["preserved_row_ids"]) == 13
    assert result.exit_code == 3


def test_a_duplicate_or_reordered_cell_is_a_protocol_deviation(
    frozen_rc3: Any,
) -> None:
    schedule = _phase_l_schedule(frozen_rc3)
    controller = harness.StopController(schedule)
    first = schedule[0]
    controller.record(first, _clean_row(first))
    assert controller.record(first, _clean_row(first)) == harness.PROTOCOL_DEVIATION
    assert controller.result().terminal_status == harness.TERMINAL_STATUS_STOPPED

    controller = harness.StopController(schedule)
    out_of_order = schedule[7]
    assert (
        controller.record(out_of_order, _clean_row(out_of_order))
        == harness.PROTOCOL_DEVIATION
    )


def test_the_controller_refuses_to_advance_after_a_stop(frozen_rc3: Any) -> None:
    schedule = _phase_l_schedule(frozen_rc3)
    controller = harness.StopController(schedule)
    cell = schedule[0]
    controller.record(cell, _clean_row(cell, tool_contract_regression_detected=True))
    with pytest.raises(harness.ScheduleViolation):
        controller.record(schedule[1], _clean_row(schedule[1]))


def test_invalidated_cells_cannot_be_reported_as_a_clean_completion(
    frozen_rc3: Any,
) -> None:
    schedule = _phase_l_schedule(frozen_rc3)

    def execute(cell: Any) -> dict[str, Any]:
        if cell.index == 4:
            return _clean_row(cell, failure_class="invalid_action_format")
        return _clean_row(cell)

    result = harness.run_schedule(schedule, execute)
    assert result.executed == 102
    assert result.terminal_status == harness.TERMINAL_STATUS_HOLD
    assert result.exit_code == 1
    assert result.invalidated_cells == [schedule[4].key]


def test_the_closed_taxonomy_and_its_dispositions_are_unchanged() -> None:
    """Phase L reuses the Phase-K taxonomy; it does not reopen or simplify it."""

    assert set(harness.FAILURE_CLASSES) == {
        "CELL_OK",
        "EXPECTED_SCRIPTED_FAULT",
        "MODEL_REFUSAL",
        "MODEL_PROTOCOL_INVALID",
        "MODEL_MODALITY_MISS",
        "BENCHMARK_PREREQUISITE_MISS",
        "CHALLENGE_ZERO_EXPOSURE",
        "UNEXPECTED_SANDBOX_FAILURE",
        "PROVIDER_INFRA_FAILURE",
        "INSTRUMENT_DEFECT",
        "FROZEN_ARTIFACT_MISMATCH",
        "PROTOCOL_DEVIATION",
    }
    assert harness.DISPOSITION["MODEL_PROTOCOL_INVALID"] == harness.CELL_INVALID_CONTINUE
    assert harness.DISPOSITION["UNEXPECTED_SANDBOX_FAILURE"] == harness.CELL_INVALID_AND_HOLD
    assert harness.DISPOSITION["CHALLENGE_ZERO_EXPOSURE"] == (
        harness.VERDICT_HOLD_AFTER_COMPLETION
    )
    for immediate in ("INSTRUMENT_DEFECT", "FROZEN_ARTIFACT_MISMATCH", "PROTOCOL_DEVIATION"):
        assert harness.DISPOSITION[immediate] == harness.IMMEDIATE_STOP
    with pytest.raises(ValueError):
        harness.disposition_for("SOMETHING_NEW")


def test_multi_call_overflow_is_model_side_not_an_instrument_defect() -> None:
    row = {
        "run_id": "x",
        "task_id": "BUD-015",
        "provider_attempt_count": 1,
        "failure_class": "multi_call_overflow",
    }
    assert harness.classify_row(row) == (
        harness.MODEL_PROTOCOL_INVALID,
        harness.CELL_INVALID_CONTINUE,
    )


# --------------------------------------------------------------------------
# 4. THE DEFECT. Pinned so the HOLD cannot be quietly lost.
# --------------------------------------------------------------------------


def test_qa_off_never_produces_detailed_evidence() -> None:
    """The root cause: detailed evidence is structurally off under QA OFF.

    ``Treatment.detailed_evidence`` returns False whenever ``qa_mode is OFF``,
    regardless of the evidence guard, so the QA-OFF evidence record can never
    carry ``tool_result`` and therefore can never carry the sandbox's stamped
    ``fault_mode``.  Phase L is QA OFF only.
    """

    assert treatment_for("off").detailed_evidence is False
    assert treatment_for("full").detailed_evidence is True


def test_observed_fault_provenance_is_reachable_under_qa_off(
    probe_finding: dict[str, Any]
) -> None:
    """REGRESSION PIN, UPDATED BY PHASE M AFTER THE INSTRUMENT WAS REPAIRED.

    BEFORE (Phase L-A, commit ``eace204d4c27a9ca48d3c0a660832f640b7a900b``,
    instrument ``2`` / raw schema ``3``): this asserted
    ``contract_reachable is False``, with ``observed_fault_mode`` and
    ``observed_fault_provenance`` unreachable and both fault tasks forced to
    ``CELL_INVALID_AND_HOLD``.  That finding was real, and the HOLD it produced is
    not retracted -- see ``docs/phaseL_rc3_requalification_freeze_report.md``,
    which Phase M leaves byte-identical.

    AFTER (Phase M, instrument ``3`` / raw schema ``4``, hash-pinned in
    ``docs/phaseM_instrument_revision.json``): the same probe, over the same
    frozen cases, through the same real ``ExperimentRunner`` and the same
    ``DeterministicStubProvider``, now recovers all four fields.

    The pin is not relaxed, it is INVERTED, and it is still a pin: if the four
    fields ever disappear again this test fails, because ``contract_reachable``
    goes back to ``False``.  ``detailed_evidence_under_qa_off`` is asserted here
    too, so the repair can never be "achieved" by turning QA OFF into a detailed
    treatment.
    """

    assert probe_finding["contract_reachable"] is True
    # The repair is raw protocol telemetry. QA OFF is still NOT detailed.
    assert probe_finding["detailed_evidence_under_qa_off"] is False
    assert probe_finding["fields_unreachable_from_persisted_qa_off_artifacts"] == []
    assert probe_finding["tasks_forced_to_hold_or_stop"] == []
    assert probe_finding["model_inference_performed"] is False


def test_both_rc3_fault_tasks_now_satisfy_the_k2_contract(
    probe_finding: dict[str, Any]
) -> None:
    """BEFORE: both tasks were ``UNEXPECTED_SANDBOX_FAILURE`` /
    ``CELL_INVALID_AND_HOLD`` because no provenance was persisted.
    AFTER: both prove their declared fault from runtime telemetry.

    The declaration is still never the source.  The probe stamps only the
    identity fields a driver legitimately owns (model, digest, seed, run key) and
    deliberately does NOT stamp fault provenance; every observed field on these
    rows was written by ``ExperimentRunner`` from the live ``GatewayOutcome``
    sequence.
    """

    findings = {item["task_id"]: item for item in probe_finding["findings"]}
    assert set(findings) == {"BUD-016", "FAULT-004"}
    for task_id, item in findings.items():
        assert item["expected_scripted_fault_matched"] is True, task_id
        assert item["harness_failure_class"] == harness.EXPECTED_SCRIPTED_FAULT, task_id
        assert item["harness_disposition"] == harness.CONTINUE, task_id
        assert item["match_refusal_reasons"] == [], task_id
        assert item["provenance_reachability"]["unrecoverable"] == [], task_id


def test_the_malformed_response_repair_is_raw_telemetry_not_evidence_detail(
    probe_finding: dict[str, Any]
) -> None:
    """The QA-OFF EVIDENCE TRACE is deliberately still unchanged.

    BEFORE, this asserted that the FAULT-004 fault was invisible everywhere: the
    persisted evidence event was byte-equal whether the declared fault fired or
    not, so nothing could be recovered.

    AFTER, the evidence event is STILL byte-equal, and that is the point.  Phase M
    did not turn QA OFF into a detailed treatment, did not enable the evidence
    guard and did not write the ``<<<MALFORMED_SIMULATED_RESPONSE>>>`` sentinel
    into the trace.  The differentiator moved into the RAW ROW, where the four
    ``observed_fault_*`` fields are stamped from the live runtime outcome.

    Stripping the declared fault from the case makes those fields go null, which
    is the crux: the observation tracks what the SANDBOX DID, so removing the
    fault removes the observation.  A declaration-derived field could not behave
    this way, because it would still have a declaration to copy.
    """

    observability = probe_finding["malformed_response_observability"]
    # The evidence trace is untouched: no detail, no sentinel, no tool output.
    assert observability["events_are_identical"] is True
    assert observability["malformed_sentinel_present_in_trace"] == {
        "fault_declared": False,
        "fault_stripped": False,
    }
    assert observability["row_fault_triggered"] == {
        "fault_declared": True,
        "fault_stripped": False,
    }
    # The raw row now carries the observation, and only when the fault fired.
    assert observability["rows_differ_in_observed_fault_provenance"] is True
    assert observability["row_observed_fault_provenance"]["fault_declared"] == {
        "observed_fault_tool": "api.call",
        "observed_fault_resource": "inventory-api/sku-4471",
        "observed_fault_mode": "malformed_response",
        "observed_fault_provenance": "gateway_outcome.executed_action",
    }
    assert all(
        value is None
        for value in observability["row_observed_fault_provenance"][
            "fault_stripped"
        ].values()
    )
    assert observability["post_repair_differentiator"]


def test_the_only_differentiator_is_a_forbidden_declared_source() -> None:
    """``fault_triggered`` is derived from the declaration, so it cannot serve.

    ``iqa_soa.metrics.collector._fault_triggered`` compares the observed
    ``fault_mode`` against ``case.fault.type``.  Phase K.2 names that class of
    source explicitly and refuses it, because an observation manufactured from
    the declaration proves nothing about the declaration.
    """

    assert "ground_truth" in harness.DECLARED_FAULT_PROVENANCE_SOURCES
    assert "benchmark_case.fault" in harness.DECLARED_FAULT_PROVENANCE_SOURCES
    row = {
        "run_id": "x",
        "task_id": "FAULT-004",
        "provider_attempt_count": 1,
        "fault_triggered": True,
        "observed_fault_tool": "api.call",
        "observed_fault_resource": "inventory-api/sku-4471",
        "observed_fault_mode": "malformed_response",
        "observed_fault_provenance": "benchmark_case.fault",
    }
    observed, reasons = harness.observed_fault_from_row(row)
    assert observed is None
    assert any("declaration" in reason for reason in reasons)


def test_the_runner_still_persists_neither_the_operation_log_nor_the_outcomes(
) -> None:
    """The MINIMALITY half of the repair, unchanged in force.

    BEFORE, this proved that neither ``SandboxState.operation_log`` nor
    ``AgentRun.outcomes`` was persisted -- which was the defect, since the four
    contract fields had no other source.

    AFTER, those two bulk structures are STILL not persisted, and that remains
    the correct behaviour.  Phase M added four derived scalar fields and a count,
    not the structures they were derived from: no operation log, no outcomes
    block, no ``ToolResult`` payload.  This test now guards the opposite failure
    mode from the one it was written for -- an over-broad repair that dumps
    runtime structures into the raw record.
    """

    runner_source = (SRC_ROOT / "iqa_soa" / "experiment" / "runner.py").read_text(
        encoding="utf-8"
    )
    # The operation log is still mentioned on exactly one line, and that line is
    # still the one that folds it into the irreversible state fingerprint.
    log_lines = [
        line.strip()
        for line in runner_source.splitlines()
        if "operation_log" in line
    ]
    assert log_lines == ['"operation_log": state.operation_log,']
    # No bulk runtime structure is serialized into the row.
    for forbidden in ('"gateway_outcomes"', '"outcomes":', '"tool_result"'):
        assert forbidden not in runner_source


def test_a_correctly_stamped_row_would_be_recognised(frozen_rc3: Any) -> None:
    """The contract is satisfiable in principle -- only the plumbing is missing.

    This is the counterfactual that makes the finding a REACHABILITY defect
    rather than a contract defect: a row carrying genuine runtime provenance is
    accepted, so repairing the instrument to persist it would close the gap.
    """

    declared = harness.scripted_faults_from_cases(list(frozen_rc3.cases))
    row = {
        "run_id": "x",
        "task_id": "BUD-016",
        "provider_attempt_count": 1,
        "failure_class": "tool_timeout",
        "error": "simulated tool timeout",
        "observed_fault_tool": "api.call",
        "observed_fault_resource": "platform-api/service-health",
        "observed_fault_mode": "timeout",
        "observed_fault_provenance": "sandbox.operation_log",
    }
    assert harness.classify_row(row, scripted_faults=declared) == (
        harness.EXPECTED_SCRIPTED_FAULT,
        harness.CONTINUE,
    )


# --------------------------------------------------------------------------
# 5. The HOLD posture itself
# --------------------------------------------------------------------------


def test_no_phase_l_execution_protocol_was_frozen() -> None:
    """Section 15 requires design finalization to stop on this discovery.

    No execution config, driver or analyzer exists, so nothing can be executed
    and no frozen hash record attests a protocol that cannot run.
    """

    for relative in (
        "configs/phaseL-qualification.yaml",
        "configs/phaseL-models.yaml",
        "scripts/run_phaseL_requalification.py",
        "scripts/analyze_phaseL_requalification.py",
        "docs/phaseL_rc3_real_model_requalification_plan.md",
    ):
        assert not (PROJECT_ROOT / relative).exists(), (
            f"{relative} must not exist while the phase is HOLD_PHASE_L_PROTOCOL"
        )


def test_the_report_exists_and_ends_with_the_hold_status() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")
    # Exactly one terminal status, and it is the HOLD.
    assert text.rstrip().endswith("HOLD_PHASE_L_PROTOCOL")
    assert "ZERO MODEL INFERENCE" in text
    # The READY status may be NAMED while explaining why it was withheld, but it
    # must never be the report's terminal line.
    assert not text.rstrip().endswith("READY_FOR_PHASE_L_EXECUTION_GATE_REVIEW")


def test_no_preregistration_v4_and_no_pilot_v7_final() -> None:
    assert not list((PROJECT_ROOT / "docs").glob("preregistration*v4*"))
    for name in ("pilot-v7", "pilot-v7-final"):
        assert not (PROJECT_ROOT / "benchmark" / name).exists()


def test_phase_l_a_modified_no_historical_or_frozen_artifact() -> None:
    """Phase L-A was additive only -- asserted over the Phase-L-A commit range.

    This is a claim about what PHASE L-A did, and it is evaluated between the
    Phase-K commit and the Phase-L-A commit, where it is true and stays true.

    It previously compared against the live working tree, which quietly turned
    "Phase L-A changed nothing" into "nothing may ever change" -- the same
    conflation that made the Phase-L-A defect unrepairable in the first place.
    Phase M repairs the instrument under a separately hash-pinned revision record
    and does not touch one Phase-L-A byte; the Phase-L-A HOLD documents are still
    asserted byte-identical below, live, against the working tree.
    """

    changed = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=MDRT",
            CANONICAL_BASE_COMMIT,
            PHASE_L_A_COMMIT,
            "--",
            "benchmark",
            "results",
            "src",
            "configs",
            "docs",
            "tests",
            "scripts",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert changed.stdout.strip() == "", (
        "Phase L-A must add files only; modified: " f"{changed.stdout.splitlines()}"
    )


def test_the_phase_l_a_hold_record_is_never_rewritten() -> None:
    """The HOLD report and its seed record are immutable, checked LIVE.

    Phase M must not rewrite history to pretend the defect never existed. These
    files ARE the Phase-L-A finding, and they are compared against the working
    tree rather than against a commit range.
    """

    changed = subprocess.run(
        [
            "git", "diff", "--name-only", "--diff-filter=MDRT", PHASE_L_A_COMMIT, "--",
            "docs/phaseL_rc3_requalification_freeze_report.md",
            "docs/phaseL_rc3_prospective_seed_derivation.json",
            "scripts/phaseL_seed_derivation.py",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert changed.stdout.strip() == "", (
        "the Phase-L-A HOLD record must never be rewritten: "
        f"{changed.stdout.splitlines()}"
    )
