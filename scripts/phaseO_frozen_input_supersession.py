#!/usr/bin/env python3
"""Prove the Phase-L freeze where it is actually true, and bound what moved.

THE PROBLEM
===========

``docs/phaseL_frozen_execution_inputs.json`` is the prospective freeze that bound
the Phase-L-B 102-cell QA-OFF requalification.  It pins fifteen files by SHA-256
and two TREES by digest, one of which is ``src/iqa_soa``.
``scripts/phaseL_protocol.py::check_frozen_inputs`` asserts every one of those
pins against the **live working tree**.

Phase O revises the instrument, because Phase N attributed six Phase-L-B
invalidations to a tool-argument contract the model was never shown and two more
to a failure-attribution rule that masked a fault which demonstrably fired.
Repairing either requires changing ``src/iqa_soa``.  The moment it changes, the
live assertion becomes false.

This is the **same shape** as the defect that stopped Phase L-A, and
``scripts/instrument_revision.py`` already names it: a historical claim ("when
Phase L-B ran, the instrument was tree ``598f7f3b...``") was being asserted by
checking a present-state claim ("the instrument in the working tree right now is
that tree").  Conflating them turns an immutability check into a prohibition on
ever repairing the defect it helped hide.

THE REMEDIES THAT WERE REJECTED, AND WHY
========================================

*Edit ``docs/phaseL_frozen_execution_inputs.json`` to record the new digest.*
A record updated to describe whatever the tree now contains is not a freeze.  It
would also retroactively describe the Phase-L-B run as having been executed
against an instrument that did not exist when it ran.

*Edit ``scripts/phaseL_protocol.py`` to stop checking the tree.*  Those bytes are
themselves a frozen Phase-L input, bound at ``a30f377e...`` by the very record
they verify.  Changing them retracts the freeze regardless of what git remembers.

*Declare the Phase-L artifacts historical and stop checking them at all.*  That
discards a live guarantee.  Fourteen of the fifteen per-file pins, and the whole
``benchmark/pilot-v7-rc3`` tree pin, are still true right now and must keep being
checked, because they are what makes "Phase O did not touch the rc3 benchmark or
the frozen Phase-L scripts" a verified statement rather than an assurance.

THE REMEDY USED
===============

Split the claim, exactly as Phase M split the Phase-K one.

**(A) The historical freeze assertion**, ``check_freeze_at_execution_commit``.
Every pin in the record -- all fifteen files and both trees -- is verified
against the **committed bytes at the Phase-L-B execution commit**.  That is where
the freeze actually bound the run, those bytes are immutable, and the check
therefore returns the same answer today, after Phase O, and after every later
phase.

**(B) The present-state assertion**, ``check_live_residual`` and
``superseded_live_assertions``.  Everything the record pins that Phase O did NOT
change must still match the live tree, and the set of assertions that no longer
match must be **exactly** the enumerated one.  The expected text is composed from
the two authoritative digests -- the Phase-L record's own pin and the approved
Phase-O revision's tree -- rather than pasted, so it cannot drift and cannot be
widened by hand.  An unapproved byte anywhere else changes the observed set and
fails.

Phase L-B is not rescored, its verdict is not retracted, pilot-v7-rc3 remains
UNQUALIFIED, and the consumed seeds remain consumed.  Nothing here authorizes any
execution.

NO MODEL INFERENCE.  This script reads git and the working tree and nothing else.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision as ir  # noqa: E402

#: The commit that archived the completed Phase-L-B evidence (PR #11).  This is
#: where the Phase-L freeze bound a real run, so it is where the freeze is
#: verified.  It is never recomputed and never updated.
PHASE_L_B_EXECUTION_COMMIT = "693f81be666ec138def100dc7e920bd020080cd9"

#: The commit that refroze the protocol Phase L-B then executed (PR #10).
PHASE_L_A_PRIME_FREEZE_COMMIT = "8bc623481805bab697f9e2bf9e5d6fc6a1a6df84"

#: The frozen-input record itself.  Read, never written.
FROZEN_INPUTS_RELATIVE = "docs/phaseL_frozen_execution_inputs.json"

#: The one tree pin Phase O supersedes.  Named explicitly so the supersession is
#: a closed, enumerable set rather than "whatever happens to fail".
SUPERSEDED_TREE_ROOT = "src/iqa_soa"


def load_frozen_inputs(commit: str | None = None) -> Mapping[str, Any]:
    """The frozen-input record, from the working tree or from a commit."""

    if commit is None:
        text = (PROJECT_ROOT / FROZEN_INPUTS_RELATIVE).read_text(encoding="utf-8")
    else:
        text = ir._git("cat-file", "blob", f"{commit}:{FROZEN_INPUTS_RELATIVE}").decode(
            "utf-8"
        )
    parsed: Mapping[str, Any] = json.loads(text)
    return parsed


def check_record_is_unedited() -> list[str]:
    """The Phase-L freeze record and protocol script are byte-unchanged.

    This is the check that makes everything else meaningful.  A supersession that
    permitted the superseded record to be edited would prove nothing at all.
    """

    failures: list[str] = []
    for relative in (
        FROZEN_INPUTS_RELATIVE,
        "scripts/phaseL_protocol.py",
        "scripts/run_phaseL_requalification.py",
        "scripts/analyze_phaseL_requalification.py",
        "scripts/qualification_harness.py",
        "docs/phaseM_instrument_revision.json",
    ):
        committed = ir.sha256_of_blob_at_commit(PHASE_L_B_EXECUTION_COMMIT, relative)
        target = PROJECT_ROOT / relative
        if not target.is_file():
            failures.append(f"O-SUP: {relative} no longer exists in the working tree")
            continue
        actual = ir.sha256_of(target)
        if committed != actual:
            failures.append(
                f"O-SUP: {relative} was EDITED. At the Phase-L-B execution commit it "
                f"hashes to {committed!r}; in the working tree it hashes to "
                f"{actual!r}. A superseded artifact is recorded, never rewritten."
            )
    return failures


def check_freeze_at_execution_commit() -> list[str]:
    """(A) Every Phase-L pin holds against COMMITTED bytes where it bound the run."""

    failures: list[str] = []
    try:
        record = load_frozen_inputs(PHASE_L_B_EXECUTION_COMMIT)
    except (ir.GitUnavailableError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [
            f"O-SUP: the Phase-L frozen-input record is unreadable at "
            f"{PHASE_L_B_EXECUTION_COMMIT}: {exc}"
        ]

    files = record.get("files")
    if not isinstance(files, Mapping):
        failures.append("O-SUP: the frozen-input record carries no file table")
    else:
        for relative, recorded in sorted(files.items()):
            committed = ir.sha256_of_blob_at_commit(
                PHASE_L_B_EXECUTION_COMMIT, str(relative)
            )
            if committed != recorded:
                failures.append(
                    f"O-SUP: at {PHASE_L_B_EXECUTION_COMMIT}, {relative} hashes to "
                    f"{committed!r}, but the Phase-L freeze recorded {recorded!r}. "
                    "History was rewritten."
                )

    trees = record.get("trees")
    if not isinstance(trees, Mapping):
        failures.append("O-SUP: the frozen-input record carries no tree table")
    else:
        for root, recorded in sorted(trees.items()):
            try:
                committed = ir.tree_digest_at_commit(
                    PHASE_L_B_EXECUTION_COMMIT, str(root)
                )
            except ir.GitUnavailableError as exc:  # pragma: no cover - git absent
                failures.append(f"O-SUP: cannot digest {root} at the execution commit: {exc}")
                continue
            if committed != recorded:
                failures.append(
                    f"O-SUP: at {PHASE_L_B_EXECUTION_COMMIT}, tree {root} digests to "
                    f"{committed!r}, but the Phase-L freeze recorded {recorded!r}. "
                    "History was rewritten."
                )
    return failures


def superseded_live_assertions() -> tuple[str, ...]:
    """(B) The EXACT live claims of the frozen Phase-L protocol that Phase O supersedes.

    Composed from the two authoritative digests rather than pasted: the Phase-L
    record's own ``src/iqa_soa`` pin, and the approved Phase-O revision's tree.
    An unapproved byte under ``src/iqa_soa`` changes the live digest, so the
    observed set stops matching this one AND
    ``instrument_revision.check_approved_instrument_revision`` fails.  The
    supersession admits exactly one instrument: the approved one.
    """

    record = load_frozen_inputs()
    trees = record.get("trees")
    recorded = ""
    if isinstance(trees, Mapping):
        recorded = str(trees.get(SUPERSEDED_TREE_ROOT) or "")
    approved = str(ir.load_revision()["current_instrument"]["src_iqa_soa_tree"])

    src = str(PROJECT_ROOT / "src")
    if src not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, src)
    from iqa_soa.instrument import (
        FAULT_PROVENANCE_INSTRUMENT_VERSION,
        FAULT_PROVENANCE_RAW_SCHEMA_VERSION,
        INSTRUMENT_VERSION,
        RAW_SCHEMA_VERSION,
    )

    phase_m_changed = ir.load_revision_chain()[0].get("changed_files")
    per_file: list[str] = []
    if isinstance(phase_m_changed, Mapping):
        for relative, entry in sorted(phase_m_changed.items()):
            if not isinstance(entry, Mapping):  # pragma: no cover - validated elsewhere
                continue
            approved_sha = str(entry.get("sha256") or "")
            actual_sha = ir.sha256_of(PROJECT_ROOT / relative)
            if actual_sha == approved_sha:
                continue
            per_file.append(
                f"FROZEN_ARTIFACT_MISMATCH: approved instrument file {relative} "
                f"recorded={approved_sha} actual={actual_sha}"
            )

    return (
        f"FROZEN_ARTIFACT_MISMATCH: tree {SUPERSEDED_TREE_ROOT} "
        f"recorded={recorded} actual={approved}",
        f"FROZEN_ARTIFACT_MISMATCH: instrument version is {INSTRUMENT_VERSION!r}, "
        f"this protocol is frozen against {FAULT_PROVENANCE_INSTRUMENT_VERSION!r}",
        f"FROZEN_ARTIFACT_MISMATCH: raw schema version is {RAW_SCHEMA_VERSION}, "
        f"this protocol is frozen against {FAULT_PROVENANCE_RAW_SCHEMA_VERSION}",
        f"FROZEN_ARTIFACT_MISMATCH: {SUPERSEDED_TREE_ROOT} digests to {approved}, "
        f"the approved Phase-M revision is {recorded}",
        *per_file,
    )


def check_live_residual() -> list[str]:
    """(B) Everything Phase O did NOT change must still match the live tree.

    Fourteen of the fifteen per-file pins and the whole ``benchmark/pilot-v7-rc3``
    tree pin are still live guarantees, and this is what keeps them checked.  It
    is the half of the frozen-input check that Phase O does not supersede, and it
    is deliberately stated positively rather than as "the rest".
    """

    failures: list[str] = []
    record = load_frozen_inputs()
    files = record.get("files")
    if isinstance(files, Mapping):
        for relative, recorded in sorted(files.items()):
            target = PROJECT_ROOT / str(relative)
            if not target.is_file():
                failures.append(f"O-SUP: frozen Phase-L input {relative} no longer exists")
                continue
            actual = ir.sha256_of(target)
            if actual != recorded:
                failures.append(
                    f"O-SUP: frozen Phase-L input {relative} moved in the working "
                    f"tree (recorded={recorded} actual={actual}). Phase O supersedes "
                    f"only the {SUPERSEDED_TREE_ROOT} TREE pin; every per-file pin "
                    "remains a live guarantee."
                )
    trees = record.get("trees")
    if isinstance(trees, Mapping):
        for root, recorded in sorted(trees.items()):
            if str(root) == SUPERSEDED_TREE_ROOT:
                continue
            actual = ir.tree_digest(str(root))
            if actual != recorded:
                failures.append(
                    f"O-SUP: frozen Phase-L tree {root} moved in the working tree "
                    f"(recorded={recorded} actual={actual}). Only "
                    f"{SUPERSEDED_TREE_ROOT} is superseded."
                )
    return failures


def check_protocol_failure_set_is_exactly_the_supersession() -> list[str]:
    """The frozen protocol's live failure set must be EXACTLY what is enumerated.

    Any additional failure fails this check, so every other claim the frozen
    Phase-L protocol makes is still checked live and still holds.  A DIFFERENT
    instrument fails it too, because the expected text embeds the approved digest.
    """

    import phaseL_protocol as protocol  # noqa: PLC0415 - deliberately late

    expected = superseded_live_assertions()
    observed = tuple(protocol.check_frozen_inputs()) + tuple(
        protocol.check_instrument_pins()
    )
    if set(observed) == set(expected):
        return []
    unexpected = sorted(set(observed) - set(expected))
    absent = sorted(set(expected) - set(observed))
    failures: list[str] = []
    for item in unexpected:
        failures.append(
            "O-SUP: the frozen Phase-L protocol reports a live failure Phase O did "
            f"NOT supersede: {item}"
        )
    for item in absent:
        failures.append(
            "O-SUP: Phase O declares a superseded assertion the frozen protocol does "
            f"not actually report: {item}"
        )
    return failures


def check_phase_l_b_evidence_untouched() -> list[str]:
    """The archived Phase-L-B result tree is byte-identical to its own commit."""

    failures: list[str] = []
    root = "results/phaseL-rc3-requalification"
    try:
        committed = ir.tree_digest_at_commit(PHASE_L_B_EXECUTION_COMMIT, root)
        actual = ir.tree_digest(root)
    except ir.GitUnavailableError as exc:  # pragma: no cover - git absent
        return [f"O-SUP: cannot digest {root}: {exc}"]
    if committed != actual:
        failures.append(
            f"O-SUP: the Phase-L-B evidence tree moved. At "
            f"{PHASE_L_B_EXECUTION_COMMIT} it digests to {committed}; in the working "
            f"tree it digests to {actual}."
        )
    return failures


def run_all() -> list[str]:
    return [
        *check_record_is_unedited(),
        *check_freeze_at_execution_commit(),
        *check_live_residual(),
        *check_protocol_failure_set_is_exactly_the_supersession(),
        *check_phase_l_b_evidence_untouched(),
    ]


def summary() -> dict[str, Any]:
    return {
        "record_kind": "phase_o_frozen_input_supersession",
        "phase_l_a_prime_freeze_commit": PHASE_L_A_PRIME_FREEZE_COMMIT,
        "phase_l_b_execution_commit": PHASE_L_B_EXECUTION_COMMIT,
        "phase_l_b_verdict": "HOLD",
        "phase_l_b_terminal_status": "SCHEDULE_COMPLETE_VERDICT_HOLD",
        "pilot_v7_rc3_status": "UNQUALIFIED",
        "phase_l_seeds_status": "CONSUMED_BY_FORMAL_PHASE_L_B",
        "superseded_tree_root": SUPERSEDED_TREE_ROOT,
        "superseded_live_assertions": list(superseded_live_assertions()),
        "historical_freeze_provable_at_execution_commit": not check_freeze_at_execution_commit(),
        "phase_l_b_evidence_untouched": not check_phase_l_b_evidence_untouched(),
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
        f"Phase-O frozen-input supersession: {'PASS' if not failures else 'FAIL'} "
        f"({len(failures)} failure(s)); NO MODEL INFERENCE"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FROZEN_INPUTS_RELATIVE",
    "PHASE_L_A_PRIME_FREEZE_COMMIT",
    "PHASE_L_B_EXECUTION_COMMIT",
    "SUPERSEDED_TREE_ROOT",
    "check_freeze_at_execution_commit",
    "check_live_residual",
    "check_phase_l_b_evidence_untouched",
    "check_protocol_failure_set_is_exactly_the_supersession",
    "check_record_is_unedited",
    "run_all",
    "summary",
    "superseded_live_assertions",
]
