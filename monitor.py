import csv, hashlib, json, os, re, time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

SEARCH = "packaging"
TARGET_COUNTRIES = {"RO":"Румъния","GR":"Гърция","RS":"Сърбия","MK":"Северна Македония","HR":"Хърватия","ME":"Черна гора"}
BASE_URL = "https://www.europages.co.uk"
API_PATH = "/search-api-proxy/online.aiSearch.productTextSearch"
LATEST_DIR, HISTORY_DIR, STATE_DIR = "data/latest", "data/history", "data/state"
STATE_FILE = os.path.join(STATE_DIR, "monitor_state.json")
REMOVAL_MISS_THRESHOLD, PAGE_SIZE, MAX_ATTEMPTS, REQUEST_TIMEOUT = 3, 30, 3, 30
OFFER_FIELDS = ["country_code","country","company_name","company_slug","company_ep_slug","company_id","company_uuid","ep_id","distribution_area","founding_year","email_existing","is_ep_member","is_wlw_member","is_quick_responder","product_name","description","category","offer_uuid","auction_id","slug_id","offer_slug","offer_url"]
COMPANY_FIELDS = ["country_code","country","company_name","company_id","company_uuid","company_slug","company_ep_slug","ep_id","distribution_area","founding_year","email_existing","is_ep_member","is_wlw_member","is_quick_responder","products_count"]

def today():
    return datetime.now(ZoneInfo("Europe/Sofia")).strftime("%Y-%m-%d")
def clean(v):
    return " ".join(v.split()) if isinstance(v,str) else ("" if v is None else str(v))
def load_json(p, default):
    try:
        with open(p,encoding="utf-8") as f: return json.load(f)
    except (OSError,ValueError): return default
def save_json(obj,p):
    os.makedirs(os.path.dirname(p) or ".",exist_ok=True); t=p+".tmp"
    with open(t,"w",encoding="utf-8") as f: json.dump(obj,f,ensure_ascii=False,indent=2)
    os.replace(t,p)
