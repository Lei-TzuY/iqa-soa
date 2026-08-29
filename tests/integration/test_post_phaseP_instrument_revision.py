"""The POST_PHASEP_CONFIRMATORY approved instrument revision.

**NO MODEL IS RUN ANYWHERE IN THIS FILE**, nothing here contacts a provider or
opens a socket, and nothing here reads, enumerates or hashes anything beneath
``results/``.  Every assertion is against committed bytes, the working tree under
``src/iqa_soa``, or the deterministic writer.

The prospective post-Phase-P confirmatory randomization implementation (Work
Units 1-6) legitimately changed ``src/iqa_soa``, so the approved
instrument-revision chain -- which ended at Phase O -- gained a third link.  This
module proves the properties that make that link an ADDITIVE revision rather than
a rewrite:

1. the committed record is exactly reproducible from the current implementation
   tree by ``scripts/post_phaseP_write_instrument_revision.py``;
2. the chain is Phase M -> Phase O -> POST_PHASEP_CONFIRMATORY, with both custody
   links intact, and only the head asserted against the live tree;
3. neither predecessor record was edited, and no historical hash was updated in
   place;
4. the approved src change set is EXACTLY the eight reviewed paths, each with its
   real current SHA-256 and a substantive scientific reason;
5. no instrument, schema, adapter or contract version was invented;
6. the record's scientific status is prospective-only and retracts nothing;
7. the writer refuses an unexpected or missing src change set rather than
   widening the approved set, and performs no inference and no evidence access.
"""

from __future__ import annotations

import json
from pathlib import Path
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
import post_phaseP_write_instrument_revision as writer  # noqa: E402

RECORD_RELATIVE = "docs/post_phaseP_confirmatory_instrument_revision.json"
RECORD_PATH = PROJECT_ROOT / RECORD_RELATIVE

#: The merge-base the WU1-WU6 implementation branch diverged from, and therefore
#: the last commit at which Phase O was the approved head.
PARENT_COMMIT = "bc9d0a1234ab229d6433dbd4e54df1e17823806c"

#: The Phase-O head this link is additive to, and its own pinned tree.
PHASE_O_RECORD_RELATIVE = "docs/phaseO_instrument_revision.json"
PHASE_O_SRC_TREE = (
    "8d569696e51162acf8a0b8612f7d91398c7544cd0502cbaa59af92e35795b938"
)

#: The eight reviewed instrument paths.  Stated here independently of the writer
#: so a widened writer constant cannot quietly widen the approved set too.
APPROVED_SRC_FILES = (
    "src/iqa_soa/agent/__init__.py",
    "src/iqa_soa/agent/providers.py",
    "src/iqa_soa/experiment/confirmatory.py",
    "src/iqa_soa/experiment/confirmatory_assignment.py",
    "src/iqa_soa/experiment/confirmatory_eligibility.py",
    "src/iqa_soa/experiment/confirmatory_registration.py",
    "src/iqa_soa/experiment/runner.py",
    "src/iqa_soa/metrics/confirmatory.py",
)

#: A distinguishing phrase every reason must carry, so "the reason is long
#: enough" cannot be satisfied by eight interchangeable paragraphs.
REASON_MUST_MENTION: Mapping[str, tuple[str, ...]] = {
    "src/iqa_soa/agent/__init__.py": ("ProviderFailureOrigin", "export"),
    "src/iqa_soa/agent/providers.py": (
        "PROVIDER_INFRASTRUCTURE",
        "MODEL_OUTPUT",
        "WU5",
    ),
    "src/iqa_soa/experiment/confirmatory.py": (
        "Work Unit 5",
        "EXECUTION",
        "crash-safe",
    ),
    "src/iqa_soa/experiment/confirmatory_assignment.py": (
        "Work Unit 4",
        "assignment_manifest.json",
        "Monte-Carlo",
    ),
    "src/iqa_soa/experiment/confirmatory_eligibility.py": (
        "Stage-B",
        "eligibility",
        "BEFORE",
    ),
    "src/iqa_soa/experiment/confirmatory_registration.py": (
        "REGISTRATION_DRAFT",
        "self_digest",
        "FINAL_REGISTRATION_FROZEN",
    ),
    "src/iqa_soa/experiment/runner.py": (
        "run_one_position",
        "PRE_DISPATCH",
        "LEGACY",
    ),
    "src/iqa_soa/metrics/confirmatory.py": (
        "Work Unit 6",
        "analyze_confirmatory_randomization",
        "final_analysis_manifest.json",
    ),
}


@pytest.fixture(scope="module")
def record() -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    return parsed


