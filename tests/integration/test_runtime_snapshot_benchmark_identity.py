"""RuntimeSnapshotV1 benchmark-identity capture over a real DIRECTORY root.

``ExperimentConfig.benchmark_path`` is a benchmark SOURCE ROOT and every
production configuration points it at a directory.  The frozen capture contract
originally derived ``benchmark_sha256`` with a file-only digest, which could not
be computed at all against that shape, so the first real runtime preflight
refused.  These tests cover the production directory-valued shape the previous
synthetic file-valued fixtures never exercised, and pin the corrected
derivation.

Nothing here contacts a provider, runs inference, or executes a qualification or
confirmatory cell.  ``DeterministicStubProvider`` is a repository-owned
no-network provider.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import pytest

from iqa_soa.agent import DeterministicStubProvider
from iqa_soa.experiment import confirmatory
from iqa_soa.experiment.confirmatory import (
    ConfirmatoryExecutionError,
    capture_runtime_snapshot_v1,
)
from iqa_soa.experiment.confirmatory_registration import (
    RuntimeSnapshotV1,
    canonical_json_bytes,
)
from iqa_soa.experiment.runner import (
    BENCHMARK_SOURCE_SUFFIXES,
    ExperimentConfig,
    benchmark_source_sha256,
    load_experiment_config,
)

POLICY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<qa-policy version="1">
  <rules/>
</qa-policy>
"""

CASE_ALPHA = """\
schema_version: 1
id: SYN-ALPHA
category: benign
user_prompt: Read alpha.txt and return its contents.
system_prompt: Use only the registered synthetic tool.
"""

CASE_BETA = """\
schema_version: 1
id: SYN-BETA
category: benign
user_prompt: Read beta.txt and return its contents.
system_prompt: Use only the registered synthetic tool.
"""

CASE_GAMMA = """\
schema_version: 1
id: SYN-GAMMA
category: budget
user_prompt: Read gamma.txt and return its contents.
system_prompt: Use only the registered synthetic tool.
"""

MANIFEST_JSON = '{\n  "benchmark_version": "synthetic-v1"\n}\n'
AUDIT_MD = "# Synthetic audit\n\nNo scientific content.\n"


def _write_benchmark_tree(root: Path) -> Path:
    """A directory-valued benchmark root with nested category directories."""

    benchmark = root / "benchmark"
    (benchmark / "benign").mkdir(parents=True)
    (benchmark / "budget").mkdir(parents=True)
    (benchmark / "frozen").mkdir(parents=True)
    (benchmark / "benign" / "SYN-ALPHA.yaml").write_text(CASE_ALPHA, encoding="utf-8")
    (benchmark / "benign" / "SYN-BETA.yaml").write_text(CASE_BETA, encoding="utf-8")
    (benchmark / "budget" / "SYN-GAMMA.yaml").write_text(CASE_GAMMA, encoding="utf-8")
    (benchmark / "frozen" / "manifest.json").write_text(
        MANIFEST_JSON, encoding="utf-8"
    )
    (benchmark / "frozen" / "AUDIT.md").write_text(AUDIT_MD, encoding="utf-8")
    return benchmark


def _write_config(root: Path, benchmark_path: Path) -> tuple[Path, ExperimentConfig]:
    """An ExperimentConfig whose benchmark_path is whatever shape is passed."""

    root.mkdir(parents=True, exist_ok=True)
    policy_path = root / "policy.xml"
    models_path = root / "models.yaml"
    ablations_path = root / "ablations.yaml"
    policy_path.write_text(POLICY_XML, encoding="utf-8")
    models_path.write_text("schema_version: 1\nproviders: {}\n", encoding="utf-8")
    ablations_path.write_text("schema_version: 1\ntreatments: []\n", encoding="utf-8")
    config_path = root / "experiment.yaml"
    config_path.write_text(
        "\n".join(
            (
                "schema_version: 1",
                f"benchmark_path: {benchmark_path.as_posix()}",
                f"policy_path: {policy_path.as_posix()}",
                f"models_path: {models_path.as_posix()}",
                f"ablations_path: {ablations_path.as_posix()}",
                f"output_root: {(root / 'legacy-output').as_posix()}",
                "repetitions: 2",
                "seeds: [999]",
                "max_agent_steps: 2",
                "shuffle_treatments: true",
                'treatments: ["off", "full"]',
                "smoke_case_ids: [SYN-ALPHA]",
                "raw_jsonl: runs.jsonl",
                "raw_csv: runs.csv",
                "evidence_subdir: evidence",
                "",
            )
        ),
        encoding="utf-8",
    )
    return config_path, load_experiment_config(config_path)


