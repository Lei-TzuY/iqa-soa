"""Exact post-hoc calculations; original labels and analyzers are read-only."""
from __future__ import annotations
import argparse
import copy
import csv
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import time
from collections import Counter, defaultdict
from fractions import Fraction

from benign_construct_cycle_j import digest, require, reuse_prior


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def number(v):
    return {"fraction":str(v),"estimate":float(v)}


def bounds(rows, equivalence=False):
    fixed = Fraction();free = defaultdict(Fraction)
    for row in rows:
        coefficient = Fraction(1 if row["arm"]=="full" else -1,194)
        value=row["label"]
        if value is None:
            key=row.get("equivalence_key") if equivalence else None
            free[key or row["raw_pointer"]]+=coefficient
        elif value:fixed+=coefficient
    return {"lower":number(fixed+sum((min(Fraction(),c) for c in free.values()),Fraction())),
            "upper":number(fixed+sum((max(Fraction(),c) for c in free.values()),Fraction())),
            "unknown_labels":sum(r["label"] is None for r in rows),"free_label_groups":len(free),
            "zero_contribution_groups":sum(c==0 for c in free.values()),
            "meaning":"Recordwise binary-completion bounds, not confidence intervals; equivalence version additionally assumes uniform deterministic adjudication of matching retained evidence."}


