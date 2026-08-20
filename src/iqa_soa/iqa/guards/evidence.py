"""Evidence-readiness QA Module for the narrowed QA-IUM prototype."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from iqa_soa.iqa.guards.base import QAGuard
from iqa_soa.types import Action, Decision, GuardResult, RuntimeContext, ToolResult

if TYPE_CHECKING:  # pragma: no cover
    from iqa_soa.iqa.policy import Policy


class EvidenceGuard(QAGuard):
    """Declare the trace fields the gateway/logger can make measurable."""

    name = "evidence"
    order = 60

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
        return self.result(
            Decision.ALLOW,
            "detailed evidence capture is enabled",
            started_at=started,
            matched_policy=(f"{policy_id}:evidence" if policy_id else "evidence"),
            metadata={
                "completeness_fields": [
                    "decision_trace_available",
                    "policy_reference_available",
                    "blocking_reason_available",
                    "tool_trace_available",
                ],
                "qa_ium_compatible_fragment": True,
                "full_graph_database": False,
                "tamper_proof": False,
            },
        )


__all__ = ["EvidenceGuard"]
