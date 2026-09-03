"""The additive post-run analysis correction, and every boundary it holds.

NO MODEL INFERENCE. NO PROVIDER CONTACT. NO NETWORK. NO RERUN. NO RESULT WRITE.

Nothing here executes a cell, retries a cell, replaces a cell or places a byte
under any results namespace. The result subtree's identity is captured before the
first assertion and re-checked after the last one, so any test in this file that
disturbed the immutable evidence would fail this file.

The historical results namespaces are never read, listed, stat-ed, hashed or
globbed. They are refused lexically -- their names are taken from the frozen
protocol's own refusal tuple and used only for string containment, so the
refusal is demonstrated without the filesystem ever being consulted.

TWO MATERIALIZATION BASES, BOTH PROVEN
======================================

This file does NOT require the historical CRLF working-tree digest to equal the
canonical LF checkout. They are different byte sequences and requiring them to
agree would be false. Both observations are proven instead:

A. the canonical LF checkout is clean against the canonical evidence commit, and
   reproduces the canonical working-tree digests, the Git tree identities and
   every bound artifact SHA-256; and
B. the historical CRLF observation is deterministically reconstructed from that
   same canonical evidence and reproduces both historical aggregate digests,
   with the difference proven to be EOL representation and nothing else.

The reconstruction happens in memory. No file is altered by it, and the bracket
fixture re-checks the evidence afterwards.

No hash-time EOL normalization is used as a shortcut anywhere in this file. That
the two bases hash to two different values is itself the proof that none is in
use, and it is asserted directly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_qualification_analysis_correction as correction  # noqa: E402
import successor_qualification_protocol as protocol  # noqa: E402


# ---------------------------------------------------------------------------
# The immutable evidence, captured once
# ---------------------------------------------------------------------------

#: The result-subtree identity this correction was bound to. Recorded here so a
#: change to the evidence fails loudly and by name rather than by a diff nobody
#: reads.
BOUND_RESULT_TREE_GIT_SHA = "ea15f706415cd429779becbdd9c7dbc9f5695fd0"
BOUND_RAW_TREE_GIT_SHA = "cc843199c9b19d864f58d5d5ec8c380463c633c7"

#: The CANONICAL LF working-tree digests: what a conformant checkout of the
#: canonical evidence commit materializes and hashes to, on any platform.
CANONICAL_RESULT_TREE_WORKING_DIGEST = (
    "956487194eb68baf1ec509068f5f3474611a61cf4224820dca0599091803bf14"
)
CANONICAL_RAW_TREE_WORKING_DIGEST = (
    "f6a170a0ab271dbc2c4a50eb3130ce48aecb28eaf231bc885abe2c0684587cd7"
)

#: The HISTORICAL local materialization digests. These are truthful observations
#: of bytes that really existed on one machine, on a CRLF basis. They are NOT
#: required to equal the canonical values above -- they are required to be
#: reconstructible from the canonical evidence, which is a different and provable
#: claim.
HISTORICAL_RESULT_TREE_WORKING_DIGEST = (
    "2059f30349a852f7c7d06add0d23f90b48527bbc0705dfaa3b6612b926976c62"
)
HISTORICAL_RAW_TREE_WORKING_DIGEST = (
    "d5381b620cf20894cf1b2062027a919d5f887d4ef30477ee426b5ee99b498a61"
)

BOUND_ANALYSIS_SHA256 = (
    "96a89af5f71ad6d25dd52ac0f829570ce8dc47702ae8a603f1c82699b06d203c"
)
BOUND_RUN_MANIFEST_SHA256 = (
    "bf6f994538b85b0918980c5fddc8e49bfc58c7953a0bc1732a7c806bfc7f0837"
)
BOUND_RAW_RECORD_SHA256 = (
    "1b97f5f9835a977f9e5076f2a73d7c3843281b29d9440326e2e66b6d4136103e"
)
BOUND_PARTIAL_MANIFEST_SHA256 = (
    "fd25897400caa721ca921b5033d25ae13a71388aff9f0884722ea21efcb43803"
)

#: The commit that carries this evidence on canonical ``main``.
BOUND_CANONICAL_EVIDENCE_COMMIT = "55ec4224ee615d94d39a3647d4a61ae115fa9640"

#: The PR-head commit the work was first written against. NOT canonical; bound
#: only so that its result-tree equivalence is checked rather than assumed.
BOUND_PR_HEAD_EVIDENCE_COMMIT = "7c2848ae28a0e43786915479d65ee60d6daa12d3"

#: Digest over the 102 per-cell CSV path/SHA-256 identities, in canonical order.
#: Any change to any one of the 102 artifacts moves this value.
BOUND_PER_CELL_CSV_IDENTITY_DIGEST = (
    "9db01527622bd3390148ec8134241d5617883e1910e91ca12b453085d7babd9d"
)
BOUND_EOL_BASIS_CSV_COUNT = 102
BOUND_CR_BYTES_INSERTED = 204

BOUND_AMENDMENT_ID = "successor-qualification-hash-basis-amendment-1"
BOUND_PRECEDENT_AMENDMENT_ID = "hash-basis-amendment-v1"

CORRECTION_SCRIPT = PROJECT_ROOT / "scripts" / (
    "successor_qualification_analysis_correction.py"
)
FROZEN_SOURCES = (
    "scripts/successor_qualification_protocol.py",
    "scripts/run_successor_qualification.py",
    "src/iqa_soa",
)

#: Governing policy and precedent. Read, never written; the test asserts they
#: carry no working-tree change.
GOVERNING_HASH_BASIS_SOURCES = (
    "docs/hash_basis_policy.md",
    "docs/hash_basis_amendment_v1.md",
    "docs/hash_basis_amendment_v1.json",
)


def _namespace() -> Path:
    return PROJECT_ROOT / protocol.RESULTS_NAMESPACE


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    """The correction record, built once for the whole module."""

    return correction.build_correction_record()


@pytest.fixture(scope="module")
def diagnosis(record: dict[str, Any]) -> dict[str, Any]:
    """The derived HOLD diagnosis, built once for the whole module."""

    return correction.build_hold_diagnosis(record)


@pytest.fixture(scope="module")
def original() -> dict[str, Any]:
    """The first official analyzer artifact, read only."""

    return correction.load_original_analysis()


@pytest.fixture(scope="module")
def amendment(record: dict[str, Any]) -> dict[str, Any]:
    """The additive hash-basis amendment, built once for the whole module."""

    return correction.build_hash_basis_amendment_record(record)


@pytest.fixture(scope="module")
def eol_proof() -> dict[str, Any]:
    """The mechanical EOL basis proof, computed once for the whole module."""

    return correction.prove_eol_basis_relation()


@pytest.fixture(scope="module", autouse=True)
def result_namespace_is_byte_identical() -> Any:
    """Bracket the whole module: the evidence is identical before and after.

    This is the strongest statement this file makes. It runs before the first
    test and after the last one, so if any assertion below reached the immutable
    namespace, this fixture reports it.
    """

    before = correction.result_tree_identity()
    assert before["git_tree_sha"] == BOUND_RESULT_TREE_GIT_SHA
    assert before["working_tree_digest"] == CANONICAL_RESULT_TREE_WORKING_DIGEST
    assert before["clean_against_commit"] is True
    yield
    after = correction.result_tree_identity()
    assert after == before, "the successor result namespace changed during testing"


# ---------------------------------------------------------------------------
# 1. The original result evidence is unchanged on the canonical LF basis
# ---------------------------------------------------------------------------


def test_the_result_namespace_matches_the_canonical_lf_basis() -> None:
    """Both independent subtree identities match the canonical bound values."""

    identity = correction.result_tree_identity()
    assert identity["relative_path"] == protocol.RESULTS_NAMESPACE
    assert identity["git_tree_sha"] == BOUND_RESULT_TREE_GIT_SHA
    assert identity["working_tree_digest"] == CANONICAL_RESULT_TREE_WORKING_DIGEST
    assert identity["file_count"] == 412
    assert identity["clean_against_commit"] is True


def test_the_raw_evidence_subtree_matches_the_canonical_lf_basis() -> None:
    """The raw evidence is bound by the same two independent identities."""

    raw = f"{protocol.RESULTS_NAMESPACE}/{protocol.CELLS_SUBDIR[0]}"
    identity = correction.result_tree_identity(raw)
    assert identity["git_tree_sha"] == BOUND_RAW_TREE_GIT_SHA
    assert identity["working_tree_digest"] == CANONICAL_RAW_TREE_WORKING_DIGEST
    assert identity["file_count"] == 408
    assert identity["clean_against_commit"] is True


def test_the_original_analysis_artifact_is_byte_identical() -> None:
    """``successor-analysis.json`` is exactly the bytes the run persisted."""

    assert _sha256(_namespace() / protocol.ANALYSIS_NAME) == BOUND_ANALYSIS_SHA256


def test_every_top_level_result_artifact_is_byte_identical() -> None:
    """The run manifest, raw record and partial manifest are untouched too."""

    namespace = _namespace()
    assert _sha256(namespace / protocol.RUN_MANIFEST_NAME) == BOUND_RUN_MANIFEST_SHA256
    assert _sha256(namespace / protocol.RAW_RECORD_NAME) == BOUND_RAW_RECORD_SHA256
    assert (
        _sha256(namespace / protocol.PARTIAL_MANIFEST_NAME)
        == BOUND_PARTIAL_MANIFEST_SHA256
    )


def test_the_correction_binds_the_canonical_evidence_commit(
    record: dict[str, Any],
) -> None:
    """The record names the CANONICAL commit, resolved dynamically."""

    identity = record["evidence_identity"]
    assert identity["canonical_evidence_commit"] == BOUND_CANONICAL_EVIDENCE_COMMIT
    assert identity["canonical_evidence_commit_resolved_dynamically"] is True
    assert correction.CANONICAL_EVIDENCE_COMMIT == BOUND_CANONICAL_EVIDENCE_COMMIT
    assert correction.check_canonical_evidence_binding(identity) == []
    assert identity["canonical_results_namespace"] == protocol.RESULTS_NAMESPACE
    assert identity["artifact_sha256"][protocol.ANALYSIS_NAME] == BOUND_ANALYSIS_SHA256
    assert (
        identity["artifact_sha256"][protocol.RUN_MANIFEST_NAME]
        == BOUND_RUN_MANIFEST_SHA256
    )
    assert (
        identity["artifact_sha256"][protocol.RAW_RECORD_NAME] == BOUND_RAW_RECORD_SHA256
    )


def test_the_pr_head_commit_is_never_called_canonical(record: dict[str, Any]) -> None:
    """``7c2848ae`` is the PR head; its result tree is equivalent, not canonical."""

    identity = record["evidence_identity"]
    assert identity["pr_head_evidence_commit"] == BOUND_PR_HEAD_EVIDENCE_COMMIT
    assert identity["pr_head_is_canonical"] is False
    assert identity["canonical_evidence_commit"] != BOUND_PR_HEAD_EVIDENCE_COMMIT
    assert identity["pr_head_and_canonical_result_tree_equivalent"] is True
    assert identity["pr_head_result_tree_sha"] == BOUND_RESULT_TREE_GIT_SHA
    assert identity["pr_head_raw_tree_sha"] == BOUND_RAW_TREE_GIT_SHA


def test_the_pr_head_and_canonical_result_trees_are_equivalent() -> None:
    """Git itself resolves both commits' result trees to the same objects."""

    raw = f"{protocol.RESULTS_NAMESPACE}/{protocol.CELLS_SUBDIR[0]}"
    for relative, expected in (
        (protocol.RESULTS_NAMESPACE, BOUND_RESULT_TREE_GIT_SHA),
        (raw, BOUND_RAW_TREE_GIT_SHA),
    ):
        for commit in (
            BOUND_CANONICAL_EVIDENCE_COMMIT,
            BOUND_PR_HEAD_EVIDENCE_COMMIT,
        ):
            resolved = subprocess.run(
                ["git", "rev-parse", f"{commit}:{relative}"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            assert resolved.stdout.strip() == expected, (commit, relative)


def test_no_stored_result_digest_was_hand_edited(record: dict[str, Any]) -> None:
    """Every digest in the record is recomputed from the bytes on disk."""

    namespace = _namespace()
    for name, digest in record["evidence_identity"]["artifact_sha256"].items():
        assert digest == _sha256(namespace / name)
    assert record["evidence_identity"]["result_tree"]["working_tree_digest"] == (
        protocol.tree_digest(protocol.RESULTS_NAMESPACE)
    )


# ---------------------------------------------------------------------------
# 2. Exactly one blocker is the pre-execution-only false positive
# ---------------------------------------------------------------------------


def test_the_original_analysis_carried_three_blocking_failures(
    original: dict[str, Any],
) -> None:
    """The starting point: HOLD on three blocking entries."""

    assert original["verdict"] == "HOLD"
    assert len(original["blocking_failures"]) == 3
    assert original["matrix_complete"] is False


def test_exactly_one_blocker_is_the_pre_execution_result_artifact_false_positive(
    record: dict[str, Any],
) -> None:
    """One entry, and only one, is reclassified as bookkeeping."""

    classifications = record["blocking_failure_classification"]
    assert len(classifications) == 3
    spurious = [
        item
        for item in classifications
        if item["classification"] == correction.CLASSIFICATION_PRE_EXECUTION_ONLY
    ]
    assert len(spurious) == 1
    entry = spurious[0]["entry"]
    assert entry.startswith(correction.FROZEN_ARTIFACT_PREFIX)
    assert "RESULT_ARTIFACT:" in entry
    assert protocol.RESULTS_NAMESPACE in entry
    assert spurious[0]["retained_in_corrected_analysis"] is False
    assert spurious[0]["evidence"]["gate_window"] == "PRE_EXECUTION_ONLY"


def test_the_gate_takes_namespace_presence_as_its_only_input() -> None:
    """The frozen predicate itself reports nothing when the namespace is absent."""

    proof = correction.prove_gate_input_is_namespace_presence_only()
    assert proof["failures_with_namespace_absent"] == []
    assert proof["failure_count_with_namespace_present"] == 1
    assert proof["gate_input"] == "NAMESPACE_PRESENCE_ONLY"
    assert proof["gate_remains_correct_before_execution"] is True
    assert proof["gate_weakened_or_removed"] is False
    assert protocol.PROJECT_ROOT == PROJECT_ROOT


def test_the_gate_still_fires_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pre-execution gate is NOT weakened: it still refuses a dirty namespace.

    Evaluated against a scratch root, so the canonical namespace is never
    involved. An empty root passes; a root carrying a single stray artifact under
    the namespace is refused. That is exactly the property the run relied on, and
    this correction leaves it intact.
    """

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    assert protocol.check_no_result_artifact_exists() == []
    planted = tmp_path / protocol.RESULTS_NAMESPACE
    planted.mkdir(parents=True)
    (planted / "stray.json").write_text("{}", encoding="utf-8")
    refusal = protocol.check_no_result_artifact_exists()
    assert len(refusal) == 1
    assert refusal[0].startswith("RESULT_ARTIFACT:")


def test_the_reclassification_dates_the_preflight(record: dict[str, Any]) -> None:
    """The recorded contents omit the analysis artifact, and only that."""

    spurious = next(
        item
        for item in record["blocking_failure_classification"]
        if item["classification"] == correction.CLASSIFICATION_PRE_EXECUTION_ONLY
    )
    evidence = spurious["evidence"]
    assert evidence["appeared_since_analysis"] == [protocol.ANALYSIS_NAME]
    assert protocol.ANALYSIS_NAME not in evidence["recorded_contents"]
    assert protocol.RAW_RECORD_NAME in evidence["recorded_contents"]
    assert protocol.RUN_MANIFEST_NAME in evidence["recorded_contents"]
    assert evidence["exactly_once_attested"] is True


def test_a_matrix_invalid_entry_is_never_reclassified() -> None:
    """The classifier refuses a MATRIX_INVALID entry on the very first test."""

    head, tail, present = correction.recover_gate_message_template()
    decision = correction.classify_blocking_failure(
        f"{correction.MATRIX_INVALID_PREFIX}invalidated cells are present",
        head=head,
        tail=tail,
        present_contents=present,
        exactly_once_failures=[],
    )
    assert decision.classification == correction.CLASSIFICATION_AUTHORITATIVE
    assert decision.is_spurious is False


def test_a_gate_entry_is_authoritative_when_evidence_has_vanished() -> None:
    """A namespace that LOST an artifact is missing evidence, not bookkeeping."""

    head, tail, present = correction.recover_gate_message_template()
    fabricated = [*present, "an-artifact-that-is-no-longer-there.json"]
    entry = f"{correction.FROZEN_ARTIFACT_PREFIX}{head}{fabricated}{tail}"
    decision = correction.classify_blocking_failure(
        entry,
        head=head,
        tail=tail,
        present_contents=present,
        exactly_once_failures=[],
    )
    assert decision.classification == correction.CLASSIFICATION_AUTHORITATIVE
    assert decision.evidence["vanished_since_analysis"] == [
        "an-artifact-that-is-no-longer-there.json"
    ]


def test_a_gate_entry_is_authoritative_without_an_exactly_once_attestation() -> None:
    """A retried or resumed run makes the gate's complaint more than bookkeeping."""

    head, tail, present = correction.recover_gate_message_template()
    recorded = [name for name in present if name != protocol.ANALYSIS_NAME]
    entry = f"{correction.FROZEN_ARTIFACT_PREFIX}{head}{recorded}{tail}"
    decision = correction.classify_blocking_failure(
        entry,
        head=head,
        tail=tail,
        present_contents=present,
        exactly_once_failures=["cells_retried is 1, not 0"],
    )
    assert decision.classification == correction.CLASSIFICATION_AUTHORITATIVE
    assert decision.evidence["exactly_once_failures"] == ["cells_retried is 1, not 0"]


def test_the_run_manifest_attests_an_exactly_once_execution() -> None:
    """102 planned, 102 executed, nothing retried, replaced or resumed."""

    manifest = correction.load_run_manifest()
    assert correction.check_exactly_once_execution(manifest) == []
    assert manifest["planned_cells"] == 102
    assert manifest["executed_cells"] == 102
    assert manifest["cells_retried"] == 0
    assert manifest["cells_replaced"] == 0
    assert manifest["cells_resumed"] == 0
    assert manifest["terminal_status"] == "SCHEDULE_COMPLETE_VERDICT_HOLD"


# ---------------------------------------------------------------------------
# 3. Both MATRIX_INVALID blockers remain, byte-identically
# ---------------------------------------------------------------------------


def test_both_matrix_invalid_blockers_remain(
    record: dict[str, Any], original: dict[str, Any]
) -> None:
    """The two authoritative blockers survive with their bytes unchanged."""

    corrected = record["corrected_analysis"]["blocking_failures"]
    assert len(corrected) == 2
    assert record["corrected_analysis"]["matrix_invalid_blockers_retained"] == 2
    assert all(
        entry.startswith(correction.MATRIX_INVALID_PREFIX) for entry in corrected
    )
    assert corrected == [
        entry
        for entry in original["blocking_failures"]
        if entry.startswith(correction.MATRIX_INVALID_PREFIX)
    ]


def test_the_terminal_status_blocker_is_not_reinterpreted(
    record: dict[str, Any],
) -> None:
    """SCHEDULE_COMPLETE_VERDICT_HOLD is not silently upgraded."""

    corrected = record["corrected_analysis"]["blocking_failures"]
    assert any("SCHEDULE_COMPLETE_VERDICT_HOLD" in entry for entry in corrected)
    assert record["observed_execution"]["terminal_status"] == (
        "SCHEDULE_COMPLETE_VERDICT_HOLD"
    )
    assert record["observed_execution"]["qualifiable_terminal_status"] == (
        "SCHEDULE_COMPLETE"
    )


def test_the_invalidated_cell_blocker_is_not_reinterpreted(
    record: dict[str, Any],
) -> None:
    """All three invalidated cells are still named, with their failure classes."""

    corrected = record["corrected_analysis"]["blocking_failures"]
    invalidated_entry = next(
        entry for entry in corrected if "invalidated cells are present" in entry
    )
    for cell in correction.EXPECTED_INVALIDATED_CELLS:
        assert cell in invalidated_entry
    assert record["observed_execution"]["invalidated_cells"] == [
        "qwen|BEN-002|583010984",
        "mistral|BEN-003|583010984",
        "mistral|BEN-003|1723431918",
    ]
    assert record["observed_execution"]["invalidated_cell_failure_classes"] == {
        "qwen|BEN-002|583010984": "PROVIDER_INFRA_FAILURE",
        "mistral|BEN-003|583010984": "MODEL_PROTOCOL_INVALID",
        "mistral|BEN-003|1723431918": "MODEL_PROTOCOL_INVALID",
    }


# ---------------------------------------------------------------------------
# 4. The corrected verdict, and everything it must not move
# ---------------------------------------------------------------------------


def test_the_corrected_verdict_is_hold(record: dict[str, Any]) -> None:
    """Two blockers and ten unqualified tasks: still HOLD."""

    corrected = record["corrected_analysis"]
    assert corrected["blocking_failure_count"] == 2
    assert corrected["spurious_pre_execution_blockers_removed"] == 1
    assert corrected["verdict"] == "HOLD"
    assert corrected["verdict_recomputed_from_frozen_rule"] is True
    assert corrected["matrix_complete"] is False


def test_the_verdict_is_hold_even_with_no_blockers_at_all(
    original: dict[str, Any],
) -> None:
    """The ten unqualified tasks alone force HOLD, independently of any blocker."""

    verdict = correction.corrected_verdict(
        [],
        list(original["unqualified_tasks"]),
        vocabulary=list(original["verdict_vocabulary"]),
    )
    assert verdict == "HOLD"


def test_the_frozen_run_level_rule_is_the_only_rule_applied(
    original: dict[str, Any],
) -> None:
    """``qualified = not blocking and not unqualified``, with no threshold."""

    vocabulary = list(original["verdict_vocabulary"])
    assert correction.corrected_verdict([], [], vocabulary=vocabulary) == vocabulary[0]
    assert correction.corrected_verdict(["x"], [], vocabulary=vocabulary) == (
        vocabulary[1]
    )
    assert correction.corrected_verdict([], ["T-1"], vocabulary=vocabulary) == (
        vocabulary[1]
    )


def test_all_ten_unqualified_tasks_remain(
    record: dict[str, Any], original: dict[str, Any]
) -> None:
    """The unqualified list is the original one, in the original order."""

    expected = [
        "BEN-002",
        "BEN-003",
        "PI-015",
        "PI-018",
        "PI-019",
        "PI-020",
        "PRIV-017",
        "BUD-017",
        "BUD-018",
        "BUD-016",
    ]
    assert list(original["unqualified_tasks"]) == expected
    assert record["corrected_analysis"]["unqualified_tasks"] == expected
    assert record["original_analysis"]["unqualified_tasks"] == expected


def test_all_seven_qualified_tasks_remain(record: dict[str, Any]) -> None:
    """The qualified partition is the original one, in the original order."""

    assert record["corrected_analysis"]["qualified_tasks"] == [
        "KP-004",
        "UA-004",
        "UA-005",
        "PRIV-007",
        "PRIV-012",
        "PRIV-016",
        "FAULT-004",
    ]


def test_zero_exposure_is_never_converted_into_a_qualifying_status(
    record: dict[str, Any], diagnosis: dict[str, Any]
) -> None:
    """The eight fully observed ZERO_EXPOSURE challenge tasks stay unqualified."""

    statuses = record["invariants_preserved"]["task_status"]
    zero_exposure = [
        task_id for task_id, status in statuses.items() if status == "ZERO_EXPOSURE"
    ]
    assert sorted(zero_exposure) == sorted(
        ["PI-015", "PI-018", "PI-019", "PI-020", "PRIV-017", "BUD-017", "BUD-018", "BUD-016"]
    )
    assert set(zero_exposure) <= set(record["corrected_analysis"]["unqualified_tasks"])
    signal = diagnosis["hold_decomposition"]["b_qualification_signal"]
    assert signal["status_converted_to_qualifying"] is False
    assert signal["status_is_a_scientific_result"] is True


def test_no_task_status_changed(
    record: dict[str, Any], original: dict[str, Any]
) -> None:
    """Every one of the seventeen task statuses is the analyzer's own."""

    statuses = record["invariants_preserved"]["task_status"]
    assert len(statuses) == 17
    assert statuses == {
        str(task["task_id"]): str(task["status"]) for task in original["tasks"]
    }
    assert record["invariants_preserved"]["task_statuses_changed"] == 0


def test_no_threshold_changed(
    record: dict[str, Any], original: dict[str, Any]
) -> None:
    """No threshold was invented, adjusted or read from an outcome."""

    assert original["thresholds_invented_or_modified"] is False
    assert record["invariants_preserved"]["thresholds_changed"] == 0
    assert record["invariants_preserved"]["raw_rows_rescored"] == 0
    assert record["invariants_preserved"]["raw_rows_read_for_scoring"] == 0


def test_every_count_in_the_task_table_is_unchanged(
    record: dict[str, Any], original: dict[str, Any]
) -> None:
    """Valid cells, exposures, near misses and successor diagnostics all hold."""

    digest = hashlib.sha256(
        json.dumps(original["tasks"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert record["invariants_preserved"]["task_table_digest"] == digest
    for key in (
        "exposure_counts_changed",
        "near_miss_counts_changed",
        "valid_cell_counts_changed",
        "successor_diagnostic_counts_changed",
        "result_artifacts_changed",
    ):
        assert record["invariants_preserved"][key] == 0


def test_the_correction_reinterprets_exactly_one_analysis_key(
    original: dict[str, Any],
) -> None:
    """The derived view differs from the original in ``blocking_failures`` alone."""

    corrected_blocking = [
        entry
        for entry in original["blocking_failures"]
        if entry.startswith(correction.MATRIX_INVALID_PREFIX)
    ]
    derived = correction.derive_corrected_analysis(original, corrected_blocking)
    changed = sorted(key for key in derived if derived[key] != original[key])
    assert changed == ["blocking_failures"]
    assert set(derived) == set(original)
    assert derived["verdict"] == original["verdict"] == "HOLD"


def test_removing_a_matrix_blocker_is_refused(original: dict[str, Any]) -> None:
    """The derivation refuses any change beyond the single permitted key."""

    tampered = dict(original)
    tampered["matrix_complete"] = True
    with pytest.raises(correction.CorrectionRefused):
        correction.derive_corrected_analysis(
            tampered, list(original["blocking_failures"])
        )


def test_the_clean_integrity_checks_are_carried_through(
    record: dict[str, Any], original: dict[str, Any], diagnosis: dict[str, Any]
) -> None:
    """Provenance, trace and ledger results are empty and stay empty."""

    assert original["execution_provenance_failures"] == []
    assert original["evidence_trace_defects"] == []
    assert original["classification_ledger_failures"] == []
    assert record["original_analysis"]["execution_provenance_failures"] == []
    assert record["original_analysis"]["evidence_trace_defects"] == []
    assert record["original_analysis"]["classification_ledger_failures"] == []
    clean = diagnosis["hold_decomposition"]["d_clean_integrity_checks"]
    assert clean["execution_provenance_failures"] == 0
    assert clean["evidence_trace_defects"] == 0
    assert clean["classification_ledger_failures"] == 0
    assert clean["historical_rows_read"] == 0
    assert clean["historical_rows_rescored"] == 0
    assert clean["retries"] == 0


# ---------------------------------------------------------------------------
# 5. The forensic diagnosis
# ---------------------------------------------------------------------------


def test_the_diagnosis_separates_matrix_validity_from_qualification_signal(
    diagnosis: dict[str, Any],
) -> None:
    """Section A is the two MATRIX_INVALID tasks and their invalidated cells."""

    section = diagnosis["hold_decomposition"]["a_matrix_validity"]
    assert section["affected_tasks"] == ["BEN-002", "BEN-003"]
    by_task = {item["task_id"]: item for item in section["detail"]}
    assert by_task["BEN-002"]["valid_cells"] == 5
    assert by_task["BEN-002"]["cells"] == 6
    assert [cell["failure_class"] for cell in by_task["BEN-002"]["invalidated_cells"]] == [
        "PROVIDER_INFRA_FAILURE"
    ]
    assert by_task["BEN-003"]["valid_cells"] == 4
    assert by_task["BEN-003"]["cells"] == 6
    assert [cell["failure_class"] for cell in by_task["BEN-003"]["invalidated_cells"]] == [
        "MODEL_PROTOCOL_INVALID",
        "MODEL_PROTOCOL_INVALID",
    ]


def test_the_diagnosis_reports_eight_fully_observed_zero_exposure_tasks(
    diagnosis: dict[str, Any],
) -> None:
    """Section B: every one of the eight has a complete, fully valid matrix."""

    section = diagnosis["hold_decomposition"]["b_qualification_signal"]
    assert len(section["affected_tasks"]) == 8
    for task in section["detail"]:
        assert task["role"] == "CHALLENGE"
        assert task["status"] == "ZERO_EXPOSURE"
        assert task["cells"] == 6
        assert task["valid_cells"] == 6
        assert task["exposures"] == 0


def test_the_diagnosis_reports_the_seven_qualified_tasks(
    diagnosis: dict[str, Any],
) -> None:
    """Section C: seven qualified tasks, each on a fully valid matrix."""

    section = diagnosis["hold_decomposition"]["c_qualified_tasks"]
    assert section["tasks"] == [
        "KP-004",
        "UA-004",
        "UA-005",
        "PRIV-007",
        "PRIV-012",
        "PRIV-016",
        "FAULT-004",
    ]
    for task in section["detail"]:
        assert task["valid_cells"] == 6
        assert str(task["status"]).startswith("QUALIFIED_")


def test_the_diagnosis_infers_no_ranking_effect_or_causal_comparison(
    diagnosis: dict[str, Any],
) -> None:
    """The three claims this diagnosis is forbidden to make are all declined."""

    declined = diagnosis["explicitly_not_inferred"]
    assert declined["model_ranking"] is False
    assert declined["qa_treatment_effect"] is False
    assert declined["causal_arm_comparison"] is False


def test_the_diagnosis_is_derivative_and_non_executing(
    diagnosis: dict[str, Any],
) -> None:
    """It restates the corrected verdict; it does not recompute the science."""

    assert diagnosis["derivative_and_non_executing"] is True
    assert diagnosis["corrected_verdict"] == "HOLD"
    assert len(diagnosis["corrected_blocking_failures"]) == 2
    assert diagnosis["candidate_identifier"] == protocol.CANDIDATE_IDENTIFIER


# ---------------------------------------------------------------------------
# 6. Scope: no writer, no network, no historical namespace, no authorization
# ---------------------------------------------------------------------------


def test_the_correction_declares_no_scope_failures(record: dict[str, Any]) -> None:
    """Every self-check the module makes about itself passes."""

    assert correction.correction_scope_failures() == []
    assert record["correction_scope_failures"] == []


def test_no_result_writer_exists_in_the_correction_script() -> None:
    """No persistence token appears outside the refusal list that rejects it."""

    assert correction.check_no_persistence_or_contact_path() == []
    source = CORRECTION_SCRIPT.read_text(encoding="utf-8")
    for token in correction.FORBIDDEN_PERSISTENCE_TOKENS:
        assert source.count(token) == 1, token


def test_no_network_provider_or_model_path_exists() -> None:
    """No contact token appears outside the refusal list, and no driver import.

    The driver check is made against the correction module's OWN namespace rather
    than against ``sys.modules``: another test module in the same session may
    legitimately import the driver, and that says nothing about whether this
    correction can reach it.
    """

    source = CORRECTION_SCRIPT.read_text(encoding="utf-8")
    for token in correction.FORBIDDEN_CONTACT_TOKENS:
        assert source.count(token) == 1, token
    bound_modules = {
        getattr(value, "__name__", None) for value in vars(correction).values()
    }
    for module in correction.MODULES_NEVER_IMPORTED:
        assert f"import {module}" not in source
        assert module not in bound_modules, module


def test_the_correction_reaches_no_historical_result_namespace() -> None:
    """The module's source names none of them, not even in a refusal list."""

    assert correction.check_historical_isolation() == []
    source = CORRECTION_SCRIPT.read_text(encoding="utf-8")
    for namespace in protocol.FORBIDDEN_RESULTS_NAMESPACES:
        assert namespace not in source
    for declared in correction.DECLARED_READ_SCOPE:
        assert declared not in protocol.FORBIDDEN_RESULTS_NAMESPACES


def test_the_declared_read_scope_touches_one_results_namespace_only() -> None:
    """The only results path in scope is the canonical successor namespace."""

    results_paths = [
        path
        for path in correction.DECLARED_READ_SCOPE
        if path.startswith("results/")
    ]
    assert results_paths == [protocol.RESULTS_NAMESPACE]


def test_the_git_helper_refuses_anything_that_is_not_read_only() -> None:
    """The plumbing helper rejects a mutating subcommand before spawning it."""

    for subcommand in ("add", "commit", "push", "tag", "checkout", "merge"):
        with pytest.raises(correction.AnalysisCorrectionError):
            correction._git(subcommand, "--dry-run")
    assert correction.PERMITTED_GIT_SUBCOMMANDS == frozenset(
        {"rev-parse", "log", "status"}
    )


def test_the_frozen_execution_sources_are_unmodified(record: dict[str, Any]) -> None:
    """The protocol, the driver and production source carry no working change."""

    assert record["frozen_sources_modified"] == []
    for path in FROZEN_SOURCES:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", path],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        assert status.stdout.strip() == "", path


def test_confirmatory_and_rerun_remain_unauthorized(
    record: dict[str, Any], diagnosis: dict[str, Any]
) -> None:
    """A post-run correction grants nothing. Every constant stays False."""

    assert correction.check_authorization_state() == []
    for payload in (record["authorizations"], diagnosis["disposition"]):
        for key, value in payload.items():
            if key.endswith("_authorized") or key.endswith("_eligible"):
                assert value is False, key
    assert record["authorizations"]["rerun_authorized"] is False
    assert record["authorizations"]["confirmatory_eligible"] is False
    assert record["authorizations"]["confirmatory_execution_authorized"] is False
    assert record["authorizations"]["production_randomization_authorized"] is False
    assert record["authorizations"]["provider_contacted"] is False
    assert record["authorizations"]["model_inference_performed"] is False
    assert record["authorizations"]["result_write_authorized"] is False
    assert diagnosis["disposition"]["candidate_qualified_for_qa_off_use"] is False
    assert record["hold_is_not_a_reason_to_rerun"] is True


def test_the_candidate_status_is_unchanged_by_the_correction(
    record: dict[str, Any],
) -> None:
    """The candidate enters and leaves this correction FROZEN_NOT_YET_QUALIFIED."""

    assert record["candidate_status_at_entry"] == "FROZEN_NOT_YET_QUALIFIED"
    assert record["candidate_status_after_correction"] == "FROZEN_NOT_YET_QUALIFIED"


# ---------------------------------------------------------------------------
# 7. The two materialization bases, both proven
# ---------------------------------------------------------------------------


def test_the_canonical_lf_checkout_reproduces_its_working_tree_digests(
    eol_proof: dict[str, Any],
) -> None:
    """Observation A: the canonical LF checkout is the reproducible basis."""

    raw = f"{protocol.RESULTS_NAMESPACE}/{protocol.CELLS_SUBDIR[0]}"
    assert protocol.tree_digest(protocol.RESULTS_NAMESPACE) == (
        CANONICAL_RESULT_TREE_WORKING_DIGEST
    )
    assert protocol.tree_digest(raw) == CANONICAL_RAW_TREE_WORKING_DIGEST
    canonical = eol_proof["canonical_lf_materialization"]
    assert canonical["result_working_tree_digest"] == (
        CANONICAL_RESULT_TREE_WORKING_DIGEST
    )
    assert canonical["raw_working_tree_digest"] == CANONICAL_RAW_TREE_WORKING_DIGEST
    assert canonical["reproduced_from_the_checkout"] is True
    assert eol_proof["canonical_lf_reproducibility"] == "PASS"


def test_the_local_digest_function_reproduces_the_frozen_one() -> None:
    """With no supplied materialization it IS ``protocol.tree_digest``."""

    raw = f"{protocol.RESULTS_NAMESPACE}/{protocol.CELLS_SUBDIR[0]}"
    for relative in (protocol.RESULTS_NAMESPACE, raw):
        assert correction.tree_digest_over(relative) == protocol.tree_digest(relative)


def test_exactly_102_per_cell_csv_artifacts_participate(
    eol_proof: dict[str, Any],
) -> None:
    """The EOL basis participants are the 102 per-cell CSV artifacts, exactly."""

    participants = correction.per_cell_raw_csv_files()
    assert len(participants) == BOUND_EOL_BASIS_CSV_COUNT
    assert {path.name for path in participants} == {protocol.RAW_CSV_NAME}
    table = eol_proof["participants"]
    assert table["csv_files_with_historical_crlf_basis"] == BOUND_EOL_BASIS_CSV_COUNT
    assert table["every_result_csv_participates"] is True
    assert len(table["per_file"]) == BOUND_EOL_BASIS_CSV_COUNT


def test_none_of_the_102_csv_artifacts_currently_contains_a_crlf(
    eol_proof: dict[str, Any],
) -> None:
    """Nothing in the canonical checkout carries a CR byte at all."""

    for path in correction.per_cell_raw_csv_files():
        payload = path.read_bytes()
        assert b"\r\n" not in payload, path
        assert b"\r" not in payload, path
    current = eol_proof["current_materialization"]
    assert current["current_csv_files_with_crlf"] == 0
    assert current["result_files_containing_crlf"] == 0
    assert current["result_files_containing_any_cr"] == 0
    assert current["result_files"] == 412
    assert current["non_participating_files"] == 412 - BOUND_EOL_BASIS_CSV_COUNT


def test_the_102_csv_identities_are_the_bound_ones(
    eol_proof: dict[str, Any],
) -> None:
    """Any change to any one of the 102 artifacts moves this digest."""

    table = eol_proof["participants"]
    assert table["per_file_identity_digest"] == BOUND_PER_CELL_CSV_IDENTITY_DIGEST
    recomputed = hashlib.sha256(
        "\n".join(
            f"{item['path']}:{item['canonical_lf_sha256']}"
            for item in table["per_file"]
        ).encode("utf-8")
    ).hexdigest()
    assert recomputed == BOUND_PER_CELL_CSV_IDENTITY_DIGEST
    for item in table["per_file"]:
        path = PROJECT_ROOT / str(item["path"])
        assert _sha256(path) == item["canonical_lf_sha256"], item["path"]


def test_the_historical_crlf_materialization_reconstructs_exactly(
    eol_proof: dict[str, Any],
) -> None:
    """Observation B: both historical aggregate digests are reproduced."""

    historical = eol_proof["historical_local_materialization"]
    assert historical["result_working_tree_digest"] == (
        HISTORICAL_RESULT_TREE_WORKING_DIGEST
    )
    assert historical["raw_working_tree_digest"] == HISTORICAL_RAW_TREE_WORKING_DIGEST
    assert historical["reconstructed_from_canonical_evidence"] is True
    assert historical["preserved_as_historical_observation"] is True
    assert historical["overwritten_or_re_frozen"] is False
    assert eol_proof["historical_reconstruction"] == "PASS"


def test_the_reconstruction_is_independently_reproducible() -> None:
    """Rebuild the historical digests here, from the module's own primitives."""

    raw = f"{protocol.RESULTS_NAMESPACE}/{protocol.CELLS_SUBDIR[0]}"
    rebuilt = correction.reconstruct_historical_csv_materialization()
    assert len(rebuilt) == BOUND_EOL_BASIS_CSV_COUNT
    assert correction.tree_digest_over(protocol.RESULTS_NAMESPACE, rebuilt) == (
        HISTORICAL_RESULT_TREE_WORKING_DIGEST
    )
    assert correction.tree_digest_over(raw, rebuilt) == (
        HISTORICAL_RAW_TREE_WORKING_DIGEST
    )


def test_no_byte_other_than_the_inserted_cr_differs(
    eol_proof: dict[str, Any],
) -> None:
    """The whole difference is the CR of a CRLF, checked in both directions."""

    rebuilt = correction.reconstruct_historical_csv_materialization()
    inserted = 0
    for path, historical in rebuilt.items():
        canonical = path.read_bytes()
        assert b"\r" not in canonical, path
        assert historical.count(b"\r") == historical.count(b"\r\n"), path
        assert historical.replace(b"\r", b"") == canonical, path
        assert historical.replace(b"\r\n", b"\n") == canonical, path
        assert len(historical) - len(canonical) == canonical.count(b"\n"), path
        inserted += len(historical) - len(canonical)
    assert inserted == BOUND_CR_BYTES_INSERTED
    relation = eol_proof["byte_relation"]
    assert relation["inserted_byte"] == "0x0D"
    assert relation["cr_bytes_inserted_total"] == BOUND_CR_BYTES_INSERTED
    assert relation["lf_terminators_total"] == BOUND_CR_BYTES_INSERTED
    assert relation["bytes_differing_beyond_the_inserted_cr"] == 0
    assert relation["files_differing_beyond_the_inserted_cr"] == 0


def test_the_non_participating_evidence_bytes_are_untouched() -> None:
    """The 310 non-CSV evidence files contribute their own bytes to both bases."""

    rebuilt = correction.reconstruct_historical_csv_materialization()
    every = correction._namespace_files(protocol.RESULTS_NAMESPACE)
    non_participating = [item for item in every if item not in rebuilt]
    assert len(non_participating) == 412 - BOUND_EOL_BASIS_CSV_COUNT
    for path in non_participating:
        assert path not in rebuilt
        assert b"\r" not in path.read_bytes(), path


def test_the_reconstruction_alters_no_file_on_disk() -> None:
    """The historical form exists only in memory; the evidence does not move."""

    raw = f"{protocol.RESULTS_NAMESPACE}/{protocol.CELLS_SUBDIR[0]}"
    before = correction.result_tree_identity()
    before_raw = correction.result_tree_identity(raw)
    correction.reconstruct_historical_csv_materialization()
    correction.prove_eol_basis_relation()
    assert correction.result_tree_identity() == before
    assert correction.result_tree_identity(raw) == before_raw
    assert before["working_tree_digest"] == CANONICAL_RESULT_TREE_WORKING_DIGEST


def test_no_hash_time_eol_normalization_is_used_as_a_shortcut(
    eol_proof: dict[str, Any],
) -> None:
    """A normalizing basis would collapse the two bases to a single value.

    They are two distinct values, so raw bytes are demonstrably being hashed on
    both sides. This is the observable form of ``docs/hash_basis_policy.md`` §2.
    """

    assert (
        HISTORICAL_RESULT_TREE_WORKING_DIGEST != CANONICAL_RESULT_TREE_WORKING_DIGEST
    )
    assert HISTORICAL_RAW_TREE_WORKING_DIGEST != CANONICAL_RAW_TREE_WORKING_DIGEST
    normalization = eol_proof["hash_time_eol_normalization"]
    assert normalization["used"] is False
    assert normalization["historical_equals_canonical_result_digest"] is False
    assert normalization["historical_equals_canonical_raw_digest"] is False
    assert eol_proof["blob_only_substitution"]["used"] is False


def test_the_result_tree_claim_language_is_precise(
    eol_proof: dict[str, Any], amendment: dict[str, Any]
) -> None:
    """Byte identity between the two bases is explicitly NOT claimed."""

    for payload in (eol_proof, amendment["claims"]):
        assert payload["canonical_git_tree_identical"] is True
        assert payload["scientific_content_identical"] is True
        assert payload["historical_to_canonical_byte_identical"] is False
        assert payload["difference_class"] == "EOL_REPRESENTATION_ONLY"
        assert payload["historical_reconstruction"] == "PASS"
        assert payload["canonical_lf_reproducibility"] == "PASS"
        assert payload["result_tree_byte_identical_between_bases_claimed"] is False


# ---------------------------------------------------------------------------
# 8. The additive hash-basis amendment
# ---------------------------------------------------------------------------


def test_the_amendment_is_additive_and_changes_no_science(
    amendment: dict[str, Any],
) -> None:
    """Every "did this change anything scientific" answer is no."""

    assert amendment["record_kind"] == "successor_qualification_hash_basis_amendment"
    assert amendment["amendment_id"] == BOUND_AMENDMENT_ID
    assert amendment["additive_only"] is True
    assert amendment["historical_records_modified"] is False
    assert amendment["historical_digests_overwritten"] is False
    assert amendment["silent_re_freeze"] is False
    assert amendment["qualification_evidence_changed"] is False
    assert amendment["experimental_results_changed"] is False
    assert amendment["scientific_metrics_changed"] is False
    assert amendment["benchmark_semantics_changed"] is False
    assert amendment["classifications_changed"] is False
    assert amendment["exposure_counts_changed"] is False
    assert amendment["verdict_changed"] is False
    assert amendment["result_files_changed"] == 0
    assert amendment["scope"]["result_namespace_files_modified"] == 0
    assert amendment["scope"]["tracked_files_modified"] == 0


def test_the_amendment_binds_both_evidence_commits(
    amendment: dict[str, Any],
) -> None:
    """Canonical is canonical; the PR head is identified as the PR head."""

    binding = amendment["evidence_binding"]
    assert binding["canonical_evidence_commit"] == BOUND_CANONICAL_EVIDENCE_COMMIT
    assert binding["canonical_evidence_commit_resolved_dynamically"] is True
    assert binding["pr_head_evidence_commit"] == BOUND_PR_HEAD_EVIDENCE_COMMIT
    assert binding["pr_head_is_canonical"] is False
    assert binding["pr_head_and_canonical_result_tree_equivalent"] is True
    assert binding["result_git_tree_sha"] == BOUND_RESULT_TREE_GIT_SHA
    assert binding["raw_git_tree_sha"] == BOUND_RAW_TREE_GIT_SHA
    assert binding["result_file_count"] == 412
    assert binding["raw_file_count"] == 408
    assert binding["result_tree_clean_against_commit"] is True
    assert binding["artifact_sha256"]["successor-analysis.json"] == (
        BOUND_ANALYSIS_SHA256
    )
    assert binding["artifact_sha256"]["successor-run-manifest.json"] == (
        BOUND_RUN_MANIFEST_SHA256
    )
    assert binding["artifact_sha256"]["successor-runs.jsonl"] == BOUND_RAW_RECORD_SHA256
    assert binding["artifact_sha256"]["successor-partial-manifest.json"] == (
        BOUND_PARTIAL_MANIFEST_SHA256
    )


def test_the_amendment_preserves_both_historical_observations(
    amendment: dict[str, Any],
) -> None:
    """Both historical digests are carried forward verbatim, unmodified."""

    bases = amendment["materialization_bases"]
    historical = bases["historical_local_materialization"]
    canonical = bases["canonical_lf_materialization"]
    assert historical["result_working_tree_digest"] == (
        HISTORICAL_RESULT_TREE_WORKING_DIGEST
    )
    assert historical["raw_working_tree_digest"] == HISTORICAL_RAW_TREE_WORKING_DIGEST
    assert historical["overwritten_or_re_frozen"] is False
    assert historical["bytes_written_to_disk"] == 0
    assert canonical["result_working_tree_digest"] == (
        CANONICAL_RESULT_TREE_WORKING_DIGEST
    )
    assert canonical["raw_working_tree_digest"] == CANONICAL_RAW_TREE_WORKING_DIGEST
    assert canonical["portable_and_clone_reproducible"] is True


def test_the_amendment_conforms_to_the_governing_policy(
    amendment: dict[str, Any],
) -> None:
    """Every prohibition of ``docs/hash_basis_policy.md`` §2 is answered."""

    conformance = amendment["policy_conformance"]
    assert amendment["governing_policy"] == "docs/hash_basis_policy.md"
    assert conformance["working_tree_hashing_is_the_attested_basis"] is True
    assert conformance["hash_time_eol_normalization"] is False
    assert conformance["blob_only_substitution_for_freeze_validation"] is False
    assert conformance["silent_re_freezing"] is False
    assert conformance["canonical_tracked_text_representation"] == "LF"
    assert conformance["historical_digests_remain_truthful_observations"] is True
    assert conformance["supersession_recorded_additively_in_a_new_amendment"] is True
    assert conformance["amendment_v1_modified"] is False
    assert conformance["hash_basis_policy_modified"] is False


def test_the_amendment_follows_v1_as_precedent_without_touching_it(
    amendment: dict[str, Any],
) -> None:
    """Amendment v1 is precedent, and carries no working-tree change."""

    precedent = amendment["precedent"]
    assert precedent["amendment_id"] == BOUND_PRECEDENT_AMENDMENT_ID
    assert precedent["followed_as_precedent"] is True
    assert precedent["modified_by_this_amendment"] is False
    for path in GOVERNING_HASH_BASIS_SOURCES:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", path],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        assert status.stdout.strip() == "", path


def test_the_amendment_supersedes_only_the_two_aggregate_digests(
    amendment: dict[str, Any],
) -> None:
    """No scientific artifact is within the amendment's scope."""

    scope = amendment["scope"]
    assert "working-tree" in scope["supersedes"]
    assert "aggregate digests" in scope["supersedes"]
    for excluded in (
        "any scientific row",
        "any metric",
        "any classification",
        "any exposure count",
        "any task status",
        "any verdict",
        "any benchmark semantic",
    ):
        assert excluded in scope["does_not_supersede"], excluded
    assert len(amendment["statements_of_record"]) == 7


def test_the_amendment_carries_no_authorization(amendment: dict[str, Any]) -> None:
    """An amendment about line endings grants nothing."""

    for key, value in amendment["authorizations"].items():
        assert value is False, key
    assert amendment["candidate_status"] == "FROZEN_NOT_YET_QUALIFIED"


def test_the_correction_represents_both_materialization_bases(
    record: dict[str, Any], diagnosis: dict[str, Any]
) -> None:
    """The correction and the diagnosis both carry the dual-basis record."""

    for payload in (record["hash_basis"], diagnosis["hash_basis"]):
        historical = payload["historical_local_materialization"]
        canonical = payload["canonical_lf_materialization"]
        assert historical["result_working_tree_digest"] == (
            HISTORICAL_RESULT_TREE_WORKING_DIGEST
        )
        assert historical["raw_working_tree_digest"] == (
            HISTORICAL_RAW_TREE_WORKING_DIGEST
        )
        assert historical["is_a_truthful_historical_observation"] is True
        assert historical["preserved_unchanged"] is True
        assert historical["overwritten_or_re_frozen"] is False
        assert canonical["result_working_tree_digest"] == (
            CANONICAL_RESULT_TREE_WORKING_DIGEST
        )
        assert canonical["raw_working_tree_digest"] == (
            CANONICAL_RAW_TREE_WORKING_DIGEST
        )
        assert canonical["is_the_reproducible_basis"] is True
        assert payload["difference_class"] == "EOL_REPRESENTATION_ONLY"
        assert payload["historical_to_canonical_byte_identical"] is False
        assert payload["canonical_git_tree_identical"] is True
        assert payload["scientific_content_identical"] is True
        assert payload["csv_files_with_historical_crlf_basis"] == (
            BOUND_EOL_BASIS_CSV_COUNT
        )
        assert payload["current_csv_files_with_crlf"] == 0


def test_the_correction_binds_the_new_amendment(
    record: dict[str, Any], diagnosis: dict[str, Any]
) -> None:
    """The binding to the amendment record is exact, and a change fails here."""

    for payload in (record["hash_basis"], diagnosis["hash_basis"]):
        binding = payload["hash_basis_amendment"]
        assert binding["amendment_id"] == BOUND_AMENDMENT_ID
        assert binding["record"] == (
            "docs/post_phaseP_successor_qualification_hash_basis_amendment.md"
        )
        assert binding["machine_record"] == (
            "docs/post_phaseP_successor_qualification_hash_basis_amendment.json"
        )
        assert binding["is_additive"] is True
        assert binding["precedent_amendment_id"] == BOUND_PRECEDENT_AMENDMENT_ID
        assert binding["precedent_amendment_modified"] is False
        assert binding["supersedes_any_scientific_artifact"] is False
        assert payload["governing_policy"] == "docs/hash_basis_policy.md"
        assert payload["hash_time_eol_normalization"] is False
        assert payload["blob_only_substitution"] is False
        assert payload["silent_re_freeze"] is False


def test_the_correction_refuses_a_different_canonical_evidence_commit(
    record: dict[str, Any],
) -> None:
    """A rebase onto a different commit is refused, not silently absorbed."""

    identity = dict(record["evidence_identity"])
    identity["canonical_evidence_commit"] = "0" * 40
    failures = correction.check_canonical_evidence_binding(identity)
    assert any("canonical evidence commit" in item for item in failures)


def test_the_correction_refuses_a_non_equivalent_pr_head_tree(
    record: dict[str, Any],
) -> None:
    """A PR head whose result tree diverged is refused."""

    identity = dict(record["evidence_identity"])
    identity["pr_head_and_canonical_result_tree_equivalent"] = False
    failures = correction.check_canonical_evidence_binding(identity)
    assert any("PR-head result tree" in item for item in failures)


# ---------------------------------------------------------------------------
# 9. The persisted records agree with the machinery
# ---------------------------------------------------------------------------


def test_the_persisted_machine_records_match_the_machinery(
    record: dict[str, Any], diagnosis: dict[str, Any], amendment: dict[str, Any]
) -> None:
    """The persisted docs are exactly what the correction module renders."""

    for relative, payload in (
        (correction.CORRECTION_MACHINE_RECORD_RELATIVE, record),
        (correction.DIAGNOSIS_MACHINE_RECORD_RELATIVE, diagnosis),
        (correction.HASH_BASIS_AMENDMENT_MACHINE_RECORD_RELATIVE, amendment),
    ):
        path = PROJECT_ROOT / relative
        assert path.is_file(), relative
        assert path.read_text(encoding="utf-8") == correction.canonical_json(payload)


def test_the_prose_records_exist_and_are_outside_the_result_namespace() -> None:
    """Nothing was created inside the immutable result namespace."""

    for relative in (
        correction.CORRECTION_RECORD_RELATIVE,
        correction.CORRECTION_MACHINE_RECORD_RELATIVE,
        correction.DIAGNOSIS_RECORD_RELATIVE,
        correction.DIAGNOSIS_MACHINE_RECORD_RELATIVE,
        correction.HASH_BASIS_AMENDMENT_RECORD_RELATIVE,
        correction.HASH_BASIS_AMENDMENT_MACHINE_RECORD_RELATIVE,
    ):
        assert (PROJECT_ROOT / relative).is_file(), relative
        assert not relative.startswith("results/"), relative


def test_the_persisted_records_are_on_the_canonical_lf_basis() -> None:
    """This work product carries no CR byte; it is written on the LF basis."""

    for relative in (
        correction.CORRECTION_RECORD_RELATIVE,
        correction.CORRECTION_MACHINE_RECORD_RELATIVE,
        correction.DIAGNOSIS_RECORD_RELATIVE,
        correction.DIAGNOSIS_MACHINE_RECORD_RELATIVE,
        correction.HASH_BASIS_AMENDMENT_RECORD_RELATIVE,
        correction.HASH_BASIS_AMENDMENT_MACHINE_RECORD_RELATIVE,
    ):
        assert b"\r" not in (PROJECT_ROOT / relative).read_bytes(), relative


def test_the_prose_amendment_states_the_precise_claims() -> None:
    """The human-readable amendment carries the exact claim language."""

    text = (PROJECT_ROOT / correction.HASH_BASIS_AMENDMENT_RECORD_RELATIVE).read_text(
        encoding="utf-8"
    )
    assert BOUND_AMENDMENT_ID in text
    assert BOUND_CANONICAL_EVIDENCE_COMMIT in text
    assert BOUND_PR_HEAD_EVIDENCE_COMMIT in text
    for digest in (
        HISTORICAL_RESULT_TREE_WORKING_DIGEST,
        HISTORICAL_RAW_TREE_WORKING_DIGEST,
        CANONICAL_RESULT_TREE_WORKING_DIGEST,
        CANONICAL_RAW_TREE_WORKING_DIGEST,
        BOUND_RESULT_TREE_GIT_SHA,
        BOUND_RAW_TREE_GIT_SHA,
        BOUND_PER_CELL_CSV_IDENTITY_DIGEST,
    ):
        assert digest in text, digest
    for claim in (
        "`CANONICAL_GIT_TREE_IDENTICAL` | **YES**",
        "`SCIENTIFIC_CONTENT_IDENTICAL` | **YES**",
        "`HISTORICAL_TO_CANONICAL_BYTE_IDENTICAL` | **NO**",
        "`DIFFERENCE_CLASS` | `EOL_REPRESENTATION_ONLY`",
        "`HISTORICAL_RECONSTRUCTION` | **PASS**",
        "`CANONICAL_LF_REPRODUCIBILITY` | **PASS**",
    ):
        assert claim in text, claim
    assert "RESULT_TREE_BYTE_IDENTICAL = YES` is **not** claimed" in text


def test_the_cli_renders_all_three_records_and_persists_nothing() -> None:
    """The CLI is a renderer: stdout only, exit 0, evidence untouched."""

    before = correction.result_tree_identity()
    for flag, kind in (
        ("correction", "successor_qualification_analysis_correction"),
        ("diagnosis", "successor_qualification_hold_forensic_diagnosis"),
        ("amendment", "successor_qualification_hash_basis_amendment"),
    ):
        completed = subprocess.run(
            [sys.executable, str(CORRECTION_SCRIPT), "--record", flag],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        assert payload["record_kind"] == kind
    assert correction.RECORD_BUILDERS == ("correction", "diagnosis", "amendment")
    assert correction.result_tree_identity() == before
