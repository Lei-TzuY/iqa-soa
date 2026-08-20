"""Regression tests for the pilot-v5 canonical resource/action contract.

The mistral-small3.2:24b Model B smoke on pilot-v4 showed UA-003 failing
because the model represented the frozen resource ``restricted/demo.txt`` as
``resource="demo.txt"`` plus an invented ``arguments.mode="restricted"``.
These tests pin the repaired contract: a declared, case-derived finite
resource vocabulary is exposed to the model (native tool-schema enum plus a
matching text instruction), and only narrow, deterministic syntactic
normalization is applied afterwards -- never fuzzy reconstruction. Real
network access is never exercised: HTTP is monkeypatched exactly as the
existing provider test suite already does.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from iqa_soa.agent.providers import OpenAICompatibleProvider, _resolve_canonical_resource
from iqa_soa.benchmark.loader import load_benchmark_cases
from iqa_soa.experiment.runner import ExperimentRunner, load_experiment_config
from iqa_soa.types import Action


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = PROJECT_ROOT / "benchmark"


# ---------------------------------------------------------------------------
# Pure-function resolver tests
# ---------------------------------------------------------------------------


def test_resolver_accepts_only_unambiguous_syntactic_variants() -> None:
    canonical = ("restricted/demo.txt", "public/report.txt")
    assert _resolve_canonical_resource("restricted/demo.txt", canonical) == "restricted/demo.txt"
    assert _resolve_canonical_resource("Restricted/Demo.txt", canonical) == "restricted/demo.txt"
    assert _resolve_canonical_resource("/restricted/demo.txt/", canonical) == "restricted/demo.txt"
    assert _resolve_canonical_resource("restricted\\demo.txt", canonical) == "restricted/demo.txt"
    # Mistral's actual failure mode: information split across fields, not a
    # syntactic variant of a single canonical string. Must NOT be guessed.
    assert _resolve_canonical_resource("demo.txt", canonical) is None
    assert _resolve_canonical_resource("restricted_demo.txt", canonical) is None
    assert _resolve_canonical_resource("nonexistent/file.txt", canonical) is None


def test_resolver_refuses_ambiguous_matches() -> None:
    # PRIV-001-style collision: two canonical resources share a basename.
    canonical = ("public/profile.txt", "private/profile.txt")
    assert _resolve_canonical_resource("profile.txt", canonical) is None


def test_case_derived_vocabulary_excludes_ground_truth_and_wildcards() -> None:
    """canonical_resources is derived only from environment/allowed/forbidden/
    protected resource data -- never from ground_truth or scripted_actions --
    and excludes wildcard patterns, which are not proposable identifiers."""

    (case,) = load_benchmark_cases(BENCHMARK_ROOT / "unauthorized_action" / "UA-001.yaml")
    resources = case.canonical_resources
    assert set(resources) == {"public/report.txt", "restricted/demo.txt"}
    assert all("*" not in item for item in resources)


# ---------------------------------------------------------------------------
# Provider-level tests: the real parsing/canonicalization pipeline
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def getheader(self, name: str) -> str | None:
        del name
        return None

    def read(self) -> bytes:
        return self._body


def _tool_call_response(resource: str) -> bytes:
    return json.dumps(
        {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": None,
                        "refusal": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "sandbox_action",
                                    "arguments": json.dumps(
                                        {
                                            "action_id": "model-invented-id",
                                            "tool": "file.read",
                                            "resource": resource,
                                            "arguments": {},
                                        }
                                    ),
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
    ).encode("utf-8")


@pytest.mark.parametrize(
    "proposed,expected_canonical,expected_changed",
    [
        ("restricted/demo.txt", "restricted/demo.txt", False),
        ("Restricted/Demo.txt", "restricted/demo.txt", True),
        ("/restricted/demo.txt/", "restricted/demo.txt", True),
        ("demo.txt", None, False),
        ("totally/unrelated.txt", None, False),
    ],
)
def test_generate_action_canonicalizes_resource_and_records_provenance(
    monkeypatch: pytest.MonkeyPatch,
    proposed: str,
    expected_canonical: str | None,
    expected_changed: bool,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float) -> _FakeHTTPResponse:
        del timeout
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeHTTPResponse(_tool_call_response(proposed))

    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "not-a-real-secret")
    monkeypatch.setattr("iqa_soa.agent.providers.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
        protocol="native_tools",
    )
    canonical_resources = ("public/report.txt", "restricted/demo.txt")
    response = provider.generate_action(
        system_prompt="system",
        user_prompt="user",
        scripted_actions=(
            Action("unauthorized-read", "file.read", "restricted/demo.txt", {}),
        ),
        step=0,
        seed=1,
        canonical_resources=canonical_resources,
    )
    assert response is not None and response.action is not None
    assert response.original_resource == proposed
    resolved = expected_canonical if expected_canonical is not None else proposed
    assert response.canonical_resource == resolved
    assert response.action.resource == resolved
    # Provenance is never silent: the raw and resolved values are both
    # always recorded, even when nothing changed.
    if expected_changed:
        assert response.original_resource != response.canonical_resource
    else:
        assert response.original_resource == response.canonical_resource
    # The tool schema exposed the canonical vocabulary as a strict enum.
    tool_schema = captured["payload"]["tools"][0]["function"]["parameters"]
    assert sorted(tool_schema["properties"]["resource"]["enum"]) == sorted(canonical_resources)


def test_generate_action_without_canonical_resources_is_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No declared vocabulary (e.g. a case with none) leaves resources untouched."""

    def fake_urlopen(req: Any, timeout: float) -> _FakeHTTPResponse:
        del req, timeout
        return _FakeHTTPResponse(_tool_call_response("whatever/path.txt"))

    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "not-a-real-secret")
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
        step=0,
        seed=1,
        canonical_resources=(),
    )
    assert response is not None and response.action is not None
    assert response.action.resource == "whatever/path.txt"
    assert response.original_resource == response.canonical_resource == "whatever/path.txt"


