"""Dependency-light typed benchmark schema.

Benchmark labels are available to the evaluator, never copied into runtime
guard context.  This separation prevents a guard from succeeding by consulting
the answer key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatchcase
from typing import Any, Mapping, cast

from iqa_soa.types import Action


SUPPORTED_TOOL_NAMES = frozenset(
    {
        "file.read",
        "file.write",
        "database.query",
        "database.update",
        "database.delete",
        "message.send",
        "api.call",
        "shell.execute_simulated",
        "robot.move_simulated",
        "robot.pick_up_simulated",
    }
)


class BenchmarkCategory(str, Enum):
    BENIGN = "benign"
    PROMPT_INJECTION = "prompt_injection"
    UNAUTHORIZED_ACTION = "unauthorized_action"
    PRIVACY = "privacy"
    KNOWLEDGE_POISONING = "knowledge_poisoning"
    BUDGET = "budget"
    FAULT_INJECTION = "fault_injection"


@dataclass(frozen=True, slots=True)
class ActionRule:
    tool: str
    resource: str

    def matches(self, action: Action) -> bool:
        return self.tool == action.tool and fnmatchcase(action.resource, self.resource)


@dataclass(frozen=True, slots=True)
class BenchmarkEnvironment:
    files: dict[str, str] = field(default_factory=dict)
    database: dict[str, dict[str, Any]] = field(default_factory=dict)
    api_responses: dict[str, Any] = field(default_factory=dict)
    robot: dict[str, Any] = field(default_factory=dict)
    faults: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": _deep_copy(self.files),
            "database": _deep_copy(self.database),
            "api_responses": _deep_copy(self.api_responses),
            "robot": _deep_copy(self.robot),
            "robot_position": _deep_copy(self.robot.get("position")),
            "faults": _deep_copy(self.faults),
        }


@dataclass(frozen=True, slots=True)
class BenchmarkBudget:
    max_tool_calls: int | None = None
    max_model_calls: int | None = None
    max_tokens: int | None = None
    max_cost: float | None = None
    max_runtime_ms: float | None = None

    def to_dict(self) -> dict[str, int | float | None]:
        return {
            "max_tool_calls": self.max_tool_calls,
            "max_model_calls": self.max_model_calls,
            "max_tokens": self.max_tokens,
            "max_cost": self.max_cost,
            "max_runtime_ms": self.max_runtime_ms,
        }


@dataclass(frozen=True, slots=True)
class AttackSpec:
    type: str
    payload_location: str
    untrusted_sources: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True, slots=True)
class FaultSpec:
    type: str
    action_id: str
    hard_policy: bool = True
    description: str = ""


@dataclass(frozen=True, slots=True)
class GroundTruth:
    unsafe_action_ids: tuple[str, ...]
    expected_action_ids: tuple[str, ...]
    task_should_succeed: bool
    expected_output_contains: dict[str, tuple[str, ...]] = field(default_factory=dict)
    safe_block_success: bool = False
    protected_data_must_not_leak: bool = False
    forbidden_action_must_not_execute: bool = False
    fault_must_be_contained: bool = False


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    schema_version: int
    id: str
    category: BenchmarkCategory
    user_prompt: str
    system_prompt: str
    environment: BenchmarkEnvironment
    scripted_actions: tuple[Action, ...]
    allowed_actions: tuple[ActionRule, ...]
    forbidden_actions: tuple[ActionRule, ...]
    allowed_resources: tuple[str, ...]
    forbidden_resources: tuple[str, ...]
    protected_data: tuple[str, ...]
    protected_resources: tuple[str, ...]
    budget: BenchmarkBudget
    ground_truth: GroundTruth
    attack: AttackSpec | None = None
    fault: FaultSpec | None = None
    tags: tuple[str, ...] = ()

    @property
    def action_ids(self) -> frozenset[str]:
        return frozenset(action.action_id for action in self.scripted_actions)

    @property
    def canonical_resources(self) -> tuple[str, ...]:
        """The case's declared finite resource vocabulary.

        Derived only from data the case already declares -- environment
        backing-store keys (``files``/``database``/``api_responses``) and any
        *literal* (non-wildcard) entry in ``allowed_resources``,
        ``forbidden_resources``, or ``protected_resources``.  Wildcard
        patterns are excluded because they are not themselves proposable
        identifiers.  This never reads ``ground_truth`` or ``scripted_actions``,
        so it cannot leak which resource is the intended safe/unsafe answer:
        allowed and forbidden identifiers are exposed together,
        undifferentiated, exactly as a real resource listing would show them.
        """

        values: set[str] = set()
        values.update(self.environment.files)
        values.update(self.environment.database)
        values.update(self.environment.api_responses)
        for group in (
            self.allowed_resources,
            self.forbidden_resources,
            self.protected_resources,
        ):
            values.update(item for item in group if "*" not in item)
        return tuple(sorted(values))

    def initial_state_dict(self) -> dict[str, Any]:
        """Return a deep copy suitable for a fresh isolated treatment arm."""

        return self.environment.to_dict()


def _deep_copy(value: Any) -> Any:
    """Copy benchmark JSON-compatible values without importing runtime state."""

    if isinstance(value, dict):
        return {str(key): _deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_deep_copy(item) for item in value)
    return value


def rule_contradictions(
    allowed: tuple[ActionRule, ...], forbidden: tuple[ActionRule, ...]
) -> tuple[str, ...]:
    """Return exact contradictory allow/deny rules.

    Wildcard overlap is intentionally left to the policy engine's deny-first
    precedence; exact duplicates are almost certainly benchmark author error.
    """

    allow_keys = {(rule.tool, rule.resource) for rule in allowed}
    deny_keys = {(rule.tool, rule.resource) for rule in forbidden}
    return tuple(f"{tool}:{resource}" for tool, resource in sorted(allow_keys & deny_keys))


def as_jsonable_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], _deep_copy(dict(value)))
