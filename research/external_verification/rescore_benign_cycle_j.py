"""Correct only affected saved immutable contexts; zero new tool replay."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import time
from collections import Counter

from benign_construct_cycle_j import digest, require
from benign_construct_cycle_j_v2 import affected, evaluate


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    for name in ("prior-run", "spec", "addendum", "read-boundary", "output"):
        ap.add_argument("--" + name, type=pathlib.Path, required=True)
    for name in ("spec-sha256", "addendum-sha256", "boundary-sha256"):
        ap.add_argument("--" + name, required=True)
    args = ap.parse_args();started = dt.datetime.now(dt.timezone.utc).isoformat();tick = time.perf_counter()
    require(not args.output.exists(), "fresh rescore output required")
    require(sha(args.spec) == args.spec_sha256 and sha(args.addendum) == args.addendum_sha256 and sha(args.read_boundary) == args.boundary_sha256, "frozen rule hash differs")
    summary = read(args.prior_run / "execution_summary.json")
    bound = {args.spec: args.spec_sha256, args.addendum: args.addendum_sha256, args.read_boundary: args.boundary_sha256,
             args.prior_run / "execution_summary.json": sha(args.prior_run / "execution_summary.json")}
    for name in ("record_audit.jsonl.gz", "private_contexts_DO_NOT_PUBLISH.jsonl.gz", "frozen_population.json"):
        path = args.prior_run / name;require(sha(path) == summary["artifact_sha256"][name], "saved immutable context artifact differs")
        bound[path] = sha(path)
    for path, expected in summary["input_files_before_after"].items():
        require(sha(pathlib.Path(path)) == expected, "original bound input differs before targeted rescore")
    spec = read(args.spec)
    records = [json.loads(l) for l in gzip.decompress((args.prior_run / "record_audit.jsonl.gz").read_bytes()).decode().splitlines()]
    private = {r["pointer"]: r["contexts"] for r in (json.loads(l) for l in gzip.decompress((args.prior_run / "private_contexts_DO_NOT_PUBLISH.jsonl.gz").read_bytes()).decode().splitlines())}
    new = copy.deepcopy(records);differences, checked, labels = [], [], Counter()
    unaffected_checks = 0
    for record in new:
        contexts = private[record["raw_pointer"]]
        if not any(affected(c, spec["rules"][c["goal"]]) for c in contexts):
            for context in contexts:
                test = evaluate(context, spec["rules"][context["goal"]])
                require(test["semantic"] is record["decisions"][context["endpoint"]]["semantic"], "unaffected label unexpectedly changes")
                unaffected_checks += 1
            record["final_rubric_addendum_sha256"] = args.addendum_sha256
            record["read_boundary_sha256"] = args.boundary_sha256
            continue
        for context in contexts:
            endpoint = context["endpoint"];before = copy.deepcopy(record["decisions"][endpoint])
            after = evaluate(context, spec["rules"][context["goal"]])
            record["decisions"][endpoint] = after
            checked.append((context, copy.deepcopy(after)))
            differences.append({"raw_pointer": record["raw_pointer"], "raw_sha256": record["raw_sha256"], "evidence_sha256": record["evidence_sha256"],
                                "goal": record["goal"], "model": record["model"], "arm": record["arm"], "endpoint": endpoint,
                                "old_excluded_V1_decision": before, "new_V2_1_decision": after, "label_changed": before["semantic"] is not after["semantic"],
                                "source_native_utility": record["native_utility"] if endpoint == "executed" else None})
        record["final_rubric_addendum_sha256"] = args.addendum_sha256
        record["read_boundary_sha256"] = args.boundary_sha256
    for context, result in reversed(checked):
        require(evaluate(context, spec["rules"][context["goal"]]) == result, "corrected record/endpoint order changes result")
    for r in new:
        for endpoint, d in r["decisions"].items():
            labels[endpoint + ":" + str(d["semantic"])] += 1
    require(all(sha(p) == h for p, h in bound.items()), "saved inputs changed during rescore")
    for path, expected in summary["input_files_before_after"].items():
        require(sha(pathlib.Path(path)) == expected, "original input changed during rescore")
    args.output.mkdir()
    with gzip.GzipFile(filename=str(args.output / "record_audit.jsonl.gz"), mode="wb", mtime=0) as f:
        for r in new:
            f.write((json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n").encode())
    (args.output / "differential_ledger.json").write_text(json.dumps(differences, indent=2) + "\n", encoding="utf-8")
    result = {"cycle": "J_CORRECTED_RESCORING", "version": "V2.1", "started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "runtime_seconds": time.perf_counter() - tick, "original_records_retained": len(new), "affected_records_rescored": len(checked)//2,
              "affected_contexts_rescored": len(checked), "order_checks": len(checked), "unaffected_context_consistency_checks": unaffected_checks,
              "labels": dict(labels), "new_tool_calls": 0,
              "new_provider_calls": 0, "original_oracle_calls": 0, "human_reviews": 0, "rubric_sha256": args.spec_sha256,
              "addendum_sha256": args.addendum_sha256, "read_boundary_sha256": args.boundary_sha256,
              "code_sha256": sha(pathlib.Path(__file__)), "corrected_evaluator_sha256": sha(pathlib.Path(__file__).with_name("benign_construct_cycle_j_v2.py")),
              "saved_artifacts_before_after": {str(p): h for p, h in bound.items()},
              "artifact_sha256": {p.name: sha(p) for p in args.output.iterdir() if p.is_file()},
              "V1_scoring_excluded": "Participant order bug and unclassified read bookkeeping; V1 restoration/provenance remains valid."}
    (args.output / "execution_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("saved_artifacts_before_after", "artifact_sha256")}))


if __name__ == "__main__":
    main()
