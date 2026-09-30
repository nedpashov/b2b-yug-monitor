import requests
import json
import time
import re
import csv
import os
from datetime import datetime, timedelta


# ============================================================
# EUROPAGES - B2B YUG MONITOR
# HISTORY + NEW / REMOVED / CHANGED VERSION
# ============================================================

SEARCH = "packaging"

TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция",
}

BASE_URL = "https://www.europages.co.uk"

API_PATH = "/search-api-proxy/online.aiSearch.productTextSearch"

TODAY = datetime.now().strftime("%Y-%m-%d")

DATA_DIR = "data"
LATEST_DIR = os.path.join(DATA_DIR, "latest")
HISTORY_DIR = os.path.join(DATA_DIR, "history", TODAY)


# ============================================================
# DIRECTORIES
# ============================================================

def create_directories():

    os.makedirs(LATEST_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)


# ============================================================
# CREATE SESSION
# ============================================================

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
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "bg,en;q=0.9,en-GB;q=0.8",
    }

    response = session.get(
        f"{BASE_URL}/bg/products?q={SEARCH}",
        headers=headers,
        timeout=30,
    )

    print("Homepage HTTP:", response.status_code)

    ufs_session_id = session.cookies.get("ufs_session_id")

    if ufs_session_id:

        print("ufsSessionId obtained from cookie")
        print("Session:", ufs_session_id[:8] + "...")

        return session, ufs_session_id

    patterns = [
        r'"ufsSessionId"\s*:\s*"([^"]+)"',
        r'"ufs_session_id"\s*:\s*"([^"]+)"',
        r'ufsSessionId=([a-zA-Z0-9]+)',
        r'ufs_session_id=([a-zA-Z0-9]+)',
    ]

    for pattern in patterns:

        match = re.search(pattern, response.text)

        if match:

            ufs_session_id = match.group(1)

            print("ufsSessionId found in page")
            print("Session:", ufs_session_id[:8] + "...")

            return session, ufs_session_id

    return session, None


# ============================================================
# GET PAGE
# ============================================================

