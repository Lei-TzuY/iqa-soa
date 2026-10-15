# Interpretation of preserved intermediate artifacts

Only `principal_record_decisions.json.gz`, `record_ledger.csv` and `statistical_consequences.json` supply principal Cycle J conclusions. Original experiment labels are never replaced.

- `provisional_v1/` preserves the first scoring implementation/output. Participant list order was incorrectly treated as identity order; these construct labels are excluded. Its independently hash-matched original input/state/tool-result restoration is reused.
- `provisional_v2_1/` preserves the first correction. Two actual and two hypothetical Web labels incorrectly rejected a canonical HTTP-prefix representation. They are excluded; all four original Web observations returned the full named content.
- `rescore_differential.json` and `rescore_execution_summary.json` explain V1 to V2.1 changes, not final empirical discrepancy counts.
- `record_audit_final.jsonl.gz` contains valid emitted-transcript scoring before the conservative output-delivery boundary. Its four Travel3 successes are conditional on treating earlier assistant TextContent as user-facing output. Principal natural-goal labels remain UNKNOWN because original client presentation is not established. Two resulting source false negatives are conditional output-scope comparisons, not verified natural-goal disagreements.
- `final_differential.json` explains the last Web/Travel factual refinement; it does not override the later principal delivery boundary.
- The old Cycle G invalid-V3 audit is unrelated and is never used.

Every refinement is POST-HOC and outcome-aware. Freeze receipts establish ordering and byte integrity within this audit, not external prospective registration or human approval. No human decisions were received.

The executed Windows scripts remain in isolated directories. Exact historical script versions are preserved here. The current generalized reconstruction runner includes the corrected evaluator and rule-binding options but was not rerun over all 144 records; the accepted original restoration and targeted saved-context checks are sufficient. To reproduce the original restoration, copy `runner_v1.py` and `evaluator_v1.py` into a fresh external directory under their historical filenames `run_benign_cycle_j.py` and `benign_construct_cycle_j.py`, with the bound rule/definition files. Run the literal command in the manifest with that fresh output directory. Then use the bound corrected evaluator versions and targeted commands before applying the principal summary boundary. No new provider calls are required.
