"""Deterministic QA Module responsibility-chain assembly and aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Iterable, Mapping, Sequence

from iqa_soa.iqa.guards import (
    BudgetGuard,
    EvidenceGuard,
    InjectionGuard,
    OutputValidationGuard,
    PermissionGuard,
    PrivacyGuard,
    QAGuard,
)
from iqa_soa.types import Action, Decision, GuardResult, RuntimeContext, ToolResult

if TYPE_CHECKING:  # pragma: no cover
    from iqa_soa.iqa.policy import Policy


DECISION_PRECEDENCE: Mapping[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.MODIFY: 1,
    Decision.ESCALATE: 2,
    Decision.BLOCK: 3,
}


@dataclass(frozen=True, slots=True)
class AggregateDecision:
    decision: Decision
    controlling_result: GuardResult | None

    @property
    def guard_name(self) -> str | None:
        return self.controlling_result.guard_name if self.controlling_result else None

    @property
    def reason(self) -> str:
        if self.controlling_result is None:
            return "no enabled guard produced a decision"
        return self.controlling_result.reason


def aggregate_decision(results: Iterable[GuardResult]) -> AggregateDecision:
    """Apply ``BLOCK > ESCALATE > MODIFY > ALLOW`` with stable tie-breaking."""

    controlling: GuardResult | None = None
    for result in results:
        if controlling is None or DECISION_PRECEDENCE[result.decision] > DECISION_PRECEDENCE[
            controlling.decision
        ]:
            controlling = result
    return AggregateDecision(
        decision=(controlling.decision if controlling is not None else Decision.ALLOW),
        controlling_result=controlling,
    )


class GuardChain:
    """Ordered collection of independently enableable QA Modules."""

    def __init__(self, guards: Sequence[QAGuard]) -> None:
        names: set[str] = set()
        for guard in guards:
            if guard.name in names:
                raise ValueError(f"duplicate guard name: {guard.name}")
            names.add(guard.name)
        self._guards = tuple(sorted(guards, key=lambda item: (item.order, item.name)))

    @classmethod
    def from_enabled(cls, enabled: Mapping[str, bool] | None = None) -> GuardChain:
        return build_guard_chain(enabled)

    @property
    def guards(self) -> tuple[QAGuard, ...]:
        return self._guards

    @property
    def enabled_names(self) -> tuple[str, ...]:
        return tuple(guard.name for guard in self._guards if guard.enabled)

    def is_enabled(self, name: str) -> bool:
        normalized = _normalize_name(name)
        return any(guard.name == normalized and guard.enabled for guard in self._guards)

    def enable(self, name: str) -> None:
        self._set_enabled(name, True)

    def disable(self, name: str) -> None:
        self._set_enabled(name, False)

    def _set_enabled(self, name: str, value: bool) -> None:
        normalized = _normalize_name(name)
        for guard in self._guards:
            if guard.name == normalized:
                guard.enabled = value
                return
        raise KeyError(f"unknown guard: {name}")

    def evaluate(
        self,
        action: Action,
        context: RuntimeContext,
        policy: Policy,
        *,
        tool_result: ToolResult | None = None,
        phase: str | None = None,
    ) -> tuple[GuardResult, ...]:
        actual_phase = phase or ("post" if tool_result is not None else "pre")
        if actual_phase not in {"pre", "post"}:
            raise ValueError("guard phase must be 'pre' or 'post'")
        results: list[GuardResult] = []
        for guard in self._guards:
            if not guard.enabled or not guard.supports(actual_phase):
                continue
            try:
                result = guard.evaluate(
                    action,
                    context,
                    policy,
                    tool_result=tool_result,
                    phase=actual_phase,
                )
                if not isinstance(result, GuardResult):
                    raise TypeError("guard did not return GuardResult")
            except Exception as exc:  # fail safely at a pluggable module boundary
                started = perf_counter()
                result = GuardResult(
                    guard_name=guard.name,
                    decision=Decision.ESCALATE,
                    reason=f"guard evaluation failed safely: {type(exc).__name__}",
                    severity="high",
                    matched_policy=None,
                    latency_ms=max(0.0, (perf_counter() - started) * 1_000.0),
                    metadata={"guard_error": type(exc).__name__, "phase": actual_phase},
                )
            results.append(result)
        return tuple(results)

    @staticmethod
    def aggregate(results: Iterable[GuardResult]) -> AggregateDecision:
        return aggregate_decision(results)


_GUARD_TYPES: tuple[type[QAGuard], ...] = (
    InjectionGuard,
    PermissionGuard,
    PrivacyGuard,
    BudgetGuard,
    OutputValidationGuard,
    EvidenceGuard,
)

_ALIASES: Mapping[str, str] = {
    "prompt_injection": "injection",
    "injection_guard": "injection",
    "tool_permission": "permission",
    "permission_guard": "permission",
    "privacy_guard": "privacy",
    "budget_guard": "budget",
    "output": "output_validation",
    "output_validation_guard": "output_validation",
    "evidence_guard": "evidence",
}


def _normalize_name(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
    return _ALIASES.get(normalized, normalized)


def build_guard_chain(enabled: Mapping[str, bool] | None = None) -> GuardChain:
    """Build the canonical chain from a data-driven enable/disable mapping.

    Omitted entries default to enabled.  Unknown names are rejected to ensure a
    misspelled critical-module configuration cannot silently reduce governance.
    """

    normalized: dict[str, bool] = {}
    for key, value in (enabled or {}).items():
        name = _normalize_name(key)
        if name in normalized:
            raise ValueError(f"duplicate guard configuration after normalization: {key}")
        normalized[name] = bool(value)
    known = {guard_type.name for guard_type in _GUARD_TYPES}
    unknown = set(normalized).difference(known)
    if unknown:
        raise ValueError(f"unknown guard configuration: {', '.join(sorted(unknown))}")
    return GuardChain(
        [
            guard_type(enabled=normalized.get(guard_type.name, True))
            for guard_type in _GUARD_TYPES
        ]
    )


__all__ = [
    "AggregateDecision",
    "DECISION_PRECEDENCE",
    "GuardChain",
    "aggregate_decision",
    "build_guard_chain",
]
