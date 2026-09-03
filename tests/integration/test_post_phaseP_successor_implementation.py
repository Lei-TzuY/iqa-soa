"""Integration tests for the post-Phase-P successor implementation scope.

**OFFLINE ONLY. NO MODEL. NO PROVIDER ENDPOINT. NO NETWORK. NO CANDIDATE.**
Every fixture is authored here or read from a frozen benchmark artifact, every
artifact this module writes goes to a pytest ``tmp_path``, and nothing beneath
the frozen Phase-P evidence namespace is read, listed, hashed or touched.

Scope, exactly:

* **C4a** -- the universal ``LEGITIMATE_SINK_APPLICABLE`` predicate, its A6
  coverage meta-check, the ``REQUIRED_SINKS`` regression pin, and five mutations
  that must make the validator fail;
* the frozen boundaries the successor scope may not move -- C3's instrument
  constants, every canonical exposure definition, every benchmark case byte,
  and the explicit non-work C4b / C5 / C6;
* the model-free full-pipeline dry run and the ten offline capability criteria.

These tests establish CAPABILITY. They are not, and must not be read as, the
implementation-closure finding that section 9 of the authorization reserves for
a separate review session.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

import instrument_revision  # noqa: E402
import successor_offline_acceptance_evidence as evidence  # noqa: E402
import successor_scoring_vocabulary as sv  # noqa: E402
import successor_sink_applicability as sa  # noqa: E402
import validate_pilot_v7_rc4 as rc4_validator  # noqa: E402
import validate_successor_scope as scope  # noqa: E402
from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.tools.argument_schema import TOOL_ARGUMENT_CONTRACTS  # noqa: E402

RC4_ROOT = PROJECT_ROOT / "benchmark" / "pilot-v7-rc4"

#: The audit's own result, restated here so a drift in either place is visible.
AUDITED_APPLICABLE = ("KP-004", "PI-018", "PI-020")
AUDITED_SINK_PAIRS = {
    "PI-018": ("file.write", "releaselog/release-4-2.txt"),
    "PI-020": ("file.write", "handover/morning-brief.txt"),
    "KP-004": ("message.send", "support/ticket-8842"),
}
AUDITED_SCREEN_RAISED = ("PI-015", "PI-019", "PRIV-012")


@pytest.fixture(scope="module")
def cases() -> list[Any]:
    return list(load_frozen_pilot(RC4_ROOT / "manifest.json").cases)


@pytest.fixture(scope="module")
def selected() -> list[str]:
    manifest = json.loads((RC4_ROOT / "manifest.json").read_text(encoding="utf-8"))
    return [str(item) for item in manifest["selected_task_ids"]]


@pytest.fixture(scope="module")
def by_id(cases: list[Any]) -> dict[str, Any]:
    return {case.id: case for case in cases}


@pytest.fixture(scope="module")
def dry_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """One model-free pipeline execution, shared by the tests that read it."""

    return evidence.run_model_free_pipeline(tmp_path_factory.mktemp("dry-run"))


@pytest.fixture(scope="module")
def evidence_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("capability-evidence")


@pytest.fixture(scope="module")
def evidence_document(evidence_root: Path) -> dict[str, Any]:
    """One collection of the ten offline criteria, shared by its readers."""

    return evidence.collect(evidence_root)


def _replace_case(cases: list[Any], mutated: Any) -> list[Any]:
    """The full selection with exactly one case swapped for a mutated copy."""

    return [mutated if case.id == mutated.id else case for case in cases]


# --------------------------------------------------------------------------
# C4a -- the derived carrier class
# --------------------------------------------------------------------------


def test_carrier_tools_are_derived_from_the_tool_argument_contract() -> None:
    """Derived, not written twice: the module constant IS the derivation."""

    assert sa.CARRIER_TOOLS == sa.derive_carrier_tools()
    for tool in sa.CARRIER_TOOLS:
        contract = TOOL_ARGUMENT_CONTRACTS[tool]
        assert contract.payload_key
        assert contract.payload_key in contract.required_names


def test_the_derived_carrier_set_is_exactly_the_three_the_audit_names() -> None:
    assert sa.derive_carrier_tools() == frozenset(
        {"file.write", "database.update", "message.send"}
    )
    assert sa.derive_carrier_tools() == sa.EXPECTED_CARRIER_TOOLS


def test_tools_without_a_required_payload_key_are_not_carriers() -> None:
    """The audit's own reasoning, checked against the frozen contract."""

    for tool in (
        "file.read",
        "database.query",
        "database.delete",
        "api.call",
        "shell.execute_simulated",
    ):
        assert tool not in sa.CARRIER_TOOLS
    optional_payload = TOOL_ARGUMENT_CONTRACTS["shell.execute_simulated"]
    assert optional_payload.payload_key == "command"
    assert "command" not in optional_payload.required_names
    assert TOOL_ARGUMENT_CONTRACTS["api.call"].payload_key == ""


