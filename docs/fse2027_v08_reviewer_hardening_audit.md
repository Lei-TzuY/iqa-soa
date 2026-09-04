# FSE 2027 v0.8 reviewer-hardening audit

**Audit date:** 2026-09-04
**Audit kind:** manuscript reviewer-hardening + offline mechanism validation + related-work pass — non-executing with respect to any real model
**Canonical repository base:** `0fc01a64ad1a35b220c388c4ca7ec166babe8ce8` (`origin/main`, fresh-fetched and verified equal to local `HEAD`)
**Repository:** `Lei-TzuY/iqa-soa`

**Source manuscript:** `FSE_2027_IQA_SOA_Draft_v0.7.docx`
SHA-256 `2e9f2965e2abdbed33d2e9156c6442e4f3f6b4761b004b8ce07c9c898f8518b6`
(verified before the pass and re-verified unchanged after it)

**Output manuscript:** `FSE_2027_IQA_SOA_Draft_v0.8.docx`
SHA-256 `7dac016014050e75202d940542c2347c1048d13ad6e12256d853c19085273721`

---

## 0. Boundary declaration

This pass wrote one manuscript, two tracked artifacts, and one tracked script. It
contacted no provider, made no Ollama contact, performed no model inference,
executed no candidate, executed no qualification, ran no rerun, retry,
resumption, cell replacement or rescoring, entered no confirmatory execution,
realized no randomization, redesigned no benchmark, engineered no exposure,
adopted no C7 proposal, wrote no result, and created no executable authorization.

It **did** execute deterministic offline software tests, which the task
explicitly permits. Those tests use the repository's offline fixture provider and
reach no network and no model.

Successor qualification remains **`HOLD`**. Confirmatory eligibility remains
**NO**. Confirmatory execution remains **NOT ENTERED**. Rerun remains
**NOT AUTHORIZED**. Route B remains **PARKED_NOT_AUTHORIZED**.

The forbidden namespaces — the historical Phase-P results namespace
`results/phaseP-rc4-qualification/` and the four `FSE-*-schema-clarification`
working directories — were not read, listed, hashed, globbed or opened. No
content from `Lei-TzuY/Quality_Assurance` enters this record.

Nothing under `src/`, `results/`, `benchmark/`, `configs/` or `schemas/` was
modified. No historical governance record was modified. `git status` shows no
modified tracked file.

---

## 1. Precondition verification

| Check | Result |
| --- | --- |
| `git fetch origin main` performed before any edit | PASS |
| `origin/main` == local `HEAD` | PASS — both `0fc01a64ad1a35b220c388c4ca7ec166babe8ce8` |
| Required canonical base matched | PASS |
| Source v0.7 SHA-256 matched required value | PASS |
| v0.7 preserved byte-for-byte after the pass | PASS — hash re-verified identical |
| v0.8 ZIP integrity (`testzip`) | PASS — `None`, 21 entries |
| Forbidden namespaces untouched | PASS |
| Tracked production code unchanged | PASS — `git status` shows no `M` entries |

---

## 2. Human review findings — independent verification (H1–H8)

| ID | Verdict | Evidence found in v0.7 | Action taken in v0.8 |
| --- | --- | --- | --- |
| **H1** Related Work / novelty too thin | **CONFIRMED** | Exactly 9 references, 4 Related Work subsections. No engagement with the closest enforcement systems (guardrail toolkits, privilege control, isolation), none with policy/authorization infrastructure, none with evaluation-validity literature. The "merely a reference monitor for LLM agents" objection had no answer in the text. | Related Work rebuilt into 6 subsections; 16 new verified references added and 1 upgraded from preprint to its peer-reviewed venue; a new §10.4 confronts the objection directly; a novelty positioning table added. |
| **H2** RQ1 evidence prose-heavy | **CONFIRMED** | §7.1 was one 240-word paragraph asserting mechanism properties with no test named, no count, and no artifact. 64 deterministic tests supporting those properties already existed and were uncited. | §7.1 rewritten around a 15-property validation table binding each paper claim to named executable tests and asserted invariants; `docs/fse2027_rq1_mechanism_validation.json` released as the machine-readable map. |
| **H3** Registration terminology conflict | **CONFIRMED** | §6.5 said "The confirmatory analysis was registered in full" three clauses before "no final registration was completed". 46 occurrences of "registered"/"registration" in a document where **no** Stage-A draft, Stage-B eligibility manifest, or Stage-C registration manifest exists on disk. | See §4 below. Terminology split into *prospectively specified design* vs *final Stage-C registration*; "registered in full" removed; occurrences reduced 46 → 20. |
| **H4** Counterfactual overclaim | **CONFIRMED** | §7.7: "Each of those moves **would have produced** a qualifiable candidate and a reportable effect estimate." §8.4: "Every one of those decisions had a cheaper alternative that **would have produced** a publishable effect estimate." | Both narrowed to *could have altered / might have unblocked*, with the guarantee explicitly disclaimed and the interpretability point preserved. See §5. |
| **H5** RQ3 too coarse | **CONFIRMED** | §6.1 RQ3 asked whether limitations "can be attributed to the measurement instrument **rather than** to agent behavior". The paper's own §7.5 states `MODEL_PROTOCOL_INVALID` is the model emitting schema-invalid arguments (model behavior), and §7.6's `RISKY_INSTRUCTION_PROPAGATED` / `UNSUPPORTED_COMPLETION_CLAIM` describe agent behavior. The dichotomy contradicts the evidence. | RQ3 replaced with a separability formulation and made consistent in the Introduction, §6.1 and §7. See §6. |
| **H6** Executed vs designed conflated | **CONFIRMED** | §9 Internal validity: "Treatment assignment **is** persisted prospectively" — no treatment assignment exists. §4.3 and §11 described the confirmatory artifact chain as though the files existed; no `registration_draft.json`, `eligibility_manifest.json`, `registration_manifest.json`, `assignment_manifest.json` or `final_analysis_manifest.json` exists anywhere under `results/`. | Six passages rewritten to separate EXECUTED / IMPLEMENTED-NOT-EXECUTED / PROSPECTIVELY SPECIFIED. See §7. |
| **H7** Defensive repetition | **CONFIRMED** | "not executed" ×10, "was not entered" ×9, "no confirmatory" ×11, "rerun" ×11, "rescored" ×8 across the body, several restating the same limitation within two paragraphs of each other. | Controlled compression in §4.3, §5.1, §6.3, §7.6, §7.7, §8.4, §11; boundary statements kept at Abstract, §6.5, §7.4, §7.5, §7.7, Threats, Conclusion. See §8. |
| **H8** Presentation defects | **CONFIRMED (all four, plus one more found)** | Footer read `FSE 2027 Working Draft v0.4`. Four `DRAFT-ONLY NOTE` tables. `Appendix A. Author-Only Completion Checklist` present. No Data Availability section. Figure 3 drew QA OFF / PARTIAL / FULL as three identical lanes converging on one "Metrics" node. **Additional defect found:** three Threats-to-Validity paragraphs (External validity, Statistical conclusion validity, Observed measurement and protocol limitations) were rendered entirely in bold in v0.7, breaking the bold-label / regular-body pattern used by the others. | All fixed. See §11–§14. |

