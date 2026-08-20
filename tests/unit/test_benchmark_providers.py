from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib import error as urlerror

import pytest

from iqa_soa.agent.providers import (
    AgentProvider,
    DeterministicStubProvider,
    OpenAICompatibleProvider,
    ProviderError,
    _parse_action_object,
)
from iqa_soa.agent.agent import ExperimentalAgent
from iqa_soa.benchmark.loader import load_benchmark_cases
from iqa_soa.types import Action, GatewayOutcome, QAMode, RuntimeContext


BENCHMARK_ROOT = Path(__file__).resolve().parents[2] / "benchmark"


def test_stub_proposals_and_usage_are_byte_deterministic() -> None:
    case = next(case for case in load_benchmark_cases(BENCHMARK_ROOT) if case.id == "PI-001")
    provider = DeterministicStubProvider()
    one = provider.generate_action(
        system_prompt=case.system_prompt,
        user_prompt=case.user_prompt,
        scripted_actions=case.scripted_actions,
        step=1,
        seed=1729,
    )
    two = provider.generate_action(
        system_prompt=case.system_prompt,
        user_prompt=case.user_prompt,
        scripted_actions=case.scripted_actions,
        step=1,
        seed=1729,
    )
    assert one is not None and two is not None
    assert one.raw_response.encode("utf-8") == two.raw_response.encode("utf-8")
    assert (one.input_tokens, one.output_tokens) == (two.input_tokens, two.output_tokens)
    assert json.loads(one.raw_response)["action_id"] == "injected-send"


def test_strict_action_json_rejects_unknown_and_missing_keys() -> None:
    with pytest.raises(ProviderError, match="unknown keys"):
        _parse_action_object(
            {"action_id": "a", "tool": "file.read", "resource": "x", "arguments": {}, "extra": 1}
        )
    with pytest.raises(ProviderError, match="missing keys"):
        _parse_action_object({"action_id": "a", "tool": "file.read", "resource": "x"})


def test_provider_security_self_claims_are_ignored_before_validation() -> None:
    action = _parse_action_object(
        {
            "action_id": "a",
            "tool": "file.read",
            "resource": "x",
            "arguments": {},
            "source": 123,
            "derived_from_untrusted": "false",
            "risk_severity": "not-a-runtime-risk",
        }
    )
    assert action.source is None
    assert action.derived_from_untrusted is False
    assert action.risk_severity == "low"


def test_http_provider_requires_env_credential_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SYNTHETIC_TEST_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
    )
    with pytest.raises(ProviderError, match="environment variable"):
        provider.generate_action(
            system_prompt="system",
            user_prompt="user",
            scripted_actions=(),
            step=0,
            seed=1,
        )


def test_http_done_response_is_counted_as_a_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeHTTPResponse:
        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [{"message": {"content": "completed locally"}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3},
                }
            ).encode("utf-8")

    class MustNotExecute:
        def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
            raise AssertionError("a done response must not execute a tool")

    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "not-a-real-secret")
    monkeypatch.setattr(
        "iqa_soa.agent.providers.request.urlopen",
        lambda request, timeout: FakeHTTPResponse(),
    )
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
    )
    context = RuntimeContext(
        experiment_id="exp",
        run_id="run",
        task_id="task",
        category="benign",
        qa_mode=QAMode.OFF,
        provider=provider.name,
        model=provider.model,
        repetition=0,
        seed=1,
        user_prompt="user",
    )
    result = ExperimentalAgent(
        provider, MustNotExecute(), system_prompt="system", max_steps=2
    ).run(user_prompt="user", scripted_actions=(), context=context)
    assert result.outcomes == ()
    assert len(result.provider_responses) == 1
    assert result.provider_responses[0].action is None
    assert context.usage.model_calls == 1
    assert (context.usage.input_tokens, context.usage.output_tokens) == (7, 3)
    assert context.usage.elapsed_time_ms > 0


def test_failed_provider_attempt_is_counted_without_inventing_tokens() -> None:
    class FailingProvider(AgentProvider):
        name = "failing_test_provider"
        model = "failing-model"

        def generate_action(self, **_: Any):
            raise ProviderError("synthetic provider failure")

    class MustNotExecute:
        def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
            raise AssertionError("a failed provider call must not execute a tool")

    context = RuntimeContext(
        experiment_id="exp",
        run_id="run",
        task_id="task",
        category="benign",
        qa_mode=QAMode.OFF,
        provider="failing_test_provider",
        model="failing-model",
        repetition=0,
        seed=1,
        user_prompt="user",
    )
    result = ExperimentalAgent(
        FailingProvider(), MustNotExecute(), system_prompt="system", max_steps=1
    ).run(user_prompt="user", scripted_actions=(), context=context)
    assert result.error == "ProviderError: synthetic provider failure"
    assert context.usage.model_calls == 1
    assert (context.usage.input_tokens, context.usage.output_tokens) == (0, 0)
    assert result.model_latency_ms >= 0


