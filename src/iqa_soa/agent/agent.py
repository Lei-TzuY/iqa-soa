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
    no_action: bool = False


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
        for step in range(self.max_steps):
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
                    step=step,
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
            if response.action is None:
                break
            raw_actions.append(response.raw_response)
            outcomes.append(self.executor.execute(response.action, context))
        model_refusal = any(response.outcome == "model_refusal" for response in responses)
        no_action = not outcomes and any(
            response.outcome == "no_action" for response in responses
        )
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
        )
