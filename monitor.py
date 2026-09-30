import requests
import json
import time
import re
import csv
import os
from datetime import datetime


# ============================================================
# EUROPAGES - B2B YUG MONITOR
# EXPORT + HISTORY VERSION
# ============================================================

SEARCH = "packaging"

TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция",
}

BASE_URL = "https://www.europages.co.uk"
API_PATH = "/search-api-proxy/online.aiSearch.productTextSearch"


# ============================================================
# DIRECTORIES
# ============================================================

TODAY = datetime.now().strftime("%Y-%m-%d")

LATEST_DIR = "data/latest"
HISTORY_ROOT = "data/history"
TODAY_HISTORY_DIR = f"{HISTORY_ROOT}/{TODAY}"

os.makedirs(LATEST_DIR, exist_ok=True)
os.makedirs(TODAY_HISTORY_DIR, exist_ok=True)


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

    return response.json()


# ============================================================
# GET COUNTRY
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

    email_existing = company.get(
        "emailExisting",
        ""
    )

    is_ep_member = company.get(
        "is_ep_member",
        ""
    )

    is_wlw_member = company.get(
        "is_wlw_member",
        ""
    )

    is_quick_responder = company.get(
        "isQuickResponder",
        ""
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

        "date": TODAY,

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
# SAVE CSV
# ============================================================

def save_csv(rows, filename, fieldnames=None):

    if fieldnames is None:

        if rows:
            fieldnames = list(rows[0].keys())
        else:
            fieldnames = []

    if not fieldnames:

        print("No data to save:", filename)

        return

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        if rows:
            writer.writerows(rows)

    print()
    print("SAVED:", filename)
    print("ROWS:", len(rows))


# ============================================================
# UNIQUE COMPANIES
# ============================================================

def create_unique_companies(rows):

    companies = {}

    for row in rows:

        key = (
            row["country_code"],
            row["company_id"],
            row["company_name"]
        )

        if key not in companies:

            companies[key] = {

                "date":
                    TODAY,

                "country_code":
                    row["country_code"],

                "country":
                    row["country"],

                "company_name":
                    row["company_name"],

                "company_id":
                    row["company_id"],

                "company_uuid":
                    row["company_uuid"],

                "company_slug":
                    row["company_slug"],

                "company_ep_slug":
                    row["company_ep_slug"],

                "ep_id":
                    row["ep_id"],

                "distribution_area":
                    row["distribution_area"],

                "founding_year":
                    row["founding_year"],

                "email_existing":
                    row["email_existing"],

                "is_ep_member":
                    row["is_ep_member"],

                "is_wlw_member":
                    row["is_wlw_member"],

                "is_quick_responder":
                    row["is_quick_responder"],

                "products_count":
                    0,
            }

        companies[key]["products_count"] += 1

    return list(companies.values())


# ============================================================
# FIND PREVIOUS HISTORY DIRECTORY
# ============================================================

def find_comparison_directory():

    # --------------------------------------------------------
    # If today's history already exists, use today's previous
    # snapshot. This makes repeated runs on the same day safe.
    # --------------------------------------------------------

    today_offers = (
        f"{TODAY_HISTORY_DIR}/offers_ro_gr.csv"
    )

    today_companies = (
        f"{TODAY_HISTORY_DIR}/companies_ro_gr.csv"
    )

    if os.path.exists(today_offers):

        print()
        print(
            "TODAY'S PREVIOUS SNAPSHOT FOUND:",
            TODAY
        )

        return TODAY_HISTORY_DIR

    # --------------------------------------------------------
    # Otherwise find the newest history directory BEFORE today
    # --------------------------------------------------------

    if not os.path.exists(HISTORY_ROOT):

        return None

    directories = []

    for name in os.listdir(HISTORY_ROOT):

        path = os.path.join(
            HISTORY_ROOT,
            name
        )

        if not os.path.isdir(path):
            continue

        if name == TODAY:
            continue

        try:

            datetime.strptime(
                name,
                "%Y-%m-%d"
            )

            directories.append(name)

        except ValueError:

            continue

    if not directories:

        return None

    previous_date = max(directories)

    return os.path.join(
        HISTORY_ROOT,
        previous_date
    )


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(filename):

    if not os.path.exists(filename):

        return []

    rows = []

    try:

        with open(
            filename,
            "r",
            encoding="utf-8-sig"
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:
                rows.append(row)

    except Exception as e:

        print(
            "ERROR READING:",
            filename,
            e
        )

        return []

    return rows


# ============================================================
# LOAD COMPARISON DATA
# ============================================================

def load_comparison_data():

    comparison_dir = (
        find_comparison_directory()
    )

    if not comparison_dir:

        print()
        print("NO PREVIOUS HISTORY FOUND")

        return [], []

    offers_file = (
        f"{comparison_dir}/offers_ro_gr.csv"
    )

    companies_file = (
        f"{comparison_dir}/companies_ro_gr.csv"
    )

    previous_offers = load_csv(
        offers_file
    )

    previous_companies = load_csv(
        companies_file
    )

    print()
    print(
        "COMPARISON SOURCE:",
        comparison_dir
    )

    print(
        "PREVIOUS OFFERS:",
        len(previous_offers)
    )

    print(
        "PREVIOUS COMPANIES:",
        len(previous_companies)
    )

    return (
        previous_offers,
        previous_companies
    )


# ============================================================
# OFFER KEY
# ============================================================

def get_offer_key(row):

    offer_uuid = row.get(
        "offer_uuid",
        ""
    )

    if offer_uuid:

        return (
            row.get("country_code", ""),
            offer_uuid
        )

    return (
        row.get("country_code", ""),
        row.get("company_id", ""),
        row.get("product_name", ""),
        row.get("offer_slug", "")
    )


# ============================================================
# COMPANY KEY
# ============================================================

def get_company_key(row):

    company_id = row.get(
        "company_id",
        ""
    )

    if company_id:

        return (
            row.get("country_code", ""),
            company_id
        )

    return (
        row.get("country_code", ""),
        row.get("company_name", "")
    )


# ============================================================
# FIND NEW OFFERS
# ============================================================

def find_new_offers(
    current_rows,
    previous_rows
):

    previous_keys = {
        get_offer_key(row)
        for row in previous_rows
    }

    new_rows = []

    for row in current_rows:

        key = get_offer_key(row)

        if key not in previous_keys:

            new_rows.append(row)

    return new_rows


# ============================================================
# FIND NEW COMPANIES
# ============================================================

def find_new_companies(
    current_companies,
    previous_companies
):

    previous_keys = {
        get_company_key(row)
        for row in previous_companies
    }

    new_companies = []

    for row in current_companies:

        key = get_company_key(row)

        if key not in previous_keys:

            new_companies.append(row)

    return new_companies


# ============================================================
# SAVE SUMMARY
# ============================================================

def save_summary(
    total_offers,
    downloaded,
    ro_count,
    gr_count,
    rows,
    unique_companies,
    new_offers,
    new_companies
):

    summary = {

        "date":
            TODAY,

        "search":
            SEARCH,

        "total_offers_europages":
            total_offers,

        "downloaded":
            downloaded,

        "romania_offers":
            ro_count,

        "greece_offers":
            gr_count,

        "total_ro_gr":
            len(rows),

        "unique_companies":
            len(unique_companies),

        "new_offers":
            len(new_offers),

        "new_companies":
            len(new_companies),
    }

    filename = (
        f"{TODAY_HISTORY_DIR}/summary.json"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("SAVED:", filename)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("EXPORT + HISTORY VERSION")
    print("=" * 70)

    print()
    print("DATE:", TODAY)
    print("SEARCH:", SEARCH)

    print()
    print(
        "TARGET COUNTRIES:",
        ", ".join(TARGET_COUNTRIES.values())
    )

    # --------------------------------------------------------
    # LOAD PREVIOUS HISTORY
    # --------------------------------------------------------

    (
        previous_offers,
        previous_companies
    ) = load_comparison_data()

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

    print()
    print("=" * 70)
    print("DOWNLOADING EUROPAGES DATA")
    print("=" * 70)

    # --------------------------------------------------------
    # FIRST PAGE
    # --------------------------------------------------------

    first_data = get_page(
        session,
        ufs_session_id,
        1
    )

    if not first_data:

        print(
            "First page failed."
        )

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

            row = extract_offer(
                offer
            )

            rows.append(
                row
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
    # FIND NEW OFFERS
    # --------------------------------------------------------

    new_offers = find_new_offers(
        rows,
        previous_offers
    )

    # --------------------------------------------------------
    # FIND NEW COMPANIES
    # --------------------------------------------------------

    new_companies = find_new_companies(
        unique_companies,
        previous_companies
    )

    # --------------------------------------------------------
    # FIELD NAMES
    # --------------------------------------------------------

    offer_fields = [
        "date",
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

    company_fields = [
        "date",
        "country_code",
        "country",
        "company_name",
        "company_id",
        "company_uuid",
        "company_slug",
        "company_ep_slug",
        "ep_id",
        "distribution_area",
        "founding_year",
        "email_existing",
        "is_ep_member",
        "is_wlw_member",
        "is_quick_responder",
        "products_count",
    ]

    # --------------------------------------------------------
    # SAVE LATEST
    # --------------------------------------------------------

    save_csv(
        rows,
        f"{LATEST_DIR}/offers_ro_gr.csv",
        offer_fields
    )

    save_csv(
        unique_companies,
        f"{LATEST_DIR}/companies_ro_gr.csv",
        company_fields
    )

    # --------------------------------------------------------
    # SAVE TODAY HISTORY
    # --------------------------------------------------------

    save_csv(
        rows,
        f"{TODAY_HISTORY_DIR}/offers_ro_gr.csv",
        offer_fields
    )

    save_csv(
        unique_companies,
        f"{TODAY_HISTORY_DIR}/companies_ro_gr.csv",
        company_fields
    )

    # --------------------------------------------------------
    # SAVE NEW OFFERS
    # --------------------------------------------------------

    save_csv(
        new_offers,
        f"{TODAY_HISTORY_DIR}/new_offers.csv",
        offer_fields
    )

    # --------------------------------------------------------
    # SAVE NEW COMPANIES
    # --------------------------------------------------------

    save_csv(
        new_companies,
        f"{TODAY_HISTORY_DIR}/new_companies.csv",
        company_fields
    )

    # --------------------------------------------------------
    # SAVE CLEAN JSON
    # --------------------------------------------------------

    with open(
        f"{LATEST_DIR}/offers_ro_gr_clean.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            rows,
            f,
            ensure_ascii=False,
            indent=2
        )

    with open(
        f"{TODAY_HISTORY_DIR}/offers_ro_gr_clean.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            rows,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # SAVE SUMMARY
    # --------------------------------------------------------

    save_summary(
        total_offers,
        len(all_offers),
        len(target_offers["RO"]),
        len(target_offers["GR"]),
        rows,
        unique_companies,
        new_offers,
        new_companies
    )

    # --------------------------------------------------------
    # SUMMARY
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
        "NEW COMPANIES:",
        len(new_companies)
    )

    print()
    print("=" * 70)
    print("FILES CREATED")
    print("=" * 70)

    print(
        f"{LATEST_DIR}/offers_ro_gr.csv"
    )

    print(
        f"{LATEST_DIR}/companies_ro_gr.csv"
    )

    print(
        f"{TODAY_HISTORY_DIR}/offers_ro_gr.csv"
    )

    print(
        f"{TODAY_HISTORY_DIR}/companies_ro_gr.csv"
    )

    print(
        f"{TODAY_HISTORY_DIR}/new_offers.csv"
    )

    print(
        f"{TODAY_HISTORY_DIR}/new_companies.csv"
    )

    print(
        f"{TODAY_HISTORY_DIR}/summary.json"
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

   
