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

LATEST_DIR = "data/latest"
HISTORY_DIR = "data/history"


# ============================================================
# CREATE DIRECTORIES
# ============================================================

def ensure_directories():

    os.makedirs(LATEST_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)


# ============================================================
# GET TODAY
# ============================================================

def get_today():

    return datetime.now().strftime("%Y-%m-%d")


# ============================================================
# FIND PREVIOUS SNAPSHOT
# ============================================================

def find_previous_snapshot(today):

    if not os.path.exists(HISTORY_DIR):
        return None

    dates = []

    for name in os.listdir(HISTORY_DIR):

        path = os.path.join(
            HISTORY_DIR,
            name
        )

        if not os.path.isdir(path):
            continue

        if re.match(
            r"^\d{4}-\d{2}-\d{2}$",
            name
        ):

            if name < today:
                dates.append(name)

    if not dates:
        return None

    return sorted(
        dates,
        reverse=True
    )[0]


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(filename):

    if not os.path.exists(filename):
        return []

    try:

        with open(
            filename,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            return list(reader)

    except Exception as e:

        print(
            f"ERROR loading {filename}: {e}"
        )

        return []


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

        "Accept-Language":
            "bg,en;q=0.9,en-GB;q=0.8",
    }

    response = session.get(
        f"{BASE_URL}/bg/products?q={SEARCH}",
        headers=headers,
        timeout=30,
    )

    print(
        "Homepage HTTP:",
        response.status_code
    )

    ufs_session_id = (
        session.cookies.get(
            "ufs_session_id"
        )
    )

    if ufs_session_id:

        print(
            "ufsSessionId obtained from cookie"
        )

        print(
            "Session:",
            ufs_session_id[:8] + "..."
        )

        return (
            session,
            ufs_session_id
        )

    patterns = [

        r'"ufsSessionId"\s*:\s*"([^"]+)"',

        r'"ufs_session_id"\s*:\s*"([^"]+)"',

        r'ufsSessionId=([a-zA-Z0-9]+)',

        r'ufs_session_id=([a-zA-Z0-9]+)',
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            response.text
        )

        if match:

            ufs_session_id = (
                match.group(1)
            )

            print(
                "ufsSessionId found in page"
            )

            print(
                "Session:",
                ufs_session_id[:8] + "..."
            )

            return (
                session,
                ufs_session_id
            )

    return (
        session,
        None
    )


# ============================================================
# GET PAGE
# ============================================================

def get_page(
    session,
    ufs_session_id,
    page
):

    params = {

        "callerIdentity":
            "preciseIntention",

        "enCores":
            SEARCH,

        "multiProTest":
            "true",

        "query":
            SEARCH,

        "keywordsTranslate":
            SEARCH,

        "pageSize":
            "30",

        "llmIntentionType":
            "preciseIntention",

        "coreProduct":
            SEARCH,

        "searchQuery":
            SEARCH,

        "langident":
            "bg",

        "language":
            "bg",

        "site":
            "ep",

        "ufsSessionId":
            ufs_session_id,

        "verified":
            "false",

        "topResponder":
            "false",

        "isQuickResponder":
            "false",

        "source":
            "web",

        "currency":
            "EUR",

        "terminalType":
            "pc",

        "country":
            "bg",

        "history":
            "false",

        "topLevelDomain":
            "uk",

        "needReasoning":
            "false",

        "allowTestData":
            "false",

        "page":
            str(page),
    }

    headers = {

        "Accept":
            "application/json, text/plain, */*",

        "Accept-Language":
            "bg,en;q=0.9,en-GB;q=0.8",

        "Referer":
            f"{BASE_URL}/bg/products?q={SEARCH}",

        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
        ),
    }

    try:

        response = session.get(
            BASE_URL + API_PATH,
            params=params,
            headers=headers,
            timeout=30,
        )

    except Exception as e:

        print(
            f"PAGE {page}: ERROR {e}"
        )

        return None

    print(
        f"PAGE {page}: HTTP {response.status_code}"
    )

    if response.status_code != 200:

        print(
            response.text[:1000]
        )

        return None

    try:

        return response.json()

    except Exception as e:

        print(
            f"PAGE {page}: JSON ERROR {e}"
        )

        return None


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

        return " ".join(
            value.split()
        )

    return str(value)


# ============================================================
# EXTRACT OFFER
# ============================================================

