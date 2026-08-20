"""Shared, dependency-free contracts for the experimental runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    """Normalized IQA-SOA governance decision."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"


class QAMode(str, Enum):
    """Experimental treatment applied to an otherwise identical run."""

    OFF = "off"
    PARTIAL = "partial"
    FULL = "full"
    ABLATION = "ablation"


@dataclass(frozen=True, slots=True)
class Action:
    """An agent-proposed tool action; proposals never imply authority."""

    action_id: str
    tool: str
    resource: str
    arguments: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    derived_from_untrusted: bool = False
    risk_severity: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Usage:
    """Mutable per-run resource accounting available to budget guards."""

    tool_calls: int = 0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float | None = None
    elapsed_time_ms: float = 0.0


@dataclass(slots=True)
class RuntimeContext:
    """Runtime facts visible to guards, excluding hidden ground-truth labels."""

    experiment_id: str
    run_id: str
    task_id: str
    category: str
    qa_mode: QAMode
    provider: str
    model: str
    repetition: int
    seed: int
    user_prompt: str
    untrusted_content: tuple[str, ...] = ()
    usage: Usage = field(default_factory=Usage)
    confirmed_high_risk: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GuardResult:
    """One QA Module's auditable decision contribution."""

    guard_name: str
    decision: Decision
    reason: str
    severity: str
    matched_policy: str | None
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        return data


@dataclass(frozen=True, slots=True)
class ToolResult:
    """A sandboxed tool outcome; no tool may mutate the host system."""

    success: bool
    output: Any = None
    error: str | None = None
    latency_ms: float = 0.0
    simulated: bool = True
    would_execute: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GatewayOutcome:
    """Structured outcome returned by the single governed execution point."""

    proposed_action: Action
    executed_action: Action | None
    decision: Decision
    blocking_guard: str | None
    reason: str
    executed: bool
    guard_results: tuple[GuardResult, ...]
    tool_result: ToolResult | None
    qa_latency_ms: float
    evidence_latency_ms: float
    tool_latency_ms: float
    latency_ms: float
    evidence_id: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposed_action": self.proposed_action.to_dict(),
            "executed_action": (
                self.executed_action.to_dict() if self.executed_action else None
            ),
            "decision": self.decision.value,
            "blocking_guard": self.blocking_guard,
            "reason": self.reason,
            "executed": self.executed,
            "guard_results": [item.to_dict() for item in self.guard_results],
            "tool_result": self.tool_result.to_dict() if self.tool_result else None,
            "qa_latency_ms": self.qa_latency_ms,
            "evidence_latency_ms": self.evidence_latency_ms,
            "tool_latency_ms": self.tool_latency_ms,
            "latency_ms": self.latency_ms,
            "evidence_id": self.evidence_id,
            "error": self.error,
        }
