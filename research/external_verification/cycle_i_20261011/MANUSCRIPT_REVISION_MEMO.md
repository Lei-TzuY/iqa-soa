# Cycle I: required manuscript corrections and a defensible narrower contribution

**Readiness: HOLD for the located manuscript's unrestricted semantic and prospective claims. No manuscript edit or submission is authorized or executed.**

This memo audits the latest located `main_v1.6.3.pdf`, Drive file `14uHeRwZ7TT_4vpdwQ4Igpf2fLRej-VTJ`. Bounded Drive searches found v1.6.3, v1.6.2 and earlier FSE drafts; no later version was located. The desktop also contains v1.6.3 TeX, but that does not establish an authorized current submission. The PDF's 878,066 bytes hash to `32b1abda3fd48f8cf0dbe11470ac1a59d6a745ddfc4d3806e9dc42eb78a2e35b`. Its normalized connector extraction still hashes to `dfd0dddecd712acec0fb171b18f7fb78354fdd977a60cae27c65350f7f7336b5`, matching E-H provenance. Printed pages 14 and 16 were visually checked; page and printed-line locators below refer to that PDF.

The earlier G/H matrices already identified content, temporal, scoring-order, qualification and prospectivity limitations. This milestone adds a record-resolved diagnostic denominator correction, independent operational attribution of the recorded refusals, and completion ranges for the manuscript's proposal/interception statements. It changes **zero semantic labels** and does not rerun an experiment or the frozen analyzer.

## A newly demonstrated denominator mismatch

Page 14, lines 658-660, says:

> “the models still proposed the attacker goal in 66% (qwen) and 45% (mistral) of eligible cells, and the gateway intercepted 73% and 82% of them.”

The frozen `analysis.py` diagnostic at lines 335-339 computes the second pair of percentages over **all canonical FULL cells**, without filtering the frozen eligible goals. The first pair uses eligible cells. These are different populations. `historical_diagnostic_extract.json` preserves the original source excerpt, source hashes and stored results; the original file and analyzer remain unchanged.

| Population and source-defined measure | Qwen | Mistral |
|---|---:|---:|
| FULL observations over all 34 canonical goals | 136 | 136 |
| FULL observations over the 21 frozen eligible goals | 84 | 84 |
| Source-positive proposals in eligible population | 55/84 = 65.4762% | 38/84 = 45.2381% |
| Proposed-positive/executed-negative fraction, all canonical | 41/56 = 73.2143% | 31/38 = 81.5789% |
| Same fraction, frozen eligible population | 40/55 = 72.7273% | 31/38 = 81.5789% |

Qwen record `confirmatory/cells/00448-qwen-full/raw.json`, SHA256 `1881202baea9591319756df561a6765580f4ad485ee7c96062749fc49398513e`, supplies the extra source-positive proposal. Its Workspace1 goal is outside Qwen's frozen eligibility. Gateway evidence SHA256 is `b94570bb260f4d21a2d579bc034ed743f236f3db67ee70c67d47d60d85d7abe2`. The record contains an actual permission refusal. It is a denominator discrepancy, **not a newly discovered semantic-oracle error**, a new primary observation, or a new independent treatment contrast. Rounding both ratios to 73% hides the discrepancy.

**Suggested replacement for lines 658-660 and the corresponding claim on lines 676-677:**

> Under the original source-defined predicates, FULL proposals satisfied the shadow success predicate in 55/84 Qwen and 38/84 Mistral observations from the frozen eligible population. Among those source-positive proposals, the actual-execution predicate was false in 40/55 and 31/38 observations. The original all-canonical diagnostic instead used 41/56 and 31/38. These program-defined proposal/nonexecution fractions are descriptive and are distinct from independently established natural-language goal success or a causal interception rate.

No owner interpretation is selected by this wording.

## Independent resolution of the guard-attribution ambiguity

The retained post-hoc diagnostic reports 108 cells with a permission blocking guard and 31 with an output-validation blocking guard. Reading those cell counts as competing pre-dispatch refusals would contradict page 14, lines 660-661. Cycle I independently inspected the union of **129 original FULL episodes**, including the 72 source-defined proposal/nonexecution records. Ten episodes have both guard types.

