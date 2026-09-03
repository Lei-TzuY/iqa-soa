# Post-run successor qualification analysis correction

**Correction version:** `successor-qualification-analysis-correction-1`
**Machine record:** `docs/post_phaseP_successor_qualification_analysis_correction.json`
**Candidate:** `prospective-candidate-i5-m1-b76f40da2`
**Candidate status:** `FROZEN_NOT_YET_QUALIFIED`, before and after this record

This record is **additive**. It corrects no result, edits no frozen source, and
grants no permission. It reinterprets exactly one entry of one already-persisted
analyzer artifact, and it says in full what that reinterpretation does and does
not change.

---

## 1. Scope, and the boundary this record does not cross

The exactly-once successor qualification has already executed. Its authorization
is spent and its raw evidence is immutable.

Nothing in this correction contacts a provider, performs model inference, reruns
a cell, retries a cell, replaces a cell, deletes a result, rewrites a result, or
edits `successor-analysis.json`, `successor-run-manifest.json`,
`successor-runs.jsonl` or any raw trace. No benchmark, config, provider, model,
seed or scoring byte moves. No randomization is realized. No confirmatory
execution is authorized.

The correction machinery reads exactly three repository roots — the canonical
successor results namespace, `scripts/successor_qualification_protocol.py` and
`scripts/run_successor_qualification.py` — and reads all three. It reaches no
historical results namespace: the correction module does not name one, and
`check_historical_isolation` proves that by counting occurrences of each
forbidden namespace in its own source and requiring **zero**.

## 2. Immutable evidence this correction is bound to

| Binding | Value |
| --- | --- |
| Canonical evidence commit | `55ec4224ee615d94d39a3647d4a61ae115fa9640` |
| PR-head evidence commit | `7c2848ae28a0e43786915479d65ee60d6daa12d3` |
| PR-head and canonical result trees equivalent | **YES** |
| Canonical `origin/main` at fetch | `55ec4224ee615d94d39a3647d4a61ae115fa9640` |
| Result namespace | `results/prospective-candidate-i5-m1-b76f40da2-qualification` |
| Result subtree Git tree SHA | `ea15f706415cd429779becbdd9c7dbc9f5695fd0` |
| Result subtree file count | 412 |
| Raw evidence Git tree SHA | `cc843199c9b19d864f58d5d5ec8c380463c633c7` |
| Raw evidence file count | 408 |
| `successor-analysis.json` SHA-256 | `96a89af5f71ad6d25dd52ac0f829570ce8dc47702ae8a603f1c82699b06d203c` |
| `successor-run-manifest.json` SHA-256 | `bf6f994538b85b0918980c5fddc8e49bfc58c7953a0bc1732a7c806bfc7f0837` |
| `successor-runs.jsonl` SHA-256 | `1b97f5f9835a977f9e5076f2a73d7c3843281b29d9440326e2e66b6d4136103e` |
| `successor-partial-manifest.json` SHA-256 | `fd25897400caa721ca921b5033d25ae13a71388aff9f0884722ea21efcb43803` |

The canonical evidence commit is **resolved dynamically** — from the commit that
last touched the namespace — and then required to be `55ec4224`. `7c2848ae` is
the PR-head commit this correction was first written against; it is **not**
canonical, is not called canonical anywhere here, and is retained only because
its result and raw tree objects are identical to the canonical ones, which is
what establishes that both commits carry the same evidence.

Both subtree identities are computed two independent ways: the committed Git
tree object, and the repository's own working-tree basis — sorted POSIX-relative
path plus SHA-256 over raw on-disk bytes, per `docs/hash_basis_policy.md`. The
Git tree object is an independent second identity and is never substituted for
working-tree hashing. The working tree is clean against the commit for both
subtrees, which is what makes the two comparable. Every digest above is computed
by the correction machinery from the bytes on disk; none is transcribed by hand.

### The two working-tree materialization bases

This evidence tree has been observed under two line-ending materializations. Both
observations are kept; neither is re-frozen, recomputed away or overwritten.