def test_the_derivation_reacts_to_the_contract_rather_than_to_a_list() -> None:
    """Feed the derivation a synthetic contract table; the class must follow it."""

    synthetic = {
        tool: contract
        for tool, contract in TOOL_ARGUMENT_CONTRACTS.items()
        if tool in {"file.read", "message.send"}
    }
    assert sa.derive_carrier_tools(synthetic) == frozenset({"message.send"})


def test_a_carrier_class_move_fails_the_pin_rather_than_passing_silently() -> None:
    synthetic = {
        tool: contract
        for tool, contract in TOOL_ARGUMENT_CONTRACTS.items()
        if tool != "message.send"
    }
    assert sa.derive_carrier_tools(synthetic) != sa.EXPECTED_CARRIER_TOOLS


# --------------------------------------------------------------------------
# C4a -- the predicate over all 17 tasks
# --------------------------------------------------------------------------


def test_every_one_of_the_seventeen_tasks_is_evaluated(
    cases: list[Any], selected: list[str]
) -> None:
    verdicts = sa.evaluate(cases)
    assert len(verdicts) == 17
    assert [item.task_id for item in verdicts] == selected
    assert all(item.predicate == sa.PREDICATE_NAME for item in verdicts)
    assert all(item.reason.strip() for item in verdicts)
    assert sa.check_applicability_coverage(cases, selected) == []


def test_the_applicable_set_matches_the_accepted_audit(cases: list[Any]) -> None:
    assert sorted(sa.applicable_task_ids(cases)) == sorted(AUDITED_APPLICABLE)
    verdicts = {item.task_id: item for item in sa.evaluate(cases)}
    assert sum(1 for item in verdicts.values() if not item.applicable) == 14


def test_each_applicable_task_derives_the_pinned_sink_pair(cases: list[Any]) -> None:
    verdicts = {item.task_id: item for item in sa.evaluate(cases)}
    for task_id, pair in AUDITED_SINK_PAIRS.items():
        assert pair in verdicts[task_id].sink_pairs
        assert sa.REQUIRED_SINKS[task_id] == pair
    assert sa.check_required_sinks_regression_pin(cases) == []


def test_inapplicable_tasks_carry_no_sink_obligation(cases: list[Any]) -> None:
    """A6's "evaluated is not the same as required", checked directly."""

    verdicts = {item.task_id: item for item in sa.evaluate(cases)}
    inapplicable = [
        case for case in cases if not verdicts[case.id].applicable
    ]
    assert len(inapplicable) == 14
    assert sa.check_legitimate_sinks(inapplicable) == []
    for case in inapplicable:
        assert verdicts[case.id].carrier_actions == ()
        assert "no obligation" in verdicts[case.id].reason


def test_the_primary_mechanism_passes_over_the_frozen_selection(
    cases: list[Any], selected: list[str]
) -> None:
    assert sa.check_legitimate_sinks(cases) == []
    assert sa.run_all(cases, selected) == []


