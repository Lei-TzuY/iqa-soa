# Research Cycle E: original archive recovery

The original `fse2027-external-replication-v1` archive and frozen analyzer were
located on the connected desktop. An offline audit now reproduces the original
qualification decision and every confirmatory analysis field exactly. This
advances the missing-archive checkpoint of PR #51; it does not repeat the earlier
public-source audit or reopen the internal study's frozen HOLD gates.

## Recovery and preservation

Before any shared write, live GitHub and Research Evidence Ledger/Runs were read.
QA PR #42 already contained four commits, ending at Cycle D
`be3d938f834708e286baeec741c89623cc473c47`; its exact-head CI had passed.
The latest saved run was `20261010-QA-D`. No Cycle E checkpoint was found.
FSE PR #51 remained at `bb74eef9a858aa8a75c79baf27620a9322d40fa2`.
Repeated live snapshots were stable. The publication PRs #43 (QA) and #52 (FSE)
change separate release-document paths.

No matching desktop research writer was observed. Cloud-agent liveness cannot
be proved, so branch writes require the observed parent SHA and a fast-forward.
The desktop FSE checkout is at `413f020619fcd1abb68d993820963dd04199cb5d` and has a
tracked figure modification; the QA checkout has untracked research material.
Both original checkouts were kept read-only. No new PR is needed.

## Original input identity

The archive is at `C:\Users\User\Desktop\FSE\results\fse2027-external-replication-v1`.
It contains 3,028 files. SHA-256 of the canonical sorted relative-path-to-file-hash
map, excluding `__pycache__`, is
`4cc3b6316391d695824cc0cde0bbbbb55be172d79a6aeaec3f62fe0de6919295`.
The complete map was calculated before and after the audit and was unchanged.
The original freeze's 22 code/configuration files, 15 study documents,
53-file IQA source tree and 112-file installed AgentDojo tree passed verification.
The freeze manifest self-digest is
`a100807d6db6f50e6a6f079f0a52de92df3b4dec3606e7be9c20f64dffed5b61`.

Execution used the original Python 3.12.10 environment, NumPy 2.1.3 and AgentDojo
0.1.35. Network connections were disabled in the auditor process. No inference,
acquisition CLI, gate runner or report-writing command was called.

## Executed verification

- Regenerated the installed benchmark population and both original schedules,
  including carrier selection, model strata, paired seeds and arm order.
- Matched all 544 qualification and 948 confirmatory terminal records one-to-one
  with their scheduled slots and original `raw.json` records. Every record is
  VALID as recorded. Each original proposal-to-evidence link and mechanical
  telemetry/proposal count was checked; no normalization invented new outcomes.
- Checked ledger STARTED/TERMINAL events and completion markers without retries,
  missing slots or duplicate records. Confirmatory data contain 474 complete
  OFF/FULL pairs, including four carriers per attacker goal and model.
- Verified Stage A/B/C self-digests, input references, the qualification decision,
  frozen eligibility, schedule and analysis-plan references. Internal timestamps
  put qualification before registration and registration before confirmatory runs.
- Re-ran the hash-verified original pure analyzer. Qualification and all original
  confirmatory estimates, p-values, intervals, sensitivity and gate decisions
  match the saved results exactly. Metadata self-digests and run-file references
  were verified separately.
- Independently recomputed point estimates with rational arithmetic, averaging
  carriers within goals before averaging goals and equally weighted model strata.

| Endpoint, FULL minus OFF | Exact estimate | Frozen p-value | Frozen 95% interval | Gate status |
| --- | ---: | ---: | --- | --- |
| Primary eligible CPE-executed | −85/168 = −0.505952 | 0.000010 | [−0.589286, −0.422619] | Confirmatory |
| S1 native attack success | −89/280 = −0.317857 | 0.000010 | [−0.392857, −0.242857] | Confirmatory |
| S2 benign utility | 3/194 = +0.015464 | 0.452555 | [−0.010309, +0.041237] | Not significant; closes sequence |
| S3 utility under attack | 3/35 = +0.085714 | 0.001190 | [+0.039286, +0.132143] | Descriptive; S2 gate closed |

Primary eligibility is 21 canonical goals per model, 42 model-goal units total.
Its model estimates are Qwen −15/28 and Mistral −10/21. The original fixed
100,000-draw sign-flip tests and 20,000-draw stratified bootstraps were reproduced.
Retained historical model requests total 6,411; this recovery made zero new calls.

## Limits and next checkpoint

This is numerical reproduction of recorded outcomes. It does not independently
replay environment/trace oracles or prove that CPE/native outcome labels are
correct. Self-digests and local timestamps establish internal consistency, not
an externally anchored prospective registration. Request payload hashes alone
cannot reconstruct original request bodies. Submission status remains unknown.
The earlier normalized-record checker remains a separate post-hoc tool and was
not passed invented fields or fabricated original evidence.

The next FSE step is independent adapter/oracle replay on these unchanged raw
traces, then a claim-to-oracle assessment; no acquisition or gate rerun is needed
for that read-only work. QA's independent held-out semantic corpus and full
assertion baseline remain missing. Its newly located v0.5 working draft is a
source lead, with current ICST authority still unverified.

`recovery_cycle_e_20261010.json` contains the executed report and input digests.
`archive_recovery_audit.py` reads originals and prints JSON only:

```text
C:\FSE-ext-agentdojo\venv\Scripts\python.exe -B archive_recovery_audit.py "C:\Users\User\Desktop\FSE"
python -B -m unittest discover -s research/external_verification -p test_archive_recovery.py -v
```

Five failure-path tests pass; their synthetic inputs are software checks, not
experimental evidence. Repository CI exercises these tests. CI cannot repeat the
desktop empirical audit without the original archive and frozen environment.
Original manuscripts, reports, raw records and frozen decisions were not edited.
Codex assisted the verification code, execution and recovery notes.
