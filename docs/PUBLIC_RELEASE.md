# Publication preparation

## Current evidence boundary

Mechanism and governance evidence remain established only within the scope
declared in the README. Effectiveness is **not established** and the frozen
successor terminal state remains **HOLD**. No cells, thresholds, manifests,
scores, authorization records or recorded Git object identifiers are changed.

The reviewer verification path needs a full Git clone and the frozen PR-41
evidence object. Preserve these objects and refs; replacing this repository
with a source-only copy would not reproduce all qualification gates.

## Concrete anonymity dependency

`scripts/submission_artifact.py` declares `_PROVENANCE_EXPORT_PREFIXES` and
retains repository object identifiers in frozen export records. Its
`verify_anonymity()` reports that the export is anonymous only while the source
repository is not publicly readable. Public visibility would make those
identifiers linkable to this repository and its author.

**Keep the source repository private while relying on that anonymous-review
condition.** A successful anonymity check does not authorize making the source
public. Resolve the review/publication timing separately without rewriting
frozen scientific records to hide their provenance. This preparation does not
assert that a particular submission is currently under review.

## Release boundaries

New ignore rules cover local provider environment variables, secrets and
working notes. Existing evidence and anonymous-build rules remain intact.
No top-level code license is present; one was not selected on behalf of the
authors. Confirm collaborator and third-party reuse permissions before a
redistributable release. Full historical, binary and Actions-log clearance has
not been completed by this documentation change.
