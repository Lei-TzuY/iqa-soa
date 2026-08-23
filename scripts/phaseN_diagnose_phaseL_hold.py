#!/usr/bin/env python3
"""Phase-N: deterministic offline extraction of the archived Phase-L-B evidence.

**THIS SCRIPT RUNS NO MODEL, CONTACTS NO PROVIDER AND AUTHORIZES NOTHING.**

It is a READ-ONLY forensic extractor over the immutable Phase-L-B archive under
``results/phaseL-rc3-requalification/``.  It does not rescore Phase L-B, does
not produce a verdict, does not write into the archive, and does not modify any
frozen scientific input.

What it does:

* reconstructs, for every cell of a named task, the ordered provider-attempt
  ladder -- the model's RAW emitted proposal string, the adapter-canonicalized
  action and its canonical arguments -- joined to the ordered sandbox evidence
  trace (tool, resource, executed, success, gateway decision, error);
* reproduces the FROZEN Phase-L-B classification and the FROZEN contract-derived
  cell scoring by calling the frozen ``qualification_harness`` and
  ``analyze_phaseL_requalification`` code paths UNCHANGED, so the extraction can
  be reconciled against the archived ``phaseL-analysis.json`` rather than
  replacing it;
* records which ``harness.classify_row`` branch each cell took, as a descriptive
  attribution of why the frozen taxonomy produced the class it produced.

The reproduction is a RECONCILIATION, never a correction.  ``--reconcile``
asserts that every reproduced task-level number equals the archived one and
fails if it does not.  Nothing this script prints may be read as an alternative
Phase-L-B result, a corrected verdict, or a qualification.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import analyze_phaseL_requalification as analyzer  # noqa: E402
import phaseL_protocol as protocol  # noqa: E402
import qualification_harness as harness  # noqa: E402

#: The archived Phase-L-B evidence root.  Read-only for the whole of Phase N.
DEFAULT_ARCHIVE = PROJECT_ROOT / "results" / "phaseL-rc3-requalification"

#: The eight tasks the Phase-L-B analyzer left unqualified.
UNQUALIFIED_TASKS: tuple[str, ...] = (
    "PI-018",
    "PI-019",
    "PI-020",
    "KP-004",
    "BUD-014",
    "BUD-015",
    "BUD-016",
    "FAULT-004",
)

#: Every alias the frozen sandbox ``file.write`` payload resolver accepts, in
#: resolution order.  Mirrors ``src/iqa_soa/tools/registry.py::_payload`` and is
#: asserted against that file by :func:`verify_offline`, so this constant can
#: never drift away from the contract it documents.
FILE_WRITE_PAYLOAD_ALIASES: tuple[str, ...] = (
    "content",
    "body",
    "message",
    "payload",
    "data",
    "value",
)

#: The literal the frozen sandbox uses to express the alias set above.
_FROZEN_ALIAS_LITERAL = (
    "for key in ("
    + ", ".join(f'"{alias}"' for alias in FILE_WRITE_PAYLOAD_ALIASES)
    + "):"
)

#: (Phase O.)  The commit that archived the completed Phase-L-B run.  The alias
#: constant above describes the sandbox THAT run used, so it is verified there.
PHASE_L_B_EXECUTION_COMMIT = "693f81be666ec138def100dc7e920bd020080cd9"


def _registry_source_at(commit: str) -> str | None:
    """The committed bytes of the sandbox registry at ``commit``, or ``None``.

    Reads git only: ``subprocess`` spawns a local process, opens no socket, and
    raises no event the process-wide network audit hook refuses.
    """

    try:
        completed = subprocess.run(
            ["git", "cat-file", "blob", f"{commit}:src/iqa_soa/tools/registry.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.decode("utf-8")

#: Top-level modules whose presence would mean a network client is reachable.
_NETWORK_MODULE_ROOTS: frozenset[str] = frozenset(
    {"requests", "httpx", "aiohttp", "urllib3", "openai", "ollama"}
)

#: Audit events that would mean this process opened a network connection.
_NETWORK_AUDIT_EVENTS: frozenset[str] = frozenset(
    {"socket.connect", "socket.getaddrinfo", "urllib.Request"}
)


class NetworkAccessAttempted(RuntimeError):
    """Raised by the audit hook if anything in this process touches a network."""


_audit_violations: list[str] = []


def _refuse_network(event: str, args: tuple[Any, ...]) -> None:
    """Audit hook: record and refuse any network event raised in this process."""

    if event in _NETWORK_AUDIT_EVENTS:
        _audit_violations.append(event)
        raise NetworkAccessAttempted(
            f"Phase N is strictly offline; refused audit event {event!r}"
        )


def install_offline_guard() -> None:
    """Install the process-wide refusal hook.  Cannot be uninstalled."""

    sys.addaudithook(_refuse_network)


#: The name of the ONE digest basis this helper computes.  It is stamped into
#: every result so a digest can never be silently compared against one taken on a
#: different basis.  Two digests are comparable ONLY when this field matches.
#:
#: (N-R1) The Phase-N pre-diagnosis preflight measurement used a DIFFERENT basis
#: and produced a different -- equally valid -- hash over identical bytes. The two
#: bases differ in TWO independent ways, and both must be stated:
#:
#:   1. PATH BASIS.      Preflight listed repository-relative paths carrying the
#:                       ``results/phaseL-rc3-requalification/`` prefix; this
#:                       helper lists paths relative to the archive root.
#:   2. LINE TERMINATION. Preflight hashed a newline-TERMINATED listing (every
#:                       line, including the last, ends ``\n``, because it hashed
#:                       a text file); this helper hashes a newline-JOINED
#:                       listing with no trailing newline.
#:
#: Neither is more correct. They are different measurements, and
#: :func:`repository_relative_tree_digest` re-derives the preflight one so the
#: historical number is reproducible rather than merely asserted.
DIGEST_PATH_BASIS = "archive-root-relative/newline-joined"

#: The preflight basis, named so a reader recognises it rather than mistaking it
#: for a mismatch.
LEGACY_DIGEST_PATH_BASIS = "repository-relative/newline-terminated"

#: The exact value the Phase-N pre-diagnosis preflight recorded for the archive,
#: under :data:`LEGACY_DIGEST_PATH_BASIS`. Pinned here so a drift in either the
#: archive or the re-derivation is a visible test failure.
ORIGINAL_PREFLIGHT_DIGEST = (
    "0a659501b91df2f1c8e3e71bc975dc5c4457eaf9fd727646411a6c5363e86ece"
)


def tree_digest(root: Path) -> dict[str, Any]:
    """Deterministic content digest of every file beneath ``root``.

    The digest is ``sha256`` over the newline-joined, path-sorted
    ``"<file sha256>  <path>"`` listing, where each path is relative to ``root``
    itself -- the :data:`DIGEST_PATH_BASIS` basis.  ``root`` may live outside the
    repository (an isolated canonical-base worktree, say), which is what makes a
    base-versus-head comparison possible.

    The basis is part of the result. A hash computed over a different path basis
    is a different number over the same bytes, so the two are never comparable.
    """

    entries: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    material = "\n".join(f"{item['sha256']}  {item['path']}" for item in entries)
    try:
        label = root.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        # An out-of-tree root (an isolated canonical-base checkout).
        label = root.as_posix()
    return {
        "root": label,
        "path_basis": DIGEST_PATH_BASIS,
        "file_count": len(entries),
        "tree_sha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        "files": entries,
    }


def repository_relative_tree_digest(root: Path) -> dict[str, Any]:
    """Re-derive the Phase-N PREFLIGHT digest basis, exactly.

    Paths are relative to the repository root that contains ``root`` (so they
    carry the ``results/phaseL-rc3-requalification/`` prefix), and the listing is
    newline-TERMINATED rather than newline-joined -- the preflight hashed a text
    file, whose final line ends with a newline like every other.

    This exists so the historical ``0a659501...`` number can be reproduced from
    the archive rather than merely asserted, and so the two bases in the Phase-N
    record are concretely distinguishable. It is NOT the canonical basis; that is
    :func:`tree_digest`.
    """

    repo_root = root.parents[1]
    entries: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        entries.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    material = "".join(
        f"{item['sha256']}  {item['path']}\n" for item in entries
    )
    return {
        "root": root.relative_to(repo_root).as_posix(),
        "path_basis": LEGACY_DIGEST_PATH_BASIS,
        "file_count": len(entries),
        "tree_sha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
    }


def classify_branch(
    row: Mapping[str, Any],
    scripted_faults: Mapping[str, Sequence[harness.ScriptedFault]],
) -> dict[str, Any]:
    """Name the exact ``harness.classify_row`` branch this row takes.

    Descriptive only.  It re-walks the frozen classifier's own published branch
    order and reports which test fired first; it never substitutes a different
    rule and never changes an archived classification.
    """

    failure_class = str(row.get("failure_class") or "")
    task_id = str(row.get("task_id") or "")
    declared = tuple(scripted_faults.get(task_id, ()))
    match = harness.match_scripted_fault(row, declared)

    if row.get("tool_contract_regression_detected") is True:
        branch = "tool_contract_regression_detected"
    elif not row.get("provider_attempt_count"):
        branch = "no_provider_attempt_preserved"
    elif failure_class in harness.PROVIDER_FAILURE_CLASSES:
        branch = "PROVIDER_FAILURE_CLASSES"
    elif failure_class in harness.MODEL_PROTOCOL_FAILURE_CLASSES:
        branch = "MODEL_PROTOCOL_FAILURE_CLASSES"
    elif row.get("tool_call_parse_failure") is True:
        branch = "tool_call_parse_failure"
    elif row.get("multi_call_overflow") is True:
        branch = "multi_call_overflow"
    elif failure_class in harness.SANDBOX_FAILURE_CLASSES:
        if match.matched:
            branch = "SANDBOX_FAILURE_CLASSES/scripted_fault_matched"
        elif failure_class == "invalid_resource":
            branch = "SANDBOX_FAILURE_CLASSES/invalid_resource"
        else:
            branch = "SANDBOX_FAILURE_CLASSES/fail_closed"
    elif row.get("fault_triggered") is True:
        branch = (
            "fault_triggered/scripted_fault_matched"
            if match.matched
            else "fault_triggered/fail_closed"
        )
    elif row.get("model_refusal") is True:
        branch = "model_refusal"
    else:
        branch = "CELL_OK"

    return {
        "branch": branch,
        "row_failure_class": failure_class or None,
        "row_error": row.get("error"),
        "row_fault_triggered": row.get("fault_triggered"),
        "scripted_fault_matched": match.matched,
        "scripted_fault_refusal_reasons": list(match.reasons),
    }


def _argument_keys(action: Mapping[str, Any]) -> list[str] | None:
    arguments = action.get("arguments")
    if not isinstance(arguments, Mapping):
        return None
    return sorted(str(key) for key in arguments)


def attempt_ladder(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The ordered provider attempts, raw model emission beside canonical action."""

    ladder: list[dict[str, Any]] = []
    attempts = row.get("provider_attempts")
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        return ladder
    for position, attempt in enumerate(attempts):
        if not isinstance(attempt, Mapping):
            continue
        emitted = [
            item
            for item in (attempt.get("emitted_actions") or ())
            if isinstance(item, Mapping)
        ]
        ladder.append(
            {
                "attempt": position + 1,
                "outcome": attempt.get("outcome"),
                "finish_reason": attempt.get("finish_reason"),
                "protocol": attempt.get("protocol"),
                "tool_contract_refreshed": attempt.get("tool_contract_refreshed"),
                "multi_tool_call": attempt.get("multi_tool_call"),
                "failure_class": attempt.get("failure_class"),
                "original_action_id": attempt.get("original_action_id"),
                "canonical_action_id": attempt.get("canonical_action_id"),
                "original_resource": attempt.get("original_resource"),
                "canonical_resource": attempt.get("canonical_resource"),
                "model_raw_proposals": list(attempt.get("emitted_proposals") or ()),
                "canonical_actions": [
                    {
                        "action_id": item.get("action_id"),
                        "tool": item.get("tool"),
                        "resource": item.get("resource"),
                        "arguments": item.get("arguments"),
                        "argument_keys": _argument_keys(item),
                        "derived_from_untrusted": item.get("derived_from_untrusted"),
                        "risk_severity": item.get("risk_severity"),
                        "source": item.get("source"),
                    }
                    for item in emitted
                ],
            }
        )
    return ladder


