"""The successor provider selection, configuration and runtime-identity pins.

NO MODEL INFERENCE. NO PROVIDER CONTACT. NO NETWORK. These tests read committed
bytes and compare them against the human decision recorded in
``docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md``.

The historical Phase-P results namespace is never read, listed, stat-ed, hashed
or globbed by anything here. Where a test needs a historical fact it takes it
from a committed CONFIGURATION or PROTOCOL record, never from a realized row.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import sys
from typing import Any

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import successor_qualification_protocol as protocol  # noqa: E402
from iqa_soa.experiment.runner import load_provider  # noqa: E402

#: The two strata the human decision named, spelled out here independently of
#: the protocol module so the test is a check and not an echo.
DECIDED_STRATA: dict[str, dict[str, Any]] = {
    "qwen_native_none": {
        "model": "qwen3.5:27b",
        "type": "openai_compatible",
        "protocol": "native_tools",
        "tool_contract_policy": "none",
        "temperature": 0.2,
        "top_p": 1.0,
        "max_output_tokens": 1024,
        "supports_seed": True,
        "timeout_seconds": 600,
    },
    "mistral_native_trailing_user": {
        "model": "mistral-small3.2:24b",
        "type": "openai_compatible",
        "protocol": "native_tools",
        "tool_contract_policy": "trailing_user",
        "temperature": 0.2,
        "top_p": 1.0,
        "max_output_tokens": 1024,
        "supports_seed": True,
        "timeout_seconds": 600,
    },
}

SUCCESSOR_CONFIG = PROJECT_ROOT / "configs" / "successor-models.yaml"

#: The successor ExperimentConfig, named here independently of the protocol
#: module so these tests check the binding rather than echo it.
SUCCESSOR_EXPERIMENT_CONFIG = PROJECT_ROOT / "configs" / "successor-qualification.yaml"


def _config() -> dict[str, Any]:
    loaded: Any = yaml.safe_load(SUCCESSOR_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _experiment_config() -> dict[str, Any]:
    loaded: Any = yaml.safe_load(
        SUCCESSOR_EXPERIMENT_CONFIG.read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


# ---------------------------------------------------------------------------
# The selection itself
# ---------------------------------------------------------------------------


def test_exactly_two_strata_are_selected() -> None:
    assert len(protocol.PROPOSED_STRATA) == 2
    assert len(_config()["providers"]) == 2


def test_selected_identities_match_the_human_decision_exactly() -> None:
    assert dict(protocol.PROPOSED_STRATA) == {
        slot: spec["model"] for slot, spec in DECIDED_STRATA.items()
    }


def test_no_third_provider_is_configured_or_bound() -> None:
    assert set(_config()["providers"]) == set(DECIDED_STRATA)
    assert set(protocol.EXPECTED_PROVIDER_SETTINGS) == set(DECIDED_STRATA)
    assert set(protocol.EXPECTED_MODEL.values()) == {
        spec["model"] for spec in DECIDED_STRATA.values()
    }


def test_configured_settings_are_the_decided_lineage_values() -> None:
    providers = _config()["providers"]
    for slot, spec in DECIDED_STRATA.items():
        entry = providers[slot]
        for key, expected in spec.items():
            assert entry[key] == expected, f"{slot}.{key}"
        assert entry["enabled"] is True
        assert entry["seed"] is None
        assert entry["endpoint"] == "http://127.0.0.1:11434/v1/chat/completions"


def test_neither_model_was_replaced_by_a_newer_one() -> None:
    models = {entry["model"] for entry in _config()["providers"].values()}
    assert models == {"qwen3.5:27b", "mistral-small3.2:24b"}


# ---------------------------------------------------------------------------
# Historical isolation of the configuration
# ---------------------------------------------------------------------------


def test_historical_phase_config_is_not_modified() -> None:
    """The Phase-P models config still hashes to its own frozen pin.

    The pin is read from ``docs/phaseP_frozen_execution_inputs.json`` -- a
    committed frozen-INPUT record, not a realized result row -- so this proves
    the historical configuration is byte-identical without touching any
    historical evidence.
    """

    record = json.loads(
        (PROJECT_ROOT / "docs" / "phaseP_frozen_execution_inputs.json").read_text(
            encoding="utf-8"
        )
    )
    relative = "configs/phaseP-models.yaml"
    expected = record["files"][relative]
    actual = hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
    assert actual == expected


def test_successor_config_does_not_reuse_a_historical_credential_variable() -> None:
    names = {entry["api_key_env"] for entry in _config()["providers"].values()}
    assert names == {"SUCCESSOR_OLLAMA_API_KEY"}
    assert not names & set(protocol.FORBIDDEN_CREDENTIAL_ENVS)


def test_successor_config_is_not_a_historical_phase_config() -> None:
    assert protocol.CANONICAL_MODELS_RELATIVE == "configs/successor-models.yaml"
    assert protocol.CANONICAL_MODELS_RELATIVE not in protocol.FORBIDDEN_RUNTIME_CONFIGS
    for forbidden in protocol.FORBIDDEN_RUNTIME_CONFIGS:
        assert forbidden not in protocol.CANONICAL_SCIENTIFIC_INPUTS


# ---------------------------------------------------------------------------
# The config authorizes no contact
# ---------------------------------------------------------------------------


def test_loading_the_config_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Parsing the config and building both providers contacts nothing.

    Every socket entry point is replaced with a raiser, so a contact attempt
    fails the test loudly instead of silently succeeding on a host that happens
    to have a runtime listening.
    """

    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the successor provider config opened a network socket")

    monkeypatch.setattr(socket, "socket", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)

    assert protocol.check_provider_config() == []
    for slot in DECIDED_STRATA:
        provider = load_provider(SUCCESSOR_CONFIG, provider_name=slot)
        assert provider.model == DECIDED_STRATA[slot]["model"]


