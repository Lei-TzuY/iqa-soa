#!/usr/bin/env python3
"""Provenance for an APPROVED instrument revision, separately hash-pinned.

Phase K froze pilot-v7-rc3 and recorded, in
``benchmark/pilot-v7-rc3/freeze-record.json``, the ``src/iqa_soa`` tree digest
that existed at the moment of the freeze.  ``validate_pilot_v7_rc3.py`` then
asserted that digest against the CURRENT working tree.

That conflates two different claims:

**A. The historical freeze assertion.**  "When Phase K froze rc3, the instrument
was tree ``1825ca11...``."  This is a closed fact about a past commit.  It must
stay verifiable forever, and nothing a later phase does may make it unprovable.

**B. The present-state assertion.**  "The instrument in the working tree right
now is byte-identical to the one Phase K froze."  This is a claim about today.

Asserting A by checking B is what stopped Phase L-A.  The Phase-K.2
observed-fault contract turned out to be unsatisfiable from what a QA-OFF cell
persisted, and the correct repair -- persisting the four runtime provenance
fields -- was blocked because any byte changed under ``src/iqa_soa`` failed rc3
validation.  An immutability check had silently become a prohibition on ever
repairing a defect it had itself helped hide.

This module separates the two.  A is proved from git history, at the commit
where the freeze happened, using committed bytes.  B is replaced by something
STRICTER than a single tree digest: the current instrument must match an
explicitly approved, reviewed revision record that names its parent digest, its
new digest, every single changed file with that file's own SHA-256, and a
scientific reason for each change.  A drive-by edit under ``src/iqa_soa`` now
fails validation exactly as before -- it is not in the approved set -- while an
approved, reviewed, individually hash-pinned repair passes and is recorded.

The result is more provenance, not less: previously the repo could say only
"src/iqa_soa is unchanged"; it can now say what changed, to what bytes, when,
against which parent, and why.  Nothing historical is rewritten, and the old pin
is preserved rather than overwritten.

This module performs no inference, contacts no provider, and reads only git and
the working tree.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The approved instrument-revision CHAIN, oldest first.  Additive in both
#: senses: no record replaces, edits or overwrites any freeze record, and no
#: LATER record replaces, edits or overwrites an EARLIER one.  Every prior pin
#: remains exactly where it was.
#:
#: (Phase O amendment.)  Phase M assumed a single record, because there was one.
#: Phase O revises the instrument a second time -- it publishes the per-tool
#: sandbox argument contract Phase N proved was hidden, and adds ordered
#: per-action failure telemetry -- so the record set becomes a chain.  Rewriting
#: the Phase-M record to describe the Phase-O tree would have destroyed the only
#: statement of what Phase M actually changed, which is the mistake this whole
#: module exists to prevent.
#:
#: (Post-Phase-P amendment.)  The prospective post-Phase-P confirmatory
#: randomization implementation (Work Units 1-6) legitimately changed
#: ``src/iqa_soa``, so a THIRD link is appended on exactly the same terms.  The
#: Phase-O record is not edited to describe the new tree; it keeps describing the
#: tree it actually approved, and is from now on proved from COMMITTED bytes at
#: the commit its successor started from.
#:
#: (C3 amendment.)  The accepted post-Phase-P provider observability repair
#: legitimately changed ``src/iqa_soa`` again -- it is the first revision whose
#: version constants MOVE, ``INSTRUMENT_VERSION`` "4" -> "5" and
#: ``RAW_SCHEMA_VERSION`` 5 -> 6 -- so a FOURTH link is appended on exactly the
#: same terms.  No predecessor is edited to describe the new tree; each keeps
#: describing the tree it actually approved, and is proved from COMMITTED bytes
#: at the commit its own successor started from.
#:
#: (Benchmark-identity amendment.)  The first real runtime preflight of the
#: successor configuration discovered that the frozen WU5 capture rule
#: ``benchmark_sha256 = file_sha256(config.benchmark_path)`` was unsatisfiable:
#: ``benchmark_path`` is a benchmark SOURCE ROOT and production configs point it
#: at a directory, which cannot be read as a file.  Repairing the capture path
#: legitimately changed ``src/iqa_soa`` again, so a FIFTH link is appended on
#: exactly the same terms.  Unlike the fourth, its version constants do NOT move:
#: the repair is capture-only, so ``INSTRUMENT_VERSION`` stays "5" and
#: ``RAW_SCHEMA_VERSION`` stays 6, on the rule the third link already stated --
#: no boundary is bumped merely because the tree changed.
#:
#: The chain is verified link by link (see :func:`check_approved_instrument_revision`):
#: each link's parent digest must equal its predecessor's current digest, each
#: non-head link's claims are proved from COMMITTED bytes at the commit its
#: successor started from, and only the HEAD link is asserted against the live
#: working tree.  Appending a phase appends here.
REVISION_CHAIN: tuple[Path, ...] = (
    REPO_ROOT / "docs" / "phaseM_instrument_revision.json",
    REPO_ROOT / "docs" / "phaseO_instrument_revision.json",
    REPO_ROOT / "docs" / "post_phaseP_confirmatory_instrument_revision.json",
    REPO_ROOT / "docs" / "post_phaseP_provider_observability_instrument_revision.json",
    REPO_ROOT
    / "docs"
    / "post_phaseP_runtime_snapshot_benchmark_identity_instrument_revision.json",
)

#: The HEAD of the chain: the revision the CURRENT working tree must match.
#: Retained under its original name so callers written against the single-record
#: form keep working and keep meaning the same thing -- "the approved revision
#: the live instrument is".
REVISION_PATH = REVISION_CHAIN[-1]

#: The instrument tree Phase K froze, and the commit at which it froze it. Both
#: are quoted from ``benchmark/pilot-v7-rc3/freeze-record.json`` and neither is
#: modified by this module.
PHASE_K_SRC_TREE = "1825ca11de6723c10fa557d641b4c3585b20c2f9a1c634e9247d46821a53c4d3"
PHASE_K_FREEZE_COMMIT = "978c8cb1dcb1b6dc5a2ec51a7233a26c114e2569"

#: The ONE proved CUSTODY INCIDENT this module corrects, and the additive record
#: that carries the correction.
#:
#: A revision record's digests are captured by :func:`sha256_of`, which hashes RAW
#: working-tree bytes and never normalizes (``docs/hash_basis_policy.md``), while
#: a SUPERSEDED link is proved by :func:`_check_historical_link` from COMMITTED
#: blobs.  Those two bases agree only while the working tree is byte-identical to
#: its commit.  This repository declares ``* text=auto eol=lf``, so git normalizes
#: on commit and reports a CRLF working-tree file as UNCHANGED while it hashes
#: differently -- and the POST_PHASEP_CONFIRMATORY record was written over a tree
#: in which one approved file carried CRLF.  Its declared tree digest and that one
#: per-file digest describe bytes no commit can ever hold.
#:
#: The defective record is NOT edited.  It is preserved byte-for-byte as the
#: evidence of what the defect was, and is AUTHENTICATED here against
#: :data:`CUSTODY_CORRECTED_RECORD_SHA256`, which is a guarantee the chain did not
#: previously have: one changed byte in it now fails the provenance check.  The
#: corrected, committed-byte-provable custody state lives in a separate additive
#: record, and is admitted only by :func:`verify_custody_correction`, which
#: re-derives every corrected value from committed bytes and re-runs the recorded
#: line-ending reconstruction in BOTH directions before the correction is applied.
#:
#: NOTHING HERE IS A GENERAL TOLERANCE.  The correction is pinned to one record's
#: bytes, one phase, one commit and one instrument root, so it can never attach to
#: another link, another mismatch or a future revision; and a correction that is
#: absent, malformed, differently addressed or unproved changes nothing, leaving
#: the mismatch reported exactly as it was.  Every other predecessor mismatch, and
#: every future link, still requires exact committed-byte proof.
CUSTODY_CORRECTION_PATH = (
    REPO_ROOT
    / "docs"
    / "post_phaseP_confirmatory_instrument_revision_correction.json"
)
CUSTODY_CORRECTED_RECORD_PATH = (
    REPO_ROOT / "docs" / "post_phaseP_confirmatory_instrument_revision.json"
)
CUSTODY_CORRECTED_RECORD_SHA256 = (
    "927c0c3b662990500304214506e6413bf71e9ad4cebe9436c8a2bff2fb21d59a"
)
CUSTODY_CORRECTED_PHASE = "POST_PHASEP_CONFIRMATORY"
CUSTODY_CORRECTION_COMMIT = "883c425daf2e6462877f0626f5fce0664ac85ca9"
CUSTODY_CORRECTION_ROOT = "src/iqa_soa"


class GitUnavailableError(RuntimeError):
    """Git could not be consulted, so a history-based claim cannot be proved."""


def _git(*args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, check=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover
        raise GitUnavailableError(f"git {' '.join(args)} failed: {exc}") from exc
    return completed.stdout


def sha256_of_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_of(path: Path) -> str:
    """Hash raw working-tree bytes; never normalize (docs/hash_basis_policy.md)."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files(relative_root: str) -> list[str]:
    out = _git("ls-files", "-z", "--", relative_root)
    return sorted(x.decode() for x in out.split(b"\0") if x)


