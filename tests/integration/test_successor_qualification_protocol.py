"""The successor qualification protocol, its isolation, and the PR-10 boundary.

NO MODEL INFERENCE. NO PROVIDER CONTACT. NO NETWORK. NO RUNTIME CAPTURE.

The historical Phase-P results namespace is never read, listed, stat-ed, hashed
or globbed here. The one test that proves the protocol REFUSES that namespace
passes the path as a string to a guard that is deliberately lexical, so the
refusal is demonstrated without the filesystem ever being consulted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import run_successor_qualification as driver  # noqa: E402
import successor_derive_seeds as derivation  # noqa: E402
import successor_eligibility_preflight as eligibility  # noqa: E402
import successor_qualification_protocol as protocol  # noqa: E402
import successor_scoring_vocabulary as vocabulary  # noqa: E402
from iqa_soa.experiment.confirmatory_eligibility import (  # noqa: E402
    CHANNEL_IDS,
    PREDICATE_IDS,
    derive_disposition,
)
from iqa_soa.experiment.confirmatory_registration import (  # noqa: E402
    RetryPolicyV1,
    RuntimeSnapshotV1,
)


# ---------------------------------------------------------------------------
# The protocol binds the frozen candidate and its digests
# ---------------------------------------------------------------------------


def test_offline_preflight_passes_with_no_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the offline preflight opened a network socket")

    monkeypatch.setattr(socket, "socket", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)
    assert protocol.offline_preflight() == []


def test_protocol_binds_the_frozen_candidate() -> None:
    assert protocol.CANDIDATE_IDENTIFIER == "prospective-candidate-i5-m1-b76f40da2"
    assert protocol.CANDIDATE_STATUS_AT_ENTRY == "FROZEN_NOT_YET_QUALIFIED"
    freeze = json.loads(
        (PROJECT_ROOT / protocol.FREEZE_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert freeze["candidate_identifier"] == protocol.CANDIDATE_IDENTIFIER
    assert freeze["candidate_status"] == protocol.CANDIDATE_STATUS_AT_ENTRY
    assert protocol.check_candidate_freeze() == []


def test_protocol_binds_the_benchmark_digest() -> None:
    assert protocol.BENCHMARK_CASE_BYTES_DIGEST == (
        "76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea"
    )
    freeze = json.loads(
        (PROJECT_ROOT / protocol.FREEZE_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert (
        freeze["scientific_digests"]["benchmark_case_bytes_digest"]
        == protocol.BENCHMARK_CASE_BYTES_DIGEST
    )


def test_protocol_binds_the_canonical_exposure_digest() -> None:
    assert protocol.CANONICAL_EXPOSURE_DIGEST == (
        "23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092"
    )
    freeze = json.loads(
        (PROJECT_ROOT / protocol.FREEZE_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert (
        freeze["scientific_digests"]["canonical_exposure_digest"]
        == protocol.CANONICAL_EXPOSURE_DIGEST
    )


def test_instrument_schema_adapter_and_tool_contract_are_exact() -> None:
    assert protocol.EXPECTED_INSTRUMENT_VERSION == "5"
    assert protocol.EXPECTED_RAW_SCHEMA_VERSION == 6
    assert protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION == "native-tools-adapter-3"
    assert protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION == "tool-arguments-1"
    assert protocol.check_instrument_pins() == []
    assert protocol.CROSS_INSTRUMENT_POOLING_PERMITTED is False


def test_frozen_execution_inputs_are_bound_and_current() -> None:
    assert protocol.check_frozen_inputs() == []
    record = protocol.load_frozen_inputs()
    assert record is not None
    assert record["candidate_identifier"] == protocol.CANDIDATE_IDENTIFIER
    assert record["results_namespace"] == protocol.RESULTS_NAMESPACE
    assert record["credential_env"] == "SUCCESSOR_OLLAMA_API_KEY"
    assert record["provider_contacted"] is False
    assert record["model_inference_performed"] is False
    assert record["seeds"] == [583010984, 1723431918, 1639806953]
    assert record["planned_cells"] == 102
    assert record["seed_count"] == 3
    assert record["seed_derivation_record"] == (
        "docs/successor_prospective_seed_derivation.json"
    )
    assert record["seed_derivation_algorithm"] == (
        "successor-qualification-seed-derivation-1"
    )
    assert record["experiment_config"] == "configs/successor-qualification.yaml"
    assert record["expected_runtime_version"] == "0.32.13"
    assert record["runtime_version_resolution"] == "RESTORE_FROZEN_RUNTIME"
    assert record["runtime_repin_authorized"] is False


# ---------------------------------------------------------------------------
# Scoring profile
# ---------------------------------------------------------------------------


def test_successor_scoring_profile_is_exact() -> None:
    assert protocol.SCORING_PROFILE == "successor"
    assert protocol.SCORING_VOCABULARY_VERSION == "successor-scoring-vocabulary-1"
    assert protocol.check_scoring_profile() == []
    contract = json.loads(
        (PROJECT_ROOT / protocol.QUALIFICATION_CONTRACT_RELATIVE).read_text(
            encoding="utf-8"
        )
    )
    assert contract["scoring_profile"]["payload_outcomes"] == list(
        vocabulary.outcomes_for_profile("successor")
    )


def test_historical_rc4_profile_is_excluded() -> None:
    assert protocol.SCORING_PROFILE != protocol.HISTORICAL_SCORING_PROFILE
    assert (
        protocol.SCORING_VOCABULARY_VERSION
        != protocol.HISTORICAL_SCORING_VOCABULARY_VERSION
    )
    assert protocol.check_historical_isolation() == []


# ---------------------------------------------------------------------------
# Namespace refusal and result-artifact absence
# ---------------------------------------------------------------------------


def test_protocol_refuses_the_historical_result_namespace() -> None:
    """The guard is lexical, so proving the refusal touches no historical path."""

    for forbidden in protocol.FORBIDDEN_RESULTS_NAMESPACES:
        with pytest.raises(protocol.NoncanonicalInput) as excinfo:
            protocol.require_canonical_results_root(forbidden)
        assert "frozen historical evidence" in str(excinfo.value)


def test_protocol_refuses_a_child_of_a_historical_namespace() -> None:
    with pytest.raises(protocol.NoncanonicalInput):
        protocol.require_canonical_results_root(
            f"{protocol.FORBIDDEN_RESULTS_NAMESPACES[0]}/raw/cells/x"
        )


def test_protocol_refuses_an_arbitrary_output_root() -> None:
    with pytest.raises(protocol.NoncanonicalInput) as excinfo:
        protocol.require_canonical_results_root("results/somewhere-else")
    assert "does not reinterpret an alternate output root" in str(excinfo.value)


def test_successor_namespace_is_accepted_and_is_not_historical() -> None:
    accepted = protocol.require_canonical_results_root(protocol.RESULTS_NAMESPACE)
    assert protocol.is_canonical_results_root(accepted)
    assert protocol.RESULTS_NAMESPACE not in protocol.FORBIDDEN_RESULTS_NAMESPACES


def test_no_result_artifact_is_fabricated() -> None:
    assert not (PROJECT_ROOT / protocol.RESULTS_NAMESPACE).exists()
    assert protocol.check_no_result_artifact_exists() == []
    assert protocol.protocol_summary()["results_namespace_created"] is False


def test_noncanonical_scientific_input_is_refused() -> None:
    with pytest.raises(protocol.NoncanonicalInput):
        protocol.require_canonical_input(
            protocol.CANONICAL_MODELS_RELATIVE, PROJECT_ROOT / "configs" / "models.yaml"
        )
    with pytest.raises(protocol.NoncanonicalInput):
        protocol.require_canonical_input("configs/phaseP-models.yaml")


# ---------------------------------------------------------------------------
# Authorization boundaries
# ---------------------------------------------------------------------------


def test_candidate_cannot_be_marked_qualified_before_execution() -> None:
    assert protocol.CANDIDATE_QUALIFICATION_STATUS == "NOT_YET_QUALIFIED"
    assert (
        protocol.CANDIDATE_QUALIFICATION_STATUS
        not in protocol.FORBIDDEN_CANDIDATE_STATUSES
    )
    summary = protocol.protocol_summary()
    assert summary["candidate_status_at_entry"] == "FROZEN_NOT_YET_QUALIFIED"
    assert summary["candidate_qualification_status"] == "NOT_YET_QUALIFIED"
    assert summary["model_inference_performed"] is False
    assert summary["provider_contacted"] is False
    assert protocol.check_authorization_state() == []


def test_no_confirmatory_authorization_anywhere() -> None:
    assert protocol.CONFIRMATORY_EXECUTION_AUTHORIZED is False
    assert protocol.AUTHORIZES_CONFIRMATORY_EXECUTION is False
    assert protocol.RANDOMIZATION_REALIZATION_AUTHORIZED is False
    assert protocol.STAGE_C_FINAL_REGISTRATION_AUTHORIZED is False
    assert "confirmatory" in protocol.OUT_OF_SCOPE_TREATMENTS
    assert protocol.protocol_summary()["reports_no_confirmatory_disposition"] is True


def test_frozen_protocol_still_refuses_before_the_gates_are_consulted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The earlier protocol remains a denial; only the later driver record grants."""

    monkeypatch.setenv(protocol.HUMAN_GATE_ENV, protocol.HUMAN_GATE_VALUE)
    with pytest.raises(protocol.QualificationExecutionNotAuthorized):
        protocol.require_execution_authorization()
    assert driver.load_execution_authorization().record["granted"][
        "qualification_execution"
    ] is True


