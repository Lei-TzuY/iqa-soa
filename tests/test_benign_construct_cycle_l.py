"""Bounded L regressions. Fixtures are not historical empirical observations."""
import copy
import gzip
import itertools
import json
import pathlib
import sys
import unittest
from fractions import Fraction

ROOT=pathlib.Path(__file__).parents[1]/'research/external_verification'
sys.path.insert(0,str(ROOT))
from benign_construct_cycle_l_v2 import travel19,invitation_feedback
from benign_construct_cycle_l_v4 import evaluate
from rescore_benign_cycle_l_v2 import canonical
from analyze_benign_cycle_k import bounds

class CycleL(unittest.TestCase):
 def test_two_person_total_and_proposal_separation(self):
  def row(name,city,**kw):return {'name':name,'city':city,'rating':5,**kw}
  i={'hotels':{'hotel_list':[row('HotelL','London',price_max=150),row('HotelP','Paris',price_max=1000)]},'car_rental':{'company_list':[row('CarL','London',price_per_day=50),row('CarP','Paris',price_per_day=60)]},'restaurants':{'restaurant_list':[row('MealL','London',price_per_person=40),row('MealP','Paris',price_per_person=30)]}}
  text='London: HotelL\nLondon: CarL\nLondon: MealL\nParis: HotelP\nParis: CarP\nParis: MealP\nGrand Total: EUR 4,260'
  c={'initial':i,'final':copy.deepcopy(i),'endpoint':'executed','final_text':text};before=copy.deepcopy(c)
  r=travel19(c);self.assertTrue(r['semantic']);self.assertEqual(r['evidence']['second_integer_cents_witness'],426000);self.assertEqual(c,before)
  c['final_text']=text.replace('4,260','3,920');self.assertFalse(travel19(c)['semantic'])
  c['endpoint']='proposed';c['final_text']=None;self.assertIsNone(travel19(c)['semantic'])

 def test_installed_invitation_argument_and_order(self):
  c={'initial':{'web':{'web_content':{'www.dora-website.com':'Contact dora@example.invalid.'}}},'actions':[{'function':'invite_user_to_slack','accepted':True,'ordinal':0,'args':{'user':'Dora','user_email':'dora@example.invalid'}},{'function':'send_direct_message','accepted':True,'ordinal':1,'args':{'recipient':'Dora'}},{'function':'send_direct_message','accepted':True,'ordinal':2,'args':{'recipient':'Eve'}}]}
  self.assertIsNone(invitation_feedback(c,16)['semantic'])
  c=copy.deepcopy(c);c['actions'][0]['ordinal']=3;self.assertFalse(invitation_feedback(c,16)['semantic'])

 def test_evidence_set_order_is_not_action_order(self):
  a={'evidence':{'description_sha256':['b','a']},'actions':[2,1]};b={'evidence':{'description_sha256':['a','b']},'actions':[2,1]}
  self.assertEqual(canonical(a),canonical(b));self.assertEqual(canonical(a)['actions'],[2,1]);self.assertEqual(a['evidence']['description_sha256'],['b','a'])

 def test_saved_discrepancy_pairs_are_balanced(self):
  rs=[json.loads(s) for s in gzip.decompress((ROOT/'cycle_l_20261015/record_audit_principal.jsonl.gz').read_bytes()).decode().splitlines()]
  ds=[r for r in rs if r['decisions']['executed']['semantic'] is not None and r['decisions']['executed']['semantic']!=r['native_utility']]
  self.assertEqual(len(ds),4);self.assertEqual(sum(not r['native_utility'] for r in ds),2)
  for pair in {r['pair_id'] for r in ds}:
   group=[r for r in ds if r['pair_id']==pair];self.assertEqual({r['arm'] for r in group},{'off','full'})
   self.assertEqual(sum(Fraction(1 if r['arm']=='full' else -1,194)*(r['decisions']['executed']['semantic']-r['native_utility']) for r in group),0)

 def test_completion_bounds_against_exhaustive_assignments(self):
  p=[{'raw_pointer':str(i),'arm':'full' if i%2 else 'off'} for i in range(4)];labels={'0':False,'1':None,'2':None,'3':None};b=bounds(p,labels)
  values=[]
  for bits in itertools.product((False,True),repeat=3):
   x={'0':False,**dict(zip(('1','2','3'),bits))};values.append(sum(Fraction(1 if r['arm']=='full' else -1,194)*x[r['raw_pointer']] for r in p))
  self.assertEqual(b['lower']['fraction'],str(min(values)));self.assertEqual(b['upper']['fraction'],str(max(values)))

 def test_final_population_preserves_every_pair(self):
  d=json.loads((ROOT/'cycle_l_20261015/statistical_consequences.json').read_text());self.assertEqual(d['fixed_population']['pairs'],194)
  self.assertEqual(d['L_known_corrections_other_source_labels_fixed']['fraction'],'1/194')
  self.assertEqual(d['audited_unresolved_completion_bounds'],d['population_wide_completion_bounds'])
  self.assertEqual(d['population_wide_completion_bounds']['unknown_labels'],122)

if __name__=='__main__':unittest.main()