def tree_digest(relative_root: str) -> str:
    """Digest of the WORKING TREE under ``relative_root``.

    Path, NUL, the file's own SHA-256, newline -- byte-for-byte the algorithm the
    rc2 and rc3 validators already use, so the values are directly comparable to
    the pins already committed in the freeze records.
    """

    digest = hashlib.sha256()
    for relative in tracked_files(relative_root):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_of(REPO_ROOT / relative).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def tracked_files_at_commit(commit: str, relative_root: str) -> list[str]:
    out = _git("ls-tree", "-r", "-z", "--name-only", commit, "--", relative_root)
    return sorted(x.decode() for x in out.split(b"\0") if x)


def tree_digest_at_commit(commit: str, relative_root: str) -> str:
    """The same digest, computed from COMMITTED bytes at ``commit``.

    This is what makes a historical freeze assertion permanently provable: it
    reads the blobs the commit actually contains, so it returns the same value
    today, after Phase M, and after every later phase.
    """

    digest = hashlib.sha256()
    for relative in tracked_files_at_commit(commit, relative_root):
        blob = _git("cat-file", "blob", f"{commit}:{relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_of_bytes(blob).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def load_revision() -> Mapping[str, Any]:
    """The HEAD approved revision -- the one the live instrument must equal."""

    parsed: Mapping[str, Any] = json.loads(REVISION_PATH.read_text(encoding="utf-8"))
    return parsed


def load_revision_chain() -> list[Mapping[str, Any]]:
    """Every approved revision record, oldest first.

    Raises ``FileNotFoundError`` if a declared link is missing, because a chain
    with a hole in it proves nothing about custody.
    """

    return [
        json.loads(path.read_text(encoding="utf-8")) for path in REVISION_CHAIN
    ]


def sha256_of_blob_at_commit(commit: str, relative: str) -> str | None:
    """Hash a file's COMMITTED bytes at ``commit``, or ``None`` if absent there."""

    try:
        return sha256_of_bytes(_git("cat-file", "blob", f"{commit}:{relative}"))
    except GitUnavailableError:
        return None


def _repo_relative(path: Path) -> str:
    """A path named relative to the repository when it is inside it."""

    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def crlf_reconstruction(blob: bytes, bare_lf_indices: Sequence[int]) -> bytes:
    """Apply an ``eol-mask-v1`` mask to a canonical LF byte stream.

    Enumerates the LF terminators of ``blob`` in stream order: ordinals listed in
    ``bare_lf_indices`` stay a bare LF, every other one becomes CRLF, and no other
    byte is altered.  The convention, and this exact transform, are the ones
    ``docs/hash_basis_amendment_v1.json`` already uses for an earlier incident of
    the same kind.

    It is the only transform a custody correction may claim.  It can ONLY add
    carriage returns before newlines that already exist: it cannot insert, delete,
    reorder or alter one byte of source.  That is exactly why reproducing a
    defective digest with it proves the defect was line endings and nothing else,
    and why a discrepancy caused by anything else cannot satisfy it.
    """

    keep_lf = set(bare_lf_indices)
    out = bytearray()
    ordinal = 0
    for byte in blob:
        if byte == 0x0A:
            if ordinal not in keep_lf:
                out.append(0x0D)
            ordinal += 1
        out.append(byte)
    return bytes(out)


def _tree_digest_from(names: Sequence[str], hashes: Mapping[str, str]) -> str:
    """The canonical tree digest over an explicit path -> SHA-256 table."""

    digest = hashlib.sha256()
    for relative in names:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashes[relative].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def verify_custody_correction(
    *, relative_root: str = "src/iqa_soa", label: str = "A"
) -> tuple[list[str], Mapping[str, Any] | None]:
    """Prove the ONE recorded custody correction, or refuse to apply it.

    Returns ``(failures, applied)``.  ``applied`` is ``None`` unless every check
    below passes, and when it is ``None`` nothing changes: the predecessor
    mismatch the correction addresses is reported exactly as it was.  There is no
    path through this function that accepts a mismatch it has not reproduced.

    The checks, in order, and each a distinct way for a bogus correction to be
    refused:

    i.   it addresses THIS incident -- this record, this phase, this commit, this
         instrument root -- and nothing else;
    ii.  the defective record is preserved byte-for-byte, authenticated against
         the SHA-256 pinned in this module;
    iii. it quotes the defective record's declared values EXACTLY, over exactly
         the defective record's own approved file set, so it cannot correct a
         claim that record never made;
    iv.  every corrected value is re-derived HERE from COMMITTED bytes at the
         historical commit, never taken on the record's word;
    v.   the set of files whose declared digest history cannot reproduce is
         EXACTLY the set the correction reconstructs -- one unexplained file and
         the correction is refused whole;
    vi.  the recorded line-ending reconstruction reproduces each defective
         per-file digest exactly, and normalizes back to the committed blob
         exactly, so no semantic source change is invented;
    vii. substituting those reconstructions into the committed tree reproduces
         the defective TREE digest exactly, so the second mismatch is explained by
         the same one cause with no residue;
    viii. no version is invented: every version the correction carries is the one
         the corrected record itself declared, and the corrected link's parent
         block is that record's own, verbatim.
    """

    if not CUSTODY_CORRECTION_PATH.is_file():
        return [], None
    name = _repo_relative(CUSTODY_CORRECTION_PATH)
    try:
        parsed: Any = json.loads(CUSTODY_CORRECTION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"{label}: {name} is unreadable: {exc}"], None

    def refuse(message: str) -> tuple[list[str], None]:
        return [f"{label}: {name} {message}"], None

    # (0) A syntactically valid JSON document need not be an OBJECT: ``[]``,
    # ``null``, ``3``, ``"x"`` and ``true`` all parse cleanly and none of them is
    # a record.  Refuse them HERE, through the same structured path every other
    # defect takes, so the refusal is a reported validation failure rather than
    # an AttributeError from the first ``.get`` below.  Nothing is coerced,
    # defaulted or recovered, and no check after this point is relaxed.
    if not isinstance(parsed, Mapping):
        return refuse(
            f"is not a JSON object; it parsed as {type(parsed).__name__}. A "
            "correction that is not a record corrects nothing."
        )
    record: Mapping[str, Any] = parsed

    # (i) THIS incident, and no other.
    corrected_relative = _repo_relative(CUSTODY_CORRECTED_RECORD_PATH)
    if record.get("relative_root") != relative_root:
        # It speaks about a different instrument root, so it does not apply here
        # and nothing is relaxed: the unmodified checks run as they always did.
        return [], None
    if relative_root != CUSTODY_CORRECTION_ROOT:  # pragma: no cover - defensive
        return [], None
    if record.get("record_kind") != "instrument_revision_custody_correction":
        return refuse("is not a custody-correction record")
    if record.get("phase") != CUSTODY_CORRECTED_PHASE:
        return refuse(
            f"corrects phase {record.get('phase')!r}, not {CUSTODY_CORRECTED_PHASE!r}"
        )
    if record.get("corrects_record") != corrected_relative:
        return refuse(
            f"names {record.get('corrects_record')!r} as the corrected record, "
            f"not {corrected_relative!r}"
        )
    if record.get("historical_commit") != CUSTODY_CORRECTION_COMMIT:
        return refuse(
            f"reconstructs {record.get('historical_commit')!r}, not the pinned "
            f"{CUSTODY_CORRECTION_COMMIT!r}"
        )

    # (ii) The defective record is preserved, and is now authenticated.
    if not CUSTODY_CORRECTED_RECORD_PATH.is_file():
        return refuse(f"corrects {corrected_relative}, which no longer exists")
    preserved = sha256_of(CUSTODY_CORRECTED_RECORD_PATH)
    if preserved != CUSTODY_CORRECTED_RECORD_SHA256:
        return refuse(
            f"corrects {corrected_relative}, which now hashes to {preserved!r} "
            f"rather than the preserved {CUSTODY_CORRECTED_RECORD_SHA256!r}. The "
            "historical record was EDITED; a correction may supersede its "
            "digests, never rewrite it."
        )
    if record.get("corrects_record_sha256") != CUSTODY_CORRECTED_RECORD_SHA256:
        return refuse(
            f"claims the corrected record hashes to "
            f"{record.get('corrects_record_sha256')!r}, which is not the "
            f"preserved {CUSTODY_CORRECTED_RECORD_SHA256!r}"
        )

    try:
        defective: Mapping[str, Any] = json.loads(
            CUSTODY_CORRECTED_RECORD_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return refuse(f"corrects {corrected_relative}, which is unreadable: {exc}")
    declared_current = defective.get("current_instrument")
    declared_changed = defective.get("changed_files")
    if not isinstance(declared_current, Mapping) or not isinstance(
        declared_changed, Mapping
    ):
        return refuse(f"corrects {corrected_relative}, which is malformed")

    original = record.get("original_declared")
    committed_block = record.get("actual_committed")
    corrected_current = record.get("corrected_current_instrument")
    reconstruction = record.get("historical_eol_reconstruction")
    affected = record.get("affected_files")
    if (
        not isinstance(original, Mapping)
        or not isinstance(committed_block, Mapping)
        or not isinstance(corrected_current, Mapping)
        or not isinstance(reconstruction, Mapping)
        or not isinstance(affected, list)
    ):
        return refuse("is missing a required correction block")
    original_files = original.get("changed_files_sha256")
    committed_files = committed_block.get("changed_files_sha256")
    if not isinstance(original_files, Mapping) or not isinstance(
        committed_files, Mapping
    ):
        return refuse("does not enumerate the declared and committed file digests")

    # (iii) It quotes the defective record EXACTLY, over that record's own set.
    approved = sorted(
        str(item)
        for item in declared_changed
        if str(item).startswith(f"{relative_root}/")
    )
    if sorted(str(item) for item in original_files) != approved:
        return refuse(
            "does not quote exactly the corrected record's approved instrument "
            "file set"
        )
    if str(original.get("src_iqa_soa_tree") or "") != str(
        declared_current.get("src_iqa_soa_tree") or ""
    ):
        return refuse(
            "misquotes the tree digest the corrected record actually declares"
        )
    for relative in approved:
        entry = declared_changed[relative]
        quoted = str(original_files[relative])
        if not isinstance(entry, Mapping) or quoted != str(entry.get("sha256") or ""):
            return refuse(
                f"misquotes the digest the corrected record declares for {relative}"
            )

    # (iv) Every corrected value is re-derived here, from committed bytes.
    try:
        names = tracked_files_at_commit(CUSTODY_CORRECTION_COMMIT, relative_root)
        actual_tree = tree_digest_at_commit(CUSTODY_CORRECTION_COMMIT, relative_root)
    except GitUnavailableError as exc:
        return [
            f"{label}: cannot verify {name} at {CUSTODY_CORRECTION_COMMIT}: {exc}"
        ], None
    if str(corrected_current.get("src_iqa_soa_tree") or "") != actual_tree:
        return refuse(
            f"asserts a corrected tree digest of "
            f"{corrected_current.get('src_iqa_soa_tree')!r}, but at "
            f"{CUSTODY_CORRECTION_COMMIT} the committed tree digests to "
            f"{actual_tree!r}"
        )
    if str(committed_block.get("src_iqa_soa_tree") or "") != actual_tree:
        return refuse("misstates the committed tree digest at the historical commit")
    if sorted(str(item) for item in committed_files) != approved:
        return refuse("does not state a committed digest for every approved file")
    actual_committed: dict[str, str] = {}
    for relative in approved:
        blob_sha = sha256_of_blob_at_commit(CUSTODY_CORRECTION_COMMIT, relative)
        if blob_sha is None or blob_sha != str(committed_files[relative]):
            return refuse(
                f"asserts {relative} hashes to {committed_files[relative]!r} at "
                f"{CUSTODY_CORRECTION_COMMIT}, but it hashes to {blob_sha!r}"
            )
        actual_committed[relative] = blob_sha

    # (v) The unexplained set must be EXACTLY the reconstructed set.
    disagreeing = sorted(
        relative
        for relative in approved
        if str(original_files[relative]) != actual_committed[relative]
    )
    declared_affected = sorted(str(item) for item in affected)
    if disagreeing != declared_affected:
        return refuse(
            f"reconstructs {declared_affected}, but the files whose declared "
            f"digest history cannot reproduce are {disagreeing}. A discrepancy "
            "this correction has not proved is not corrected: it fails closed."
        )
    if sorted(str(item) for item in reconstruction) != declared_affected:
        return refuse("does not carry a reconstruction for every affected file")

    # (vi) The reconstruction reproduces the defect, in both directions.
    rebuilt_hashes = dict(actual_committed)
    for relative in declared_affected:
        proof = reconstruction[relative]
        if not isinstance(proof, Mapping):
            return refuse(f"gives {relative} no structured reconstruction")
        if (
            proof.get("convention") != "eol-mask-v1"
            or proof.get("index_basis")
            != "0-based LF-terminator ordinal in canonical LF byte stream"
            or proof.get("all_other_lf_terminators_are_crlf") is not True
        ):
            return refuse(
                f"does not state {relative}'s reconstruction in the eol-mask-v1 "
                "convention this repository already uses "
                "(docs/hash_basis_amendment_v1.json)"
            )
        indices = proof.get("bare_lf_terminator_indices")
        if not isinstance(indices, list) or not all(
            isinstance(item, int) and not isinstance(item, bool) and item >= 0
            for item in indices
        ):
            return refuse(f"gives {relative} no line-ending reconstruction mask")
        if indices != sorted(indices) or len(set(indices)) != len(indices):
            return refuse(
                f"{relative}'s mask indices are unordered or contain duplicates"
            )
        try:
            blob = _git("cat-file", "blob", f"{CUSTODY_CORRECTION_COMMIT}:{relative}")
        except GitUnavailableError as exc:  # pragma: no cover - git absent
            return [
                f"{label}: cannot read {relative} at the historical "
                f"commit: {exc}"
            ], None
        if b"\r" in blob:
            return refuse(
                f"claims an eol-mask over {relative}, but its committed bytes "
                "already carry CR, so the mask is not lossless"
            )
        if proof.get("canonical_source") != relative or proof.get(
            "canonical_source_sha256"
        ) != actual_committed[relative]:
            return refuse(f"misstates {relative}'s canonical source for the mask")
        if proof.get("total_lf_terminators") != blob.count(b"\n") or any(
            item >= blob.count(b"\n") for item in indices
        ):
            return refuse(
                f"{relative}'s mask indices fall outside its LF-terminator range"
            )
        rebuilt = crlf_reconstruction(blob, indices)
        rebuilt_sha = sha256_of_bytes(rebuilt)
        if rebuilt_sha != str(original_files[relative]):
            return refuse(
                f"reconstructs {relative} to {rebuilt_sha!r}, which is not the "
                f"defective {original_files[relative]!r}. The mismatch is NOT "
                "proved to be line endings and is not corrected."
            )
        if rebuilt.replace(b"\r\n", b"\n") != blob:
            return refuse(
                f"reconstructs {relative} into bytes that do not normalize back "
                "to the committed blob; that is not a pure line-ending transform"
            )
        rebuilt_hashes[relative] = rebuilt_sha

    # (vii) And the tree mismatch is the same one cause, with no residue.
    table = {
        relative: (
            rebuilt_hashes[relative]
            if relative in rebuilt_hashes
            else (sha256_of_blob_at_commit(CUSTODY_CORRECTION_COMMIT, relative) or "")
        )
        for relative in names
    }
    rebuilt_tree = _tree_digest_from(names, table)
    if rebuilt_tree != str(declared_current.get("src_iqa_soa_tree") or ""):
        return refuse(
            f"reconstructs the {relative_root} tree at "
            f"{CUSTODY_CORRECTION_COMMIT} to {rebuilt_tree!r}, which is not the "
            f"defective {declared_current.get('src_iqa_soa_tree')!r}. The declared "
            "tree digest is not explained by the line-ending defect alone."
        )

    # (viii) No version is invented, and the parent hand-off is quoted verbatim.
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        if corrected_current.get(key) != declared_current.get(key):
            return refuse(
                f"asserts {key}={corrected_current.get(key)!r} for the corrected "
                f"link, but that link declares {declared_current.get(key)!r}"
            )
        if record.get(key) != declared_current.get(key):
            return refuse(
                f"restates {key} as something the corrected link never declared"
            )
    if record.get("corrected_previous_instrument") != defective.get(
        "previous_instrument"
    ):
        return refuse(
            "rewrites the corrected link's parent hand-off, which was never "
            "defective and must be carried forward verbatim"
        )

    applied: dict[str, Any] = {
        "record": corrected_relative,
        "correction": name,
        "phase": CUSTODY_CORRECTED_PHASE,
        "commit": CUSTODY_CORRECTION_COMMIT,
        "tree": actual_tree,
        "files": actual_committed,
    }
    return [], applied


def _changed_files_since(commit: str, relative_root: str) -> list[str]:
    out = _git("diff", "--name-only", "-z", commit, "--", relative_root)
    return sorted(x.decode() for x in out.split(b"\0") if x)


def check_historical_freeze_assertion(
    *,
    commit: str = PHASE_K_FREEZE_COMMIT,
    expected_tree: str = PHASE_K_SRC_TREE,
    relative_root: str = "src/iqa_soa",
    label: str = "A",
) -> list[str]:
    """(A) Prove the ORIGINAL freeze claim, from history, at its own commit.

    The old pin is neither overwritten nor deleted.  It is checked where it is
    actually true -- against the commit that made it.
    """

    failures: list[str] = []
    try:
        actual = tree_digest_at_commit(commit, relative_root)
    except GitUnavailableError as exc:
        return [f"{label}: cannot verify the historical freeze assertion: {exc}"]
    if actual != expected_tree:
        failures.append(
            f"{label}: the historical freeze assertion no longer holds: "
            f"{relative_root} at {commit} digests to {actual}, but the freeze "
            f"record pins {expected_tree}. History was rewritten."
        )
    return failures


def _check_chain_link(
    link: Mapping[str, Any],
    *,
    index: int,
    expected_parent_tree: str,
    relative_root: str,
    label: str,
) -> tuple[list[str], str]:
    """Structural checks common to every link, plus its declared new digest.

    Returns ``(failures, current_tree)``.  ``current_tree`` is the digest this
    link claims to have produced, and it becomes the next link's expected parent.
    """

    failures: list[str] = []
    name = str(link.get("phase") or f"link-{index}")
    previous = link.get("previous_instrument")
    current = link.get("current_instrument")
    if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
        return ([f"{label}: revision {name} is missing previous/current blocks"], "")

    # (2) Unbroken chain of custody.  Link 0's parent is the Phase-K freeze; every
    # later link's parent is its predecessor's result.
    if previous.get("src_iqa_soa_tree") != expected_parent_tree:
        failures.append(
            f"{label}: revision {name} parent instrument digest "
            f"{previous.get('src_iqa_soa_tree')!r} is not "
            f"{expected_parent_tree!r}; the chain of custody is broken"
        )

    parent_commit = link.get("parent_commit")
    changed = link.get("changed_files")
    if not isinstance(parent_commit, str) or not parent_commit:
        failures.append(f"{label}: revision {name} does not name its parent commit")
    if not isinstance(changed, Mapping):
        failures.append(f"{label}: revision {name} does not enumerate changed files")
    else:
        for file_name in sorted(changed):
            if not file_name.startswith(f"{relative_root}/"):
                continue
            entry = changed[file_name]
            if not isinstance(entry, Mapping):
                failures.append(
                    f"{label}: revision {name} gives {file_name} no structured entry"
                )
                continue
            reason = entry.get("reason")
            if not isinstance(reason, str) or len(reason.strip()) < 20:
                failures.append(
                    f"{label}: revision {name} records no scientific reason for "
                    f"{file_name}"
                )
    return failures, str(current.get("src_iqa_soa_tree") or "")


def _check_historical_link(
    link: Mapping[str, Any],
    *,
    successor_parent_commit: str,
    relative_root: str,
    label: str,
    correction: Mapping[str, Any] | None = None,
) -> list[str]:
    """Prove a SUPERSEDED link's claims from COMMITTED bytes, never from today.

    A link that is no longer the head describes a tree the working directory has
    since moved past.  Asserting its per-file hashes against the current tree
    would be exactly the "assert A by checking B" conflation this module was
    written to remove: it would make every superseded revision permanently false,
    which is the opposite of preserving it.

    The claims are instead proved where they are actually true -- at the commit
    its SUCCESSOR started from, which is the last commit at which that link was
    the approved head.  Those bytes are immutable, so this stays provable forever.

    ``correction``, when given, is an ALREADY PROVED custody correction from
    :func:`verify_custody_correction`: the link's own declared digests were
    captured on the wrong byte basis, and the corrected values -- re-derived from
    the very commit this function reads -- stand in their place.  Nothing else
    changes: the digests are still compared, still against committed bytes, still
    exactly, and a correction recorded at any other commit is refused rather than
    applied.
    """

    failures: list[str] = []
    name = str(link.get("phase") or "link")
    current = link.get("current_instrument")
    if not isinstance(current, Mapping):  # pragma: no cover - caught upstream
        return failures
    declared = str(current.get("src_iqa_soa_tree") or "")
    corrected_files: Mapping[str, str] = {}
    if correction is not None:
        if str(correction["commit"]) != successor_parent_commit:
            return [
                f"{label}: the custody correction for {name} reconstructs "
                f"{correction['commit']!r}, but this link is proved at "
                f"{successor_parent_commit!r}; the correction does not apply here"
            ]
        declared = str(correction["tree"])
        corrected_files = correction["files"]
    try:
        actual = tree_digest_at_commit(successor_parent_commit, relative_root)
    except GitUnavailableError as exc:
        return [
            f"{label}: cannot verify superseded revision {name} at "
            f"{successor_parent_commit}: {exc}"
        ]
    corrected = " (as corrected)" if correction is not None else ""
    if actual != declared:
        failures.append(
            f"{label}: superseded revision {name} claims{corrected} {relative_root} "
            f"tree {declared!r}, but at {successor_parent_commit} -- the last commit "
            f"at which it was the approved head -- the committed tree digests to "
            f"{actual!r}. History was rewritten or the chain is out of order."
        )
    changed = link.get("changed_files")
    if isinstance(changed, Mapping):
        for file_name, entry in sorted(changed.items()):
            if not file_name.startswith(f"{relative_root}/"):
                continue
            if not isinstance(entry, Mapping):
                continue
            committed = sha256_of_blob_at_commit(successor_parent_commit, file_name)
            expected = corrected_files.get(file_name, entry.get("sha256"))
            if committed != expected:
                failures.append(
                    f"{label}: superseded revision {name} approves{corrected} "
                    f"{file_name} at {expected!r}, but at {successor_parent_commit} "
                    f"it hashes to {committed!r}"
                )
    return failures


def check_approved_instrument_revision(
    *, relative_root: str = "src/iqa_soa", label: str = "A"
) -> list[str]:
    """(B) The CURRENT instrument must be the HEAD of an approved revision chain.

    Every one of these must hold, and each is a distinct way for an unapproved
    edit to be caught:

    1. every declared revision record exists and names its parent commit,
       digests and changed files;
    2. the chain of custody is unbroken -- link 0's parent instrument digest is
       the digest the Phase-K freeze pinned, and every later link's parent digest
       is its predecessor's result;
    3. every SUPERSEDED link still proves out against COMMITTED bytes at the
       commit its successor started from, so an earlier revision can never be
       quietly rewritten to describe a later tree;
    4. the working tree digests to exactly the HEAD link's new pinned value;
    5. the set of files changed since the HEAD link's parent commit is exactly
       that link's approved set -- no extra file, no missing file;
    6. every file the HEAD link approves hashes to its approved SHA-256, and
       every approved file in every link carries a non-empty scientific reason;
    7. the HEAD link's recorded instrument and raw-schema versions agree with the
       code.

    One superseded link's digests were captured over CRLF working-tree bytes that
    no commit can hold, and are superseded -- never rewritten -- by the additive
    custody correction proved in :func:`verify_custody_correction`; see
    :data:`CUSTODY_CORRECTION_PATH`.  That correction is pinned to one record's
    bytes, one phase and one commit, adds no tolerance anywhere else, and when it
    does not prove out it is withheld, so (3) fails exactly as it would have.
    """

    failures: list[str] = []
    missing = [path for path in REVISION_CHAIN if not path.is_file()]
    if missing:
        return [
            f"{label}: {relative_root} differs from the last freeze but the approved "
            "instrument revision chain is incomplete; missing "
            + ", ".join(item.relative_to(REPO_ROOT).as_posix() for item in missing)
        ]
    try:
        chain = load_revision_chain()
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{label}: instrument revision record is unreadable: {exc}"]
    if not chain:  # pragma: no cover - REVISION_CHAIN is never empty
        return [f"{label}: the approved instrument revision chain is empty"]

    # (0) The one proved custody correction, or nothing.  A correction that does
    # not prove out is reported here AND withheld, so the mismatch it addresses is
    # still reported below exactly as it was.
    correction_failures, correction = verify_custody_correction(
        relative_root=relative_root, label=label
    )
    failures.extend(correction_failures)
    corrected_index = -1
    if correction is not None:
        for index, path in enumerate(REVISION_CHAIN):
            if path != CUSTODY_CORRECTED_RECORD_PATH:
                continue
            if index < len(chain) and chain[index].get("phase") == correction["phase"]:
                corrected_index = index
            break

    # (1)-(2), and the reason half of (6), over every link in order.
    expected_parent = PHASE_K_SRC_TREE
    for index, link in enumerate(chain):
        link_failures, produced = _check_chain_link(
            link,
            index=index,
            expected_parent_tree=expected_parent,
            relative_root=relative_root,
            label=label,
        )
        failures.extend(link_failures)
        if not produced:
            return failures
        if index == corrected_index and correction is not None:
            # The corrected link's own pin was captured on the wrong byte basis,
            # so the digest it hands to its successor is the committed one.
            produced = str(correction["tree"])
        expected_parent = produced

    # (3) Superseded links are proved from history, at the commit their successor
    # started from -- never against the working tree.
    for index in range(len(chain) - 1):
        successor_parent = chain[index + 1].get("parent_commit")
        if not isinstance(successor_parent, str) or not successor_parent:
            continue
        failures.extend(
            _check_historical_link(
                chain[index],
                successor_parent_commit=successor_parent,
                relative_root=relative_root,
                label=label,
                correction=correction if index == corrected_index else None,
            )
        )

    head = chain[-1]
    current = head.get("current_instrument")
    if not isinstance(current, Mapping):  # pragma: no cover - caught above
        return failures

    # (4) The working tree is exactly the approved HEAD revision.
    try:
        actual_tree = tree_digest(relative_root)
    except GitUnavailableError as exc:
        return [*failures, f"{label}: cannot digest the working instrument tree: {exc}"]
    if actual_tree != current.get("src_iqa_soa_tree"):
        failures.append(
            f"{label}: the working {relative_root} tree digests to {actual_tree}, "
            f"which is not the approved revision "
            f"{current.get('src_iqa_soa_tree')!r}. Either an unapproved edit was "
            "made, or the revision record was not regenerated."
        )

    # (5)-(6) Exactly the approved files changed since the head link's parent, to
    # exactly the approved bytes.
    parent_commit = head.get("parent_commit")
    changed = head.get("changed_files")
    if isinstance(parent_commit, str) and parent_commit and isinstance(changed, Mapping):
        approved = {name for name in changed if name.startswith(f"{relative_root}/")}
        try:
            observed = set(_changed_files_since(parent_commit, relative_root))
        except GitUnavailableError as exc:
            return [*failures, f"{label}: cannot enumerate instrument changes: {exc}"]
        for name in sorted(observed - approved):
            failures.append(
                f"{label}: {name} changed since {parent_commit} but is not in the "
                "approved instrument revision"
            )
        for name in sorted(approved - observed):
            failures.append(
                f"{label}: the revision record approves {name}, which did not "
                f"actually change since {parent_commit}"
            )
        for name in sorted(approved & observed):
            entry = changed[name]
            if not isinstance(entry, Mapping):  # pragma: no cover - checked above
                continue
            actual_file = sha256_of(REPO_ROOT / name)
            if actual_file != entry.get("sha256"):
                failures.append(
                    f"{label}: {name} hashes to {actual_file}, not the approved "
                    f"{entry.get('sha256')!r}"
                )

    # (7) The recorded versions must be the versions the code actually declares.
    import sys

    src = str(REPO_ROOT / "src")
    if src not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, src)
    from iqa_soa.instrument import INSTRUMENT_VERSION, RAW_SCHEMA_VERSION

    if current.get("instrument_version") != INSTRUMENT_VERSION:
        failures.append(
            f"{label}: the revision record declares instrument_version "
            f"{current.get('instrument_version')!r}, but the code declares "
            f"{INSTRUMENT_VERSION!r}"
        )
    if current.get("raw_schema_version") != RAW_SCHEMA_VERSION:
        failures.append(
            f"{label}: the revision record declares raw_schema_version "
            f"{current.get('raw_schema_version')!r}, but the code declares "
            f"{RAW_SCHEMA_VERSION!r}"
        )
    return failures


def check_instrument_provenance(
    *, relative_root: str = "src/iqa_soa", label: str = "A"
) -> list[str]:
    """Both halves: the historical assertion AND the approved current revision.

    When the working tree still matches the frozen digest exactly, no revision
    record is required and none is consulted -- an unrevised repository behaves
    exactly as it did before this module existed.
    """

    failures = check_historical_freeze_assertion(
        relative_root=relative_root, label=label
    )
    try:
        if tree_digest(relative_root) == PHASE_K_SRC_TREE:
            return failures
    except GitUnavailableError as exc:  # pragma: no cover - git absent
        return [*failures, f"{label}: cannot digest {relative_root}: {exc}"]
    return [
        *failures,
        *check_approved_instrument_revision(relative_root=relative_root, label=label),
    ]


def summary() -> Mapping[str, Any]:
    """A machine-readable statement of where the instrument stands."""

    revised = tree_digest("src/iqa_soa") != PHASE_K_SRC_TREE
    correction_failures, correction = verify_custody_correction()
    return {
        "custody_correction_record": (
            _repo_relative(CUSTODY_CORRECTION_PATH)
            if CUSTODY_CORRECTION_PATH.is_file()
            else None
        ),
        "custody_correction_applies_to": CUSTODY_CORRECTED_PHASE,
        "custody_correction_holds": not correction_failures and correction is not None,
        "custody_corrected_record_preserved_sha256": CUSTODY_CORRECTED_RECORD_SHA256,
        "phase_k_frozen_src_tree": PHASE_K_SRC_TREE,
        "phase_k_freeze_commit": PHASE_K_FREEZE_COMMIT,
        "historical_assertion_holds": not check_historical_freeze_assertion(),
        "current_src_tree": tree_digest("src/iqa_soa"),
        "instrument_revised_since_freeze": revised,
        "approved_revision_holds": not check_approved_instrument_revision()
        if revised
        else True,
        "approved_revision_chain": [
            path.relative_to(REPO_ROOT).as_posix() for path in REVISION_CHAIN
        ],
        "approved_revision_head": REVISION_PATH.relative_to(REPO_ROOT).as_posix(),
        "model_inference_performed": False,
    }


def main() -> int:
    failures = check_instrument_provenance()
    print(json.dumps(summary(), indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"instrument provenance: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s))"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CUSTODY_CORRECTED_PHASE",
    "CUSTODY_CORRECTED_RECORD_PATH",
    "CUSTODY_CORRECTED_RECORD_SHA256",
    "CUSTODY_CORRECTION_COMMIT",
    "CUSTODY_CORRECTION_PATH",
    "CUSTODY_CORRECTION_ROOT",
    "PHASE_K_FREEZE_COMMIT",
    "PHASE_K_SRC_TREE",
    "REVISION_CHAIN",
    "REVISION_PATH",
    "check_approved_instrument_revision",
    "check_historical_freeze_assertion",
    "check_instrument_provenance",
    "crlf_reconstruction",
    "load_revision",
    "load_revision_chain",
    "sha256_of_blob_at_commit",
    "summary",
    "tree_digest",
    "tree_digest_at_commit",
    "verify_custody_correction",
]
