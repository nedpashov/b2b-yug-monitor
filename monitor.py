import requests
import json
import time
import re
import csv


# ============================================================
# EUROPAGES - B2B YUG MONITOR
# EXPORT VERSION
# ============================================================

SEARCH = "packaging"

TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция",
}

BASE_URL = "https://www.europages.co.uk"
API_PATH = "/search-api-proxy/online.aiSearch.productTextSearch"


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

    country_code = company.get("countryCode", "")

    country_code = clean_text(country_code).upper()

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

    # Europages product URL
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
# SAVE CSV
# ============================================================

def save_csv(rows, filename):

    if not rows:

        print("No data to save.")

        return

    fieldnames = list(rows[0].keys())

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
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("EXPORT VERSION")
    print("=" * 70)

    print()
    print("SEARCH:", SEARCH)

    print()
    print(
        "TARGET COUNTRIES:",
        ", ".join(TARGET_COUNTRIES.values())
    )

    session, ufs_session_id = create_session()

    if not ufs_session_id:

        print()
        print("ERROR: ufsSessionId not found.")

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
    # FILTER
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
    # SAVE
    # --------------------------------------------------------

    save_csv(
        rows,
        "offers_ro_gr.csv"
    )

    save_csv(
        unique_companies,
        "companies_ro_gr.csv"
    )

    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    with open(
        "offers_ro_gr_clean.json",
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
    print("=" * 70)
    print("FILES CREATED")
    print("=" * 70)

    print("offers_ro_gr.csv")
    print("companies_ro_gr.csv")
    print("offers_ro_gr_clean.json")

    print()
    print("=" * 70)
    print("MONITOR COMPLETE")
    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
