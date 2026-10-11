"""Read-only Cycle I provenance/fact inspection; no action or oracle execution.

Run with the recovered AgentDojo interpreter and -B. Output is minimized JSON
on stdout. The controlled H review map, identifiers and message bodies are never
exported. Loading default fixtures is metadata inspection, not outcome replay.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import datetime as dt
import hashlib
import inspect
import json
import pathlib
import socket
import sys
import time


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def require(ok, why):
    if not ok:
        raise ValueError(why)


def deny(*args, **kwargs):
    raise RuntimeError("Cycle I desktop inspection forbids writes, network, tools and scoring")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=pathlib.Path)
    parser.add_argument("h_directory", type=pathlib.Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    archive = repo / "results/fse2027-external-replication-v1"
    h = args.h_directory.resolve()
    tick = time.perf_counter()
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    sys.dont_write_bytecode = True
    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny

    def hook(event, parameters):
        if event.startswith("socket.") and event != "socket.__new__":
            deny()
        if event == "open":
            _, mode, flags = parameters
            if (isinstance(mode, str) and any(c in mode for c in "wax+")) or flags & 0x703:
                deny()
        if event in ("os.remove", "os.rename", "os.rmdir", "os.mkdir", "subprocess.Popen", "os.system"):
            deny()

    sys.addaudithook(hook)
    input_path = h / "review-input-20261011-v1.json"
    require(sha(input_path) == "17789cbeff349a4e286ba802fbc40ab35c6f5cb05e8596c63edba22d5f53d783", "H review input differs")
    pending = load(input_path)["input"]
    require(len(pending) == 71, "pending context count differs")
    bound = {}
    for row in pending:
        raw = row["raw_pointer"].replace("\\", "/")
        bound[archive / raw] = row["raw_sha256"]
        bound[archive / raw.replace("/raw.json", "/evidence.jsonl")] = row["evidence_sha256"]
    require(len(bound) == 76, "pending original-file count differs")
    summary_path = h / "targeted-replay-v5/execution_summary.json"
    require(sha(summary_path) == "bc7f3982c0a01bfb658e17d7e55677946a8b147a7f3f2895e226db3fa84e7a89", "successful H summary differs")
    frozen = load(summary_path)["frozen_source_provenance"]
    for group in ("code", "study_documents"):
        for name, expected in frozen[group].items():
            bound[repo / name] = expected
    runs_path = archive / "confirmatory/runs.jsonl"
    bound[runs_path] = "d4661a2051051a3e81ef0b0e4ddf5ce1e628621208ca065344d55d96a661ffa0"
    for path, expected in bound.items():
        require(sha(path) == expected, "bound source changed: " + str(path))
    before = {str(p): sha(p) for p in bound}

    from agentdojo.task_suite.load_suites import get_suites
    from agentdojo.functions_runtime import FunctionsRuntime

    FunctionsRuntime.run_function = deny
    suites = get_suites("v1.2.2")
    for suite in suites.values():
        for task in list(suite.user_tasks.values()) + list(suite.injection_tasks.values()):
            for name in ("security", "security_from_traces", "utility", "utility_from_traces"):
                if hasattr(type(task), name):
                    setattr(type(task), name, deny)
    bank = suites["banking"].load_and_inject_default_environment({})
    workspace = suites["workspace"].load_and_inject_default_environment({})
    participants = sorted({person for event in workspace.calendar.events.values()
                           if str(event.start_time).startswith("2024-05-15")
                           for person in event.participants if person != workspace.calendar.account_email})
    contacts = {str(c.email): c for c in workspace.inbox.contact_list}
    require(len(participants) == 5, "May15 participant population differs")
    import agentdojo
    package = pathlib.Path(agentdojo.__file__).parent
    relevant_sources = ["default_suites/v1/tools/banking_client.py", "default_suites/v1/tools/email_client.py",
                        "default_suites/v1_2/banking/injection_tasks.py", "default_suites/v1_2/workspace/injection_tasks.py",
                        "data/suites/banking/environment.yaml", "data/suites/workspace/environment.yaml",
                        "data/suites/workspace/include/calendar.yaml", "data/suites/workspace/include/inbox.yaml"]
    source_hashes = {name: sha(package / name) for name in relevant_sources}
    package_files = {p.relative_to(package).as_posix(): sha(p) for p in sorted(package.rglob("*"))
                     if p.is_file() and "__pycache__" not in p.parts}
    package_tree = {"files": len(package_files), "sha256": hashlib.sha256(json.dumps(
        package_files, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()}
    require(package_tree == frozen["agentdojo_installed_tree"], "installed AgentDojo tree differs")
    identities = {}
    affected_users = set()
    for row in pending:
        if (row["suite"], row["goal"]) not in (("banking", "injection_task_5"), ("workspace", "injection_task_13")):
            continue
        record = load(archive / row["raw_pointer"])["record"]
        if record["user_task"]:
            affected_users.add((record["suite"], record["user_task"]))
    for suite_name, task_id in sorted(affected_users):
        task = suites[suite_name].user_tasks[task_id]
        source = inspect.getsource(task.init_environment)
        identities[suite_name + "/" + task_id] = {"source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                                                "source": source}

    original_rows = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines() if line]
    require(len(original_rows) == 948, "confirmatory summary count differs")
    gaps = [r for r in original_rows if r["arm"] == "full" and r["kind"] == "security"
            and r["canonical_population"] and r["cpe_proposed"] and not r["cpe_executed"]]
    require(len(gaps) == 72, "source-defined proposal/nonexecution gap differs")
    gap_positions = {r["position"] for r in gaps}
    targeted = [r for r in original_rows if r["arm"] == "full" and
                (r["n_blocked"] or "output_validation" in r["blocking_guards"])]
    require(gap_positions <= {r["position"] for r in targeted}, "gap source has no selected operational evidence")
    saved_f = h.parent / "cycle-f-20261010/full-replay-v5/record_replay.jsonl"
    require(sha(saved_f) == "68a099a6c876b517807a493ce2129ae5e721634053229b6e0e98949352bb16e8", "saved F replay provenance differs")
    expected_original = {r["raw"]: r for r in
                         (json.loads(line) for line in saved_f.read_text(encoding="utf-8").splitlines())}
    bound[saved_f] = sha(saved_f)
    before[str(saved_f)] = sha(saved_f)
    trace_rows = []
    pre_guards = Counter()
    post_guards = Counter()
    guard_cells = Counter()
    raw_keys = None
    for row in targeted:
        position = int(row["position"])
        pointer = f"confirmatory/cells/{position:05d}-{row['model']}-full/raw.json"
        raw_path = archive / pointer
        require(pointer in expected_original, "gap record missing from F provenance")
        require(sha(raw_path) == expected_original[pointer]["raw_sha256"], "original gap raw hash differs")
        raw = load(raw_path)
        if raw_keys is None:
            raw_keys = {"raw": list(raw), "record": list(raw.get("record", {})),
                        "executed_trace_first": list(raw.get("executed_trace", [{}])[0]) if raw.get("executed_trace") else []}
        trace = raw.get("executed_trace", [])
        evidence_path = raw_path.with_name("evidence.jsonl")
        require(sha(evidence_path) == expected_original[pointer]["evidence_sha256"], "original gap evidence hash differs")
        events = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines() if line]
        dispatch_events = [e for e in events if "executed" in e]
        require(dispatch_events, "dispatch evidence missing")
        blocked_count = sum(not e["executed"] for e in dispatch_events)
        require(blocked_count == row["n_blocked"] == sum(not x["executed"] for x in raw["proposals"]),
                "independent nonexecution/proposal/summary counts disagree")
        event_by_id = {e["evidence_id"]: e for e in dispatch_events}
        tool_messages = [m for m in raw["messages"] if m["role"] == "tool"]
        require(len(tool_messages) == len(raw["proposals"]), "call/result history incomplete")
        seen = set()
        for proposal, message in zip(raw["proposals"], tool_messages):
            event = event_by_id[proposal["evidence_id"]]
            require(event["executed"] == proposal["executed"], "raw and gateway dispatch flags disagree")
            guard = event.get("blocking_guard")
            if not event["executed"]:
                require("ToolCallBlocked" in str(message.get("error", "")), "nonexecution lacks retained refusal result")
                pre_guards[guard] += 1
            elif guard:
                post_guards[guard] += 1
            if guard:
                seen.add(guard)
        guard_cells.update(seen)
        trace_rows.append({"position": position, "model": row["model"], "suite": row["suite"],
                           "goal": row.get("injection_task"), "raw_pointer": pointer,
                           "raw_sha256": sha(raw_path), "raw_record_matches_source_summary": raw.get("record") == row,
                           "n_blocked": row.get("n_blocked"), "trace_entries": len(trace),
                           "nonexecuted_gateway_entries": blocked_count,
                           "dispatch_evidence_entries": len(dispatch_events),
                           "any_successful_dispatch": any(e["executed"] and e.get("error") is None for e in dispatch_events),
                           "blocking_guard_summary": row.get("blocking_guards")})
        bound[raw_path] = sha(raw_path)
        bound[evidence_path] = sha(evidence_path)
        before[str(raw_path)] = sha(raw_path)
        before[str(evidence_path)] = sha(evidence_path)
    after = {str(p): sha(p) for p in bound}
    require(all(after[k] == v for k, v in before.items()), "source changed during read-only inspection")
    require(package_tree == {"files": len(package_files), "sha256": hashlib.sha256(json.dumps(
        {p.relative_to(package).as_posix(): sha(p) for p in sorted(package.rglob("*"))
         if p.is_file() and "__pycache__" not in p.parts}, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()}, "AgentDojo sources changed during inspection")
    result = {"cycle": "I", "operation": "READ_ONLY_METADATA_AND_TRACE_INSPECTION",
              "started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "runtime_seconds": time.perf_counter() - tick, "code_sha256": sha(pathlib.Path(__file__)),
              "remaining_original_files_verified": 76, "bound_sources_before_after": len(before),
              "gap_raw_records_inspected": len(gaps), "all_gap_raw_files_verified_after": True,
              "operational_records_inspected": len(targeted),
              "pre_dispatch_refusals_by_guard": dict(pre_guards),
              "post_dispatch_blocking_guard_dispositions": dict(post_guards),
              "operational_cells_with_guard": dict(guard_cells),
              "installed_package_tree": package_tree, "source_hashes": source_hashes,
              "banking5": {"account_schema_fields": list(type(bank.bank_account).model_fields),
                           "finite_capacity_metadata": "ABSENT", "starting_balance_is_not_capacity": True,
                           "source_gold_example_amount_is_not_an_enforced_maximum": True},
              "workspace13": {"other_May15_participants": len(participants),
                              "initial_contact_list_count": len(contacts),
                              "participants_with_explicit_initial_contact_entry": sum(p in contacts for p in participants),
                              "authenticated_first_name_map": "NOT_IDENTIFIABLE_FROM_RETAINED_EVIDENCE"},
              "initializer_sources": identities, "raw_schema": raw_keys,
              "gap_trace_records": [r for r in trace_rows if r["position"] in gap_positions],
              "operational_trace_records": trace_rows,
              "new_semantic_labels": 0, "historical_action_replays": 0, "tool_execution_calls": 0,
              "native_scoring_calls": 0, "provider_calls": 0, "human_decisions": 0}
    print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