def test_driver_offline_preflight_reports_no_contact_and_no_rows() -> None:
    assert driver.main([]) == protocol.EXIT_OK
    report = driver.offline_preflight_report()
    assert report["protocol_preflight_failures"] == []
    assert report["eligibility_argument_failures"] == []
    assert report["provider_contacted"] is False
    assert report["model_inference_performed"] is False
    assert report["rows_written"] == 0
    assert report["results_namespace_created"] is False


def test_retries_are_fixed_at_zero() -> None:
    assert protocol.INFRASTRUCTURE_RETRY_LIMIT == 0
    assert all(value is False for value in protocol.NO_RETRY_POLICY.values())


def test_persistence_is_fail_closed_with_no_overwrite() -> None:
    assert protocol.PERSISTENCE_POLICY["overwrite_permitted"] is False
    assert protocol.PERSISTENCE_POLICY["resume_permitted"] is False
    assert protocol.PERSISTENCE_POLICY["merge_permitted"] is False
    assert protocol.PERSISTENCE_POLICY["fail_closed"] is True


def test_seed_derivation_is_prospective_and_complete() -> None:
    assert len(protocol.SEEDS) == 3
    assert protocol.PLANNED_CELLS == 17 * 2 * 3
    assert protocol.SEED_SELECTION_STATUS == (
        "DERIVED_PROSPECTIVELY_BEFORE_ANY_SUCCESSOR_OUTCOME"
    )
    assert protocol.check_seed_derivation() == []


# ---------------------------------------------------------------------------
# PR-10: selection is not eligibility
# ---------------------------------------------------------------------------


def test_pr10_argument_passes_its_own_integrity_checks() -> None:
    assert eligibility.check_argument_integrity() == []