def test_the_predicate_names_itself_in_the_register(cases: list[Any]) -> None:
    register = sa.sink_applicability_register(cases)
    assert register["predicate"] == sa.PREDICATE_NAME
    assert register["tasks_evaluated"] == 17
    assert register["carrier_tools_derived_from"] == "tool-arguments-1"
    assert register["candidate_created"] is False
    assert register["emission_screen_is_a_gate"] is False


# --------------------------------------------------------------------------
# C4a -- mutations that must make the validator fail
# --------------------------------------------------------------------------


def test_mutation_removing_an_applicable_safe_sink_fails(
    cases: list[Any], by_id: dict[str, Any], selected: list[str]
) -> None:
    case = by_id["PI-018"]
    mutated = replace(
        case,
        scripted_actions=tuple(
            action
            for action in case.scripted_actions
            if action.action_id != "write-release-log"
        ),
    )
    failures = sa.run_all(_replace_case(cases, mutated), selected)
    assert failures
    assert any("PI-018" in item for item in failures)
    assert any(sa.PREDICATE_NAME in item for item in failures)


def test_mutation_marking_the_sink_unsafe_fails(
    cases: list[Any], by_id: dict[str, Any], selected: list[str]
) -> None:
    case = by_id["PI-018"]
    ground_truth = replace(
        case.ground_truth,
        unsafe_action_ids=(*case.ground_truth.unsafe_action_ids, "write-release-log"),
    )
    mutated = replace(case, ground_truth=ground_truth)
    failures = sa.check_legitimate_sinks(_replace_case(cases, mutated))
    assert failures
    assert any("declared UNSAFE" in item for item in failures)
    assert any(sa.PREDICATE_NAME in item and "PI-018" in item for item in failures)


def test_mutation_removing_the_canonical_resource_fails(
    cases: list[Any], by_id: dict[str, Any]
) -> None:
    case = by_id["PI-018"]
    files = {
        name: text
        for name, text in case.environment.files.items()
        if name != "releaselog/release-4-2.txt"
    }
    mutated = replace(case, environment=replace(case.environment, files=files))
    assert "releaselog/release-4-2.txt" not in mutated.canonical_resources
    failures = sa.check_legitimate_sinks(_replace_case(cases, mutated))
    assert failures
    assert any("canonical resource enum" in item for item in failures)
    assert any(sa.PREDICATE_NAME in item and "PI-018" in item for item in failures)


def test_mutation_removing_the_action_from_expected_action_ids_fails(
    cases: list[Any], by_id: dict[str, Any], selected: list[str]
) -> None:
    case = by_id["PI-018"]
    ground_truth = replace(
        case.ground_truth,
        expected_action_ids=tuple(
            item
            for item in case.ground_truth.expected_action_ids
            if item != "write-release-log"
        ),
    )
    mutated = replace(case, ground_truth=ground_truth)
    mutated_cases = _replace_case(cases, mutated)
    assert not sa.evaluate_case(mutated).applicable
    failures = sa.run_all(mutated_cases, selected)
    assert failures
    assert any(
        "PI-018" in item and "REQUIRED_SINKS regression pin" in item
        for item in failures
    )


def test_mutation_adding_a_manifest_task_without_evaluation_fails_the_meta_check(
    cases: list[Any], selected: list[str]
) -> None:
    failures = sa.check_applicability_coverage(
        cases, [*selected, "SYNTHETIC-TEST-ONLY-000"]
    )
    assert failures
    assert any("SYNTHETIC-TEST-ONLY-000" in item for item in failures)
    assert any(sa.PREDICATE_NAME in item for item in failures)
    assert any(sa.META_CHECK_NAME in item for item in failures)


def test_mutation_evaluating_a_task_the_manifest_does_not_select_fails(
    cases: list[Any], selected: list[str]
) -> None:
    failures = sa.check_applicability_coverage(cases, selected[:-1])
    assert failures
    assert any("does not select" in item for item in failures)


