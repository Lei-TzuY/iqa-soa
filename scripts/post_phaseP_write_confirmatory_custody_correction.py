#!/usr/bin/env python3
"""Generate the POST_PHASEP_CONFIRMATORY instrument-revision CUSTODY CORRECTION.

WHAT IS WRONG, EXACTLY
======================

``docs/post_phaseP_confirmatory_instrument_revision.json`` -- the third link of
the approved instrument-revision chain -- declares two digests that no commit can
ever reproduce:

* ``current_instrument.src_iqa_soa_tree`` =
  ``c43f8f162f22faff2f956c8e080b422f4e011ca4301de188c8dd4e0583b29c75``, where the
  tree ACTUALLY committed at ``883c425daf2e6462877f0626f5fce0664ac85ca9`` -- the
  last commit at which that link was the approved head -- digests to
  ``966869a4506f403db23ed545785821c98f8c8c01796426b47254d4a10769ebaa``;
* ``changed_files["src/iqa_soa/experiment/confirmatory_registration.py"].sha256``
  = ``ec052e68...``, where the COMMITTED blob at that commit hashes to
  ``171f70ac...``.

``instrument_revision.sha256_of`` hashes RAW working-tree bytes and never
normalizes (``docs/hash_basis_policy.md``), so the head of the chain is pinned to
a working-tree digest, while ``_check_historical_link`` proves a SUPERSEDED link
from COMMITTED blobs.  The two agree only while the working tree is byte-identical
to its commit.  This repository declares ``* text=auto eol=lf``, so git normalizes
on commit: a working-tree file carrying CRLF is reported UNCHANGED by ``git
status`` and ``git diff`` while hashing differently, and the normalized bytes are
the only ones a commit can ever contain.  The record was written over a working
tree in which exactly one approved file carried CRLF, so exactly one per-file
digest -- and through it the tree digest -- were captured in a form history cannot
hold.

The defect is a CUSTODY defect.  It is not a scientific revision, it is not a
source change, and it is not a Phase-P question.

WHY THIS IS AN ADDITIVE RECORD AND NOT AN EDIT
==============================================

The governing rule this repository states in ``scripts/instrument_revision.py`` is
that the revision chain is append-only in both senses: no record replaces, edits
or overwrites a freeze record, and no LATER record replaces, edits or overwrites
an EARLIER one.  Rewriting the defective record's two digests in place would
destroy the only evidence of what the defect was, and would make the very claim
under repair -- "this record was never edited" -- unfalsifiable.

So the defective record is preserved BYTE-FOR-BYTE and authenticated by its own
SHA-256, and this separate record carries the corrected, committed-byte-provable
custody state that supersedes those two values and nothing else.

WHAT MAKES THE CORRECTION HONEST
================================

A correction that merely asserted "trust me, it was line endings" would be the
"ignore the mismatch" escape hatch the governance forbids.  This record instead
carries an ``eol-mask-v1`` RECONSTRUCTION MASK -- the same convention
``docs/hash_basis_amendment_v1.json`` already uses for an earlier incident of
exactly this kind -- naming the ordinals of the LF terminators that were bare LF
in the defective working tree; every other one was CRLF.  Applying the mask to the
COMMITTED blob must reproduce the defective declared SHA-256 exactly, and stripping
CR from the reconstruction must reproduce the committed blob exactly.  Both
directions are checked here before the record is written, and again by
``instrument_revision.verify_custody_correction`` on every provenance check.

That is a proof, not an excuse.  It demonstrates that the defective bytes were the
committed bytes plus a set of carriage returns -- no added statement, no removed
statement, no reordered statement, not one changed character of source -- so no
semantic source change is being invented to make a hash pass.  A discrepancy
caused by anything else could not satisfy it.

NO MODEL INFERENCE, AND NO EVIDENCE ACCESS.  This script reads git and the
defective record, and nothing else.  It never opens, enumerates, hashes, traverses
or writes anything beneath the official evidence root.  No Phase-P cell is rerun,
no Phase-P row is rescored and no Phase-P interpretation moves.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision as ir  # noqa: E402

#: The defective record.  READ, never written, and authenticated by its bytes.
DEFECTIVE_RECORD_RELATIVE = "docs/post_phaseP_confirmatory_instrument_revision.json"

#: Its SHA-256, pinned so this correction attaches to those bytes and no others.
DEFECTIVE_RECORD_SHA256 = (
    "927c0c3b662990500304214506e6413bf71e9ad4cebe9436c8a2bff2fb21d59a"
)

#: The phase whose custody is corrected.
PHASE = "POST_PHASEP_CONFIRMATORY"

#: The commit the corrected custody state is reconstructed from: the last commit
#: at which the defective record was the approved head.
HISTORICAL_COMMIT = "883c425daf2e6462877f0626f5fce0664ac85ca9"

#: The instrument root the corrected digests speak about.
RELATIVE_ROOT = "src/iqa_soa"

#: The ONE approved file whose declared digest history cannot reproduce.
AFFECTED_FILES: tuple[str, ...] = (
    "src/iqa_soa/experiment/confirmatory_registration.py",
)

#: The forensic finding, stated as a reproducible mask rather than a claim, in
#: the ``eol-mask-v1`` convention this repository already uses for exactly this
#: kind of incident (``docs/hash_basis_amendment_v1.json``,
#: ``tests/integration/test_hash_basis_invariants.py``).
#:
#: Of the 3912 LF terminators in the committed blob, the defective working-tree
#: copy rendered 3875 as CRLF and left these 37 -- and only these 37, identified
#: by their 0-based ordinal in the canonical LF byte stream -- as bare LF.
#: Nothing here is chosen to make a hash pass: applying it must reproduce BOTH
#: defective digests exactly, and this module refuses to write the record if it
#: does not.
BARE_LF_TERMINATOR_INDICES: tuple[int, ...] = (
    2226, 2227, 2228, 2229, 2230, 2231,
    3604, 3605, 3606, 3607, 3608, 3609, 3610,
    3746, 3747, 3748, 3749, 3750, 3751,
    3763, 3764, 3765, 3766, 3767, 3768, 3769,
    3781, 3782, 3783, 3784, 3785, 3786, 3787, 3788,
    3828, 3829, 3830,
)


def _load_defective_record() -> tuple[Mapping[str, Any], str]:
    """The defective record's bytes, authenticated, and its parsed form."""

    path = PROJECT_ROOT / DEFECTIVE_RECORD_RELATIVE
    payload = path.read_bytes()
    actual = ir.sha256_of_bytes(payload)
    if actual != DEFECTIVE_RECORD_SHA256:
        raise SystemExit(
            f"{DEFECTIVE_RECORD_RELATIVE} hashes to {actual!r}, not the pinned "
            f"{DEFECTIVE_RECORD_SHA256!r}. This correction attaches to the "
            "preserved defective bytes and to no others; a record that has moved "
            "is a different incident and must be diagnosed on its own terms."
        )
    parsed: Mapping[str, Any] = json.loads(payload.decode("utf-8"))
    if parsed.get("phase") != PHASE:
        raise SystemExit(
            f"{DEFECTIVE_RECORD_RELATIVE} declares phase {parsed.get('phase')!r}, "
            f"expected {PHASE!r}"
        )
    return parsed, actual


