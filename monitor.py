import requests
import json
import time
import re
import csv
import os
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

SEARCH = "packaging"
TARGET_COUNTRIES = {"RO": "Румъния", "GR": "Гърция"}
BASE_URL = "https://www.europages.co.uk"
API_PATH = "/search-api-proxy/online.aiSearch.productTextSearch"
LATEST_DIR = "data/latest"
HISTORY_DIR = "data/history"
STATE_DIR = "data/state"
STATE_FILE = os.path.join(STATE_DIR, "monitor_state.json")
REMOVAL_MISS_THRESHOLD = 3

OFFER_FIELDS = [
    "country_code", "country", "company_name", "company_slug", "company_ep_slug",
    "company_id", "company_uuid", "ep_id", "distribution_area", "founding_year",
    "email_existing", "is_ep_member", "is_wlw_member", "is_quick_responder",
    "product_name", "description", "category", "offer_uuid", "auction_id", "slug_id",
    "offer_slug", "offer_url",
]

COMPANY_FIELDS = [
    "country_code", "country", "company_name", "company_id", "company_uuid",
    "company_slug", "company_ep_slug", "ep_id", "distribution_area", "founding_year",
    "email_existing", "is_ep_member", "is_wlw_member", "is_quick_responder", "products_count",
]


def ensure_directories():
    for path in (LATEST_DIR, HISTORY_DIR, STATE_DIR):
        os.makedirs(path, exist_ok=True)


def get_today():
    return datetime.now(ZoneInfo("Europe/Sofia")).strftime("%Y-%m-%d")


def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR loading {filename}: {e}")
        return default


def save_json(data, filename):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_state():
    state = load_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("offers", {})
    state.setdefault("companies", {})
    state.setdefault("last_processed_date", "")
    return state


def load_csv(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"ERROR loading {filename}: {e}")
        return []


def find_previous_snapshot(today):
    if not os.path.exists(HISTORY_DIR):
        return None
    dates = []
    for name in os.listdir(HISTORY_DIR):
        if re.match(r"^\d{4}-\d{2}-\d{2}$", name):
            path = os.path.join(HISTORY_DIR, name)
            if os.path.isdir(path) and name < today:
                dates.append(name)
    return sorted(dates, reverse=True)[0] if dates else None


def create_session():
    print("=" * 70)
    print("CREATING EUROPAGES SESSION")
    print("=" * 70)
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "bg,en;q=0.9,en-GB;q=0.8",
    }
    response = session.get(f"{BASE_URL}/bg/products?q={SEARCH}", headers=headers, timeout=30)
    print("Homepage HTTP:", response.status_code)
    ufs_session_id = session.cookies.get("ufs_session_id")
    if ufs_session_id:
        print("ufsSessionId obtained from cookie")
        print("Session:", ufs_session_id[:8] + "...")
        return session, ufs_session_id
    patterns = [r'"ufsSessionId"\s*:\s*"([^"]+)"', r'"ufs_session_id"\s*:\s*"([^"]+)"', r'ufsSessionId=([a-zA-Z0-9]+)', r'ufs_session_id=([a-zA-Z0-9]+)']
    for pattern in patterns:
        match = re.search(pattern, response.text)
        if match:
            ufs_session_id = match.group(1)
            print("ufsSessionId found in page")
            print("Session:", ufs_session_id[:8] + "...")
            return session, ufs_session_id
    return session, None


def get_page(session, ufs_session_id, page):
    params = {
        "callerIdentity": "preciseIntention", "enCores": SEARCH, "multiProTest": "true",
        "query": SEARCH, "keywordsTranslate": SEARCH, "pageSize": "30",
        "llmIntentionType": "preciseIntention", "coreProduct": SEARCH, "searchQuery": SEARCH,
        "langident": "bg", "language": "bg", "site": "ep", "ufsSessionId": ufs_session_id,
        "verified": "false", "topResponder": "false", "isQuickResponder": "false", "source": "web",
        "currency": "EUR", "terminalType": "pc", "country": "bg", "history": "false",
        "topLevelDomain": "uk", "needReasoning": "false", "allowTestData": "false", "page": str(page),
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "bg,en;q=0.9,en-GB;q=0.8",
        "Referer": f"{BASE_URL}/bg/products?q={SEARCH}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0",
    }
    try:
        response = session.get(BASE_URL + API_PATH, params=params, headers=headers, timeout=30)
    except Exception as e:
        print(f"PAGE {page}: ERROR {e}")
        return None
    print(f"PAGE {page}: HTTP {response.status_code}")
    if response.status_code != 200:
        print(response.text[:1000])
        return None
    try:
        return response.json()
    except Exception as e:
        print(f"PAGE {page}: JSON ERROR {e}")
        return None


