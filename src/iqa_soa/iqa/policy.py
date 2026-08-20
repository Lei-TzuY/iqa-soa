"""Typed executable policy model for the minimal QA-XML v0.1 subset.

The research proposal positions QA-XML as an executable intermediate
representation rather than an informal configuration file.  These immutable
value objects are the boundary between XML compilation and IQA-SOA runtime
guards.  The representation is deliberately small for the FSE prototype while
retaining an explicit ``extensions`` mapping for future AST/SMT metadata.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from typing import Any, Literal, TypeAlias, cast


PermissionEffect: TypeAlias = Literal["allow", "deny"]
OutputFormat: TypeAlias = Literal["json", "object", "text"]

_EFFECTS = frozenset({"allow", "deny"})
_RISK_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
_OUTPUT_FORMATS = frozenset({"json", "object", "text"})
_BUDGET_FIELDS = (
    "max_tool_calls",
    "max_model_calls",
    "max_tokens",
    "max_cost",
    "max_runtime_ms",
)


class PolicyConflictError(ValueError):
    """Raised when one exact tool/resource pair is both allowed and denied."""

    def __init__(self, conflicts: Iterable[tuple[str, str]]) -> None:
        ordered = tuple(sorted(set(conflicts)))
        rendered = ", ".join(f"{tool}:{resource}" for tool, resource in ordered)
        super().__init__(f"contradictory exact permission rules: {rendered}")
        self.conflicts = ordered


def _non_empty_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    values: Iterable[object]
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Iterable):
        values = value
    else:
        raise TypeError(f"{field_name} must be a string or iterable of strings")

    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        normalized = _non_empty_text(item, field_name)
        if normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return tuple(result)


def _strict_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be boolean")
    return value


def _optional_count(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or None")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _optional_number(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric or None")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return normalized


@dataclass(frozen=True, slots=True)
class PermissionRule:
    """One deny-first glob rule over a normalized tool/resource pair."""

    effect: PermissionEffect
    tool: str
    resource: str = "*"
    rule_id: str | None = None

    def __post_init__(self) -> None:
        effect = _non_empty_text(self.effect, "effect").lower()
        if effect not in _EFFECTS:
            raise ValueError("effect must be 'allow' or 'deny'")
        object.__setattr__(self, "effect", cast(PermissionEffect, effect))
        object.__setattr__(self, "tool", _non_empty_text(self.tool, "tool"))
        object.__setattr__(
            self, "resource", _non_empty_text(self.resource, "resource")
        )
        if self.rule_id is not None:
            object.__setattr__(
                self, "rule_id", _non_empty_text(self.rule_id, "rule_id")
            )

    def matches(self, tool: str, resource: str) -> bool:
        """Return whether both values match this rule's case-sensitive globs."""

        normalized_resource = resource.replace("\\", "/")
        resource_pattern = self.resource.replace("\\", "/")
        return fnmatchcase(tool, self.tool) and fnmatchcase(
            normalized_resource, resource_pattern
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "effect": self.effect,
            "tool": self.tool,
            "resource": self.resource,
            "rule_id": self.rule_id,
        }


@dataclass(frozen=True, slots=True)
class PrivacyPolicy:
    """Benchmark-grounded resources and literal values that must be protected."""

    protected_resources: tuple[str, ...] = ()
    protected_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "protected_resources",
            _string_tuple(self.protected_resources, "protected_resources"),
        )
        object.__setattr__(
            self,
            "protected_values",
            _string_tuple(self.protected_values, "protected_values"),
        )


