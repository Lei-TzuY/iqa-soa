"""The post-Phase-P seed-provenance temporal supersession.

**NO MODEL IS RUN ANYWHERE IN THIS FILE**, nothing here contacts a provider or
opens a socket, and nothing here reads, enumerates or hashes anything beneath
``results/phaseP-rc4-qualification/``.  Every assertion is against committed
bytes, tracked working-tree bytes, or a synthetic in-memory scan.

The Phase-P seed selection was prospectively correct when it was frozen, and the
repository is entitled to have documented the completed run afterwards.  Those
are two different claims about two different moments, and this module proves that
the split between them is exact:

**A. The historical prospective claim** -- at ``f4a085f``, the frozen triple
appeared nowhere under the scan roots except Phase P's own three declared
seed-selection artifacts, the forbidden set covered everything else the history
recorded, and the collision report was collision-free under that state.

**B. The present-state claim** -- today the triple additionally appears in
exactly ONE enumerated path, ``docs/phaseP_rc4_hold_forensic_diagnosis.json``, a
POST-RUN DERIVATIVE ledger of the completed, permanently-HOLD run.  One path.
Not a prefix, not a glob, not "anything named phaseP".

The forensic diagnosis is legitimate after-the-fact documentation.  It does NOT
mean the seeds were known before selection, that the selection was post-hoc, that
the Phase-P run is invalid, or that the ledger is an allowed prospective
seed-selection artifact.  Several tests below exist specifically to keep it from
being promoted into that role.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Iterator, Mapping

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _root in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

import phaseP_derive_seeds as seeds  # noqa: E402
import phaseP_protocol as protocol  # noqa: E402
import post_phaseP_seed_provenance_supersession as supersession  # noqa: E402

FREEZE_COMMIT = "f4a085f2031dddae6a2175f2993368cbcecdd257"
DIAGNOSIS_COMMIT = "69d1efc0006062bc533a117419b91e8329254dad"
DIAGNOSIS_RELATIVE = "docs/phaseP_rc4_hold_forensic_diagnosis.json"
FROZEN_TRIPLE = (1197050110, 1904689056, 1133353488)


@pytest.fixture(scope="module")
def historical_scan() -> Mapping[int, list[str]]:
    """The committed-history seed scan AS OF the Phase-P freeze commit."""

    return supersession.scan_seeds_at_commit(FREEZE_COMMIT)


@pytest.fixture(scope="module")
def live_scan() -> Mapping[int, list[str]]:
    return seeds.scan_committed_seeds(PROJECT_ROOT)


@pytest.fixture
def synthetic_scan(
    live_scan: Mapping[int, list[str]],
) -> Iterator[dict[int, list[str]]]:
    """A mutable copy of the live scan, for adversarial source injection.

    Nothing on disk is touched: the supersession's live check is pointed at this
    in-memory mapping, so a "leaked seed" can be simulated without writing a file
    into the repository or staging anything.
    """

    yield {seed: list(sources) for seed, sources in live_scan.items()}


def _with_scan(
    monkeypatch: pytest.MonkeyPatch, scan: Mapping[int, list[str]]
) -> None:
    monkeypatch.setattr(
        seeds, "scan_committed_seeds", lambda *_a, **_k: dict(scan)
    )


# ==========================================================================
# 1. The historical prospective claim, at the commit where it bound
# ==========================================================================


def test_the_historical_seed_freeze_holds_at_the_phase_p_freeze_commit() -> None:
    assert supersession.PHASE_P_FREEZE_COMMIT == FREEZE_COMMIT
    assert supersession.check_historical_seed_freeze() == []


def test_the_deterministic_seed_triple_is_unchanged() -> None:
    """Recomputed from the canonical base SHA alone -- never pasted."""

    assert supersession.frozen_seed_triple() == FROZEN_TRIPLE
    assert tuple(protocol.SEEDS) == FROZEN_TRIPLE
    derived, _trail = seeds.derive_seeds()
    assert tuple(derived) == FROZEN_TRIPLE
    committed = supersession.blob_at_commit(FREEZE_COMMIT, supersession.SEED_RECORD_RELATIVE)
    assert committed is not None
    assert json.loads(committed.decode("utf-8"))["seeds"] == list(FROZEN_TRIPLE)


def test_the_frozen_derivation_script_is_the_historical_instrument() -> None:
    """It was not given a commit parameter, and it was not edited."""

    committed = supersession.blob_at_commit(
        FREEZE_COMMIT, supersession.FROZEN_DERIVATION_RELATIVE
    )
    assert committed is not None
    assert (
        PROJECT_ROOT / supersession.FROZEN_DERIVATION_RELATIVE
    ).read_bytes() == committed


def test_the_forbidden_set_is_historically_complete(
    historical_scan: Mapping[int, list[str]],
) -> None:
    prior = seeds.prior_phase_seeds(historical_scan)
    assert set(prior) <= set(seeds.FORBIDDEN_SEEDS)
    assert set(prior) == {1729, 2718, 3141, 5772, 8119, *seeds.PHASE_L_SEEDS}


def test_no_phase_p_seed_leaked_at_the_freeze(
    historical_scan: Mapping[int, list[str]],
) -> None:
    prior = seeds.prior_phase_seeds(historical_scan)
    assert set(FROZEN_TRIPLE) & set(prior) == set()
    for seed in FROZEN_TRIPLE:
        assert set(historical_scan[seed]) <= seeds.PHASE_P_ARTIFACTS
        assert set(historical_scan[seed]), seed


def test_the_historical_collision_report_is_collision_free(
    historical_scan: Mapping[int, list[str]],
) -> None:
    derived, trail = seeds.derive_seeds()
    report = seeds.collision_report(derived, trail, scanned=historical_scan)
    assert report["collision_free"] is True
    assert report["forbidden_set_covers_every_committed_seed"] is True
    assert report["derived_seeds_found_in_committed_history"] == []
    assert report["derived_seeds_leaked_outside_phase_p_artifacts"] == {}


def test_the_committed_record_is_reproducible_from_the_historical_scan(
    historical_scan: Mapping[int, list[str]],
) -> None:
    """The record describes the state that existed when the selection was frozen."""

    rebuilt = seeds.render(seeds.build_record(scanned=historical_scan))
    committed = supersession.blob_at_commit(
        FREEZE_COMMIT, supersession.SEED_RECORD_RELATIVE
    )
    assert committed is not None
    assert rebuilt == committed.decode("utf-8")


# ==========================================================================
# 2. The post-run derivative ledger, and only it
# ==========================================================================


def test_the_diagnosis_did_not_exist_at_the_freeze() -> None:
    """If it had, the seeds really would have been visible before selection."""

    assert supersession.blob_at_commit(FREEZE_COMMIT, DIAGNOSIS_RELATIVE) is None


def test_the_diagnosis_exists_from_its_own_commit_onwards() -> None:
    assert supersession.blob_at_commit(DIAGNOSIS_COMMIT, DIAGNOSIS_RELATIVE) is not None
    assert supersession.is_ancestor(FREEZE_COMMIT, DIAGNOSIS_COMMIT)
    assert not supersession.is_ancestor(DIAGNOSIS_COMMIT, FREEZE_COMMIT)


def test_the_diagnosis_declares_exactly_the_required_identity_and_status() -> None:
    """Validated from the COMMITTED derivative artifact, never from the evidence."""

    committed = supersession.blob_at_commit(DIAGNOSIS_COMMIT, DIAGNOSIS_RELATIVE)
    assert committed is not None
    assert (PROJECT_ROOT / DIAGNOSIS_RELATIVE).read_bytes() == committed
    parsed = json.loads(committed.decode("utf-8"))
    assert parsed["artifact_kind"] == "phase_p_rc4_hold_forensic_diagnosis"
    assert parsed["authoritative_for_qualification"] is False
    assert parsed["official_verdict"] == "HOLD"
    assert parsed["terminal_status"] == "SCHEDULE_COMPLETE_VERDICT_HOLD"
    attestation = parsed["immutable_evidence_attestation"]
    assert attestation["phase_p_cells_rerun"] == 0
    assert attestation["model_inference_performed"] is False
    assert attestation["official_evidence_modified"] is False
    assert supersession.check_post_run_derivative_artifact() == []


def test_the_ledger_is_never_promoted_into_the_prospective_artifacts() -> None:
    """A post-run record must not become an allowed seed-SELECTION artifact."""

    assert DIAGNOSIS_RELATIVE not in seeds.PHASE_P_ARTIFACTS
    assert seeds.PHASE_P_ARTIFACTS == frozenset(
        {
            "configs/phaseP-qualification.yaml",
            "docs/phaseP_rc4_prospective_seed_derivation.json",
            "docs/phaseP_frozen_execution_inputs.json",
        }
    )
    assert supersession.POST_RUN_DERIVATIVE_SEED_SOURCES == frozenset(
        {DIAGNOSIS_RELATIVE}
    )
    assert not (
        supersession.POST_RUN_DERIVATIVE_SEED_SOURCES & seeds.PHASE_P_ARTIFACTS
    )
    assert (
        supersession.summary()["post_run_occurrence_classification"]
        == "POST_RUN_DERIVATIVE_SEED_OCCURRENCE"
    )


def test_the_current_extra_seed_source_is_exactly_the_diagnosis(
    live_scan: Mapping[int, list[str]],
) -> None:
    extra = supersession.extra_seed_sources(live_scan, FROZEN_TRIPLE)
    assert set(extra) == set(FROZEN_TRIPLE)
    for seed, sources in extra.items():
        assert sources == {DIAGNOSIS_RELATIVE}, seed
    assert supersession.check_live_postrun_seed_supersession() == []


def test_run_all_is_empty_only_when_both_temporal_claims_hold() -> None:
    assert supersession.run_all() == []
    assert supersession.summary()["historical_prospective_claim_holds"] is True
    assert supersession.summary()["live_postrun_supersession_holds"] is True


# ==========================================================================
# 3. The bound is a BOUND: adversarial sources still fail
# ==========================================================================


def test_a_synthetic_extra_json_source_fails_the_supersession(
    monkeypatch: pytest.MonkeyPatch, synthetic_scan: dict[int, list[str]]
) -> None:
    """A future JSON artifact leaking a Phase-P seed is still a hard failure."""

    synthetic_scan[FROZEN_TRIPLE[0]].append("docs/some_future_artifact.json")
    _with_scan(monkeypatch, synthetic_scan)
    failures = supersession.check_live_postrun_seed_supersession()
    assert failures
    assert any("docs/some_future_artifact.json" in item for item in failures)


def test_a_synthetic_extra_config_yaml_source_fails_the_supersession(
    monkeypatch: pytest.MonkeyPatch, synthetic_scan: dict[int, list[str]]
) -> None:
    """Same for a config, proved on the pure classification path.

    The injection is in memory rather than on disk: writing a tracked file into
    the repository to prove a check works would mutate the very state under test.
    """

    synthetic_scan[FROZEN_TRIPLE[1]].append("configs/some-future-phase.yaml")
    assert supersession.extra_seed_sources(synthetic_scan, FROZEN_TRIPLE)[
        FROZEN_TRIPLE[1]
    ] == {DIAGNOSIS_RELATIVE, "configs/some-future-phase.yaml"}
    _with_scan(monkeypatch, synthetic_scan)
    failures = supersession.check_live_postrun_seed_supersession()
    assert failures
    assert any("configs/some-future-phase.yaml" in item for item in failures)


def test_a_result_row_leaking_a_phase_p_seed_fails_the_supersession(
    monkeypatch: pytest.MonkeyPatch, synthetic_scan: dict[int, list[str]]
) -> None:
    synthetic_scan[FROZEN_TRIPLE[2]].append("results/phaseQ-future/raw/runs.jsonl")
    _with_scan(monkeypatch, synthetic_scan)
    assert any(
        "results/phaseQ-future/raw/runs.jsonl" in item
        for item in supersession.check_live_postrun_seed_supersession()
    )


def test_removing_the_expected_diagnosis_occurrence_does_not_broaden_acceptance(
    monkeypatch: pytest.MonkeyPatch, synthetic_scan: dict[int, list[str]]
) -> None:
    """The bound is an EQUALITY, so a missing occurrence fails too.

    Otherwise the supersession would describe a repository state that does not
    exist, and a later change that quietly dropped the ledger -- or trimmed the
    seeds out of it -- would pass unnoticed.
    """

    synthetic_scan[FROZEN_TRIPLE[0]] = [
        source
        for source in synthetic_scan[FROZEN_TRIPLE[0]]
        if source != DIAGNOSIS_RELATIVE
    ]
    _with_scan(monkeypatch, synthetic_scan)
    failures = supersession.check_live_postrun_seed_supersession()
    assert failures
    assert any("does not appear in the declared post-run" in item for item in failures)


def test_an_uncovered_non_phase_p_seed_still_fails(
    monkeypatch: pytest.MonkeyPatch, synthetic_scan: dict[int, list[str]]
) -> None:
    """Every completeness guarantee about NON-Phase-P seeds is retained."""

    synthetic_scan[424242] = ["configs/some-future-phase.yaml"]
    _with_scan(monkeypatch, synthetic_scan)
    failures = supersession.check_live_postrun_seed_supersession()
    assert any("forbidden set does not cover" in item for item in failures)
    assert any("424242" in item for item in failures)


def test_a_phase_p_seed_undeclared_by_its_own_artifacts_fails(
    monkeypatch: pytest.MonkeyPatch, synthetic_scan: dict[int, list[str]]
) -> None:
    """The post-run ledger supplements the declaration; it never replaces it."""

    synthetic_scan[FROZEN_TRIPLE[0]] = [DIAGNOSIS_RELATIVE]
    _with_scan(monkeypatch, synthetic_scan)
    failures = supersession.check_live_postrun_seed_supersession()
    assert any("declared by none of Phase P's own artifacts" in item for item in failures)


# ==========================================================================
# 4. The frozen protocol still refuses a poisoned triple
# ==========================================================================


@pytest.mark.parametrize(
    "poison, label",
    [
        ((929260329, 1904689056, 1133353488), "an old Phase-L seed"),
        ((1197050110, 1197050110, 1133353488), "a duplicate new seed"),
        ((1133353488, 1904689056, 1197050110), "a reordered triple"),
        ((1729, 2718, 3141), "the Phase-F/I triple"),
    ],
)
def test_a_poisoned_seed_triple_still_fails_the_frozen_protocol(
    monkeypatch: pytest.MonkeyPatch, poison: tuple[int, ...], label: str
) -> None:
    """No historicalization may launder a triple the frozen protocol rejects."""

    monkeypatch.setattr(protocol, "SEEDS", poison)
    assert protocol.check_seed_provenance(), (
        f"{label} was accepted by the seed provenance check"
    )


def test_the_supersession_refuses_a_triple_it_cannot_prove_historically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The historical proof is recomputed, not asserted from the record."""

    monkeypatch.setattr(
        supersession, "frozen_seed_triple", lambda: (1729, 2718, 3141)
    )
    failures = supersession.check_historical_seed_freeze()
    assert failures
    assert any("FORBIDDEN" in item or "reproduces" in item for item in failures)


# ==========================================================================
# 5. The module itself reaches nothing it must not
# ==========================================================================


def test_the_supersession_performs_no_inference_and_no_evidence_access() -> None:
    import ast

    path = SCRIPTS_ROOT / "post_phaseP_seed_provenance_supersession.py"
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
    # No literal composes a path into results/, so nothing can be opened there.
    assert not [item for item in literals if item.startswith("results/")]
    # The evidence root may be NAMED once, in the module docstring, purely to say
    # that it is never reached.  Nowhere else.
    module_doc = ast.get_docstring(tree) or ""
    named = [
        item for item in literals if "results/phaseP-rc4-qualification" in item
    ]
    assert len(named) == 1, named
    assert named[0].strip() == module_doc.strip()
    assert "never opens, enumerates or hashes anything beneath" in module_doc
    payload: Mapping[str, Any] = supersession.summary()
    assert payload["model_inference_performed"] is False
    assert payload["authorizes_confirmatory_execution"] is False
    assert payload["phase_p_result_reinterpreted"] is False
    assert payload["phase_p_cells_rerun"] == 0
    assert payload["phase_p_verdict"] == "HOLD"
    assert payload["pilot_v7_rc4_status"] == "UNQUALIFIED"
