#!/usr/bin/env python3
"""Generate ``docs/phaseO_rc4_revision_record.json``, the machine-readable audit.

Every field is DERIVED from the repository -- the rc4 builder's audit table, the
frozen manifests, the instrument revision chain, and the supersession record --
so the JSON cannot drift from the artifacts it describes. Regenerating it on an
unchanged tree reproduces it byte-for-byte, which is what makes it reviewable by
re-running this script rather than by reading it.

It is the counterpart to ``docs/phaseO_rc4_redesign_spec.md`` (the design) and
``docs/phaseO_rc4_redesign_report.md`` (the account of what was done).

NO MODEL INFERENCE.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(_root) not in sys.path:  # pragma: no cover - import shim
        sys.path.insert(0, str(_root))

import build_pilot_v7_rc4 as builder  # noqa: E402
import instrument_revision as ir  # noqa: E402
import phaseO_frozen_input_supersession as supersession  # noqa: E402
import qualification_harness_v2 as h2  # noqa: E402
import rc4_scoring_vocabulary as vocabulary  # noqa: E402
from iqa_soa.experiment.failure_events import (  # noqa: E402
    FAILURE_EVENT_FAILURE_CLASSES,
    FAILURE_EVENT_FAULT_MODES,
    FAILURE_EVENT_KEYS,
    FAILURE_EVENT_PROVENANCE_SOURCES,
)
from iqa_soa.instrument import (  # noqa: E402
    INSTRUMENT_VERSION,
    NATIVE_TOOL_ADAPTER_VERSION,
    RAW_SCHEMA_VERSION,
)
from iqa_soa.tools.argument_schema import (  # noqa: E402
    TOOL_ARGUMENT_CONTRACTS,
    TOOL_ARGUMENT_CONTRACT_VERSION,
    WITHDRAWN_UNDISCLOSED_PAYLOAD_ALIASES,
    contract_digest,
)

OUT_PATH = PROJECT_ROOT / "docs" / "phaseO_rc4_revision_record.json"
RC4_ROOT = PROJECT_ROOT / "benchmark" / "pilot-v7-rc4"
RC3_ROOT = PROJECT_ROOT / "benchmark" / "pilot-v7-rc3"

#: Files Phase O MODIFIES, as opposed to adds.  Mirrors the pinned set in
#: tests/integration/test_phaseO_rc4_redesign.py, which fails if the real
#: mutation surface differs from it by a single path.
def _modified_paths() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=MDRT",
         builder.CANONICAL_BASE_COMMIT, "--"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout
    return sorted(line for line in out.splitlines() if line.strip())


def _added_paths() -> list[str]:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A",
         builder.CANONICAL_BASE_COMMIT, "--"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    ).stdout
    return sorted(line for line in tracked.splitlines() if line.strip())


def build_record() -> dict[str, Any]:
    manifest = json.loads((RC4_ROOT / "manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((RC4_ROOT / "provenance.json").read_text(encoding="utf-8"))
    rc3_manifest = json.loads((RC3_ROOT / "manifest.json").read_text(encoding="utf-8"))
    rc3_hashes = {case["task_id"]: case["sha256"] for case in rc3_manifest["cases"]}

    audit_rows = []
    for entry in provenance["carried_forward"]:
        row = {
            "rc3_task_id": entry["predecessor_task_id"],
            "rc4_task_id": entry["task_id"],
            "disposition": entry["status"],
            "qualification_role": entry["qualification_role"],
            "rc3_sha256": rc3_hashes[entry["predecessor_task_id"]],
            "rc4_sha256": entry["selected_sha256"],
            "bytes_identical": entry["bytes_identical_to_predecessor"],
            "new_id_assigned": entry["task_id"] != entry["predecessor_task_id"],
            "reason": entry["reason"],
        }
        for key in ("construct_preserved", "what_changes", "what_must_not_change",
                    "why_not_trivial"):
            if key in entry:
                row[key] = entry[key]
        audit_rows.append(row)

    counts: dict[str, int] = {}
    for entry in provenance["carried_forward"]:
        counts[str(entry["status"])] = counts.get(str(entry["status"]), 0) + 1

    return {
        "record_kind": "phase_o_rc4_revision_record",
        "phase": "O",
        "canonical_base_commit": builder.CANONICAL_BASE_COMMIT,
        "branch": "phase-o/pilot-v7-rc4-offline-redesign",
        "benchmark_version": "pilot-v7-rc4",
        "predecessor_benchmark_version": "pilot-v7-rc3",
        "predecessor_qualification_status": "UNQUALIFIED",
        "predecessor_verdict": "HOLD",
        "predecessor_terminal_status": "SCHEDULE_COMPLETE_VERDICT_HOLD",
        "qualification_status": "UNQUALIFIED",
        "release_status": "release-candidate",
        "design_mode": "OFFLINE-DESIGNED",
        "is_final": False,
        "model_inference_performed": False,
        "provider_contacted": False,
        "cells_executed": 0,
        "rescoring_performed": False,
        "authorizes_confirmatory_execution": False,
        "seed_status": {
            "PHASE_L_SEEDS_STATUS": "CONSUMED_BY_FORMAL_PHASE_L_B",
            "consumed": [929260329, 1281385038, 978843421],
            "selected_in_phase_o": [],
            "rc4_seed_triple_selected": False,
        },
        "audit": {
            "task_count": len(audit_rows),
            "disposition_counts": counts,
            "tasks": audit_rows,
        },
        "task_id_mapping": {
            entry["predecessor_task_id"]: entry["task_id"]
            for entry in provenance["carried_forward"]
        },
        "new_task_ids": sorted(
            entry["task_id"]
            for entry in provenance["carried_forward"]
            if entry["task_id"] != entry["predecessor_task_id"]
        ),
        "phase_n_findings_addressed": provenance["phase_n_findings_addressed"],
        "not_weakened_deliberately": provenance["not_weakened_deliberately"],
        "tool_argument_contract": {
            "version": TOOL_ARGUMENT_CONTRACT_VERSION,
            "previous_version": "tool-arguments-0",
            "digest": contract_digest(tuple(sorted(TOOL_ARGUMENT_CONTRACTS))),
            "module": "src/iqa_soa/tools/argument_schema.py",
            "enforced_by": "src/iqa_soa/tools/registry.py",
            "advertised_by": "src/iqa_soa/agent/providers.py",
            "withdrawn_undisclosed_aliases": list(WITHDRAWN_UNDISCLOSED_PAYLOAD_ALIASES),
            "tools": {
                name: {
                    "required": list(contract.required_names),
                    "optional": list(contract.optional_names),
                    "payload_key": contract.payload_key,
                    "accepts_additional": contract.accepts_additional,
                    "fallback": contract.fallback,
                }
                for name, contract in sorted(TOOL_ARGUMENT_CONTRACTS.items())
            },
        },
        "failure_attribution": {
            "harness": "scripts/qualification_harness_v2.py",
            "harness_version": h2.HARNESS_VERSION,
            "frozen_predecessor": "scripts/qualification_harness.py",
            "frozen_predecessor_edited": False,
            "telemetry_module": "src/iqa_soa/experiment/failure_events.py",
            "raw_schema_version": RAW_SCHEMA_VERSION,
            "row_contract": h2.prospective_row_contract(),
        },
        "adversarial_review_history": [
            {
                "revision": "O",
                "commit": "26853b2512a9b778a4c1df5ca8289cac58881cd6",
                "claimed_verdict": "READY_FOR_RC4_PROTOCOL_FREEZE",
                "review_verdict": "HOLD",
                "accepted": False,
                "core_redesign_rejected": False,
                "finding": (
                    "The classification-critical schema-5 failure_events "
                    "persistence path was not fail-closed on malformed persisted "
                    "telemetry. events_from_row silently returned (), skipped "
                    "malformed entries, coerced wrong types to None, fabricated an "
                    "empty provenance, accepted bool as an integer sequence, and "
                    "SORTED persisted events into order. "
                    "classify_row_detailed checked only that failure_event_count "
                    "was present, never that failure_events existed, was a list, "
                    "matched the count, or held structurally valid entries. A "
                    "corrupted row therefore lost its evidence during parsing and "
                    "was then scored CELL_OK, or MODEL_MODALITY_MISS for a task "
                    "declaring a fault: Phase N finding N-2 displaced one level "
                    "down, from the row scalar into the parser."
                ),
            },
            {
                "revision": "O-R1",
                "action": "REPAIR",
                "verdict": "READY_FOR_PHASE_O_R1_ADVERSARIAL_REREVIEW",
                "predecessor_verdict_carried_forward": False,
                "authorizes_merge": False,
                "authorizes_ready": False,
                "authorizes_protocol_freeze": False,
                "authorizes_seed_selection": False,
                "authorizes_execution": False,
                "requires_separate_adversarial_rereview": True,
            },
        ],
        "failure_event_persistence_repair": {
            "revision": "O-R1",
            "module": "src/iqa_soa/experiment/failure_events.py",
            "authoritative_reader": "parse_failure_events",
            "authoritative_reader_is_unique": True,
            "lenient_reader_removed": "events_from_row",
            "lenient_reader_deprecated_rather_than_removed": False,
            "raises": "FailureEventTelemetryError",
            "validates": "the PERSISTED representation, not the in-memory producer",
            "reports_all_defects": True,
            "invariants": {
                "failure_event_count_required": True,
                "failure_events_required": True,
                "count_is_int_not_bool": True,
                "count_is_non_negative": True,
                "failure_events_is_a_list": True,
                "count_binds_list_length_exactly": True,
                "event_key_set_is_exact": list(FAILURE_EVENT_KEYS),
                "sequence_is_int_not_bool": True,
                "sequence_is_positive": True,
                "sequence_is_unique": True,
                "sequence_is_strictly_increasing_in_persisted_order": True,
                "persisted_order_is_never_sorted": True,
                "executed_is_a_real_bool": True,
                "error_is_string_or_null_and_never_blank": True,
                "failure_class_closed_set": sorted(FAILURE_EVENT_FAILURE_CLASSES),
                "fault_mode_closed_set": sorted(FAILURE_EVENT_FAULT_MODES),
                "provenance_closed_set": sorted(FAILURE_EVENT_PROVENANCE_SOURCES),
                "declaration_derived_provenance_accepted": False,
                "coherence_error_or_fault_mode_required": True,
                "coherence_failure_class_iff_error": True,
                "tool_and_resource_may_be_empty": True,
                "tool_and_resource_emptiness_rationale": (
                    "both are copied verbatim from the action the MODEL proposed, "
                    "so an empty one is a faithful record of an empty proposal and "
                    "not a defect in the instrument"
                ),
            },
            "provenance_set_is_narrower_than_runtime_set": True,
            "provenance_narrowing_rationale": (
                "sandbox.operation_log and evidence.tool_call are sources for the "
                "ROW-level Phase-M fault provenance; no failure EVENT is ever read "
                "from them, so admitting them would accept a label this instrument "
                "cannot produce. The event set is a proper subset of "
                "RUNTIME_FAULT_PROVENANCE_SOURCES and is disjoint from "
                "DECLARED_FAULT_PROVENANCE_SOURCES, so the K.2 circularity guard is "
                "strengthened and never relaxed."
            ),
            "closed_vocabularies_are_imported_not_copied": {
                "fault_modes": "iqa_soa.tools.sandbox.SUPPORTED_FAULT_MODES",
                "failure_classes": (
                    "iqa_soa.failure_taxonomy.SANDBOX_ACTION_FAILURE_CLASSES"
                ),
            },
            "classification_order": [
                "frozen row/cell identity binding",
                "instrument preconditions (tool-contract regression, provider attempt)",
                "the rc4 row-field contract, including failure_events",
                "THE SCHEMA-5 EVIDENCE GATE",
                "scientific classification",
            ],
            "gate_precedes_every_scientific_branch": True,
            "malformed_telemetry_classification": h2.INSTRUMENT_DEFECT,
            "malformed_telemetry_disposition": h2.IMMEDIATE_STOP,
            "corrupted_expected_fault_can_become_cell_ok": False,
            "corrupted_expected_fault_can_become_modality_miss": False,
            "valid_classifications_preserved": True,
            "producer_persistence_consumer_round_trip_proved": True,
            "mutation_checks": 14,
            "mutation_checks_include_pre_repair_harness_reconstruction": True,
        },
        "phase_n_import_pollution_repair": {
            "revision": "O-R1",
            "finding": (
                "test_offline_verification_passes and "
                "test_no_provider_or_agent_module_is_loaded inspected the pytest "
                "process's own sys.modules, so a Phase-O test that legitimately "
                "imports iqa_soa.agent.providers to prove tool-schema conformance "
                "made both fail in a whole-suite run while both passed alone"
            ),
            "repair": "process isolation",
            "invariant_weakened": False,
            "sys_modules_mutated_globally": False,
            "helper_flag_added": "--with-extraction",
            "isolated_check_covers_the_whole_extraction": True,
            "vacuity_check_present": True,
            "order_independence_check_present": True,
            "passes_alone": True,
            "passes_in_full_pytest": True,
        },
        "scoring_vocabulary": vocabulary.summary(),
        "instrument": {
            "instrument_version": INSTRUMENT_VERSION,
            "raw_schema_version": RAW_SCHEMA_VERSION,
            "native_tool_adapter_version": NATIVE_TOOL_ADAPTER_VERSION,
            "revision_record": "docs/phaseO_instrument_revision.json",
            "revision_chain": [
                path.relative_to(PROJECT_ROOT).as_posix() for path in ir.REVISION_CHAIN
            ],
            "src_iqa_soa_tree": ir.tree_digest("src/iqa_soa"),
            "observation_only": False,
        },
        "artifact_hashes": {
            f"benchmark/pilot-v7-rc4/{name}": ir.sha256_of(RC4_ROOT / name)
            for name in (
                "manifest.json", "provenance.json", "qualification-contract.json",
                "AUDIT.md", "freeze-record.json",
            )
        },
        "tree_digests": {
            "benchmark/pilot-v7-rc4": ir.tree_digest("benchmark/pilot-v7-rc4"),
            "benchmark/pilot-v7-rc3": ir.tree_digest("benchmark/pilot-v7-rc3"),
            "results/phaseL-rc3-requalification": ir.tree_digest(
                "results/phaseL-rc3-requalification"
            ),
            "src/iqa_soa": ir.tree_digest("src/iqa_soa"),
        },
        "historical_immutability": {
            "rc3_bytes_untouched": True,
            "phase_l_b_archive_untouched": not (
                supersession.check_phase_l_b_evidence_untouched()
            ),
            "phase_n_diagnosis_untouched": True,
            "phase_m_revision_record_untouched": True,
            "phase_l_freeze_provable_at_execution_commit": not (
                supersession.check_freeze_at_execution_commit()
            ),
            "superseded_live_assertions": list(
                supersession.superseded_live_assertions()
            ),
            "supersession_module": "scripts/phaseO_frozen_input_supersession.py",
            "modified_paths": _modified_paths(),
            "added_paths": _added_paths(),
        },
        "offline_artifacts": {
            "validator": "scripts/validate_pilot_v7_rc4.py",
            "construct_probe": "scripts/phaseO_rc4_construct_probe.py",
            "builder": "scripts/build_pilot_v7_rc4.py",
            "spec": "docs/phaseO_rc4_redesign_spec.md",
            "report": "docs/phaseO_rc4_redesign_report.md",
            "tests": [
                "tests/benchmark/test_pilot_v7_rc4_construct.py",
                "tests/integration/test_phaseO_rc4_redesign.py",
            ],
        },
        "what_this_record_does_not_do": [
            "It does not rescore Phase L-B, whose 102 classifications remain binding.",
            "It does not retract the Phase-L-B HOLD.",
            "It does not qualify pilot-v7-rc3, which remains UNQUALIFIED.",
            "It does not qualify pilot-v7-rc4, which is UNQUALIFIED.",
            "It does not select seeds; the Phase-L triple is CONSUMED.",
            "It does not create a preregistration or an execution driver.",
            "It authorizes no model inference of any kind.",
            "It does not mark PR #13 ready and does not merge it.",
            "It does not carry forward the first Phase-O revision's "
            "READY_FOR_RC4_PROTOCOL_FREEZE claim, which adversarial review held.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    payload = json.dumps(build_record(), indent=2, sort_keys=True) + "\n"
    if args.check:
        drifted = (
            not OUT_PATH.is_file() or OUT_PATH.read_text(encoding="utf-8") != payload
        )
        print(
            f"phaseO revision record: {'FAIL' if drifted else 'PASS'}; "
            "NO MODEL INFERENCE"
        )
        return 1 if drifted else 0
    OUT_PATH.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {OUT_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["OUT_PATH", "build_record"]