def test_credential_value_is_never_read_by_the_config_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The credential is checked by name only; its value is never resolved."""

    monkeypatch.delenv("SUCCESSOR_OLLAMA_API_KEY", raising=False)
    assert protocol.check_provider_config() == []
    provider = load_provider(SUCCESSOR_CONFIG, provider_name="qwen_native_none")
    assert provider.descriptor()["api_key_env"] == "SUCCESSOR_OLLAMA_API_KEY"
    assert "api_key" not in provider.descriptor()


# ---------------------------------------------------------------------------
# Prospective runtime identity pins
# ---------------------------------------------------------------------------


def test_model_digest_pins_are_traceable_to_committed_non_outcome_history() -> None:
    """Every pin appears verbatim in each cited non-outcome lineage record."""

    for relative in protocol.MODEL_DIGEST_PROVENANCE:
        text = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        for digest in protocol.EXPECTED_MODEL_DIGEST.values():
            assert digest in text, f"{digest} absent from {relative}"


def test_model_digest_provenance_names_no_results_namespace() -> None:
    for relative in protocol.MODEL_DIGEST_PROVENANCE:
        assert not relative.startswith("results/")


def test_runtime_mismatch_produces_environment_hold() -> None:
    with pytest.raises(protocol.EnvironmentHold):
        protocol.verify_model_identity("qwen3.5:27b", "0" * 64)
    with pytest.raises(protocol.EnvironmentHold):
        protocol.verify_runtime_identity(
            arm="qwen",
            observed={
                "model": "qwen3.5:27b",
                "model_digest": "1" * 64,
                "runtime_version": protocol.EXPECTED_RUNTIME_VERSION,
                "tool_contract_policy": "none",
                "protocol": "native_tools",
            },
        )


def test_missing_runtime_observation_is_also_an_environment_hold() -> None:
    """An unobserved fact must never read as a matching one."""

    with pytest.raises(protocol.EnvironmentHold) as excinfo:
        protocol.verify_runtime_identity(arm="mistral", observed={})
    assert "omits" in str(excinfo.value)


def test_matching_runtime_observation_is_accepted_without_contact() -> None:
    protocol.verify_runtime_identity(
        arm="mistral",
        observed={
            "model": "mistral-small3.2:24b",
            "model_digest": protocol.EXPECTED_MODEL_DIGEST["mistral-small3.2:24b"],
            "runtime_version": protocol.EXPECTED_RUNTIME_VERSION,
            "tool_contract_policy": "trailing_user",
            "protocol": "native_tools",
        },
    )


def test_environment_hold_is_never_a_repair_instruction() -> None:
    with pytest.raises(protocol.EnvironmentHold) as excinfo:
        protocol.verify_model_identity("mistral-small3.2:24b", "2" * 64)
    message = str(excinfo.value)
    assert "never pulls, updates, retags or replaces a model" in message


# ---------------------------------------------------------------------------
# The runtime version pin, and every way it could be softened
# ---------------------------------------------------------------------------


def test_expected_runtime_version_is_the_frozen_pin_and_was_not_repinned() -> None:
    assert protocol.EXPECTED_RUNTIME_VERSION == "0.32.13"
    assert protocol.ACCEPTED_RUNTIME_VERSIONS == ("0.32.13",)
    assert protocol.RUNTIME_REPIN_AUTHORIZED is False
    assert protocol.RUNTIME_VERSION_RESOLUTION == "RESTORE_FROZEN_RUNTIME"
    assert protocol.RUNTIME_RESTORE_REQUIRED is True
    assert protocol.check_runtime_version_policy() == []


def test_runtime_0_33_0_is_an_environment_hold_and_is_never_accepted() -> None:
    """The version the environment reported must fail closed, for both arms."""

    assert protocol.ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION == "0.33.0"
    assert (
        protocol.ENVIRONMENT_HOLD_OBSERVED_RUNTIME_VERSION
        not in protocol.ACCEPTED_RUNTIME_VERSIONS
    )
    for arm, model, policy in (
        ("qwen", "qwen3.5:27b", "none"),
        ("mistral", "mistral-small3.2:24b", "trailing_user"),
    ):
        with pytest.raises(protocol.EnvironmentHold) as excinfo:
            protocol.verify_runtime_identity(
                arm=arm,
                observed={
                    "model": model,
                    "model_digest": protocol.EXPECTED_MODEL_DIGEST[model],
                    "runtime_version": "0.33.0",
                    "tool_contract_policy": policy,
                    "protocol": "native_tools",
                },
            )
        message = str(excinfo.value)
        assert "ENVIRONMENT_HOLD" in message
        assert "0.32.13" in message
        assert "RESTORE_FROZEN_RUNTIME" in message


def test_runtime_0_32_13_passes_the_version_predicate() -> None:
    """The frozen runtime is the one version that satisfies the predicate."""

    for arm, model, policy in (
        ("qwen", "qwen3.5:27b", "none"),
        ("mistral", "mistral-small3.2:24b", "trailing_user"),
    ):
        protocol.verify_runtime_identity(
            arm=arm,
            observed={
                "model": model,
                "model_digest": protocol.EXPECTED_MODEL_DIGEST[model],
                "runtime_version": "0.32.13",
                "tool_contract_policy": policy,
                "protocol": "native_tools",
            },
        )


def test_the_version_comparison_cannot_be_bypassed() -> None:
    """Neither a near-miss string nor a coercible look-alike may pass.

    The subclass and the always-equal object are the two shapes a bypass
    actually takes in practice: a value that compares equal without being the
    frozen string, and a value some other layer would have coerced.
    """

    class AlwaysEqual:
        def __eq__(self, other: object) -> bool:
            return True

        def __ne__(self, other: object) -> bool:
            return False

        def __hash__(self) -> int:
            return hash("0.32.13")

        def __str__(self) -> str:
            return "0.32.13"

    class VersionLike(str):
        pass

    bypasses: list[object] = [
        "0.32.13 ",
        " 0.32.13",
        "v0.32.13",
        "0.32.13.0",
        "0.32.1",
        "0.32",
        "0.32.130",
        "0.33.0",
        AlwaysEqual(),
        VersionLike("0.32.13"),
        ["0.32.13"],
        ("0.32.13",),
        {"version": "0.32.13"},
    ]
    for candidate in bypasses:
        with pytest.raises(protocol.EnvironmentHold):
            protocol.verify_runtime_identity(
                arm="qwen",
                observed={
                    "model": "qwen3.5:27b",
                    "model_digest": protocol.EXPECTED_MODEL_DIGEST["qwen3.5:27b"],
                    "runtime_version": candidate,
                    "tool_contract_policy": "none",
                    "protocol": "native_tools",
                },
            )
    assert protocol.RUNTIME_VERSION_COMPARISON == "EXACT_STRING_EQUALITY"


def test_an_environment_hold_authorizes_no_remedy() -> None:
    """No downgrade, no update, no repin, no pull, no replace, no retag."""

    assert protocol.RUNTIME_HOLD_REMEDIES_REFUSED == {
        "automatic_downgrade_permitted": False,
        "runtime_update_permitted": False,
        "protocol_repin_permitted": False,
        "model_pull_permitted": False,
        "model_replacement_permitted": False,
        "model_retag_permitted": False,
        "version_equivalence_exception_permitted": False,
    }
    assert protocol.RUNTIME_VERSION_EQUIVALENCE_EXCEPTION_PERMITTED is False


def test_model_digests_are_exactly_the_two_frozen_values() -> None:
    assert protocol.EXPECTED_MODEL_DIGEST == {
        "qwen3.5:27b": (
            "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
        ),
        "mistral-small3.2:24b": (
            "5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b"
        ),
    }


def test_a_model_digest_mismatch_is_a_hold_for_either_model() -> None:
    for model in protocol.EXPECTED_MODEL_DIGEST:
        with pytest.raises(protocol.EnvironmentHold) as excinfo:
            protocol.verify_model_identity(model, "f" * 64)
        assert "ENVIRONMENT_HOLD" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The successor ExperimentConfig
# ---------------------------------------------------------------------------


def test_the_successor_experiment_config_exists_and_is_bound() -> None:
    assert SUCCESSOR_EXPERIMENT_CONFIG.is_file()
    assert (
        protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
        == "configs/successor-qualification.yaml"
    )
    assert (
        protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
        in protocol.CANONICAL_SCIENTIFIC_INPUTS
    )
    assert protocol.check_experiment_config() == []


def test_a_missing_experiment_config_fails_the_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Point the protocol at a tree without the config; it must fail, not skip.

    ``PROJECT_ROOT`` is redirected rather than the real file being deleted, so
    the proof costs nothing and touches no committed byte.
    """

    monkeypatch.setattr(protocol, "PROJECT_ROOT", tmp_path)
    failures = protocol.check_experiment_config()
    assert failures
    assert any("is absent" in item for item in failures)
    assert SUCCESSOR_EXPERIMENT_CONFIG.is_file()


