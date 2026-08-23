#!/usr/bin/env python3
"""Generate the Phase-O approved instrument-revision record.

The record this writes -- ``docs/phaseO_instrument_revision.json`` -- is the
second link of the approved instrument-revision chain declared in
``scripts/instrument_revision.py``.  It is ADDITIVE in both directions:

* it does not replace, edit or overwrite ``benchmark/pilot-v7-rc3/freeze-record.json``,
  whose ``src_iqa_soa_tree`` pin still describes the instrument at the Phase-K
  freeze commit and is still proved there from git history;
* it does not replace, edit or overwrite ``docs/phaseM_instrument_revision.json``,
  whose claims are still proved from COMMITTED bytes at the commit Phase O
  started from -- the last commit at which Phase M was the approved head.

WHY A SECOND REVISION EXISTS
============================

Phase N attributed six invalidated Phase-L-B cells to
``TOOL_SCHEMA_PRESENTATION_DEFECT`` (finding N-1): the contract shown to the
model advertised ``"arguments": {"type": "object"}`` and named no payload key,
while ``ToolRegistry`` enforced an undisclosed six-alias set.  It attributed two
further invalidations to ``HARNESS_FAILURE_ATTRIBUTION_DEFECT`` (finding N-2):
the row-level ``failure_class`` scalar is absorbing and order-independent, so a
declared fault that demonstrably fired was masked by an earlier, unrelated
resource miss in the same trajectory.

Neither is repairable inside the benchmark or the harness alone.  The first
requires the SANDBOX and the PROVIDER to render one shared argument contract;
the second requires the INSTRUMENT to persist ordered per-action failure
telemetry that it never recorded.  Phase O therefore revises the instrument, and
records exactly what it changed, to what bytes, against which parent, and why.

**This revision is NOT observation-only, and the record says so.** Phase M could
truthfully state that a Phase-M row and a Phase-B row measure the same quantity
in the same way.  Phase O cannot: the request payload the model receives changed,
and the sandbox now refuses argument sets it previously accepted.  That is why
``NATIVE_TOOL_ADAPTER_VERSION`` moves for the first time since Phase B, and why
pooling across this boundary is a claim that must be argued rather than assumed.

Every field is derived from the repository, not typed by hand; only the per-file
scientific reasons are authored, because only a human can supply those.
Regenerating this file on an unchanged tree must reproduce it byte-for-byte, so
a reviewer can verify it by re-running this script.

NO MODEL INFERENCE.  This script reads git and the working tree and nothing else.
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
    FAULT_PROVENANCE_INSTRUMENT_VERSION,
    FAULT_PROVENANCE_RAW_SCHEMA_VERSION,
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    PRE_ARGUMENT_CONTRACT_NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACT_VERSION,
    WITHDRAWN_UNDISCLOSED_PAYLOAD_ALIASES,
)

#: The canonical Phase-O parent: ``main`` at the moment this phase branched,
#: which is the commit that merged the Phase-N forensic diagnosis (PR #12).
PARENT_COMMIT = "0cc3b05ab79559acdd4f50675ed7937199dc4dbe"

#: The Phase-L-B HOLD and the Phase-N diagnosis this revision acts on.  Recorded,
#: never rewritten, and explicitly NOT retracted by anything here.
PHASE_L_B_HOLD = {
    "commit": "693f81be666ec138def100dc7e920bd020080cd9",
    "report": "docs/phaseL_rc3_requalification_execution_report.md",
    "terminal_status": "SCHEDULE_COMPLETE_VERDICT_HOLD",
    "verdict": "HOLD",
    "rc3_status": "UNQUALIFIED",
    "note": (
        "Phase L-B executed all 102 formal cells of the frozen pilot-v7-rc3 "
        "QA-OFF requalification exactly once and held. That verdict stands, "
        "pilot-v7-rc3 remains UNQUALIFIED, and no Phase-L-B classification, row "
        "or archived byte is altered by this revision. Phase O repairs the two "
        "instrument defects the Phase-N diagnosis attributed the invalidations "
        "to, prospectively, for a release candidate that has not been executed."
    ),
}

PHASE_N_DIAGNOSIS = {
    "commit": PARENT_COMMIT,
    "report": "docs/phaseN_phaseL_hold_forensic_diagnosis.md",
    "verdict": "READY_FOR_RC4_OFFLINE_REDESIGN",
    "findings_acted_on": {
        "N-1": (
            "TOOL_SCHEMA_PRESENTATION_DEFECT. The contract shown to the model was "
            "strictly weaker than the contract the sandbox enforced, so a model "
            "could satisfy the advertised schema completely and still be refused. "
            "Six Phase-L-B cells were invalidated and forced the run to HOLD."
        ),
        "N-2": (
            "HARNESS_FAILURE_ATTRIBUTION_DEFECT. The row-level failure_class "
            "scalar gives invalid_resource absolute, order-independent precedence, "
            "so a declared fault that fired with correct runtime provenance was "
            "masked by an earlier unrelated resource miss in two Phase-L-B cells."
        ),
    },
}

#: Authored per-file scientific reasons.  Every changed instrument file must have
#: one, and a reason written for a file that did not change is an error: both
#: directions are checked in ``build_record``.
REASONS: dict[str, str] = {
    "src/iqa_soa/tools/argument_schema.py": (
        "NEW. The single source of truth for the per-tool sandbox argument "
        "contract. Phase N finding N-1 established that the model-visible schema "
        "and the sandbox's enforced contract were two independently maintained "
        "descriptions of one interface, and that they disagreed: the schema "
        "declared arguments as an unconstrained object while the sandbox required "
        "one of six undisclosed aliases. Both sides now render from this table, so "
        "'the advertised schema is truthful' becomes a checkable statement rather "
        "than a claim. The design rule is stated in the module and applied "
        "uniformly: a key is REQUIRED if and only if the sandbox cannot perform "
        "the action without it, and where the sandbox has a deterministic fallback "
        "the key is OPTIONAL and the fallback is disclosed. No requirement is "
        "added for uniformity."
    ),
    "src/iqa_soa/tools/registry.py": (
        "Enforces exactly the published contract. The six-alias _payload scan "
        "(content, body, message, payload, data, value) is withdrawn in favour of "
        "the one advertised key per tool; database.update's undisclosed "
        "values/data aliases and its undisclosed 'treat the leftover arguments as "
        "a record' fallback are withdrawn; robot.move_simulated's undisclosed "
        "'position' alias is withdrawn; message.send now refuses a bodyless send "
        "instead of recording payload=None and reporting success. Validation runs "
        "at dispatch BEFORE the fault lookup, so a proposal that never became a "
        "call cannot consume, mask or trigger a scripted fault. A refusal carries "
        "the deterministic 'sandbox argument contract' prefix, the new "
        "invalid_arguments failure class, and the exact required key, so a model "
        "can correct itself from the error text as Phase L-B recorded qwen doing "
        "in 4 of 4 cells. No handler mutates state before refusing."
    ),
    "src/iqa_soa/agent/providers.py": (
        "Advertises the contract the sandbox enforces. _native_action_tool renders "
        "per-tool argument requirements into parameters.allOf as if/then clauses "
        "keyed on the tool value, and the same contract in prose into the function "
        "description; the schema_instruction states it a third time in the system "
        "prompt, which reaches BOTH protocols and both arms. The redundancy is "
        "deliberate: Phase N established that the Mistral path loses the "
        "provider-rendered tool contract once tool-result messages follow the only "
        "user turn, so a contract carried solely by the tools field is not "
        "reliably visible. The advertised contract's version and digest are "
        "recorded on the provider descriptor, so a later reader can prove from the "
        "artifact alone which argument contract a run's model was shown -- the "
        "fact Phase N had to reconstruct from source because nothing recorded it. "
        "No prompt content, policy, guard, temperature, seed or sampling parameter "
        "changed."
    ),
    "src/iqa_soa/failure_taxonomy.py": (
        "Adds invalid_arguments to SCIENTIFIC_FAILURE_CLASSES and classifies it "
        "from the sandbox's deterministic error prefix. Phase N showed the frozen "
        "taxonomy had no class for 'the sandbox correctly refused a model-supplied "
        "argument set', so such a refusal fell through to the generic tool_failure "
        "and from there to UNEXPECTED_SANDBOX_FAILURE / CELL_INVALID_AND_HOLD, a "
        "class whose own docstring reserves it for UNEXPLAINED failures. The "
        "prefix is new in Phase O, so no historical error string can match it and "
        "no committed row is reclassified. classify_gateway_outcomes itself is "
        "deliberately left behaviourally unchanged -- every committed Phase-B..L "
        "row was written under it and re-ranking it now would silently change what "
        "those rows mean -- and its docstring now states that it is lossy and "
        "names the ordered replacement."
    ),
    "src/iqa_soa/experiment/failure_events.py": (
        "NEW. Derives an ordered, per-action failure-event list from the live "
        "GatewayOutcome sequence. Phase N finding N-2: the single row scalar "
        "cannot represent 'the model missed a resource and THEN reached the "
        "declared modality and fired the declared fault', which is precisely the "
        "trajectory that invalidated two Phase-L-B FAULT-004 cells. Every public "
        "function accepts Sequence[GatewayOutcome] and nothing else, so the "
        "benchmark declaration is structurally out of reach and an event cannot be "
        "manufactured from the answer it will be compared against. It carries no "
        "tool output, no sentinel payload, no protected value, no argument VALUE "
        "and no model text: QA-OFF treatment semantics are untouched."
    ),
    "src/iqa_soa/experiment/runner.py": (
        "Stamps the ordered failure events onto the raw row from "
        "agent_run.outcomes, alongside the Phase-M fault provenance and before the "
        "outcomes are discarded, and writes the schema-5 pilot field set. No "
        "treatment, guard, prompt, policy, tool dispatch or metric changed."
    ),
    "src/iqa_soa/metrics/definitions.py": (
        "Adds FAILURE_EVENT_TELEMETRY_FIELDS and PILOT_RAW_FIELDS_V5 as a strict "
        "superset of PILOT_RAW_FIELDS_V4, and registers schema 5 in "
        "RAW_FIELDS_BY_SCHEMA_VERSION so a reader still selects the field contract "
        "a row was WRITTEN under. No schema-2, 3 or 4 field changed name, type or "
        "meaning."
    ),
    "src/iqa_soa/instrument.py": (
        "Adds the Phase-O instrument boundary (version 4), raw schema 5, and the "
        "native-tools-adapter-3 adapter boundary, each as a permanent NAMED "
        "constant beside its predecessors so no frozen phase is retroactively "
        "invalidated. NATIVE_TOOL_ADAPTER_VERSION moves for the first time since "
        "Phase B because the adapter's request payload genuinely changed; Phase M "
        "held it constant precisely because Phase M did not touch the adapter, and "
        "holding it now would hide the change this phase exists to make."
    ),
}

#: Live assertions that this revision makes false in the CURRENT tree while
#: leaving them true at their own commits.  Recorded rather than edited away, on
#: exactly the terms Phase M established for the frozen rc2 validator.
SUPERSEDED_LIVE_ASSERTIONS: dict[str, str] = {
    "scripts/phaseL_protocol.py": (
        "check_frozen_inputs() asserts docs/phaseL_frozen_execution_inputs.json "
        "against the LIVE working tree, and that record pins the src/iqa_soa tree "
        "to the Phase-M instrument 598f7f3b... . Phase O revises the instrument, "
        "so that one tree assertion is now false live and remains true at the "
        "Phase-L-A' freeze commit and at the Phase-L-B execution commit, where the "
        "freeze actually bound the run. Its bytes are NOT edited: the file is "
        "itself a frozen Phase-L input, bound by the record it verifies. The "
        "prospective replacement is scripts/phaseO_frozen_input_supersession.py, "
        "which proves the same claim from COMMITTED bytes at the Phase-L-B "
        "execution commit. Every per-FILE hash the record pins still matches the "
        "working tree; only the two tree digests moved, and only src/iqa_soa's "
        "moved for a reason -- benchmark/pilot-v7-rc3 is byte-unchanged."
    ),
    "scripts/validate_pilot_v7_rc2.py": (
        "Already superseded by Phase M on the same terms, and superseded again "
        "here only in the sense that the digest its one false assertion reports is "
        "now the Phase-O tree rather than the Phase-M tree. "
        "scripts/phaseM_historical_analysis.py composes that expected string from "
        "the approved head of the revision chain, so it follows the chain "
        "automatically and nothing in it needed editing."
    ),
}


def build_record() -> dict[str, object]:
    changed = ir._changed_files_since(PARENT_COMMIT, "src/iqa_soa")
    missing = [name for name in changed if name not in REASONS]
    if missing:
        raise SystemExit(
            "every changed instrument file needs a scientific reason; missing: "
            + ", ".join(missing)
        )
    unused = [name for name in REASONS if name not in changed]
    if unused:
        raise SystemExit(
            "a reason was written for a file that did not change: " + ", ".join(unused)
        )
    return {
        "record_kind": "instrument_revision",
        "phase": "O",
        "title": "Truthful per-tool argument contract and ordered failure-event telemetry",
        "additive_to": "docs/phaseM_instrument_revision.json",
        "overwrites_nothing": (
            "Neither benchmark/pilot-v7-rc3/freeze-record.json nor "
            "docs/phaseM_instrument_revision.json is edited. The rc3 freeze "
            "record's src_iqa_soa_tree pin still describes the Phase-K freeze "
            "commit and is still proved there from git history; the Phase-M "
            "record's pins are still proved from committed bytes at "
            + PARENT_COMMIT
            + ", the last commit at which Phase M was the approved head. "
            "scripts/instrument_revision.py verifies the chain link by link."
        ),
        "parent_commit": PARENT_COMMIT,
        "phase_l_b_hold": PHASE_L_B_HOLD,
        "phase_n_diagnosis": PHASE_N_DIAGNOSIS,
        "previous_instrument": {
            "record": "docs/phaseM_instrument_revision.json",
            "parent_commit": "eace204d4c27a9ca48d3c0a660832f640b7a900b",
            "src_iqa_soa_tree": ir.tree_digest_at_commit(PARENT_COMMIT, "src/iqa_soa"),
            "instrument_version": FAULT_PROVENANCE_INSTRUMENT_VERSION,
            "raw_schema_version": FAULT_PROVENANCE_RAW_SCHEMA_VERSION,
            "native_tool_adapter_version": (
                PRE_ARGUMENT_CONTRACT_NATIVE_TOOL_ADAPTER_VERSION
            ),
            "tool_argument_contract_version": "tool-arguments-0",
        },
        "current_instrument": {
            "src_iqa_soa_tree": ir.tree_digest("src/iqa_soa"),
            "instrument_version": INSTRUMENT_VERSION,
            "raw_schema_version": RAW_SCHEMA_VERSION,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
            "tool_argument_contract_version": TOOL_ARGUMENT_CONTRACT_VERSION,
            "adapter_unchanged": False,
        },
        "observation_only": False,
        "why_not_observation_only": (
            "Phase M could truthfully say that a Phase-M row and a Phase-B row "
            "measure the same quantity in the same way, because it added columns "
            "and changed nothing the model or the sandbox did. Phase O cannot. The "
            "request payload the model receives now carries a per-tool argument "
            "contract, and the sandbox now refuses argument sets it previously "
            "accepted through undisclosed aliases. Rows written under instrument 4 "
            "and rows written under instrument 3 are therefore not "
            "interchangeable, and pooling across this boundary is a claim to be "
            "argued explicitly rather than assumed. The version exists so that "
            "refusal is machine-checkable."
        ),
        "withdrawn_undisclosed_payload_aliases": list(
            WITHDRAWN_UNDISCLOSED_PAYLOAD_ALIASES
        ),
        "changed_files": {
            name: {"sha256": ir.sha256_of(ir.REPO_ROOT / name), "reason": REASONS[name]}
            for name in changed
        },
        "benchmark_bytes_unchanged": {
            "pilot-v7-rc3_manifest_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc3" / "manifest.json"
            ),
            "pilot-v7-rc3_qualification_contract_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc3" / "qualification-contract.json"
            ),
            "pilot-v7-rc3_provenance_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc3" / "provenance.json"
            ),
            "pilot-v7-rc3_audit_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc3" / "AUDIT.md"
            ),
            "pilot-v7-rc3_freeze_record_sha256": ir.sha256_of(
                PROJECT_ROOT / "benchmark" / "pilot-v7-rc3" / "freeze-record.json"
            ),
            "qa_policy_default_xml_sha256": ir.sha256_of(
                PROJECT_ROOT / "configs" / "policies" / "default.xml"
            ),
            "note": (
                "No rc3 task YAML, manifest byte, contract byte or scoring "
                "threshold was touched. The rc4 redesign lives entirely under "
                "benchmark/pilot-v7-rc4/ and creates no rc3 byte."
            ),
        },
        "qa_off_treatment_invariant": (
            "treatment_for('off').detailed_evidence remains False and the evidence "
            "guard remains disabled under QA OFF. The failure-event list is raw "
            "protocol telemetry on the same terms as the Phase-M fault provenance: "
            "no tool output, no malformed-response sentinel, no protected value, "
            "no argument VALUE, no SandboxState.operation_log and no "
            "AgentRun.outcomes block is persisted. Argument KEY names appear in "
            "refusal messages, because a contract violation is unreportable "
            "without naming the key that was wrong."
        ),
        "historical_rows": (
            "Committed Phase-D, Phase-F, Phase-I and Phase-L raw rows are neither "
            "rewritten nor re-run. They remain readable under the schema they were "
            "written with, via RAW_FIELDS_BY_SCHEMA_VERSION. Their frozen "
            "analyzers are NOT edited: scripts/phaseM_historical_analysis.py "
            "executes each from the commit that froze it, where the instrument and "
            "adapter constants it imports genuinely are the ones its phase ran "
            "under. That mechanism absorbs the adapter bump unchanged."
        ),
        "superseded_live_assertions": SUPERSEDED_LIVE_ASSERTIONS,
        "frozen_historical_inputs": (
            "This revision changes no prospectively frozen scientific input. Every "
            "binding in every committed provenance record still matches the "
            "working tree, audited by scripts/phaseM_frozen_input_audit.py. The "
            "two Phase-L TREE digests are a separate matter and are handled under "
            "superseded_live_assertions."
        ),
        "frozen_input_audit": "scripts/phaseM_frozen_input_audit.py",
        "historical_analysis_compatibility": "scripts/phaseM_historical_analysis.py",
        "offline_validator": "scripts/instrument_revision.py",
        "offline_tests": "tests/integration/test_phaseO_rc4_redesign.py",
        "model_inference_performed": False,
        "phase_o_execution_authorized": False,
        "authorizes_confirmatory_execution": False,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ir.REVISION_PATH)
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


__all__ = ["PARENT_COMMIT", "REASONS", "SUPERSEDED_LIVE_ASSERTIONS", "build_record"]
