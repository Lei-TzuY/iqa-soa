# Post-Phase-P confirmatory randomization durability clarification

**Work Unit 4 narrow durability repair — MC provenance no-redraw evidence and platform durability**

| | |
|---|---|
| Document base | `origin/main` @ `621ae1b74914833b10946069bcb94b467f0217c4` |
| Implementation tip inspected | `post-phasep-confirmatory-randomization-implementation` @ `e582d7803cc3047eaa7ed6684f828f71a6505ff0` |
| Scope | two persistence-durability gaps only |
| Opens | no methodology, schema, statistical, or lifecycle choice |

---

## 0. Boundary declaration

This clarification is intentionally narrow. It closes exactly two defects found by primary implementation review after WU4 was coded:

1. **D-WU4-1 — MC provenance can redraw after a pre-final persistence failure.** The frozen persistence clarification correctly requires that a Monte-Carlo seed, once acquired, is never silently redrawn for the same `design_id`, but its earlier operation sequence acquires `secrets.token_bytes(32)` before any durable no-redraw evidence necessarily exists. A failure before `randomization_mc_provenance.json` is successfully created can therefore leave neither a final artifact nor any durable marker, re-arming the same `design_id` for another entropy draw.
2. **D-WU4-2 — Windows directory-handle flushing is not accepted as evidence of the required directory-entry durability property.** The assignment clarification freezes a semantic durability obligation, not merely a syscall returning success. The implementation probe used `FlushFileBuffers` on a directory handle, but the Windows platform documentation does not document that call as a supported directory-handle durability primitive. A probe that returns success is insufficient evidence for the frozen guarantee.

Everything else remains frozen and is not reopened:

- the confirmatory estimand, statistic, exact/Monte-Carlo threshold, plus-one inference, and sharp-null semantics;
- Stage A/B/C schemas and loaders;
- the exact 10-key `EXACT_ENUMERATION` MC-provenance schema;
- the exact 19-key `MONTE_CARLO` MC-provenance schema;
- the exact 13-key `AssignmentManifestV1` schema;
- canonical JSON and `self_digest`;
- `task_order` / `bits`, one bit per registered task, `K = 0`, and `resolve_label` / `complement`;
- assignment `R1`–`R7` and the `R5 -> R5' -> R6` ordering, except that this document narrows what counts as a supported Windows realization of the already-frozen durability semantic property;
- the public assignment error mapping `A1` / `A16` / `A19`;
- all WU1–WU3 code and behavior;
- Phase-P evidence and interpretation.

This document changes **zero scientific JSON fields** and adds **zero scientific artifacts**.

```text
WU4_DURABILITY_CLARIFICATION_FROZEN
MC_PROVENANCE_NO_REDRAW_GAP_CLOSED: YES
WINDOWS_DIRECTORY_HANDLE_FLUSH_ACCEPTED: NO
WINDOWS_VOLUME_FLUSH_REFERENCE_PATH_FROZEN: YES
WU4_DURABILITY_FIX_READY_FOR_CODE: YES
```

---

## 1. Binding relationship to the existing persistence clarification

The binding source remains:

`docs/post_phaseP_confirmatory_randomization_persistence_schema_clarification.md`

This document **supplements** that record only where its already-frozen guarantees could not be realized by the implementation sequence it described.

The following existing requirements remain controlling:

- provenance generation and persistence are one public operation;
- no caller can inject a seed, timestamp, NumPy version, mode, `M`, or random source;
- `MONTE_CARLO` calls `secrets.token_bytes(32)` exactly once;
- after entropy acquisition, there is no automatic retry and no second draw for the same `design_id`;
- a failed attempt requires the abandon-and-recreate / new-`design_id` path when a safe same-design recovery cannot be proved;
- assignment durable reservation precedes every assignment-bit draw;
- assignment final publication is no-clobber and its final directory entry becomes durable before `.pending` cleanup.