No finding was rejected. One additional defect (the bold Threats paragraphs) was found and fixed.

---

## 3. RQ1 offline mechanism-validation package

### 3.1 Commands executed

```
python -m pytest -q tests/integration/test_gateway.py
    -> 10 passed in 0.10s

python -m pytest -q tests/integration/test_gateway.py tests/unit/test_qa_xml.py \
    tests/unit/test_qa_guards.py tests/unit/test_evidence_logger.py \
    tests/unit/test_qa_policy.py
    -> 64 passed in 0.23s
```

The full suite was **not** run. No test file was modified and no new test was
added: the existing deterministic tests already covered every property the
manuscript needed, so the gap was in the manuscript, not in the test suite.

| Metric | Value |
| --- | --- |
| Test files executed | 5 |
| Tests executed | 64 |
| Tests passed | 64 |
| Tests failed | 0 |
| Properties mapped | 15 |
| Distinct test functions cited by the map | 19 |
| Real-model cells executed | 0 |

No relevant deterministic test failed, so no manuscript claim had to be
withdrawn, and no implementation defect was discovered. Production code under
`src/` was not touched.

### 3.2 Claim-to-test map

Released as `docs/fse2027_rq1_mechanism_validation.json`
(schema `FSE2027RQ1MechanismValidationV1`, `validation_kind`
`deterministic_offline_software_validation`, `real_model_inference: false`).
Every `result` field was written only after the corresponding test executed.

| # | Property | Test file | Test function(s) |
| --- | --- | --- | --- |
| P01 | Independent mediation of a candidate action; OFF/FULL control-path distinction | `tests/integration/test_gateway.py` | `test_same_unsafe_proposal_executes_off_and_is_blocked_full` |
| P02 | BLOCK prevents the protected side effect | `tests/integration/test_gateway.py` | `test_modified_action_is_reauthorized_before_execution` |
| P03 | A MODIFY rewrite is reauthorized before execution | `tests/integration/test_gateway.py` | `test_modified_action_is_reauthorized_before_execution` |
| P04 | Injection-derived outbound action blocked under parsed QA-XML policy | `tests/integration/test_gateway.py` | `test_parsed_default_policy_intercepts_smoke_injection` |
| P05 | Protected read and outbound protected value blocked without logging the value | `tests/unit/test_qa_guards.py` | `test_privacy_blocks_protected_read_and_outbound_value_without_logging_secret` |
| P06 | Required-evidence preflight fails closed before the side effect | `tests/integration/test_gateway.py` | `test_required_evidence_preflight_fails_before_side_effect` |
| P07 | Post-execution validation contains a malformed tool result | `tests/integration/test_gateway.py` | `test_post_tool_malformed_result_is_contained_after_execution` |
| P08 | Unavailable tool dispatch not recorded as execution | `tests/integration/test_gateway.py` | `test_unavailable_tool_dispatch_is_not_reported_as_execution` |
| P09 | Fault outcome escalates rather than silently succeeding | `tests/integration/test_gateway.py` | `test_usage_counts_only_executed_calls_and_faults_are_caught` |
| P10 | Decorator governs an existing tool proposer without rewriting it | `tests/integration/test_gateway.py` | `test_service_decorator_routes_proposals_without_tool_rewrite` |
| P11 | QA-XML is a closed, schema-enforced policy artifact | `tests/unit/test_qa_xml.py` | `test_closed_schema_rejects_unknown_or_misordered_xml`; `test_rejects_dtd_and_entity_declarations_before_validation`; `test_rejects_direct_contradictory_duplicate_permission` |
| P12 | Ordered guard evaluation with deterministic aggregation | `tests/unit/test_qa_guards.py` | `test_factory_order_enable_disable_and_unknown_rejection`; `test_aggregation_precedence_and_stable_ties` |
| P13 | A faulting guard fails closed | `tests/unit/test_qa_guards.py` | `test_guard_extension_fault_escalates_instead_of_crashing` |
| P14 | Proposer cannot downgrade policy-assigned risk | `tests/unit/test_qa_guards.py` | `test_proposer_cannot_downgrade_high_impact_tool_risk` |
| P15 | Evidence is append-only and records decision, disposition, completeness | `tests/unit/test_evidence_logger.py` | `test_logger_is_exclusive_append_only_and_ids_are_stable`; `test_detailed_event_has_causal_links_completeness_and_redaction`; `test_logger_identity_fields_cannot_be_spoofed` |

All 15 rows: **PASS**.

### 3.3 Interpretation boundary written into the manuscript

§7.1 now carries an explicit two-part limit, so the table cannot be read as an
effect claim:

1. This is software validation, not safety-effect evidence — it says nothing
   about how often a real model proposes an unsafe action or how much harm the
   boundary averts in deployment.
2. The OFF/FULL row is a **control-path distinction over one fixed proposal under
   a deterministic fixture, not a treatment effect**.

`tests/unit/test_qa_policy.py` was executed as part of the 64 but no property was
claimed from it; it is reported in the command record, not in the claim table.

---

## 4. Registration terminology corrections (H3)

### 4.1 The repository's actual lifecycle

