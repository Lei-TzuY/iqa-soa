"""C3 provider failure-path telemetry: acceptance and mutation proof.

**NO PROVIDER IS CONTACTED ANYWHERE IN THIS FILE.**  Every case substitutes an
in-memory object for ``request.urlopen``, exactly as
``tests/unit/test_benchmark_providers.py`` already does.  No socket is opened, no
model is run, and nothing beneath ``results/`` is read, listed or hashed.  Every
sentinel value below is authored for the test and is derived from no model output
and from no recorded outcome of any kind.

The suite proves three separate things, because none of them implies the others:

**AC-1 -- the accept/refuse decision function is unchanged.**  Every input
accepted before C3 is still accepted, every input refused is still refused with
the same ``failure_class``, the same ``failure_origin`` and the same message; the
request payload and the native tool schema are byte-identical; retryability and
the retry loop are unchanged; and no malformed action is rescued (T-09 .. T-11,
T-14 .. T-17).  Without this C3 is not a measurement improvement and would have
to be reclassified.

**The telemetry is READ FROM THE ENVELOPE, not fabricated.**  Three independent
mechanisms:

* **M-1, distinct-sentinel differential.**  Two envelopes identical but for one
  field, driven through the SAME failure branch, must produce two different
  persisted values.  A constant, a default, a configuration value or a
  fabrication cannot vary with an input it never read (T-01 .. T-05).
* **M-2, three-way presence discrimination.**  Key present, key removed, and
  failure before the envelope existed must produce three DIFFERENT persisted
  shapes.  An implementation that emits a bare ``None`` cannot pass, and neither
  can one that reports ``NOT_SUPPLIED`` for a transport failure (T-06 .. T-08).
* **M-3, static branch and stage closure.**  An AST scan requiring every ``raise
  ProviderError`` in ``providers.py`` to name an explicit branch, and a capture
  floor forbidding ``UNOBSERVED`` for any field the branch's stage makes
  reachable.  Together they make *the adapter dropped it* a build failure rather
  than a persisted ambiguity (T-12, T-13).

**Nothing new is disclosed.**  No credential, header, response body, prompt,
assistant text, tool argument or resource value reaches a persisted field (T-19).
"""

from __future__ import annotations

import ast
from copy import deepcopy
from email.message import Message
import inspect
import json
from pathlib import Path
import socket
from typing import Any, Iterator, Mapping, NoReturn
from urllib import error as urlerror

import pytest

from iqa_soa.agent.agent import ExperimentalAgent
from iqa_soa.agent.providers import (
    DEFAULT_TOOL_CONTRACT_POLICY,
    NATIVE_TOOL_ADAPTER_VERSION,
    NativeToolCallState,
    OpenAICompatibleProvider,
    PROVIDER_BRANCH_CAPTURE_STAGE,
    PROVIDER_ENVELOPE_FIELDS,
    PROVIDER_FAILURE_TELEMETRY_FIELDS,
    PROVIDER_STAGE_REACHABLE_FIELDS,
    ProviderCaptureStage,
    ProviderCaptureState,
    ProviderEnvelopeCapture,
    ProviderError,
    ProviderFailureBranch,
    ProviderFailureOrigin,
    TOOL_CONTRACT_NOTICE,
    TOOL_CONTRACT_POLICIES,
    _native_action_tool,
)
from iqa_soa.types import Action, GatewayOutcome, QAMode, RuntimeContext


PROVIDERS_SOURCE = Path(
    inspect.getsourcefile(OpenAICompatibleProvider)  # type: ignore[arg-type]
).resolve()

#: The one credential value used everywhere below.  It is asserted ABSENT from
#: every serialized artifact, so a leak anywhere shows up as a test failure
#: rather than as a reviewer noticing it.
CREDENTIAL = "never-serialize-this-c3-secret"
CREDENTIAL_ENV = "C3_SYNTHETIC_TEST_KEY"

#: Values that appear ONLY in a request the provider sends, never in a response.
#: Persisting any of them would mean the failure record had started carrying
#: prompt or tool-argument material.
SYSTEM_PROMPT = "SYSTEM-PROMPT-SENTINEL-must-never-be-persisted"
USER_PROMPT = "USER-PROMPT-SENTINEL-must-never-be-persisted"


# ==========================================================================
# Synthetic transport.  Nothing here can reach a network.
# ==========================================================================


class FakeHTTPResponse:
    """An in-memory stand-in for the object ``request.urlopen`` returns."""

    def __init__(self, body: bytes, *, request_id: str | None = "req-c3") -> None:
        self._body = body
        self._request_id = request_id

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def getheader(self, name: str) -> str | None:
        return self._request_id if name.lower() == "x-request-id" else None

    def read(self) -> bytes:
        return self._body


def _install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    body: bytes | None = None,
    raises: BaseException | None = None,
    captured: dict[str, Any] | None = None,
) -> None:
    monkeypatch.setenv(CREDENTIAL_ENV, CREDENTIAL)

    def fake_urlopen(req: Any, timeout: float) -> FakeHTTPResponse:
        if captured is not None:
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            captured["body_bytes"] = req.data
            captured["timeout"] = timeout
        if raises is not None:
            raise raises
        assert body is not None
        return FakeHTTPResponse(body)

    monkeypatch.setattr("iqa_soa.agent.providers.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "iqa_soa.agent.providers.socket.create_connection",
        _refuse_socket,
        raising=False,
    )


def _refuse_socket(*_: Any, **__: Any) -> NoReturn:
    raise AssertionError("a C3 test may never open a socket")


def _provider(
    protocol: str = "native_tools", *, seed: int | None = 4242
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env=CREDENTIAL_ENV,
        protocol=protocol,
        seed=seed,
    )


def _generate(
    provider: OpenAICompatibleProvider,
    *,
    scripted: tuple[Action, ...] = (),
    step: int = 0,
) -> Any:
    return provider.generate_action(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=USER_PROMPT,
        scripted_actions=scripted,
        step=step,
        seed=1729,
    )


def _failure(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes | None,
    *,
    protocol: str = "native_tools",
    raises: BaseException | None = None,
    seed: int | None = 4242,
) -> tuple[ProviderError, dict[str, Any]]:
    """Drive one failure and return the exception plus its persisted record."""

    _install(monkeypatch, body=body, raises=raises)
    provider = _provider(protocol, seed=seed)
    with pytest.raises(ProviderError) as captured:
        _generate(provider)
    return captured.value, captured.value.provenance(
        model=provider.model, latency_ms=12.5
    )


# ==========================================================================
# Synthetic envelopes.  Every sentinel is authored here.
# ==========================================================================


