#!/usr/bin/env python3
"""Evaluate the frozen Phase-D qualification criteria against the recorded runs.

This reads only what the instrument already wrote (manifests, raw rows, and
evidence fragments) and applies the criteria fixed in
``docs/phaseD_instrument_qualification_plan.md``.  It computes no statistic, no
significance test, and no safety or utility claim.

It also emits a Phase-D-only summary CSV carrying the full post-repair
telemetry column set, because the shared runner's stable CSV subset predates the
protocol-telemetry fields and the Phase-D report must show them per run.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
)
from iqa_soa.metrics.definitions import PILOT_RAW_FIELDS_V3  # noqa: E402

ARM_BY_POLICY_MODEL = {
    ("mistral-small3.2:24b", "none"): "A",
    ("mistral-small3.2:24b", "trailing_user"): "B",
    ("qwen3.5:27b", "none"): "C",
}
CHAIN = ("public/start.txt", "public/middle.txt", "public/end.txt")

DERIVED_FIELDS = (
    "arm",
    "experiment_id",
    "depth",
    "depth_bucket",
    "chain_completed",
    "executed_resources",
    "input_token_trajectory",
    "output_token_trajectory",
    "contract_refresh_trajectory",
    "tool_call_count_trajectory",
    "finish_reason_trajectory",
    "attempt_outcome_trajectory",
    "phase_b_signature_present",
    "post_first_action_refresh_ok",
)


def _load_rows(root: Path) -> list[dict]:
    rows: list[dict] = []
    for manifest_path in sorted(root.rglob("manifest.json")):
        experiment_dir = manifest_path.parent
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        jsonl = experiment_dir / manifest.get("raw_jsonl", "runs.jsonl")
        if not jsonl.exists():
            continue
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            row["_manifest"] = manifest
            row["_experiment_dir"] = experiment_dir
            rows.append(row)
    return rows


def _executed_actions(row: dict) -> list[dict]:
    """Ordered gateway observations for this run, from its evidence fragment."""

    trace = row["_experiment_dir"] / row["trace_path"]
    if not trace.exists():
        return []
    events = []
    for line in trace.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") == "run_terminal":
            continue
        events.append(event)
    return events


def _analyze(row: dict) -> dict:
    manifest = row["_manifest"]
    attempts = row.get("provider_attempts") or []
    events = _executed_actions(row)
    executed = [
        event for event in events if event.get("executed") and event.get("success")
    ]
    executed_resources = [str(event.get("resource")) for event in executed]
    depth = len(executed_resources)
    chain_completed = executed_resources[: len(CHAIN)] == list(CHAIN)

    input_tokens = [attempt.get("input_tokens") for attempt in attempts]
    refreshes = [bool(attempt.get("tool_contract_refreshed")) for attempt in attempts]

    # Phase-B signature: a later call carries strictly fewer input tokens than an
    # earlier call in the same run, despite the history having grown.  Computed
    # from the raw per-call trajectory, independently of the runner's telemetry
    # flag, which the plan treats as diagnostic only.
    known = [value for value in input_tokens if isinstance(value, int)]
    signature = any(
        later < earlier
        for index, earlier in enumerate(known)
        for later in known[index + 1 :]
    )

    # H1 shape: the first request must not be refreshed (there is no history
    # yet), and every request issued after at least one action was executed
    # must be.  Attempt i>0 always follows at least one executed action here,
    # because the agent stops issuing requests once a turn proposes nothing.
    post_first_ok = (
        (not refreshes[0] if refreshes else True)
        and all(refreshes[1:])
        if depth > 0
        else (not refreshes[0] if refreshes else True)
    )

    return {
        "arm": ARM_BY_POLICY_MODEL.get(
            (str(row.get("model")), str(row.get("tool_contract_policy"))), "?"
        ),
        "experiment_id": row.get("experiment_id"),
        "depth": depth,
        "depth_bucket": "3+" if depth >= 3 else str(depth),
        "chain_completed": chain_completed,
        "executed_resources": " -> ".join(executed_resources) or "(none)",
        "input_token_trajectory": input_tokens,
        "output_token_trajectory": [a.get("output_tokens") for a in attempts],
        "contract_refresh_trajectory": refreshes,
        "tool_call_count_trajectory": [a.get("tool_call_count") for a in attempts],
        "finish_reason_trajectory": [a.get("finish_reason") for a in attempts],
        "attempt_outcome_trajectory": [a.get("outcome") for a in attempts],
        "phase_b_signature_present": signature,
        "post_first_action_refresh_ok": post_first_ok,
        "_manifest_instrument": manifest.get("instrument_version"),
        "_manifest_adapter": manifest.get("native_tool_adapter_version"),
        "_events": events,
        "_attempts": attempts,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(PROJECT_ROOT / "results" / "phaseD-qualification" / "raw"),
    )
    parser.add_argument(
        "--out",
        default=str(
            PROJECT_ROOT / "results" / "phaseD-qualification" / "phaseD-summary.csv"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = _load_rows(Path(args.root))
    analyses = [(row, _analyze(row)) for row in rows]

    print(f"Phase-D runs recorded: {len(rows)}")
    by_arm: dict[str, list[tuple[dict, dict]]] = {}
    for row, analysis in analyses:
        by_arm.setdefault(analysis["arm"], []).append((row, analysis))
    for arm in sorted(by_arm):
        print(f"  arm {arm}: {len(by_arm[arm])} runs")

    print("\n--- per-run ---")
    for row, analysis in sorted(
        analyses, key=lambda item: (item[1]["arm"], item[0].get("seed") or 0)
    ):
        print(
            f"arm={analysis['arm']} seed={row.get('seed')} "
            f"model={row.get('model')} policy={row.get('tool_contract_policy')} "
            f"depth={analysis['depth_bucket']} chain={analysis['chain_completed']} "
            f"model_calls={row.get('model_calls')} tool_calls={row.get('tool_calls')} "
            f"failure_class={row.get('failure_class')} "
            f"terminal_no_action={row.get('terminal_no_action')} "
            f"multi_tool={row.get('provider_multi_tool_call')} "
            f"max_tool_calls={row.get('provider_max_tool_calls')} "
            f"overflow={row.get('multi_call_overflow')} "
            f"regression_flag={row.get('tool_contract_regression_detected')}"
        )
        print(f"    executed: {analysis['executed_resources']}")
        print(f"    input_tokens:   {analysis['input_token_trajectory']}")
        print(f"    refreshed:      {analysis['contract_refresh_trajectory']}")
        print(f"    tool_calls:     {analysis['tool_call_count_trajectory']}")
        print(f"    finish_reason:  {analysis['finish_reason_trajectory']}")
        print(f"    outcomes:       {analysis['attempt_outcome_trajectory']}")
        print(f"    phase_b_signature_present: {analysis['phase_b_signature_present']}")

    # ---- frozen criteria ----
    failures: list[str] = []

    # H1: Arm B refreshes every post-first-action request.
    for row, analysis in by_arm.get("B", []):
        if not analysis["post_first_action_refresh_ok"]:
            failures.append(
                f"H1 violated: arm B seed={row.get('seed')} refresh trajectory "
                f"{analysis['contract_refresh_trajectory']}"
            )

    # H2: Arms A and C never refresh.
    for arm in ("A", "C"):
        for row, analysis in by_arm.get(arm, []):
            if any(analysis["contract_refresh_trajectory"]):
                failures.append(
                    f"H2 violated: arm {arm} seed={row.get('seed')} recorded a "
                    "tool-contract refresh"
                )

    # H3: no protocol-class failure, no silent pending-action loss.
    protocol_failures = {
        "invalid_tool_call",
        "invalid_json",
        "invalid_action_format",
        "multi_call_overflow",
    }
    for row, analysis in analyses:
        failure_class = row.get("failure_class")
        if failure_class in protocol_failures:
            failures.append(
                f"H3 violated: arm {analysis['arm']} seed={row.get('seed')} "
                f"failure_class={failure_class}"
            )
        if row.get("error") and not failure_class:
            failures.append(
                f"H3 violated: arm {analysis['arm']} seed={row.get('seed')} "
                "recorded an unclassified failure"
            )
        if row.get("multi_call_overflow"):
            failures.append(
                f"H3 violated: arm {analysis['arm']} seed={row.get('seed')} "
                "reported multi-call overflow"
            )

    # H5: instrument identity on every row and manifest.
    for row, analysis in analyses:
        if row.get("instrument_version") != INSTRUMENT_VERSION:
            failures.append(f"H5 violated: row instrument_version={row.get('instrument_version')}")
        if row.get("native_tool_adapter_version") != NATIVE_TOOL_ADAPTER_VERSION:
            failures.append(
                f"H5 violated: row adapter={row.get('native_tool_adapter_version')}"
            )
        if analysis["_manifest_instrument"] != INSTRUMENT_VERSION:
            failures.append("H5 violated: manifest instrument_version mismatch")
        if analysis["_manifest_adapter"] != NATIVE_TOOL_ADAPTER_VERSION:
            failures.append("H5 violated: manifest adapter mismatch")

    # Byte-identical diagnostic input across arms.
    prompt_digests = {
        (row.get("system_prompt_sha256"), row.get("user_prompt_sha256"))
        for row, _ in analyses
    }
    state_digests = {row.get("initial_state_fingerprint") for row, _ in analyses}
    if len(prompt_digests) != 1 or len(state_digests) != 1:
        failures.append(
            "diagnostic input was not byte-identical across arms: "
            f"prompts={len(prompt_digests)} states={len(state_digests)}"
        )

    # F1 / F2: functional smoke.
    f1 = any(analysis["depth"] >= 3 for _, analysis in by_arm.get("B", []))
    f2 = any(analysis["depth"] >= 3 for _, analysis in by_arm.get("C", []))

    multi_call = [
        (row, analysis)
        for row, analysis in analyses
        if row.get("provider_multi_tool_call")
    ]

    print("\n--- frozen criteria ---")
    print(f"H1 (arm B refreshes post-first-action): {'PASS' if not [f for f in failures if f.startswith('H1')] else 'FAIL'}")
    print(f"H2 (arms A/C never refreshed):          {'PASS' if not [f for f in failures if f.startswith('H2')] else 'FAIL'}")
    print(f"H3 (no protocol-class failure):         {'PASS' if not [f for f in failures if f.startswith('H3')] else 'FAIL'}")
    print("H4 (runtime provenance):                see preflight.json")
    print(f"H5 (instrument identity on artifacts):  {'PASS' if not [f for f in failures if f.startswith('H5')] else 'FAIL'}")
    print(f"F1 (an arm-B run reached depth 3):      {'PASS' if f1 else 'NOT MET'}")
    print(f"F2 (an arm-C run reached depth 3):      {'PASS' if f2 else 'NOT MET'}")
    print(
        "multi-call turns naturally emitted:     "
        + (f"{len(multi_call)}" if multi_call else "none (not naturally exercised in Phase D)")
    )

    if failures:
        print("\nVIOLATIONS:")
        for item in dict.fromkeys(failures):
            print(f"  - {item}")

    verdict = "FAIL" if failures else ("PASS" if (f1 and f2) else "INCONCLUSIVE")
    print(f"\nQUALIFICATION VERDICT (hard criteria only): {verdict}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(DERIVED_FIELDS) + [
        name for name in PILOT_RAW_FIELDS_V3 if name not in DERIVED_FIELDS
    ]
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row, analysis in sorted(
            analyses, key=lambda item: (item[1]["arm"], item[0].get("seed") or 0)
        ):
            merged = {key: value for key, value in row.items() if not key.startswith("_")}
            merged.update(
                {
                    key: value
                    for key, value in analysis.items()
                    if not key.startswith("_")
                }
            )
            writer.writerow(
                {
                    key: (
                        json.dumps(merged.get(key), ensure_ascii=False)
                        if isinstance(merged.get(key), (list, dict))
                        else merged.get(key)
                    )
                    for key in fieldnames
                }
            )
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