Established from `src/iqa_soa/experiment/confirmatory_registration.py`,
`confirmatory_eligibility.py`, and a filesystem check of `results/`:

| Stage | `registration_state` literal | Artifact | Exists on disk? |
| --- | --- | --- | --- |
| Stage A | `REGISTRATION_DRAFT` | `registration_draft.json` | **No** |
| Stage B | `ELIGIBILITY_FROZEN` | `eligibility_manifest.json` | **No** |
| Stage C | `FINAL_REGISTRATION_FROZEN` | `registration_manifest.json` | **No** |

The Stage-A/B/C machinery is **implemented** (`freeze_final_registration`,
`RegistrationManifest`, `REGISTRATION_MANIFEST_SCHEMA_VERSION =
"RegistrationManifestV1"` are all present in `src/`). No instance of any of the
three artifacts exists. Therefore: the analysis design was fixed prospectively;
**final registration was never completed**. Both statements are true and the
manuscript must not blur them.

### 4.2 Changes made

| Location | Before | After |
| --- | --- | --- |
| §6.5 | "The confirmatory analysis **was registered in full** … no final registration was completed." | "The confirmatory analysis design **was specified prospectively and in full** … **Prospective specification is not the same thing as final registration, and the distinction matters here.**" followed by the explicit three-stage statement and "none of the three stages was ever reached". |
| §6.2 | "The registration procedure … **is fixed in advance**." | "…**is specified in advance and implemented in the repository, but no stage of it has been executed**." Closes with "No registration draft, eligibility manifest, or final registration manifest exists." |
| §5.4 | Stage A/B/C described in bare present tense. | Added: "That is the lifecycle **as specified and implemented**; in this study nothing beyond qualification was entered, so **no stage of it has been executed**." |
| §6.4 lead | "The endpoints marked as **registered** were fixed prospectively…" | "The endpoints below were fixed prospectively, **before any outcome data existed**…" |
| §6.4 metrics table | "Unsafe-action execution rate (**registered** primary endpoint)"; "**Registered prospectively**; not measured…" (×4 rows) | "(**prospectively specified** primary endpoint)"; "**Specified prospectively**; not measured…" |
| §6.2 table | "Reserved for the **registered** confirmatory contrast" | "Reserved for the **prospectively specified** confirmatory contrast" |
| Introduction | "The QA FULL versus QA OFF contrast remains **registered**, unexecuted" | "…remains **prospectively specified**, unexecuted" |
| §7.7 | "the confirmatory analysis was **registered** as conditional" | "…was **specified** as conditional" |
| Appendix C | "The analysis … was **registered** before any real-model data existed"; "The **registered** estimand"; "**Registered** task count and randomization machinery"; "No value of K has been **registered**" | "…was **specified** before…"; "The **pre-specified** estimand"; "**Task count** and randomization machinery"; "No value of K has been **fixed, because no Stage-C final registration was completed**" |

Occurrences of "registered"/"registration" in the body: **46 → 20**. The
surviving occurrences are either lifecycle-stage names, the phrase "final
registration was not completed", or descriptions of what a future confirmatory
study *would* register.

**The fact that the analysis machinery was defined before any outcome data
existed is not weakened anywhere.** §6.5 states it directly, Appendix C states it
twice, and §10.5 now frames it against the registered-reports literature.

---

## 5. Counterfactual claims narrowed (H4)

| Location | v0.7 | v0.8 |
| --- | --- | --- |
| §7.7 | "Each of those moves **would have produced a qualifiable candidate and a reportable effect estimate**, and each would have made that estimate uninterpretable." | "Each of those moves **could have altered the qualification outcome or unblocked the downstream analysis; none of them was guaranteed to produce a qualifiable candidate, and none is claimed here to have been.** What each **would reliably have done is compromise the interpretability** of whatever inference followed, because the change would have been selected in view of the outcome it was meant to repair." |
| §8.4 | "Every one of those decisions had a cheaper alternative that **would have produced a publishable effect estimate**." | "Every one of those decisions had a cheaper alternative that **might have unblocked the confirmatory stage. None of the alternatives was guaranteed to yield a qualifiable candidate, and any that did would have yielded an estimate whose interpretation was already compromised.**" |

The methodological point — that a post-outcome change contaminates
interpretation — is preserved verbatim in both places. Neither passage now
asserts that rerunning, threshold changes, reclassification, or benchmark editing
was guaranteed to yield qualification or a publishable effect.

Contextual scan of the final v0.8: `"would have produced"` — **0 hits**;
`"publishable effect"` — **0 hits**.

---

## 6. RQ3 replaced (H5)

**OLD_RQ3 (v0.7 §6.1):**

> RQ3 — Failure and measurement diagnosis. Which provider, protocol, measurement,
> and task-reachability limitations does the qualification process surface, and
> can they be attributed to the measurement instrument rather than to agent
> behavior?

**NEW_RQ3 (v0.8 §6.1):**

> RQ3 — Failure and measurement diagnosis. Can prospective qualification
> distinguish provider-infrastructure, model-protocol, measurement, and
> task-reachability limitations from one another, and keep each of them distinct
> from a safety outcome? The question is deliberately not whether a limitation
> belongs to the measurement instrument rather than to agent behavior. That
> dichotomy does not survive contact with the evidence: a model-protocol
> invalidity is model behavior that nonetheless invalidates a cell, and several
> of the refined diagnostic classes record agent behavior while recording no
> exposure. What qualification must do is keep these categories separately
> reportable, so that an infrastructure failure, an invalid tool call, a
> measurement limitation, and an unreached risky route are never summed into a
> single safety-relevant count.

The new formulation admits `PROVIDER_INFRA_FAILURE`, `MODEL_PROTOCOL_INVALID`,
the refined measurement diagnostic classes, and zero-exposure/reachability
outcomes as four separate reportable categories, which is exactly what §7.4–§7.6
report.

**Consistency propagated to:** Introduction RQ summary (rewritten to the
separability wording), §6.1 (full replacement above), §7.4/§7.5/§7.6 (already
consistent — they report the four categories separately and were left intact),
§9 "Observed measurement and protocol limitations" (already consistent).
Conclusion needed no change: it does not restate RQ3.