def test_native_tool_call_captures_metadata_and_canonicalizes_action_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeHTTPResponse:
        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def getheader(self, name: str) -> str | None:
            return "req-safe-123" if name.lower() == "x-request-id" else None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "id": "chatcmpl-safe-123",
                    "model": "synthetic-model-2026-08-14",
                    "system_fingerprint": "fp-safe",
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "content": None,
                                "refusal": None,
                                "tool_calls": [
                                    {
                                        "id": "call-safe",
                                        "type": "function",
                                        "function": {
                                            "name": "sandbox_action",
                                            "arguments": json.dumps(
                                                {
                                                    "action_id": "model-invented-id",
                                                    "tool": "file.read",
                                                    "resource": "report.txt",
                                                    "arguments": {},
                                                }
                                            ),
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 7},
                }
            ).encode("utf-8")

    def fake_urlopen(req: Any, timeout: float) -> FakeHTTPResponse:
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["authorization"] = req.get_header("Authorization")
        captured["client_request_id"] = req.get_header("X-client-request-id")
        captured["timeout"] = timeout
        return FakeHTTPResponse()

    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "never-serialize-this-secret")
    monkeypatch.setattr("iqa_soa.agent.providers.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
        protocol="native_tools",
        top_p=0.9,
        max_output_tokens=321,
    )
    response = provider.generate_action(
        system_prompt="system",
        user_prompt="user",
        scripted_actions=(
            Action("read-report", "file.read", "report.txt", {}, risk_severity="high"),
        ),
        step=0,
        seed=2718,
    )
    assert response is not None and response.action is not None
    assert response.action.action_id == "read-report"
    assert response.action.risk_severity == "low"
    assert response.original_action_id == "model-invented-id"
    assert response.request_id == "req-safe-123"
    assert response.response_id == "chatcmpl-safe-123"
    assert response.effective_model == "synthetic-model-2026-08-14"
    assert response.finish_reason == "tool_calls"
    assert response.system_fingerprint == "fp-safe"
    assert response.effective_seed == 2718
    assert captured["payload"]["top_p"] == 0.9
    assert captured["payload"]["max_completion_tokens"] == 321
    assert captured["payload"]["parallel_tool_calls"] is False
    assert captured["authorization"] == "Bearer never-serialize-this-secret"
    assert captured["client_request_id"]
    serialized = json.dumps({"descriptor": provider.descriptor(), "provenance": response.provenance()})
    assert "never-serialize-this-secret" not in serialized


def test_native_tools_encode_prior_outcomes_as_tool_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeHTTPResponse:
        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [{"message": {"content": '{"done":true}'}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1},
                }
            ).encode("utf-8")

    def fake_urlopen(req: Any, timeout: float) -> FakeHTTPResponse:
        del timeout
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return FakeHTTPResponse()

    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "test-only")
    monkeypatch.setattr("iqa_soa.agent.providers.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
        protocol="native_tools",
    )
    response = provider.generate_action(
        system_prompt="system",
        user_prompt="user",
        scripted_actions=(),
        step=1,
        seed=1,
        history=(
            {
                "action": {
                    "action_id": "read-report",
                    "tool": "file.read",
                    "resource": "report.txt",
                    "arguments": {},
                },
                "decision": "allow",
                "executed": True,
                "success": True,
                "output": "synthetic report",
                "error": None,
            },
        ),
    )

    assert response is not None and response.outcome == "no_action"
    messages = captured["payload"]["messages"]
    # The trailing user turn is the Class-P tool-contract re-exposure: the
    # assistant/tool history layout itself is unchanged.
    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "user",
    ]
    assert response.tool_contract_refreshed is True
    assert messages[2]["tool_calls"][0]["id"] == "iqa-history-0"
    assert json.loads(messages[2]["tool_calls"][0]["function"]["arguments"])[
        "action_id"
    ] == "read-report"
    assert messages[3]["tool_call_id"] == "iqa-history-0"
    assert json.loads(messages[3]["content"])["success"] is True


def test_refusal_is_a_scientific_outcome_not_a_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeHTTPResponse:
        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "id": "chatcmpl-refusal",
                    "model": "synthetic-model",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": None,
                                "refusal": "I cannot perform that action.",
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 4},
                }
            ).encode("utf-8")

    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "test-only")
    monkeypatch.setattr(
        "iqa_soa.agent.providers.request.urlopen",
        lambda request, timeout: FakeHTTPResponse(),
    )
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
    )
    response = provider.generate_action(
        system_prompt="system",
        user_prompt="user",
        scripted_actions=(),
        step=0,
        seed=1,
    )
    assert response is not None
    assert response.action is None
    assert response.outcome == "model_refusal"


def test_http_rate_limit_is_classified_without_leaking_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "secret-rate-limit-test")

    def fail(*_: Any, **__: Any) -> Any:
        raise urlerror.HTTPError(
            "https://example.invalid/v1/chat/completions",
            429,
            "body-must-not-be-recorded",
            {"x-request-id": "req-rate-limit"},
            None,
        )

    monkeypatch.setattr("iqa_soa.agent.providers.request.urlopen", fail)
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
    )
    with pytest.raises(ProviderError) as captured:
        provider.generate_action(
            system_prompt="system",
            user_prompt="user",
            scripted_actions=(),
            step=0,
            seed=1,
        )
    assert captured.value.failure_class == "rate_limit"
    assert captured.value.request_id == "req-rate-limit"
    assert captured.value.retryable is True
    assert "secret-rate-limit-test" not in str(captured.value)
    assert "body-must-not-be-recorded" not in str(captured.value)


def test_endpoint_and_model_can_be_resolved_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_BASE", "https://example.invalid/compatible")
    monkeypatch.setenv("MODEL_NAME", "model-from-env")
    provider = OpenAICompatibleProvider(
        base_url_env="MODEL_BASE",
        model_env="MODEL_NAME",
        api_key_env="SYNTHETIC_TEST_KEY",
    )
    assert provider.endpoint == "https://example.invalid/compatible/v1/chat/completions"
    assert provider.model == "model-from-env"