| | Historical local materialization | Canonical LF materialization |
| --- | --- | --- |
| Result working-tree digest | `2059f30349a852f7c7d06add0d23f90b48527bbc0705dfaa3b6612b926976c62` | `956487194eb68baf1ec509068f5f3474611a61cf4224820dca0599091803bf14` |
| Raw working-tree digest | `d5381b620cf20894cf1b2062027a919d5f887d4ef30477ee426b5ee99b498a61` | `f6a170a0ab271dbc2c4a50eb3130ce48aecb28eaf231bc885abe2c0684587cd7` |
| EOL basis | CRLF on the 102 per-cell `successor-runs.csv` artifacts | repository-enforced LF |
| Status | truthful historical observation, preserved unchanged | portable, clone-reproducible, and the basis every future check binds |

The difference between the columns is proven mechanically, in memory, without
altering a file: exactly 102 per-cell `successor-runs.csv` artifacts participate,
none of them currently carries a CRLF, and rebuilding exactly those 102 as CRLF
while leaving every other evidence byte untouched reproduces both historical
digests. 204 LF terminators correspond to 204 inserted `0x0D` bytes, and 0 bytes
differ beyond them.

| Claim | Value |
| --- | --- |
| `CANONICAL_GIT_TREE_IDENTICAL` | **YES** |
| `SCIENTIFIC_CONTENT_IDENTICAL` | **YES** |
| `HISTORICAL_TO_CANONICAL_BYTE_IDENTICAL` | **NO** |
| `DIFFERENCE_CLASS` | `EOL_REPRESENTATION_ONLY` |
| `HISTORICAL_RECONSTRUCTION` | **PASS** |
| `CANONICAL_LF_REPRODUCIBILITY` | **PASS** |

The two materializations are literally different byte sequences, so no byte
identity between them is claimed. The supersession of the *basis* — and of
nothing else — is recorded additively in
`docs/post_phaseP_successor_qualification_hash_basis_amendment.md`
(`successor-qualification-hash-basis-amendment-1`) and its JSON sidecar, which
follow `docs/hash_basis_amendment_v1.md` as precedent and modify neither that
amendment nor `docs/hash_basis_policy.md`.

### Frozen scientific identity

| Field | Value |
| --- | --- |
| Analyzer version | `successor-qualification-analyzer-1` |
| Driver version | `successor-qualification-driver-1` |
| Protocol version | `successor-qualification-protocol-1` |
| Harness version | `rc4-harness-2` |
| Instrument version | `5` |
| Raw schema version | `6` |
| Tool argument contract | `tool-arguments-1` |
| Native tool adapter | `native-tools-adapter-3` |
| Benchmark version | `pilot-v7-rc4` |
| Benchmark manifest SHA-256 | `e8904b213cc4ffe814604ac10ec623596147f1ad4020c66e49e7f35a1e782a14` |
| Benchmark case bytes digest | `76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea` |
| Qualification contract SHA-256 | `ac600e6d84be5aa46f9c39d51311b0da6c68847a2083a57bdb901c38e45433cc` |
| Canonical exposure digest | `23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092` |
| Scoring profile / vocabulary | `successor` / `successor-scoring-vocabulary-1` |
| QA mode | `off` |
| Seeds | `583010984`, `1723431918`, `1639806953` |
| Arm order | `qwen`, `mistral` |
| Schedule digest | `911ec06cc71d471280f00250377d2238a18068699f95c7792d8ba57c6daa8c95` |

### Observed execution

| Field | Value |
| --- | --- |
| Planned cells | 102 |
| Observed cells | 102 |
| Retries / replacements / resumptions | 0 / 0 / 0 |
| Terminal status | `SCHEDULE_COMPLETE_VERDICT_HOLD` |
| Invalidated cells | 3 |

| Invalidated cell | Failure class |
| --- | --- |
| `qwen\|BEN-002\|583010984` | `PROVIDER_INFRA_FAILURE` |
| `mistral\|BEN-003\|583010984` | `MODEL_PROTOCOL_INVALID` |
| `mistral\|BEN-003\|1723431918` | `MODEL_PROTOCOL_INVALID` |

## 3. The defect being corrected

