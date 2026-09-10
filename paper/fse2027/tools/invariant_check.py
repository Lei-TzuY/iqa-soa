#!/usr/bin/env python3
r"""Assert that the page-budget trimming changed no scientific content.

Runs against the COMPILED PDF, not the source, so it checks what a reviewer
would actually read. Every item below is either a binding scientific fact from
the frozen state, or a piece of core material the submission pass was required
to preserve.

    python tools/invariant_check.py [build/main.pdf]

Exit status 0 if every invariant holds, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[3]
STUDY = json.loads(
    (ROOT / "artifact" / "study_metadata.json").read_text(encoding="utf-8")
)
Q = STUDY["qualification"]

# (label, regex) - matched against the PDF's text with whitespace normalised.
INVARIANTS = [
    # --- binding scientific state ------------------------------------------
    ("qualification verdict HOLD",            r"verdict is HOLD|ended HOLD|verdict\s+HOLD"),
    ("scheduled cells",                       rf"{Q['scheduled_cells']} scheduled cells"),
    # A float (the RQ1 table) is placed inside this sentence, so ~2.6k
    # characters of table text separate the two halves in extraction order.
    ("recorded terminal observations",        rf"All {Q['terminal_rows']} reached recorded.{{0,3200}}?terminal observations"),
    ("zero retries",                          rf"Retries\s+{Q['retries']}|retry limit was zero|zero retries"),
    ("invalidated cells",                     rf"Invalidated cells\s+{Q['invalidated_cells']}|[Tt]hree cells were invalidated|three of {Q['scheduled_cells']} cells were invalidated"),
    ("qualified task count",                  rf"Qualified / unqualified tasks\s+{Q['qualified_tasks']} / {Q['unqualified_tasks']}|[Ss]even of the seventeen"),
    ("unqualified task count",                rf"Unqualified tasks\s+{Q['unqualified_tasks']} / {Q['total_frozen_tasks']}|ten of seventeen task roles failed|Qualified / unqualified tasks\s+{Q['qualified_tasks']} / {Q['unqualified_tasks']}"),
    ("terminal status",                       r"SCHEDULE_COMPLETE_VERDICT_HOLD"),
    ("confirmatory eligibility no",           r"Confirmatory eligible\s+No|confirmatory eligibility was\s+no"),
    ("confirmatory execution not entered",    r"confirmatory execution was not entered"),
    ("no QA treatment effect established",    r"no QA FULL versus QA OFF effect is\s+estimated|supports no treatment-effect claim|carries a single treatment"),
    ("does not claim IQA-SOA is safer",       r"do not claim, evidence that IQA-SOA makes LLM agents safer|not claim, anywhere, is that IQA-SOA improves the safety"),

    # --- generated claim/boundary and trace evidence -----------------------
    ("Claim-Evidence-Boundary table",          r"Claim.Evidence.Boundary summary"),
    ("mechanism claim row",                    r"C-MED\..{0,80}?mechanism"),
    ("governance claim row",                   r"C-QUAL\..{0,80}?governance"),
    ("effectiveness nonclaim row",             r"C-EFFECT\..{0,80}?effectiveness"),
    ("end-to-end trace identity",              r"TRACE-PRIV-001"),
    ("trace dispatch prevention",              r"QA FULL.{0,500}?BLOCK \(privacy\).{0,500}?Did not occur"),
    ("QA Policy IR",                           r"QA Policy IR"),
    ("instrumented mediation boundary",        r"complete mediation at the instrumented tool/service execution boundary"),

    # --- three-way distinction ---------------------------------------------
    ("runtime authority",                     r"Runtime authority"),
    ("measurement validity",                  r"Measure-?\s*ment\s+validity"),
    ("effectiveness inference",               r"Effectiveness inference"),

    # --- four research questions -------------------------------------------
    ("RQ1", r"RQ1"), ("RQ2", r"RQ2"), ("RQ3", r"RQ3"), ("RQ4", r"RQ4"),

    # --- invalidated-cell classes and interpretation ------------------------
    ("PROVIDER_INFRA_FAILURE",                r"PROVIDER_INFRA_FAILURE"),
    ("MODEL_PROTOCOL_INVALID",                r"MODEL_PROTOCOL_INVALID"),
    ("neither class is a safety exposure",    r"neither is a safety exposure"),
    ("no model/provider ranking",             r"neither is evidence that one provider\s*or model is globally safer or better"),

    # --- named task roles ---------------------------------------------------
    ("qualified challenge tasks named",       r"KP-004, UA-005, PRIV-007, PRIV-012, PRIV-016"),
    ("UA-004 negative control",               r"UA-004 held as a deliberate negative control"),
    ("FAULT-004 fault modality",              r"FAULT-004 established its intended\s+fault modality"),
    ("BEN-002 / BEN-003 matrix validity",     r"BEN-002 and BEN-003 are unqualified on matrix\s+validity"),
    ("eight zero-exposure tasks named",       r"PI-015, PI-018,\s*PI-019, PI-020, PRIV-017, BUD-016, BUD-017, BUD-018"),

    # --- diagnostics as non-exposure ---------------------------------------
    ("PI-018 diagnostics",                    r"PI-018 recorded three"),
    ("RISKY_INSTRUCTION_PROPAGATED",          r"RISKY_INSTRUCTION_PROPAGATED"),
    ("UNSUPPORTED_COMPLETION_CLAIM",          r"UNSUPPORTED_COMPLETION_CLAIM"),
    ("PRIV-017 diagnostics",                  r"PRIV-017 recorded eleven"),
    ("NONCANONICAL_RESOURCE_SELECTION",       r"NONCANONICAL_RESOURCE_SELECTION"),
    ("defined as non-exposure classes",       r"defined before execution as non-?exposure classes"),
    ("BUD-016 / BUD-018 exposure zero",       r"exposure counts for BUD-016 and BUD-018 remain\s+zero"),

    # --- core sections ------------------------------------------------------
    ("Threats to Validity section",           r"THREATS TO VALIDITY"),
    ("construct validity",                    r"Construct validity"),
    ("internal validity",                     r"Internal validity"),
    ("benchmark validity",                    r"Benchmark validity"),
    ("external validity",                     r"External validity"),
    ("statistical conclusion validity",       r"Statistical conclusion validity"),
    ("researcher degrees of freedom",         r"Researcher degrees of freedom"),
    ("observed measurement limitations",      r"Observed measurement and protocol limitations"),
    ("Data Availability section",             r"Data Availability"),
    ("Related Work positioning table",        r"Positioning against the closest enforcement systems"),
    ("novelty concession",                    r"not that runtime mediation of agent actions is new"),
    ("Phase-P HOLD / UNQUALIFIED",            r"HOLD / UNQUALIFIED"),
]

FORBIDDEN = [
    ("author name (Lei-TzuY)",       r"Lei-?TzuY"),
    ("author name (Bill Lei)",       r"Bill\s+Lei"),
    ("author name (Tzu-Yi Lei)",     r"Tzu-?Yi\s+Lei"),
    ("public repository path",       r"github\.com|[A-Za-z0-9_-]+/iqa-soa|Quality_Assurance"),
    ("author email",                 r"byilyi2|gmail\.com"),
    ("windows filesystem path",      r"C:\\\\|C:/Users"),
    ("draft version footer",         r"Working Draft|Draft v0\.|Route-A submission path"),
    ("a QA effect estimate",         r"treatment effect of\s+\d|effect size of|p\s*=\s*0\.\d"),
]


def main(pdf_path: str = "build/main.pdf") -> int:
    doc = pymupdf.open(pdf_path)
    raw = "\n".join(p.get_text() for p in doc)

    # Normalise what the typesetter did to the words, so that a match failure
    # means missing CONTENT and not merely a line break inside a phrase.
    raw = re.sub(r"(?m)^\s*\d{1,4}\s*$", " ", raw)        # review line numbers
    raw = re.sub(r"Who Controls the Agent\?", " ", raw)   # running heads
    raw = re.sub(r"Conference.{0,4}27, 2027, Venue withheld for review", " ", raw)
    raw = re.sub(r"(?m)^\s*Anon\.\s*$", " ", raw)
    flat = re.sub(r"\s+", " ", raw)
    flat = re.sub(r"(\w)_ (\w)", r"\1_\2", flat)          # broken identifiers

    # A line break at a hyphen is ambiguous: "Measure- ment" must rejoin without
    # the hyphen, but "BEN- 003" must rejoin WITH it. Build both readings and
    # accept a match in either, so the check tests content, not typesetting.
    joined = re.sub(r"(\w)- (\w)", r"\1\2", flat)         # drop the hyphen
    kept = re.sub(r"(\w)- (\w)", r"\1-\2", flat)          # keep the hyphen
    text = joined + "\n<<<ALT>>>\n" + kept

    failures: list[str] = []

    print("PRESERVED SCIENTIFIC CONTENT")
    print("-" * 62)
    for label, pattern in INVARIANTS:
        ok = re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None
        print(f"  [{'OK ' if ok else 'MISSING'}] {label}")
        if not ok:
            failures.append(f"missing: {label}")

    print("\nFORBIDDEN CONTENT (anonymity + fabricated results)")
    print("-" * 62)
    for label, pattern in FORBIDDEN:
        hit = re.search(pattern, text, re.IGNORECASE)
        print(f"  [{'FOUND  ' if hit else 'CLEAN'}] {label}")
        if hit:
            failures.append(f"forbidden: {label} -> {hit.group(0)!r}")

    print("\n" + "=" * 62)
    if failures:
        print(f"INVARIANT_CHECK: FAIL ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("INVARIANT_CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "build/main.pdf"))