def test_pr10_covers_the_four_frozen_predicates_in_order() -> None:
    for stratum in eligibility.argument_record()["strata"]:
        ids = [item["predicate_id"] for item in stratum["predicates"]]
        assert tuple(ids) == PREDICATE_IDS


def test_pr10_cannot_become_confirmatory_eligible_from_selection_alone() -> None:
    record = eligibility.argument_record()
    assert record["current_provider_eligibility"] == "UNASSESSED"
    for stratum in record["strata"]:
        assert stratum["confirmatory_eligible"] is False
        assert stratum["disposition"] == "NOT_ASSIGNED_STAGE_B_NOT_ENTERED"
        assert stratum["projected_stage_b_disposition"] != "CONFIRMATORY_ELIGIBLE"
        assert stratum["selection_establishes"] == "PROPOSED_STRATUM"


def test_projection_is_the_frozen_derivation_and_is_not_recorded() -> None:
    assessments = eligibility.offline_assessments()
    statuses = [item.stage_b_status for item in assessments]
    assert eligibility.projected_disposition(assessments) == derive_disposition(statuses)
    for stratum in eligibility.argument_record()["strata"]:
        assert stratum["projected_disposition_is_recorded"] is False


def test_pending_predicates_carry_no_stage_b_evidence() -> None:
    """Section 9.3: UNASSESSED predicates carry exactly ``[]``."""

    for stratum in eligibility.argument_record()["strata"]:
        for predicate in stratum["predicates"]:
            if predicate["stage_b_status_if_assessed_today"] == "UNASSESSED":
                assert predicate["stage_b_evidence_refs_if_assessed_today"] == []


def test_infrastructure_symmetry_carries_no_predicate_level_evidence() -> None:
    """Section 9.5: its evidence lives on the channels, in every status."""

    for stratum in eligibility.argument_record()["strata"]:
        symmetry = stratum["predicates"][1]
        assert symmetry["predicate_id"] == "INFRASTRUCTURE_SYMMETRY"
        assert symmetry["stage_b_evidence_refs_if_assessed_today"] == []
        audit = stratum["infrastructure_symmetry_audit"]
        assert audit["derived_status"] == "UNASSESSED"
        assert tuple(item["channel_id"] for item in audit["channels"]) == CHANNEL_IDS
        assert all(item["check_status"] == "NOT_CHECKED" for item in audit["channels"])


def test_every_pending_predicate_names_a_blocking_fact() -> None:
    for assessment in eligibility.offline_assessments():
        if assessment.offline_status == "PENDING":
            assert assessment.blocking_facts


def test_offline_evidence_locators_resolve_to_real_committed_files() -> None:
    for assessment in eligibility.offline_assessments():
        for ref in assessment.offline_evidence:
            assert ref.evidence_kind == "REPOSITORY_PATH"
            path = PROJECT_ROOT / ref.locator
            assert path.is_file(), ref.locator
            assert (
                hashlib.sha256(path.read_bytes()).hexdigest() == ref.content_digest
            ), ref.locator


def test_an_unexplained_pending_is_refused() -> None:
    with pytest.raises(eligibility.SuccessorEligibilityError):
        eligibility.OfflinePredicateAssessment(
            predicate_id="TOTAL_OBSERVATION",
            offline_status="PENDING",
            established_offline="",
            blocking_facts=(),
            offline_evidence=(),
        )


def test_a_pass_without_evidence_is_refused() -> None:
    with pytest.raises(eligibility.SuccessorEligibilityError):
        eligibility.OfflinePredicateAssessment(
            predicate_id="POSITION_STATE_ISOLATION",
            offline_status="PASS",
            established_offline="",
            blocking_facts=(),
            offline_evidence=(),
        )


# ---------------------------------------------------------------------------
# Runtime snapshots and the Stage-A boundary
# ---------------------------------------------------------------------------


def _well_formed_snapshot() -> RuntimeSnapshotV1:
    """A structurally PERFECT snapshot built entirely offline.

    Every digest field is a syntactically valid SHA-256 and the frozen dataclass
    accepts it, so this object is exactly what a fabrication would look like.
    That is the point: it is never captured, and the refusal must not depend on
    catching a malformed value.
    """

    return RuntimeSnapshotV1(
        provider_name="qwen_native_none",
        model="qwen3.5:27b",
        endpoint="http://127.0.0.1:11434/v1/chat/completions",
        provider_config_digest="a" * 64,
        provider_parameters_digest="b" * 64,
        timeout_seconds="600",
        retry_policy=RetryPolicyV1(
            max_attempts=1,
            backoff_kind="NONE",
            initial_delay_seconds="0",
            max_delay_seconds="0",
            retryable_error_classes=(),
        ),
        tool_contract_policy="none",
        native_tool_adapter_version="native-tools-adapter-3",
        package_source_sha256="c" * 64,
        python_version="3.13.0",
        artifact_version="0.2.0",
        prompt_digest="d" * 64,
        experiment_config_digest="e" * 64,
        models_config_digest="f" * 64,
        environment_fingerprint="0" * 64,
        captured_at="2026-09-02T00:00:00Z",
    )


def test_a_synthetic_runtime_snapshot_is_not_accepted_as_captured_evidence() -> None:
    """Shape is not provenance: a valid RuntimeSnapshotV1 is still refused."""

    snapshot = _well_formed_snapshot()
    assert len(snapshot.runtime_identity_digest) == 64  # it really is well-formed
    with pytest.raises(eligibility.SyntheticRuntimeSnapshotRejected) as excinfo:
        eligibility.accept_captured_runtime_snapshot(snapshot)
    assert "SYNTHETIC_RUNTIME_SNAPSHOT_REFUSED" in str(excinfo.value)


