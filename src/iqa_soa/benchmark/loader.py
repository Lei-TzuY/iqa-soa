"""Strict YAML benchmark loading and cross-reference validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
import re
from typing import Any, NoReturn, cast

import yaml  # type: ignore[import-untyped]

from iqa_soa.benchmark.schema import (
    ActionRule,
    AttackSpec,
    BenchmarkBudget,
    BenchmarkCase,
    BenchmarkCategory,
    BenchmarkEnvironment,
    FaultSpec,
    GroundTruth,
    SUPPORTED_TOOL_NAMES,
    rule_contradictions,
)
from iqa_soa.types import Action


class BenchmarkValidationError(ValueError):
    """A case cannot be admitted into an experiment."""


_CASE_KEYS = {
    "schema_version",
    "id",
    "category",
    "user_prompt",
    "system_prompt",
    "environment",
    "scripted_actions",
    "allowed_actions",
    "forbidden_actions",
    "allowed_resources",
    "forbidden_resources",
    "protected_data",
    "protected_resources",
    "budget",
    "attack",
    "fault",
    "ground_truth",
    "tags",
}
_CASE_REQUIRED = _CASE_KEYS - {"system_prompt", "attack", "fault", "tags"}
_ENV_KEYS = {"files", "database", "api_responses", "robot", "faults"}
_ACTION_KEYS = {
    "action_id",
    "tool",
    "resource",
    "arguments",
    "source",
    "derived_from_untrusted",
    "risk_severity",
}
_ACTION_REQUIRED = {"action_id", "tool", "resource", "arguments"}
_RULE_KEYS = {"tool", "resource"}
_BUDGET_KEYS = {
    "max_tool_calls",
    "max_model_calls",
    "max_tokens",
    "max_cost",
    "max_runtime_ms",
}
_ATTACK_KEYS = {"type", "payload_location", "untrusted_sources", "description"}
_ATTACK_REQUIRED = {"type", "payload_location", "untrusted_sources"}
_FAULT_KEYS = {"type", "action_id", "hard_policy", "description"}
_FAULT_REQUIRED = {"type", "action_id"}
_FAULT_TYPES = {
    "timeout",
    "high_latency",
    "malformed_response",
    "unavailable",
    "partial_failure",
}
_TRUTH_KEYS = {
    "unsafe_action_ids",
    "expected_action_ids",
    "task_should_succeed",
    "expected_output_contains",
    "safe_block_success",
    "protected_data_must_not_leak",
    "forbidden_action_must_not_execute",
    "fault_must_be_contained",
}
_TRUTH_REQUIRED = {"unsafe_action_ids", "expected_action_ids", "task_should_succeed"}
_CASE_ID = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3}$")


def load_benchmark_cases(
    path: str | Path, *, case_ids: Iterable[str] | None = None
) -> list[BenchmarkCase]:
    """Load all ``*.yaml``/``*.yml`` cases beneath *path* and validate first.

    No partial list is returned: every discovered file is parsed and all case
    IDs are checked for uniqueness before an optional selection is applied.
    """

    root = Path(path)
    if not root.exists():
        raise BenchmarkValidationError(f"benchmark path does not exist: {root}")
    files = [root] if root.is_file() else sorted((*root.rglob("*.yaml"), *root.rglob("*.yml")))
    if not files:
        raise BenchmarkValidationError(f"no benchmark YAML files found under {root}")
    cases: list[BenchmarkCase] = []
    sources: dict[str, Path] = {}
    errors: list[str] = []
    for file in files:
        try:
            loaded = yaml.safe_load(file.read_text(encoding="utf-8"))
            entries = loaded if isinstance(loaded, list) else [loaded]
            for index, entry in enumerate(entries):
                where = f"{file}[{index}]" if len(entries) > 1 else str(file)
                case = parse_benchmark_case(entry, where=where)
                if case.id in sources:
                    raise BenchmarkValidationError(
                        f"duplicate case id {case.id!r} in {sources[case.id]} and {file}"
                    )
                sources[case.id] = file
                cases.append(case)
        except (OSError, yaml.YAMLError, BenchmarkValidationError) as exc:
            errors.append(f"{file}: {exc}")
    if errors:
        raise BenchmarkValidationError("benchmark validation failed:\n- " + "\n- ".join(errors))
    wanted = set(case_ids) if case_ids is not None else None
    if wanted is not None:
        missing = wanted - set(sources)
        if missing:
            raise BenchmarkValidationError(f"unknown requested case IDs: {sorted(missing)}")
        cases = [case for case in cases if case.id in wanted]
    return sorted(cases, key=lambda case: case.id)


def parse_benchmark_case(value: Any, *, where: str = "benchmark case") -> BenchmarkCase:
    data = _mapping(value, where)
    _keys(data, _CASE_KEYS, _CASE_REQUIRED, where)
    version = _integer(data["schema_version"], f"{where}.schema_version", minimum=1)
    if version != 1:
        _fail(f"{where}.schema_version must be 1")
    case_id = _string(data["id"], f"{where}.id")
    if not _CASE_ID.fullmatch(case_id):
        _fail(f"{where}.id must match {_CASE_ID.pattern}")
    try:
        category = BenchmarkCategory(_string(data["category"], f"{where}.category"))
    except ValueError as exc:
        raise BenchmarkValidationError(f"{where}.category is not supported") from exc
    user_prompt = _string(data["user_prompt"], f"{where}.user_prompt")
    system_prompt = _string(
        data.get("system_prompt", "Follow the user task using registered tools."),
        f"{where}.system_prompt",
    )
    environment = _environment(data["environment"], f"{where}.environment")
    actions = tuple(
        _action(item, f"{where}.scripted_actions[{index}]")
        for index, item in enumerate(_sequence(data["scripted_actions"], f"{where}.scripted_actions"))
    )
    if not actions:
        _fail(f"{where}.scripted_actions must not be empty")
    action_ids = [action.action_id for action in actions]
    if len(action_ids) != len(set(action_ids)):
        _fail(f"{where}.scripted_actions contains duplicate action_id values")
    allowed = _rules(data["allowed_actions"], f"{where}.allowed_actions")
    forbidden = _rules(data["forbidden_actions"], f"{where}.forbidden_actions")
    contradictions = rule_contradictions(allowed, forbidden)
    if contradictions:
        _fail(f"{where} has contradictory action rules: {list(contradictions)}")
    allowed_resources = _string_tuple(data["allowed_resources"], f"{where}.allowed_resources")
    forbidden_resources = _string_tuple(
        data["forbidden_resources"], f"{where}.forbidden_resources"
    )
    resource_overlap = set(allowed_resources) & set(forbidden_resources)
    if resource_overlap:
        _fail(f"{where} has contradictory resource rules: {sorted(resource_overlap)}")
    protected_data = _string_tuple(data["protected_data"], f"{where}.protected_data")
    protected_resources = _string_tuple(
        data["protected_resources"], f"{where}.protected_resources"
    )
    budget = _budget(data["budget"], f"{where}.budget")
    attack = _attack(data.get("attack"), f"{where}.attack")
    fault = _fault(data.get("fault"), f"{where}.fault")
    truth = _ground_truth(data["ground_truth"], f"{where}.ground_truth")
    action_set = set(action_ids)
    refs = set(truth.unsafe_action_ids) | set(truth.expected_action_ids)
    refs |= set(truth.expected_output_contains)
    if fault:
        refs.add(fault.action_id)
    missing_refs = refs - action_set
    if missing_refs:
        _fail(f"{where} references unknown action IDs: {sorted(missing_refs)}")
    overlap = set(truth.unsafe_action_ids) & set(truth.expected_action_ids)
    if overlap:
        _fail(f"{where} marks actions both unsafe and expected: {sorted(overlap)}")
    output_without_expected_action = set(truth.expected_output_contains) - set(
        truth.expected_action_ids
    )
    if output_without_expected_action:
        _fail(
            f"{where} defines output requirements for non-expected actions: "
            f"{sorted(output_without_expected_action)}"
        )
    if category is BenchmarkCategory.BENIGN and truth.unsafe_action_ids:
        _fail(f"{where}: benign cases cannot label unsafe actions")
    if category in {BenchmarkCategory.PROMPT_INJECTION, BenchmarkCategory.KNOWLEDGE_POISONING}:
        if attack is None or not attack.untrusted_sources:
            _fail(f"{where}: injection/poisoning cases require untrusted attack provenance")
        missing_sources = set(attack.untrusted_sources) - set(environment.files)
        if attack.payload_location not in environment.files or missing_sources:
            _fail(
                f"{where}: attack payload/untrusted sources must reference environment files"
            )
        unsafe_by_id = {a.action_id: a for a in actions}
        controlling = [unsafe_by_id[item] for item in truth.unsafe_action_ids]
        if not any(
            action.derived_from_untrusted
            and action.source in attack.untrusted_sources
            for action in controlling
        ):
            _fail(f"{where}: an unsafe action must be derived from untrusted content")
    if category is BenchmarkCategory.FAULT_INJECTION and fault is None:
        _fail(f"{where}: fault_injection cases require fault metadata")
    if category is BenchmarkCategory.PRIVACY and not (protected_data or protected_resources):
        _fail(f"{where}: privacy cases require protected data/resources")
    tags = _string_tuple(data.get("tags", []), f"{where}.tags")
    return BenchmarkCase(
        schema_version=version,
        id=case_id,
        category=category,
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        environment=environment,
        scripted_actions=actions,
        allowed_actions=allowed,
        forbidden_actions=forbidden,
        allowed_resources=allowed_resources,
        forbidden_resources=forbidden_resources,
        protected_data=protected_data,
        protected_resources=protected_resources,
        budget=budget,
        attack=attack,
        fault=fault,
        ground_truth=truth,
        tags=tags,
    )


def _environment(value: Any, where: str) -> BenchmarkEnvironment:
    data = _mapping(value, where)
    _keys(data, _ENV_KEYS, set(), where)
    files = _string_map(data.get("files", {}), f"{where}.files")
    database = _mapping_map(data.get("database", {}), f"{where}.database")
    api_responses = dict(_mapping(data.get("api_responses", {}), f"{where}.api_responses"))
    robot = dict(_mapping(data.get("robot", {}), f"{where}.robot"))
    faults_raw = _mapping(data.get("faults", {}), f"{where}.faults")
    faults: dict[str, dict[str, Any]] = {}
    for key, item in faults_raw.items():
        fault_key = _string(key, f"{where}.faults key")
        fault_where = f"{where}.faults.{fault_key}"
        spec = dict(_mapping(item, fault_where))
        unknown = set(spec) - {"mode", "type", "latency_ms", "latency", "detail"}
        if unknown:
            _fail(f"{fault_where} has unknown keys: {sorted(unknown)}")
        if "mode" in spec and "type" in spec:
            _fail(f"{fault_where} cannot define both mode and type")
        mode = _string(spec.get("mode", spec.get("type")), f"{fault_where}.mode")
        if mode not in _FAULT_TYPES:
            _fail(f"{fault_where}.mode is unsupported: {mode!r}")
        if "latency_ms" in spec and "latency" in spec:
            _fail(f"{fault_where} cannot define both latency_ms and latency")
        latency = spec.get("latency_ms", spec.get("latency"))
        if latency is not None:
            _number(latency, f"{fault_where}.latency_ms", minimum=0)
        if "detail" in spec:
            _string(spec["detail"], f"{fault_where}.detail", empty=True)
        faults[fault_key] = spec
    return BenchmarkEnvironment(files, database, api_responses, robot, faults)


def _action(value: Any, where: str) -> Action:
    data = _mapping(value, where)
    _keys(data, _ACTION_KEYS, _ACTION_REQUIRED, where)
    tool = _string(data["tool"], f"{where}.tool")
    if tool not in SUPPORTED_TOOL_NAMES:
        _fail(f"{where}.tool is not registered: {tool!r}")
    severity = _string(data.get("risk_severity", "low"), f"{where}.risk_severity")
    if severity not in {"low", "medium", "high", "critical"}:
        _fail(f"{where}.risk_severity is invalid")
    derived = data.get("derived_from_untrusted", False)
    if not isinstance(derived, bool):
        _fail(f"{where}.derived_from_untrusted must be boolean")
    source = data.get("source")
    if source is not None:
        source = _string(source, f"{where}.source")
    return Action(
        action_id=_string(data["action_id"], f"{where}.action_id"),
        tool=tool,
        resource=_string(data["resource"], f"{where}.resource"),
        arguments=dict(_mapping(data["arguments"], f"{where}.arguments")),
        source=source,
        derived_from_untrusted=derived,
        risk_severity=severity,
    )


def _rules(value: Any, where: str) -> tuple[ActionRule, ...]:
    rules: list[ActionRule] = []
    for index, item in enumerate(_sequence(value, where)):
        entry_where = f"{where}[{index}]"
        if isinstance(item, str):
            if ":" not in item:
                _fail(f"{entry_where} string rule must be TOOL:RESOURCE")
            tool, resource = item.split(":", 1)
        else:
            data = _mapping(item, entry_where)
            _keys(data, _RULE_KEYS, _RULE_KEYS, entry_where)
            tool = _string(data["tool"], f"{entry_where}.tool")
            resource = _string(data["resource"], f"{entry_where}.resource")
        if tool not in SUPPORTED_TOOL_NAMES:
            _fail(f"{entry_where} references unregistered tool {tool!r}")
        rules.append(ActionRule(tool, resource))
    if len(rules) != len({(rule.tool, rule.resource) for rule in rules}):
        _fail(f"{where} contains duplicate rules")
    return tuple(rules)


def _budget(value: Any, where: str) -> BenchmarkBudget:
    data = _mapping(value, where)
    _keys(data, _BUDGET_KEYS, set(), where)
    values: dict[str, int | float | None] = {}
    for name in ("max_tool_calls", "max_model_calls", "max_tokens"):
        raw = data.get(name)
        values[name] = None if raw is None else _integer(raw, f"{where}.{name}", minimum=0)
    for name in ("max_cost", "max_runtime_ms"):
        raw = data.get(name)
        values[name] = None if raw is None else _number(raw, f"{where}.{name}", minimum=0)
    return BenchmarkBudget(
        max_tool_calls=cast(int | None, values["max_tool_calls"]),
        max_model_calls=cast(int | None, values["max_model_calls"]),
        max_tokens=cast(int | None, values["max_tokens"]),
        max_cost=cast(float | None, values["max_cost"]),
        max_runtime_ms=cast(float | None, values["max_runtime_ms"]),
    )


def _attack(value: Any, where: str) -> AttackSpec | None:
    if value is None:
        return None
    data = _mapping(value, where)
    _keys(data, _ATTACK_KEYS, _ATTACK_REQUIRED, where)
    return AttackSpec(
        type=_string(data["type"], f"{where}.type"),
        payload_location=_string(data["payload_location"], f"{where}.payload_location"),
        untrusted_sources=_string_tuple(data["untrusted_sources"], f"{where}.untrusted_sources"),
        description=_string(data.get("description", ""), f"{where}.description", empty=True),
    )


def _fault(value: Any, where: str) -> FaultSpec | None:
    if value is None:
        return None
    data = _mapping(value, where)
    _keys(data, _FAULT_KEYS, _FAULT_REQUIRED, where)
    hard_policy = data.get("hard_policy", True)
    if not isinstance(hard_policy, bool):
        _fail(f"{where}.hard_policy must be boolean")
    fault_type = _string(data["type"], f"{where}.type")
    if fault_type not in _FAULT_TYPES:
        _fail(f"{where}.type is unsupported: {fault_type!r}")
    return FaultSpec(
        type=fault_type,
        action_id=_string(data["action_id"], f"{where}.action_id"),
        hard_policy=hard_policy,
        description=_string(data.get("description", ""), f"{where}.description", empty=True),
    )


def _ground_truth(value: Any, where: str) -> GroundTruth:
    data = _mapping(value, where)
    _keys(data, _TRUTH_KEYS, _TRUTH_REQUIRED, where)
    expected_raw = _mapping(data.get("expected_output_contains", {}), f"{where}.expected_output_contains")
    expected_output = {
        _string(key, f"{where}.expected_output_contains key"): _string_tuple(
            item, f"{where}.expected_output_contains.{key}"
        )
        for key, item in expected_raw.items()
    }
    boolean_names = (
        "task_should_succeed",
        "safe_block_success",
        "protected_data_must_not_leak",
        "forbidden_action_must_not_execute",
        "fault_must_be_contained",
    )
    bools: dict[str, bool] = {}
    for name in boolean_names:
        raw = data.get(name, False)
        if not isinstance(raw, bool):
            _fail(f"{where}.{name} must be boolean")
        bools[name] = raw
    return GroundTruth(
        unsafe_action_ids=_string_tuple(data["unsafe_action_ids"], f"{where}.unsafe_action_ids"),
        expected_action_ids=_string_tuple(data["expected_action_ids"], f"{where}.expected_action_ids"),
        expected_output_contains=expected_output,
        **bools,
    )


def _keys(data: Mapping[str, Any], allowed: set[str], required: set[str], where: str) -> None:
    unknown = set(data) - allowed
    missing = required - set(data)
    if unknown:
        _fail(f"{where} has unknown keys: {sorted(unknown)}")
    if missing:
        _fail(f"{where} is missing keys: {sorted(missing)}")


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{where} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        _fail(f"{where} keys must be strings")
    return cast(Mapping[str, Any], value)


def _sequence(value: Any, where: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _fail(f"{where} must be a list")
    return cast(Sequence[Any], value)


def _string(value: Any, where: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value):
        _fail(f"{where} must be a {'string' if empty else 'non-empty string'}")
    return value


def _integer(value: Any, where: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{where} must be an integer >= {minimum}")
    return cast(int, value)


def _number(value: Any, where: str, *, minimum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        _fail(f"{where} must be a number >= {minimum}")
    return float(value)


def _string_tuple(value: Any, where: str) -> tuple[str, ...]:
    result = tuple(_string(item, f"{where}[{index}]") for index, item in enumerate(_sequence(value, where)))
    if len(result) != len(set(result)):
        _fail(f"{where} contains duplicates")
    return result


def _string_map(value: Any, where: str) -> dict[str, str]:
    data = _mapping(value, where)
    return {
        _string(key, f"{where} key"): _string(item, f"{where}.{key}", empty=True)
        for key, item in data.items()
    }


def _mapping_map(value: Any, where: str) -> dict[str, dict[str, Any]]:
    data = _mapping(value, where)
    return {
        _string(key, f"{where} key"): dict(_mapping(item, f"{where}.{key}"))
        for key, item in data.items()
    }


def _fail(message: str) -> NoReturn:
    raise BenchmarkValidationError(message)
