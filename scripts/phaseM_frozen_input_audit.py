#!/usr/bin/env python3
"""Audit every frozen bound input a committed provenance record binds by hash.

WHY THIS EXISTS
===============

A phase that runs real models freezes its scientific inputs *prospectively*: it
records, in its own provenance artifact, the SHA-256 of every file the result
depends on, and it does so BEFORE the result is read.  That is what makes the
result falsifiable rather than merely archived -- an input whose bytes may move
afterwards is not an input, it is a variable.

``results/phaseI-rc2-requalification/phaseI-provenance.json`` binds

    scripts/analyze_phaseI_requalification.py
        -> 2ec5e5f40618e27400a534465d380be0092fb0b0cd1bd013aac562f99f80798e

inside ``bound_inputs``.  The first Phase-M revision edited that file so the
frozen Phase-I results would stay readable after the instrument moved to
version "3" / raw schema 4.  The compatibility problem was real; the remedy was
not.  Git preserving the old bytes does not authorize changing a frozen bound
input in the CURRENT scientific tree, and re-recording the new hash would have
been worse still -- it would have made the record describe whatever the file
happens to contain, which is the opposite of a freeze.

Phase M.1 restores those bytes and moves the compatibility fix entirely outside
frozen paths (``scripts/phaseM_historical_analysis.py``).  This module is the
standing regression guard: it re-derives the expected hashes FROM the committed
provenance rather than from anything Phase M wrote, so it keeps working for
phases that do not exist yet.

WHAT IS AND IS NOT A LIVE CONTRACT
==================================

Not every recorded hash is a promise about today's working tree, and pretending
otherwise would make this audit fail for reasons that predate Phase M by many
phases.  Two classes are distinguished, from the container key, not by taste:

``bound_inputs`` -- FROZEN_BOUND_INPUT.
    The inputs a phase bound before reading its result.  These MUST still match
    the current working tree.  A mismatch is a hard failure.

``input_sha256`` -- ENVIRONMENT_SNAPSHOT.
    Phase A recorded the state of its execution environment at freeze time,
    including instrument sources that later phases were always expected to
    repair.  Several of these diverged at the Phase-B instrument repair, long
    before Phase M.  They are verified against the commit that recorded them --
    proving history was not rewritten -- and reported, never silently dropped.

A third rule applies to BOTH classes and is the one that decides the Phase-M.1
question directly:

    NO REGRESSION.  Any binding that matched the working tree at the Phase-M
    parent commit must still match it now.

That predicate inherits no historical debt and cannot be satisfied by editing a
provenance file, because the parent commit's provenance bytes are read from git.

This module performs no inference, contacts no provider, and reads only git and
the working tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The commit Phase M started from.  Rule 3 is evaluated against it: a binding
#: that held here and does not hold now was broken BY Phase M.
PHASE_M_PARENT_COMMIT = "eace204d4c27a9ca48d3c0a660832f640b7a900b"

#: Mapping keys that carry a prospective freeze of scientific inputs.
FROZEN_BOUND_INPUT_KEYS = ("bound_inputs",)

#: Mapping keys that record the execution environment rather than bind it.
ENVIRONMENT_SNAPSHOT_KEYS = ("input_sha256",)

#: Roots searched for committed provenance artifacts.
PROVENANCE_ROOTS = ("results", "benchmark", "docs")

#: Bindings this audit must always find.  Discovery keeps the audit open to
#: phases that do not exist yet; this closes the other failure mode, where a
#: binding is deleted or renamed and the audit silently checks nothing.  The
#: values are quoted from committed provenance and are never written from it.
REQUIRED_COVERAGE: Mapping[str, Mapping[str, str]] = {
    "results/phaseI-rc2-requalification/phaseI-provenance.json": {
        "scripts/analyze_phaseI_requalification.py": (
            "2ec5e5f40618e27400a534465d380be0092fb0b0cd1bd013aac562f99f80798e"
        ),
        "scripts/run_phaseI_requalification.py": (
            "1f18a62979b268f5c20b31630359dcf024cb6dcd7eea088aa366c32242b87bc4"
        ),
        "benchmark/pilot-v7-rc2/manifest.json": (
            "d2c6d86c4a3edb7531096c083064a0bfa13a74364e851e2735c80e1e72260759"
        ),
        "configs/phaseI-models.yaml": (
            "a15d7a203ba8075b6526d690d5f88db2f03166d792547d8fc94750cf3ccfa96a"
        ),
        "configs/phaseI-qualification.yaml": (
            "48162be7c012ff205c924822ef74a8218681077523572a475042c2ee54ec871b"
        ),
        "configs/policies/default.xml": (
            "256a8205fa944f74e12642925298260848fae5ebbb320f695ce0a234ea9f63e5"
        ),
        "docs/phaseI_rc2_real_model_requalification_plan.md": (
            "dcc23417ba9d43da6698d3688a14dcd1f9e5bf5b9d12f23e017db4d34fd5a004"
        ),
    },
    "results/phaseF-qualification/phaseF-provenance.json": {
        "benchmark/pilot-v7-rc1/manifest.json": (
            "400b2ac2124311c79a69abd0fd5428373f873bf7d9a718e3e3cb15f2a929e00a"
        ),
        "configs/phaseF-models.yaml": (
            "b3ad625d3b0a44c369f1e314d67164392cb31c4649542880762ef801881e7127"
        ),
        "configs/phaseF-qualification.yaml": (
            "c553da40832d5c4fc76ba03eb885446f91a1058bff4778fbb6144ccf3b74264d"
        ),
        "configs/policies/default.xml": (
            "256a8205fa944f74e12642925298260848fae5ebbb320f695ce0a234ea9f63e5"
        ),
        "docs/phaseF_real_model_qualification_plan.md": (
            "4042f6c5ae43f06f39161f1115aa73a1dc4e7e3ba6dd1820ce9a710ce0a65823"
        ),
    },
}

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")


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


def sha256_of(path: Path) -> str:
    """Hash raw working-tree bytes; never normalize (docs/hash_basis_policy.md)."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_at_commit(commit: str, relative: str) -> str | None:
    """The file's SHA-256 as the commit actually contains it, or None if absent."""

    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    if completed.returncode != 0:
        return None
    return hashlib.sha256(completed.stdout).hexdigest()


