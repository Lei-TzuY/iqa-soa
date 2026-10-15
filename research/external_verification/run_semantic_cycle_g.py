"""Restore new Cycle G observations only; never execute original scoring logic.

Requires the original desktop archive/runtime and immutable Cycle F replay input.
Only hashes, controlled pointers and semantic decisions are exported. Restored
private message contents stay in process memory. No inference or network calls.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import gzip
import hashlib
import importlib.util
import io
import json
import pathlib
import socket
import sys
import time
import types
from collections import Counter

from semantic_cycle_g import RUBRIC_SHA256, audit_context, digest


def require(ok, text):
    if not ok:
        raise ValueError(text)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def compact_event(before, after, fn):
    """Retain all grader-required projections plus hashes of full snapshots."""
    b, a = {}, {}
    if fn in ("send_email", "delete_email"):
        old, new = before["inbox"]["emails"], after["inbox"]["emails"]
        b["inbox"] = {"emails": {k: None for k in old}}
        a["inbox"] = {"emails": {k: new[k] if k not in old else None for k in new}}
        if fn == "send_email" and "cloud_drive" in before:
            b["cloud_drive"] = {"files": before["cloud_drive"]["files"]}
    if fn == "delete_file":
        b["cloud_drive"] = {"files": {k: None for k in before["cloud_drive"]["files"]}}
        a["cloud_drive"] = {"files": {k: None for k in after["cloud_drive"]["files"]}}
    if fn == "create_calendar_event":
        old, new = before["calendar"]["events"], after["calendar"]["events"]
        b["calendar"] = {"events": {k: None for k in old}}
        a["calendar"] = {"events": {k: new[k] if k not in old else None for k in new}}
    if fn == "reserve_hotel":
        a["reservation"] = after["reservation"]
    if fn == "send_money":
        ids = {t["id"] for t in before["bank_account"]["transactions"]}
        b["bank_account"] = {"transactions": [{"id": k} for k in ids]}
        a["bank_account"] = {"transactions": [t for t in after["bank_account"]["transactions"] if t["id"] not in ids]}
    if fn == "send_direct_message":
        old, new = before["slack"]["user_inbox"], after["slack"]["user_inbox"]
        b["slack"] = {"user_inbox": {u: [None]*len(v) for u,v in old.items()}}
        a["slack"] = {"user_inbox": {u: [None]*len(old.get(u, [])) + v[len(old.get(u, [])):] for u,v in new.items()}}
    if fn == "post_webpage":
        a["web"] = {"web_content": after["web"]["web_content"]}
    if fn in ("invite_user_to_slack", "add_user_to_channel", "remove_user_from_slack"):
        for obj, raw in ((b, before), (a, after)):
            obj["slack"] = {k:raw["slack"][k] for k in ("users", "user_channels")}
    return b, a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", type=pathlib.Path)
    ap.add_argument("cycle_f_output", type=pathlib.Path)
    ap.add_argument("output", type=pathlib.Path)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    repo, output = args.repo_root.resolve(), args.output.resolve()
    require(not output.exists() and repo not in output.parents, "new isolated output outside original repo required")
    own = pathlib.Path(__file__).resolve().parent
    rubric_path = own / "semantic_rubric_v2.json"
    require(file_sha(rubric_path) == RUBRIC_SHA256, "frozen rubric hash differs")
    rubric = read_json(rubric_path)
    selected = {g["suite"] + "/" + g["goal_id"] for g in rubric["goals"] if g["scope"] == "NEW_REMAINING_31"}
    require(len(selected) == 31, "remaining-goal population differs")
    helper_path = own / "oracle_replay_cycle_f.py"
    require(file_sha(helper_path) == "942104d6e2d24cca6ed8b05b3a1c3a12c6c85a992a025a6f863668809e764204", "Cycle F helper changed")
    sys.dont_write_bytecode = True
    def deny(*a, **k):
        raise RuntimeError("Cycle G network/scoring operation denied")
    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
    def audit(event, params):
        if event.startswith("socket.") and event != "socket.__new__":
            raise RuntimeError("network denied")
        if event == "open":
            p, mode, flags = params
            writing = (isinstance(mode, str) and any(x in mode for x in "wax+")) or (flags & 0x703 != 0)
            if writing and isinstance(p, (str, bytes)):
                require(output in pathlib.Path(p).resolve().parents, "write outside isolated output")
        if event in ("os.remove", "os.rename", "os.rmdir", "subprocess.Popen", "os.system"):
            raise RuntimeError("mutation/process denied")
        if event == "os.mkdir":
            p = pathlib.Path(params[0]).resolve()
            require(p == output or output in p.parents, "mkdir outside isolated output")
    sys.addaudithook(audit)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    tick = time.perf_counter()
    spec = importlib.util.spec_from_file_location("cycle_f_helpers_only", helper_path)
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    sys.path[:0] = [str(repo / "scripts"), str(repo / "src")]
    from agentdojo.task_suite.load_suites import get_suites
    from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
    from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
    from agentdojo.types import get_text_content_as_str
    from agentdojo.default_suites.v1.tools import email_client, cloud_drive_client
    from fse2027_ext.freeze import verify, collect
    import yaml
    archive = repo / "results" / "fse2027-external-replication-v1"
    verify(repo, read_json(archive / "freeze-manifest.json"))
    frozen_before = collect(repo)
    prior_path = args.cycle_f_output / "record_replay.jsonl"
    require(file_sha(prior_path) == "68a099a6c876b517807a493ce2129ae5e721634053229b6e0e98949352bb16e8", "retained Cycle F record input differs")
    prior = {(r["stage"],r["position"]):r for r in read_lines(prior_path)}
    suites = get_suites("v1.2.2")
    for s in suites.values():
        for task in list(s.injection_tasks.values()) + list(s.user_tasks.values()):
            for name in ("security", "security_from_traces", "utility", "utility_from_traces"):
                if hasattr(type(task), name):
                    setattr(type(task), name, deny)
    contexts, records, binding = [], [], Counter()
    hashes = {}
    original_datetime = dt.datetime
    for stage in ("qualification", "confirmatory"):
        for row in read_lines(archive / stage / "runs.jsonl"):
            key = row["suite"] + "/" + (row["injection_task"] or "")
            if key not in selected:
                continue
            if args.limit is not None and len(records) >= args.limit:
                continue
            cell = archive / stage / "cells" / f"{row['position']:05d}-{row['model']}-{row['arm']}"
            old = prior[(stage, row["position"])]
            for filename, field in (("raw.json", "raw_sha256"), ("evidence.jsonl", "evidence_sha256")):
                fp = cell / filename
                require(file_sha(fp) == old[field], "historical input hash changed")
                hashes[str(fp)] = old[field]
            raw = read_json(cell / "raw.json")
            require(raw["record"] == row and row["pipeline_runs"] == 1, "record/history identity differs")
            s = suites[row["suite"]]
            env = s.load_and_inject_default_environment(raw["injections"])
            if row["user_task"]:
                env = s.user_tasks[row["user_task"]].init_environment(env)
            initial = h.portable(env)
            require(h.digest(initial) == old["initial_state_sha256"], "initial state differs from Cycle F")
            shadow = copy.deepcopy(env)
            native = [FunctionCall.model_validate(c) for m in raw["messages"] if m["role"] == "assistant" for c in m.get("tool_calls") or []]
            tool_msgs = [m for m in raw["messages"] if m["role"] == "tool"]
            evidence = {e["evidence_id"]:e for e in read_lines(cell / "evidence.jsonl")}
            require(len(tool_msgs) == len(raw["proposals"]) <= len(native), "incomplete original history")
            boundary = native[:len(tool_msgs)]
            bank = h.clocks_from_outputs(raw, yaml)
            ac, pc = h.HistoricalClock(bank, True), h.HistoricalClock({}, False)
            class ActualTime(original_datetime):
                @classmethod
                def now(cls, tz=None):
                    return ac.now(tz)
            class ProposedTime(original_datetime):
                @classmethod
                def now(cls, tz=None):
                    return pc.now(tz)
            actual_events, proposed_events = [], []
            runtime, sruntime = FunctionsRuntime(s.tools), FunctionsRuntime(s.tools)
            dispatched, proposed = [], []
            for index, (call, proposal, msg) in enumerate(zip(boundary, raw["proposals"], tool_msgs)):
                require(msg["tool_call"] == call.model_dump(), "call/result pointer mismatch")
                if call.function not in runtime.functions:
                    continue
                proposed.append(call.model_dump())
                e = evidence[proposal["evidence_id"]]
                require(e["qa_mode"] == row["arm"] and bool(e["executed"]) == bool(proposal["executed"]), "arm/dispatch evidence mismatch")
                for module in (email_client, cloud_drive_client):
                    module.datetime = types.SimpleNamespace(datetime=ProposedTime)
                pc.bind(call, shadow)
                before = h.portable(shadow)
                sr, se = sruntime.run_function(shadow, call.function, copy.deepcopy(call.args))
                after = h.portable(shadow)
                cb, ca = compact_event(before, after, call.function)
                proposed_events.append({"index":index,"function":call.function,"arguments":copy.deepcopy(call.args),
                    "error":se,"before":cb,"after":ca,"observed_result":h.portable(sr),
                    "before_full_sha256":h.digest(before),"after_full_sha256":h.digest(after)})
                if not proposal["executed"]:
                    binding["blocked_proposals"] += 1
                    continue
                actual = e.get("executed_action") if row["arm"] == "full" else None
                if row["arm"] == "full":
                    require(actual is not None, "FULL authorized action missing")
                    fn, a = actual["resource"].split("/")[-1], actual["arguments"]
                else:
                    fn, a = call.function, call.args
                executed_call = FunctionCall(function=fn, args=copy.deepcopy(a), id=call.id)
                for module in (email_client, cloud_drive_client):
                    module.datetime = types.SimpleNamespace(datetime=ActualTime)
                text = get_text_content_as_str(msg["content"])
                ac.bind(executed_call, env, text)
                before = h.portable(env)
                observed_result, error = runtime.run_function(env, fn, copy.deepcopy(a))
                h.restore_calendar_order(observed_result, text, env, yaml)
                after = h.portable(env)
                require(error == msg["error"] == e.get("error"), "historical tool error mismatch")
                if proposal["disposition"] != "EXECUTED_RESULT_WITHHELD":
                    require(tool_result_to_str(observed_result) == text, "historical tool output differs")
                    binding["exact_historical_outputs"] += 1
                binding["dispatched"] += 1
                binding["tool_errors"] += error is not None
                require((error is None) == bool(e.get("success")), "historical success field mismatch")
                cb, ca = compact_event(before, after, fn)
                actual_events.append({"index":index,"function":fn,"arguments":copy.deepcopy(a),"error":error,
                    "before":cb,"after":ca,"observed_result":h.portable(observed_result),
                    "before_full_sha256":h.digest(before),"after_full_sha256":h.digest(after)})
                dispatched.append(call.model_dump())
            for module in (email_client, cloud_drive_client):
                module.datetime = dt
            require(dispatched == raw["executed_trace"] and proposed == raw["proposed_trace"], "retained dispatch/proposal history differs")
            final = h.portable(env)
            require(h.digest(final) == old["post_execution_projection_sha256"], "actual final state differs from Cycle F projection")
            require(get_text_content_as_str(raw["messages"][-1]["content"] or []) == raw["final_output_text"], "final text differs")
            ctxs = {"executed":{"initial":initial,"final":final,"events":actual_events,"final_text":raw["final_output_text"]}}
            if not (row["suite"] == "travel" and row["injection_task"] == "injection_task_6"):
                ctxs["proposed"] = {"initial":initial,"final":h.portable(shadow),"events":proposed_events,"final_text":raw["final_output_text"]}
            evaluated = {endpoint:audit_context(c, row["suite"],row["injection_task"]) for endpoint,c in ctxs.items()}
            reversed_endpoints = {ep:audit_context(c,row["suite"],row["injection_task"]) for ep,c in reversed(list(ctxs.items()))}
            require(evaluated == reversed_endpoints, "endpoint order dependence")
            for endpoint, c in ctxs.items():
                contexts.append((len(records), endpoint, c, row["suite"], row["injection_task"]))
            # Recorded outcomes are accessed only after semantic decisions.
            fields = ("native_security","cpe_executed","cpe_proposed") if row["kind"] == "security" else ("native_utility",)
            rec = {"stage":stage,"position":row["position"],"model":row["model"],"arm":row["arm"],
                "suite":row["suite"],"goal":row["injection_task"],"kind":row["kind"],"user_task":row["user_task"],
                "benchmark_version":"v1.2.2","rubric_id":"cycle-g-v2/"+key,"rubric_sha256":RUBRIC_SHA256,
                "raw_pointer":old["raw"],"raw_sha256":old["raw_sha256"],"evidence_sha256":old["evidence_sha256"],
                "recorded":{k:row.get(k) for k in fields},"semantic":evaluated,
                "execution_status":"EXECUTED" if actual_events else "BLOCKED" if proposed_events else "UNOBSERVABLE",
                "proposal_status":"PROPOSED" if proposed_events else "UNOBSERVABLE",
                "dispatched_calls":len(actual_events),"proposed_calls":len(proposed_events),
                "tool_errors":sum(e["error"] is not None for e in actual_events),
                "opaque_executed_clock_reads":ac.opaque_reads,"opaque_proposed_clock_reads":pc.opaque_reads,
                "terminal_native_calls_not_dispatched":len(native)-len(boundary),
                "initial_projection_sha256":h.digest(initial),"final_projection_sha256":h.digest(final),
                "controlled_evidence_pointers":[old["raw"]+"#/messages",old["raw"]+"#/executed_trace",old["raw"]+"#/proposed_trace"],
                "endpoint_order_invariant":True}
            records.append(rec)
            if len(records) % 100 == 0:
                print(json.dumps({"construct_records":len(records),"elapsed_seconds":time.perf_counter()-tick}),flush=True)
    reverse_checks = 0
    for index, endpoint, c, suite, goal in reversed(contexts):
        require(audit_context(c,suite,goal) == records[index]["semantic"][endpoint], "record/endpoint reverse-order dependence")
        reverse_checks += 1
    for fp, expected in hashes.items():
        require(file_sha(pathlib.Path(fp)) == expected, "original input changed during audit")
    verify(repo, read_json(archive / "freeze-manifest.json"))
    require(collect(repo) == frozen_before, "frozen original source changed")
    require(file_sha(rubric_path) == RUBRIC_SHA256, "rubric changed during evaluation")
    summary = {"audit":"Cycle G independent construct evaluation", "rubric_sha256":RUBRIC_SHA256,
        "started_utc":started,"finished_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_seconds":time.perf_counter()-tick,"python":sys.version,"records":len(records),
        "full_new_goal_population":args.limit is None,"reverse_order_context_checks":reverse_checks,
        "independent_oracle_calls":0,"new_model_calls":0,"network_calls":0,"binding":dict(binding),
        "original_input_files_before_after":len(hashes),"original_input_hash_map_sha256":h.digest(hashes),
        "source_hashes":{"runner":file_sha(pathlib.Path(__file__)),"evaluator":file_sha(own/"semantic_cycle_g.py"),
        "cycle_f_helpers":file_sha(helper_path),"cycle_f_records":file_sha(prior_path)},
        "frozen_source_provenance":frozen_before,
        "limitations":"Machine semantic labels, not human adjudication. Explicit ambiguity preserved. Shared deterministic mock replay only restores historical observations; proposals are hypothetical."}
    output.mkdir()
    body = "".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in records).encode()
    (output / "construct_records.jsonl.gz").write_bytes(gzip.compress(body,mtime=0))
    (output / "execution_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(output),"records":len(records),"runtime_seconds":summary["runtime_seconds"],
        "reverse_order_context_checks":reverse_checks,"binding":dict(binding),
        "artifacts":{p.name:{"sha256":file_sha(p),"bytes":p.stat().st_size} for p in output.iterdir()}}),flush=True)


if __name__ == "__main__":
    main()
