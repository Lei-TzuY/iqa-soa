#!/usr/bin/env python3
"""Run a FROZEN historical analysis script the only way that stays honest.

THE PROBLEM
===========

Phase M moved the instrument to version "3" and the raw row to schema 4.  The
frozen Phase-F and Phase-I analyzers, and the frozen pilot-v7-rc2 offline
validator, import the moving aliases ``INSTRUMENT_VERSION`` and
``RAW_SCHEMA_VERSION`` from ``iqa_soa.instrument`` and assert them against the
artifacts they read.  Executed in a post-Phase-M working tree they therefore
reject their own frozen evidence for declaring instrument "2" / schema 3.

The evidence is not wrong.  The analyzer is not wrong.  The pairing is wrong:
an instrument-2 analyzer is being handed an instrument-3 constant.

THE REMEDIES THAT WERE REJECTED, AND WHY
========================================

*Edit the frozen analyzer to pin the historical constant.*  This is what the
first Phase-M revision did.  It is the right change to the wrong file:
``scripts/analyze_phaseI_requalification.py`` is bound by SHA-256 inside
``results/phaseI-rc2-requalification/phaseI-provenance.json``, so its bytes are
a prospectively frozen scientific input.  Changing them in the current tree
retracts the freeze no matter how well git remembers the old bytes.

*Re-record the new hash in the Phase-I provenance.*  Strictly worse.  A record
that is updated to describe whatever the file now contains is not a freeze.

*Substitute a historical instrument module into ``sys.modules`` while loading
the analyzer.*  This makes the analyzer's behaviour depend on who imported it,
and the substitution is invisible at the call site.  A reader of the frozen
source would have no way to know which constant it actually saw.

THE REMEDY USED
===============

Execute the frozen script from a detached git worktree at the commit that froze
it.  Nothing is patched, nothing is substituted and nothing is edited: the
analyzer, the ``iqa_soa`` package it imports, the configs it reads and the
results it analyzes are all the real committed bytes of a real commit.  The
instrument constant it sees is "2" because at that commit the instrument WAS
"2".

That also makes the reproduction total rather than partial.  These analyzers
compute their own ``bound_inputs`` block from ``PROJECT_ROOT``, so running from
the frozen worktree regenerates the frozen bound-input hashes -- including the
analyzer's own ``2ec5e5f4...`` -- and they can be compared to the committed
provenance directly.

Only four keys are permitted to differ, and each records WHERE the analysis was
invoked rather than WHAT it measured: ``generated_at``, ``branch``,
``branch_head_commit`` and ``frozen_commit``.  Every other key, and the summary
tables byte-for-byte, must reproduce exactly.

This module performs no inference, contacts no provider, and writes only into a
caller-supplied output directory.  It never writes to ``results/``.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Keys that record the invocation context of an analysis rather than its
#: findings.  A reproduction run legitimately differs on these and on nothing
#: else; the list is deliberately short and closed.
INVOCATION_CONTEXT_KEYS = (
    "branch",
    "branch_head_commit",
    "frozen_commit",
    "generated_at",
)


class FrozenAnalysis:
    """A frozen script, the commit that froze it, and how to reproduce it."""

    def __init__(
        self,
        *,
        name: str,
        phase: str,
        script: str,
        freeze_commit: str,
        argv: Sequence[str] = (),
        provenance: str | None = None,
        artifacts: Sequence[str] = (),
        expect_pass_text: str | None = None,
    ) -> None:
        self.name = name
        self.phase = phase
        self.script = script
        self.freeze_commit = freeze_commit
        self.argv = tuple(argv)
        self.provenance = provenance
        self.artifacts = tuple(artifacts)
        self.expect_pass_text = expect_pass_text


#: Every frozen script Phase M must keep runnable without touching its bytes.
FROZEN_ANALYSES: tuple[FrozenAnalysis, ...] = (
    FrozenAnalysis(
        name="phaseF",
        phase="F",
        script="scripts/analyze_phaseF_qualification.py",
        # The commit that archived Phase F on main (PR #4).  It carries both the
        # frozen analyzer and the committed Phase-F results.
        freeze_commit="da6ccdc552c2e085cf6a3d0131c108f86bd32a7e",
        argv=("--write",),
        provenance="results/phaseF-qualification/phaseF-provenance.json",
        artifacts=("phaseF-summary.csv",),
    ),
    FrozenAnalysis(
        name="phaseI",
        phase="I",
        script="scripts/analyze_phaseI_requalification.py",
        # The commit that archived Phase I on main (PR #6), and the canonical
        # base of pilot-v7-rc3.
        freeze_commit="978c8cb1dcb1b6dc5a2ec51a7233a26c114e2569",
        provenance="results/phaseI-rc2-requalification/phaseI-provenance.json",
        artifacts=("phaseI-summary.csv", "phaseI-task-summary.csv"),
    ),
    FrozenAnalysis(
        name="rc2_validator",
        phase="H",
        script="scripts/validate_pilot_v7_rc2.py",
        # The commit that froze pilot-v7-rc2 (PR #5).
        freeze_commit="6ba6595f6c3d6be0edd702541e70abafaaf2aa9c",
        expect_pass_text="pilot-v7-rc2 offline validation: PASS (0 failure(s))",
    ),
)


def rc2_superseded_live_assertions() -> tuple[str, ...]:
    """The one live claim of the frozen rc2 validator the approved revision supersedes.

    The frozen rc2 validator pins ``src/iqa_soa`` to the Phase-H instrument tree
    and asserts that pin against the LIVE working tree.  Phase M revised the
    instrument under an approved, per-file hash-pinned revision record, so that
    single claim is now false in the current tree while remaining true at its own
    commit -- where :data:`FROZEN_ANALYSES` proves the whole validator still
    passes.

    The supersession is RECORDED rather than edited away: the frozen validator
    keeps saying exactly what it always said, and Phase M states, in a
    Phase-M-owned file, which claim its approved revision supersedes and why.

    The expected text is composed from the two authoritative digests -- the
    Phase-K frozen tree and the approved revision's tree -- rather than pasted,
    so it cannot drift out of date and cannot be widened by hand.  An unapproved
    byte under ``src/iqa_soa`` changes the live digest, so the observed string
    stops matching AND ``check_approved_instrument_revision`` fails: the
    supersession admits exactly one instrument, the approved one.
    """

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, scripts_dir)
    import instrument_revision

    approved = instrument_revision.load_revision()["current_instrument"]
    return (
        f"A: frozen tree changed: src/iqa_soa "
        f"expected {instrument_revision.PHASE_K_SRC_TREE} "
        f"got {approved['src_iqa_soa_tree']}",
    )


class GitUnavailableError(RuntimeError):
    """Git could not be consulted, so a frozen commit cannot be materialized."""


def _git(*args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, check=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitUnavailableError(f"git {' '.join(args)} failed: {exc}") from exc
    return completed.stdout


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_at_commit(commit: str, relative: str) -> str | None:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=REPO_ROOT, capture_output=True, check=False,
    )
    if completed.returncode != 0:
        return None
    return hashlib.sha256(completed.stdout).hexdigest()


@contextmanager
def frozen_worktree(commit: str) -> Iterator[Path]:
    """A disposable detached checkout of ``commit``.

    The root is kept SHORT and outside the repository.  Some committed evidence
    paths are long enough that a deep worktree root exceeds the Windows
    ``MAX_PATH`` limit during checkout, and ``core.longpaths`` is set on the
    command line rather than in the repository so no user's config is modified.
    """

    root = Path(tempfile.mkdtemp(prefix="pm1-", dir=tempfile.gettempdir()))
    path = root / "wt"
    try:
        _git(
            "-c", "core.longpaths=true",
            "worktree", "add", "--detach", "--force", str(path), commit,
        )
        yield path
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(path)],
            cwd=REPO_ROOT, capture_output=True, check=False,
        )
        subprocess.run(
            ["git", "worktree", "prune"], cwd=REPO_ROOT, capture_output=True, check=False
        )
        shutil.rmtree(root, ignore_errors=True)


def check_frozen_script_bytes(spec: FrozenAnalysis) -> list[str]:
    """The current tree, the freeze commit and the provenance must all agree.

    Running the script from the frozen commit proves nothing about the current
    tree unless the current tree still holds the same bytes.  This is what ties
    the reproduction below back to the repository a reader actually has.
    """

    failures: list[str] = []
    target = REPO_ROOT / spec.script
    if not target.is_file():
        return [f"{spec.name}: {spec.script} is absent from the working tree"]
    current = sha256_of(target)
    frozen = sha256_at_commit(spec.freeze_commit, spec.script)
    if frozen is None:
        failures.append(
            f"{spec.name}: {spec.script} does not exist at freeze commit "
            f"{spec.freeze_commit[:8]}"
        )
    elif current != frozen:
        failures.append(
            f"{spec.name}: {spec.script} hashes to {current} in the working tree "
            f"but to {frozen} at its freeze commit {spec.freeze_commit[:8]}"
        )
    if spec.provenance is not None:
        recorded = _bound_input_hash(spec.provenance, spec.script)
        if recorded is not None and recorded != current:
            failures.append(
                f"{spec.name}: {spec.provenance} binds {spec.script} to {recorded}, "
                f"but the working tree hashes to {current}"
            )
    return failures


def _bound_input_hash(provenance: str, relative: str) -> str | None:
    path = REPO_ROOT / provenance
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):  # pragma: no cover
        return None
    bound = payload.get("bound_inputs")
    if not isinstance(bound, Mapping):
        return None
    value = bound.get(relative)
    return value if isinstance(value, str) else None


def reproduce(spec: FrozenAnalysis, out_dir: Path) -> dict[str, Any]:
    """Execute the frozen script at its freeze commit and compare the result."""

    result: dict[str, Any] = {
        "name": spec.name,
        "phase": spec.phase,
        "script": spec.script,
        "freeze_commit": spec.freeze_commit,
        "failures": check_frozen_script_bytes(spec),
        "model_inference_performed": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with frozen_worktree(spec.freeze_commit) as worktree:
        argv = [sys.executable, str(worktree / spec.script), *spec.argv]
        if spec.provenance is not None:
            argv += ["--out", str(out_dir)]
        completed = subprocess.run(
            argv, cwd=str(worktree), capture_output=True, text=True, check=False
        )
    combined = completed.stdout + completed.stderr
    result["exit_code"] = completed.returncode
    if "Traceback" in combined:
        result["failures"].append(
            f"{spec.name}: the frozen script crashed at its freeze commit:\n{combined}"
        )
    if spec.expect_pass_text is not None:
        if spec.expect_pass_text not in combined:
            result["failures"].append(
                f"{spec.name}: expected {spec.expect_pass_text!r} at freeze commit "
                f"{spec.freeze_commit[:8]}, got:\n{combined}"
            )
        else:
            result["passes_at_freeze_commit"] = True
    if spec.provenance is not None:
        result.update(_compare_provenance(spec, out_dir))
    return result


def _compare_provenance(spec: FrozenAnalysis, out_dir: Path) -> dict[str, Any]:
    """Every scientific key, and every summary table, must reproduce exactly."""

    assert spec.provenance is not None
    committed_path = REPO_ROOT / spec.provenance
    reproduced_path = out_dir / Path(spec.provenance).name
    out: dict[str, Any] = {"failures": []}
    if not reproduced_path.is_file():
        out["failures"].append(
            f"{spec.name}: the frozen analyzer wrote no {reproduced_path.name}"
        )
        return out
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    reproduced = json.loads(reproduced_path.read_text(encoding="utf-8"))
    differing = sorted(
        key
        for key in set(committed) | set(reproduced)
        if committed.get(key) != reproduced.get(key)
    )
    unexpected = [key for key in differing if key not in INVOCATION_CONTEXT_KEYS]
    for key in unexpected:
        out["failures"].append(
            f"{spec.name}: {spec.provenance} key {key!r} did not reproduce: "
            f"committed={committed.get(key)!r} reproduced={reproduced.get(key)!r}"
        )
    out["provenance_keys_differing"] = differing
    out["verdict_reproduced"] = reproduced.get("verdict")
    out["verdict_committed"] = committed.get("verdict")
    out["bound_inputs_reproduced_exactly"] = (
        committed.get("bound_inputs") == reproduced.get("bound_inputs")
    )
    if not out["bound_inputs_reproduced_exactly"]:
        out["failures"].append(
            f"{spec.name}: the frozen bound-input hash set did not reproduce"
        )
    tables: dict[str, bool] = {}
    for artifact in spec.artifacts:
        committed_artifact = committed_path.parent / artifact
        reproduced_artifact = out_dir / artifact
        if not (committed_artifact.is_file() and reproduced_artifact.is_file()):
            out["failures"].append(f"{spec.name}: {artifact} is missing from a side")
            continue
        identical = sha256_of(committed_artifact) == sha256_of(reproduced_artifact)
        tables[artifact] = identical
        if not identical:
            out["failures"].append(
                f"{spec.name}: {artifact} is not byte-identical to the committed table"
            )
    out["summary_tables_byte_identical"] = tables
    return out


def check_rc2_superseded_assertions() -> list[str]:
    """The live rc2 validator must fail on the approved revision, and only that.

    A frozen validator whose live claim has been superseded is informative only
    while the supersession is exact.  If the live failure set ever grows, shrinks
    or changes text, something other than the approved instrument revision moved
    and this fails.
    """

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, scripts_dir)
    import validate_pilot_v7_rc2 as rc2

    expected = rc2_superseded_live_assertions()
    observed = tuple(rc2.check_historical_immutability())
    if observed == expected:
        return []
    return [
        "rc2_validator: the live failure set is not exactly the approved "
        f"instrument revision.\n  expected: {list(expected)}\n"
        f"  observed: {list(observed)}"
    ]


def check_all(out_root: Path | None = None) -> list[str]:
    """Byte identity, reproduction and supersession, for every frozen script."""

    failures: list[str] = []
    root = out_root or Path(tempfile.mkdtemp(prefix="pm1-out-"))
    for spec in FROZEN_ANALYSES:
        failures.extend(reproduce(spec, root / spec.name)["failures"])
    failures.extend(check_rc2_superseded_assertions())
    if out_root is None:
        shutil.rmtree(root, ignore_errors=True)
    return failures


def summary(out_root: Path | None = None) -> dict[str, Any]:
    root = out_root or Path(tempfile.mkdtemp(prefix="pm1-out-"))
    results = [reproduce(spec, root / spec.name) for spec in FROZEN_ANALYSES]
    superseded = check_rc2_superseded_assertions()
    if out_root is None:
        shutil.rmtree(root, ignore_errors=True)
    failures = [f for result in results for f in result["failures"]] + superseded
    return {
        "phase": "M.1",
        "model_inference_performed": False,
        "frozen_scripts_modified_by_phase_m": [],
        "invocation_context_keys_permitted_to_differ": list(INVOCATION_CONTEXT_KEYS),
        "rc2_superseded_live_assertions": list(rc2_superseded_live_assertions()),
        "analyses": results,
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reproduce frozen historical analyses from their freeze commits"
    )
    parser.add_argument(
        "--out", default=None, help="keep the reproduced artifacts under this directory"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the full machine-readable report"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = summary(Path(args.out) if args.out else None)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        for analysis in report["analyses"]:
            mark = "ok  " if not analysis["failures"] else "FAIL"
            detail = ""
            if analysis.get("verdict_committed") is not None:
                detail = (
                    f" verdict={analysis['verdict_reproduced']}"
                    f" bound_inputs_exact={analysis['bound_inputs_reproduced_exactly']}"
                )
            elif analysis.get("passes_at_freeze_commit"):
                detail = " PASS at freeze commit"
            print(f"  {mark} {analysis['script']} @ {analysis['freeze_commit'][:8]}{detail}")
    for failure in report["failures"]:
        print(failure)
    print(
        f"frozen historical analysis: {report['verdict']} "
        f"({len(report['failures'])} failure(s))"
    )
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "FROZEN_ANALYSES",
    "INVOCATION_CONTEXT_KEYS",
    "FrozenAnalysis",
    "check_all",
    "check_frozen_script_bytes",
    "check_rc2_superseded_assertions",
    "frozen_worktree",
    "rc2_superseded_live_assertions",
    "reproduce",
    "summary",
]