def _directory_config(root: Path) -> tuple[Path, ExperimentConfig, Path]:
    benchmark = _write_benchmark_tree(root)
    config_path, config = _write_config(root / "cfg", benchmark)
    return config_path, config, benchmark


def _capture(config: ExperimentConfig) -> RuntimeSnapshotV1:
    return capture_runtime_snapshot_v1(
        config=config, provider=DeterministicStubProvider()
    )


def _config_preimages(
    config: ExperimentConfig, monkeypatch: pytest.MonkeyPatch
) -> Mapping[str, Any]:
    """The exact ExperimentExecutionConfigIdentityV1 preimage capture builds."""

    captured: list[dict[str, Any]] = []
    real_digest = confirmatory._canonical_digest

    def recording_digest(payload: Any) -> str:
        if isinstance(payload, Mapping):
            captured.append(dict(payload))
        return real_digest(payload)

    monkeypatch.setattr(confirmatory, "_canonical_digest", recording_digest)
    _capture(config)
    monkeypatch.setattr(confirmatory, "_canonical_digest", real_digest)
    return next(
        payload
        for payload in captured
        if payload.get("schema_version") == "ExperimentExecutionConfigIdentityV1"
    )


# --------------------------------------------------------------------------
# 1. The production directory-valued shape captures at all
# --------------------------------------------------------------------------


def test_production_capture_succeeds_with_directory_valued_benchmark_path(
    tmp_path: Path,
) -> None:
    _, config, benchmark = _directory_config(tmp_path)
    assert benchmark.is_dir() and not benchmark.is_file()
    assert config.benchmark_path == benchmark.resolve()

    snapshot = _capture(config)

    assert isinstance(snapshot, RuntimeSnapshotV1)
    assert len(snapshot.to_dict()) == 20
    assert set(snapshot.to_dict()) == confirmatory._RUNTIME_SNAPSHOT_KEYS


def test_file_only_digest_cannot_serve_a_directory_benchmark_root(
    tmp_path: Path,
) -> None:
    """The defect this correction repairs, pinned so it cannot silently return."""

    _, _, benchmark = _directory_config(tmp_path)
    with pytest.raises(OSError):
        benchmark.read_bytes()


# --------------------------------------------------------------------------
# 2/3. Deterministic, and independent of filesystem enumeration order
# --------------------------------------------------------------------------


def test_benchmark_digest_is_deterministic_across_repeated_captures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, config, benchmark = _directory_config(tmp_path)
    first = _config_preimages(config, monkeypatch)["benchmark_sha256"]
    second = _config_preimages(config, monkeypatch)["benchmark_sha256"]

    assert first == second
    assert first == benchmark_source_sha256(benchmark)


