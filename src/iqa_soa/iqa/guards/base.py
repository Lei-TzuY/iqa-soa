"""Base contract and helpers for IQA-SOA QA Modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
from typing import TYPE_CHECKING, Any, ClassVar

from iqa_soa.types import Action, Decision, GuardResult, RuntimeContext, ToolResult

if TYPE_CHECKING:  # pragma: no cover
    from iqa_soa.iqa.policy import Policy


class QAGuard(ABC):
    """One deterministic QA Module in the responsibility chain."""

    name: ClassVar[str] = "guard"
    order: ClassVar[int] = 100
    phases: ClassVar[frozenset[str]] = frozenset({"pre"})

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def supports(self, phase: str) -> bool:
        return phase in self.phases

    @abstractmethod
    def evaluate(
        self,
        action: Action,
        context: RuntimeContext,
        policy: Policy,
        *,
        tool_result: ToolResult | None = None,
        phase: str = "pre",
    ) -> GuardResult:
        """Return a normalized, evidence-ready decision contribution."""

    def result(
        self,
        decision: Decision,
        reason: str,
        *,
        started_at: float,
        severity: str = "none",
        matched_policy: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GuardResult:
        return GuardResult(
            guard_name=self.name,
            decision=decision,
            reason=reason,
            severity=severity,
            matched_policy=matched_policy,
            latency_ms=max(0.0, (perf_counter() - started_at) * 1_000.0),
            metadata=dict(metadata or {}),
        )


__all__ = ["QAGuard"]