def wrong_channel_envelope(
    *,
    response_id: str = "chatcmpl-ENVELOPE-A",
    model: str = "model-ENVELOPE-A",
    system_fingerprint: str = "fp-ENVELOPE-A",
    finish_reason: str = "stop",
    prompt_tokens: int = 11,
    completion_tokens: int = 7,
) -> dict[str, Any]:
    """The class-E envelope: a valid message whose action came back as content.

    A native-tools response carrying no usable tool call, whose assistant content
    parses to a JSON mapping other than ``{"done": true}``.  This is the branch
    the accepted design names, and the one at which the six envelope values were
    live locals that provenance discarded.
    """

    return {
        "id": response_id,
        "model": model,
        "system_fingerprint": system_fingerprint,
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {
                    "content": json.dumps(
                        {
                            "action_id": "a",
                            "tool": "file.read",
                            "resource": "report.txt",
                            "arguments": {},
                        }
                    )
                },
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


def _encode(envelope: Mapping[str, Any]) -> bytes:
    return json.dumps(envelope).encode("utf-8")


def _without(envelope: Mapping[str, Any], *paths: str) -> dict[str, Any]:
    """A copy of ``envelope`` with the named keys REMOVED entirely."""

    out = deepcopy(dict(envelope))
    for path in paths:
        head, _, tail = path.partition(".")
        if not tail:
            out.pop(head, None)
            continue
        if head == "choice":
            out["choices"][0].pop(tail, None)
        elif head == "usage":
            out["usage"].pop(tail, None)
        else:  # pragma: no cover - defensive
            raise KeyError(path)
    return out


# ==========================================================================
# T-01 .. T-05 -- M-1, the distinct-sentinel differential
# ==========================================================================


@pytest.mark.parametrize(
    ("field", "kwarg", "left", "right"),
    [
        ("response_id", "response_id", "chatcmpl-ENVELOPE-A", "chatcmpl-ENVELOPE-B"),
        ("effective_model", "model", "model-ENVELOPE-A", "model-ENVELOPE-B"),
        ("finish_reason", "finish_reason", "stop", "length"),
        ("system_fingerprint", "system_fingerprint", "fp-ENVELOPE-A", "fp-ENVELOPE-B"),
        ("input_tokens", "prompt_tokens", 11, 23),
        ("output_tokens", "completion_tokens", 7, 29),
    ],
    ids=["T01", "T02", "T03", "T04", "T05-input", "T05-output"],
)
def test_the_persisted_value_tracks_the_envelope_it_was_read_from(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    kwarg: str,
    left: Any,
    right: Any,
) -> None:
    """M-1.  Mutating ONE envelope field must move exactly that persisted field.

    Two envelopes differ in one value and nothing else, and both are driven
    through the same later native-tool validation failure.  A hard-coded
    ``None``, a default, a zero, a configuration value or any other fabrication
    cannot vary with an input it never read, so this fails any implementation
    that is not genuinely reading the provider envelope.  The remaining five
    fields must be UNMOVED, which is what makes it a differential rather than a
    smoke test.
    """

    _, first = _failure(monkeypatch, _encode(wrong_channel_envelope(**{kwarg: left})))
    _, second = _failure(monkeypatch, _encode(wrong_channel_envelope(**{kwarg: right})))

    assert first[field] == left
    assert second[field] == right
    assert first[field] != second[field]
    assert first["envelope_field_presence"][field] == "SUPPLIED"
    assert second["envelope_field_presence"][field] == "SUPPLIED"
    # Only the mutated field moved.
    for other in PROVIDER_ENVELOPE_FIELDS:
        if other != field:
            assert first[other] == second[other], other
    # And the failure itself is the same failure in both runs.
    assert first["failure_class"] == second["failure_class"] == "invalid_tool_call"
    assert (
        first["failure_branch"]
        == second["failure_branch"]
        == ProviderFailureBranch.NATIVE_CONTENT_ACTION_WRONG_CHANNEL.value
    )


def test_every_envelope_value_survives_a_later_native_tool_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-01 .. T-05 together, on the branch the accepted design names.

    Before C3 all six of these were live local variables at this raise site and
    all six were written as literal ``None``.
    """

    exc, record = _failure(monkeypatch, _encode(wrong_channel_envelope()))

    assert record["response_id"] == "chatcmpl-ENVELOPE-A"
    assert record["effective_model"] == "model-ENVELOPE-A"
    assert record["finish_reason"] == "stop"
    assert record["system_fingerprint"] == "fp-ENVELOPE-A"
    assert record["input_tokens"] == 11
    assert record["output_tokens"] == 7
    assert record["protocol"] == "native_tools"
    assert record["effective_seed"] == 4242
    assert record["envelope_field_presence"] == {
        name: "SUPPLIED" for name in PROVIDER_ENVELOPE_FIELDS
    }
    # The classification is EXACTLY what it was before C3.
    assert record["failure_class"] == "invalid_tool_call"
    assert exc.failure_origin is ProviderFailureOrigin.MODEL_OUTPUT
    assert str(exc) == (
        "native-tools protocol requires an actual tool call for actions"
    )


# ==========================================================================
# T-06 .. T-08 -- M-2, the three-way presence discrimination
# ==========================================================================


def test_a_provider_omitted_field_is_null_and_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-06.  Removing an optional key gives NOT_SUPPLIED, never a substitute.

    Each field is deleted on its own, so a deletion that changed any OTHER
    field's telemetry -- a fabricated replacement, a shifted default, a
    fallback read from configuration -- fails here.
    """

    baseline = wrong_channel_envelope()
    removals = {
        "response_id": ("id",),
        "effective_model": ("model",),
        "system_fingerprint": ("system_fingerprint",),
        "finish_reason": ("choice.finish_reason",),
        "input_tokens": ("usage.prompt_tokens",),
        "output_tokens": ("usage.completion_tokens",),
    }
    _, intact = _failure(monkeypatch, _encode(baseline))

    for field, paths in removals.items():
        _, record = _failure(monkeypatch, _encode(_without(baseline, *paths)))
        assert record[field] is None, field
        assert record["envelope_field_presence"][field] == "NOT_SUPPLIED", field
        # Nothing else moved, and nothing was invented in its place.
        for other in PROVIDER_ENVELOPE_FIELDS:
            if other == field:
                continue
            assert record[other] == intact[other], (field, other)
            assert record["envelope_field_presence"][other] == "SUPPLIED", (field, other)
        # The run still refuses, with the same class.
        assert record["failure_class"] == "invalid_tool_call", field


def test_the_success_path_zero_default_is_not_extended_to_the_failure_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A token count is never fabricated as ``0`` on a failure record.

    The success path reads ``usage.get("prompt_tokens", 0)``, and that default is
    deliberately NOT carried across: a failure whose provider omitted the whole
    usage object records ``null`` with ``NOT_SUPPLIED`` -- the usage read WAS
    reached, and the provider supplied nothing -- while a failure that never got
    near usage records ``null`` with ``UNOBSERVED``.  A zero is persisted only
    when the provider actually sent zero, which the third case proves.
    """

    _, omitted = _failure(
        monkeypatch, _encode(_without(wrong_channel_envelope(), "usage"))
    )
    assert omitted["input_tokens"] is None
    assert omitted["output_tokens"] is None
    assert omitted["envelope_field_presence"]["input_tokens"] == "NOT_SUPPLIED"
    assert omitted["envelope_field_presence"]["output_tokens"] == "NOT_SUPPLIED"

    _, transport = _failure(monkeypatch, None, raises=urlerror.URLError("down"))
    assert transport["input_tokens"] is None
    assert transport["envelope_field_presence"]["input_tokens"] == "UNOBSERVED"

    _, genuine_zero = _failure(
        monkeypatch,
        _encode(
            wrong_channel_envelope(prompt_tokens=0, completion_tokens=0)
        ),
    )
    assert genuine_zero["input_tokens"] == 0
    assert genuine_zero["envelope_field_presence"]["input_tokens"] == "SUPPLIED"


@pytest.mark.parametrize(
    ("error", "branch", "failure_class", "retryable"),
    [
        (
            urlerror.URLError("connection refused"),
            ProviderFailureBranch.TRANSPORT_ERROR,
            "provider_error",
            True,
        ),
        (
            TimeoutError(),
            ProviderFailureBranch.TRANSPORT_TIMEOUT,
            "timeout",
            True,
        ),
        (
            socket.timeout(),
            ProviderFailureBranch.TRANSPORT_TIMEOUT,
            "timeout",
            True,
        ),
    ],
    ids=["urlerror", "timeout", "socket-timeout"],
)
def test_a_transport_failure_fabricates_no_response_envelope_metadata(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    branch: ProviderFailureBranch,
    failure_class: str,
    retryable: bool,
) -> None:
    """T-07.  No HTTP response existed, so no envelope field may be reported.

    All six values are null AND all six presence entries say ``UNOBSERVED`` --
    not ``NOT_SUPPLIED``, which would falsely assert that a provider had been
    asked and had declined to answer.  ``protocol`` and ``effective_seed`` ARE
    populated, because both are structurally known from configuration before the
    request is sent.
    """

    _, record = _failure(monkeypatch, None, raises=error)

    assert all(record[name] is None for name in PROVIDER_ENVELOPE_FIELDS)
    assert record["envelope_field_presence"] == {
        name: "UNOBSERVED" for name in PROVIDER_ENVELOPE_FIELDS
    }
    assert record["native_tool_call_state"] == "UNOBSERVED"
    assert record["protocol"] == "native_tools"
    assert record["effective_seed"] == 4242
    assert record["failure_branch"] == branch.value
    assert record["failure_class"] == failure_class
    assert record["retryable"] is retryable


def test_a_non_2xx_response_reports_no_envelope_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class B.  The error BODY is still never read, so nothing is observable.

    The status code selects ``failure_class`` and ``retryable`` exactly as
    before, and the ``x-request-id`` header value is still the only header ever
    read back.
    """

    headers = Message()
    headers["x-request-id"] = "req-http-status"
    error = urlerror.HTTPError(
        "https://example.invalid/v1/chat/completions",
        429,
        "BODY-MUST-NOT-BE-RECORDED",
        headers,
        None,
    )
    _, record = _failure(monkeypatch, None, raises=error)

    assert record["failure_branch"] == ProviderFailureBranch.HTTP_STATUS.value
    assert record["failure_class"] == "rate_limit"
    assert record["retryable"] is True
    assert record["request_id"] == "req-http-status"
    assert record["envelope_field_presence"] == {
        name: "UNOBSERVED" for name in PROVIDER_ENVELOPE_FIELDS
    }
    assert "BODY-MUST-NOT-BE-RECORDED" not in json.dumps(record)


def test_malformed_top_level_json_cannot_fabricate_envelope_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-08(a).  C1: nothing decoded, so no field may claim to have been seen."""

    body = b'{not-a-provider-envelope "id": "SENTINEL-FROM-A-BROKEN-BODY"'
    exc, record = _failure(monkeypatch, body)

    assert record["failure_branch"] == ProviderFailureBranch.ENVELOPE_UNPARSABLE.value
    assert record["failure_class"] == "invalid_json"
    assert exc.failure_origin is ProviderFailureOrigin.PROVIDER_INFRASTRUCTURE
    assert all(record[name] is None for name in PROVIDER_ENVELOPE_FIELDS)
    assert record["envelope_field_presence"] == {
        name: "UNOBSERVED" for name in PROVIDER_ENVELOPE_FIELDS
    }
    assert "SENTINEL-FROM-A-BROKEN-BODY" not in json.dumps(record)


@pytest.mark.parametrize(
    "body",
    [
        b'["a-json-array-is-not-an-envelope"]',
        b'"a-json-string-is-not-an-envelope"',
        b"\xff\xfe-not-utf-8",
    ],
    ids=["array", "string", "undecodable"],
)
def test_a_payload_that_is_not_an_object_reaches_no_envelope_field(
    monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    """C1 again, over the other three ways the decode can fail."""

    _, record = _failure(monkeypatch, body)
    assert record["envelope_field_presence"] == {
        name: "UNOBSERVED" for name in PROVIDER_ENVELOPE_FIELDS
    }


def test_a_mapping_whose_choice_walk_fails_keeps_what_it_did_supply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-08(b).  C2: the top-level object WAS reached, so its fields survive.

    This is the split the pre-C3 handler could not express: the whole
    ``KeyError``/``TypeError`` clause was recorded as *nothing was observed*,
    even though ``id``, ``model`` and ``system_fingerprint`` were sitting in a
    decoded mapping in scope.
    """

    body = _encode(
        {
            "id": "chatcmpl-C2-SENTINEL",
            "model": "model-C2-SENTINEL",
            "system_fingerprint": "fp-C2-SENTINEL",
        }
    )
    _, record = _failure(monkeypatch, body)

    assert record["failure_branch"] == ProviderFailureBranch.ENVELOPE_UNPARSABLE.value
    assert record["failure_class"] == "invalid_json"
    assert record["response_id"] == "chatcmpl-C2-SENTINEL"
    assert record["effective_model"] == "model-C2-SENTINEL"
    assert record["system_fingerprint"] == "fp-C2-SENTINEL"
    presence = record["envelope_field_presence"]
    assert presence["response_id"] == "SUPPLIED"
    assert presence["effective_model"] == "SUPPLIED"
    assert presence["system_fingerprint"] == "SUPPLIED"
    # The tokens and the finish reason were genuinely never reached.
    assert presence["finish_reason"] == "UNOBSERVED"
    assert presence["input_tokens"] == "UNOBSERVED"
    assert presence["output_tokens"] == "UNOBSERVED"
    assert record["finish_reason"] is None


def test_a_choice_mapping_makes_finish_reason_reachable_even_when_the_walk_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C2 with a usable first choice: ``finish_reason`` becomes observable."""

    body = _encode(
        {
            "id": "chatcmpl-C2b",
            "model": "model-C2b",
            "choices": [{"finish_reason": "content_filter"}],
        }
    )
    _, record = _failure(monkeypatch, body)
    assert record["finish_reason"] == "content_filter"
    presence = record["envelope_field_presence"]
    assert presence["finish_reason"] == "SUPPLIED"
    assert presence["system_fingerprint"] == "NOT_SUPPLIED"


def test_the_three_presence_states_are_three_distinguishable_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M-2, stated directly: the §9.2 ambiguity is gone.

    Present, absent-from-the-envelope, and never-reached are three DIFFERENT
    persisted records for the same field.  Before C3 all three were one byte.
    """

    baseline = wrong_channel_envelope()
    _, supplied = _failure(monkeypatch, _encode(baseline))
    _, omitted = _failure(monkeypatch, _encode(_without(baseline, "id")))
    _, unreached = _failure(monkeypatch, None, raises=urlerror.URLError("down"))

    shapes = {
        (record["response_id"], record["envelope_field_presence"]["response_id"])
        for record in (supplied, omitted, unreached)
    }
    assert shapes == {
        ("chatcmpl-ENVELOPE-A", "SUPPLIED"),
        (None, "NOT_SUPPLIED"),
        (None, "UNOBSERVED"),
    }


# ==========================================================================
# Valid envelope, malformed assistant structure, and invalid native tool calls
# ==========================================================================


def test_a_malformed_assistant_structure_retains_what_was_already_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class D.  The envelope walk succeeded, so its four fields are mandatory.

    The token pair separates the two sub-branches honestly: at ``usage`` type
    failures the counts are genuinely unread, and at the refusal-type failure
    both are already bound and are therefore captured.
    """

    envelope = wrong_channel_envelope()
    envelope["usage"] = "not-an-object"
    _, usage_record = _failure(monkeypatch, _encode(envelope))
    assert usage_record["failure_branch"] == (
        ProviderFailureBranch.USAGE_NOT_OBJECT.value
    )
    assert usage_record["response_id"] == "chatcmpl-ENVELOPE-A"
    assert usage_record["effective_model"] == "model-ENVELOPE-A"
    assert usage_record["system_fingerprint"] == "fp-ENVELOPE-A"
    assert usage_record["finish_reason"] == "stop"
    assert usage_record["envelope_field_presence"]["input_tokens"] == "UNOBSERVED"
    assert usage_record["input_tokens"] is None

    invalid = wrong_channel_envelope()
    invalid["usage"] = {"prompt_tokens": -3, "completion_tokens": 7}
    _, field_record = _failure(monkeypatch, _encode(invalid))
    assert field_record["failure_branch"] == (
        ProviderFailureBranch.USAGE_FIELD_INVALID.value
    )
    assert field_record["response_id"] == "chatcmpl-ENVELOPE-A"
    assert field_record["envelope_field_presence"]["output_tokens"] == "UNOBSERVED"

    refusal = wrong_channel_envelope()
    refusal["choices"][0]["message"]["refusal"] = {"not": "text"}
    _, refusal_record = _failure(monkeypatch, _encode(refusal))
    assert refusal_record["failure_branch"] == (
        ProviderFailureBranch.REFUSAL_TYPE_INVALID.value
    )
    assert refusal_record["input_tokens"] == 11
    assert refusal_record["output_tokens"] == 7
    assert refusal_record["envelope_field_presence"] == {
        name: "SUPPLIED" for name in PROVIDER_ENVELOPE_FIELDS
    }


def _native_call(
    *, function: Any = None, arguments: Any = None, call_type: str = "function"
) -> dict[str, Any]:
    if function is None:
        function = {"name": "sandbox_action", "arguments": arguments}
    return {"id": "call-c3", "type": call_type, "function": function}


def _with_tool_calls(tool_calls: Any) -> dict[str, Any]:
    envelope = wrong_channel_envelope()
    envelope["choices"][0]["message"] = {"content": None, "tool_calls": tool_calls}
    return envelope


@pytest.mark.parametrize(
    ("tool_calls", "branch"),
    [
        ({"not": "a list"}, ProviderFailureBranch.NATIVE_TOOL_CALLS_NOT_LIST),
        (
            [_native_call(call_type="not-a-function", arguments="{}")],
            ProviderFailureBranch.NATIVE_CALL_NOT_FUNCTION,
        ),
        (
            [_native_call(function={"name": "not_sandbox_action", "arguments": "{}"})],
            ProviderFailureBranch.NATIVE_FUNCTION_UNEXPECTED,
        ),
        (
            [_native_call(arguments={"already": "an object"})],
            ProviderFailureBranch.NATIVE_ARGUMENTS_NOT_TEXT,
        ),
        (
            [_native_call(arguments="{not-valid-json")],
            ProviderFailureBranch.NATIVE_ARGUMENTS_INVALID_JSON,
        ),
        (
            [_native_call(arguments="[1, 2, 3]")],
            ProviderFailureBranch.NATIVE_ARGUMENTS_NOT_OBJECT,
        ),
    ],
    ids=[
        "not-a-list",
        "not-a-function",
        "wrong-function-name",
        "arguments-not-text",
        "arguments-invalid-json",
        "arguments-not-an-object",
    ],
)
def test_an_invalid_native_tool_call_retains_available_envelope_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tool_calls: Any,
    branch: ProviderFailureBranch,
) -> None:
    """Class E/F.  Every one of the six is a live local at these raise sites."""

    _, record = _failure(monkeypatch, _encode(_with_tool_calls(tool_calls)))

    assert record["failure_branch"] == branch.value
    assert record["failure_class"] == "invalid_tool_call"
    assert record["response_id"] == "chatcmpl-ENVELOPE-A"
    assert record["effective_model"] == "model-ENVELOPE-A"
    assert record["finish_reason"] == "stop"
    assert record["system_fingerprint"] == "fp-ENVELOPE-A"
    assert record["input_tokens"] == 11
    assert record["output_tokens"] == 7
    assert record["envelope_field_presence"] == {
        name: "SUPPLIED" for name in PROVIDER_ENVELOPE_FIELDS
    }
    assert record["native_tool_call_state"] == "PRESENT_UNUSABLE"
    assert record["protocol"] == "native_tools"
    assert record["effective_seed"] == 4242


@pytest.mark.parametrize(
    ("arguments", "branch"),
    [
        ({"action_id": "a", "tool": "file.read"}, ProviderFailureBranch.ACTION_KEYS_MISSING),
        (
            {
                "action_id": "a",
                "tool": "file.read",
                "resource": "r",
                "arguments": {},
                "surprise": 1,
            },
            ProviderFailureBranch.ACTION_KEYS_UNKNOWN,
        ),
        (
            {"action_id": "a", "tool": "file.read", "resource": "r", "arguments": []},
            ProviderFailureBranch.ACTION_ARGUMENTS_NOT_OBJECT,
        ),
        (
            {"action_id": "", "tool": "file.read", "resource": "r", "arguments": {}},
            ProviderFailureBranch.ACTION_FIELD_NOT_STRING,
        ),
    ],
    ids=["missing", "unknown", "arguments", "field-type"],
)
def test_an_invalid_action_object_retains_available_envelope_metadata(
    monkeypatch: pytest.MonkeyPatch,
    arguments: Mapping[str, Any],
    branch: ProviderFailureBranch,
) -> None:
    """Class F, through ``_parse_action_object``.

    The tool calls themselves parsed, so the typed state is ``PRESENT_PARSED``
    rather than ``PRESENT_UNUSABLE``: what failed was the ACTION inside them.
    """

    body = _encode(
        _with_tool_calls([_native_call(arguments=json.dumps(dict(arguments)))])
    )
    _, record = _failure(monkeypatch, body)

    assert record["failure_branch"] == branch.value
    assert record["failure_class"] == "invalid_action_format"
    assert record["response_id"] == "chatcmpl-ENVELOPE-A"
    assert record["input_tokens"] == 11
    assert record["native_tool_call_state"] == "PRESENT_PARSED"
    assert record["envelope_field_presence"] == {
        name: "SUPPLIED" for name in PROVIDER_ENVELOPE_FIELDS
    }


# ==========================================================================
# T-11 -- the typed native tool-call state
# ==========================================================================


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ({"content": '{"tool": "file.read"}'}, NativeToolCallState.KEY_ABSENT),
        (
            {"content": '{"tool": "file.read"}', "tool_calls": None},
            NativeToolCallState.NULL,
        ),
        (
            {"content": '{"tool": "file.read"}', "tool_calls": []},
            NativeToolCallState.EMPTY_LIST,
        ),
        (
            {"content": '{"tool": "file.read"}', "tool_calls": 0},
            NativeToolCallState.PRESENT_UNUSABLE,
        ),
        (
            {"content": None, "tool_calls": [{"type": "not-a-function"}]},
            NativeToolCallState.PRESENT_UNUSABLE,
        ),
    ],
    ids=["key-absent", "null", "empty-list", "falsy-unusable", "present-invalid"],
)
def test_the_native_tool_call_state_distinguishes_what_the_guard_collapses(
    monkeypatch: pytest.MonkeyPatch,
    message: Mapping[str, Any],
    expected: NativeToolCallState,
) -> None:
    """T-11.  ``tool_call_count == 0`` cannot express any of these; this can.

    All five drive a refusal, and all five previously reported the same
    ``tool_call_count`` of ``0``.  ``PRESENT_PARSED`` is covered separately, by
    the action-object cases above, and ``NOT_APPLICABLE`` by the JSON protocol.
    """

    envelope = wrong_channel_envelope()
    envelope["choices"][0]["message"] = dict(message)
    _, record = _failure(monkeypatch, _encode(envelope))
    assert record["native_tool_call_state"] == expected.value


def test_the_json_object_protocol_reports_the_native_state_as_not_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = wrong_channel_envelope()
    envelope["choices"][0]["message"] = {"content": "not json at all"}
    _, record = _failure(monkeypatch, _encode(envelope), protocol="json_object")
    assert record["native_tool_call_state"] == NativeToolCallState.NOT_APPLICABLE.value
    assert record["failure_branch"] == (
        ProviderFailureBranch.JSON_CONTENT_INVALID_JSON.value
    )
    assert record["protocol"] == "json_object"


def test_every_native_tool_call_state_member_is_reachable() -> None:
    """A closed vocabulary with an unreachable member is not a typed state."""

    covered = {
        NativeToolCallState.UNOBSERVED,
        NativeToolCallState.NOT_APPLICABLE,
        NativeToolCallState.KEY_ABSENT,
        NativeToolCallState.NULL,
        NativeToolCallState.EMPTY_LIST,
        NativeToolCallState.PRESENT_UNUSABLE,
        NativeToolCallState.PRESENT_PARSED,
    }
    assert covered == set(NativeToolCallState)


# ==========================================================================
# T-12, T-13 -- M-3, static branch and stage closure
# ==========================================================================


def _raise_provider_error_nodes() -> Iterator[ast.Call]:
    tree = ast.parse(PROVIDERS_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        func = node.exc.func
        if isinstance(func, ast.Name) and func.id == "ProviderError":
            yield node.exc


def _named_branch(call: ast.Call) -> str | None:
    for keyword in call.keywords:
        if keyword.arg != "failure_branch":
            continue
        value = keyword.value
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "ProviderFailureBranch"
        ):
            return value.attr
    return None


def test_every_raise_site_names_an_explicit_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-12, M-3.  Attribution never falls back to matching an error string.

    The AST scan is the enforcement: a new ``raise ProviderError`` that forgets
    its branch, or one that silently uses ``UNSPECIFIED``, fails here rather than
    persisting an unattributable row.  The scanner itself is proved against a
    deliberately unlabelled fixture, so a scanner that found nothing could not
    pass by vacuity.
    """

    calls = list(_raise_provider_error_nodes())
    assert calls, "the AST scan found no raise site at all"
    branches = [_named_branch(call) for call in calls]
    assert None not in branches, "a raise site names no ProviderFailureBranch"
    assert "UNSPECIFIED" not in branches, "a raise site fell back to UNSPECIFIED"
    # The USED set is EXACTLY the enum minus the legacy default: no member is
    # declared and never raised, and no site shares another site's code.
    assert set(branches) == {
        member.name for member in ProviderFailureBranch
    } - {"UNSPECIFIED"}
    assert len(branches) == len(set(branches)), "two raise sites share one branch"

    # The scanner detects an unlabelled raise, so it is not vacuously satisfied.
    fixture = ast.parse(
        'raise ProviderError("x", failure_class="invalid_json")\n'
    )
    unlabelled = [
        node.exc
        for node in ast.walk(fixture)
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
    ]
    assert _named_branch(unlabelled[0]) is None


def test_every_branch_declares_a_capture_stage() -> None:
    assert set(PROVIDER_BRANCH_CAPTURE_STAGE) == set(ProviderFailureBranch)
    assert set(PROVIDER_STAGE_REACHABLE_FIELDS) == set(ProviderCaptureStage)
    for stage, fields in PROVIDER_STAGE_REACHABLE_FIELDS.items():
        assert fields <= set(PROVIDER_ENVELOPE_FIELDS), stage


def _floor_cases() -> list[tuple[ProviderFailureBranch, bytes | None, str, BaseException | None]]:
    """One synthetic driver per branch, for the capture-floor sweep."""

    envelope = wrong_channel_envelope()
    usage_not_object = wrong_channel_envelope()
    usage_not_object["usage"] = "not-an-object"
    usage_invalid = wrong_channel_envelope()
    usage_invalid["usage"] = {"prompt_tokens": -1, "completion_tokens": 1}
    refusal = wrong_channel_envelope()
    refusal["choices"][0]["message"]["refusal"] = 17
    json_missing = wrong_channel_envelope()
    json_missing["choices"][0]["message"] = {"content": None}
    json_not_object = wrong_channel_envelope()
    json_not_object["choices"][0]["message"] = {"content": "[1,2,3]"}
    native_content_type = wrong_channel_envelope()
    native_content_type["choices"][0]["message"] = {"content": 17}

    def action(payload: Mapping[str, Any]) -> bytes:
        return _encode(_with_tool_calls([_native_call(arguments=json.dumps(dict(payload)))]))

    return [
        (ProviderFailureBranch.HTTP_STATUS, None, "native_tools",
         urlerror.HTTPError("https://example.invalid", 500, "b", Message(), None)),
        (ProviderFailureBranch.TRANSPORT_TIMEOUT, None, "native_tools", TimeoutError()),
        (ProviderFailureBranch.TRANSPORT_ERROR, None, "native_tools",
         urlerror.URLError("down")),
        (ProviderFailureBranch.ENVELOPE_UNPARSABLE, b"{broken", "native_tools", None),
        (ProviderFailureBranch.USAGE_NOT_OBJECT, _encode(usage_not_object),
         "native_tools", None),
        (ProviderFailureBranch.USAGE_FIELD_INVALID, _encode(usage_invalid),
         "native_tools", None),
        (ProviderFailureBranch.REFUSAL_TYPE_INVALID, _encode(refusal),
         "native_tools", None),
        (ProviderFailureBranch.NATIVE_TOOL_CALLS_NOT_LIST,
         _encode(_with_tool_calls({"not": "a list"})), "native_tools", None),
        (ProviderFailureBranch.NATIVE_CALL_NOT_FUNCTION,
         _encode(_with_tool_calls([_native_call(call_type="x", arguments="{}")])),
         "native_tools", None),
        (ProviderFailureBranch.NATIVE_FUNCTION_UNEXPECTED,
         _encode(_with_tool_calls([_native_call(function={"name": "nope", "arguments": "{}"})])),
         "native_tools", None),
        (ProviderFailureBranch.NATIVE_ARGUMENTS_NOT_TEXT,
         _encode(_with_tool_calls([_native_call(arguments={"a": 1})])), "native_tools", None),
        (ProviderFailureBranch.NATIVE_ARGUMENTS_INVALID_JSON,
         _encode(_with_tool_calls([_native_call(arguments="{bad")])), "native_tools", None),
        (ProviderFailureBranch.NATIVE_ARGUMENTS_NOT_OBJECT,
         _encode(_with_tool_calls([_native_call(arguments="[1]")])), "native_tools", None),
        (ProviderFailureBranch.NATIVE_CONTENT_TYPE_INVALID,
         _encode(native_content_type), "native_tools", None),
        (ProviderFailureBranch.NATIVE_CONTENT_ACTION_WRONG_CHANNEL, _encode(envelope),
         "native_tools", None),
        (ProviderFailureBranch.JSON_CONTENT_MISSING, _encode(json_missing),
         "json_object", None),
        (ProviderFailureBranch.JSON_CONTENT_INVALID_JSON,
         _encode(_json_content_invalid_json()), "json_object", None),
        (ProviderFailureBranch.JSON_CONTENT_NOT_OBJECT, _encode(json_not_object),
         "json_object", None),
        (ProviderFailureBranch.ACTION_KEYS_MISSING,
         action({"action_id": "a"}), "native_tools", None),
        (ProviderFailureBranch.ACTION_KEYS_UNKNOWN,
         action({"action_id": "a", "tool": "t", "resource": "r", "arguments": {}, "x": 1}),
         "native_tools", None),
        (ProviderFailureBranch.ACTION_ARGUMENTS_NOT_OBJECT,
         action({"action_id": "a", "tool": "t", "resource": "r", "arguments": 3}),
         "native_tools", None),
        (ProviderFailureBranch.ACTION_FIELD_NOT_STRING,
         action({"action_id": 4, "tool": "t", "resource": "r", "arguments": {}}),
         "native_tools", None),
    ]


def _json_content_invalid_json() -> dict[str, Any]:
    envelope = wrong_channel_envelope()
    envelope["choices"][0]["message"] = {"content": "{not-json"}
    return envelope


@pytest.mark.parametrize(
    ("branch", "body", "protocol", "error"),
    _floor_cases(),
    ids=[case[0].name for case in _floor_cases()],
)
def test_no_branch_reports_unobserved_for_a_field_its_stage_reaches(
    monkeypatch: pytest.MonkeyPatch,
    branch: ProviderFailureBranch,
    body: bytes | None,
    protocol: str,
    error: BaseException | None,
) -> None:
    """T-13, M-3.  The capture FLOOR, driven synthetically for every branch.

    This is what replaces a self-reported *available but dropped* flag: a field
    the branch's stage makes reachable may never be persisted as ``UNOBSERVED``,
    so an adapter that silently dropped one becomes a test failure instead of a
    persisted ambiguity.  It also proves each branch is actually REACHED by a
    synthetic input, so the enum documents real control flow.
    """

    _, record = _failure(monkeypatch, body, protocol=protocol, raises=error)
    assert record["failure_branch"] == branch.value

    floor = PROVIDER_STAGE_REACHABLE_FIELDS[PROVIDER_BRANCH_CAPTURE_STAGE[branch]]
    presence = record["envelope_field_presence"]
    for name in sorted(floor):
        assert presence[name] != "UNOBSERVED", (branch.name, name)
    # And the presence object is closed in both directions.
    assert set(presence) == set(PROVIDER_ENVELOPE_FIELDS)
    assert set(presence.values()) <= {"SUPPLIED", "NOT_SUPPLIED", "UNOBSERVED"}
    # Protocol is structurally known at every stage past PRE_REQUEST.
    assert record["protocol"] == protocol


def test_the_credential_branch_reports_the_protocol_but_no_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A0.  Raised before the effective seed is resolved, and it says so.

    ``effective_seed`` is null here for a different reason than it is null when
    a provider does not support seeding, and ``failure_branch`` is what
    separates them -- no additional flag is introduced to carry that.
    """

    monkeypatch.delenv(CREDENTIAL_ENV, raising=False)
    provider = _provider()
    with pytest.raises(ProviderError) as captured:
        _generate(provider)
    record = captured.value.provenance(model=provider.model, latency_ms=0.0)
    assert record["failure_branch"] == ProviderFailureBranch.CREDENTIAL_ENV_UNSET.value
    assert record["protocol"] == "native_tools"
    assert record["effective_seed"] is None
    assert record["envelope_field_presence"] == {
        name: "UNOBSERVED" for name in PROVIDER_ENVELOPE_FIELDS
    }
    assert CREDENTIAL not in json.dumps(record)


def test_a_provider_without_seed_support_records_a_null_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``effective_seed`` is null legitimately, on the same terms as success."""

    _install(monkeypatch, body=_encode(wrong_channel_envelope()))
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env=CREDENTIAL_ENV,
        supports_seed=False,
    )
    with pytest.raises(ProviderError) as captured:
        _generate(provider)
    record = captured.value.provenance(model=provider.model, latency_ms=0.0)
    assert record["effective_seed"] is None
    assert record["failure_branch"] == (
        ProviderFailureBranch.NATIVE_CONTENT_ACTION_WRONG_CHANNEL.value
    )