@dataclass(frozen=True, slots=True)
class Budget:
    """Hard per-run resource ceilings used by the deterministic budget guard.

    Runtime is represented internally in milliseconds.  ``from_constraints``
    additionally accepts ``max_runtime`` in seconds and converts it explicitly.
    """

    max_tool_calls: int | None = None
    max_model_calls: int | None = None
    max_tokens: int | None = None
    max_cost: float | None = None
    max_runtime_ms: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_tool_calls",
            _optional_count(self.max_tool_calls, "max_tool_calls"),
        )
        object.__setattr__(
            self,
            "max_model_calls",
            _optional_count(self.max_model_calls, "max_model_calls"),
        )
        object.__setattr__(
            self, "max_tokens", _optional_count(self.max_tokens, "max_tokens")
        )
        object.__setattr__(
            self, "max_cost", _optional_number(self.max_cost, "max_cost")
        )
        object.__setattr__(
            self,
            "max_runtime_ms",
            _optional_number(self.max_runtime_ms, "max_runtime_ms"),
        )

    @property
    def max_runtime(self) -> float | None:
        """Compatibility view of the runtime ceiling in seconds."""

        if self.max_runtime_ms is None:
            return None
        return self.max_runtime_ms / 1000.0

    @classmethod
    def from_constraints(cls, value: object) -> Budget:
        """Normalize a budget object or mapping into milliseconds.

        A mapping may contain either ``max_runtime_ms`` or ``max_runtime``.
        The latter is interpreted as seconds.  Providing both is rejected.
        Benchmark budget dataclasses exposing these named attributes are also
        accepted so callers do not need to couple the policy module to a loader.
        """

        if isinstance(value, cls):
            return value

        if isinstance(value, Mapping):
            supplied = dict(value)
        else:
            supplied = {
                name: getattr(value, name)
                for name in (*_BUDGET_FIELDS, "max_runtime")
                if hasattr(value, name)
            }
            if not supplied:
                raise TypeError("budget must be a Budget, mapping, or budget-like object")

        unknown = set(supplied) - {*_BUDGET_FIELDS, "max_runtime"}
        if unknown:
            rendered = ", ".join(sorted(str(key) for key in unknown))
            raise ValueError(f"unknown budget constraint(s): {rendered}")
        if supplied.get("max_runtime") is not None and supplied.get(
            "max_runtime_ms"
        ) is not None:
            raise ValueError("budget cannot define both max_runtime and max_runtime_ms")

        runtime_ms = supplied.get("max_runtime_ms")
        if supplied.get("max_runtime") is not None:
            seconds = _optional_number(supplied["max_runtime"], "max_runtime")
            runtime_ms = None if seconds is None else seconds * 1000.0

        return cls(
            max_tool_calls=supplied.get("max_tool_calls"),
            max_model_calls=supplied.get("max_model_calls"),
            max_tokens=supplied.get("max_tokens"),
            max_cost=supplied.get("max_cost"),
            max_runtime_ms=runtime_ms,
        )

    def narrowed_by(self, other: Budget) -> Budget:
        """Return the component-wise stricter combination of two budgets."""

        def minimum(left: int | float | None, right: int | float | None) -> Any:
            if left is None:
                return right
            if right is None:
                return left
            return min(left, right)

        return Budget(
            max_tool_calls=minimum(self.max_tool_calls, other.max_tool_calls),
            max_model_calls=minimum(self.max_model_calls, other.max_model_calls),
            max_tokens=minimum(self.max_tokens, other.max_tokens),
            max_cost=minimum(self.max_cost, other.max_cost),
            max_runtime_ms=minimum(self.max_runtime_ms, other.max_runtime_ms),
        )


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Severity thresholds at or above which human confirmation is required."""

    require_confirmation: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        severities = tuple(
            item.lower()
            for item in _string_tuple(
                self.require_confirmation, "require_confirmation"
            )
        )
        unknown = set(severities) - _RISK_SEVERITIES
        if unknown:
            raise ValueError(
                "unknown risk severity: " + ", ".join(sorted(unknown))
            )
        object.__setattr__(self, "require_confirmation", severities)


@dataclass(frozen=True, slots=True)
class InjectionPolicy:
    """Deterministic regular expressions for benchmark-defined attack content."""

    patterns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        patterns = _string_tuple(self.patterns, "patterns")
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid injection pattern {pattern!r}: {exc}") from exc
        object.__setattr__(self, "patterns", patterns)


@dataclass(frozen=True, slots=True)
class OutputValidationPolicy:
    """Deterministic requirements checked on outbound payloads/tool results."""

    required_fields: tuple[str, ...] = ()
    forbidden_values: tuple[str, ...] = ()
    require_evidence: bool = False
    required_format: OutputFormat | None = None
    require_tool_support: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_fields",
            _string_tuple(self.required_fields, "required_fields"),
        )
        object.__setattr__(
            self,
            "forbidden_values",
            _string_tuple(self.forbidden_values, "forbidden_values"),
        )
        object.__setattr__(
            self,
            "require_evidence",
            _strict_bool(self.require_evidence, "require_evidence"),
        )
        object.__setattr__(
            self,
            "require_tool_support",
            _strict_bool(self.require_tool_support, "require_tool_support"),
        )
        if self.required_format is not None:
            normalized = _non_empty_text(
                self.required_format, "required_format"
            ).lower()
            if normalized not in _OUTPUT_FORMATS:
                raise ValueError(
                    "required_format must be one of: json, object, text"
                )
            object.__setattr__(
                self, "required_format", cast(OutputFormat, normalized)
            )


@dataclass(frozen=True, slots=True)
class Policy:
    """Validated executable QA constraints consumed by IQA-SOA guards."""

    policy_id: str
    version: str = "0.1"
    permissions: tuple[PermissionRule, ...] = ()
    privacy: PrivacyPolicy = field(default_factory=PrivacyPolicy)
    budget: Budget = field(default_factory=Budget)
    risk: RiskPolicy = field(default_factory=RiskPolicy)
    injection: InjectionPolicy = field(default_factory=InjectionPolicy)
    output_validation: OutputValidationPolicy = field(
        default_factory=OutputValidationPolicy
    )
    extensions: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "policy_id", _non_empty_text(self.policy_id, "policy_id")
        )
        object.__setattr__(
            self, "version", _non_empty_text(self.version, "version")
        )
        permissions = tuple(self.permissions)
        if not all(isinstance(rule, PermissionRule) for rule in permissions):
            raise TypeError("permissions must contain only PermissionRule values")
        permissions = tuple(dict.fromkeys(permissions))
        conflicts = _permission_conflicts(permissions)
        if conflicts:
            raise PolicyConflictError(conflicts)
        object.__setattr__(self, "permissions", permissions)

        for name, expected in (
            ("privacy", PrivacyPolicy),
            ("budget", Budget),
            ("risk", RiskPolicy),
            ("injection", InjectionPolicy),
            ("output_validation", OutputValidationPolicy),
        ):
            if not isinstance(getattr(self, name), expected):
                raise TypeError(f"{name} must be {expected.__name__}")

        if not isinstance(self.extensions, Mapping):
            raise TypeError("extensions must be a mapping")
        object.__setattr__(self, "extensions", dict(self.extensions))

    @property
    def allow_rules(self) -> tuple[PermissionRule, ...]:
        return tuple(rule for rule in self.permissions if rule.effect == "allow")

    @property
    def deny_rules(self) -> tuple[PermissionRule, ...]:
        return tuple(rule for rule in self.permissions if rule.effect == "deny")

    def permission_for(
        self, tool: str, resource: str
    ) -> PermissionEffect | None:
        """Resolve permission deterministically; any matching deny wins."""

        matching = tuple(
            rule for rule in self.permissions if rule.matches(tool, resource)
        )
        if any(rule.effect == "deny" for rule in matching):
            return "deny"
        if any(rule.effect == "allow" for rule in matching):
            return "allow"
        return None

    def with_case_constraints(
        self,
        *,
        allowed_actions: Sequence[object] = (),
        forbidden_actions: Sequence[object] = (),
        allowed_resources: Sequence[str] = (),
        forbidden_resources: Sequence[str] = (),
        protected_resources: Sequence[str] = (),
        protected_values: Sequence[str] = (),
        budget: Budget | Mapping[str, object] | object | None = None,
        injection_patterns: Sequence[str] = (),
        output_required_fields: Sequence[str] = (),
        output_forbidden_values: Sequence[str] = (),
        output_require_evidence: bool | None = None,
    ) -> Policy:
        """Return a policy narrowed by benchmark case constraints.

        Case allow rules replace (rather than union with) base allow rules so a
        broad base policy cannot widen a benchmark allowlist.  Base deny rules
        are always retained, and case denies are added.  When both action and
        resource allowlists are supplied they are combined conjunctively.

        ``budget`` may use ``max_runtime`` in seconds or ``max_runtime_ms``;
        both normalize to the internal millisecond field before the stricter
        component-wise budget is selected.
        """

        case_allows = _case_allow_rules(allowed_actions, allowed_resources)
        base_denies = self.deny_rules
        base_allows = self.allow_rules
        allow_constraints_present = bool(allowed_actions or allowed_resources)
        merged_allows = case_allows if allow_constraints_present else base_allows

        case_denies = tuple(
            _coerce_rule(item, "deny") for item in forbidden_actions
        ) + tuple(
            PermissionRule("deny", "*", resource)
            for resource in _string_tuple(
                forbidden_resources, "forbidden_resources"
            )
        )
        merged_permissions = tuple(
            dict.fromkeys((*merged_allows, *base_denies, *case_denies))
        )

        privacy = PrivacyPolicy(
            protected_resources=(*self.privacy.protected_resources, *protected_resources),
            protected_values=(*self.privacy.protected_values, *protected_values),
        )
        merged_budget = self.budget
        if budget is not None:
            merged_budget = merged_budget.narrowed_by(Budget.from_constraints(budget))

        injection = InjectionPolicy(
            patterns=(*self.injection.patterns, *injection_patterns)
        )
        require_evidence = self.output_validation.require_evidence
        if output_require_evidence is not None:
            require_evidence = require_evidence or _strict_bool(
                output_require_evidence, "output_require_evidence"
            )
        output = OutputValidationPolicy(
            required_fields=(
                *self.output_validation.required_fields,
                *output_required_fields,
            ),
            forbidden_values=(
                *self.output_validation.forbidden_values,
                *output_forbidden_values,
            ),
            require_evidence=require_evidence,
            required_format=self.output_validation.required_format,
            require_tool_support=self.output_validation.require_tool_support,
        )

        return Policy(
            policy_id=self.policy_id,
            version=self.version,
            permissions=merged_permissions,
            privacy=privacy,
            budget=merged_budget,
            risk=self.risk,
            injection=injection,
            output_validation=output,
            extensions=self.extensions,
        )

    def to_dict(self, *, include_protected_values: bool = False) -> dict[str, Any]:
        """Return a JSON-compatible representation, redacting secrets by default."""

        privacy: dict[str, Any] = {
            "protected_resources": list(self.privacy.protected_resources),
            "protected_value_count": len(self.privacy.protected_values),
        }
        if include_protected_values:
            privacy["protected_values"] = list(self.privacy.protected_values)
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "permissions": [rule.to_dict() for rule in self.permissions],
            "privacy": privacy,
            "budget": {
                name: getattr(self.budget, name) for name in _BUDGET_FIELDS
            },
            "risk": {
                "require_confirmation": list(self.risk.require_confirmation)
            },
            "injection": {"patterns": list(self.injection.patterns)},
            "output_validation": {
                "required_fields": list(self.output_validation.required_fields),
                "forbidden_values": list(self.output_validation.forbidden_values),
                "require_evidence": self.output_validation.require_evidence,
                "required_format": self.output_validation.required_format,
                "require_tool_support": self.output_validation.require_tool_support,
            },
            "extensions": dict(self.extensions),
        }


def _permission_conflicts(
    permissions: Sequence[PermissionRule],
) -> tuple[tuple[str, str], ...]:
    allows = {
        (rule.tool, rule.resource) for rule in permissions if rule.effect == "allow"
    }
    denies = {
        (rule.tool, rule.resource) for rule in permissions if rule.effect == "deny"
    }
    return tuple(sorted(allows & denies))


def _coerce_rule(value: object, effect: PermissionEffect) -> PermissionRule:
    if isinstance(value, PermissionRule):
        if value.effect == effect:
            return value
        return PermissionRule(effect, value.tool, value.resource, value.rule_id)

    if isinstance(value, str):
        if ":" in value:
            tool, resource = value.split(":", 1)
        else:
            tool, resource = value, "*"
        return PermissionRule(effect, tool, resource)

    if isinstance(value, Mapping):
        tool = value.get("tool", value.get("action"))
        if tool is None:
            raise ValueError("permission mapping requires 'tool' or 'action'")
        resource = value.get("resource", "*")
        rule_id = value.get("rule_id", value.get("id"))
        return PermissionRule(
            effect,
            _non_empty_text(tool, "tool"),
            _non_empty_text(resource, "resource"),
            None if rule_id is None else _non_empty_text(rule_id, "rule_id"),
        )

    if hasattr(value, "tool") and hasattr(value, "resource"):
        rule_id = getattr(value, "rule_id", None)
        return PermissionRule(
            effect,
            _non_empty_text(getattr(value, "tool"), "tool"),
            _non_empty_text(getattr(value, "resource"), "resource"),
            None if rule_id is None else _non_empty_text(rule_id, "rule_id"),
        )
    raise TypeError(
        "permission constraint must be a rule, 'tool:resource' string, mapping, "
        "or object exposing tool/resource"
    )


def _intersect_resource_patterns(
    action_pattern: str, resource_pattern: str
) -> str | None:
    if action_pattern == "*":
        return resource_pattern
    if resource_pattern == "*" or action_pattern == resource_pattern:
        return action_pattern

    action_is_literal = not any(char in action_pattern for char in "*?[")
    resource_is_literal = not any(char in resource_pattern for char in "*?[")
    if action_is_literal and fnmatchcase(action_pattern, resource_pattern):
        return action_pattern
    if resource_is_literal and fnmatchcase(resource_pattern, action_pattern):
        return resource_pattern
    if action_is_literal or resource_is_literal:
        # A literal not matched by the other glob proves this pair disjoint.
        return None
    # Disjoint literal prefixes before the first wildcard also prove that two
    # simple path globs cannot intersect (for example public/* vs private/*).
    action_prefix = re.split(r"[*?[]", action_pattern, maxsplit=1)[0]
    resource_prefix = re.split(r"[*?[]", resource_pattern, maxsplit=1)[0]
    if (
        action_prefix
        and resource_prefix
        and not action_prefix.startswith(resource_prefix)
        and not resource_prefix.startswith(action_prefix)
    ):
        return None
    raise ValueError(
        "ambiguous intersection between action resource pattern "
        f"{action_pattern!r} and allowed resource pattern {resource_pattern!r}; "
        "encode the combined tool/resource rule explicitly"
    )


def _case_allow_rules(
    actions: Sequence[object], resources: Sequence[str]
) -> tuple[PermissionRule, ...]:
    action_rules = tuple(_coerce_rule(item, "allow") for item in actions)
    resource_patterns = _string_tuple(resources, "allowed_resources")
    if not resource_patterns:
        return action_rules
    if not action_rules:
        return tuple(
            PermissionRule("allow", "*", resource) for resource in resource_patterns
        )

    combined: list[PermissionRule] = []
    for action_rule in action_rules:
        for resource in resource_patterns:
            try:
                intersection = _intersect_resource_patterns(
                    action_rule.resource, resource
                )
            except ValueError:
                raise
            if intersection is None:
                continue
            combined.append(
                PermissionRule(
                    "allow", action_rule.tool, intersection, action_rule.rule_id
                )
            )
    if not combined:
        raise ValueError("action and resource allowlists have an empty intersection")
    return tuple(dict.fromkeys(combined))


def merge_case_constraints(policy: Policy, **constraints: Any) -> Policy:
    """Functional alias for :meth:`Policy.with_case_constraints`."""

    return policy.with_case_constraints(**constraints)


__all__ = [
    "Budget",
    "InjectionPolicy",
    "OutputValidationPolicy",
    "PermissionEffect",
    "PermissionRule",
    "Policy",
    "PolicyConflictError",
    "PrivacyPolicy",
    "RiskPolicy",
    "merge_case_constraints",
]
