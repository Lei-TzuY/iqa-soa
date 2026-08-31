"""The POST_PHASEP_CONFIRMATORY approved instrument revision.

**NO MODEL IS RUN ANYWHERE IN THIS FILE**, nothing here contacts a provider or
opens a socket, and nothing here reads, enumerates or hashes anything beneath
``results/``.  Every assertion is against committed bytes, the working tree under
``src/iqa_soa``, or the deterministic writer.

The prospective post-Phase-P confirmatory randomization implementation (Work
Units 1-6) legitimately changed ``src/iqa_soa``, so the approved
instrument-revision chain -- which ended at Phase O -- gained a third link.  This
module proves the properties that make that link an ADDITIVE revision rather than
a rewrite:

1. the committed record is exactly reproducible from the current implementation
   tree by ``scripts/post_phaseP_write_instrument_revision.py``;
2. the chain is Phase M -> Phase O -> POST_PHASEP_CONFIRMATORY, with both custody
   links intact, and only the head asserted against the live tree;
3. neither predecessor record was edited, and no historical hash was updated in
   place;
4. the approved src change set is EXACTLY the eight reviewed paths, each with its
   real current SHA-256 and a substantive scientific reason;
5. no instrument, schema, adapter or contract version was invented;
6. the record's scientific status is prospective-only and retracts nothing;
7. the writer refuses an unexpected or missing src change set rather than
   widening the approved set, and performs no inference and no evidence access.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

import instrument_revision  # noqa: E402
import post_phaseP_write_instrument_revision as writer  # noqa: E402
import post_phaseP_write_provider_observability_revision as c3_writer  # noqa: E402

RECORD_RELATIVE = "docs/post_phaseP_confirmatory_instrument_revision.json"
RECORD_PATH = PROJECT_ROOT / RECORD_RELATIVE

#: The merge-base the WU1-WU6 implementation branch diverged from, and therefore
#: the last commit at which Phase O was the approved head.
PARENT_COMMIT = "bc9d0a1234ab229d6433dbd4e54df1e17823806c"

#: The commit at which POST_PHASEP_CONFIRMATORY STOPPED being the approved head:
#: the parent of the C3 provider-observability revision that superseded it.  Its
#: own claims -- what it changed, to what bytes, and what its record said -- are
#: historical facts about the window ``PARENT_COMMIT .. SUCCESSOR_COMMIT``, and
#: every test below that asks such a question now asks it over that window rather
#: than against today's tree.  Asserting a superseded revision's claims against a
#: tree a later APPROVED revision has legitimately moved past is the "prove A by
#: checking B" conflation ``instrument_revision`` exists to remove.
SUCCESSOR_COMMIT = "883c425daf2e6462877f0626f5fce0664ac85ca9"

#: The successor link this record is now the parent of.
SUCCESSOR_RECORD_RELATIVE = (
    "docs/post_phaseP_provider_observability_instrument_revision.json"
)

#: The ADDITIVE custody correction that supersedes this record's two
#: irreproducible digests without editing one byte of it.
CORRECTION_RELATIVE = (
    "docs/post_phaseP_confirmatory_instrument_revision_correction.json"
)

#: The one approved file whose declared digest was captured over CRLF
#: working-tree bytes that ``* text=auto eol=lf`` guarantees no commit can hold.
AFFECTED_FILE = "src/iqa_soa/experiment/confirmatory_registration.py"

#: The Phase-O head this link is additive to, and its own pinned tree.
PHASE_O_RECORD_RELATIVE = "docs/phaseO_instrument_revision.json"
PHASE_O_SRC_TREE = (
    "8d569696e51162acf8a0b8612f7d91398c7544cd0502cbaa59af92e35795b938"
)

#: The eight reviewed instrument paths.  Stated here independently of the writer
#: so a widened writer constant cannot quietly widen the approved set too.
APPROVED_SRC_FILES = (
    "src/iqa_soa/agent/__init__.py",
    "src/iqa_soa/agent/providers.py",
    "src/iqa_soa/experiment/confirmatory.py",
    "src/iqa_soa/experiment/confirmatory_assignment.py",
    "src/iqa_soa/experiment/confirmatory_eligibility.py",
    "src/iqa_soa/experiment/confirmatory_registration.py",
    "src/iqa_soa/experiment/runner.py",
    "src/iqa_soa/metrics/confirmatory.py",
)

#: A distinguishing phrase every reason must carry, so "the reason is long
#: enough" cannot be satisfied by eight interchangeable paragraphs.
REASON_MUST_MENTION: Mapping[str, tuple[str, ...]] = {
    "src/iqa_soa/agent/__init__.py": ("ProviderFailureOrigin", "export"),
    "src/iqa_soa/agent/providers.py": (
        "PROVIDER_INFRASTRUCTURE",
        "MODEL_OUTPUT",
        "WU5",
    ),
    "src/iqa_soa/experiment/confirmatory.py": (
        "Work Unit 5",
        "EXECUTION",
        "crash-safe",
    ),
    "src/iqa_soa/experiment/confirmatory_assignment.py": (
        "Work Unit 4",
        "assignment_manifest.json",
        "Monte-Carlo",
    ),
    "src/iqa_soa/experiment/confirmatory_eligibility.py": (
        "Stage-B",
        "eligibility",
        "BEFORE",
    ),
    "src/iqa_soa/experiment/confirmatory_registration.py": (
        "REGISTRATION_DRAFT",
        "self_digest",
        "FINAL_REGISTRATION_FROZEN",
    ),
    "src/iqa_soa/experiment/runner.py": (
        "run_one_position",
        "PRE_DISPATCH",
        "LEGACY",
    ),
    "src/iqa_soa/metrics/confirmatory.py": (
        "Work Unit 6",
        "analyze_confirmatory_randomization",
        "final_analysis_manifest.json",
    ),
}


@pytest.fixture(scope="module")
def record() -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    return parsed


@pytest.fixture(scope="module")
def correction() -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(
        (PROJECT_ROOT / CORRECTION_RELATIVE).read_text(encoding="utf-8")
    )
    return parsed


def _blob(commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=PROJECT_ROOT, capture_output=True, check=True,
    ).stdout


# ==========================================================================
# 1. The committed record is exactly reproducible from the current tree
# ==========================================================================


def test_the_committed_record_was_never_rewritten() -> None:
    """The record is byte-identical to the version its successor superseded.

    While this was the head, the test regenerated the record with
    ``writer.build_record()`` and required the committed bytes to match. Running
    that writer now would hash the LIVE post-C3 tree and demand a record
    describing work this revision did not do -- which is exactly the in-place
    rewrite of a superseded revision the whole mechanism forbids.

    The question a superseded record has to answer instead is "were you left
    alone?", and it is answered from immutable bytes: the working-tree record must
    equal the version committed at the commit its successor started from. The
    writer is still bound here, by its declared parent, so a record regenerated
    against some other parent could not pass silently.
    """

    committed = _blob(SUCCESSOR_COMMIT, RECORD_RELATIVE)
    assert RECORD_PATH.read_bytes() == committed
    assert writer.PARENT_COMMIT == PARENT_COMMIT
    parsed = json.loads(committed.decode("utf-8"))
    assert parsed["phase"] == "POST_PHASEP_CONFIRMATORY"
    assert parsed["parent_commit"] == PARENT_COMMIT


def test_the_recorded_tree_is_the_tree_its_successor_binds_as_its_parent(
    record: Mapping[str, Any],
) -> None:
    """The pin is no longer the live tree, and the successor carries custody on.

    An approved successor legitimately moved ``src/iqa_soa``, so the head-of-chain
    assertion moved with it. What must still hold is custody -- and the digest the
    successor binds is the CORRECTED one, because that is the one provable from
    committed bytes at the commit it started from. Neither record is edited to
    achieve that: the correction is a third, additive artifact, and the successor
    names it.
    """

    pinned = record["current_instrument"]["src_iqa_soa_tree"]
    assert pinned != PHASE_O_SRC_TREE
    assert pinned != instrument_revision.tree_digest("src/iqa_soa")
    successor = json.loads(
        (PROJECT_ROOT / SUCCESSOR_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    corrected = instrument_revision.tree_digest_at_commit(
        SUCCESSOR_COMMIT, "src/iqa_soa"
    )
    assert successor["previous_instrument"]["src_iqa_soa_tree"] == corrected
    assert successor["parent_commit"] == SUCCESSOR_COMMIT
    custody = successor["predecessor_custody"]
    assert custody["correction_record"] == CORRECTION_RELATIVE
    assert custody["corrected_record"] == RECORD_RELATIVE
    assert custody["corrected_record_edited_by_this_revision"] is False
    assert custody["predecessor_declared_src_iqa_soa_tree"] == pinned
    assert custody["predecessor_declared_pin_is_reproducible_from_history"] is False
    assert custody["authoritative_src_iqa_soa_tree"] == corrected
    # The successor's writer reaches the same conclusion from committed bytes.
    assert c3_writer.authoritative_predecessor_custody() == {
        "correction_record": CORRECTION_RELATIVE,
        "corrected_src_iqa_soa_tree": corrected,
    }


def test_the_recorded_pin_is_superseded_by_an_additive_custody_correction(
    record: Mapping[str, Any], correction: Mapping[str, Any]
) -> None:
    """A pre-existing custody defect, repaired ADDITIVELY and proved from history.

    ``instrument_revision.sha256_of`` hashes raw WORKING-TREE bytes and never
    normalizes, so a head record is pinned to working-tree digests, while a
    SUPERSEDED link is proved against COMMITTED blobs. The two agree only while
    the working tree is byte-identical to its commit. This repository declares
    ``* text=auto eol=lf``, so git normalizes on commit and reports a working-tree
    file carrying CRLF as UNCHANGED while it hashes differently -- which is what
    happened here, before C3 and independently of it. Two of this record's digests
    therefore describe bytes no commit can ever hold.

    The repair is ADDITIVE. This record is NOT edited -- the test above proves it
    byte-identical to its own commit -- and a separate correction record carries
    the corrected, committed-byte-provable custody state. This test proves the
    correction states the defect exactly and reproduces BOTH mismatches from
    committed bytes alone, so nothing is taken on trust.
    """

    declared_tree = record["current_instrument"]["src_iqa_soa_tree"]
    declared_file = record["changed_files"][AFFECTED_FILE]["sha256"]
    committed_tree = instrument_revision.tree_digest_at_commit(
        SUCCESSOR_COMMIT, "src/iqa_soa"
    )
    committed_file = instrument_revision.sha256_of_blob_at_commit(
        SUCCESSOR_COMMIT, AFFECTED_FILE
    )

    # The defect, stated: two declared values, neither reproducible from history.
    assert declared_tree != committed_tree
    assert declared_file != committed_file
    assert correction["original_declared"]["src_iqa_soa_tree"] == declared_tree
    assert correction["original_declared"]["changed_files_sha256"][AFFECTED_FILE] == (
        declared_file
    )
    assert correction["actual_committed"]["src_iqa_soa_tree"] == committed_tree
    assert correction["actual_committed"]["changed_files_sha256"][AFFECTED_FILE] == (
        committed_file
    )
    assert correction["corrected_current_instrument"]["src_iqa_soa_tree"] == (
        committed_tree
    )
    assert correction["affected_files"] == [AFFECTED_FILE]

    # And the cause, PROVED: the committed blob plus carriage returns, and nothing
    # else, reproduces the defective per-file digest exactly; stripping them
    # returns the committed blob exactly. A transform that can only ADD CR cannot
    # invent a source change.
    proof = correction["historical_eol_reconstruction"][AFFECTED_FILE]
    assert proof["convention"] == "eol-mask-v1"
    assert proof["index_basis"] == (
        "0-based LF-terminator ordinal in canonical LF byte stream"
    )
    assert proof["all_other_lf_terminators_are_crlf"] is True
    assert proof["content_difference_beyond_line_endings"] is False
    blob = _blob(SUCCESSOR_COMMIT, AFFECTED_FILE)
    indices = proof["bare_lf_terminator_indices"]
    rebuilt = instrument_revision.crlf_reconstruction(blob, indices)
    assert instrument_revision.sha256_of_bytes(rebuilt) == declared_file
    assert rebuilt.replace(b"\r\n", b"\n") == blob
    assert b"\r" not in blob
    assert blob.count(b"\n") == proof["total_lf_terminators"]
    assert proof["bare_lf_terminator_count"] == len(indices)
    assert indices == sorted(indices)
    assert len(set(indices)) == len(indices)
    assert proof["reconstructed_crlf_count"] == blob.count(b"\n") - len(indices)
    assert proof["reconstructed_sha256"] == proof["historical_recorded_sha256"]
    assert proof["canonical_source_sha256"] == committed_file
    assert proof["capture_canonical_source_commit"] == SUCCESSOR_COMMIT
    # And the mask is not a uniform CRLF materialization: the defective bytes were
    # MIXED, so nothing simpler than the recorded mask reproduces them.
    assert proof["uniform_crlf_materialization_reproduces_historical_bytes"] is False
    assert instrument_revision.sha256_of_bytes(
        blob.replace(b"\n", b"\r\n")
    ) != declared_file

    # Every OTHER approved file reproduces exactly, so the tree mismatch has one
    # cause and no residue.
    for name in APPROVED_SRC_FILES:
        if name == AFFECTED_FILE:
            continue
        assert record["changed_files"][name]["sha256"] == (
            instrument_revision.sha256_of_blob_at_commit(SUCCESSOR_COMMIT, name)
        ), name


def test_the_affected_file_is_now_line_ending_normalised_in_the_working_tree(
    correction: Mapping[str, Any],
) -> None:
    """The defect cannot recur: the raw bytes ARE the committed bytes now.

    Normalizing the working copy is what makes the raw-working-tree basis and the
    committed-blob basis agree again for this file. It is a pure line-ending
    change: git reports no content difference, so the file is NOT in the C3
    approved change set and no revision approves it.
    """

    disk = (PROJECT_ROOT / AFFECTED_FILE).read_bytes()
    committed = _blob(SUCCESSOR_COMMIT, AFFECTED_FILE)
    assert disk == committed
    assert b"\r\n" not in disk
    assert instrument_revision.sha256_of(PROJECT_ROOT / AFFECTED_FILE) == (
        correction["actual_committed"]["changed_files_sha256"][AFFECTED_FILE]
    )
    changed_since = subprocess.run(
        ["git", "diff", "--name-only", SUCCESSOR_COMMIT, "--", "src/iqa_soa"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert AFFECTED_FILE not in changed_since
    successor = json.loads(
        (PROJECT_ROOT / SUCCESSOR_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert AFFECTED_FILE not in successor["changed_files"]


# ==========================================================================
# 2. The chain, and both custody links
# ==========================================================================


def test_the_record_is_the_third_link_of_the_approved_chain(
    record: Mapping[str, Any],
) -> None:
    """The chain gained a fourth link; this one keeps its position and bytes.

    It is no longer the head, and that is the chain working as designed rather
    than a defect in it. Custody is still asserted in both directions: Phase O's
    result is this link's parent, and this link's result is the successor's
    parent.
    """

    chain = instrument_revision.load_revision_chain()
    assert [link["phase"] for link in chain] == [
        "M",
        "O",
        "POST_PHASEP_CONFIRMATORY",
        "POST_PHASEP_PROVIDER_OBSERVABILITY",
    ]
    assert instrument_revision.REVISION_CHAIN[2] == RECORD_PATH
    assert chain[2] == record
    assert instrument_revision.REVISION_PATH == instrument_revision.REVISION_CHAIN[-1]
    assert instrument_revision.REVISION_PATH != RECORD_PATH
    # Custody, both hand-offs. Phase O's is quoted directly; this link's is the
    # CORRECTED digest, because its own declared pin was captured on the wrong
    # byte basis and no commit can reproduce it. Neither record is edited to make
    # that true -- the correction is a separate, additive artifact.
    assert chain[1]["current_instrument"]["src_iqa_soa_tree"] == (
        chain[2]["previous_instrument"]["src_iqa_soa_tree"]
    )
    assert chain[3]["previous_instrument"]["src_iqa_soa_tree"] == (
        instrument_revision.tree_digest_at_commit(SUCCESSOR_COMMIT, "src/iqa_soa")
    )
    assert chain[2]["current_instrument"]["src_iqa_soa_tree"] != (
        chain[3]["previous_instrument"]["src_iqa_soa_tree"]
    )
    # Only the HEAD is asserted against the live working tree.
    assert chain[3]["current_instrument"]["src_iqa_soa_tree"] == (
        instrument_revision.tree_digest("src/iqa_soa")
    )


def test_the_chain_validates_clean_once_the_custody_correction_is_applied() -> None:
    """The chain validator is run IN FULL and must be silent.

    The two custody failures this link used to raise are gone, and not because
    anything was suppressed: ``verify_custody_correction`` re-derives the
    corrected digests from COMMITTED bytes at the historical commit and proves the
    defective ones are the same bytes plus carriage returns.
    """

    assert instrument_revision.verify_custody_correction()[0] == []
    assert instrument_revision.check_instrument_provenance() == []
    assert instrument_revision.check_approved_instrument_revision() == []


def test_removing_the_correction_restores_the_original_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The correction is load-bearing, and nothing else was relaxed.

    Point it at a path that does not exist and the validator returns to the
    pre-repair state: the two committed-byte mismatches this superseded link
    raised before the repair, plus the hand-off break that follows from the
    successor binding the corrected digest. That is the proof that no general
    tolerance for a hash or line-ending mismatch was introduced -- without the
    record, the chain still fails closed on precisely the discrepancy the
    correction was written to explain.
    """

    monkeypatch.setattr(
        instrument_revision, "CUSTODY_CORRECTION_PATH", tmp_path / "absent.json"
    )
    failures = instrument_revision.check_instrument_provenance()
    assert len(failures) == 3, failures
    superseded = [
        item
        for item in failures
        if "superseded revision POST_PHASEP_CONFIRMATORY" in item
    ]
    assert len(superseded) == 2, failures
    assert any("src/iqa_soa tree" in item for item in superseded), superseded
    assert any(AFFECTED_FILE in item for item in superseded), superseded
    assert [item for item in failures if "chain of custody is broken" in item]


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda payload: payload | {"historical_commit": "0" * 40},
            id="another commit",
        ),
        pytest.param(
            lambda payload: payload | {"corrects_record_sha256": "0" * 64},
            id="another record",
        ),
        pytest.param(
            lambda payload: payload | {"phase": "O"}, id="another phase"
        ),
        pytest.param(
            lambda payload: payload
            | {
                "corrected_current_instrument": (
                    payload["corrected_current_instrument"] | {"src_iqa_soa_tree": "0" * 64}
                )
            },
            id="an unproved corrected tree",
        ),
        pytest.param(
            lambda payload: payload
            | {
                "historical_eol_reconstruction": {
                    AFFECTED_FILE: (
                        payload["historical_eol_reconstruction"][AFFECTED_FILE]
                        | {"bare_lf_terminator_indices": [0]}
                    )
                }
            },
            id="a reconstruction that does not reproduce the defect",
        ),
        pytest.param(
            lambda payload: payload | {"affected_files": []},
            id="an unexplained file",
        ),
        pytest.param(
            lambda payload: payload
            | {
                "historical_eol_reconstruction": {
                    AFFECTED_FILE: (
                        payload["historical_eol_reconstruction"][AFFECTED_FILE]
                        | {"convention": "trust-me-v1"}
                    )
                }
            },
            id="an unrecognised reconstruction convention",
        ),
    ],
)
def test_an_unproved_custody_correction_is_refused_and_never_applied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    correction: Mapping[str, Any],
    mutate: Any,
) -> None:
    """Every way of weakening the correction is refused, and the mismatch stands.

    A correction is admitted only when it addresses THIS record's bytes at THIS
    commit AND reproduces both defective digests from committed bytes. Break any
    one of those and the correction is withheld: the validator reports the
    refusal AND still reports the underlying custody failures. There is no path
    that accepts a mismatch it has not reproduced.
    """

    tampered = tmp_path / "correction.json"
    tampered.write_text(
        json.dumps(mutate(dict(correction))), encoding="utf-8", newline="\n"
    )
    monkeypatch.setattr(instrument_revision, "CUSTODY_CORRECTION_PATH", tampered)

    correction_failures, applied = instrument_revision.verify_custody_correction()
    assert applied is None
    assert correction_failures
    failures = instrument_revision.check_instrument_provenance()
    assert any("superseded revision POST_PHASEP_CONFIRMATORY" in x for x in failures)