def test_benchmark_digest_ignores_filesystem_enumeration_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two trees with identical content but opposite creation order agree."""

    forward = tmp_path / "forward" / "benchmark"
    reverse = tmp_path / "reverse" / "benchmark"
    payload = (
        ("benign/SYN-ALPHA.yaml", CASE_ALPHA),
        ("benign/SYN-BETA.yaml", CASE_BETA),
        ("budget/SYN-GAMMA.yaml", CASE_GAMMA),
        ("frozen/manifest.json", MANIFEST_JSON),
        ("frozen/AUDIT.md", AUDIT_MD),
    )
    for root, ordering in ((forward, payload), (reverse, tuple(reversed(payload)))):
        for relative, content in ordering:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    assert benchmark_source_sha256(forward) == benchmark_source_sha256(reverse)

    _, forward_config = _write_config(tmp_path / "cfg-forward", forward)
    _, reverse_config = _write_config(tmp_path / "cfg-reverse", reverse)
    assert (
        _config_preimages(forward_config, monkeypatch)["benchmark_sha256"]
        == _config_preimages(reverse_config, monkeypatch)["benchmark_sha256"]
    )


def test_benchmark_digest_binds_relative_path_not_just_content(
    tmp_path: Path,
) -> None:
    """A pure rename is as detectable as an edit: the tree is not a bag of bytes."""

    original = _write_benchmark_tree(tmp_path / "original")
    renamed = _write_benchmark_tree(tmp_path / "renamed")
    (renamed / "benign" / "SYN-ALPHA.yaml").rename(
        renamed / "benign" / "SYN-DELTA.yaml"
    )

    assert benchmark_source_sha256(original) != benchmark_source_sha256(renamed)


# --------------------------------------------------------------------------
# 4. One changed bound benchmark byte changes benchmark_sha256
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "benign/SYN-ALPHA.yaml",
        "benign/SYN-BETA.yaml",
        "budget/SYN-GAMMA.yaml",
        "frozen/manifest.json",
        "frozen/AUDIT.md",
    ],
)
def test_single_bound_benchmark_byte_change_moves_the_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    _, config, benchmark = _directory_config(tmp_path)
    before = _config_preimages(config, monkeypatch)
    first = _capture(config)

    target = benchmark / relative
    target.write_bytes(target.read_bytes() + b"# one byte\n")

    after = _config_preimages(config, monkeypatch)
    changed = _capture(config)

    assert after["benchmark_sha256"] != before["benchmark_sha256"]
    assert changed.experiment_config_digest != first.experiment_config_digest
    assert changed.runtime_identity_digest != first.runtime_identity_digest


def test_added_and_removed_benchmark_case_move_the_digest(tmp_path: Path) -> None:
    _, _, benchmark = _directory_config(tmp_path)
    baseline = benchmark_source_sha256(benchmark)

    added = benchmark / "benign" / "SYN-EPSILON.yaml"
    added.write_text(CASE_ALPHA, encoding="utf-8")
    assert benchmark_source_sha256(benchmark) != baseline

    added.unlink()
    assert benchmark_source_sha256(benchmark) == baseline

    (benchmark / "budget" / "SYN-GAMMA.yaml").unlink()
    assert benchmark_source_sha256(benchmark) != baseline


# --------------------------------------------------------------------------
# 5. The frozen source-set rule: unrelated files are outside the identity
# --------------------------------------------------------------------------


def test_frozen_source_set_rule_is_exactly_the_three_scientific_suffixes() -> None:
    assert BENCHMARK_SOURCE_SUFFIXES == frozenset({".json", ".md", ".yaml"})


@pytest.mark.parametrize(
    "relative",
    [
        "notes.txt",
        "benign/.DS_Store",
        "__pycache__/scratch.pyc",
        "budget/scratch.yaml.bak",
        "frozen/manifest.json.orig",
    ],
)
def test_unrelated_untracked_file_does_not_alter_the_scientific_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    """Files outside the frozen source set are not part of benchmark identity."""

    _, config, benchmark = _directory_config(tmp_path)
    before = _config_preimages(config, monkeypatch)["benchmark_sha256"]

    stray = benchmark / relative
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"not a scientific benchmark byte\n")

    after = _config_preimages(config, monkeypatch)["benchmark_sha256"]
    assert after == before


def test_source_set_rule_is_declared_not_silent(tmp_path: Path) -> None:
    """A file INSIDE the frozen source set still counts, so the rule is a rule."""

    _, _, benchmark = _directory_config(tmp_path)
    baseline = benchmark_source_sha256(benchmark)
    (benchmark / "benign" / "extra.yaml").write_text("schema_version: 1\n", "utf-8")
    assert benchmark_source_sha256(benchmark) != baseline


# --------------------------------------------------------------------------
# 6/7. Fail closed on missing, empty and malformed benchmark source
# --------------------------------------------------------------------------


def test_missing_benchmark_source_fails_closed(tmp_path: Path) -> None:
    _, config, benchmark = _directory_config(tmp_path)
    for item in sorted(benchmark.rglob("*"), reverse=True):
        item.unlink() if item.is_file() else item.rmdir()
    benchmark.rmdir()
    assert not benchmark.exists()

    with pytest.raises(ConfirmatoryExecutionError, match="benchmark source"):
        _capture(config)


def test_empty_benchmark_directory_fails_closed(tmp_path: Path) -> None:
    _, config, benchmark = _directory_config(tmp_path)
    for item in sorted(benchmark.rglob("*"), reverse=True):
        item.unlink() if item.is_file() else item.rmdir()
    assert benchmark.is_dir() and not any(benchmark.rglob("*"))

    with pytest.raises(ConfirmatoryExecutionError, match="benchmark source"):
        _capture(config)


def test_benchmark_root_holding_no_scientific_source_fails_closed(
    tmp_path: Path,
) -> None:
    """A root of only out-of-set files is malformed, not silently digestible."""

    _, config, benchmark = _directory_config(tmp_path)
    for item in benchmark.rglob("*"):
        if item.is_file():
            item.unlink()
    (benchmark / "notes.txt").write_bytes(b"only unrelated content\n")

    with pytest.raises(ConfirmatoryExecutionError, match="benchmark source"):
        _capture(config)


def test_unreadable_benchmark_case_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An OSError mid-tree refuses; it never degrades to a partial digest."""

    _, config, _ = _directory_config(tmp_path)
    real_read_bytes = Path.read_bytes

    def failing_read_bytes(self: Path) -> bytes:
        if self.suffix == ".yaml" and self.name.startswith("SYN-"):
            raise OSError("synthetic unreadable benchmark case")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", failing_read_bytes)
    with pytest.raises(ConfirmatoryExecutionError, match="benchmark source"):
        _capture(config)


