"""QA-IUM-compatible evidence-fragment helpers.

The FSE prototype stores append-only JSONL fragments.  These fields preserve a
future path to the proposal's evidence DAG, but this module deliberately does not
claim to implement a graph database, cryptographic ledger, or tamper proofing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from iqa_soa.types import Decision, GuardResult, ToolResult


@dataclass(frozen=True, slots=True)
class EvidenceCompleteness:
    decision_trace_available: bool
    policy_reference_available: bool
    blocking_reason_available: bool
    tool_trace_available: bool

    @property
    def score(self) -> float:
        values = (
            self.decision_trace_available,
            self.policy_reference_available,
            self.blocking_reason_available,
            self.tool_trace_available,
        )
        return sum(values) / len(values)

    def to_dict(self) -> dict[str, bool | float]:
        return {
            "decision_trace_available": self.decision_trace_available,
            "policy_reference_available": self.policy_reference_available,
            "blocking_reason_available": self.blocking_reason_available,
            "tool_trace_available": self.tool_trace_available,
            "evidence_completeness": self.score,
        }


def evidence_completeness(
    *,
    guard_results: Sequence[GuardResult],
    policy_id: str | None,
    reason: str | None,
    executed: bool,
    tool_result: ToolResult | None,
) -> EvidenceCompleteness:
    """Calculate the four documented auditability proxies."""

    return EvidenceCompleteness(
        decision_trace_available=bool(guard_results),
        policy_reference_available=bool(policy_id),
        blocking_reason_available=bool(reason),
        # A blocked action has an explicit no-execution trace; an executed action
        # is complete only when its ToolResult is present.
        tool_trace_available=(not executed) or tool_result is not None,
    )


def causal_links(
    *,
    policy_id: str | None,
    policy_version: str | None,
    guard_results: Sequence[GuardResult],
    decision: Decision,
    blocking_guard: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the proposal's requirement-to-disposition causal-link projection."""

    matched = [item.matched_policy for item in guard_results if item.matched_policy]
    return {
        "requirement": metadata.get("requirement_id"),
        "derived_constraints": matched,
        "bound_checkpoints": [item.guard_name for item in guard_results],
        "triggered_event": blocking_guard,
        "disposition": decision.value,
        "source_version": {
            "policy_id": policy_id,
            "policy_version": policy_version,
            "benchmark_version": metadata.get("benchmark_version"),
        },
        "responsibility_attribution": metadata.get(
            "responsibility_attribution", "iqa-soa.service-gateway"
        ),
        "rollback_point": metadata.get("rollback_point"),
    }


__all__ = ["EvidenceCompleteness", "causal_links", "evidence_completeness"]
