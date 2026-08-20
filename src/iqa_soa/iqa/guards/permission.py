"""Deterministic tool/resource authorization using glob rules."""

from __future__ import annotations

from fnmatch import fnmatchcase
from time import perf_counter
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from iqa_soa.iqa.guards.base import QAGuard
from iqa_soa.types import Action, Decision, GuardResult, RuntimeContext, ToolResult

if TYPE_CHECKING:  # pragma: no cover
    from iqa_soa.iqa.policy import PermissionRule, Policy


_SEVERITY = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_TOOL_RISK_FLOOR = {
    # A proposer cannot label destructive/high-consequence operations as low.
    "message.send": "high",
    "database.update": "high",
    "database.delete": "high",
    "api.call": "high",
    "shell.execute_simulated": "high",
    "robot.move_simulated": "high",
    "robot.pick_up_simulated": "high",
}


def _entry_matches(entry: Any, action: Action) -> bool:
    """Match common benchmark constraint encodings without weakening policy rules."""

    if isinstance(entry, str):
        if ":" in entry:
            tool, resource = entry.split(":", 1)
        else:
            tool, resource = entry, "*"
        return fnmatchcase(action.tool, tool) and fnmatchcase(
            action.resource.replace("\\", "/"), resource.replace("\\", "/")
        )
    if isinstance(entry, Mapping):
        tool = str(entry.get("tool", entry.get("action", "*")))
        resource = str(entry.get("resource", "*"))
        return fnmatchcase(action.tool, tool) and fnmatchcase(
            action.resource.replace("\\", "/"), resource.replace("\\", "/")
        )
    return False


class PermissionGuard(QAGuard):
    name = "permission"
    order = 20

    def evaluate(
        self,
        action: Action,
        context: RuntimeContext,
        policy: Policy,
        *,
        tool_result: ToolResult | None = None,
        phase: str = "pre",
    ) -> GuardResult:
        started = perf_counter()
        policy_id = getattr(policy, "policy_id", None)

        rules: Iterable[PermissionRule] = getattr(policy, "permissions", ())
        matched_denies: list[Any] = []
        matched_allows: list[Any] = []
        allow_rules: list[Any] = []
        for rule in rules:
            effect = str(getattr(rule, "effect", "")).lower()
            if effect == "allow":
                allow_rules.append(rule)
            matches = bool(rule.matches(action.tool, action.resource))
            if matches and effect == "deny":
                matched_denies.append(rule)
            elif matches and effect == "allow":
                matched_allows.append(rule)

        metadata = context.metadata
        forbidden = tuple(metadata.get("forbidden_actions", ()))
        allowed = tuple(metadata.get("allowed_actions", ()))
        forbidden_tools = tuple(metadata.get("forbidden_tools", ()))
        allowed_tools = tuple(metadata.get("allowed_tools", ()))
        forbidden_resources = tuple(metadata.get("forbidden_resources", ()))
        allowed_resources = tuple(metadata.get("allowed_resources", ()))
        case_deny = (
            any(_entry_matches(item, action) for item in forbidden)
            or any(fnmatchcase(action.tool, str(item)) for item in forbidden_tools)
            or any(
                fnmatchcase(
                    action.resource.replace("\\", "/"), str(item).replace("\\", "/")
                )
                for item in forbidden_resources
            )
        )
        case_allow_configured = bool(allowed or allowed_tools or allowed_resources)
        action_allowed = not allowed or any(_entry_matches(item, action) for item in allowed)
        tool_allowed = not allowed_tools or any(
            fnmatchcase(action.tool, str(item)) for item in allowed_tools
        )
        resource_allowed = not allowed_resources or any(
            fnmatchcase(
                action.resource.replace("\\", "/"), str(item).replace("\\", "/")
            )
            for item in allowed_resources
        )
        case_allow = action_allowed and tool_allowed and resource_allowed

        if matched_denies or case_deny:
            matched = matched_denies[0] if matched_denies else None
            clause = getattr(matched, "rule_id", None) or "deny"
            return self.result(
                Decision.BLOCK,
                "an explicit deny rule matched the proposed action",
                started_at=started,
                severity="high",
                matched_policy=(f"{policy_id}:permissions:{clause}" if policy_id else clause),
                metadata={"deny_wins": True, "case_constraint": case_deny},
            )

        if allow_rules and not matched_allows:
            return self.result(
                Decision.BLOCK,
                "action is outside the policy allowlist",
                started_at=started,
                severity="high",
                matched_policy=(f"{policy_id}:permissions:allowlist" if policy_id else "allowlist"),
                metadata={"default_deny": True},
            )
        if case_allow_configured and not case_allow:
            return self.result(
                Decision.BLOCK,
                "action is outside the benchmark case allowlist",
                started_at=started,
                severity="high",
                matched_policy=(f"{policy_id}:case-constraints" if policy_id else "case-constraints"),
                metadata={"default_deny": True, "case_constraint": True},
            )

        # Confirmation is meaningful only after authorization succeeds.  A
        # forbidden high-risk action must remain a definitive permission BLOCK,
        # never become a weaker confirmation ESCALATE.
        required = tuple(
            getattr(getattr(policy, "risk", None), "require_confirmation", ())
        )
        declared_severity = action.risk_severity.lower()
        risk_floor = _TOOL_RISK_FLOOR.get(action.tool, "low")
        effective_severity = max(
            (declared_severity, risk_floor), key=lambda item: _SEVERITY.get(item, 1)
        )
        action_level = _SEVERITY.get(effective_severity, 1)
        for threshold in required:
            threshold_text = str(threshold).lower()
            if (
                action_level >= _SEVERITY.get(threshold_text, 99)
                and not context.confirmed_high_risk
            ):
                return self.result(
                    Decision.ESCALATE,
                    f"{effective_severity} risk action requires confirmation",
                    started_at=started,
                    severity=effective_severity,
                    matched_policy=(
                        f"{policy_id}:risk:{threshold_text}"
                        if policy_id
                        else f"risk:{threshold_text}"
                    ),
                    metadata={
                        "required_confirmation": threshold_text,
                        "declared_severity": declared_severity,
                        "tool_risk_floor": risk_floor,
                        "effective_severity": effective_severity,
                    },
                )

        return self.result(
            Decision.ALLOW,
            "tool and resource permission checks passed",
            started_at=started,
            matched_policy=(f"{policy_id}:permissions" if policy_id else None),
            metadata={"matched_allow": bool(matched_allows or case_allow_configured)},
        )


__all__ = ["PermissionGuard"]