---

## 7. Executed vs designed corrections (H6)

Three states are now distinguished consistently: **executed in this paper**,
**implemented but not executed**, and **prospectively specified for future
confirmatory use**.

| Location | Before (reads as executed) | After |
| --- | --- | --- |
| §4.3 ¶1 | "The post-Phase-P confirmatory path additionally **separates** scientific lifecycle artifacts: a registration draft, eligibility manifest, final registration manifest, …" | "The confirmatory path **is implemented so that** scientific lifecycle artifacts stay separable … **None of those artifacts exists, because no confirmatory study was entered; what this paper reports about them is the design and the implementation, not an execution.**" |
| §4.3 ¶2 | "A confirmatory study **will use** a separate registered evidence namespace…" | "A confirmatory study **would use** a separate evidence namespace, frozen runtime identities, prospective assignment, and the analysis plan fixed in advance…" |
| §5.4 | Stage A/B/C in bare present tense. | Added explicit "no stage of it has been executed" (see §4.2). |
| §9 Internal validity | "**Treatment assignment is persisted prospectively**; eligibility is frozen before outcomes are available." | "**The confirmatory implementation is designed to** … persist treatment assignment prospectively, freeze eligibility before any outcome is available … **None of those mechanisms was exercised in this study, because no treatment was assigned and no confirmatory matrix was entered. The controls actually exercised here are the qualification-stage ones:** frozen candidate, benchmark, policy and scoring identities; an exactly-once schedule with a zero retry budget; and recorded invalidation reasons." |
| §9 Statistical conclusion validity | "The registered confirmatory analysis therefore **constructs** one task-level difference…" | "The prospectively specified confirmatory analysis **is therefore designed to construct** … That analysis has not been run…" |
| §9 Researcher degrees of freedom | "…**persisting** prospective randomization/assignment, and publishing non-overwriting execution and final-analysis artifacts." | "…**The staged separation and the prospective randomization and assignment machinery are implemented but unexercised, since no stage beyond qualification was entered.**" |
| §11 Reproducibility | "The confirmatory chain **stores** registration_draft.json, … in non-overwriting namespaces." | "The confirmatory chain **is implemented to store** … **That chain has never been run, so none of those files exists and the replication package contains none of them.**" |
| §12 Future Work | "…may **the registered plan** summarized in Appendix C be executed…" | "…may **the plan** summarized in Appendix C **be registered and executed**, and it must then be executed **as specified**…" |

Contextual scan of the final v0.8: `"treatment assignment is"` — **0 hits**.

---

## 8. Defensive repetition compression (H7)

| Phrase | v0.7 | v0.8 |
| --- | --- | --- |
| "registered" / "registration" | 46 | 20 |
| "rerun" | 11 | 8 |
| "rescored" | 8 | 6 |
| "no QA" | 8 | 6 |
| "not executed" | 10 | 9 |
| "no confirmatory" (prose only; the §7.7 status table accounts for 5 more) | 7 | 7 |

Sentences removed as locally redundant:

- §4.3 — the second restatement that successor rows were "neither repaired,
  rescored, nor pooled" inside the same paragraph as the Phase-P statement.
- §5.1 — "Both outcomes are preserved rather than repaired, **rerun, rescored, or
  converted into a QA effect**" → "Both outcomes are preserved rather than
  repaired"; the full list survives in §7.7 where it is load-bearing.
- §6.3 — "The two arms are not compared, ranked, or pooled anywhere in this
  paper." (§7.5 and §7.7 both already say it).
- §7.6 — closing sentence duplicating the post-hoc-reclassification warning that
  §8.5 develops at length and §9 lists as a limitation.
- §7.7 — "and none is reported anywhere in this paper" trailing clause.
- §11 — "It contains no confirmatory evidence, because none was produced."
  (superseded by the new Data Availability section, which states it once,
  precisely).
- Appendix C — the closing banner reduced from "NOT EXECUTED. NO CONFIRMATORY
  RESULT EXISTS." to "NOT EXECUTED." (the full banner still opens the appendix).

**Boundaries deliberately kept** at the Abstract, §6.5, §7.1, §7.4, §7.5, §7.7,
§8.4, §8.6, all of §9, §11, Conclusion, Data Availability and Appendix C. No
scientific boundary was deleted. The scan in §15 confirms nothing became an
overclaim.

---

## 9. Abstract

| | Words |
| --- | --- |
| v0.7 | **335** |
| v0.8 | **258** |

Target 220–260: met. The abstract now reaches the 102-cell result by sentence
nine and states HOLD explicitly. Negative disclaimers were reduced from six
separate statements to two: one sentence establishing that no QA-ON treatment
effect is claimed, and one stating that nothing was rerun, rescored, or
reclassified. HOLD is not hidden; it appears in the same sentence as the verdict
consequence.

---

## 10. Related Work and novelty positioning (H1)

### 10.1 Counts

| | Value |
| --- | --- |
| OLD_REFERENCE_COUNT | **9** |
| NEW_REFERENCE_COUNT | **25** |
| New references added | **16** |
| Existing references corrected | **1** ([5] Agent Security Bench: `arXiv:2410.02644` → ICLR 2025 peer-reviewed version) |
| Related Work subsections | 4 → **6** |
| RELATED_WORK_STATUS | **VERIFIED** (web access available; every entry checked against a primary source) |

### 10.2 Verification table for every newly added or corrected reference

Every row was verified against the venue proceedings page, ACL Anthology, USENIX,
NDSS, dblp, or the official arXiv abstract page. No entry was written from
memory. No bibliographic field was invented.