_ROW_SCALARS: tuple[str, ...] = (
    "failure_class",
    "error",
    "fault_triggered",
    "observed_fault_tool",
    "observed_fault_resource",
    "observed_fault_mode",
    "observed_fault_provenance",
    "tool_calls",
    "model_calls",
    "provider_attempt_count",
    "task_success",
    "budget_violation",
    "resource_budget_violation",
    "unsafe_action_proposed",
    "unsafe_action_executed",
    "model_refusal",
    "terminal_no_action",
    "tool_call_parse_failure",
    "multi_call_overflow",
    "invalid_action_format",
)


def _plan_view(plan: Any) -> dict[str, Any]:
    return {
        "role": plan.role,
        "scoring_rule": plan.scoring_rule,
        "canonical_signatures": [list(item) for item in plan.canonical_signatures],
        "prerequisites": [list(item) for item in plan.prerequisites],
        "near_miss_signatures": [list(item) for item in plan.near_miss_signatures],
        "excluded_near_misses": list(plan.excluded_near_misses),
        "safe_route": [list(item) for item in plan.safe_route],
        "modality_signature": (
            list(plan.modality_signature) if plan.modality_signature else None
        ),
        "max_tool_calls": plan.max_tool_calls,
        "ordered_required": plan.ordered_required,
        "count_threshold_required": plan.count_threshold_required,
        "argument_predicate": (
            {
                "kind": plan.argument_predicate.kind,
                "key": plan.argument_predicate.key,
                "contract_terms": list(plan.argument_predicate.contract_terms),
            }
            if plan.argument_predicate is not None
            else None
        ),
    }


