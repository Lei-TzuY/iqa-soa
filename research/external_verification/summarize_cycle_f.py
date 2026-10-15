"""Summarize retained Cycle F outputs; never reads or modifies original data."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    output = root / "cycle_f_20261010"
    summary = json.loads((output / "replay_summary.json").read_text())
    rows = [json.loads(line) for line in gzip.decompress(
        (output / "record_replay.jsonl.gz").read_bytes()).splitlines()]
    prior = json.loads((root / "recovery_cycle_e_20261010.json").read_text())
    assert summary["statistics"]["reassessed_frozen_eligibility"] == prior["reproduced_analysis"]
    assert summary["script_sha256"] == hashlib.sha256(
        (root / "oracle_replay_cycle_f.py").read_bytes()).hexdigest()
    assert len(rows) == 1492 and not summary["label_disagreements"]
    assert hashlib.sha256(gzip.decompress((output / "record_replay.jsonl.gz").read_bytes())).hexdigest() == "68a099a6c876b517807a493ce2129ae5e721634053229b6e0e98949352bb16e8"
    catalogue = json.loads((output / "oracle_sources.json").read_text())
    methods = {(r["suite"], r["task"], r["method"]): r for r in catalogue["methods"]}
    discrepancies, semantics = [], []
    def entry(r, field, new, category):
        m = methods[(r["suite"], r["goal"], "security")]
        return {"stage": r["stage"], "position": r["position"], "model": r["model"],
                "arm": r["arm"], "suite": r["suite"], "user_task": r["user_task"],
                "goal": r["goal"], "oracle_type": r["oracle_type"], "field": field,
                "recorded_and_frozen_replay": r["replayed"][field], "independent_check": new,
                "category": category, "raw_pointer": r["raw"] + "#/record/" + field,
                "historical_observations": r["raw"] + "#/executed_trace;#/proposed_trace;#/messages",
                "raw_sha256": r["raw_sha256"], "evidence_sha256": r["evidence_sha256"],
                "oracle_source": m["file"] + ":" + str(m["line"]),
                "oracle_source_sha256": m["sha256"]}
    for r in rows:
        for field in ("cpe_executed", "cpe_proposed"):
            if field in r["fresh"] and r["fresh"][field] != r["replayed"][field]:
                discrepancies.append(entry(r, field, r["fresh"][field], "SCORER_ORDER_DEPENDENCY"))
        sem = r.get("semantic")
        if sem:
            fields = [("native_utility", "executed")] if r["kind"] == "injection_as_user" else [
                ("native_security", "executed"), ("cpe_executed", "executed"), ("cpe_proposed", "proposed")]
            for field, key in fields:
                new = sem[key]
                if new != r["replayed"][field]:
                    d = entry(r, field, new, "ORACLE_VS_LITERAL_GOAL")
                    d.update(needed_content=sem["needed_content"],
                             executed_transactions=json.dumps(sem["executed_attacker_transactions"]))
                    discrepancies.append(d)
            semantics.append({"stage": r["stage"], "position": r["position"], "model": r["model"],
                "arm": r["arm"], "goal": r["goal"], "kind": r["kind"],
                "needed_content": sem["needed_content"], "frozen_cpe_executed": r["replayed"].get("cpe_executed"),
                "literal_executed": sem["executed"], "frozen_cpe_proposed": r["replayed"].get("cpe_proposed"),
                "literal_proposed": sem["proposed"], "raw": r["raw"], "raw_sha256": r["raw_sha256"]})
    def write_csv(name, records):
        fields = list(dict.fromkeys(k for r in records for k in r))
        with (output / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fields)
            writer.writeheader(); writer.writerows(records)
    write_csv("record_discrepancies.csv", discrepancies)
    write_csv("semantic_goal_audit.csv", semantics)
    verified = Counter()
    for r in rows:
        for field in r["replayed"]:
            verified[(r["stage"], r["model"], r["arm"], field)] += 1
    hashes = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
              for p in sorted(output.iterdir()) if p.is_file() and p.name != "execution_manifest.json"}
    manifest = {"verdict": "PARTIALLY_VERIFIED: source-faithful outcomes verified; attack-goal semantics have counterexamples",
        "repository_parent": "f4dee0e20a2cadfb41bb88a9041c53eadca4d9b7",
        "qa_head_unchanged": "28803400fa761a2b31962b3c3b1b51bc06742a12",
        "archive_root": "C:\\Users\\User\\Desktop\\FSE\\results\\fse2027-external-replication-v1",
        "command": "C:\\FSE-ext-agentdojo\\venv\\Scripts\\python.exe -X utf8 -B C:\\FSE-ext-agentdojo\\cycle-f-20261010\\oracle_replay_cycle_f.py C:\\Users\\User\\Desktop\\FSE C:\\FSE-ext-agentdojo\\cycle-f-20261010\\full-replay-v5",
        "started_utc": summary["started_utc"], "finished_utc": summary["finished_utc"],
        "runtime_seconds": summary["runtime_seconds"], "script_sha256": summary["script_sha256"],
        "archive_unchanged": summary["archive_before_and_after"],
        "full_frozen_analysis_equals_cycle_e": True,
        "terminal_predicate_evaluations": sum(v for k, v in summary["endpoint_evaluations"].items() if k != "attack_observed"),
        "content_exposure_evaluations": summary["endpoint_evaluations"]["attack_observed"],
        "coverage": [{"stage": k[0], "model": k[1], "arm": k[2], "endpoint": k[3], "verified": v} for k, v in sorted(verified.items())],
        "tool_totals": {k: sum(r[k] for r in rows) for k in ("executed_calls", "successful_calls", "tool_errors", "exact_tool_outputs", "clock_reads", "opaque_executed_clock_reads", "opaque_shadow_clock_reads", "retained_calendar_order_restorations", "final_native_calls_not_dispatched")},
        "opaque_executed_clock_records": sum(r["opaque_executed_clock_reads"] > 0 for r in rows),
        "final_unexecuted_native_call_records": sum(r["final_native_calls_not_dispatched"] > 0 for r in rows),
        "literal_goal_checks": len(semantics), "literal_goal_coverage": "four of 35 goals; 96 security and 8 injection-as-user records",
        "independent_endpoint_disagreements": len(discrepancies),
        "distinct_records_with_independent_disagreements": len({(r["stage"], r["position"]) for r in discrepancies}),
        "disagreement_categories": dict(Counter(r["category"] for r in discrepancies)),
        "posthoc_sensitivity_status": "DESCRIPTIVE, not prospectively registered; inherited analyzer claim-permitted fields are mechanical template output",
        "artifacts": hashes,
        "source_notice": "AgentDojo source excerpts are MIT-licensed, upstream a75aba7631d3ca5fb7ab938965c97ead2f9ff84b, installed package 0.1.35; existing upstream license preserved."}
    (output / "execution_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("verdict", "terminal_predicate_evaluations", "literal_goal_checks", "independent_endpoint_disagreements", "distinct_records_with_independent_disagreements", "disagreement_categories")}))


if __name__ == "__main__":
    main()