Where the prior provenance sequence relied on the eventual existence of `randomization_mc_provenance.json` to block redraw, this clarification adds the missing **pre-entropy durable reservation** for Monte-Carlo mode.

---

## 2. No scientific schema change

The scientific artifacts remain exactly:

```text
randomization_mc_provenance.json
assignment_manifest.json
```

The new operational path is:

```text
results/confirmatory/<design_id>/randomization_mc_provenance.json.pending
```

It is **not** a seventh scientific artifact and is not added to the implementation-design artifact catalog.

It has no `schema_version`, no `self_digest`, no scientific fields, no lifecycle state, and no downstream digest reference. No loader, runner, or analyzer consumes it as scientific input.

The persisted scientific key counts remain:

```text
EXACT_ENUMERATION provenance: 10
MONTE_CARLO provenance:       19
AssignmentManifestV1:        13
```

The operational provenance reservation therefore changes **zero** canonical scientific bytes and **zero** scientific digests.

---

## 3. MC provenance durable no-redraw reservation

### 3.1 Frozen path and marker

For `MONTE_CARLO` mode only, production provenance generation uses:

```text
final:   results/confirmatory/<design_id>/randomization_mc_provenance.json
pending: results/confirmatory/<design_id>/randomization_mc_provenance.json.pending
```

The `.pending` file begins as exactly:

```text
MC_PROVENANCE_GENERATION_RESERVED_V1\n
```

The marker is operational evidence only. It carries no seed material and no scientific metadata.

### 3.2 Why this reservation exists only on the Monte-Carlo branch

`EXACT_ENUMERATION` calls no entropy API and therefore has no seed-shopping / redraw risk. Its existing exclusive-create persistence path remains unchanged.

`MONTE_CARLO` acquires an exogenous 256-bit seed. Once that draw occurs, losing every durable trace of the attempt would permit an undetectable second draw for the same `design_id`. The reservation exists solely to make that impossible.

A `.pending` file encountered under an exact-mode registration is an impossible operational state for a conforming implementation and is therefore refused fail-closed rather than silently removed or ignored.

---

## 4. Frozen Monte-Carlo provenance operation sequence

For `MONTE_CARLO`, the production operation still accepts only `(confirmatory_root, design_id)` and now executes in this exact order:

1. Load and revalidate the complete Stage-A/B/C chain from disk.
2. Derive mode, `K`, statistic id, and registered `M` from the validated registration only.
3. Compute the final and `.pending` provenance paths using the existing safe-`design_id` discipline.
4. **Final-first gate:** if the final provenance path exists, raise `DuplicateMcProvenanceError`. This occurs before reservation creation and before entropy.
5. If final is absent and `.pending` already exists, raise `McProvenanceIntegrityError`. Draw zero entropy bytes. Do not clean, repair, resume, or replace the reservation.
6. Exclusive-create `.pending` and write `MC_PROVENANCE_GENERATION_RESERVED_V1\n`.
7. Flush and sync the `.pending` file data.
8. Durably synchronize the filesystem metadata that contains the newly-created `.pending` directory entry. If this durability property cannot be established, fail **before entropy** and retain `.pending` if it exists.
9. Capture `generated_at`.
10. Call `secrets.token_bytes(32)` **exactly once**.
11. Convert the exact 32 bytes to `seed_hex` and the unsigned big-endian `seed_int`; construct `Generator(PCG64(seed_int))` as already frozen.
12. Construct the exact nineteen-key body from frozen values and internally captured values.
13. Capture `created_at`, compute `self_digest`, and validate the complete `P1`–`P24` contract in construction-time form.
14. Exclusive-create `randomization_mc_provenance.json`.
15. Write the complete canonical scientific bytes, flush them, and sync the final file data.
16. Durably synchronize the filesystem metadata containing the final provenance directory entry. **For Monte-Carlo mode, successful completion of this barrier is the operational instant `MC_PROVENANCE_PERSISTED` begins.**
17. **Only after step 16 succeeds** may `.pending` be unlinked. Cleanup is optional/non-authoritative; cleanup failure does not invalidate a valid final provenance artifact.
18. Return only the already-persisted, already-validated provenance object.