| # | Reference | Venue / status | Verification source |
| --- | --- | --- | --- |
| [5] *corrected* | H. Zhang, J. Huang, K. Mei, Y. Yao, Z. Wang, C. Zhan, H. Wang, Y. Zhang. "Agent Security Bench (ASB)…" | **ICLR 2025** (was cited as arXiv preprint) | ICLR 2025 proceedings PDF; title page reads "Published as a conference paper at ICLR 2025"; author list and affiliations read directly from the PDF. OpenReview `id=V4y0CpX4hK` |
| [10] | C. E. Jimenez, J. Yang, A. Wettig, S. Yao, K. Pei, O. Press, K. Narasimhan. "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?" | ICLR 2024 | `proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html` |
| [11] | Y. Liu, Y. Jia, R. Geng, J. Jia, N. Z. Gong. "Formalizing and Benchmarking Prompt Injection Attacks and Defenses." | USENIX Security 2024 | `usenix.org/conference/usenixsecurity24/presentation/liu-yupei`; arXiv:2310.12815 comments field reads verbatim "Published in USENIX Security Symposium 2024" |
| [12] | Q. Zhan, Z. Liang, Z. Ying, D. Kang. "InjecAgent…" | Findings of ACL 2024, pp. 10471–10506 | ACL Anthology `2024.findings-acl.624`; DOI 10.18653/v1/2024.findings-acl.624 (title, authors, pages, DOI all read from the Anthology page) |
| [13] | M. Andriushchenko, A. Souly, M. Dziemian, D. Duenas, M. Lin, J. Wang, D. Hendrycks, A. Zou, Z. Kolter, M. Fredrikson, Y. Gal, X. Davies. "AgentHarm…" | ICLR 2025 | `iclr.cc/virtual/2025/poster/32106` (full ordered author list read from the poster page) |
| [14] | Y. Ruan, H. Dong, A. Wang, S. Pitis, Y. Zhou, J. Ba, Y. Dubois, C. J. Maddison, T. Hashimoto. "Identifying the Risks of LM Agents with an LM-Emulated Sandbox." | ICLR 2024 | `proceedings.iclr.cc/paper_files/paper/2024/hash/7274ed909a312d4d869cc328ad1c5f04-Abstract-Conference.html` (ordered author list read from the proceedings page) |
| [15] | Y. Falcone, S. Krstić, G. Reger, D. Traytel. "A Taxonomy for Classifying Runtime Verification Tools." | STTT 23(2):255–284, 2021 | dblp `journals/sttt/FalconeKRT21`; Springer DOI 10.1007/s10009-021-00609-z |
| [16] | F. B. Schneider. "Enforceable Security Policies." | ACM TISSEC 3(1):30–50, 2000 | ACM DL DOI 10.1145/353323.353382 |
| [17] | Ú. Erlingsson, F. B. Schneider. "SASI Enforcement of Security Policies: A Retrospective." | NSPW 1999, pp. 87–95 | ACM DL DOI 10.1145/335169.335201; NSPW 1999 proceedings listing |
| [18] | R. Pang, R. Caceres, M. Burrows, Z. Chen, P. Dave, N. Germer, A. Golynski, K. Graney, N. Kang, L. Kissner, J. L. Korn, A. Parmar, C. D. Richards, M. Wang. "Zanzibar: Google's Consistent, Global Authorization System." | USENIX ATC 2019, pp. 33–46 | `usenix.org/conference/atc19/presentation/pang` |
| [19] | T. Rebedea, R. Dinu, M. Sreedhar, C. Parisien, J. Cohen. "NeMo Guardrails…" | EMNLP 2023: System Demonstrations | ACL Anthology `2023.emnlp-demo.40`; dblp `conf/emnlp/RebedeaDSPC23` |
| [20] | Y. Wu, F. Roesner, T. Kohno, N. Zhang, U. Iqbal. "IsolateGPT: An Execution Isolation Architecture for LLM-Based Agentic Systems." | NDSS 2025 | dblp `conf/ndss/WuRK0025`; NDSS proceedings PDF `6A-f1131-Wu.pdf` |
| [21] | E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, F. Tramèr. "Defeating Prompt Injections by Design." | **Preprint**, arXiv:2503.18813 (v2, 24 Jun 2025) | arXiv abstract page checked directly: no journal reference, comments field reads only "Updated version with newer models and link to the code" — **no peer-reviewed version exists**; cited as a preprint and labelled as such in the reference list |
| [22] | T. Shi, J. He, Z. Wang, H. Li, L. Wu, W. Guo, D. Song. "Progent: Securing AI Agents with Privilege Control." | **Preprint**, arXiv:2504.11703 (v3) | arXiv abstract page checked directly: no Comments or Journal-reference field indicating a venue — **no peer-reviewed version exists**; cited as a preprint and labelled as such |
| [23] | I. D. Raji, E. M. Bender, A. Paullada, E. Denton, A. Hanna. "AI and the Everything in the Whole Wide World Benchmark." | NeurIPS 2021 Datasets & Benchmarks Track | `datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/084b6fbb10729ed4da8c3d3f5a3ae7c9-Abstract-round2.html` |
| [24] | S. Kapoor, B. Stroebl, Z. S. Siegel, N. Nadgir, A. Narayanan. "AI Agents That Matter." | **Preprint**, arXiv:2407.01502 | arXiv abstract page checked directly: no journal reference, no venue comment — **no peer-reviewed version exists**; cited as a preprint and labelled as such |
| [25] | N. A. Ernst, M. T. Baldassarre. "Registered Reports in Software Engineering." | Empirical Software Engineering 28(2):55, 2023 | dblp `journals/ese/ErnstB23`; DOI 10.1007/s10664-022-10277-5 |

**NEW_REFERENCES_VERIFIED: 17** (16 new + 1 corrected).

Three of the seventeen are preprints ([21] CaMeL, [22] Progent, [24] AI Agents
That Matter). Each was checked on its arXiv abstract page for a journal
reference or venue comment and none exists; each is substantively relevant
(the first two are the closest comparable enforcement systems, the third is the
most-cited critique of agent-evaluation practice); each is explicitly labelled
"Preprint" in the reference list.

### 10.3 Coverage across the requested families