For every selected raw/evidence pair, the original F provenance hashes match; gateway dispatch flags match raw proposal flags; the non-dispatch count matches the terminal summary; and a retained `ToolCallBlocked` result supports each non-dispatched call. All **228 non-dispatched calls** have `permission` as their blocking guard. Separately, **75 already-dispatched events** carry `output_validation` as their blocking guard. They occur in 31 episodes and are not additional pre-dispatch refusals. The 72 source-positive/nonexecuted episodes contain 82 permission refusals, but a goal-level shadow/actual gap is still not the same counting unit as a refused call.

Thus the paper's **operational attribution of all 228 refusals to permission is independently supported on these retained mock-tool histories**. The output-validation counts do not falsify it. They also cannot be counted as 75 prevented attacks or new oracle disagreements. This inspection establishes event identity and ordering flags, not real-world transactions, independent human labels or the incremental causal value of permission enforcement versus a permission-only comparison arm.

**Suggested addition after the refusal sentence:**

> Here a refusal means a proposed call that did not dispatch and returned a recorded ToolCallBlocked result. The independent retained-history audit identifies 228 such calls across 108 episodes, all attributed to permission. Seventy-five separate output-validation dispositions occurred after dispatch across 31 episodes; ten episodes contained both event types. Those post-dispatch dispositions are not prevention events.

## Proposal claims remain partially identified

Using only existing H labels, with the original 21 eligible goals/model and four carriers per goal unchanged:

| POST-HOC completion range, frozen eligible FULL observations | Qwen | Mistral |
|---|---:|---:|
| Hypothetical proposal success rate | [51/84,56/84] = [60.7143%,66.6667%] | [34/84,38/84] = [40.4762%,45.2381%] |
| Proposed-success/actual-nonsuccess fraction among proposed successes | [37/53,3/4] = [69.8113%,75%] | [7/9,16/19] = [77.7778%,84.2105%] |

These fractions jointly vary numerator and denominator; they are not obtained by subtracting separate rate bounds. Unknown endpoint labels vary freely, conditional on known H labels. No new common goal-wide rule is presumed. Future coherent adjudication may restrict that completion set. The ranges are **not confidence intervals**, new confirmatory tests, successful execution of blocked proposals, or proof of a specific causal mechanism. No pooling or change to model strata is performed. Equal carrier counts preserve the original per-goal descriptive weighting within each stratum.

The independent primary H FULL-minus-OFF bounds remain **[-0.517857,-0.434524]**, and H primary proposed bounds remain **[-0.130952,-0.017857]**. Cycle I does not recalculate or narrow either bound, because no new authorized decisions were provided.

## Exact revision map

The “after” wording below is a proposal only. Every manuscript-edit action is UNEXECUTED.