def write_csv(path, records, fields=None):
    fields=fields or list(dict.fromkeys(k for record in records for k in record))
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        writer.writerows({k:"UNKNOWN" if v is None else "TRUE" if v is True else "FALSE" if v is False else v for k,v in r.items()} for r in records)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--audit-dir",type=pathlib.Path,required=True);args=ap.parse_args();b=args.audit_dir
    started=dt.datetime.now(dt.timezone.utc).isoformat();tick=time.perf_counter()
    prior=b.parent/"cycle_i_continuation_20261011/construct_record_audit.json"
    inputs=[b/"record_audit_final.jsonl.gz",b/"frozen_population.json",b/"evidence_equivalence_fingerprints.json",b/"frozen_output_delivery_boundary.json",b/"frozen_equivalence_spec.json",prior]
    before={str(p):sha(p) for p in inputs}
    original=[json.loads(l) for l in gzip.decompress((b/"record_audit_final.jsonl.gz").read_bytes()).decode().splitlines()]
    new=copy.deepcopy(original)
    population=json.loads((b/"frozen_population.json").read_text())
    previous=json.loads(prior.read_text());fingerprints={r["raw_pointer"]:r["evidence_equivalence_sha256"] for r in json.loads((b/"evidence_equivalence_fingerprints.json").read_text())["fingerprints"]}
    require(len(population)==388 and len(new)==144,"fixed population differs")
    groups=defaultdict(list)
    for r in population:groups[r["model"],r["pair_id"]].append(r)
    require(len(groups)==194 and all(len(rs)==2 and {r['arm'] for r in rs}=={'off','full'} and len({r['goal'] for r in rs})==1 for rs in groups.values()),"frozen 194 pairs differ")
    require(Counter(r["model"] for r in population)=={"qwen":194,"mistral":194},"model weighting differs")
    output_scope=[]
    for r in new:
        if r["goal"]=="travel/user_task_3":
            decision=r["decisions"]["executed"]
            if decision["semantic"] is True:
                r["conditional_retained_transcript_success"]=True
                output_scope.append({"raw_pointer":r["raw_pointer"],"raw_sha256":r["raw_sha256"],"goal":r["goal"],"model":r["model"],"arm":r["arm"],"native_utility":r["native_utility"],"conditional_transcript_success":True,"principal_semantic":"UNKNOWN","category":"CONDITIONAL_OUTPUT_SCOPE_DISAGREEMENT" if not r["native_utility"] else "OUTPUT_DELIVERY_SCOPE_UNRESOLVED"})
                decision["semantic"]=None;decision["reason"]="ORIGINAL_CLIENT_OUTPUT_DELIVERY_CONTRACT_NOT_ESTABLISHED"
                decision["unintended_effects"].append({"category":"INCOMPLETE_OR_OPAQUE_DELIVERY_EVIDENCE"})
    unified=[]
    for r in new:
        for endpoint,d in r["decisions"].items():
            unified.append({"stage":r["stage"],"position":r["position"],"model":r["model"],"arm":r["arm"],"goal":r["goal"],"raw_pointer":r["raw_pointer"],"raw_sha256":r["raw_sha256"],"evidence_sha256":r["evidence_sha256"],"endpoint":endpoint,"source_verdict":r["native_utility"] if endpoint=="executed" else "UNEXECUTED_SOURCE_PROPOSED_ENDPOINT","semantic":d["semantic"],"required_component":d["required_action"],"reason":d["reason"],"evidence_origin":"NEW_ORIGINAL_RECORD_AUDIT","effects":json.dumps(d["unintended_effects"],sort_keys=True)})
    prior_overlay=[]
    for r in previous["records"]:
        decision=reuse_prior(r);prior_overlay.append({**r,"J_decision":decision})
        unified.append({"stage":r["stage"],"position":r["position"],"model":r["model"],"arm":r["arm"],"goal":r["goal"],"raw_pointer":r["raw_pointer"],"raw_sha256":r["raw_sha256"],"evidence_sha256":r["evidence_sha256"],"endpoint":"executed","source_verdict":r["native"],"semantic":decision["semantic"],"required_component":r["semantic"],"reason":decision["reason"],"evidence_origin":"REUSED_I_NO_NEW_REPLAY","effects":json.dumps(decision["unintended_effects"],sort_keys=True)})
    lookup={r["raw_pointer"]:r for r in unified if r["endpoint"]=="executed" and r["stage"]=="confirmatory"}
    require(len(lookup)==164,"41-task/164-observation coverage differs")
    source_point=sum((Fraction(int(r["native_utility"])*(1 if r["arm"]=="full" else -1),194) for r in population),Fraction())
    require(source_point==Fraction(3,194),"original source S2 differs")
    conditional=[];independent=[];known_corrected=[]
    for r in population:
        selected=lookup.get(r["raw_pointer"])
        base={**r,"equivalence_key":fingerprints.get(r["raw_pointer"])}
        conditional.append({**base,"label":selected["semantic"] if selected else r["native_utility"]})
        independent.append({**base,"label":selected["semantic"] if selected else None})
        known_corrected.append({**base,"label":selected["semantic"] if selected and selected["semantic"] is not None else r["native_utility"]})
    # Equivalence scenario must not use conflicting known outcomes.
    class_known=defaultdict(set)
    for r in independent:
        if r.get("equivalence_key") and r["label"] is not None:class_known[r["equivalence_key"]].add(r["label"])
    require(all(len(s)<=1 for s in class_known.values()),"evidence-equivalence class conflicts")
    corrected=sum((Fraction(int(r["label"])*(1 if r["arm"]=="full" else -1),194) for r in known_corrected),Fraction())
    unitwise=[]
    for model in ("qwen","mistral"):
        units=defaultdict(dict)
        for r in known_corrected:
            if r["model"]==model:units[r["goal"]][r["arm"]]=int(r["label"])
        require(len(units)==97,"97 model task units differ")
        unitwise.append(sum((Fraction(a['full']-a['off']) for a in units.values()),Fraction())/97)
    require(sum(unitwise,Fraction())/2==corrected,"independent task/model arithmetic differs")
    disagreements=[r for r in unified if r["endpoint"]=="executed" and r["semantic"] is not None and r["semantic"] is not r["source_verdict"]]
    for r in disagreements:r["category"]="SOURCE_ORACLE_FALSE_POSITIVE" if r["semantic"] is False else "SOURCE_ORACLE_FALSE_NEGATIVE"
    strata=[]
    for endpoint in ("executed","proposed"):
        rs=[r for r in unified if r["endpoint"]==endpoint]
        for dimensions in (("goal",),("goal","stage"),("stage","model","arm"),("model",),("arm",)):
            buckets=defaultdict(list)
            for r in rs:buckets[tuple(r[k] for k in dimensions)].append(r)
            for keys,items in buckets.items():
                strata.append({"endpoint":endpoint,"dimensions":"/".join(dimensions),"values":"/".join(map(str,keys)),"examined":len(items),"classified":sum(r['semantic'] is not None for r in items),"true":sum(r['semantic'] is True for r in items),"false":sum(r['semantic'] is False for r in items),"unknown":sum(r['semantic'] is None for r in items),"confirmed_disagreements":sum(r in disagreements for r in items)})
    goaldict=defaultdict(list)
    for r in lookup.values():goaldict[r["goal"]].append(r)
    fully=sum(all(r['semantic'] is not None for r in rs) for rs in goaldict.values())
    stats={"cycle":"J","status":"POST_HOC_PARTIAL_IDENTIFICATION","fixed_population":{"pairs":194,"tasks":97,"confirmatory_observations":388,"task_pairs_per_model":97,"model_weights":{"qwen":"1/2","mistral":"1/2"},"pairwise_endpoint_coefficient":"+/-1/194"},
           "original_source_defined_S2":number(source_point),"original_S2_CI_unchanged":[-0.010309278,0.041237113],"original_S2_p_unchanged":0.452555474,
           "known_discrepancy_corrections_every_other_source_label_fixed":number(corrected),"per_model_conditional_points":dict(zip(("qwen","mistral"),map(number,unitwise))),
           "conditional_native_rest_fixed_recordwise_bounds":bounds(conditional),"independently_classified_only_unaudited_free_recordwise_bounds":bounds(independent),
           "conditional_evidence_equivalence_native_rest_fixed_scenario":bounds(conditional,True),"conditional_evidence_equivalence_unaudited_free_scenario":bounds(independent,True),
           "output_scope_sensitivity":"Four Travel3 principal labels are UNKNOWN. Retained-transcript output conditionally supports all four, with two conditional source false negatives; that pair-balanced recoding leaves the known-corrected contrast unchanged. No original client presentation contract/human decision is established.",
           "meaning":"No new confidence intervals or p-values. Original source statistic is separate from post-hoc broader workflow correctness. Native-rest-fixed assumptions are unverified outside coverage. Equivalence scenario assumes matching retained evidence receives the same judgment, including a uniform missing output/presentation interpretation; it is not proof of labels or actual user delivery. S2 gate remains closed; S3 descriptive."}
    confirm=[r for r in unified if r["endpoint"]=="executed" and r["stage"]=="confirmatory"]
    summary={"cycle":"J","started_utc":started,"runtime_seconds":time.perf_counter()-tick,"new_tasks":36,"prior_tasks_reused":5,"audited_task_populations":41,"fully_classified_confirmatory_task_populations":fully,"total_task_populations":97,
             "new_original_records_restored":144,"old_records_reused":30,"distinct_all_stage_records":174,"confirmatory_observations_audited":164,"confirmatory_classified":sum(r['semantic'] is not None for r in confirm),"confirmatory_unknown":sum(r['semantic'] is None for r in confirm),"unaudited_confirmatory_observations":224,
             "all_stage_classified":sum(r['semantic'] is not None for r in unified if r['endpoint']=='executed'),"all_stage_unknown":sum(r['semantic'] is None for r in unified if r['endpoint']=='executed'),"source_disagreements_all_stages":len(disagreements),"source_disagreements_confirmatory":sum(r['stage']=='confirmatory' for r in disagreements),
             "new_current_cycle_confirmatory_disagreements":sum(r['evidence_origin']=='NEW_ORIGINAL_RECORD_AUDIT' for r in disagreements),"new_prior_negative_overlay_disagreements":sum(r['stage']=='qualification' for r in disagreements),
             "false_positives":sum(r['category']=='SOURCE_ORACLE_FALSE_POSITIVE' for r in disagreements),"false_negatives":sum(r['category']=='SOURCE_ORACLE_FALSE_NEGATIVE' for r in disagreements),"conditional_output_scope_disagreements":sum(r['category']=='CONDITIONAL_OUTPUT_SCOPE_DISAGREEMENT' for r in output_scope),
             "new_actual_counts":dict(Counter(str(r['semantic']) for r in unified if r['endpoint']=='executed' and r['evidence_origin']=='NEW_ORIGINAL_RECORD_AUDIT')),"new_proposed_counts":dict(Counter(str(r['semantic']) for r in unified if r['endpoint']=='proposed')),"human_reviews":0,"owner_decisions":0,"new_provider_calls":0,"HOLD":"UNCHANGED",
             "input_hashes_before_after":before,"task_complete_positive_limit":"Only stated frozen mock-workflow criteria are supported; no actual external service/user receipt, subjective quality, prospective registration or full-population utility equivalence."}
    require(all(sha(p)==h for p,h in before.items()),"analysis input changed")
    for name,obj in (("statistical_consequences.json",stats),("analysis_summary.json",summary)):
        (b/name).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    for name,obj in (("principal_record_decisions.json.gz",new),("prior_reuse_overlay.json.gz",prior_overlay)):
        (b/name).write_bytes(gzip.compress((json.dumps(obj,indent=2)+"\n").encode(),mtime=0))
    write_csv(b/"record_ledger.csv",unified)
    write_csv(b/"confirmed_disagreements.csv",disagreements)
    write_csv(b/"conditional_output_scope.csv",output_scope)
    write_csv(b/"coverage_by_stratum.csv",strata)
    matrix=[]
    for r in population:
        a=lookup.get(r['raw_pointer']);matrix.append({"goal":r['goal'],"model":r['model'],"arm":r['arm'],"position":r['position'],"pair_id":r['pair_id'],"raw_pointer":r['raw_pointer'],"raw_sha256":r['raw_sha256'],"native":r['native_utility'],"semantic":a['semantic'] if a else "UNEXECUTED","status":"CLASSIFIED" if a and a['semantic'] is not None else "AMBIGUOUS_OR_UNOBSERVABLE" if a else "UNEXECUTED","equivalence_fingerprint":fingerprints.get(r['raw_pointer'],"UNEXECUTED")})
    write_csv(b/"complete_population_coverage.csv",matrix)
    print(json.dumps({"summary":{k:v for k,v in summary.items() if k!='input_hashes_before_after'},"statistics":stats},indent=2))


if __name__=="__main__":main()
