#!/usr/bin/env python3
"""Probe whether the Phase-K.2 fault-provenance contract is REACHABLE under QA OFF.

Phase L-A set out to freeze the execution protocol for a 17 x 2 x 3 QA-OFF
requalification of pilot-v7-rc3.  Section 10 of that protocol requires the future
driver to stamp four runtime-derived fields on any cell that observed a sandbox
fault::

    observed_fault_tool
    observed_fault_resource
    observed_fault_mode
    observed_fault_provenance

``scripts/qualification_harness.py`` fixes where each of them may come from
(``RUNTIME_FAULT_PROVENANCE_SOURCES``) and fails closed when they are absent: an
unproved sandbox failure becomes ``UNEXPECTED_SANDBOX_FAILURE``, whose frozen
disposition is ``CELL_INVALID_AND_HOLD``.

This probe asks the question Phase K never asked: **can a driver actually obtain
those fields from what the canonical instrument persists for a QA-OFF cell?**

Phase K proved the contract satisfiable by driving ``ToolRegistry`` directly and
reading ``SandboxState.operation_log`` in-process
(``check_observed_fault_provenance_is_runtime_derived`` in
``scripts/validate_pilot_v7_rc3.py``).  A real qualification driver has no such
access.  It receives a raw row and an evidence trace written by
``ExperimentRunner``, and nothing else.

So the probe runs the REAL ``ExperimentRunner``, on the REAL frozen rc3 cases, in
the REAL QA-OFF treatment, and then inspects exactly what was written to disk.
It substitutes the ``DeterministicStubProvider`` for the model, which replays each
case's own ``scripted_actions``.  That is the point: it exercises the persistence
path without inference, and it reaches the faulted tool and resource by
construction, so the result is a property of the INSTRUMENT rather than of any
model's behaviour.  A real model that reached the same actions would produce rows
with exactly the same field set.

NO MODEL IS RUN.  No provider is contacted.  Output goes to a temporary directory
and nothing under ``results/`` is written.

BEFORE / AFTER (do not delete this record).

* At the Phase-L-A commit ``eace204d4c27a9ca48d3c0a660832f640b7a900b``, with
  instrument version ``2`` / raw schema ``3``, this probe exited **4**:
  ``observed_fault_mode`` and ``observed_fault_provenance`` were unreachable and
  both BUD-016 and FAULT-004 were forced to ``CELL_INVALID_AND_HOLD``.  That
  finding was correct and is not retracted.
* From the Phase-M instrument revision -- version ``3`` / raw schema ``4``,
  hash-pinned in ``docs/phaseM_instrument_revision.json`` -- the same probe over
  the same frozen cases exits **0**: ``ExperimentRunner`` now derives the four
  fields from the live ``GatewayOutcome`` sequence
  (``iqa_soa.experiment.fault_provenance``) and both tasks classify
  ``EXPECTED_SCRIPTED_FAULT`` -> ``CONTINUE``.

The probe itself is UNCHANGED in what it measures.  It still refuses to accept
anything but the four contract fields recovered from persisted artifacts, so if
the repair is ever reverted or the fields silently disappear it returns to
exit 4.

Exit codes:
    0  the contract is reachable -- every required field is recoverable
    4  the contract is NOT reachable -- report HOLD_PHASE_L_PROTOCOL
    2  the probe could not be completed
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import qualification_harness as harness  # noqa: E402
from iqa_soa.agent.providers import DeterministicStubProvider  # noqa: E402
from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentRunner,
    load_experiment_config,
)
from iqa_soa.experiment.treatments import treatment_for  # noqa: E402

BENCHMARK_VERSION = "pilot-v7-rc3"

#: The only two rc3 tasks that declare a scripted fault, and the exact tool,
#: resource and mode each declares.  Read here for reporting only; the probe
#: never uses them as an observation.
FAULT_TASKS: tuple[str, ...] = ("BUD-016", "FAULT-004")

#: A frozen model digest stands in for the arm identity.  The probe stamps the
#: identity fields the way a Phase-L driver would -- from the frozen cell, before
#: execution -- so that the ONLY thing the classification can turn on is fault
#: provenance.
PROBE_MODEL = "qwen3.5:27b"
PROBE_DIGEST = "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
PROBE_SEED = 929260329


def _run_qa_off_cells(task_ids: Sequence[str], workdir: Path) -> tuple[Path, list[dict[str, Any]]]:
    """Execute the named rc3 tasks through the canonical runner under QA OFF."""

    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "manifest.json")
    if frozen.benchmark_version != BENCHMARK_VERSION:
        raise RuntimeError(f"expected {BENCHMARK_VERSION}, got {frozen.benchmark_version}")
    config = load_experiment_config(PROJECT_ROOT / "configs" / "phaseI-qualification.yaml")
    config = replace(
        config,
        output_root=workdir,
        treatments=("off",),
        repetitions=1,
        seeds=(PROBE_SEED,),
    )
    experiment_dir = ExperimentRunner(config, provider=DeterministicStubProvider()).run(
        treatments=["off"],
        case_ids=list(task_ids),
        repetitions=1,
        frozen_benchmark=frozen,
        max_total_runs=len(task_ids),
        # A stub provider may never be labelled as a real-model experiment.
        experiment_kind="deterministic_mechanism_validation",
        infrastructure_retry_limit=0,
    )
    rows = [
        json.loads(line)
        for line in (experiment_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return experiment_dir, rows


def _trace_events(experiment_dir: Path, row: Mapping[str, Any]) -> list[dict[str, Any]]:
    path = experiment_dir / str(row.get("trace_path") or "")
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _recoverable_provenance(
    row: Mapping[str, Any], events: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Which of the four required fields a driver could recover, and from where.

    This is deliberately generous.  It looks for the fields on the row, then for
    any admitted runtime structure the persisted artifacts might carry: a
    ``GatewayOutcome``-shaped block, a sandbox ``operation_log``, and an evidence
    ``tool_call`` record with the ``tool_result.metadata`` the sandbox stamps.
    """

    found: dict[str, str] = {}

    for name in harness.REQUIRED_FAULT_PROVENANCE_FIELDS:
        if isinstance(row.get(name), str) and row[name].strip():
            found[name] = "raw row (already stamped)"

    # gateway_outcome.* -- is any GatewayOutcome shape persisted at all?
    for key in ("gateway_outcomes", "outcomes", "executed_action", "proposed_action"):
        if row.get(key):
            found.setdefault("observed_fault_tool", f"row[{key!r}]")
            found.setdefault("observed_fault_resource", f"row[{key!r}]")

    # sandbox.operation_log -- is the log persisted anywhere recoverable?
    if row.get("operation_log"):
        for name in harness.REQUIRED_FAULT_PROVENANCE_FIELDS:
            found.setdefault(name, "row['operation_log']")

    # evidence.tool_call -- tool and resource are always present; the fault mode
    # lives in tool_result.metadata, which only DETAILED evidence records.
    for event in events:
        if event.get("tool"):
            found.setdefault("observed_fault_tool", "evidence.tool_call")
            found.setdefault("observed_fault_resource", "evidence.tool_call")
        tool_result = event.get("tool_result")
        if isinstance(tool_result, Mapping):
            metadata = tool_result.get("metadata")
            if isinstance(metadata, Mapping) and metadata.get("fault_mode"):
                found.setdefault("observed_fault_mode", "evidence.tool_call.tool_result")
                found.setdefault("observed_fault_provenance", "evidence.tool_call")

    missing = [
        name for name in harness.REQUIRED_FAULT_PROVENANCE_FIELDS if name not in found
    ]
    return {"recoverable": found, "unrecoverable": missing}