def test_the_correction_never_edits_the_record_it_corrects(
    correction: Mapping[str, Any],
) -> None:
    """It supersedes two digests; it does not rewrite the record that holds them.

    The corrected record's bytes are pinned in the validator itself, so editing it
    to make its own hashes pass now FAILS the provenance check rather than
    silently succeeding -- a guarantee the chain did not previously have.
    """

    assert correction["record_kind"] == "instrument_revision_custody_correction"
    assert correction["corrects_record"] == RECORD_RELATIVE
    assert correction["corrects_record_sha256"] == (
        instrument_revision.sha256_of(RECORD_PATH)
    )
    assert correction["corrects_record_sha256"] == (
        instrument_revision.CUSTODY_CORRECTED_RECORD_SHA256
    )
    assert instrument_revision.CUSTODY_CORRECTED_RECORD_PATH == RECORD_PATH
    assert instrument_revision.CUSTODY_CORRECTION_COMMIT == SUCCESSOR_COMMIT
    # It is NOT a chain link: the chain is still the four approved revisions.
    assert instrument_revision.CUSTODY_CORRECTION_PATH not in (
        instrument_revision.REVISION_CHAIN
    )
    # It carries the corrected link's own versions, and invents none.
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        assert correction[key] == json.loads(
            RECORD_PATH.read_text(encoding="utf-8")
        )["current_instrument"][key], key
    assert correction["instrument_version"] == "4"
    assert correction["raw_schema_version"] == 5
    assert correction["native_tool_adapter_version"] == "native-tools-adapter-3"
    # And it says, in terms, what it is and what it is not.
    assert correction["source_bytes_changed_by_this_correction"] is False
    assert correction["model_inference_performed"] is False
    assert correction["provider_contacted"] is False
    assert correction["phase_p_execution_rerun"] is False
    assert correction["phase_p_result_reinterpreted"] is False
    assert correction["historical_rows_rescored"] is False
    assert correction["instrument_revisions_overwritten"] is False
    assert correction["ben_003_rehabilitated"] is False
    assert "PRESERVED BYTE-FOR-BYTE" in correction["corrects_record_preserved"]
    assert "CUSTODY CORRECTION, not a scientific revision" in (
        correction["custody_correction_not_scientific_revision"]
    )
    assert "not read, enumerated, traversed, hashed" in (
        correction["phase_p_evidence_untouched"]
    )
    assert "No Phase-P interpretation moves" in (
        correction["phase_p_interpretation_unchanged"]
    )
    assert "PROVED, not asserted" in correction["no_semantic_source_change_invented"]
    # It follows the repository's own governing policy, and its own precedent for
    # this class of incident, rather than inventing a parallel vocabulary.
    assert correction["governing_policy"] == "docs/hash_basis_policy.md"
    assert correction["eol_mask_precedent"] == "docs/hash_basis_amendment_v1.json"
    for relative in (correction["governing_policy"], correction["eol_mask_precedent"]):
        assert (PROJECT_ROOT / relative).is_file(), relative