def test_no_snapshot_shape_whatsoever_is_accepted() -> None:
    for payload in ({}, {"schema_version": "RuntimeSnapshotV1"}, None, "snapshot"):
        with pytest.raises(eligibility.SyntheticRuntimeSnapshotRejected):
            eligibility.accept_captured_runtime_snapshot(payload)


def test_stage_a_cannot_seal_without_an_actual_runtime_snapshot() -> None:
    assert eligibility.stage_a_status() == "BLOCKED_PENDING_RUNTIME_SNAPSHOT"
    record = eligibility.argument_record()
    assert record["stage_a_status"] == "BLOCKED_PENDING_RUNTIME_SNAPSHOT"
    assert record["registration_draft_written"] is False
    assert record["runtime_snapshots_captured"] == 0
    assert record["runtime_snapshots_synthesized"] == 0
    assert record["runtime_snapshot_capture_required_next"] is True
    for stratum in record["strata"]:
        assert stratum["captured_runtime_snapshot_count"] == 0
        assert stratum["registration_expected_runtime_identity_digest"] is None


def test_stage_b_is_not_entered_and_no_eligibility_manifest_exists() -> None:
    """No Stage-B manifest was written anywhere this work is allowed to write.

    The search is deliberately bounded to the three roots this authorization can
    create files under. A repository-wide glob would traverse frozen historical
    evidence, which is exactly what the boundary forbids -- and searching there
    would prove nothing anyway, since nothing here can write there.
    """

    record = eligibility.argument_record()
    assert record["stage_b_entered"] is False
    assert record["eligibility_manifest_written"] is False
    for root in (
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "candidates",
        PROJECT_ROOT / protocol.RESULTS_NAMESPACE,
    ):
        if root.exists():
            assert not list(root.rglob("eligibility_manifest.json"))
            assert not list(root.rglob("registration_draft.json"))


def test_no_provider_was_contacted_by_the_pr10_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the PR-10 argument opened a network socket")

    monkeypatch.setattr(socket, "socket", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)
    record = eligibility.argument_record()
    assert record["provider_contacted"] is False
    assert record["endpoint_probed"] is False
    assert record["model_metadata_queried"] is False
    assert record["model_inference_performed"] is False


def test_committed_pr10_artifact_matches_the_module() -> None:
    committed = json.loads(
        (PROJECT_ROOT / eligibility.ARGUMENT_RECORD_RELATIVE).read_text(
            encoding="utf-8"
        )
    )
    assert committed == eligibility.argument_record()


# ---------------------------------------------------------------------------
# The frozen execution-input set, and what happens when a bound input moves
# ---------------------------------------------------------------------------


def _rewrite(path: Path, text: str) -> None:
    """Write *text* with the repository's canonical LF newline convention."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _mirror_bound_inputs(root: Path) -> None:
    """Copy every digest-bound input, and the record itself, under *root*.

    Mutation tests operate on this mirror.  No committed byte is ever written by
    a test, and the historical evidence tree is neither copied nor read: every
    bound path is a config, doc, script, candidate artifact or benchmark file.
    """

    for bound in (*protocol.FROZEN_INPUT_PATHS, protocol.FROZEN_INPUTS_RELATIVE):
        target = root / bound
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((PROJECT_ROOT / bound).read_bytes())
    for tree_root in protocol.FROZEN_TREE_ROOTS:
        (root / tree_root).mkdir(parents=True, exist_ok=True)


def test_frozen_execution_inputs_include_the_experiment_config() -> None:
    record = protocol.load_frozen_inputs()
    assert record is not None
    files = record["files"]
    relative = protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    assert relative in files
    assert relative in protocol.FROZEN_INPUT_PATHS
    assert len(files[relative]) == 64
    assert files[relative] == hashlib.sha256(
        (PROJECT_ROOT / relative).read_bytes()
    ).hexdigest()
    assert protocol.accepted_frozen_digest(relative) == files[relative]


def test_the_digest_architecture_stays_acyclic() -> None:
    """No bound input digests the record that binds it.

    The frozen-input record hashes the protocol, the configs, the docs and the
    scripts; nothing hashes the record.  There is therefore no self-hash and no
    fixpoint to solve, so re-freezing is one deterministic pass.
    """

    assert protocol.FROZEN_INPUTS_RELATIVE not in protocol.FROZEN_INPUT_PATHS
    record = protocol.load_frozen_inputs()
    assert record is not None
    assert protocol.FROZEN_INPUTS_RELATIVE not in record["files"]
    assert protocol.FROZEN_INPUTS_RELATIVE not in record["trees"]
    for tree_root in protocol.FROZEN_TREE_ROOTS:
        assert not protocol.FROZEN_INPUTS_RELATIVE.startswith(tree_root + "/")


def test_no_frozen_input_path_points_into_historical_evidence() -> None:
    for relative in (*protocol.FROZEN_INPUT_PATHS, *protocol.FROZEN_TREE_ROOTS):
        assert not relative.startswith("results/"), relative
        for forbidden in protocol.FORBIDDEN_RESULTS_NAMESPACES:
            assert not relative.startswith(forbidden), relative
        assert relative not in protocol.FORBIDDEN_RUNTIME_CONFIGS


def test_mutating_the_experiment_config_fails_digest_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One added byte in the ExperimentConfig is a frozen-input failure."""

    relative = protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    before = (PROJECT_ROOT / relative).read_bytes()
    _mirror_bound_inputs(tmp_path)

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    _rewrite(
        tmp_path / relative,
        (tmp_path / relative).read_text(encoding="utf-8") + "\n# one added byte\n",
    )
    failures = protocol.check_frozen_inputs()
    assert any(relative in item and "digests to" in item for item in failures)

    assert (PROJECT_ROOT / relative).read_bytes() == before


