#!/usr/bin/env python3
"""Generate the POST_PHASEP_RUNTIME_SNAPSHOT_BENCHMARK_IDENTITY revision record.

The record this writes --
``docs/post_phaseP_runtime_snapshot_benchmark_identity_instrument_revision.json``
-- is the FIFTH link of the approved instrument-revision chain declared in
``scripts/instrument_revision.py``.  It is ADDITIVE in both directions, on
exactly the terms Phase O established, the post-Phase-P confirmatory
implementation reused, and the C3 provider-observability repair reused again:

* it does not replace, edit or overwrite any benchmark freeze record;
* it does not replace, edit or overwrite ``docs/phaseM_instrument_revision.json``,
  ``docs/phaseO_instrument_revision.json``,
  ``docs/post_phaseP_confirmatory_instrument_revision.json`` or
  ``docs/post_phaseP_provider_observability_instrument_revision.json``.  Each
  predecessor's claims are still proved from COMMITTED bytes at the commit ITS
  successor started from, which for the immediate predecessor is this revision's
  own parent commit.

Unlike the C3 link, this one inherits NO custody defect.  Its predecessor's
declared ``src/iqa_soa`` pin is reproducible from history exactly: at
``PARENT_COMMIT`` the committed tree digests to the very value the fourth link
declared.  :func:`predecessor_custody` proves that rather than assuming it, and
REFUSES the record if it does not hold, so this link never binds a predecessor
digest a later reader cannot verify.

WHY A FIFTH REVISION EXISTS
===========================

The first real runtime preflight of the successor qualification configuration
discovered a contract contradiction that had survived the WU5 freeze.

``ExperimentConfig.benchmark_path`` is a benchmark SOURCE ROOT.
``load_experiment_config`` applies no ``is_file()`` requirement to it (unlike
``ablations_path``), ``ExperimentRunner`` hands it to ``load_benchmark_cases`` as
a ROOT, and the runner already records its identity with the directory-capable
tree digest ``_path_digest`` under the field name ``benchmark_sha256``.  The
production configuration ``configs/successor-qualification.yaml`` accordingly
sets ``benchmark_path: benchmark``, a DIRECTORY.

The frozen WU5 capture contract nevertheless specified
``benchmark_sha256 = file_sha256(config.benchmark_path)``, and
``capture_runtime_snapshot_v1`` implemented it with a file-only helper that calls
``path.read_bytes()``.  A directory cannot be read as a file, so the production
capture did not merely produce a questionable value -- it could not be computed
at all, and the preflight refused with an instrumentation error.

Repairing it changed two files under ``src/iqa_soa``.  The moment any byte there
moved, the approved revision chain stopped describing the live instrument and
every gate asserting "the working instrument is the head of an approved revision
chain" failed.  That failure is the mechanism working.  The sanctioned response
is the one this module performs: append a new, reviewed, individually hash-pinned
link that names its parent commit, binds the existing head as its predecessor,
enumerates every changed instrument file with that file's own SHA-256 and a
scientific reason, and pins the tree the live instrument now is.

WHAT DELIBERATELY DID NOT MOVE
==============================

``INSTRUMENT_VERSION`` stays ``"5"``, ``RAW_SCHEMA_VERSION`` stays ``6``,
``NATIVE_TOOL_ADAPTER_VERSION`` stays ``native-tools-adapter-3`` and
``TOOL_ARGUMENT_CONTRACT_VERSION`` stays ``tool-arguments-1``.  Holding all four
is a positive claim this record makes, on the rule the post-Phase-P confirmatory
link already stated: *no boundary is bumped merely because the tree changed*.

The claim is checkable from the diff.  ``runner.py`` changes are PURELY ADDITIVE
-- three hunks, not one removed line -- so no existing runner code path, and in
particular neither ``_path_digest`` nor ``ExperimentRunner``, is altered.
``confirmatory.py`` removes exactly ONE line, the ``benchmark_sha256`` entry of
the ``ExperimentExecutionConfigIdentityV1`` preimage.  Nothing under
``src/iqa_soa/agent/``, ``src/iqa_soa/tools/``, ``src/iqa_soa/iqa/``,
``src/iqa_soa/metrics/`` or ``src/iqa_soa/instrument.py`` is touched at all, so
the request payload, the tool contract, the sandbox accept/refuse decision
function, the raw row schema and every metric are byte-identical.

WHAT THIS REVISION DOES NOT DO
==============================

It performs no model inference, contacts no provider and opens no socket.  It
reruns, resumes, repairs, replaces and reinterprets no Phase-P execution, and
rescores no historical row.  It authorizes no qualification and no confirmatory
execution.  It reads nothing under ``results/phaseP-rc4-qualification/``.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import instrument_revision as ir  # noqa: E402
import validate_successor_scope as scope  # noqa: E402
from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACT_VERSION,
)

#: The canonical commit at which POST_PHASEP_PROVIDER_OBSERVABILITY was the
#: approved instrument head, and therefore the commit from which the superseded
#: fourth link is proved.  The repair this record admits was made directly on
#: that tree: there is no intermediate unapproved-instrument commit, and one is
#: not invented here.
PARENT_COMMIT = "a24d8924e7bd3e42c07530aab074236db7478447"

#: The predecessor link.  Read, never written.
PREDECESSOR_RECORD_RELATIVE = (
    "docs/post_phaseP_provider_observability_instrument_revision.json"
)
PREDECESSOR_PHASE = "POST_PHASEP_PROVIDER_OBSERVABILITY"

#: This link's own label.  It names the CHANGE, not an experimental phase and not
#: a candidate: no phase is named, no candidate version is assigned and no
#: successor candidate is created by this record or by the change it documents.
PHASE = "POST_PHASEP_RUNTIME_SNAPSHOT_BENCHMARK_IDENTITY"

#: Where this record is written.
RECORD_RELATIVE = (
    "docs/post_phaseP_runtime_snapshot_benchmark_identity_instrument_revision.json"
)

#: The instrument root this revision speaks about.
RELATIVE_ROOT = "src/iqa_soa"

#: The EXACT approved instrument change set, sorted as
#: ``instrument_revision._changed_files_since`` returns it.  A file that changed
#: and is not here, or is here and did not change, refuses the record rather than
#: widening the approved set.
APPROVED_SRC_FILES: tuple[str, ...] = (
    "src/iqa_soa/experiment/confirmatory.py",
    "src/iqa_soa/experiment/runner.py",
)

#: The human authorization and the contract records this revision is bounded by.
GOVERNING_RECORDS = (
    "docs/post_phaseP_confirmatory_execution_io_clarification.md",
    "docs/post_phaseP_runtime_snapshot_benchmark_identity_correction.md",
)

#: The scientific invariants this revision must leave exactly where it found
#: them.  Recomputed, never copied, and a mismatch refuses the record.
BENCHMARK_CASE_BYTES_DIGEST = (
    "76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea"
)
CANONICAL_EXPOSURE_DIGEST = (
    "23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092"
)

#: The completed Phase-P result this revision comes AFTER and does not touch.
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
        "nor rescored by this revision. BEN-003 remains historical and "
        "unrepaired. This repair is PROSPECTIVE and acts only on a pre-execution "
        "identity capture that no Phase-P row ever used: Phase P recorded "
        "benchmark identity through the RUNNER's own _path_digest path, which "
        "this revision does not touch and which the repaired capture now agrees "
        "with."
    ),
}

#: Authored per-file scientific reasons.  Every changed instrument file must have
#: one, and a reason written for a file that did not change is an error.
REASONS: dict[str, str] = {
    "src/iqa_soa/experiment/runner.py": (
        "PURELY ADDITIVE, and deliberately so: the diff is three hunks and not "
        "one removed line, so no existing runner code path is altered. It adds "
        "the frozen source-set constant BENCHMARK_SOURCE_SUFFIXES = "
        "{'.json', '.md', '.yaml'} and the public helper "
        "benchmark_source_sha256(path), which delegates to the pre-existing "
        "private _path_digest exactly as the pre-existing package_source_sha256 "
        "already does, and names both in __all__. THE DIGEST ALGORITHM ITSELF IS "
        "NOT CHANGED: _path_digest is not edited, re-parameterized or re-ordered, "
        "and it keeps its sorted enumeration, its repository-relative name basis "
        "and its length-prefixed name-plus-content framing. ExperimentRunner is "
        "not edited: its benchmark loading, its arm ordering, its seed "
        "derivation, its row writing and the input_digests block it records -- "
        "including the benchmark_sha256 it already computed with _path_digest -- "
        "are byte-identical. No existing symbol is removed, renamed or rebound "
        "and no legacy importer observes any difference. The helper exists so "
        "that the confirmatory capture path can reuse the repository's ONE "
        "canonical benchmark identity instead of inventing a second, "
        "incompatible benchmark hash."
    ),
    "src/iqa_soa/experiment/confirmatory.py": (
        "The whole of the repair, and exactly one removed line. The "
        "ExperimentExecutionConfigIdentityV1 preimage inside "
        "capture_runtime_snapshot_v1 now obtains benchmark_sha256 from the "
        "directory-capable canonical benchmark-source digest, via the new "
        "fail-closed wrapper _benchmark_source_sha256, instead of from the "
        "file-only _file_sha256. The old derivation was not merely questionable, "
        "it was IMPOSSIBLE: ExperimentConfig.benchmark_path is a benchmark source "
        "root and every production configuration points it at a directory, which "
        "path.read_bytes() cannot read, so the first real runtime preflight "
        "refused with ConfirmatoryExecutionError rather than capturing. "
        "EVERYTHING ELSE IS PRESERVED EXACTLY: the RuntimeSnapshotV1 schema stays "
        "at twenty fields, the experiment_config_digest object keeps exactly its "
        "sixteen keys with no output_root, the field NAME benchmark_sha256 is "
        "unchanged, and _file_sha256 remains the primitive for source_path, "
        "policy_path, models_path and ablations_path, which are genuine single "
        "files. provider_config_digest, provider_parameters_digest, "
        "prompt_digest, models_config_digest, environment_fingerprint, "
        "retry_policy, tool_contract_policy, timeout_seconds, endpoint capture, "
        "the seventeen-field runtime_identity_digest basis and the self_digest "
        "rule are untouched. No caller override, keyword, hook, registry entry or "
        "exported alternative is added: capture_runtime_snapshot_v1 still accepts "
        "exactly config and provider, both keyword-only. Missing, empty, "
        "source-free and unreadable benchmark roots all fail closed."
    ),
}

#: Live assertions elsewhere in the repository that this link supersedes.  Each
#: is a frozen protocol pinning an older src/iqa_soa tree; none is edited, none
#: is weakened, and each remains provable at its own commit.
SUPERSEDED_LIVE_ASSERTIONS: dict[str, str] = {
    "scripts/phaseP_protocol.py": (
        "check_frozen_inputs() pins the Phase-O src/iqa_soa tree and "
        "check_instrument_pins() pins EXPECTED_INSTRUMENT_VERSION = '4' and "
        "EXPECTED_RAW_SCHEMA_VERSION = 5. Both were already false live before "
        "this revision, and THAT IS THE DESIRED BEHAVIOUR AND MUST NOT BE "
        "REPAIRED: the frozen Phase-P protocol refuses to run under an instrument "
        "it was not frozen against, which prevents any retroactive "
        "reinterpretation of Phase-P rows. scripts/phaseP_protocol.py is NOT "
        "edited, FROZEN_ARTIFACT_MISMATCH is not weakened and no preflight is "
        "relaxed; the claims are proved where they are true, from committed bytes."
    ),
    "scripts/phaseL_protocol.py": (
        "Already superseded by Phase O, by the post-Phase-P confirmatory link and "
        "by the C3 link on their stated terms, and superseded again here only in "
        "the sense that the digest its one false tree assertion reports is now "
        "the post-repair tree. scripts/phaseO_frozen_input_supersession.py "
        "composes the expected text from the approved HEAD of the revision chain "
        "rather than pasting it, so it consumes this new head automatically and "
        "nothing in it needed editing."
    ),
    "scripts/validate_pilot_v7_rc2.py": (
        "Already superseded by Phase M, Phase O, the post-Phase-P confirmatory "
        "link and the C3 link on the same terms, and superseded again here only "
        "in the sense that the digest its one false assertion reports is now the "
        "post-repair tree. scripts/phaseM_historical_analysis.py composes that "
        "expected string from the approved head of the revision chain, so it "
        "follows the chain automatically."
    ),
}


def _load_predecessor() -> dict[str, Any]:
    """The predecessor head record, read by NAME and never through the chain."""

    path = PROJECT_ROOT / PREDECESSOR_RECORD_RELATIVE
    parsed: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if parsed.get("phase") != PREDECESSOR_PHASE:
        raise SystemExit(
            f"{PREDECESSOR_RECORD_RELATIVE} declares phase {parsed.get('phase')!r}, "
            f"expected {PREDECESSOR_PHASE!r}; the predecessor link is not the one "
            "this revision was reviewed against"
        )
    return parsed


def approved_changed_files() -> tuple[str, ...]:
    """Exactly the approved src change set, or a refusal, in both directions."""

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


def predecessor_custody() -> dict[str, Any]:
    """The predecessor's custody state as HISTORY can prove it, or a refusal.

    Unlike the C3 link, this one inherits no custody defect: the fourth link's
    declared ``src/iqa_soa`` pin is expected to be reproducible from committed
    bytes at :data:`PARENT_COMMIT` exactly.  That is PROVED here rather than
    assumed, and a mismatch refuses the record instead of binding a predecessor
    digest a later reader could not verify.  No custody correction is invented,
    admitted or needed.
    """

    predecessor = _load_predecessor()
    previous_current = predecessor.get("current_instrument")
    if not isinstance(previous_current, dict):
        raise SystemExit(
            f"{PREDECESSOR_RECORD_RELATIVE} names no current instrument block"
        )
    declared = str(previous_current.get("src_iqa_soa_tree") or "")
    committed = ir.tree_digest_at_commit(PARENT_COMMIT, RELATIVE_ROOT)
    if declared != committed:
        raise SystemExit(
            f"the predecessor declares {RELATIVE_ROOT} tree {declared!r}, but at "
            f"{PARENT_COMMIT} the committed tree digests to {committed!r}; the "
            "chain of custody is broken and this revision refuses to bind an "
            "unprovable predecessor digest"
        )
    changed = predecessor.get("changed_files")
    if isinstance(changed, dict):
        for name, entry in sorted(changed.items()):
            if not name.startswith(f"{RELATIVE_ROOT}/") or not isinstance(entry, dict):
                continue
            blob = ir.sha256_of_blob_at_commit(PARENT_COMMIT, name)
            if blob != entry.get("sha256"):
                raise SystemExit(
                    f"the predecessor approves {name} at {entry.get('sha256')!r}, "
                    f"but at {PARENT_COMMIT} it hashes to {blob!r}"
                )
    return {
        "predecessor_declared_src_iqa_soa_tree": declared,
        "committed_src_iqa_soa_tree_at_parent_commit": committed,
        "predecessor_declared_pin_is_reproducible_from_history": True,
        "custody_correction_required": False,
        "corrected_record_edited_by_this_revision": False,
        "predecessor_record_sha256": ir.sha256_of(
            ir.REPO_ROOT / PREDECESSOR_RECORD_RELATIVE
        ),
        "note": (
            "This link inherits NO custody defect. The predecessor's declared pin "
            "and every one of its per-file digests reproduce exactly from "
            "committed bytes at this revision's parent commit, which is proved "
            "here before the record is written rather than asserted. No custody "
            "correction is admitted, needed or invented, and no predecessor "
            "record is edited, regenerated or overwritten."
        ),
    }


def scientific_invariants() -> dict[str, Any]:
    """Recompute the invariants this revision must not move, or refuse."""

    manifest = scope.load_manifest()
    cases = scope.load_cases()
    contract = json.loads(
        (scope.BENCHMARK_ROOT / "qualification-contract.json").read_text(
            encoding="utf-8"
        )
    )
    case_bytes = scope.benchmark_case_bytes_digest(manifest)
    exposure = scope.canonical_exposure_digest(cases, contract)
    if case_bytes != BENCHMARK_CASE_BYTES_DIGEST:
        raise SystemExit(
            f"the benchmark case-byte digest is {case_bytes}, not the pinned "
            f"{BENCHMARK_CASE_BYTES_DIGEST}; this revision may not move a "
            "benchmark byte"
        )
    if exposure != CANONICAL_EXPOSURE_DIGEST:
        raise SystemExit(
            f"the canonical exposure digest is {exposure}, not the pinned "
            f"{CANONICAL_EXPOSURE_DIGEST}; this revision may not move an exposure "
            "definition"
        )
    return {
        "benchmark_case_bytes_digest": case_bytes,
        "canonical_exposure_digest": exposure,
        "recomputed_not_copied": True,
        "benchmark_bytes_changed_by_this_revision": 0,
    }


def build_record() -> dict[str, Any]:
    changed = approved_changed_files()
    predecessor = _load_predecessor()
    previous_current = predecessor.get("current_instrument")
    if not isinstance(previous_current, dict):  # pragma: no cover - checked above
        raise SystemExit(
            f"{PREDECESSOR_RECORD_RELATIVE} names no current instrument block"
        )
    custody = predecessor_custody()
    previous_tree = str(custody["committed_src_iqa_soa_tree_at_parent_commit"])

    return {
        "record_kind": "instrument_revision",
        "phase": PHASE,
        "title": (
            "Post-Phase-P RuntimeSnapshotV1 benchmark-identity capture correction "
            "(capture-only; no boundary moves)"
        ),
        "additive_to": PREDECESSOR_RECORD_RELATIVE,
        "overwrites_nothing": (
            "No existing instrument revision is overwritten and no historical "
            "hash in any of them is updated in place. Neither "
            "docs/phaseM_instrument_revision.json, "
            "docs/phaseO_instrument_revision.json, "
            "docs/post_phaseP_confirmatory_instrument_revision.json, "
            "docs/post_phaseP_confirmatory_instrument_revision_correction.json "
            "nor docs/post_phaseP_provider_observability_instrument_revision.json "
            "is edited. No benchmark freeze record is edited. Each predecessor's "
            "pins are still proved from committed bytes at the commit its own "
            "successor started from; this link's predecessor is proved at "
            + PARENT_COMMIT
            + ", the last commit at which it was the approved head. "
            "scripts/instrument_revision.py verifies the chain link by link."
        ),
        "parent_commit": PARENT_COMMIT,
        "parent_commit_basis": (
            "The canonical commit at which the post-Phase-P provider "
            "observability revision was the approved head, and the commit this "
            "benchmark-identity repair was made directly on. There is no "
            "intermediate unapproved-instrument commit and none is invented: the "
            "repair, this link and the downstream re-freeze are released together "
            "as one reviewed change."
        ),
        "governed_by": list(GOVERNING_RECORDS),
        "phase_p_rc4_hold": PHASE_P_RC4_HOLD,
        "predecessor_custody": custody,
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
            "bumped merely because the tree changed -- the rule the post-Phase-P "
            "confirmatory link already stated. Every claim behind that is "
            "checkable from the diff: runner.py is purely additive (three hunks, "
            "zero removed lines), confirmatory.py removes exactly one line, and "
            "src/iqa_soa/agent/, src/iqa_soa/tools/, src/iqa_soa/iqa/, "
            "src/iqa_soa/metrics/ and src/iqa_soa/instrument.py are not touched "
            "at all. The request payload the model receives, the advertised and "
            "enforced tool argument contract, the prompts, the policy, the "
            "treatments, the seed derivation, the tool dispatch, the sandbox "
            "accept/refuse decision function, the failure taxonomy, the raw row "
            "schema and every persisted scientific endpoint are what instrument 5 "
            "/ raw schema 6 already produced. A row written under this revision "
            "and a row written under the C3 link measure the same quantity in the "
            "same way. Bumping a boundary here would assert an instrument "
            "difference that does not exist and would gratuitously forbid pooling "
            "measurements that are in fact commensurable."
        ),
        "instrument_boundary_declaration": (
            "NO NEW BOUNDARY IS DECLARED. Rows written under instrument 5 / raw "
            "schema 6 / native-tools-adapter-3 before this revision and rows "
            "written after it are produced by the same instrument in the same "
            "way, and may be pooled without a new argument. The pre-existing "
            "boundary between instrument 5 / raw schema 6 and instrument 4 / raw "
            "schema 5 is preserved exactly as the C3 link declared it, and is "
            "neither widened, narrowed nor reinterpreted here. The Phase-P "
            "protocol's deliberate pin to instrument 4 / raw schema 5 remains "
            "incompatible on purpose and is not repaired."
        ),
        "observation_only": True,
        "why_observation_only": (
            "Nothing the model sees and nothing the sandbox does is different. "
            "This repair does not reach any execution path at all: it corrects "
            "how a PRE-EXECUTION provenance capture derives one identity field. "
            "The request payload, the tool definition, the advertised and "
            "enforced argument contract, the prompts, the treatments, the policy, "
            "the seed derivation and the tool dispatch are byte-identical, so "
            "controlled_input_digest, system_prompt_sha256 and user_prompt_sha256 "
            "are unaffected. Every accept/refuse predicate, every failure_class, "
            "every failure_origin and every retryability rule is byte-identical, "
            "so every response accepted before the repair is still accepted and "
            "every response refused is still refused with the same class. No "
            "benchmark case byte, no canonical exposure definition, no scoring "
            "rule and no persisted raw scientific row field changes. The ONLY "
            "observable difference is that RuntimeSnapshotV1 capture now succeeds "
            "against a directory-valued benchmark_path where it previously could "
            "not be computed."
        ),
        "realized_measurement_population": (
            "There is NO old-vs-new successor measurement population to pool "
            "across, because the defective rule realized none. The old production "
            "path was structurally incapable of capturing the real "
            "directory-valued successor configuration -- it raised rather than "
            "returning a digest -- so no successor RuntimeSnapshotV1 was ever "
            "produced under it, and no successor qualification or confirmatory "
            "row exists at all. The repair is therefore prospective in the "
            "strongest sense: it precedes the first successor measurement rather "
            "than dividing an existing series. No claim is made here about "
            "Phase-P pooling beyond preserving the boundary the C3 link already "
            "declared; Phase P recorded benchmark identity through the runner's "
            "own _path_digest path, which this revision does not touch."
        ),
        "changed_files": {
            name: {"sha256": ir.sha256_of(ir.REPO_ROOT / name), "reason": REASONS[name]}
            for name in changed
        },
        "scientific_invariants": scientific_invariants(),
        "successor_qualification_inference_before_repair": 0,
        "confirmatory_executions_before_repair": 0,
        "successor_runtime_snapshots_before_repair": 0,
        "successor_result_rows_before_repair": 0,
        "phase_p_rows_rerun": 0,
        "phase_p_rows_rescored": 0,
        "prospective_implementation_only": (
            "This record documents a PROSPECTIVE post-Phase-P instrumentation "
            "correctness repair only. No model inference is performed by it or by "
            "the script that produces it; no provider is contacted and no socket "
            "is opened. No Phase-P execution is rerun, resumed, repaired, "
            "replaced or reinterpreted. No historical Phase-D, Phase-F, Phase-I, "
            "Phase-L or Phase-P row is modified, reclassified or rescored. No "
            "benchmark freeze record is overwritten. No existing instrument "
            "revision is overwritten. This revision authorizes no qualification "
            "execution, no confirmatory execution and no production randomization."
        ),
        "model_inference_performed": False,
        "provider_contacted": False,
        "phase_p_execution_rerun": False,
        "phase_p_result_reinterpreted": False,
        "historical_rows_rescored": False,
        "benchmark_freeze_records_overwritten": False,
        "instrument_revisions_overwritten": False,
        "authorizes_qualification_execution": False,
        "authorizes_confirmatory_execution": False,
        "post_phaseP_confirmatory_execution_authorized": False,
        "production_randomization_realized": False,
        "successor_candidate_created": False,
        "ben_003_rehabilitated": False,
        "historical_rows": (
            "Committed Phase-D, Phase-F, Phase-I, Phase-L and Phase-P raw rows "
            "are neither rewritten nor re-run. The raw row schema is untouched by "
            "this revision -- src/iqa_soa/metrics/definitions.py is not among the "
            "changed files -- so RAW_FIELDS_BY_SCHEMA_VERSION gains nothing and "
            "loses nothing, and every historical row remains readable exactly as "
            "it was under the instrument version its own phase pinned."
        ),
        "phase_p_evidence_untouched": (
            "The official Phase-P evidence root results/phaseP-rc4-qualification/ "
            "is not read, enumerated, traversed, hashed, regenerated, resumed, "
            "repaired, replaced or modified by this revision or by "
            "scripts/post_phaseP_write_runtime_snapshot_benchmark_identity_revision.py, "
            "and no value in this record, and nothing in the change it documents, "
            "is derived from it. The corrected benchmark-source digest walks only "
            "config.benchmark_path, which is the benchmark/ tree; no results "
            "namespace is reachable from it."
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
            "benchmark_source_tree_sha256": _benchmark_source_tree_sha256(),
            "note": (
                "No rc3 or rc4 task YAML, manifest byte, contract byte, freeze "
                "record or scoring threshold was touched. This repair creates no "
                "benchmark byte and changes no benchmark reachability, task "
                "semantic, canonical exposure setting or QA treatment. "
                "benchmark_source_tree_sha256 is the value the CORRECTED rule now "
                "produces for the production benchmark root, recorded so a later "
                "reader can see the repaired capture is bound to the same "
                "benchmark bytes every other record pins."
            ),
        },
        "qa_off_treatment_invariant": (
            "treatment_for('off').detailed_evidence remains False and the "
            "evidence guard remains disabled under QA OFF. This revision "
            "persists no new field of any kind: it changes the DERIVATION of one "
            "already-existing RuntimeSnapshotV1 identity digest and adds nothing "
            "to any raw row, evidence record or artifact. No assistant text, "
            "prompt echo, chain-of-thought, tool argument value, resource value, "
            "response hash, raw header, endpoint URL, credential or response body "
            "reaches disk that did not before."
        ),
        "superseded_live_assertions": SUPERSEDED_LIVE_ASSERTIONS,
        "frozen_historical_inputs": (
            "This revision changes no prospectively frozen scientific input. The "
            "successor frozen-input record's src/iqa_soa TREE binding is "
            "mechanically invalidated by the approved source change and is "
            "recomputed downstream from the repository-owned "
            "compute_frozen_inputs() path once this link is green; no stored "
            "SHA is hand-edited and no validator is weakened."
        ),
        "frozen_input_audit": "scripts/phaseM_frozen_input_audit.py",
        "historical_analysis_compatibility": "scripts/phaseM_historical_analysis.py",
        "offline_validator": "scripts/instrument_revision.py",
        "offline_writer": (
            "scripts/post_phaseP_write_runtime_snapshot_benchmark_identity_revision.py"
        ),
        "offline_tests": (
            "tests/integration/test_post_phaseP_runtime_snapshot_benchmark_identity_revision.py, "
            "tests/integration/test_runtime_snapshot_benchmark_identity.py"
        ),
    }


def _benchmark_source_tree_sha256() -> str:
    """The corrected rule's digest over the production benchmark root."""

    from iqa_soa.experiment.runner import benchmark_source_sha256

    return str(benchmark_source_sha256(PROJECT_ROOT / "benchmark"))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Write the fifth revision link.")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / RECORD_RELATIVE)
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
    "BENCHMARK_CASE_BYTES_DIGEST",
    "CANONICAL_EXPOSURE_DIGEST",
    "GOVERNING_RECORDS",
    "PARENT_COMMIT",
    "PHASE",
    "PREDECESSOR_PHASE",
    "PREDECESSOR_RECORD_RELATIVE",
    "REASONS",
    "RECORD_RELATIVE",
    "SUPERSEDED_LIVE_ASSERTIONS",
    "approved_changed_files",
    "build_record",
    "predecessor_custody",
    "scientific_invariants",
]