def tracked_files(*roots: str) -> list[str]:
    out = _git("ls-files", "-z", "--", *roots)
    return sorted(x.decode() for x in out.split(b"\0") if x)


def last_commit_touching(relative: str) -> str:
    return _git("log", "-1", "--format=%H", "--", relative).decode().strip()


class Binding:
    """One recorded ``path -> SHA-256`` pair, with everything needed to judge it."""

    def __init__(self, container: str, key: str, path: str, recorded: str) -> None:
        self.container = container
        self.key = key
        self.path = path
        self.recorded = recorded

    @property
    def contract_kind(self) -> str:
        if self.key in FROZEN_BOUND_INPUT_KEYS:
            return "FROZEN_BOUND_INPUT"
        if self.key in ENVIRONMENT_SNAPSHOT_KEYS:
            return "ENVIRONMENT_SNAPSHOT"
        return "SIDECAR_DIGEST" if self.key == "@sha256-sidecar" else "UNCLASSIFIED"

    def current_sha256(self) -> str | None:
        target = REPO_ROOT / self.path
        return sha256_of(target) if target.is_file() else None

    def to_json(self) -> dict[str, Any]:
        current = self.current_sha256()
        recording_commit = last_commit_touching(self.container)
        at_recording = sha256_at_commit(recording_commit, self.path)
        at_parent = sha256_at_commit(PHASE_M_PARENT_COMMIT, self.path)
        return {
            "container": self.container,
            "key": self.key,
            "path": self.path,
            "contract_kind": self.contract_kind,
            "recorded_sha256": self.recorded,
            "current_sha256": current,
            "matches_current_tree": current == self.recorded,
            "recording_commit": recording_commit,
            "matches_at_recording_commit": at_recording == self.recorded,
            "matches_at_phase_m_parent": at_parent == self.recorded,
        }


def _walk_for_bindings(
    node: Any, container: str, key_path: Sequence[str]
) -> Iterator[Binding]:
    """Yield every ``<repo path> -> <sha256>`` pair under a recognised key."""

    if isinstance(node, Mapping):
        for key, value in node.items():
            if not isinstance(key, str):
                continue
            if (
                key in FROZEN_BOUND_INPUT_KEYS or key in ENVIRONMENT_SNAPSHOT_KEYS
            ) and isinstance(value, Mapping):
                for path, digest in value.items():
                    if not isinstance(path, str) or not isinstance(digest, str):
                        continue
                    if _SHA256_RE.match(digest) and "/" in path:
                        yield Binding(container, key, path, digest)
                continue
            yield from _walk_for_bindings(value, container, [*key_path, key])
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_for_bindings(value, container, [*key_path, str(index)])


