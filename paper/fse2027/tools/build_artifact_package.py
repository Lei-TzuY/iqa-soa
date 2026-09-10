#!/usr/bin/env python3
r"""Assemble the anonymous FSE 2027 replication package.

    python paper/fse2027/tools/build_artifact_package.py

Writes ``paper/fse2027/artifact-anonymous/``, a self-contained, double-anonymous
snapshot of exactly the evidence the manuscript claims, plus the software needed
to inspect it.

WHAT THIS SCRIPT DOES NOT DO
============================

It runs no model, contacts no provider, opens no network socket, executes no
qualification, and recomputes no verdict. It copies bytes and, for the local
filesystem paths described below, rewrites them. Every source file under
``results/`` is opened read-only; none is modified, rescored, reclassified, or
reinterpreted.

It never reads, lists, traverses, hashes, or opens the Phase-P results
namespace, or any ``FSE-*-schema-clarification`` working directory. Those paths
are asserted absent from the copy set in :func:`assert_forbidden_paths_absent`.

THE ONE TRANSFORMATION APPLIED
==============================

The successor qualification artifacts record, alongside every repository-relative
path and its SHA-256, the *absolute* local path the run happened to use. Those
absolute paths name a local filesystem and must not ship in a double-anonymous
package. Each is rewritten to ``<ARTIFACT_ROOT>/`` plus the same tail, with
separators normalised to ``/``.

This is safe to the byte level:

* every rewritten field has a sibling ``repository_relative_path`` /
  ``canonical_repository_relative_path`` carrying the same file identity;
* every input digest (``*_sha256``) is over the *contents* of the referenced
  file, never over the path string, and is copied unchanged;
* no artifact carries a self-digest over its own file bytes, so no digest
  binding is invalidated (``schedule_digest`` is over the schedule, not the
  manifest file).

Every rewrite is recorded, with the original and redacted SHA-256 of each
touched file, in ``redaction-report.json``, so a reviewer can confirm that the
redaction changed paths and nothing else.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "paper" / "fse2027" / "artifact-anonymous"
ARCHIVE = ROOT / "paper" / "fse2027" / "build" / "fse2027-anonymous-artifact.zip"

QUAL = "results/prospective-candidate-i5-m1-b76f40da2-qualification"
PREFLIGHT = "results/prospective-candidate-i5-m1-b76f40da2-runtime-preflight"

#: Paths this script must never touch, in any mode, for any reason.
FORBIDDEN = (
    "results/phaseP-rc4-qualification",
    "FSE-eligibility-schema-clarification",
    "FSE-final-registration-schema-clarification",
    "FSE-persistence-schema-clarification",
    "FSE-schema-clarification",
    ".git",
)

EXCLUDE_DIR_NAMES = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache",
                     ".ruff_cache", "iqa_soa_fse.egg-info"}

BS = chr(92)
#: ``C:\Users\...\FSE\rest`` or ``C:\\Users\\...\\FSE\\rest`` (JSON-escaped).
ABS_PATH = re.compile(
    r"[A-Za-z]:(?:" + re.escape(BS) + r"{1,2}|/)"
    r"(?:[^\"\\/\s]+(?:" + re.escape(BS) + r"{1,2}|/))*?FSE(?:" + re.escape(BS) + r"{1,2}|/)"
)

# ---------------------------------------------------------------------------
# The copy set. Each entry: (source, destination, role, paper section, class)
#   class: "result"   = scientific/result artifact (evidence, never regenerated)
#          "software" = software artifact (code, config, schema, docs)
# ---------------------------------------------------------------------------
FILES: list[tuple[str, str, str, str, str]] = []
TREES: list[tuple[str, str, str, str, str, tuple[str, ...]]] = []


def add(src: str, dst: str, role: str, section: str, kind: str) -> None:
    for old_src, old_dst, *_ in FILES:
        if old_dst == dst:
            if old_src != src:
                raise ValueError(f"conflicting package destination {dst}: {old_src}, {src}")
            return
    FILES.append((src, dst, role, section, kind))


def add_tree(src: str, dst: str, role: str, section: str, kind: str,
             suffixes: tuple[str, ...] = ()) -> None:
    TREES.append((src, dst, role, section, kind, suffixes))


def build_copy_set() -> None:
    FILES.clear()
    TREES.clear()
    # -- 1. Runtime governance implementation ------------------------------
    add_tree("src/iqa_soa", "code/src/iqa_soa",
             "Runtime governance implementation (Service Gateway, Service "
             "Decorator, ordered guard chain, QA-XML, evidence log)",
             "Sections 3-4", "software", (".py",))
    add("schemas/qa-policy.xsd", "code/schemas/qa-policy.xsd",
        "QA-XML policy schema (strict validation of executable constraints)",
        "Section 3.3", "software")
    add("configs/policies/default.xml", "code/configs/policies/default.xml",
        "Executable QA-XML policy used by the runtime",
        "Section 3.3", "software")
    add("pyproject.toml", "code/pyproject.toml",
        "Package metadata, pinned dependencies, and the pytest configuration "
        "(pythonpath=src) that makes the RQ1 commands resolve",
        "Section 7.1", "software")

    # -- 2. Deterministic mechanism validation tests -----------------------
    for t in ("tests/integration/test_gateway.py", "tests/unit/test_qa_xml.py",
              "tests/unit/test_qa_guards.py", "tests/unit/test_evidence_logger.py",
              "tests/unit/test_qa_policy.py"):
        add(t, "code/" + t,
            "Deterministic mechanism-validation test file named in Section 7.1",
            "Section 7.1", "software")

    # Canonical submission-evidence contract and the exact source/test paths
    # it names.  Paths are mirrored under code/ so the repository verifier can
    # resolve the same claim IDs inside the anonymous package.
    claims = json.loads((ROOT / "artifact/claim_evidence_manifest.json").read_text("utf-8"))
    for f in (
        "artifact/claim_evidence_manifest.json",
        "artifact/trust_boundary.json",
        "artifact/study_metadata.json",
        "artifact/traces/privacy_exfiltration.json",
        "artifact/generated/claim_evidence_table.md",
        "artifact/generated/claim_evidence_table.tex",
        "artifact/generated/end_to_end_trace.md",
        "artifact/generated/end_to_end_trace.tex",
        "artifact/generated/study_status.md",
        "artifact/generated/study_status.tex",
    ):
        add(f, "code/" + f,
            "Canonical generated submission evidence or its machine-readable contract",
            "Sections 3, 7, 11", "software")
    add("scripts/submission_artifact.py", "code/scripts/submission_artifact.py",
        "Offline generator and verifier for claims, trace, qualification accounting, paper drift, and anonymity",
        "Sections 7, 11", "software")
    add("README.md", "code/README.md",
        "Reviewer entry point and evidence-classification boundary", "Artifact", "software")
    add("paper/fse2027/main.tex", "code/paper/fse2027/main.tex",
        "Anonymous manuscript source consuming generated evidence", "Paper", "software")
    add("paper/fse2027/references.bib", "code/paper/fse2027/references.bib",
        "Verified bibliography used by the anonymous manuscript", "Related work", "software")

    contract_sources = {
        path
        for claim in claims["claims"]
        for path in claim["artifact_paths"]
    }
    contract_sources.update(claims["canonical_study_sources"].values())
    contract_tests = {
        test_id.split("::", 1)[0]
        for claim in claims["claims"]
        for test_id in claim["test_ids"]
    }
    for src in sorted(contract_sources | contract_tests):
        if src.startswith("src/iqa_soa/"):
            continue  # already included by the complete runtime source tree
        add(src, "code/" + src,
            "Source or exact test referenced by the canonical claim-evidence manifest",
            "Claim-Evidence-Boundary table", "software")

    # -- 3. Frozen benchmark and candidate ---------------------------------
    for f in ("manifest.json", "freeze-record.json", "provenance.json",
              "qualification-contract.json", "AUDIT.md"):
        add(f"benchmark/pilot-v7-rc4/{f}", f"benchmark/pilot-v7-rc4/{f}",
            "Frozen benchmark definition at version pilot-v7-rc4",
            "Sections 5, 7.2", "software")
    # The frozen candidate definition. The paper's Data Availability section
    # names it explicitly, so the package must carry it or contradict the paper.
    add_tree("candidates/prospective-candidate-i5-m1-b76f40da2",
             "candidate/prospective-candidate-i5-m1-b76f40da2",
             "Frozen candidate definition: manifest, freeze record, digest "
             "manifest, change ledger, provenance, qualification contract, "
             "resource-selection audit and sink-applicability register",
             "Sections 5, 7.2", "software")

    manifest = json.loads((ROOT / "benchmark/pilot-v7-rc4/manifest.json").read_text("utf-8"))
    for case in manifest["cases"]:
        rel = case["path"]
        add(f"benchmark/{rel}", f"benchmark/cases/{rel}",
            f"Frozen task definition {case['task_id']} (1 of the 17 selected roles)",
            "Sections 5, 7.4", "software")

    # -- 4. Frozen public-safe configuration -------------------------------
    for f, why in (
        ("configs/successor-qualification.yaml",
         "Frozen QA-OFF qualification experiment configuration (17 tasks, 3 "
         "prospectively derived seeds, treatments=[off], retry limit 0)"),
        ("configs/successor-models.yaml",
         "Frozen provider configuration for the two arms; credentials are "
         "referenced by environment-variable NAME only and no secret is stored"),
        ("configs/ablations.yaml", "Ablation definitions digested by the run manifest"),
        ("configs/experiment.yaml", "Baseline experiment configuration"),
        ("configs/models.yaml", "Default provider slots (network provider disabled)"),
        ("configs/pilot.yaml", "Pilot configuration referenced by pyproject data-files"),
        ("configs/pilot-models.yaml", "Pilot provider slots referenced by pyproject data-files"),
    ):
        add(f, "code/" + f, why, "Sections 6.2-6.3, 7.2", "software")

    # -- 5. Successor QA-OFF qualification evidence ------------------------
    add(f"{QUAL}/successor-run-manifest.json", "qualification/successor-run-manifest.json",
        "Run manifest: schedule, provenance counters, invalidated cells, "
        "terminal status SCHEDULE_COMPLETE_VERDICT_HOLD",
        "Sections 7.2, 7.3, 7.5", "result")
    add(f"{QUAL}/successor-analysis.json", "qualification/successor-analysis.json",
        "Frozen analyzer's analysis artifact: verdict HOLD, 7/17 qualified roles",
        "Sections 7.3, 7.4, 7.7", "result")
    add(f"{QUAL}/successor-partial-manifest.json", "qualification/successor-partial-manifest.json",
        "Per-cell partial manifest written during execution",
        "Section 7.2", "result")
    add(f"{QUAL}/successor-runs.jsonl", "qualification/successor-runs.jsonl",
        "Classification ledger: exactly one terminal row per scheduled cell (102)",
        "Sections 7.2, 7.5, 7.6", "result")
    add_tree(f"{QUAL}/raw/cells", "qualification/raw/cells",
             "Per-cell raw evidence: run manifest, append-only evidence trace, "
             "and row export for each of the 102 cells",
             "Sections 7.2, 7.5, 7.6", "result")
    add_tree(PREFLIGHT, "qualification/runtime-preflight",
             "Runtime preflight evidence: canonical runtime identity of both "
             "provider arms, captured before any qualification cell ran",
             "Section 7.2", "result")

    # -- 6. Dated governance records ---------------------------------------
    gov = [
        ("docs/post_phaseP_successor_provider_and_qualification_protocol_authorization.md",
         "Prospective authorization freezing the two provider arms, the protocol, and the seed derivation"),
        ("docs/post_phaseP_successor_runtime_preflight_contact_authorization.md",
         "Dated authorization for the runtime preflight contact"),
        ("docs/post_phaseP_successor_runtime_preflight_contact_authorization.json",
         "Machine-readable runtime-preflight authorization record"),
        ("docs/post_phaseP_successor_qualification_execution_authorization.md",
         "Dated authorization permitting the qualification to execute exactly once"),
        ("docs/post_phaseP_successor_qualification_execution_authorization.json",
         "Machine-readable execution authorization record"),
        ("docs/post_phaseP_successor_qualification_hold_forensic_diagnosis.md",
         "Dated record stating the HOLD verdict, the three invalidated cells, and "
         "why confirmatory execution was not entered"),
        ("docs/post_phaseP_successor_qualification_hold_forensic_diagnosis.json",
         "Machine-readable HOLD diagnosis record"),
        ("docs/post_phaseP_successor_qualification_analysis_correction.md",
         "Dated record of the one additive reclassification, which left the verdict unchanged"),
        ("docs/post_phaseP_successor_qualification_analysis_correction.json",
         "Machine-readable additive reclassification record"),
        ("docs/post_phaseP_successor_qualification_hash_basis_amendment.md",
         "Dated hash-basis amendment governing the digest binding"),
        ("docs/post_phaseP_successor_qualification_hash_basis_amendment.json",
         "Machine-readable hash-basis amendment"),
        ("docs/successor_real_model_qualification_plan.md",
         "The prospectively frozen qualification plan executed exactly once"),
        ("docs/successor_frozen_execution_inputs.json",
         "Frozen execution inputs and their digests"),
        ("docs/successor_prospective_seed_derivation.json",
         "Full prospective derivation of the three seeds from a base commit "
         "predating every successor result"),
        ("docs/successor_pr10_offline_eligibility_argument.json",
         "Offline provider-eligibility argument (PR-10)"),
    ]
    for src, why in gov:
        add(src, "governance/" + Path(src).name, why, "Sections 7.2, 7.3, 7.7", "result")

    # -- 7. Analysis / audit scripts ---------------------------------------
    add("paper/fse2027/tools/artifact-src/verify_released_counts.py",
        "analysis/verify_released_counts.py",
        "Recomputes every released count in Table 2 and Sections 7.2-7.6 from "
        "the released evidence alone; reports mismatches, changes nothing",
        "Sections 7.2-7.6", "software")
    add("paper/fse2027/tools/artifact-src/verify_manifest.py",
        "analysis/verify_manifest.py",
        "Verifies every SHA-256 in MANIFEST.sha256 against the shipped files",
        "Package integrity", "software")
    add("scripts/successor_scoring_vocabulary.py", "analysis/successor_scoring_vocabulary.py",
        "Frozen scoring vocabulary defining the exposure, near-miss and "
        "non-exposure classes used by Sections 7.5-7.6",
        "Sections 7.5, 7.6", "software")

    # -- 8. Figure-generation scripts --------------------------------------
    add("scripts/render_fse_route_a_figure3.py", "figures/render_figure_treatment_families.py",
        "Generates the treatment-families figure (Figure 2 in the paper) from "
        "declared constants; reads no result file",
        "Section 6.2", "software")
    add("paper/fse2027/figures/sanitize_figures.py", "figures/sanitize_figures.py",
        "Flattens, trims and strips PNG metadata from the manuscript figures",
        "Figures", "software")

    # -- 9. Supplementary material S1-S4 -----------------------------------
    for f, why in (
        ("S1-successor-qualification-provenance.md",
         "S1 - frozen candidate/benchmark identity, seeds, arm order, cell "
         "arithmetic, provenance counters, additive reclassification"),
        ("S2-prospective-confirmatory-analysis-plan.md",
         "S2 - the prospectively specified confirmatory analysis plan, NOT EXECUTED"),
        ("S3-rq1-property-to-test-map.md",
         "S3 - current claim-bound mechanism map and its explicit nonclaims"),
        ("S4-extended-reproducibility.md",
         "S4 - artifact chain layout, digest binding, exact validation commands"),
        ("README.md", "Supplement index and scientific-state table"),
    ):
        add(f"paper/fse2027/supplement/{f}", f"supplement/{f}", why, "Sections 7.1, 7.2, 11",
            "result" if f.endswith(".json") else "software")


# ---------------------------------------------------------------------------


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_forbidden_paths_absent(rel: str) -> None:
    norm = rel.replace(BS, "/")
    for bad in FORBIDDEN:
        if norm == bad or norm.startswith(bad + "/") or f"/{bad}/" in f"/{norm}/":
            raise SystemExit(f"REFUSED: copy set names a forbidden path: {rel}")


def redact(text: str) -> tuple[str, int]:
    """Rewrite absolute local paths to ``<ARTIFACT_ROOT>/``. Returns (text, n)."""
    n = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal n
        n += 1
        return "<ARTIFACT_ROOT>/"

    out = ABS_PATH.sub(sub, text)
    if n:
        # Normalise the separators in the tail of a rewritten path only.
        def tail(m: re.Match[str]) -> str:
            return "<ARTIFACT_ROOT>/" + m.group(1).replace(BS + BS, "/").replace(BS, "/")
        out = re.sub(r"<ARTIFACT_ROOT>/([^\"]*)", tail, out)
    return out, n


def copy_one(src: Path, dst: Path, redactions: list[dict[str, object]]) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    raw = src.read_bytes()
    if src.suffix in (".json", ".jsonl", ".yaml", ".md", ".csv", ".txt"):
        text = raw.decode("utf-8")
        new, n = redact(text)
        if n:
            before = hashlib.sha256(raw).hexdigest()
            data = new.encode("utf-8")
            dst.write_bytes(data)
            redactions.append({
                "package_path": str(dst.relative_to(PKG)).replace(BS, "/"),
                "rewrites": n,
                "sha256_before_redaction": before,
                "sha256_after_redaction": hashlib.sha256(data).hexdigest(),
            })
            return
    dst.write_bytes(raw)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PKG)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--no-archive", action="store_true")
    return parser.parse_args()


def main() -> int:
    global PKG, ARCHIVE
    args = parse_args()
    PKG = args.output.resolve()
    ARCHIVE = args.archive.resolve()
    root = ROOT.resolve()
    if PKG == root or root.is_relative_to(PKG):
        raise SystemExit(f"REFUSED: unsafe package output target: {PKG}")
    build_copy_set()

    for src, *_ in FILES:
        assert_forbidden_paths_absent(src)
    for src, *_ in TREES:
        assert_forbidden_paths_absent(src)

    if PKG.exists():
        shutil.rmtree(PKG)
    PKG.mkdir(parents=True)

    redactions: list[dict[str, object]] = []
    entries: list[dict[str, str]] = []

    def record(dst: Path, role: str, section: str, kind: str) -> None:
        entries.append({
            "path": str(dst.relative_to(PKG)).replace(BS, "/"),
            "sha256": sha256_file(dst),
            "bytes": str(dst.stat().st_size),
            "role": role,
            "paper_section": section,
            "artifact_class": kind,
        })

    for src, dst_rel, role, section, kind in FILES:
        s = ROOT / src
        if not s.exists():
            raise SystemExit(f"MISSING SOURCE: {src}")
        d = PKG / dst_rel
        copy_one(s, d, redactions)
        record(d, role, section, kind)

    for src, dst_rel, role, section, kind, suffixes in TREES:
        base = ROOT / src
        if not base.is_dir():
            raise SystemExit(f"MISSING SOURCE TREE: {src}")
        for p in sorted(base.rglob("*")):
            if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
                continue
            if not p.is_file():
                continue
            if suffixes and p.suffix not in suffixes:
                continue
            rel = p.relative_to(base)
            d = PKG / dst_rel / rel
            copy_one(p, d, redactions)
            record(d, role, section, kind)

    # Redacted source paths change the digests named by generated metadata.
    # Re-derive only software evidence inside the package so the shipped
    # verifier is self-consistent; retained scientific/result files are never
    # regenerated, rescored, or reclassified.
    derived = subprocess.run(
        [sys.executable, "-B", "scripts/submission_artifact.py", "generate"],
        cwd=PKG / "code",
        check=False,
        capture_output=True,
        text=True,
    )
    if derived.returncode:
        raise SystemExit(
            "PACKAGE EVIDENCE GENERATION FAILED:\n"
            + derived.stdout
            + derived.stderr
        )

    (PKG / "redaction-report.json").write_text(json.dumps({
        "record_kind": "anonymous_package_redaction_report",
        "rule": "Absolute local filesystem paths rewritten to <ARTIFACT_ROOT>/ "
                "with separators normalised to '/'. Package-local generated "
                "software evidence was then re-derived from those redacted copies.",
        "why_lossless": "Every rewritten field has a sibling repository-relative "
                        "path carrying the same file identity, and every *_sha256 "
                        "digest is over file CONTENTS, never over a path string. "
                        "No artifact carries a self-digest over its own file bytes, "
                        "so no digest binding is invalidated.",
        "files_redacted": len(redactions),
        "total_rewrites": sum(int(r["rewrites"]) for r in redactions),
        "files": redactions,
        "software_files_rederived_after_redaction": [
            "code/artifact/study_metadata.json",
            "code/artifact/traces/privacy_exfiltration.json",
            "code/artifact/generated/study_status.md",
            "code/artifact/generated/study_status.tex",
            "code/artifact/generated/claim_evidence_table.md",
            "code/artifact/generated/claim_evidence_table.tex",
            "code/artifact/generated/end_to_end_trace.md",
            "code/artifact/generated/end_to_end_trace.tex"
        ],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    generated = "deterministic-content-derived-export"
    result = finish(entries, generated)
    if result == 0:
        verify_anonymous_export()
    if result == 0 and not args.no_archive:
        write_archive()
    return result


def verify_anonymous_export() -> None:
    """Fail if the generated package contains a known identity leak."""
    patterns = {
        "author/repository identifier": re.compile(
            "Lei" + r"-?TzuY|" + "Lei" + "-TzuY/iqa-soa", re.I
        ),
        "public repository URL": re.compile(
            r"github(?:usercontent)?\.com/[^\s\"')]*iqa-soa", re.I
        ),
        "Windows home path": re.compile(
            r"[A-Za-z]:[/\\]Users[/\\][^/\\\s\"']+", re.I
        ),
        "POSIX home path": re.compile(r"/(?:home|Users)/[^/\s\"']+", re.I),
        "known author email": re.compile(
            "byi" + r"lyi2|(?:bill|tzuyi)[._-]?lei[^\s@]*@", re.I
        ),
    }
    forbidden_names = {".git", ".github", ".DS_Store", "Thumbs.db", "__pycache__"}
    failures: list[str] = []
    for path in PKG.rglob("*"):
        if path.name in forbidden_names or path.suffix in {".pyc", ".pyo"}:
            failures.append(f"forbidden generated metadata: {path.relative_to(PKG)}")
        if not path.is_file():
            continue
        text = path.read_bytes().decode("latin-1", errors="ignore")
        for name, pattern in patterns.items():
            match = pattern.search(text)
            if match:
                failures.append(
                    f"{path.relative_to(PKG).as_posix()}: {name}: {match.group(0)!r}"
                )
    if failures:
        raise SystemExit("ANONYMITY FAILURE:\n  " + "\n  ".join(failures))
    print("ANONYMOUS EXPORT VERIFIED")


def write_archive() -> None:
    """Write the uploadable ZIP with platform-independent member names."""
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    temporary = ARCHIVE.with_suffix(".zip.tmp")
    if temporary.exists():
        temporary.unlink()

    file_count = 0
    with zipfile.ZipFile(
        temporary,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(PKG.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(PKG)
            arcname = relative_path.as_posix()
            assert_forbidden_paths_absent(arcname)
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
            file_count += 1

    temporary.replace(ARCHIVE)
    print(f"archive: {ARCHIVE}")
    print(f"archive files: {file_count}")


def finish(entries: list[dict[str, str]], generated: str) -> int:
    """Write README, setup, RQ1 instructions, and both manifests."""
    from artifact_package_text import write_documents  # type: ignore

    write_documents(PKG, generated)

    # Re-hash after the documents exist, so they appear in the manifests too.
    docs = ["README.md", "SETUP.md", "RQ1-VALIDATION.md", "PROVENANCE.md",
            "redaction-report.json"]
    doc_meta = {
        "README.md": ("Package overview, contents, scope, and what is NOT here",
                      "Sections 11, Data Availability", "software"),
        "SETUP.md": ("Environment and setup instructions", "Section 11", "software"),
        "RQ1-VALIDATION.md": ("Deterministic RQ1 validation instructions and the "
                              "claim-to-test map in tabular form",
                              "Section 7.1", "software"),
        "PROVENANCE.md": ("Provenance manifest: what each artifact is, which paper "
                          "claim it supports, and how it was produced",
                          "Sections 7, 11", "software"),
        "redaction-report.json": ("Every absolute-path rewrite, with the file's "
                                  "SHA-256 before and after",
                                  "Package integrity", "software"),
    }
    for name in docs:
        p = PKG / name
        role, section, kind = doc_meta[name]
        entries.append({
            "path": name,
            "sha256": sha256_file(p),
            "bytes": str(p.stat().st_size),
            "role": role,
            "paper_section": section,
            "artifact_class": kind,
        })

    # Some generated software files are intentionally re-derived after path
    # redaction. Hash the final package bytes, never the earlier copy.
    for entry in entries:
        path = PKG / entry["path"]
        entry["sha256"] = sha256_file(path)
        entry["bytes"] = str(path.stat().st_size)
    entries.sort(key=lambda e: e["path"])

    lines = [f"{e['sha256']}  {e['path']}" for e in entries]
    (PKG / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    counts = {"result": 0, "software": 0}
    for e in entries:
        counts[e["artifact_class"]] += 1

    study = json.loads((ROOT / "artifact/study_metadata.json").read_text("utf-8"))
    claim_map = json.loads((ROOT / "artifact/claim_evidence_manifest.json").read_text("utf-8"))
    q = study["qualification"]
    mechanism_test_ids = {
        test_id
        for claim in claim_map["claims"]
        if claim["claim_type"] == "mechanism"
        for test_id in claim["test_ids"]
    }
    (PKG / "manifest.json").write_text(json.dumps({
        "record_kind": "fse2027_anonymous_replication_package_manifest",
        "schema_version": 1,
        "generated": generated,
        "anonymous": True,
        "contains_git_history": False,
        "contains_author_identifiers": False,
        "contains_absolute_local_paths": False,
        "contains_credentials": False,
        "scientific_state": {
            "qualification_verdict": q["verdict"],
            "scheduled_cells": q["scheduled_cells"],
            "observed_cells": q["terminal_rows"],
            "retries": q["retries"],
            "invalidated_cells": q["invalidated_cells"],
            "qualified_task_roles": f"{q['qualified_tasks']} / {q['total_frozen_tasks']}",
            "unqualified_task_roles": f"{q['unqualified_tasks']} / {q['total_frozen_tasks']}",
            "confirmatory_eligible": q["confirmatory_eligible"],
            "confirmatory_execution_entered": q["confirmatory_execution_performed"],
            "qa_full_vs_qa_off_treatment_effect": "NOT ESTABLISHED",
            "claim_bound_mechanism_test_ids": len(mechanism_test_ids),
        },
        "file_count": len(entries),
        "artifact_class_counts": counts,
        "files": entries,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"package: {PKG}")
    print(f"files:   {len(entries)}  "
          f"(result artifacts {counts['result']}, software artifacts {counts['software']})")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
