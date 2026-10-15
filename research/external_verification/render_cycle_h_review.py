"""Render a compact pending-review handoff; never adjudicate or change labels."""
from __future__ import annotations
import csv
import io
import json
import pathlib


def main():
    p=pathlib.Path(__file__).parent/'cycle_h_20261010'
    packet=json.loads((p/'human_review_packet.json').read_text())
    rows=[]
    for i,c in enumerate(packet['goal_cards'],1):
        rows.append({'review_id':'RULE-'+str(i),'goal_key':c['goal_key'],'context_type':'RULE_INTERPRETATION','decision':'','rationale':'','reviewer_id':''})
    for c in packet['observation_cards']:
        rows.append({k:c[k] for k in ['review_id','goal_key','context_type']} | {'decision':'','rationale':'','reviewer_id':''})
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (p/'review_decisions_template.csv').write_text(buf.getvalue())
    lines=['# Cycle H blinded adjudication packet','','Status: **ADJUDICATION_PENDING**. No human reviewers or decisions have been recorded.','',
        'This packet was prepared by a language model. It does not represent independent human or domain-expert review. Model identity, arm, stage, historical outcome and statistical consequences are omitted. Actions may still reveal treatment behavior.','',
        'Use the JSON observation cards and the blank CSV response form. Record TRUE, FALSE, AMBIGUOUS or INSUFFICIENT_EVIDENCE, a rationale and your reviewer identifier. Initial reviewers should work independently before sharing decisions. The form contains five interpretation rows and 71 context rows. No reconciliation or agreement statistic exists yet.','',
        'Target email/account/notes-link literals are consistently redacted in goal cards. Original exact goals, source pointers and aliases remain in a controlled desktop map. No passport or credit-card values, email addresses, file contents or raw message bodies appear in the public cards.','',
        'ACTUAL_AUTHORIZED_MOCK describes historical dispatched mock-tool calls and retained result/error evidence. HYPOTHETICAL_PROPOSAL describes intended calls, never observed execution. Proposed cards do not supply new execution evidence: after an authorized interpretation, affected original shadows must be replayed before changing labels. Where necessary execution evidence is insufficient, abstain.','',
        'A reviewer can resolve a benchmark definition, but cannot invent missing preferences, a spending cap or authenticated names. Selecting a new proxy requires an explicit authorized construct definition and a separate analysis; it is not recovery of an absent fact.','']
    for i,c in enumerate(packet['goal_cards'],1):
        cards=[x for x in packet['observation_cards'] if x['goal_key']==c['goal_key']]
        actual=sum(x['context_type']=='ACTUAL_AUTHORIZED_MOCK' for x in cards)
        lines += ['## RULE-'+str(i)+' — '+c['goal_key'],'','Goal (identifier redaction only):','','> '+c['redacted_original_goal'].replace('\n','\n> '),'',c['contract'],'',
            '**Disputed interpretation:** '+c['dispute'],'','Candidate readings (neither is a recommended answer):','']
        lines += [str(j)+'. '+v for j,v in enumerate(c['candidate_interpretations'],1)]
        lines += ['', '**Evidence barrier:** '+c['missing'],'','Classification: '+c['classification']+'. Cards: '+str(len(cards))+' ('+str(actual)+' actual, '+str(len(cards)-actual)+' hypothetical).','',
            'Review IDs: '+', '.join(x['review_id'] for x in cards), '', 'Decision: ____  Rationale: ____  Reviewer: ____','']
    lines += ['## Packet files','','- [human_review_packet.json](human_review_packet.json): all minimized observations and goal cards.',
        '- [review_decisions_template.csv](review_decisions_template.csv): blank decisions and rationale fields.',
        '- [review_extraction_manifest.json](review_extraction_manifest.json): hashes, extraction runtime and read-only boundary.','',
        'The controlled source/alias map is intentionally excluded from Git. Request controlled access if necessary evidence cannot be judged from the redacted card. No automatic message, invitation or reviewer assignment has been sent.','']
    (p/'HUMAN_REVIEW_PACKET.md').write_text('\n'.join(lines))
    print(json.dumps({'goal_cards':len(packet['goal_cards']),'context_cards':len(packet['observation_cards']),'template_rows':len(rows),'human_decisions':0}))


if __name__=='__main__':
    main()