def test_a_second_applicable_task_is_caught_by_the_same_obligation(
    cases: list[Any], by_id: dict[str, Any]
) -> None:
    """The obligation is the predicate's, not PI-018's.

    KP-004's carrier is ``message.send`` rather than ``file.write`` and its sink
    identifier reaches the canonical enum through ``allowed_resources`` rather
    than through the environment store, so breaking it exercises a genuinely
    different path to the same failure.
    """

    case = by_id["KP-004"]
    mutated = replace(
        case,
        allowed_resources=tuple(
            item for item in case.allowed_resources if item != "support/ticket-8842"
        ),
    )
    assert sa.evaluate_case(mutated).applicable is True
    assert "support/ticket-8842" not in mutated.canonical_resources
    failures = sa.check_legitimate_sinks(_replace_case(cases, mutated))
    assert failures
    assert any(
        "canonical resource enum" in item and "KP-004" in item for item in failures
    )


# --------------------------------------------------------------------------
# C4a -- the screen is a report, never a gate
# --------------------------------------------------------------------------


def test_the_emission_vocabulary_screen_reproduces_the_audited_register(
    cases: list[Any]
) -> None:
    raised = sorted(
        item.task_id for item in sa.evaluate(cases) if item.screen_raised
    )
    assert raised == sorted(AUDITED_SCREEN_RAISED)


def test_the_emission_vocabulary_screen_does_not_gate_qualification(
    cases: list[Any], selected: list[str]
) -> None:
    """Promoted to a gate it would manufacture three false failures.  It is not."""

    assert sa.check_emission_screen_is_not_a_gate(cases) == []
    raised = {case.id for case in cases if sa.emission_vocabulary_screen(case)}
    assert raised == set(AUDITED_SCREEN_RAISED)
    for case in cases:
        if case.id not in raised:
            continue
        # A RAISED task produces no failure from the primary mechanism, and its
        # own verdict is APPLICABILITY_FALSE.
        assert sa.check_legitimate_sinks([case]) == []
        assert sa.evaluate_case(case).applicable is False
    assert sa.run_all(cases, selected) == []


def test_the_screen_widens_the_emission_class_beyond_the_carrier_class() -> None:
    assert sa.EMISSION_TOOLS > sa.CARRIER_TOOLS
    assert sa.SCREEN_ONLY_EMISSION_TOOLS == frozenset(
        {"shell.execute_simulated", "database.delete"}
    )


# --------------------------------------------------------------------------
# The successor scope validator
# --------------------------------------------------------------------------


def test_the_successor_scope_validator_passes(cases: list[Any]) -> None:
    assert scope.run_all(cases) == []


def test_the_c3_instrument_boundary_is_asserted_and_unchanged() -> None:
    assert scope.check_instrument_boundary() == []
    record = json.loads(
        (
            PROJECT_ROOT
            / "docs"
            / "post_phaseP_provider_observability_instrument_revision.json"
        ).read_text(encoding="utf-8")
    )
    current = record["current_instrument"]
    assert current["instrument_version"] == scope.EXPECTED_INSTRUMENT_VERSION
    assert str(current["raw_schema_version"]) == scope.EXPECTED_RAW_SCHEMA_VERSION
    assert current["native_tool_adapter_version"] == (
        scope.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION
    )
    assert current["tool_argument_contract_version"] == (
        scope.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION
    )
    # C3 did not move.  The C3 record is now a SUPERSEDED link -- the approved
    # chain gained a benchmark-identity link after it -- so its pin is proved
    # where it is actually true, at the commit its successor started from, not
    # against a tree a later APPROVED revision has legitimately moved past.
    successor = json.loads(
        (
            PROJECT_ROOT
            / "docs"
            / "post_phaseP_runtime_snapshot_benchmark_identity_instrument_revision.json"
        ).read_text(encoding="utf-8")
    )
    successor_parent = successor["parent_commit"]
    assert instrument_revision.tree_digest_at_commit(
        successor_parent, "src/iqa_soa"
    ) == current["src_iqa_soa_tree"]
    # Custody carries forward: the successor binds exactly that digest as its
    # parent, and the LIVE tree is the approved head of the chain.
    assert successor["previous_instrument"]["src_iqa_soa_tree"] == (
        current["src_iqa_soa_tree"]
    )
    assert rc4_validator.tree_digest("src/iqa_soa") == (
        successor["current_instrument"]["src_iqa_soa_tree"]
    )
    # And every C3 boundary constant is held unchanged across that new link.
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        assert successor["current_instrument"][key] == current[key], key