def discover_bindings() -> list[Binding]:
    """Every hash binding recorded by any committed provenance artifact.

    Discovery rather than a hard-coded list, so a phase that does not exist yet
    is audited the moment it commits a ``bound_inputs`` block.  ``REQUIRED_COVERAGE``
    guards the opposite failure, where a binding disappears and nothing notices.
    """

    bindings: list[Binding] = []
    for relative in tracked_files(*PROVENANCE_ROOTS):
        if relative.endswith(".json"):
            try:
                payload = json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            bindings.extend(_walk_for_bindings(payload, relative, []))
        elif relative.endswith(".sha256"):
            try:
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            except OSError:  # pragma: no cover - unreadable sidecar
                continue
            for line in text.splitlines():
                digest, _, path = line.strip().partition("  ")
                if _SHA256_RE.match(digest) and path:
                    bindings.append(Binding(relative, "@sha256-sidecar", path, digest))
    bindings.sort(key=lambda b: (b.container, b.path))
    return bindings


def check_frozen_bound_inputs() -> list[str]:
    """RULE 1 -- every prospectively frozen input still matches the CURRENT tree."""

    failures: list[str] = []
    for binding in discover_bindings():
        if binding.contract_kind not in ("FROZEN_BOUND_INPUT", "SIDECAR_DIGEST"):
            continue
        current = binding.current_sha256()
        if current is None:
            failures.append(
                f"FROZEN INPUT MISSING: {binding.path} is bound by "
                f"{binding.container}:{binding.key} but is absent from the tree"
            )
        elif current != binding.recorded:
            failures.append(
                f"FROZEN INPUT CHANGED: {binding.path} is bound by "
                f"{binding.container}:{binding.key} to {binding.recorded}, "
                f"but the current tree hashes to {current}"
            )
    return failures


def check_required_coverage() -> list[str]:
    """RULE 2 -- the audit is not vacuous: known bindings still exist, unaltered."""

    failures: list[str] = []
    discovered = {
        (b.container, b.path): b.recorded
        for b in discover_bindings()
        if b.contract_kind == "FROZEN_BOUND_INPUT"
    }
    for container, expected in REQUIRED_COVERAGE.items():
        for path, digest in expected.items():
            found = discovered.get((container, path))
            if found is None:
                failures.append(
                    f"COVERAGE LOST: {container} no longer binds {path}; a frozen "
                    "input may not be un-bound"
                )
            elif found != digest:
                failures.append(
                    f"PROVENANCE REWRITTEN: {container} now binds {path} to {found}, "
                    f"but the frozen record is {digest}"
                )
    return failures


def check_no_regression_since_phase_m_parent() -> list[str]:
    """RULE 3 -- Phase M broke nothing that held when Phase M began.

    Applies to EVERY class, including the Phase-A environment snapshot, and
    inherits no divergence that predates the parent commit.
    """

    failures: list[str] = []
    for binding in discover_bindings():
        at_parent = sha256_at_commit(PHASE_M_PARENT_COMMIT, binding.path)
        if at_parent != binding.recorded:
            continue  # already diverged before Phase M; not Phase M's regression
        current = binding.current_sha256()
        if current != binding.recorded:
            failures.append(
                f"PHASE-M REGRESSION: {binding.path} matched its recorded hash "
                f"{binding.recorded} at {PHASE_M_PARENT_COMMIT[:8]} "
                f"({binding.container}:{binding.key}) but now hashes to "
                f"{current if current is not None else 'ABSENT'}"
            )
    return failures


def check_history_not_rewritten() -> list[str]:
    """Each commit's own provenance still agrees with that same commit's blobs.

    Evaluated ENTIRELY inside a commit: the container is read as that commit
    contains it, and each binding it holds is compared against that commit's
    blob.  Nothing here consults the working tree, so uncommitted work in
    progress can neither trip this rule nor mask it, and the predicate stays a
    statement about history rather than about today.  (Whether today's tree
    matches is a different question, and is Rule 1.)

    Three Phase-A entries do not hold, and are not defects: they are the
    mixed-EOL materializations that ``docs/hash_basis_amendment_v1.json`` exists
    to record.  They are named there, so they are named here too, rather than
    tolerated by a blanket exemption.
    """

    amended = _amended_artifacts()
    failures: list[str] = []
    containers = {binding.container for binding in discover_bindings()}
    for container in sorted(containers):
        commit = last_commit_touching(container)
        if not commit:  # pragma: no cover - untracked container
            continue
        # A container with uncommitted edits has no recording commit for its
        # CURRENT content yet, so there is no history to check -- only an
        # intention. Rule 1 already holds its bindings to the working tree, and
        # this rule resumes governing it the moment it is committed.
        if sha256_at_commit(commit, container) != sha256_of(REPO_ROOT / container):
            continue
        for binding in _bindings_at_commit(commit, container):
            if sha256_at_commit(commit, binding.path) == binding.recorded:
                continue
            if binding.path in amended:
                continue
            failures.append(
                f"HISTORY REWRITTEN: {container}:{binding.key} at commit "
                f"{commit[:8]} records {binding.path} as {binding.recorded}, "
                "which is not what that commit contains"
            )
    return failures


