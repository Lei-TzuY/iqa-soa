#!/usr/bin/env python3
"""Prove the Phase-P seed selection where it bound, and bound what moved after.

THE PROBLEM
===========

``scripts/phaseP_derive_seeds.py`` proves that the three prospective Phase-P
seeds were not chosen after seeing a result.  Part of that proof is a scan of
committed history: at the moment the triple was frozen, none of the three values
appeared anywhere under :data:`SCAN_ROOTS` except in Phase P's own three declared
seed-selection artifacts.  ``phaseP_protocol.check_seed_provenance`` re-runs that
scan and asserts it against the **live working tree**.

That was correct, and it was correct for a reason: before execution, a seed
appearing anywhere else would mean the value had been visible in the repository
before it was selected.

Then Phase P executed, and the run terminated
``SCHEDULE_COMPLETE_VERDICT_HOLD``.  Commit ``69d1efc`` legitimately committed
``docs/phaseP_rc4_hold_forensic_diagnosis.json``, a DERIVATIVE post-run audit
ledger of the completed run.  Because it describes cells that actually ran, it
necessarily records the seeds those cells actually used.

So the live scan now finds the three seeds in a fourth file, and the frozen
pre-execution assertion is false in the present tree.

**This is not a seed collision, and it is not a defect in the selection.**  It is
the same "assert A by checking B" conflation ``scripts/instrument_revision.py``
was written to remove, one phase further on:

**A. The historical prospective claim.**  "At the moment the Phase-P triple was
frozen, those values had not appeared in pre-existing committed history outside
Phase P's own seed-selection artifacts."  This is a closed fact about the freeze
commit.  It must stay verifiable forever.

**B. The present-state claim.**  "Those values appear nowhere else in the
repository right now."  This was a valid restatement of A only while Phase P was
still unexecuted.  Documenting the completed run makes it false, and must.

THE REMEDIES THAT WERE REJECTED, AND WHY
========================================

*Add the forensic diagnosis to ``PHASE_P_ARTIFACTS``.*  That set is the list of
artifacts a seed is allowed to appear in **because they declare the selection**.
Adding a post-run ledger to it would assert that a record written after the run
is a prospective seed-selection artifact, which is exactly backwards and would
also mean a future post-hoc file could launder a seed into the allowed set.
``scripts/phaseP_derive_seeds.py`` is a frozen Phase-P input regardless.

*Remove the seeds from the forensic diagnosis.*  The ledger would then no longer
describe the run it documents.  Evidence is recorded, never trimmed to fit a
check.

*Widen the check to ignore anything matching ``phaseP*`` or ``docs/**``.*  A
wildcard would silently admit every future file, which is the opposite of a
bound.  The allowed post-freeze source here is ONE exact path.

*Declare the seed provenance historical and stop checking it.*  That discards a
live guarantee.  Everything the check proves about non-Phase-P seeds, and about
the triple appearing in NO source other than the one declared post-run ledger, is
still true right now and must keep being checked.

THE REMEDY USED
===============

Split the claim, exactly as Phase M split the Phase-K one and Phase O split the
Phase-L one.

**(A)** :func:`check_historical_seed_freeze` proves the prospective claim from
COMMITTED bytes at :data:`PHASE_P_FREEZE_COMMIT`, using a commit-aware equivalent
of the frozen scan.  The frozen scanner itself is NOT edited to take a commit
parameter: it stays byte-for-byte the historical instrument it was, and this
module verifies that.

**(B)** :func:`check_live_postrun_seed_supersession` requires that, in today's
tracked tree, the extra sources naming a Phase-P seed are EXACTLY
:data:`POST_RUN_DERIVATIVE_SEED_SOURCES` -- one enumerated path, whose identity
and post-run status are themselves verified from the committed derivative
artifact.  Any additional source fails, so a future config, result row or JSON
leaking a Phase-P seed is still a hard failure.  Every completeness guarantee
about NON-Phase-P seeds is retained unchanged.

TERMINOLOGY
===========

``docs/phaseP_rc4_hold_forensic_diagnosis.json`` is a **POST-RUN DERIVATIVE SEED
OCCURRENCE**.  It is not, and is never described here as, a prospective
seed-selection artifact.  It does not mean the seeds were known before selection,
that selection was post-hoc, or that the Phase-P run is invalid.  The Phase-P
verdict remains permanently HOLD and pilot-v7-rc4 remains UNQUALIFIED; nothing
here reinterprets, rescores or reruns any of it.

NO MODEL INFERENCE.  This module reads git and tracked working-tree bytes and
nothing else.  It never opens, enumerates or hashes anything beneath
``results/phaseP-rc4-qualification/``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import phaseP_derive_seeds as seed_derivation  # noqa: E402

#: The commit that froze the Phase-P qualification protocol (PR #14).  This is
#: where the prospective seed selection actually bound, so it is where the
#: prospective claim is verified.  Never recomputed, never updated.
PHASE_P_FREEZE_COMMIT = "f4a085f2031dddae6a2175f2993368cbcecdd257"

#: The commit that documented the COMPLETED Phase-P run (PR #15), after the run
#: had already terminated SCHEDULE_COMPLETE_VERDICT_HOLD.
POST_RUN_DIAGNOSIS_COMMIT = "69d1efc0006062bc533a117419b91e8329254dad"

#: The frozen seed-selection record, and the frozen derivation script.  Read,
#: never written.
SEED_RECORD_RELATIVE = seed_derivation.RECORD_RELATIVE
FROZEN_DERIVATION_RELATIVE = "scripts/phaseP_derive_seeds.py"

#: THE ONE ALLOWED POST-FREEZE SOURCE.  An exact relative path, enumerated --
#: never a prefix, never a glob, never "anything named phaseP".  A Phase-P seed
#: appearing in any source outside PHASE_P_ARTIFACTS and outside this set is a
#: hard failure, which is what keeps this a bound rather than an exemption.
#:
#: It is a POST-RUN DERIVATIVE SEED OCCURRENCE: a ledger of cells that already
#: ran, not an artifact that participated in choosing the seeds.
POST_RUN_DERIVATIVE_SEED_SOURCES: frozenset[str] = frozenset(
    {"docs/phaseP_rc4_hold_forensic_diagnosis.json"}
)

#: The identity the committed derivative artifact must declare about itself.
#: Verified against the artifact's own committed bytes; NOTHING here is validated
#: by reading the untracked official Phase-P evidence root.
REQUIRED_DIAGNOSIS_IDENTITY: Mapping[str, Any] = {
    "artifact_kind": "phase_p_rc4_hold_forensic_diagnosis",
    "authoritative_for_qualification": False,
    "official_verdict": "HOLD",
    "terminal_status": "SCHEDULE_COMPLETE_VERDICT_HOLD",
}

#: The immutable-evidence attestation the derivative artifact must carry.
REQUIRED_DIAGNOSIS_ATTESTATION: Mapping[str, Any] = {
    "phase_p_cells_rerun": 0,
    "model_inference_performed": False,
    "official_evidence_modified": False,
}


class SeedSupersessionError(RuntimeError):
    """Git could not be consulted, so a history-based claim cannot be proved."""


def _git(*args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, capture_output=True, check=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SeedSupersessionError(f"git {' '.join(args)} failed: {exc}") from exc
    return completed.stdout


def blob_at_commit(commit: str, relative: str) -> bytes | None:
    """A file's COMMITTED bytes at ``commit``, or ``None`` if absent there."""

    try:
        return _git("cat-file", "blob", f"{commit}:{relative}")
    except SeedSupersessionError:
        return None