def _blob(commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=PROJECT_ROOT, capture_output=True, check=True,
    ).stdout


# ==========================================================================
# 1. The committed record is exactly reproducible from the current tree
# ==========================================================================


def test_the_committed_record_is_exactly_reproducible() -> None:
    """Byte-for-byte, from the live implementation tree, with no hand editing.

    This is the property that makes the record reviewable: a reviewer re-runs the
    writer and compares. It also means no digest in it can have been pasted --
    including the new ``src_iqa_soa_tree``, which is recomputed here with the
    existing ``instrument_revision.tree_digest`` algorithm.
    """

    expected = json.dumps(writer.build_record(), indent=2, sort_keys=True) + "\n"
    assert RECORD_PATH.read_text(encoding="utf-8") == expected


def test_the_recorded_tree_is_the_live_tree_under_the_existing_algorithm(
    record: Mapping[str, Any],
) -> None:
    assert record["current_instrument"]["src_iqa_soa_tree"] == (
        instrument_revision.tree_digest("src/iqa_soa")
    )
    assert record["current_instrument"]["src_iqa_soa_tree"] != PHASE_O_SRC_TREE


# ==========================================================================
# 2. The chain, and both custody links
# ==========================================================================


def test_the_record_is_the_head_of_the_approved_chain(
    record: Mapping[str, Any],
) -> None:
    assert instrument_revision.check_instrument_provenance() == []
    chain = instrument_revision.load_revision_chain()
    assert [link["phase"] for link in chain] == ["M", "O", "POST_PHASEP_CONFIRMATORY"]
    assert instrument_revision.REVISION_PATH == instrument_revision.REVISION_CHAIN[-1]
    assert instrument_revision.REVISION_PATH == RECORD_PATH
    assert chain[-1] == record


def test_the_new_link_binds_the_existing_phase_o_head(
    record: Mapping[str, Any],
) -> None:
    """Its parent digest is the Phase-O head's own pin, not a recomputation."""

    phase_o = json.loads(
        (PROJECT_ROOT / PHASE_O_RECORD_RELATIVE).read_text(encoding="utf-8")
    )
    previous = record["previous_instrument"]
    assert previous["record"] == PHASE_O_RECORD_RELATIVE
    assert previous["phase"] == "O"
    assert previous["src_iqa_soa_tree"] == (
        phase_o["current_instrument"]["src_iqa_soa_tree"]
    )
    assert previous["src_iqa_soa_tree"] == PHASE_O_SRC_TREE
    # And the Phase-O head is what the parent commit actually contains.
    assert instrument_revision.tree_digest_at_commit(
        PARENT_COMMIT, "src/iqa_soa"
    ) == PHASE_O_SRC_TREE
    assert record["parent_commit"] == PARENT_COMMIT
    assert record["additive_to"] == PHASE_O_RECORD_RELATIVE
    # Every version the predecessor carried is carried forward faithfully.
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        assert previous[key] == phase_o["current_instrument"][key], key


# ==========================================================================
# 3. Nothing historical was rewritten
# ==========================================================================


@pytest.mark.parametrize(
    "relative",
    ["docs/phaseM_instrument_revision.json", PHASE_O_RECORD_RELATIVE],
)
def test_no_predecessor_revision_record_was_edited(relative: str) -> None:
    """A successor that permitted its predecessor to be edited proves nothing."""

    assert (PROJECT_ROOT / relative).read_bytes() == _blob(PARENT_COMMIT, relative)


def test_no_benchmark_freeze_record_was_edited() -> None:
    for relative in (
        "benchmark/pilot-v7-rc3/freeze-record.json",
        "benchmark/pilot-v7-rc4/freeze-record.json",
        "benchmark/pilot-v7-rc4/qualification-contract.json",
        "docs/phaseL_frozen_execution_inputs.json",
        "docs/phaseP_frozen_execution_inputs.json",
    ):
        assert (PROJECT_ROOT / relative).read_bytes() == _blob(
            PARENT_COMMIT, relative
        ), relative


def test_the_phase_k_freeze_assertion_is_still_provable() -> None:
    """The oldest pin is preserved, not overwritten, and still holds at its commit."""

    assert instrument_revision.check_historical_freeze_assertion() == []


# ==========================================================================
# 4. Exactly the approved src change set, hashed and reasoned
# ==========================================================================