There is no second entropy call anywhere in this operation.

---

## 5. Provenance reservation error and restart semantics

No new exception class is minted.

The production provenance operation obeys this exact gate:

| On-disk state | Production generation behavior |
|---|---|
| final absent, pending absent | may begin a new MC attempt by reserving `.pending` durably before entropy |
| final absent, pending present | `McProvenanceIntegrityError`; zero entropy; human/new-`design_id` path |
| final present, pending absent | `DuplicateMcProvenanceError`; zero entropy |
| final present, pending present | final-first `DuplicateMcProvenanceError`; zero entropy; `.pending` is operational residue only |

A race at reservation creation is fail-closed: if exclusive creation of `.pending` reports existence, re-check final. If final now exists, return the duplicate-final refusal; otherwise return `McProvenanceIntegrityError`. In neither branch is entropy acquired.

The public **provenance loader** continues to read only the final scientific artifact and continues to implement `P1`–`P24`. It does not read `.pending` and does not add a twenty-fifth rule.

---

## 6. Provenance crash-window exhaustion

The new reservation closes every same-design redraw window:

| Crash/failure point | Required outcome |
|---|---|
| after `.pending` creation but before its directory entry is durable | operation has not acquired entropy; fail closed |
| after durable `.pending`, before `token_bytes` | `.pending` blocks any later same-design generation; zero seed was drawn, but the conservative design burns the `design_id` |
| immediately after `token_bytes(32)` | durable `.pending` remains; retry refuses before entropy |
| after entropy, before final `open("xb")` | durable `.pending` remains; retry refuses before entropy |
| final create itself fails | durable `.pending` remains; retry refuses before entropy |
| crash during final write | final may be partial and `.pending` remains; generation sees final first and never redraws; loader rejects malformed final |
| final file-data sync fails | `.pending` remains; no redraw |
| final directory-entry durability sync fails | `.pending` remains; no redraw; the operation has not reached `MC_PROVENANCE_PERSISTED` |
| final durable, cleanup not yet attempted | final is authoritative; state has advanced; no redraw |
| cleanup fails | final remains authoritative; no redraw |

Manual deletion or alteration of the operational reservation is outside the automatic protocol threat model, exactly like manual deletion of the assignment reservation.

```text
MC_PROVENANCE_POST_ENTROPY_CRASH_CAN_REARM_SAME_DESIGN: NO
```

---

## 7. Windows durability evidence — correction

### 7.1 Directory-handle `FlushFileBuffers` is not accepted

The implementation at `e582d78` opens a directory using `CreateFileW(..., FILE_FLAG_BACKUP_SEMANTICS, ...)` and then calls `FlushFileBuffers` on that directory handle.

A successful local probe is **not** enough to establish the frozen semantic property.

Platform evidence checked for this clarification:

- Microsoft documents obtaining directory handles with `CreateFile` + `FILE_FLAG_BACKUP_SEMANTICS`, and separately enumerates functions documented to accept directory handles; `FlushFileBuffers` is not in that documented directory-handle list.
- Microsoft documents `FlushFileBuffers` for an open file handle and explicitly documents a separate supported use in which a **volume handle** is supplied to flush all open files on a volume; that volume operation requires administrative privileges.

Therefore:

```text
FlushFileBuffers(directory_handle) success
```

is not accepted as proof of `R3`, `R5'`, MC-reservation directory-entry durability, or MC-final directory-entry durability.

The implementation must not silently retain that path as a fallback.

### 7.2 Required semantic property remains unchanged

The actual requirement is still:

> durably synchronize the filesystem metadata containing the relevant newly-created directory entry before the protocol is allowed to cross the next no-redraw boundary.

That applies to:

1. assignment `.pending` creation before any assignment bit draw (`R3`);
2. assignment final entry after `os.link` and before assignment `.pending` cleanup (`R5'`);
3. MC-provenance `.pending` creation before `token_bytes(32)`;
4. MC-provenance final entry before MC `.pending` cleanup.

