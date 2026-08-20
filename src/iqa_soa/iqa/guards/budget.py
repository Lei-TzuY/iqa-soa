"""Projected resource-budget enforcement."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Any

from iqa_soa.iqa.guards.base import QAGuard
from iqa_soa.types import Action, Decision, GuardResult, RuntimeContext, ToolResult

if TYPE_CHECKING:  # pragma: no cover
    from iqa_soa.iqa.policy import Policy


def _number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, parsed)


class BudgetGuard(QAGuard):
    name = "budget"
    order = 40
    phases = frozenset({"pre", "post"})

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
        budget = getattr(policy, "budget", None)
        if budget is None:
            return self.result(Decision.ALLOW, "no budget is configured", started_at=started)

        usage = context.usage
        projections = context.metadata.get("projected_usage", {})
        if not isinstance(projections, dict):
            projections = {}
        is_post = phase == "post" and tool_result is not None
        projected_tool_calls = usage.tool_calls + (0 if is_post else 1)
        projected_model_calls = usage.model_calls + (
            0
            if is_post
            else int(
                _number(
                    projections.get(
                        "model_calls", context.metadata.get("projected_model_calls")
                    )
                )
            )
        )
        projected_tokens = usage.input_tokens + usage.output_tokens + (
            0
            if is_post
            else int(
                _number(
                    projections.get(
                        "tokens", context.metadata.get("projected_tokens")
                    )
                )
            )
        )
        projected_runtime_ms = usage.elapsed_time_ms + (
            tool_result.latency_ms
            if is_post and tool_result is not None
            else _number(
                projections.get(
                    "runtime_ms", context.metadata.get("projected_runtime_ms")
                )
            )
        )
        incremental_cost_value = projections.get(
            "cost", context.metadata.get("projected_cost")
        )
        projected_cost: float | None
        if usage.estimated_cost is None and incremental_cost_value is None:
            projected_cost = None
        else:
            projected_cost = _number(usage.estimated_cost) + (
                0.0 if is_post else _number(incremental_cost_value)
            )

        checks: tuple[tuple[str, float | int | None, float | int | None], ...] = (
            ("max_tool_calls", projected_tool_calls, getattr(budget, "max_tool_calls", None)),
            ("max_model_calls", projected_model_calls, getattr(budget, "max_model_calls", None)),
            ("max_tokens", projected_tokens, getattr(budget, "max_tokens", None)),
            ("max_cost", projected_cost, getattr(budget, "max_cost", None)),
            (
                "max_runtime_ms",
                projected_runtime_ms,
                getattr(budget, "max_runtime_ms", getattr(budget, "max_runtime", None)),
            ),
        )
        policy_id = getattr(policy, "policy_id", None)
        for name, projected, limit in checks:
            if limit is not None and projected is not None and projected > limit:
                return self.result(
                    Decision.BLOCK,
                    f"projected usage exceeds {name}",
                    started_at=started,
                    severity="high",
                    matched_policy=(f"{policy_id}:budget:{name}" if policy_id else f"budget:{name}"),
                    metadata={
                        "budget": name,
                        "projected": projected,
                        "limit": limit,
                        "phase": phase,
                    },
                )

        return self.result(
            Decision.ALLOW,
            "projected call, model, token, cost, and runtime budgets pass",
            started_at=started,
            matched_policy=(f"{policy_id}:budget" if policy_id else None),
            metadata={
                "projected_tool_calls": projected_tool_calls,
                "projected_model_calls": projected_model_calls,
                "projected_tokens": projected_tokens,
                "projected_cost": projected_cost,
                "projected_runtime_ms": projected_runtime_ms,
                "phase": phase,
            },
        )


__all__ = ["BudgetGuard"]