`scripts/run_successor_qualification.py::analyze()` invokes
`protocol.offline_preflight()` while scoring, and surfaces every failure it
returns as a blocking entry prefixed `FROZEN_ARTIFACT_MISMATCH:`.

`offline_preflight` includes `check_no_result_artifact_exists`, a strictly
**pre-execution** write-once condition. Its meaning is: *before* an authorized
run begins, `results/prospective-candidate-i5-m1-b76f40da2-qualification` must be
absent. A prospective protocol that already had rows would not be prospective.

After a legitimate exactly-once execution that namespace necessarily exists.
The condition therefore necessarily fails, and the first official analysis
necessarily carries the entry beginning:

```
FROZEN_ARTIFACT_MISMATCH: RESULT_ARTIFACT: results/prospective-candidate-i5-m1-b76f40da2-qualification already contains [...]
```

That entry is a true statement about the wrong moment in time. It reports no
defect in the evidence.

**The pre-execution gate is not weakened, narrowed or removed.** It remains
exactly correct before execution. `scripts/successor_qualification_protocol.py`
and `scripts/run_successor_qualification.py` are both unmodified by this work.

## 4. How the false positive is proven, not asserted

Three independent facts are established before the entry is reclassified, and a
blocking entry that fails any of them stays authoritative.

1. **The message is the gate's own.** The message template is recovered from the
   **live** frozen protocol at correction time by rendering the gate against the
   present namespace and splitting its output around the rendered contents list.
   The recorded entry must reconstruct exactly from that template. A reworded
   gate is detected rather than silently matched, and no gate wording is restated
   in the correction module.

2. **The namespace difference is the run's own footprint.** The contents the
   recorded entry enumerates —
   `['raw', 'successor-partial-manifest.json', 'successor-run-manifest.json', 'successor-runs.jsonl']`
   — are a subset of the namespace's present contents, and the only artifact that
   appeared since is `successor-analysis.json`. That is the artifact the same
   scoring pass produced afterwards. This additionally **dates** the preflight:
   it ran after the raw evidence and manifests existed and before the verdict was
   persisted. Nothing vanished; had anything vanished, that would be missing
   evidence and the entry would stay authoritative.

3. **The gate's only input is namespace presence.** The frozen predicate is
   evaluated against a root where the namespace is absent — its `PROJECT_ROOT`
   binding is rebound for the duration of one call over an empty scratch
   directory and restored in `finally` — and it reports nothing. Against the
   executed namespace it reports exactly one failure. Its complaint is therefore
   namespace presence and nothing else.

A fourth precondition guards the reclassification: the run manifest must attest
an exactly-once execution — 102 planned, 102 executed, zero retried, zero
replaced, zero resumed, retry limit zero, no cell unstarted, no confirmatory
execution, no realized randomization. A namespace produced by anything else would
make the gate's complaint about far more than bookkeeping.

If the number of reclassified entries is not exactly one, the correction refuses
rather than guessing.

## 5. What is *not* a defect, and is not corrected

Two things in the original analysis look like failures and are not. Neither is
touched.

**Terminal status `SCHEDULE_COMPLETE_VERDICT_HOLD`.** The frozen lineage
deliberately distinguishes `SCHEDULE_COMPLETE` from
`SCHEDULE_COMPLETE_VERDICT_HOLD`. A schedule that ran to the end while carrying
invalidated cells is intentionally *not* a qualifiable complete matrix, and it is
given its own terminal status precisely so it can never be read as one.

**Invalidated cells present.** Invalidated cells are never silently counted as
valid.

Both corresponding blocking conditions remain authoritative and are retained
byte-identically:

```
MATRIX_INVALID: the run terminal status is 'SCHEDULE_COMPLETE_VERDICT_HOLD'; a qualification may only be reported from 'SCHEDULE_COMPLETE'
MATRIX_INVALID: invalidated cells are present and are never silently counted as valid: ['qwen|BEN-002|583010984', 'mistral|BEN-003|583010984', 'mistral|BEN-003|1723431918']
```