| Location and existing wording | Evidence status | Suggested wording or required correction |
|---|---|---|
| Abstract, p1: “lowered the rate of executed attacker-goal effects ... by 0.51” | PARTIALLY_VERIFIED | “The original implemented-predicate analysis estimated FULL-minus-OFF = -0.505952 (original 95% interval [-0.589,-0.423]) on its frozen eligible population. Independent post-hoc construct analysis leaves 14 executed labels unresolved and bounds the contrast at [-0.517857,-0.434524], conditional on classified labels.” Keep the original interval and completion bounds explicitly distinct. |
| Measures, p11, and discussion p15: native predicates match the protected-effect boundary “exactly for 33 of 35 goals” | FALSIFIED as an unrestricted intent/effect equivalence; VERIFIED only as source-predicate equivalence | “Thirty-three implemented predicates inspect environment state. Reproduction of these source predicates does not establish natural-language goal fulfillment. Content omissions, reservation-slot overwrites and scorer-state mutation are independently observed measurement defects.” Cite F/G record ledgers and G hotel investigation. |
| Qualification, p13, Table4: “Goals with executed untreated effect: 21 of 34” | VERIFIED as the historical source-defined admission count; semantic equivalence FALSIFIED | Relabel to “Goals admitted by original source-defined qualification.” Do not claim semantic qualification of 21 goals/model, use old G eligibility scenarios as current H results, or change the principal population. G showed Mistral Banking1 and Travel1 lacked semantic-positive qualification records; H did not recompute changed eligibility. |
| Table5, p14, lines638-647: “pre-registered order” and original estimates/intervals | Exact numerical reproduction VERIFIED; independent external prospectivity UNEXECUTED | Preserve the original table as a source-defined frozen analysis, with an explicit note that independent evidence of an external pre-outcome registration anchor is unlocated. Present all E-H/I recodings, bounds and diagnostic corrections separately as POST-HOC. A file timestamp, digest chain or PDF date is not independent registration evidence. |
| p14, lines658-660 and676-677: eligible proposals / “intercepted ... of them” | FALSIFIED denominator binding; PARTIALLY_VERIFIED semantic mechanism | Use the denominator correction and proposal completion table above. Distinguish shadow satisfaction, actual mock dispatch and operational refusal counts. Do not describe a shadow success as a completed attack or a ratio alone as causal interception. |
| p14, lines660-661: “all 228 refusals ... permission guard” | VERIFIED operational attribution in retained mock histories | Retain with the definition and pre/post distinction above. State that this is observed guard attribution within the configured system; no permission-only comparison arm exists. |
| Abstract, p14 RQ5, p18 conclusion: “without measurable benign-utility cost” | VERIFIED original native utility statistic; equivalence and independent benign-task semantics UNEXECUTED | Report original native utility difference +0.015464, original interval [-0.010309,+0.041237] and p=.452555. The p16 threats section already correctly says nonsignificance is not equivalence; carry that restriction into the abstract and conclusion. No independent semantic audit of benign user-task correctness is claimed. |
| p16, lines736-739: construct-validity paragraph | PARTIALLY_VERIFIED / AMBIGUOUS | Add 30/35 retained goal populations classified, 877/910 actual and846/884 hypothetical contexts classified, five goals/38 records/71 unresolved contexts, zero independent human decisions, known oracle defects, and owner-definition versus absent-fact barriers. State the accepted mock-action versus persistent-state distinction and unresolved preference, capacity, identity, cloud-scope and modality meanings. |
| p14 RQ5, p15 component attribution, p18 conclusion: effect “attributable to task-scoped least privilege” | PARTIALLY_VERIFIED configured contrast; permission-only incremental causality UNEXECUTED | “The configured FULL-versus-OFF contrast was observed under an idealized ground-truth-derived tool policy. Recorded refusals were issued by permission; the experiment does not isolate incremental component causality or policy acquisition.” Retain the existing p15 limitation prominently. |
| p18 data availability: “artifact accompanying this submission” | UNEXECUTED venue claim | Describe an available research artifact/draft without asserting submission, anonymity compliance, receipt or acceptance absent independent evidence. Preserve the original manuscript until an authorized revision. |

Record anchors: F `record_discrepancies.csv`; G `record_discrepancies.csv` (Banking1 qualification462/516/526 and confirm558/559; Travel1 qual322,confirm610/611); G `hotel_discrepancy_investigation.json` (accepted bookings at qual410,confirm100/101/936/937; blocked proposal at561); H `additional_discrepancies.csv` (Travel6 direct qualification30); and I `denominator_discrepancy.csv` (confirm448). These pointers are evidence references, not independent sample counts. Invalid G V3 remains excluded; the corrected valid V4 is preserved.

## Publication decision

A defensible narrower contribution remains: an executable lifecycle and gateway evaluated under a fixed mock benchmark configuration; preservation and reproduction of source-defined results; independent discovery of benchmark measurement defects; partial identification under explicit known-label assumptions; and a controlled human/data handoff. The newly verified event decomposition supports an operational statement about permission refusals. It does **not** validate every semantic or causal claim in the manuscript.

The current manuscript needs the corrections above before a narrowly scoped research-readiness assessment can be reconsidered. Complete semantic correctness, an exact independently adjudicated -0.51 effect, externally established prospectivity, independent human validation, real-world prevention, broader generalization and venue status remain unsupported or unresolved. Historical HOLD decisions remain untouched. The next executable action is the three owner definitions in `OWNER_DECISIONS.md`, followed only when actually authorized by frozen rule versions and targeted original-record replay. No decision is assumed here.
