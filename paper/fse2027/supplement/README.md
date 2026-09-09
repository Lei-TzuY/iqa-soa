# Anonymous supplementary material

Companion material for the submission *Who Controls the Agent? Auditable Runtime
Governance and Fail-Closed Evaluation for LLM Agents*.

**The main paper is complete and readable without this supplement.** Nothing here
introduces a result, a statistic, or a claim that the paper does not already
state. Every file records detail that was moved out of the paper body for the
venue page budget, at the level of provenance machinery, full property-to-test
mappings, and the mechanics of an analysis plan that was never executed.

## Anonymity

These files contain no author name, affiliation, email, institutional
identifier, public repository URL, local filesystem path, or Git history. They
are prepared for double-anonymous review.

## Contents

| File | Moved from | Content |
| --- | --- | --- |
| `S1-successor-qualification-provenance.md` | Appendix B | Frozen candidate and benchmark identities, seed derivation, arm order, cell arithmetic, recorded provenance counters, and the additive reclassification record |
| `S2-prospective-confirmatory-analysis-plan.md` | Appendix C | The full prospectively specified confirmatory analysis plan, which was **not executed** |
| `S3-rq1-property-to-test-map.md` | Section 7.1 | Generated Claim--Evidence--Boundary and exact-test map, including explicit nonclaims |
| `S4-extended-reproducibility.md` | Section 11 | Artifact chain layout, digest binding, and the exact validation commands |
| `artifact/claim_evidence_manifest.json` | Section 7.1 | Canonical machine-readable claim, evidence, and boundary manifest |

## Scientific state

Unchanged from the paper, and unchanged by the preparation of this supplement:

| Invariant | Value |
| --- | --- |
| Qualification verdict | HOLD |
| Frozen status table | Generated from retained run and analysis JSON by `make generate-paper-evidence` |
| QA FULL vs QA OFF treatment effect | Not established |

No real-model execution, provider contact, model inference, rerun, rescoring, or
reclassification was performed in preparing this material.