# --------------------------------------------------------------------------
# 8. The pre-existing file-valued synthetic fixture stays defined
# --------------------------------------------------------------------------


def test_file_valued_benchmark_path_remains_defined_and_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "file-shaped"
    root.mkdir()
    benchmark_file = root / "synthetic-cases.yaml"
    benchmark_file.write_text(CASE_ALPHA, encoding="utf-8")
    _, config = _write_config(root / "cfg", benchmark_file)

    assert config.benchmark_path.is_file()
    first = _config_preimages(config, monkeypatch)["benchmark_sha256"]
    assert first == _config_preimages(config, monkeypatch)["benchmark_sha256"]
    assert first == benchmark_source_sha256(benchmark_file)

    benchmark_file.write_bytes(benchmark_file.read_bytes() + b"# edit\n")
    assert _config_preimages(config, monkeypatch)["benchmark_sha256"] != first


def test_file_valued_benchmark_path_ignores_the_suffix_restriction(
    tmp_path: Path,
) -> None:
    """An explicitly named file is the benchmark source whatever it is called."""

    root = tmp_path / "odd-suffix"
    root.mkdir()
    benchmark_file = root / "synthetic-cases.benchmark"
    benchmark_file.write_text(CASE_ALPHA, encoding="utf-8")
    _, config = _write_config(root / "cfg", benchmark_file)

    assert _capture(config).experiment_config_digest


def test_missing_file_valued_benchmark_path_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "absent-file"
    root.mkdir()
    benchmark_file = root / "synthetic-cases.yaml"
    benchmark_file.write_text(CASE_ALPHA, encoding="utf-8")
    _, config = _write_config(root / "cfg", benchmark_file)
    benchmark_file.unlink()

    with pytest.raises(ConfirmatoryExecutionError, match="benchmark source"):
        _capture(config)


# --------------------------------------------------------------------------
# 9/10. Every other config-identity input keeps its semantics
# --------------------------------------------------------------------------


def test_config_source_digest_still_detects_config_text_mutation(
    tmp_path: Path,
) -> None:
    config_path, config, _ = _directory_config(tmp_path)
    first = _capture(config)

    config_path.write_bytes(config_path.read_bytes() + b"# trailing comment\n")
    changed = _capture(load_experiment_config(config_path))

    assert changed.experiment_config_digest != first.experiment_config_digest
    assert changed.runtime_identity_digest != first.runtime_identity_digest


@pytest.mark.parametrize("field", ["policy_path", "models_path", "ablations_path"])
def test_file_valued_identity_inputs_keep_file_digest_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    _, config, _ = _directory_config(tmp_path)
    key = {
        "policy_path": "policy_sha256",
        "models_path": "models_sha256",
        "ablations_path": "ablations_sha256",
    }[field]
    path = getattr(config, field)
    assert isinstance(path, Path)

    preimage = _config_preimages(config, monkeypatch)
    assert preimage[key] == hashlib.sha256(path.read_bytes()).hexdigest()

    path.write_bytes(path.read_bytes() + b"\n# synthetic identity edit\n")
    after = _config_preimages(config, monkeypatch)
    assert after[key] != preimage[key]
    assert after[key] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_models_digest_still_equals_the_independently_stored_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, config, _ = _directory_config(tmp_path)
    snapshot = _capture(config)
    preimage = _config_preimages(config, monkeypatch)

    assert snapshot.models_config_digest == preimage["models_sha256"]
    assert snapshot.models_config_digest == confirmatory._file_sha256(
        config.models_path
    )