def test_mutating_the_models_config_fails_digest_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relative = protocol.CANONICAL_MODELS_RELATIVE
    before = (PROJECT_ROOT / relative).read_bytes()
    _mirror_bound_inputs(tmp_path)

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    _rewrite(
        tmp_path / relative,
        (tmp_path / relative)
        .read_text(encoding="utf-8")
        .replace("temperature: 0.2", "temperature: 0.7"),
    )
    failures = protocol.check_frozen_inputs()
    assert any(relative in item and "digests to" in item for item in failures)

    assert (PROJECT_ROOT / relative).read_bytes() == before


def test_a_dropped_experiment_config_binding_is_a_frozen_input_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A record that quietly stopped binding the config must fail, not shrink."""

    _mirror_bound_inputs(tmp_path)
    record = json.loads(
        (PROJECT_ROOT / protocol.FROZEN_INPUTS_RELATIVE).read_text(encoding="utf-8")
    )
    del record["files"][protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE]
    _rewrite(
        tmp_path / protocol.FROZEN_INPUTS_RELATIVE,
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_frozen_inputs()
    assert any(
        protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE in item
        and "not among the digest-bound execution inputs" in item
        for item in failures
    )


def test_the_frozen_record_is_exactly_what_the_protocol_computes() -> None:
    """Re-freezing today reproduces the committed record exactly."""

    assert protocol.load_frozen_inputs() == protocol.compute_frozen_inputs()


def test_the_frozen_record_is_never_silently_overwritten(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert protocol.main(["--write-frozen-inputs"]) == protocol.EXIT_PREFLIGHT_STOP
    assert "REFUSED" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The successor ExperimentConfig, from the protocol's side
# ---------------------------------------------------------------------------


def _mutated_experiment_config(root: Path, **overrides: object) -> None:
    """Write the successor ExperimentConfig under *root* with *overrides*."""

    import yaml

    relative = protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    config = yaml.safe_load((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
    config.update(overrides)
    _rewrite(root / relative, yaml.safe_dump(config, sort_keys=True))


def test_the_experiment_config_is_a_canonical_scientific_input() -> None:
    assert protocol.check_experiment_config() == []
    resolved = protocol.require_canonical_input(
        protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    )
    assert (
        resolved
        == (PROJECT_ROOT / protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE).resolve()
    )
    summary = protocol.protocol_summary()
    assert summary["experiment_config"] == "configs/successor-qualification.yaml"
    assert summary["models_config"] == "configs/successor-models.yaml"
    assert summary["treatments"] == ["off"]
    assert summary["experiment_output_root"] == (
        "results/prospective-candidate-i5-m1-b76f40da2-qualification/raw"
    )


def test_the_experiment_config_may_not_name_a_phase_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A config pointed at the historical namespace fails the check.

    The forbidden namespace is handled as a STRING by a deliberately lexical
    guard, so the historical evidence directory is never read, listed or stat-ed
    to prove the refusal.
    """

    _mutated_experiment_config(
        tmp_path, output_root=f"{protocol.FORBIDDEN_RESULTS_NAMESPACES[0]}/raw"
    )
    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_experiment_config()
    assert any("output_root" in item for item in failures)
    assert any("frozen historical evidence" in item for item in failures)


def test_the_experiment_config_may_not_point_at_a_phase_models_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mutated_experiment_config(
        tmp_path, models_path=protocol.FORBIDDEN_RUNTIME_CONFIGS[0]
    )
    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_experiment_config()
    assert any("historical phase config" in item for item in failures)


def test_a_config_carrying_undervived_seeds_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A seed the authorized derivation did not produce is a preflight failure.

    Historical seeds are used as the substitute precisely because they are the
    most plausible wrong answer: they are real, committed, and would look
    unremarkable in a diff.
    """

    _mutated_experiment_config(tmp_path, seeds=[1729, 2718, 3141], repetitions=3)
    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_experiment_config()
    assert any("seeds is" in item for item in failures)
    assert any("a seed this protocol did not derive" in item for item in failures)
    assert 1729 not in protocol.SEEDS


def test_a_repetition_count_disagreeing_with_the_seed_count_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`repetitions` describes the seed count; a disagreement is a failure."""

    _mutated_experiment_config(tmp_path, repetitions=5)
    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_experiment_config()
    assert any("repetitions is" in item for item in failures)


def test_an_out_of_scope_treatment_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A confirmatory arm in the qualification config is a preflight failure."""

    _mutated_experiment_config(tmp_path, treatments=["off", "full"])
    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_experiment_config()
    assert any("out-of-scope treatment" in item for item in failures)


# ---------------------------------------------------------------------------
# The runtime-version boundary, from the protocol's side
# ---------------------------------------------------------------------------


def test_the_runtime_version_policy_is_intact() -> None:
    assert protocol.check_runtime_version_policy() == []
    summary = protocol.protocol_summary()
    assert summary["expected_runtime_version"] == "0.32.13"
    assert summary["accepted_runtime_versions"] == ["0.32.13"]
    assert summary["runtime_version_comparison"] == "EXACT_STRING_EQUALITY"
    assert summary["runtime_version_resolution"] == "RESTORE_FROZEN_RUNTIME"
    assert summary["runtime_repin_authorized"] is False
    assert summary["runtime_restore_required"] is True
    assert summary["environment_hold_observed_runtime_version"] == "0.33.0"
    assert all(
        value is False for value in summary["runtime_hold_remedies_refused"].values()
    )


def test_a_repinned_runtime_fails_the_policy_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repinning to the environment's version is caught, not tolerated."""

    monkeypatch.setattr(protocol, "EXPECTED_RUNTIME_VERSION", "0.33.0")
    failures = protocol.check_runtime_version_policy()
    assert failures
    assert any("RUNTIME_VERSION" in item for item in failures)


