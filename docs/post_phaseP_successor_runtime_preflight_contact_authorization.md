# Post-Phase-P successor runtime-preflight metadata-contact and RuntimeSnapshotV1 capture authorization

**Record kind:** human narrow contact authorization
**Candidate:** `prospective-candidate-i5-m1-b76f40da2`
**Candidate status at entry:** `FROZEN_NOT_YET_QUALIFIED`
**Canonical main:** `469b0c5916ae74f098da8ab2a45955297a04120b`
**Authorization version:** `successor-runtime-preflight-contact-authorization-1`
**Machine-readable form:** `docs/post_phaseP_successor_runtime_preflight_contact_authorization.json`
**Validator:** `scripts/successor_runtime_preflight_authorization.py`
**Discharges:** the runtime-preflight metadata-contact and pre-execution
provenance-capture blocker, and nothing else.

---

## 0. Boundary declaration

`docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md`
selected two proposed strata and authorized the successor-owned provider
configuration, `ExperimentConfig`, qualification protocol, frozen
execution-input bindings and offline eligibility machinery. It explicitly
withheld provider contact, **including metadata-only probes**.

This record lifts that withholding for **exactly two loopback GET metadata
operations** and for the repository-owned pre-execution `RuntimeSnapshotV1`
capture that those operations make honest. It lifts nothing else.

This is **loopback metadata / pre-execution provenance** authorization. It is
not an execution authorization, not an eligibility determination, and not a
qualification decision.

**Phase P is untouched.** Phase P remains `UNQUALIFIED`, `HOLD`,
`SCHEDULE_COMPLETE_VERDICT_HOLD`. `BEN-003` remains historical and unrepaired.
No realized Phase-P row was read, re-run, re-scored, reclassified or
reinterpreted while producing this record, and none may be while acting under
it.

**No contact happened here.** The session that produced this record contacted no
provider, opened no socket, ran no model, executed no qualification, executed no
confirmatory cell and realized no randomization. The authorization is
prospective: it describes what a **later, separate** preflight session may do.

---

## 1. The authorization

### `RUNTIME_PREFLIGHT_METADATA_CONTACT: AUTHORIZED`

A future runtime-preflight session may perform **exactly** these two HTTP
operations, and no others:

| # | Method | URL |
|---|---|---|
| 1 | `GET` | `http://127.0.0.1:11434/api/version` |
| 2 | `GET` | `http://127.0.0.1:11434/api/tags` |

### `RUNTIME_SNAPSHOT_CAPTURE: AUTHORIZED`

After — and only after — both metadata operations succeed, that session may call
the repaired repository-owned capture

```
capture_runtime_snapshot_v1(
    config=<committed successor ExperimentConfig>,
    provider=<configured frozen provider instance>,
)
```

for **exactly the two frozen strata**, and may persist the resulting
`RuntimeSnapshotV1` documents as **pre-execution provenance evidence**.

---

## 2. The allowed contact surface, stated exhaustively

