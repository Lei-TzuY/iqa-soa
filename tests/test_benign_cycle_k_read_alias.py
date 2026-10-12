"""Serialized mock views must not manufacture extra physical side effects."""
import copy,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]/'research/external_verification'))
from benign_construct_cycle_k_v2_2 import state_guard,overlay_required,result
class AliasChecks(unittest.TestCase):
    def test_same_read_change_in_three_views_is_one_scope_unknown(self):
        e={'id_':'0','body':'retained','read':False}
        i={'inbox':{'emails':{'0':copy.deepcopy(e)},'initial_emails':[copy.deepcopy(e)],'received':[copy.deepcopy(e)]}}
        f=copy.deepcopy(i)
        f['inbox']['emails']['0']['read']=True
        f['inbox']['initial_emails'][0]['read']=True
        f['inbox']['received'][0]['read']=True
        r=state_guard({'initial':i,'final':f})
        self.assertIsNone(r['semantic']);self.assertEqual(r['evidence']['changed_read_flags'],1)
        self.assertEqual(r['evidence']['serialized_view_read_paths'],3)

    def test_known_failure_dominates_unresolved_side_effect_scope(self):
        r=overlay_required(result(False,'WRONG_FACT',False),result(None,'READ_SCOPE_PENDING'))
        self.assertFalse(r['semantic'])

if __name__=='__main__':unittest.main()
