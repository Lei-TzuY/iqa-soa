# Paper and Research-Question Mapping

## Authority and narrowing

`2026-final.pdf` is the source of truth for QA-XML, IQA-SOA, QA-IUM, UC-SCEM, and the proposal's comparison/ablation/red-team/replay design. The master implementation prompt narrows that proposal into an FSE runtime-governance experiment. `FSE_2027_IQA_SOA_Draft_v0.1.docx` is a manuscript skeleton with `[TBD]` results and is not treated as empirical evidence.

The proposal promises, but does not supply, a concrete XML grammar, QA Module ABI, exact partial baseline, dataset, sample size, repetition count, randomization, or statistical tests. Choices introduced by this prototype are labeled as such rather than attributed to the proposal.

## Research questions

| FSE RQ | Question | Implementation artifacts | Primary evidence |
|---|---|---|---|
| RQ1 Safety | How much does runtime QA reduce unsafe/unauthorized agent behavior? | QA-XML policy, Gateway, injection/privacy/permission guards, adversarial categories | Violation, unsafe execution, attack success, privacy leakage, interception recall |
| RQ2 Functional quality | Does governance preserve legitimate task utility? | Benign cases, expected actions/output predicates, full/partial conditions | Task success, expected output, completion steps, false rejection, interventions |
| RQ3 Non-functional quality | What runtime/resource/audit overhead does governance add? | Timing/resource collector, evidence fragments | End-to-end/QA/evidence/tool/model latency, calls/tokens/cost, evidence completeness |
| RQ4 Quality trade-offs | What safety improvement is achieved at what utility/cost? | Exact paired runner and paired analysis | Before/After deltas, CIs/effect sizes, Figure B, category curves |
| RQ5 Component contribution | Which QA Modules account for observed changes? | Data-driven FULL-minus-one variants | Risk/task/overhead changes by injection, privacy, permission, budget, output, evidence ablation |

## Proposal-to-artifact coverage

| Proposal concept | FSE implementation | Status/limit |
|---|---|---|
| Controlled LLM semantic compiler | Provider proposes typed actions; it cannot execute them | Implemented at action-proposal boundary, not full NL→QA-XML compilation |
| QA-XML five-dimensional constraint language | Strict executable subset for input/injection, tool/privacy/budget/output/disposition | Implemented subset; no claimed formal semantics/SMT completeness |
| IQA-SOA Gateway + Decorator + QA Modules | Single gateway, interceptor, ordered configurable chain | Implemented |
| No/partial/full baselines | G0, transparent G1 permission+budget, G2 | Implemented protocol choice for G1 |
| Red-team and fault injection | Injection, unauthorized, privacy, poisoning, budget, synthetic dependency faults | Implemented benchmark slice |
| QA-IUM lifecycle DAG | Stable append-only evidence fragments with causal/version links | Supporting slice only; no graph DB, GNN, or tamper-proof claim |
| Online log replay | Deterministic replay under recorded order/context | Evaluation plumbing only; no learning/convergence claim |
| Safe online optimization/Quality-Based Cost Model | Not included by the narrowing prompt | Out of scope |
| Pareto improvement with >=95% constraint satisfaction | Trade-off metrics/figures prepare the evidence path | Not preclaimed; requires a sufficiently powered experiment |
| Formal verification and long-term stability | Extensible policy model and strict schema | Not implemented/claimed |

## Research integrity

Generated smoke and deterministic-stub results validate plumbing and expected fixture behavior. They do not demonstrate real-model generalization, statistical power, or industrial effectiveness. Publication claims require frozen benchmarks, independent model runs, documented versions/prices/hardware, an a priori analysis plan, and preservation of every failed or inconvenient observation.

Phase 2 implements that evidence path with a hash-frozen pilot, credential-safe
real-provider boundary, paired OFF/FULL cells, explicit model/refusal/failure
provenance, task-clustered pilot analysis, and separate P1--P4 outputs. Until an
actual provider smoke and pilot complete, these additions are infrastructure,
not empirical support for RQ1--RQ4.