def test_the_experiment_config_points_at_the_successor_models_config() -> None:
    config = _experiment_config()
    assert config["models_path"] == "configs/successor-models.yaml"
    assert config["models_path"] not in protocol.FORBIDDEN_RUNTIME_CONFIGS
    assert protocol.EXPECTED_EXPERIMENT_CONFIG["models_path"] == config["models_path"]


def test_the_successor_config_owns_the_provider_configuration() -> None:
    """The provider settings live in the successor config and nowhere else.

    The ExperimentConfig names a models file; it does not restate provider
    fields.  That is what "owns" means here -- there is exactly one place a
    provider slot can be changed.
    """

    experiment = _experiment_config()
    provider_fields = {
        "endpoint",
        "model",
        "api_key_env",
        "temperature",
        "top_p",
        "max_output_tokens",
        "protocol",
        "tool_contract_policy",
        "timeout_seconds",
    }
    assert not provider_fields & set(experiment)
    providers = _config()["providers"]
    assert set(providers) == set(DECIDED_STRATA)
    for slot in DECIDED_STRATA:
        assert provider_fields <= set(providers[slot])


def test_the_experiment_config_uses_the_existing_schema_and_key_set() -> None:
    from iqa_soa.experiment.runner import _CONFIG_KEYS

    config = _experiment_config()
    assert set(config) == set(_CONFIG_KEYS)
    assert config["schema_version"] == 1


