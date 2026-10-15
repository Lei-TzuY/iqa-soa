"""Resolve only a necessary-condition lattice bug on four saved read-alias records."""
import argparse,copy,datetime as dt,gzip,hashlib,json,pathlib,time
from benign_construct_cycle_k_v2_2 import evaluate
from benign_construct_cycle_j import digest,require
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser()
 for n in ('prior','private-contexts','spec','boundary','output'):ap.add_argument('--'+n,type=pathlib.Path,required=True)
 ap.add_argument('--evaluator-sha256',required=True);ap.add_argument('--boundary-sha256',required=True);a=ap.parse_args()
 require(not a.output.exists(),'fresh output required');require(sha(a.boundary)==a.boundary_sha256,'boundary changed')
 require(sha(pathlib.Path(__file__).with_name('benign_construct_cycle_k_v2_2.py'))==a.evaluator_sha256,'evaluator changed')
 bound={p:sha(p) for p in (a.prior,a.private_contexts,a.spec,a.boundary,pathlib.Path(__file__).with_name('benign_construct_cycle_k_v2_2.py'))}
 rows=[json.loads(l) for l in gzip.decompress(a.prior.read_bytes()).decode().splitlines()]
 cs={r['pointer']:r['contexts'] for r in [json.loads(l) for l in gzip.decompress(a.private_contexts.read_bytes()).decode().splitlines()]}
 spec=json.loads(a.spec.read_text(encoding='utf-8'));changes=[];selected=0;start=dt.datetime.now(dt.timezone.utc).isoformat();tick=time.perf_counter()
 for r in rows:
  if r['goal']!='workspace/user_task_39':continue
  selected+=1
  for c in cs[r['raw_pointer']]:
   old=copy.deepcopy(r['decisions'][c['endpoint']]);before=digest(c);new=evaluate(c,spec['rules'][r['goal']]);require(digest(c)==before,'context mutated')
   require(evaluate(copy.deepcopy(c),spec['rules'][r['goal']])==new,'fresh copy/order differs')
   r['decisions'][c['endpoint']]=new
   if new!=old:changes.append({'raw_pointer':r['raw_pointer'],'raw_sha256':r['raw_sha256'],'endpoint':c['endpoint'],'old_semantic':old['semantic'],'new_semantic':new['semantic'],'reason':new['reason'],'context_sha256':before})
  r['K2_2_boundary_sha256']=a.boundary_sha256
 require(selected==4,'four original read-alias records required');require(all(sha(p)==h for p,h in bound.items()),'saved input changed')
 a.output.mkdir()
 with gzip.GzipFile(filename=str(a.output/'record_audit_principal.jsonl.gz'),mode='wb',mtime=0) as f:
  for r in rows:f.write((json.dumps(r,sort_keys=True)+'\n').encode())
 summary={'cycle':'K','version':'K2.2','started_utc':start,'runtime_seconds':time.perf_counter()-tick,'affected_original_records':selected,'contexts':8,'fresh_copy_and_immutability_checks':16,'changes':changes,'input_hashes_before_after':{str(p):h for p,h in bound.items()},'new_mock_tool_calls':0,'new_provider_calls':0,'human_decisions':0}
 (a.output/'final_execution_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in summary.items() if k!='input_hashes_before_after'}))
if __name__=='__main__':main()