def extract(archive: Path, tasks: Sequence[str]) -> dict[str, Any]:
    """Extract the full descriptive forensic record for ``tasks``."""

    benchmark = protocol.load_benchmark(None)
    schedule = protocol.build_phase_l_schedule(benchmark)
    plans, _contract = analyzer.build_scoring_plans(None, None)
    rows = analyzer._read_jsonl(archive / "phaseL-runs.jsonl")

    wanted = set(tasks)
    cells: list[dict[str, Any]] = []
    reproduced: dict[str, list[Any]] = {}

    for position, row in enumerate(rows):
        if position >= len(schedule):
            break
        cell = schedule[position]
        plan = plans.get(cell.task_id)
        if plan is None:
            continue
        failure_class, disposition = harness.classify_row(
            row, cell, scripted_faults=benchmark.scripted_faults
        )
        events, defects = analyzer._trace_events(archive, row, cell)
        scoring_class, scoring_disposition = (
            (harness.INSTRUMENT_DEFECT, harness.IMMEDIATE_STOP)
            if defects
            else (failure_class, disposition)
        )
        scored = analyzer.evaluate_cell(
            cell=cell,
            row=row,
            events=events,
            plan=plan,
            failure_class=scoring_class,
            disposition=scoring_disposition,
        )
        reproduced.setdefault(cell.task_id, []).append(scored)
        if cell.task_id not in wanted:
            continue

        proposals = analyzer.proposals_for(events, row)
        cells.append(
            {
                "schedule_index": cell.index,
                "cell_key": cell.key,
                "arm": cell.arm,
                "task_id": cell.task_id,
                "seed": cell.seed,
                "model": cell.model,
                "tool_contract_policy": row.get("tool_contract_policy"),
                "historical_classification": {
                    "failure_class": failure_class,
                    "disposition": disposition,
                },
                "classifier_branch": classify_branch(row, benchmark.scripted_faults),
                "row_scalars": {name: row.get(name) for name in _ROW_SCALARS},
                "provider_attempts": attempt_ladder(row),
                "sandbox_trace": [
                    {
                        "sequence": event.get("sequence"),
                        "tool": event.get("tool"),
                        "resource": event.get("resource"),
                        "executed": event.get("executed"),
                        "success": event.get("success"),
                        "final_decision": event.get("final_decision"),
                        "error": event.get("error"),
                    }
                    for event in events
                ],
                "joined_proposals": [
                    {
                        "index": item.index,
                        "tool": item.tool,
                        "resource": item.resource,
                        "executed": item.executed,
                        "success": item.success,
                        "decision": item.decision,
                        "argument_keys": sorted(str(key) for key in item.arguments),
                        "arguments_available": item.arguments_available,
                    }
                    for item in proposals
                ],
                "frozen_cell_scoring": {
                    "valid": scored.valid,
                    "exposed": scored.exposed,
                    "near_miss": scored.near_miss,
                    "prerequisites_satisfied": scored.prerequisites_satisfied,
                    "safe_route_complete": scored.safe_route_complete,
                    "modality_established": scored.modality_established,
                    "executed_tool_calls": scored.executed_tool_calls,
                    "cap_crossed": scored.cap_crossed,
                    "fault_observed": scored.fault_observed,
                    "fault_bound_to_declaration": scored.fault_bound_to_declaration,
                    "detail": list(scored.detail),
                },
                "evidence_trace_defects": list(defects),
            }
        )

    return {
        "record_kind": "phase_n_phaseL_hold_forensic_extraction",
        "phase": "N",
        "model_inference_performed": False,
        "provider_contacted": False,
        "rescoring_performed": False,
        "phase_l_b_classification_is_immutable": True,
        "archive_root": archive.relative_to(PROJECT_ROOT).as_posix(),
        "tasks": list(tasks),
        "file_write_payload_aliases": list(FILE_WRITE_PAYLOAD_ALIASES),
        "frozen_scoring_plans": {
            task_id: _plan_view(plans[task_id])
            for task_id in tasks
            if task_id in plans
        },
        "cells": cells,
        "reproduced_task_reports": {
            task_id: _task_report_view(
                analyzer.classify_task(plans[task_id], results)
            )
            for task_id, results in sorted(reproduced.items())
            if task_id in plans
        },
    }


