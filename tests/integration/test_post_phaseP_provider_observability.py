"""The C3 provider-observability version boundary, end to end and offline.

**NO MODEL IS RUN ANYWHERE IN THIS FILE**, nothing here contacts a provider or
opens a socket, and nothing here reads, enumerates, traverses or hashes anything
beneath ``results/`` -- in particular nothing beneath
``results/phaseP-rc4-qualification/``.  Every provider response is a synthetic
in-memory object substituted for ``request.urlopen``, and every sentinel value is
authored here.

``tests/unit/test_provider_failure_telemetry.py`` proves the adapter-level
behaviour: that the telemetry is read from the envelope, that the accept/refuse
decision function is unchanged, and that nothing new is disclosed.  This module
proves the four things that are properties of the INSTRUMENT rather than of the
adapter:

* **AC-2, version movement.**  ``RAW_SCHEMA_VERSION`` 5 -> 6 and
  ``INSTRUMENT_VERSION`` "4" -> "5", with the native-tools adapter and the
  model-visible argument contract deliberately unmoved, and every historical
  constant still holding its original value.
* **AC-2, historical readability.**  Schema 1-5 remain readable exactly as
  written, under their own field contracts and their own failure-row semantics.
  A schema-5 row is never reinterpreted under schema-6 rules.
* **AC-3, the synthetic fault-injection dry run.**  The complete writer path,
  driven with a fake ``urlopen``, produces a persisted raw row whose
  ``provider_attempts[-1]`` carries all eleven accepted fields and whose
  row-level ``provider_response_id`` / ``effective_model`` / ``finish_reason`` /
  ``system_fingerprint`` / ``effective_provider_seed`` are non-null on a FAILURE
  row for the first time.
* **AC-4, the declared boundary.**  The new instrument boundary is stated
  explicitly, it does not weaken or replace the frozen ``rc4_instrument_boundary``,
  and the analyzer refuses by default to pool instrument-4 and instrument-5
  sources.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Mapping

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

import instrument_revision  # noqa: E402
import post_phaseP_write_provider_observability_revision as writer  # noqa: E402

from iqa_soa.agent.providers import (  # noqa: E402
    OpenAICompatibleProvider,
    PROVIDER_FAILURE_TELEMETRY_FIELDS,
)
from iqa_soa.benchmark import load_frozen_pilot  # noqa: E402
from iqa_soa.experiment.runner import (  # noqa: E402
    ExperimentRunner,
    load_experiment_config,
)
from iqa_soa.instrument import (  # noqa: E402
    FAILURE_EVENT_RAW_SCHEMA_VERSION,
    FAULT_PROVENANCE_INSTRUMENT_VERSION,
    FAULT_PROVENANCE_RAW_SCHEMA_VERSION,
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    PRE_ARGUMENT_CONTRACT_NATIVE_TOOL_ADAPTER_VERSION,
    PRE_REPAIR_INSTRUMENT_VERSION,
    PRE_REPAIR_RAW_SCHEMA_VERSION,
    PROTOCOL_TELEMETRY_INSTRUMENT_VERSION,
    PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION,
    PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_BOUNDARY,
    PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_VERSION,
    PROVIDER_FAILURE_TELEMETRY_RAW_SCHEMA_VERSION,
    RAW_SCHEMA_VERSION,
    READABLE_PILOT_RAW_SCHEMA_VERSIONS,
    READABLE_RAW_SCHEMA_VERSIONS,
    TOOL_CONTRACT_INSTRUMENT_VERSION,
    TRUTHFUL_ARGUMENT_CONTRACT_NATIVE_TOOL_ADAPTER_VERSION,
)
from iqa_soa.metrics import pilot as pilot_metrics  # noqa: E402
from iqa_soa.metrics.definitions import (  # noqa: E402
    FAILURE_ROW_PROJECTION_CAPTURED_WHERE_AVAILABLE,
    FAILURE_ROW_PROJECTION_NULL_BY_CONSTRUCTION,
    PILOT_RAW_FIELDS,
    PILOT_RAW_FIELDS_V3,
    PILOT_RAW_FIELDS_V4,
    PILOT_RAW_FIELDS_V5,
    PILOT_RAW_FIELDS_V6,
    PROVIDER_ENVELOPE_PRESENCE_KEYS,
    PROVIDER_FAILURE_PROJECTION_FIELDS,
    PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS,
    RAW_FIELDS_BY_SCHEMA_VERSION,
    REQUIRED_RAW_FIELDS,
    failure_row_projection_contract,
    provider_failure_attempt_required_keys,
    provider_failure_attempt_violations,
)
from iqa_soa.tools.argument_schema import TOOL_ARGUMENT_CONTRACT_VERSION  # noqa: E402

RECORD_RELATIVE = "docs/post_phaseP_provider_observability_instrument_revision.json"
RECORD_PATH = PROJECT_ROOT / RECORD_RELATIVE

#: The commit this implementation started from: the last commit at which the
#: post-Phase-P confirmatory revision was the approved head.
PARENT_COMMIT = "883c425daf2e6462877f0626f5fce0664ac85ca9"

#: Stated here independently of the writer, so a widened writer constant cannot
#: quietly widen the approved set too.
APPROVED_SRC_FILES = (
    "src/iqa_soa/agent/__init__.py",
    "src/iqa_soa/agent/providers.py",
    "src/iqa_soa/experiment/runner.py",
    "src/iqa_soa/instrument.py",
    "src/iqa_soa/metrics/definitions.py",
    # The production reader boundary. definitions.py DECLARES the schema-6
    # per-attempt contract; pilot.py is where the raw-row reader ENFORCES it,
    # and without this entry the contract is testable but not end-to-end binding.
    "src/iqa_soa/metrics/pilot.py",
)


def _blob(commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=PROJECT_ROOT, capture_output=True, check=True,
    ).stdout


@pytest.fixture(scope="module")
def record() -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    return parsed


# ==========================================================================
# AC-2 -- version movement
# ==========================================================================


def test_the_two_aliases_moved_and_nothing_else_did() -> None:
    """T-18.  Exactly two constants move, and both are named permanently.

    The native-tools adapter and the model-visible argument contract are held
    DELIBERATELY: the request payload is byte-identical and the accept/refuse
    decision function is byte-identical, so bumping either would assert a
    difference that does not exist and would destroy the independence between the
    adapter boundary and the instrument boundary that Phase M established.
    """

    assert PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_VERSION == "5"
    assert PROVIDER_FAILURE_TELEMETRY_RAW_SCHEMA_VERSION == 6
    assert INSTRUMENT_VERSION == PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_VERSION
    assert RAW_SCHEMA_VERSION == PROVIDER_FAILURE_TELEMETRY_RAW_SCHEMA_VERSION

    assert NATIVE_TOOL_ADAPTER_VERSION == "native-tools-adapter-3"
    assert NATIVE_TOOL_ADAPTER_VERSION == (
        TRUTHFUL_ARGUMENT_CONTRACT_NATIVE_TOOL_ADAPTER_VERSION
    )
    assert TOOL_ARGUMENT_CONTRACT_VERSION == "tool-arguments-1"


def test_every_historical_constant_still_holds_its_original_value() -> None:
    """T-18.  A named boundary is permanent; C3 re-points aliases only."""

    assert PRE_REPAIR_INSTRUMENT_VERSION == "1"
    assert PROTOCOL_TELEMETRY_INSTRUMENT_VERSION == "2"
    assert FAULT_PROVENANCE_INSTRUMENT_VERSION == "3"
    assert TOOL_CONTRACT_INSTRUMENT_VERSION == "4"
    assert PRE_REPAIR_RAW_SCHEMA_VERSION == 2
    assert PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION == 3
    assert FAULT_PROVENANCE_RAW_SCHEMA_VERSION == 4
    assert FAILURE_EVENT_RAW_SCHEMA_VERSION == 5
    assert PRE_ARGUMENT_CONTRACT_NATIVE_TOOL_ADAPTER_VERSION == "native-tools-adapter-2"
    # Nothing is removed from either readable tuple, and 6 is appended.
    assert READABLE_RAW_SCHEMA_VERSIONS == (1, 2, 3, 4, 5, 6)
    assert READABLE_PILOT_RAW_SCHEMA_VERSIONS == (2, 3, 4, 5, 6)


# ==========================================================================
# AC-2 -- historical readability, and the schema-6 read contract
# ==========================================================================


def test_every_historical_field_contract_is_byte_identical_to_its_committed_form() -> None:
    """T-19.  Schemas 1-5 are read exactly as they were written.

    The comparison is against the COMMITTED module at the commit this change
    started from, so a field silently added to, removed from or reordered within
    an older tuple fails here -- which no assertion written against the live
    module could catch.
    """

    committed_source = _blob(PARENT_COMMIT, "src/iqa_soa/metrics/definitions.py")
    namespace: dict[str, Any] = {}
    exec(compile(committed_source, "definitions.py@parent", "exec"), namespace)

    for name, live in (
        ("REQUIRED_RAW_FIELDS", REQUIRED_RAW_FIELDS),
        ("PILOT_RAW_FIELDS", PILOT_RAW_FIELDS),
        ("PILOT_RAW_FIELDS_V3", PILOT_RAW_FIELDS_V3),
        ("PILOT_RAW_FIELDS_V4", PILOT_RAW_FIELDS_V4),
        ("PILOT_RAW_FIELDS_V5", PILOT_RAW_FIELDS_V5),
    ):
        assert live == namespace[name], name

    previous = namespace["RAW_FIELDS_BY_SCHEMA_VERSION"]
    for version in (1, 2, 3, 4, 5):
        assert RAW_FIELDS_BY_SCHEMA_VERSION[version] == previous[version], version
    # Schema 6 is the only entry added, and it adds no column.
    assert set(RAW_FIELDS_BY_SCHEMA_VERSION) - set(previous) == {6}
    assert PILOT_RAW_FIELDS_V6 == PILOT_RAW_FIELDS_V5
    assert RAW_FIELDS_BY_SCHEMA_VERSION[6] == PILOT_RAW_FIELDS_V6


def test_a_schema_five_row_is_read_under_schema_five_semantics() -> None:
    """T-21 (task list).  A historical null keeps its historical meaning.

    On a schema 2-5 failure row the five projected columns are null BY
    CONSTRUCTION -- an artifact of the instrument, saying nothing about what the
    provider sent. C3 must not retroactively turn those nulls into observations,
    and ``failure_row_projection_contract`` is what keeps the two readings apart.
    """

    for version in (2, 3, 4, 5):
        assert failure_row_projection_contract(version) == (
            FAILURE_ROW_PROJECTION_NULL_BY_CONSTRUCTION
        ), version
        assert provider_failure_attempt_required_keys(version) == (), version
    assert failure_row_projection_contract(6) == (
        FAILURE_ROW_PROJECTION_CAPTURED_WHERE_AVAILABLE
    )

    # A synthetic schema-5 failure attempt, shaped exactly as the pre-C3
    # instrument wrote one, is still valid under its own schema.
    legacy_attempt = {
        "outcome": "failure",
        "failure_class": "invalid_tool_call",
        "client_request_id": "c",
        "request_id": None,
        "response_id": None,
        "effective_model": None,
        "finish_reason": None,
        "system_fingerprint": None,
        "input_tokens": None,
        "output_tokens": None,
    }
    for version in (2, 3, 4, 5):
        assert provider_failure_attempt_violations(
            legacy_attempt, raw_schema_version=version
        ) == [], version
    with pytest.raises(KeyError):
        failure_row_projection_contract(7)


def test_a_schema_six_failure_row_requires_the_c3_telemetry_contract() -> None:
    """T-22 (task list).  Schema 6 demands what schema 5 could not produce."""

    assert provider_failure_attempt_required_keys(6) == (
        PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS
    )
    assert PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS == PROVIDER_FAILURE_TELEMETRY_FIELDS

    legacy_attempt = {"outcome": "failure", "failure_class": "invalid_tool_call"}
    violations = provider_failure_attempt_violations(
        legacy_attempt, raw_schema_version=6
    )
    assert len(violations) == len(PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS)
    assert all(item.startswith("missing ") for item in violations)

    complete = {
        "outcome": "failure",
        **{name: None for name in PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS},
        "envelope_field_presence": {
            name: "UNOBSERVED" for name in PROVIDER_ENVELOPE_PRESENCE_KEYS
        },
    }
    assert provider_failure_attempt_violations(complete, raw_schema_version=6) == []

    # The presence object is closed in both directions, and its values are a
    # closed vocabulary.
    extra_key = dict(complete)
    extra_key["envelope_field_presence"] = {
        **complete["envelope_field_presence"],
        "invented": "UNOBSERVED",
    }
    assert provider_failure_attempt_violations(extra_key, raw_schema_version=6)
    bad_value = dict(complete)
    bad_value["envelope_field_presence"] = {
        **complete["envelope_field_presence"],
        "response_id": "PROBABLY",
    }
    assert provider_failure_attempt_violations(bad_value, raw_schema_version=6)

    # A SUCCESS attempt is unconstrained: C3 does not touch the success record.
    assert provider_failure_attempt_violations(
        {"outcome": "action"}, raw_schema_version=6
    ) == []


# ==========================================================================
# AC-3 -- the synthetic fault-injection dry run, through the real writer
# ==========================================================================


WRONG_CHANNEL_ENVELOPE = {
    "id": "chatcmpl-DRYRUN-SENTINEL",
    "model": "model-DRYRUN-SENTINEL",
    "system_fingerprint": "fp-DRYRUN-SENTINEL",
    "choices": [
        {
            "finish_reason": "stop",
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
    "usage": {"prompt_tokens": 41, "completion_tokens": 17},
}


class _FakeHTTPResponse:
    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def getheader(self, name: str) -> str | None:
        return "req-dryrun" if name.lower() == "x-request-id" else None

    def read(self) -> bytes:
        return json.dumps(WRONG_CHANNEL_ENVELOPE).encode("utf-8")


@pytest.fixture()
def dry_run_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Mapping[str, Any]:
    """One persisted raw row from the REAL writer, with no provider contact.

    ``request.urlopen`` is replaced and ``socket.create_connection`` is made to
    raise, so a code path that tried to reach a network would fail loudly rather
    than silently succeed.
    """

    def _refuse(*_: Any, **__: Any) -> Any:
        raise AssertionError("the dry run may never open a socket")

    monkeypatch.setenv("C3_DRYRUN_KEY", "dry-run-secret")
    monkeypatch.setattr(
        "iqa_soa.agent.providers.request.urlopen",
        lambda request, timeout: _FakeHTTPResponse(),
    )
    monkeypatch.setattr(
        "iqa_soa.agent.providers.socket.create_connection", _refuse, raising=False
    )
    provider = OpenAICompatibleProvider(
        endpoint="https://example.invalid/v1/chat/completions",
        model="synthetic-dryrun-model",
        api_key_env="C3_DRYRUN_KEY",
        protocol="native_tools",
        seed=9091,
    )
    config = load_experiment_config(
        PROJECT_ROOT / "configs" / "experiment.yaml"
    ).with_overrides(output_root=tmp_path, repetitions=1)
    frozen = load_frozen_pilot(
        PROJECT_ROOT / "benchmark" / "pilot-v1" / "manifest.json"
    )
    directory = ExperimentRunner(config, provider=provider).run(
        treatments=["off"],
        repetitions=1,
        frozen_benchmark=frozen,
        max_total_runs=64,
        experiment_kind="real_model_pilot",
    )
    rows = [
        json.loads(line)
        for line in (directory / config.raw_jsonl).read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    assert rows, "the dry run produced no row"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["raw_schema_version"] == 6
    assert manifest["instrument_version"] == "5"
    assert manifest["native_tool_adapter_version"] == "native-tools-adapter-3"
    return rows[0]


def test_the_dry_run_row_carries_every_accepted_field(
    dry_run_row: Mapping[str, Any],
) -> None:
    """T-20, AC-3.  The whole path, from synthetic envelope to persisted row."""

    attempts = dry_run_row["provider_attempts"]
    assert attempts, "a failed provider call must still record an attempt"
    attempt = attempts[-1]
    assert attempt["outcome"] == "failure"
    assert provider_failure_attempt_violations(attempt, raw_schema_version=6) == []

    assert attempt["failure_branch"] == "NATIVE_CONTENT_ACTION_WRONG_CHANNEL"
    assert attempt["response_id"] == "chatcmpl-DRYRUN-SENTINEL"
    assert attempt["effective_model"] == "model-DRYRUN-SENTINEL"
    assert attempt["system_fingerprint"] == "fp-DRYRUN-SENTINEL"
    assert attempt["finish_reason"] == "stop"
    assert attempt["input_tokens"] == 41
    assert attempt["output_tokens"] == 17
    assert attempt["protocol"] == "native_tools"
    assert attempt["effective_seed"] == 9091
    assert attempt["native_tool_call_state"] == "KEY_ABSENT"
    assert attempt["envelope_field_presence"] == {
        name: "SUPPLIED" for name in PROVIDER_ENVELOPE_PRESENCE_KEYS
    }


def test_the_five_projected_columns_are_non_null_on_a_failure_row(
    dry_run_row: Mapping[str, Any],
) -> None:
    """T-20, AC-3.  The row-level projection carries values for the first time.

    Under schema 5 all five of these were null on EVERY failure row -- four
    because ``ProviderError.provenance()`` hard-coded them and the fifth because
    its key was absent from the failure record entirely. That is the ambiguity
    the schema bump exists to separate, and this is the assertion that it is
    actually gone.
    """

    assert dry_run_row["failure_class"] == "invalid_tool_call"
    assert dry_run_row["provider_response_id"] == "chatcmpl-DRYRUN-SENTINEL"
    assert dry_run_row["effective_model"] == "model-DRYRUN-SENTINEL"
    assert dry_run_row["finish_reason"] == "stop"
    assert dry_run_row["system_fingerprint"] == "fp-DRYRUN-SENTINEL"
    assert dry_run_row["effective_provider_seed"] == 9091
    for name in PROVIDER_FAILURE_PROJECTION_FIELDS:
        assert dry_run_row[name] is not None, name


def test_the_dry_run_row_discloses_nothing_new(
    dry_run_row: Mapping[str, Any],
) -> None:
    """The persisted row carries no credential, prompt echo or response body."""

    serialized = json.dumps(dry_run_row, sort_keys=True, default=str)
    for forbidden in ("dry-run-secret", "Bearer", "Authorization", "example.invalid"):
        assert forbidden not in serialized, forbidden


def test_the_written_row_satisfies_the_schema_it_declares(
    dry_run_row: Mapping[str, Any],
) -> None:
    """Every schema-6 column is present, and schema 6 adds none."""

    missing = set(RAW_FIELDS_BY_SCHEMA_VERSION[6]) - set(dry_run_row)
    assert missing == set(), sorted(missing)
    assert set(RAW_FIELDS_BY_SCHEMA_VERSION[6]) == set(RAW_FIELDS_BY_SCHEMA_VERSION[5])


# ==========================================================================
# AC-4 -- the declared boundary, and default separation
# ==========================================================================


def test_the_new_instrument_boundary_is_declared_explicitly() -> None:
    """T-21, AC-4.  Stated, machine-readable, and specific about both sides."""

    declaration = PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_BOUNDARY
    for clause in (
        "instrument 5 / raw schema 6 / native-tools-adapter-3",
        "instrument 4 / raw schema 5 / native-tools-adapter-3",
        "DEFAULT IS SEPARATION",
        "MUST NOT be merged, pooled, averaged or compared",
        "must say so explicitly and justify it",
    ):
        assert clause in declaration, clause


def test_the_frozen_rc4_boundary_is_neither_weakened_nor_replaced() -> None:
    """T-21, AC-4.  rc4's own contract is untouched, byte for byte."""

    relative = "benchmark/pilot-v7-rc4/qualification-contract.json"
    assert (PROJECT_ROOT / relative).read_bytes() == _blob(PARENT_COMMIT, relative)
    contract = json.loads((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
    frozen = json.dumps(contract)
    assert "rc4_instrument_boundary" in frozen
    # The new declaration lives on the instrument, not inside rc4's contract:
    # rc4 is a frozen, UNQUALIFIED release candidate and C3 creates no successor.
    assert PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_BOUNDARY not in frozen


def test_instrument_four_and_instrument_five_sources_are_not_pooled_by_default(
    tmp_path: Path,
) -> None:
    """T-23 (task list), AC-4.  The analyzer refuses the merge, it does not warn.

    Two otherwise valid real-pilot sources that disagree on ``instrument_version``
    are refused, so a post-C3 run cannot be silently averaged with a Phase-B..P
    run. The refusal is driven through the real loader, not asserted about a
    constant.
    """

    from tests.integration.test_real_pilot_analysis import _pilot_run

    first = _pilot_run(tmp_path / "one", "synthetic-online-a")
    second = _pilot_run(tmp_path / "two", "synthetic-online-b")
    # Both were written by the live instrument, so they pool cleanly.
    assert pilot_metrics.load_real_pilot_records([first, second])

    # Relabel the SECOND source as an instrument-4 run, consistently across its
    # manifest and every one of its rows, so what is being tested is the
    # cross-source pooling rule and not a row/manifest disagreement.
    manifest_path = second / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["instrument_version"] == "5"
    manifest["instrument_version"] = TOOL_CONTRACT_INSTRUMENT_VERSION
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    raw_path = second / load_experiment_config(
        PROJECT_ROOT / "configs" / "experiment.yaml"
    ).raw_jsonl
    rows = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        row["instrument_version"] = TOOL_CONTRACT_INSTRUMENT_VERSION
    raw_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    with pytest.raises(pilot_metrics.AnalysisError, match="different instrument"):
        pilot_metrics.load_real_pilot_records([first, second])


def test_a_schema_six_manifest_is_readable_and_so_is_every_older_one() -> None:
    """Nothing is removed from the readable set; schema 6 is added to it."""

    assert 6 in READABLE_PILOT_RAW_SCHEMA_VERSIONS
    assert set(READABLE_PILOT_RAW_SCHEMA_VERSIONS) >= {2, 3, 4, 5}
    assert set(READABLE_RAW_SCHEMA_VERSIONS) >= {1, 2, 3, 4, 5}


# ==========================================================================
# The approved instrument revision this change is recorded under
# ==========================================================================


def test_the_record_is_exactly_reproducible_from_the_live_tree() -> None:
    """T-22.  A reviewer re-runs the writer and compares; no digest is pasted."""

    expected = json.dumps(writer.build_record(), indent=2, sort_keys=True) + "\n"
    assert RECORD_PATH.read_text(encoding="utf-8") == expected


def test_the_record_is_the_head_of_the_approved_chain(
    record: Mapping[str, Any],
) -> None:
    chain = instrument_revision.load_revision_chain()
    assert [link["phase"] for link in chain] == [
        "M",
        "O",
        "POST_PHASEP_CONFIRMATORY",
        "POST_PHASEP_PROVIDER_OBSERVABILITY",
    ]
    assert instrument_revision.REVISION_PATH == RECORD_PATH
    assert chain[-1] == record
    assert record["current_instrument"]["src_iqa_soa_tree"] == (
        instrument_revision.tree_digest("src/iqa_soa")
    )
    assert record["parent_commit"] == PARENT_COMMIT
    # Custody: it binds the predecessor's AUTHORITATIVE digest -- the one provable
    # from committed bytes at the commit this revision started from. The
    # predecessor's own record declares a digest captured over CRLF working-tree
    # bytes that no commit can hold, a defect that predates C3; that record is
    # preserved byte-for-byte and superseded by an additive correction, not edited.
    predecessor = json.loads(
        (PROJECT_ROOT / writer.PREDECESSOR_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    corrected = instrument_revision.tree_digest_at_commit(PARENT_COMMIT, "src/iqa_soa")
    assert record["previous_instrument"]["src_iqa_soa_tree"] == corrected
    assert predecessor["current_instrument"]["src_iqa_soa_tree"] != corrected
    # And the chain validates clean end to end, with nothing suppressed.
    assert instrument_revision.check_instrument_provenance() == []


def test_the_approved_set_is_exactly_the_observed_src_change_set(
    record: Mapping[str, Any],
) -> None:
    observed = subprocess.run(
        ["git", "diff", "--name-only", PARENT_COMMIT, "--", "src/iqa_soa"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert sorted(observed) == sorted(APPROVED_SRC_FILES)
    assert sorted(record["changed_files"]) == sorted(APPROVED_SRC_FILES)
    assert tuple(writer.APPROVED_SRC_FILES) == APPROVED_SRC_FILES


def test_every_approved_file_carries_its_real_hash_and_a_distinct_reason(
    record: Mapping[str, Any],
) -> None:
    changed = record["changed_files"]
    for name in APPROVED_SRC_FILES:
        entry = changed[name]
        assert entry["sha256"] == instrument_revision.sha256_of(
            PROJECT_ROOT / name
        ), name
        assert len(entry["reason"].strip()) >= 20, name
    assert len({entry["reason"] for entry in changed.values()}) == len(changed)


def test_the_record_declares_the_versions_the_code_declares(
    record: Mapping[str, Any],
) -> None:
    current = record["current_instrument"]
    assert current["instrument_version"] == INSTRUMENT_VERSION == "5"
    assert current["raw_schema_version"] == RAW_SCHEMA_VERSION == 6
    assert current["native_tool_adapter_version"] == NATIVE_TOOL_ADAPTER_VERSION
    assert current["tool_argument_contract_version"] == TOOL_ARGUMENT_CONTRACT_VERSION
    assert current["adapter_unchanged"] is True
    previous = record["previous_instrument"]
    assert previous["instrument_version"] == "4"
    assert previous["raw_schema_version"] == 5
    # The adapter and the model-visible contract are the SAME on both sides.
    assert previous["native_tool_adapter_version"] == (
        current["native_tool_adapter_version"]
    )
    assert previous["tool_argument_contract_version"] == (
        current["tool_argument_contract_version"]
    )


def test_the_record_states_an_observation_only_prospective_change(
    record: Mapping[str, Any],
) -> None:
    assert record["record_kind"] == "instrument_revision"
    assert record["observation_only"] is True
    assert record["model_inference_performed"] is False
    assert record["phase_p_execution_rerun"] is False
    assert record["phase_p_result_reinterpreted"] is False
    assert record["historical_rows_rescored"] is False
    assert record["benchmark_freeze_records_overwritten"] is False
    assert record["instrument_revisions_overwritten"] is False
    assert record["authorizes_confirmatory_execution"] is False
    assert record["successor_candidate_created"] is False
    assert record["ben_003_rehabilitated"] is False
    hold = record["phase_p_rc4_hold"]
    assert hold["qualification_status"] == "UNQUALIFIED"
    assert hold["verdict"] == "HOLD"
    assert hold["terminal_status"] == "SCHEDULE_COMPLETE_VERDICT_HOLD"
    assert hold["phase_p_cells_rerun"] == 0
    assert hold["phase_p_rows_rescored"] == 0
    assert "MODEL_PROTOCOL_INVALID" in hold["note"]
    assert "MATRIX_INVALID" in hold["note"]
    assert "UNKNOWABLE" in hold["note"]


@pytest.mark.parametrize(
    "relative",
    [
        "docs/phaseM_instrument_revision.json",
        "docs/phaseO_instrument_revision.json",
        "docs/post_phaseP_confirmatory_instrument_revision.json",
        "benchmark/pilot-v7-rc3/freeze-record.json",
        "benchmark/pilot-v7-rc4/freeze-record.json",
        "benchmark/pilot-v7-rc4/qualification-contract.json",
        "docs/phaseL_frozen_execution_inputs.json",
        "docs/phaseP_frozen_execution_inputs.json",
        "scripts/phaseP_protocol.py",
    ],
)
def test_no_predecessor_or_frozen_record_was_edited(relative: str) -> None:
    """Nothing historical moved, including the Phase-P protocol's own pins.

    ``scripts/phaseP_protocol.py`` is in this list deliberately. Its literal pins
    now FAIL to match the live constants, and that is the correct and intended
    behaviour: it is the mechanism that binds any future successor to the post-C3
    instrument only, and prevents a retroactive reinterpretation of Phase-P rows.
    Repairing it would be exactly the wrong move.
    """

    assert (PROJECT_ROOT / relative).read_bytes() == _blob(PARENT_COMMIT, relative)


def test_the_writer_reaches_no_evidence_and_performs_no_inference() -> None:
    """It reads git, ``src/iqa_soa``, ``benchmark/`` and ``configs/`` -- nothing else."""

    import ast

    path = SCRIPTS_ROOT / "post_phaseP_write_provider_observability_revision.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for forbidden in ("socket", "http", "urllib", "requests", "httpx", "openai", "ollama"):
        assert forbidden not in imported, forbidden

    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert not [item for item in literals if item.strip("/") == "results"]
    assert not [item for item in literals if item.startswith("results/")]
    named = [item for item in literals if "results/phaseP-rc4-qualification" in item]
    assert len(named) == 1, (
        "the Phase-P evidence root is named more than once in the writer; the only "
        "permitted mention is the record's untouched-evidence statement"
    )


def test_the_writer_refuses_a_widened_or_narrowed_change_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        writer.ir,
        "_changed_files_since",
        lambda _commit, _root: [*APPROVED_SRC_FILES, "src/iqa_soa/failure_taxonomy.py"],
    )
    with pytest.raises(SystemExit, match="not the approved set"):
        writer.build_record()

    monkeypatch.setattr(
        writer.ir,
        "_changed_files_since",
        lambda _commit, _root: list(APPROVED_SRC_FILES[:-1]),
    )
    with pytest.raises(SystemExit, match="not the approved set"):
        writer.build_record()


def test_the_writer_refuses_a_predecessor_custody_state_it_cannot_prove(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No provable predecessor digest, no record. It refuses rather than guessing.

    The predecessor's declared pin is irreproducible from history, so the ONLY
    digest this revision may bind is the corrected one the additive custody
    correction supplies -- and only while that correction itself proves out
    against committed bytes. Take the correction away and the writer refuses; have
    it assert a digest the commit does not contain and it refuses too.
    """

    monkeypatch.setattr(writer.ir, "CUSTODY_CORRECTION_PATH", tmp_path / "absent.json")
    with pytest.raises(SystemExit, match="custody correction does not hold"):
        writer.build_record()

    monkeypatch.undo()
    monkeypatch.setattr(
        writer.ir,
        "verify_custody_correction",
        lambda **_kwargs: (
            [],
            {
                "commit": PARENT_COMMIT,
                "record": writer.PREDECESSOR_RECORD_RELATIVE,
                "tree": "0" * 64,
            },
        ),
    )
    with pytest.raises(SystemExit, match="corrected tree"):
        writer.build_record()


def test_the_record_states_the_predecessor_custody_correction(
    record: Mapping[str, Any],
) -> None:
    """The one thing that did NOT check out is named, repaired additively, cited.

    ``instrument_revision.sha256_of`` hashes raw WORKING-TREE bytes while a
    superseded link is proved against COMMITTED blobs, and this repository
    declares ``* text=auto eol=lf`` -- so a working-tree file carrying CRLF is
    reported UNCHANGED by git while hashing differently. The predecessor's pin
    was computed over such a tree, before C3 and independently of it, and no
    commit can reproduce it.

    This revision does not hide that, does not edit the predecessor, and does not
    bind an unprovable digest. It cites the additive correction record, states the
    predecessor's declared value beside the authoritative one, and binds the
    authoritative one.
    """

    custody = record["predecessor_custody"]
    committed = instrument_revision.tree_digest_at_commit(PARENT_COMMIT, "src/iqa_soa")
    assert custody["predecessor_declared_pin_is_reproducible_from_history"] is False
    assert custody["authoritative_src_iqa_soa_tree"] == committed
    assert custody["committed_src_iqa_soa_tree_at_parent_commit"] == committed
    assert custody["predecessor_declared_src_iqa_soa_tree"] != committed
    assert custody["corrected_record"] == writer.PREDECESSOR_RECORD_RELATIVE
    assert custody["corrected_record_edited_by_this_revision"] is False
    assert custody["correction_record"] == writer.CUSTODY_CORRECTION_RELATIVE

    correction_path = PROJECT_ROOT / custody["correction_record"]
    assert correction_path.is_file()
    assert custody["correction_record_sha256"] == instrument_revision.sha256_of(
        correction_path
    )
    assert custody["corrected_record_sha256"] == instrument_revision.sha256_of(
        PROJECT_ROOT / custody["corrected_record"]
    )
    # The predecessor record is byte-identical to the version at its own commit:
    # superseded, never rewritten.
    assert (PROJECT_ROOT / custody["corrected_record"]).read_bytes() == _blob(
        PARENT_COMMIT, custody["corrected_record"]
    )
    assert "REPAIRED ADDITIVELY" in custody["note"]
    assert "PRESERVED BYTE-FOR-BYTE" in custody["note"]

# ==========================================================================
# The schema-6 attempt contract, ENFORCED at the production reader boundary
# ==========================================================================
#
# Everything above proves the contract is DECLARED and decidable.  Everything
# below proves the production consumer actually applies it: a real bundle is
# produced by the real runner, its ``runs.jsonl`` is rewritten on disk, and the
# refusal is driven through ``load_real_pilot_records`` -- the same call
# ``analyze_real_pilot`` and ``scripts/generate_pilot_figures.py`` make -- rather
# than by calling the decision function directly.


def _valid_failure_attempt() -> dict[str, Any]:
    """A complete, valid schema-6 FAILURE attempt, as the live instrument writes one.

    Every value here is authored for this test and is derived from no model
    output and from no recorded outcome of any kind.
    """

    return {
        "outcome": "failure",
        "failure_class": "invalid_tool_call",
        "failure_branch": "NATIVE_CONTENT_ACTION_WRONG_CHANNEL",
        "response_id": "chatcmpl-CONTRACT-SENTINEL",
        "system_fingerprint": "fp-CONTRACT-SENTINEL",
        "finish_reason": "stop",
        "effective_model": "model-CONTRACT-SENTINEL",
        "input_tokens": 41,
        "output_tokens": 17,
        "protocol": "native_tools",
        "effective_seed": 9091,
        "native_tool_call_state": "KEY_ABSENT",
        "envelope_field_presence": {
            name: "SUPPLIED" for name in PROVIDER_ENVELOPE_PRESENCE_KEYS
        },
    }


def _rewrite_rows(source: Path, mutate: Any) -> None:
    """Apply ``mutate`` to every persisted raw row, in place, on disk."""

    raw_path = source / load_experiment_config(
        PROJECT_ROOT / "configs" / "experiment.yaml"
    ).raw_jsonl
    rows = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        mutate(row)
    raw_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _set_raw_schema(source: Path, version: int) -> None:
    """Relabel the bundle's declared raw schema version in its manifest."""

    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["raw_schema_version"] = version
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )


def _append_attempt(attempt: Any) -> Any:
    """Give every row one additional provider attempt, counted correctly.

    The attempt is APPENDED rather than substituted so ``provider_attempt_count``
    stays honest and the pre-existing structural checks -- list shape, count
    agreement, at-least-one-attempt -- pass unchanged.  What is under test is the
    C3 attempt contract and nothing else.
    """

    def mutate(row: dict[str, Any]) -> None:
        row["provider_attempts"] = [
            *row["provider_attempts"],
            dict(attempt) if isinstance(attempt, Mapping) else attempt,
        ]
        row["provider_attempt_count"] = len(row["provider_attempts"])

    return mutate


@pytest.fixture(scope="module")
def schema_six_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One real, valid, freshly written schema-6 bundle, reused read-only."""

    from tests.integration.test_real_pilot_analysis import _pilot_run

    source = _pilot_run(
        tmp_path_factory.mktemp("schema6-baseline"), "synthetic-online-a"
    )
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["raw_schema_version"] == 6
    assert manifest["instrument_version"] == "5"
    assert manifest["native_tool_adapter_version"] == NATIVE_TOOL_ADAPTER_VERSION
    return source


def _fresh_bundle(tmp_path: Path, schema_six_bundle: Path) -> Path:
    """A writable copy of the valid bundle, so every case starts from clean."""

    target = tmp_path / "bundle"
    shutil.copytree(schema_six_bundle, target)
    return target


def test_the_production_reader_accepts_a_valid_schema_six_failure_attempt(
    tmp_path: Path, schema_six_bundle: Path
) -> None:
    """A well-formed C3 failure attempt passes through the real loader.

    This is the control for every refusal below: without it a refusal would not
    distinguish "the contract is enforced" from "the bundle was broken anyway".
    """

    source = _fresh_bundle(tmp_path, schema_six_bundle)
    _rewrite_rows(source, _append_attempt(_valid_failure_attempt()))
    rows, validation = pilot_metrics.load_real_pilot_records([source])
    assert rows
    assert validation["records"] == len(rows)
    assert all(
        any(item.get("outcome") == "failure" for item in row["provider_attempts"])
        for row in rows
    )


@pytest.mark.parametrize("omitted", PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS)
def test_removing_any_required_attempt_field_is_refused_by_the_reader(
    tmp_path: Path, schema_six_bundle: Path, omitted: str
) -> None:
    """Each of the eleven accepted fields is individually load-bearing.

    Removed one at a time, so a single over-broad check cannot be mistaken for
    eleven independent ones.
    """

    attempt = _valid_failure_attempt()
    del attempt[omitted]
    source = _fresh_bundle(tmp_path, schema_six_bundle)
    _rewrite_rows(source, _append_attempt(attempt))
    with pytest.raises(pilot_metrics.AnalysisError) as excinfo:
        pilot_metrics.load_real_pilot_records([source])
    assert f"missing {omitted}" in str(excinfo.value), str(excinfo.value)
    assert "raw schema 6" in str(excinfo.value)


def _replace_presence(attempt: dict[str, Any], value: Any) -> None:
    attempt["envelope_field_presence"] = value


def _set_presence_key(attempt: dict[str, Any], key: str, value: Any) -> None:
    attempt["envelope_field_presence"][key] = value


def _drop_presence_key(attempt: dict[str, Any], key: str) -> None:
    del attempt["envelope_field_presence"][key]


@pytest.mark.parametrize(
    "mutate, expected",
    [
        pytest.param(
            lambda attempt: _replace_presence(attempt, "SUPPLIED"),
            "envelope_field_presence is not an object",
            id="presence object replaced by a string",
        ),
        pytest.param(
            lambda attempt: _replace_presence(attempt, []),
            "envelope_field_presence is not an object",
            id="presence object replaced by a list",
        ),
        pytest.param(
            lambda attempt: _replace_presence(attempt, None),
            "envelope_field_presence is not an object",
            id="presence object replaced by null",
        ),
        pytest.param(
            lambda attempt: _replace_presence(attempt, 6),
            "envelope_field_presence is not an object",
            id="presence object replaced by an integer",
        ),
        pytest.param(
            lambda attempt: _set_presence_key(attempt, "response_id", "PROBABLY"),
            "envelope_field_presence",
            id="a presence value outside the closed vocabulary",
        ),
        pytest.param(
            lambda attempt: _set_presence_key(attempt, "finish_reason", None),
            "envelope_field_presence",
            id="a presence value of the wrong type",
        ),
        pytest.param(
            lambda attempt: _drop_presence_key(attempt, "finish_reason"),
            "envelope_field_presence keys are",
            id="a presence key removed -- the object is closed",
        ),
        pytest.param(
            lambda attempt: _set_presence_key(attempt, "invented", "UNOBSERVED"),
            "envelope_field_presence keys are",
            id="a presence key invented -- the object is closed",
        ),
    ],
)
def test_wrong_types_and_wrong_enums_are_refused_by_the_reader(
    tmp_path: Path, schema_six_bundle: Path, mutate: Any, expected: str
) -> None:
    """The closed presence object is enforced in production, not only in a unit test."""

    attempt = _valid_failure_attempt()
    mutate(attempt)
    source = _fresh_bundle(tmp_path, schema_six_bundle)
    _rewrite_rows(source, _append_attempt(attempt))
    with pytest.raises(pilot_metrics.AnalysisError) as excinfo:
        pilot_metrics.load_real_pilot_records([source])
    assert expected in str(excinfo.value), str(excinfo.value)


@pytest.mark.parametrize("scalar", [None, 3, "x", True, []])
def test_a_non_object_attempt_entry_is_refused_under_schema_six(
    tmp_path: Path, schema_six_bundle: Path, scalar: Any
) -> None:
    """A schema-6 attempt that is not an object is corruption, not a datum."""

    source = _fresh_bundle(tmp_path, schema_six_bundle)
    _rewrite_rows(source, _append_attempt(scalar))
    with pytest.raises(pilot_metrics.AnalysisError, match="is not an object"):
        pilot_metrics.load_real_pilot_records([source])


def test_extra_attempt_keys_follow_the_existing_open_contract_exactly(
    tmp_path: Path, schema_six_bundle: Path
) -> None:
    """The ATTEMPT object is open; only ``envelope_field_presence`` is closed.

    C3 states the accepted MINIMUM telemetry, so an attempt carrying additional
    keys satisfies it.  Wiring the contract into the reader must not silently
    convert that open contract into a closed one: that would be a new rule, and
    no new rule is authorized here.
    """

    attempt = _valid_failure_attempt()
    attempt["an_unrecognised_key"] = "tolerated by the accepted-minimum contract"
    attempt["another"] = {"nested": [1, 2, 3]}
    assert provider_failure_attempt_violations(attempt, raw_schema_version=6) == []

    source = _fresh_bundle(tmp_path, schema_six_bundle)
    _rewrite_rows(source, _append_attempt(attempt))
    assert pilot_metrics.load_real_pilot_records([source])


def test_a_success_attempt_is_still_unconstrained_at_the_reader(
    tmp_path: Path, schema_six_bundle: Path
) -> None:
    """C3 does not touch the success record, and enforcement must not either."""

    source = _fresh_bundle(tmp_path, schema_six_bundle)
    _rewrite_rows(source, _append_attempt({"outcome": "action", "response_id": "r"}))
    assert pilot_metrics.load_real_pilot_records([source])


def test_the_unmodified_schema_six_bundle_the_runner_wrote_is_accepted(
    tmp_path: Path, schema_six_bundle: Path
) -> None:
    """The live instrument's own output satisfies the contract it now enforces.

    Enforcement the production writer cannot satisfy would be a regression
    dressed as a hardening, so this is asserted over a bundle nothing edited.
    """

    rows, _ = pilot_metrics.load_real_pilot_records(
        [_fresh_bundle(tmp_path, schema_six_bundle)]
    )
    for row in rows:
        for attempt in row["provider_attempts"]:
            assert (
                provider_failure_attempt_violations(attempt, raw_schema_version=6) == []
            )


def test_the_identical_row_is_accepted_when_the_bundle_declares_schema_five(
    tmp_path: Path, schema_six_bundle: Path
) -> None:
    """A schema-5 row is NEVER read under schema-6 attempt semantics.

    The same bytes schema 6 refuses are accepted when the bundle declares schema
    5, because ``provider_failure_attempt_required_keys`` is empty below 6 and the
    new branch is never entered.  This is the property that keeps every frozen
    Phase-B..P artifact readable exactly as written: a later schema's contract is
    not retroactively imposed on rows whose instrument could not have satisfied
    it.
    """

    incomplete = {"outcome": "failure", "failure_class": "invalid_tool_call"}

    refused = _fresh_bundle(tmp_path / "as-six", schema_six_bundle)
    _rewrite_rows(refused, _append_attempt(incomplete))
    with pytest.raises(pilot_metrics.AnalysisError, match="raw schema 6"):
        pilot_metrics.load_real_pilot_records([refused])

    accepted = _fresh_bundle(tmp_path / "as-five", schema_six_bundle)
    _rewrite_rows(accepted, _append_attempt(incomplete))
    _set_raw_schema(accepted, FAILURE_EVENT_RAW_SCHEMA_VERSION)
    assert pilot_metrics.load_real_pilot_records([accepted])


@pytest.mark.parametrize("version", (2, 3, 4, 5))
def test_no_historical_schema_enters_the_new_branch_at_all(version: int) -> None:
    """Schemas 1-5 are excluded structurally, not by a hand-written exception.

    The reader selects the attempt contract from the same function the schema
    definition owns, and that function returns an EMPTY tuple below schema 6, so
    there is no schema 1-5 code path left to get wrong.
    """

    assert provider_failure_attempt_required_keys(version) == (), version
    for scalar in (None, 3, "x", True, []):
        assert (
            provider_failure_attempt_violations(
                {"outcome": "failure", "junk": scalar}, raw_schema_version=version
            )
            == []
        ), (version, scalar)
    assert provider_failure_attempt_required_keys(6) == (
        PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS
    )


def test_malformed_schema_six_telemetry_never_reaches_scientific_classification(
    tmp_path: Path, schema_six_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal happens BEFORE a row becomes a scientific observation.

    Ordering is the whole point of choosing this boundary: a bundle whose C3
    telemetry is corrupt must be rejected as instrument/evidence corruption, not
    classified first and questioned afterwards.  Proved by making classification
    itself fail loudly if it is ever reached.
    """

    def must_not_classify(row: Mapping[str, Any]) -> dict[str, Any]:
        raise AssertionError(
            "malformed schema-6 provider telemetry reached failure classification"
        )

    def must_not_validate(row: Mapping[str, Any], allow: bool) -> None:
        raise AssertionError(
            "malformed schema-6 provider telemetry reached _validate_failure"
        )

    monkeypatch.setattr(pilot_metrics, "_classified_failure_row", must_not_classify)
    monkeypatch.setattr(pilot_metrics, "_validate_failure", must_not_validate)

    source = _fresh_bundle(tmp_path, schema_six_bundle)
    _rewrite_rows(
        source,
        _append_attempt({"outcome": "failure", "failure_class": "invalid_tool_call"}),
    )
    with pytest.raises(pilot_metrics.AnalysisError, match="provider_attempts"):
        pilot_metrics.load_real_pilot_records([source])
    # analyze_real_pilot goes through the same loader, so it is closed too.
    with pytest.raises(pilot_metrics.AnalysisError, match="provider_attempts"):
        pilot_metrics.analyze_real_pilot([source], bootstrap_samples=10, seed=3)


def test_enforcement_introduced_no_second_validator() -> None:
    """The reader DELEGATES; it does not restate the contract.

    A second copy of the rule is the failure mode this repair exists to avoid, so
    the reader is required to call the schema definition's own functions and to
    name none of the contract's constants itself.
    """

    import inspect

    source = inspect.getsource(pilot_metrics._validate_pilot_manifest)
    assert "provider_failure_attempt_required_keys" in source
    assert "provider_failure_attempt_violations" in source
    for restated in (
        "PROVIDER_FAILURE_TELEMETRY_ATTEMPT_KEYS",
        "PROVIDER_ENVELOPE_PRESENCE_KEYS",
        "PROVIDER_ENVELOPE_PRESENCE_STATES",
        "envelope_field_presence",
        "failure_branch",
        "native_tool_call_state",
    ):
        assert restated not in source, restated
    # The schema version is never hard-coded: the contract is selected, not assumed.
    assert "== 6" not in source and ">= 6" not in source
