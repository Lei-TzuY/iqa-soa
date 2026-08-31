#!/usr/bin/env python3
"""Generate the POST_PHASEP_PROVIDER_OBSERVABILITY instrument-revision record.

The record this writes --
``docs/post_phaseP_provider_observability_instrument_revision.json`` -- is the
FOURTH link of the approved instrument-revision chain declared in
``scripts/instrument_revision.py``.  It is ADDITIVE in both directions, on
exactly the terms Phase O established when it appended itself behind Phase M and
the post-Phase-P confirmatory implementation established when it appended itself
behind Phase O:

* it does not replace, edit or overwrite any benchmark freeze record;
* it does not replace, edit or overwrite ``docs/phaseM_instrument_revision.json``,
  ``docs/phaseO_instrument_revision.json`` or
  ``docs/post_phaseP_confirmatory_instrument_revision.json``.  Each predecessor's
  claims are still proved from COMMITTED bytes at the commit ITS successor
  started from, which for the immediate predecessor is this revision's own
  parent commit.

The immediate predecessor carries a pre-existing CUSTODY defect that predates C3:
two of its digests were captured over CRLF working-tree bytes that ``* text=auto
eol=lf`` guarantees no commit can hold.  That record is preserved byte-for-byte
and is NOT edited here.  Its corrected, committed-byte-provable custody state
comes from the additive
``docs/post_phaseP_confirmatory_instrument_revision_correction.json``, admitted
only through ``instrument_revision.verify_custody_correction``, and this revision
binds THAT digest as its predecessor -- see
:func:`authoritative_predecessor_custody`.

WHY A FOURTH REVISION EXISTS
============================

The accepted post-Phase-P provider observability design
(``docs/post_phaseP_provider_observability_design.md``) froze change **C3** at the
minimum telemetry set, and a separate explicit human authorization admitted that
design -- and only that design -- to implementation.  Implementing it changed five
files under ``src/iqa_soa``.  The moment any byte under ``src/iqa_soa`` moved, the
approved revision chain stopped describing the live instrument and every gate that
asserts "the working instrument is the head of an approved revision chain" failed.

That failure is the mechanism working.  The sanctioned response is the one this
module performs: append a new, reviewed, individually hash-pinned link that names
its parent commit, binds the existing head as its predecessor, enumerates every
changed instrument file with that file's own SHA-256 and a scientific reason, and
pins the tree the live instrument now is.

WHAT MOVED, AND WHAT DELIBERATELY DID NOT
=========================================

``INSTRUMENT_VERSION`` moves "4" -> "5" and ``RAW_SCHEMA_VERSION`` moves 5 -> 6.
``NATIVE_TOOL_ADAPTER_VERSION`` and ``TOOL_ARGUMENT_CONTRACT_VERSION`` do NOT
move, and holding them is a positive claim this record makes: the request payload
is byte-identical and the accept/refuse decision function is byte-identical, so a
Phase-P row and a post-C3 row were produced by the SAME native-tools adapter
asking the model the same question under the same rules.  Unlike the confirmatory
link, this revision cannot claim that no boundary moved -- the failure-row content
contract of five existing columns changed -- which is exactly why the two version
constants do move.

WHAT THIS REVISION DOES NOT DO
==============================

It is PROSPECTIVE IMPLEMENTATION ONLY.  No model is run, no Phase-P cell is rerun
or reinterpreted, no historical row is rescored, the completed Phase-P
pilot-v7-rc4 result remains UNQUALIFIED with a permanent HOLD verdict, the
BEN-003 classification is untouched, no successor candidate is created and no
confirmatory execution is authorized.

NO MODEL INFERENCE, AND NO EVIDENCE ACCESS.  This script reads git, the working
tree under ``src/iqa_soa``, ``benchmark/``, ``configs/`` and the predecessor
revision record.  It never opens, enumerates, hashes, traverses or writes anything
beneath ``results/``.
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
    PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_BOUNDARY,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACT_VERSION,
)

#: The last commit at which POST_PHASEP_CONFIRMATORY was the approved head, and
#: therefore the commit from which the superseded link is proved.
PARENT_COMMIT = "883c425daf2e6462877f0626f5fce0664ac85ca9"

#: The predecessor link.  Read, never written.
PREDECESSOR_RECORD_RELATIVE = "docs/post_phaseP_confirmatory_instrument_revision.json"
PREDECESSOR_PHASE = "POST_PHASEP_CONFIRMATORY"

#: This link's own label.  It names the CHANGE, not an experimental phase and not
#: a candidate: no phase is named, no candidate version is assigned and no
#: successor candidate is created by this record or by the change it documents.
PHASE = "POST_PHASEP_PROVIDER_OBSERVABILITY"

#: The instrument root this revision speaks about.
RELATIVE_ROOT = "src/iqa_soa"

#: The EXACT approved instrument change set, sorted.  A file that changed and is
#: not here, or is here and did not change, refuses the record rather than
#: widening the approved set.
APPROVED_SRC_FILES: tuple[str, ...] = (
    "src/iqa_soa/agent/__init__.py",
    "src/iqa_soa/agent/providers.py",
    "src/iqa_soa/experiment/runner.py",
    "src/iqa_soa/instrument.py",
    "src/iqa_soa/metrics/definitions.py",
    "src/iqa_soa/metrics/pilot.py",
)

#: The accepted design this revision implements, and the records it is bounded by.
GOVERNING_RECORDS = (
    "docs/post_phaseP_prospective_redesign_decision.md",
    "docs/post_phaseP_provider_observability_design.md",
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
        "nor rescored by this revision. C3 is PROSPECTIVE: it improves the "
        "attribution of provider and model-protocol failures that have not "
        "happened yet, and it cannot act on a frozen row. The preserved "
        "invalidated cell mistral | BEN-003 | 1133353488 remains "
        "MODEL_PROTOCOL_INVALID, the BEN-003 task status remains MATRIX_INVALID, "
        "and the forensic attribution remains MODEL_PROTOCOL_FAILURE. The "
        "envelope and token values that cell's response carried were never "
        "persisted and are UNKNOWABLE; no telemetry design can recover them and "
        "this one does not attempt to."
    ),
}

#: Authored per-file scientific reasons.  Every changed instrument file must have
#: one, and a reason written for a file that did not change is an error.
REASONS: dict[str, str] = {
    "src/iqa_soa/agent/providers.py": (
        "The whole of C3. Adds four closed instrument-authored vocabularies -- "
        "ProviderCaptureState (SUPPLIED / NOT_SUPPLIED / UNOBSERVED), "
        "ProviderCaptureStage, ProviderFailureBranch (one member per raise site "
        "plus an UNSPECIFIED legacy default) and NativeToolCallState -- plus the "
        "frozen ProviderEnvelopeCapture carrier, and labels all 23 "
        "raise ProviderError sites with the branch they are. "
        "ProviderError.provenance() previously hard-coded response_id, "
        "effective_model, finish_reason, system_fingerprint, input_tokens and "
        "output_tokens to a literal None at EVERY one of those sites, so a "
        "persisted None could not be distinguished from a value the provider "
        "omitted, nor from one that was never reachable: three facts collapsed "
        "into one byte. Those six values are now captured where they are in "
        "scope and each is paired with an explicit presence state, and the "
        "record additionally carries failure_branch, protocol, effective_seed "
        "and a typed native_tool_call_state. THE ACCEPT/REFUSE DECISION FUNCTION "
        "IS PRESERVED EXACTLY: every predicate, every failure_class, every "
        "failure_origin, every message string, every retryability rule and the "
        "entire request payload are byte-identical, the three new constructor "
        "parameters are keyword-only and default-safe so every legacy caller "
        "keeps its meaning, ProviderResponse and ProviderResponse.provenance() "
        "are untouched, and no committed row is reclassified. No assistant text, "
        "prompt, raw body, header, credential, tool argument or resource value "
        "is persisted."
    ),
    "src/iqa_soa/agent/__init__.py": (
        "Additive export only. NativeToolCallState, ProviderCaptureStage, "
        "ProviderCaptureState, ProviderEnvelopeCapture and ProviderFailureBranch "
        "join the package's public surface beside ProviderError and "
        "ProviderFailureOrigin, so a reader or analyzer binds the C3 failure "
        "vocabulary from the stable iqa_soa.agent name rather than reaching into "
        "iqa_soa.agent.providers internals. No existing export is removed, "
        "renamed or rebound, no symbol changes identity, and no legacy importer "
        "observes any difference."
    ),
    "src/iqa_soa/instrument.py": (
        "Moves the two boundary aliases and names the new constants "
        "permanently. PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_VERSION = '5' and "
        "PROVIDER_FAILURE_TELEMETRY_RAW_SCHEMA_VERSION = 6 are added, "
        "INSTRUMENT_VERSION and RAW_SCHEMA_VERSION are re-aliased to them, and 6 "
        "is appended to both READABLE tuples so schemas 1-5 stay readable "
        "forever and no historical row is rewritten. "
        "TOOL_CONTRACT_INSTRUMENT_VERSION = '4' and "
        "FAILURE_EVENT_RAW_SCHEMA_VERSION = 5 keep their values as the permanent "
        "names of the instrument and schema every frozen Phase-P artifact was "
        "written under. NATIVE_TOOL_ADAPTER_VERSION deliberately does NOT move: "
        "Phase M is the controlling precedent, the adapter's request payload and "
        "response-side accept/refuse function are byte-identical, and bumping it "
        "would assert an adapter difference that does not exist. "
        "PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_BOUNDARY declares the new "
        "boundary explicitly, in the form the frozen rc4_instrument_boundary "
        "uses and without weakening or replacing it, so no analyst pools "
        "instrument-5 and instrument-4 rows by default."
    ),
    "src/iqa_soa/metrics/definitions.py": (
        "Adds the schema-6 raw-field definition and the read contract it needs. "
        "PILOT_RAW_FIELDS_V6 is EQUAL to PILOT_RAW_FIELDS_V5 -- schema 6 adds no "
        "column, because all eleven accepted telemetry fields live inside the "
        "already-persisted provider_attempts column -- and "
        "RAW_FIELDS_BY_SCHEMA_VERSION gains its permanent entry 6. Unlike "
        "schemas 3, 4 and 5 this revision cannot claim to be strictly additive: "
        "provider_response_id, effective_model, finish_reason, "
        "system_fingerprint and effective_provider_seed keep their name and type "
        "but change their FAILURE-ROW CONTENT CONTRACT from 'null by "
        "construction' to 'captured where the failure boundary made it "
        "available'. failure_row_projection_contract states both semantics "
        "explicitly per schema version so a schema-5 row is read under schema-5 "
        "semantics and is never silently reinterpreted, and "
        "provider_failure_attempt_required_keys returns an empty tuple for every "
        "historical schema so no frozen artifact is retroactively required to "
        "carry telemetry its instrument could not produce."
    ),
    "src/iqa_soa/metrics/pilot.py": (
        "ENFORCEMENT ONLY. The schema-6 per-attempt failure-telemetry contract "
        "was DECLARED in metrics/definitions.py but was exercised nowhere in the "
        "production reader, so a raw_schema_version 6 bundle carrying malformed "
        "or absent C3 provider_attempts telemetry would have been read, "
        "classified and analyzed as though its telemetry were sound. "
        "_validate_pilot_manifest -- the ONE existing raw-row validation "
        "boundary, already the place a reader selects a row's field set by the "
        "schema it was WRITTEN under -- now also selects the attempt contract "
        "there, via provider_failure_attempt_required_keys, and refuses any "
        "attempt that provider_failure_attempt_violations rejects. No second "
        "validator is introduced and no rule is restated: the decision function "
        "is the one definitions.py already owned. SCHEMAS 1-5 ARE UNTOUCHED, and "
        "structurally so rather than by assertion: "
        "provider_failure_attempt_required_keys returns an empty tuple below "
        "schema 6, so a schema 1-5 bundle never enters the new branch at all and "
        "its attempt telemetry -- including a non-object or absent entry that "
        "the pre-existing row contract already permitted -- keeps exactly the "
        "meaning it was written with. A schema-5 row is therefore never read "
        "under schema-6 attempt semantics. The refusal is raised BEFORE "
        "_classified_failure_row and _validate_failure, so malformed schema-6 "
        "telemetry fails closed as instrument/evidence corruption rather than "
        "becoming a scientific observation; nothing is normalized, repaired, "
        "inferred, default-filled or silently dropped, and the bundle is refused "
        "whole. The existing provider_attempts checks -- list shape, "
        "provider_attempt_count agreement, and at-least-one-attempt -- are "
        "unchanged, no attempt is invented where none is required, no frozen "
        "Phase-P artifact is reinterpreted, and no analyzer, metric, pairing "
        "rule or failure classification is altered."
    ),
    "src/iqa_soa/experiment/runner.py": (
        "ONE LINE OF BEHAVIOUR. The writer selects PILOT_RAW_FIELDS_V6 instead "
        "of PILOT_RAW_FIELDS_V5, so the tuple it writes is named for the schema "
        "the manifest declares. The two tuples are EQUAL, so not one persisted "
        "column changes name, position, type or presence. Nothing else in the "
        "file moves: the row projection at effective_provider_seed, "
        "provider_response_id, effective_model, finish_reason and "
        "system_fingerprint already reads those keys from the final provider "
        "attempt with .get() and needed no edit to start carrying real values on "
        "a failure row. ExperimentRunner.run semantics, the schedule, the seed "
        "derivation, the treatment definitions, the prompts, the policy, the "
        "tool dispatch and the evidence handling are unchanged."
    ),
}

#: Live assertions this revision makes false in the CURRENT tree while leaving
#: them true at their own commits.  Recorded rather than edited away.
SUPERSEDED_LIVE_ASSERTIONS: dict[str, str] = {
    "scripts/phaseP_protocol.py": (
        "check_instrument_pins() pins EXPECTED_INSTRUMENT_VERSION = '4' and "
        "EXPECTED_RAW_SCHEMA_VERSION = 5 as literals, and check_frozen_inputs() "
        "pins the Phase-O src/iqa_soa tree. Both are now false live, and THAT IS "
        "THE DESIRED BEHAVIOUR AND MUST NOT BE REPAIRED: the frozen Phase-P "
        "protocol refuses to run under an instrument it was not frozen against, "
        "which is the mechanism that binds any future successor to the post-C3 "
        "instrument ONLY and prevents a retroactive reinterpretation of Phase-P "
        "rows. scripts/phaseP_protocol.py is NOT edited, "
        "FROZEN_ARTIFACT_MISMATCH is not weakened, no preflight is relaxed, and "
        "the claims are proved where they are true -- from committed bytes at "
        + PARENT_COMMIT
        + " -- in tests/integration/test_phaseP_execution_protocol.py. Note that "
        "TOOL_CONTRACT_INSTRUMENT_VERSION and FAILURE_EVENT_RAW_SCHEMA_VERSION, "
        "which that module also pins, still match: only the two aliases moved."
    ),
    "scripts/phaseL_protocol.py": (
        "Already superseded by Phase O and again by the post-Phase-P "
        "confirmatory link on their stated terms, and superseded again here only "
        "in the sense that the digest its one false tree assertion reports is now "
        "the post-C3 tree. scripts/phaseO_frozen_input_supersession.py composes "
        "the expected text from the approved HEAD of the revision chain rather "
        "than pasting it, so it consumes this new head automatically and nothing "
        "in it needed editing."
    ),
    "scripts/validate_pilot_v7_rc2.py": (
        "Already superseded by Phase M, Phase O and the post-Phase-P "
        "confirmatory link on the same terms, and superseded again here only in "
        "the sense that the digest its one false assertion reports is now the "
        "post-C3 tree. scripts/phaseM_historical_analysis.py composes that "
        "expected string from the approved head of the revision chain, so it "
        "follows the chain automatically."
    ),
}


def _load_predecessor() -> dict[str, object]:
    """The predecessor head record, read by NAME and never through the chain."""

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


#: The additive custody correction that supersedes the predecessor's two
#: irreproducible digests.  Read through ``instrument_revision``, never restated.
CUSTODY_CORRECTION_RELATIVE = (
    "docs/post_phaseP_confirmatory_instrument_revision_correction.json"
)


def authoritative_predecessor_custody() -> dict[str, object]:
    """The predecessor's custody state as HISTORY can prove it, or a refusal.

    The predecessor record declares its ``src/iqa_soa`` pin, and one of its
    per-file digests, over RAW working-tree bytes that carried CRLF.  This
    repository declares ``* text=auto eol=lf``, so git normalizes on commit and no
    commit can ever hold those bytes: the two digests are irreproducible from
    history, and a chain link that cannot be proved from committed bytes is not a
    chain link.

    That defect is repaired ADDITIVELY, by
    ``docs/post_phaseP_confirmatory_instrument_revision_correction.json``.  The
    defective record is preserved byte-for-byte as the evidence of the defect and
    is NOT edited; the correction carries the corrected, committed-byte-provable
    custody state, and ``instrument_revision.verify_custody_correction`` re-derives
    every value in it from committed bytes and re-runs its line-ending
    reconstruction in both directions before admitting it.

    This revision therefore binds THE CORRECTED custody state as its predecessor
    digest, because that is the one a later reader can prove.  If the correction
    does not hold -- absent, malformed, addressed elsewhere, or unproved -- the
    record is REFUSED rather than written against a digest nobody can verify.
    """

    failures, correction = ir.verify_custody_correction(relative_root=RELATIVE_ROOT)
    if failures or correction is None:
        raise SystemExit(
            "the predecessor custody correction does not hold, so this revision "
            "cannot name a provable predecessor digest: "
            + (
                "; ".join(failures)
                if failures
                else f"{CUSTODY_CORRECTION_RELATIVE} is absent"
            )
        )
    if str(correction["commit"]) != PARENT_COMMIT:
        raise SystemExit(
            f"the custody correction reconstructs {correction['commit']!r}, but "
            f"this revision's parent commit is {PARENT_COMMIT!r}"
        )
    if str(correction["record"]) != PREDECESSOR_RECORD_RELATIVE:
        raise SystemExit(
            f"the custody correction corrects {correction['record']!r}, which is "
            f"not this revision's predecessor {PREDECESSOR_RECORD_RELATIVE!r}"
        )
    committed_tree = ir.tree_digest_at_commit(PARENT_COMMIT, RELATIVE_ROOT)
    if str(correction["tree"]) != committed_tree:
        raise SystemExit(
            f"the custody correction asserts a corrected tree of "
            f"{correction['tree']!r}, but at {PARENT_COMMIT} the committed tree "
            f"digests to {committed_tree!r}"
        )
    return {
        "correction_record": CUSTODY_CORRECTION_RELATIVE,
        "corrected_src_iqa_soa_tree": committed_tree,
    }


def build_record() -> dict[str, object]:
    changed = approved_changed_files()
    predecessor = _load_predecessor()
    previous_current = predecessor.get("current_instrument")
    if not isinstance(previous_current, dict):
        raise SystemExit(
            f"{PREDECESSOR_RECORD_RELATIVE} names no current instrument block"
        )
    declared_tree = str(previous_current.get("src_iqa_soa_tree") or "")
    committed_tree = ir.tree_digest_at_commit(PARENT_COMMIT, RELATIVE_ROOT)
    custody = authoritative_predecessor_custody()
    previous_tree = str(custody["corrected_src_iqa_soa_tree"])
    if previous_tree != committed_tree:  # pragma: no cover - checked above
        raise SystemExit(
            f"the corrected predecessor digest {previous_tree!r} is not the tree "
            f"committed at {PARENT_COMMIT} ({committed_tree!r}); the chain of "
            "custody is broken"
        )
    correction_record_sha = ir.sha256_of(ir.REPO_ROOT / CUSTODY_CORRECTION_RELATIVE)
    predecessor_record_sha = ir.sha256_of(
        ir.REPO_ROOT / PREDECESSOR_RECORD_RELATIVE
    )

    return {
        "record_kind": "instrument_revision",
        "phase": PHASE,
        "title": (
            "Post-Phase-P provider failure-path observability repair (change C3, "
            "minimum telemetry set only)"
        ),
        "additive_to": PREDECESSOR_RECORD_RELATIVE,
        "overwrites_nothing": (
            "No existing instrument revision is overwritten and no historical "
            "hash in any of them is updated in place. Neither "
            "benchmark/pilot-v7-rc3/freeze-record.json, "
            "benchmark/pilot-v7-rc4/freeze-record.json, "
            "benchmark/pilot-v7-rc4/qualification-contract.json, "
            "docs/phaseM_instrument_revision.json, "
            "docs/phaseO_instrument_revision.json nor "
            "docs/post_phaseP_confirmatory_instrument_revision.json is edited. "
            "Each predecessor's pins are still proved from committed bytes at the "
            "commit its own successor started from; this link's predecessor is "
            "proved at " + PARENT_COMMIT + ", the last commit at which it was the "
            "approved head. scripts/instrument_revision.py verifies the chain link "
            "by link."
        ),
        "parent_commit": PARENT_COMMIT,
        "parent_commit_basis": (
            "The last commit at which the post-Phase-P confirmatory revision was "
            "the approved head, and the commit this C3 implementation started "
            "from."
        ),
        "governed_by": list(GOVERNING_RECORDS),
        "phase_p_rc4_hold": PHASE_P_RC4_HOLD,
        "predecessor_custody": {
            "authoritative_src_iqa_soa_tree": previous_tree,
            "committed_src_iqa_soa_tree_at_parent_commit": committed_tree,
            "predecessor_declared_src_iqa_soa_tree": declared_tree,
            "predecessor_declared_pin_is_reproducible_from_history": (
                declared_tree == committed_tree
            ),
            "correction_record": CUSTODY_CORRECTION_RELATIVE,
            "correction_record_sha256": correction_record_sha,
            "corrected_record": PREDECESSOR_RECORD_RELATIVE,
            "corrected_record_sha256": predecessor_record_sha,
            "corrected_record_edited_by_this_revision": False,
            "note": (
                "REPAIRED ADDITIVELY, and not caused by this revision. "
                "instrument_revision.sha256_of hashes raw WORKING-TREE bytes and "
                "never normalizes, so a head record is pinned to a working-tree "
                "digest, while a SUPERSEDED link is proved against COMMITTED blobs "
                "by _check_historical_link. The two agree only while the working "
                "tree is byte-identical to its commit. This repository declares "
                "'* text=auto eol=lf', so git normalizes on commit and reports a "
                "CRLF working-tree file as unchanged while it hashes differently. "
                "The predecessor's pin, and one of its per-file digests, were "
                "computed over such a tree before C3 existed, so no commit can "
                "reproduce them. The defective record is PRESERVED BYTE-FOR-BYTE "
                "and is NOT edited, regenerated or overwritten by this revision; "
                "the corrected, committed-byte-provable custody state lives in the "
                "separate additive correction record named above, which "
                "instrument_revision.verify_custody_correction re-derives from "
                "committed bytes and proves by reconstructing the defective digests "
                "in both directions before admitting it. THIS REVISION BINDS THE "
                "CORRECTED DIGEST, because that is the one a later reader can "
                "prove from history. scripts/instrument_revision.py is not "
                "weakened: the correction is pinned to one record's bytes, one "
                "phase and one commit, and any predecessor mismatch it has not "
                "reproduced still fails closed."
            ),
        },
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
        "instrument_versions_moved": (
            "INSTRUMENT_VERSION moves '4' -> '5' and RAW_SCHEMA_VERSION moves "
            "5 -> 6. Both are required. The instrument bump follows the rule this "
            "repository already states for Phase M: the harness that produced a "
            "post-C3 row is not the harness that produced a Phase-B..P row, and "
            "the constant exists so that difference is machine-checkable rather "
            "than argued from memory. The raw-schema bump is required for a "
            "reason no earlier bump had: five EXISTING columns change their "
            "content contract on failure rows, so a schema-5 failure row pooled "
            "with a schema-6 failure row would attribute an instrument change to "
            "the provider. NATIVE_TOOL_ADAPTER_VERSION and "
            "TOOL_ARGUMENT_CONTRACT_VERSION do NOT move, and holding them is a "
            "positive claim: the request payload is byte-identical and the "
            "accept/refuse decision function is byte-identical, so the model was "
            "asked the same question under the same rules on both sides of the "
            "boundary."
        ),
        "instrument_boundary_declaration": (
            PROVIDER_FAILURE_TELEMETRY_INSTRUMENT_BOUNDARY
        ),
        "observation_only": True,
        "why_observation_only": (
            "Nothing the model sees and nothing the sandbox does is different. "
            "The request payload, the tool definition, the advertised and "
            "enforced argument contract, the prompts, the treatments, the policy, "
            "the seed derivation and the tool dispatch are byte-identical, so "
            "controlled_input_digest, system_prompt_sha256 and user_prompt_sha256 "
            "are unaffected. Every accept/refuse predicate, every failure_class, "
            "every failure_origin and every retryability rule is byte-identical, "
            "so every response accepted before C3 is still accepted and every "
            "response refused is still refused with the same class. C3 changes "
            "only what the adapter RECORDS while raising."
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
            "overwritten. This revision authorizes no real confirmatory "
            "execution, creates no successor candidate and names no phase."
        ),
        "model_inference_performed": False,
        "phase_p_execution_rerun": False,
        "phase_p_result_reinterpreted": False,
        "historical_rows_rescored": False,
        "benchmark_freeze_records_overwritten": False,
        "instrument_revisions_overwritten": False,
        "authorizes_confirmatory_execution": False,
        "post_phaseP_confirmatory_execution_authorized": False,
        "successor_candidate_created": False,
        "ben_003_rehabilitated": False,
        "historical_rows": (
            "Committed Phase-D, Phase-F, Phase-I, Phase-L and Phase-P raw rows "
            "are neither rewritten nor re-run. They remain readable under the "
            "schema they were written with, via RAW_FIELDS_BY_SCHEMA_VERSION, "
            "which gains entry 6 and loses nothing, and under the instrument "
            "version their own phase ran under, which is still the permanently "
            "named constant that phase pinned. On a schema 2-5 failure row the "
            "five projected columns keep NULL_BY_CONSTRUCTION semantics, stated "
            "explicitly by "
            "iqa_soa.metrics.definitions.failure_row_projection_contract, so no "
            "historical null is reinterpreted as an observation about a provider."
        ),
        "phase_p_evidence_untouched": (
            "The official Phase-P evidence root results/phaseP-rc4-qualification/ "
            "is not read, enumerated, traversed, hashed, regenerated, resumed, "
            "repaired, replaced or modified by this revision or by "
            "scripts/post_phaseP_write_provider_observability_revision.py, and no "
            "value in this record, and no telemetry field, name, size or default "
            "in the change it documents, is derived from it."
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
                "record or scoring threshold was touched. C3 creates no benchmark "
                "byte and changes no benchmark reachability, task semantic, "
                "canonical exposure setting or QA treatment."
            ),
        },
        "qa_off_treatment_invariant": (
            "treatment_for('off').detailed_evidence remains False and the "
            "evidence guard remains disabled under QA OFF. The eleven fields C3 "
            "persists are instrument-authored closed enums, provider-generated "
            "short identifiers already persisted on the SUCCESS record, and "
            "integers already persisted in existing usage telemetry. No assistant "
            "text, prompt echo, chain-of-thought, tool ARGUMENT value, resource "
            "value from refused content, response hash, content length, raw "
            "header, endpoint URL, credential or response body reaches disk that "
            "did not before."
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
        "offline_writer": (
            "scripts/post_phaseP_write_provider_observability_revision.py"
        ),
        "offline_tests": (
            "tests/unit/test_provider_failure_telemetry.py, "
            "tests/integration/test_post_phaseP_provider_observability.py"
        ),
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
    "CUSTODY_CORRECTION_RELATIVE",
    "GOVERNING_RECORDS",
    "PARENT_COMMIT",
    "PHASE",
    "PREDECESSOR_RECORD_RELATIVE",
    "REASONS",
    "SUPERSEDED_LIVE_ASSERTIONS",
    "approved_changed_files",
    "authoritative_predecessor_custody",
    "build_record",
]