def test_a_widened_accepted_set_fails_the_policy_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(protocol, "ACCEPTED_RUNTIME_VERSIONS", ("0.32.13", "0.33.0"))
    assert any(
        "are accepted" in item for item in protocol.check_runtime_version_policy()
    )


def test_an_equivalence_exception_fails_the_policy_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol, "RUNTIME_VERSION_EQUIVALENCE_EXCEPTION_PERMITTED", True
    )
    assert any(
        "equivalence exception" in item
        for item in protocol.check_runtime_version_policy()
    )


def test_the_preflight_fails_closed_on_a_held_runtime() -> None:
    """A held runtime stops the run; it never becomes a repair instruction."""

    with pytest.raises(protocol.EnvironmentHold) as excinfo:
        protocol.verify_runtime_identity(
            arm="qwen",
            observed={
                "model": "qwen3.5:27b",
                "model_digest": protocol.EXPECTED_MODEL_DIGEST["qwen3.5:27b"],
                "runtime_version": protocol.ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION,
                "tool_contract_policy": "none",
                "protocol": "native_tools",
            },
        )
    message = str(excinfo.value)
    assert "never downgrades, updates" in message
    assert "no version-equivalence exception" in message
    assert issubclass(protocol.EnvironmentHold, protocol.SuccessorProtocolError)


# ---------------------------------------------------------------------------
# Nothing here fabricates evidence or authorizes execution
# ---------------------------------------------------------------------------


def test_no_fake_results_exist_anywhere_this_work_may_write() -> None:
    """The successor namespace is absent, and no successor artifact name exists."""

    assert not (PROJECT_ROOT / protocol.RESULTS_NAMESPACE).exists()
    assert not (PROJECT_ROOT / protocol.EXPERIMENT_OUTPUT_ROOT).exists()
    assert protocol.check_no_result_artifact_exists() == []
    for name in (
        protocol.RAW_RECORD_NAME,
        protocol.RAW_CSV_NAME,
        protocol.RUN_MANIFEST_NAME,
        protocol.PARTIAL_MANIFEST_NAME,
        protocol.ANALYSIS_NAME,
    ):
        assert not list((PROJECT_ROOT / "docs").rglob(name))
        assert not list((PROJECT_ROOT / "configs").rglob(name))
        assert not list((PROJECT_ROOT / "candidates").rglob(name))


def test_no_runtime_snapshot_was_captured_or_synthesized_for_the_config() -> None:
    """The ExperimentConfig gives the snapshot a digest target, not a snapshot."""

    record = eligibility.argument_record()
    assert record["runtime_snapshots_captured"] == 0
    assert record["runtime_snapshots_synthesized"] == 0
    for stratum in record["strata"]:
        assert stratum["experiment_config"] == "configs/successor-qualification.yaml"
        assert stratum["registration_expected_runtime_identity_digest"] is None
        assert stratum["runtime_repin_authorized"] is False
        assert stratum["runtime_version_comparison"] == "EXACT_STRING_EQUALITY"
    with pytest.raises(eligibility.SyntheticRuntimeSnapshotRejected):
        eligibility.accept_captured_runtime_snapshot(_well_formed_snapshot())


def test_qualification_and_confirmatory_execution_remain_unauthorized() -> None:
    """Neither the ExperimentConfig nor the runtime decision opened a gate."""

    assert protocol.QUALIFICATION_EXECUTION_AUTHORIZED is False
    assert protocol.CONFIRMATORY_EXECUTION_AUTHORIZED is False
    assert protocol.AUTHORIZES_CONFIRMATORY_EXECUTION is False
    assert protocol.MODEL_INFERENCE_AUTHORIZED is False
    assert protocol.PROVIDER_CONTACT_AUTHORIZED is False
    assert protocol.ENDPOINT_PROBE_AUTHORIZED is False
    assert protocol.RANDOMIZATION_REALIZATION_AUTHORIZED is False
    assert protocol.STAGE_C_FINAL_REGISTRATION_AUTHORIZED is False
    record = protocol.load_frozen_inputs()
    assert record is not None
    assert record["authorizes_qualification_execution"] is False
    assert record["authorizes_confirmatory_execution"] is False
    assert record["authorizes_model_inference"] is False
    assert record["authorizes_provider_contact"] is False
    with pytest.raises(protocol.QualificationExecutionNotAuthorized):
        protocol.require_execution_authorization()


def test_the_authorization_record_states_both_human_decisions() -> None:
    """The two decisions this freeze rests on are in the citable record."""

    text = (PROJECT_ROOT / protocol.AUTHORIZATION_RECORD_RELATIVE).read_text(
        encoding="utf-8"
    )
    for clause in (
        "`RUNTIME_VERSION_RESOLUTION` | `RESTORE_FROZEN_RUNTIME`",
        "`EXPECTED_RUNTIME_VERSION` | `0.32.13`",
        "`RUNTIME_REPIN` | `NOT_AUTHORIZED`",
        "`SUCCESSOR_EXPERIMENT_CONFIG_CREATION` | `AUTHORIZED`",
        "`SUCCESSOR_EXPERIMENT_CONFIG_FREEZE` | `AUTHORIZED`",
        "`PROVIDER_CONTACT` | `NOT_AUTHORIZED`",
        "`MODEL_INFERENCE` | `NOT_AUTHORIZED`",
        "`QUALIFICATION_EXECUTION` | `NOT_AUTHORIZED`",
        "`CONFIRMATORY_EXECUTION` | `NOT_AUTHORIZED`",
    ):
        assert clause in text, clause


