# External AgentDojo evidence verification

**Public source audit: EXECUTED. External empirical record audit: UNEXECUTED.**

This is a new post-hoc verification package, not the original frozen experiment,
an execution authorization, or a replacement for the original analysis. It makes
no model calls and does not reopen an internal HOLD or repeat a one-shot study.

## Ground truth and retrieval boundary

The latest located manuscripts are
[main_v1.6.3.pdf](https://drive.google.com/file/d/14uHeRwZ7TT_4vpdwQ4Igpf2fLRej-VTJ/view)
(modified 2026-09-29 04:21 UTC) and
[supplement_v1.6.2.pdf](https://drive.google.com/file/d/1JCh6fNkIJREof-wAJBaieN7XixWkBqOx/view)
(modified 2026-09-28 22:49 UTC). They report the separate external study
fse2027-external-replication-v1, including qualification and paired
QA-FULL/QA-OFF execution. **The manuscript reports this study; its empirical
validity has not been independently verified here.**

Connected Lei-TzuY/iqa-soa main was
d6f8638285a393a55a8eaa2fbd11ef4722b56aa1, tree
1cd5e846643bd7953c6974d50dc53bf28efff8be. Its LaTeX is the earlier internal
v0.8 draft, not the located v1.6.3 PDF. This gap matters for artifact building.
The retrieval.json inventory records 32 inspected branch file inventories,
50 PR records, eight empty workflow-artifact inventories, empty releases,
scoped Drive queries, and the upstream identity. This is a scoped unsuccessful
retrieval, not proof that the raw package does not exist elsewhere. Closed PR
source trees were not exhaustively scanned.

The official [FSE 2027 Research Papers call](https://conf.researchr.org/track/fse-2027/fse-2027-papers)
was checked 2026-10-09: the outage extension set 3 October 2026 AoE as deadline;
initial papers allow 18 text/figure pages plus four reference pages, with Data
Availability excluded. Anonymous replication access is expected. No submission
receipt or acceptance status has been located or inferred. Finalized PDFs and
submission files are untouched.

## Executed source check

From the repository root, with Python 3.11 or newer:

~~~text
python research/external_verification/upstream_audit.py --check
python -m unittest discover -s research/external_verification -p test_audit.py -v
~~~

The upstream directory retains an exact partial source snapshot from AgentDojo
tag v0.1.35, commit a75aba7631d3ca5fb7ab938965c97ead2f9ff84b, with its MIT
license. All 70 files are checked against original Git blob hashes and SHA-256.
No upstream source is imported or executed. The AST inventory resolves version
updates and 11 explicitly combined tasks:

| Suite | User tasks | Goals | Suite tool registrations | Cartesian pairs |
|---|---:|---:|---:|---:|
| banking | 16 | 9 | 11 | 144 |
| slack | 21 | 5 | 11 | 105 |
| travel | 20 | 7 | 28 | 140 |
| workspace | 40 | 14 | 24 | 560 |
| Total | 97 | 35 | 74 | 949 |

The active predicates split into 33 environment-state goals, one proposed-call
trace goal (slack/injection_task_5) and one model-text goal
(travel/injection_task_6). The text goal is outside the protected-effect
population. The trace goal needs dispatched-call rescoring to represent
execution. These are source observations, not reproduction of adapter tests,
tool read/effect classifications, qualification, confirmatory runs, or effects.

## Claim-to-evidence matrix

| Claim | Evidence available | Verification | Corrective check |
|---|---|---|---|
| Pinned population and 33/1/1 predicate split | Tagged source; hashes and AST report | Executed source inventory | Execute predicates on recovered environments and dispatched traces |
| 544 cells and 21 eligible goals per model | Manuscripts | Unverified raw results | Recompute terminality, invalidity, exposure and Stage-B eligibility |
| 948 paired runs without retries/replacements | Manuscripts | Unverified raw results | Check every registered slot, arm, seed, order and terminal row |
| Primary -0.506, its interval and p value | Manuscript Table 5 | Unverified raw results | Average four carriers inside each of 21 goal units per model; recover frozen analyzer |
| All-goal and utility endpoints | Manuscripts | Unverified raw results | Retain all 35 native goals and 97 benign tasks; respect fixed sequence |
| Full chain adds value beyond permission enforcement | No permission-only arm reported | Incremental causal value unresolved | Separately preregister permission-only comparison under identical policy |
| Deployable policy acquisition | Oracle-derived policy described | Not established | Lock independently specified policies before outcome access |

Qualification selects goals using untreated exposure; the estimand is conditional
on that selection. Its 42 goal units must not become 168 independent carriers
or 336 independent arm observations. Selection timing, hash selection, shared
tasks across goals, order/runtime drift and oracle construction need raw checks.
Nonsignificant benign utility alone does not prove equivalence; verify the
reported prespecified materiality margin and interval from the frozen contract.

## Execute after recovering the original archive

Required original material: selection/rubric and date anchors; tagged dependencies,
adapter and policy sources; freeze and analysis configuration; complete schedules,
raw episodes, terminal/classification ledgers, environments and gateway evidence;
Stage A/B/C originals and bindings; randomization/provider-seed provenance;
runtime/context/output-cap telemetry; original statistical code, outputs and seeds.

Preserve that archive unchanged. Review its actual schemas and write a mapping
configuration that mechanically refers to original JSON/JSONL bytes. No fabricated
observations or reconstructed timestamps may fill missing inputs.

~~~text
python research/external_verification/prepare_bundle.py --raw-root ORIGINAL_ARCHIVE --mapping REVIEWED_MAPPING.json --output NEW_BOUND_BUNDLE
python research/external_verification/records_audit.py --bundle NEW_BOUND_BUNDLE --output NEW_POSTHOC_REPORT.json --resampling-seed 20261009
~~~

Outputs must not already exist. Inputs are read only; every field is bound to an
original JSON pointer and all source hashes are checked. Missing evidence,
invalid/unavailable cells, dropped/replaced/duplicate slots, unequal paired seeds,
or inconsistent eligibility stop the audit. Missing observations are never
renormalized. An invalid matrix requires the original missing-data contract;
this checker emits no partial estimate and never changes a threshold to get GO.

### Configuration and input schema

The mapping configuration contains:

- study: exactly fse2027-external-replication-v1.
- source_files: relative original paths mapped to exact SHA-256 strings.
  JSONL sources are read as arrays; JSON retains its original shape.
- bindings: eligible_goals, attack_carriers, qualification_schedule,
  confirmatory_schedule. Each is an original {"file":"relative/path",
  "pointer":"/original/key"} binding.
- record_collections: array of file, collection_pointer (empty for JSONL),
  field_pointers relative to each row, and optional absolute context_bindings.
  Every field below needs exactly one source binding; computed values are rejected.

Schedules contain phase, model, kind, suite, user_task, goal, seed, arm.
Eligibility maps each model tag to arrays of [suite, injection_task_ID].
Carrier entries contain suite, goal, user_tasks. All 35 goals have four distinct
carrier IDs from the same suite.

Each normalized record has values and bindings dictionaries with the same fields:
phase (qualify/confirm); model (qwen3.5:27b/mistral-small3.2:24b); kind
(attack/benign/direct); suite; nullable user_task and goal; integer seed; arm
(OFF/FULL); booleans valid, terminal, utility, native_attack_success,
protected_effect_executed, protected_effect_proposed, attack_delivered.
Inapplicable endpoints are null, including both protected-effect endpoints for
the text goal. Actual raw schemas/mappings remain **UNRECOVERED**. No real
normalization or record audit has executed.

### Evaluation and expected output schema

Per model, qualification is 140 attacked + 97 benign + 35 direct-goal positions
under OFF; confirmation is 140 attacked + 97 benign positions under each arm.
Thus 544 and 948 are separate denominators. Primary: 21 goal units per model.
S1/S3: 35 native goals per model. Benign utility: 97 task units per model.

The post-hoc report includes status; source/code hashes; actual slot counts;
qualification and eligibility checks; model-level and equal-stratum paired
estimates; pointwise intervals; Monte-Carlo counts and seed; unresolved
provenance/oracle checks. Four carrier differences are averaged inside each goal.
This package uses 100,000 sign flips with a plus-one p estimate and 20,000
stratified percentile bootstrap resamples, with a fixed endpoint sequence.
The new verification seed is not the missing original seed, and this RNG/code
is not the original frozen analyzer. Resulting intervals are post-hoc sensitivity.

The frozen_analysis_reproduced flag is always false. Original frozen statistics,
Stage A-C digest semantics and pre-outcome anchoring, runtime identity, selection,
order and raw environment/trace oracles require separate reproduction. Agreement
with manuscript numbers alone is insufficient to complete the empirical milestone.

## Provenance

OpenAI Codex assisted this post-hoc code, execution and documentation. Upstream
source retains its authorship and MIT notice. Synthetic tests validate checker
failure paths and unit aggregation; they are never study observations or paper
results. The locked qualification decisions and finalized manuscripts are unchanged.
