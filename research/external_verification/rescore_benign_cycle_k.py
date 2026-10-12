"""K2 scoring on saved immutable K1 contexts; no mock tools or model calls."""
from __future__ import annotations
import argparse
import copy
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import pathlib
import socket
import time
from collections import Counter
from benign_construct_cycle_k_v2 import evaluate
from benign_construct_cycle_j import digest, require

AFFECTED={'READ_THEN_INVITE','REUNION_EVENT','HIKE_EVENT','HOBBY_POST',
          'SUNDAY_RESTAURANT','MONDAY_RESTAURANT_REVIEWS','SUV_RECOMMENDATION','EV_WEEK','TWO_CARS',
          'INVITEE_EMAILS','NEXT_YOGA','MEETING_GAP','TODAY_COUNT','SHARED_IDS','HAWAII_ACTIVITY','SHOW_UNREAD'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def obj(p):return json.loads(p.read_text(encoding='utf-8'))
def records(p):return [json.loads(x) for x in gzip.decompress(p.read_bytes()).decode().splitlines()]
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')

def main():
 ap=argparse.ArgumentParser()
 for name in ('prior','spec','boundary','output'):ap.add_argument('--'+name,type=pathlib.Path,required=True)
 ap.add_argument('--boundary-sha256',required=True);ap.add_argument('--code-sha256',required=True);ap.add_argument('--evaluator-sha256',required=True)
 a=ap.parse_args();out=a.output.resolve();require(not out.exists(),'fresh isolated output required')
 original=records(a.prior/'record_audit.jsonl.gz');private=records(a.prior/'private_contexts_DO_NOT_PUBLISH.jsonl.gz')
 source_summary=obj(a.prior/'execution_summary.json');spec=obj(a.spec)
 bound={a.boundary:a.boundary_sha256,pathlib.Path(__file__):a.code_sha256,
        pathlib.Path(__file__).with_name('benign_construct_cycle_k_v2.py'):a.evaluator_sha256,
        a.spec:source_summary['spec_sha256'],a.prior/'record_audit.jsonl.gz':source_summary['artifact_sha256']['record_audit.jsonl.gz'],
        a.prior/'private_contexts_DO_NOT_PUBLISH.jsonl.gz':source_summary['artifact_sha256']['private_contexts_DO_NOT_PUBLISH.jsonl.gz']}
 require(all(sha(p)==h for p,h in bound.items()),'saved input/code hash differs')
 def deny(*_a,**_kw):raise RuntimeError('network/original-oracle forbidden')
 socket.socket.connect=socket.socket.connect_ex=socket.create_connection=deny
 tick=time.perf_counter();started=dt.datetime.now(dt.timezone.utc).isoformat()
 contexts={r['pointer']:r['contexts'] for r in private};results=[];diff=[];checks=Counter()
 reversed_checks=[]
 for r in original:
  new=copy.deepcopy(r);kind=spec['rules'][r['goal']]['kind']
  for c in contexts[r['raw_pointer']]:
   before=digest(c);label=evaluate(c,spec['rules'][r['goal']]);require(digest(c)==before,'context mutated')
   old=r['decisions'][c['endpoint']]
   if kind not in AFFECTED:
    require(label==old,'unaffected context changed');checks['unaffected_context_checks']+=1
   else:checks['affected_contexts_evaluated']+=1
   new['decisions'][c['endpoint']]=label
   if label!=old:
    diff.append({k:r[k] for k in ('stage','position','model','arm','goal','raw_pointer','raw_sha256','evidence_sha256')}|
                {'endpoint':c['endpoint'],'old_K1_semantic':old['semantic'],'new_K2_semantic':label['semantic'],
                 'old_K1_reason':old['reason'],'new_K2_reason':label['reason'],'saved_context_sha256':before,
                 'new_evidence_sha256':digest(label['evidence']),'K1_rubric_sha256':source_summary['spec_sha256'],
                 'K2_boundary_sha256':a.boundary_sha256})
   reversed_checks.append((c,copy.deepcopy(label),r['goal']));checks['immutability_checks']+=1
  new['K2_boundary_sha256']=a.boundary_sha256;results.append(new)
 for c,label,goal in reversed(reversed_checks):
  require(evaluate(c,spec['rules'][goal])==label,'record/endpoint order changes scoring');checks['reverse_order_checks']+=1
 require(all(sha(p)==h for p,h in bound.items()),'input changed during saved scoring')
 out.mkdir()
 with gzip.GzipFile(filename=str(out/'record_audit_final.jsonl.gz'),mode='wb',mtime=0) as f:
  for r in results:f.write((json.dumps(r,sort_keys=True)+'\n').encode())
 with (out/'scoring_differential.csv').open('w',newline='',encoding='utf-8') as f:
  writer=csv.DictWriter(f,fieldnames=list(diff[0]));writer.writeheader();writer.writerows(diff)
 summary={'cycle':'K','version':'K2','started_utc':started,'runtime_seconds':time.perf_counter()-tick,
          'records':len(results),'affected_records':sum(spec['rules'][r['goal']]['kind'] in AFFECTED for r in results),
          'checks':dict(checks),'differential_rows':len(diff),'actual_counts':dict(Counter(str(r['decisions']['executed']['semantic']) for r in results)),
          'proposed_counts':dict(Counter(str(r['decisions']['proposed']['semantic']) for r in results)),
          'semantic_label_changes':sum(r['old_K1_semantic']!=r['new_K2_semantic'] for r in diff),
          'input_hashes_before_after':{str(p):h for p,h in bound.items()},'new_mock_tool_calls':0,'new_provider_calls':0,'original_oracle_calls':0,'human_reviews':0,
          'artifact_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file()}}
 write(out/'rescore_execution_summary.json',summary)
 print(json.dumps({k:v for k,v in summary.items() if k not in ('input_hashes_before_after','artifact_sha256')}))

if __name__=='__main__':main()