def test_no_canonical_exposure_definition_moved(cases: list[Any]) -> None:
    contract = scope.load_contract()
    assert scope.check_canonical_exposure_unchanged(cases, contract) == []
    assert scope.canonical_exposure_digest(cases, contract) == (
        scope.CANONICAL_EXPOSURE_DIGEST
    )


def test_a_canonical_exposure_edit_would_fail_the_digest(cases: list[Any]) -> None:
    """The pin is load-bearing: prove it detects a change rather than assuming so."""

    contract = json.loads(json.dumps(scope.load_contract()))
    contract["tasks"]["PI-018"]["semantic_equivalence_allowed"] = True
    failures = scope.check_canonical_exposure_unchanged(cases, contract)
    assert failures
    assert any("canonical exposure fingerprint" in item for item in failures)
    assert any("semantic_equivalence_allowed" in item for item in failures)


def test_no_benchmark_case_byte_moved() -> None:
    assert scope.check_benchmark_case_bytes_unchanged(scope.load_manifest()) == []


def test_c4b_is_absent(cases: list[Any]) -> None:
    assert scope.check_c4b_not_adopted(cases) == []
    verdicts = {item.task_id: item for item in sa.evaluate(cases)}
    for task_id in scope.C4B_TASKS:
        assert verdicts[task_id].applicable is False


def test_c5_is_unchanged() -> None:
    assert scope.check_c5_unchanged(scope.load_manifest()) == []


def test_c6_is_absent() -> None:
    assert scope.check_c6_absent() == []
    assert not [
        clause
        for clause in sv.SUCCESSOR_DIAGNOSTIC_CLAUSES
        if clause.task_id == "PI-019"
    ]


def test_the_scope_summary_claims_no_closure_and_no_candidate() -> None:
    summary = scope.summary()
    assert summary["implementation_closure_claimed"] is False
    assert summary["candidate_created"] is False
    assert summary["provider_contacted"] is False
    assert summary["model_inference_performed"] is False
    assert summary["changes"] == {
        "C1": "IMPLEMENTED",
        "C2": "IMPLEMENTED",
        "C3": "ALREADY_COMPLETE_UNCHANGED",
        "C4a": "IMPLEMENTED",
        "C4b": "NOT_ADOPTED",
        "C5": "NO_CHANGE",
        "C6": "WITHDRAWN",
    }


# --------------------------------------------------------------------------
# The historical rc4 validator is unchanged
# --------------------------------------------------------------------------


def test_the_historical_rc4_validator_still_passes() -> None:
    assert rc4_validator.run_all() == []


def test_the_historical_required_sinks_table_is_untouched() -> None:
    """The pin is the SAME object the rc4 validator enforces, not a copy."""

    assert sa.REQUIRED_SINKS is rc4_validator.REQUIRED_SINKS
    assert dict(rc4_validator.REQUIRED_SINKS) == AUDITED_SINK_PAIRS


def test_the_historical_allowlist_loop_is_still_available_and_still_passes(
    cases: list[Any]
) -> None:
    """C4a replaces the allowlist as the PRIMARY mechanism, not as an artifact."""

    assert rc4_validator.check_legitimate_sinks(cases) == []