# ---------------------------------------------------------------------------
# The prospective seed derivation
# ---------------------------------------------------------------------------


def test_the_derivation_recomputes_exactly_and_deterministically() -> None:
    """Two independent runs agree, and agree with the committed record."""

    first, first_trail = derivation.derive_seeds()
    second, second_trail = derivation.derive_seeds()
    assert first == second
    assert [item.to_dict() for item in first_trail] == [
        item.to_dict() for item in second_trail
    ]
    assert list(protocol.SEEDS) == first
    assert len(first) == derivation.SEED_COUNT == 3

    record = json.loads(
        (PROJECT_ROOT / derivation.RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert record["seeds"] == first
    assert derivation.check_record() == []


def test_every_candidate_recomputes_from_its_material() -> None:
    """The record is auditable: each seed follows from the printed material."""

    record = json.loads(
        (PROJECT_ROOT / derivation.RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    for item in record["candidates"]:
        digest = hashlib.sha256(item["material"].encode("utf-8")).digest()
        assert digest.hex() == item["sha256"]
        assert int.from_bytes(digest[:4], "big") & 0x7FFFFFFF == item["seed"]
        assert item["material"] == derivation.candidate_material(
            item["ordinal"], item["counter"]
        )


def test_the_derivation_changes_if_the_base_sha_changes() -> None:
    """The seeds are pinned to the freeze commit, not floating."""

    other = derivation.derive_seeds(base_commit="0" * 40)[0]
    assert other != list(protocol.SEEDS)
    assert not set(other) & set(protocol.SEEDS)
    assert protocol.SEED_DERIVATION_BASE_COMMIT == protocol.CANONICAL_BASE_COMMIT


def test_the_derivation_changes_if_the_domain_separator_changes() -> None:
    """A triple derived for another purpose cannot be reused here."""

    other = derivation.derive_seeds(
        domain_separator="IQA-SOA|phase-p|pilot-v7-rc4|qa-off-real-model-qualification"
    )[0]
    assert other != list(protocol.SEEDS)
    assert protocol.SEED_DERIVATION_DOMAIN_SEPARATOR == derivation.DOMAIN_SEPARATOR


def test_no_derived_seed_collides_with_committed_history() -> None:
    """Proved against the tracked scan, not asserted."""

    record = json.loads(
        (PROJECT_ROOT / derivation.RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    checks = record["collision_checks"]
    assert checks["collision_free"] is True
    assert checks["reserved_set_covers_every_committed_seed"] is True
    assert checks["committed_seeds_not_in_reserved_set"] == []
    assert checks["derived_seeds_found_in_committed_history"] == []
    assert checks["derived_seeds_leaked_outside_successor_artifacts"] == {}
    assert checks["internal_duplicate_seeds"] == []
    assert checks["zero_valued_seeds"] == []
    assert checks["committed_seed_count"] == len(checks["committed_seeds_discovered"])
    assert set(protocol.SEEDS).isdisjoint(
        int(seed) for seed in checks["committed_seeds_discovered"]
    )


def test_no_historical_phase_p_or_phase_l_seed_is_reused() -> None:
    consumed = set(derivation.PHASE_P_SEEDS) | set(derivation.PHASE_L_SEEDS)
    assert consumed <= set(derivation.RESERVED_SEEDS)
    assert not set(protocol.SEEDS) & consumed
    assert not set(protocol.SEEDS) & set(derivation.RESERVED_SEEDS)
    assert derivation.DERIVATION_ALGORITHM_VERSION != (
        derivation.DERIVATION_METHOD_REUSED_FROM
    )


def test_a_zero_candidate_is_rejected() -> None:
    assert derivation._rejection_reason(0, [], set()) != ""
    assert "zero" in derivation._rejection_reason(0, [], set())


def test_a_duplicate_candidate_is_rejected() -> None:
    reason = derivation._rejection_reason(583010984, [583010984], set())
    assert "duplicates" in reason


def test_a_forbidden_candidate_is_rejected() -> None:
    reason = derivation._rejection_reason(1729, [], derivation.RESERVED_SEEDS)
    assert "FORBIDDEN" in reason


def test_the_counter_retry_is_deterministic_and_every_rejection_is_recorded() -> None:
    """Force collisions; the search must walk counters and record each refusal.

    The forbidden set is widened to include the real counter-0 answers, so the
    algorithm has to reject them and move on. Running it twice must produce the
    same seeds AND the same rejection trail.
    """

    widened = set(derivation.RESERVED_SEEDS) | set(protocol.SEEDS)
    first, first_trail = derivation.derive_seeds(forbidden=widened)
    second, second_trail = derivation.derive_seeds(forbidden=widened)

    assert first == second
    assert first != list(protocol.SEEDS)
    assert not set(first) & widened
    assert len(set(first)) == 3

    rejected = [item for item in first_trail if not item.accepted]
    assert len(rejected) == 3, "each ordinal's counter-0 answer must be rejected"
    for item in rejected:
        assert item.counter == 0
        assert item.rejection_reason
        assert item.seed in protocol.SEEDS
    assert [item.to_dict() for item in first_trail] == [
        item.to_dict() for item in second_trail
    ]
    for item in first_trail:
        if item.accepted:
            assert item.counter >= 1


def test_no_result_or_outcome_participates_in_the_derivation() -> None:
    """Every input is a commit SHA, a fixed string, an ordinal and a counter."""

    record = json.loads(
        (PROJECT_ROOT / derivation.RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert record["outcome_informed_seed_selection"] is False
    assert record["model_inference_performed"] is False
    assert record["model_output_influenced_derivation"] is False
    assert record["result_row_influenced_derivation"] is False
    assert record["manual_selection_performed"] is False
    assert record["provider_contacted"] is False
    assert record["successor_result_row_count_at_derivation"] == 0
    assert record["derived_before_any_successor_qualification_outcome"] is True
    assert record["canonical_base_commit"] == protocol.CANONICAL_BASE_COMMIT

    for item in record["candidates"]:
        assert item["material"].startswith(protocol.CANONICAL_BASE_COMMIT + "|")
        assert item["material"].endswith(f"|counter-{item['counter']}")


def test_the_derivation_scan_reads_no_results_namespace() -> None:
    """`results/` is excluded, and the exclusion is asserted, not assumed."""

    assert "results" in derivation.EXCLUDED_SCAN_ROOTS
    assert "results" not in derivation.SCAN_ROOTS
    for source in derivation.tracked_files():
        assert not source.startswith("results/"), source
    for forbidden in protocol.FORBIDDEN_RESULTS_NAMESPACES:
        assert not any(
            source.startswith(forbidden) for source in derivation.tracked_files()
        )


def test_the_scan_is_tracked_file_enumeration_not_a_filesystem_walk() -> None:
    """Untracked local directories cannot influence the record."""

    tracked = set(derivation.tracked_files())
    assert tracked
    for source in tracked:
        assert (PROJECT_ROOT / source).is_file()
    untracked_marker = "configs/successor-qualification.yaml"
    assert untracked_marker not in tracked or untracked_marker in (
        derivation.SUCCESSOR_ARTIFACTS
    )


def test_the_frozen_inputs_bind_the_seed_derivation_artifact() -> None:
    record = protocol.load_frozen_inputs()
    assert record is not None
    relative = protocol.SEED_DERIVATION_RECORD_RELATIVE
    assert relative in protocol.FROZEN_INPUT_PATHS
    assert relative in record["files"]
    assert "scripts/successor_derive_seeds.py" in record["files"]
    assert record["files"][relative] == hashlib.sha256(
        (PROJECT_ROOT / relative).read_bytes()
    ).hexdigest()
    assert record["seed_derivation_digest"] == derivation.derivation_digest(
        protocol.SEEDS, base_commit=protocol.SEED_DERIVATION_BASE_COMMIT
    )


def test_mutating_the_seed_derivation_artifact_fails_digest_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relative = protocol.SEED_DERIVATION_RECORD_RELATIVE
    before = (PROJECT_ROOT / relative).read_bytes()
    _mirror_bound_inputs(tmp_path)

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    record = json.loads((tmp_path / relative).read_text(encoding="utf-8"))
    record["seeds"] = [1729, 2718, 3141]
    _rewrite(
        tmp_path / relative,
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    failures = protocol.check_frozen_inputs()
    assert any(relative in item and "digests to" in item for item in failures)

    assert (PROJECT_ROOT / relative).read_bytes() == before


def test_a_tampered_seed_record_fails_the_seed_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A record claiming other seeds than the protocol binds must fail."""

    relative = protocol.SEED_DERIVATION_RECORD_RELATIVE
    before = (PROJECT_ROOT / relative).read_bytes()
    record = json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
    record["seeds"] = [1729, 2718, 3141]
    _rewrite(
        tmp_path / relative,
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_seed_derivation()
    assert failures
    assert any("the protocol binds" in item for item in failures)
    assert any("1729" in item for item in failures)

    assert (PROJECT_ROOT / relative).read_bytes() == before


def test_a_missing_seed_record_fails_the_seed_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No record means no provenance, and no provenance is a stop."""

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_seed_derivation()
    assert any("is absent" in item for item in failures)
    assert (PROJECT_ROOT / protocol.SEED_DERIVATION_RECORD_RELATIVE).is_file()


def test_the_derivation_fails_closed_without_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tree where committed history cannot be consulted proves nothing.

    The scan is refused rather than degraded into a partial one, because a
    partial scan would silently weaken the completeness proof the forbidden set
    rests on.
    """

    monkeypatch.setattr(derivation, "PROJECT_ROOT", tmp_path)
    with pytest.raises(derivation.SuccessorSeedDerivationError) as excinfo:
        derivation.tracked_files()
    assert "committed history" in str(excinfo.value)


def test_deriving_seeds_is_not_realizing_a_randomization() -> None:
    record = json.loads(
        (PROJECT_ROOT / derivation.RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert record["authorizes_execution"] is False
    assert record["authorizes_qualification_execution"] is False
    assert record["authorizes_confirmatory_execution"] is False
    assert protocol.RANDOMIZATION_REALIZATION_AUTHORIZED is False
    assert protocol.STAGE_C_FINAL_REGISTRATION_AUTHORIZED is False
    assert protocol.QUALIFICATION_EXECUTION_AUTHORIZED is False
    with pytest.raises(protocol.QualificationExecutionNotAuthorized):
        protocol.require_execution_authorization()


def test_the_authorization_record_states_the_seed_decision() -> None:
    text = (PROJECT_ROOT / protocol.AUTHORIZATION_RECORD_RELATIVE).read_text(
        encoding="utf-8"
    )
    for clause in (
        "`SUCCESSOR_PROSPECTIVE_SEED_DERIVATION` | `AUTHORIZED`",
        "`SEED_DERIVATION_ALGORITHM` | `successor-qualification-seed-derivation-1`",
        "`SEED_COUNT` | `3`",
        "`SEEDS_DERIVED_BEFORE_ANY_SUCCESSOR_QUALIFICATION_OUTCOME` | `YES`",
        "`HISTORICAL_SEED_VALUE_REUSE` | `NO`",
        "`OUTCOME_INFORMED_SEED_SELECTION` | `NO`",
    ):
        assert clause in text, clause