| Family | Covered by |
| --- | --- |
| A. Tool-using LLM agents | [1] ReAct, [2] Toolformer |
| B. Prompt-injection / agent-security benchmarks | [3] Greshake et al., [4] AgentDojo, [5] ASB, [6] R-Judge, [11] Liu et al., [12] InjecAgent, [13] AgentHarm |
| C. Runtime monitoring / runtime verification | [7] Leucker & Schallhart, [15] Falcone et al. |
| D. Reference monitors / complete mediation / policy enforcement | [8] Saltzer & Schroeder, [16] Schneider, [17] Erlingsson & Schneider |
| E. Policy-as-code / authorization middleware | [18] Zanzibar |
| F. LLM-agent guardrails and tool authorization | [19] NeMo Guardrails, [21] CaMeL, [22] Progent |
| G. Sandboxing / capability control for agents | [14] ToolEmu, [20] IsolateGPT |
| H. SE evaluation of LLM agents | [10] SWE-bench |
| I. Provenance / auditable agent execution | Not separately cited — the audit-record contribution is argued from the implementation and §7.1 rather than from a claimed gap in the literature. Recorded as a residual risk in §16. |
| J. Evaluation methodology / benchmark validity | [23] Raji et al., [24] Kapoor et al., [25] Ernst & Baldassarre |

### 10.4 Novelty positioning

The new §10.4 answers the anticipated objection head-on rather than deflecting
it. Its key move is to **concede** the architectural point:

> "These systems and IQA-SOA share a premise — that a probabilistic component
> should not be the sole authority over external effects — and that architectural
> family is common ground rather than something we claim to have originated. Our
> position is therefore not that runtime mediation of agent actions is new."

and then locate the contribution precisely:

> "A reviewer is entitled to ask whether the first of these amounts to policy
> middleware applied to LLM agents. Taken alone, the mediation layer largely is —
> reusing a well-understood boundary is the point, not an oversight. The claim
> this paper's evidence actually carries is the second and third."

A comparison table was added to §10.6 with five dimensions comparable from the
cited sources' own descriptions: independent runtime mediation of tool actions;
executable policy artifact separate from the model; enforcement before the
external side effect; per-decision audit record as a stated contribution;
prospective instrument qualification gating effect claims.

**Anti-straw-man measures taken.** The caption states explicitly that a dash
means the dimension *is not a claimed contribution of the cited work*, not that
the system would be incapable of it, and adds "several of these systems record
execution traces or could be extended to gate an evaluation, and nothing here
should be read as asserting a deficiency their authors did not discuss." An
initial draft row for the agent-security benchmarks would have shown dashes in
all five columns; it was **removed**, because those works evaluate agents rather
than mediate them and the dimensions do not apply — marking them absent would
have been exactly the straw-man the task forbids. The caption records their
deliberate absence and why.

---

## 11. Figure 3

**FIGURE3_STATUS: UPDATED.**

Defect confirmed by rendering v0.7's `word/media/image3.png`: QA OFF, PARTIAL QA
and QA FULL were drawn as three visually identical lanes — same box style, same
"Same Model + Same Provider" → "Execution Trace" chain — all converging into a
single "Metrics: Safety / Utility / Overhead / Evidence" node. A reader could
reasonably infer that all three lanes produced real-model measurements. Only QA
OFF did.

Replacement generated by a new reproducible script,
`scripts/render_fse_route_a_figure3.py`, from declared label constants. The
script reads no result file, contacts no provider, and derives nothing from
evidence rows; its module docstring records the frozen scientific state it
mirrors.

Visual semantics now encode execution status:

| Lane | Rendering | Badge |
| --- | --- | --- |
| QA OFF | Solid heavy stroke, filled; terminates at "Verdict HOLD — 102/102 observed, 0 retries, 3 invalidated, 7/17 roles" | **EXECUTED IN THIS PAPER** |
| PARTIAL QA | Dashed grey stroke, unfilled; stages read "No real-model execution" / "No measurements produced" | IMPLEMENTED - NOT EXECUTED UNDER A REAL MODEL |
| QA FULL | Dashed grey stroke, unfilled; same terminal stages | IMPLEMENTED - PROSPECTIVELY SPECIFIED CONFIRMATORY PATH - NOT EXECUTED |

The shared "Metrics" sink was removed. The executed lane now terminates at a
**"Confirmatory gate CLOSED (eligibility: no)"** node, from which a dashed edge
leads to **"QA FULL vs QA OFF effect estimate — NOT PRODUCED"**. An in-figure
note states the solid/dashed convention.

The Figure 3 caption was rewritten to match. Figures 1 and 2 were inspected and
left byte-identical — no defect was found in either.

---

## 12. Presentation fixes (H8)

| Item | Before | After |
| --- | --- | --- |
| Footer | `FSE 2027 Working Draft v0.4  |  Page N` | `FSE 2027 Working Draft v0.8  |  Page N` — **CORRECTED** |
| Front-matter version line | "Working Draft v0.7 (Route-A reframe)" | "Working Draft v0.8 (Route-A reviewer-hardening pass)" |
| `DRAFT-ONLY NOTE` blocks | **4** (front matter, §5.4, §7 opener, Appendix A) | **0** |
| `Appendix A. Author-Only Completion Checklist` | Present (heading + note table + 10 bullets) | **Removed** — see §12.1 |
| Data Availability section | Absent | **Present, immediately after Conclusion and before References** |
| Threats bold rendering | 3 paragraphs fully bold (External validity, Statistical conclusion validity, Observed measurement and protocol limitations) — pre-existing v0.7 defect | All 7 Threats paragraphs normalized to bold label + regular body |
| Table captions | The two new tables initially had no caption format | Styled to match the manuscript's existing figure-caption format (centred, bold, 8.5 pt) |
| Reference formatting | New entries [10]–[25] initially inherited body size | Matched to the existing 9 pt hanging-indent reference format |
| Author-identifying metadata | `dc:creator` = `python-docx`, `cp:lastModifiedBy` empty | Unchanged — no author identity present |

### 12.1 Content preserved from the removed Appendix A

Ten of its eleven checklist items are already stated in the manuscript body (§6.6
workflow list, §7.7, §12) or discharged by this pass. The two that remain live
project management, recorded here so nothing is lost:

1. **Convert to the official FSE/ACM submission template**, confirm current
   page/anonymization rules, and prepare the anonymized replication package
   without exposing author-identifying metadata. → still open; see §13.
2. **Obtain a candidate that satisfies QA-OFF qualification** before any Stage-A
   registration draft is finalized; do not reuse Phase-P rows or successor
   qualification rows as confirmatory evidence. → still open, and stated in the
   manuscript body at §12 Future Work.

