# Successor Qualification Hash-Basis Amendment

Amendment ID: `successor-qualification-hash-basis-amendment-1`
Applies to repository state: `55ec4224ee615d94d39a3647d4a61ae115fa9640` (canonical `main`)
Machine-readable sidecar: `docs/post_phaseP_successor_qualification_hash_basis_amendment.json`
Governing policy: `docs/hash_basis_policy.md`
Precedent: `docs/hash_basis_amendment_v1.md` (read as precedent; **not modified**)
Candidate: `prospective-candidate-i5-m1-b76f40da2`

**This amendment is additive.** It edits no evidence file, no frozen source, no
historical digest and no earlier amendment. It changes no experimental result,
no scientific metric, no classification, no exposure count, no task status, no
verdict and no benchmark semantic. Its sole purpose is to record that one
unchanged evidence tree was observed under two different line-ending
materializations, and to name which of the two is the portable basis.

---

## 1. Finding

The successor qualification evidence under
`results/prospective-candidate-i5-m1-b76f40da2-qualification` has been observed
under two working-tree materializations.

The **historical local materialization** carried CRLF line endings on the 102
per-cell `successor-runs.csv` artifacts. Its two aggregate working-tree digests
were recorded, and they are truthful records of bytes that really existed on
disk.

The **canonical LF checkout** — the one the root `.gitattributes`
(`* text=auto eol=lf`) enforces on every platform — carries LF on those same 102
artifacts, and hashes to two different aggregate digests.

Working-tree hashing is the attested basis (`docs/hash_basis_policy.md` §1), and
it is not weakened here. Two different byte sequences therefore correctly produce
two different digests. That is the tamper detector working, not a defect, and not
evidence that different data was ever frozen, observed, scored or analysed.

This is the same class of finding as `hash-basis-amendment-v1` §3: uniform CRLF
against a committed LF blob, differing in line-ending representation and in
nothing else. It is recorded here as a separate, additive amendment because it
concerns different artifacts at a different commit, and because amendment v1 is
never edited.

## 2. The two materialization bases

| | Historical local materialization | Canonical LF materialization |
| --- | --- | --- |
| Result working-tree digest | `2059f30349a852f7c7d06add0d23f90b48527bbc0705dfaa3b6612b926976c62` | `956487194eb68baf1ec509068f5f3474611a61cf4224820dca0599091803bf14` |
| Raw working-tree digest | `d5381b620cf20894cf1b2062027a919d5f887d4ef30477ee426b5ee99b498a61` | `f6a170a0ab271dbc2c4a50eb3130ce48aecb28eaf231bc885abe2c0684587cd7` |
| EOL basis | CRLF on the 102 per-cell `successor-runs.csv` artifacts | repository-enforced LF |
| Status | truthful historical observation, **preserved unchanged** | **portable and clone-reproducible**; the basis for every future check |
| Re-frozen or overwritten | **no** | — |

Both aggregate digests are computed on the repository's own working-tree basis:
sorted POSIX-relative path plus SHA-256 over raw on-disk bytes, per
`docs/hash_basis_policy.md`. No byte is normalized before it is hashed in either
column.

The historical digests above are **not** superseded as observations. What this
amendment supersedes is their *basis* — they are not portable, they will not
reproduce in a clean clone, and no future check may require them.

## 3. Evidence binding

| Binding | Value |
| --- | --- |
| Canonical evidence commit | `55ec4224ee615d94d39a3647d4a61ae115fa9640` |
| PR-head evidence commit | `7c2848ae28a0e43786915479d65ee60d6daa12d3` |
| PR-head and canonical result trees equivalent | **YES** |
| Result namespace | `results/prospective-candidate-i5-m1-b76f40da2-qualification` |
| Result subtree Git tree SHA | `ea15f706415cd429779becbdd9c7dbc9f5695fd0` |
| Result subtree file count | 412 |
| Raw evidence Git tree SHA | `cc843199c9b19d864f58d5d5ec8c380463c633c7` |
| Raw evidence file count | 408 |
| `successor-analysis.json` SHA-256 | `96a89af5f71ad6d25dd52ac0f829570ce8dc47702ae8a603f1c82699b06d203c` |
| `successor-run-manifest.json` SHA-256 | `bf6f994538b85b0918980c5fddc8e49bfc58c7953a0bc1732a7c806bfc7f0837` |
| `successor-runs.jsonl` SHA-256 | `1b97f5f9835a977f9e5076f2a73d7c3843281b29d9440326e2e66b6d4136103e` |
| `successor-partial-manifest.json` SHA-256 | `fd25897400caa721ca921b5033d25ae13a71388aff9f0884722ea21efcb43803` |

`7c2848ae` is the PR-head commit this work was first written against. It is
**not** canonical and is not called canonical anywhere in this record or in the
correction it accompanies. It is retained only because
`git rev-parse <commit>:<namespace>` resolves to the same tree objects at both
commits, for both the result subtree and the raw subtree, which is what
establishes that the earlier observation and the canonical record describe the
same evidence.

The Git tree object is recorded as an **independent second identity**. It is
never substituted for working-tree hashing, which `docs/hash_basis_policy.md` §2
forbids.

## 4. The proven EOL relation

The relation between the two materializations is proven mechanically by
`scripts/successor_qualification_analysis_correction.py::prove_eol_basis_relation`,
which alters no file. The historical form is rebuilt **in memory** from the
canonical LF evidence; nothing is placed on disk, and the evidence tree's digest
is re-checked after the reconstruction to confirm it did not move.