def get_page(session, ufs_session_id, page):

    params = {
        "callerIdentity": "preciseIntention",
        "enCores": SEARCH,
        "multiProTest": "true",
        "query": SEARCH,
        "keywordsTranslate": SEARCH,
        "pageSize": "30",
        "llmIntentionType": "preciseIntention",
        "coreProduct": SEARCH,
        "searchQuery": SEARCH,
        "langident": "bg",
        "language": "bg",
        "site": "ep",
        "ufsSessionId": ufs_session_id,
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

    response = session.get(
        BASE_URL + API_PATH,
        params=params,
        headers=headers,
        timeout=30,
    )

    print(f"PAGE {page}: HTTP {response.status_code}")

    if response.status_code != 200:

        print(response.text[:1000])

        return None

    try:

        return response.json()

    except Exception as e:

        print("JSON ERROR:", e)

        return None


# ============================================================
# COUNTRY
# ============================================================

def get_country(offer):

    try:

        return (
            offer
            .get("company", {})
            .get("countryCode", "")
            .upper()
        )

    except Exception:

        return ""


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if value is None:

        return ""

    if isinstance(value, str):

        return " ".join(value.split())

    return str(value)


# ============================================================
# EXTRACT OFFER
# ============================================================

def extract_offer(offer):

    company = offer.get("company", {})

    if not isinstance(company, dict):

        company = {}

    country_code = clean_text(
        company.get("countryCode", "")
    ).upper()

    country_name = TARGET_COUNTRIES.get(
        country_code,
        country_code
    )

    product_name = clean_text(
        offer.get("name", "")
    )

    description = clean_text(
        offer.get("description", "")
    )

    company_name = clean_text(
        company.get("name", "")
    )

    company_slug = clean_text(
        company.get("slug", "")
    )

    company_ep_slug = clean_text(
        company.get("epSlug", "")
    )

    company_uuid = clean_text(
        company.get("uuid", "")
    )

    company_id = clean_text(
        company.get("companyId", "")
    )

    ep_id = clean_text(
        company.get("epId", "")
    )

    distribution_area = clean_text(
        company.get("distributionArea", "")
    )

    founding_year = clean_text(
        company.get("foundingYear", "")
    )

    email_existing = clean_text(
        company.get("emailExisting", "")
    )

    is_ep_member = clean_text(
        company.get("is_ep_member", "")
    )

    is_wlw_member = clean_text(
        company.get("is_wlw_member", "")
    )

    is_quick_responder = clean_text(
        company.get("isQuickResponder", "")
    )

    offer_uuid = clean_text(
        offer.get("uuid", "")
    )

    auction_id = clean_text(
        offer.get("auctionId", "")
    )

    slug_id = clean_text(
        offer.get("slugId", "")
    )

    offer_slug = clean_text(
        offer.get("slug", "")
    )

    v_category = clean_text(
        offer.get("vCategory", "")
    )

    offer_url = ""

    if offer_slug:

        offer_url = (
            f"{BASE_URL}/bg/products/"
            f"{offer_slug}"
        )

    return {

        "country_code": country_code,

        "country": country_name,

        "company_name": company_name,

        "company_slug": company_slug,

        "company_ep_slug": company_ep_slug,

        "company_id": company_id,

        "company_uuid": company_uuid,

        "ep_id": ep_id,

        "distribution_area": distribution_area,

        "founding_year": founding_year,

        "email_existing": email_existing,

        "is_ep_member": is_ep_member,

        "is_wlw_member": is_wlw_member,

        "is_quick_responder": is_quick_responder,

        "product_name": product_name,

        "description": description,

        "category": v_category,

        "offer_uuid": offer_uuid,

        "auction_id": auction_id,

        "slug_id": slug_id,

        "offer_slug": offer_slug,

        "offer_url": offer_url,
    }


# ============================================================
# CSV SAVE
# ============================================================

def save_csv(rows, filename, fieldnames=None):

    if fieldnames is None:

        if rows:

            fieldnames = list(rows[0].keys())

        else:

            fieldnames = [
                "country_code",
                "country",
                "company_name",
                "company_slug",
                "company_ep_slug",
                "company_id",
                "company_uuid",
                "ep_id",
                "distribution_area",
                "founding_year",
                "email_existing",
                "is_ep_member",
                "is_wlw_member",
                "is_quick_responder",
                "product_name",
                "description",
                "category",
                "offer_uuid",
                "auction_id",
                "slug_id",
                "offer_slug",
                "offer_url",
            ]

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()

        if rows:

            writer.writerows(rows)

    print()
    print("SAVED:", filename)
    print("ROWS:", len(rows))


# ============================================================
# CSV LOAD
# ============================================================

def load_csv(filename):

    if not os.path.exists(filename):

        return []

    try:

        with open(
            filename,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as f:

            return list(
                csv.DictReader(f)
            )

    except Exception as e:

        print(
            f"ERROR loading {filename}: {e}"
        )

        return []


# ============================================================
# FIND PREVIOUS SNAPSHOT
# ============================================================

def find_previous_snapshot():

    history_root = os.path.join(
        DATA_DIR,
        "history"
    )

    if not os.path.exists(history_root):

        return None

    dates = []

    for name in os.listdir(history_root):

        path = os.path.join(
            history_root,
            name
        )

        if os.path.isdir(path):

            try:

                datetime.strptime(
                    name,
                    "%Y-%m-%d"
                )

                if name < TODAY:

                    dates.append(name)

            except ValueError:

                pass

    if not dates:

        return None

    return sorted(
        dates,
        reverse=True
    )[0]


# ============================================================
# OFFER KEY
# ============================================================

def offer_key(row):

    uuid = clean_text(
        row.get("offer_uuid", "")
    )

    if uuid:

        return "UUID:" + uuid

    slug = clean_text(
        row.get("offer_slug", "")
    )

    if slug:

        return "SLUG:" + slug

    auction_id = clean_text(
        row.get("auction_id", "")
    )

    if auction_id:

        return "AUCTION:" + auction_id

    return "|".join([
        clean_text(row.get("country_code", "")),
        clean_text(row.get("company_name", "")),
        clean_text(row.get("product_name", "")),
    ])


# ============================================================
# COMPANY KEY
# ============================================================

def company_key(row):

    company_id = clean_text(
        row.get("company_id", "")
    )

    if company_id:

        return (
            "ID:"
            + clean_text(row.get("country_code", ""))
            + ":"
            + company_id
        )

    company_uuid = clean_text(
        row.get("company_uuid", "")
    )

    if company_uuid:

        return "UUID:" + company_uuid

    return "|".join([
        clean_text(row.get("country_code", "")),
        clean_text(row.get("company_name", "")),
    ])


# ============================================================
# CREATE UNIQUE COMPANIES
# ============================================================

def create_unique_companies(rows):

    companies = {}

    for row in rows:

        key = company_key(row)

        if key not in companies:

            companies[key] = {

                "country_code":
                    row.get("country_code", ""),

                "country":
                    row.get("country", ""),

                "company_name":
                    row.get("company_name", ""),

                "company_id":
                    row.get("company_id", ""),

                "company_uuid":
                    row.get("company_uuid", ""),

                "company_slug":
                    row.get("company_slug", ""),

                "company_ep_slug":
                    row.get("company_ep_slug", ""),

                "ep_id":
                    row.get("ep_id", ""),

                "distribution_area":
                    row.get("distribution_area", ""),

                "founding_year":
                    row.get("founding_year", ""),

                "email_existing":
                    row.get("email_existing", ""),

                "is_ep_member":
                    row.get("is_ep_member", ""),

                "is_wlw_member":
                    row.get("is_wlw_member", ""),

                "is_quick_responder":
                    row.get("is_quick_responder", ""),

                "products_count":
                    0,
            }

        companies[key]["products_count"] += 1

    return list(companies.values())


# ============================================================
# COMPARE DATA
# ============================================================

def compare_data(previous, current, key_function):

    previous_map = {
        key_function(row): row
        for row in previous
    }

    current_map = {
        key_function(row): row
        for row in current
    }

    previous_keys = set(
        previous_map.keys()
    )

    current_keys = set(
        current_map.keys()
    )

    new_keys = (
        current_keys
        - previous_keys
    )

    removed_keys = (
        previous_keys
        - current_keys
    )

    common_keys = (
        current_keys
        & previous_keys
    )

    new_rows = [
        current_map[key]
        for key in new_keys
    ]

    removed_rows = [
        previous_map[key]
        for key in removed_keys
    ]

    changed_rows = []

    for key in common_keys:

        old = previous_map[key]

        new = current_map[key]

        if old != new:

            changed = dict(new)

            changed["_previous"] = json.dumps(
                old,
                ensure_ascii=False
            )

            changed_rows.append(
                changed
            )

    return (
        new_rows,
        removed_rows,
        changed_rows
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(data, filename):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("HISTORY + NEW / REMOVED / CHANGED VERSION")
    print("=" * 70)

    print()
    print("DATE:", TODAY)
    print("SEARCH:", SEARCH)

    print()
    print(
        "TARGET COUNTRIES:",
        ", ".join(TARGET_COUNTRIES.values())
    )

    create_directories()

    # --------------------------------------------------------
    # FIND PREVIOUS DAY
    # --------------------------------------------------------

    previous_date = find_previous_snapshot()

    previous_offers = []
    previous_companies = []

    if previous_date:

        previous_dir = os.path.join(
            DATA_DIR,
            "history",
            previous_date
        )

        previous_offers_file = os.path.join(
            previous_dir,
            "offers_ro_gr.csv"
        )

        previous_companies_file = os.path.join(
            previous_dir,
            "companies_ro_gr.csv"
        )

        previous_offers = load_csv(
            previous_offers_file
        )

        previous_companies = load_csv(
            previous_companies_file
        )

        print()
        print(
            "PREVIOUS SNAPSHOT FOUND:",
            previous_date
        )

        print(
            "COMPARISON SOURCE:",
            previous_dir
        )

        print(
            "PREVIOUS OFFERS:",
            len(previous_offers)
        )

        print(
            "PREVIOUS COMPANIES:",
            len(previous_companies)
        )

    else:

        print()
        print("NO PREVIOUS SNAPSHOT FOUND")

    # --------------------------------------------------------
    # CREATE SESSION
    # --------------------------------------------------------

    session, ufs_session_id = create_session()

    if not ufs_session_id:

        print()
        print(
            "ERROR: ufsSessionId not found."
        )

        return

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("DOWNLOADING EUROPAGES DATA")
    print("=" * 70)

    first_data = get_page(
        session,
        ufs_session_id,
        1
    )

    if not first_data:

        print("First page failed.")

        return

    model = first_data.get(
        "model",
        {}
    )

    paging = model.get(
        "paging",
        {}
    )

    total_pages = int(
        paging.get(
            "totalPages",
            1
        )
    )

    total_offers = paging.get(
        "total",
        0
    )

    all_offers = []

    # --------------------------------------------------------
    # ALL PAGES
    # --------------------------------------------------------

    for page in range(
        1,
        total_pages + 1
    ):

        if page == 1:

            data = first_data

        else:

            time.sleep(1)

            data = get_page(
                session,
                ufs_session_id,
                page
            )

        if not data:

            continue

        offers = (
            data
            .get("model", {})
            .get("offers", [])
        )

        all_offers.extend(
            offers
        )

    # --------------------------------------------------------
    # FILTER COUNTRIES
    # --------------------------------------------------------

    target_offers = {
        "RO": [],
        "GR": [],
    }

    for offer in all_offers:

        country = get_country(
            offer
        )

        if country in target_offers:

            target_offers[
                country
            ].append(
                offer
            )

    # --------------------------------------------------------
    # EXTRACT
    # --------------------------------------------------------

    rows = []

    for country in [
        "RO",
        "GR"
    ]:

        for offer in target_offers[country]:

            rows.append(
                extract_offer(
                    offer
                )
            )

    # --------------------------------------------------------
    # UNIQUE COMPANIES
    # --------------------------------------------------------

    unique_companies = (
        create_unique_companies(
            rows
        )
    )

    # --------------------------------------------------------
    # COMPARE
    # --------------------------------------------------------

    if previous_date:

        (
            new_offers,
            removed_offers,
            changed_offers
        ) = compare_data(
            previous_offers,
            rows,
            offer_key
        )

        (
            new_companies,
            removed_companies,
            changed_companies
        ) = compare_data(
            previous_companies,
            unique_companies,
            company_key
        )

    else:

        new_offers = rows

        removed_offers = []

        changed_offers = []

        new_companies = unique_companies

        removed_companies = []

        changed_companies = []

    # --------------------------------------------------------
    # SAVE LATEST
    # --------------------------------------------------------

    save_csv(
        rows,
        os.path.join(
            LATEST_DIR,
            "offers_ro_gr.csv"
        )
    )

    save_csv(
        unique_companies,
        os.path.join(
            LATEST_DIR,
            "companies_ro_gr.csv"
        )
    )

    # --------------------------------------------------------
    # SAVE TODAY SNAPSHOT
    # --------------------------------------------------------

    save_csv(
        rows,
        os.path.join(
            HISTORY_DIR,
            "offers_ro_gr.csv"
        )
    )

    save_csv(
        unique_companies,
        os.path.join(
            HISTORY_DIR,
            "companies_ro_gr.csv"
        )
    )

    # --------------------------------------------------------
    # SAVE CHANGES
    # --------------------------------------------------------

    save_csv(
        new_offers,
        os.path.join(
            HISTORY_DIR,
            "new_offers.csv"
        )
    )

    save_csv(
        removed_offers,
        os.path.join(
            HISTORY_DIR,
            "removed_offers.csv"
        )
    )

    save_csv(
        changed_offers,
        os.path.join(
            HISTORY_DIR,
            "changed_offers.csv"
        )
    )

    save_csv(
        new_companies,
        os.path.join(
            HISTORY_DIR,
            "new_companies.csv"
        )
    )

    save_csv(
        removed_companies,
        os.path.join(
            HISTORY_DIR,
            "removed_companies.csv"
        )
    )

    save_csv(
        changed_companies,
        os.path.join(
            HISTORY_DIR,
            "changed_companies.csv"
        )
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = {

        "date": TODAY,

        "search": SEARCH,

        "target_countries":
            TARGET_COUNTRIES,

        "previous_date":
            previous_date,

        "total_offers":
            total_offers,

        "downloaded_offers":
            len(all_offers),

        "romania_offers":
            len(target_offers["RO"]),

        "greece_offers":
            len(target_offers["GR"]),

        "total_target_offers":
            len(rows),

        "unique_companies":
            len(unique_companies),

        "new_offers":
            len(new_offers),

        "removed_offers":
            len(removed_offers),

        "changed_offers":
            len(changed_offers),

        "new_companies":
            len(new_companies),

        "removed_companies":
            len(removed_companies),

        "changed_companies":
            len(changed_companies),
    }

    save_json(
        summary,
        os.path.join(
            HISTORY_DIR,
            "summary.json"
        )
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    print(
        "TOTAL OFFERS:",
        total_offers
    )

    print(
        "DOWNLOADED:",
        len(all_offers)
    )

    print(
        "ROMANIA OFFERS:",
        len(target_offers["RO"])
    )

    print(
        "GREECE OFFERS:",
        len(target_offers["GR"])
    )

    print(
        "TOTAL RO + GR:",
        len(rows)
    )

    print(
        "UNIQUE COMPANIES:",
        len(unique_companies)
    )

    print()

    print(
        "NEW OFFERS:",
        len(new_offers)
    )

    print(
        "REMOVED OFFERS:",
        len(removed_offers)
    )

    print(
        "CHANGED OFFERS:",
        len(changed_offers)
    )

    print()

    print(
        "NEW COMPANIES:",
        len(new_companies)
    )

    print(
        "REMOVED COMPANIES:",
        len(removed_companies)
    )

    print(
        "CHANGED COMPANIES:",
        len(changed_companies)
    )

    print()
    print("=" * 70)
    print("MONITOR COMPLETE")
    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
   