def test_the_approved_set_is_exactly_the_observed_src_change_set(
    record: Mapping[str, Any],
) -> None:
    observed = subprocess.run(
        ["git", "diff", "--name-only", PARENT_COMMIT, "--", "src/iqa_soa"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert sorted(observed) == list(APPROVED_SRC_FILES)
    assert sorted(record["changed_files"]) == list(APPROVED_SRC_FILES)
    assert tuple(writer.APPROVED_SRC_FILES) == APPROVED_SRC_FILES


def test_every_approved_file_carries_its_real_hash_and_a_real_reason(
    record: Mapping[str, Any],
) -> None:
    changed = record["changed_files"]
    for name in APPROVED_SRC_FILES:
        entry = changed[name]
        assert entry["sha256"] == instrument_revision.sha256_of(
            PROJECT_ROOT / name
        ), name
        reason = entry["reason"]
        assert len(reason.strip()) >= 20, name
        assert reason.strip().casefold() not in {"updated code", "code change"}, name
    # The reasons are eight DISTINCT statements, not one boilerplate paragraph.
    assert len({entry["reason"] for entry in changed.values()}) == len(changed)


@pytest.mark.parametrize("name", APPROVED_SRC_FILES)
def test_each_reason_states_that_file_s_own_prospective_purpose(
    record: Mapping[str, Any], name: str
) -> None:
    reason = record["changed_files"][name]["reason"]
    for token in REASON_MUST_MENTION[name]:
        assert token in reason, (name, token)


def test_the_two_edited_legacy_modules_declare_that_legacy_behaviour_is_preserved(
    record: Mapping[str, Any],
) -> None:
    """The provider and runner edits are additive, and the record says exactly how."""

    providers = record["changed_files"]["src/iqa_soa/agent/providers.py"]["reason"]
    assert "PRESERVED" in providers
    assert "no committed row is reclassified" in providers
    runner = record["changed_files"]["src/iqa_soa/experiment/runner.py"]["reason"]
    assert "ExperimentRunner.run SEMANTICS ARE UNCHANGED" in runner


# ==========================================================================
# 5. No version was invented
# ==========================================================================


def test_the_recorded_versions_are_the_versions_the_code_declares(
    record: Mapping[str, Any],
) -> None:
    from iqa_soa.instrument import (
        INSTRUMENT_VERSION,
        NATIVE_TOOL_ADAPTER_VERSION,
        RAW_SCHEMA_VERSION,
    )
    from iqa_soa.tools.argument_schema import TOOL_ARGUMENT_CONTRACT_VERSION

    current = record["current_instrument"]
    assert current["instrument_version"] == INSTRUMENT_VERSION
    assert current["raw_schema_version"] == RAW_SCHEMA_VERSION
    assert current["native_tool_adapter_version"] == NATIVE_TOOL_ADAPTER_VERSION
    assert current["tool_argument_contract_version"] == TOOL_ARGUMENT_CONTRACT_VERSION


def test_no_boundary_constant_moved_merely_because_the_tree_changed(
    record: Mapping[str, Any],
) -> None:
    """The WU1-WU6 work preserved legacy semantics, so no boundary is bumped.

    Bumping one here would assert an incomparability that does not exist and
    would retroactively invalidate the committed Phase-P artifacts, which are
    written under instrument 4 / raw schema 5.
    """

    previous = record["previous_instrument"]
    current = record["current_instrument"]
    for key in (
        "instrument_version",
        "raw_schema_version",
        "native_tool_adapter_version",
        "tool_argument_contract_version",
    ):
        assert current[key] == previous[key], key
    assert current["instrument_version"] == "4"
    assert current["raw_schema_version"] == 5
    assert current["adapter_unchanged" ] is True
    # The code constants are NOT edited by this repair.
    for relative in ("src/iqa_soa/instrument.py", "src/iqa_soa/tools/argument_schema.py"):
        assert (PROJECT_ROOT / relative).read_bytes() == _blob(
            PARENT_COMMIT, relative
        ), relative


# ==========================================================================
# 6. Scientific status: prospective only, retracting nothing
# ==========================================================================


def test_the_record_states_a_prospective_implementation_only(
    record: Mapping[str, Any],
) -> None:
    assert record["phase"] == "POST_PHASEP_CONFIRMATORY"
    assert record["record_kind"] == "instrument_revision"
    assert record["model_inference_performed"] is False
    assert record["phase_p_execution_rerun"] is False
    assert record["phase_p_result_reinterpreted"] is False
    assert record["historical_rows_rescored"] is False
    assert record["benchmark_freeze_records_overwritten"] is False
    assert record["instrument_revisions_overwritten"] is False
    assert record["authorizes_confirmatory_execution"] is False
    assert record["post_phaseP_confirmatory_execution_authorized"] is False
    statement = record["prospective_implementation_only"]
    for clause in (
        "PROSPECTIVE",
        "No Phase-P execution is rerun",
        "No benchmark freeze record is overwritten",
        "No existing instrument revision is overwritten",
        "authorizes no real confirmatory execution",
    ):
        assert clause in statement, clause


def test_the_historical_phase_p_verdict_is_carried_forward_unchanged(
    record: Mapping[str, Any],
) -> None:
    hold = record["phase_p_rc4_hold"]
    assert hold["benchmark_version"] == "pilot-v7-rc4"
    assert hold["qualification_status"] == "UNQUALIFIED"
    assert hold["verdict"] == "HOLD"
    assert hold["terminal_status"] == "SCHEDULE_COMPLETE_VERDICT_HOLD"
    assert hold["phase_p_cells_rerun"] == 0
    assert hold["phase_p_rows_rescored"] == 0
    # And it agrees with the committed forensic ledger rather than restating it.
    diagnosis = json.loads(
        (PROJECT_ROOT / hold["diagnosis_record"]).read_text(encoding="utf-8")
    )
    assert diagnosis["official_verdict"] == hold["verdict"]
    assert diagnosis["terminal_status"] == hold["terminal_status"]


def test_work_unit_authorization_stays_with_the_frozen_lifecycle(
    record: Mapping[str, Any],
) -> None:
    authorization = record["confirmatory_lifecycle_authorization"]
    governed_by = authorization["governed_by"]
    assert governed_by, "a revision that names no governing authority governs itself"
    for relative in governed_by:
        assert (PROJECT_ROOT / relative).is_file(), relative
    assert "grants no execution" in authorization["note"]


# ==========================================================================
# 7. The writer refuses, and reaches nothing it must not
# ==========================================================================


def test_the_writer_refuses_an_unexpected_src_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drive-by edit is refused, not absorbed into the approved set."""

    monkeypatch.setattr(
        writer.ir,
        "_changed_files_since",
        lambda _commit, _root: [*APPROVED_SRC_FILES, "src/iqa_soa/instrument.py"],
    )
    with pytest.raises(SystemExit) as excinfo:
        writer.build_record()
    assert "src/iqa_soa/instrument.py" in str(excinfo.value)


def test_the_writer_refuses_a_missing_approved_src_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An approved file that did not actually change is refused too."""

    monkeypatch.setattr(
        writer.ir,
        "_changed_files_since",
        lambda _commit, _root: list(APPROVED_SRC_FILES[:-1]),
    )
    with pytest.raises(SystemExit) as excinfo:
        writer.build_record()
    assert APPROVED_SRC_FILES[-1] in str(excinfo.value)


def test_the_writer_refuses_a_predecessor_whose_tree_is_not_the_parent_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken chain of custody refuses rather than being papered over."""

    monkeypatch.setattr(
        writer.ir, "tree_digest_at_commit", lambda _commit, _root: "0" * 64
    )
    with pytest.raises(SystemExit) as excinfo:
        writer.build_record()
    assert "chain of custody" in str(excinfo.value)


def test_the_writer_performs_no_inference_and_no_evidence_access() -> None:
    """It reads git, ``src/iqa_soa``, ``benchmark/`` and ``configs/`` -- nothing else.

    In particular it never names, opens, enumerates or hashes the official
    Phase-P evidence root. The only place that path appears is the record's own
    statement that it was not touched.
    """

    import ast

    path = SCRIPTS_ROOT / "post_phaseP_write_instrument_revision.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for forbidden in (
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "openai",
        "ollama",
    ):
        assert forbidden not in imported, forbidden

    # The evidence root may be NAMED in prose, and must never be REACHED. No
    # string literal in this module composes a path into ``results/``.
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
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    assert named[0] in record["phase_p_evidence_untouched"] or (
        "results/phaseP-rc4-qualification" in record["phase_p_evidence_untouched"]
    )
    assert "not read, enumerated, traversed, hashed" in (
        record["phase_p_evidence_untouched"]
    )


def test_the_writer_never_rewrites_an_older_revision_file() -> None:
    """Its default output is the chain HEAD, which is this record and no other."""

    import argparse
    import inspect

    assert writer.PREDECESSOR_RECORD_RELATIVE == PHASE_O_RECORD_RELATIVE
    source = inspect.getsource(writer.main)
    assert "ir.REVISION_CHAIN[-1]" in source
    assert isinstance(argparse.ArgumentParser(), argparse.ArgumentParser)
    assert instrument_revision.REVISION_CHAIN[-1] == RECORD_PATH