Item 8 of the old checklist — "Expand Related Work systematically across
FSE/ICSE/ASE, security, runtime verification, and LLM-agent venues; verify every
bibliographic entry" — is **discharged by this pass** (§10 above). This also
closes gap **G7** of `docs/fse2027_post_successor_manuscript_gap_audit.md`.

---

## 13. Page-budget assessment for the next pass

Measured in the current content-first format (US Letter, single column, 6.9 in
text width), rendered through Word:

| | v0.7 | v0.8 |
| --- | --- | --- |
| Pages | 19 | **21** |
| Words (Word count) | 10,887 | **12,923** |

Word split for v0.8 (paragraph text; the 11 tables add ≈1,570 words):

| Section | Words | | Section | Words |
| --- | --- | --- | --- | --- |
| Abstract | 280 | | 8. Discussion | 1,136 |
| 1. Introduction | 1,099 | | 9. Threats to Validity | 789 |
| 2. Problem Setting | 398 | | 10. Related Work | 1,327 |
| 3. Architecture | 522 | | 11. Reproducibility | 207 |
| 4. Implementation | 454 | | 12. Future Work | 288 |
| 5. Benchmark Construction | 561 | | 13. Conclusion | 330 |
| 6. RQs and Evaluation Design | 929 | | Data Availability | 209 |
| 7. Results | 1,347 | | References | 839 |
| | | | Appendices B + C | 688 |

**FSE 2027 Research Track limit: 18 pages of text and figures, plus 4 pages of
references, single-column ACM `acmsmall` review/anonymous format.**

Estimate against that limit. Body content excluding references and appendices is
≈9,970 paragraph words plus ≈1,570 table words ≈ **11,540 words**. At the
≈600 words/page that `acmsmall` typically achieves, that is ≈19 pages of text
alone, before the three figures (≈1.2 pages) and the vertical overhead of 11
tables (≈2–3 pages beyond their word count). **Realistic estimate: 22–25 pages
against an 18-page limit — roughly 4–7 pages over.** References at 839 words
will fit comfortably inside the separate 4-page allowance (≈1.5 pages).

Sections likely to dominate the official budget, in order:

1. **§7 Results (1,347 words + the 15-row RQ1 table + 3 result tables)** — the
   RQ1 table is the single largest new object.
2. **§10 Related Work (1,327 words + the 6-column novelty table)**.
3. **§8 Discussion (1,136 words across six subsections)** — §8.3 and §8.5 overlap
   materially with §7.7 and §9.
4. **§6.4 metrics table (11 rows)** — four of its rows now say only "specified
   prospectively; not measured in this paper".
5. **§1 Introduction (1,099 words)**.

Material that should move to the artifact/supplement if the trim is needed:

- **Appendix B and Appendix C (688 words)** → supplement. Appendix C's value is
  as a prospectively fixed artifact, which the replication package can carry.
- **The "Observed invariant" column of the RQ1 table** → the released JSON
  already carries it verbatim; the body table could keep Property / Test /
  Result and cite the artifact. This alone recovers roughly a page.
- **The unmeasured rows of the §6.4 metrics table** → compress to one sentence
  plus a supplement pointer.
- **§8.3 and §8.5** → merge; both argue that qualification must precede effect
  estimation.

**No scientifically necessary content was deleted in this pass to pre-empt a page
limit that cannot be measured outside the real template.** The trim is scoped and
recorded for the template pass, where it can be measured rather than guessed.

---

## 14. Files changed or created

**TRACKED_FILES_CHANGED_OR_CREATED: 3 (all new, all unstaged)**

| File | Status | Purpose |
| --- | --- | --- |
| `docs/fse2027_v08_reviewer_hardening_audit.md` | new | this record |
| `docs/fse2027_rq1_mechanism_validation.json` | new | RQ1 claim-to-test map |
| `scripts/render_fse_route_a_figure3.py` | new | reproducible Figure 3 generation |

No focused test file was needed: the existing deterministic tests already
covered all 15 claimed properties, so no RQ1 software-validation gap remained to
close. This keeps the pass within the allowed-file budget with one file to spare.

**Untracked and gitignored (not staged, not committed):**

- `FSE_2027_IQA_SOA_Draft_v0.8.docx` — DOCX files are gitignored (`.gitignore`, `*.docx`)
- `build/figures/fse_route_a_figure3.png` — `build/` is gitignored

**Not changed:** anything under `src/`, `results/`, `tests/`, `benchmark/`,
`configs/`, `schemas/`; every existing document in `docs/`; `findings.md`;
`progress.md`; `task_plan.md`; `FSE_2027_IQA_SOA_Draft_v0.1`–`v0.7.docx`.

`git diff --check` — clean. `git status --porcelain` shows no modified tracked
file. Nothing was staged, committed, pushed, merged, tagged, or turned into a PR.

---

## 15. Validation results

### 15.1 Integrity

| Check | Result |
| --- | --- |
| Canonical main still `0fc01a64ad1a35b220c388c4ca7ec166babe8ce8` | PASS |
| v0.7 SHA-256 still `2e9f2965…8518b6` | PASS |
| v0.8 ZIP integrity | PASS (`testzip()` → `None`, 21 entries) |
| v0.8 opens cleanly in Word | PASS (rendered to PDF by Word without warning) |
| Figures 1 and 2 byte-identical to v0.7 | PASS |
| Figure 3 replaced with the generated image | PASS (SHA-256 of the embedded PNG equals the generated file) |
| Styles preserved | PASS (Heading 1/2, Normal, List Bullet, List Number, Table Grid; two intentional fixes recorded in §12) |
| Author-identifying metadata | NONE (`dc:creator` `python-docx`, `cp:lastModifiedBy` empty, no `Company`/`Manager`) |

### 15.2 Visual QA — every page inspected

v0.8 was rendered to PDF through Word and rasterized to 21 page images at 110 dpi;
all 21 were inspected individually.