def extract_offer(offer):

    company = offer.get(
        "company",
        {}
    )

    if not isinstance(
        company,
        dict
    ):

        company = {}

    country_code = clean_text(
        company.get(
            "countryCode",
            ""
        )
    ).upper()

    country_name = (
        TARGET_COUNTRIES.get(
            country_code,
            country_code
        )
    )

    product_name = clean_text(
        offer.get(
            "name",
            ""
        )
    )

    description = clean_text(
        offer.get(
            "description",
            ""
        )
    )

    company_name = clean_text(
        company.get(
            "name",
            ""
        )
    )

    company_slug = clean_text(
        company.get(
            "slug",
            ""
        )
    )

    company_ep_slug = clean_text(
        company.get(
            "epSlug",
            ""
        )
    )

    company_uuid = clean_text(
        company.get(
            "uuid",
            ""
        )
    )

    company_id = clean_text(
        company.get(
            "companyId",
            ""
        )
    )

    ep_id = clean_text(
        company.get(
            "epId",
            ""
        )
    )

    distribution_area = clean_text(
        company.get(
            "distributionArea",
            ""
        )
    )

    founding_year = clean_text(
        company.get(
            "foundingYear",
            ""
        )
    )

    email_existing = clean_text(
        company.get(
            "emailExisting",
            ""
        )
    )

    is_ep_member = clean_text(
        company.get(
            "is_ep_member",
            ""
        )
    )

    is_wlw_member = clean_text(
        company.get(
            "is_wlw_member",
            ""
        )
    )

    is_quick_responder = clean_text(
        company.get(
            "isQuickResponder",
            ""
        )
    )

    offer_uuid = clean_text(
        offer.get(
            "uuid",
            ""
        )
    )

    auction_id = clean_text(
        offer.get(
            "auctionId",
            ""
        )
    )

    slug_id = clean_text(
        offer.get(
            "slugId",
            ""
        )
    )

    offer_slug = clean_text(
        offer.get(
            "slug",
            ""
        )
    )

    v_category = clean_text(
        offer.get(
            "vCategory",
            ""
        )
    )

    offer_url = ""

    if offer_slug:

        offer_url = (
            f"{BASE_URL}/bg/products/"
            f"{offer_slug}"
        )

    return {

        "country_code":
            country_code,

        "country":
            country_name,

        "company_name":
            company_name,

        "company_slug":
            company_slug,

        "company_ep_slug":
            company_ep_slug,

        "company_id":
            company_id,

        "company_uuid":
            company_uuid,

        "ep_id":
            ep_id,

        "distribution_area":
            distribution_area,

        "founding_year":
            founding_year,

        "email_existing":
            email_existing,

        "is_ep_member":
            is_ep_member,

        "is_wlw_member":
            is_wlw_member,

        "is_quick_responder":
            is_quick_responder,

        "product_name":
            product_name,

        "description":
            description,

        "category":
            v_category,

        "offer_uuid":
            offer_uuid,

        "auction_id":
            auction_id,

        "slug_id":
            slug_id,

        "offer_slug":
            offer_slug,

        "offer_url":
            offer_url,
    }


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(
    rows,
    filename,
    fieldnames=None
):

    if fieldnames is None:

        if rows:

            fieldnames = list(
                rows[0].keys()
            )

        else:

            fieldnames = []

    os.makedirs(
        os.path.dirname(filename)
        or ".",
        exist_ok=True
    )

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        if fieldnames:

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                extrasaction="ignore"
            )

            writer.writeheader()

            if rows:

                writer.writerows(
                    rows
                )

    print()

    if rows:

        print(
            "SAVED:",
            filename
        )

        print(
            "ROWS:",
            len(rows)
        )

    else:

        print(
            "SAVED EMPTY:",
            filename
        )

        print(
            "ROWS: 0"
        )


# ============================================================
# UNIQUE COMPANIES
# ============================================================

def create_unique_companies(
    rows
):

    companies = {}

    for row in rows:

        company_id = row.get(
            "company_id",
            ""
        )

        company_uuid = row.get(
            "company_uuid",
            ""
        )

        company_name = row.get(
            "company_name",
            ""
        )

        key = (
            row.get(
                "country_code",
                ""
            ),

            company_id
            or company_uuid
            or company_name
        )

        if key not in companies:

            companies[key] = {

                "country_code":
                    row.get(
                        "country_code",
                        ""
                    ),

                "country":
                    row.get(
                        "country",
                        ""
                    ),

                "company_name":
                    company_name,

                "company_id":
                    company_id,

                "company_uuid":
                    company_uuid,

                "company_slug":
                    row.get(
                        "company_slug",
                        ""
                    ),

                "company_ep_slug":
                    row.get(
                        "company_ep_slug",
                        ""
                    ),

                "ep_id":
                    row.get(
                        "ep_id",
                        ""
                    ),

                "distribution_area":
                    row.get(
                        "distribution_area",
                        ""
                    ),

                "founding_year":
                    row.get(
                        "founding_year",
                        ""
                    ),

                "email_existing":
                    row.get(
                        "email_existing",
                        ""
                    ),

                "is_ep_member":
                    row.get(
                        "is_ep_member",
                        ""
                    ),

                "is_wlw_member":
                    row.get(
                        "is_wlw_member",
                        ""
                    ),

                "is_quick_responder":
                    row.get(
                        "is_quick_responder",
                        ""
                    ),

                "products_count":
                    0,
            }

        companies[key][
            "products_count"
        ] += 1

    return list(
        companies.values()
    )