def _task_report_view(report: Any) -> dict[str, Any]:
    """Project a frozen ``TaskReport`` onto the archived analysis field names.

    ``TaskReport`` is a ``slots=True`` dataclass, and the analyzer serializes its
    ``fault_bound`` field under the archived key ``fault_bound_to_declaration``.
    Reconciliation compares against the archive, so it must use the archive's own
    names.
    """

    return {
        "task_id": report.task_id,
        "role": report.role,
        "status": report.status,
        "cells": report.cells,
        "valid_cells": report.valid_cells,
        "exposures": report.exposures,
        "near_misses": report.near_misses,
        "prerequisites_satisfied": report.prerequisites_satisfied,
        "safe_route_complete": report.safe_route_complete,
        "fault_bound_to_declaration": report.fault_bound,
        "modality_by_arm": dict(report.modality_by_arm),
        "stage_two_depth": report.stage_two_depth,
        "review_flags": list(report.review_flags),
        "notes": list(report.notes),
    }


#: The archived task-level fields the reproduction must equal exactly.
_RECONCILED_FIELDS: tuple[str, ...] = (
    "status",
    "role",
    "cells",
    "valid_cells",
    "exposures",
    "near_misses",
    "prerequisites_satisfied",
    "safe_route_complete",
    "fault_bound_to_declaration",
    "modality_by_arm",
    "stage_two_depth",
)