---

## 8. Windows reference realization

For a **local Windows volume**, the accepted reference realization is a documented **volume flush**, not a directory-handle flush.

A conforming Windows implementation executes the durability barrier as follows:

1. Resolve the target path to the local volume that contains the confirmatory design directory.
2. Open the relevant parent directory with `CreateFileW` + `FILE_FLAG_BACKUP_SEMANTICS` and **keep that directory handle open across the volume flush**. The directory handle exists to anchor the affected directory object as open; `FlushFileBuffers` is **not** called on this handle.
3. Open the containing volume with `CreateFileW` using a supported volume path form (for example a drive-volume form or volume-GUID form without a trailing root separator) and the access required by `FlushFileBuffers`.
4. Call `FlushFileBuffers` on the **volume handle** while the parent-directory handle from step 2 remains open.
5. Treat success as the Windows durability barrier for the preceding directory-entry mutation.
6. Close both native handles reliably.

Microsoft documents that flushing a volume this way requires administrative privileges. That requirement is accepted by this confirmatory protocol.

If the parent directory cannot be opened under documented directory-handle semantics, the process lacks the necessary volume privilege, the path is a remote/UNC path for which an equivalent supported durability primitive cannot be established, volume resolution fails, the volume cannot be opened, or the volume flush fails, the operation **fails closed** at the relevant boundary.

No assignment bit or MC seed may be drawn after a failed pre-draw/pre-entropy durability barrier.

For a post-draw/post-entropy final-entry barrier failure, retain the corresponding `.pending` reservation and fail. Do not clean it up and do not retry generation.

The implementation is allowed to support additional platform-specific mechanisms in the future only if they provide equal or stronger documented durability semantics. A mere successful syscall probe is not sufficient evidence.

---

## 9. POSIX reference realization

The existing POSIX realization remains accepted:

1. file contents are flushed and `fsync`-ed where the protocol requires durable file data;
2. the parent directory is opened as a directory descriptor;
3. `fsync` is called on that directory descriptor after the relevant directory-entry mutation;
4. any unsupported operation or failure is propagated fail-closed.

No portability claim is made for filesystems that do not honor the durability semantics required by the underlying calls. A configured filesystem on which the property cannot be established is not eligible for this persistence operation.

---

## 10. Scientific-state interpretation

Operational reservations do not create lifecycle states.

For `EXACT_ENUMERATION`, `MC_PROVENANCE_PERSISTED` retains the existing meaning: the final provenance artifact has been successfully persisted and validates under the frozen scientific contract; no entropy reservation exists on this branch.

For `MONTE_CARLO`, final-file existence alone is **not** sufficient for the generating operation to report successful state advancement. `MC_PROVENANCE_PERSISTED` begins only after all three conditions hold:

1. the final nineteen-key artifact is complete and validates under `P1`–`P24`;
2. its final file data has been durably synchronized; and
3. the final provenance directory entry has passed the step-16 durability barrier.

A `.pending` file alone never means the state has advanced. If step 16 fails, the operation returns failure, retains `.pending`, and does not report `MC_PROVENANCE_PERSISTED` even if the final pathname happens to remain visible in the current process lifetime.

`ASSIGNMENT_PERSISTED` remains governed by the already-frozen assignment clarification: successful durable final-entry synchronization (`R5'`) is the publication boundary; `.pending` is not scientific state.

No state-machine token or persisted state field is added or renamed.

---

## 11. Implementation repair authorization

Under the already-merged WU4 code authorization, the implementation branch may make only the changes necessary to realize this clarification.

Expected source/test surface remains:

```text
src/iqa_soa/experiment/confirmatory_assignment.py
tests/unit/test_confirmatory_assignment.py
```

No real confirmatory artifact may be generated. No Phase-P artifact may be inspected or modified.

The repair must preserve every passing WU4 schema/loader/randomness test not contradicted by this clarification.

---

