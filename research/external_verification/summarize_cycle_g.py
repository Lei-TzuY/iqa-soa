"""Deterministic POST-HOC construct summaries; never overwrite frozen results.

Consumes hash-bound, content-minimized Cycle F/G outputs and original terminal
metadata. Unknown labels remain unknown. Bounds are binary-label completion
bounds for the frozen estimand, not confidence intervals or complete-case tests.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import pathlib
from collections import Counter, defaultdict
from fractions import Fraction

MODELS = ("qwen", "mistral")
OLD_GOALS = {"injection_task_0", "injection_task_1", "injection_task_3", "injection_task_6"}
RUBRIC = "394bba468fbff2cd5db53335bdba3e0ef4dfa3c03c30cbf54aea6920223af7d8"
B3_RUBRIC = "5ada9782e55f69b3f8954ce972bca5dce27c50d1a08d2b54551ec91a2b34bf8a"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path):
    body = path.read_bytes()
    if path.suffix == ".gz":
        body = gzip.decompress(body)
    return json.loads(body)


def read_lines(path):
    body = gzip.decompress(path.read_bytes())
    return [json.loads(line) for line in body.splitlines() if line]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(r):
    return r["stage"], r["position"]


def unit(r):
    return r["suite"] + "/" + (r.get("goal") or r["injection_task"])


def known(value):
    return isinstance(value, bool)


def number(x):
    return {"fraction": str(x), "estimate": float(x)}


def paired_metadata(rows):
    pairs = defaultdict(dict)
    for r in rows:
        if r["stage"] != "confirmatory":
            continue
        k = (r["model"], r["cell_id"])
        require(r["arm"] not in pairs[k], "duplicate paired arm")
        pairs[k][r["arm"]] = r
    for arms in pairs.values():
        require(set(arms) == {"off", "full"}, "missing paired arm")
        off, full = arms["off"], arms["full"]
        for field in ("seed", "kind", "suite", "user_task", "injection_task", "pair_id"):
            require(off[field] == full[field], "paired identity mismatch: " + field)
        require(off["pair_id"] is not None, "missing original pair_id")
    return dict(pairs)


def unit_differences(pairs, decisions, field, allowed=None, completion=None):
    grouped = {m: defaultdict(list) for m in MODELS}
    n_pairs, n_unknown_records = 0, 0
    endpoint = "proposed" if field == "cpe_proposed" else "executed"
    for (model, _), arms in pairs.items():
        off, full = arms["off"], arms["full"]
        if off["kind"] != "security":
            continue
        goal = unit(off)
        if field.startswith("cpe_") and not off["canonical_population"]:
            continue
        if allowed is not None and goal not in allowed[model]:
            continue
        ys = {}
        for arm, record in arms.items():
            value = decisions[key(record)][endpoint] if decisions is not None else record[field]
            if not known(value):
                n_unknown_records += 1
                require(completion in ("lower", "upper", "all_false", "all_true"), "unknown label needs explicit completion")
                value = completion == "all_true" or (completion == "lower" and arm == "off") or (completion == "upper" and arm == "full")
            ys[arm] = int(value)
        grouped[model][goal].append(Fraction(ys["full"] - ys["off"]))
        n_pairs += 1
    means = {m: {u: sum(v, Fraction()) / len(v) for u, v in sorted(g.items())} for m, g in grouped.items()}
    require(all(means[m] for m in MODELS), "a model stratum is empty")
    model_means = {m: sum(g.values(), Fraction()) / len(g) for m, g in means.items()}
    estimate = sum(model_means.values(), Fraction()) / len(MODELS)
    return {"estimate": number(estimate), "strata": {m: number(v) for m, v in model_means.items()},
            "n_pairs": n_pairs, "n_model_goal_units": sum(map(len, means.values())),
            "unknown_records_completed": n_unknown_records,
            "unit_differences": {m: {u: str(v) for u, v in g.items()} for m, g in means.items()}}


def bootstrap_envelope(lower, upper):
    # Same positive-weight goal resamples bound every fixed completion's CI.
    # This does not turn incomplete classification into confirmatory evidence.
    import numpy as np
    label = "fse2027-external-replication-v1|analysis|bootstrap|primary_cpe_executed"
    seed = int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    lo, hi = np.zeros(20_000), np.zeros(20_000)
    for m in MODELS:
        goals = list(lower["unit_differences"][m])
        require(goals == list(upper["unit_differences"][m]), "bound cluster lists differ")
        l = np.array([float(Fraction(lower["unit_differences"][m][g])) for g in goals])
        h = np.array([float(Fraction(upper["unit_differences"][m][g])) for g in goals])
        idx = rng.integers(0, len(goals), size=(20_000, len(goals)))
        lo += l[idx].mean(axis=1) / len(MODELS)
        hi += h[idx].mean(axis=1) / len(MODELS)
    return {"envelope": [float(np.percentile(lo, 2.5)), float(np.percentile(hi, 97.5))],
            "draws": 20_000, "seed": seed, "numpy": np.__version__,
            "meaning": "POST-HOC envelope of same-resample goal-cluster percentile CIs over binary unknown-label completions; not a CI for an identified full semantic estimand and not a fixed-sequence test."}


def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=pathlib.Path, default=pathlib.Path(__file__).parent / "cycle_g_20261010")
    args = parser.parse_args()
    root, old = args.audit_dir, args.audit_dir.parent / "cycle_f_20261010"
    bound = {"construct_records.jsonl.gz": "1b66fd89b8e96d8305f1af56b206024f460ae0b10ba2e288542c981b83ec57ab",
             "execution_summary.json": "3f86b10fcada5f57ac2afd757d201d64ca2e0db38739b0d15bac2cc3987b98f4",
             "original_record_metadata.json.gz": "67700d4a783831cf277374085bfeda8ba591e8b1624a8acec3dfe2837c84132f",
             "semantic_rubric_v2.json": RUBRIC,
             "semantic_rubric_v4_b3.json": B3_RUBRIC,
             "construct_records_b3_v4.jsonl.gz": "2a0626126477f56d7d3d60213ce48f619eed328c92e969eb02fc538930a3fe19",
             "execution_summary_b3_v4.json": "6d88ca7bf3e83608c04a67d5f4260039aa7c51b7f58218e5e92c8e37b481b7b8"}
    for name, expected in bound.items():
        require(sha(root / name) == expected, "bound input differs: " + name)
    inputs = list(root / n for n in bound) + [old / n for n in ("record_replay.jsonl.gz", "replay_summary.json", "record_discrepancies.csv", "oracle_sources.json")]
    before = {str(p): sha(p) for p in inputs}
    new_records = read_lines(root / "construct_records.jsonl.gz")
    v1 = {key(r): r for r in read_lines(root / "construct_records_v1.jsonl.gz")}
    prior = read_lines(old / "record_replay.jsonl.gz")
    require(hashlib.sha256(gzip.decompress((old / "record_replay.jsonl.gz").read_bytes())).hexdigest() == "68a099a6c876b517807a493ce2129ae5e721634053229b6e0e98949352bb16e8", "Cycle F input differs")
    historical_all = [r for r in prior if r["suite"] == "banking" and r["goal"] in OLD_GOALS]
    historical = [r for r in historical_all if r["goal"] != "injection_task_3"]
    b3_records = read_lines(root / "construct_records_b3_v4.jsonl.gz")
    require(len(new_records) == 806 and len(historical_all) == 104 and len(historical) == 78 and len(b3_records) == 26, "construct population differs")
    metadata = read_json(root / "original_record_metadata.json.gz")
    meta = {key(r): r for r in metadata["records"]}
    f_by_key = {key(r): r for r in prior}
    require(len(meta) == len(prior) == 1492, "terminal metadata population differs")
    for k, r in meta.items():
        f = f_by_key[k]
        for field in ("model", "arm", "suite", "kind", "user_task"):
            require(r[field] == f[field], "metadata/F identity mismatch")
        require(r["injection_task"] == f["goal"], "metadata goal mismatch")
        for field, value in f["recorded"].items():
            require(value == r[field], "metadata/F recorded-label mismatch")
    spec = read_json(root / "semantic_rubric_v2.json")
    goal_specs = {g["suite"] + "/" + g["goal_id"]: g for g in spec["goals"]}
    goal_specs["banking/injection_task_3"] = next(g for g in read_json(root / "semantic_rubric_v4_b3.json")["goals"] if g["suite"] == "banking" and g["goal_id"] == "injection_task_3")
    require(len(goal_specs) == 35, "35-goal catalogue differs")
    sources = read_json(old / "oracle_sources.json")["methods"]
    source = {(x["suite"], x["task"]): x for x in sources if x["kind"] == "injection" and x["method"] == "security"}
    with (old / "record_discrepancies.csv").open(encoding="utf-8") as f:
        old_diff = {(r["stage"], int(r["position"]), r["field"]): r for r in csv.DictReader(f)}
    decisions, details, discrepancies, ambiguities, revisions, b3_reconciliation = {}, [], [], [], [], []
    legacy_keys, b3_keys = {key(r) for r in historical}, {key(r) for r in b3_records}
    for r in historical + new_records + b3_records:
        k = key(r)
        legacy, b3 = k in legacy_keys, k in b3_keys
        require(k not in decisions, "duplicate construct record")
        m = meta[k]
        for field in ("model", "arm", "suite", "kind", "user_task"):
            require(r[field] == m[field], "construct metadata identity differs")
        require(r["goal"] == m["injection_task"] and r["raw_sha256"] == f_by_key[k]["raw_sha256"], "construct goal/hash differs")
        if legacy:
            values = {ep: r["semantic"][ep] for ep in ("executed", "proposed")}
            pointer = r["raw"]
            rubric_id, rubric_hash = "cycle-f-four-banking-goals-historical", sha(old / "goal_sources.json")
            info = {ep: {"outcome": values[ep], "reason": "preserved Cycle F literal content finding; not re-evaluated in G", "evidence": {"semantic_pointer": "cycle_f_20261010/record_replay.jsonl.gz:" + str(k)}} for ep in values}
            status = "EXECUTED" if r["executed_calls"] else "BLOCKED"
        else:
            require(r["rubric_sha256"] == (B3_RUBRIC if b3 else RUBRIC), "record rubric differs")
            values = {ep: x["primary"]["outcome"] for ep, x in r["semantic"].items()}
            info = {ep: x["primary"] for ep, x in r["semantic"].items()}
            pointer, rubric_id, rubric_hash, status = r["raw_pointer"], r["rubric_id"], r["rubric_sha256"], r["execution_status"]
            for ep, value in values.items():
                if b3:
                    b3_reconciliation.append({"stage": r["stage"], "position": r["position"], "model": r["model"], "arm": r["arm"], "goal": unit(r), "endpoint": ep, "preserved_cycle_f_content_outcome": f_by_key[k]["semantic"][ep], "v4_construct_outcome": value, "reason": info[ep]["reason"], "raw_pointer": pointer, "raw_sha256": r["raw_sha256"], "rubric_sha256": B3_RUBRIC})
                    continue
                previous = v1[k]["semantic"][ep]["primary"]["outcome"]
                if previous != value:
                    revisions.append({"stage": r["stage"], "position": r["position"], "model": r["model"], "arm": r["arm"], "goal": unit(r), "endpoint": ep, "v1_outcome": previous, "v2_outcome": value, "reason": info[ep]["reason"], "amendment": "semantic_amendment_v2.json", "raw_pointer": pointer, "raw_sha256": r["raw_sha256"]})
        decisions[k] = values
        base = {"stage": r["stage"], "position": r["position"], "model": r["model"], "arm": r["arm"], "suite": r["suite"], "goal": r["goal"], "user_task": r["user_task"], "kind": r["kind"], "benchmark_version": "v1.2.2", "origin": "HISTORICAL_CYCLE_F" if legacy else "CYCLE_G_B3_V4" if b3 else "CYCLE_G_V2", "rubric_id": rubric_id, "rubric_sha256": rubric_hash, "raw_pointer": pointer, "raw_sha256": r["raw_sha256"], "evidence_sha256": r["evidence_sha256"]}
        for ep, value in values.items():
            fields = ["cpe_proposed"] if ep == "proposed" else (["native_security", "cpe_executed"] if r["kind"] == "security" else ["native_utility"])
            fields = [field for field in fields if m[field] is not None]
            old_values = {field: m[field] for field in fields}
            row = {**base, "endpoint": ep, "semantic_outcome": value, "classifiable": known(value), "context_status": "PROPOSED" if ep == "proposed" else status,
                   "historical_outcomes": json.dumps(old_values, sort_keys=True), "decision_reason": info[ep]["reason"], "evidence": json.dumps(info[ep].get("evidence", {}), sort_keys=True, separators=(",", ":")), "scenarios": json.dumps(info[ep].get("scenarios", {}), sort_keys=True), "controlled_evidence_pointer": pointer + ("#/proposed_trace;#/messages" if ep == "proposed" else "#/executed_trace;#/messages;#/final_output_text")}
            details.append(row)
            if not known(value):
                ambiguities.append({**row, "category": "SEMANTIC_AMBIGUITY" if value == "AMBIGUOUS" else "INCOMPLETE_OR_OPAQUE_EVIDENCE", "adjudication_required": goal_specs[unit(r)]["adjudication_required"]})
            for field, original in old_values.items():
                if not known(value) or original == value:
                    continue
                previous = old_diff.get((r["stage"], r["position"], field))
                order = previous is not None and previous["category"] == "SCORER_ORDER_DEPENDENCY"
                category = "SCORING_ORDER_DEPENDENCY" if order else "SOURCE_ORACLE_FALSE_POSITIVE" if original else "SOURCE_ORACLE_FALSE_NEGATIVE"
                cause = "SCORING_ORDER_DEPENDENCY" if order else "OTHER_VERIFIED_CAUSE" if r["suite"] == "travel" and r["goal"] == "injection_task_4" else "WRONG_TARGET_OR_CONTENT"
                src = source[(r["suite"], r["goal"])]
                discrepancies.append({**base, "endpoint": field, "frozen_historical_outcome": original, "independent_semantic_outcome": value, "category": category, "cause": cause, "previously_in_cycle_f": previous is not None, "decision_reason": info[ep]["reason"], "evidence": row["evidence"], "oracle_source": src["file"] + ":" + str(src["line"]), "oracle_file_sha256": src["sha256"], "observation_pointer": row["controlled_evidence_pointer"]})
    require(len(decisions) == 910, "cumulative construct population differs")
    pairs = paired_metadata(metadata["records"])
    require(len(pairs) == 474, "474 original pairs differ")
    kinds = Counter(arms["off"]["kind"] for arms in pairs.values())
    require(kinds == {"security": 280, "benign": 194}, "pair-kind population differs")
    prior_summary = read_json(old / "replay_summary.json")
    eligibility = prior_summary["statistics"]["posthoc_four_banking_goals_only"]["frozen_eligibility"]
    require(all(len(eligibility[m]) == 21 for m in MODELS), "frozen eligibility differs")
    a = unit_differences(pairs, None, "cpe_executed", eligibility)
    require(a["estimate"]["fraction"] == "-85/168" and a["n_pairs"] == 168, "original rational primary differs")
    b_labels = {key(r): {"executed": r["cpe_executed"]} for r in metadata["records"] if r["kind"] == "security"}
    for r in historical_all:
        if r["kind"] == "security":
            b_labels[key(r)]["executed"] = r["semantic"]["executed"]
    b = unit_differences(pairs, b_labels, "cpe_executed", eligibility)
    require(b["estimate"]["fraction"] == "-1/2", "preserved Cycle F sensitivity differs")
    contrasts = {}
    for field, allowed in (("cpe_executed", eligibility), ("cpe_proposed", eligibility), ("native_security", None)):
        contrasts[field] = {mode: unit_differences(pairs, decisions, field, allowed, mode) for mode in ("lower", "upper", "all_false", "all_true")}
    contrasts["cpe_executed"]["bootstrap_envelope"] = bootstrap_envelope(contrasts["cpe_executed"]["lower"], contrasts["cpe_executed"]["upper"])
    eligibility_bounds = {m: {"certain": set(), "possible": set()} for m in MODELS}
    for k, m in meta.items():
        if m["stage"] == "qualification" and m["kind"] == "security" and m["canonical_population"]:
            value = decisions[k]["executed"]
            if value is True:
                eligibility_bounds[m["model"]]["certain"].add(unit(m))
            if value is not False:
                eligibility_bounds[m["model"]]["possible"].add(unit(m))
    changed_estimand = {}
    for mode in ("all_false", "all_true"):
        eligible = {m: sorted(eligibility_bounds[m]["certain" if mode == "all_false" else "possible"]) for m in MODELS}
        changed_estimand[mode] = {"eligibility": eligible, "analysis": unit_differences(pairs, decisions, "cpe_executed", eligible, mode), "status": "POST-HOC changed-eligibility/changed-estimand scenario; not principal result"}
    strata = defaultdict(list)
    for row in details:
        for dimension in ("goal", "suite", "model", "arm", "stage", "kind"):
            label = row["suite"] + "/" + row["goal"] if dimension == "goal" else row[dimension]
            strata[(dimension, label, row["endpoint"])].append(row)
        strata[("model_stage_arm", row["model"] + "/" + row["stage"] + "/" + row["arm"], row["endpoint"])].append(row)
        strata[("all", "35_goals", row["endpoint"])].append(row)
        strata[("origin", row["origin"], row["endpoint"])].append(row)
    coverage = []
    for (dimension, label, endpoint), rows in sorted(strata.items()):
        count = Counter(str(x["semantic_outcome"]) for x in rows)
        compared = {(x["stage"], x["position"]) for x in rows}
        endpoint_names = {"cpe_proposed"} if endpoint == "proposed" else {"native_security", "cpe_executed", "native_utility"}
        diffs = [d for d in discrepancies if (d["stage"], d["position"]) in compared and d["endpoint"] in endpoint_names]
        n_comparisons = sum(len(json.loads(x["historical_outcomes"])) for x in rows if x["classifiable"])
        n_historical = sum(len(json.loads(x["historical_outcomes"])) for x in rows)
        coverage.append({"dimension": dimension, "stratum": label, "endpoint": endpoint, "retained_records": len(rows), "classifiable_records": count["True"] + count["False"], "true": count["True"], "false": count["False"], "ambiguous": count["AMBIGUOUS"], "unobservable": count["UNOBSERVABLE"], "historical_endpoints": n_historical, "classifiable_historical_endpoints": n_comparisons, "endpoint_disagreements": len(diffs), "records_with_disagreement": len({(d["stage"], d["position"]) for d in diffs}), "disagreement_rate_classifiable_endpoints": len(diffs) / n_comparisons if n_comparisons else None})
    goals = []
    for goal, rubric in goal_specs.items():
        rows = [r for r in details if r["suite"] + "/" + r["goal"] == goal]
        ex, pr = ([x for x in rows if x["endpoint"] == endpoint] for endpoint in ("executed", "proposed"))
        require(len(ex) == 26, "per-goal retained denominator differs")
        goals.append({"goal": goal, "suite": rubric["suite"], "resolved_class": rubric["resolved_class"], "source_pointer": rubric["goal_source"] + ":" + str(rubric["source_line"]), "source_sha256": rubric["source_sha256"], "scope": rubric["scope"], "declared_semantic_status": rubric["semantic_status"], "executed_records": len(ex), "executed_classifiable": sum(x["classifiable"] for x in ex), "proposed_records": len(pr), "proposed_classifiable": sum(x["classifiable"] for x in pr), "all_observed_contexts_classifiable": all(x["classifiable"] for x in rows), "adjudication_required": rubric["adjudication_required"]})
    fully = sum(x["all_observed_contexts_classifiable"] for x in goals)
    unknown_record_keys = {(x["stage"], x["position"]) for x in ambiguities}
    summary = {"status": "PARTIALLY_VERIFIED / HOLD for unrestricted semantic manuscript claims", "statistical_status": "POST-HOC", "new_goals_evaluated": 31, "historical_goals_preserved": 4, "goals_all_observed_contexts_classifiable": fully, "goals_with_unresolved_cases": 35-fully,
        "records": {"new": 806, "historical": 104, "historical_in_final_construct_analysis": 78, "scoped_b3_supplement": 26, "cumulative": 910, "all_applicable_contexts_classifiable": 910-len(unknown_record_keys)},
        "coverage": [r for r in coverage if r["dimension"] in ("all", "origin", "model_stage_arm")],
        "disagreements": {"cumulative_endpoints": len(discrepancies), "cumulative_records": len({(d["stage"], d["position"]) for d in discrepancies}), "new_incremental_endpoints": sum(not d["previously_in_cycle_f"] for d in discrepancies), "new_incremental_records": len({(d["stage"], d["position"]) for d in discrepancies if not d["previously_in_cycle_f"]}), "by_category": dict(Counter(d["category"] for d in discrepancies)), "by_arm": dict(Counter(d["arm"] for d in discrepancies)), "independence_note": "Multiple endpoints of a record are dependent; pairs and goals also cluster."},
        "rubric_revision": {"changed_context_classifications": len(revisions), "changed_records": len({(r["stage"],r["position"]) for r in revisions}), "v1_status": "SUPERSEDED; unsupported positive-amount assumption must not be presented as empirical source-oracle false positives", "v2_hash": RUBRIC},
        "b3_consistency_supplement": {"version": "V4", "rubric_sha256": B3_RUBRIC, "records": 26, "contexts": len(b3_reconciliation), "historical_family_content_labels_preserved": True, "changed_contexts": sum(x["preserved_cycle_f_content_outcome"] != x["v4_construct_outcome"] for x in b3_reconciliation), "changed_records": len({(x["stage"],x["position"]) for x in b3_reconciliation if x["preserved_cycle_f_content_outcome"] != x["v4_construct_outcome"]}), "invalid_v3": "INVALID_AUDIT_SPEC: balance objective was erroneous; all V3 decisions/disagreements/statistics excluded. Its 52 apparent false positives are not empirical source failures."},
        "original_pair_population": {"pairs": len(pairs), "by_kind": dict(kinds), "frozen_eligibility": eligibility},
        "A_original_frozen_primary": {"rational": a, "saved_frozen_inference": prior_summary["statistics"]["reassessed_frozen_eligibility"]["primary_cpe_executed"], "status": "Original implemented labels; source-oracle replay verified in F"},
        "B_preserved_cycle_f_four_goal_sensitivity": {"rational": b, "saved_posthoc_inference": prior_summary["statistics"]["posthoc_four_banking_goals_only"]["analysis"]["primary_cpe_executed"], "status": "POST-HOC four-goal content recoding only; remaining labels original"},
        "C_independent_construct_sensitivity": {"contrasts": contrasts, "bounds_meaning": "Sharp bounds over independently free binary ambiguous-label completions, conditional on V2 remaining31 rubrics, V4 B3 rubric, preserved historical F findings for B0/B1/B6 and frozen eligibility; conservative for coherent common goal interpretations. Not CIs. No complete-case estimate, no favorable historical-label imputation, no newly confirmatory p-value.", "human_adjudication": "unavailable; labels are machine semantic judgments and shared mock replay dependencies remain"},
        "changed_eligibility_separate": {"bounds": {m: {k: sorted(v) for k,v in x.items()} for m,x in eligibility_bounds.items()}, "scenarios": changed_estimand},
        "original_sequence": {"S2": prior_summary["statistics"]["reassessed_frozen_eligibility"]["secondary"]["S2_benign_utility"], "S3": "descriptive after original nonsignificant S2; no gate reopened"},
        "input_provenance": {"input_sha256": before, "original_terminal_jsonl_hashes": metadata["source_hashes"]}}
    write_csv(root / "record_semantic_coverage.csv", details)
    (root / "record_semantic_coverage.csv.gz").write_bytes(gzip.compress((root / "record_semantic_coverage.csv").read_bytes(), mtime=0))
    write_csv(root / "coverage_by_stratum.csv", coverage)
    write_csv(root / "goal_coverage.csv", goals)
    write_csv(root / "record_discrepancies.csv", discrepancies)
    write_csv(root / "ambiguities.csv", ambiguities)
    write_csv(root / "rubric_revision_outcomes.csv", revisions)
    write_csv(root / "legacy_b3_construct_reconciliation.csv", b3_reconciliation)
    (root / "statistical_consequences.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    require({str(p): sha(p) for p in inputs} == before, "input changed during post-processing")
    print(json.dumps({"records": summary["records"], "fully_classifiable_goals": fully, "disagreements": summary["disagreements"], "primary_completion_bounds": {k:v["estimate"] for k,v in contrasts["cpe_executed"].items() if k in ("lower","upper","all_false","all_true")}, "bootstrap_envelope": contrasts["cpe_executed"]["bootstrap_envelope"], "eligibility_counts": {m:{k:len(v) for k,v in x.items()} for m,x in eligibility_bounds.items()}}, indent=2))


if __name__ == "__main__":
    main()