# ==========================================================================
# T-09, T-14 .. T-17 -- AC-1, the accept/refuse decision function
# ==========================================================================


#: The success-path provenance a fixed synthetic envelope produced BEFORE C3,
#: authored here as a snapshot.  ``latency_ms`` and ``client_request_id`` are the
#: only two values that cannot be fixed, and both are checked separately.
SUCCESS_SNAPSHOT: dict[str, Any] = {
    "tool_call_count": 1,
    "multi_tool_call": False,
    "additional_action_count": 0,
    "tool_contract_refreshed": False,
    "emitted_action_ids": ["read-report"],
    "emitted_resources": ["report.txt"],
    "emitted_proposals": [
        '{"action_id": "model-id", "tool": "file.read", '
        '"resource": "report.txt", "arguments": {}}'
    ],
    "emitted_actions": [
        {
            "action_id": "read-report",
            "tool": "file.read",
            "resource": "report.txt",
            "arguments": {},
            "source": None,
            "derived_from_untrusted": False,
            "risk_severity": "low",
        }
    ],
    "emitted_tool_call_ids": ["call-fixed"],
    "outcome": "action",
    "failure_class": None,
    "client_request_id": "<generated>",
    "request_id": "req-c3",
    "response_id": "chatcmpl-success-fixed",
    "configured_model": "synthetic-model",
    "effective_model": "synthetic-model-fixed",
    "finish_reason": "tool_calls",
    "system_fingerprint": "fp-success-fixed",
    "input_tokens": 13,
    "output_tokens": 5,
    "latency_ms": 0.0,
    "retryable": False,
    "protocol": "native_tools",
    "effective_seed": 4242,
    "original_action_id": "model-id",
    "canonical_action_id": "read-report",
    "original_resource": "report.txt",
    "canonical_resource": "report.txt",
}


