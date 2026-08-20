"""A deliberately small plan-execute agent for controlled experiments."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping, Protocol, Sequence

from iqa_soa.agent.providers import AgentProvider, ProviderError, ProviderResponse
from iqa_soa.failure_taxonomy import classify_gateway_outcomes
from iqa_soa.types import Action, GatewayOutcome, RuntimeContext


class ActionExecutor(Protocol):
    def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome: ...


@dataclass(frozen=True, slots=True)
class AgentRun:
    outcomes: tuple[GatewayOutcome, ...]
    provider_responses: tuple[ProviderResponse, ...]
    proposed_action_bytes: tuple[str, ...]
    model_latency_ms: float
    error: str | None = None
    failure_class: str | None = None
    provider_attempts: tuple[Mapping[str, Any], ...] = ()
    model_refusal: bool = False
    # Preserved pre-repair semantics: a terminal no-action response when the
    # run executed no action at all.  Kept unchanged for backward compatibility;
    # use ``terminal_no_action`` for the unconditional signal.
    no_action: bool = False
    # Any terminal no-action response, whether or not actions were executed.
    terminal_no_action: bool = False
    # How many provider attempts ended in a terminal no-action response.
    terminal_no_action_attempts: int = 0
    # A terminal no-action response that followed at least one executed action.
    no_action_after_actions: bool = False
    # The provider emitted more than one native tool call in a single turn.
    provider_multi_tool_call: bool = False
    # Largest number of tool calls emitted in any single turn.
    provider_max_tool_calls: int = 0
    # Actions queued from multi-call turns and later submitted individually.
    queued_action_count: int = 0
    # Instrument self-check: a later model call carried strictly fewer input
    # tokens than an earlier one despite the history having grown.  That is the
    # signature of a provider/template dropping the tool contract from the
    # rendered prompt (Phase B).  Telemetry only; never fails the run.
    tool_contract_regression_detected: bool = False


class ExperimentalAgent:
    """Obtain proposals from a provider and submit every one to the gateway."""

    def __init__(
        self,
        provider: AgentProvider,
        executor: ActionExecutor,
        *,
        system_prompt: str,
        max_steps: int = 20,
    ) -> None:
        if max_steps < 0:
            raise ValueError("max_steps must be non-negative")
        self.provider = provider
        self.executor = executor
        self.system_prompt = system_prompt
        self.max_steps = max_steps

    def run(
        self,
        *,
        user_prompt: str,
        scripted_actions: Sequence[Action],
        context: RuntimeContext,
        canonical_resources: Sequence[str] = (),
    ) -> AgentRun:
        responses: list[ProviderResponse] = []
        outcomes: list[GatewayOutcome] = []
        raw_actions: list[str] = []
        attempts: list[Mapping[str, Any]] = []
        model_latency_ms = 0.0
        error: str | None = None
        failure_class: str | None = None
        # Actions the provider emitted beyond the first in a single turn.  They
        # are consumed one per step, in emission order, and each is submitted to
        # the gateway individually, so no action bypasses IQA-SOA and the run is
        # not destroyed merely because the model expressed several at once.
        pending: list[Action] = []
        queued_action_count = 0
        provider_multi_tool_call = False
        provider_max_tool_calls = 0
        tool_contract_regression_detected = False
        previous_input_tokens: int | None = None
        for _step in range(self.max_steps):
            if pending:
                # No model call is made for a queued action, so model-call
                # budget accounting stays correct; the gateway still charges
                # tool-call budget when it executes.
                outcomes.append(self.executor.execute(pending.pop(0), context))
                continue
            started = time.perf_counter()
            history = tuple(
                {
                    "action": outcome.proposed_action.to_dict(),
                    "decision": outcome.decision.value,
                    "executed": outcome.executed,
                    "success": (
                        outcome.tool_result.success if outcome.tool_result else None
                    ),
                    "output": outcome.tool_result.output if outcome.tool_result else None,
                    "error": outcome.error,
                }
                for outcome in outcomes
            )
            try:
                response = self.provider.generate_action(
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt,
                    scripted_actions=scripted_actions,
                    # The action step is the number of actions already taken.
                    # This equals the loop index whenever no action was queued,
                    # so pre-repair behaviour is unchanged.
                    step=len(outcomes),
                    seed=context.seed,
                    history=history,
                    canonical_resources=canonical_resources,
                )
            except ProviderError as exc:
                # A failed remote invocation still consumed one model call and
                # wall time even when the provider could not report tokens.
                failed_latency_ms = (time.perf_counter() - started) * 1000.0
                model_latency_ms += failed_latency_ms
                context.usage.elapsed_time_ms += failed_latency_ms
                context.usage.model_calls += 1
                error = f"{type(exc).__name__}: {exc}"
                failure_class = exc.failure_class
                attempts.append(
                    exc.provenance(model=self.provider.model, latency_ms=failed_latency_ms)
                )
                break
            measured_ms = (time.perf_counter() - started) * 1000.0
            if response is None:
                break
            responses.append(response)
            attempts.append(response.provenance())
            measured_provider_ms = max(response.latency_ms, measured_ms)
            model_latency_ms += measured_provider_ms
            context.usage.elapsed_time_ms += measured_provider_ms
            context.usage.model_calls += 1
            context.usage.input_tokens += response.input_tokens
            context.usage.output_tokens += response.output_tokens
            if response.estimated_cost is not None:
                prior = context.usage.estimated_cost or 0.0
                context.usage.estimated_cost = prior + response.estimated_cost
            if (
                previous_input_tokens is not None
                and outcomes
                and response.input_tokens < previous_input_tokens
            ):
                tool_contract_regression_detected = True
            previous_input_tokens = response.input_tokens
            provider_max_tool_calls = max(
                provider_max_tool_calls, response.tool_call_count
            )
            if response.tool_call_count > 1:
                provider_multi_tool_call = True
            if response.action is None:
                break
            raw_actions.append(response.raw_response)
            if response.additional_actions:
                pending.extend(response.additional_actions)
                queued_action_count += len(response.additional_actions)
            outcomes.append(self.executor.execute(response.action, context))
        model_refusal = any(response.outcome == "model_refusal" for response in responses)
        terminal_no_action_attempts = sum(
            response.outcome == "no_action" for response in responses
        )
        terminal_no_action = terminal_no_action_attempts > 0
        # Unchanged pre-repair definition, retained for backward compatibility.
        no_action = not outcomes and terminal_no_action
        no_action_after_actions = terminal_no_action and bool(outcomes)
        if failure_class is None and model_refusal:
            failure_class = "model_refusal"
        if failure_class is None:
            outcome_failure_class, outcome_error = classify_gateway_outcomes(outcomes)
            if outcome_failure_class is not None:
                failure_class = outcome_failure_class
                error = error or outcome_error
        return AgentRun(
            outcomes=tuple(outcomes),
            provider_responses=tuple(responses),
            proposed_action_bytes=tuple(raw_actions),
            model_latency_ms=model_latency_ms,
            error=error,
            failure_class=failure_class,
            provider_attempts=tuple(attempts),
            model_refusal=model_refusal,
            no_action=no_action,
            terminal_no_action=terminal_no_action,
            terminal_no_action_attempts=terminal_no_action_attempts,
            no_action_after_actions=no_action_after_actions,
            provider_multi_tool_call=provider_multi_tool_call,
            provider_max_tool_calls=provider_max_tool_calls,
            queued_action_count=queued_action_count,
            tool_contract_regression_detected=tool_contract_regression_detected,
        )