def get_country(offer):
    try:
        return offer.get("company", {}).get("countryCode", "").upper()
    except Exception:
        return ""


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    return str(value)


def extract_offer(offer):
    company = offer.get("company", {})
    if not isinstance(company, dict):
        company = {}
    country_code = clean_text(company.get("countryCode", "")).upper()
    offer_slug = clean_text(offer.get("slug", ""))
    row = {
        "country_code": country_code,
        "country": TARGET_COUNTRIES.get(country_code, country_code),
        "company_name": clean_text(company.get("name", "")),
        "company_slug": clean_text(company.get("slug", "")),
        "company_ep_slug": clean_text(company.get("epSlug", "")),
        "company_id": clean_text(company.get("companyId", "")),
        "company_uuid": clean_text(company.get("uuid", "")),
        "ep_id": clean_text(company.get("epId", "")),
        "distribution_area": clean_text(company.get("distributionArea", "")),
        "founding_year": clean_text(company.get("foundingYear", "")),
        "email_existing": clean_text(company.get("emailExisting", "")),
        "is_ep_member": clean_text(company.get("is_ep_member", "")),
        "is_wlw_member": clean_text(company.get("is_wlw_member", "")),
        "is_quick_responder": clean_text(company.get("isQuickResponder", "")),
        "product_name": clean_text(offer.get("name", "")),
        "description": clean_text(offer.get("description", "")),
        "category": clean_text(offer.get("vCategory", "")),
        "offer_uuid": clean_text(offer.get("uuid", "")),
        "auction_id": clean_text(offer.get("auctionId", "")),
        "slug_id": clean_text(offer.get("slugId", "")),
        "offer_slug": offer_slug,
        "offer_url": f"{BASE_URL}/bg/products/{offer_slug}" if offer_slug else "",
    }
    return row


def offer_key(row):
    if row.get("offer_uuid"):
        return "uuid:" + row["offer_uuid"]
    if row.get("slug_id"):
        return "slugid:" + row["slug_id"]
    if row.get("auction_id") and row.get("offer_slug"):
        return "auction_slug:" + row["auction_id"] + ":" + row["offer_slug"]
    if row.get("offer_slug"):
        return "slug:" + row["offer_slug"]
    raw = "|".join(row.get(k, "") for k in ("country_code", "company_id", "product_name"))
    return "fallback:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def company_key(row):
    if row.get("company_id"):
        return f"id:{row['country_code']}:{row['company_id']}"
    if row.get("company_uuid"):
        return f"uuid:{row['country_code']}:{row['company_uuid']}"
    if row.get("company_slug"):
        return f"slug:{row['country_code']}:{row['company_slug']}"
    return "name:" + row.get("country_code", "") + ":" + row.get("company_name", "").strip().lower()


def fingerprint(row, fields):
    payload = {k: row.get(k, "") for k in fields}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dedupe_rows(rows, key_func):
    result = {}
    for row in rows:
        result[key_func(row)] = row
    return list(result.values())


def create_unique_companies(rows):
    companies = {}
    for row in rows:
        key = company_key(row)
        if key not in companies:
            companies[key] = {k: row.get(k, "") for k in COMPANY_FIELDS if k != "products_count"}
            companies[key]["products_count"] = 0
        companies[key]["products_count"] += 1
    return list(companies.values())