1. **The digest function is the frozen one.** With no supplied materialization,
   the reconstruction's digest function reproduces
   `successor_qualification_protocol.tree_digest` exactly over both subtrees. No
   value computed for this amendment is trusted before that equality holds.

2. **The canonical LF checkout reproduces the canonical digests.** Both aggregate
   digests in the right-hand column of §2 are reproduced from the checkout as it
   stands.

3. **Exactly 102 artifacts participate.** Every `.csv` file beneath the result
   namespace is a per-cell `successor-runs.csv`, and there are exactly 102 of
   them. The remaining 310 evidence files do not participate.

4. **None of them currently carries a CRLF.** Across all 412 evidence files, the
   number containing a CRLF is **0**, and the number containing any `CR` byte at
   all is **0**. `git check-attr eol` reports `lf` for these paths.

5. **Rebuilding those 102 as CRLF reproduces the historical digests exactly.**
   Applying `LF -> CRLF` to exactly those 102 artifacts, and leaving every other
   evidence byte untouched, yields
   `2059f30349a852f7c7d06add0d23f90b48527bbc0705dfaa3b6612b926976c62` for the
   result subtree and
   `d5381b620cf20894cf1b2062027a919d5f887d4ef30477ee426b5ee99b498a61` for the raw
   subtree.

6. **No byte other than the inserted `CR` differs.** For every one of the 102
   artifacts, checked individually and in both directions: the canonical form
   contains no `CR` byte; every `CR` in the reconstructed form is the first byte
   of a `CRLF` pair; deleting every `CR` from the reconstructed form returns the
   canonical bytes exactly; and the number of inserted bytes equals the number of
   LF terminators. Across the set, 204 LF terminators correspond to 204 inserted
   `0x0D` bytes, and **0** bytes differ beyond them.

The per-artifact table — path, canonical LF SHA-256 and byte count, historical
CRLF SHA-256 and byte count, and inserted-`CR` count — is recorded in the JSON
sidecar under `eol_basis_proof.participants.per_file`, together with the digest
`9db01527622bd3390148ec8134241d5617883e1910e91ca12b453085d7babd9d` over the 102
canonical path/SHA-256 identities.

### No hash-time normalization was used

`docs/hash_basis_policy.md` §2 forbids normalizing line endings before hashing as
a way to make a check pass. None is used here, and that is **observable rather
than promised**: a normalizing basis would have collapsed the two columns of §2
into a single value. They are two distinct values, which is only possible if raw
bytes are hashed on both sides.

## 5. Precise claim language

The two materializations are literally different byte sequences. This record
therefore does **not** claim byte identity between them, and the following are
the exact claims made:

| Claim | Value |
| --- | --- |
| `CANONICAL_GIT_TREE_IDENTICAL` | **YES** |
| `SCIENTIFIC_CONTENT_IDENTICAL` | **YES** |
| `HISTORICAL_TO_CANONICAL_BYTE_IDENTICAL` | **NO** |
| `DIFFERENCE_CLASS` | `EOL_REPRESENTATION_ONLY` |
| `HISTORICAL_RECONSTRUCTION` | **PASS** |
| `CANONICAL_LF_REPRODUCIBILITY` | **PASS** |

`RESULT_TREE_BYTE_IDENTICAL = YES` is **not** claimed between the historical and
canonical materializations, and the machine record carries
`result_tree_byte_identical_between_bases_claimed: false` so that the refusal is
explicit rather than an omission.

## 6. Scope of supersession

**Superseded:** the interpretation and hash basis of exactly two values — the
result subtree working-tree aggregate digest and the raw subtree working-tree
aggregate digest of the successor qualification evidence. Future checks bind the
canonical LF column of §2.

**Not superseded, and not within the scope of this amendment:**

- any scientific row, metric, classification, exposure count, near-miss count,
  valid-cell count or task status;
- any verdict, disposition or authorization;
- any benchmark semantic, threshold, seed, arm or scoring rule;
- any frozen artifact digest recorded elsewhere in the repository;
- `docs/hash_basis_policy.md`, `docs/hash_basis_amendment_v1.md` or its JSON
  sidecar, none of which is modified;
- the historical digest observations themselves, which remain recorded verbatim.

Result-namespace files modified: **0**. Tracked files modified: **0**.

## 7. Statements of record

1. The qualification evidence itself is **unchanged**; no byte beneath
   `results/prospective-candidate-i5-m1-b76f40da2-qualification` was modified.
2. Git tree identity is **unchanged**: `ea15f706…` for the result subtree and
   `cc843199…` for the raw subtree, at both the canonical and the PR-head commit.
3. The historical CRLF materialization **really existed**, and both of its
   digests are preserved unchanged as historical observations.
4. The current canonical LF checkout is the **portable and reproducible basis**.
5. **Only line-ending representation differs** between the two materializations,
   over exactly 102 per-cell `successor-runs.csv` artifacts.
6. **No** scientific row, metric, classification, exposure, verdict or benchmark
   semantic changes.
7. This amendment supersedes **only** the interpretation and basis of the two
   working-tree aggregate digests, and **no** scientific artifact.

## 8. Forward rule

Future validation of this evidence MUST use the canonical LF digests of §2, MUST
compute them from raw working-tree bytes in a checkout conformant with
`docs/hash_basis_policy.md` §6, and MUST NOT rewrite either historical digest in
place. Where a historical digest is encountered in the correction or diagnosis
records, this amendment supplies its canonical counterpart.

Nothing in this amendment authorizes a rerun, a cell retry, a cell replacement, a
confirmatory execution or a production randomization. The corrected verdict
remains `HOLD`, and a `HOLD` is a scientific result.