def test_the_experiment_config_loader_now_accepts_the_successor_config() -> None:
    """The loader accepts it, and the loaded object is the successor's own.

    The barrier to a successor execution must be the withheld authorization, not
    a configuration that cannot load. This proves the second barrier is gone
    while the first is intact.
    """

    from iqa_soa.experiment.runner import load_experiment_config

    loaded = load_experiment_config(SUCCESSOR_EXPERIMENT_CONFIG)
    assert loaded.schema_version == 1
    assert list(loaded.seeds) == [583010984, 1723431918, 1639806953]
    assert loaded.repetitions == 3
    assert list(loaded.treatments) == ["off"]
    assert loaded.shuffle_treatments is False
    assert loaded.models_path == (
        PROJECT_ROOT / "configs/successor-models.yaml"
    ).resolve()
    assert loaded.output_root == (
        PROJECT_ROOT / "results/prospective-candidate-i5-m1-b76f40da2-qualification/raw"
    ).resolve()
    assert loaded.raw_jsonl == "successor-runs.jsonl"
    assert loaded.raw_csv == "successor-runs.csv"
    assert (
        protocol.EXPERIMENT_CONFIG_EXECUTABILITY["loadable_by_existing_loader_today"]
        is True
    )
    assert protocol.EXPERIMENT_CONFIG_EXECUTABILITY["fabricated_seed_written"] is False
    assert (
        protocol.EXPERIMENT_CONFIG_EXECUTABILITY["loader_validation_weakened"] is False
    )