def test_the_correction_record_is_reproducible_from_its_writer(
    correction: Mapping[str, Any],
) -> None:
    """It is generated, not hand-written, and regenerating it changes nothing."""

    import post_phaseP_write_confirmatory_custody_correction as correction_writer

    assert correction_writer.build_record() == correction
    payload = json.dumps(correction, indent=2, sort_keys=True) + "\n"
    assert (PROJECT_ROOT / CORRECTION_RELATIVE).read_bytes() == payload.encode("utf-8")


def test_the_new_link_binds_the_existing_phase_o_head(
    record: Mapping[str, Any],
) -> None:
    """Its parent digest is the Phase-O head's own pin, not a recomputation."""

    phase_o = json.loads(
        (PROJECT_ROOT / PHASE_O_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    previous = record["previous_instrument"]
    assert previous["record"] == PHASE_O_RECORD_RELATIVE
    assert previous["phase"] == "O"
    assert previous["src_iqa_soa_tree"] == (
        phase_o["current_instrument"]["src_iqa_soa_tree"]
    )
    assert previous["src_iqa_soa_tree"] == PHASE_O_SRC_TREE
    # And the Phase-O head is what the parent commit actually contains.
    assert instrument_revision.tree_digest_at_commit(
        PARENT_COMMIT, "src/iqa_soa"
    ) == PHASE_O_SRC_TREE
    assert record["parent_commit"] == PARENT_COMMIT
    assert record["additive_to"] == PHASE_O_RECORD_RELATIVE
    # Every version the predecessor carried is carried forward faithfully.
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        assert previous[key] == phase_o["current_instrument"][key], key


# ==========================================================================
# 3. Nothing historical was rewritten
# ==========================================================================


@pytest.mark.parametrize(
    "relative",
    ["docs/phaseM_instrument_revision.json", PHASE_O_RECORD_RELATIVE],
)
def test_no_predecessor_revision_record_was_edited(relative: str) -> None:
    """A successor that permitted its predecessor to be edited proves nothing."""

    assert (PROJECT_ROOT / relative).read_bytes() == _blob(PARENT_COMMIT, relative)


def test_no_benchmark_freeze_record_was_edited() -> None:
    for relative in (
        "benchmark/pilot-v7-rc3/freeze-record.json",
        "benchmark/pilot-v7-rc4/freeze-record.json",
        "benchmark/pilot-v7-rc4/qualification-contract.json",
        "docs/phaseL_frozen_execution_inputs.json",
        "docs/phaseP_frozen_execution_inputs.json",
    ):
        assert (PROJECT_ROOT / relative).read_bytes() == _blob(
            PARENT_COMMIT, relative
        ), relative


def test_the_phase_k_freeze_assertion_is_still_provable() -> None:
    """The oldest pin is preserved, not overwritten, and still holds at its commit."""

    assert instrument_revision.check_historical_freeze_assertion() == []


# ==========================================================================
# 4. Exactly the approved src change set, hashed and reasoned
# ==========================================================================


def test_the_approved_set_is_exactly_the_observed_src_change_set(
    record: Mapping[str, Any],
) -> None:
    """Asked over this revision's OWN window, from committed bytes.

    Comparing against the working tree would now report the C3 change set as an
    unapproved addition to a revision that closed before C3 existed.
    """

    observed = subprocess.run(
        ["git", "diff", "--name-only", PARENT_COMMIT, SUCCESSOR_COMMIT,
         "--", "src/iqa_soa"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert sorted(observed) == list(APPROVED_SRC_FILES)
    assert sorted(record["changed_files"]) == list(APPROVED_SRC_FILES)
    assert tuple(writer.APPROVED_SRC_FILES) == APPROVED_SRC_FILES


def test_every_approved_file_carries_its_real_hash_and_a_real_reason(
    record: Mapping[str, Any],
) -> None:
    changed = record["changed_files"]
    correction = json.loads(
        (PROJECT_ROOT / CORRECTION_RELATIVE).read_text(encoding="utf-8")
    )
    affected = set(correction["affected_files"])
    for name in APPROVED_SRC_FILES:
        entry = changed[name]
        # Proved from COMMITTED bytes over this revision's own window. The one
        # exception is the file whose digest was captured over CRLF working-tree
        # bytes; for it, the authoritative digest is the corrected one the
        # additive custody correction supplies, which IS the committed digest.
        # That file is named by the correction rather than hard-coded here.
        committed = instrument_revision.sha256_of_blob_at_commit(
            SUCCESSOR_COMMIT, name
        )
        if name in affected:
            assert entry["sha256"] != committed, name
            assert correction["actual_committed"]["changed_files_sha256"][name] == (
                committed
            ), name
        else:
            assert entry["sha256"] == committed, name
        reason = entry["reason"]
        assert len(reason.strip()) >= 20, name
        assert reason.strip().casefold() not in {"updated code", "code change"}, name
    # The reasons are eight DISTINCT statements, not one boilerplate paragraph.
    assert len({entry["reason"] for entry in changed.values()}) == len(changed)


@pytest.mark.parametrize("name", APPROVED_SRC_FILES)
def test_each_reason_states_that_file_s_own_prospective_purpose(
    record: Mapping[str, Any], name: str
) -> None:
    reason = record["changed_files"][name]["reason"]
    for token in REASON_MUST_MENTION[name]:
        assert token in reason, (name, token)


def test_the_two_edited_legacy_modules_declare_that_legacy_behaviour_is_preserved(
    record: Mapping[str, Any],
) -> None:
    """The provider and runner edits are additive, and the record says exactly how."""

    providers = record["changed_files"]["src/iqa_soa/agent/providers.py"]["reason"]
    assert "PRESERVED" in providers
    assert "no committed row is reclassified" in providers
    runner = record["changed_files"]["src/iqa_soa/experiment/runner.py"]["reason"]
    assert "ExperimentRunner.run SEMANTICS ARE UNCHANGED" in runner


# ==========================================================================
# 5. No version was invented
# ==========================================================================


def test_the_recorded_versions_are_the_permanently_named_constants(
    record: Mapping[str, Any],
) -> None:
    """The versions this revision ran under, named permanently and still true.

    ``INSTRUMENT_VERSION`` and ``RAW_SCHEMA_VERSION`` are documented aliases for
    "what the instrument writes today", and an approved successor moved both.
    This record's claims are about the instrument IT approved, so they are
    asserted against the permanent constants that instrument was named by --
    which have not moved and never will -- rather than against the two aliases.
    The adapter and the model-visible argument contract are unmoved by C3, so
    those two are still asserted live, unchanged.
    """

    from iqa_soa.instrument import (
        FAILURE_EVENT_RAW_SCHEMA_VERSION,
        INSTRUMENT_VERSION,
        NATIVE_TOOL_ADAPTER_VERSION,
        RAW_SCHEMA_VERSION,
        TOOL_CONTRACT_INSTRUMENT_VERSION,
    )
    from iqa_soa.tools.argument_schema import TOOL_ARGUMENT_CONTRACT_VERSION

    current = record["current_instrument"]
    assert current["instrument_version"] == TOOL_CONTRACT_INSTRUMENT_VERSION == "4"
    assert current["raw_schema_version"] == FAILURE_EVENT_RAW_SCHEMA_VERSION == 5
    assert current["native_tool_adapter_version"] == NATIVE_TOOL_ADAPTER_VERSION
    assert current["tool_argument_contract_version"] == TOOL_ARGUMENT_CONTRACT_VERSION
    # And the live aliases have moved past this revision, by an approved one.
    assert INSTRUMENT_VERSION == "5"
    assert RAW_SCHEMA_VERSION == 6


def test_no_boundary_constant_moved_merely_because_the_tree_changed(
    record: Mapping[str, Any],
) -> None:
    """The WU1-WU6 work preserved legacy semantics, so no boundary is bumped.

    Bumping one here would assert an incomparability that does not exist and
    would retroactively invalidate the committed Phase-P artifacts, which are
    written under instrument 4 / raw schema 5.
    """

    previous = record["previous_instrument"]
    current = record["current_instrument"]
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        assert current[key] == previous[key], key
    assert current["instrument_version"] == "4"
    assert current["raw_schema_version"] == 5
    assert current["adapter_unchanged" ] is True
    # The code constants were NOT edited by THIS repair, asserted over its own
    # window from committed bytes. A later approved revision (C3) did move
    # ``instrument.py``, which is why this is no longer a live comparison; that
    # movement is approved and hash-pinned by the successor link, not by this one.
    for relative in ("src/iqa_soa/instrument.py", "src/iqa_soa/tools/argument_schema.py"):
        assert _blob(SUCCESSOR_COMMIT, relative) == _blob(
            PARENT_COMMIT, relative
        ), relative
    assert "src/iqa_soa/instrument.py" not in record["changed_files"]


# ==========================================================================
# 6. Scientific status: prospective only, retracting nothing
# ==========================================================================


def test_the_record_states_a_prospective_implementation_only(
    record: Mapping[str, Any],
) -> None:
    assert record["phase"] == "POST_PHASEP_CONFIRMATORY"
    assert record["record_kind"] == "instrument_revision"
    assert record["model_inference_performed"] is False
    assert record["phase_p_execution_rerun"] is False
    assert record["phase_p_result_reinterpreted"] is False
    assert record["historical_rows_rescored"] is False
    assert record["benchmark_freeze_records_overwritten"] is False
    assert record["instrument_revisions_overwritten"] is False
    assert record["authorizes_confirmatory_execution"] is False
    assert record["post_phaseP_confirmatory_execution_authorized"] is False
    statement = record["prospective_implementation_only"]
    for clause in (
        "PROSPECTIVE",
        "No Phase-P execution is rerun",
        "No benchmark freeze record is overwritten",
        "No existing instrument revision is overwritten",
        "authorizes no real confirmatory execution",
    ):
        assert clause in statement, clause


def test_the_historical_phase_p_verdict_is_carried_forward_unchanged(
    record: Mapping[str, Any],
) -> None:
    hold = record["phase_p_rc4_hold"]
    assert hold["benchmark_version"] == "pilot-v7-rc4"
    assert hold["qualification_status"] == "UNQUALIFIED"
    assert hold["verdict"] == "HOLD"
    assert hold["terminal_status"] == "SCHEDULE_COMPLETE_VERDICT_HOLD"
    assert hold["phase_p_cells_rerun"] == 0
    assert hold["phase_p_rows_rescored"] == 0
    # And it agrees with the committed forensic ledger rather than restating it.
    diagnosis = json.loads(
        (PROJECT_ROOT / hold["diagnosis_record"]).read_text(encoding="utf-8")
    )
    assert diagnosis["official_verdict"] == hold["verdict"]
    assert diagnosis["terminal_status"] == hold["terminal_status"]


def test_work_unit_authorization_stays_with_the_frozen_lifecycle(
    record: Mapping[str, Any],
) -> None:
    authorization = record["confirmatory_lifecycle_authorization"]
    governed_by = authorization["governed_by"]
    assert governed_by, "a revision that names no governing authority governs itself"
    for relative in governed_by:
        assert (PROJECT_ROOT / relative).is_file(), relative
    assert "grants no execution" in authorization["note"]


# ==========================================================================
# 7. The writer refuses, and reaches nothing it must not
# ==========================================================================


def test_the_writer_refuses_an_unexpected_src_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drive-by edit is refused, not absorbed into the approved set."""

    monkeypatch.setattr(
        writer.ir,
        "_changed_files_since",
        lambda _commit, _root: [*APPROVED_SRC_FILES, "src/iqa_soa/instrument.py"],
    )
    with pytest.raises(SystemExit) as excinfo:
        writer.build_record()
    assert "src/iqa_soa/instrument.py" in str(excinfo.value)


def test_the_writer_refuses_a_missing_approved_src_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An approved file that did not actually change is refused too."""

    monkeypatch.setattr(
        writer.ir,
        "_changed_files_since",
        lambda _commit, _root: list(APPROVED_SRC_FILES[:-1]),
    )
    with pytest.raises(SystemExit) as excinfo:
        writer.build_record()
    assert APPROVED_SRC_FILES[-1] in str(excinfo.value)


def test_the_writer_refuses_a_predecessor_whose_tree_is_not_the_parent_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken chain of custody refuses rather than being papered over."""

    monkeypatch.setattr(
        writer.ir,
        "_changed_files_since",
        lambda _commit, _root: list(APPROVED_SRC_FILES),
    )
    monkeypatch.setattr(
        writer.ir, "tree_digest_at_commit", lambda _commit, _root: "0" * 64
    )
    with pytest.raises(SystemExit) as excinfo:
        writer.build_record()
    assert "chain of custody" in str(excinfo.value)


def test_the_writer_now_refuses_because_the_change_set_moved_past_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-running the superseded writer on today's tree REFUSES, as it should.

    This is the property that makes the record safe to leave alone: the writer
    that produced it cannot silently regenerate it over a later tree, because the
    observed change set is no longer its approved set.
    """

    with pytest.raises(SystemExit) as excinfo:
        writer.build_record()
    assert "not the approved set" in str(excinfo.value)


def test_the_writer_performs_no_inference_and_no_evidence_access() -> None:
    """It reads git, ``src/iqa_soa``, ``benchmark/`` and ``configs/`` -- nothing else.

    In particular it never names, opens, enumerates or hashes the official
    Phase-P evidence root. The only place that path appears is the record's own
    statement that it was not touched.
    """

    import ast

    path = SCRIPTS_ROOT / "post_phaseP_write_instrument_revision.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for forbidden in (
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "openai",
        "ollama",
    ):
        assert forbidden not in imported, forbidden

    # The evidence root may be NAMED in prose, and must never be REACHED. No
    # string literal in this module composes a path into ``results/``.
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert not [item for item in literals if item.strip("/") == "results"]
    assert not [item for item in literals if item.startswith("results/")]
    named = [item for item in literals if "results/phaseP-rc4-qualification" in item]
    assert len(named) == 1, (
        "the Phase-P evidence root is named more than once in the writer; the only "
        "permitted mention is the record's untouched-evidence statement"
    )
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    assert named[0] in record["phase_p_evidence_untouched"] or (
        "results/phaseP-rc4-qualification" in record["phase_p_evidence_untouched"]
    )
    assert "not read, enumerated, traversed, hashed" in (
        record["phase_p_evidence_untouched"]
    )


def test_the_writer_never_rewrites_an_older_revision_file() -> None:
    """Its default output is the chain HEAD, which is this record and no other."""

    import argparse
    import inspect

    assert writer.PREDECESSOR_RECORD_RELATIVE == PHASE_O_RECORD_RELATIVE
    source = inspect.getsource(writer.main)
    assert "ir.REVISION_CHAIN[-1]" in source
    assert isinstance(argparse.ArgumentParser(), argparse.ArgumentParser)
    # Its ``--out`` default now resolves to the SUCCESSOR record rather than to
    # this one, and it refuses to build a record at all on today's tree, so the
    # two together make an accidental rewrite of this file impossible.
    assert instrument_revision.REVISION_CHAIN[-1] != RECORD_PATH
    assert instrument_revision.REVISION_CHAIN[2] == RECORD_PATH
    with pytest.raises(SystemExit):
        writer.build_record()


# ==========================================================================
# Custody-correction JSON type robustness
# ==========================================================================


#: Every JSON value that parses cleanly and is NOT an object.  Each one used to
#: reach ``record.get(...)`` and raise ``AttributeError`` out of the validator;
#: each one must now be refused through the ordinary structured path.
NON_OBJECT_CORRECTION_DOCUMENTS: tuple[str, ...] = (
    "[]",
    "null",
    "3",
    '"x"',
    "true",
    "[]\n",
    '{"a": 1}\n[]',  # not valid JSON at all -- the unreadable path, still closed
    "",
)


@pytest.mark.parametrize("document", NON_OBJECT_CORRECTION_DOCUMENTS)
def test_a_correction_record_that_is_not_an_object_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, document: str
) -> None:
    """A syntactically valid JSON NON-object is a refusal, not a crash.

    ``[]``, ``null``, ``3``, ``"x"`` and ``true`` all parse, and none of them is
    a record.  Before the type check they reached the first ``.get`` and raised
    ``AttributeError``, which fails closed only by accident of the caller.  They
    must fail closed the way every other defective correction does: a reported,
    deterministic validation failure with ``applied is None``.
    """

    bogus = tmp_path / "correction.json"
    bogus.write_text(document, encoding="utf-8", newline="\n")
    monkeypatch.setattr(instrument_revision, "CUSTODY_CORRECTION_PATH", bogus)

    # No exception escapes -- neither AttributeError nor anything else.
    failures, applied = instrument_revision.verify_custody_correction()
    assert applied is None
    assert failures, document
    assert len(failures) == 1, failures
    assert failures[0].startswith("A: "), failures
    assert "correction.json" in failures[0], failures

    # And the refusal is deterministic: the same bytes give the same message.
    again, again_applied = instrument_revision.verify_custody_correction()
    assert again == failures and again_applied is None


@pytest.mark.parametrize("document", ("[]", "null", "3", '"x"', "true"))
def test_a_non_object_correction_leaves_the_underlying_custody_failures_standing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, document: str
) -> None:
    """Refusing it withholds it: the mismatch it did not prove is still reported.

    This is the same property the tamper suite asserts for every other way of
    weakening the correction, and it must hold for a non-object document too --
    otherwise a ``[]`` on disk would be a way to make the custody failures
    disappear without proving anything.
    """

    bogus = tmp_path / "correction.json"
    bogus.write_text(document, encoding="utf-8", newline="\n")
    monkeypatch.setattr(instrument_revision, "CUSTODY_CORRECTION_PATH", bogus)

    failures = instrument_revision.check_instrument_provenance()
    assert any("is not a JSON object" in item for item in failures), failures
    assert any(
        "superseded revision POST_PHASEP_CONFIRMATORY" in item for item in failures
    ), failures
    assert any("chain of custody is broken" in item for item in failures), failures


def test_the_type_check_names_what_it_actually_parsed() -> None:
    """The refusal message is specific, so a reviewer is not left guessing."""

    import tempfile

    for document, expected in (
        ("[]", "list"),
        ("null", "NoneType"),
        ("3", "int"),
        ('"x"', "str"),
        ("true", "bool"),
    ):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "correction.json"
            path.write_text(document, encoding="utf-8", newline="\n")
            original = instrument_revision.CUSTODY_CORRECTION_PATH
            instrument_revision.CUSTODY_CORRECTION_PATH = path
            try:
                failures, applied = instrument_revision.verify_custody_correction()
            finally:
                instrument_revision.CUSTODY_CORRECTION_PATH = original
        assert applied is None
        assert f"parsed as {expected}" in failures[0], (document, failures)


def test_the_real_correction_is_still_admitted_after_the_type_check() -> None:
    """The genuine record is unaffected: it is an object and it still applies."""

    failures, applied = instrument_revision.verify_custody_correction()
    assert failures == []
    assert applied is not None
    assert isinstance(applied, Mapping)
    assert instrument_revision.check_instrument_provenance() == []
    assert instrument_revision.check_approved_instrument_revision() == []
