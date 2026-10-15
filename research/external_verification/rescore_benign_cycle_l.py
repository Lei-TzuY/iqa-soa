"""Targeted saved-context L2 rescore and complete immutable-order validation."""
from __future__ import annotations
import argparse,copy,csv,datetime as dt,gzip,hashlib,json,pathlib,socket,time
from collections import Counter
from benign_construct_cycle_j import digest, require
from benign_construct_cycle_l_v2 import evaluate

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=pathlib.Path,required=True);ap.add_argument('--spec',type=pathlib.Path,required=True);ap.add_argument('--boundary',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args()
 require(not a.output.exists(),'fresh output required')
 boundary=json.loads(a.boundary.read_text(encoding='utf-8'));require(sha(pathlib.Path(__file__).with_name('benign_construct_cycle_l_v2.py'))==boundary['evaluator_sha256'],'evaluator binding differs')
 require(sha(a.spec)==boundary['L1_sha256'],'L1 binding differs')
 def deny(*args,**kwargs):raise RuntimeError('network denied')
 socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny
 paths=[a.input/'record_audit.jsonl.gz',a.input/'private_contexts_DO_NOT_PUBLISH.jsonl.gz',a.input/'execution_summary.json',a.spec,a.boundary,pathlib.Path(__file__),pathlib.Path(__file__).with_name('benign_construct_cycle_l_v2.py'),pathlib.Path(__file__).with_name('benign_construct_cycle_l.py')]
 before={str(p):sha(p) for p in paths};spec=json.loads(a.spec.read_text(encoding='utf-8'));started=dt.datetime.now(dt.timezone.utc).isoformat();tick=time.perf_counter()
 records=[json.loads(s) for s in gzip.decompress(paths[0].read_bytes()).decode().splitlines()];contexts=[json.loads(s) for s in gzip.decompress(paths[1].read_bytes()).decode().splitlines()]
 changed_goals={'slack/user_task_16','slack/user_task_20','workspace/user_task_13','workspace/user_task_19','workspace/user_task_29','travel/user_task_5','travel/user_task_19'}
 diffs=[];changed=0;targets=0
 for r,p in zip(records,contexts):
  require(r['raw_pointer']==p['pointer'],'record binding differs')
  r['L2_boundary_sha256']=sha(a.boundary)
  if r['goal'] not in changed_goals:continue
  targets+=1
  for original in p['contexts']:
   c=copy.deepcopy(original);h=digest(c);new=evaluate(c,spec['rules'][c['goal']]);require(h==digest(c),'scorer mutated input')
   old=r['decisions'][c['endpoint']]
   diffs.append({'raw_pointer':r['raw_pointer'],'raw_sha256':r['raw_sha256'],'goal':r['goal'],'model':r['model'],'arm':r['arm'],'endpoint':c['endpoint'],'old_semantic':old['semantic'],'new_semantic':new['semantic'],'old_reason':old['reason'],'new_reason':new['reason'],'rubric_sha256':r['rubric_sha256'],'L2_boundary_sha256':r['L2_boundary_sha256']})
   changed+=old['semantic']!=new['semantic'];r['decisions'][c['endpoint']]=new
 for r,p in reversed(list(zip(records,contexts))):
  for original in reversed(p['contexts']):
   c=copy.deepcopy(original);h=digest(c);got=evaluate(c,spec['rules'][c['goal']]);require(got==r['decisions'][c['endpoint']],'order or targeted coverage inconsistency');require(h==digest(c),'input mutated during full validation')
 require(before=={str(p):sha(p) for p in paths},'bound input changed')
 a.output.mkdir()
 with gzip.GzipFile(filename=str(a.output/'record_audit_principal.jsonl.gz'),mode='wb',mtime=0) as f:
  for r in records:f.write((json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n').encode())
 with (a.output/'scoring_differential.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(diffs[0]));w.writeheader();w.writerows(diffs)
 receipt={'started_utc':started,'runtime_seconds':time.perf_counter()-tick,'records':96,'targeted_records':targets,'targeted_contexts':targets*2,'label_changes':changed,'full_reverse_order_and_immutability_checks':192,'new_tool_calls':0,'human_reviews':0,'provider_calls':0,'actual_counts':dict(Counter(str(r['decisions']['executed']['semantic']) for r in records)),'proposed_counts':dict(Counter(str(r['decisions']['proposed']['semantic']) for r in records)),'input_hashes_before_after':before,'artifact_sha256':{p.name:sha(p) for p in a.output.iterdir()}}
 (a.output/'rescore_execution_summary.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in receipt.items() if k not in ('input_hashes_before_after','artifact_sha256')}))
if __name__=='__main__':main()