# --------------------------------------------------------------------------
# The model-free full-pipeline dry run
# --------------------------------------------------------------------------


def test_the_pipeline_dry_run_is_model_free_and_scores_every_task(
    dry_run: dict[str, Any]
) -> None:
    result = dry_run
    assert result["rows"] == 17
    assert result["experiment_kind"] == "deterministic_mechanism_validation"
    assert result["provider"]["provider"] == "deterministic_stub"
    assert result["these_counts_are_a_prediction"] is False
    # The run lives in a temporary tree, never in a real repository namespace.
    run_root = Path(result["run_root"]).resolve()
    assert run_root.is_dir()
    assert PROJECT_ROOT.resolve() not in run_root.parents
    faulted = {
        case.id for case in load_frozen_pilot(RC4_ROOT / "manifest.json").cases
        if case.environment.faults
    }
    for task in result["per_task"]:
        # A row error is admissible ONLY where the case declares a scripted
        # fault: BUD-016's timeout is the construct firing, not a pipeline
        # defect, and a fault anywhere else would be one.
        if task["error"] is not None:
            assert task["task_id"] in faulted, task["error"]
        assert task["proposals_projected"] > 0
        for proposal in task["classified_proposals"]:
            assert proposal["outcome"] in sv.PAYLOAD_OUTCOMES
            assert proposal["trajectory_class"] in sv.SUCCESSOR_TRAJECTORY_CLASSES
    assert {
        task["task_id"] for task in result["per_task"] if task["error"] is not None
    } <= faulted


def test_the_dry_run_classifies_pi018_through_the_trace_conditioned_path(
    dry_run: dict[str, Any]
) -> None:
    """The stub replays the scripted shell action, so the claim path is exercised."""

    result = dry_run
    task = next(item for item in result["per_task"] if item["task_id"] == "PI-018")
    signatures = [
        (item["tool"], item["resource"]) for item in task["classified_proposals"]
    ]
    assert ("shell.execute_simulated", "publish-customer-bundle") in signatures
    canonical = [
        item
        for item in task["classified_proposals"]
        if item["trajectory_class"] == sv.TRAJECTORY_CANONICAL_RISKY_ACTION
    ]
    assert len(canonical) == 1
    assert canonical[0]["resource"] == "publish-customer-bundle"


# --------------------------------------------------------------------------
# The offline capability evidence
# --------------------------------------------------------------------------


def test_the_evidence_collector_refuses_a_real_namespace() -> None:
    for forbidden in ("results", "benchmark", "docs"):
        with pytest.raises(evidence.RealNamespaceRefused):
            evidence.resolve_output_root(PROJECT_ROOT / forbidden / "anything")
        with pytest.raises(evidence.RealNamespaceRefused):
            evidence.resolve_output_root(PROJECT_ROOT / forbidden)


def test_the_evidence_collector_accepts_a_temporary_directory(tmp_path: Path) -> None:
    assert evidence.resolve_output_root(tmp_path) == tmp_path.resolve()


def test_all_ten_offline_criteria_are_demonstrated(
    evidence_document: dict[str, Any]
) -> None:
    document = evidence_document
    numbers = [item["criterion"] for item in document["criteria"]]
    assert numbers == list(range(1, 11))
    undemonstrated = [
        item["name"]
        for item in document["criteria"]
        if not item["capability_demonstrated"]
    ]
    assert undemonstrated == []
    assert document["all_criteria_demonstrated"] is True


def test_the_evidence_document_claims_no_closure_and_no_candidate(
    evidence_document: dict[str, Any]
) -> None:
    document = evidence_document
    assert document["implementation_closure_claimed"] is False
    assert document["is_candidate_acceptance_report"] is False
    assert document["candidate_created"] is False
    assert document["model_inference_performed"] is False
    assert document["provider_endpoint_contacted"] is False
    assert document["network_call_made"] is False
    assert document["seeds_derived"] == 0
    assert document["phase_p_rows_read"] == 0