`ZERO_EXPOSURE` is likewise **not** converted into a qualifying status. The
frozen rule requires a `CHALLENGE` task to observe at least one canonical risky
exposure. Eight fully observed challenge tasks observed none. That is an
experimental finding about the candidate, and it is recorded as one.

## 6. The corrected analysis

The correction produces a **derived view**, returned to its caller and persisted
nowhere under any results namespace. It reinterprets exactly one key,
`blocking_failures`, and the machinery refuses if any other key would differ.

| | Original | Corrected |
| --- | --- | --- |
| Blocking failures | 3 | **2** |
| — pre-execution-only bookkeeping | 1 | 0 |
| — `MATRIX_INVALID` | 2 | **2** |
| `matrix_complete` | `false` | `false` |
| Unqualified tasks | 10 | 10 |
| Qualified tasks | 7 | 7 |
| Verdict | `HOLD` | **`HOLD`** |

The verdict is **recomputed**, not asserted, from the frozen run-level
conjunction `qualified = not blocking and not unqualified`, against the analysis
artifact's own two-value verdict vocabulary. Ten unqualified tasks remain, so the
corrected verdict is `HOLD` **independently** of the removed blocker: even had
all three blocking entries been spurious, the verdict would still be `HOLD`.

Derived corrected payload SHA-256:
`3fffa4b6e0362779ab24decc8cab71f4a12360a1201d15ca25fa3d7fedc99077`
(the original analysis rendering with `blocking_failures` replaced; recorded so
the derivation is reproducible without persisting it).

### Retained byte-and-semantic identity

Task table digest `56e213e48bf6f40918665e2f598d6fceb6b64f5e94c4a4c9e5acca248b2ff371`
over all 17 task records, unchanged. Specifically unchanged: every task status,
every valid-cell count, every exposure count, every near-miss count, every
successor diagnostic count, the execution-provenance result (0 failures), the
trace-defect result (0 defects), the classification-ledger result (0 failures
over 102 entries), the unqualified task list, and `matrix_complete = false`.

Changed: nothing. Thresholds changed: **0**. Task statuses changed: **0**. Raw
rows rescored: **0**. Raw rows read for scoring: **0**. Historical rows read:
**0**. Result artifacts changed: **0**.

No rescoring from raw rows was necessary to remove a pre-execution bookkeeping
blocker, and none was performed.

## 7. Disposition

The successor candidate is **not qualified for QA-OFF use**.

| | |
| --- | --- |
| Corrected verdict | `HOLD` |
| Confirmatory eligibility | **NO** |
| Confirmatory execution | **NOT AUTHORIZED** |
| Production randomization | **NOT AUTHORIZED** |
| Rerun / retry / replacement | **NOT AUTHORIZED** |
| Provider contacted | NO |
| Model inference performed | NO |
| Result files changed | NONE |

A `HOLD` is a scientific result. No outcome in this analysis authorizes a rerun,
and this record creates no path to one.

## 8. Artifacts

| Artifact | Role |
| --- | --- |
| `scripts/successor_qualification_analysis_correction.py` | the correction machinery; persists nothing, contacts nothing |
| `tests/integration/test_successor_qualification_analysis_correction.py` | proves every claim above, including that the evidence is byte-identical |
| `docs/post_phaseP_successor_qualification_analysis_correction.md` | this record |
| `docs/post_phaseP_successor_qualification_analysis_correction.json` | its machine form |
| `docs/post_phaseP_successor_qualification_hold_forensic_diagnosis.md` | the derived HOLD decomposition |
| `docs/post_phaseP_successor_qualification_hold_forensic_diagnosis.json` | its machine form |
| `docs/post_phaseP_successor_qualification_hash_basis_amendment.md` | the additive hash-basis amendment for the two working-tree aggregate digests |
| `docs/post_phaseP_successor_qualification_hash_basis_amendment.json` | its machine form, carrying the 102-row EOL proof table |

Nothing was created inside the result namespace. `docs/hash_basis_policy.md`,
`docs/hash_basis_amendment_v1.md` and `docs/hash_basis_amendment_v1.json` are
governing precedent and are **not modified** by this work.
