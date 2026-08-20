"""Single IQA-SOA governance and execution entry point."""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter
from typing import TYPE_CHECKING, Any, Mapping, Protocol

from iqa_soa.evidence import EvidenceLogger
from iqa_soa.iqa.chain import AggregateDecision, GuardChain, aggregate_decision
from iqa_soa.types import (
    Action,
    Decision,
    GatewayOutcome,
    GuardResult,
    QAMode,
    RuntimeContext,
    ToolResult,
)

if TYPE_CHECKING:  # pragma: no cover
    from iqa_soa.iqa.policy import Policy


class ActionExecutor(Protocol):
    """Minimal boundary implemented by ToolRegistry and arbitrary adapters."""

    def execute(self, action: Action) -> ToolResult: ...


class ServiceGateway:
    """Adjudicate a proposal, execute at most once, and record evidence."""

    def __init__(
        self,
        registry: ActionExecutor,
        chain: GuardChain,
        policy: Policy,
        logger: EvidenceLogger,
        detailed_evidence: bool = True,
    ) -> None:
        self.registry = registry
        self.chain = chain
        self.policy = policy
        self.logger = logger
        self.detailed_evidence = detailed_evidence

    def evaluate(self, action: Action, context: RuntimeContext) -> AggregateDecision:
        """Evaluate without executing; QA OFF deterministically returns ALLOW."""

        if context.qa_mode == QAMode.OFF:
            return AggregateDecision(Decision.ALLOW, None)
        return aggregate_decision(self.chain.evaluate(action, context, self.policy))

    def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
        started = perf_counter()
        guard_results: tuple[GuardResult, ...] = ()
        executed_action: Action | None = None
        tool_result: ToolResult | None = None
        tool_latency_ms = 0.0
        error: str | None = None

        if context.qa_mode == QAMode.OFF:
            decision = Decision.ALLOW
            reason = "QA checks bypassed by the OFF treatment"
            blocking_guard = None
            # No QA Module ran.  Branch and observation overhead belongs to the
            # end-to-end measurement, not the governance-overhead metric.
            qa_latency_ms = 0.0
            executed_action = action
            tool_result, tool_latency_ms = self._execute_once(action, context)
        else:
            qa_started = perf_counter()
            pre_results = self.chain.evaluate(
                action, context, self.policy, phase="pre"
            )
            pre = aggregate_decision(pre_results)
            guard_results = pre_results
            qa_latency_ms = max(0.0, (perf_counter() - qa_started) * 1_000.0)
            decision = pre.decision
            reason = pre.reason
            blocking_guard = (
                pre.guard_name
                if decision in {Decision.BLOCK, Decision.ESCALATE}
                else None
            )

            if decision not in {Decision.BLOCK, Decision.ESCALATE}:
                candidate = self._apply_modifications(action, pre_results)
                if candidate != action:
                    # A modifier is not an authorization oracle. Re-run every
                    # pre-execution guard over the effective action so a change
                    # of tool/resource/payload cannot bypass permission/privacy.
                    recheck_started = perf_counter()
                    recheck_results = self.chain.evaluate(
                        candidate, context, self.policy, phase="pre"
                    )
                    qa_latency_ms += max(
                        0.0, (perf_counter() - recheck_started) * 1_000.0
                    )
                    guard_results = (*pre_results, *recheck_results)
                    rechecked = aggregate_decision(guard_results)
                    stabilized = self._apply_modifications(candidate, recheck_results)
                    if stabilized != candidate:
                        unstable = GuardResult(
                            guard_name="gateway",
                            decision=Decision.ESCALATE,
                            reason="action modification did not stabilize after revalidation",
                            severity="high",
                            matched_policy=None,
                            latency_ms=0.0,
                            metadata={"phase": "pre", "unstable_modification": True},
                        )
                        guard_results = (*guard_results, unstable)
                        rechecked = aggregate_decision(guard_results)
                    decision = rechecked.decision
                    reason = rechecked.reason
                    blocking_guard = (
                        rechecked.guard_name
                        if decision in {Decision.BLOCK, Decision.ESCALATE}
                        else None
                    )

                if decision not in {Decision.BLOCK, Decision.ESCALATE}:
                    evidence_required = bool(
                        getattr(self.policy.output_validation, "require_evidence", False)
                        and self.detailed_evidence
                        and self.chain.is_enabled("evidence")
                    )
                    if evidence_required:
                        readiness_started = perf_counter()
                        try:
                            self.logger.ensure_writable()
                        except Exception as exc:
                            readiness = GuardResult(
                                guard_name="evidence",
                                decision=Decision.ESCALATE,
                                reason="required evidence storage is unavailable before execution",
                                severity="high",
                                matched_policy=f"{self.policy.policy_id}:output:require-evidence",
                                latency_ms=max(
                                    0.0,
                                    (perf_counter() - readiness_started) * 1_000.0,
                                ),
                                metadata={
                                    "phase": "pre",
                                    "evidence_error": type(exc).__name__,
                                },
                            )
                            guard_results = (*guard_results, readiness)
                            decision = Decision.ESCALATE
                            blocking_guard = "evidence"
                            reason = readiness.reason
                            error = (
                                "required evidence preflight failed: "
                                f"{type(exc).__name__}: {exc}"
                            )

                if decision not in {Decision.BLOCK, Decision.ESCALATE}:
                    executed_action = candidate
                    tool_result, tool_latency_ms = self._execute_once(
                        executed_action, context
                    )
                if executed_action is not None and tool_result is not None:
                    post_started = perf_counter()
                    post_results = self.chain.evaluate(
                        executed_action,
                        context,
                        self.policy,
                        tool_result=tool_result,
                        phase="post",
                    )
                    qa_latency_ms += max(
                        0.0, (perf_counter() - post_started) * 1_000.0
                    )
                    guard_results = (*guard_results, *post_results)
                    final = aggregate_decision(guard_results)
                    decision = final.decision
                    blocking_guard = (
                        final.guard_name
                        if decision in {Decision.BLOCK, Decision.ESCALATE}
                        else None
                    )
                    if decision == Decision.ALLOW:
                        reason = "all enabled QA Modules allowed the action and tool result"
                    elif decision == Decision.MODIFY:
                        reason = final.reason
                    else:
                        reason = final.reason
                        # The action already ran, but a rejected result must not flow
                        # back into subsequent agent context as usable content.
                        # Preserve execution/fault metadata for measurement while
                        # withholding the invalid or sensitive output value.
                        tool_result = self._contain_tool_result(tool_result, decision)

        pre_evidence_latency_ms = max(0.0, (perf_counter() - started) * 1_000.0)
        detailed = (
            context.qa_mode != QAMode.OFF
            and self.detailed_evidence
            and self.chain.is_enabled("evidence")
        )
        evidence_id: str | None = None
        did_execute = bool(
            executed_action is not None
            and tool_result is not None
            and tool_result.would_execute
        )
        evidence_started = perf_counter()
        try:
            evidence_id = self.logger.log_gateway(
                context=context,
                action=action,
                policy=self.policy,
                guard_results=guard_results,
                decision=decision,
                executed=did_execute,
                tool_result=tool_result,
                reason=reason,
                blocking_guard=blocking_guard,
                qa_latency_ms=qa_latency_ms,
                # The evidence record cannot know its own final write duration;
                # this field is the pre-log elapsed measurement.  The returned
                # outcome separately reports the measured logger wall time.
                latency_ms=pre_evidence_latency_ms,
                detailed=detailed,
                executed_action=executed_action,
                error=error,
            )
        except Exception as exc:  # evidence failure must be visible, never hidden
            error = f"evidence logging failed: {type(exc).__name__}: {exc}"
            if (
                context.qa_mode != QAMode.OFF
                and decision not in {Decision.BLOCK, Decision.ESCALATE}
            ):
                decision = Decision.ESCALATE
                blocking_guard = "evidence"
                reason = "evidence logging failed after safe execution handling"

        evidence_latency_ms = max(0.0, (perf_counter() - evidence_started) * 1_000.0)
        actual_latency_ms = max(0.0, (perf_counter() - started) * 1_000.0)
        latency_ms = max(
            actual_latency_ms,
            qa_latency_ms + tool_latency_ms + evidence_latency_ms,
        )
        context.usage.elapsed_time_ms += latency_ms

        return GatewayOutcome(
            proposed_action=action,
            executed_action=executed_action,
            decision=decision,
            blocking_guard=blocking_guard,
            reason=reason,
            executed=did_execute,
            guard_results=tuple(guard_results),
            tool_result=tool_result,
            qa_latency_ms=qa_latency_ms,
            evidence_latency_ms=evidence_latency_ms,
            tool_latency_ms=tool_latency_ms,
            latency_ms=latency_ms,
            evidence_id=evidence_id,
            error=error or (tool_result.error if tool_result is not None else None),
        )

    def _execute_once(
        self, action: Action, context: RuntimeContext
    ) -> tuple[ToolResult, float]:
        """Own the tool-call counter and catch extension-boundary faults."""

        context.usage.tool_calls += 1
        started = perf_counter()
        try:
            result = self.registry.execute(action)
            if not isinstance(result, ToolResult):
                result = ToolResult(
                    success=True,
                    output=result,
                    simulated=True,
                    would_execute=True,
                    metadata={"coerced_tool_result": True},
                )
        except Exception as exc:  # pragma: no cover - defensive arbitrary executor
            result = ToolResult(
                success=False,
                error=f"tool execution failed safely: {type(exc).__name__}: {exc}",
                simulated=True,
                would_execute=True,
                metadata={"caught_exception": type(exc).__name__},
            )
        actual_ms = max(0.0, (perf_counter() - started) * 1_000.0)
        latency_ms = max(actual_ms, result.latency_ms)
        if result.latency_ms != latency_ms:
            result = replace(result, latency_ms=latency_ms)
        return result, latency_ms

    @staticmethod
    def _apply_modifications(action: Action, results: tuple[Any, ...]) -> Action:
        modified = action
        for result in results:
            if result.decision != Decision.MODIFY:
                continue
            metadata: Mapping[str, Any] = result.metadata
            replacement = metadata.get("modified_action")
            if isinstance(replacement, Action):
                modified = replacement
                continue
            arguments = dict(modified.arguments)
            changed_arguments = metadata.get("modified_arguments")
            if isinstance(changed_arguments, Mapping):
                arguments.update(changed_arguments)
            for key in metadata.get("remove_arguments", ()):
                arguments.pop(str(key), None)
            modified = replace(
                modified,
                tool=str(metadata.get("modified_tool", modified.tool)),
                resource=str(metadata.get("modified_resource", modified.resource)),
                arguments=arguments,
            )
        return modified

    @staticmethod
    def _contain_tool_result(
        tool_result: ToolResult, decision: Decision
    ) -> ToolResult:
        metadata = dict(tool_result.metadata)
        metadata.update(
            {
                "contained": True,
                "original_success": tool_result.success,
                "validation_decision": decision.value,
            }
        )
        return replace(tool_result, output=None, metadata=metadata)


__all__ = ["ActionExecutor", "ServiceGateway"]
