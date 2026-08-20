"""Regression tests for the Phase-C Class-P protocol/instrumentation repair.

These reproduce the Phase-B failure modes deterministically and offline.  No
real model is contacted: provider HTTP is faked, and the provider-side template
behaviour is reproduced by a renderer that implements the same gating rule the
Ollama Mistral chat template uses.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import pytest

from iqa_soa.agent.providers import (
    TOOL_CONTRACT_NOTICE,
    OpenAICompatibleProvider,
    ProviderError,
)


# --------------------------------------------------------------------------
# Provider-side template simulation
# --------------------------------------------------------------------------


def render_mistral_style(messages: Sequence[Mapping[str, Any]], tools: Any) -> str:
    """Reproduce the Ollama Mistral template's tool-gating rule exactly.

    The template emits ``[AVAILABLE_TOOLS]`` only while the user message is
    within the final two messages of the conversation::

        {{- if and (le (len (slice $.Messages $index)) 2) $.Tools }}

    Everything else here is incidental; the adjacency rule is the behaviour
    under test.
    """

    total = len(messages)
    parts: list[str] = []
    for index, message in enumerate(messages):
        role = message.get("role")
        if role == "system":
            parts.append(f"[SYSTEM_PROMPT]{message.get('content')}[/SYSTEM_PROMPT]")
        elif role == "user":
            if (total - index) <= 2 and tools:
                parts.append(
                    f"[AVAILABLE_TOOLS]{json.dumps(tools, sort_keys=True)}"
                    "[/AVAILABLE_TOOLS]"
                )
            parts.append(f"[INST]{message.get('content')}[/INST]")
        elif role == "assistant":
            for call in message.get("tool_calls") or []:
                function = call["function"]
                parts.append(
                    f"[TOOL_CALLS]{function['name']}[ARGS]{function['arguments']}"
                )
        elif role == "tool":
            parts.append(f"[TOOL_RESULTS]{message.get('content')}[/TOOL_RESULTS]")
    return "".join(parts)


def render_native_style(messages: Sequence[Mapping[str, Any]], tools: Any) -> str:
    """Reproduce a renderer that always presents tools (Qwen-style)."""

    rendered = json.dumps(list(messages), sort_keys=True, default=str)
    return f"TOOLS={json.dumps(tools, sort_keys=True)}\n{rendered}"


def tool_contract_visible(rendered: str) -> bool:
    """True only when the callable tool *definition* survived rendering.

    Checking for the bare function name is not sufficient: an echoed prior
    ``[TOOL_CALLS]sandbox_action`` in the history mentions the name without
    making the tool callable.  These markers appear only in the JSON schema of
    the tool contract itself.
    """

    return (
        "sandbox_action" in rendered
        and "shell.execute_simulated" in rendered  # tool enum, schema-only
        and "additionalProperties" in rendered  # parameter schema, schema-only
    )


# --------------------------------------------------------------------------
# Fake HTTP plumbing
# --------------------------------------------------------------------------


def _envelope(tool_calls: list[dict[str, Any]] | None, content: str | None) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-test",
        "model": "synthetic-model",
        "system_fingerprint": "fp_test",
        "choices": [
            {
                "message": message,
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10},
    }


def _tool_call(action_id: str, resource: str) -> dict[str, Any]:
    return {
        "id": f"call-{action_id}",
        "type": "function",
        "function": {
            "name": "sandbox_action",
            "arguments": json.dumps(
                {
                    "action_id": action_id,
                    "tool": "file.read",
                    "resource": resource,
                    "arguments": {},
                }
            ),
        },
    }


def install_fake_transport(
    monkeypatch: pytest.MonkeyPatch, envelope: Mapping[str, Any]
) -> dict[str, Any]:
    """Capture the outgoing payload and return a canned envelope."""

    captured: dict[str, Any] = {}

    class FakeHTTPResponse:
        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(envelope).encode("utf-8")

        def getheader(self, name: str) -> str | None:
            return None

    def fake_urlopen(req: Any, timeout: float | None = None) -> FakeHTTPResponse:
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return FakeHTTPResponse()

    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "test-only")
    monkeypatch.setattr("iqa_soa.agent.providers.request.urlopen", fake_urlopen)
    return captured


def build_provider(policy: str = "trailing_user") -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
        protocol="native_tools",
        tool_contract_policy=policy,
    )


def history_of(length: int) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "action": {
                "action_id": f"step-{index}",
                "tool": "file.read",
                "resource": f"public/{index}.txt",
                "arguments": {},
            },
            "decision": "allow",
            "executed": True,
            "success": True,
            "output": "synthetic",
            "error": None,
        }
        for index in range(length)
    )


def capture_payload(
    monkeypatch: pytest.MonkeyPatch, *, history_length: int, policy: str
) -> dict[str, Any]:
    captured = install_fake_transport(monkeypatch, _envelope(None, "done"))
    build_provider(policy).generate_action(
        system_prompt="system",
        user_prompt="user",
        scripted_actions=(),
        step=history_length,
        seed=1,
        history=history_of(history_length),
        canonical_resources=("public/0.txt", "public/1.txt"),
    )
    return captured["payload"]


# --------------------------------------------------------------------------
# 1. Second and third agentic calls retain an operational tool contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize("history_length", [1, 2])
def test_later_calls_retain_operational_tool_contract(
    monkeypatch: pytest.MonkeyPatch, history_length: int
) -> None:
    payload = capture_payload(
        monkeypatch, history_length=history_length, policy="trailing_user"
    )
    # The HTTP payload still declares the tools...
    assert payload["tools"][0]["function"]["name"] == "sandbox_action"
    # ...and the contract survives a template that gates on user adjacency.
    rendered = render_mistral_style(payload["messages"], payload["tools"])
    assert tool_contract_visible(rendered)


# --------------------------------------------------------------------------
# 2. Mistral-style layout does not silently lose tool availability
# --------------------------------------------------------------------------


def test_pre_repair_policy_reproduces_the_phase_b_defect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The unrepaired layout loses the contract once history is present."""

    first = capture_payload(monkeypatch, history_length=0, policy="none")
    assert tool_contract_visible(render_mistral_style(first["messages"], first["tools"]))

    later = capture_payload(monkeypatch, history_length=1, policy="none")
    # Tools are still in the HTTP payload, which is exactly why the defect was
    # invisible: the loss happens during provider-side rendering.
    assert later["tools"][0]["function"]["name"] == "sandbox_action"
    assert not tool_contract_visible(
        render_mistral_style(later["messages"], later["tools"])
    )