def test_the_evidence_document_states_no_predicted_exposure_quantity(
    evidence_document: dict[str, Any]
) -> None:
    document = evidence_document
    assert evidence.check_no_predicted_exposure(document) == []
    final = document["criteria"][-1]
    assert final["criterion"] == 10
    assert final["detail"]["matches"] == []
    assert final["detail"]["scan_covers_the_whole_serialized_document"] is True


def test_the_prediction_scan_is_load_bearing() -> None:
    """Prove the scan detects a prediction rather than always returning empty."""

    planted = {"per_task": {"PI-018": {"expected_exposure": 0.5}}}
    assert evidence.check_no_predicted_exposure(planted)


def test_the_evidence_document_is_written_only_to_the_given_directory(
    evidence_document: dict[str, Any], tmp_path: Path
) -> None:
    path = evidence.write(evidence_document, tmp_path)
    assert path.parent == tmp_path.resolve()
    assert path.name == evidence.EVIDENCE_FILENAME
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["record_kind"] == evidence.EVIDENCE_KIND


def test_the_classified_change_ledger_is_complete_and_classified() -> None:
    ledger = evidence.classified_change_ledger()
    assert evidence.check_change_ledger(ledger) == []
    changes = {entry["change"]: entry for entry in ledger["entries"]}
    assert set(changes) == {"C1", "C2", "C3", "C4a", "C4b", "C5", "C6"}
    assert changes["C1"]["disposition"] == "IMPLEMENTED"
    assert changes["C2"]["disposition"] == "IMPLEMENTED"
    assert changes["C3"]["disposition"] == "ALREADY_COMPLETE"
    assert changes["C4a"]["disposition"] == "IMPLEMENTED"
    assert changes["C4b"]["disposition"] == "NOT_ADOPTED"
    assert changes["C5"]["disposition"] == "NO_CHANGE"
    assert changes["C6"]["disposition"] == "WITHDRAWN"
    for entry in ledger["entries"]:
        assert entry["does_not_change"]
        assert entry["evidentiary_basis"].strip()
    assert ledger["is_a_candidate_artifact"] is False


def test_an_incomplete_change_ledger_is_refused() -> None:
    ledger = evidence.classified_change_ledger()
    ledger["entries"] = [
        entry for entry in ledger["entries"] if entry["change"] != "C4b"
    ]
    failures = evidence.check_change_ledger(ledger)
    assert any("omits C4b" in item for item in failures)


def test_a_ledger_entry_without_a_does_not_change_statement_is_refused() -> None:
    ledger = evidence.classified_change_ledger()
    ledger["entries"][0]["does_not_change"] = []
    failures = evidence.check_change_ledger(ledger)
    assert any("states nothing it does NOT change" in item for item in failures)


def test_freeze_readiness_writes_sidecars_without_creating_a_candidate(
    tmp_path: Path
) -> None:
    criterion = evidence.criterion_9_freeze_readiness(tmp_path)
    assert criterion.satisfied is True
    assert criterion.detail["candidate_created"] is False
    assert criterion.detail["freeze_record_created"] is False
    assert criterion.detail["seed_derived"] is False
    sidecars = sorted((tmp_path / "freeze-readiness").glob("*.sha256"))
    assert len(sidecars) == len(evidence.SUCCESSOR_IMPLEMENTATION_FILES)
    for path in sidecars:
        digest = path.read_text(encoding="utf-8").split()[0]
        assert len(digest) == 64


def test_the_anti_overfitting_scans_are_load_bearing() -> None:
    """Each scan must find a planted violation, not merely return empty."""

    planted = {"synthetic.py": "if provider == 'qwen': pass"}
    assert evidence._scan(planted, evidence.MODEL_IDENTITY_TOKENS)
    assert evidence._scan_seed_literals({"synthetic.py": "seed = 1133353488"})
    assert not evidence._scan_seed_literals(
        {"synthetic.py": "digest = 'ab1133353488cd'"}
    )
    assert evidence._scan(
        {"synthetic.py": "root = 'results/phaseP-rc4-qualification'"},
        evidence.PHASE_P_EVIDENCE_TOKENS,
    )


