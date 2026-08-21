# Hash-Basis and Checkout Policy

Status: normative for this repository, effective from the commit that introduces
the root `.gitattributes`.

Scope: this document defines *what bytes a SHA-256 freeze attests* and *how those
bytes are materialized on disk*. It changes no experimental result, no metric, no
benchmark semantics, and no runtime, provider, or guard behaviour.

---

## 1. What a freeze attests

A SHA-256 freeze in this repository attests the **raw working-tree bytes** of the
file as the experiment actually read it. Validators hash the file exactly as it
exists on disk:

- `src/iqa_soa/benchmark/pilot.py` hashes `candidate.read_bytes()` for each frozen
  case and `raw_bytes` for the manifest.
- `src/iqa_soa/metrics/pilot.py` and `src/iqa_soa/metrics/statistics.py` hash
  `manifest_path.read_bytes()`.
- The Phase-D verifier hashes the qualification plan file on disk.

This is deliberate. Hashing the bytes actually consumed is what makes the freeze a
**tamper detector**: if a case file, manifest, or plan is edited on disk between
freeze and run, the digest changes and the run is rejected.

## 2. Prohibited weakenings

The following are **not** permitted, because each destroys the tamper-detection
property above:

- **Hash-time normalization.** Never `read_bytes().replace(b"\r\n", b"\n")` before
  hashing, and never hash decoded text with `newline=` translation. A normalizing
  validator cannot distinguish a benign EOL difference from an injected `\r`.
- **Blob-only hashing.** Never replace working-tree hashing with
  `git cat-file blob` / `git hash-object` lookups. The Git object store attests
  what was *committed*, not what the experiment *read*; a modified working tree
  would silently validate.
- **Silent re-freezing.** Never overwrite a recorded historical digest in place to
  make a check pass. Superseded or re-based digests are recorded additively, in a
  new amendment record.

## 3. Canonical representation

The canonical text representation of every tracked text file in this repository is
**LF (`\n`)**. This is already true of the Git object store: every tracked text
blob at `47e237c` is LF-only.

The root `.gitattributes` makes the *checkout* match that basis:

```
* text=auto eol=lf
```

- `text=auto` — Git classifies files, normalizing text to LF on check-in. The
  committed blobs are already LF, so this introduces no content change; running
  `git add --renormalize` is unnecessary and is not part of this policy.
- `eol=lf` — text files are materialized in the working tree with LF on **every**
  platform, overriding the user's `core.autocrlf` and `core.eol` settings.

Consequence: working-tree bytes equal committed blob bytes for text files in a
clean checkout, on Windows, Linux, and macOS alike. `eol=lf` is repository-enforced
cross-platform checkout semantics; it is a property of the committed attribute
file, not of any one machine's configuration.

Hashing is unchanged. Working-tree bytes are still what gets hashed — the policy
only makes those bytes deterministic across clones.

## 4. Why this was needed

Git for Windows ships `core.autocrlf=true` in its system config. Without a
`.gitattributes`, a Windows clone of this repository materializes text files with
CRLF while a Linux clone materializes LF. Working-tree hashing then yields
different digests for byte-identical committed content, and freeze validation fails
for reasons unrelated to tampering.

This was not hypothetical. On canonical `main` (`47e237c`) the full suite is:

| checkout materialization | `pytest` result |
| --- | --- |
| CRLF (Windows default `core.autocrlf=true`) | **5 failed**, 279 passed |
| LF (canonical) | **284 passed** |

All five failures were Phase-D verifier tests rejecting
`docs/phaseD_instrument_qualification_plan.md` because its CRLF materialization
hashes to `bd6ce851…` instead of its frozen LF digest `2896f0e0…`. The frozen
digest was correct; the checkout was not.

## 5. Two distinct classes of digest

These must never be conflated:

**Canonical repository / freeze basis** — the digest of the LF bytes that a
conformant checkout materializes. Portable, reproducible on any platform, and the
basis every *future* freeze must use.

**Historical local materialization observation** — a digest that was recorded from
one particular machine's working tree, whose EOL form depended on that machine's
`core.autocrlf` setting and edit history. Such a digest is a truthful record of
bytes that really existed locally, but it is *not* portable and will not reproduce
in a clean clone.

At `47e237c` the repository contains both classes. Five artifacts carry historical
records on a non-LF basis; they are enumerated, with their canonical LF
counterparts, in `docs/hash_basis_amendment_v1.md` and its JSON sidecar. Those
historical records are left unchanged. The amendment is additive.

## 6. Rules for new freezes

1. Verify checkout policy conformance **before** generating any new frozen
   artifact: `.gitattributes` present, `git check-attr eol -- <path>` reports `lf`,
   and the file's working-tree bytes contain no `\r\n`.
2. Generate and record the digest from the working-tree bytes of that conformant
   checkout. It will equal the committed blob digest.
3. Never edit a recorded digest to make a check pass. Investigate the byte
   difference; if the difference is legitimate, record it in a new amendment.
4. `tests/integration/test_hash_basis_invariants.py` enforces items 1–2 and the
   prohibitions in §2. It is offline and deterministic.

## 7. Refreshing an existing working tree

`.gitattributes` governs *checkout*. A working tree that was materialized before
this policy landed keeps its old CRLF bytes until the files are re-checked-out.
Committed content is unaffected either way. To re-materialize a clean tree:

```sh
git rm --cached -r .      # drop index entries only; blobs are untouched
git reset --hard          # re-materialize every file under the new attributes
```

or simply re-clone. Do **not** use `git add --renormalize` for this: the blobs are
already LF, so it has no content to normalize, and it is explicitly out of scope
for this policy.
