# S2 — Prospective confirmatory analysis plan

# NOT EXECUTED. NO CONFIRMATORY RESULT EXISTS.

The analysis described here was specified **before any real-model confirmatory
data existed**, and it was conditional on a candidate first satisfying QA-OFF
qualification.

No candidate has satisfied it.

- No Stage-C final registration was completed.
- No treatment was assigned.
- No confirmatory position was executed.
- The analyzer was never run on a confirmatory matrix.

Nothing in this file is a result, and no value reported anywhere in the paper is
derived from it. It is retained because a plan fixed before any data existed is
itself a reportable artifact, and because a reader is entitled to see exactly
what would have been claimed and how it would have been tested.

---

## S2.1 Intended contrast and estimand

The pre-specified estimand is the **fixed benchmark-suite effect of QA FULL
relative to QA OFF**, not a claim about all possible agent tasks.

For each endpoint and each registered task:

1. Repetitions are first averaged **within** each registered (provider, model)
   stratum. Repetitions therefore capture within-task stochastic variability
   without being treated as independent task samples.
2. The strata then receive **equal weight**, so unbalanced repetition counts give
   no stratum extra task-level weight.
3. The resulting task-level difference is **QA FULL minus QA OFF**.

## S2.2 Endpoint sequence

| Position | Endpoint |
| --- | --- |
| Primary | Unsafe-action execution |
| Secondary 1 | Safety/security violation |
| Secondary 2 | Unsafe action proposed |
| Secondary 3 | Constraint violation |
| Secondary 4 | Privacy leak |
| Secondary 5 | Attack success |

Utility, overhead, PARTIAL QA, and FULL-minus-one ablation summaries are
supporting or exploratory. They would be reported **separately from the
inferential family** unless prospectively promoted into it.

## S2.3 Task count and randomization machinery

The randomization inference mode is fixed prospectively by the registered task
count *K*.

| Condition | Mode |
| --- | --- |
| *K* ≤ 16 | The analyzer enumerates the **full task-complement support** |
| *K* > 16 | One prospectively seeded **PCG64 Monte-Carlo sign matrix**, whose same global draws are reused for every reached endpoint |

Reusing the global draws is deliberate: it prevents a reduced-applicability
secondary endpoint from switching inference modes mid-family.

## S2.4 Gate structure

- Testing proceeds as a **fixed sequence** at a prospectively fixed level.
- The first failure to reject, or the first unavailable endpoint, **closes every
  later gate**.
- Zero-difference tasks **remain in** *K*.
- A task count of zero makes confirmatory testing **unavailable**, rather than
  triggering task deletion, replacement, or renormalization. The same applies to
  any missing or unobserved primary position.

## S2.5 What was and was not fixed

**Fixed prospectively:** the gate structure, the endpoint order, the differencing
rule, and the randomization mode. That is the whole of what was specified.

**Never fixed:** no value of *K*, because no Stage-C final registration was
completed.

**Never exercised:** none of the machinery above has been run.
