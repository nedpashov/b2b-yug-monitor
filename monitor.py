import requests
import json
import time

BASE_URL = "https://www.europages.co.uk/search-api-proxy/online.aiSearch.productTextSearch"

QUERY = "packaging"
TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция"
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "bg,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
    "referer": "https://www.europages.co.uk/bg/products?q=packaging",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0",
}

COOKIES = {
    "region": "BG",
    "currency": "EUR",
    "language": "bg",
}


def get_page(page):
    params = {
        "callerIdentity": "preciseIntention",
        "enCores": QUERY,
        "multiProTest": "true",
        "query": QUERY,
        "keywordsTranslate": QUERY,
        "pageSize": 30,
        "llmIntentionType": "preciseIntention",
        "coreProduct": QUERY,
        "searchQuery": QUERY,
        "langident": "bg",
        "language": "bg",
        "site": "ep",
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
        "page": page,
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        cookies=COOKIES,
        timeout=30
    )

    print(f"PAGE {page}: HTTP {response.status_code}")

    response.raise_for_status()

    return response.json()


def main():

    print("=" * 70)
    print("B2B YUG MONITOR - EUROPAGES")
    print("=" * 70)
    print(f"Search: {QUERY}")
    print("Countries: Румъния, Гърция")
    print("=" * 70)

    all_matches = []

    # Първо вземаме страница 1,
    # за да разберем колко страници има.
    first_data = get_page(1)

    model = first_data.get("model", {})
    paging = model.get("paging", {})

    total_pages = paging.get("totalPages", 1)
    total_offers = paging.get("total", 0)

    print()
    print(f"TOTAL OFFERS: {total_offers}")
    print(f"TOTAL PAGES: {total_pages}")
    print()

    for page in range(1, total_pages + 1):

        print("-" * 70)
        print(f"SEARCHING PAGE {page}/{total_pages}")
        print("-" * 70)

        try:
            if page == 1:
                data = first_data
            else:
                data = get_page(page)

            offers = data.get("model", {}).get("offers", [])

            print(f"OFFERS RECEIVED: {len(offers)}")

            for offer in offers:

                company = offer.get("company", {})
                country = company.get("countryCode")

                if country in TARGET_COUNTRIES:

                    match = {
                        "country": TARGET_COUNTRIES[country],
                        "country_code": country,
                        "offer": offer
                    }

                    all_matches.append(match)

                    title = (
                        offer.get("title")
                        or offer.get("name")
                        or "Без заглавие"
                    )

                    print(
                        f"FOUND: [{country}] {title}"
                    )

        except Exception as e:
            print(f"ERROR ON PAGE {page}: {e}")

        # Малка пауза между заявките
        time.sleep(1)

    # Записваме резултатите
    with open(
        "offers_ro_gr.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_matches,
            f,
            ensure_ascii=False,
            indent=2
        )

    # Статистика
    ro_count = sum(
        1 for x in all_matches
        if x["country_code"] == "RO"
    )

    gr_count = sum(
        1 for x in all_matches
        if x["country_code"] == "GR"
    )

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(f"TOTAL OFFERS SCANNED: {total_offers}")
    print(f"ROMANIA (RO): {ro_count}")
    print(f"GREECE (GR): {gr_count}")
    print(f"RO + GR: {len(all_matches)}")

    print()
    print("Saved: offers_ro_gr.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
