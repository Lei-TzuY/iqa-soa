"""Independent rational POST-HOC partial identification, preserving F/G history.

No benchmark security() calls, acquisitions or unknown-label point imputation.
Weights derive from retained pairs, carrier nesting and equal model strata.
"""
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
import time
from collections import Counter, defaultdict
from fractions import Fraction


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    b = p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix == '.gz' else b)


def key(r):
    return r['stage'], int(r['position'])


def goal(r):
    return r['suite'] + '/' + (r.get('goal') or r['injection_task'])


def known(x):
    return isinstance(x, bool)


def number(x):
    return {'fraction': str(x), 'estimate': float(x)}


def weights(metadata, eligibility=None):
    """Independent derivation: model -> goal -> original carrier/seed pairs."""
    pairs = defaultdict(dict)
    for r in metadata:
        if r['stage'] == 'confirmatory':
            k = (r['model'], r['pair_id'])
            require(r['arm'] not in pairs[k], 'duplicate original paired arm')
            pairs[k][r['arm']] = r
    require(len(pairs) == 474, 'original 474 pairs differ')
    groups = defaultdict(list)
    for (model, _), arms in pairs.items():
        require(set(arms) == {'off', 'full'}, 'missing original paired arm')
        off, full = arms['off'], arms['full']
        for f in ['model', 'suite', 'injection_task', 'user_task', 'seed', 'kind', 'cell_id']:
            require(off[f] == full[f], 'pair identity mismatch ' + f)
        if off['kind'] != 'security':
            continue
        if eligibility is not None and (not off['canonical_population'] or goal(off) not in eligibility[model]):
            continue
        groups[(model, goal(off))].append(arms)
    models = sorted({m for m, _ in groups})
    counts = Counter(m for m, _ in groups)
    coeffs = {}
    for (m, g), ps in groups.items():
        w = Fraction(1, len(models) * counts[m] * len(ps))
        for arms in ps:
            for arm, r in arms.items():
                coeffs[key(r)] = {'coefficient': w if arm == 'full' else -w, 'record': r}
    return coeffs, {'original_pairs': len(pairs), 'analysis_pairs': sum(map(len, groups.values())),
        'model_goal_units': len(groups), 'goals_per_model': dict(counts),
        'carrier_seed_pairs_per_unit': sorted(set(map(len, groups.values())))}


def bounds(coeffs, decisions, endpoint):
    fixed = Fraction(); lo = Fraction(); hi = Fraction(); unknown = []
    for k, c in coeffs.items():
        w = c['coefficient']; y = decisions[k][endpoint]
        if known(y):
            fixed += w * int(y)
        else:
            require(y in ('AMBIGUOUS', 'UNOBSERVABLE'), 'invalid unknown outcome')
            lo += min(Fraction(), w); hi += max(Fraction(), w)
            unknown.append({'stage': k[0], 'position': k[1], 'goal': goal(c['record']),
                'model': c['record']['model'], 'arm': c['record']['arm'], 'coefficient': str(w)})
    return {'lower': number(fixed + lo), 'upper': number(fixed + hi), 'unknown_labels': len(unknown),
        'unknown_records': unknown, 'meaning': 'Sharp binary-label completion bounds, not confidence intervals; conditional on retained known semantic labels and frozen eligibility.'}


def tipping(coeffs, decisions, endpoint, upper):
    """Separate question: additional known-label errors needed to reach zero.

    Unknown decisions are already completed to maximize FULL-minus-OFF. This is
    adversarial sensitivity, not observed errors, a probability or a new test.
    """
    helpful = []
    clusters = defaultdict(Fraction)
    for k, c in coeffs.items():
        w = c['coefficient']; y = decisions[k][endpoint]
        if known(y) and ((w > 0 and y is False) or (w < 0 and y is True)):
            helpful.append(abs(w)); clusters[(c['record']['model'], goal(c['record']))] += abs(w)
    def needed(xs):
        s = upper
        if s >= 0:
            return 0
        for n, x in enumerate(sorted(xs, reverse=True), 1):
            s += x
            if s >= 0:
                return n
        return None
    return {'question': 'After maximizing all remaining unknown labels, how many additional presently known labels would need to be wrong to reach a nonnegative contrast?',
        'known_record_label_flips_to_zero': needed(helpful), 'model_goal_clusters_with_arbitrary_helpful_flips_to_zero': needed(list(clusters.values())),
        'upper_start': number(upper), 'assumption': 'Binary adversarial recoding of additional known labels; hypothetical sensitivity only. This does not establish their correctness or independent human validation.'}