def test_the_config_has_three_seeds_and_repetitions_three() -> None:
    config = _experiment_config()
    assert config["repetitions"] == 3
    assert len(config["seeds"]) == 3
    assert len(set(config["seeds"])) == 3
    assert config["seeds"] == list(protocol.SEEDS)
    assert all(isinstance(seed, int) and seed > 0 for seed in config["seeds"])


def test_the_config_still_realizes_no_randomization() -> None:
    config = _experiment_config()
    assert config["shuffle_treatments"] is False
    assert config["treatments"] == ["off"]
    for treatment in config["treatments"]:
        assert treatment not in protocol.OUT_OF_SCOPE_TREATMENTS
    assert protocol.RANDOMIZATION_REALIZATION_AUTHORIZED is False


def test_no_phase_p_seed_value_is_reused_by_the_config() -> None:
    """The config carries no seed any historical execution consumed."""

    import successor_derive_seeds as derivation

    config = _experiment_config()
    consumed = set(derivation.PHASE_P_SEEDS) | set(derivation.PHASE_L_SEEDS)
    assert not set(config["seeds"]) & consumed
    assert not set(config["seeds"]) & set(derivation.RESERVED_SEEDS)


def test_the_experiment_config_fixes_zero_retries() -> None:
    """Zero retries is a protocol invariant, and the config adds no retry field."""

    assert protocol.INFRASTRUCTURE_RETRY_LIMIT == 0
    assert all(value is False for value in protocol.NO_RETRY_POLICY.values())
    assert "infrastructure_retry_limit" not in _experiment_config()
    assert not {"retries", "retry", "max_attempts"} & set(_experiment_config())