def is_ancestor(ancestor: str, descendant: str) -> bool:
    """Whether ``descendant`` descends from ``ancestor`` in committed history."""

    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )
    return completed.returncode == 0


def tracked_files_at_commit(commit: str) -> list[str]:
    """Every file the COMMIT tracks under the frozen scan roots.

    The commit-aware counterpart of ``phaseP_derive_seeds.tracked_files``, which
    is ``git ls-files`` at the current commit.  The frozen function is not given
    a commit parameter: it remains exactly the instrument it was.
    """

    out = _git(
        "ls-tree", "-r", "-z", "--name-only", commit, "--", *seed_derivation.SCAN_ROOTS
    )
    return sorted(item.decode("utf-8") for item in out.split(b"\0") if item)


def scan_seeds_at_commit(commit: str) -> dict[int, list[str]]:
    """The frozen seed scan, run over COMMITTED bytes at ``commit``.

    Byte-for-byte the same three surfaces, the same suffix dispatch, the same
    ``configs/``-only rule for YAML and the same key vocabulary as
    ``phaseP_derive_seeds.scan_committed_seeds``.  The regexes and the JSON
    walker are IMPORTED from the frozen module rather than restated, so the
    historical scan and the live scan cannot drift into two different questions.
    """

    found: dict[int, set[str]] = {}
    for source in tracked_files_at_commit(commit):
        dot = source.rfind(".")
        suffix = source[dot:].casefold() if dot >= 0 else ""
        if suffix == ".yaml":
            if not source.startswith("configs/"):
                continue
            payload = blob_at_commit(commit, source)
            if payload is None:  # pragma: no cover - listed by ls-tree
                continue
            text = payload.decode("utf-8", errors="replace")
            for match in seed_derivation._SEED_LIST.finditer(text):
                for token in match.group(1).split(","):
                    stripped = token.strip()
                    if stripped.isdigit():
                        found.setdefault(int(stripped), set()).add(source)
            for match in seed_derivation._SEED_SCALAR.finditer(text):
                found.setdefault(int(match.group(1)), set()).add(source)
        elif suffix == ".jsonl":
            payload = blob_at_commit(commit, source)
            if payload is None:  # pragma: no cover - listed by ls-tree
                continue
            for line in payload.decode("utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    value = parsed.get("seed")
                    if isinstance(value, int) and not isinstance(value, bool):
                        found.setdefault(value, set()).add(source)
        elif suffix == ".json":
            payload = blob_at_commit(commit, source)
            if payload is None:  # pragma: no cover - listed by ls-tree
                continue
            try:
                parsed_json = json.loads(payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            seed_derivation._collect_json_seeds(parsed_json, found, source)
    return {seed: sorted(sources) for seed, sources in sorted(found.items())}


def frozen_seed_triple() -> tuple[int, ...]:
    """The triple the frozen derivation produces, recomputed, never pasted."""

    triple, _trail = seed_derivation.derive_seeds()
    return tuple(triple)


def extra_seed_sources(
    scanned: Mapping[int, Sequence[str]], seeds: Sequence[int]
) -> dict[int, set[str]]:
    """Per Phase-P seed, the sources that are NOT a declared Phase-P artifact.

    A pure classification helper over a scan mapping.  It reads nothing, so a
    test can hand it a synthetic scan and check the bound directly.
    """

    return {
        seed: set(scanned.get(seed, ())) - set(seed_derivation.PHASE_P_ARTIFACTS)
        for seed in seeds
    }


# --------------------------------------------------------------------------
# (A) The historical prospective claim
# --------------------------------------------------------------------------


def check_historical_seed_freeze(
    *, commit: str = PHASE_P_FREEZE_COMMIT, label: str = "P-SEED"
) -> list[str]:
    """Prove the prospective seed selection where it actually bound.

    Every claim is read from COMMITTED bytes at the freeze commit, so it returns
    the same answer today, after the run, after the forensic diagnosis, and after
    every later phase.
    """

    failures: list[str] = []

    # 1. The frozen derivation instrument existed there, and is what we run now.
    committed_script = blob_at_commit(commit, FROZEN_DERIVATION_RELATIVE)
    if committed_script is None:
        return [
            f"{label}: {FROZEN_DERIVATION_RELATIVE} does not exist at {commit}; the "
            "prospective derivation cannot be proved where it bound"
        ]
    live_script = (PROJECT_ROOT / FROZEN_DERIVATION_RELATIVE).read_bytes()
    if live_script != committed_script:
        failures.append(
            f"{label}: {FROZEN_DERIVATION_RELATIVE} was EDITED since {commit}. The "
            "frozen derivation is the historical instrument and is recorded, never "
            "rewritten."
        )

    # 2. The committed seed record at the freeze carries exactly the triple, and
    #    the working-tree record is still byte-identical to it.
    committed_record_bytes = blob_at_commit(commit, SEED_RECORD_RELATIVE)
    if committed_record_bytes is None:
        return [
            *failures,
            f"{label}: {SEED_RECORD_RELATIVE} does not exist at {commit}",
        ]
    if (PROJECT_ROOT / SEED_RECORD_RELATIVE).read_bytes() != committed_record_bytes:
        failures.append(
            f"{label}: {SEED_RECORD_RELATIVE} was EDITED since {commit}. A "
            "superseded prospective record is preserved, never rewritten."
        )
    try:
        record = json.loads(committed_record_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [*failures, f"{label}: the committed seed record is unreadable: {exc}"]

    # 3. The derivation is a pure function of the canonical base commit and
    #    reproduces the recorded triple.
    derived = frozen_seed_triple()
    recorded = record.get("seeds")
    if recorded != list(derived):
        failures.append(
            f"{label}: the committed seed record carries {recorded!r}, but the "
            f"frozen derivation reproduces {list(derived)!r}"
        )
    if str(record.get("canonical_base_commit")) != seed_derivation.CANONICAL_BASE_COMMIT:
        failures.append(
            f"{label}: the committed seed record was derived from "
            f"{record.get('canonical_base_commit')!r}, expected "
            f"{seed_derivation.CANONICAL_BASE_COMMIT!r}"
        )

    # 4. The triple is distinct, positive, and not a forbidden historical seed.
    if len(set(derived)) != len(derived):
        failures.append(f"{label}: the frozen triple is not three distinct seeds")
    if any(seed <= 0 for seed in derived):
        failures.append(f"{label}: a frozen seed is not a positive integer")
    overlap = sorted(set(derived) & set(seed_derivation.FORBIDDEN_SEEDS))
    if overlap:
        failures.append(
            f"{label}: frozen seeds {overlap} are FORBIDDEN historical seeds"
        )

    # 5-6. The committed-history scan AS OF the freeze: no Phase-P seed outside
    #      Phase P's own declared artifacts, and the forbidden set complete.
    try:
        historical = scan_seeds_at_commit(commit)
    except SeedSupersessionError as exc:
        return [*failures, f"{label}: cannot scan committed history at {commit}: {exc}"]
    prior = seed_derivation.prior_phase_seeds(historical)
    leaked = sorted(set(derived) & set(prior))
    if leaked:
        failures.append(
            f"{label}: at {commit} the frozen seeds {leaked} already appeared "
            f"outside Phase P's own artifacts: { {seed: prior[seed] for seed in leaked} }"
        )
    uncovered = sorted(set(prior) - set(seed_derivation.FORBIDDEN_SEEDS))
    if uncovered:
        failures.append(
            f"{label}: at {commit} the committed history recorded seeds the "
            f"forbidden set does not cover: {uncovered}"
        )
    for seed in derived:
        declared = set(historical.get(seed, ())) & set(seed_derivation.PHASE_P_ARTIFACTS)
        if not declared:
            failures.append(
                f"{label}: at {commit} the frozen seed {seed} is declared by none of "
                f"Phase P's own artifacts {sorted(seed_derivation.PHASE_P_ARTIFACTS)}"
            )

    # 7. The original collision report is collision-free under the repository
    #    state that existed when the selection was frozen -- and the committed
    #    record is byte-reproducible from that historical scan, which proves the
    #    record was written against that state and not against a later one.
    _triple, trail = seed_derivation.derive_seeds()
    report = seed_derivation.collision_report(list(derived), trail, scanned=historical)
    if report.get("collision_free") is not True:
        failures.append(
            f"{label}: the frozen collision report is NOT collision-free under the "
            f"repository state at {commit}: {report}"
        )
    rebuilt = seed_derivation.render(seed_derivation.build_record(scanned=historical))
    if rebuilt != committed_record_bytes.decode("utf-8"):
        failures.append(
            f"{label}: the committed seed record is not byte-reproducible from the "
            f"committed-history scan at {commit}; it does not describe the state "
            "that existed when the selection was frozen"
        )
    return failures


# --------------------------------------------------------------------------
# (B) The present-state post-run claim
# --------------------------------------------------------------------------


def check_post_run_derivative_artifact(*, label: str = "P-SEED") -> list[str]:
    """The one allowed post-freeze source is what it claims to be.

    Verified from the COMMITTED derivative artifact alone.  The untracked
    official Phase-P evidence root is not opened, enumerated or hashed here: what
    is checked is that the committed ledger declares itself derivative,
    non-authoritative, and non-mutating -- not that its own attestations are
    re-derived from the evidence it describes.
    """

    failures: list[str] = []
    for relative in sorted(POST_RUN_DERIVATIVE_SEED_SOURCES):
        # It must be NEW since the freeze: a source that already existed there
        # would mean the seed really had been visible before selection.
        if blob_at_commit(PHASE_P_FREEZE_COMMIT, relative) is not None:
            failures.append(
                f"{label}: {relative} already existed at {PHASE_P_FREEZE_COMMIT}; it "
                "cannot be a POST-RUN derivative occurrence"
            )
        committed = blob_at_commit(POST_RUN_DIAGNOSIS_COMMIT, relative)
        if committed is None:
            failures.append(
                f"{label}: {relative} does not exist at "
                f"{POST_RUN_DIAGNOSIS_COMMIT}, the commit declared to have added it"
            )
            continue
        if not is_ancestor(PHASE_P_FREEZE_COMMIT, POST_RUN_DIAGNOSIS_COMMIT):
            failures.append(
                f"{label}: {POST_RUN_DIAGNOSIS_COMMIT} does not descend from the "
                f"Phase-P freeze {PHASE_P_FREEZE_COMMIT}; it cannot be post-run"
            )
        target = PROJECT_ROOT / relative
        if not target.is_file():
            failures.append(f"{label}: {relative} no longer exists in the working tree")
            continue
        if target.read_bytes() != committed:
            failures.append(
                f"{label}: {relative} was EDITED since {POST_RUN_DIAGNOSIS_COMMIT}. "
                "The derivative ledger is recorded, never rewritten -- and its seeds "
                "are never trimmed to satisfy a check."
            )
            continue
        try:
            parsed = json.loads(committed.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            failures.append(f"{label}: {relative} is unreadable: {exc}")
            continue
        for key, expected in REQUIRED_DIAGNOSIS_IDENTITY.items():
            if parsed.get(key) != expected:
                failures.append(
                    f"{label}: {relative} declares {key}={parsed.get(key)!r}, "
                    f"expected {expected!r}; only a non-authoritative post-run HOLD "
                    "ledger may be a declared post-run seed occurrence"
                )
        attestation = parsed.get("immutable_evidence_attestation")
        if not isinstance(attestation, Mapping):
            failures.append(
                f"{label}: {relative} carries no immutable-evidence attestation"
            )
            continue
        for key, expected in REQUIRED_DIAGNOSIS_ATTESTATION.items():
            if attestation.get(key) != expected:
                failures.append(
                    f"{label}: {relative} attests {key}={attestation.get(key)!r}, "
                    f"expected {expected!r}"
                )
    return failures


def check_live_postrun_seed_supersession(*, label: str = "P-SEED") -> list[str]:
    """(B) Today's extra occurrences are EXACTLY the declared post-run source.

    Everything the frozen check guarantees about non-Phase-P seeds is retained
    verbatim: the forbidden set must still cover every non-Phase-P seed the
    tracked tree records, and every Phase-P seed must still be declared by Phase
    P's own artifacts.  What changes is only that each Phase-P seed is now
    permitted -- required, in fact -- to appear in one further, enumerated,
    post-run derivative ledger and in nothing else.
    """

    failures = check_post_run_derivative_artifact(label=label)

    derived = frozen_seed_triple()
    try:
        scanned = seed_derivation.scan_committed_seeds(PROJECT_ROOT)
    except seed_derivation.SeedDerivationError as exc:  # pragma: no cover - git absent
        return [*failures, f"{label}: cannot scan the tracked tree: {exc}"]

    # The bound, stated per seed and as an EQUALITY.  A missing occurrence is a
    # failure too, so removing one from the ledger cannot broaden acceptance by
    # making the expected set look satisfied.
    for seed, extra in sorted(extra_seed_sources(scanned, derived).items()):
        if extra != set(POST_RUN_DERIVATIVE_SEED_SOURCES):
            unexpected = sorted(extra - POST_RUN_DERIVATIVE_SEED_SOURCES)
            absent = sorted(POST_RUN_DERIVATIVE_SEED_SOURCES - extra)
            if unexpected:
                failures.append(
                    f"{label}: Phase-P seed {seed} appears in a source that is "
                    f"neither a declared Phase-P artifact nor the declared post-run "
                    f"derivative ledger: {unexpected}"
                )
            if absent:
                failures.append(
                    f"{label}: Phase-P seed {seed} does not appear in the declared "
                    f"post-run derivative source {absent}; the supersession describes "
                    "a repository state that does not exist"
                )
        declared = set(scanned.get(seed, ())) & set(seed_derivation.PHASE_P_ARTIFACTS)
        if not declared:
            failures.append(
                f"{label}: Phase-P seed {seed} is declared by none of Phase P's own "
                f"artifacts {sorted(seed_derivation.PHASE_P_ARTIFACTS)}"
            )

    # Retained unchanged: completeness for every NON-Phase-P seed.  The three
    # frozen seeds are excluded here because they are handled by the exact bound
    # above -- and only there.
    prior = seed_derivation.prior_phase_seeds(scanned)
    uncovered = sorted(
        set(prior) - set(seed_derivation.FORBIDDEN_SEEDS) - set(derived)
    )
    if uncovered:
        failures.append(
            f"{label}: the tracked tree records seeds the forbidden set does not "
            f"cover: {uncovered}"
        )
    return failures


def run_all() -> list[str]:
    """Empty only when BOTH temporal claims hold, each where it is true."""

    return [*check_historical_seed_freeze(), *check_live_postrun_seed_supersession()]


def summary() -> dict[str, Any]:
    derived = frozen_seed_triple()
    scanned = seed_derivation.scan_committed_seeds(PROJECT_ROOT)
    return {
        "record_kind": "post_phase_p_seed_provenance_supersession",
        "phase_p_freeze_commit": PHASE_P_FREEZE_COMMIT,
        "post_run_diagnosis_commit": POST_RUN_DIAGNOSIS_COMMIT,
        "frozen_seed_triple": list(derived),
        "historical_prospective_claim_holds": not check_historical_seed_freeze(),
        "live_postrun_supersession_holds": not check_live_postrun_seed_supersession(),
        "post_run_derivative_seed_sources": sorted(POST_RUN_DERIVATIVE_SEED_SOURCES),
        "post_run_occurrence_classification": "POST_RUN_DERIVATIVE_SEED_OCCURRENCE",
        "current_extra_sources": {
            str(seed): sorted(sources)
            for seed, sources in sorted(extra_seed_sources(scanned, derived).items())
        },
        "phase_p_verdict": "HOLD",
        "phase_p_terminal_status": "SCHEDULE_COMPLETE_VERDICT_HOLD",
        "pilot_v7_rc4_status": "UNQUALIFIED",
        "phase_p_cells_rerun": 0,
        "phase_p_result_reinterpreted": False,
        "model_inference_performed": False,
        "authorizes_confirmatory_execution": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    failures = run_all()
    if args.json:
        print(json.dumps(summary(), indent=2, sort_keys=True))
    for failure in failures:
        print(failure)
    print(
        f"post-Phase-P seed provenance supersession: "
        f"{'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s)); "
        "NO MODEL INFERENCE"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FROZEN_DERIVATION_RELATIVE",
    "PHASE_P_FREEZE_COMMIT",
    "POST_RUN_DERIVATIVE_SEED_SOURCES",
    "POST_RUN_DIAGNOSIS_COMMIT",
    "REQUIRED_DIAGNOSIS_ATTESTATION",
    "REQUIRED_DIAGNOSIS_IDENTITY",
    "SEED_RECORD_RELATIVE",
    "SeedSupersessionError",
    "blob_at_commit",
    "check_historical_seed_freeze",
    "check_live_postrun_seed_supersession",
    "check_post_run_derivative_artifact",
    "extra_seed_sources",
    "frozen_seed_triple",
    "is_ancestor",
    "run_all",
    "scan_seeds_at_commit",
    "summary",
    "tracked_files_at_commit",
]
