"""Exact fixed-population L sensitivities. No frozen analyzer is executed."""
from __future__ import annotations
import argparse,csv,datetime as dt,gzip,hashlib,json,pathlib,time
from collections import Counter,defaultdict
from fractions import Fraction
from analyze_benign_cycle_k import bounds

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def zipped(p):return [json.loads(s) for s in gzip.decompress(p.read_bytes()).decode().splitlines()]
def enc(v):return {'fraction':str(v),'estimate':float(v)}
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def csvwrite(p,rows):
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def boolean(s):return True if s=='True' else False if s=='False' else None
def barrier(reason,goal=None):
 if reason=='MISSING_IDENTITY_OR_SCOPE':return 'MISSING_EVIDENCE' if goal=='banking/user_task_9' else 'PENDING_HUMAN'
 if reason=='REUSED_I_REQUIRED_ACTION_AND_NO_OBSERVED_EXTRA_MUTATOR':return 'PENDING_HUMAN'
 if any(k in reason for k in ('READ_SCOPE','READ_STATE_SCOPE','SCOPE_ADJUDICATION','BOOKING','REPRESENTATION_AMBIGUOUS','CONTRACT_AMBIGUITY','UNPARSED','REVIEW_PENDING','TIME_AVAILABILITY')):return 'PENDING_HUMAN'
 if any(k in reason for k in ('AUTHENTICAT','IDENTIT','MISSING_HISTORICAL','DELIVERY','HYPOTHETICAL','BOOKING','RESET_','DEADLINE')):return 'MISSING_EVIDENCE'
 if any(k in reason for k in ('SUBJECTIVE','QUALITY','REVIEWS','TRADEOFF','SCOPE','PENDING_HUMAN','SUMMARY','ACTIVIT')):return 'PENDING_HUMAN'
 return 'PENDING_HUMAN'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit-dir',type=pathlib.Path,required=True);a=ap.parse_args();p=a.audit_dir;k=p.parent/'cycle_k_20261012';j=p.parent/'cycle_j_20261012'
 inputs=[p/'record_audit_principal.jsonl.gz',k/'complete_population_coverage.csv',j/'evidence_equivalence_fingerprints.json',k/'record_audit_principal.jsonl.gz']
 before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs};started=dt.datetime.now(dt.timezone.utc).isoformat();tick=time.perf_counter()
 pop=list(csv.DictReader((k/'complete_population_coverage.csv').open(encoding='utf-8')));new=zipped(inputs[0]);oldk=zipped(inputs[3]);assert len(pop)==388 and len(new)==96
 native={r['raw_pointer']:boolean(r['native_utility']) for r in pop};previous={r['raw_pointer']:boolean(r['independent_semantic']) for r in pop if r['audit_status']!='UNEXECUTED'}
 current=dict(previous);current.update({r['raw_pointer']:r['decisions']['executed']['semantic'] for r in new})
 assert len(previous)==292 and sum(v is not None for v in previous.values())==225
 assert len(current)==388 and not ({r['raw_pointer'] for r in new}&set(previous))
 pairs=defaultdict(list)
 for r in pop:pairs[(r['model'],r['pair_id'])].append(r)
 assert len(pairs)==194 and Counter(m for m,_ in pairs)=={'qwen':97,'mistral':97}
 assert all(len(rs)==2 and {r['arm'] for r in rs}=={'off','full'} for rs in pairs.values())
 for r in pop:r['native_utility']=native[r['raw_pointer']]
 corrected={key:current[key] if current[key] is not None else val for key,val in native.items()}
 def contrast(labels):return sum((Fraction(1 if r['arm']=='full' else -1,194)*labels[r['raw_pointer']] for r in pop),Fraction())
 original=contrast(native);point=contrast(corrected);assert original==Fraction(3,194)
 units=[];newptr={r['raw_pointer'] for r in new}
 for (m,pair),rs in pairs.items():
  off=next(r for r in rs if r['arm']=='off');full=next(r for r in rs if r['arm']=='full')
  delta=corrected[full['raw_pointer']]-corrected[off['raw_pointer']];source=full['native_utility']-off['native_utility']
  inc=sum((Fraction(1 if r['arm']=='full' else -1,194)*(current[r['raw_pointer']]-native[r['raw_pointer']]) for r in rs if r['raw_pointer'] in newptr and current[r['raw_pointer']] is not None),Fraction())
  units.append({'model':m,'pair_id':pair,'goal':off['goal'],'OFF_pointer':off['raw_pointer'],'FULL_pointer':full['raw_pointer'],'native_OFF':off['native_utility'],'native_FULL':full['native_utility'],'native_pair_delta':source,'corrected_OFF':corrected[off['raw_pointer']],'corrected_FULL':corrected[full['raw_pointer']],'corrected_pair_delta':delta,'new_L_correction_fraction':str(inc),'unknown_endpoints':sum(current[r['raw_pointer']] is None for r in rs)})
 strata={m:Fraction(sum(u['corrected_pair_delta'] for u in units if u['model']==m),97) for m in ('qwen','mistral')};assert point==sum(strata.values(),Fraction())/2
 # Independent coefficient enumeration supplies the same ungrouped endpoints.
 fixed=sum((Fraction(1 if r['arm']=='full' else -1,194)*current[r['raw_pointer']] for r in pop if current[r['raw_pointer']] is not None),Fraction())
 lower=fixed-Fraction(sum(current[r['raw_pointer']] is None and r['arm']=='off' for r in pop),194)
 upper=fixed+Fraction(sum(current[r['raw_pointer']] is None and r['arm']=='full' for r in pop),194)
 b=bounds(pop,current);assert b['lower']['fraction']==str(lower) and b['upper']['fraction']==str(upper)
 groups={r['raw_pointer']:r['goal']+':J:'+r['evidence_equivalence_sha256'] for r in read(j/'evidence_equivalence_fingerprints.json')['fingerprints']}
 groups.update({r['raw_pointer']:r['goal']+':K:'+r['evidence_equivalence_sha256'] for r in oldk})
 groups.update({r['raw_pointer']:r['goal']+':L:'+r['evidence_equivalence_sha256'] for r in new})
 statistics={'cycle':'L','status':'POST_HOC','fixed_population':{'pairs':194,'observations':388,'tasks':97,'task_pairs_per_model':97,'weights':{'qwen':'1/2','mistral':'1/2'}},'frozen_source_defined_S2':enc(original),'frozen_CI_unchanged':[-0.010309278,0.041237113],'frozen_p_unchanged':0.452555474,'historical_J_corrections_rest_native_fixed':enc(Fraction(1,97)),'historical_K_corrections_rest_native_fixed':enc(Fraction(1,194)),'L_known_corrections_other_source_labels_fixed':enc(point),'L_conditional_model_strata':{m:enc(v) for m,v in strata.items()},'audited_unresolved_completion_bounds':b,'population_wide_completion_bounds':b,'matching_evidence_equality_scenario':bounds(pop,current,groups),'independent_ungrouped_coefficient_witness':{'lower':enc(lower),'upper':enc(upper)},'meaning':'Every observation is now examined under bounded criteria; unresolved labels remain free, so audited and population-wide bounds coincide. Matching retained evidence additionally assumes deterministic equal adjudication, not missing client delivery or external preference facts. All new calculations are POST-HOC binary-label completion bounds, not CIs. No new p-value, significance, equivalence or no-cost claim. S2 gate closed; S3 descriptive.'}
 write(p/'statistical_consequences.json',statistics);csvwrite(p/'pair_impacts.csv',units)
 rows=[];disagreements=[]
 for r in new:
  for endpoint in ('executed','proposed'):
   d=r['decisions'][endpoint];comparison=endpoint=='executed' and d['semantic'] is not None;disagree=comparison and d['semantic']!=r['native_utility']
   category='SOURCE_ORACLE_FALSE_POSITIVE' if disagree and r['native_utility'] else 'SOURCE_ORACLE_FALSE_NEGATIVE' if disagree else 'HYPOTHETICAL_NO_RECORDED_UTILITY_COMPARISON' if endpoint=='proposed' else 'INDEPENDENT_AGREEMENT' if comparison else barrier(d['reason'])
   x={key:r[key] for key in ('stage','position','goal','model','arm','pair_id','raw_pointer','raw_sha256','evidence_sha256')}
   x.update(endpoint=endpoint,native_utility=r['native_utility'] if endpoint=='executed' else '',semantic=d['semantic'],reason=d['reason'],category=category,comparison_available=comparison,disagreement=disagree,execution_status=d['execution_status'],client_delivery=d['client_delivery'],rubric_sha256=r['rubric_sha256'],L2_boundary_sha256=r.get('L2_boundary_sha256',''),L3_boundary_sha256=r.get('L3_boundary_sha256',''),L4_boundary_sha256=r.get('L4_boundary_sha256',''),decision_evidence_sha256=hashlib.sha256(json.dumps(d['evidence'],sort_keys=True).encode()).hexdigest())
   rows.append(x)
   if disagree:disagreements.append(x)
 csvwrite(p/'record_ledger.csv',rows);csvwrite(p/'new_disagreements.csv',disagreements)
 population=[]
 for r in pop:population.append(r|{'audit_status':'CLASSIFIED' if current[r['raw_pointer']] is not None else 'UNRESOLVED','independent_semantic':current[r['raw_pointer']]})
 csvwrite(p/'complete_population_coverage.csv',population)
 taskrows=[]
 for goal in sorted({r['goal'] for r in pop}):
  rs=[r for r in population if r['goal']==goal];taskrows.append({'goal':goal,'original_observations':4,'examined':4,'classified':sum(r['independent_semantic'] is not None for r in rs),'unresolved':sum(r['independent_semantic'] is None for r in rs),'unaudited':0,'cycle_L_task':goal in {r['goal'] for r in new},'fully_classified_retained_contexts':all(r['independent_semantic'] is not None for r in rs)})
 csvwrite(p/'task_coverage.csv',taskrows)
 grouped=defaultdict(list)
 for r in rows:grouped[(r['goal'],r['model'],r['arm'],r['endpoint'])].append(r)
 csvwrite(p/'coverage_by_stratum.csv',[{'goal':g,'model':m,'arm':arm,'endpoint':ep,'records':len(rs),'classified':sum(r['semantic'] is not None for r in rs),'unresolved':sum(r['semantic'] is None for r in rs),'disagreements':sum(r['disagreement'] for r in rs)} for (g,m,arm,ep),rs in grouped.items()])
 csvwrite(p/'remaining_barriers.csv',[r|{'stopping_state':barrier(r['reason'])} for r in rows if r['endpoint']=='executed' and r['semantic'] is None])
 reasons={}
 for folder,name,mode in [('cycle_j_20261012','principal_record_decisions.json.gz','json'),('cycle_k_20261012','record_audit_principal.jsonl.gz','lines'),('cycle_l_20261015','record_audit_principal.jsonl.gz','lines')]:
  text=gzip.decompress((p.parent/folder/name).read_bytes()).decode();rs=json.loads(text) if mode=='json' else [json.loads(line) for line in text.splitlines()]
  for r in rs:reasons[r['raw_pointer']]={'reason':r['decisions']['executed']['reason'],'source_cycle':folder}
 for r in json.loads(gzip.decompress((j/'prior_reuse_overlay.json.gz').read_bytes()).decode()):
  if r['stage']=='confirmatory':reasons[r['raw_pointer']]={'reason':r['J_decision']['reason'],'source_cycle':'J_reused_I'}
 population_barriers=[]
 for r in population:
  if r['independent_semantic'] is None:
   data=r|reasons[r['raw_pointer']];data['stopping_state']=barrier(data['reason'],data['goal']);data['classification_note']='Primary handoff category only; semantic and missing-fact dependencies may overlap. No label or rule is approved by this categorization.';population_barriers.append(data)
 csvwrite(p/'population_barriers.csv',population_barriers)
 totalunknown=sum(v is None for v in current.values())
 counts={'started_utc':started,'runtime_seconds':time.perf_counter()-tick,'new_tasks':24,'new_original_confirmatory_observations':96,'new_original_pairs':48,'new_executed_counts':dict(Counter(str(r['decisions']['executed']['semantic']) for r in new)),'new_hypothetical_counts':dict(Counter(str(r['decisions']['proposed']['semantic']) for r in new)),'population_task_counts':{'examined':97,'fully_classified_retained_contexts':sum(r['fully_classified_retained_contexts'] for r in taskrows),'partially_classified_or_unresolved':sum(not r['fully_classified_retained_contexts'] for r in taskrows)},'population_observation_counts':{'examined':388,'classified':388-totalunknown,'unresolved':totalunknown,'unaudited':0},'unresolved_arms':dict(Counter(r['arm'] for r in population if r['independent_semantic'] is None)),'new_disagreement_records':len(disagreements),'new_false_positives':sum(r['category']=='SOURCE_ORACLE_FALSE_POSITIVE' for r in disagreements),'new_false_negatives':sum(r['category']=='SOURCE_ORACLE_FALSE_NEGATIVE' for r in disagreements),'new_disagreement_pairs':len({(r['model'],r['pair_id']) for r in disagreements}),'new_disagreement_tasks':len({r['goal'] for r in disagreements}),'historical_false_positives_preserved':10,'historical_format_only_subset':2,'cumulative_false_positive_records':10+sum(r['category']=='SOURCE_ORACLE_FALSE_POSITIVE' for r in disagreements),'cumulative_false_negative_records':sum(r['category']=='SOURCE_ORACLE_FALSE_NEGATIVE' for r in disagreements),'remaining_primary_barrier_counts':dict(Counter(r['stopping_state'] for r in population_barriers)),'human_decisions':0,'provider_calls':0,'HOLD':'UNCHANGED','inputs_before_after':before}
 assert before=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs};write(p/'analysis_summary.json',counts);print(json.dumps({'summary':counts,'statistics':statistics}))
if __name__=='__main__':main()
