"""Exact post-hoc K arithmetic on the fixed original benign population."""
from __future__ import annotations
import argparse,csv,datetime as dt,gzip,hashlib,json,pathlib,time
from collections import Counter,defaultdict
from fractions import Fraction

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def zipped(p,lines=False):
 s=gzip.decompress(p.read_bytes()).decode()
 return [json.loads(x) for x in s.splitlines()] if lines else json.loads(s)
def encode(v):return {'fraction':str(v),'estimate':float(v)}
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def csv_write(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def bounds(pop,labels,groups=None):
 fixed=Fraction();free=defaultdict(Fraction);known=defaultdict(set)
 for r in pop:
  key=r['raw_pointer'];g=groups.get(key,key) if groups else key
  coefficient=Fraction(1 if r['arm']=='full' else -1,194);label=labels.get(key)
  if label is not None:known[g].add(label)
  else:free[g]+=coefficient
 for g,s in known.items():assert len(s)<=1,'conflicting known labels in matching evidence'
 for r in pop:
  key=r['raw_pointer'];g=groups.get(key,key) if groups else key
  coefficient=Fraction(1 if r['arm']=='full' else -1,194);label=labels.get(key)
  if label is not None:fixed+=coefficient*label
  elif known.get(g):fixed+=coefficient*next(iter(known[g]))
 for g in list(free):
  if known.get(g):del free[g]
 return {'lower':encode(fixed+sum((min(Fraction(),x) for x in free.values()),Fraction())),
         'upper':encode(fixed+sum((max(Fraction(),x) for x in free.values()),Fraction())),
         'unknown_labels':sum(labels.get(r['raw_pointer']) is None for r in pop),
         'free_groups':len(free),'zero_contribution_groups':sum(v==0 for v in free.values()),
         'status':'POST_HOC_BINARY_COMPLETION_BOUNDS_NOT_CONFIDENCE_INTERVALS'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit-dir',type=pathlib.Path,required=True);a=ap.parse_args()
 p=a.audit_dir;j=p.parent/'cycle_j_20261012';tick=time.perf_counter();started=dt.datetime.now(dt.timezone.utc).isoformat()
 inputs=[p/'record_audit_principal.jsonl.gz',j/'frozen_population.json',j/'principal_record_decisions.json.gz',j/'prior_reuse_overlay.json.gz',j/'evidence_equivalence_fingerprints.json',p/'final_validation_and_witnesses.json']
 before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
 pop=read(j/'frozen_population.json');old=zipped(j/'principal_record_decisions.json.gz');prior=zipped(j/'prior_reuse_overlay.json.gz');new=zipped(p/'record_audit_principal.jsonl.gz',True)
 assert len(pop)==388 and len(new)==128 and len({r['goal'] for r in pop})==97
 assert not ({r['goal'] for r in new}&{r['goal'] for r in old+prior})
 pairs=defaultdict(list)
 for r in pop:pairs[(r['model'],r['pair_id'])].append(r)
 assert len(pairs)==194 and all(len(v)==2 and {r['arm'] for r in v}=={'off','full'} for v in pairs.values())
 assert Counter(k[0] for k in pairs)=={'qwen':97,'mistral':97}
 audited={r['raw_pointer']:r['decisions']['executed']['semantic'] for r in old+new}
 audited.update({r['raw_pointer']:r['J_decision']['semantic'] for r in prior if r['stage']=='confirmatory'})
 native={r['raw_pointer']:r['native_utility'] for r in pop}
 corrected={k:audited[k] if audited.get(k) is not None else v for k,v in native.items()}
 native_rest={r['raw_pointer']:audited[r['raw_pointer']] if r['raw_pointer'] in audited else r['native_utility'] for r in pop}
 independent={r['raw_pointer']:audited.get(r['raw_pointer']) for r in pop}
 def contrast(labels):return sum((Fraction(1 if r['arm']=='full' else -1,194)*labels[r['raw_pointer']] for r in pop),Fraction())
 source=contrast(native);point=contrast(corrected);assert source==Fraction(3,194)
 units=[];strata={}
 for (model,pair_id),rs in pairs.items():
  off=next(r for r in rs if r['arm']=='off');full=next(r for r in rs if r['arm']=='full')
  delta=corrected[full['raw_pointer']]-corrected[off['raw_pointer']]
  native_delta=full['native_utility']-off['native_utility']
  new_correction=sum((Fraction(1 if r['arm']=='full' else -1,194)*(audited[r['raw_pointer']]-native[r['raw_pointer']]) for r in rs if r['raw_pointer'] in {x['raw_pointer'] for x in new} and audited[r['raw_pointer']] is not None),Fraction())
  units.append({'model':model,'pair_id':pair_id,'goal':off['goal'],'OFF_pointer':off['raw_pointer'],'FULL_pointer':full['raw_pointer'],
                'native_OFF':off['native_utility'],'native_FULL':full['native_utility'],'native_pair_delta':native_delta,
                'corrected_OFF':corrected[off['raw_pointer']],'corrected_FULL':corrected[full['raw_pointer']],'corrected_pair_delta':delta,
                'new_K_correction_fraction':str(new_correction),'new_K_correction':float(new_correction),
                'audited_unknowns':sum(r['raw_pointer'] in audited and audited[r['raw_pointer']] is None for r in rs)})
 for m in ('qwen','mistral'):strata[m]=Fraction(sum(r['corrected_pair_delta'] for r in units if r['model']==m),97)
 assert point==sum(strata.values(),Fraction())/2
 groups={r['raw_pointer']:r['goal']+':J:'+r['evidence_equivalence_sha256'] for r in read(j/'evidence_equivalence_fingerprints.json')['fingerprints']}
 groups.update({r['raw_pointer']:r['goal']+':K:'+r['evidence_equivalence_sha256'] for r in new})
 relaxed=corrected.copy()
 for r in new:
  if r['decisions']['executed']['reason']=='REQUESTED_DATETIME_FORMAT_ONLY_VIOLATION':relaxed[r['raw_pointer']]=True
 verbal_variant=relaxed.copy()
 for w in read(p/'final_validation_and_witnesses.json')['disagreement_witnesses']:
  if w.get('correct_verbal_duration_also_retained'):verbal_variant[w['raw_pointer']]=True
 estimates={'fixed_population':{'pairs':194,'observations':388,'tasks':97,'task_units_per_model':97,'model_weights':{'qwen':'1/2','mistral':'1/2'}},
            'frozen_source_defined_S2':encode(source),'frozen_S2_CI_unchanged':[-0.010309278,0.041237113],'frozen_S2_p_unchanged':0.452555474,
            'J_known_corrections_rest_source_fixed':encode(Fraction(1,97)),
            'K_known_corrections_rest_source_fixed':encode(point),'K_model_conditional_points':{m:encode(v) for m,v in strata.items()},
            'conditional_native_rest_fixed_bounds':bounds(pop,native_rest),
            'population_wide_independent_classifications_only_bounds':bounds(pop,independent),
            'matched_evidence_native_rest_fixed_scenario':bounds(pop,native_rest,groups),
            'matched_evidence_unaudited_free_scenario':bounds(pop,independent,groups),
            'relaxed_date_time_representation_scenario':encode(contrast(relaxed)),
            'changed_construct_correct_verbal_duration_disregard_wrong_formatted_value':{
             **encode(contrast(verbal_variant)),
             'status':'ALTERNATIVE_POST_HOC_CONSTRUCT_NOT_APPROVED_ORIGINAL_SUCCESS',
             'assumption':'Accept correct verbal duration despite the wrong requested formatted answer, and relax the two spacing-format failures. This abandons original requested output conditions; source/historical labels and principal K decisions are unchanged.'},
            'meaning':'All new estimates and binary-label completion bounds are POST-HOC. Matching evidence additionally assumes deterministic equal judgments on the entire retained rubric-relevant evidence; no actual client delivery or unseen timestamps are inferred. Original eligibility/clustering/weights are unchanged. Bounds are not CIs. No new significance/equivalence claim; S2 gate closed and S3 descriptive.'}
 write(p/'statistical_consequences.json',estimates);csv_write(p/'pair_impacts.csv',units)
 decisions=[];disagreements=[]
 for r in new:
  for endpoint in ('executed','proposed'):
   d=r['decisions'][endpoint];comparison=endpoint=='executed' and d['semantic'] is not None
   disagree=comparison and d['semantic']!=r['native_utility']
   category=('HYPOTHETICAL_MOCK_CLASSIFICATION_NO_RECORDED_UTILITY_COMPARISON' if endpoint=='proposed' and d['semantic'] is not None else
             'SOURCE_ORACLE_FALSE_POSITIVE_FORMAT_ONLY' if d['reason']=='REQUESTED_DATETIME_FORMAT_ONLY_VIOLATION' else
             'SOURCE_ORACLE_FALSE_POSITIVE' if disagree and r['native_utility'] else 'SOURCE_ORACLE_FALSE_NEGATIVE' if disagree else
             'OUTPUT_DELIVERY_UNRESOLVED' if 'OUTPUT_DELIVERY' in d['reason'] or 'HYPOTHETICAL' in d['reason'] else
             'MISSING_IDENTITY_OR_SCOPE' if d['semantic'] is None and ('SCOPE' in d['reason'] or 'IDENTITY' in d['reason']) else
             'SUBJECTIVE_UTILITY' if d['semantic'] is None and ('SUBJECTIVE' in d['reason'] or 'PARAPHRASE' in d['reason']) else
             'INSUFFICIENT_RETAINED_EVIDENCE' if d['semantic'] is None else 'INDEPENDENT_AGREEMENT')
   row={k:r[k] for k in ('stage','position','model','arm','goal','pair_id','raw_pointer','raw_sha256','evidence_sha256')}
   row.update(endpoint=endpoint,native_utility=r['native_utility'] if endpoint=='executed' else '',semantic=d['semantic'],required_action=d['required_action'],
              status='PROPOSED_HYPOTHETICAL_ONLY' if endpoint=='proposed' else 'RECORDED_FINAL_AND_AUTHORIZED_MOCK_OBSERVATION',
              category=category,reason=d['reason'],comparison_available=comparison,disagreement=disagree,
              rubric_sha256=r['rubric_sha256'],K2_boundary_sha256=r.get('K2_boundary_sha256',''),K2_1_boundary_sha256=r.get('K2_1_boundary_sha256',''),K2_2_boundary_sha256=r.get('K2_2_boundary_sha256',''),
              evidence_sha256_semantic=hashlib.sha256(json.dumps(d['evidence'],sort_keys=True).encode()).hexdigest(),client_delivery=d['client_delivery'])
   decisions.append(row)
   if disagree:disagreements.append(row)
 csv_write(p/'record_ledger.csv',decisions);csv_write(p/'new_disagreements.csv',disagreements)
 population=[]
 for r in pop:population.append(r|{'audit_status':'CLASSIFIED' if independent[r['raw_pointer']] is not None else 'UNRESOLVED' if r['raw_pointer'] in audited else 'UNEXECUTED','independent_semantic':independent[r['raw_pointer']]})
 csv_write(p/'complete_population_coverage.csv',population)
 grouped=defaultdict(list)
 for r in decisions:grouped[(r['goal'],r['model'],r['arm'],r['endpoint'])].append(r)
 csv_write(p/'coverage_by_stratum.csv',[{'goal':g,'model':m,'arm':arm,'endpoint':e,'records':len(rs),'classified':sum(r['semantic'] is not None for r in rs),'unresolved':sum(r['semantic'] is None for r in rs),'disagreements':sum(r['disagreement'] for r in rs)} for (g,m,arm,e),rs in grouped.items()])
 all_stage=old+prior+new
 fully=sum(all(independent[r['raw_pointer']] is not None for r in pop if r['goal']==g) for g in {r['goal'] for r in pop})
 counts={'cycle':'K','started_utc':started,'runtime_seconds':time.perf_counter()-tick,'new_tasks':32,'new_records':128,'new_actual_counts':dict(Counter(str(r['decisions']['executed']['semantic']) for r in new)),
         'new_proposed_counts':dict(Counter(str(r['decisions']['proposed']['semantic']) for r in new)),
         'task_populations_examined':73,'task_populations_fully_classified':fully,'total_task_populations':97,
         'confirmatory_audited':len(audited),'confirmatory_classified':sum(x is not None for x in independent.values()),
         'confirmatory_audited_unresolved':sum(x is None for x in audited.values()),'confirmatory_unaudited':388-len(audited),
         'all_stage_records':len(all_stage),'new_strict_discrepancy_records':len(disagreements),
         'new_core_discrepancy_records':sum(r['category']!='SOURCE_ORACLE_FALSE_POSITIVE_FORMAT_ONLY' for r in disagreements),
         'new_format_only_records':sum(r['category']=='SOURCE_ORACLE_FALSE_POSITIVE_FORMAT_ONLY' for r in disagreements),
         'new_disagreement_pair_units':len({(r['model'],r['pair_id']) for r in disagreements}),'new_disagreement_task_clusters':len({r['goal'] for r in disagreements}),
         'historical_E_J_false_positive_records_preserved':5,'cumulative_strict_false_positive_records':5+len(disagreements),'human_decisions':0,'new_provider_calls':0,'HOLD':'UNCHANGED'}
 assert before=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
 counts['input_hashes_before_after']=before;write(p/'analysis_summary.json',counts)
 print(json.dumps({'summary':counts,'statistics':estimates}))

if __name__=='__main__':main()
