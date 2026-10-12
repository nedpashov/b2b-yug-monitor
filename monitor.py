import csv
import hashlib
import json
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


# ============================================================
# B2B YUG MONITOR — COMPLETE REPLACEMENT
# Europages packaging search, six countries, history and state
# ============================================================

SEARCH = "packaging"

TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция",
    "RS": "Сърбия",
    "MK": "Северна Македония",
    "HR": "Хърватия",
    "ME": "Черна гора",
}

BASE_URL = "https://www.europages.co.uk"
API_PATH = "/search-api-proxy/online.aiSearch.productTextSearch"

LATEST_DIR = "data/latest"
HISTORY_DIR = "data/history"
STATE_DIR = "data/state"
STATE_FILE = os.path.join(STATE_DIR, "monitor_state.json")

REMOVAL_MISS_THRESHOLD = 3
PAGE_SIZE = 30
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT = 30

OFFER_FIELDS = [
    "country_code", "country", "company_name", "company_slug",
    "company_ep_slug", "company_id", "company_uuid", "ep_id",
    "distribution_area", "founding_year", "email_existing",
    "is_ep_member", "is_wlw_member", "is_quick_responder",
    "product_name", "description", "category", "offer_uuid",
    "auction_id", "slug_id", "offer_slug", "offer_url",
]

COMPANY_FIELDS = [
    "country_code", "country", "company_name", "company_id",
    "company_uuid", "company_slug", "company_ep_slug", "ep_id",
    "distribution_area", "founding_year", "email_existing",
    "is_ep_member", "is_wlw_member", "is_quick_responder",
    "products_count",
]


def get_today():
    return datetime.now(ZoneInfo("Europe/Sofia")).strftime("%Y-%m-%d")


def ensure_directories():
    for path in (LATEST_DIR, HISTORY_DIR, STATE_DIR):
        os.makedirs(path, exist_ok=True)


def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"WARNING: cannot read {filename}: {exc}")
        return default


def save_json(data, filename):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    temp_name = filename + ".tmp"
    with open(temp_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_name, filename)


def load_csv(filename):
    if not filename or not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except OSError as exc:
        print(f"WARNING: cannot read {filename}: {exc}")
        return []


