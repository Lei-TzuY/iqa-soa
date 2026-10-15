"""Targeted offline restoration of 128 new Cycle K benign observations.

No model calls or benchmark verdict functions; only deterministic historical
mock tools, bound clock/order restoration, and independent semantic criteria.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import gzip
import hashlib
import importlib.util
import inspect
import json
import pathlib
import socket
import sys
import time
import types
from collections import Counter, defaultdict

from benign_construct_cycle_j import changed_paths, digest, minimized_event, require
from benign_construct_cycle_k import evaluate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def lines(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l]


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    for name in ("repo", "spec", "definitions", "f-index", "f-helper", "output"):
        ap.add_argument("--" + name, type=pathlib.Path, required=True)
    ap.add_argument("--spec-sha256", required=True)
    ap.add_argument("--code-sha256", required=True)
    ap.add_argument("--evaluator-sha256", required=True)
    ap.add_argument("--common-helper-sha256", required=True)
    args = ap.parse_args()
    output, repo = args.output.resolve(), args.repo.resolve()
    require(not output.exists() and repo not in output.parents, "fresh isolated output required")
    require(sha(args.spec) == args.spec_sha256, "frozen rubric differs")
    spec = read(args.spec); binding = spec["source_binding"]
    bound = {args.spec: args.spec_sha256, args.definitions: binding["task_definitions_sha256"],
             args.f_index: binding["f_record_index_sha256"], args.f_helper: binding["f_helper_sha256"],
             pathlib.Path(__file__): args.code_sha256,
             pathlib.Path(__file__).with_name("benign_construct_cycle_k.py"): args.evaluator_sha256,
             pathlib.Path(__file__).with_name("benign_construct_cycle_j.py"): args.common_helper_sha256}
    require(all(sha(p) == h for p, h in bound.items()), "bound source input differs")
    sys.dont_write_bytecode = True
    def deny(*_args, **_kwargs):
        raise RuntimeError("original oracle/network denied")
    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
    def guard(event, params):
        if event.startswith("socket.") and event != "socket.__new__":
            raise RuntimeError("network denied")
        if event == "open":
            path, mode, flags = params
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (flags & 0x703 != 0)
            if writing and isinstance(path, (str, bytes)):
                require(output in pathlib.Path(path).resolve().parents, "write outside isolated output")
        if event in ("os.remove", "os.rename", "os.rmdir", "subprocess.Popen", "os.system"):
            raise RuntimeError("external mutation denied")
        if event == "os.mkdir":
            path = pathlib.Path(params[0]).resolve()
            require(path == output or output in path.parents, "mkdir outside output")
    sys.addaudithook(guard)
    started, tick = dt.datetime.now(dt.timezone.utc).isoformat(), time.perf_counter()
    module_spec = importlib.util.spec_from_file_location("bound_F_restoration_only", args.f_helper)
    helper = importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(helper)
    sys.path[:0] = [str(repo / "src"), str(repo / "scripts")]
    import agentdojo
    import yaml
    from agentdojo.task_suite.load_suites import get_suites
    from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
    from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
    from agentdojo.types import get_text_content_as_str
    from agentdojo.default_suites.v1.tools import email_client, cloud_drive_client
    from fse2027_ext.freeze import collect, verify
    package = pathlib.Path(agentdojo.__file__).parent
    source_before = helper.tree(package)
    require(source_before == binding["AgentDojo_inventory"], "installed AgentDojo source differs")
    for file, expected in binding["tool_sha256"].items():
        require(sha(package / "default_suites/v1/tools" / file) == expected, "atomic tool source differs")
    suites = get_suites("v1.2.2")
    for definition in read(args.definitions)["definitions"]:
        sn, task_id = definition["key"].split("/");task = suites[sn].user_tasks[task_id]
        require(task.PROMPT == definition["objective"], "version-resolved task prompt differs")
        require(hashlib.sha256(inspect.getsource(type(task)).encode()).hexdigest() == definition["class_sha256"], "task class source differs")
    for suite in suites.values():
        for task in list(suite.user_tasks.values()) + list(suite.injection_tasks.values()):
            for method in ("utility", "utility_from_traces", "security", "security_from_traces"):
                if hasattr(type(task), method):
                    setattr(type(task), method, deny)
    archive = repo / "results/fse2027-external-replication-v1"
    verify(repo, read(archive / "freeze-manifest.json"));frozen_before = collect(repo)
    for stage, h in binding["summary_sha256"].items():
        bound[archive / stage / "runs.jsonl"] = h
    require(all(sha(p) == h for p, h in bound.items()), "original summary differs")
    summary = lines(archive / "confirmatory/runs.jsonl")
    population = [r for r in summary if r["kind"] == "benign"]
    require(len(population) == 388, "388 benign observations required")
    groups = defaultdict(list)
    for row in population:
        groups[row["model"], row["pair_id"]].append(row)
    require(len(groups) == 194 and all(len(g) == 2 and {r['arm'] for r in g} == {'off', 'full'} for g in groups.values()), "194 paired observations required")
    require(Counter(r["model"] for r in population) == {"qwen": 194, "mistral": 194}, "equal model strata differ")
    require(all(len({(r['suite'],r['user_task']) for r in g}) == 1 for g in groups.values()), "pair task identity differs")
    selected = [r for r in population if r["suite"] + "/" + r["user_task"] in spec["rules"]]
    require(len(selected) == 128 and Counter(r["suite"] + "/" + r["user_task"] for r in selected) == {k: 4 for k in spec["rules"]}, "frozen 32-task/128-record selection differs")
    index = {(r["stage"], r["position"]): r for r in lines(args.f_index)}
    records, private, count = [], [], Counter()
    original_datetime = dt.datetime
    immutable_contexts = []
    for row in selected:
        goal = row["suite"] + "/" + row["user_task"]
        old = index["confirmatory", row["position"]]
        cell = archive / "confirmatory/cells" / f"{row['position']:05d}-{row['model']}-{row['arm']}"
        for name, field in (("raw.json", "raw_sha256"), ("evidence.jsonl", "evidence_sha256")):
            path = cell / name;require(sha(path) == old[field], "original selected input differs")
            bound[path] = old[field]
        raw = read(cell / "raw.json")
        require(raw["record"] == row and not raw["injections"] and row["pipeline_runs"] == 1, "original benign record boundary differs")
        suite = suites[row["suite"]]
        actual = suite.user_tasks[row["user_task"]].init_environment(suite.load_and_inject_default_environment({}))
        initial = helper.portable(actual);require(digest(initial) == old["initial_state_sha256"], "initial state differs from bound F index")
        shadow = copy.deepcopy(actual)
        named_calls = [(mi, FunctionCall.model_validate(c)) for mi,m in enumerate(raw["messages"]) if m["role"] == "assistant" for c in m.get("tool_calls") or []]
        native = [call for _,call in named_calls]
        assistant_texts = [{"message_ordinal":mi,"text":"\n".join(b["content"] for b in m.get("content") or [] if b.get("type")=="text" and b.get("content") is not None),"is_final":mi==len(raw["messages"])-1}
                           for mi,m in enumerate(raw["messages"]) if m["role"]=="assistant"]
        only_text = "\n".join(b["content"] for b in raw["messages"][-1].get("content") or [] if b.get("type")=="text" and b.get("content") is not None)
        require(only_text == raw["final_output_text"], "final output contains non-text blocks or extraction differs")
        messages = [m for m in raw["messages"] if m["role"] == "tool"]
        require(len(messages) == len(raw["proposals"]) <= len(native), "incomplete call/result history")
        gateway = {e["evidence_id"]: e for e in lines(cell / "evidence.jsonl")}
        runtime, shadow_runtime = FunctionsRuntime(suite.tools), FunctionsRuntime(suite.tools)
        clock = helper.HistoricalClock(helper.clocks_from_outputs(raw, yaml), True)
        shadow_clock = helper.HistoricalClock({}, False)
        class BoundDatetime(original_datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.now(tz)
        class ShadowDatetime(original_datetime):
            @classmethod
            def now(cls, tz=None):
                return shadow_clock.now(tz)
        event_sets = {"executed": [], "proposed": []};dispatched = []
        for ordinal, (call, proposal, message) in enumerate(zip(native, raw["proposals"], messages)):
            require(message["tool_call"] == call.model_dump(), "call/result identity differs")
            if call.function not in runtime.functions:
                count["invalid_function_proposals"] += 1
                continue
            e = gateway[proposal["evidence_id"]]
            require(e["qa_mode"] == row["arm"] and bool(e["executed"]) == bool(proposal["executed"]), "arm/dispatch binding differs")
            modes = [("proposed", shadow, shadow_runtime, shadow_clock, ShadowDatetime, call)]
            if proposal["executed"]:
                authorized = e.get("executed_action") if row["arm"] == "full" else None
                require(row["arm"] != "full" or authorized is not None, "FULL actual arguments missing")
                fn, arguments = (authorized["resource"].split("/")[-1], authorized["arguments"]) if authorized else (call.function, call.args)
                actual_call = FunctionCall(function=fn, args=copy.deepcopy(arguments), id=call.id)
                modes.append(("executed", actual, runtime, clock, BoundDatetime, actual_call))
                dispatched.append(call.model_dump())
            else:
                count["blocked_original_proposals"] += 1
            for endpoint, state, engine, bound_clock, datetime_type, chosen in modes:
                for module in (email_client, cloud_drive_client):
                    module.datetime = types.SimpleNamespace(datetime=datetime_type)
                retained = get_text_content_as_str(message["content"])
                bound_clock.bind(chosen, state, retained if endpoint == "executed" else None)
                before = helper.portable(state)
                result, error = engine.run_function(state, chosen.function, copy.deepcopy(chosen.args))
                if endpoint == "executed" and helper.restore_calendar_order(result, retained, state, yaml):
                    count["retained_participant_order_restorations"] += 1
                after = helper.portable(state)
                output_binding = "HYPOTHETICAL_MOCK_OUTCOME_ONLY"
                if endpoint == "executed":
                    require(error == message["error"] == e.get("error") and (error is None) == bool(e.get("success")), "retained acceptance/error differs")
                    if proposal["disposition"] == "EXECUTED_RESULT_WITHHELD":
                        output_binding = "RECORDED_ACCEPTANCE_ATOMIC_STATE_OUTPUT_WITHHELD"
                        count["withheld_results"] += 1
                    else:
                        require(tool_result_to_str(result) == retained, "retained tool output differs")
                        count["exact_retained_tool_outputs"] += 1
                        output_binding = "EXACT_ORIGINAL_TOOL_RESULT_AND_STATE_TRANSITION"
                count[endpoint + "_calls"] += 1;count[endpoint + "_tool_errors"] += error is not None
                event_sets[endpoint].append({"ordinal": ordinal, "function": chosen.function, "args": copy.deepcopy(chosen.args), "accepted": error is None,
                                            "error": bool(error), "args_sha256": digest(chosen.args), "result_sha256": digest(helper.portable(result)),
                                            "before_sha256": digest(before), "after_sha256": digest(after), "changed_paths": changed_paths(before, after),
                                            "evidence_id": proposal["evidence_id"], "output_binding": output_binding, "source_message_ordinal":named_calls[ordinal][0]})
        for module in (email_client, cloud_drive_client):
            module.datetime = dt
        require(dispatched == raw["executed_trace"], "executed trace binding differs")
        final = helper.portable(actual)
        require(digest(final) == old["post_execution_projection_sha256"], "executed state differs from F post-dispatch projection")
        decisions = {}
        contexts = []
        for endpoint, state in (("executed", actual), ("proposed", shadow)):
            context = {"goal": goal, "initial": copy.deepcopy(initial), "final": helper.portable(state), "actions": event_sets[endpoint],
                       "final_text": raw["final_output_text"] if endpoint == "executed" else None, "endpoint": endpoint,
                       "objective": suite.user_tasks[row["user_task"]].PROMPT,
                       "assistant_texts": copy.deepcopy(assistant_texts) if endpoint=="executed" else []}
            before_hash = digest(context)
            decisions[endpoint] = evaluate(context, spec["rules"][goal])
            require(digest(context) == before_hash, "evaluator mutated context")
            contexts.append(context)
            immutable_contexts.append((copy.deepcopy(context), copy.deepcopy(decisions[endpoint])))
        for context in reversed(contexts):
            require(evaluate(context, spec["rules"][goal]) == decisions[context["endpoint"]], "endpoint evaluation order changes result")
        records.append({"stage": "confirmatory", "position": row["position"], "model": row["model"], "arm": row["arm"], "pair_id": row["pair_id"], "goal": goal,
                        "raw_pointer": old["raw"], "raw_sha256": old["raw_sha256"], "evidence_sha256": old["evidence_sha256"], "initial_sha256": digest(initial), "final_actual_sha256": digest(final),
                        "native_utility": row["native_utility"], "decisions": decisions, "rubric_sha256": args.spec_sha256,
                        "actual_events": [minimized_event(a) for a in event_sets["executed"]], "proposed_events": [minimized_event(a) for a in event_sets["proposed"]],
                        "final_text_sha256": hashlib.sha256(raw["final_output_text"].encode()).hexdigest(), "final_text_characters": len(raw["final_output_text"]),
                        "assistant_text_provenance": [{"message_ordinal":m["message_ordinal"],"is_final":m["is_final"],"text_sha256":hashlib.sha256(m["text"].encode()).hexdigest(),"characters":len(m["text"])} for m in assistant_texts],
                        "evidence_equivalence_sha256": digest({"goal":goal,"initial":initial,"final":final,"actions":[{k:a[k] for k in ("function","args","accepted","error","source_message_ordinal")} for a in event_sets["executed"]],"assistant_texts":assistant_texts}),
                        "terminal_calls_not_dispatched": len(native) - len(messages), "opaque_actual_clock_reads": clock.opaque_reads, "opaque_proposed_clock_reads": shadow_clock.opaque_reads})
        private.append({"pointer": old["raw"], "contexts": contexts})
    for context, wanted in reversed(immutable_contexts):
        require(evaluate(context, spec["rules"][context["goal"]]) == wanted, "record evaluation order changes result")
    require(all(sha(p) == h for p, h in bound.items()), "original input changed during targeted audit")
    require(helper.tree(package) == source_before and collect(repo) == frozen_before, "benchmark or frozen protocol source changed")
    output.mkdir()
    with gzip.GzipFile(filename=str(output / "record_audit.jsonl.gz"), mode="wb", mtime=0) as f:
        for record in records:
            f.write((json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode())
    with gzip.GzipFile(filename=str(output / "private_contexts_DO_NOT_PUBLISH.jsonl.gz"), mode="wb", mtime=0) as f:
        for item in private:
            f.write((json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n").encode())
    provenance = [{"stage": "confirmatory", "position": r["position"], "model": r["model"], "arm": r["arm"], "pair_id": r["pair_id"], "goal": r["suite"] + "/" + r["user_task"], "native_utility": r["native_utility"],
                   "raw_pointer": index["confirmatory", r["position"]]["raw"], "raw_sha256": index["confirmatory", r["position"]]["raw_sha256"], "evidence_sha256": index["confirmatory", r["position"]]["evidence_sha256"]} for r in population]
    dump(output / "frozen_population.json", provenance)
    summary = {"cycle": "K", "status": "POST_HOC_TARGETED_ORIGINAL_BENIGN_CONSTRUCT_AUDIT", "started_utc": started,
               "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "runtime_seconds": time.perf_counter() - tick,
               "new_tasks": 32, "original_records_replayed": len(records), "confirmatory_pairs_replayed": len(records)//2,
               "actual_contexts": len(records), "hypothetical_contexts": len(records), "counts": dict(count),
               "record_reverse_order_checks": len(immutable_contexts), "endpoint_reverse_order_checks": len(immutable_contexts),
               "input_files_before_after": {str(p): h for p, h in bound.items()}, "source_inventory_before_after": source_before,
               "spec_sha256": args.spec_sha256, "code_sha256": sha(pathlib.Path(__file__)), "evaluator_sha256": sha(pathlib.Path(__file__).with_name("benign_construct_cycle_k.py")),
               "private_contexts_published": False, "human_reviews": 0, "provider_calls": 0, "original_oracle_calls": 0,
               "artifact_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()}}
    dump(output / "execution_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("input_files_before_after", "artifact_sha256", "source_inventory_before_after")}, ensure_ascii=True))


if __name__ == "__main__":
    main()
