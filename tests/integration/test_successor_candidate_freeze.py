"""The post-Phase-P candidate freeze: its invariants, and what must break it.

NO MODEL INFERENCE. NO PROVIDER. NO NETWORK. NO ENDPOINT. NO SEED. NO PHASE-P
EVIDENCE. The one pipeline exercised here is the model-free deterministic
replay the merged implementation already owns.

The expensive half of this module -- two independent generations of the whole
freeze-relevant artifact set -- runs ONCE, in a module-scoped fixture. Every
mutation test then works on a cheap per-test copy of the written namespace, so
the fail-closed behaviour is exercised many times without regenerating anything.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from typing import Any, Callable

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import TOOL_ARGUMENT_CONTRACT_VERSION  # noqa: E402

import rc4_scoring_vocabulary as rc4v  # noqa: E402
import successor_candidate_freeze as fz  # noqa: E402
import successor_candidate_naming as naming  # noqa: E402
import successor_scoring_vocabulary as sv  # noqa: E402
import validate_successor_candidate_freeze as cv  # noqa: E402
import validate_successor_scope as scope  # noqa: E402


# --------------------------------------------------------------------------
# The one expensive generation
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> fz.FreezeResult:
    """One freeze, generated twice under two independent temporary roots."""

    roots = [
        tmp_path_factory.mktemp("candidate-freeze-generation-0"),
        tmp_path_factory.mktemp("candidate-freeze-generation-1"),
    ]
    return fz.freeze(roots)


@pytest.fixture(scope="module")
def frozen_root(
    result: fz.FreezeResult, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """The written candidate namespace, as a repository root."""

    root = tmp_path_factory.mktemp("candidate-freeze-written")
    fz.write_candidate(result, root)
    return root


@pytest.fixture()
def mutable_root(frozen_root: Path, tmp_path: Path) -> Path:
    """A per-test copy of the written namespace, safe to corrupt."""

    destination = tmp_path / "repo"
    shutil.copytree(frozen_root, destination)
    return destination


def _namespace(root: Path) -> Path:
    return cv.candidate_root(root)


def _load(root: Path, name: str) -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(
        (_namespace(root) / name).read_bytes().decode("utf-8")
    )
    return parsed


def _rewrite(root: Path, name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    document = _load(root, name)
    mutate(document)
    (_namespace(root) / name).write_bytes(fz.artifact_bytes(document))


def _failures(root: Path) -> list[str]:
    return cv.run_all(root, check_baseline=False)


# --------------------------------------------------------------------------
# The freeze itself
# --------------------------------------------------------------------------


def test_freeze_passes_every_offline_gate(result: fz.FreezeResult) -> None:
    assert result.failures == ()
    assert result.passed is True
    assert [gate.name for gate in result.gates if not gate.satisfied] == []


def test_freeze_writes_exactly_the_declared_artifact_set(frozen_root: Path) -> None:
    present = sorted(item.name for item in _namespace(frozen_root).iterdir())
    assert present == sorted(fz.FREEZE_CRITICAL_ARTIFACTS)


def test_written_candidate_validates(frozen_root: Path) -> None:
    assert cv.run_all(frozen_root, check_baseline=False) == []


def test_baseline_declaration_matches_git() -> None:
    """The classified difference table is checked against reality, not trusted."""

    assert cv.check_baseline_declaration() == []


def test_no_benchmark_case_file_is_copied_into_the_namespace(frozen_root: Path) -> None:
    manifest = _load(frozen_root, fz.ARTIFACT_MANIFEST)
    selection = manifest["benchmark_selection"]
    assert selection["case_files_copied_into_the_candidate_namespace"] is False
    present = {item.name for item in _namespace(frozen_root).iterdir()}
    assert not any(name.endswith(".yaml") for name in present)


# --------------------------------------------------------------------------
# Identity and status
# --------------------------------------------------------------------------


def test_every_artifact_names_the_one_identifier(frozen_root: Path) -> None:
    expected = naming.candidate_identifier()
    for name in fz.FREEZE_CRITICAL_ARTIFACTS:
        assert _load(frozen_root, name)["candidate_identifier"] == expected


def test_candidate_status_is_exactly_frozen_not_yet_qualified(frozen_root: Path) -> None:
    record = _load(frozen_root, fz.ARTIFACT_FREEZE)
    assert record["candidate_status"] == "FROZEN_NOT_YET_QUALIFIED"
    assert record["authorization"]["qualification_status"] == "NOT_YET_QUALIFIED"
    assert record["freeze_is_execution_authorization"] is False


def test_provider_eligibility_is_not_realized(frozen_root: Path) -> None:
    for name in fz.FREEZE_CRITICAL_ARTIFACTS:
        document = _load(frozen_root, name)
        block = document.get("authorization")
        if block is not None:
            assert block["provider_eligibility"] == "NOT_REALIZED"
            assert block["provider_selected"] is False
            assert block["provider_contacted"] is False


def test_every_execution_authorization_is_false(frozen_root: Path) -> None:
    block = _load(frozen_root, fz.ARTIFACT_FREEZE)["authorization"]
    assert block["real_qualification_authorized"] is False
    assert block["model_inference_authorized"] is False
    assert block["qualification_execution_authorized"] is False
    assert block["confirmatory_execution_authorized"] is False
    assert block["seeds_derived"] == 0
    assert block["random_bits_realized"] == 0
    assert block["production_seed_realized"] is False


def test_readiness_never_reaches_a_qualification_conclusion(frozen_root: Path) -> None:
    readiness = _load(frozen_root, fz.ARTIFACT_READINESS)
    assert readiness["conclusion"] == "OFFLINE_FREEZE_GATES_PASS"
    for forbidden in fz.FORBIDDEN_READINESS_CONCLUSIONS:
        assert readiness["conclusions_this_report_may_never_reach"][forbidden] is False
        assert readiness["conclusion"] != forbidden


# --------------------------------------------------------------------------
# The bound scientific invariants
# --------------------------------------------------------------------------


def test_seventeen_tasks_exactly(frozen_root: Path) -> None:
    manifest = scope.load_manifest()
    expected = sorted(str(item) for item in manifest["selected_task_ids"])
    assert len(expected) == 17
    assert sorted(
        _load(frozen_root, fz.ARTIFACT_MANIFEST)["benchmark_selection"][
            "selected_task_ids"
        ]
    ) == expected
    assert sorted(
        _load(frozen_root, fz.ARTIFACT_CONTRACT)["task_selection"]["task_ids"]
    ) == expected
    register = _load(frozen_root, fz.ARTIFACT_SINKS)["register"]
    assert register["tasks_evaluated"] == 17
    assert _load(frozen_root, fz.ARTIFACT_AUDIT)["tasks_audited"] == 17


def test_benchmark_case_byte_digest_is_bound_and_recomputes(frozen_root: Path) -> None:
    recomputed = scope.benchmark_case_bytes_digest(scope.load_manifest())
    assert recomputed == (
        "76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea"
    )
    record = _load(frozen_root, fz.ARTIFACT_FREEZE)
    assert record["scientific_digests"]["benchmark_case_bytes_digest"] == recomputed


def test_canonical_exposure_digest_is_bound_and_recomputes(frozen_root: Path) -> None:
    recomputed = scope.canonical_exposure_digest(
        scope.load_cases(), scope.load_contract()
    )
    assert recomputed == (
        "23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092"
    )
    record = _load(frozen_root, fz.ARTIFACT_FREEZE)
    assert record["scientific_digests"]["canonical_exposure_digest"] == recomputed


def test_instrument_schema_adapter_and_tool_contract_are_bound(
    frozen_root: Path,
) -> None:
    block = _load(frozen_root, fz.ARTIFACT_FREEZE)["instrument"]
    assert block["instrument_version"] == INSTRUMENT_VERSION == "5"
    assert block["raw_schema_version"] == RAW_SCHEMA_VERSION == 6
    assert (
        block["native_tool_adapter_version"]
        == NATIVE_TOOL_ADAPTER_VERSION
        == "native-tools-adapter-3"
    )
    assert (
        block["tool_argument_contract_version"]
        == TOOL_ARGUMENT_CONTRACT_VERSION
        == "tool-arguments-1"
    )
    assert block["cross_instrument_pooling_permitted"] is False


def test_c1_and_c2_are_diagnostic_and_never_exposure(frozen_root: Path) -> None:
    contract = _load(frozen_root, fz.ARTIFACT_CONTRACT)
    c1 = contract["c1_semantics"]
    assert c1["adds"] == sv.PAYLOAD_UNSUPPORTED_COMPLETION_CLAIM
    assert c1["is_exposure"] is False and c1["is_near_miss"] is False
    assert c1["is_trace_conditioned"] is True
    c2 = contract["c2_semantics"]
    assert c2["adds"] == sv.PAYLOAD_NONCANONICAL_RESOURCE_SELECTION
    assert c2["is_exposure"] is False and c2["is_near_miss"] is False


def test_c4a_derives_carriers_and_covers_every_task(frozen_root: Path) -> None:
    document = _load(frozen_root, fz.ARTIFACT_SINKS)
    derivation = document["carrier_derivation"]
    assert sorted(derivation["derived_carrier_tools"]) == [
        "database.update",
        "file.write",
        "message.send",
    ]
    assert derivation["derived_from"] == "tool-arguments-1"
    assert document["applicable_sink_pairs"] == {
        "PI-018": [["file.write", "releaselog/release-4-2.txt"]],
        "PI-020": [["file.write", "handover/morning-brief.txt"]],
        "KP-004": [["message.send", "support/ticket-8842"]],
    }
    assert document["required_sinks_regression_pin"]["role"] == "REGRESSION_ONLY"
    register = document["register"]
    assert len(register["applicability_true"]) + len(
        register["applicability_false"]
    ) == 17


def test_c3_is_bound_unchanged(frozen_root: Path) -> None:
    record = _load(frozen_root, fz.ARTIFACT_FREEZE)["change_dispositions"]["C3"]
    assert record["kind"] == "INSTRUMENTATION_CHANGE"
    assert record["disposition"] == "ALREADY_COMPLETE"
    assert record["status"] == "UNCHANGED"
    assert scope.check_instrument_boundary() == []


def test_c4b_is_absent_and_c6_is_absent(frozen_root: Path) -> None:
    dispositions = _load(frozen_root, fz.ARTIFACT_FREEZE)["change_dispositions"]
    assert dispositions["C4b"]["disposition"] == "NOT_ADOPTED"
    assert dispositions["C6"]["disposition"] == "WITHDRAWN"
    assert scope.check_c4b_not_adopted(scope.load_cases()) == []
    assert scope.check_c6_absent() == []


def test_c5_is_unchanged_and_its_limitation_is_recorded(frozen_root: Path) -> None:
    assert scope.check_c5_unchanged(scope.load_manifest()) == []
    audit = _load(frozen_root, fz.ARTIFACT_AUDIT)["bud018"]
    assert audit["disposition"] == "KEEP_UNCHANGED"
    assert audit["bytes_changed"] is False
    assert audit["limitation_is_recorded_not_repaired"] is True
    assert "not separable from" in audit["declared_known_limitation"]


def test_rc4_isolation_and_retrospective_entry_impossible(frozen_root: Path) -> None:
    assert len(rc4v.PAYLOAD_OUTCOMES) == 4
    for outcome in sv.SUCCESSOR_ONLY_OUTCOMES:
        assert outcome not in rc4v.PAYLOAD_OUTCOMES
    predecessor = _load(frozen_root, fz.ARTIFACT_FREEZE)["predecessor"]
    assert predecessor["qualification_status"] == "UNQUALIFIED"
    assert predecessor["verdict"] == "HOLD"
    assert predecessor["terminal_status"] == "SCHEDULE_COMPLETE_VERDICT_HOLD"
    assert predecessor["ben003_cell_status"] == "MODEL_PROTOCOL_INVALID"
    assert predecessor["ben003_matrix_status"] == "MATRIX_INVALID"
    assert predecessor["ben003_forensic_attribution"] == "MODEL_PROTOCOL_FAILURE"
    assert predecessor["retrospective_entry_into_the_historical_profile"] == "IMPOSSIBLE"
    assert predecessor["historical_evidence_read"] is False


def test_descriptive_audit_is_never_a_gate(frozen_root: Path) -> None:
    audit = _load(frozen_root, fz.ARTIFACT_AUDIT)
    assert audit["is_a_gate"] is False
    assert audit["is_descriptive_only"] is True
    assert audit["gates_this_audit_participates_in"] == []
    for row in audit["audit"]:
        assert row["is_a_threshold"] is False


def test_the_change_ledger_proves_zero_unauthorized_model_visible_change(
    frozen_root: Path,
) -> None:
    ledger = _load(frozen_root, fz.ARTIFACT_LEDGER)
    assert ledger["unauthorized_benchmark_model_visible_change_count"] == 0
    assert ledger["model_visible_difference_count"] == 0
    assert ledger["implementation_difference_count"] > 0
    for row in ledger["implementation_difference_register"]:
        assert row["category"] in fz.DIFFERENCE_CATEGORIES
        assert row["category"] == fz.classify_difference(row["path"])
    register = {row["change"]: row for row in ledger["authorized_change_register"]}
    assert register["C1"]["change_kind"] == "MEASUREMENT_CHANGE"
    assert register["C1"]["authorization"] == "AUTHORIZED"
    assert register["C1"]["disposition"] == "IMPLEMENTED"
    assert register["C2"]["change_kind"] == "MEASUREMENT_CHANGE"
    assert register["C2"]["disposition"] == "IMPLEMENTED"
    assert register["C3"]["change_kind"] == "INSTRUMENTATION_CHANGE"
    assert register["C3"]["status"] == "UNCHANGED"
    assert register["C4a"]["change_kind"] == "VALIDATOR_SCOPE_MEASUREMENT_CHANGE"
    assert register["C4a"]["disposition"] == "IMPLEMENTED"
    assert register["C4b"]["disposition"] == "NOT_ADOPTED"
    assert register["C5"]["disposition"] == "NO_CHANGE"
    assert register["C6"]["disposition"] == "WITHDRAWN"


def test_provenance_binds_every_required_parameter(frozen_root: Path) -> None:
    provenance = _load(frozen_root, fz.ARTIFACT_PROVENANCE)
    for key in cv.REQUIRED_PROVENANCE_KEYS:
        assert key in provenance
    assert provenance["source_commit"] == fz.SOURCE_COMMIT
    assert provenance["randomization"]["seeds_derived"] == 0
    assert provenance["randomization"]["production_seed_realized"] is False
    assert provenance["boundary"]["phase_p_evidence_read"] is False
    assert set(provenance["generation_code"]) == set(fz.GENERATION_CODE_FILES)


# --------------------------------------------------------------------------
# Determinism, normalization and the digest architecture
# --------------------------------------------------------------------------


def test_two_independent_generations_differ_only_at_registered_leaves(
    result: fz.FreezeResult,
) -> None:
    determinism = result.determinism
    assert determinism["independent_generations"] == 2
    assert determinism["unregistered_differing_leaf_paths"] == []
    assert determinism["normalized_generations_identical"] is True
    assert set(determinism["raw_differing_leaf_paths"]) <= set(
        determinism["registered_leaf_paths"]
    )


def test_the_raw_run_root_is_among_the_observed_differences(
    result: fz.FreezeResult,
) -> None:
    """The known ephemeral scratch field is demonstrated to vary, not assumed to."""

    assert "$.criteria[5].detail.run_root" in result.determinism[
        "raw_differing_leaf_paths"
    ]


def test_the_normalization_sentinel_is_exact(frozen_root: Path) -> None:
    evidence = _load(frozen_root, fz.ARTIFACT_READINESS)[
        "offline_capability_evidence"
    ]
    values = dict(fz.leaf_values(evidence))
    for leaf in fz.NORMALIZED_LEAF_PATHS:
        assert values[leaf.path] == "<EPHEMERAL_RUN_ROOT>"


def test_only_the_registered_leaves_are_normalized() -> None:
    """A value that merely looks like a temporary path is left alone."""

    document = {
        "output_root": "/tmp/one",
        "unregistered_path": "/tmp/one/looks/exactly/like/a/scratch/path",
        "criteria": [
            {"criterion": number, "detail": {"run_root": f"/tmp/one/{number}"}}
            for number in range(1, 11)
        ],
    }
    document["criteria"][8]["detail"]["sidecar_directory"] = "/tmp/one/sidecars"
    normalized = fz.normalize_evidence(document)
    assert normalized["output_root"] == "<EPHEMERAL_RUN_ROOT>"
    assert normalized["criteria"][5]["detail"]["run_root"] == "<EPHEMERAL_RUN_ROOT>"
    assert (
        normalized["criteria"][8]["detail"]["sidecar_directory"]
        == "<EPHEMERAL_RUN_ROOT>"
    )
    assert normalized["unregistered_path"] == document["unregistered_path"]
    assert normalized["criteria"][4]["detail"]["run_root"] == "/tmp/one/5"


def test_a_reordered_criteria_list_fails_closed() -> None:
    """Positional registration must not silently rewrite the wrong field."""

    document = {
        "output_root": "/tmp/one",
        "criteria": [
            {"criterion": number, "detail": {"run_root": "/tmp/one"}}
            for number in reversed(range(1, 11))
        ],
    }
    assert fz.check_normalization_structure(document) != []
    with pytest.raises(fz.NormalizationStructureMoved):
        fz.normalize_evidence(document)


def test_a_missing_registered_leaf_fails_closed() -> None:
    document = {
        "criteria": [
            {"criterion": number, "detail": {"run_root": "/tmp/one"}}
            for number in range(1, 11)
        ],
    }
    document["criteria"][8]["detail"]["sidecar_directory"] = "/tmp/one"
    with pytest.raises(fz.NormalizationStructureMoved):
        fz.normalize_evidence(document)


def test_unknown_nondeterminism_is_detected_as_a_differing_leaf() -> None:
    """Anything outside the registry shows up, so the freeze can refuse it."""

    left = {"criteria": [], "scientific_quantity": 1}
    right = {"criteria": [], "scientific_quantity": 2}
    assert fz.differing_leaves(left, right) == ["$.scientific_quantity"]
    registered = {leaf.path for leaf in fz.NORMALIZED_LEAF_PATHS}
    assert "$.scientific_quantity" not in registered


def test_a_structural_difference_is_reported_not_intersected_away() -> None:
    assert fz.differing_leaves({"a": 1}, {"a": 1, "b": 2}) == ["$.b"]


def test_a_substantive_mutation_changes_the_digest(frozen_root: Path) -> None:
    document = _load(frozen_root, fz.ARTIFACT_MANIFEST)
    before = fz.digest_of(document)
    document["instrument"]["instrument_version"] = "4"
    assert fz.digest_of(document) != before


def test_the_digest_architecture_is_acyclic(frozen_root: Path) -> None:
    manifest = _load(frozen_root, fz.ARTIFACT_DIGESTS)
    assert manifest["self_digested"] is False
    assert manifest["digests_the_freeze_record"] is False
    covered = {row["artifact"] for row in manifest["covered_artifacts"]}
    assert covered == set(fz.CONTENT_ARTIFACTS)
    assert fz.ARTIFACT_DIGESTS not in covered
    assert fz.ARTIFACT_FREEZE not in covered
    record = _load(frozen_root, fz.ARTIFACT_FREEZE)
    assert record["digest_manifest_sha256"] == fz.digest_of_path(
        _namespace(frozen_root) / fz.ARTIFACT_DIGESTS
    )


def test_every_bound_digest_recomputes_from_disk(frozen_root: Path) -> None:
    manifest = _load(frozen_root, fz.ARTIFACT_DIGESTS)
    for row in manifest["covered_artifacts"]:
        path = _namespace(frozen_root) / row["artifact"]
        assert fz.digest_of_path(path) == row["sha256"]


# --------------------------------------------------------------------------
# Fail-closed: every mutation below must be refused
# --------------------------------------------------------------------------


def test_the_unmutated_copy_still_validates(mutable_root: Path) -> None:
    assert _failures(mutable_root) == []


def test_identifier_mismatch_fails(mutable_root: Path) -> None:
    _rewrite(
        mutable_root,
        fz.ARTIFACT_MANIFEST,
        lambda d: d.__setitem__("candidate_identifier", "some-other-candidate"),
    )
    assert any("IDENTITY" in failure for failure in _failures(mutable_root))


def test_a_candidate_marked_qualified_fails(mutable_root: Path) -> None:
    _rewrite(
        mutable_root,
        fz.ARTIFACT_FREEZE,
        lambda d: d.__setitem__("candidate_status", "QUALIFIED"),
    )
    assert any("STATUS" in failure for failure in _failures(mutable_root))


def test_premature_provider_eligibility_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["authorization"]["provider_eligibility"] = "REALIZED"

    _rewrite(mutable_root, fz.ARTIFACT_FREEZE, mutate)
    assert any("provider_eligibility" in failure for failure in _failures(mutable_root))


@pytest.mark.parametrize(
    "flag",
    [
        "model_inference_authorized",
        "qualification_execution_authorized",
        "confirmatory_execution_authorized",
        "real_qualification_authorized",
        "randomization_realized",
    ],
)
def test_enabling_any_authorization_fails(mutable_root: Path, flag: str) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["authorization"][flag] = True

    _rewrite(mutable_root, fz.ARTIFACT_FREEZE, mutate)
    assert any(flag in failure for failure in _failures(mutable_root))


def test_a_realized_seed_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["randomization"]["seeds_derived"] = 3

    _rewrite(mutable_root, fz.ARTIFACT_PROVENANCE, mutate)
    assert any("seeds_derived" in failure for failure in _failures(mutable_root))


def test_benchmark_digest_mutation_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["scientific_digests"]["benchmark_case_bytes_digest"] = "0" * 64

    _rewrite(mutable_root, fz.ARTIFACT_FREEZE, mutate)
    assert any(
        "benchmark case-byte digest" in failure for failure in _failures(mutable_root)
    )


def test_task_byte_pin_mutation_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["benchmark_selection"]["case_sha256"]["PI-018"] = "0" * 64

    _rewrite(mutable_root, fz.ARTIFACT_MANIFEST, mutate)
    assert any("per-task case digests" in failure for failure in _failures(mutable_root))


def test_canonical_exposure_digest_mutation_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["canonical_exposure"]["digest"] = "0" * 64

    _rewrite(mutable_root, fz.ARTIFACT_CONTRACT, mutate)
    assert any(
        "canonical exposure digest" in failure for failure in _failures(mutable_root)
    )


@pytest.mark.parametrize(
    "key",
    [
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ],
)
def test_instrument_schema_adapter_or_tool_contract_drift_fails(
    mutable_root: Path, key: str
) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["instrument"][key] = "drifted"

    _rewrite(mutable_root, fz.ARTIFACT_FREEZE, mutate)
    assert any(f"C3: {fz.ARTIFACT_FREEZE} binds {key}" in f for f in _failures(mutable_root))


def test_c1_drift_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["c1_semantics"]["is_exposure"] = True

    _rewrite(mutable_root, fz.ARTIFACT_CONTRACT, mutate)
    assert any("C1:" in failure for failure in _failures(mutable_root))


def test_c2_drift_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["c2_semantics"]["is_near_miss"] = True

    _rewrite(mutable_root, fz.ARTIFACT_CONTRACT, mutate)
    assert any("C2:" in failure for failure in _failures(mutable_root))


def test_c4b_adopted_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        for row in document["authorized_change_register"]:
            if row["change"] == "C4b":
                row["adopted"] = True
                row["disposition"] = "IMPLEMENTED"

    _rewrite(mutable_root, fz.ARTIFACT_LEDGER, mutate)
    assert any("C4b" in failure for failure in _failures(mutable_root))


def test_c5_modified_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        for row in document["authorized_change_register"]:
            if row["change"] == "C5":
                row["modified"] = True

    _rewrite(mutable_root, fz.ARTIFACT_LEDGER, mutate)
    assert any("C5" in failure for failure in _failures(mutable_root))


def test_c6_reintroduced_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        for row in document["authorized_change_register"]:
            if row["change"] == "C6":
                row["reintroduced"] = True
                row["disposition"] = "IMPLEMENTED"

    _rewrite(mutable_root, fz.ARTIFACT_LEDGER, mutate)
    assert any("C6" in failure for failure in _failures(mutable_root))


def test_an_incomplete_change_ledger_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["authorized_change_register"] = [
            row for row in document["authorized_change_register"] if row["change"] != "C3"
        ]

    _rewrite(mutable_root, fz.ARTIFACT_LEDGER, mutate)
    assert any("omits C3" in failure for failure in _failures(mutable_root))


def test_an_unauthorized_model_visible_ledger_item_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["implementation_difference_register"].append(
            {
                "path": "benchmark/prompt_injection/PI-018.yaml",
                "git_status": "M",
                "category": "BENCHMARK_MODEL_VISIBLE",
                "origin": "ADDED_BY_THIS_FREEZE_SESSION",
                "is_model_visible": True,
                "authorized": False,
            }
        )

    _rewrite(mutable_root, fz.ARTIFACT_LEDGER, mutate)
    assert any("model-visible change" in failure for failure in _failures(mutable_root))


def test_a_nonzero_unauthorized_model_visible_count_fails(mutable_root: Path) -> None:
    _rewrite(
        mutable_root,
        fz.ARTIFACT_LEDGER,
        lambda d: d.__setitem__(
            "unauthorized_benchmark_model_visible_change_count", 1
        ),
    )
    assert any(
        "UNAUTHORIZED_BENCHMARK_MODEL_VISIBLE_CHANGE" in failure
        for failure in _failures(mutable_root)
    )


def test_an_incomplete_sink_register_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        register = document["register"]
        register["verdicts"] = register["verdicts"][:-1]
        register["tasks_evaluated"] = len(register["verdicts"])

    _rewrite(mutable_root, fz.ARTIFACT_SINKS, mutate)
    assert any("SINKS" in failure for failure in _failures(mutable_root))


def test_a_carrier_derivation_mismatch_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["carrier_derivation"]["derived_carrier_tools"] = ["file.write"]

    _rewrite(mutable_root, fz.ARTIFACT_SINKS, mutate)
    assert any("carrier tools" in failure for failure in _failures(mutable_root))


def test_a_missing_task_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["task_selection"]["task_ids"] = document["task_selection"]["task_ids"][
            :-1
        ]

    _rewrite(mutable_root, fz.ARTIFACT_CONTRACT, mutate)
    assert any("COVERAGE" in failure for failure in _failures(mutable_root))


def test_a_missing_audit_row_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["audit"] = document["audit"][:-1]
        document["tasks_audited"] = len(document["audit"])

    _rewrite(mutable_root, fz.ARTIFACT_AUDIT, mutate)
    assert any("COVERAGE" in failure for failure in _failures(mutable_root))


def test_promoting_the_descriptive_audit_to_a_gate_fails(mutable_root: Path) -> None:
    _rewrite(mutable_root, fz.ARTIFACT_AUDIT, lambda d: d.__setitem__("is_a_gate", True))
    assert any("AUDIT" in failure for failure in _failures(mutable_root))


def test_a_gate_that_consumes_the_audit_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["gates"].append(
            {
                "gate": "RESOURCE_SELECTION_AUDIT_THRESHOLD",
                "satisfied": True,
                "failures": [],
                "detail": {},
            }
        )

    _rewrite(mutable_root, fz.ARTIFACT_READINESS, mutate)
    assert any("makes the descriptive" in failure for failure in _failures(mutable_root))


def test_a_forecast_of_task_behaviour_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["predicted_exposure"] = {"PI-018": 0.5}

    _rewrite(mutable_root, fz.ARTIFACT_CONTRACT, mutate)
    assert any("FORECAST" in failure for failure in _failures(mutable_root))


def test_a_missing_provenance_binding_fails(mutable_root: Path) -> None:
    _rewrite(
        mutable_root, fz.ARTIFACT_PROVENANCE, lambda d: d.pop("scientific_digests")
    )
    assert any("PROVENANCE" in failure for failure in _failures(mutable_root))


def test_a_bound_artifact_mutation_fails(mutable_root: Path) -> None:
    """Editing a tier-0 artifact breaks the digest the tier-1 manifest binds."""

    def mutate(document: dict[str, Any]) -> None:
        document["is_final"] = True

    _rewrite(mutable_root, fz.ARTIFACT_MANIFEST, mutate)
    assert any(
        "has been mutated" in failure or "DIGEST" in failure
        for failure in _failures(mutable_root)
    )


def test_a_whitespace_only_mutation_fails(mutable_root: Path) -> None:
    """The digest basis is the file bytes, so even reformatting is caught."""

    path = _namespace(mutable_root) / fz.ARTIFACT_AUDIT
    document = json.loads(path.read_bytes().decode("utf-8"))
    path.write_bytes((json.dumps(document, sort_keys=True) + "\n").encode("utf-8"))
    assert any("DIGEST" in failure for failure in _failures(mutable_root))


def test_a_missing_freeze_critical_artifact_fails(mutable_root: Path) -> None:
    (_namespace(mutable_root) / fz.ARTIFACT_PROVENANCE).unlink()
    assert any("is missing from" in failure for failure in _failures(mutable_root))


def test_an_unexpected_extra_artifact_fails(mutable_root: Path) -> None:
    (_namespace(mutable_root) / "extra-candidate-artifact.json").write_bytes(b"{}\n")
    assert any(
        "not a declared freeze-critical artifact" in failure
        for failure in _failures(mutable_root)
    )


def test_an_absent_namespace_fails(tmp_path: Path) -> None:
    failures = cv.run_all(tmp_path, check_baseline=False)
    assert any("does not exist" in failure for failure in failures)


def test_widening_the_normalization_policy_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["normalization_policy"]["rules"]["arbitrary_paths_stripped"] = True

    _rewrite(mutable_root, fz.ARTIFACT_FREEZE, mutate)
    assert any(
        "broader than the one that was approved" in failure
        for failure in _failures(mutable_root)
    )


def test_a_non_canonical_normalization_sentinel_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["normalization_policy"]["canonical_replacement"] = "<REDACTED>"

    _rewrite(mutable_root, fz.ARTIFACT_READINESS, mutate)
    assert any("exact sentinel" in failure for failure in _failures(mutable_root))


def test_recorded_nondeterminism_outside_the_registry_fails(mutable_root: Path) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["determinism"]["unregistered_differing_leaf_paths"] = [
            "$.criteria[3].detail.tasks"
        ]

    _rewrite(mutable_root, fz.ARTIFACT_READINESS, mutate)
    assert any(
        "outside the closed" in failure for failure in _failures(mutable_root)
    )


def test_a_single_generation_freeze_is_refused() -> None:
    with pytest.raises(ValueError):
        fz.freeze([Path(".")])


def test_writing_before_gates_pass_is_refused(tmp_path: Path) -> None:
    failed = fz.FreezeResult(
        artifacts={}, gates=(), determinism={}, failures=("GATE: synthetic",)
    )
    with pytest.raises(RuntimeError):
        fz.write_candidate(failed, tmp_path)
