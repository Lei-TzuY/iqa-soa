"""Offline, source-only AgentDojo audit. No model, package import, or provider call."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = (1, 2, 2)
SUITES = ("banking", "slack", "travel", "workspace")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def literal(node: ast.AST, constants: dict) -> object:
    return constants[node.id] if isinstance(node, ast.Name) else ast.literal_eval(node)


def collect_tasks(base: Path) -> dict:
    """Resolve literal registrations, updates, and explicit combined-task calls.

    This supports the pinned source grammar, not arbitrary Python. Fail closed on
    unknown registration syntax. It mirrors version selection, not score execution.
    """
    registry: dict[tuple, dict] = {}
    for file in sorted(base.glob("v*/*/*tasks.py")):
        suite = file.parent.name
        if suite not in SUITES:
            raise ValueError(f"unknown suite {suite}")
        module = ast.parse(file.read_text(encoding="utf-8"))
        constants: dict = {}
        for item in module.body:
            if isinstance(item, ast.Assign):
                try:
                    value = ast.literal_eval(item.value)
                except (TypeError, ValueError):
                    continue
                for name in item.targets:
                    if isinstance(name, ast.Name):
                        constants[name.id] = value
            if isinstance(item, ast.ClassDef):
                for decorator in item.decorator_list:
                    attr = decorator.func if isinstance(decorator, ast.Call) else decorator
                    if not isinstance(attr, ast.Attribute) or not isinstance(attr.value, ast.Name):
                        continue
                    if attr.value.id != "task_suite":
                        continue
                    if attr.attr not in {"register_user_task", "register_injection_task",
                                          "update_user_task", "update_injection_task"}:
                        raise ValueError(f"unsupported registration {ast.unparse(decorator)}")
                    match = re.fullmatch(r"(UserTask|InjectionTask)(\d+)", item.name)
                    if match is None:
                        raise ValueError(f"unsupported task name {item.name}")
                    version = tuple(literal(decorator.args[0], constants)) if isinstance(decorator, ast.Call) else (1, 0, 0)
                    if len(version) != 3 or any(type(v) is not int for v in version):
                        raise ValueError("bad version")
                    key = (suite, match[1], int(match[2]))
                    versions = registry.setdefault(key, {})
                    if version in versions:
                        # Upstream deliberately re-registers workspace UserTask13
                        # in v1_1_2. Its last registration wins at base version.
                        if attr.attr.startswith("update_"):
                            raise ValueError(f"duplicate update {key} {version}")
                    versions[version] = {"node": item, "file": file, "line": item.lineno,
                                         "combined": False}
            if isinstance(item, ast.Expr) and isinstance(item.value, ast.Call):
                call = item.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "create_combined_task":
                    name = literal(call.args[0], constants)
                    match = re.fullmatch(r"UserTask(\d+)", str(name))
                    if match is None or len(call.args) != 3:
                        raise ValueError("unsupported combined task")
                    key = (suite, "UserTask", int(match[1]))
                    if key in registry:
                        raise ValueError(f"duplicate combined task {key}")
                    registry[key] = {(1, 0, 0): {"node": call, "file": file,
                                               "line": item.lineno, "combined": True}}
    chosen = {}
    for key, versions in registry.items():
        compatible = [v for v in versions if v <= TARGET]
        if compatible:
            version = max(compatible)
            chosen[key] = dict(versions[version], version=version)
    return chosen


def source_audit() -> dict:
    manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        data = (ROOT / "upstream" / entry["path"]).read_bytes()
        if len(data) != entry["bytes"] or git_blob(data) != entry["git_blob_sha1"] or digest(data) != entry["sha256"]:
            raise ValueError(f"source bytes drift: {entry['path']}")
    base = ROOT / "upstream/src/agentdojo/default_suites"
    tasks = collect_tasks(base)
    suite_results = {}
    goal_rows = []
    for suite in SUITES:
        users = [k for k in tasks if k[0] == suite and k[1] == "UserTask"]
        goals = [k for k in tasks if k[0] == suite and k[1] == "InjectionTask"]
        tree = ast.parse((base / "v1" / suite / "task_suite.py").read_text(encoding="utf-8"))
        tool_lists = [n.value for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "TOOLS" for t in n.targets)]
        if len(tool_lists) != 1 or not isinstance(tool_lists[0], ast.List):
            raise ValueError("unsupported tool registry")
        tools = [n.id for n in tool_lists[0].elts if isinstance(n, ast.Name)]
        if len(tools) != len(tool_lists[0].elts) or len(tools) != len(set(tools)):
            raise ValueError("ambiguous tools")
        suite_results[suite] = {"user_tasks": len(users), "attacker_goals": len(goals),
                               "suite_tool_registrations": len(tools),
                               "cartesian_user_goal_pairs": len(users) * len(goals),
                               "combined_user_tasks": sum(tasks[k]["combined"] for k in users)}
        for key in sorted(goals):
            task = tasks[key]
            methods = {n.name: n for n in task["node"].body if isinstance(n, ast.FunctionDef)}
            if "security_from_traces" in methods:
                predicate = methods["security_from_traces"]
                kind = "proposed_call_trace"
            else:
                predicate = methods["security"]
                text_used = any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                                and n.id == "model_output" for n in ast.walk(predicate))
                kind = "model_text" if text_used else "environment_state"
            goal_rows.append({"suite": suite, "goal": f"injection_task_{key[2]}",
                              "source": str(task["file"].relative_to(ROOT / "upstream")),
                              "class_line": task["line"], "version": list(task["version"]),
                              "predicate_method": predicate.name, "predicate_line": predicate.lineno,
                              "predicate_source_sha256": digest(ast.get_source_segment(
                                  task["file"].read_text(encoding="utf-8"), predicate).encode()),
                              "boundary": kind})
    totals = {key: sum(row[key] for row in suite_results.values()) for key in next(iter(suite_results.values()))}
    boundary_counts = dict(sorted(Counter(row["boundary"] for row in goal_rows).items()))
    # Expectations are manuscript-reported source claims, not study measurements.
    expected = {"user_tasks": 97, "attacker_goals": 35,
                "suite_tool_registrations": 74, "cartesian_user_goal_pairs": 949}
    match = {k: totals[k] == v for k, v in expected.items()}
    if not all(match.values()) or boundary_counts != {"environment_state": 33, "model_text": 1, "proposed_call_trace": 1}:
        raise ValueError(f"source claim mismatch: {totals} {boundary_counts}")
    return {"schema_version": 1, "verification": "EXECUTED_SOURCE_AUDIT_ONLY",
            "upstream": manifest["upstream"], "source_files_verified": len(manifest["files"]),
            "audit_code_sha256": digest(Path(__file__).read_bytes()), "suites": suite_results,
            "totals": totals, "predicate_boundaries": boundary_counts, "goals": goal_rows,
            "external_empirical_results": "UNVERIFIED_RAW_PACKAGE_UNLOCATED",
            "limitations": ["AST inventory does not execute scoring predicates or tools.",
                            "949 is the Cartesian population count, not a rerun of adapter equivalence tests.",
                            "74 counts suite tool registrations; read/effect classification is not audited here.",
                            "No external model records, eligibility, stage chain or frozen statistics were recovered."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(source_audit(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if (ROOT / "source_audit.json").read_text(encoding="utf-8") != result:
            raise SystemExit("SOURCE AUDIT REPORT DRIFT")
        print("SOURCE AUDIT VERIFIED: 70 exact files; 97 tasks; 35 goals; 949 pairs; empirical study remains unverified")
    else:
        with args.output.open("x", encoding="utf-8") as f:
            f.write(result)
        print("WROTE SOURCE AUDIT; no empirical result reproduced")


if __name__ == "__main__":
    main()
