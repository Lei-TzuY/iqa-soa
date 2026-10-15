"""Replay only 24 selected original records / 44 proxy evaluation contexts.

Original source oracles are denied. Deterministic mock tools reconstruct bound
historical actual observations and independent hypothetical proposal shadows.
No new model/provider requests; outputs are minimized and isolated.
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
from collections import Counter, defaultdict

from banking2_proxy_cycle_i import audit_context, bind_initial_foods, digest, minimized_event


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def history_projection(environment):
    return [{"subject": t.subject, "amount": t.amount, "date": str(t.date),
             "recipient_sha256": hashlib.sha256(t.recipient.encode()).hexdigest()}
            for t in environment.bank_account.transactions]


def main():
    ap = argparse.ArgumentParser()
    for name in ("repo", "f-index", "f-helper", "spec", "selection", "output"):
        ap.add_argument("--" + name, type=pathlib.Path, required=True)
    ap.add_argument("--spec-sha256", required=True)
    args = ap.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    require(not output.exists() and repo not in output.parents,
            "fresh output outside original repo required")
    require(sha(args.spec) == args.spec_sha256, "frozen proxy specification changed")
    rubric = read(args.spec)
    require(sha(args.selection) == rubric["selection"]["selection_sha256"],
            "selected context manifest changed")
    selection = read(args.selection)
    require(len(selection) == 44, "44 affected contexts required")
    selected = defaultdict(dict)
    for row in selection:
        require(row["suite"] == "banking" and row["goal"] == "injection_task_2",
                "out-of-scope selected goal")
        key = row["stage"], int(row["position"])
        require(row["endpoint"] not in selected[key], "duplicate selected context")
        selected[key][row["endpoint"]] = row
    require(len(selected) == 24 and Counter(r["endpoint"] for r in selection) == {
        "executed": 20, "proposed": 24}, "selected population differs")
    bindings = {args.spec: args.spec_sha256, args.selection: sha(args.selection),
                args.f_index: rubric["source_binding"]["f_record_index_sha256"],
                args.f_helper: rubric["source_binding"]["f_helper_sha256"]}
    for path, expected in bindings.items():
        require(sha(path) == expected, "bound input differs: " + str(path))
    sys.dont_write_bytecode = True

    def deny(*_a, **_k):
        raise RuntimeError("source oracle or network operation denied")

    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny

    def guard(event, params):
        if event.startswith("socket.") and event != "socket.__new__":
            raise RuntimeError("network denied")
        if event == "open":
            path, mode, flags = params
            writing = (isinstance(mode, str) and any(x in mode for x in "wax+")) or (flags & 0x703 != 0)
            if writing and isinstance(path, (str, bytes)):
                require(output in pathlib.Path(path).resolve().parents,
                        "write outside isolated output")
        if event in ("os.remove", "os.rename", "os.rmdir", "subprocess.Popen", "os.system"):
            raise RuntimeError("mutation/process denied")
        if event == "os.mkdir":
            path = pathlib.Path(params[0]).resolve()
            require(path == output or output in path.parents, "mkdir outside isolated output")

    sys.addaudithook(guard)
    started, tick = dt.datetime.now(dt.timezone.utc).isoformat(), time.perf_counter()
    module_spec = importlib.util.spec_from_file_location("bound_cycle_f_restoration", args.f_helper)
    helper = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(helper)
    sys.path[:0] = [str(repo / "scripts"), str(repo / "src")]
    import agentdojo
    from agentdojo.task_suite.load_suites import get_suites
    from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
    from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
    from agentdojo.types import get_text_content_as_str
    from agentdojo.default_suites.v1.tools import banking_client
    from fse2027_ext.freeze import collect, verify

    package = pathlib.Path(agentdojo.__file__).parent
    source_before = helper.tree(package)
    require(source_before == rubric["source_binding"]["AgentDojo_inventory"], "installed benchmark changed")
    require(sha(pathlib.Path(banking_client.__file__)) == rubric["source_binding"]["banking_tool_sha256"],
            "atomic banking contract changed")
    archive = repo / "results/fse2027-external-replication-v1"
    verify(repo, read(archive / "freeze-manifest.json"))
    frozen_before = collect(repo)
    suites = get_suites("v1.2.2")
    suite = suites["banking"]
    task = suite.injection_tasks["injection_task_2"]
    require(task.GOAL == rubric["goal"]["exact_objective"], "resolved objective differs")
    require(hashlib.sha256(inspect.getsource(type(task)).encode()).hexdigest() ==
            rubric["source_binding"]["task_class_sha256"], "resolved goal class changed")
    for s in suites.values():
        for t in list(s.injection_tasks.values()) + list(s.user_tasks.values()):
            for name in ("security", "security_from_traces", "utility", "utility_from_traces"):
                if hasattr(type(t), name):
                    setattr(type(t), name, deny)
    prior = {(r["stage"], r["position"]): r for r in lines(args.f_index)}
    contexts, records, counters = [], [], Counter()
    history_reference = rubric["initial_food_evidence"]["all_initial_transaction_projections"]
    source_row_metadata = {}
    for stage in ("qualification", "confirmatory"):
        summary = archive / stage / "runs.jsonl"
        bindings[summary] = sha(summary)
        for row in lines(summary):
            key = stage, row["position"]
            if key not in selected:
                continue
            source_row_metadata[key] = row
            require(row["kind"] in ("security", "injection_as_user") and row["suite"] == "banking" and
                    row["injection_task"] == "injection_task_2", "out-of-scope observation")
            require(row["kind"] != "injection_as_user" or stage == "qualification",
                    "direct-goal observation outside original qualification")
            old = prior[key]
            chosen = next(iter(selected[key].values()))
            cell = archive / stage / "cells" / f"{row['position']:05d}-{row['model']}-{row['arm']}"
            for name, field in (("raw.json", "raw_sha256"), ("evidence.jsonl", "evidence_sha256")):
                path = cell / name
                require(sha(path) == old[field] == chosen[field], "original input hash differs")
                bindings[path] = old[field]
            raw = read(cell / "raw.json")
            require(raw["record"] == row and row["pipeline_runs"] == 1, "original record identity differs")
            actual = suite.load_and_inject_default_environment(raw["injections"])
            if row["user_task"]:
                actual = suite.user_tasks[row["user_task"]].init_environment(actual)
            initial = helper.portable(actual)
            require(digest(initial) == old["initial_state_sha256"], "initial state differs from F")
            history = history_projection(actual)
            history_bound = history == history_reference
            initial_food_binding = (bind_initial_foods(history, rubric)
                                    if rubric.get("initial_attestation_policy") == "UNCHANGED_FOOD_SPECIFIC_INITIAL_PURCHASE"
                                    else {"initial_history_bound": history_bound})
            shadow = copy.deepcopy(actual)
            all_calls = [FunctionCall.model_validate(c) for m in raw["messages"]
                         if m["role"] == "assistant" for c in m.get("tool_calls") or []]
            tool_messages = [m for m in raw["messages"] if m["role"] == "tool"]
            require(len(tool_messages) == len(raw["proposals"]) <= len(all_calls), "original evaluation boundary incomplete")
            calls = all_calls[:len(tool_messages)]
            gateway = {e["evidence_id"]: e for e in lines(cell / "evidence.jsonl")}
            actual_events, shadow_events, dispatched, proposed = [], [], [], []
            runtime, shadow_runtime = FunctionsRuntime(suite.tools), FunctionsRuntime(suite.tools)
            for ordinal, (call, proposal, message) in enumerate(zip(calls, raw["proposals"], tool_messages)):
                require(message["tool_call"] == call.model_dump(), "call/result linkage differs")
                if call.function not in runtime.functions:
                    counters["unknown_runtime_functions"] += 1
                    continue
                e = gateway[proposal["evidence_id"]]
                require(e["qa_mode"] == row["arm"] and bool(e["executed"]) == bool(proposal["executed"]),
                        "recorded treatment/dispatch differs")
                proposed.append(call.model_dump())
                modes = [("proposed", shadow, shadow_runtime, call.function, copy.deepcopy(call.args))]
                if proposal["executed"]:
                    authorized = e.get("executed_action") if row["arm"] == "full" else None
                    require(row["arm"] != "full" or authorized is not None, "authorized actual arguments absent")
                    fn, arguments = ((authorized["resource"].split("/")[-1], authorized["arguments"])
                                     if authorized is not None else (call.function, call.args))
                    modes.append(("executed", actual, runtime, fn, copy.deepcopy(arguments)))
                else:
                    counters["blocked_original_proposals"] += 1
                for mode, state, engine, fn, arguments in modes:
                    before = helper.portable(state)
                    result, error = engine.run_function(state, fn, copy.deepcopy(arguments))
                    after = helper.portable(state)
                    ids = {t["id"] for t in before["bank_account"]["transactions"]}
                    added = [t for t in after["bank_account"]["transactions"] if t["id"] not in ids]
                    retained_text = get_text_content_as_str(message["content"])
                    basis = "HYPOTHETICAL_MOCK_ACCEPTANCE" if mode == "proposed" else "RETAINED_RESULT_AND_ATOMIC_STATE_TRANSITION"
                    if mode == "executed":
                        require(error == message["error"] == e.get("error"), "retained tool error differs")
                        require((error is None) == bool(e.get("success")), "retained success/error binding differs")
                        if proposal["disposition"] == "EXECUTED_RESULT_WITHHELD":
                            basis = "RECORDED_EXECUTION_SUCCESS_AND_FROZEN_ATOMIC_APPEND_RESULT_WITHHELD"
                            counters["post_dispatch_results_withheld"] += 1
                        else:
                            require(tool_result_to_str(result) == retained_text, "retained tool output differs")
                            counters["exact_retained_tool_outputs"] += 1
                        counters["dispatched_tool_calls"] += 1
                        counters["actual_tool_errors"] += error is not None
                        dispatched.append(call.model_dump())
                    else:
                        counters["hypothetical_tool_calls"] += 1
                        counters["hypothetical_tool_errors"] += error is not None
                    accepted = error is None
                    binding = False
                    if fn == "send_money" and accepted:
                        require(len(added) == 1, "successful atomic transfer lacks one fresh transaction")
                        tx = added[0]
                        binding = all(tx[field] == arguments[field] for field in ("recipient", "subject", "date"))
                        binding = binding and float(tx["amount"]) == float(arguments["amount"])
                        require(binding, "atomic append differs from complete original arguments")
                    event = {"ordinal": ordinal, "function": fn, "arguments": copy.deepcopy(arguments),
                             "acceptance": accepted, "acceptance_basis": basis,
                             "original_proposal_executed": bool(proposal["executed"]),
                             "error_sha256": digest(error), "before_state_sha256": digest(before),
                             "after_state_sha256": digest(after), "mock_result_sha256": digest(helper.portable(result)),
                             "retained_result_sha256": digest(retained_text) if mode == "executed" else None,
                             "evidence_id": proposal["evidence_id"], "new_transactions": added,
                             "atomic_append_argument_binding": binding}
                    (actual_events if mode == "executed" else shadow_events).append(event)
            require(dispatched == raw["executed_trace"] and proposed == raw["proposed_trace"],
                    "retained actual/proposed trace differs")
            final = helper.portable(actual)
            require(digest(final) == old["post_execution_projection_sha256"], "reconstructed actual final state differs from F")
            available = {"executed": actual_events, "proposed": shadow_events}
            decisions, record_contexts = {}, {}
            for endpoint in selected[key]:
                ctx = {**initial_food_binding, "initial_history_sha256": digest(history),
                       "initial_state_sha256": digest(initial), "endpoint": endpoint,
                       "events": copy.deepcopy(available[endpoint])}
                record_contexts[endpoint] = ctx
                decisions[endpoint] = audit_context(ctx, rubric)
                contexts.append((key, endpoint, ctx))
            reverse = {ep: audit_context(ctx, rubric) for ep, ctx in reversed(list(record_contexts.items()))}
            require(reverse == decisions, "endpoint evaluation order dependence")
            # Historical scoring fields are compared only after proxy decisions.
            fields = ("native_security", "cpe_executed", "cpe_proposed")
            records.append({"stage": stage, "position": row["position"], "model": row["model"],
                            "arm": row["arm"], "kind": row["kind"], "suite": "banking", "goal": "injection_task_2",
                            "user_task": row["user_task"], "seed": row["seed"], "pair_id": row.get("pair_id"),
                            "benchmark_version": "v1.2.2", "raw_pointer": old["raw"],
                            "raw_sha256": old["raw_sha256"], "evidence_sha256": old["evidence_sha256"],
                            "rubric_sha256": args.spec_sha256,
                            "initial_history_bound": history_bound, "initial_history_sha256": digest(history),
                            "food_specific_initial_binding": initial_food_binding,
                            "initial_projection_sha256": digest(initial), "final_actual_projection_sha256": digest(final),
                            "final_proposed_projection_sha256": digest(helper.portable(shadow)),
                            "proxy": decisions, "personal_preference": "AMBIGUOUS_UNCHANGED",
                            "recorded": {field: row.get(field) for field in fields},
                            "events": {ep: [minimized_event(e, rubric) for e in available[ep]] for ep in selected[key]},
                            "terminal_native_calls_not_dispatched": len(all_calls)-len(calls),
                            "endpoint_order_invariant": True})
    require(len(records) == 24 and len(contexts) == 44 and set(source_row_metadata) == set(selected),
            "targeted replay incomplete")
    by_key = {(r["stage"], r["position"]): r for r in records}
    for key, endpoint, ctx in reversed(contexts):
        require(audit_context(copy.deepcopy(ctx), rubric) == by_key[key]["proxy"][endpoint],
                "record evaluation order dependence")
    for path, expected in bindings.items():
        require(sha(path) == expected, "input changed during replay")
    verify(repo, read(archive / "freeze-manifest.json"))
    require(collect(repo) == frozen_before and helper.tree(package) == source_before,
            "original frozen source changed during replay")
    summary = {"cycle": "I_BANKING2_PURCHASE_HISTORY_PROXY", "status": "POST_HOC_ALTERNATIVE_CONSTRUCT_EXECUTED",
               "started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "runtime_seconds": time.perf_counter()-tick, "python": sys.version,
               "records": len(records), "contexts": len(contexts), "record_reverse_order_checks": 44,
               "endpoint_reverse_order_checks": 44, "second_witness_checks": 44,
               "second_witness_limit": "Shared historical decoder and frozen mock restoration/facts; no independent human review.",
               "counts": {ep: dict(Counter(str(r["proxy"][ep]["outcome"]) for r in records if ep in r["proxy"]))
                          for ep in ("executed", "proposed")}, "binding": dict(counters),
               "input_files_before_after": {str(path): expected for path, expected in bindings.items()},
               "AgentDojo_inventory_before_after": source_before, "frozen_provenance_before_after": frozen_before,
               "source_hashes": {"runner": sha(pathlib.Path(__file__)),
                                 "evaluator": sha(pathlib.Path(__file__).with_name("banking2_proxy_cycle_i.py")),
                                 "rubric": args.spec_sha256, "selection": sha(args.selection)},
               "original_oracle_calls": 0, "new_model_provider_calls": 0, "network_calls": 0,
               "human_reviews": 0, "personal_preference_labels_changed": 0,
               "other_goal_labels_changed": 0, "historical_H_bounds_changed": False,
               "limitations": "Only the authorized purchased-food proxy. Hypothetical mock acceptance is not actual execution. Initial purchases do not establish actual preference; original H/I outcomes and HOLD remain unchanged."}
    output.mkdir()
    body = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":"))+"\n" for r in records).encode()
    (output/"proxy_records.jsonl.gz").write_bytes(gzip.compress(body, mtime=0))
    (output/"execution_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "records": len(records), "contexts": len(contexts),
                      "counts": summary["counts"], "binding": summary["binding"],
                      "runtime_seconds": summary["runtime_seconds"],
                      "artifacts": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)} for p in output.iterdir()}}), flush=True)


if __name__ == "__main__":
    main()
