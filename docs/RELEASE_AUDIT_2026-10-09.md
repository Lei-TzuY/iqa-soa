# Private release audit — 2026-10-09 UTC

**Repository: Lei-TzuY/iqa-soa. Verdict: BLOCKED. Keep PRIVATE.**

Audited default branch `main` at `d6f8638285a393a55a8eaa2fbd11ef4722b56aa1`. Recovered publication PR [#50](https://github.com/Lei-TzuY/iqa-soa/pull/50) was already merged on 2026-10-07. Its valid work is retained. This follow-up does not repeat that cleanup or certify the repository for public release. New unrelated research PRs are outside this remediation.

## Confirmed coverage and limits

| Accessible refs | Commits | Root trees | Unique blob versions | Raw SHA verified | Normalized only | Unavailable blobs |
| --- | --- | --- | --- | --- | --- | --- |
| 83 | 176 | 114 | 1799 | 1799 | 0 | 0 |

The recovery enumerated all advertised Git refs returned by the GitHub API (branches, PR heads, tags and frozen refs), peeled annotated tags and followed every accessible commit parent. No parent lookup failed. Every distinct root tree was retrieved without truncation. This covers API-visible reachable history, not unreachable/server-internal objects, deleted refs, other clones or external services.

Blob content was screened for common provider-token formats, PEM private keys, credentials/connection strings and personal-information candidates; candidate matches were reviewed without recording secret values. Raw bytes were checked against Git blob SHA where available. Text-normalized UTF-16 exceptions are counted separately. Binary strings/ZIP text checks are not full document, image, media, model or OCR review. This was not a comprehensive entropy/dependency-vulnerability/security penetration audit. No confirmed active credential was found in reviewed content; absence of a pattern match is not a release guarantee. Rotate any credential the owner recognizes as having appeared historically; a HEAD deletion alone does not remove it from Git history.

All 334 observed Actions runs across the three research repositories had artifact metadata queried. Nine retained artifacts were identified (all in Quality_Assurance), but all byte-download attempts returned HTTP 403. Logs from 40 jobs across the four latest runs per research repository (12 runs; 3,471,990 decoded UTF-8 bytes) were screened with no secret-pattern matches. Older run/attempt logs were not scanned. The other four repositories had no observed Actions runs. Research workflows already restrict ordinary CI to contents:read; the tagged reviewer-release workflow's contents:write is intentional. No workflows/artifacts/releases were deleted or rewritten.

Repository settings still show PRIVATE and no GitHub Pages site. Administrative secrets/environment settings, deployed databases and external services cannot be inspected by this connector. Complete wiki, issue/PR-comment/discussion and attachment review is not performed; owner must clear these publication surfaces too. Enabled wiki settings do not establish that a wiki exists. No visibility change, force push, shared-history rewrite, evidence deletion, merge or broker communication is authorized by this audit.

Repository Actions run inventory: 8. License status: No repository source license. Collaborator/third-party evidence and manuscript restrictions require approval.

## Findings and publication risk

| Severity | Category | Finding |
| --- | --- | --- |
| HIGH | Double-anonymous review | Submission packaging explicitly depends on the original repository staying private because preserved Git/source identifiers can link anonymous evidence back to its owner. |
| HIGH | IP/research | Source license, collaborator consent and unpublished manuscript/raw-experiment distribution approval are unresolved. |

## Validation evidence

Recovered default-HEAD CI run 37637458690 succeeded: 2,726 passed for each Python 3.11/3.13 test job, with static/submission-artifact checks. Existing CI is reused; no local full suite was rerun.

## Private retention

Preserve refs/frozen-evidence/pr-41 and its commit 7c2848ae28a0e43786915479d65ee60d6daa12d3; keep original research evidence, manuscripts and collaborator material private until approved.

## Required owner decisions and next steps

Owner must resolve the anonymity period and publication policy before any visibility change, choose a source license and approve collaborator/evidence redistribution. A public artifact should have an independently reviewed source/identity policy; do not rewrite frozen evidence.

Preserve the original privately. A reviewed clean-history export can avoid importing restricted old objects, but must include necessary source dependencies, the chosen source license and asset notices. Removing files in a PR does not sanitize the original history. Controlled shared-history rewriting requires a separate explicit authorization and backup plan; it is not performed here.

Before any publication: review/merge applicable safe fixes, validate the final candidate and all distributable assets, clear collaborator/anonymity/IP gates, review Git refs and Actions/logs/releases/metadata at the final SHA, then obtain explicit owner authorization. Only after every gate passes may the release record be changed to `READY_FOR_OWNER_APPROVAL`.

## Sources

- [GitHub repository visibility effects](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility): public source and Actions history/logs are part of the exposure surface.
- [Tatoeba export format/license](https://tatoeba.org/en/downloads): the CC0 subset has ID, language, text and modification-date fields; the full sentence corpus has a different license.
- [Google reCAPTCHA testing FAQ](https://developers.google.com/recaptcha/docs/faq): documented test keys allow verification to pass and are not production credentials.