def test_config_identity_object_key_set_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the DERIVATION of benchmark_sha256 moved; the key set did not."""

    _, config, _ = _directory_config(tmp_path)
    assert set(_config_preimages(config, monkeypatch)) == {
        "schema_version",
        "config_schema_version",
        "source_config_sha256",
        "benchmark_sha256",
        "policy_sha256",
        "models_sha256",
        "ablations_sha256",
        "repetitions",
        "seeds",
        "max_agent_steps",
        "shuffle_treatments",
        "treatments",
        "smoke_case_ids",
        "raw_jsonl",
        "raw_csv",
        "evidence_subdir",
    }


# --------------------------------------------------------------------------
# 11/12. Self-digest validation and stable runtime identity
# --------------------------------------------------------------------------


def test_runtime_snapshot_self_digest_validation_still_works(
    tmp_path: Path,
) -> None:
    _, config, _ = _directory_config(tmp_path)
    snapshot = _capture(config)
    artifact = snapshot.to_dict()

    without_self = {
        key: value for key, value in artifact.items() if key != "self_digest"
    }
    assert artifact["self_digest"] == hashlib.sha256(
        canonical_json_bytes(without_self)
    ).hexdigest()

    confirmatory._validate_live_snapshot(snapshot)


def test_repeated_captures_share_runtime_identity_despite_moving_timestamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, config, _ = _directory_config(tmp_path)
    stamps = iter(("2026-01-01T00:00:00Z", "2026-01-01T00:00:41Z"))
    monkeypatch.setattr(confirmatory, "_capture_timestamp", lambda: next(stamps))

    first = _capture(config)
    second = _capture(config)

    assert first.captured_at != second.captured_at
    assert first.self_digest != second.self_digest
    assert first.runtime_identity_digest == second.runtime_identity_digest
    assert first.experiment_config_digest == second.experiment_config_digest


# --------------------------------------------------------------------------
# 13/14. No caller override, no manual snapshot path
# --------------------------------------------------------------------------


def test_capture_exposes_no_benchmark_digest_override(tmp_path: Path) -> None:
    """The capture signature admits exactly config and provider, both keyword."""

    import inspect

    parameters = inspect.signature(capture_runtime_snapshot_v1).parameters
    assert tuple(parameters) == ("config", "provider")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in parameters.values()
    )

    _, config, _ = _directory_config(tmp_path)
    for attempt in (
        {"benchmark_sha256": "0" * 64},
        {"benchmark_digest": "0" * 64},
        {"benchmark_source_sha256": lambda _path: "0" * 64},
        {"capturer": lambda **_kwargs: None},
    ):
        with pytest.raises(TypeError):
            capture_runtime_snapshot_v1(
                config=config, provider=DeterministicStubProvider(), **attempt
            )


def test_experiment_config_is_the_only_accepted_config_shape(
    tmp_path: Path,
) -> None:
    """A look-alike carrying a pre-chosen digest is refused, not trusted."""

    _, config, _ = _directory_config(tmp_path)

    class ShadowConfig:
        def __init__(self, real: ExperimentConfig) -> None:
            self.__dict__.update(
                {
                    name: getattr(real, name)
                    for name in ExperimentConfig.__slots__
                }
            )
            self.benchmark_sha256 = "0" * 64

    with pytest.raises(ConfirmatoryExecutionError, match="ExperimentConfig"):
        capture_runtime_snapshot_v1(
            config=ShadowConfig(config),  # type: ignore[arg-type]
            provider=DeterministicStubProvider(),
        )


def test_manually_constructed_snapshot_is_not_accepted_as_a_live_capture(
    tmp_path: Path,
) -> None:
    """Hand-built snapshots stay refused; capture remains the only source."""

    _, config, _ = _directory_config(tmp_path)
    real = _capture(config)

    forged = RuntimeSnapshotV1(
        provider_name=real.provider_name,
        model=real.model,
        endpoint=real.endpoint,
        provider_config_digest=real.provider_config_digest,
        provider_parameters_digest=real.provider_parameters_digest,
        timeout_seconds=real.timeout_seconds,
        retry_policy=real.retry_policy,
        tool_contract_policy=real.tool_contract_policy,
        native_tool_adapter_version=real.native_tool_adapter_version,
        package_source_sha256=real.package_source_sha256,
        python_version=real.python_version,
        artifact_version=real.artifact_version,
        prompt_digest=real.prompt_digest,
        experiment_config_digest="0" * 64,
        models_config_digest=real.models_config_digest,
        environment_fingerprint=real.environment_fingerprint,
        captured_at=real.captured_at,
    )

    assert forged.runtime_identity_digest != real.runtime_identity_digest
    assert forged.experiment_config_digest != _capture(config).experiment_config_digest


# --------------------------------------------------------------------------
# The corrected rule agrees with the runner's existing benchmark identity
# --------------------------------------------------------------------------


def test_corrected_rule_matches_the_runner_benchmark_identity_on_a_clean_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No second benchmark identity: the two agree wherever the tree is clean."""

    from iqa_soa.experiment.runner import _path_digest

    _, config, benchmark = _directory_config(tmp_path)
    assert benchmark_source_sha256(benchmark) == _path_digest(benchmark)
    assert (
        _config_preimages(config, monkeypatch)["benchmark_sha256"]
        == _path_digest(benchmark)
    )