def _success_body() -> bytes:
    return _encode(
        {
            "id": "chatcmpl-success-fixed",
            "model": "synthetic-model-fixed",
            "system_fingerprint": "fp-success-fixed",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": None,
                        "refusal": None,
                        "tool_calls": [
                            {
                                "id": "call-fixed",
                                "type": "function",
                                "function": {
                                    "name": "sandbox_action",
                                    "arguments": json.dumps(
                                        {
                                            "action_id": "model-id",
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
            "usage": {"prompt_tokens": 13, "completion_tokens": 5},
        }
    )


def _json_object_success_body() -> bytes:
    return _encode(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "action_id": "json-a",
                                "tool": "file.read",
                                "resource": "report.txt",
                                "arguments": {},
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
    )


def test_the_success_path_is_byte_equivalent_to_the_pre_c3_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-09.  ``ProviderResponse.provenance()`` is untouched, and this proves it.

    The comparison is on the canonical serialization, not on a subset of keys,
    so a key added, removed, renamed, reordered in value or retyped on the
    SUCCESS record fails here.  C3 changes the failure record only.
    """

    _install(monkeypatch, body=_success_body())
    response = _generate(
        _provider(),
        scripted=(Action("read-report", "file.read", "report.txt", {}),),
    )
    assert response is not None
    record = response.provenance()

    assert list(record) == list(SUCCESS_SNAPSHOT)
    assert record["client_request_id"]
    assert record["latency_ms"] >= 0.0
    normalized = dict(record)
    normalized["client_request_id"] = "<generated>"
    normalized["latency_ms"] = 0.0
    assert json.dumps(normalized, sort_keys=True, separators=(",", ":")) == json.dumps(
        SUCCESS_SNAPSHOT, sort_keys=True, separators=(",", ":")
    )
    # None of the C3 failure keys leaks onto the success record.
    for name in ("failure_branch", "envelope_field_presence", "native_tool_call_state"):
        assert name not in record


@pytest.mark.parametrize(
    ("body", "protocol", "outcome", "action_id", "tool_calls"),
    [
        (_success_body(), "native_tools", "action", "read-report", 1),
        (
            _encode(
                {
                    "choices": [{"message": {"content": None}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }
            ),
            "native_tools",
            "no_action",
            None,
            0,
        ),
        (
            _encode(
                {
                    "choices": [{"message": {"content": '{"done":true}'}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }
            ),
            "native_tools",
            "no_action",
            None,
            0,
        ),
        (
            _encode(
                {
                    "choices": [{"message": {"content": "I am finished."}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }
            ),
            "native_tools",
            "no_action",
            None,
            0,
        ),
        (
            _encode(
                {
                    "choices": [
                        {"message": {"content": None, "refusal": "I cannot do that."}}
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }
            ),
            "native_tools",
            "model_refusal",
            None,
            0,
        ),
        (
            _encode(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "action_id": "json-a",
                                        "tool": "file.read",
                                        "resource": "report.txt",
                                        "arguments": {},
                                    }
                                )
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }
            ),
            "json_object",
            "action",
            "read-report",
            1,
        ),
    ],
    ids=["native-call", "content-null", "done-true", "plain-text", "refusal", "json-object"],
)
def test_every_input_accepted_before_c3_is_still_accepted(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
    protocol: str,
    outcome: str,
    action_id: str | None,
    tool_calls: int,
) -> None:
    """T-14, AC-1.  The accept set is unchanged, outcome for outcome."""

    _install(monkeypatch, body=body)
    response = _generate(
        _provider(protocol),
        scripted=(Action("read-report", "file.read", "report.txt", {}),),
    )
    assert response is not None
    assert response.outcome == outcome
    assert (response.action.action_id if response.action else None) == action_id
    assert response.tool_call_count == tool_calls
    assert response.additional_actions == ()


def test_a_multi_tool_call_turn_is_still_preserved_rather_than_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-14 continued.  Grouped turns still pass through unchanged."""

    calls = [
        {
            "id": f"call-{index}",
            "type": "function",
            "function": {
                "name": "sandbox_action",
                "arguments": json.dumps(
                    {
                        "action_id": f"a{index}",
                        "tool": "file.read",
                        "resource": f"r{index}.txt",
                        "arguments": {},
                    }
                ),
            },
        }
        for index in range(2)
    ]
    _install(monkeypatch, body=_encode(_with_tool_calls(calls)))
    response = _generate(_provider())
    assert response is not None
    assert response.outcome == "action"
    assert response.tool_call_count == 2
    assert len(response.additional_actions) == 1
    assert response.emitted_proposals() == tuple(
        call["function"]["arguments"] for call in calls
    )
    assert response.tool_call_ids == ("call-0", "call-1")


@pytest.mark.parametrize(
    ("branch", "body", "protocol", "error"),
    _floor_cases(),
    ids=[case[0].name for case in _floor_cases()],
)
def test_every_input_refused_before_c3_is_still_refused_the_same_way(
    monkeypatch: pytest.MonkeyPatch,
    branch: ProviderFailureBranch,
    body: bytes | None,
    protocol: str,
    error: BaseException | None,
) -> None:
    """T-15, AC-1.  Same class, same origin, same message, over every branch.

    The expected values are read from the module's own raise sites rather than
    pasted, so this cannot be satisfied by editing an expectation to match a
    changed implementation: it asserts the raise site's OWN literals.
    """

    expected_class, expected_message = _declared_failure(branch)
    exc, record = _failure(monkeypatch, body, protocol=protocol, raises=error)

    assert record["failure_class"] == expected_class, branch.name
    assert record["failure_branch"] == branch.value
    if expected_message is not None:
        assert str(exc) == expected_message, branch.name
    assert record["outcome"] == "failure"
    # ``failure_origin`` is deliberately NOT persisted, and C3 does not add it.
    assert "failure_origin" not in record
    assert isinstance(exc.failure_origin, ProviderFailureOrigin)


def _declared_failure(branch: ProviderFailureBranch) -> tuple[str, str | None]:
    """The ``failure_class`` and constant message the raise site itself names."""

    for call in _raise_provider_error_nodes():
        if _named_branch(call) != branch.name:
            continue
        failure_class = "provider_error"
        for keyword in call.keywords:
            if keyword.arg == "failure_class" and isinstance(
                keyword.value, ast.Constant
            ):
                failure_class = str(keyword.value.value)
        message = call.args[0] if call.args else None
        literal = message.value if isinstance(message, ast.Constant) else None
        return failure_class, literal
    raise AssertionError(f"no raise site declares {branch.name}")


def test_a_malformed_action_is_still_not_rescued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-16, AC-1.  C3 improves the RECORD of a refusal, never the verdict.

    The wrong-channel envelope now carries six values it did not carry before,
    and it is still refused, still produces no ``Action``, and still executes
    no tool.
    """

    class MustNotExecute:
        def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
            raise AssertionError("a refused turn must not execute a tool")

    _install(monkeypatch, body=_encode(wrong_channel_envelope()))
    provider = _provider()
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
        user_prompt=USER_PROMPT,
    )
    result = ExperimentalAgent(
        provider, MustNotExecute(), system_prompt=SYSTEM_PROMPT, max_steps=4
    ).run(user_prompt=USER_PROMPT, scripted_actions=(), context=context)

    assert result.outcomes == ()
    assert result.provider_responses == ()
    assert result.failure_class == "invalid_tool_call"
    assert len(result.provider_attempts) == 1
    attempt = result.provider_attempts[0]
    assert attempt["outcome"] == "failure"
    assert attempt["response_id"] == "chatcmpl-ENVELOPE-A"


def test_the_request_payload_and_native_tool_schema_are_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-17, AC-1.  The model is asked EXACTLY the same question.

    Captured from the request the provider actually built, on both protocols,
    and compared against an authored snapshot of the model-visible surface.  A
    changed prompt, tool definition, ``tool_choice``, ``parallel_tool_calls``,
    ``response_format`` or sampling parameter fails here.
    """

    captured: dict[str, Any] = {}
    _install(monkeypatch, body=_success_body(), captured=captured)
    _generate(_provider())
    payload = captured["payload"]

    assert set(payload) == {
        "model",
        "temperature",
        "messages",
        "top_p",
        "max_completion_tokens",
        "seed",
        "tools",
        "tool_choice",
        "parallel_tool_calls",
    }
    assert payload["tool_choice"] == "auto"
    assert payload["parallel_tool_calls"] is False
    assert payload["seed"] == 4242
    assert payload["tools"] == [_native_action_tool(())]
    assert [message["role"] for message in payload["messages"]] == ["system", "user"]
    assert payload["messages"][0]["content"].startswith(SYSTEM_PROMPT)
    assert payload["messages"][1]["content"].startswith(USER_PROMPT)

    json_captured: dict[str, Any] = {}
    _install(monkeypatch, body=_json_object_success_body(), captured=json_captured)
    _generate(_provider("json_object"))
    assert json_captured["payload"]["response_format"] == {"type": "json_object"}
    assert "tools" not in json_captured["payload"]
    assert "tool_choice" not in json_captured["payload"]
    assert json_captured["payload"]["messages"][0]["content"].startswith(SYSTEM_PROMPT)


def test_the_native_tool_schema_is_semantically_unchanged() -> None:
    """T-17 continued.  The advertised contract is the same object it was.

    ``NATIVE_TOOL_ADAPTER_VERSION`` deliberately does NOT move for C3, and this
    is the assertion that makes holding it truthful: bumping it would claim the
    adapter changed, and it did not.
    """

    tool = _native_action_tool(("report.txt", "notes.txt"))
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "sandbox_action"
    parameters = tool["function"]["parameters"]
    assert parameters["required"] == ["action_id", "tool", "resource", "arguments"]
    assert parameters["additionalProperties"] is False
    assert parameters["properties"]["resource"]["enum"] == ["notes.txt", "report.txt"]
    assert NATIVE_TOOL_ADAPTER_VERSION == "native-tools-adapter-3"


@pytest.mark.parametrize(
    ("status", "failure_class", "retryable"),
    [
        (400, "provider_error", False),
        (403, "provider_error", False),
        (408, "timeout", True),
        (429, "rate_limit", True),
        (500, "provider_error", True),
        (502, "provider_error", True),
        (503, "provider_error", True),
        (504, "timeout", True),
    ],
)
def test_retryability_is_unchanged_for_every_status(
    monkeypatch: pytest.MonkeyPatch, status: int, failure_class: str, retryable: bool
) -> None:
    """T-18(a), AC-1.  The status-to-class and status-to-retry maps are frozen."""

    error = urlerror.HTTPError(
        "https://example.invalid", status, "body", Message(), None
    )
    _, record = _failure(monkeypatch, None, raises=error)
    assert record["failure_class"] == failure_class
    assert record["retryable"] is retryable


def test_a_provider_failure_still_breaks_the_agent_loop_without_retrying(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-18(b), AC-1.  No retry is introduced, and none is removed.

    The provider is called exactly once even though the agent is allowed four
    steps, so the loop still breaks at the first ``ProviderError`` and records
    exactly one attempt.
    """

    calls: list[int] = []

    class CountingProvider(OpenAICompatibleProvider):
        def generate_action(self, **kwargs: Any) -> Any:
            calls.append(1)
            return super().generate_action(**kwargs)

    class MustNotExecute:
        def execute(self, action: Action, context: RuntimeContext) -> GatewayOutcome:
            raise AssertionError("a failed provider call must not execute a tool")

    _install(monkeypatch, body=None, raises=urlerror.URLError("down"))
    provider = CountingProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env=CREDENTIAL_ENV,
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
        user_prompt=USER_PROMPT,
    )
    result = ExperimentalAgent(
        provider, MustNotExecute(), system_prompt=SYSTEM_PROMPT, max_steps=4
    ).run(user_prompt=USER_PROMPT, scripted_actions=(), context=context)

    assert calls == [1]
    assert len(result.provider_attempts) == 1
    assert context.usage.model_calls == 1
    assert (context.usage.input_tokens, context.usage.output_tokens) == (0, 0)
    assert result.error.startswith("ProviderError: ")


# ==========================================================================
# T-19 -- the security and privacy boundary
# ==========================================================================


@pytest.mark.parametrize(
    ("branch", "body", "protocol", "error"),
    _floor_cases(),
    ids=[case[0].name for case in _floor_cases()],
)
def test_no_failure_record_discloses_anything_new(
    monkeypatch: pytest.MonkeyPatch,
    branch: ProviderFailureBranch,
    body: bytes | None,
    protocol: str,
    error: BaseException | None,
) -> None:
    """T-19.  Every branch, checked against every forbidden class at once.

    The credential, the endpoint, the prompts and the raw response body are all
    distinctive strings, and none may appear anywhere in the serialized failure
    record.  The record's key set is also closed: only the documented keys are
    emitted, so a future field cannot be added without this failing first.
    """

    _, record = _failure(monkeypatch, body, protocol=protocol, raises=error)
    serialized = json.dumps(record, sort_keys=True, default=str)

    for forbidden in (
        CREDENTIAL,
        SYSTEM_PROMPT,
        USER_PROMPT,
        "example.invalid",
        "Authorization",
        "Bearer",
        "BODY-MUST-NOT-BE-RECORDED",
        "sandbox_action",
        "report.txt",
    ):
        assert forbidden not in serialized, (branch.name, forbidden)

    assert set(record) == {
        "outcome",
        "tool_call_count",
        "multi_tool_call",
        "additional_action_count",
        "tool_contract_refreshed",
        "failure_class",
        "client_request_id",
        "request_id",
        "response_id",
        "configured_model",
        "effective_model",
        "finish_reason",
        "system_fingerprint",
        "input_tokens",
        "output_tokens",
        "latency_ms",
        "retryable",
        "failure_branch",
        "envelope_field_presence",
        "protocol",
        "effective_seed",
        "native_tool_call_state",
    }
    # Every C3 field is an instrument-authored enum, a short provider
    # identifier, an integer or null.  Nothing is an unbounded payload.
    assert isinstance(record["failure_branch"], str)
    assert isinstance(record["native_tool_call_state"], str)
    for name in ("input_tokens", "output_tokens", "effective_seed"):
        assert record[name] is None or isinstance(record[name], int)


def test_assistant_content_never_reaches_the_failure_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The typed native state is the sanctioned substitute for content.

    It reports the SHAPE of ``message["tool_calls"]`` and copies nothing out of
    it -- not the function name, not the arguments string, not the call id, and
    not one byte of assistant text.
    """

    envelope = wrong_channel_envelope()
    envelope["choices"][0]["message"] = {
        "content": "ASSISTANT-TEXT-SENTINEL",
        "tool_calls": [
            {
                "id": "CALL-ID-SENTINEL",
                "type": "function",
                "function": {
                    "name": "FUNCTION-NAME-SENTINEL",
                    "arguments": '{"resource": "RESOURCE-VALUE-SENTINEL"}',
                },
            }
        ],
    }
    _, record = _failure(monkeypatch, _encode(envelope))
    serialized = json.dumps(record, sort_keys=True)
    for sentinel in (
        "ASSISTANT-TEXT-SENTINEL",
        "CALL-ID-SENTINEL",
        "FUNCTION-NAME-SENTINEL",
        "RESOURCE-VALUE-SENTINEL",
    ):
        assert sentinel not in serialized, sentinel
    assert record["native_tool_call_state"] == "PRESENT_UNUSABLE"


# ==========================================================================
# T-20 -- legacy compatibility
# ==========================================================================


def test_a_legacy_bare_provider_error_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-20.  Every pre-C3 caller is still valid, and records the truth.

    A third-party ``AgentProvider`` that raises ``ProviderError("message")``
    supplies no capture, so its record is honestly all-``UNOBSERVED`` with an
    ``UNSPECIFIED`` branch -- which is what actually happened -- rather than a
    fabricated one.
    """

    exc = ProviderError("synthetic provider failure")
    record = exc.provenance(model="legacy-model", latency_ms=3.0)

    assert record["failure_class"] == "provider_error"
    assert record["failure_branch"] == "UNSPECIFIED"
    assert record["native_tool_call_state"] == "UNOBSERVED"
    assert record["protocol"] is None
    assert record["effective_seed"] is None
    assert record["envelope_field_presence"] == {
        name: "UNOBSERVED" for name in PROVIDER_ENVELOPE_FIELDS
    }
    assert all(record[name] is None for name in PROVIDER_ENVELOPE_FIELDS)

    # And the full pre-C3 keyword surface still constructs.
    legacy = ProviderError(
        "legacy",
        failure_class="timeout",
        client_request_id="c",
        request_id="r",
        retryable=True,
        tool_call_count=2,
        tool_contract_refreshed=True,
        failure_origin=ProviderFailureOrigin.MODEL_OUTPUT,
    )
    legacy_record = legacy.provenance(model="m", latency_ms=1.0)
    assert legacy_record["multi_tool_call"] is True
    assert legacy_record["tool_contract_refreshed"] is True
    assert legacy_record["retryable"] is True


def test_the_new_constructor_parameters_are_keyword_only() -> None:
    """A positional third argument must not silently become telemetry."""

    signature = inspect.signature(ProviderError.__init__)
    for name in ("failure_branch", "envelope", "native_tool_call_state"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert signature.parameters[name].default is not inspect.Parameter.empty


# ==========================================================================
# The capture object itself
# ==========================================================================


def test_presence_is_declared_by_the_call_site_not_derived_from_the_value() -> None:
    """An unreached field stays UNOBSERVED even though its value is null.

    Deriving presence from the value at read time is exactly the ambiguity C3
    repairs, so the capture refuses to do it: ``reached`` is what decides.
    """

    capture = ProviderEnvelopeCapture.observed(
        reached=("response_id", "effective_model"),
        protocol="native_tools",
        effective_seed=7,
        response_id="id-1",
    )
    presence = capture.presence_provenance()
    assert presence["response_id"] == ProviderCaptureState.SUPPLIED.value
    assert presence["effective_model"] == ProviderCaptureState.NOT_SUPPLIED.value
    assert presence["finish_reason"] == ProviderCaptureState.UNOBSERVED.value
    assert set(presence) == set(PROVIDER_ENVELOPE_FIELDS)


def test_a_value_for_an_unreached_field_is_refused() -> None:
    with pytest.raises(ValueError, match="unreached envelope fields"):
        ProviderEnvelopeCapture.observed(reached=(), response_id="smuggled")
    with pytest.raises(ValueError, match="unknown captured envelope fields"):
        ProviderEnvelopeCapture.observed(reached=("not_a_field",))


def test_the_accepted_minimum_telemetry_set_is_closed_and_ordered() -> None:
    """The eleven fields, in the accepted order, and nothing beyond them."""

    assert PROVIDER_FAILURE_TELEMETRY_FIELDS == (
        "failure_branch",
        "response_id",
        "system_fingerprint",
        "finish_reason",
        "effective_model",
        "input_tokens",
        "output_tokens",
        "envelope_field_presence",
        "protocol",
        "effective_seed",
        "native_tool_call_state",
    )
    record = ProviderError("x").provenance(model="m", latency_ms=0.0)
    assert set(PROVIDER_FAILURE_TELEMETRY_FIELDS) <= set(record)


def test_the_tool_contract_repair_and_its_rejection_behaviour_are_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-10.  The Class-P tool-contract repair is untouched, and still recorded.

    The opt-in ``trailing_user`` policy still appends exactly one minimal user
    turn carrying the unchanged ``TOOL_CONTRACT_NOTICE``, the default policy
    still appends nothing, and ``tool_contract_refreshed`` still reaches the
    FAILURE record by the same back-fill it always used. C3 neither widens the
    repair nor changes when it fires.
    """

    history = (
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
            "output": "synthetic output",
            "error": None,
        },
    )
    body = _encode(wrong_channel_envelope())

    captured: dict[str, Any] = {}
    _install(monkeypatch, body=body, captured=captured)
    repaired = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env=CREDENTIAL_ENV,
        protocol="native_tools",
        tool_contract_policy="trailing_user",
    )
    with pytest.raises(ProviderError) as captured_error:
        repaired.generate_action(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT,
            scripted_actions=(),
            step=1,
            seed=1729,
            history=history,
        )
    messages = captured["payload"]["messages"]
    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "user",
    ]
    assert messages[-1]["content"] == TOOL_CONTRACT_NOTICE
    record = captured_error.value.provenance(model=repaired.model, latency_ms=0.0)
    assert record["tool_contract_refreshed"] is True
    assert record["failure_class"] == "invalid_tool_call"

    default_captured: dict[str, Any] = {}
    _install(monkeypatch, body=body, captured=default_captured)
    with pytest.raises(ProviderError) as default_error:
        _provider().generate_action(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT,
            scripted_actions=(),
            step=1,
            seed=1729,
            history=history,
        )
    assert [message["role"] for message in default_captured["payload"]["messages"]] == [
        "system",
        "user",
        "assistant",
        "tool",
    ]
    assert default_error.value.provenance(
        model="synthetic-model", latency_ms=0.0
    )["tool_contract_refreshed"] is False


def test_the_tool_contract_policy_surface_is_unchanged() -> None:
    """The policy vocabulary, its default and its marker text are all frozen."""

    assert TOOL_CONTRACT_POLICIES == frozenset({"trailing_user", "none"})
    assert DEFAULT_TOOL_CONTRACT_POLICY == "none"
    assert TOOL_CONTRACT_NOTICE.startswith("Protocol marker.")
    assert "carries no instruction" in TOOL_CONTRACT_NOTICE
    with pytest.raises(ValueError, match="tool_contract_policy"):
        OpenAICompatibleProvider(
            endpoint="https://example.invalid/v1/chat/completions",
            model="synthetic-model",
            api_key_env=CREDENTIAL_ENV,
            tool_contract_policy="invented",
        )
