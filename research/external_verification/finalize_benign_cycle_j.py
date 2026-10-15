"""Final targeted web/finite-output checks on retained immutable J contexts."""
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
from benign_construct_cycle_j_v2 import evaluate


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    for name in ("repo", "initial-run", "prior-run", "spec", "web-rule", "field-rule", "timeline-rule", "output"):
        ap.add_argument("--" + name, type=pathlib.Path, required=True)
    for name in ("web-sha256", "field-sha256", "timeline-sha256"):
        ap.add_argument("--" + name, required=True)
    args = ap.parse_args();started = dt.datetime.now(dt.timezone.utc).isoformat();tick = time.perf_counter()
    require(not args.output.exists(), "fresh output required")
    bound = {args.web_rule: args.web_sha256, args.field_rule: args.field_sha256, args.timeline_rule: args.timeline_sha256}
    require(all(sha(p) == h for p, h in bound.items()), "frozen new criterion differs")
    initial_summary = read(args.initial_run / "execution_summary.json")
    prior_summary = read(args.prior_run / "execution_summary.json")
    for name, folder, manifest in (("private_contexts_DO_NOT_PUBLISH.jsonl.gz", args.initial_run, initial_summary),
                                   ("record_audit.jsonl.gz", args.prior_run, prior_summary)):
        path = folder / name;require(sha(path) == manifest["artifact_sha256"][name], "saved artifact differs");bound[path] = sha(path)
    for path, h in initial_summary["input_files_before_after"].items():
        require(sha(pathlib.Path(path)) == h, "bound original input differs")
    spec = read(args.spec)
    records = [json.loads(l) for l in gzip.decompress((args.prior_run / "record_audit.jsonl.gz").read_bytes()).decode().splitlines()]
    contexts = {r["pointer"]: r["contexts"] for r in (json.loads(l) for l in gzip.decompress((args.initial_run / "private_contexts_DO_NOT_PUBLISH.jsonl.gz").read_bytes()).decode().splitlines())}
    chosen = {"slack/user_task_0", "travel/user_task_1", "travel/user_task_3", "travel/user_task_4"}
    differences, checked, provenance = [], [], []
    for r in records:
        if r["goal"] not in chosen:
            continue
        pair = contexts[r["raw_pointer"]]
        if r["goal"].startswith("travel/"):
            p = args.repo / "results/fse2027-external-replication-v1" / r["raw_pointer"]
            require(sha(p) == r["raw_sha256"], "original timeline raw hash differs");bound[p] = r["raw_sha256"]
            raw = read(p)
            timeline = [{"message_ordinal": i, "text": "\n".join(b["content"] for b in m.get("content") or [] if b["type"] == "text")}
                        for i, m in enumerate(raw["messages"]) if m["role"] == "assistant"]
            tool_ordinals = [i for i, m in enumerate(raw["messages"]) if m["role"] == "tool"]
            pair[0]["assistant_timeline"] = timeline
            pair[1]["assistant_timeline"] = None
            for c in pair:
                for a in c["actions"]:
                    a["tool_message_ordinal"] = tool_ordinals[a["ordinal"]]
            provenance.append({"raw_pointer": r["raw_pointer"], "raw_sha256": r["raw_sha256"], "evidence_sha256": r["evidence_sha256"],
                               "goal": r["goal"], "blocks": [{"ordinal": m["message_ordinal"], "sha256": hashlib.sha256(m["text"].encode()).hexdigest(), "characters": len(m["text"])} for m in timeline]})
        for c in pair:
            before = copy.deepcopy(r["decisions"][c["endpoint"]]);after = evaluate(c, spec["rules"][r["goal"]])
            r["decisions"][c["endpoint"]] = after;checked.append((c, copy.deepcopy(after)))
            differences.append({"raw_pointer": r["raw_pointer"], "raw_sha256": r["raw_sha256"], "goal": r["goal"], "endpoint": c["endpoint"],
                                "before": before, "after": after, "label_changed": before["semantic"] is not after["semantic"]})
        r["final_observation_rules"] = {"web": args.web_sha256, "fields": args.field_sha256, "timeline": args.timeline_sha256}
    require(len(checked) == 32, "only 16 records / 32 contexts permitted")
    for c, result in reversed(checked):
        require(evaluate(c, spec["rules"][c["goal"]]) == result, "final scoring order changes result")
    require(all(sha(p) == h for p, h in bound.items()), "input changed during final targeted check")
    for path, h in initial_summary["input_files_before_after"].items():
        require(sha(pathlib.Path(path)) == h, "original input changed")
    args.output.mkdir()
    def jsonfile(name, obj):
        (args.output/name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    with gzip.GzipFile(filename=str(args.output/"record_audit.jsonl.gz"), mode="wb", mtime=0) as f:
        for r in records:f.write((json.dumps(r, sort_keys=True, ensure_ascii=False)+"\n").encode())
    with gzip.GzipFile(filename=str(args.output/"private_final_contexts_DO_NOT_PUBLISH.jsonl.gz"), mode="wb", mtime=0) as f:
        for pointer, cs in contexts.items():f.write((json.dumps({"pointer": pointer,"contexts":cs},sort_keys=True,ensure_ascii=False)+"\n").encode())
    jsonfile("final_differential.json", differences);jsonfile("assistant_text_provenance.json",provenance)
    labels = Counter(endpoint+":"+str(d["semantic"]) for r in records for endpoint,d in r["decisions"].items())
    summary = {"cycle":"J_FINAL_V2_2_AND_TIMELINE","started_utc":started,"finished_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"runtime_seconds":time.perf_counter()-tick,
               "original_records_retained":144,"targeted_records":16,"targeted_contexts":32,"order_checks":32,"labels":dict(labels),
               "web_rule_sha256":args.web_sha256,"field_rule_sha256":args.field_sha256,"timeline_rule_sha256":args.timeline_sha256,
               "code_sha256":sha(pathlib.Path(__file__)),"evaluator_sha256":sha(pathlib.Path(__file__).with_name("benign_construct_cycle_j_v2.py")),
               "bound_inputs_before_after":{str(p):h for p,h in bound.items()},"new_tool_calls":0,"provider_calls":0,"original_oracle_calls":0,"human_reviews":0,
               "artifact_sha256":{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}}
    jsonfile("execution_summary.json", summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ("bound_inputs_before_after","artifact_sha256")}))


if __name__ == "__main__":
    main()
