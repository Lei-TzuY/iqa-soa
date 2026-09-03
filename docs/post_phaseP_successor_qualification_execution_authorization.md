# Final successor real-model qualification execution authorization

**Authorization version:** `successor-qualification-execution-authorization-1`  
**Canonical parent commit:** `a7d9410d4667059da2056994d4af2ff0b029884c`  
**Candidate:** `prospective-candidate-i5-m1-b76f40da2`  
**Candidate status at entry:** `FROZEN_NOT_YET_QUALIFIED`

## Binding human decision

The human reviewer authorizes exactly one real-model successor qualification
execution for `prospective-candidate-i5-m1-b76f40da2` under the already-frozen
successor qualification contract and committed `RuntimeSnapshotV1` evidence.
This is an additive authorization. It does not alter or correct the earlier
record in
`docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md`:
the frozen protocol's provider-contact, endpoint-probe, model-inference and
qualification-execution constants remain historically `False`. The driver must
validate both that unchanged denial and the later machine record before it may
mint an execution capability.

This record binds the canonical parent above plus the exact prospective driver
and input bytes in the companion machine record. It deliberately does not bind a
self-referential final commit SHA.

## Authorized execution

The one execution is exactly:

- 17 frozen tasks x 2 frozen strata x 3 prospectively derived seed values = 102
  cells;
- treatment `off` only;
- `qwen_native_none / qwen3.5:27b` and
  `mistral_native_trailing_user / mistral-small3.2:24b` only;
- seed values `583010984`, `1723431918`, and `1639806953` only;
- instrument `5`, raw schema `6`, `native-tools-adapter-3`, and
  `tool-arguments-1`;
- zero retries, zero replacement cells, no extra seed and no resume as a new
  run;
- persistence of the frozen qualification raw evidence followed by the frozen
  post-run qualification analysis and verdict.

## Network and model capability

For that one future execution only, the driver may contact literal loopback
origin `http://127.0.0.1:11434` for `GET /api/version`, `GET /api/tags`, and the
already-frozen inference endpoint
`POST http://127.0.0.1:11434/v1/chat/completions`. Only the two frozen models
above may be requested. No remote endpoint, unrelated request, model show, pull,
update, retag or replacement is authorized.

Immediately before the first cell, the driver must verify Ollama `0.32.13`, the
Qwen model digest
`7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e`,
and the Mistral model digest
`5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b`.
It must then use the repository-owned `RuntimeSnapshotV1` capture for both
strata. Fresh `captured_at` and `self_digest` values may differ, but the fresh
runtime identities must be exactly:

- Qwen: `3c49ab568c75b07b8c640cd4862003725b4552948cdba594ddd753af4911d30b`;
- Mistral: `5ff8e0922b589522682b3e2d9efd3b55b0e014221011669247d421996d742e48`.

Any mismatch is `ENVIRONMENT_HOLD` with zero cells.

## Exercise gates and exactly-once spending

This authorization is necessary but not sufficient to exercise the run. The
future invocation must also supply both:

- environment `IQA_SOA_SUCCESSOR_QUALIFICATION_HUMAN_GATE=AUTHORIZED`; and
- CLI flag `--execute-real-model`.

The successor credential environment name required by the frozen protocol must
also be present. Neither exercise gate is itself authorization.

The authorization is unspent only while
`results/prospective-candidate-i5-m1-b76f40da2-qualification/` is absent. The
driver creates that namespace once, without overwrite, after the fresh
environment check. Namespace creation spends this authorization permanently for
future invocations. Cleanup-and-rerun, a second qualification, replacement and
resume-as-new-run are forbidden. An interruption follows the locked driver's
fail-closed partial-manifest rule.

## Exact byte bindings

The companion JSON record is canonical and closed. The driver recalculates every
binding below from disk and refuses on any missing, extra, malformed or moved
field. These values are filled mechanically after the final driver bytes and
repository-owned frozen-input recomputation are fixed.

| Binding | SHA-256 |
|---|---|
| candidate freeze record | `c099346d2e1dadaa7da8fbca2cfb3ebbf7b7d3ba4d95083827bb9daee3f339cc` |
| qualification contract | `46b0893b8259d3bb1fed8810fe624d2a3393d5227bc72ea31ee395872dcdadb6` |
| successor frozen execution inputs | `0faf64de2ae5c7b9b4df8bbf40c8656c8c5747977c5d6db1d154d660924de831` |
| authorized qualification driver | `b095d5ac87e4ed551b8d61b8f80d10b2a664ebda058b3abe4b356ccdadc5c2b1` |
| successor model configuration | `7ff2ec9e7a452331e80414194a4f5a74ab87e1c677c48d1abebd173b063566c2` |
| successor qualification configuration | `f5240e2571c3d6141e9d53b0a244daf8f9ce7be8c0f25b0dfd063484d7d8d090` |
| qualification plan | `52cf7303460197a1e605515e9662e9460e6301e4c065706225e0829db28c81f8` |
| seed derivation record | `08afb9ec753358ed1f75d1db645cfe179b1a952dcdc51a29aa23c82f8d70a05e` |
| runtime-preflight report | `c0aa8be9cc00f32f6f85b0ebaa9bb81a8b939f06233d8507c0d1f41998be491b` |

The logical seed-derivation digest is
`97674242a12d05ccac8fe1ee1c1ef3885f2a999da538f1ccc3d2a429b62d4b3b`.
The committed Qwen and Mistral snapshot self-digests are respectively
`5f2ff4e2eaf6852ca87b861e1e93d0d179b5df0956f7f5760d27e37fa89b1d2c`
and `b2c3ea571ad71a7bf02650079e41b6ed5068be85de30b903284dffbffd97161b`.
The frozen qualification schedule digest is
`911ec06cc71d471280f00250377d2238a18068699f95c7792d8ba57c6daa8c95`.

The benchmark case-byte digest remains
`76f40da2402780736616d886f5865a89c66981c4a0aa858340b6b431df03acea`.
The canonical exposure digest remains
`23bd76a57989ac3dc30ea718f0d0b3ac2ae3983a850c3a696868e45b632c4092`.

## Explicitly withheld

This record does not authorize confirmatory execution, confirmatory
randomization, Stage-C registration, a second qualification, retries,
replacement cells, additional seed values, provider/model reselection, runtime
repinning, benchmark or scoring modification, repair after outcomes, historical
Phase-P access, or historical reinterpretation.

## Creation-session boundary

This authorization-and-wiring session performs no provider contact, model
inference or qualification execution. It does not set the exercise environment
gate and does not invoke the real-provider execution path.

