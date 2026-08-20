from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from iqa_soa.agent.agent import ExperimentalAgent
from iqa_soa.agent.providers import AgentProvider, ProviderResponse
from iqa_soa.failure_taxonomy import classify_tool_error
from iqa_soa.types import Action, Decision, GatewayOutcome, QAMode, RuntimeContext, ToolResult


class _OneActionProvider(AgentProvider):
    name = "taxonomy_test_provider"
    model = "taxonomy-test-model"

    def generate_action(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        scripted_actions: Sequence[Action],
        step: int,
        seed: int,
        history: Sequence[Mapping[str, Any]] = (),
        canonical_resources: Sequence[str] = (),
    ) -> ProviderResponse | None:
        del system_prompt, user_prompt, scripted_actions, seed, history, canonical_resources
        if step:
            return None
        action = Action("invented", "file.read", "missing.txt", {})
        return ProviderResponse(
            action=action,
            input_tokens=1,
            output_tokens=1,
            latency_ms=0.0,
            raw_response=json.dumps(action.to_dict()),
            model=self.model,
        )


class _MissingResourceExecutor:
    def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
        del context
        return GatewayOutcome(
            proposed_action=action,
            executed_action=action,
            decision=Decision.ALLOW,
            blocking_guard=None,
            reason="sandbox attempted requested resource",
            executed=True,
            guard_results=(),
            tool_result=ToolResult(False, error="sandbox file not found: missing.txt"),
            qa_latency_ms=0.0,
            evidence_latency_ms=0.0,
            tool_latency_ms=0.0,
            latency_ms=0.0,
            evidence_id=None,
            error="sandbox file not found: missing.txt",
        )


def test_model_requested_missing_resource_is_a_scientific_failure() -> None:
    context = RuntimeContext(
        experiment_id="exp",
        run_id="run",
        task_id="task",
        category="benign",
        qa_mode=QAMode.OFF,
        provider="taxonomy_test_provider",
        model="taxonomy-test-model",
        repetition=0,
        seed=1,
        user_prompt="read a file",
    )
    result = ExperimentalAgent(
        _OneActionProvider(), _MissingResourceExecutor(), system_prompt="system", max_steps=2
    ).run(user_prompt="read a file", scripted_actions=(), context=context)

    assert result.failure_class == "invalid_resource"
    assert result.error == "sandbox file not found: missing.txt"
    assert result.outcomes[0].tool_result is not None
    assert result.outcomes[0].tool_result.success is False


def test_generic_tool_and_timeout_errors_have_explicit_classes() -> None:
    assert classify_tool_error("simulated tool unavailable") == "tool_failure"
    assert classify_tool_error("simulated tool timeout") == "tool_timeout"
