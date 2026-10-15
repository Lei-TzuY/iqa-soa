"""Audit manuscript diagnostic denominators using unchanged E-H saved evidence.

No oracle evaluation, historical action replay, owner decision or new semantic
label is performed. Completion ranges are post-hoc arithmetic over the existing
H unknowns, not confidence intervals or new confirmatory tests.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import itertools
import json
import pathlib
import time
from collections import Counter, defaultdict
from fractions import Fraction


BINDINGS = {
    "cycle_g_20261010/original_record_metadata.json.gz": "67700d4a783831cf277374085bfeda8ba591e8b1624a8acec3dfe2837c84132f",
    "cycle_h_20261010/record_semantic_coverage.csv.gz": "8a02769283675624444f65cbee52343650b6a69afdd7f442d779b10df81c6454",
    "cycle_h_20261010/statistical_consequences.json": "61d4f142a94603fbca247d4be068ee7c01455dd10f8e9a7f147c9e2a8082be27",
    "cycle_h_20261010/human_review_packet.json": "7e078a643fd05675c4d8e5e99aec7c5e10c3728e435b6ac9d5ca85573c0e7db4",
    "cycle_h_20261010/review_decisions_template.csv": "3dc1e796b6761dfdc6e0032b6b0ed573dfad6724d4be6622b25a76f13c9af7cb",
    "cycle_h_20261010/frozen_rules_v2.json": "ec3b81b709c7a4c81203720dbbaa9619f3d49b9cd785d471074885f689667f97",
}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def number(value):
    return {"fraction": str(value), "value": float(value)}


def parse_outcome(value):
    if value == "True":
        return True
    if value == "False":
        return False
    require(value == "AMBIGUOUS", "unsupported saved semantic outcome")
    return None


def completion_counts(contexts):
    """Attainable (proposed-and-not-executed, proposed) integer counts.

    Unknown labels may vary independently; no new common goal-wide rule is
    presumed. The resulting set can be broader than future coherent rules.
    """
    states = {(0, 0)}
    for proposed, executed in contexts:
        ps = (False, True) if proposed is None else (proposed,)
        es = (False, True) if executed is None else (executed,)
        increments = {(int(p and not e), int(p)) for p, e in itertools.product(ps, es)}
        states = {(n + dn, d + dd) for n, d in states for dn, dd in increments}
    return states


def completion_rates(contexts):
    require(contexts, "empty diagnostic population")
    pmin = sum(p is True for p, _ in contexts)
    pmax = sum(p is not False for p, _ in contexts)
    states = completion_counts(contexts)
    ratios = [Fraction(n, d) for n, d in states if d]
    return {"proposal_rate": {"lower": number(Fraction(pmin, len(contexts))),
                               "upper": number(Fraction(pmax, len(contexts)))},
            "proposal_nonexecution_fraction": {"lower": number(min(ratios)) if ratios else None,
                                                "upper": number(max(ratios)) if ratios else None},
            "attainable_count_states": len(states), "zero_denominator_possible": any(d == 0 for _, d in states)}


def frozen_eligibility(records):
    models = sorted({r["model"] for r in records})
    return {m: {r["suite"] + "/" + r["injection_task"] for r in records
                if r["stage"] == "qualification" and r["model"] == m and r["kind"] == "security"
                and r["canonical_population"] and r["cpe_executed"] is True} for m in models}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=pathlib.Path, default=pathlib.Path(__file__).parent)
    parser.add_argument("--source-extract", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "a fresh output directory is required")
    tick = time.perf_counter()
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    source_files = {args.evidence_root / name: expected for name, expected in BINDINGS.items()}
    for path, expected in source_files.items():
        require(sha(path) == expected, "evidence hash differs: " + str(path))
    before = {str(p): sha(p) for p in source_files}
    before[str(args.source_extract)] = sha(args.source_extract)
    metadata = load(args.evidence_root / "cycle_g_20261010/original_record_metadata.json.gz")["records"]
    coverage = list(csv.DictReader(gzip.open(args.evidence_root / "cycle_h_20261010/record_semantic_coverage.csv.gz", "rt")))
    by_endpoint = {(r["stage"], int(r["position"]), r["endpoint"]): r for r in coverage}
    require(len(by_endpoint) == len(coverage) == 1794, "duplicate or missing saved contexts")
    require(len(metadata) == 1492, "saved metadata count differs")
    require(not any("V3" in r["origin"] for r in coverage), "invalid G V3 provenance entered")
    unknown = [r for r in coverage if parse_outcome(r["semantic_outcome"]) is None]
    packet = load(args.evidence_root / "cycle_h_20261010/human_review_packet.json")
    responses = list(csv.DictReader((args.evidence_root / "cycle_h_20261010/review_decisions_template.csv").open()))
    require(packet["authorized_human_decisions"] == 0 and all(r["decision"] == r["rationale"] == r["reviewer_id"] == "" for r in responses),
            "new reviewer decision requires a separately authorized workflow")
    require(len(unknown) == len(packet["observation_cards"]) == 71 and len(responses) == 76, "pending population differs")
    require(Counter(r["endpoint"] for r in unknown) == {"executed": 33, "proposed": 38}, "pending endpoint count differs")
    unknown_records = {(r["stage"], r["position"]) for r in unknown}
    require(len(unknown_records) == 38, "pending record count differs")
    eligible = frozen_eligibility(metadata)
    original = load(args.source_extract)
    require(eligible == {m: set(gs) for m, gs in original["original_eligible_goals"].items()}, "frozen eligibility differs")
    require(all(len(gs) == 21 for gs in eligible.values()), "original 21/21 eligibility differs")
    pairs = defaultdict(dict)
    for r in metadata:
        if r["stage"] == "confirmatory":
            key = r["model"], r["pair_id"]
            require(r["arm"] not in pairs[key], "duplicate pair arm")
            pairs[key][r["arm"]] = r
    require(len(pairs) == 474 and all(set(p) == {"off", "full"} for p in pairs.values()), "original 474 pairs differ")
    require(sum(p["off"]["kind"] == "security" and p["off"]["canonical_population"]
                and p["off"]["suite"] + "/" + p["off"]["injection_task"] in eligible[m]
                for (m, _), p in pairs.items()) == 168, "original primary pairs differ")

    diagnostic = []; exclusions = []
    for model in sorted(eligible):
        canonical = [r for r in metadata if r["stage"] == "confirmatory" and r["model"] == model
                     and r["arm"] == "full" and r["kind"] == "security" and r["canonical_population"]]
        for population in ("ALL_CANONICAL", "FROZEN_ELIGIBLE"):
            records = canonical if population == "ALL_CANONICAL" else [r for r in canonical if r["suite"] + "/" + r["injection_task"] in eligible[model]]
            require(len(records) == (136 if population == "ALL_CANONICAL" else 84), "diagnostic denominator differs")
            goal_counts = Counter(r["suite"] + "/" + r["injection_task"] for r in records)
            require(set(goal_counts.values()) == {4}, "goal/carrier nesting differs")
            props = [r for r in records if r["cpe_proposed"] is True]
            gaps = [r for r in props if r["cpe_executed"] is False]
            contexts = [(parse_outcome(by_endpoint["confirmatory", r["position"], "proposed"]["semantic_outcome"]),
                         parse_outcome(by_endpoint["confirmatory", r["position"], "executed"]["semantic_outcome"])) for r in records]
            source_ratio = Fraction(len(gaps), len(props))
            if population == "ALL_CANONICAL":
                require(abs(float(source_ratio) - original["descriptive"][model]["interception_rate_full"]) < 1e-15, "frozen diagnostic does not reproduce")
            else:
                require(abs(len(props) / len(records) - original["descriptive"][model]["full"]["cpe_proposed_eligible"]) < 1e-15, "eligible proposal rate does not reproduce")
            entry = {"model": model, "population": population, "goals": len(goal_counts), "records": len(records),
                     "source_proposed_true": len(props), "source_proposed_true_executed_false": len(gaps),
                     "source_proposal_rate": number(Fraction(len(props), len(records))),
                     "source_nonexecution_fraction": number(source_ratio),
                     "H_known_proposed_true": sum(p is True for p, _ in contexts),
                     "H_unknown_proposed": sum(p is None for p, _ in contexts),
                     "H_unknown_executed": sum(e is None for _, e in contexts),
                     "H_known_joint_counts": {str(k): v for k, v in Counter(contexts).items()},
                     "H_POST_HOC_completion_ranges": completion_rates(contexts)}
            diagnostic.append(entry)
        for r in canonical:
            if r["suite"] + "/" + r["injection_task"] not in eligible[model] and r["cpe_proposed"] is True:
                evidence = by_endpoint["confirmatory", r["position"], "proposed"]
                exclusions.append({"stage": r["stage"], "position": r["position"], "model": model, "arm": "full",
                                   "suite": r["suite"], "goal": r["injection_task"], "source_executed": r["cpe_executed"],
                                   "source_proposed": r["cpe_proposed"], "raw_pointer": evidence["raw_pointer"],
                                   "raw_sha256": evidence["raw_sha256"], "evidence_sha256": evidence["evidence_sha256"],
                                   "cause": "ALL_CANONICAL_DIAGNOSTIC_INCLUDES_NONELIGIBLE_GOAL"})
    require([r["position"] for r in exclusions] == [448], "excluded-proposal record differs")
    h_stats = load(args.evidence_root / "cycle_h_20261010/statistical_consequences.json")
    result = {"cycle": "I", "status": "HUMAN_ADJUDICATION_PENDING / unrestricted manuscript HOLD",
              "statistical_status": "POST_HOC_DESCRIPTIVE_MEASUREMENT_AUDIT",
              "started_utc": started, "runtime_seconds": time.perf_counter() - tick,
              "source_files": before, "code_sha256": sha(pathlib.Path(__file__)),
              "remaining": {"goals": 5, "records": 38, "contexts": 71, "executed": 33, "proposed": 38},
              "coverage_unchanged": {"goals": [30, 35], "executed": [877, 910], "proposed": [846, 884]},
              "owner_decisions": 0, "human_reviews": 0, "new_semantic_labels": 0, "affected_record_replays": 0,
              "primary_H_bounds_unchanged": h_stats["D_H_bounds"],
              "primary_proposed_H_bounds_unchanged": h_stats["independent_proposed_outcome_bounds"]["H"],
              "diagnostic": diagnostic, "denominator_exclusions": exclusions,
              "interpretation": "The frozen diagnostic is P(source proposed=True,source executed=False)/P(source proposed=True) over ALL canonical FULL observations; it does not inspect blocking events or isolate a causal interception mechanism. Independent H completion ranges use existing labels only. They allow unknown endpoint labels to vary independently, are conditional on known H constructs, and are not confidence intervals, original-population effect estimates, or new adjudications.",
              "original_sequence": "S2 still closes the original fixed-sequence gate; S3 remains descriptive."}
    require(before == {p: sha(pathlib.Path(p)) for p in before}, "audit changed an input")
    args.output.mkdir(parents=True)
    (args.output / "analysis_results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (args.output / "denominator_discrepancy.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(exclusions[0])); writer.writeheader(); writer.writerows(exclusions)
    print(json.dumps({"runtime_seconds": result["runtime_seconds"], "diagnostic": diagnostic,
                      "new_semantic_labels": 0, "affected_record_replays": 0}))


if __name__ == "__main__":
    main()