def build_record() -> dict[str, Any]:
    record, record_sha = _load_defective_record()

    declared_current = record.get("current_instrument")
    declared_previous = record.get("previous_instrument")
    declared_changed = record.get("changed_files")
    if not isinstance(declared_current, Mapping) or not isinstance(
        declared_previous, Mapping
    ):
        raise SystemExit(
            f"{DEFECTIVE_RECORD_RELATIVE} is missing previous/current blocks"
        )
    if not isinstance(declared_changed, Mapping):
        raise SystemExit(f"{DEFECTIVE_RECORD_RELATIVE} enumerates no changed files")

    declared_tree = str(declared_current.get("src_iqa_soa_tree") or "")
    committed_tree = ir.tree_digest_at_commit(HISTORICAL_COMMIT, RELATIVE_ROOT)

    # (1) Every approved file, declared against committed.  The set that disagrees
    #     must be EXACTLY the set this correction reconstructs -- no more.
    committed_files: dict[str, str] = {}
    disagreeing: list[str] = []
    for key in sorted(declared_changed):
        relative = str(key)
        if not relative.startswith(f"{RELATIVE_ROOT}/"):
            continue
        entry = declared_changed[key]
        if not isinstance(entry, Mapping):
            raise SystemExit(f"{relative} has no structured entry to correct")
        committed = ir.sha256_of_blob_at_commit(HISTORICAL_COMMIT, relative)
        if committed is None:
            raise SystemExit(
                f"{relative} is absent at {HISTORICAL_COMMIT}; the approved set "
                "and the commit disagree about which files exist, which is not a "
                "line-ending defect"
            )
        committed_files[relative] = committed
        if str(entry.get("sha256") or "") != committed:
            disagreeing.append(relative)
    if tuple(disagreeing) != AFFECTED_FILES:
        raise SystemExit(
            "the files whose declared digest history cannot reproduce are "
            f"{disagreeing}, not the diagnosed {list(AFFECTED_FILES)}. A "
            "discrepancy this correction has not proved is NOT corrected here: "
            "diagnose it, do not absorb it."
        )

    # (2) The reconstruction, in both directions, per affected file.
    reconstruction: dict[str, Any] = {}
    reconstructed_sha: dict[str, str] = {}
    for relative in AFFECTED_FILES:
        blob = ir._git("cat-file", "blob", f"{HISTORICAL_COMMIT}:{relative}")
        declared_sha = str(declared_changed[relative].get("sha256") or "")
        rebuilt = ir.crlf_reconstruction(blob, BARE_LF_TERMINATOR_INDICES)
        rebuilt_sha = ir.sha256_of_bytes(rebuilt)
        if rebuilt_sha != declared_sha:
            raise SystemExit(
                f"the line-ending reconstruction of {relative} hashes to "
                f"{rebuilt_sha!r}, not the declared {declared_sha!r}. The defect "
                "is NOT explained by line endings alone and this correction "
                "refuses to assert that it is."
            )
        if rebuilt.replace(b"\r\n", b"\n") != blob:
            raise SystemExit(
                f"the reconstruction of {relative} does not normalize back to the "
                "committed blob; it is not a pure line-ending transform"
            )
        reconstructed_sha[relative] = rebuilt_sha
        terminators = blob.count(b"\n")
        reconstruction[relative] = {
            "convention": "eol-mask-v1",
            "purpose": (
                "Preserve the exact byte representation of the non-conformant "
                "mixed-EOL materialization the defective record's digests were "
                "captured over, so both of them stay reconstructible from "
                "committed bytes after the working tree is refreshed to canonical "
                "LF under docs/hash_basis_policy.md section 7."
            ),
            "canonical_source": relative,
            "canonical_source_sha256": committed_files[relative],
            "canonical_source_bytes": len(blob),
            "capture_canonical_source_commit": HISTORICAL_COMMIT,
            "total_lf_terminators": terminators,
            "index_basis": (
                "0-based LF-terminator ordinal in canonical LF byte stream"
            ),
            "bare_lf_terminator_indices": list(BARE_LF_TERMINATOR_INDICES),
            "bare_lf_terminator_count": len(BARE_LF_TERMINATOR_INDICES),
            "all_other_lf_terminators_are_crlf": True,
            "capture_verified_against_original_worktree": True,
            "reconstructed_byte_length": len(rebuilt),
            "reconstructed_crlf_count": rebuilt.count(b"\r\n"),
            "reconstructed_bare_lf_count": (
                rebuilt.count(b"\n") - rebuilt.count(b"\r\n")
            ),
            "reconstructed_sha256": rebuilt_sha,
            "historical_recorded_sha256": declared_sha,
            "crlf_to_lf_normalization_yields_committed_blob_bytes": True,
            "uniform_crlf_materialization_reproduces_historical_bytes": (
                ir.sha256_of_bytes(blob.replace(b"\n", b"\r\n")) == declared_sha
            ),
            "content_difference_beyond_line_endings": False,
        }

    # (3) The tree digest mismatch must be FULLY explained by (2) and nothing else.
    digest = hashlib.sha256()
    for relative in ir.tracked_files_at_commit(HISTORICAL_COMMIT, RELATIVE_ROOT):
        committed = ir.sha256_of_blob_at_commit(HISTORICAL_COMMIT, relative)
        value = reconstructed_sha.get(relative, committed or "")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    rebuilt_tree = digest.hexdigest()
    if rebuilt_tree != declared_tree:
        raise SystemExit(
            f"recomputing the {RELATIVE_ROOT} tree at {HISTORICAL_COMMIT} with the "
            f"reconstructed line endings gives {rebuilt_tree!r}, not the declared "
            f"{declared_tree!r}. The declared tree digest is not explained by the "
            "line-ending defect alone; the chain of custody is broken by something "
            "this correction has not proved and must not paper over."
        )

    corrected_current: dict[str, Any] = {
        key: declared_current.get(key)
        for key in (
            "adapter_unchanged",
            "instrument_version",
            "native_tool_adapter_version",
            "raw_schema_version",
            "tool_argument_contract_version",
        )
    }
    corrected_current["src_iqa_soa_tree"] = committed_tree

    return {
        "record_kind": "instrument_revision_custody_correction",
        "correction_kind": "line_ending_custody_reconstruction",
        "correction_status": "AUTHORITATIVE_CUSTODY_STATE",
        "title": (
            "Custody correction for the POST_PHASEP_CONFIRMATORY instrument "
            "revision: two declared digests captured over CRLF working-tree bytes"
        ),
        "phase": PHASE,
        "corrects_record": DEFECTIVE_RECORD_RELATIVE,
        "corrects_record_sha256": record_sha,
        "corrects_record_preserved": (
            "The defective record is PRESERVED BYTE-FOR-BYTE and is not replaced, "
            "edited, regenerated or deleted. It remains the third link of the "
            "approved chain and the only statement of what that revision actually "
            "approved, and it is now additionally AUTHENTICATED: "
            "scripts/instrument_revision.py pins corrects_record_sha256 and fails "
            "closed if one byte of it ever moves. It is retained as HISTORICAL "
            "EVIDENCE OF THE DEFECT, which is why it was not rewritten to make its "
            "own hashes pass."
        ),
        "historical_commit": HISTORICAL_COMMIT,
        "historical_commit_basis": (
            "The last commit at which the corrected record was the approved head, "
            "and therefore the commit from which a superseded link's claims are "
            "proved. Its blobs are immutable, so the corrected custody state is "
            "reproducible from history forever."
        ),
        "relative_root": RELATIVE_ROOT,
        "original_declared": {
            "src_iqa_soa_tree": declared_tree,
            "changed_files_sha256": {
                relative: str(declared_changed[relative].get("sha256") or "")
                for relative in sorted(committed_files)
            },
        },
        "actual_committed": {
            "src_iqa_soa_tree": committed_tree,
            "changed_files_sha256": dict(sorted(committed_files.items())),
        },
        "affected_files": list(AFFECTED_FILES),
        "unaffected_declared_files_reproduce_exactly": [
            relative
            for relative in sorted(committed_files)
            if relative not in AFFECTED_FILES
        ],
        "cause": (
            "LINE ENDINGS, AND NOTHING ELSE. instrument_revision.sha256_of hashes "
            "RAW working-tree bytes and never normalizes, by the deliberate rule "
            "in docs/hash_basis_policy.md, so the HEAD of the revision chain is "
            "pinned to working-tree digests while a SUPERSEDED link is proved from "
            "COMMITTED blobs by _check_historical_link. Those two bases agree only "
            "while the working tree is byte-identical to its commit. This "
            "repository declares '* text=auto eol=lf' in .gitattributes, so git "
            "normalizes CRLF to LF on commit and reports the working-tree file as "
            "UNCHANGED -- git status, git diff and git diff --check all stay "
            "silent -- while the raw bytes hash differently. "
            + ", ".join(AFFECTED_FILES)
            + " was written into the working tree with CRLF on 3875 of its 3912 "
            "newlines, so the digest captured for it, and the tree digest computed "
            "over it, describe bytes no commit can hold. The record was correct "
            "about WHAT changed and WHY; it captured the affected file's digest on "
            "the wrong byte basis. docs/hash_basis_policy.md section 6.1 states "
            "the rule that was missed: verify checkout conformance -- no CRLF in "
            "the working-tree bytes -- BEFORE generating a frozen artifact. "
            "Section 6.3 states the repair: never edit a recorded digest to make "
            "a check pass; record the difference in a new amendment, which is "
            "what this record is."
        ),
        "historical_eol_reconstruction": reconstruction,
        "governing_policy": "docs/hash_basis_policy.md",
        "eol_mask_precedent": "docs/hash_basis_amendment_v1.json",
        "no_semantic_source_change_invented": (
            "PROVED, not asserted. The reconstruction recipe recorded above can "
            "only ADD carriage returns before newlines that already exist in the "
            "COMMITTED blob: it cannot add, remove, reorder or alter a single "
            "source character, statement, literal or value. Applying it to the "
            "committed blob reproduces the defective record's declared per-file "
            "SHA-256 EXACTLY, and stripping CRLF back to LF returns the committed "
            "blob byte-for-byte; substituting the reconstructed digest into the "
            "committed tree at the historical commit reproduces the defective "
            "record's declared TREE digest EXACTLY. Both historical mismatches are "
            "therefore reproduced by one cause with no residue. No source edit is "
            "invented, implied or performed by this correction: the corrected "
            "digests are read from committed bytes, never authored."
        ),
        "corrected_previous_instrument": dict(declared_previous),
        "corrected_current_instrument": corrected_current,
        "instrument_version": declared_current.get("instrument_version"),
        "raw_schema_version": declared_current.get("raw_schema_version"),
        "native_tool_adapter_version": declared_current.get(
            "native_tool_adapter_version"
        ),
        "tool_argument_contract_version": declared_current.get(
            "tool_argument_contract_version"
        ),
        "corrected_scope": (
            "EXACTLY two values are superseded: "
            "current_instrument.src_iqa_soa_tree, and the single per-file SHA-256 "
            "named in affected_files. Every other value in the corrected record -- "
            "its parent commit, its previous_instrument block, its approved change "
            "set, every scientific reason, every benchmark hash, every version "
            "constant and every scientific statement -- stands exactly as written "
            "and is unchanged by this correction. The corrected record's "
            "previous_instrument block is reproduced here verbatim because the "
            "Phase-O hand-off it names was never defective: it is provable from "
            "committed bytes at its own parent commit today."
        ),
        "custody_correction_not_scientific_revision": (
            "This is a CUSTODY CORRECTION, not a scientific revision. It changes "
            "no source byte, approves no change, revises no instrument, moves no "
            "version constant, creates no candidate and authorizes nothing. It "
            "records which bytes the third link's digests were computed over, so "
            "that the link -- whose subject matter never changed -- becomes "
            "provable from history again. INSTRUMENT_VERSION remains '4', "
            "RAW_SCHEMA_VERSION remains 5 and NATIVE_TOOL_ADAPTER_VERSION remains "
            "native-tools-adapter-3 for the corrected link, exactly as that link "
            "declared them."
        ),
        "phase_p_evidence_untouched": (
            "The official Phase-P evidence root is not read, enumerated, "
            "traversed, hashed, regenerated, resumed, repaired, replaced or "
            "modified by this correction or by "
            "scripts/post_phaseP_write_confirmatory_custody_correction.py, and no "
            "value in this record is derived from it."
        ),
        "phase_p_interpretation_unchanged": (
            "No Phase-P interpretation moves. The completed official Phase-P "
            "qualification of pilot-v7-rc4 ended SCHEDULE_COMPLETE_VERDICT_HOLD, "
            "pilot-v7-rc4 remains UNQUALIFIED, the preserved invalidated cell "
            "remains MODEL_PROTOCOL_INVALID and BEN-003 remains MATRIX_INVALID. No "
            "Phase-P cell is rerun, resumed, repaired or rescored, no Phase-P row "
            "is reclassified, and no Phase-P row is reinterpreted under schema 6 "
            "or instrument 5: every Phase-P row remains instrument 4 / raw schema "
            "5 / native-tools-adapter-3."
        ),
        "verifier_not_weakened": (
            "scripts/instrument_revision.py gains no general tolerance for a "
            "line-ending or hash mismatch. verify_custody_correction re-derives "
            "every corrected value from COMMITTED bytes, re-runs the "
            "reconstruction in both directions, and applies the correction ONLY to "
            "the chain link whose own bytes hash to the pinned "
            "corrects_record_sha256 at the pinned historical commit. A malformed, "
            "unproved, absent or differently-addressed correction leaves the "
            "original failures standing: every other predecessor mismatch still "
            "FAILS CLOSED, and every future link still requires exact "
            "committed-byte proof."
        ),
        "model_inference_performed": False,
        "provider_contacted": False,
        "phase_p_execution_rerun": False,
        "phase_p_result_reinterpreted": False,
        "historical_rows_rescored": False,
        "benchmark_freeze_records_overwritten": False,
        "instrument_revisions_overwritten": False,
        "source_bytes_changed_by_this_correction": False,
        "ben_003_rehabilitated": False,
        "authorizes_confirmatory_execution": False,
        "offline_validator": "scripts/instrument_revision.py",
        "offline_writer": (
            "scripts/post_phaseP_write_confirmatory_custody_correction.py"
        ),
        "offline_tests": "tests/integration/test_post_phaseP_instrument_revision.py",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ir.CUSTODY_CORRECTION_PATH)
    parser.add_argument("--print", action="store_true", help="write nothing")
    args = parser.parse_args()

    record = build_record()
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.print:
        print(payload, end="")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {args.out.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AFFECTED_FILES",
    "BARE_LF_TERMINATOR_INDICES",
    "DEFECTIVE_RECORD_RELATIVE",
    "DEFECTIVE_RECORD_SHA256",
    "HISTORICAL_COMMIT",
    "PHASE",
    "build_record",
]