def save_csv(rows, filename, fields):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    temp_name = filename + ".tmp"
    with open(temp_name, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    os.replace(temp_name, filename)


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    return str(value)


def create_session():
    print("=" * 70)
    print("CREATING EUROPAGES SESSION")
    print("=" * 70)

    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "bg,en;q=0.9,en-GB;q=0.8",
    }

    try:
        response = session.get(
            f"{BASE_URL}/bg/products?q={SEARCH}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print("ERROR creating Europages session:", exc)
        return session, None

    print("Homepage HTTP:", response.status_code)

    session_id = session.cookies.get("ufs_session_id")
    if session_id:
        print("ufsSessionId obtained from cookie")
        return session, session_id

    patterns = [
        r'"ufsSessionId"\s*:\s*"([^"]+)"',
        r'"ufs_session_id"\s*:\s*"([^"]+)"',
        r"ufsSessionId=([a-zA-Z0-9_-]+)",
        r"ufs_session_id=([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, response.text)
        if match:
            print("ufsSessionId found in page source")
            return session, match.group(1)

    print("ERROR: ufsSessionId not found.")
    return session, None


def get_page(session, session_id, page):
    params = {
        "callerIdentity": "preciseIntention",
        "enCores": SEARCH,
        "multiProTest": "true",
        "query": SEARCH,
        "keywordsTranslate": SEARCH,
        "pageSize": str(PAGE_SIZE),
        "llmIntentionType": "preciseIntention",
        "coreProduct": SEARCH,
        "searchQuery": SEARCH,
        "langident": "bg",
        "language": "bg",
        "site": "ep",
        "ufsSessionId": session_id,
        "verified": "false",
        "topResponder": "false",
        "isQuickResponder": "false",
        "source": "web",
        "currency": "EUR",
        "terminalType": "pc",
        "country": "bg",
        "history": "false",
        "topLevelDomain": "uk",
        "needReasoning": "false",
        "allowTestData": "false",
        "page": str(page),
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "bg,en;q=0.9,en-GB;q=0.8",
        "Referer": f"{BASE_URL}/bg/products?q={SEARCH}",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
        ),
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(
                BASE_URL + API_PATH,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            print(
                f"PAGE {page}: HTTP {response.status_code} "
                f"(attempt {attempt}/{MAX_ATTEMPTS})"
            )

            if response.status_code != 200:
                if attempt < MAX_ATTEMPTS:
                    delay = attempt * 3
                    print(f"Retrying page {page} in {delay}s...")
                    time.sleep(delay)
                    continue
                print("Final response:", response.text[:300])
                return None

            try:
                data = response.json()
            except ValueError as exc:
                print(f"PAGE {page}: invalid JSON: {exc}")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(attempt * 3)
                    continue
                return None

            if not isinstance(data, dict):
                print(f"PAGE {page}: response is not a JSON object.")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(attempt * 3)
                    continue
                return None

            model = data.get("model")
            if not isinstance(model, dict):
                print(f"PAGE {page}: missing/invalid model.")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(attempt * 3)
                    continue
                return None

            if not isinstance(model.get("offers"), list):
                print(f"PAGE {page}: missing/invalid offers list.")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(attempt * 3)
                    continue
                return None

            return data

        except requests.RequestException as exc:
            print(
                f"PAGE {page}: request error on attempt "
                f"{attempt}/{MAX_ATTEMPTS}: {exc}"
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(attempt * 3)
            else:
                return None
        except Exception as exc:
            print(f"PAGE {page}: unexpected error: {exc}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(attempt * 3)
            else:
                return None

    return None


def extract_offer(offer):
    company = offer.get("company", {})
    if not isinstance(company, dict):
        company = {}

    country_code = clean_text(company.get("countryCode", "")).upper()
    offer_slug = clean_text(offer.get("slug", ""))

    return {
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


def get_country(offer):
    company = offer.get("company", {})
    if not isinstance(company, dict):
        return ""
    return clean_text(company.get("countryCode", "")).upper()


def offer_key(row):
    if row.get("offer_uuid"):
        return "uuid:" + row["offer_uuid"]
    if row.get("slug_id"):
        return "slugid:" + row["slug_id"]
    if row.get("auction_id") and row.get("offer_slug"):
        return "auction_slug:" + row["auction_id"] + ":" + row["offer_slug"]
    if row.get("offer_slug"):
        return "slug:" + row["offer_slug"]
    raw = "|".join(row.get(k, "") for k in (
        "country_code", "company_id", "product_name"
    ))
    return "fallback:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def company_key(row):
    if row.get("company_id"):
        return f"id:{row['country_code']}:{row['company_id']}"
    if row.get("company_uuid"):
        return f"uuid:{row['country_code']}:{row['company_uuid']}"
    if row.get("company_slug"):
        return f"slug:{row['country_code']}:{row['company_slug']}"
    return "name:" + row.get("country_code", "") + ":" + row.get(
        "company_name", ""
    ).strip().lower()


def fingerprint(row, fields):
    payload = {field: row.get(field, "") for field in fields}
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dedupe_rows(rows, key_function):
    seen = set()
    result = []
    for row in rows:
        key = key_function(row)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def create_unique_companies(offer_rows):
    companies = {}
    for row in offer_rows:
        key = company_key(row)
        if key not in companies:
            companies[key] = {
                field: row.get(field, "")
                for field in COMPANY_FIELDS
                if field != "products_count"
            }
            companies[key]["products_count"] = 0
        companies[key]["products_count"] += 1
    return list(companies.values())


def find_previous_snapshot(today):
    if not os.path.isdir(HISTORY_DIR):
        return None
    dates = []
    for name in os.listdir(HISTORY_DIR):
        path = os.path.join(HISTORY_DIR, name)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", name) and os.path.isdir(path) and name < today:
            dates.append(name)
    return sorted(dates, reverse=True)[0] if dates else None


def find_history_file(previous_date, new_name, old_name):
    if not previous_date:
        return None
    folder = os.path.join(HISTORY_DIR, previous_date)
    for name in (new_name, old_name):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    return None


def load_state():
    state = load_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("offers", {})
    state.setdefault("companies", {})
    state.setdefault("last_processed_date", "")
    return state


def bootstrap_state_from_history(state, previous_date):
    if state["offers"] or state["companies"] or not previous_date:
        return state

    old_offers_path = find_history_file(
        previous_date, "offers_yug.csv", "offers_ro_gr.csv"
    )
    old_companies_path = find_history_file(
        previous_date, "companies_yug.csv", "companies_ro_gr.csv"
    )
    old_offers = load_csv(old_offers_path)
    old_companies = load_csv(old_companies_path)

    for row in old_offers:
        key = offer_key(row)
        state["offers"][key] = {
            "record": row,
            "fingerprint": fingerprint(row, OFFER_FIELDS),
            "first_seen": previous_date,
            "last_seen": previous_date,
            "missed_days": 0,
            "status": "active",
        }

    company_fields = [field for field in COMPANY_FIELDS if field != "products_count"]
    for row in old_companies:
        key = company_key(row)
        state["companies"][key] = {
            "record": row,
            "fingerprint": fingerprint(row, company_fields),
            "first_seen": previous_date,
            "last_seen": previous_date,
            "missed_days": 0,
            "status": "active",
        }

    print(
        f"STATE BOOTSTRAPPED FROM {previous_date}: "
        f"{len(old_offers)} offers, {len(old_companies)} companies"
    )
    return state


def compare_and_update_state(current_offers, current_companies, state, today):
    result = {
        name: [] for name in (
            "new_offers", "changed_offers", "removed_offers",
            "returned_offers", "pending_removed_offers",
            "new_companies", "changed_companies", "removed_companies",
            "returned_companies", "pending_removed_companies",
        )
    }

    # Repeated workflow runs on one calendar day must not count a missing
    # offer/company as another separate daily miss.
    same_day_rerun = state.get("last_processed_date") == today

    def process(current_rows, state_key, key_func, fields, prefix):
        old_records = state[state_key]
        current_map = {key_func(row): row for row in current_rows}

        for key, row in current_map.items():
            fp = fingerprint(row, fields)
            old = old_records.get(key)

            if old is None:
                result["new_" + prefix].append(row)
                first_seen = today
                status = "active"
            else:
                first_seen = old.get("first_seen", today)
                old_status = old.get("status", "active")
                if old_status == "removed":
                    result["returned_" + prefix].append(row)
                elif old.get("fingerprint") != fp:
                    result["changed_" + prefix].append(row)
                status = "active"

            old_records[key] = {
                "record": row,
                "fingerprint": fp,
                "first_seen": first_seen,
                "last_seen": today,
                "missed_days": 0,
                "status": status,
            }

        for key, old in list(old_records.items()):
            if key in current_map:
                continue
            if old.get("last_seen") == today:
                continue

            record = old.get("record", {})

            # Idempotency protection: no second increment on the same date.
            if same_day_rerun:
                if old.get("status", "active") != "removed":
                    result["pending_removed_" + prefix].append(record)
                continue

            old["missed_days"] = int(old.get("missed_days", 0)) + 1
            if old.get("missed_days", 0) >= REMOVAL_MISS_THRESHOLD:
                if old.get("status") != "removed":
                    result["removed_" + prefix].append(record)
                old["status"] = "removed"
            else:
                result["pending_removed_" + prefix].append(record)

    process(current_offers, "offers", offer_key, OFFER_FIELDS, "offers")
    company_fields = [field for field in COMPANY_FIELDS if field != "products_count"]
    process(current_companies, "companies", company_key, company_fields, "companies")
    state["last_processed_date"] = today
    return result


def main():
    ensure_directories()
    today = get_today()
    state = load_state()
    previous_date = find_previous_snapshot(today)
    state = bootstrap_state_from_history(state, previous_date)

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("6-COUNTRY VERSION — SAFE RETRIES AND SNAPSHOT PROTECTION")
    print("=" * 70)
    print("DATE:", today)
    print("SEARCH:", SEARCH)
    print("TARGET COUNTRIES:")
    for code, name in TARGET_COUNTRIES.items():
        print(f"  {code} - {name}")
    print("PREVIOUS SNAPSHOT:", previous_date or "None")
    print()

    session, session_id = create_session()
    if not session_id:
        print("MONITOR ABORTED — ufsSessionId not found.")
        return

    first_data = get_page(session, session_id, 1)
    if first_data is None:
        print("MONITOR ABORTED — first page failed. Existing data preserved.")
        return

    paging = first_data.get("model", {}).get("paging", {})
    try:
        total_pages = int(paging.get("totalPages", 1) or 1)
        total_reported = paging.get("total", 0)
    except (TypeError, ValueError):
        print("MONITOR ABORTED — invalid paging information. Existing data preserved.")
        return

    if total_pages < 1:
        print("MONITOR ABORTED — invalid page count. Existing data preserved.")
        return

    print("PAGES TO DOWNLOAD:", total_pages)
    print("TOTAL OFFERS REPORTED BY EUROPAGES:", total_reported)

    all_offers = []
    failed_pages = []

    for page in range(1, total_pages + 1):
        data = first_data if page == 1 else get_page(session, session_id, page)

        if data is None:
            failed_pages.append(page)
            print(f"PAGE {page}: FAILED")
        else:
            offers = data.get("model", {}).get("offers", [])
            all_offers.extend(offers)
            print(f"PAGE {page}/{total_pages}: {len(offers)} offers")

        if page < total_pages:
            time.sleep(1)

    # Critical guard: no state, latest, or history writes unless every page succeeded.
    if failed_pages:
        print()
        print("=" * 70)
        print("MONITOR ABORTED — INCOMPLETE DOWNLOAD")
        print("FAILED PAGES:", ", ".join(map(str, failed_pages)))
        print(f"SUCCESSFUL PAGES: {total_pages - len(failed_pages)}/{total_pages}")
        print("EXISTING latest CSV FILES, STATE AND HISTORY WERE PRESERVED.")
        print("=" * 70)
        return

    print()
    print("ALL PAGES DOWNLOADED SUCCESSFULLY")
    print("DOWNLOADED RAW OFFERS:", len(all_offers))

    target_rows = [
        extract_offer(offer)
        for offer in all_offers
        if get_country(offer) in TARGET_COUNTRIES
    ]
    target_rows = dedupe_rows(target_rows, offer_key)
    unique_companies = create_unique_companies(target_rows)

    # State is changed only after the full download passed the safety check.
    result = compare_and_update_state(
        target_rows, unique_companies, state, today
    )

    history_dir = os.path.join(HISTORY_DIR, today)
    os.makedirs(history_dir, exist_ok=True)

    latest_offers = os.path.join(LATEST_DIR, "offers_yug.csv")
    latest_companies = os.path.join(LATEST_DIR, "companies_yug.csv")
    history_offers = os.path.join(history_dir, "offers_yug.csv")
    history_companies = os.path.join(history_dir, "companies_yug.csv")

    save_csv(target_rows, latest_offers, OFFER_FIELDS)
    save_csv(unique_companies, latest_companies, COMPANY_FIELDS)
    save_csv(target_rows, history_offers, OFFER_FIELDS)
    save_csv(unique_companies, history_companies, COMPANY_FIELDS)

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

    save_json(state, STATE_FILE)

    country_counts = {
        code: sum(1 for row in target_rows if row.get("country_code") == code)
        for code in TARGET_COUNTRIES
    }

    summary = {
        "date": today,
        "search": SEARCH,
        "target_countries": TARGET_COUNTRIES,
        "previous_snapshot": previous_date,
        "total_offers_reported_by_europages": total_reported,
        "downloaded_offers": len(all_offers),
        "filtered_offers": len(target_rows),
        "unique_companies": len(unique_companies),
        "country_counts": country_counts,
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
        "download_complete": True,
        "pages_downloaded": total_pages,
    }
    save_json(summary, os.path.join(history_dir, "summary.json"))

    print()
    print("=" * 70)
    print("B2B YUG MONITOR RESULT")
    print("=" * 70)
    print("TOTAL OFFERS REPORTED BY EUROPAGES:", total_reported)
    print("DOWNLOADED:", len(all_offers))
    print("TARGET OFFERS:", len(target_rows))
    print("UNIQUE COMPANIES:", len(unique_companies))
    print("COUNTRY BREAKDOWN:")
    for code, name in TARGET_COUNTRIES.items():
        print(f"{code} - {name}: {country_counts[code]}")
    for key in (
        "new_offers", "changed_offers", "removed_offers",
        "returned_offers", "pending_removed_offers",
        "new_companies", "changed_companies", "removed_companies",
        "returned_companies", "pending_removed_companies",
    ):
        print(f"{key.upper()}: {len(result[key])}")
    print("REMOVAL RULE: removed after", REMOVAL_MISS_THRESHOLD, "successful daily misses.")
    print("LATEST OFFERS:", latest_offers)
    print("LATEST COMPANIES:", latest_companies)
    print("STATE:", STATE_FILE)
    print("HISTORY:", history_dir)
    print("=" * 70)
    print("MONITOR COMPLETE")


if __name__ == "__main__":
    main()