def save_csv(rows, filename, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        if fieldnames:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            if rows:
                writer.writerows(rows)
    print()
    print("SAVED:" if rows else "SAVED EMPTY:", filename)
    print("ROWS:", len(rows))


def compare_and_update_state(current_rows, current_companies, state, today):
    current_offers = {offer_key(r): r for r in current_rows}
    current_company_map = {company_key(r): r for r in current_companies}
    old_offers = state["offers"]
    old_companies = state["companies"]

    new_offers, changed_offers, removed_offers, returned_offers = [], [], [], []
    new_companies, changed_companies, removed_companies, returned_companies = [], [], [], []
    pending_removed_offers, pending_removed_companies = [], []

    for key, row in current_offers.items():
        fp = fingerprint(row, OFFER_FIELDS)
        old = old_offers.get(key)
        if old is None:
            new_offers.append(row)
        elif old.get("status") == "removed":
            returned_offers.append(row)
        elif old.get("fingerprint") != fp:
            changed_offers.append(row)
        old_offers[key] = {
            "record": row,
            "fingerprint": fp,
            "first_seen": old.get("first_seen", today) if old else today,
            "last_seen": today,
            "missed_days": 0,
            "status": "active",
        }

    for key, old in list(old_offers.items()):
        if key in current_offers:
            continue
        if old.get("last_seen") == today:
            continue
        if old.get("status") == "removed":
            continue
        old["missed_days"] = int(old.get("missed_days", 0)) + 1
        row = old.get("record", {})
        if old["missed_days"] >= REMOVAL_MISS_THRESHOLD:
            old["status"] = "removed"
            old["removed_date"] = today
            removed_offers.append(row)
        else:
            pending_removed_offers.append(row)

    for key, row in current_company_map.items():
        fp = fingerprint(row, [k for k in COMPANY_FIELDS if k != "products_count"])
        old = old_companies.get(key)
        if old is None:
            new_companies.append(row)
        elif old.get("status") == "removed":
            returned_companies.append(row)
        elif old.get("fingerprint") != fp:
            changed_companies.append(row)
        old_companies[key] = {
            "record": row,
            "fingerprint": fp,
            "first_seen": old.get("first_seen", today) if old else today,
            "last_seen": today,
            "missed_days": 0,
            "status": "active",
        }

    for key, old in list(old_companies.items()):
        if key in current_company_map:
            continue
        if old.get("last_seen") == today or old.get("status") == "removed":
            continue
        old["missed_days"] = int(old.get("missed_days", 0)) + 1
        row = old.get("record", {})
        if old["missed_days"] >= REMOVAL_MISS_THRESHOLD:
            old["status"] = "removed"
            old["removed_date"] = today
            removed_companies.append(row)
        else:
            pending_removed_companies.append(row)

    state["last_processed_date"] = today
    state["last_successful_offer_count"] = len(current_rows)
    state["last_successful_company_count"] = len(current_companies)

    return {
        "new_offers": new_offers,
        "changed_offers": changed_offers,
        "removed_offers": removed_offers,
        "returned_offers": returned_offers,
        "pending_removed_offers": pending_removed_offers,
        "new_companies": new_companies,
        "changed_companies": changed_companies,
        "removed_companies": removed_companies,
        "returned_companies": returned_companies,
        "pending_removed_companies": pending_removed_companies,
    }


def bootstrap_state_from_history(state, previous_date):
    if state["offers"] or state["companies"] or not previous_date:
        return state
    prev_dir = os.path.join(HISTORY_DIR, previous_date)
    prev_offers = load_csv(os.path.join(prev_dir, "offers_ro_gr.csv"))
    prev_companies = load_csv(os.path.join(prev_dir, "companies_ro_gr.csv"))
    for row in prev_offers:
        key = offer_key(row)
        state["offers"][key] = {"record": row, "fingerprint": fingerprint(row, OFFER_FIELDS), "first_seen": previous_date, "last_seen": previous_date, "missed_days": 0, "status": "active"}
    for row in prev_companies:
        key = company_key(row)
        state["companies"][key] = {"record": row, "fingerprint": fingerprint(row, [k for k in COMPANY_FIELDS if k != "products_count"]), "first_seen": previous_date, "last_seen": previous_date, "missed_days": 0, "status": "active"}
    print(f"STATE BOOTSTRAPPED FROM {previous_date}: {len(prev_offers)} offers, {len(prev_companies)} companies")
    return state


def main():
    ensure_directories()
    today = get_today()
    state = load_state()
    previous_date = find_previous_snapshot(today)
    state = bootstrap_state_from_history(state, previous_date)

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("HISTORY + RELIABLE NEW / REMOVED / CHANGED VERSION")
    print("=" * 70)
    print()
    print("DATE:", today)
    print("SEARCH:", SEARCH)
    print()
    print("TARGET COUNTRIES:", ", ".join(TARGET_COUNTRIES.values()))
    print()
    if previous_date:
        prev_offers = load_csv(os.path.join(HISTORY_DIR, previous_date, "offers_ro_gr.csv"))
        prev_companies = load_csv(os.path.join(HISTORY_DIR, previous_date, "companies_ro_gr.csv"))
        print("PREVIOUS SNAPSHOT FOUND:", previous_date)
        print("COMPARISON SOURCE:", os.path.join(HISTORY_DIR, previous_date))
        print("PREVIOUS OFFERS:", len(prev_offers))
        print("PREVIOUS COMPANIES:", len(prev_companies))
    else:
        print("NO PREVIOUS SNAPSHOT FOUND")
    print()

    session, ufs_session_id = create_session()
    if not ufs_session_id:
        print("ERROR: ufsSessionId not found.")
        return

    print()
    print("=" * 70)
    print("DOWNLOADING EUROPAGES DATA")
    print("=" * 70)

    first_data = get_page(session, ufs_session_id, 1)
    if not first_data:
        print("First page failed.")
        return

    model = first_data.get("model", {})
    paging = model.get("paging", {})
    total_pages = int(paging.get("totalPages", 1) or 1)
    total_offers = paging.get("total", 0)
    all_offers = []

    for page in range(1, total_pages + 1):
        data = first_data if page == 1 else get_page(session, ufs_session_id, page)
        if not data:
            continue
        all_offers.extend(data.get("model", {}).get("offers", []))
        if page != total_pages:
            time.sleep(1)

    target_rows = [extract_offer(o) for o in all_offers if get_country(o) in TARGET_COUNTRIES]
    target_rows = dedupe_rows(target_rows, offer_key)
    unique_companies = create_unique_companies(target_rows)
    result = compare_and_update_state(target_rows, unique_companies, state, today)
    save_json(state, STATE_FILE)

    history_dir = os.path.join(HISTORY_DIR, today)
    os.makedirs(history_dir, exist_ok=True)

    save_csv(target_rows, os.path.join(LATEST_DIR, "offers_ro_gr.csv"), OFFER_FIELDS)
    save_csv(unique_companies, os.path.join(LATEST_DIR, "companies_ro_gr.csv"), COMPANY_FIELDS)
    save_csv(target_rows, os.path.join(history_dir, "offers_ro_gr.csv"), OFFER_FIELDS)
    save_csv(unique_companies, os.path.join(history_dir, "companies_ro_gr.csv"), COMPANY_FIELDS)

    output_map = [
        ("new_offers", "new_offers.csv", OFFER_FIELDS),
        ("removed_offers", "removed_offers.csv", OFFER_FIELDS),
        ("changed_offers", "changed_offers.csv", OFFER_FIELDS),
        ("returned_offers", "returned_offers.csv", OFFER_FIELDS),
        ("pending_removed_offers", "pending_removed_offers.csv", OFFER_FIELDS),
        ("new_companies", "new_companies.csv", COMPANY_FIELDS),
        ("removed_companies", "removed_companies.csv", COMPANY_FIELDS),
        ("changed_companies", "changed_companies.csv", COMPANY_FIELDS),
        ("returned_companies", "returned_companies.csv", COMPANY_FIELDS),
        ("pending_removed_companies", "pending_removed_companies.csv", COMPANY_FIELDS),
    ]
    for key, filename, fields in output_map:
        save_csv(result[key], os.path.join(history_dir, filename), fields)

    summary = {
        "date": today,
        "search": SEARCH,
        "target_countries": TARGET_COUNTRIES,
        "previous_snapshot": previous_date,
        "total_offers_reported_by_europages": total_offers,
        "downloaded_offers": len(all_offers),
        "filtered_offers": len(target_rows),
        "unique_companies": len(unique_companies),
        "new_offers": len(result["new_offers"]),
        "changed_offers": len(result["changed_offers"]),
        "removed_offers": len(result["removed_offers"]),
        "returned_offers": len(result["returned_offers"]),
        "pending_removed_offers": len(result["pending_removed_offers"]),
        "new_companies": len(result["new_companies"]),
        "changed_companies": len(result["changed_companies"]),
        "removed_companies": len(result["removed_companies"]),
        "returned_companies": len(result["returned_companies"]),
        "pending_removed_companies": len(result["pending_removed_companies"]),
        "removal_threshold_days": REMOVAL_MISS_THRESHOLD,
    }
    save_json(summary, os.path.join(history_dir, "summary.json"))

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print("TOTAL OFFERS:", total_offers)
    print("DOWNLOADED:", len(all_offers))
    print("ROMANIA OFFERS:", sum(1 for r in target_rows if r["country_code"] == "RO"))
    print("GREECE OFFERS:", sum(1 for r in target_rows if r["country_code"] == "GR"))
    print("TOTAL RO + GR:", len(target_rows))
    print("UNIQUE COMPANIES:", len(unique_companies))
    print()
    print("NEW OFFERS:", len(result["new_offers"]))
    print("CHANGED OFFERS:", len(result["changed_offers"]))
    print("REMOVED OFFERS:", len(result["removed_offers"]))
    print("RETURNED OFFERS:", len(result["returned_offers"]))
    print("PENDING REMOVED OFFERS:", len(result["pending_removed_offers"]))
    print()
    print("NEW COMPANIES:", len(result["new_companies"]))
    print("CHANGED COMPANIES:", len(result["changed_companies"]))
    print("REMOVED COMPANIES:", len(result["removed_companies"]))
    print("RETURNED COMPANIES:", len(result["returned_companies"]))
    print("PENDING REMOVED COMPANIES:", len(result["pending_removed_companies"]))
    print()
    print("REMOVAL RULE: an item is REMOVED only after", REMOVAL_MISS_THRESHOLD, "successful daily misses.")
    print("STATE:", STATE_FILE)
    print("=" * 70)
    print("MONITOR COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