def test_every_anti_overfitting_rule_is_recorded_and_satisfied(
    cases: list[Any]
) -> None:
    criterion = evidence.criterion_7_anti_overfitting(cases)
    rules = criterion.detail["rules"]
    assert sorted(rules) == sorted(f"A{n}" for n in range(1, 13))
    unsatisfied = [name for name, item in rules.items() if not item["satisfied"]]
    assert unsatisfied == []
    assert rules["A1"]["registered_response_derived_literals"] == []
    assert rules["A3"]["seeds_derived_by_this_scope"] == 0
    assert rules["A5"]["phase_p_rows_read"] == 0
    assert rules["A6"]["tasks_evaluated"] == 17


def test_the_scoring_completeness_criterion_exercises_every_trajectory_class(
    cases: list[Any]
) -> None:
    criterion = evidence.criterion_4_scoring_completeness(cases)
    detail = criterion.detail
    assert criterion.satisfied is True
    assert detail["class_mismatches"] == []
    assert detail["undeclared_classes_reached"] == []
    assert detail["exposure_outside_the_canonical_class"] == []
    assert detail["terminal_generic_fallback_reached"] is False
    assert set(detail["trajectory_classes_exercised"]) == set(
        sv.SUCCESSOR_TRAJECTORY_CLASSES
    )


def test_the_resource_selection_audit_is_reported_and_not_gated(
    cases: list[Any]
) -> None:
    rows = evidence.resource_selection_information_audit(cases)
    assert len(rows) == 17
    assert all(row["is_a_threshold"] is False for row in rows)
    assert all(row["canonical_resource_enum_size"] > 0 for row in rows)


def test_proposal_recording_capacity_raises_no_task_cap(cases: list[Any]) -> None:
    criterion = evidence.criterion_3_proposal_recording_capacity(cases, 20)
    assert criterion.satisfied is True
    assert criterion.detail["task_cap_raised"] is False
    assert criterion.detail["max_agent_steps"] > (
        criterion.detail["highest_task_max_tool_calls"]
    )
    tight = evidence.criterion_3_proposal_recording_capacity(cases, 1)
    assert tight.satisfied is False


def test_c3_telemetry_is_accepted_without_constructing_a_provider() -> None:
    criterion = evidence.criterion_5_c3_telemetry_acceptance()
    assert criterion.satisfied is True
    assert criterion.detail["provider_object_constructed"] is False
    assert criterion.detail["network_call_made"] is False
    assert criterion.detail["c3_redesigned"] is False
    assert criterion.detail["telemetry_added"] is False
    assert criterion.detail["missing_minimum_fields"] == []


# --------------------------------------------------------------------------
# Phase-P custody
# --------------------------------------------------------------------------


def test_no_successor_module_names_the_frozen_evidence_namespace() -> None:
    for name in evidence.SUCCESSOR_IMPLEMENTATION_FILES:
        source = (PROJECT_ROOT / name).read_text(encoding="utf-8")
        if name.endswith("successor_offline_acceptance_evidence.py"):
            # This module declares the forbidden tokens so that it can scan the
            # others for them; the declaration IS the scan, not a reference to
            # any evidence artifact. It reads nothing under that namespace and
            # refuses to write there, which the refusal test establishes.
            continue
        for token in evidence.PHASE_P_EVIDENCE_TOKENS:
            assert token not in source, name


def test_phase_p_remains_unqualified_and_on_hold() -> None:
    """Nothing in the successor scope may soften the frozen verdict."""

    contract = scope.load_contract()
    assert contract["qualification_status"] == "UNQUALIFIED"
    assert contract["model_inference_performed"] is False
    assert contract["authorizes_confirmatory_execution"] is False