def _malformed_response_indistinguishability(workdir: Path) -> dict[str, Any]:
    """Is FAULT-004's malformed response visible AT ALL in a QA-OFF trace?

    ``ToolRegistry._fault_result`` returns a ``malformed_response`` as SUCCESS
    with the sentinel payload ``<<<MALFORMED_SIMULATED_RESPONSE>>>`` and no error
    string.  Under QA OFF the evidence record carries neither the tool result nor
    the output, so the question is whether the persisted event differs at all
    from the same call with no fault declared.

    This runs FAULT-004 twice through the canonical runner: once as frozen, and
    once with the case's declared faults stripped.  If the two persisted events
    are equal, the fault is not merely unproved -- it is unobservable, and no
    amount of driver engineering can recover it from the trace.
    """

    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "manifest.json")
    case = {item.id: item for item in frozen.cases}["FAULT-004"]
    without_fault = replace(
        frozen, cases=(replace(case, environment=replace(case.environment, faults={})),)
    )

    volatile = {"timestamp", "evidence_id", "experiment_id", "run_id"}
    observed: dict[str, dict[str, Any]] = {}
    triggered: dict[str, Any] = {}
    sentinel_in_trace: dict[str, bool] = {}
    row_provenance: dict[str, dict[str, Any]] = {}
    for label, variant in (("fault_declared", frozen), ("fault_stripped", without_fault)):
        config = load_experiment_config(PROJECT_ROOT / "configs" / "phaseI-qualification.yaml")
        config = replace(
            config,
            output_root=workdir / label,
            treatments=("off",),
            repetitions=1,
            seeds=(PROBE_SEED,),
        )
        experiment_dir = ExperimentRunner(
            config, provider=DeterministicStubProvider()
        ).run(
            treatments=["off"],
            case_ids=["FAULT-004"],
            repetitions=1,
            frozen_benchmark=variant,
            max_total_runs=1,
            experiment_kind="deterministic_mechanism_validation",
            infrastructure_retry_limit=0,
        )
        row = json.loads(
            (experiment_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()[0]
        )
        trace_text = (experiment_dir / str(row["trace_path"])).read_text(encoding="utf-8")
        event = json.loads(trace_text.splitlines()[0])
        observed[label] = {
            key: value for key, value in event.items() if key not in volatile
        }
        triggered[label] = row.get("fault_triggered")
        sentinel_in_trace[label] = "MALFORMED_SIMULATED_RESPONSE" in trace_text
        row_provenance[label] = {
            name: row.get(name)
            for name in harness.REQUIRED_FAULT_PROVENANCE_FIELDS
        }

    identical = observed["fault_declared"] == observed["fault_stripped"]
    rows_differ = row_provenance["fault_declared"] != row_provenance["fault_stripped"]
    return {
        "task_id": "FAULT-004",
        "persisted_event_with_fault": observed["fault_declared"],
        "persisted_event_without_fault": observed["fault_stripped"],
        "events_are_identical": identical,
        "row_fault_triggered": triggered,
        "malformed_sentinel_present_in_trace": sentinel_in_trace,
        "row_observed_fault_provenance": row_provenance,
        "rows_differ_in_observed_fault_provenance": rows_differ,
        "only_differentiator": (
            "row['fault_triggered'], which iqa_soa.metrics.collector._fault_triggered "
            "computes as tool_result.metadata['fault_mode'] == case.fault.type -- a "
            "comparison against the benchmark DECLARATION. Phase K.2 names that class "
            "of source in DECLARED_FAULT_PROVENANCE_SOURCES and forbids it as "
            "provenance precisely because it is circular."
        )
        if identical and not rows_differ
        else "",
        "post_repair_differentiator": (
            "The EVIDENCE events remain byte-identical, which is correct and "
            "deliberate: QA OFF is still non-detailed and no tool output, sentinel "
            "payload or protected value was added to the trace. The differentiator "
            "now lives in the RAW ROW, where ExperimentRunner stamps the four "
            "observed_fault_* fields from the live GatewayOutcome sequence. Stripping "
            "the declared fault removes the runtime stamp, so the fields go null -- "
            "the observation follows what the sandbox DID, not what the benchmark "
            "declared."
        )
        if rows_differ
        else "",
    }


def probe(*, keep: bool = False) -> dict[str, Any]:
    """Run the probe and return a structured finding."""

    frozen = load_frozen_pilot(PROJECT_ROOT / "benchmark" / BENCHMARK_VERSION / "manifest.json")
    declared = harness.scripted_faults_from_cases(list(frozen.cases))
    manifest_sha256 = frozen.manifest_sha256

    workdir = Path(tempfile.mkdtemp(prefix="phaseL-provenance-probe-"))
    try:
        experiment_dir, rows = _run_qa_off_cells(FAULT_TASKS, workdir)

        schedule = harness.build_schedule(
            [harness.ArmSpec("probe", PROBE_MODEL, PROBE_DIGEST)],
            list(FAULT_TASKS),
            [PROBE_SEED],
            qa_mode="off",
            benchmark_manifest_sha256=manifest_sha256,
        )
        cells = {cell.task_id: cell for cell in schedule}

        findings: list[dict[str, Any]] = []
        for row in rows:
            task_id = str(row.get("task_id"))
            cell = cells[task_id]
            events = _trace_events(experiment_dir, row)

            # Stamp exactly the identity fields a Phase-L driver legitimately
            # owns: they come from the frozen cell, not from the model.  Fault
            # provenance is deliberately NOT stamped -- that is the question.
            bound = dict(row)
            bound.update(
                {
                    "model": cell.model,
                    "model_digest": cell.model_digest,
                    "seed": cell.seed,
                    "run_key": cell.run_key,
                }
            )
            assert not harness.bind_row_to_cell(bound, cell), (
                "identity binding must succeed so the classification turns only "
                "on fault provenance"
            )

            failure_class, disposition = harness.classify_row(
                bound, cell, scripted_faults=declared
            )
            match = harness.match_scripted_fault(bound, declared.get(task_id, ()))
            reachability = _recoverable_provenance(bound, events)

            declaration = declared.get(task_id, ())
            findings.append(
                {
                    "task_id": task_id,
                    "declared_fault": [
                        {"tool": f.tool, "resource": f.resource, "mode": f.mode}
                        for f in declaration
                    ],
                    "row_failure_class": row.get("failure_class"),
                    "row_fault_triggered": row.get("fault_triggered"),
                    "row_error": row.get("error"),
                    "evidence_event_keys": sorted({k for e in events for k in e}),
                    "evidence_event_count": len(events),
                    "harness_failure_class": failure_class,
                    "harness_disposition": disposition,
                    "expected_scripted_fault_matched": match.matched,
                    "match_refusal_reasons": list(match.reasons),
                    "provenance_reachability": reachability,
                }
            )

        detailed_evidence_under_qa_off = treatment_for("off").detailed_evidence
        unreachable = sorted(
            {
                name
                for finding in findings
                for name in finding["provenance_reachability"]["unrecoverable"]
            }
        )
        blocked = [
            finding["task_id"]
            for finding in findings
            if finding["harness_disposition"]
            in (harness.CELL_INVALID_AND_HOLD, harness.IMMEDIATE_STOP)
        ]
        return {
            "phase": "L-A",
            "benchmark_version": BENCHMARK_VERSION,
            "benchmark_manifest_sha256": manifest_sha256,
            "treatment": "off",
            "model_inference_performed": False,
            "provider": "DeterministicStubProvider (replays the case's own scripted_actions)",
            "detailed_evidence_under_qa_off": detailed_evidence_under_qa_off,
            "required_fault_provenance_fields": list(
                harness.REQUIRED_FAULT_PROVENANCE_FIELDS
            ),
            "admitted_runtime_sources": sorted(
                harness.RUNTIME_FAULT_PROVENANCE_SOURCES
            ),
            "findings": findings,
            "malformed_response_observability": _malformed_response_indistinguishability(
                workdir / "indistinguishability"
            ),
            "fields_unreachable_from_persisted_qa_off_artifacts": unreachable,
            "tasks_forced_to_hold_or_stop": blocked,
            "contract_reachable": not unreachable and not blocked,
            "experiment_dir": str(experiment_dir) if keep else None,
        }
    finally:
        if not keep:
            shutil.rmtree(workdir, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep", action="store_true", help="keep the temporary experiment directory"
    )
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--out", default=None, help="optional path for the JSON finding")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        finding = probe(keep=args.keep)
    except Exception as exc:  # the probe itself failing is not a HOLD finding
        print(f"PROBE_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(finding, indent=2, sort_keys=True))
    else:
        print(f"benchmark          : {finding['benchmark_version']}")
        print(f"treatment          : {finding['treatment']} (no model was run)")
        print(
            "detailed evidence under QA OFF: "
            f"{finding['detailed_evidence_under_qa_off']}"
        )
        for item in finding["findings"]:
            print(f"\n--- {item['task_id']} ---")
            print(f"  declared fault        : {item['declared_fault']}")
            print(f"  row.failure_class     : {item['row_failure_class']!r}")
            print(f"  row.fault_triggered   : {item['row_fault_triggered']!r}")
            print(f"  evidence event keys   : {item['evidence_event_keys']}")
            print(f"  harness class         : {item['harness_failure_class']}")
            print(f"  harness disposition   : {item['harness_disposition']}")
            print(
                "  unrecoverable fields  : "
                f"{item['provenance_reachability']['unrecoverable']}"
            )
        observability = finding["malformed_response_observability"]
        print("\n--- FAULT-004 malformed-response observability ---")
        print(f"  event with fault   : {json.dumps(observability['persisted_event_with_fault'], sort_keys=True)}")
        print(f"  event without fault: {json.dumps(observability['persisted_event_without_fault'], sort_keys=True)}")
        print(f"  identical          : {observability['events_are_identical']}")
        print(f"  sentinel in trace  : {observability['malformed_sentinel_present_in_trace']}")
        print(f"  row provenance     : {json.dumps(observability['row_observed_fault_provenance'], sort_keys=True)}")
        print(f"  rows differ        : {observability['rows_differ_in_observed_fault_provenance']}")
        print(
            f"\nfields unreachable    : "
            f"{finding['fields_unreachable_from_persisted_qa_off_artifacts']}"
        )
        print(f"tasks held/stopped    : {finding['tasks_forced_to_hold_or_stop']}")
        print(f"contract reachable    : {finding['contract_reachable']}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(finding, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"finding={out}")

    if not finding["contract_reachable"]:
        print(
            "HOLD_PHASE_L_PROTOCOL: the Phase-K.2 observed-fault provenance "
            "contract cannot be satisfied from the artifacts the canonical "
            "instrument persists for a QA-OFF cell",
            file=sys.stderr,
        )
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