def load_csv(p):
    try:
        with open(p,encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
    except OSError: return []
def save_csv(rows,p,fields):
    os.makedirs(os.path.dirname(p) or ".",exist_ok=True); t=p+".tmp"
    with open(t,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader()
        w.writerows([{k:r.get(k,"") for k in fields} for r in rows])
    os.replace(t,p)
def create_session():
    s=requests.Session()
    h={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36","Accept-Language":"bg,en;q=0.9"}
    try: r=s.get(f"{BASE_URL}/bg/products?q={SEARCH}",headers=h,timeout=REQUEST_TIMEOUT); r.raise_for_status()
    except requests.RequestException as e: print("Session error:",e); return s,None
    sid=s.cookies.get("ufs_session_id")
    if not sid:
        for pat in [r'"ufsSessionId"\s*:\s*"([^"]+)"',r'"ufs_session_id"\s*:\s*"([^"]+)"',r"ufsSessionId=([a-zA-Z0-9_-]+)",r"ufs_session_id=([a-zA-Z0-9_-]+)"]:
            m=re.search(pat,r.text)
            if m: sid=m.group(1); break
    print("Homepage HTTP:",r.status_code,"| session ID:", "found" if sid else "NOT FOUND")
    return s,sid
def get_page(s,sid,page):
    params={"callerIdentity":"preciseIntention","enCores":SEARCH,"multiProTest":"true","query":SEARCH,"keywordsTranslate":SEARCH,"pageSize":str(PAGE_SIZE),"llmIntentionType":"preciseIntention","coreProduct":SEARCH,"searchQuery":SEARCH,"langident":"bg","language":"bg","site":"ep","ufsSessionId":sid,"verified":"false","topResponder":"false","isQuickResponder":"false","source":"web","currency":"EUR","terminalType":"pc","country":"bg","history":"false","topLevelDomain":"uk","needReasoning":"false","allowTestData":"false","page":str(page)}
    h={"Accept":"application/json, text/plain, */*","Accept-Language":"bg,en;q=0.9","Referer":f"{BASE_URL}/bg/products?q={SEARCH}","User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36"}
    for a in range(1,MAX_ATTEMPTS+1):
        try:
            r=s.get(BASE_URL+API_PATH,params=params,headers=h,timeout=REQUEST_TIMEOUT)
            print(f"PAGE {page}: HTTP {r.status_code} (request {a}/{MAX_ATTEMPTS})")
            if r.status_code!=200: raise ValueError(f"HTTP {r.status_code}: {r.text[:150]}")
            d=r.json()
            if not isinstance(d,dict) or not isinstance(d.get("model"),dict) or not isinstance(d["model"].get("offers"),list): raise ValueError("invalid response structure")
            return d
        except (requests.RequestException,ValueError) as e:
            print(f"PAGE {page} request error: {e}")
            if a<MAX_ATTEMPTS: time.sleep(a*2)
    return None
def extract(o):
    c=o.get("company",{}); c=c if isinstance(c,dict) else {}; cc=clean(c.get("countryCode","")).upper(); slug=clean(o.get("slug",""))
    return {"country_code":cc,"country":TARGET_COUNTRIES.get(cc,cc),"company_name":clean(c.get("name","")),"company_slug":clean(c.get("slug","")),"company_ep_slug":clean(c.get("epSlug","")),"company_id":clean(c.get("companyId","")),"company_uuid":clean(c.get("uuid","")),"ep_id":clean(c.get("epId","")),"distribution_area":clean(c.get("distributionArea","")),"founding_year":clean(c.get("foundingYear","")),"email_existing":clean(c.get("emailExisting","")),"is_ep_member":clean(c.get("is_ep_member","")),"is_wlw_member":clean(c.get("is_wlw_member","")),"is_quick_responder":clean(c.get("isQuickResponder","")),"product_name":clean(o.get("name","")),"description":clean(o.get("description","")),"category":clean(o.get("vCategory","")),"offer_uuid":clean(o.get("uuid","")),"auction_id":clean(o.get("auctionId","")),"slug_id":clean(o.get("slugId","")),"offer_slug":slug,"offer_url":f"{BASE_URL}/bg/products/{slug}" if slug else ""}
def offer_key(r):
    if r.get("offer_uuid"): return "uuid:"+r["offer_uuid"]
    if r.get("slug_id"): return "slugid:"+r["slug_id"]
    if r.get("auction_id") and r.get("offer_slug"): return "auction_slug:"+r["auction_id"]+":"+r["offer_slug"]
    if r.get("offer_slug"): return "slug:"+r["offer_slug"]
    raw="|".join(r.get(k,"") for k in ("country_code","company_id","product_name"))
    return "fallback:"+hashlib.sha256(raw.encode()).hexdigest()
def company_key(r):
    for field,prefix in (("company_id","id"),("company_uuid","uuid"),("company_slug","slug")):
        if r.get(field): return f"{prefix}:{r.get('country_code','')}:{r[field]}"
    return "name:"+r.get("country_code","")+":"+r.get("company_name","").strip().lower()
def fp(row,fields):
    return hashlib.sha256(json.dumps({k:row.get(k,"") for k in fields},ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def dedupe(rows,key):
    out=[]; seen=set()
    for r in rows:
        k=key(r)
        if k not in seen: seen.add(k); out.append(r)
    return out
def companies_from(offers):
    out={}
    for r in offers:
        k=company_key(r)
        if k not in out:
            out[k]={f:r.get(f,"") for f in COMPANY_FIELDS if f!="products_count"}; out[k]["products_count"]=0
        out[k]["products_count"]+=1
    return list(out.values())
def previous_snapshot(day):
    if not os.path.isdir(HISTORY_DIR): return None
    ds=[n for n in os.listdir(HISTORY_DIR) if re.fullmatch(r"\d{4}-\d{2}-\d{2}",n) and n<day and os.path.isdir(os.path.join(HISTORY_DIR,n))]
    return sorted(ds,reverse=True)[0] if ds else None
def state_load():
    s=load_json(STATE_FILE,{})
    if not isinstance(s,dict): s={}
    s.setdefault("offers",{}); s.setdefault("companies",{}); s.setdefault("last_processed_date","")
    return s
def bootstrap_state_from_history(state, previous_date):
    # Keep the existing recovery behavior if state is missing but history exists.
    if state["offers"] or state["companies"] or not previous_date:
        return state
    folder = os.path.join(HISTORY_DIR, previous_date)
    offers_path = next((os.path.join(folder, n) for n in ("offers_yug.csv", "offers_ro_gr.csv")
                        if os.path.exists(os.path.join(folder, n))), None)
    companies_path = next((os.path.join(folder, n) for n in ("companies_yug.csv", "companies_ro_gr.csv")
                           if os.path.exists(os.path.join(folder, n))), None)
    old_offers, old_companies = load_csv(offers_path), load_csv(companies_path)
    for row in old_offers:
        state["offers"][offer_key(row)] = {
            "record": row, "fingerprint": fp(row, OFFER_FIELDS),
            "first_seen": previous_date, "last_seen": previous_date,
            "missed_days": 0, "status": "active",
        }
    cfields = [f for f in COMPANY_FIELDS if f != "products_count"]
    for row in old_companies:
        state["companies"][company_key(row)] = {
            "record": row, "fingerprint": fp(row, cfields),
            "first_seen": previous_date, "last_seen": previous_date,
            "missed_days": 0, "status": "active",
        }
    if old_offers or old_companies:
        print(f"STATE BOOTSTRAPPED FROM {previous_date}: {len(old_offers)} offers, {len(old_companies)} companies")
    return state

def compare(current_offers,current_companies,state,day):
    names=("new_offers","changed_offers","removed_offers","returned_offers","pending_removed_offers","new_companies","changed_companies","removed_companies","returned_companies","pending_removed_companies")
    result={n:[] for n in names}; same_day=state.get("last_processed_date")==day
    def process(rows,sk,keyfn,fields,prefix):
        oldmap=state[sk]; cur={keyfn(r):r for r in rows}
        for k,r in cur.items():
            digest=fp(r,fields); old=oldmap.get(k)
            if old is None: result["new_"+prefix].append(r); first=day
            else:
                first=old.get("first_seen",day)
                if old.get("status")=="removed": result["returned_"+prefix].append(r)
                elif old.get("fingerprint")!=digest: result["changed_"+prefix].append(r)
            oldmap[k]={"record":r,"fingerprint":digest,"first_seen":first,"last_seen":day,"missed_days":0,"status":"active"}
        for k,old in oldmap.items():
            if k in cur or old.get("last_seen")==day: continue
            if same_day:
                if old.get("status","active")!="removed": result["pending_removed_"+prefix].append(old.get("record",{}))
                continue
            old["missed_days"]=int(old.get("missed_days",0))+1
            if old["missed_days"]>=REMOVAL_MISS_THRESHOLD:
                if old.get("status")!="removed": result["removed_"+prefix].append(old.get("record",{}))
                old["status"]="removed"
            else: result["pending_removed_"+prefix].append(old.get("record",{}))
    process(current_offers,"offers",offer_key,OFFER_FIELDS,"offers")
    process(current_companies,"companies",company_key,[f for f in COMPANY_FIELDS if f!="products_count"],"companies")
    state["last_processed_date"]=day
    return result
def download_snapshot(s,sid,first,total_pages,total):
    all_rows=[]; failed=[]; suspicious=[]; counts={}
    for page in range(1,total_pages+1):
        expected=max(0,min(PAGE_SIZE,total-(page-1)*PAGE_SIZE)) if total>0 else None
        accepted=None
        for attempt in range(1,MAX_ATTEMPTS+1):
            d=first if page==1 and attempt==1 else get_page(s,sid,page)
            if d is None:
                if attempt<MAX_ATTEMPTS: time.sleep(attempt*2)
                continue
            rows=d["model"]["offers"]
            if expected is None or len(rows)==expected:
                accepted=rows; break
            print(f"PAGE {page}: suspicious count {len(rows)}; expected {expected} (validation {attempt}/{MAX_ATTEMPTS})")
            if attempt<MAX_ATTEMPTS: time.sleep(attempt*2)
            else: suspicious.append(page)
        if accepted is None:
            failed.append(page); print(f"PAGE {page}/{total_pages}: FAILED")
        else:
            counts[page]=len(accepted); all_rows.extend(accepted); print(f"PAGE {page}/{total_pages}: {len(accepted)} offers")
        if page<total_pages: time.sleep(1)
    mismatch=total>0 and len(all_rows)!=total
    return all_rows,failed,suspicious,counts,mismatch
def main():
    for p in (LATEST_DIR,HISTORY_DIR,STATE_DIR): os.makedirs(p,exist_ok=True)
    day=today(); state=state_load(); prev=previous_snapshot(day); state=bootstrap_state_from_history(state,prev)
    print("="*65); print("EUROPAGES - B2B YUG MONITOR"); print("PAGINATION VALIDATION + SAFE SNAPSHOT"); print("DATE:",day,"| SEARCH:",SEARCH,"| PREVIOUS:",prev or "None")
    for k,v in TARGET_COUNTRIES.items(): print(f"  {k} - {v}")
    s,sid=create_session()
    if not sid: print("MONITOR ABORTED — no session ID; existing data preserved."); return
    first=get_page(s,sid,1)
    if first is None: print("MONITOR ABORTED — first page failed; existing data preserved."); return
    paging=first["model"].get("paging",{})
    try: pages=int(paging.get("totalPages",1) or 1); total=int(paging.get("total",0) or 0)
    except (TypeError,ValueError): print("MONITOR ABORTED — invalid paging data; existing data preserved."); return
    if pages<1 or total<0: print("MONITOR ABORTED — invalid paging values; existing data preserved."); return
    print("PAGES TO DOWNLOAD:",pages); print("TOTAL OFFERS REPORTED BY EUROPAGES:",total)
    if total>0 and pages!=(total+PAGE_SIZE-1)//PAGE_SIZE:
        print("WARNING: totalPages does not match total/pageSize; page validation will still be enforced.")
    raw,failed,suspicious,counts,mismatch=download_snapshot(s,sid,first,pages,total)
    if failed or suspicious or mismatch:
        print("="*65); print("MONITOR ABORTED — INCOMPLETE OR UNVERIFIED DOWNLOAD")
        if failed: print("FAILED PAGES:",", ".join(map(str,failed)))
        if suspicious: print("SUSPICIOUS PAGES AFTER RETRIES:",", ".join(map(str,suspicious)))
        print("EXPECTED TOTAL:",total,"| DOWNLOADED TOTAL:",len(raw))
        print("PAGE COUNTS:",", ".join(f"{p}:{counts.get(p,0)}" for p in range(1,pages+1)))
        print("LATEST, STATE AND HISTORY WERE NOT CHANGED."); print("="*65); return
    print("ALL PAGES VALIDATED SUCCESSFULLY; RAW OFFERS:",len(raw))
    rows=dedupe([extract(o) for o in raw if clean((o.get("company") or {}).get("countryCode","")).upper() in TARGET_COUNTRIES],offer_key)
    co=companies_from(rows); result=compare(rows,co,state,day)
    hist=os.path.join(HISTORY_DIR,day); os.makedirs(hist,exist_ok=True)
    save_csv(rows,os.path.join(LATEST_DIR,"offers_yug.csv"),OFFER_FIELDS)
    save_csv(co,os.path.join(LATEST_DIR,"companies_yug.csv"),COMPANY_FIELDS)
    save_csv(rows,os.path.join(hist,"offers_yug.csv"),OFFER_FIELDS)
    save_csv(co,os.path.join(hist,"companies_yug.csv"),COMPANY_FIELDS)
    for key in ("new_offers","removed_offers","changed_offers","returned_offers","pending_removed_offers","new_companies","removed_companies","changed_companies","returned_companies","pending_removed_companies"):
        fields=COMPANY_FIELDS if "companies" in key else OFFER_FIELDS
        save_csv(result[key],os.path.join(hist,key+".csv"),fields)
    save_json(state,STATE_FILE)
    country_counts={cc:sum(r["country_code"]==cc for r in rows) for cc in TARGET_COUNTRIES}
    summary={"date":day,"search":SEARCH,"target_countries":TARGET_COUNTRIES,"previous_snapshot":prev,"total_offers_reported_by_europages":total,"downloaded_offers":len(raw),"filtered_offers":len(rows),"unique_companies":len(co),"country_counts":country_counts,"removal_threshold_days":REMOVAL_MISS_THRESHOLD,"download_complete":True,"pages_downloaded":pages,"page_counts":counts}
    for k,v in result.items(): summary[k]=len(v)
    save_json(summary,os.path.join(hist,"summary.json"))
    print("="*65); print("B2B YUG MONITOR RESULT"); print("REPORTED:",total,"| DOWNLOADED:",len(raw),"| TARGET OFFERS:",len(rows),"| COMPANIES:",len(co))
    for cc,name in TARGET_COUNTRIES.items(): print(f"{cc} - {name}: {country_counts[cc]}")
    for k,v in result.items(): print(k.upper()+":",len(v))
    print("LATEST:",LATEST_DIR,"| STATE:",STATE_FILE,"| HISTORY:",hist); print("MONITOR COMPLETE")
if __name__=="__main__": main()