| Requirement | Result |
| --- | --- |
| No clipping | PASS |
| No overlap | PASS |
| No broken tables | PASS — the 15-row RQ1 table paginates cleanly with its header row repeating |
| No missing glyphs | PASS (em dashes, curly quotes, `Ú`, `è`, `ć`, `ì`, `—` all render) |
| No stale v0.4 footer | PASS — every page footer reads `FSE 2027 Working Draft v0.8` |
| No visible DRAFT-only note | PASS |
| No author-only checklist | PASS |
| Figure 3 legible and semantically correct | PASS |

Two layout defects were found during visual QA and fixed before the final build:
the RQ1 table's long `snake_case` test identifiers initially forced an unusable
column balance (fixed with a fixed table layout plus zero-width break
opportunities, which do not alter the visible text), and inserted paragraphs
initially lacked the manuscript's first-line indent and reference type size
(both matched to the existing formatting).

**DOCX_RENDER_VISUAL_QA: PASS**

### 15.3 Contextual phrase scan

| Pattern | Hits in v0.8 | Disposition |
| --- | --- | --- |
| `QA improves safety` | 0 | — |
| `qualification passed` | 0 | — |
| `candidate qualified` | 0 | — |
| `near pass` | 0 | — |
| `partial pass` | 0 | — |
| `globally safer` | 1 | **Reviewed — acceptable.** §7.5: "neither is evidence that one provider or model **is globally safer or better than the other**." An explicit negation. |
| `registered in full` | 0 | — |
| `would have produced` | 0 | — |
| `publishable effect` | 0 | — |
| `significant` | 0 | — |
| `p =` | 0 | — |
| `confidence interval` | 0 | — |
| `treatment assignment is` | 0 | — |
| `TBD` | 0 | — |
| `DRAFT-ONLY` | 0 | — |
| `Author-Only` | 0 | — |
| `v0.4` | 0 | — |

All three occurrences of "safer" in v0.8 were read in context and all three are
negations ("neither is evidence that one provider or model is globally safer…";
"neither arm is described here as safer or better than the other"; "we do not
claim, evidence that IQA-SOA makes LLM agents safer").

### 15.4 Scientific-state invariants

| Invariant | v0.8 | Result |
| --- | --- | --- |
| Successor qualification verdict | HOLD | PASS |
| Terminal status | `SCHEDULE_COMPLETE_VERDICT_HOLD` | PASS |
| Scheduled / observed cells | 102 / 102 | PASS |
| Retries | 0 | PASS |
| Invalidated cells | 3 (1 `PROVIDER_INFRA_FAILURE`, 2 `MODEL_PROTOCOL_INVALID`) | PASS |
| Qualified task roles | 7 / 17 | PASS |
| Unqualified task roles | 10 / 17 | PASS |
| Confirmatory eligibility | No | PASS |
| Confirmatory execution | Not entered | PASS |
| Final registration completed | No | PASS |
| C7 adopted | No | PASS |
| Route B | Parked, not authorized | PASS |
| Historical Phase-P candidate | HOLD / UNQUALIFIED, unchanged | PASS |

### 15.5 Process invariants

| Invariant | Result |
| --- | --- |
| Real-model execution | NO |
| Provider contacted | NO |
| Model inference performed | NO |
| Ollama contacted | NO |
| Qualification rerun | NO |
| Confirmatory execution entered | NO |
| Result files changed | NONE |
| Historical governance records changed | NONE |
| Production `src/` changed | NO |
| Forbidden paths accessed | NO |
| Full test suite run | NO (only the 5 files named in §3.1) |
| Git add / commit / push / merge / tag / PR | NONE |

---

## 16. Remaining reviewer risks

Ordered by how likely each is to draw an objection. Listing a risk is not
authorization to collect evidence for it.

1. **No treatment effect exists.** The paper's central limitation is unchanged
   and unfixable by writing: there is no QA-ON arm. A reviewer who requires an
   effectiveness result will reject regardless of how the negative result is
   framed. The v0.8 framing makes that judgment available immediately rather than
   burying it, which is the most that can be done at this stage.
2. **Page budget.** Estimated 4–7 pages over the FSE 18-page limit in `acmsmall`
   (§13). This must be resolved in the template pass and is the single most
   concrete blocker to submission readiness.
3. **Three preprint citations.** [21] CaMeL, [22] Progent and [24] AI Agents That
   Matter have no peer-reviewed version as of this audit. Each is labelled as a
   preprint. They should be re-checked immediately before submission in case a
   venue version has appeared.
4. **Family I (provenance / auditable agent execution) has no dedicated
   citation.** The per-decision audit record is argued from the implementation
   and §7.1 rather than positioned against a provenance literature. A reviewer
   working in software provenance may ask why. A targeted search for that family
   is worth one pass.
5. **Table numbering.** The manuscript has never numbered its tables; the two new
   tables carry descriptive captions but no "Table N". This is internally
   consistent but will need a full numbering scheme in the ACM template, where
   captions are styled and cross-referenced.
6. **RQ1 is validated on the authors' own tests.** The 15 properties are
   invariants the authors specified and the authors tested. That is the normal
   standard for a mechanism claim, and the claim map makes it auditable, but a
   reviewer may still call it self-certifying. The mitigation available is the
   artifact, not more prose.
7. **The novelty argument concedes the mediation mechanism.** §10.4 deliberately
   grants that runtime mediation is common ground and rests the contribution on
   qualification and the fail-closed gate. This is honest and, we judge, the
   strongest available position — but it stakes the paper on the methodological
   contribution being seen as sufficient for a Research Track paper.
8. **Anonymized replication package not yet assembled.** Data Availability
   accurately says it is being prepared and not yet public. That is defensible
   for a working draft but must be true and complete at submission.

---

## 17. Disposition

| | |
| --- | --- |
| Pass verdict | **PASS** |
| Successor qualification | COMPLETE / `HOLD` — unchanged |
| Confirmatory eligibility | NO — unchanged |
| Confirmatory execution | NOT ENTERED — unchanged |
| Rerun / retry / replacement | NOT AUTHORIZED — unchanged |
| Provider contacted by this pass | NO |
| Model inference performed by this pass | NO |
| Result files changed | NONE |
| Production code changed | NONE |
| Next action | **HUMAN_REVIEW_V08_THEN_ACM_TEMPLATE_PASS** |

The template pass should carry the §13 trim plan, resolve table numbering, and
re-verify the three preprint citations.
