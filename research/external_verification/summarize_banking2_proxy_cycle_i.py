"""Separate POST-HOC proxy sensitivity; never modify original H/FSE labels.

Exact record coefficients preserve model -> goal -> carrier nesting. Independent
unitwise arithmetic and small exact completion enumeration validate new bounds.
"""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import gzip
import hashlib
import io
import itertools
import json
import pathlib
import time
from collections import Counter, defaultdict
from fractions import Fraction


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def records(path):
    return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]


def key(r):
    return r["stage"], int(r["position"])


def number(v):
    return {"fraction": str(v), "estimate": float(v)}


def derive_population(metadata, eligibility):
    paired = defaultdict(dict)
    for r in metadata:
        if r["stage"] == "confirmatory":
            k = r["model"], r["pair_id"]
            require(r["arm"] not in paired[k], "duplicate original arm")
            paired[k][r["arm"]] = r
    require(len(paired) == 474, "original total paired population changed")
    grouped = defaultdict(list)
    kinds = Counter()
    for (model, _), pair in paired.items():
        require(set(pair) == {"off", "full"}, "missing original paired arm")
        off, full = pair["off"], pair["full"]
        for f in ("model", "suite", "kind", "user_task", "injection_task", "seed", "cell_id"):
            require(off[f] == full[f], "paired identity differs")
        kinds[off["kind"]] += 1
        goal = off["suite"] + "/" + str(off["injection_task"])
        if off["kind"] == "security" and off["canonical_population"] and goal in eligibility[model]:
            grouped[model, goal].append(pair)
    models = sorted({m for m, _ in grouped})
    units = Counter(m for m, _ in grouped)
    require(len(models) == 2 and len(grouped) == 42 and all(n == 21 for n in units.values()),
            "frozen principal strata changed")
    require(sum(map(len, grouped.values())) == 168 and {len(v) for v in grouped.values()} == {4},
            "principal carrier nesting changed")
    weights = {}
    for (model, goal), pairs in grouped.items():
        w = Fraction(1, len(models) * units[model] * len(pairs))
        for pair in pairs:
            for arm, row in pair.items():
                weights[key(row)] = w if arm == "full" else -w
    require(set(weights.values()) == {Fraction(1,168), Fraction(-1,168)}, "unexpected exact coefficients")
    return weights, grouped, {"original_total_pairs": 474, "original_benign_pairs": 194,
        "all_attacker_pairs": 280, "principal_pairs": 168, "model_goal_units": 42,
        "goals_per_model": dict(units), "carrier_pairs_per_model_goal": 4,
        "frozen_eligibility": eligibility, "original_kind_pair_counts": dict(kinds)}


def bound(weights, labels):
    fixed, lo, hi, unknown = Fraction(), Fraction(), Fraction(), []
    for k, w in weights.items():
        y = labels[k]
        if isinstance(y, bool):
            fixed += w * int(y)
        else:
            require(y in ("AMBIGUOUS", "UNOBSERVABLE", "UNKNOWN"), "invalid incomplete outcome")
            lo += min(Fraction(), w); hi += max(Fraction(), w)
            unknown.append({"stage": k[0], "position": k[1], "coefficient": str(w)})
    return {"lower": number(fixed+lo), "upper": number(fixed+hi),
            "unknown_labels": len(unknown), "unknown_records": unknown,
            "meaning": "Binary-label completion bounds, not confidence intervals; conditional on the explicitly stated construct and retained fixed labels."}


def unitwise(grouped, labels):
    by_model = defaultdict(list)
    for (model, _goal), pairs in grouped.items():
        low, high = Fraction(), Fraction()
        for pair in pairs:
            off, full = labels[key(pair["off"])], labels[key(pair["full"])]
            of = [int(off)] if isinstance(off,bool) else [0,1]
            fu = [int(full)] if isinstance(full,bool) else [0,1]
            low += Fraction(min(fu)-max(of), len(pairs))
            high += Fraction(max(fu)-min(of), len(pairs))
        by_model[model].append((low,high))
    return tuple(sum((sum((v[i] for v in units),Fraction()) / len(units)
                       for units in by_model.values()),Fraction()) / len(by_model) for i in (0,1))


