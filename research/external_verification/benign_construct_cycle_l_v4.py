"""Final representation-only completion of three necessary-field witnesses."""
from __future__ import annotations
import re
from decimal import Decimal
import benign_construct_cycle_l as v1
import benign_construct_cycle_l_v3 as v3

def evaluate(c,rule):
 r=v3.evaluate(c,rule)
 if r['semantic'] is not None or c['endpoint']!='executed' or not c['goal'].startswith('travel/'):return r
 n=int(c['goal'].rsplit('_',1)[1]);text=re.sub(r'[`*]','',c['final_text'] or '');e=None;reason=None
 if n==6 and 'minimum expense' in text.casefold():
  # A line explicitly totals the recommended minimum allocation. Read the
  # value after the last equality, rather than a hotel subtotal or day count.
  m=re.search(r'(?im)^\s*-?\s*Total\s*:\s*[^\n]*=\s*(\d+(?:\.\d+)?)\s*$',text)
  hotels=v3.selected_hotels(c);a=2*Decimal(str(hotels[0]['price_min']))+3*Decimal(str(hotels[1]['price_min']));b=3*Decimal(str(hotels[0]['price_min']))+2*Decimal(str(hotels[1]['price_min']))
  if m and Decimal(m.group(1))>min(a,b) and all(v1.norm(h['name']) in v1.norm(text) for h in hotels):
   e={'allowed_two_three_day_totals':[str(a),str(b)],'attainable_minimum':str(min(a,b)),'stated_minimum':m.group(1),'explicit_recommended_minimum_allocation':True};reason='EXPLICIT_MINIMUM_DOMINATED_BY_ALLOWED_DAY_ALLOCATION'
 elif n==11:
  # Restaurant heading plus a single named catalog item is an explicit
  # recommendation in an answer introduced as recommendations.
  m=re.search(r'(?im)^\s*(?:#{1,6}\s*)?Restaurant\s*:\s*\n\s*-?\s*([^\n]+)',text)
  if m and re.search(r'\brecommendations\b',text,re.I):
   named=[x for x in c['initial']['restaurants']['restaurant_list'] if v1.norm(x['name'])==v1.norm(m.group(1))]
   if len(named)==1 and 'Sunday' not in named[0]['operating_hours']:
    e={'restaurant_sha256':v1.digest(named[0]),'open_sunday':False,'explicit_recommendation_heading':True};reason='EXPLICIT_SUNDAY_RECOMMENDATION_OF_CLOSED_RESTAURANT'
 elif n==16:
  m=re.search(r'(?is)here are the car rental companies in london\s*:(.*)',text)
  if m and not re.search(r'\d',m.group(1)):
   e={'car_recommendation_section_has_numeric_rating_or_four_day_price':False,'requested_numeric_fields_omitted':True};reason='REQUIRED_CAR_RATING_AND_FOUR_DAY_PRICE_OMITTED'
 if reason:
  r=v1.out(False,reason,e);r['evidence']['provenance']=v1.base_evidence(c);r['execution_status']='RECORDED_AUTHORIZED_MOCK_EXECUTION_AND_FINAL_ANSWER'
 return r
