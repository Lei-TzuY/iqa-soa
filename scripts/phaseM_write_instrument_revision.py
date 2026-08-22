#!/usr/bin/env python3
"""Generate the Phase-M approved instrument-revision record.

The record this writes -- ``docs/phaseM_instrument_revision.json`` -- is the
ADDITIVE counterpart to ``benchmark/pilot-v7-rc3/freeze-record.json``.  It does
not replace, edit or overwrite the rc3 freeze record, and in particular it does
not touch the ``src_iqa_soa_tree`` digest Phase K pinned there.  That digest
stays exactly where it is and stays true: it describes the instrument as of the
Phase-K freeze commit, which ``scripts/instrument_revision.py`` now proves from
git history rather than from the working tree.

This record answers the separate question the repository previously could not
answer at all: *if the instrument is no longer that tree, what exactly is it
now, and on whose authority?*

Every field is derived from the repository, not typed by hand; only the
per-file scientific reasons are authored, because only a human can supply
those.  Regenerating this file on an unchanged tree must reproduce it
byte-for-byte, so a reviewer can verify it by re-running this script.

NO MODEL INFERENCE.  This script reads git and the working tree and nothing
else.
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
    PROTOCOL_TELEMETRY_INSTRUMENT_VERSION,
    PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION,
    RAW_SCHEMA_VERSION,
)

#: The canonical Phase-M parent: main at the moment this phase branched, which
#: is the commit that archived the Phase-L-A HOLD.
PARENT_COMMIT = "eace204d4c27a9ca48d3c0a660832f640b7a900b"

#: The Phase-L-A HOLD this revision exists to clear.  Recorded, never rewritten.
PHASE_L_A_HOLD = {
    "commit": PARENT_COMMIT,
    "report": "docs/phaseL_rc3_requalification_freeze_report.md",
    "status": "HOLD_PHASE_L_PROTOCOL",
    "finding": (
        "The Phase-K.2 observed-fault provenance contract could not be satisfied "
        "from any artifact the canonical instrument persisted for a QA-OFF cell: "
        "observed_fault_mode and observed_fault_provenance were unreachable, so "
        "every BUD-016 and FAULT-004 cell would have been classified "
        "UNEXPECTED_SANDBOX_FAILURE -> CELL_INVALID_AND_HOLD before any token was "
        "generated. The HOLD was correct and is NOT retracted; Phase M repairs "
        "the instrument defect the HOLD identified."
    ),
}

#: Why each instrument file changed.  Authored, reviewed, and bound to the
#: file's own SHA-256 by ``instrument_revision.check_approved_instrument_revision``.
REASONS: dict[str, str] = {
    "src/iqa_soa/experiment/fault_provenance.py": (
        "NEW. Derives the four Phase-K.2 observed-fault fields from the live "
        "GatewayOutcome sequence. Its public functions accept "
        "Sequence[GatewayOutcome] and nothing else, so the benchmark declaration "
        "(BenchmarkCase, case.fault, ground_truth, ScriptedFault, the "
        "qualification contract, a task-id fault table) is structurally out of "
        "scope and cannot manufacture an observation it will later be compared "
        "against. Multiple runtime faults collapse by distinct identity and two "
        "or more DISTINCT identities fail closed by withholding all four fields. "
        "The count field is named observed_fault_identity_count, prospectively, "
        "because it counts distinct fault IDENTITIES and not runtime fault "
        "occurrences; no committed artifact carries the field, so the rename "
        "changes no scientific behaviour and no recorded value."
    ),
    "src/iqa_soa/experiment/runner.py": (
        "Stamps the derived fault provenance onto the raw row in _run_one, from "
        "agent_run.outcomes, before the outcomes are discarded; and writes the "
        "schema-4 pilot field set. This is the persistence gap Phase L-A found: "
        "AgentRun.outcomes was never serialized, SandboxState.operation_log "
        "reached disk only inside an irreversible fingerprint, and QA-OFF "
        "evidence is non-detailed by treatment definition. No treatment, guard, "
        "prompt, policy, tool dispatch or metric changed."
    ),
    "src/iqa_soa/instrument.py": (
        "Adds the Phase-M instrument boundary (version 3) and raw schema 4, and "
        "gives every historical version a permanent NAMED constant so a frozen "
        "phase pins the version it actually ran under instead of whichever value "
        "is current. Without that, an additive revision would retroactively fail "
        "committed Phase-D, Phase-F and Phase-I artifacts. "
        "NATIVE_TOOL_ADAPTER_VERSION deliberately does not move: Phase M did not "
        "touch the adapter, and the two boundaries stay independent."
    ),
    "src/iqa_soa/metrics/definitions.py": (
        "Adds FAULT_PROVENANCE_TELEMETRY_FIELDS and PILOT_RAW_FIELDS_V4 as a "
        "strict superset of PILOT_RAW_FIELDS_V3, plus "
        "RAW_FIELDS_BY_SCHEMA_VERSION so a reader selects the field contract a "
        "row was WRITTEN under. No schema-3 field changed name, type or meaning. "
        "The schema-4 count column is named observed_fault_identity_count for "
        "precision; it is a schema-4-only field and no committed row carries it."
    ),
    "src/iqa_soa/metrics/pilot.py": (
        "Accepts every readable pilot raw schema instead of only the current "
        "one, and requires each row to carry the fields of its own schema "
        "version. This is what keeps frozen schema-2 and schema-3 artifacts "
        "analyzable across the revision. The instrument-pooling refusal is "
        "unchanged and now also separates instrument 2 from instrument 3."
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
            "a reason was written for a file that did not change: "
            + ", ".join(unused)
        )
    return {
        "record_kind": "instrument_revision",
        "phase": "M",
        "title": "QA-OFF runtime fault-provenance persistence repair",
        "additive_to": "benchmark/pilot-v7-rc3/freeze-record.json",
        "overwrites_nothing": (
            "The rc3 freeze record is NOT edited. Its src_iqa_soa_tree pin "
            "remains the instrument as of the Phase-K freeze commit and is "
            "verified against git history by scripts/instrument_revision.py, so "
            "the historical assertion stays provable forever."
        ),
        "parent_commit": PARENT_COMMIT,
        "phase_l_a_hold": PHASE_L_A_HOLD,
        "previous_instrument": {
            "freeze_commit": ir.PHASE_K_FREEZE_COMMIT,
            "src_iqa_soa_tree": ir.PHASE_K_SRC_TREE,
            "instrument_version": PROTOCOL_TELEMETRY_INSTRUMENT_VERSION,
            "raw_schema_version": PROTOCOL_TELEMETRY_RAW_SCHEMA_VERSION,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
        },
        "current_instrument": {
            "src_iqa_soa_tree": ir.tree_digest("src/iqa_soa"),
            "instrument_version": INSTRUMENT_VERSION,
            "raw_schema_version": RAW_SCHEMA_VERSION,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
            "adapter_unchanged": True,
        },
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
                "threshold was touched. Phase M is an instrument repair only."
            ),
        },
        "qa_off_treatment_invariant": (
            "treatment_for('off').detailed_evidence remains False and the "
            "evidence guard remains disabled under QA OFF. The repair is raw "
            "protocol telemetry, not evidence-guard activation: no tool output, "
            "no malformed-response sentinel, no protected value, no "
            "SandboxState.operation_log and no AgentRun.outcomes block is "
            "persisted."
        ),
        "historical_rows": (
            "Committed Phase-D, Phase-F and Phase-I raw rows are neither "
            "rewritten nor re-run. They remain readable and analyzable under the "
            "schema they were written with. Their analyzers are NOT edited to "
            "achieve that: Phase M.1 restored every frozen historical script to "
            "its frozen bytes and moved compatibility into "
            "scripts/phaseM_historical_analysis.py, which executes each frozen "
            "script from the commit that froze it, where the instrument constant "
            "it imports genuinely is the one its phase ran under."
        ),
        "frozen_historical_inputs": (
            "This revision changes no prospectively frozen scientific input. "
            "scripts/analyze_phaseI_requalification.py, bound by "
            "results/phaseI-rc2-requalification/phaseI-provenance.json to "
            "2ec5e5f40618e27400a534465d380be0092fb0b0cd1bd013aac562f99f80798e, "
            "still hashes to exactly that in the current tree, as do every other "
            "bound input and every .sha256 sidecar. Audited by "
            "scripts/phaseM_frozen_input_audit.py."
        ),
        "superseded_live_assertions": {
            "scripts/validate_pilot_v7_rc2.py": (
                "The frozen rc2 validator pins src/iqa_soa to the Phase-H "
                "instrument tree and asserts it against the LIVE working tree. "
                "Phase M revises the instrument, so that one claim is now false "
                "in the current tree and remains true at its own commit. Its "
                "bytes are NOT edited; the supersession is recorded in "
                "scripts/phaseM_historical_analysis.py and is required to be "
                "exactly that one assertion. Every other claim the frozen "
                "validator makes still holds live."
            )
        },
        "model_inference_performed": False,
        "phase_l_execution_authorized": False,
        "offline_validator": "scripts/instrument_revision.py",
        "offline_tests": "tests/integration/test_phaseM_fault_provenance_instrument.py",
        "frozen_input_audit": "scripts/phaseM_frozen_input_audit.py",
        "historical_analysis_compatibility": "scripts/phaseM_historical_analysis.py",
    }


def main() -> int:
    record = build_record()
    ir.REVISION_PATH.parent.mkdir(parents=True, exist_ok=True)
    ir.REVISION_PATH.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {ir.REVISION_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