| Property | Value | Anything else |
|---|---|---|
| scheme | `http` | refused |
| host | `127.0.0.1` | refused — including `localhost`, `::1`, `0.0.0.0`, any LAN address, any remote host, any name that would need resolving |
| port | `11434` | refused, including an absent port |
| method | `GET` | refused — `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, and any other |
| path | `/api/version`, `/api/tags` | refused |
| query string | absent | refused |
| fragment | absent | refused |
| userinfo in URL | absent | refused |
| credentials | **none** — no header, no token, no API key, no environment credential value | refused |
| request body | **none** | refused |

The allowlist is **closed**: an operation is authorized only by appearing in it.
Nothing is authorized by resembling something in it, by being "also
metadata-only", or by being "read-only". `/api/show`, `/api/ps`, `/v1/models`
and `/v1/embeddings` are metadata or read-only and are **refused**, because the
human decision named two operations and not a category.

`SUCCESSOR_OLLAMA_API_KEY` remains checked **by name only**. Its value is not
read, not sent, not printed and not written to any artifact. Neither authorized
operation carries a credential of any kind.

---

## 3. What this record does NOT authorize

| Scope | Status |
|---|---|
| `POST /api/generate` | `NOT_AUTHORIZED` |
| `POST /api/chat` | `NOT_AUTHORIZED` |
| `POST /v1/chat/completions` | `NOT_AUTHORIZED` |
| `POST /api/show` | `NOT_AUTHORIZED` |
| model pull | `NOT_AUTHORIZED` |
| model update | `NOT_AUTHORIZED` |
| model retag | `NOT_AUTHORIZED` |
| model replacement | `NOT_AUTHORIZED` |
| remote-provider access | `NOT_AUTHORIZED` |
| benchmark prompts | `NOT_AUTHORIZED` |
| `MODEL_INFERENCE` | `NOT_AUTHORIZED` |
| `QUALIFICATION_EXECUTION` | `NOT_AUTHORIZED` |
| `CONFIRMATORY_EXECUTION` | `NOT_AUTHORIZED` |
| production randomization / assignment realization | `NOT_AUTHORIZED` |
| Stage-C final confirmatory registration | `NOT_AUTHORIZED` |
| Stage-B eligibility disposition recording | `NOT_AUTHORIZED` |
| qualification result rows | `NOT_AUTHORIZED` |
| confirmatory result rows | `NOT_AUTHORIZED` |
| randomization artifacts | `NOT_AUTHORIZED` |
| benchmark outcomes | `NOT_AUTHORIZED` |

**A successful preflight qualifies nothing.** Observing that the live runtime
still presents the pinned version and the two pinned model digests establishes
that the environment matches the frozen pins. It does not make either stratum
`PROVIDER_QUALIFIED` or `CONFIRMATORY_ELIGIBLE`, it does not make the candidate
`QUALIFIED`, and it does not convert into permission to run a single cell.

---

## 4. Bindings

This authorization is bound to the following exact objects. A single changed
byte in any of them invalidates it, and
`scripts/successor_runtime_preflight_authorization.py` recomputes every one of
them from disk rather than trusting this table.

| Bound object | Value |
|---|---|
| canonical main | `469b0c5916ae74f098da8ab2a45955297a04120b` |
| candidate identifier | `prospective-candidate-i5-m1-b76f40da2` |
| candidate freeze record | `candidates/prospective-candidate-i5-m1-b76f40da2/freeze-record.json` |
| candidate freeze-record digest | `c099346d2e1dadaa7da8fbca2cfb3ebbf7b7d3ba4d95083827bb9daee3f339cc` |
| candidate qualification-contract digest | `46b0893b8259d3bb1fed8810fe624d2a3393d5227bc72ea31ee395872dcdadb6` |
| successor frozen-execution-input record | `docs/successor_frozen_execution_inputs.json` |
| successor frozen-execution-input digest | `f8c8ee086ca52ba3b4b93ceb3d72c5e9d2691b7d2152a6fba45185bc5f778ce2` |
| successor `ExperimentConfig` | `configs/successor-qualification.yaml` |
| successor `ExperimentConfig` digest | `f5240e2571c3d6141e9d53b0a244daf8f9ce7be8c0f25b0dfd063484d7d8d090` |
| successor provider/model config | `configs/successor-models.yaml` |
| successor provider/model config digest | `7ff2ec9e7a452331e80414194a4f5a74ab87e1c677c48d1abebd173b063566c2` |
| qualification protocol | `scripts/successor_qualification_protocol.py` |
| qualification protocol digest | `ddf82fc080d4c462f0230a8f646a6f08fc020ffac5b7818a3b58a97b98eb3cea` |
| prospective seed derivation record | `docs/successor_prospective_seed_derivation.json` |
| prospective seed derivation record digest | `08afb9ec753358ed1f75d1db645cfe179b1a952dcdc51a29aa23c82f8d70a05e` |
| prospective seed derivation digest | `97674242a12d05ccac8fe1ee1c1ef3885f2a999da538f1ccc3d2a429b62d4b3b` |
| benchmark case-bytes digest | `76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea` |
| canonical exposure digest | `23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092` |

The prospective seed **values** are deliberately not reproduced here. They live
in the three artifacts `scripts/successor_derive_seeds.py` declares as the
successor's own, and reprinting them in a fourth file would be reported by that
module's collision scan as a leak. The derivation digest above identifies the
triple without disclosing it.

### Frozen runtime requirement

| Bound runtime fact | Value |
|---|---|
| Ollama runtime version | `0.32.13` |
| comparison | exact string equality — no normalization, truncation, prefix or range match |
| Qwen `qwen3.5:27b` model identity | `7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e` |
| Mistral `mistral-small3.2:24b` model identity | `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b` |

These are the pins already carried prospectively by
`scripts/successor_qualification_protocol.py` from committed non-outcome lineage
records. This record **restates** them so the contact authorization is
self-contained; it does not re-derive, re-select or repin them, and the
validator asserts the restatement still agrees with the protocol rather than
letting the two drift.

---

## 5. RuntimeSnapshotV1 capture authorization

**Authorized callable:** `iqa_soa.experiment.confirmatory.capture_runtime_snapshot_v1`

**Authorized arguments:** the committed successor `ExperimentConfig`
(`configs/successor-qualification.yaml`) and a provider instance configured from
the committed successor provider config (`configs/successor-models.yaml`).

**Authorized scope:** exactly the two frozen strata —
`qwen_native_none` / `qwen3.5:27b` and
`mistral_native_trailing_user` / `mistral-small3.2:24b`. Not a third. Not one
alone.

**Authorized effect:** persistence of **pre-execution** `RuntimeSnapshotV1`
evidence, and nothing else.

**Evidence namespace:** `results/prospective-candidate-i5-m1-b76f40da2-runtime-preflight`.

That namespace is deliberately **not** the qualification namespace
`results/prospective-candidate-i5-m1-b76f40da2-qualification`. A pre-execution
provenance capture is not a result, and it must not be written where a result
row would live, must not create that namespace, and must not be readable later
as evidence that a qualification began.

Persistence is fail-closed and write-once: each artifact is written exactly once
to a path that must not already exist. There is no overwrite mode, no resume
mode and no merge mode.

### What the capture is not

The capture does **not** enter Stage B. `scripts/successor_eligibility_preflight.py`
refuses every offered `RuntimeSnapshotV1` and continues to refuse them; this
record does not change that module, does not weaken that refusal, and records no
eligibility disposition. Whether a captured snapshot may ever discharge
`RUNTIME_CONFIGURATION_FROZEN` for PR-10 is a separate later decision that this
record does not make.

`capture_runtime_snapshot_v1` itself opens no socket: it reads committed
configuration, the provider descriptor and local interpreter facts. The two
metadata operations in section 1 are what make its output an observation of a
real runtime rather than a well-formed assertion about an unobserved one, which
is why they are authorized together and why the capture is authorized only after
they succeed.

---

## 6. Fail-closed conditions

The future preflight must **HOLD with zero inference** if any of the following
holds. Each is a stop, never a repair instruction.

| Condition | Meaning |
|---|---|
| `LIVE_RUNTIME_VERSION_MISMATCH` | live Ollama version is not `0.32.13` |
| `QWEN_MODEL_DIGEST_MISMATCH` | observed Qwen digest is not the pinned identity |
| `MISTRAL_MODEL_DIGEST_MISMATCH` | observed Mistral digest is not the pinned identity |
| `ENDPOINT_NOT_LOOPBACK` | the endpoint to be contacted is not `127.0.0.1:11434` |
| `UNEXPECTED_HTTP_OPERATION_REQUIRED` | anything beyond the two allowed operations would be needed |
| `FROZEN_INPUT_DIGEST_MISMATCH` | any bound digest in section 4 disagrees with disk |
| `CANDIDATE_FREEZE_INVALID` | the candidate freeze does not verify |
| `QUALIFICATION_RESULT_NAMESPACE_EXISTS` | `results/prospective-candidate-i5-m1-b76f40da2-qualification` already exists |
| `RUNTIME_SNAPSHOT_CAPTURE_FAILED` | the capture raised, or returned an invalid snapshot |

**No mismatch may be repaired during the preflight.** The preflight does not
pull, update, retag or replace a model; does not install, upgrade or downgrade a
runtime; does not repin the protocol; does not rewrite a frozen input; and does
not re-freeze the candidate to make a digest agree. It reports the hold and
stops.

`RUNTIME_VERSION_RESOLUTION` remains `RESTORE_FROZEN_RUNTIME`, and
`RUNTIME_REPIN_AUTHORIZED` remains false. The governing provider authorization
already records a human-reported live environment version that is **not** the
frozen pin; if that is still the case, the preflight's correct outcome is a
hold, and this record does not soften it.

---

## 7. Historical boundary

`results/phaseP-rc4-qualification/` is never accessed — not read, not listed,
not stat-ed, not hashed, not written. The four untracked `FSE-*` clarification
directories are never inspected. No historical row may be read, re-run,
re-scored, reclassified or reinterpreted. Phase P remains permanently
`HOLD` / `UNQUALIFIED`.

Rows written under instrument 5 / raw schema 6 may never be pooled, merged,
averaged or compared with rows written under instrument 4 / raw schema 5. The
Phase-P pin to instrument 4 / raw schema 5 stays deliberately incompatible and
is not repaired here.

---

## 8. Why a separate authorization surface

The generic constants `PROVIDER_CONTACT_AUTHORIZED`,
`ENDPOINT_PROBE_AUTHORIZED`, `MODEL_INFERENCE_AUTHORIZED` and
`QUALIFICATION_EXECUTION_AUTHORIZED` in
`scripts/successor_qualification_protocol.py` govern **qualification
execution**. They all remain `False`, and this record deliberately does not
touch them.

Setting `PROVIDER_CONTACT_AUTHORIZED` or `ENDPOINT_PROBE_AUTHORIZED` to `True`
would have been the smaller edit and the wrong one: those names are read by
`scripts/run_successor_qualification.py` and by the protocol's own
`check_authorization_state`, and flipping either would advertise a contact
permission far wider than two GETs while eroding the statement that real
qualification still requires its own, later, separate human decision.

So the permission lives in its own narrowly named module,
`scripts/successor_runtime_preflight_authorization.py`, whose surface is
`RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED` and
`RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED`. That module **asserts** the four
qualification constants are still `False`, so widening qualification
authorization now breaks the preflight validator instead of quietly inheriting
it.

The qualification runner was not turned into an executable real-model runner.
`require_execution_authorization` still refuses every execution path, and
supplying the CLI flag and the environment gate still does not substitute for
the missing human record.

---

## 9. What was created under this authorization

| Artifact | Role |
|---|---|
| `docs/post_phaseP_successor_runtime_preflight_contact_authorization.md` | This record. |
| `docs/post_phaseP_successor_runtime_preflight_contact_authorization.json` | Its machine-readable form, generated from the validator so the two cannot drift. |
| `scripts/successor_runtime_preflight_authorization.py` | The narrow authorization surface and its offline validator. |
| `tests/integration/test_successor_runtime_preflight_authorization.py` | Focused tests for the surface, the refusals and the bindings. |

Nothing under `src/iqa_soa/` was modified. Nothing under `benchmark/` was
modified. No provider, model or seed was reselected. No candidate artifact was
rewritten and the candidate was **not** re-frozen: the freeze binds an explicit
artifact set and an explicit frozen-input path list, neither of which this
additive, post-freeze permission record enters, so no existing binding
mechanically requires a re-freeze.

---

## 10. Standing status after this record

| Fact | Status |
|---|---|
| `RUNTIME_PREFLIGHT_METADATA_CONTACT_AUTHORIZED` | `True` |
| `RUNTIME_SNAPSHOT_CAPTURE_AUTHORIZED` | `True` |
| `PROVIDER_CONTACT_AUTHORIZED` (qualification) | `False` |
| `ENDPOINT_PROBE_AUTHORIZED` (qualification) | `False` |
| `MODEL_INFERENCE_AUTHORIZED` | `False` |
| `QUALIFICATION_EXECUTION_AUTHORIZED` | `False` |
| `CONFIRMATORY_EXECUTION_AUTHORIZED` | `False` |
| `PRODUCTION_RANDOMIZATION_AUTHORIZED` | `False` |
| `STAGE_C_FINAL_REGISTRATION_AUTHORIZED` | `False` |
| candidate status | `FROZEN_NOT_YET_QUALIFIED` |
| candidate qualification status | `NOT_YET_QUALIFIED` |
| provider eligibility | `UNASSESSED` |
| Phase P | `UNQUALIFIED` / `HOLD` / `SCHEDULE_COMPLETE_VERDICT_HOLD` |
| provider contacted | `False` |
| model inference performed | `False` |

The next decision remains the one the freeze record already named: a separate
human decision on real provider/model eligibility, registration, randomization,
qualification and confirmatory execution. This record supplies none of it.
