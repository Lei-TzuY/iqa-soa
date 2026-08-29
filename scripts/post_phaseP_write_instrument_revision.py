#!/usr/bin/env python3
"""Generate the POST_PHASEP_CONFIRMATORY approved instrument-revision record.

The record this writes --
``docs/post_phaseP_confirmatory_instrument_revision.json`` -- is the THIRD link
of the approved instrument-revision chain declared in
``scripts/instrument_revision.py``.  It is ADDITIVE in both directions, on
exactly the terms Phase O established when it appended itself behind Phase M:

* it does not replace, edit or overwrite
  ``benchmark/pilot-v7-rc3/freeze-record.json``, whose ``src_iqa_soa_tree`` pin
  still describes the instrument at the Phase-K freeze commit and is still
  proved there from git history;
* it does not replace, edit or overwrite ``docs/phaseM_instrument_revision.json``
  or ``docs/phaseO_instrument_revision.json``.  Phase M's claims are still proved
  from COMMITTED bytes at the commit Phase O started from, and Phase O's claims
  are now proved from COMMITTED bytes at the commit THIS revision started from --
  the last commit at which Phase O was the approved head.

WHY A THIRD REVISION EXISTS
===========================

The frozen post-Phase-P confirmatory-randomization implementation design
(``docs/post_phaseP_confirmatory_randomization_implementation_design.md``), the
code-implementation authorization
(``docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md``)
and the schema clarifications frozen beside them authorized Work Units 1-6 to be
implemented in the repository, PROSPECTIVELY, before any confirmatory execution
exists.  Implementing them necessarily added modules under ``src/iqa_soa`` and
made three small additive edits to existing ones.  The moment any byte under
``src/iqa_soa`` moved, the approved revision chain -- which ended at Phase O --
stopped describing the live instrument, and every gate that asserts "the working
instrument is the head of an approved revision chain" failed.

That failure is the mechanism working, not a defect in it.  The sanctioned
response is the one this module performs: append a new, reviewed, individually
hash-pinned link that names its parent commit, binds the existing Phase-O head as
its predecessor, enumerates every changed instrument file with that file's own
SHA-256 and a scientific reason, and pins the tree the live instrument now is.
Nothing historical is rewritten and no earlier pin is overwritten.

WHAT THIS REVISION DOES NOT DO
==============================

It is PROSPECTIVE IMPLEMENTATION ONLY.  No model is run, no Phase-P cell is
rerun or reinterpreted, no historical row is rescored, the completed Phase-P
pilot-v7-rc4 result remains UNQUALIFIED with a permanent HOLD verdict, and this
revision authorizes no confirmatory execution by itself.  Work-Unit authorization
remains governed by the separately frozen prospective confirmatory lifecycle.

Every field is derived from the repository, not typed by hand; only the per-file
scientific reasons are authored, because only a human can supply those.
Regenerating this file on an unchanged tree must reproduce it byte-for-byte, so a
reviewer can verify it by re-running this script.

NO MODEL INFERENCE, AND NO EVIDENCE ACCESS.  This script reads git, the working
tree under ``src/iqa_soa``, ``benchmark/``, ``configs/`` and the predecessor
revision record.  It never opens, enumerates, hashes, traverses or writes
anything beneath ``results/``.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision as ir  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACT_VERSION,
)

#: The canonical parent: the ``origin/main`` merge-base from which the WU1-WU6
#: prospective implementation branch diverged (the merge of PR #28).  It is also
#: the last commit at which Phase O was the approved head, which is where the
#: superseded Phase-O link is proved from committed bytes.
PARENT_COMMIT = "bc9d0a1234ab229d6433dbd4e54df1e17823806c"

#: The predecessor link.  Read, never written.
PREDECESSOR_RECORD_RELATIVE = "docs/phaseO_instrument_revision.json"
PREDECESSOR_PHASE = "O"

#: This link's own phase name.
PHASE = "POST_PHASEP_CONFIRMATORY"

#: The instrument root this revision speaks about.
RELATIVE_ROOT = "src/iqa_soa"

#: The EXACT approved instrument change set, sorted.  A file that changed and is
#: not here, or is here and did not change, refuses the record rather than
#: widening the approved set.  Enumerated rather than discovered, so review
#: approves a fixed list.
APPROVED_SRC_FILES: tuple[str, ...] = (
    "src/iqa_soa/agent/__init__.py",
    "src/iqa_soa/agent/providers.py",
    "src/iqa_soa/experiment/confirmatory.py",
    "src/iqa_soa/experiment/confirmatory_assignment.py",
    "src/iqa_soa/experiment/confirmatory_eligibility.py",
    "src/iqa_soa/experiment/confirmatory_registration.py",
    "src/iqa_soa/experiment/runner.py",
    "src/iqa_soa/metrics/confirmatory.py",
)

#: The completed Phase-P result this revision comes AFTER and does not touch.
#: Recorded, never rewritten, and explicitly NOT retracted, rescored or reopened.
PHASE_P_RC4_HOLD = {
    "phase": "P",
    "benchmark_version": "pilot-v7-rc4",
    "qualification_status": "UNQUALIFIED",
    "verdict": "HOLD",
    "terminal_status": "SCHEDULE_COMPLETE_VERDICT_HOLD",
    "diagnosis_record": "docs/phaseP_rc4_hold_forensic_diagnosis.json",
    "report": "docs/phaseP_rc4_hold_forensic_diagnosis.md",
    "phase_p_cells_rerun": 0,
    "phase_p_rows_rescored": 0,
    "note": (
        "The completed official Phase-P qualification of pilot-v7-rc4 ended "
        "SCHEDULE_COMPLETE_VERDICT_HOLD and pilot-v7-rc4 remains UNQUALIFIED. "
        "That verdict stands, and is neither retracted, revisited, reinterpreted "
        "nor rescored by this revision. No Phase-P cell is rerun, no Phase-P row "
        "is reclassified, and the official Phase-P evidence root is not read, "
        "enumerated, hashed, regenerated or modified by this revision or by the "
        "script that produces it."
    ),
}

#: The frozen prospective lifecycle that governs Work-Unit authorization.  This
#: revision records the instrument; it grants nothing.
CONFIRMATORY_LIFECYCLE_AUTHORITIES = (
    "docs/post_phaseP_prospective_redesign_decision.md",
    "docs/post_phaseP_qualification_methodology_decision.md",
    "docs/post_phaseP_analysis_contract_decision.md",
    "docs/post_phaseP_confirmatory_randomization_design_decision.md",
    "docs/post_phaseP_confirmatory_randomization_implementation_design.md",
    "docs/post_phaseP_confirmatory_randomization_code_implementation_authorization.md",
)

#: Authored per-file scientific reasons.  Every changed instrument file must have
#: one, and a reason written for a file that did not change is an error: both
#: directions are checked in ``build_record``.
REASONS: dict[str, str] = {
    "src/iqa_soa/agent/__init__.py": (
        "Additive export only. ProviderFailureOrigin joins the package's public "
        "surface beside ProviderError, so the frozen WU5 confirmatory execution "
        "boundary binds the structured provider failure-origin vocabulary from "
        "iqa_soa.agent instead of reaching into iqa_soa.agent.providers internals "
        "-- a distinction the frozen WU5 observation taxonomy has to record per "
        "attempt and must therefore import from a stable name. The change is one "
        "import line and one __all__ entry: no existing export is removed, "
        "renamed or rebound, no symbol changes identity, and no legacy importer "
        "observes any difference."
    ),
    "src/iqa_soa/agent/providers.py": (
        "Adds ProviderFailureOrigin (PROVIDER_INFRASTRUCTURE, MODEL_OUTPUT) and "
        "stamps it on every ProviderError raised while PARSING a provider "
        "message, so a failed provider-boundary observation carries whether the "
        "defect was in the MODEL'S OUTPUT or in the PROVIDER/INFRASTRUCTURE path. "
        "The frozen WU5 observation taxonomy requires exactly that separation and "
        "cannot derive it after the fact: a transport fault, an exhausted retry "
        "and a syntactically invalid model action are not distinguishable from "
        "failure_class alone, and an infrastructure fault silently counted as a "
        "model observation would corrupt a prospective confirmatory position "
        "before any analysis saw it. LEGACY BEHAVIOUR IS PRESERVED EXACTLY: the "
        "constructor argument is keyword-only and defaults to "
        "PROVIDER_INFRASTRUCTURE, so every pre-existing raise site keeps its "
        "previous meaning; no failure_class value, message string, retryability "
        "rule, tool-call counting rule or ProviderError.provenance() field "
        "changes; and no request payload, prompt, tool schema, argument contract, "
        "temperature, seed or sampling parameter changes. "
        "NATIVE_TOOL_ADAPTER_VERSION and TOOL_ARGUMENT_CONTRACT_VERSION therefore "
        "do not move, and no committed row is reclassified."
    ),
    "src/iqa_soa/experiment/confirmatory.py": (
        "NEW. The frozen Work Unit 5 post-Phase-P confirmatory EXECUTION "
        "BOUNDARY. It owns run_confirmatory_experiment, the runtime-identity "
        "capture and refusal path (capture_runtime_snapshot_v1, "
        "RuntimeIdentityRefused), the closed EXECUTION_ROW_KEYS row schema with "
        "its content and snapshot-binding validation, and crash-safe "
        "single-position execution built on the "
        "CONFIRMATORY_POSITION_EXECUTION_RESERVED_V1 reservation marker, so a "
        "position is either durably recorded exactly once or left unclaimed -- "
        "never half-written and never silently re-executed. It re-validates the "
        "runtime it actually ran under against the identity the frozen "
        "registration chain fixed, and refuses rather than repairing any "
        "divergence. It takes the address of a design only, reloads the frozen "
        "registration/eligibility/assignment chain from disk, and reaches no "
        "legacy scheduling, seed-derivation or scoring path. Nothing here "
        "authorizes an execution: the confirmatory lifecycle gate is upstream of "
        "every entry point in it."
    ),
    "src/iqa_soa/experiment/confirmatory_assignment.py": (
        "NEW. The frozen Work Unit 4 prospective Monte-Carlo randomization "
        "provenance and assignment persistence. It produces "
        "randomization_mc_provenance.json in its exact ten-key exact-enumeration "
        "or nineteen-key Monte-Carlo tagged shape, and assignment_manifest.json "
        "carrying one production bit per registered task, from a validated "
        "FINAL_REGISTRATION_FROZEN chain and nothing else. Randomness is drawn "
        "internally, never accepted from a caller, and is returned only AFTER it "
        "is durably published: staging, no-clobber publication, directory-"
        "metadata sync and pending-file removal are ordered so a crash cannot "
        "leave an assignment that was used but not recorded, or recorded twice "
        "with different bits. It reuses the Work Unit 1 canonical-JSON and "
        "self_digest helpers rather than forking a second digest algorithm, so "
        "the frozen prospective MC provenance is bound to the same registration "
        "digests the rest of the chain is bound to."
    ),
    "src/iqa_soa/experiment/confirmatory_eligibility.py": (
        "NEW. The frozen Stage-B PRE-OUTCOME confirmatory eligibility freeze: the "
        "EligibilityManifestV1 schema, the total disposition derivation, the "
        "infrastructure-symmetry derivation, the twenty-six fail-closed rules "
        "E1-E26 executed in numbered order against the RAW parsed artifact, and "
        "immutable eligibility_manifest.json persistence bound to the Stage-A "
        "draft's self_digest. Eligibility is frozen strictly BEFORE any outcome "
        "exists, which is what makes it a prospective criterion rather than a "
        "post-hoc filter: nothing here reads a result, dereferences an evidence "
        "locator, opens a socket, contacts a provider, draws randomness or "
        "creates a design_id, and every provider and runtime configured in the "
        "repository remains CURRENT_PROVIDER_ELIGIBILITY: UNASSESSED. Nothing is "
        "normalized or repaired; a malformed artifact is refused, never fixed up "
        "on the caller's behalf."
    ),
    "src/iqa_soa/experiment/confirmatory_registration.py": (
        "NEW. The frozen Stage-A REGISTRATION_DRAFT schema, the canonical JSON "
        "profile and the self_digest construction/verification procedure the "
        "whole confirmatory chain shares, and the Stage-C "
        "FINAL_REGISTRATION_FROZEN RegistrationManifestV1 schema with its "
        "deterministic partition of the Stage-A matrix by the frozen Stage-B "
        "dispositions, position_id, K, randomization_mode, the five-key "
        "matrix_digest preimage and the thirty-nine fail-closed rules F1-F39. It "
        "also fixes the runtime-identity schema the execution boundary later "
        "re-validates against. One artifact stores exactly one digest of itself, "
        "canonicalization has a single authorized serializer, and the persisted "
        "bytes are canonical JSON plus exactly one trailing LF that is never part "
        "of any digest. A draft records a PROPOSED design only: it selects no "
        "real task, provider, model, repetition, seed or design_id, and "
        "authorizes no eligibility assessment, randomization, assignment or "
        "execution."
    ),
    "src/iqa_soa/experiment/runner.py": (
        "Adds one minimal ADDITIVE confirmatory hook, run_one_position, which "
        "runs a single caller-selected position through the existing _run_one "
        "machinery, plus the structured failure-stage signal the frozen WU5 "
        "boundary needs: PositionExecutionError carries PRE_DISPATCH, "
        "RUNTIME_FAILURE or INSTRUMENTATION_FAILURE, so a confirmatory position "
        "can distinguish a failure BEFORE the provider-dispatch-capable boundary "
        "(nothing was consumed) from one after it (dispatch may already have "
        "occurred and must not be silently retried as if unused). It also exposes "
        "package_source_sha256, which reuses the existing package-tree digest "
        "algorithm rather than introducing a second one. LEGACY "
        "ExperimentRunner.run SEMANTICS ARE UNCHANGED: the two new _run_one "
        "callbacks are keyword-only and default to None, and the legacy path "
        "passes neither, so the row contents, the exception-to-row fallback, the "
        "schedule, the seed derivation, the treatment definitions, the prompts, "
        "the policy, the tool dispatch, the evidence handling and every persisted "
        "field remain exactly what instrument 4 / raw schema 5 already wrote. The "
        "hook performs no scheduling, no seed derivation, no provider "
        "construction, no persistence and no confirmatory interpretation of its "
        "own."
    ),
    "src/iqa_soa/metrics/confirmatory.py": (
        "NEW. The frozen Work Unit 6 confirmatory randomization analyzer and its "
        "immutable terminal artifact. It owns exactly one production entry point, "
        "analyze_confirmatory_randomization, and publishes "
        "final_analysis_manifest.json under the same reserve-then-publish "
        "discipline the execution boundary uses, so the terminal analysis is "
        "written once, durably, and can never be silently regenerated over. It "
        "accepts no loaded object, provider, capturer, clock, seed or p-value "
        "from a caller, dispatches no provider inference and generates no new "
        "entropy: the randomization distribution it tests against is the one the "
        "frozen WU4 provenance already recorded. It re-validates every execution "
        "row and runtime snapshot through the WU5 validators before any statistic "
        "is computed and fails closed with ConfirmatoryAnalysisIntegrityError "
        "rather than analysing partial or unbound evidence. The legacy paired "
        "analyzer in iqa_soa.metrics.statistics is untouched and uncalled; the "
        "legacy flat task-cluster helper is retained only as a test-time "
        "equivalence oracle on a balanced matrix, never as production "
        "aggregation."
    ),
}

#: Live assertions this revision makes false in the CURRENT tree while leaving
#: them true at their own commits.  Recorded rather than edited away, on exactly
#: the terms Phase M established for the frozen rc2 validator and Phase O
#: extended to the frozen Phase-L protocol.
SUPERSEDED_LIVE_ASSERTIONS: dict[str, str] = {
    "scripts/phaseL_protocol.py": (
        "Already superseded by Phase O on its stated terms, and superseded again "
        "here only in the sense that the digest its one false tree assertion "
        "reports is now the post-Phase-P confirmatory tree rather than the "
        "Phase-O tree. scripts/phaseO_frozen_input_supersession.py composes the "
        "expected text from the approved HEAD of the revision chain rather than "
        "pasting it, so it consumes this new head automatically and nothing in it "
        "needed editing. Its bytes are NOT edited, the Phase-L freeze is still "
        "proved from COMMITTED bytes at the Phase-L-B execution commit, and the "
        "residual live set is still required to be EXACTLY the enumerated "
        "supersession."
    ),
    "scripts/phaseP_protocol.py": (
        "check_frozen_inputs() and check_instrument_pins() assert "
        "docs/phaseP_frozen_execution_inputs.json and the approved Phase-O "
        "revision against the LIVE working tree, and both pin src/iqa_soa to the "
        "Phase-O instrument 8d569696... . Those assertions bound the completed "
        "Phase-P run and remain true at "
        + PARENT_COMMIT
        + ", the last commit at which Phase O was the approved head; they are now "
        "false live because an approved successor revision exists. Neither "
        "scripts/phaseP_protocol.py nor docs/phaseP_frozen_execution_inputs.json "
        "is edited, FROZEN_ARTIFACT_MISMATCH is not weakened, and no Phase-P "
        "preflight is relaxed: the frozen Phase-P protocol still refuses to "
        "execute on this tree, which is the correct behaviour for a frozen "
        "protocol whose instrument has moved. The claim is proved where it is "
        "actually true -- from committed bytes at that commit -- in "
        "tests/integration/test_phaseP_execution_protocol.py."
    ),
    "scripts/validate_pilot_v7_rc2.py": (
        "Already superseded by Phase M and again by Phase O on the same terms, "
        "and superseded again here only in the sense that the digest its one "
        "false assertion reports is now the post-Phase-P confirmatory tree. "
        "scripts/phaseM_historical_analysis.py composes that expected string from "
        "the approved head of the revision chain, so it follows the chain "
        "automatically and nothing in it needed editing."
    ),
}


def _load_predecessor() -> dict[str, object]:
    """The Phase-O head record, read by NAME and never through the chain head.

    Reading it through ``instrument_revision.load_revision()`` would make this
    writer self-referential the moment the new record is appended to the chain,
    so the predecessor is addressed explicitly and its phase is checked.
    """

    path = PROJECT_ROOT / PREDECESSOR_RECORD_RELATIVE
    parsed: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    if parsed.get("phase") != PREDECESSOR_PHASE:
        raise SystemExit(
            f"{PREDECESSOR_RECORD_RELATIVE} declares phase {parsed.get('phase')!r}, "
            f"expected {PREDECESSOR_PHASE!r}; the predecessor link is not the one "
            "this revision was reviewed against"
        )
    return parsed


def approved_changed_files() -> tuple[str, ...]:
    """Exactly the approved src change set, or a refusal.

    Both directions are refused: a file that changed and is not approved, and an
    approved file that did not change.  The record is never widened to whatever
    the tree happens to contain.
    """

    observed = tuple(ir._changed_files_since(PARENT_COMMIT, RELATIVE_ROOT))
    if observed != APPROVED_SRC_FILES:
        unexpected = sorted(set(observed) - set(APPROVED_SRC_FILES))
        absent = sorted(set(APPROVED_SRC_FILES) - set(observed))
        raise SystemExit(
            "the observed src/iqa_soa change set is not the approved set; "
            f"unexpected={unexpected} missing={absent}"
        )
    missing_reasons = [name for name in observed if name not in REASONS]
    if missing_reasons:
        raise SystemExit(
            "every changed instrument file needs a scientific reason; missing: "
            + ", ".join(missing_reasons)
        )
    unused = [name for name in REASONS if name not in observed]
    if unused:
        raise SystemExit(
            "a reason was written for a file that did not change: " + ", ".join(unused)
        )
    return observed


def build_record() -> dict[str, object]:
    changed = approved_changed_files()
    predecessor = _load_predecessor()
    previous_current = predecessor.get("current_instrument")
    if not isinstance(previous_current, dict):
        raise SystemExit(
            f"{PREDECESSOR_RECORD_RELATIVE} names no current instrument block"
        )
    previous_tree = str(previous_current.get("src_iqa_soa_tree") or "")
    committed_tree = ir.tree_digest_at_commit(PARENT_COMMIT, RELATIVE_ROOT)
    if previous_tree != committed_tree:
        raise SystemExit(
            f"the Phase-O record pins {RELATIVE_ROOT} to {previous_tree!r}, but at "
            f"{PARENT_COMMIT} the committed tree digests to {committed_tree!r}; the "
            "chain of custody would be broken"
        )

    return {
        "record_kind": "instrument_revision",
        "phase": PHASE,
        "title": (
            "Prospective post-Phase-P confirmatory randomization implementation "
            "(Work Units 1-6)"
        ),
        "additive_to": PREDECESSOR_RECORD_RELATIVE,
        "overwrites_nothing": (
            "No existing instrument revision is overwritten and no historical "
            "hash in any of them is updated in place. Neither "
            "benchmark/pilot-v7-rc3/freeze-record.json, "
            "benchmark/pilot-v7-rc4/freeze-record.json, "
            "docs/phaseM_instrument_revision.json nor "
            "docs/phaseO_instrument_revision.json is edited. The rc3 freeze "
            "record's src_iqa_soa_tree pin still describes the Phase-K freeze "
            "commit and is still proved there from git history; the Phase-M "
            "record's pins are still proved from committed bytes at "
            "0cc3b05ab79559acdd4f50675ed7937199dc4dbe; and the Phase-O record's "
            "pins are now proved from committed bytes at "
            + PARENT_COMMIT
            + ", the last commit at which Phase O was the approved head. "
            "scripts/instrument_revision.py verifies the chain link by link."
        ),
        "parent_commit": PARENT_COMMIT,
        "parent_commit_basis": (
            "The origin/main merge-base from which the prospective WU1-WU6 "
            "implementation branch diverged."
        ),
        "phase_p_rc4_hold": PHASE_P_RC4_HOLD,
        "previous_instrument": {
            "record": PREDECESSOR_RECORD_RELATIVE,
            "phase": PREDECESSOR_PHASE,
            "parent_commit": str(predecessor.get("parent_commit") or ""),
            "src_iqa_soa_tree": previous_tree,
            "instrument_version": previous_current.get("instrument_version"),
            "raw_schema_version": previous_current.get("raw_schema_version"),
            "native_tool_adapter_version": previous_current.get(
                "native_tool_adapter_version"
            ),
            "tool_argument_contract_version": previous_current.get(
                "tool_argument_contract_version"
            ),
        },
        "current_instrument": {
            "src_iqa_soa_tree": ir.tree_digest(RELATIVE_ROOT),
            "instrument_version": INSTRUMENT_VERSION,
            "raw_schema_version": RAW_SCHEMA_VERSION,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
            "tool_argument_contract_version": TOOL_ARGUMENT_CONTRACT_VERSION,
            "adapter_unchanged": True,
        },
        "instrument_versions_unchanged": (
            "INSTRUMENT_VERSION, RAW_SCHEMA_VERSION, NATIVE_TOOL_ADAPTER_VERSION "
            "and TOOL_ARGUMENT_CONTRACT_VERSION are recorded at the values the "
            "code ACTUALLY declares, and none of them moves. No boundary is "
            "bumped merely because the tree changed. WU1-WU6 was frozen to "
            "preserve legacy experiment semantics: five of the eight approved "
            "paths are new modules no legacy path imports, and the three edits to "
            "existing modules are additive and default-preserving. The request "
            "payload the model receives, the advertised and enforced tool "
            "argument contract, the treatment definitions, the prompts, the "
            "policy, the seed derivation, the tool dispatch, the failure taxonomy "
            "and every persisted raw field are what instrument 4 / raw schema 5 "
            "already produced, so a row written under this revision and a row "
            "written under Phase O measure the same quantity in the same way. "
            "Bumping a boundary constant here would assert an incomparability "
            "that does not exist and would retroactively invalidate committed "
            "Phase-P artifacts."
        ),
        "observation_only": True,
        "why_observation_only": (
            "Phase O could not claim this, because its request payload and its "
            "sandbox refusals genuinely changed. This revision can. Nothing the "
            "model sees and nothing the sandbox does is different: "
            "ProviderFailureOrigin is a keyword-only, default-preserving "
            "annotation on failures that were already raised with the same "
            "failure_class, message and provenance, and run_one_position is a new "
            "entry point whose two _run_one callbacks default to None on the "
            "legacy path. The new confirmatory modules are imported by no legacy "
            "execution path. Pooling across this boundary therefore needs no new "
            "argument."
        ),
        "changed_files": {
            name: {"sha256": ir.sha256_of(ir.REPO_ROOT / name), "reason": REASONS[name]}
            for name in changed
        },
        "prospective_implementation_only": (
            "This record documents a PROSPECTIVE post-Phase-P implementation "
            "only. No model inference is performed by it or by the script that "
            "produces it; no provider is contacted and no socket is opened. No "
            "Phase-P execution is rerun, resumed, repaired, replaced or "
            "reinterpreted. No historical Phase-D, Phase-F, Phase-I, Phase-L or "
            "Phase-P row is modified, reclassified or rescored. No benchmark "
            "freeze record is overwritten. No existing instrument revision is "
            "overwritten. This revision authorizes no real confirmatory execution "
            "by itself."
        ),
        "model_inference_performed": False,
        "phase_p_execution_rerun": False,
        "phase_p_result_reinterpreted": False,
        "historical_rows_rescored": False,
        "benchmark_freeze_records_overwritten": False,
        "instrument_revisions_overwritten": False,
        "authorizes_confirmatory_execution": False,
        "post_phaseP_confirmatory_execution_authorized": False,
        "confirmatory_lifecycle_authorization": {
            "governed_by": list(CONFIRMATORY_LIFECYCLE_AUTHORITIES),
            "note": (
                "Work-Unit authorization remains governed by the separately "
                "frozen prospective confirmatory lifecycle recorded in the "
                "documents above. This instrument revision authenticates the "
                "implementation tree; it grants no execution, opens no gate, "
                "selects no design_id, assesses no provider eligibility and "
                "consumes no seed."
            ),
        },
        "historical_rows": (
            "Committed Phase-D, Phase-F, Phase-I, Phase-L and Phase-P raw rows "
            "are neither rewritten nor re-run. They remain readable under the "
            "schema they were written with, via RAW_FIELDS_BY_SCHEMA_VERSION, and "
            "under the instrument version their own phase ran under. Their frozen "
            "analyzers are NOT edited: scripts/phaseM_historical_analysis.py "
            "still executes each from the commit that froze it. Because no "
            "instrument, schema, adapter or contract version moves in this "
            "revision, that mechanism absorbs it unchanged."
        ),
        "phase_p_evidence_untouched": (
            "The official Phase-P evidence root results/phaseP-rc4-qualification/ "
            "is not read, enumerated, traversed, hashed, regenerated, resumed, "
            "repaired, replaced or modified by this revision or by "
            "scripts/post_phaseP_write_instrument_revision.py, and no value in "
            "this record is derived from it."
        ),
        "benchmark_bytes_unchanged": {
            "pilot-v7-rc3_manifest_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc3" / "manifest.json"
            ),
            "pilot-v7-rc3_freeze_record_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc3" / "freeze-record.json"
            ),
            "pilot-v7-rc4_manifest_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc4" / "manifest.json"
            ),
            "pilot-v7-rc4_qualification_contract_sha256": ir.sha256_of(
                PROJECT_ROOT
                / "benchmark"
                / "pilot-v7-rc4"
                / "qualification-contract.json"
            ),
            "pilot-v7-rc4_provenance_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc4" / "provenance.json"
            ),
            "pilot-v7-rc4_audit_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc4" / "AUDIT.md"
            ),
            "pilot-v7-rc4_freeze_record_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc4" / "freeze-record.json"
            ),
            "qa_policy_default_xml_sha256": ir.sha256_of(
                PROJECT_ROOT / "configs" / "policies" / "default.xml"
            ),
            "note": (
                "No rc3 or rc4 task YAML, manifest byte, contract byte, freeze "
                "record or scoring threshold was touched. The WU1-WU6 "
                "implementation creates no benchmark byte."
            ),
        },
        "qa_off_treatment_invariant": (
            "treatment_for('off').detailed_evidence remains False and the "
            "evidence guard remains disabled under QA OFF. This revision persists "
            "no new field on any legacy raw row: the structured provider failure "
            "origin and the position failure stage are in-process signals "
            "consumed by the prospective confirmatory boundary, and "
            "ProviderError.provenance() is unchanged, so no tool output, sentinel "
            "payload, protected value, argument VALUE, SandboxState.operation_log "
            "or AgentRun.outcomes block reaches disk that did not before."
        ),
        "superseded_live_assertions": SUPERSEDED_LIVE_ASSERTIONS,
        "frozen_historical_inputs": (
            "This revision changes no prospectively frozen scientific input. "
            "Every path -> SHA-256 binding in every committed provenance record "
            "still matches the working tree, audited by "
            "scripts/phaseM_frozen_input_audit.py. The Phase-L and Phase-P "
            "src/iqa_soa TREE digests are a separate matter and are handled under "
            "superseded_live_assertions."
        ),
        "frozen_input_audit": "scripts/phaseM_frozen_input_audit.py",
        "historical_analysis_compatibility": "scripts/phaseM_historical_analysis.py",
        "offline_validator": "scripts/instrument_revision.py",
        "offline_writer": "scripts/post_phaseP_write_instrument_revision.py",
        "offline_tests": "tests/integration/test_post_phaseP_instrument_revision.py",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ir.REVISION_CHAIN[-1])
    parser.add_argument("--print", action="store_true", help="write nothing")
    args = parser.parse_args()

    record = build_record()
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.print:
        print(payload, end="")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {args.out.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "APPROVED_SRC_FILES",
    "PARENT_COMMIT",
    "PHASE",
    "PREDECESSOR_RECORD_RELATIVE",
    "REASONS",
    "SUPERSEDED_LIVE_ASSERTIONS",
    "approved_changed_files",
    "build_record",
]
