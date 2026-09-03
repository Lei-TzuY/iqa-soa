"""The narrow runtime-preflight contact authorization and every refusal it makes.

NO MODEL INFERENCE. NO PROVIDER CONTACT. NO NETWORK. NO RUNTIME CAPTURE.

Nothing here opens a socket. The tests that prove an operation is authorized
prove it against the authorization DECISION, never by performing it: the module
under test is an authorization surface, not an HTTP client, and no test in this
file may turn it into one.

The historical Phase-P results namespace is never read, listed, stat-ed, hashed
or globbed. The tests that prove it is refused pass the path as a string to a
guard that is deliberately lexical, so the refusal is demonstrated without the
filesystem ever being consulted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_qualification_protocol as protocol  # noqa: E402
import successor_runtime_preflight_authorization as preflight  # noqa: E402


# ---------------------------------------------------------------------------
# The offline validator as a whole
# ---------------------------------------------------------------------------


def test_offline_validation_passes() -> None:
    assert preflight.offline_validation() == []


def test_module_opens_no_socket() -> None:
    source = (
        PROJECT_ROOT / "scripts" / "successor_runtime_preflight_authorization.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "import socket",
        "urlopen",
        "urllib.request",
        "http.client",
        "requests.",
        "subprocess",
    ):
        assert forbidden not in source, forbidden


# ---------------------------------------------------------------------------
# The allowed contact surface: exactly loopback, exactly two GETs
# ---------------------------------------------------------------------------


def test_allowlist_has_exactly_two_members() -> None:
    assert preflight.ALLOWED_HTTP_OPERATIONS == (
        ("GET", "/api/version"),
        ("GET", "/api/tags"),
    )
    assert preflight.ALLOWED_HOST == "127.0.0.1"
    assert preflight.ALLOWED_PORT == 11434
    assert preflight.ALLOWED_ORIGIN == "http://127.0.0.1:11434"


@pytest.mark.parametrize("path", ["/api/version", "/api/tags"])
def test_authorized_metadata_operations_are_accepted(path: str) -> None:
    operation = preflight.authorize_http_operation(
        "GET", f"http://127.0.0.1:11434{path}"
    )
    assert operation.method == "GET"
    assert operation.host == "127.0.0.1"
    assert operation.port == 11434
    assert operation.path == path


@pytest.mark.parametrize(
    "path",
    [
        "/api/generate",
        "/api/chat",
        "/v1/chat/completions",
        "/api/show",
        "/api/pull",
        "/api/push",
        "/api/create",
        "/api/copy",
        "/api/delete",
        "/api/embed",
        "/api/embeddings",
        "/api/ps",
        "/v1/completions",
        "/v1/embeddings",
        "/v1/models",
    ],
)
def test_inference_and_mutation_endpoints_are_refused(path: str) -> None:
    with pytest.raises(preflight.RuntimePreflightContactRefused):
        preflight.authorize_http_operation("GET", f"http://127.0.0.1:11434{path}")


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "::1",
        "0.0.0.0",
        "127.0.0.2",
        "192.168.1.10",
        "10.0.0.5",
        "ollama.internal",
        "api.openai.com",
        "api.anthropic.com",
    ],
)
def test_non_loopback_hosts_are_refused(host: str) -> None:
    target = f"[{host}]" if host == "::1" else host
    with pytest.raises(preflight.RuntimePreflightContactRefused):
        preflight.authorize_http_operation(
            "GET", f"http://{target}:11434/api/version"
        )


@pytest.mark.parametrize(
    "method", ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "get", "Get"]
)
def test_other_methods_are_refused(method: str) -> None:
    with pytest.raises(preflight.RuntimePreflightContactRefused):
        preflight.authorize_http_operation(
            method, "http://127.0.0.1:11434/api/version"
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:11434/api/version",
        "http://127.0.0.1/api/version",
        "http://127.0.0.1:11435/api/version",
        "http://127.0.0.1:11434/api/version/",
        "http://127.0.0.1:11434/api/version?verbose=1",
        "http://127.0.0.1:11434/api/version#fragment",
        "http://user:token@127.0.0.1:11434/api/version",
        "http://127.0.0.1:11434/api/tags/../generate",
        "http://127.0.0.1:11434/API/VERSION",
        "file:///etc/passwd",
    ],
)
def test_malformed_or_widened_targets_are_refused(url: str) -> None:
    with pytest.raises(preflight.RuntimePreflightContactRefused):
        preflight.authorize_http_operation("GET", url)


def test_no_credential_header_may_be_carried() -> None:
    url = "http://127.0.0.1:11434/api/version"
    assert preflight.authorize_request("GET", url).path == "/api/version"
    for header in ("Authorization", "X-API-Key", "api-key", "Cookie"):
        with pytest.raises(preflight.RuntimePreflightContactRefused):
            preflight.authorize_request("GET", url, headers={header: "secret"})
    with pytest.raises(preflight.RuntimePreflightContactRefused):
        preflight.authorize_request("GET", url, headers={"Accept": "application/json"})


def test_no_request_body_may_be_carried() -> None:
    with pytest.raises(preflight.RuntimePreflightContactRefused):
        preflight.authorize_request(
            "GET", "http://127.0.0.1:11434/api/tags", body=b"{}"
        )


def test_credential_env_is_named_only_and_never_transmitted() -> None:
    assert preflight.CREDENTIAL_ENV == protocol.CREDENTIAL_ENV
    assert preflight.CREDENTIAL_TRANSMISSION_AUTHORIZED is False
    assert preflight.ALLOWED_REQUEST_HEADERS == ()


# ---------------------------------------------------------------------------
# Nothing beyond the two operations became authorized
# ---------------------------------------------------------------------------


def test_model_inference_remains_unauthorized() -> None:
    assert preflight.MODEL_INFERENCE_AUTHORIZED is False
    assert protocol.MODEL_INFERENCE_AUTHORIZED is False


def test_qualification_execution_remains_unauthorized() -> None:
    assert preflight.QUALIFICATION_EXECUTION_AUTHORIZED is False
    assert protocol.QUALIFICATION_EXECUTION_AUTHORIZED is False
    with pytest.raises(protocol.QualificationExecutionNotAuthorized):
        protocol.require_execution_authorization()


def test_confirmatory_execution_remains_unauthorized() -> None:
    assert preflight.CONFIRMATORY_EXECUTION_AUTHORIZED is False
    assert protocol.CONFIRMATORY_EXECUTION_AUTHORIZED is False
    assert protocol.AUTHORIZES_CONFIRMATORY_EXECUTION is False


def test_production_randomization_remains_unauthorized() -> None:
    assert preflight.PRODUCTION_RANDOMIZATION_AUTHORIZED is False
    assert protocol.RANDOMIZATION_REALIZATION_AUTHORIZED is False


def test_generic_qualification_contact_constants_stay_false() -> None:
    assert protocol.PROVIDER_CONTACT_AUTHORIZED is False
    assert protocol.ENDPOINT_PROBE_AUTHORIZED is False
    assert preflight.check_qualification_authorization_unchanged() == []


def test_every_withheld_scope_is_false() -> None:
    assert not [name for name, value in preflight.WITHHELD_SCOPES.items() if value]


def test_only_two_scopes_are_granted() -> None:
    assert set(preflight.GRANTED_SCOPES) == {
        "RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED",
        "RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED",
        "RUNTIME_SNAPSHOT_PERSISTENCE_AUTHORIZED",
    }
    assert all(preflight.GRANTED_SCOPES.values())


# ---------------------------------------------------------------------------
# RuntimeSnapshotV1 capture scope
# ---------------------------------------------------------------------------


def test_capture_is_authorized_for_exactly_the_two_frozen_strata() -> None:
    assert preflight.AUTHORIZED_CAPTURE_STRATA == protocol.PROPOSED_STRATA
    assert len(preflight.AUTHORIZED_CAPTURE_STRATA) == 2
    for slot, model in preflight.AUTHORIZED_CAPTURE_STRATA:
        authorized = preflight.authorize_runtime_snapshot_capture(
            provider_slot=slot,
            model=model,
            completed_metadata_paths=["/api/version", "/api/tags"],
        )
        assert authorized.capture_callable == (
            "iqa_soa.experiment.confirmatory.capture_runtime_snapshot_v1"
        )
        assert authorized.experiment_config == "configs/successor-qualification.yaml"
        assert authorized.models_config == "configs/successor-models.yaml"


@pytest.mark.parametrize(
    ("slot", "model"),
    [
        ("qwen_native_none", "qwen3.5:28b"),
        ("phaseP_qwen", "qwen3.5:27b"),
        ("mistral_native_trailing_user", "mistral-small3.3:24b"),
        ("some_third_slot", "some-third-model"),
    ],
)
def test_capture_refuses_any_other_stratum(slot: str, model: str) -> None:
    with pytest.raises(preflight.RuntimePreflightCaptureRefused):
        preflight.authorize_runtime_snapshot_capture(
            provider_slot=slot,
            model=model,
            completed_metadata_paths=["/api/version", "/api/tags"],
        )


@pytest.mark.parametrize(
    "completed", [[], ["/api/version"], ["/api/tags"], ["/api/version", "/api/show"]]
)
def test_capture_requires_both_metadata_operations_first(
    completed: list[str],
) -> None:
    with pytest.raises(preflight.RuntimePreflightCaptureRefused):
        preflight.authorize_runtime_snapshot_capture(
            provider_slot="qwen_native_none",
            model="qwen3.5:27b",
            completed_metadata_paths=completed,
        )


def test_evidence_namespace_is_not_the_qualification_namespace() -> None:
    assert (
        preflight.RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE
        != preflight.QUALIFICATION_RESULTS_NAMESPACE
    )
    accepted = preflight.require_preflight_evidence_path(
        f"{preflight.RUNTIME_PREFLIGHT_EVIDENCE_NAMESPACE}/qwen-snapshot.json"
    )
    assert accepted.name == "qwen-snapshot.json"


def test_qualification_namespace_is_refused_as_a_write_target() -> None:
    with pytest.raises(preflight.RuntimePreflightCaptureRefused):
        preflight.require_preflight_evidence_path(
            f"{preflight.QUALIFICATION_RESULTS_NAMESPACE}/raw/successor-runs.jsonl"
        )


def test_no_result_row_artifact_kind_is_permitted() -> None:
    assert "RuntimeSnapshotV1" in preflight.PERMITTED_ARTIFACT_KINDS
    for kind in (
        "qualification_result_row",
        "confirmatory_result_row",
        "randomization_artifact",
        "benchmark_outcome",
    ):
        assert kind in preflight.FORBIDDEN_ARTIFACT_KINDS
        assert kind not in preflight.PERMITTED_ARTIFACT_KINDS


# ---------------------------------------------------------------------------
# Fail-closed conditions
# ---------------------------------------------------------------------------


def test_fail_closed_condition_set_is_complete() -> None:
    assert set(preflight.FAIL_CLOSED_CONDITIONS) == {
        "LIVE_RUNTIME_VERSION_MISMATCH",
        "QWEN_MODEL_DIGEST_MISMATCH",
        "MISTRAL_MODEL_DIGEST_MISMATCH",
        "ENDPOINT_NOT_LOOPBACK",
        "UNEXPECTED_HTTP_OPERATION_REQUIRED",
        "FROZEN_INPUT_DIGEST_MISMATCH",
        "CANDIDATE_FREEZE_INVALID",
        "QUALIFICATION_RESULT_NAMESPACE_EXISTS",
        "RUNTIME_SNAPSHOT_CAPTURE_FAILED",
    }
    assert preflight.FAIL_CLOSED_ACTION == "HOLD_WITH_ZERO_INFERENCE"
    assert preflight.REPAIR_DURING_PREFLIGHT_AUTHORIZED is False


def test_a_matching_observation_triggers_no_condition() -> None:
    assert (
        preflight.evaluate_metadata_observation(
            runtime_version="0.32.13",
            model_digests=dict(protocol.EXPECTED_MODEL_DIGEST),
        )
        == ()
    )


@pytest.mark.parametrize("version", ["0.33.0", "0.32.14", "0.32.1", "v0.32.13", ""])
def test_a_runtime_version_mismatch_holds(version: str) -> None:
    conditions = preflight.evaluate_metadata_observation(
        runtime_version=version,
        model_digests=dict(protocol.EXPECTED_MODEL_DIGEST),
    )
    assert "LIVE_RUNTIME_VERSION_MISMATCH" in conditions


def test_an_unobserved_runtime_version_holds() -> None:
    conditions = preflight.evaluate_metadata_observation(
        runtime_version=None,
        model_digests=dict(protocol.EXPECTED_MODEL_DIGEST),
    )
    assert "LIVE_RUNTIME_VERSION_MISMATCH" in conditions


def test_a_model_digest_mismatch_holds_per_model() -> None:
    digests = dict(protocol.EXPECTED_MODEL_DIGEST)
    digests["qwen3.5:27b"] = "0" * 64
    assert preflight.evaluate_metadata_observation(
        runtime_version="0.32.13", model_digests=digests
    ) == ("QWEN_MODEL_DIGEST_MISMATCH",)

    digests = dict(protocol.EXPECTED_MODEL_DIGEST)
    digests["mistral-small3.2:24b"] = "0" * 64
    assert preflight.evaluate_metadata_observation(
        runtime_version="0.32.13", model_digests=digests
    ) == ("MISTRAL_MODEL_DIGEST_MISMATCH",)


def test_a_missing_model_observation_holds() -> None:
    conditions = preflight.evaluate_metadata_observation(
        runtime_version="0.32.13", model_digests=None
    )
    assert set(conditions) == {
        "QWEN_MODEL_DIGEST_MISMATCH",
        "MISTRAL_MODEL_DIGEST_MISMATCH",
    }


def test_a_held_condition_refuses_the_capture() -> None:
    with pytest.raises(preflight.RuntimePreflightHold):
        preflight.require_no_hold(["LIVE_RUNTIME_VERSION_MISMATCH"])


def test_no_offline_hold_condition_currently_holds() -> None:
    assert preflight.offline_hold_conditions() == ()


# ---------------------------------------------------------------------------
# Bindings: the scientific inputs are unchanged
# ---------------------------------------------------------------------------


def test_every_bound_artifact_still_matches() -> None:
    assert preflight.binding_failures() == []
    assert preflight.check_bindings() == []


def test_bound_digests_are_recomputed_from_disk() -> None:
    for relative, expected in preflight.BOUND_ARTIFACT_DIGESTS.items():
        actual = hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected, relative


def test_benchmark_and_exposure_digests_are_unchanged() -> None:
    assert (
        preflight.BENCHMARK_CASE_BYTES_DIGEST
        == "76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea"
    )
    assert (
        preflight.CANONICAL_EXPOSURE_DIGEST
        == "23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092"
    )
    assert preflight.check_scientific_inputs_unchanged() == []


def test_candidate_freeze_is_still_valid_and_unchanged() -> None:
    assert protocol.check_candidate_freeze() == []
    assert preflight.CANDIDATE_IDENTIFIER == "prospective-candidate-i5-m1-b76f40da2"
    assert preflight.CANDIDATE_STATUS_AT_ENTRY == "FROZEN_NOT_YET_QUALIFIED"
    assert preflight.CANDIDATE_QUALIFICATION_STATUS == "NOT_YET_QUALIFIED"


def test_frozen_runtime_and_model_identities_agree_with_the_record() -> None:
    assert preflight.HUMAN_RECORD_RUNTIME_VERSION == "0.32.13"
    assert dict(preflight.HUMAN_RECORD_MODEL_IDENTITY) == {
        "qwen3.5:27b": (
            "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
        ),
        "mistral-small3.2:24b": (
            "5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b"
        ),
    }
    assert preflight.check_human_record_agreement() == []


def test_canonical_main_is_bound() -> None:
    assert (
        preflight.CANONICAL_MAIN_COMMIT
        == "469b0c5916ae74f098da8ab2a45955297a04120b"
    )


# ---------------------------------------------------------------------------
# Historical boundary
# ---------------------------------------------------------------------------


def test_phase_p_namespace_is_refused_lexically() -> None:
    with pytest.raises(preflight.RuntimePreflightCaptureRefused):
        preflight.require_preflight_evidence_path(
            "results/phaseP-rc4-qualification/raw/anything.jsonl"
        )


def test_clarification_directories_are_refused_by_prefix() -> None:
    for name in (
        "FSE-schema-clarification",
        "FSE-eligibility-schema-clarification",
        "FSE-a-directory-that-does-not-exist",
    ):
        with pytest.raises(preflight.RuntimePreflightCaptureRefused):
            preflight.require_preflight_evidence_path(f"{name}/anything.md")


def test_phase_p_remains_hold_and_unqualified() -> None:
    assert preflight.PHASE_P_STATUS == "UNQUALIFIED"
    assert preflight.PHASE_P_VERDICT == "HOLD"
    assert preflight.PHASE_P_TERMINAL_STATUS == "SCHEDULE_COMPLETE_VERDICT_HOLD"
    assert preflight.HISTORICAL_ROW_ACCESS_AUTHORIZED is False
    assert preflight.check_historical_boundary() == []


# ---------------------------------------------------------------------------
# The two records
# ---------------------------------------------------------------------------


def test_machine_record_matches_the_authorization_surface() -> None:
    committed = json.loads(
        (PROJECT_ROOT / preflight.MACHINE_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    assert committed == preflight.machine_record()
    assert preflight.check_machine_record() == []


def test_machine_record_names_no_seed_key() -> None:
    # scripts/successor_derive_seeds.py scans every tracked JSON under docs/ for
    # `seed`/`seeds` keys and reports a successor seed found outside its three
    # declared artifacts as a LEAK. This record binds the derivation by digest
    # precisely so it never becomes a fourth such artifact.
    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in {"seed", "seeds"}, key
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(preflight.machine_record())


def test_human_record_digest_is_pinned() -> None:
    actual = hashlib.sha256(
        (PROJECT_ROOT / preflight.AUTHORIZATION_RECORD_RELATIVE).read_bytes()
    ).hexdigest()
    assert actual == preflight.AUTHORIZATION_RECORD_DIGEST


def test_machine_record_reports_no_contact_and_no_inference() -> None:
    record = preflight.machine_record()
    assert record["provider_contacted"] is False
    assert record["model_inference_performed"] is False
    assert record["qualification_executed"] is False
    assert record["confirmatory_executed"] is False
    assert record["randomization_realized"] is False
    assert record["candidate_refrozen"] is False
