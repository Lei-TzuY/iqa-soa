# S3 - Claim-Evidence-Boundary and test map

This supplement is generated from `artifact/claim_evidence_manifest.json`. The
manifest is the canonical map; this rendering is not maintained independently.
Every test identifier is resolved before verification and is executed by the
appropriate reviewer command.

The complete table is in `artifact/generated/claim_evidence_table.md`. Mechanism
claims cover the instrumented Decorator/Gateway path, exact-name and
argument-contract dispatch refusal, rewrite reauthorization, policy parsing,
guard and evidence failure handling, output containment, and append-only
redacted evidence. Governance claims bind the exactly-once successor run,
terminal accounting, frozen all-task conjunction, retained HOLD, and absent
confirmatory authorization. The effectiveness entry is a verified nonclaim:
this study establishes no QA FULL versus QA OFF treatment effect.

Regenerate and execute the map with:

```text
make generate-paper-evidence
make verify-mechanism
make verify-qualification
```

The deterministic paired trace used in the paper is
`artifact/traces/privacy_exfiltration.json`. Its fixed proposal dispatches once
under QA OFF and zero times under QA FULL, where the Privacy Guard blocks before
the protected side effect. It is mechanism evidence only.