# ============================================================
# OFFER STABLE ID
# ============================================================

def offer_key(row):

    country = row.get(
        "country_code",
        ""
    )

    offer_uuid = row.get(
        "offer_uuid",
        ""
    )

    if offer_uuid:

        return (
            country
            + "|OFFER|"
            + offer_uuid
        )

    auction_id = row.get(
        "auction_id",
        ""
    )

    if auction_id:

        return (
            country
            + "|AUCTION|"
            + auction_id
        )

    slug_id = row.get(
        "slug_id",
        ""
    )

    if slug_id:

        return (
            country
            + "|SLUGID|"
            + slug_id
        )

    offer_slug = row.get(
        "offer_slug",
        ""
    )

    if offer_slug:

        return (
            country
            + "|SLUG|"
            + offer_slug
        )

    return (
        country
        + "|FALLBACK|"
        + row.get(
            "company_name",
            ""
        )
        + "|"
        + row.get(
            "product_name",
            ""
        )
    )


# ============================================================
# COMPANY STABLE ID
# ============================================================

def company_key(row):

    country = row.get(
        "country_code",
        ""
    )

    company_id = row.get(
        "company_id",
        ""
    )

    if company_id:

        return (
            country
            + "|COMPANY|"
            + company_id
        )

    company_uuid = row.get(
        "company_uuid",
        ""
    )

    if company_uuid:

        return (
            country
            + "|UUID|"
            + company_uuid
        )

    company_slug = row.get(
        "company_slug",
        ""
    )

    if company_slug:

        return (
            country
            + "|SLUG|"
            + company_slug
        )

    return (
        country
        + "|NAME|"
        + row.get(
            "company_name",
            ""
        )
    )


# ============================================================
# CREATE INDEX
# ============================================================

def create_index(
    rows,
    key_function
):

    result = {}

    for row in rows:

        key = key_function(
            row
        )

        result[key] = row

    return result


# ============================================================
# COMPARE RECORDS
# ============================================================