## 12. Required focused regression tests

At minimum, add or strengthen synthetic tests proving all of the following.

### 12.1 MC provenance no-redraw tests

- MC `.pending` is created and made durable **before** the first `token_bytes(32)` call.
- Existing MC `.pending` with no final artifact causes `McProvenanceIntegrityError` and zero entropy calls.
- Existing final provenance causes `DuplicateMcProvenanceError` and zero entropy calls.
- Concurrent reservation loss (`FileExistsError`) causes zero entropy calls.
- Failure of the final provenance `open("xb")` **after entropy** leaves `.pending`; a second call draws zero additional entropy.
- Failure during final write leaves `.pending`; a second call draws zero additional entropy.
- Failure of final file-data sync leaves `.pending`; a second call draws zero additional entropy.
- Failure of final directory-entry durability sync leaves `.pending`; a second call draws zero additional entropy and the operation does not report `MC_PROVENANCE_PERSISTED`.
- Final + pending is final-authoritative for generation: duplicate-final refusal, zero entropy.
- Successful final persistence does not clean `.pending` until after final directory-entry durability succeeds.
- Exact mode still makes zero entropy calls and does not require an MC reservation.
- Neither scientific provenance schema contains a `pending` field; key counts remain 10/19.

### 12.2 Windows durability tests

Native Windows behavior is tested by mocking the Win32 boundary rather than requiring an elevated test runner.

Tests must prove:

- the accepted Windows durability helper opens/holds the parent directory handle but targets the **volume handle** for the actual `FlushFileBuffers` barrier;
- the parent-directory handle remains open while the volume flush executes;
- the implementation no longer treats `FlushFileBuffers(directory_handle)` as proof of durability;
- inability to resolve/open/flush the volume, or inability to open the parent directory under supported semantics, fails closed;
- pre-draw assignment reservation failure causes zero `randbits` calls;
- pre-entropy provenance reservation failure causes zero `token_bytes` calls;
- assignment `R5'` failure retains assignment `.pending`;
- provenance final-entry durability failure retains provenance `.pending`;
- no cleanup callback occurs before the relevant durability barrier succeeds.

---

## 13. Explicit non-changes

This clarification does **not** authorize:

- changing the MC seed algorithm;
- changing PCG64 or NumPy-version provenance;
- changing `M`;
- changing any randomization bit;
- adding a caller-controlled random source;
- changing the assignment scientific schema;
- changing the provenance scientific schema;
- changing canonical JSON;
- changing Stage A/B/C;
- changing the confirmatory statistic or analyzer;
- changing the runner;
- running a real confirmatory experiment;
- touching historical Phase-P evidence.

Full pytest is still **not** required for this narrow repair. Focused WU1–WU4 regression plus strict mypy remains the gate until the final merge candidate.

---

## 14. Closure checklist

| Requirement | Status |
|---|---|
| Exact provenance stays 10 keys | YES |
| MC provenance stays 19 keys | YES |
| Assignment stays 13 keys | YES |
| MC seed source remains `secrets.token_bytes(32)` exactly once | YES |
| No caller seed surface | YES |
| Durable evidence exists before MC entropy | YES |
| Failure after MC entropy cannot re-arm same `design_id` | YES |
| MC operational reservation is outside scientific digest chain | YES |
| Monte-Carlo state does not advance before final directory-entry durability succeeds | YES |
| Assignment `R5 -> R5' -> R6` remains frozen | YES |
| Directory-handle `FlushFileBuffers` accepted as Windows proof | NO |
| Documented Windows volume-flush path accepted as reference realization | YES |
| Parent directory handle remains open across Windows volume flush | YES |
| Unsupported Windows durability fails closed | YES |
| Phase-P remains untouched | YES |

```text
UNRESOLVED_WU4_DURABILITY_ITEMS: NONE
REMAINING_WU4_DURABILITY_ARCHITECTURE_CHOICES: NONE
WU4_DURABILITY_FIX_READY_FOR_CODE: YES
```
