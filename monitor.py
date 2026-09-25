import requests
import json
import time
import re


# ============================================================
# EUROPAGES - B2B YUG MONITOR
# DIAGNOSTIC VERSION
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
# FIND COUNTRY
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
# PRINT OFFER STRUCTURE
# ============================================================

def print_offer(index, offer, country):

    print()
    print("=" * 70)
    print(
        f"{TARGET_COUNTRIES[country].upper()} "
        f"- OFFER {index}"
    )
    print("=" * 70)

    print()
    print("TOP LEVEL FIELDS:")
    print("-" * 70)

    for key, value in offer.items():

        if isinstance(value, (dict, list)):

            print(
                f"- {key} "
                f"[{type(value).__name__}]"
            )

        else:

            text = str(value)

            if len(text) > 300:
                text = text[:300] + "..."

            print(
                f"- {key}: {text}"
            )

    # --------------------------------------------------------
    # COMPANY
    # --------------------------------------------------------

    company = offer.get("company")

    if isinstance(company, dict):

        print()
        print("COMPANY FIELDS:")
        print("-" * 70)

        for key, value in company.items():

            if isinstance(value, (dict, list)):

                print(
                    f"- {key} "
                    f"[{type(value).__name__}]"
                )

            else:

                text = str(value)

                if len(text) > 300:
                    text = text[:300] + "..."

                print(
                    f"- {key}: {text}"
                )

    # --------------------------------------------------------
    # POSSIBLE TEXT FIELDS
    # --------------------------------------------------------

    print()
    print("POSSIBLE TEXT / DESCRIPTION FIELDS:")
    print("-" * 70)

    keywords = [
        "title",
        "name",
        "description",
        "desc",
        "product",
        "category",
        "url",
        "link",
        "price",
        "company",
        "address",
        "city",
        "country",
        "website",
    ]

    for key, value in offer.items():

        key_lower = key.lower()

        if any(word in key_lower for word in keywords):

            if isinstance(value, str):

                print(
                    f"{key}: {value[:500]}"
                )

            elif isinstance(value, (dict, list)):

                print(
                    f"{key}: "
                    f"[{type(value).__name__}]"
                )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("DIAGNOSTIC MODE")
    print("=" * 70)

    print()
    print("SEARCH:", SEARCH)

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

    model = first_data.get("model", {})
    paging = model.get("paging", {})

    total_pages = int(
        paging.get("totalPages", 1)
    )

    total_offers = paging.get("total", 0)

    all_offers = []

    # --------------------------------------------------------
    # ALL PAGES
    # --------------------------------------------------------

    for page in range(1, total_pages + 1):

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

        all_offers.extend(offers)

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    target_offers = {
        "RO": [],
        "GR": [],
    }

    for offer in all_offers:

        country = get_country(offer)

        if country in target_offers:

            target_offers[country].append(
                offer
            )

    print()
    print("=" * 70)
    print("DOWNLOAD COMPLETE")
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
        "ROMANIA:",
        len(target_offers["RO"])
    )

    print(
        "GREECE:",
        len(target_offers["GR"])
    )

    # --------------------------------------------------------
    # PRINT DIAGNOSTICS
    # --------------------------------------------------------

    counter = 1

    for country in ["RO", "GR"]:

        for offer in target_offers[country]:

            print_offer(
                counter,
                offer,
                country
            )

            counter += 1

    # --------------------------------------------------------
    # SAVE FULL RAW DATA
    # --------------------------------------------------------

    with open(
        "diagnostic_ro_gr.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            target_offers,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)

    print(
        "Saved: diagnostic_ro_gr.json"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()