def test_repair_restores_tool_availability_under_mistral_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    later = capture_payload(monkeypatch, history_length=1, policy="trailing_user")
    assert tool_contract_visible(
        render_mistral_style(later["messages"], later["tools"])
    )
    # The repair restores protocol information only: it must not tell the model
    # to keep acting.
    trailing = later["messages"][-1]
    assert trailing["role"] == "user"
    assert TOOL_CONTRACT_NOTICE in trailing["content"]
    lowered = trailing["content"].lower()
    for incentive in (
        "continue using",
        "take another action",
        "you should",
        "must call",
        "keep going",
        "try again",
    ):
        assert incentive not in lowered


# --------------------------------------------------------------------------
# 3. Native/always-tools provider behaviour remains compatible
# --------------------------------------------------------------------------


def test_native_renderer_provider_remains_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = capture_payload(monkeypatch, history_length=1, policy="trailing_user")
    assert tool_contract_visible(render_native_style(payload["messages"], payload["tools"]))
    roles = [message["role"] for message in payload["messages"]]
    # The OpenAI-standard history encoding is untouched; only a trailing user
    # turn is appended.
    assert roles[:4] == ["system", "user", "assistant", "tool"]
    assert payload["parallel_tool_calls"] is False
    assert payload["tool_choice"] == "auto"


def test_first_call_is_byte_identical_across_policies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no history there is nothing to re-expose, so nothing changes."""

    repaired = capture_payload(monkeypatch, history_length=0, policy="trailing_user")
    legacy = capture_payload(monkeypatch, history_length=0, policy="none")
    assert repaired == legacy


# --------------------------------------------------------------------------
# 4. Multiple emitted tool calls do not destroy the whole run
# --------------------------------------------------------------------------


def test_multiple_tool_calls_are_preserved_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_transport(
        monkeypatch,
        _envelope(
            [_tool_call("read-a", "public/0.txt"), _tool_call("read-b", "public/1.txt")],
            None,
        ),
    )
    response = build_provider().generate_action(
        system_prompt="system",
        user_prompt="user",
        scripted_actions=(),
        step=0,
        seed=1,
        canonical_resources=("public/0.txt", "public/1.txt"),
    )
    assert response is not None
    assert response.outcome == "action"
    assert response.tool_call_count == 2
    assert response.action is not None and response.action.action_id == "read-a"
    assert [item.action_id for item in response.additional_actions] == ["read-b"]
    assert response.provenance()["multi_tool_call"] is True


def test_runtime_provenance_degrades_without_raising() -> None:
    """Provenance is best-effort: an unreachable runtime must never break a run."""

    from iqa_soa.agent.providers import probe_runtime_provenance

    provenance = probe_runtime_provenance(
        "http://127.0.0.1:9/v1/chat/completions", "absent-model", timeout_seconds=0.5
    )
    assert provenance["model_identifier"] == "absent-model"
    assert provenance["runtime"] is None
    assert provenance["template_sha256"] is None
    assert provenance["probe_error"]


def test_malformed_call_inside_a_multi_call_turn_still_fails_loudly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserving multiple calls must not weaken per-call validation."""

    broken = _tool_call("read-b", "public/1.txt")
    broken["function"]["name"] = "not_sandbox_action"
    install_fake_transport(
        monkeypatch, _envelope([_tool_call("read-a", "public/0.txt"), broken], None)
    )
    with pytest.raises(ProviderError) as excinfo:
        build_provider().generate_action(
            system_prompt="system",
            user_prompt="user",
            scripted_actions=(),
            step=0,
            seed=1,
        )
    assert excinfo.value.failure_class == "invalid_tool_call"
    assert excinfo.value.tool_call_count == 2
