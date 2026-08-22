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

#: The approved instrument-revision record.  Additive: it does not replace, edit
#: or overwrite any freeze record, and every prior pin remains where it was.
REVISION_PATH = REPO_ROOT / "docs" / "phaseM_instrument_revision.json"

#: The instrument tree Phase K froze, and the commit at which it froze it. Both
#: are quoted from ``benchmark/pilot-v7-rc3/freeze-record.json`` and neither is
#: modified by this module.
PHASE_K_SRC_TREE = "1825ca11de6723c10fa557d641b4c3585b20c2f9a1c634e9247d46821a53c4d3"
PHASE_K_FREEZE_COMMIT = "978c8cb1dcb1b6dc5a2ec51a7233a26c114e2569"


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
    parsed: Mapping[str, Any] = json.loads(REVISION_PATH.read_text(encoding="utf-8"))
    return parsed


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


def check_approved_instrument_revision(
    *, relative_root: str = "src/iqa_soa", label: str = "A"
) -> list[str]:
    """(B) The CURRENT instrument must be an approved, hash-pinned revision.

    Every one of these must hold, and each is a distinct way for an unapproved
    edit to be caught:

    1. the revision record exists and names its parent commit and digests;
    2. its parent instrument digest is exactly the digest the previous freeze
       pinned, so the chain of custody is unbroken;
    3. the working tree digests to exactly the new pinned value;
    4. the set of files changed since the parent commit is exactly the approved
       set -- no extra file, no missing file;
    5. every approved file's current bytes hash to its approved SHA-256;
    6. every approved file carries a non-empty scientific reason;
    7. the recorded instrument and raw-schema versions agree with the code.
    """

    failures: list[str] = []
    if not REVISION_PATH.is_file():
        return [
            f"{label}: {relative_root} differs from the last freeze but no approved "
            f"instrument revision record exists at "
            f"{REVISION_PATH.relative_to(REPO_ROOT).as_posix()}"
        ]
    try:
        record = load_revision()
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{label}: instrument revision record is unreadable: {exc}"]

    previous = record.get("previous_instrument")
    current = record.get("current_instrument")
    if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
        return [f"{label}: instrument revision record is missing previous/current blocks"]

    # (2) Unbroken chain of custody back to the previous freeze.
    if previous.get("src_iqa_soa_tree") != PHASE_K_SRC_TREE:
        failures.append(
            f"{label}: the revision record's parent instrument digest "
            f"{previous.get('src_iqa_soa_tree')!r} is not the Phase-K frozen "
            f"digest {PHASE_K_SRC_TREE!r}; the chain of custody is broken"
        )

    # (3) The working tree is exactly the approved revision.
    try:
        actual_tree = tree_digest(relative_root)
    except GitUnavailableError as exc:
        return [f"{label}: cannot digest the working instrument tree: {exc}"]
    if actual_tree != current.get("src_iqa_soa_tree"):
        failures.append(
            f"{label}: the working {relative_root} tree digests to {actual_tree}, "
            f"which is not the approved revision "
            f"{current.get('src_iqa_soa_tree')!r}. Either an unapproved edit was "
            "made, or the revision record was not regenerated."
        )

    # (4)-(6) Exactly the approved files changed, to exactly the approved bytes,
    # each for a stated reason.
    parent_commit = record.get("parent_commit")
    changed = record.get("changed_files")
    if not isinstance(parent_commit, str) or not parent_commit:
        failures.append(f"{label}: the revision record does not name its parent commit")
    elif not isinstance(changed, Mapping):
        failures.append(f"{label}: the revision record does not enumerate changed files")
    else:
        approved = {
            name for name in changed if name.startswith(f"{relative_root}/")
        }
        try:
            observed = set(_changed_files_since(parent_commit, relative_root))
        except GitUnavailableError as exc:
            return [f"{label}: cannot enumerate instrument changes: {exc}"]
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
            if not isinstance(entry, Mapping):
                failures.append(f"{label}: {name} has no structured revision entry")
                continue
            actual_file = sha256_of(REPO_ROOT / name)
            if actual_file != entry.get("sha256"):
                failures.append(
                    f"{label}: {name} hashes to {actual_file}, not the approved "
                    f"{entry.get('sha256')!r}"
                )
            reason = entry.get("reason")
            if not isinstance(reason, str) or len(reason.strip()) < 20:
                failures.append(
                    f"{label}: {name} carries no scientific reason for the change"
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
    return {
        "phase_k_frozen_src_tree": PHASE_K_SRC_TREE,
        "phase_k_freeze_commit": PHASE_K_FREEZE_COMMIT,
        "historical_assertion_holds": not check_historical_freeze_assertion(),
        "current_src_tree": tree_digest("src/iqa_soa"),
        "instrument_revised_since_freeze": revised,
        "approved_revision_holds": not check_approved_instrument_revision()
        if revised
        else True,
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
    "PHASE_K_FREEZE_COMMIT",
    "PHASE_K_SRC_TREE",
    "REVISION_PATH",
    "check_approved_instrument_revision",
    "check_historical_freeze_assertion",
    "check_instrument_provenance",
    "load_revision",
    "summary",
    "tree_digest",
    "tree_digest_at_commit",
]
