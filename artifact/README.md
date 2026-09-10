# Submission evidence contract

This directory is the machine-readable boundary between paper claims and the
repository evidence used to support them.

- `claim_evidence_manifest.json` classifies each claim as mechanism,
  governance, or effectiveness evidence and records both its supported scope
  and explicit nonclaims.
- `trust_boundary.json` names the trusted computing base, untrusted inputs,
  out-of-scope threats, and the disposition of each reviewed bypass surface.
- `study_metadata.json`, `traces/privacy_exfiltration.json`, and files under
  `generated/` are deterministic products of retained artifacts and executable
  mechanism code. Regenerate them with `make generate-paper-evidence`; CI checks
  byte identity rather than accepting hand-edited copies.

None of these commands contacts a provider, reruns qualification, changes a
threshold, or creates confirmatory evidence.