# ---------------------------------------------------------------------------
# End-to-end: canonicalization plus governance through the real runner
# ---------------------------------------------------------------------------


def _fake_urlopen_for(resource: str) -> Any:
    def handler(req: Any, timeout: float) -> _FakeHTTPResponse:
        del timeout
        payload = json.loads(req.data.decode("utf-8"))
        # First call of a run has no assistant/tool history yet (system+user
        # only); every later call must terminate the plan.
        if len(payload["messages"]) <= 2:
            return _FakeHTTPResponse(_tool_call_response(resource))
        done = json.dumps(
            {
                "choices": [{"finish_reason": "stop", "message": {"content": None}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 1},
            }
        ).encode("utf-8")
        return _FakeHTTPResponse(done)

    return handler


def _ua001_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, resource: str
) -> list[dict[str, Any]]:
    monkeypatch.setenv("SYNTHETIC_TEST_KEY", "not-a-real-secret")
    monkeypatch.setattr(
        "iqa_soa.agent.providers.request.urlopen", _fake_urlopen_for(resource)
    )
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-model",
        api_key_env="SYNTHETIC_TEST_KEY",
        protocol="native_tools",
    )
    config = load_experiment_config(PROJECT_ROOT / "configs" / "experiment.yaml").with_overrides(
        output_root=tmp_path, repetitions=1
    )
    output = ExperimentRunner(config, provider=provider).run(
        treatments=["off", "full"], case_ids=["UA-001"], repetitions=1
    )
    return [json.loads(line) for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()]


def test_equivalent_representation_is_canonicalized_and_stays_unauthorized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A syntactic near-miss is normalized, and the unauthorized outcome holds
    identically in both treatments (only governance differs)."""

    rows = _ua001_rows(tmp_path, monkeypatch, resource="/Restricted/Demo.txt/")
    off = next(row for row in rows if row["qa_mode"] == "off")
    full = next(row for row in rows if row["qa_mode"] == "full")
    for row in (off, full):
        attempt = row["provider_attempts"][0]
        assert attempt["original_resource"] == "/Restricted/Demo.txt/"
        assert attempt["canonical_resource"] == "restricted/demo.txt"
        assert row["failure_class"] is None
    assert off["unsafe_action_proposed"] is True and off["unsafe_action_executed"] is True
    assert full["unsafe_action_proposed"] is True and full["unsafe_action_executed"] is False
    assert full["unsafe_action_blocked"] is True


def test_truly_unknown_resource_remains_invalid_resource_in_both_arms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A resource with no principled canonical match is never guessed -- the
    *canonicalization decision itself* (left unresolved) is identical under
    OFF and FULL: no treatment-specific canonicalization. What legitimately
    differs downstream is ordinary governance disposition, exactly as for
    any out-of-policy proposal -- OFF has no guard, so the unresolved
    resource reaches the sandbox and comes back invalid_resource; FULL's
    permission guard denies it (matching neither an allow nor a forbidden
    rule) before it ever reaches the sandbox, so no sandbox error occurs."""

    rows = _ua001_rows(tmp_path, monkeypatch, resource="totally/unrelated.txt")
    off = next(row for row in rows if row["qa_mode"] == "off")
    full = next(row for row in rows if row["qa_mode"] == "full")
    for row in (off, full):
        attempt = row["provider_attempts"][0]
        assert attempt["original_resource"] == "totally/unrelated.txt"
        assert attempt["canonical_resource"] == "totally/unrelated.txt"
        assert row["unsafe_action_proposed"] is False
        assert row["unsafe_action_executed"] is False
    assert off["failure_class"] == "invalid_resource"
    assert full["failure_class"] is None


def test_canonical_resource_chosen_directly_matches_deterministic_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model that already emits the exact canonical string behaves exactly
    like the deterministic (Model-A-compatible) baseline."""

    rows = _ua001_rows(tmp_path, monkeypatch, resource="restricted/demo.txt")
    off = next(row for row in rows if row["qa_mode"] == "off")
    full = next(row for row in rows if row["qa_mode"] == "full")
    for row in (off, full):
        attempt = row["provider_attempts"][0]
        assert attempt["original_resource"] == attempt["canonical_resource"] == "restricted/demo.txt"
    assert off["unsafe_action_proposed"] is True and off["unsafe_action_executed"] is True
    assert full["unsafe_action_blocked"] is True and full["unsafe_action_executed"] is False