def reconcile(extraction: Mapping[str, Any], archive: Path) -> list[str]:
    """Prove the reproduction equals the archived Phase-L-B analysis exactly."""

    archived = json.loads(
        (archive / "phaseL-analysis.json").read_text(encoding="utf-8")
    )
    by_task = {entry["task_id"]: entry for entry in archived["tasks"]}
    failures: list[str] = []
    for task_id, report in sorted(extraction["reproduced_task_reports"].items()):
        want = by_task.get(task_id)
        if want is None:
            failures.append(f"{task_id}: absent from the archived analysis")
            continue
        for field_name in _RECONCILED_FIELDS:
            got = report.get(field_name)
            expected = want.get(field_name)
            if got != expected:
                failures.append(
                    f"{task_id}.{field_name}: reproduced {got!r}, archive holds "
                    f"{expected!r}"
                )
    return failures


def verify_offline() -> list[str]:
    """Prove this process performs no network, provider or model access.

    Three independent checks:

    1. no network-client module is importable-and-loaded in this process;
    2. no provider adapter module (``iqa_soa.agent.providers``) is loaded, so no
       code path capable of calling a model exists here at all;
    3. the process-wide audit hook recorded zero refused network events.

    The alias assertion is included because this module publishes the sandbox
    ``file.write`` payload contract as a constant, and a constant that drifted
    from the sandbox the Phase-L-B run actually used would make the diagnosis
    wrong.

    (Phase O amendment.)  That assertion is made against the registry as
    COMMITTED at the Phase-L-B execution commit, not against the working tree.
    ``FILE_WRITE_PAYLOAD_ALIASES`` documents the contract the Phase-L-B models
    were rejected by; Phase O acts on this diagnosis and withdraws the six
    undisclosed aliases in favour of one advertised key, so the live registry no
    longer contains the frozen literal -- by design, and as the direct
    consequence of finding N-1.  Checking the live tree would have meant the
    diagnosis silently invalidates itself the moment it is acted on.  Reading git
    keeps the check strict and permanently answerable, and it opens no socket.
    """

    failures: list[str] = []
    for name in sorted(sys.modules):
        root = name.split(".")[0]
        if root in _NETWORK_MODULE_ROOTS:
            failures.append(f"network client module {name!r} is loaded")
        if name.endswith("agent.providers") or name.endswith("agent.agent"):
            failures.append(f"provider/agent module {name!r} is loaded")
    if _audit_violations:
        failures.append(
            "the offline audit hook refused network events: "
            + ", ".join(sorted(set(_audit_violations)))
        )
    registry = _registry_source_at(PHASE_L_B_EXECUTION_COMMIT)
    if registry is None:
        failures.append(
            "cannot read src/iqa_soa/tools/registry.py at the Phase-L-B execution "
            f"commit {PHASE_L_B_EXECUTION_COMMIT}"
        )
    elif _FROZEN_ALIAS_LITERAL not in registry:
        failures.append(
            "FILE_WRITE_PAYLOAD_ALIASES no longer matches the sandbox payload "
            "resolver committed at the Phase-L-B execution commit "
            f"{PHASE_L_B_EXECUTION_COMMIT}"
        )
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--out", default=None)
    parser.add_argument("--tasks", nargs="*", default=list(UNQUALIFIED_TASKS))
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--verify-offline", action="store_true")
    parser.add_argument(
        "--with-extraction",
        action="store_true",
        help=(
            "with --verify-offline, run the whole extraction FIRST and then verify. "
            "The check then covers what the diagnosis actually does, rather than "
            "only what importing it does"
        ),
    )
    parser.add_argument("--digest", action="store_true")
    parser.add_argument(
        "--both-bases",
        action="store_true",
        help=(
            "with --digest, also print the repository-relative basis, so the two "
            "path bases in the Phase-N record are visibly distinct numbers over "
            "identical bytes"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    install_offline_guard()
    args = build_parser().parse_args(argv)
    archive = Path(args.archive).resolve()

    if args.digest:
        digest = tree_digest(archive)
        payload = {key: value for key, value in digest.items() if key != "files"}
        if args.both_bases:
            payload = {
                DIGEST_PATH_BASIS: payload,
                LEGACY_DIGEST_PATH_BASIS: repository_relative_tree_digest(archive),
            }
        print(json.dumps(payload, indent=2))
        return 0

    if args.verify_offline:
        if args.with_extraction:
            # Discarded on purpose: the artifact is irrelevant here, and what is
            # being proved is that producing it loads no provider, imports no
            # network client and trips no audit event.
            extract(archive, tuple(args.tasks))
        failures = verify_offline()
        for failure in failures:
            print(f"OFFLINE-CHECK FAIL: {failure}")
        print(
            f"offline verification: {len(failures)} failure(s); "
            "NO MODEL INFERENCE; no provider contacted"
        )
        return 1 if failures else 0

    extraction = extract(archive, tuple(args.tasks))
    exit_code = 0
    if args.reconcile:
        failures = reconcile(extraction, archive)
        for failure in failures:
            print(f"RECONCILE FAIL: {failure}")
        print(
            "reconciliation against the archived Phase-L-B analysis: "
            f"{len(failures)} failure(s); NO MODEL INFERENCE"
        )
        exit_code = 1 if failures else 0
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(extraction, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {out}")
    elif not args.reconcile:
        print(json.dumps(extraction, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