def test_the_experiment_config_binds_the_frozen_instrument_generation() -> None:
    """The pins live in the protocol, and the config is digest-bound to it."""

    assert protocol.EXPECTED_INSTRUMENT_VERSION == "5"
    assert protocol.EXPECTED_RAW_SCHEMA_VERSION == 6
    assert protocol.EXPECTED_NATIVE_TOOL_ADAPTER_VERSION == "native-tools-adapter-3"
    assert protocol.EXPECTED_TOOL_ARGUMENT_CONTRACT_VERSION == "tool-arguments-1"
    record = protocol.load_frozen_inputs()
    assert record is not None
    assert record["experiment_config"] == (
        protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    )
    assert record["instrument_version"] == "5"
    assert record["raw_schema_version"] == 6
    assert record["native_tool_adapter_version"] == "native-tools-adapter-3"
    assert record["tool_argument_contract_version"] == "tool-arguments-1"
    assert record["infrastructure_retry_limit"] == 0


def test_the_experiment_config_names_the_candidate_specific_namespace() -> None:
    config = _experiment_config()
    assert config["output_root"] == (
        "results/prospective-candidate-i5-m1-b76f40da2-qualification/raw"
    )
    assert protocol.CANDIDATE_IDENTIFIER in config["output_root"]
    assert config["output_root"].startswith(protocol.RESULTS_NAMESPACE + "/")


def test_the_qualification_namespace_cannot_equal_a_phase_namespace() -> None:
    config = _experiment_config()
    for forbidden in protocol.FORBIDDEN_RESULTS_NAMESPACES:
        assert config["output_root"] != forbidden
        assert not config["output_root"].startswith(forbidden + "/")
        with pytest.raises(protocol.NoncanonicalInput):
            protocol.require_canonical_results_root(f"{forbidden}/raw")
    assert protocol.RESULTS_NAMESPACE not in protocol.FORBIDDEN_RESULTS_NAMESPACES


def test_no_phase_config_can_satisfy_the_successor_runtime() -> None:
    """A phase config is refused as either successor scientific input."""

    for forbidden in protocol.FORBIDDEN_RUNTIME_CONFIGS:
        assert forbidden not in protocol.CANONICAL_SCIENTIFIC_INPUTS
        with pytest.raises(protocol.NoncanonicalInput):
            protocol.require_canonical_input(forbidden)
        for canonical in (
            protocol.CANONICAL_MODELS_RELATIVE,
            protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE,
        ):
            with pytest.raises(protocol.NoncanonicalInput):
                protocol.require_canonical_input(canonical, PROJECT_ROOT / forbidden)


def test_no_historical_credential_env_can_satisfy_the_successor_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setting every historical credential satisfies no successor precondition."""

    for name in protocol.FORBIDDEN_CREDENTIAL_ENVS:
        monkeypatch.setenv(name, "not-a-real-key")
    monkeypatch.delenv(protocol.CREDENTIAL_ENV, raising=False)

    assert protocol.CREDENTIAL_ENV == "SUCCESSOR_OLLAMA_API_KEY"
    assert protocol.CREDENTIAL_ENV not in protocol.FORBIDDEN_CREDENTIAL_ENVS
    names = {entry["api_key_env"] for entry in _config()["providers"].values()}
    assert names == {protocol.CREDENTIAL_ENV}
    with pytest.raises(protocol.QualificationExecutionNotAuthorized):
        protocol.require_execution_authorization()


def test_the_experiment_config_is_byte_identical_to_the_frozen_digest() -> None:
    relative = protocol.CANONICAL_EXPERIMENT_CONFIG_RELATIVE
    accepted = protocol.accepted_frozen_digest(relative)
    actual = hashlib.sha256(
        (PROJECT_ROOT / relative).read_bytes()
    ).hexdigest()
    assert actual == accepted
