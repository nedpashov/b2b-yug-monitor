import requests
import json
import time
import re
from urllib.parse import urlencode


# ============================================================
# B2B YUG MONITOR - EUROPAGES
# ============================================================

SEARCH = "packaging"

TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция",
}

BASE_URL = "https://www.europages.co.uk"

API_PATH = "/search-api-proxy/online.aiSearch.productTextSearch"


# ============================================================
# SESSION
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

    try:
        response = session.get(
            f"{BASE_URL}/bg/products?q={SEARCH}",
            headers=headers,
            timeout=30,
        )

        print("Homepage HTTP:", response.status_code)

        # ----------------------------------------------------
        # Try to find ufsSessionId in cookies
        # ----------------------------------------------------

        ufs_session_id = session.cookies.get("ufs_session_id")

        if ufs_session_id:
            print("ufsSessionId obtained from cookie")
            print("Session:", ufs_session_id[:8] + "...")
            return session, ufs_session_id

        # ----------------------------------------------------
        # Try to find it in page source
        # ----------------------------------------------------

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

        print("WARNING: ufsSessionId was not found.")

        return session, None

    except Exception as e:
        print("ERROR creating session:", e)
        return session, None


# ============================================================
# API REQUEST
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

    url = BASE_URL + API_PATH

    response = session.get(
        url,
        params=params,
        headers=headers,
        timeout=30,
    )

    print(f"PAGE {page}: HTTP {response.status_code}")

    if response.status_code != 200:
        print("ERROR RESPONSE:")
        print(response.text[:2000])
        return None

    try:
        return response.json()

    except Exception as e:
        print("JSON ERROR:", e)
        print(response.text[:1000])
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
# OFFER TITLE
# ============================================================

def get_title(offer):
    possible_fields = [
        "title",
        "name",
        "productName",
        "offerTitle",
        "label",
    ]

    for field in possible_fields:
        value = offer.get(field)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return "Без заглавие"


# ============================================================
# OFFER URL
# ============================================================

def get_url(offer):
    possible_fields = [
        "url",
        "link",
        "offerUrl",
        "productUrl",
    ]

    for field in possible_fields:
        value = offer.get(field)

        if isinstance(value, str) and value.startswith("http"):
            return value

    return ""


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("=" * 70)

    print()
    print("SEARCH:", SEARCH)
    print("TARGET COUNTRIES:", ", ".join(TARGET_COUNTRIES.values()))
    print()

    # --------------------------------------------------------
    # CREATE SESSION
    # --------------------------------------------------------

    session, ufs_session_id = create_session()

    if not ufs_session_id:
        print()
        print("=" * 70)
        print("FAILED: NO ufsSessionId")
        print("=" * 70)
        return

    print()
    print("=" * 70)
    print("TESTING EUROPAGES API")
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
        print("API request failed.")
        return

    model = first_data.get("model", {})

    paging = model.get("paging", {})

    total_pages = paging.get("totalPages", 1)
    total_offers = paging.get("total", 0)

    first_offers = model.get("offers", [])

    print()
    print("=" * 70)
    print("API CONNECTION SUCCESSFUL")
    print("=" * 70)

    print("CURRENT PAGE:", paging.get("currentPage"))
    print("TOTAL PAGES:", total_pages)
    print("TOTAL OFFERS:", total_offers)
    print("OFFERS RECEIVED:", len(first_offers))

    # --------------------------------------------------------
    # COLLECT ALL OFFERS
    # --------------------------------------------------------

    all_offers = []

    print()
    print("=" * 70)
    print("DOWNLOADING ALL PAGES")
    print("=" * 70)

    for page in range(1, int(total_pages) + 1):

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
            print(f"PAGE {page}: FAILED")
            continue

        offers = data.get("model", {}).get("offers", [])

        print(
            f"PAGE {page}/{total_pages} -> "
            f"{len(offers)} offers"
        )

        all_offers.extend(offers)

    print()
    print("=" * 70)
    print("ALL PAGES DOWNLOADED")
    print("=" * 70)

    print("TOTAL OFFERS DOWNLOADED:", len(all_offers))

    # --------------------------------------------------------
    # FILTER COUNTRIES
    # --------------------------------------------------------

    results = {
        "RO": [],
        "GR": [],
    }

    for offer in all_offers:

        country = get_country(offer)

        if country in results:
            results[country].append({
                "title": get_title(offer),
                "country": country,
                "url": get_url(offer),
                "company": offer.get("company", {}),
                "raw_offer": offer,
            })

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    print("ROMANIA:", len(results["RO"]))
    print("GREECE :", len(results["GR"]))
    print(
        "TOTAL RO + GR:",
        len(results["RO"]) + len(results["GR"])
    )

    # --------------------------------------------------------
    # SHOW FOUND OFFERS
    # --------------------------------------------------------

    print()

    for country_code in ["RO", "GR"]:

        print("-" * 70)
        print(TARGET_COUNTRIES[country_code])
        print("-" * 70)

        for index, offer in enumerate(
            results[country_code],
            start=1
        ):

            print(
                f"{index}. "
                f"{offer['title']}"
            )

            if offer["url"]:
                print(
                    "   URL:",
                    offer["url"]
                )

    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    output = {
        "search": SEARCH,
        "target_countries": TARGET_COUNTRIES,
        "total_pages": total_pages,
        "total_offers": total_offers,
        "downloaded_offers": len(all_offers),
        "results": results,
    }

    with open(
        "offers_ro_gr.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)
    print("SAVED: offers_ro_gr.json")
    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()