def checked_bound(weights, grouped, labels, enumerate_small=False):
    result = bound(weights, labels)
    direct = (Fraction(result["lower"]["fraction"]), Fraction(result["upper"]["fraction"]))
    require(unitwise(grouped, labels) == direct, "independent model/goal/carrier arithmetic differs")
    if enumerate_small:
        unknown = [k for k in weights if not isinstance(labels[k],bool)]
        require(len(unknown) <= 10, "new exact-enumeration scope unexpectedly large")
        sums = []
        for choices in itertools.product((False,True),repeat=len(unknown)):
            completion = dict(labels);completion.update(zip(unknown,choices))
            sums.append(sum((w*int(completion[k]) for k,w in weights.items()),Fraction()))
        require((min(sums),max(sums)) == direct, "exact binary completions differ")
        result["independently_enumerated_completions"] = len(sums)
    return result


def write_csv(path, rows, fields=None):
    buffer = io.StringIO(newline="")
    fields = fields or list(rows[0])
    w = csv.DictWriter(buffer,fieldnames=fields);w.writeheader();w.writerows(rows)
    path.write_text(buffer.getvalue(),encoding="utf-8")


def main():
    ap = argparse.ArgumentParser();ap.add_argument("--audit-dir",type=pathlib.Path,required=True)
    args = ap.parse_args();own=args.audit_dir;parent=own.parent;tick=time.perf_counter()
    started=dt.datetime.now(dt.timezone.utc).isoformat()
    h=parent/"cycle_h_20261010";g=parent/"cycle_g_20261010"
    bound_inputs={h/"record_semantic_coverage.csv.gz":"8a02769283675624444f65cbee52343650b6a69afdd7f442d779b10df81c6454",
                  h/"statistical_consequences.json":"61d4f142a94603fbca247d4be068ee7c01455dd10f8e9a7f147c9e2a8082be27",
                  g/"original_record_metadata.json.gz":"67700d4a783831cf277374085bfeda8ba591e8b1624a8acec3dfe2837c84132f",
                  g/"statistical_consequences.json":"7d39650befb155e992b9a88b04fb7052d29cf15cbecc01f319a8d708d14629d4"}
    for p,expected in bound_inputs.items():require(sha(p)==expected,"frozen input changed: "+p.name)
    paths=[own/"selected_contexts.json",own/"frozen_proxy_rubric_v1.json",own/"frozen_proxy_rubric_v2.json",
           own/"whole_history_v1/proxy_records.jsonl.gz",own/"food_attestation_v2/proxy_records.jsonl.gz"]
    bound_inputs.update({p:sha(p) for p in paths})
    rows=list(csv.DictReader(io.StringIO(gzip.decompress((h/"record_semantic_coverage.csv.gz").read_bytes()).decode())))
    require(len(rows)==1794,"original H context population differs")
    prior={(*key(r),r["endpoint"]):r for r in rows}
    selected=read(own/"selected_contexts.json")
    selected_keys={(*key(r),r["endpoint"]) for r in selected}
    require(len(selected_keys)==44 and len({key(r) for r in selected})==24,"selected scope differs")
    banking2_prior=[r for r in rows if r["suite"]=="banking" and r["goal"]=="injection_task_2"]
    outside=[r for r in banking2_prior if (*key(r),r["endpoint"]) not in selected_keys]
    require(len(banking2_prior)==52 and len({key(r) for r in banking2_prior})==26 and
            len(outside)==8 and all(r["semantic_outcome"]=="False" for r in outside),
            "preserved negative contexts outside reassessment differ")
    v1={key(r):r for r in records(own/"whole_history_v1/proxy_records.jsonl.gz")}
    v2={key(r):r for r in records(own/"food_attestation_v2/proxy_records.jsonl.gz")}
    require(set(v1)==set(v2)=={key(r) for r in selected},"version record identity differs")
    rubric=read(own/"frozen_proxy_rubric_v2.json")
    metadata=read(g/"original_record_metadata.json.gz")["records"]
    meta={key(r):r for r in metadata}
    require(len(meta)==1492,"original saved metadata differs")
    hstats=read(h/"statistical_consequences.json")
    eligibility=read(g/"statistical_consequences.json")["original_pair_population"]["frozen_eligibility"]
    weights,grouped,population=derive_population(metadata,eligibility)
    labels={ep:{} for ep in ("executed","proposed")}
    for r in rows:
        val=r["semantic_outcome"]
        labels[r["endpoint"]][key(r)]={"True":True,"False":False}.get(val,val)
    overlay_v1=copy.deepcopy(labels);overlay_v2=copy.deepcopy(labels)
    ledger,comparisons=[],[]
    for ck in sorted(selected_keys):
        stage,position,ep=ck;k=(stage,position);old=prior[ck];r=v2[k];p=r["proxy"][ep]
        require(old["semantic_outcome"]=="AMBIGUOUS","selected original preference no longer ambiguous")
        require(r["raw_sha256"]==old["raw_sha256"] and r["evidence_sha256"]==old["evidence_sha256"],"record source binding differs")
        require(r["rubric_sha256"]==sha(own/"frozen_proxy_rubric_v2.json") and
                p["second_witness_agrees"] and r["endpoint_order_invariant"],"immutable proxy witness missing")
        new=p["outcome"];overlay_v1[ep][k]=v1[k]["proxy"][ep]["outcome"];overlay_v2[ep][k]=new
        historical=json.loads(old["historical_outcomes"])
        fields=[]
        for field,value in historical.items():
            require(isinstance(value,bool),"nonbinary historical endpoint")
            if field in r["recorded"] and r["recorded"][field] is not None:
                require(r["recorded"][field]==value,"runner/retained H endpoint differs")
            require(meta[k].get(field)==value,"original metadata/retained H endpoint differs")
            fields.append(field)
            comparisons.append({"stage":stage,"position":position,"model":r["model"],"arm":r["arm"],
                "kind":r["kind"],"endpoint":ep,"historical_endpoint":field,"historical_outcome":value,
                "proxy_outcome":new,"agreement":value==new if isinstance(new,bool) else "UNRESOLVED",
                "interpretation":"Different purchased-food construct; agreement is not verification of personal preference.",
                "raw_pointer":r["raw_pointer"],"raw_sha256":r["raw_sha256"],"rubric_sha256":r["rubric_sha256"]})
        witnesses=[e for e in r["events"][ep] if e["ordinal"] in p["witness_ordinals"]]
        ledger.append({"stage":stage,"position":position,"model":r["model"],"arm":r["arm"],"kind":r["kind"],
            "suite":"banking","goal":"injection_task_2","benchmark_version":"v1.2.2","endpoint":ep,
            "raw_pointer":r["raw_pointer"],"raw_sha256":r["raw_sha256"],"evidence_sha256":r["evidence_sha256"],
            "original_H_personal_preference":"AMBIGUOUS","personal_preference_after":"AMBIGUOUS_UNCHANGED",
            "proxy_V1_outcome":v1[k]["proxy"][ep]["outcome"],"proxy_V2_outcome":new,
            "proxy_only_classification_change":isinstance(new,bool),
            "V1_to_V2_change":v1[k]["proxy"][ep]["outcome"]!=new,
            "status":"EXECUTED_ACCEPTED" if ep=="executed" and new is True else
                     "HYPOTHETICAL_PROPOSED_SUCCESS" if ep=="proposed" and new is True else
                     "UNKNOWN" if not isinstance(new,bool) else "PROXY_FALSE",
            "attested_initial_foods":json.dumps(r["food_specific_initial_binding"]["attested_food_pool"]),
            "unbound_initial_foods":json.dumps(r["food_specific_initial_binding"]["unbound_food_pool"]),
            "matched_foods":json.dumps(p["foods"]),"witness_ordinals":json.dumps(p["witness_ordinals"]),
            "original_blocked_witnesses":sum(not e["original_proposal_executed"] for e in witnesses),
            "historical_outcomes":json.dumps(historical,sort_keys=True),
            "historical_endpoint_comparisons":len(fields),
            "historical_comparison_status":"AVAILABLE" if fields else "UNEXECUTED_NO_RECORDED_PROPOSAL_ENDPOINT",
            "reason":p["reason"],"rubric_V1_sha256":v1[k]["rubric_sha256"],
            "rubric_V2_sha256":r["rubric_sha256"],"context_sha256":p["context_sha256"],
            "evidence":json.dumps(witnesses,sort_keys=True)})
    require(len(ledger)==44 and Counter(r["endpoint"] for r in ledger)=={"executed":20,"proposed":24},"context ledger differs")
    base_digest=lambda ds:hashlib.sha256(json.dumps({ep:{str(k):v for k,v in vals.items()} for ep,vals in ds.items()},sort_keys=True).encode()).hexdigest()
    original_labels_digest=base_digest(labels)
    statistical={"cycle":"I_BANKING2_PURCHASE_HISTORY_PROXY","statistical_status":"POST_HOC_CHANGED_CONSTRUCT",
        "population":population,"original_sequence":"S2 remains closed; S3 descriptive. No new p-values or confidence intervals.",
        "original_personal_preference_H_bounds_unchanged":{},"conservative_whole_history_V1_H_hybrid_bounds":{},
        "food_attestation_V2_H_hybrid_bounds":{},"proxy_other_frozen_source_labels_fixed":{},
        "per_record_bound_impacts":[]}
    source_labels={ep:{key(r):r["cpe_"+ep] for r in metadata if key(r) in weights} for ep in labels}
    for ep in labels:
        original=sum((w*int(source_labels[ep][k]) for k,w in weights.items()),Fraction())
        original_h=checked_bound(weights,grouped,labels[ep])
        ref=hstats["D_H_bounds"] if ep=="executed" else hstats["independent_proposed_outcome_bounds"]["H"]
        require(original_h["lower"]==ref["lower"] and original_h["upper"]==ref["upper"] and
                original_h["unknown_labels"]==ref["unknown_labels"],"original H arithmetic changed")
        statistical["original_personal_preference_H_bounds_unchanged"][ep]=original_h
        statistical["conservative_whole_history_V1_H_hybrid_bounds"][ep]=checked_bound(weights,grouped,overlay_v1[ep])
        statistical["food_attestation_V2_H_hybrid_bounds"][ep]=checked_bound(weights,grouped,overlay_v2[ep],True)
        native_rest=copy.deepcopy(source_labels[ep])
        for ck in selected_keys:
            if ck[2]==ep and ck[:2] in weights:native_rest[ck[:2]]=v2[ck[:2]]["proxy"][ep]["outcome"]
        rest=checked_bound(weights,grouped,native_rest)
        if rest["unknown_labels"]==0:rest["conditional_point"]=rest["lower"]
        statistical["proxy_other_frozen_source_labels_fixed"][ep]={"original_source_defined_point":number(original),
            "proxy_sensitivity":rest,"assumption":"Only affected Banking2 proxy labels substituted; every other source label fixed. This is not full-population semantic verification."}
    require(statistical["proxy_other_frozen_source_labels_fixed"]["executed"]["original_source_defined_point"]["fraction"]=="-85/168","original primary source estimate differs")
    current=copy.deepcopy(labels)
    for row in ledger:
        k=key(row);ep=row["endpoint"];before=bound(weights,current[ep]);current[ep][k]=row["proxy_V2_outcome"]
        after=bound(weights,current[ep]);w=weights.get(k,Fraction())
        statistical["per_record_bound_impacts"].append({"stage":k[0],"position":k[1],"endpoint":ep,
            "model":row["model"],"arm":row["arm"],"in_principal_population":k in weights,"coefficient":str(w),
            "proxy_decision":row["proxy_V2_outcome"],
            "lower_change":str(Fraction(after["lower"]["fraction"])-Fraction(before["lower"]["fraction"])),
            "upper_change":str(Fraction(after["upper"]["fraction"])-Fraction(before["upper"]["fraction"])),
            "changed_construct_lower_after":after["lower"]["fraction"],"changed_construct_upper_after":after["upper"]["fraction"]})
    require(base_digest(labels)==original_labels_digest,"original H decisions mutated")
    coverage=[]
    for dims in [("endpoint",),("stage","endpoint"),("model","endpoint"),("arm","endpoint"),("kind","endpoint"),
                 ("stage","model","arm","kind","endpoint")]:
        groups=defaultdict(list)
        for r in ledger:groups[tuple(r[d] for d in dims)].append(r)
        for vals,rs in sorted(groups.items()):
            coverage.append({"dimensions":"/".join(dims),**dict(zip(dims,vals)),"contexts":len(rs),
                "distinct_records":len({key(r) for r in rs}),"proxy_true":sum(r["proxy_V2_outcome"] is True for r in rs),
                "proxy_false":sum(r["proxy_V2_outcome"] is False for r in rs),
                "proxy_unknown":sum(not isinstance(r["proxy_V2_outcome"],bool) for r in rs),
                "source_endpoint_comparisons":sum(r["historical_endpoint_comparisons"] for r in rs)})
    disagreements=[r for r in comparisons if r["agreement"] is False]
    result={"records":24,"contexts":44,"contexts_by_endpoint":dict(Counter(r["endpoint"] for r in ledger)),
        "proxy_classifiable":sum(isinstance(r["proxy_V2_outcome"],bool) for r in ledger),
        "V1_to_V2_changed_contexts":sum(r["V1_to_V2_change"] for r in ledger),
        "record_kinds":dict(Counter(r["kind"] for r in v2.values())),
        "all_Banking2_prior_contexts":52,"all_Banking2_prior_records":26,
        "outside_current_reassessment_contexts":8,"entirely_unreassessed_records":2,
        "unreassessed_contexts_in_selected_records":4,"records_with_any_unreassessed_context":6,
        "unreassessed_Banking2_context_status":"Eight prior H FALSE contexts carried forward as fixed inputs, not newly reassessed or newly validated by this run.",
        "source_endpoint_comparisons":len(comparisons),"source_endpoint_disagreements":len(disagreements),
        "source_disagreeing_distinct_records":len({key(r) for r in disagreements}),
        "contexts_with_source_comparison":sum(bool(r["historical_endpoint_comparisons"]) for r in ledger),
        "contexts_without_recorded_source_endpoint":sum(not r["historical_endpoint_comparisons"] for r in ledger),
        "original_personal_preference_contexts_changed":0,"original_H_labels_digest_unchanged":original_labels_digest,
        "other_goal_labels_changed":0,"original_H_coverage_unchanged":hstats["coverage"],
        "original_H_remaining_unchanged":hstats["H_remaining"],"unrestricted_manuscript":"HOLD_UNCHANGED",
        "personal_preference":"AMBIGUOUS / NOT IDENTIFIABLE FROM RETAINED PURCHASE HISTORY",
        "independent_human_reviews":0,"analysis_started_utc":started,"runtime_seconds":time.perf_counter()-tick,
        "input_hashes_before_after":{str(p):expected for p,expected in bound_inputs.items()}}
    statistical["interpretation"]="V2 H-hybrid ranges are a purchased-food proxy scenario for Banking2 with other H constructs retained, not tightened actual-preference H bounds or confirmatory evidence. Preference remains ambiguous; source-rest-fixed points are conditional comparisons."
    write_csv(own/"context_differential_ledger.csv",ledger)
    write_csv(own/"source_endpoint_comparisons.csv",comparisons)
    write_csv(own/"source_endpoint_disagreements.csv",disagreements,list(comparisons[0]))
    fields=sorted({k for r in coverage for k in r})
    write_csv(own/"proxy_coverage.csv",coverage,fields)
    write_csv(own/"record_bound_impacts.csv",statistical.pop("per_record_bound_impacts"))
    (own/"statistical_consequences.json").write_text(json.dumps(statistical,indent=2)+"\n")
    (own/"analysis_summary.json").write_text(json.dumps(result,indent=2)+"\n")
    for p,expected in bound_inputs.items():require(sha(p)==expected,"input mutated during analysis")
    print(json.dumps({**{k:v for k,v in result.items() if k not in ("input_hashes_before_after","original_H_coverage_unchanged","original_H_remaining_unchanged")},
                      "new_hybrid_bounds":statistical["food_attestation_V2_H_hybrid_bounds"],
                      "source_rest_fixed":statistical["proxy_other_frozen_source_labels_fixed"]}))


if __name__ == "__main__":
    main()
