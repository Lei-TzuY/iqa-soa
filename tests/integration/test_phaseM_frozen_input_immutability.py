"""Phase M.1: prospectively frozen scientific inputs are byte-immutable.

WHAT WENT WRONG
===============

Phase M needed frozen Phase-D/F/I evidence to stay analyzable after the
instrument moved to version "3" / raw schema 4, and achieved it by editing the
historical analyzers so they pinned the version their phase actually ran under.
For most of those files that was legitimate.  For one it was not:

    results/phaseI-rc2-requalification/phaseI-provenance.json
      bound_inputs["scripts/analyze_phaseI_requalification.py"]
        = 2ec5e5f40618e27400a534465d380be0092fb0b0cd1bd013aac562f99f80798e

Phase I bound that file's bytes by SHA-256 *before* reading its result.  That
makes the analyzer a prospectively frozen scientific input rather than a mutable
convenience reader, and editing it in the current tree retracts the freeze --
git preserving the old bytes is not authorization, it is only a record.

Nothing failed when it happened.  Every existing immutability gate covered
``benchmark``, ``results``, ``configs/policies`` and ``docs``; none covered
``scripts``, even though a ``scripts`` path was bound by a committed provenance
record.

WHAT THIS MODULE ASSERTS
========================

The hashes here are read from committed provenance, not from anything Phase M
wrote, so a future phase's ``bound_inputs`` block is covered the moment it is
committed.  One hash is additionally hard-coded: an audit whose expectations all
come from the file it audits can be satisfied by editing that file, so the
specific binding the review identified is pinned independently, in this module,
where changing it is a visible edit to a test.

Every test is offline.  NO MODEL IS RUN.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision  # noqa: E402
import phaseM_frozen_input_audit as audit  # noqa: E402
import phaseM_historical_analysis as compat  # noqa: E402

#: The binding the adversarial review named.  Hard-coded on purpose: this value
#: does not come from ``phaseI-provenance.json``, so it still fails if that
#: record is ever rewritten to describe whatever the analyzer now contains.
PHASE_I_ANALYZER = "scripts/analyze_phaseI_requalification.py"
PHASE_I_ANALYZER_FROZEN_SHA256 = (
    "2ec5e5f40618e27400a534465d380be0092fb0b0cd1bd013aac562f99f80798e"
)
PHASE_I_PROVENANCE = "results/phaseI-rc2-requalification/phaseI-provenance.json"

#: Everything Phase M is permitted to MODIFY (as opposed to add) relative to its
#: parent commit.  Pinning the whole mutation surface is what turns "we did not
#: touch a frozen file" from a claim into a check: a new entry here is a visible
#: edit to a test, and an unlisted modification fails immediately.
#:
#: The two Phase-D scripts are on this list because they carry NO freeze
#: contract -- no provenance binds them and no committed test pins their bytes --
#: which ``test_the_modified_historical_scripts_carry_no_freeze_contract`` proves
#: from committed records rather than asserting.
PHASE_M_MODIFIED_PATHS = frozenset(
    {
        "scripts/analyze_phaseD_qualification.py",
        "scripts/phaseD_preflight.py",
        "scripts/phaseL_fault_provenance_reachability_probe.py",
        "scripts/validate_pilot_v7_rc3.py",
        "src/iqa_soa/experiment/runner.py",
        "src/iqa_soa/instrument.py",
        "src/iqa_soa/metrics/definitions.py",
        "src/iqa_soa/metrics/pilot.py",
        "tests/benchmark/test_pilot_v7_rc2_construct.py",
        "tests/integration/test_phaseF_qualification.py",
        "tests/integration/test_phaseI_requalification.py",
        "tests/integration/test_phaseL_requalification.py",
        "tests/integration/test_real_pilot_runner.py",
    }
)

_GIT = subprocess.run(
    ["git", "--version"], capture_output=True, check=False
).returncode == 0
requires_git = pytest.mark.skipif(not _GIT, reason="git executable not available")


def _sha256(relative: str) -> str:
    return hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
    ).stdout


# ==========================================================================
# 1. The specific binding the review identified
# ==========================================================================


def test_the_phase_i_analyzer_still_hashes_to_its_frozen_sha256() -> None:
    """The blocker, asserted independently of every record it appears in."""

    assert _sha256(PHASE_I_ANALYZER) == PHASE_I_ANALYZER_FROZEN_SHA256


def test_the_phase_i_provenance_still_records_that_hash() -> None:
    """And the record still says so, so the two cannot be reconciled by edit."""

    payload = json.loads(
        (PROJECT_ROOT / PHASE_I_PROVENANCE).read_text(encoding="utf-8")
    )
    assert payload["bound_inputs"][PHASE_I_ANALYZER] == PHASE_I_ANALYZER_FROZEN_SHA256


# ==========================================================================
# 2. Every frozen bound input, derived from committed provenance
# ==========================================================================


def test_every_bound_input_matches_the_current_working_tree() -> None:
    """Read from provenance, so a phase written after this test is covered too."""

    assert audit.check_frozen_bound_inputs() == []


def test_the_audit_still_covers_the_bindings_it_is_supposed_to() -> None:
    """An audit that discovers nothing passes vacuously; this closes that."""

    assert audit.check_required_coverage() == []
    frozen = [
        binding
        for binding in audit.discover_bindings()
        if binding.contract_kind == "FROZEN_BOUND_INPUT"
    ]
    assert len(frozen) >= 12
    assert any(binding.path == PHASE_I_ANALYZER for binding in frozen)


def test_no_binding_that_held_when_phase_m_began_is_broken_now() -> None:
    """The decisive predicate, and the one the first Phase-M revision failed.

    It inherits no historical debt: a binding that had already diverged at the
    parent commit is not Phase M's regression and is not counted against it.
    """

    assert audit.check_no_regression_since_phase_m_parent() == []


def test_recorded_hashes_still_hold_at_the_commit_that_recorded_them() -> None:
    """History was not rewritten to make a current mismatch look like a match."""

    assert audit.check_history_not_rewritten() == []


def test_every_sha256_sidecar_still_verifies() -> None:
    sidecar_failures = [
        failure
        for failure in audit.check_frozen_bound_inputs()
        if "sidecar" in failure or ".sha256" in failure
    ]
    assert sidecar_failures == []


def test_the_full_audit_passes() -> None:
    assert audit.audit() == []
    assert audit.summary()["verdict"] == "PASS"
    assert audit.summary()["model_inference_performed"] is False


# ==========================================================================
# 3. Phase M's mutation surface is pinned, not described
# ==========================================================================


@requires_git
def test_phase_m_modifies_exactly_the_declared_set_and_nothing_else() -> None:
    """No file is edited, deleted, renamed or retyped outside the declared set.

    This is the check whose absence let the Phase-I analyzer be edited silently.
    Additions are unconstrained -- Phase M is additive work -- but every mutation
    is enumerated above and reviewable in one place.
    """

    modified = {
        line
        for line in _git(
            "diff", "--name-only", "--diff-filter=MDRT",
            audit.PHASE_M_PARENT_COMMIT, "--",
        ).splitlines()
        if line.strip()
    }
    assert modified == PHASE_M_MODIFIED_PATHS, {
        "unexpectedly modified": sorted(modified - PHASE_M_MODIFIED_PATHS),
        "declared but unmodified": sorted(PHASE_M_MODIFIED_PATHS - modified),
    }


@requires_git
def test_no_frozen_historical_script_is_modified_by_phase_m() -> None:
    """The three restored scripts equal their freeze commits AND their provenance."""

    for spec in compat.FROZEN_ANALYSES:
        assert compat.check_frozen_script_bytes(spec) == [], spec.name


def test_the_modified_historical_scripts_carry_no_freeze_contract() -> None:
    """Phase D's analyzer and preflight ARE modified; this proves they may be.

    The distinction is not a judgement call and is not taken on trust.  A file
    may be modified only if NO committed provenance binds its bytes and NO
    ``.sha256`` sidecar covers it.  If a later phase ever binds one of them, this
    test fails and the modification must be undone.
    """

    bound = {binding.path for binding in audit.discover_bindings()}
    for name in ("scripts/analyze_phaseD_qualification.py", "scripts/phaseD_preflight.py"):
        assert name in PHASE_M_MODIFIED_PATHS
        assert name not in bound, f"{name} is bound by provenance and may not be edited"


@requires_git
def test_the_phase_i_protected_path_list_still_protects_the_analyzers() -> None:
    """A protected path may not be removed to permit editing what it protects.

    The first Phase-M revision dropped ``analyze_phaseF_qualification.py`` and
    ``validate_pilot_v7_rc2.py`` from Phase I's live protected set and
    reclassified them as mutable "frozen evidence readers".  A statement about
    what Phase I did historically is useful, but it does not replace a live
    byte-identity contract, and this fails if either is dropped again.
    """

    source = (
        PROJECT_ROOT / "tests" / "integration" / "test_phaseI_requalification.py"
    ).read_text(encoding="utf-8")
    for protected in (
        '"scripts/analyze_phaseF_qualification.py"',
        '"scripts/validate_pilot_v7_rc2.py"',
        '"scripts/validate_pilot_v7_rc1.py"',
        '"scripts/run_phaseF_qualification.py"',
    ):
        assert protected in source, protected
    assert "FROZEN_EVIDENCE_READERS" not in source


# ==========================================================================
# 4. Compatibility WITHOUT touching a frozen file
# ==========================================================================


@requires_git
@pytest.mark.parametrize("name", ["phaseF", "phaseI"])
def test_the_frozen_analyzer_reproduces_its_committed_result(
    name: str, tmp_path: Path
) -> None:
    """Historical evidence stays analyzable, from the frozen analyzer's own bytes.

    Executed from the commit that froze it, so the instrument constant it imports
    genuinely is the one its phase ran under -- no patching, no substitution and
    no edit.  The reproduction is total: the verdict, every provenance key that
    is not pure invocation context, the regenerated ``bound_inputs`` hash set
    (including the analyzer's own frozen SHA-256) and the summary tables
    byte-for-byte.
    """

    spec = next(s for s in compat.FROZEN_ANALYSES if s.name == name)
    result = compat.reproduce(spec, tmp_path / name)
    assert result["failures"] == []
    assert result["verdict_reproduced"] == result["verdict_committed"] == "HOLD"
    assert result["bound_inputs_reproduced_exactly"] is True
    assert all(result["summary_tables_byte_identical"].values())
    assert set(result["provenance_keys_differing"]) <= set(
        compat.INVOCATION_CONTEXT_KEYS
    )
    assert result["model_inference_performed"] is False


@requires_git
def test_running_a_frozen_analyzer_does_not_touch_committed_results(
    tmp_path: Path,
) -> None:
    """Reproduction is read-only with respect to the repository."""

    before = instrument_revision.tree_digest("results")
    for spec in compat.FROZEN_ANALYSES:
        compat.reproduce(spec, tmp_path / spec.name)
    assert instrument_revision.tree_digest("results") == before


@requires_git
def test_the_frozen_rc2_validator_still_passes_at_its_freeze_commit() -> None:
    """Its claims are all true where it made them, including the instrument pin."""

    spec = next(s for s in compat.FROZEN_ANALYSES if s.name == "rc2_validator")
    result = compat.reproduce(spec, Path(_tmp_out()))
    assert result["failures"] == []
    assert result["passes_at_freeze_commit"] is True


def _tmp_out() -> str:
    import tempfile

    return tempfile.mkdtemp(prefix="pm1-rc2-")


def test_the_rc2_supersession_is_exactly_the_approved_instrument_revision() -> None:
    """The frozen rc2 validator's one now-false live claim, and only that one.

    Recorded rather than edited away.  If the live failure set ever grows,
    shrinks or changes text, something other than the approved instrument
    revision moved, and that is not a supersession.
    """

    assert compat.check_rc2_superseded_assertions() == []
    expected = compat.rc2_superseded_live_assertions()
    assert len(expected) == 1
    assert "src/iqa_soa" in expected[0]
    assert instrument_revision.PHASE_K_SRC_TREE in expected[0]


def test_the_compatibility_runner_reports_no_frozen_script_modified() -> None:
    report = compat.summary()
    assert report["verdict"] == "PASS"
    assert report["frozen_scripts_modified_by_phase_m"] == []
    assert report["model_inference_performed"] is False


# ==========================================================================
# 5. The revision record still governs the instrument
# ==========================================================================


@requires_git
def test_the_instrument_is_still_an_approved_hash_pinned_revision() -> None:
    assert instrument_revision.check_instrument_provenance() == []


def test_the_revision_record_states_that_no_frozen_input_changed() -> None:
    """The report may not claim broad immutability; it must claim this one."""

    record: dict[str, Any] = dict(instrument_revision.load_revision())
    statement = record["frozen_historical_inputs"]
    assert PHASE_I_ANALYZER_FROZEN_SHA256 in statement
    assert PHASE_I_ANALYZER in statement
    assert record["superseded_live_assertions"]["scripts/validate_pilot_v7_rc2.py"]
    assert record["model_inference_performed"] is False


# ==========================================================================
# 6. Nothing here runs a model
# ==========================================================================


def test_no_module_in_this_repair_can_reach_a_provider() -> None:
    for name in ("phaseM_frozen_input_audit.py", "phaseM_historical_analysis.py"):
        source = (SCRIPTS_ROOT / name).read_text(encoding="utf-8")
        for forbidden in ("ollama", "openai", "requests.", "urllib.request", "httpx"):
            assert forbidden not in source.lower(), f"{name} references {forbidden}"