def write_csv(p, rows, fields=None):
    fields = fields or list(rows[0])
    buf = io.StringIO(newline=''); w = csv.DictWriter(buf, fieldnames=fields); w.writeheader(); w.writerows(rows)
    data = buf.getvalue().encode()
    p.write_bytes(gzip.compress(data, mtime=0) if p.suffix == '.gz' else data)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--audit-dir', type=pathlib.Path,
        default=pathlib.Path(__file__).parent/'cycle_h_20261010'); args = ap.parse_args()
    h = args.audit_dir; g = h.parent/'cycle_g_20261010'; tick = time.perf_counter()
    bound = {h/'construct_records.jsonl.gz': '17ada6df6efa90b13481528abd6bc76aa793e48e7061c54dae7e169b25f5f4f1',
        h/'execution_summary.json': 'bc7f3982c0a01bfb658e17d7e55677946a8b147a7f3f2895e226db3fa84e7a89',
        h/'frozen_rules_v2.json': 'ec3b81b709c7a4c81203720dbbaa9619f3d49b9cd785d471074885f689667f97',
        g/'original_record_metadata.json.gz': '67700d4a783831cf277374085bfeda8ba591e8b1624a8acec3dfe2837c84132f',
        g/'ambiguities.csv': '839df129be867b04f0c80ebc79fea75ac7d73d24a0a9ff15b50ba890c3ec3368',
        g/'statistical_consequences.json': '7d39650befb155e992b9a88b04fb7052d29cf15cbecc01f319a8d708d14629d4'}
    for p, expected in bound.items():
        require(sha(p) == expected, 'bound input changed: ' + p.name)
    before = {str(p): sha(p) for p in bound}
    g_manifest = load(g/'execution_manifest.json')
    coverage_path = g/'record_semantic_coverage.csv.gz'
    coverage_hash = g_manifest['artifacts']['research/external_verification/cycle_g_20261010/record_semantic_coverage.csv.gz']['sha256']
    require(sha(coverage_path) == coverage_hash, 'G coverage hash mismatch')
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(coverage_path.read_bytes()).decode())))
    metadata = load(g/'original_record_metadata.json.gz')['records']; meta = {key(r): r for r in metadata}
    require(len(meta) == 1492 and len(rows) == 1794, 'retained metadata/contexts differ')
    decisions = defaultdict(dict); by_context = {}
    for r in rows:
        val = r['semantic_outcome']; r['semantic_outcome'] = {'True': True, 'False': False}.get(val, val)
        decisions[key(r)][r['endpoint']] = r['semantic_outcome']; by_context[(*key(r),r['endpoint'])] = r
    original_decisions = copy.deepcopy(decisions)
    amb = list(csv.DictReader((g/'ambiguities.csv').open()))
    require(len(amb) == 103 and len({key(r) for r in amb}) == 56, 'unresolved G population differs')
    require(Counter(r['endpoint'] for r in amb) == {'executed':48,'proposed':55}, 'endpoint ambiguity counts differ')
    replay = [json.loads(x) for x in gzip.decompress((h/'construct_records.jsonl.gz').read_bytes()).splitlines()]
    selection = {key(r):r for r in load(h/'replay_selection_v2.json')['records']}
    require(len(replay) == len(selection) == 18, 'targeted replay differs')
    differential, new_disagreements = [], []
    for r in replay:
        require(r['rubric_sha256'] == bound[h/'frozen_rules_v2.json'], 'H record rubric mismatch')
        require(r['raw_sha256'] == selection[key(r)]['raw_sha256'] and r['evidence_sha256'] == selection[key(r)]['evidence_sha256'], 'record input binding differs')
        for ep, detail in r['semantic'].items():
            old = by_context[(*key(r),ep)]; new = detail['primary']['outcome']
            require(detail['immutable_repeat_verified'] and detail['second_checker_agrees'] is True, 'H independent checker/invariance missing')
            if known(old['semantic_outcome']):
                require(new == old['semantic_outcome'], 'H changed a previously settled context')
            else:
                require(ep in selection[key(r)]['affected_endpoints'] and known(new), 'unresolved selected context remains')
            decisions[key(r)][ep] = new
            d = {k:old[k] for k in ['stage','position','model','arm','suite','goal','kind','raw_pointer','raw_sha256','evidence_sha256']}
            d.update(endpoint=ep, old_semantic_outcome=old['semantic_outcome'], new_semantic_outcome=new,
                classification_changed=new != old['semantic_outcome'], old_rubric_sha256=old['rubric_sha256'], new_rubric_sha256=r['rubric_sha256'],
                decision_rule='H_V2_ABSENT_REQUIRED_SPEECH_ACT' if r['suite']=='travel' else 'H_V1_ACCEPTED_MOCK_INFORMATION_TRANSACTION',
                evidence=json.dumps(detail['primary']['evidence'],sort_keys=True), historical_outcomes=old['historical_outcomes'],
                evidence_scope='HYPOTHETICAL_PROPOSAL' if ep=='proposed' else 'RETAINED_FINAL_TEXT' if r['suite']=='travel' else 'ACTUAL_AUTHORIZED_MOCK_EXECUTION')
            differential.append(d)
            for field, historical in json.loads(old['historical_outcomes']).items():
                if historical != new and not known(old['semantic_outcome']):
                    new_disagreements.append({**d,'historical_endpoint':field,'frozen_historical_outcome':historical,
                        'independent_semantic_outcome':new,'category':'SOURCE_ORACLE_FALSE_POSITIVE' if historical else 'SOURCE_ORACLE_FALSE_NEGATIVE'})
    changed = [d for d in differential if d['classification_changed']]
    require(len(changed)==32 and len(differential)==35, 'targeted differential counts differ')
    for r in rows:
        k = key(r); ep = r['endpoint']; r['previous_cycle_g_outcome'] = r['semantic_outcome']
        r['semantic_outcome'] = decisions[k][ep]; r['classifiable'] = known(r['semantic_outcome'])
        if (k,ep) in {(key(d),d['endpoint']) for d in changed}:
            r['origin']='CYCLE_H_V2';r['rubric_sha256']=bound[h/'frozen_rules_v2.json']
    g_stats = load(g/'statistical_consequences.json'); eligibility = g_stats['original_pair_population']['frozen_eligibility']
    primary, population = weights(metadata, eligibility); native, native_population = weights(metadata)
    require(population['analysis_pairs']==168 and population['model_goal_units']==42 and all(v==21 for v in population['goals_per_model'].values()), 'frozen primary estimand changed')
    require(set(c['coefficient'] for c in primary.values()) == {Fraction(1,168),Fraction(-1,168)}, 'unexpected principal nested weights')
    contrasts = {}
    for ep, cs in [('executed',primary),('proposed',primary),('native_executed',native)]:
        endpoint='executed' if ep=='native_executed' else ep
        contrasts[ep]={'G':bounds(cs,original_decisions,endpoint),'H':bounds(cs,decisions,endpoint)}
    require(contrasts['executed']['G']['lower']['fraction']=='-15/28' and contrasts['executed']['G']['upper']['fraction']=='-67/168','independent G bounds disagree')
    require(contrasts['proposed']['G']['lower']['fraction']=='-1/6' and contrasts['proposed']['G']['upper']['fraction']=='1/56','independent G proposed bounds disagree')
    original = sum(c['coefficient']*int(c['record']['cpe_executed']) for c in primary.values())
    require(original==Fraction(-85,168),'original source-defined estimate differs')
    impacts=[]; current=copy.deepcopy(original_decisions)
    for d in sorted(changed,key=lambda x:(x['stage'],int(x['position']),x['endpoint'])):
        cs=primary;ep=d['endpoint'];before_b=bounds(cs,current,ep)
        current[key(d)][ep]=d['new_semantic_outcome'];after_b=bounds(cs,current,ep)
        w=cs.get(key(d),{}).get('coefficient',Fraction())
        impacts.append({'stage':d['stage'],'position':d['position'],'goal':goal(d),'model':d['model'],'arm':d['arm'],'endpoint':ep,
            'coefficient':str(w),'in_frozen_primary':key(d) in cs,'new_decision':d['new_semantic_outcome'],
            'lower_change':str(Fraction(after_b['lower']['fraction'])-Fraction(before_b['lower']['fraction'])),
            'upper_change':str(Fraction(after_b['upper']['fraction'])-Fraction(before_b['upper']['fraction'])),
            'bounds_after_lower':after_b['lower']['fraction'],'bounds_after_upper':after_b['upper']['fraction']})
    remain=[r for r in rows if not r['classifiable']]
    strata=defaultdict(list)
    for r in rows:
        for dim, label in [('all','35_goals'),('goal',goal(r)),('suite',r['suite']),('model',r['model']),('arm',r['arm']),('stage',r['stage']),('model_stage_arm','/'.join(r[f] for f in ['model','stage','arm']))]:
            strata[(dim,label,r['endpoint'])].append(r)
    coverage=[]
    for (dim,label,ep), rs in sorted(strata.items()):
        c=Counter(str(r['semantic_outcome']) for r in rs)
        coverage.append({'dimension':dim,'stratum':label,'endpoint':ep,'records':len(rs),'classifiable':c['True']+c['False'],
            'true':c['True'],'false':c['False'],'ambiguous':c['AMBIGUOUS'],'unobservable':c['UNOBSERVABLE']})
    deps=[]; ranks=[]
    for gl in sorted({goal(r) for r in amb}):
        old=[r for r in amb if goal(r)==gl]; remaining=[r for r in remain if goal(r)==gl]
        deps.append({'goal':gl,'G_distinct_records':len({key(r) for r in old}),'G_executed':sum(r['endpoint']=='executed' for r in old),'G_proposed':sum(r['endpoint']=='proposed' for r in old),
            'H_remaining_records':len({key(r) for r in remaining}),'H_remaining_executed':sum(r['endpoint']=='executed' for r in remaining),'H_remaining_proposed':sum(r['endpoint']=='proposed' for r in remaining)})
    for ep in ['executed','proposed']:
        for gl in sorted({goal(r) for r in remain}):
            rs=[r for r in remain if goal(r)==gl and r['endpoint']==ep and key(r) in primary]
            wc=[primary[key(r)]['coefficient'] for r in rs]
            ranks.append({'goal':gl,'endpoint':ep,'unresolved_frozen_primary_labels':len(rs),'off':sum(x<0 for x in wc),'full':sum(x>0 for x in wc),
                'maximum_bound_width_reduction':str(sum((abs(x) for x in wc),Fraction())), 'qualification_only_changes_primary_eligibility':False})
    fully=sum(all(known(v) for r in rows if goal(r)==gl for v in [r['semantic_outcome']]) for gl in {goal(r) for r in rows})
    executed=[r for r in rows if r['endpoint']=='executed']; proposed=[r for r in rows if r['endpoint']=='proposed']
    result={'cycle':'H','status':'PARTIALLY_VERIFIED / HOLD for unrestricted semantic manuscript claims','statistical_status':'POST_HOC',
        'G_reconciliation':{'goals_partial':8,'records':56,'executed_ambiguous':48,'proposed_ambiguous':55,'contexts':103,'overlap_records':47,'proposal_only_records':8,'executed_only_records':1},
        'H_resolved':{'contexts':len(changed),'records':len({key(r) for r in changed}),'executed':sum(r['endpoint']=='executed' for r in changed),'proposed':sum(r['endpoint']=='proposed' for r in changed)},
        'H_remaining':{'contexts':len(remain),'records':len({key(r) for r in remain}),'goals':len({goal(r) for r in remain}),'executed':sum(r['endpoint']=='executed' for r in remain),'proposed':sum(r['endpoint']=='proposed' for r in remain)},
        'coverage':{'goals_all_retained_contexts_classifiable':fully,'executed':{'classifiable':sum(r['classifiable'] for r in executed),'total':len(executed)},'proposed':{'classifiable':sum(r['classifiable'] for r in proposed),'total':len(proposed)},'all_contexts_classifiable_records':sum(all(known(x) for x in eps.values()) for eps in decisions.values()),'total_records':len(decisions)},
        'new_disagreements':{'endpoints':len(new_disagreements),'records':len({key(r) for r in new_disagreements})},
        'frozen_population':population,'native_population_separate':native_population,
        'A_original_source_defined':number(original),'B_preserved_F_four_goal_sensitivity':number(Fraction(-1,2)),
        'C_G_bounds':contrasts['executed']['G'],'D_H_bounds':contrasts['executed']['H'],
        'independent_proposed_outcome_bounds':contrasts['proposed'],'native_all_goals_separate':contrasts['native_executed'],
        'separate_adversarial_known_label_tipping':tipping(primary,decisions,'executed',Fraction(contrasts['executed']['H']['upper']['fraction'])),
        'original_sequence':'Original S2 p=.452555 remains nonsignificant and closes fixed-sequence gate; S3 descriptive. No new confirmatory p-values or confidence intervals calculated.',
        'changed_eligibility':'Not reassessed in H; preserved G changed-eligibility scenarios remain separate changed estimands.',
        'human_review':{'status':'ADJUDICATION_PENDING','authorized_human_decisions':0,'reviewers':[]},
        'input_hashes':{p.name:sha(p) for p in bound},'analysis_started_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    write_csv(h/'differential_ledger.csv',differential);write_csv(h/'additional_discrepancies.csv',new_disagreements, list(new_disagreements[0]) if new_disagreements else ['stage','position','historical_endpoint','category'])
    write_csv(h/'coverage_by_stratum.csv',coverage);write_csv(h/'ambiguity_dependency_map.csv',deps);write_csv(h/'bound_changes.csv',impacts);write_csv(h/'remaining_influence.csv',ranks)
    write_csv(h/'record_semantic_coverage.csv.gz',rows);write_csv(h/'unresolved_contexts.csv.gz',remain)
    result['runtime_seconds']=time.perf_counter()-tick
    (h/'statistical_consequences.json').write_text(json.dumps(result,indent=2)+'\n')
    require(before=={str(p):sha(p) for p in bound},'analysis mutated inputs')
    print(json.dumps({k:result[k] for k in ['H_resolved','H_remaining','coverage','new_disagreements','D_H_bounds','independent_proposed_outcome_bounds','separate_adversarial_known_label_tipping','runtime_seconds']}))


if __name__=='__main__':
    main()
