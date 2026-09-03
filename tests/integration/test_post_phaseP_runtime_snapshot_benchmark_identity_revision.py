"""The FIFTH instrument-revision link: benchmark-identity capture correction.

This link admits the repair of a frozen WU5 capture rule that was
unsatisfiable against every production configuration:
``benchmark_sha256 = file_sha256(config.benchmark_path)`` where
``benchmark_path`` is a benchmark SOURCE ROOT and production configs point it at
a directory.

Unlike the C3 link, this one moves NO version constant, and unlike the C3 link it
inherits NO custody defect.  Both are asserted here rather than assumed, and each
way of tampering with the record is exercised so the chain fails closed.

Nothing here contacts a provider, performs inference, or reads anything under
``results/phaseP-rc4-qualification/``.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision  # noqa: E402
import post_phaseP_write_runtime_snapshot_benchmark_identity_revision as writer  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import TOOL_ARGUMENT_CONTRACT_VERSION  # noqa: E402

RECORD_RELATIVE = (
    "docs/post_phaseP_runtime_snapshot_benchmark_identity_instrument_revision.json"
)
RECORD_PATH = PROJECT_ROOT / RECORD_RELATIVE
PARENT_COMMIT = "a24d8924e7bd3e42c07530aab074236db7478447"
PHASE = "POST_PHASEP_RUNTIME_SNAPSHOT_BENCHMARK_IDENTITY"
APPROVED_SRC_FILES = (
    "src/iqa_soa/experiment/confirmatory.py",
    "src/iqa_soa/experiment/runner.py",
)


@pytest.fixture(scope="module")
def record() -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    return parsed


def _blob(commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=PROJECT_ROOT, capture_output=True, check=True,
    ).stdout


def _tampered(record: Mapping[str, Any], mutate: Any) -> list[str]:
    """Run the REAL validator over a chain whose head has been tampered with."""

    chain = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in instrument_revision.REVISION_CHAIN
    ]
    head = deepcopy(dict(record))
    mutate(head)
    chain[-1] = head
    original = instrument_revision.load_revision_chain
    instrument_revision.load_revision_chain = lambda: chain  # type: ignore[assignment]
    try:
        return instrument_revision.check_approved_instrument_revision()
    finally:
        instrument_revision.load_revision_chain = original  # type: ignore[assignment]


# --------------------------------------------------------------------------
# The chain is green, and the record is reproducible rather than pasted
# --------------------------------------------------------------------------


def test_the_chain_is_five_links_and_validates_clean() -> None:
    chain = instrument_revision.load_revision_chain()
    assert [link["phase"] for link in chain] == [
        "M",
        "O",
        "POST_PHASEP_CONFIRMATORY",
        "POST_PHASEP_PROVIDER_OBSERVABILITY",
        PHASE,
    ]
    assert len(instrument_revision.REVISION_CHAIN) == 5
    assert instrument_revision.REVISION_PATH == RECORD_PATH
    assert instrument_revision.check_approved_instrument_revision() == []
    assert instrument_revision.check_instrument_provenance() == []


def test_the_record_is_exactly_reproducible_from_the_live_tree() -> None:
    """A reviewer re-runs the writer and compares; no digest is pasted."""

    expected = json.dumps(writer.build_record(), indent=2, sort_keys=True) + "\n"
    assert RECORD_PATH.read_text(encoding="utf-8") == expected


def test_the_record_is_the_head_and_binds_the_live_tree(
    record: Mapping[str, Any],
) -> None:
    assert record["parent_commit"] == PARENT_COMMIT
    assert record["current_instrument"]["src_iqa_soa_tree"] == (
        instrument_revision.tree_digest("src/iqa_soa")
    )
    assert record["additive_to"] == writer.PREDECESSOR_RECORD_RELATIVE


def test_this_link_inherits_no_custody_defect(record: Mapping[str, Any]) -> None:
    """The predecessor's own declared pin reproduces from committed bytes."""

    predecessor = json.loads(
        (PROJECT_ROOT / writer.PREDECESSOR_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    committed = instrument_revision.tree_digest_at_commit(PARENT_COMMIT, "src/iqa_soa")
    declared = predecessor["current_instrument"]["src_iqa_soa_tree"]
    assert declared == committed
    assert record["previous_instrument"]["src_iqa_soa_tree"] == committed
    custody = record["predecessor_custody"]
    assert custody["predecessor_declared_pin_is_reproducible_from_history"] is True
    assert custody["custody_correction_required"] is False
    assert custody["corrected_record_edited_by_this_revision"] is False


# --------------------------------------------------------------------------
# The approved change set is exact, hashed, and individually reasoned
# --------------------------------------------------------------------------


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
        assert entry["sha256"] == instrument_revision.sha256_of(PROJECT_ROOT / name)
        assert len(entry["reason"].strip()) >= 20, name
    assert len({entry["reason"] for entry in changed.values()}) == len(changed)


def test_the_runner_reason_states_the_change_is_additive_only(
    record: Mapping[str, Any],
) -> None:
    """runner.py must be described as what it is: no algorithm change."""

    reason = record["changed_files"]["src/iqa_soa/experiment/runner.py"]["reason"]
    assert "PURELY ADDITIVE" in reason
    assert "_path_digest is not edited" in reason
    assert "ExperimentRunner is not edited" in reason
    hunks = subprocess.run(
        ["git", "diff", "-U0", PARENT_COMMIT, "--", "src/iqa_soa/experiment/runner.py"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.splitlines()
    removed = [
        line for line in hunks if line.startswith("-") and not line.startswith("---")
    ]
    assert removed == [], f"runner.py is not purely additive: {removed}"


def test_the_confirmatory_reason_names_the_one_corrected_derivation(
    record: Mapping[str, Any],
) -> None:
    reason = record["changed_files"]["src/iqa_soa/experiment/confirmatory.py"]["reason"]
    assert "benchmark_sha256" in reason
    assert "_file_sha256" in reason
    hunks = subprocess.run(
        [
            "git", "diff", "-U0", PARENT_COMMIT, "--",
            "src/iqa_soa/experiment/confirmatory.py",
        ],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.splitlines()
    removed = [
        line for line in hunks if line.startswith("-") and not line.startswith("---")
    ]
    assert len(removed) == 1, removed
    assert "benchmark_sha256" in removed[0]


# --------------------------------------------------------------------------
# No boundary moved, and the reason it did not is recorded
# --------------------------------------------------------------------------


def test_no_version_constant_moved(record: Mapping[str, Any]) -> None:
    current = record["current_instrument"]
    previous = record["previous_instrument"]
    assert current["instrument_version"] == INSTRUMENT_VERSION == "5"
    assert current["raw_schema_version"] == RAW_SCHEMA_VERSION == 6
    assert current["native_tool_adapter_version"] == NATIVE_TOOL_ADAPTER_VERSION
    assert current["tool_argument_contract_version"] == TOOL_ARGUMENT_CONTRACT_VERSION
    # Unlike the C3 link, EVERY constant is held across this boundary.
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        assert previous[key] == current[key], key
    assert "instrument_versions_unchanged" in record
    assert "instrument_versions_moved" not in record


def test_untouched_subtrees_prove_the_unchanged_boundary_claims() -> None:
    """The record's boundary claims are checkable from the diff, not asserted."""

    observed = subprocess.run(
        ["git", "diff", "--name-only", PARENT_COMMIT, "--", "src/iqa_soa"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    for prefix in (
        "src/iqa_soa/agent/",
        "src/iqa_soa/tools/",
        "src/iqa_soa/iqa/",
        "src/iqa_soa/metrics/",
    ):
        assert not [n for n in observed if n.startswith(prefix)], prefix
    assert "src/iqa_soa/instrument.py" not in observed


def test_the_record_declares_observation_only_and_a_no_new_boundary(
    record: Mapping[str, Any],
) -> None:
    assert record["record_kind"] == "instrument_revision"
    assert record["observation_only"] is True
    assert "NO NEW BOUNDARY IS DECLARED" in record["instrument_boundary_declaration"]
    for flag in (
        "model_inference_performed",
        "provider_contacted",
        "phase_p_execution_rerun",
        "phase_p_result_reinterpreted",
        "historical_rows_rescored",
        "benchmark_freeze_records_overwritten",
        "instrument_revisions_overwritten",
        "authorizes_qualification_execution",
        "authorizes_confirmatory_execution",
        "production_randomization_realized",
        "successor_candidate_created",
        "ben_003_rehabilitated",
    ):
        assert record[flag] is False, flag


def test_the_pooling_statement_records_an_unrealized_population(
    record: Mapping[str, Any],
) -> None:
    """No old-vs-new successor population exists, because the old rule made none."""

    assert record["successor_qualification_inference_before_repair"] == 0
    assert record["confirmatory_executions_before_repair"] == 0
    assert record["successor_runtime_snapshots_before_repair"] == 0
    assert record["successor_result_rows_before_repair"] == 0
    assert record["phase_p_rows_rerun"] == 0
    assert record["phase_p_rows_rescored"] == 0
    assert "structurally incapable" in record["realized_measurement_population"]


def test_the_phase_p_hold_is_preserved_verbatim(record: Mapping[str, Any]) -> None:
    hold = record["phase_p_rc4_hold"]
    assert hold["qualification_status"] == "UNQUALIFIED"
    assert hold["verdict"] == "HOLD"
    assert hold["terminal_status"] == "SCHEDULE_COMPLETE_VERDICT_HOLD"
    assert hold["phase_p_cells_rerun"] == 0
    assert hold["phase_p_rows_rescored"] == 0
    assert "BEN-003 remains historical and unrepaired" in hold["note"]


def test_scientific_invariants_are_recomputed_and_unmoved(
    record: Mapping[str, Any],
) -> None:
    invariants = record["scientific_invariants"]
    assert invariants["benchmark_case_bytes_digest"] == (
        "76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea"
    )
    assert invariants["canonical_exposure_digest"] == (
        "23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092"
    )
    assert invariants["recomputed_not_copied"] is True
    assert invariants["benchmark_bytes_changed_by_this_revision"] == 0
    assert writer.scientific_invariants() == invariants


def test_no_benchmark_byte_changed_since_the_parent_commit() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", PARENT_COMMIT, "--", "benchmark"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert changed == []


# --------------------------------------------------------------------------
# Tampering: every one of these must be caught
# --------------------------------------------------------------------------


def test_a_tampered_parent_commit_is_caught(record: Mapping[str, Any]) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["parent_commit"] = "0" * 40

    assert _tampered(record, mutate) != []


def test_a_tampered_predecessor_digest_is_caught(record: Mapping[str, Any]) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["previous_instrument"]["src_iqa_soa_tree"] = "b" * 64

    failures = _tampered(record, mutate)
    assert any("chain of custody is broken" in f for f in failures)


def test_a_tampered_current_tree_is_caught(record: Mapping[str, Any]) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["current_instrument"]["src_iqa_soa_tree"] = "c" * 64

    failures = _tampered(record, mutate)
    assert any("is not the approved revision" in f for f in failures)


def test_a_narrowed_changed_file_set_is_caught(record: Mapping[str, Any]) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["changed_files"].pop("src/iqa_soa/experiment/runner.py")

    failures = _tampered(record, mutate)
    assert any("is not in the approved instrument revision" in f for f in failures)


def test_a_widened_changed_file_set_is_caught(record: Mapping[str, Any]) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["changed_files"]["src/iqa_soa/instrument.py"] = {
            "sha256": "d" * 64,
            "reason": "a fabricated reason long enough to pass the length floor",
        }

    failures = _tampered(record, mutate)
    assert any("did not actually change" in f for f in failures)


def test_a_tampered_per_file_digest_is_caught(record: Mapping[str, Any]) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["changed_files"]["src/iqa_soa/experiment/confirmatory.py"]["sha256"] = (
            "e" * 64
        )

    failures = _tampered(record, mutate)
    assert any("hashes to" in f for f in failures)


def test_an_omitted_scientific_reason_is_caught(record: Mapping[str, Any]) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["changed_files"]["src/iqa_soa/experiment/runner.py"]["reason"] = "too short"

    failures = _tampered(record, mutate)
    assert any("records no scientific reason" in f for f in failures)


@pytest.mark.parametrize(
    ("key", "value"),
    [("instrument_version", "6"), ("raw_schema_version", 7)],
)
def test_a_tampered_version_constant_is_caught(
    record: Mapping[str, Any], key: str, value: Any
) -> None:
    def mutate(head: dict[str, Any]) -> None:
        head["current_instrument"][key] = value

    failures = _tampered(record, mutate)
    assert any("but the code declares" in f for f in failures)


# --------------------------------------------------------------------------
# The writer refuses rather than widening
# --------------------------------------------------------------------------


def test_the_writer_refuses_an_unreasoned_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reduced = dict(writer.REASONS)
    reduced.pop("src/iqa_soa/experiment/runner.py")
    monkeypatch.setattr(writer, "REASONS", reduced)
    with pytest.raises(SystemExit, match="needs a scientific reason"):
        writer.approved_changed_files()


def test_the_writer_refuses_a_reason_for_an_unchanged_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    widened = dict(writer.REASONS)
    widened["src/iqa_soa/instrument.py"] = "a reason for a file that did not change"
    monkeypatch.setattr(writer, "REASONS", widened)
    with pytest.raises(SystemExit, match="did not change"):
        writer.approved_changed_files()


def test_the_writer_refuses_an_approved_set_that_is_not_the_observed_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        writer, "APPROVED_SRC_FILES", ("src/iqa_soa/experiment/runner.py",)
    )
    with pytest.raises(SystemExit, match="not the approved set"):
        writer.approved_changed_files()


def test_the_writer_refuses_an_unprovable_predecessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(writer, "PARENT_COMMIT", writer.PARENT_COMMIT + "")
    monkeypatch.setattr(
        instrument_revision, "tree_digest_at_commit", lambda *a, **k: "f" * 64
    )
    with pytest.raises(SystemExit, match="chain of custody is broken"):
        writer.predecessor_custody()


def test_the_writer_refuses_a_moved_scientific_invariant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(writer, "BENCHMARK_CASE_BYTES_DIGEST", "0" * 64)
    with pytest.raises(SystemExit, match="benchmark case-byte digest"):
        writer.scientific_invariants()


# --------------------------------------------------------------------------
# Nothing historical was edited
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "docs/phaseM_instrument_revision.json",
        "docs/phaseO_instrument_revision.json",
        "docs/post_phaseP_confirmatory_instrument_revision.json",
        "docs/post_phaseP_confirmatory_instrument_revision_correction.json",
        "docs/post_phaseP_provider_observability_instrument_revision.json",
        "benchmark/pilot-v7-rc3/freeze-record.json",
        "benchmark/pilot-v7-rc4/freeze-record.json",
        "benchmark/pilot-v7-rc4/qualification-contract.json",
        "benchmark/pilot-v7-rc4/manifest.json",
        "docs/phaseL_frozen_execution_inputs.json",
        "docs/phaseP_frozen_execution_inputs.json",
        "scripts/phaseP_protocol.py",
        "scripts/phaseL_protocol.py",
    ],
)
def test_no_predecessor_or_frozen_record_was_edited(relative: str) -> None:
    """Predecessors and frozen protocols are preserved byte-for-byte.

    ``scripts/phaseP_protocol.py`` and ``scripts/phaseL_protocol.py`` are in this
    list deliberately.  Their literal pins do not match the live tree, and that
    is the correct and intended behaviour -- it is the mechanism that binds a
    future successor to the post-repair instrument only.  Repairing them would be
    exactly the wrong move, and this test proves they were not.
    """

    assert (PROJECT_ROOT / relative).read_bytes() == _blob(PARENT_COMMIT, relative)


def test_the_writer_reaches_no_phase_p_evidence() -> None:
    import ast

    path = (
        PROJECT_ROOT
        / "scripts"
        / "post_phaseP_write_runtime_snapshot_benchmark_identity_revision.py"
    )
    source = path.read_text(encoding="utf-8")
    # The ONLY results/ path the module mentions is the forbidden namespace, and
    # it appears exactly twice: in the module docstring saying it is not read,
    # and in the record field saying it is untouched.  Never anywhere else.
    assert source.count("results/") == 2
    assert source.count("results/phaseP-rc4-qualification/") == 2

    # And neither occurrence is a path this module builds or opens: every string
    # literal naming it is prose, not an argument to Path()/open().
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name not in {"Path", "open", "read_text", "read_bytes", "rglob", "iterdir"}:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                assert "results/" not in arg.value, ast.dump(node)

    assert "results/phaseP-rc4-qualification/" in (
        json.loads(RECORD_PATH.read_text(encoding="utf-8"))["phase_p_evidence_untouched"]
    )