def _bindings_at_commit(commit: str, container: str) -> list[Binding]:
    """The bindings a container held AT ``commit``, read from committed bytes."""

    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{container}"],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    if completed.returncode != 0:
        return []
    text = completed.stdout.decode("utf-8", errors="replace")
    if container.endswith(".json"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:  # pragma: no cover
            return []
        return list(_walk_for_bindings(payload, container, []))
    bindings: list[Binding] = []
    for line in text.splitlines():
        digest, _, path = line.strip().partition("  ")
        if _SHA256_RE.match(digest) and path:
            bindings.append(Binding(container, "@sha256-sidecar", path, digest))
    return bindings


def _amended_artifacts() -> frozenset[str]:
    """Artifacts whose recorded digest is governed by the hash-basis amendment."""

    path = REPO_ROOT / "docs" / "hash_basis_amendment_v1.json"
    if not path.is_file():  # pragma: no cover - amendment absent
        return frozenset()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):  # pragma: no cover
        return frozenset()
    entries = payload.get("amended_artifacts")
    if not isinstance(entries, list):  # pragma: no cover
        return frozenset()
    return frozenset(
        str(entry["artifact"])
        for entry in entries
        if isinstance(entry, Mapping) and isinstance(entry.get("artifact"), str)
    )


def audit() -> list[str]:
    """All four rules, in the order a reader should think about them."""

    return [
        *check_required_coverage(),
        *check_frozen_bound_inputs(),
        *check_no_regression_since_phase_m_parent(),
        *check_history_not_rewritten(),
    ]


def summary() -> dict[str, Any]:
    """A machine-readable statement of where every frozen bound input stands."""

    bindings = [b.to_json() for b in discover_bindings()]
    frozen = [b for b in bindings if b["contract_kind"] == "FROZEN_BOUND_INPUT"]
    sidecars = [b for b in bindings if b["contract_kind"] == "SIDECAR_DIGEST"]
    snapshots = [b for b in bindings if b["contract_kind"] == "ENVIRONMENT_SNAPSHOT"]
    failures = audit()
    return {
        "phase": "M.1",
        "phase_m_parent_commit": PHASE_M_PARENT_COMMIT,
        "model_inference_performed": False,
        "counts": {
            "frozen_bound_inputs": len(frozen),
            "sha256_sidecars": len(sidecars),
            "environment_snapshots": len(snapshots),
        },
        "frozen_bound_inputs_all_match_current_tree": all(
            b["matches_current_tree"] for b in frozen
        ),
        "sha256_sidecars_all_match_current_tree": all(
            b["matches_current_tree"] for b in sidecars
        ),
        "environment_snapshot_divergences": [
            {
                "path": b["path"],
                "recorded_sha256": b["recorded_sha256"],
                "current_sha256": b["current_sha256"],
                "diverged_before_phase_m": not b["matches_at_phase_m_parent"],
            }
            for b in snapshots
            if not b["matches_current_tree"]
        ],
        "bindings": bindings,
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase-M.1 frozen bound-input audit")
    parser.add_argument(
        "--json", action="store_true", help="emit the full machine-readable audit"
    )
    parser.add_argument(
        "--out", default=None, help="write the machine-readable audit to this path"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = summary()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for binding in report["bindings"]:
            if binding["contract_kind"] == "ENVIRONMENT_SNAPSHOT":
                continue
            mark = "ok  " if binding["matches_current_tree"] else "FAIL"
            print(f"  {mark} {binding['recorded_sha256']}  {binding['path']}")
    if args.out is not None:
        Path(args.out).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    for failure in report["failures"]:
        print(failure)
    print(
        f"frozen bound-input audit: {report['verdict']} "
        f"({len(report['failures'])} failure(s); "
        f"{report['counts']['frozen_bound_inputs']} bound input(s), "
        f"{report['counts']['sha256_sidecars']} sidecar(s) checked)"
    )
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "Binding",
    "PHASE_M_PARENT_COMMIT",
    "REQUIRED_COVERAGE",
    "audit",
    "check_frozen_bound_inputs",
    "check_history_not_rewritten",
    "check_no_regression_since_phase_m_parent",
    "check_required_coverage",
    "discover_bindings",
    "summary",
]