def compare_records(
    previous_rows,
    current_rows,
    key_function
):

    previous = create_index(
        previous_rows,
        key_function
    )

    current = create_index(
        current_rows,
        key_function
    )

    new_rows = []

    removed_rows = []

    changed_rows = []

    # --------------------------------------------------------
    # NEW / CHANGED
    # --------------------------------------------------------

    for key, row in current.items():

        if key not in previous:

            new_rows.append(
                row
            )

        else:

            old_row = previous[key]

            if old_row != row:

                changed = dict(
                    row
                )

                changed[
                    "_previous"
                ] = json.dumps(
                    old_row,
                    ensure_ascii=False
                )

                changed_rows.append(
                    changed
                )

    # --------------------------------------------------------
    # REMOVED
    # --------------------------------------------------------

    for key, row in previous.items():

        if key not in current:

            removed_rows.append(
                row
            )

    return (
        new_rows,
        removed_rows,
        changed_rows
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    data,
    filename
):

    os.makedirs(
        os.path.dirname(filename)
        or ".",
        exist_ok=True
    )

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

    ensure_directories()

    today = get_today()

    print("=" * 70)
    print(
        "EUROPAGES - B2B YUG MONITOR"
    )
    print(
        "HISTORY + NEW / REMOVED / CHANGED VERSION"
    )
    print("=" * 70)

    print()
    print(
        "DATE:",
        today
    )

    print(
        "SEARCH:",
        SEARCH
    )

    print()
    print(
        "TARGET COUNTRIES:",
        ", ".join(
            TARGET_COUNTRIES.values()
        )
    )

    # ========================================================
    # FIND PREVIOUS SNAPSHOT
    # ========================================================

    previous_date = (
        find_previous_snapshot(
            today
        )
    )

    previous_offers = []
    previous_companies = []

    if previous_date:

        previous_dir = os.path.join(
            HISTORY_DIR,
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
        print(
            "NO PREVIOUS SNAPSHOT FOUND"
        )

    # ========================================================
    # SESSION
    # ========================================================

    session, ufs_session_id = (
        create_session()
    )

    if not ufs_session_id:

        print()
        print(
            "ERROR: ufsSessionId not found."
        )

        return

    print()
    print("=" * 70)
    print(
        "DOWNLOADING EUROPAGES DATA"
    )
    print("=" * 70)

    # ========================================================
    # FIRST PAGE
    # ========================================================

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

    try:

        total_pages = int(
            paging.get(
                "totalPages",
                1
            )
        )

    except Exception:

        total_pages = 1

    total_offers = paging.get(
        "total",
        0
    )

    all_offers = []

    # ========================================================
    # ALL PAGES
    # ========================================================

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

    # ========================================================
    # FILTER
    # ========================================================

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

    # ========================================================
    # EXTRACT
    # ========================================================

    rows = []

    for country in [
        "RO",
        "GR"
    ]:

        for offer in target_offers[
            country
        ]:

            rows.append(
                extract_offer(
                    offer
                )
            )

    # ========================================================
    # UNIQUE COMPANIES
    # ========================================================

    unique_companies = (
        create_unique_companies(
            rows
        )
    )

    # ========================================================
    # COMPARE
    # ========================================================

    (
        new_offers,
        removed_offers,
        changed_offers
    ) = compare_records(
        previous_offers,
        rows,
        offer_key
    )

    (
        new_companies,
        removed_companies,
        changed_companies
    ) = compare_records(
        previous_companies,
        unique_companies,
        company_key
    )

    # ========================================================
    # TODAY DIRECTORY
    # ========================================================

    today_dir = os.path.join(
        HISTORY_DIR,
        today
    )

    os.makedirs(
        today_dir,
        exist_ok=True
    )

    # ========================================================
    # LATEST
    # ========================================================

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

    # ========================================================
    # DAILY SNAPSHOT
    # ========================================================

    save_csv(
        rows,
        os.path.join(
            today_dir,
            "offers_ro_gr.csv"
        )
    )

    save_csv(
        unique_companies,
        os.path.join(
            today_dir,
            "companies_ro_gr.csv"
        )
    )

    # ========================================================
    # DAILY CHANGES
    # ========================================================

    offer_fields = (
        list(rows[0].keys())
        if rows
        else [
            "country_code",
            "country",
            "company_name",
            "product_name",
            "offer_uuid",
            "offer_url"
        ]
    )

    company_fields = (
        list(
            unique_companies[0].keys()
        )
        if unique_companies
        else [
            "country_code",
            "country",
            "company_name",
            "company_id",
            "company_uuid",
            "products_count"
        ]
    )

    # Changed offers have _previous
    changed_offer_fields = (
        offer_fields
        + ["_previous"]
    )

    changed_company_fields = (
        company_fields
        + ["_previous"]
    )

    save_csv(
        new_offers,
        os.path.join(
            today_dir,
            "new_offers.csv"
        ),
        offer_fields
    )

    save_csv(
        removed_offers,
        os.path.join(
            today_dir,
            "removed_offers.csv"
        ),
        offer_fields
    )

    save_csv(
        changed_offers,
        os.path.join(
            today_dir,
            "changed_offers.csv"
        ),
        changed_offer_fields
    )

    save_csv(
        new_companies,
        os.path.join(
            today_dir,
            "new_companies.csv"
        ),
        company_fields
    )

    save_csv(
        removed_companies,
        os.path.join(
            today_dir,
            "removed_companies.csv"
        ),
        company_fields
    )

    save_csv(
        changed_companies,
        os.path.join(
            today_dir,
            "changed_companies.csv"
        ),
        changed_company_fields
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {

        "date":
            today,

        "search":
            SEARCH,

        "target_countries":
            TARGET_COUNTRIES,

        "previous_date":
            previous_date,

        "total_offers":
            total_offers,

        "downloaded":
            len(all_offers),

        "romania_offers":
            len(
                target_offers["RO"]
            ),

        "greece_offers":
            len(
                target_offers["GR"]
            ),

        "total_ro_gr":
            len(rows),

        "unique_companies":
            len(
                unique_companies
            ),

        "new_offers":
            len(
                new_offers
            ),

        "removed_offers":
            len(
                removed_offers
            ),

        "changed_offers":
            len(
                changed_offers
            ),

        "new_companies":
            len(
                new_companies
            ),

        "removed_companies":
            len(
                removed_companies
            ),

        "changed_companies":
            len(
                changed_companies
            ),
    }

    save_json(
        summary,
        os.path.join(
            today_dir,
            "summary.json"
        )
    )

    # ========================================================
    # RESULT
    # ========================================================

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
        len(
            target_offers["RO"]
        )
    )

    print(
        "GREECE OFFERS:",
        len(
            target_offers["GR"]
        )
    )

    print(
        "TOTAL RO + GR:",
        len(rows)
    )

    print(
        "UNIQUE COMPANIES:",
        len(
            unique_companies
        )
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
    print(
        "MONITOR COMPLETE"
    )
    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
