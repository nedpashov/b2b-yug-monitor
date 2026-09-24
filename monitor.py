import requests
import json
import time

# ============================================================
# B2B YUG MONITOR - EUROPAGES
# ============================================================

BASE_URL = (
    "https://www.europages.co.uk/"
    "search-api-proxy/online.aiSearch.productTextSearch"
)

QUERY = "packaging"

TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция",
}

# Временно използваме session ID от работещата заявка.
# Ако Europages го отхвърли като изтекъл, ще видим
# точното съобщение и ще направим автоматично получаване.
UFS_SESSION_ID = "cc2b6bc58703691d"


HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": (
        "bg,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,bg-BG;q=0.6"
    ),
    "referer": (
        "https://www.europages.co.uk/bg/products?q=packaging"
    ),
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
    ),
}


def get_page(page=1):

    params = {
        "callerIdentity": "preciseIntention",
        "enCores": QUERY,
        "multiProTest": "true",
        "query": QUERY,
        "keywordsTranslate": QUERY,
        "pageSize": "30",

        "llmIntentionType": "preciseIntention",

        "multiProTest": "true",

        "coreProduct": QUERY,
        "searchQuery": QUERY,

        "langident": "bg",
        "language": "bg",
        "site": "ep",

        "ufsSessionId": UFS_SESSION_ID,

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

        # ВАЖНО:
        # Тук засега НЕ задаваме page=.
        # Първо проверяваме, че базовата заявка работи.
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        timeout=30,
    )

    print()
    print("=" * 70)
    print(f"HTTP STATUS: {response.status_code}")
    print("=" * 70)

    if response.status_code != 200:

        print("ERROR RESPONSE:")
        print(response.text[:3000])

        print()
        print("REQUEST URL:")
        print(response.url)

        return None

    try:
        data = response.json()
    except Exception as e:

        print("JSON ERROR:")
        print(e)

        print()
        print("RAW RESPONSE:")
        print(response.text[:3000])

        return None

    return data


def main():

    print("=" * 70)
    print("EUROPAGES - B2B YUG MONITOR")
    print("=" * 70)

    print()
    print("SEARCH:", QUERY)
    print("TARGET COUNTRIES: Румъния, Гърция")

    print()
    print("TESTING EUROPAGES API...")
    print()

    data = get_page(1)

    if data is None:

        print()
        print("=" * 70)
        print("REQUEST FAILED")
        print("=" * 70)

        return

    model = data.get("model", {})

    paging = model.get("paging", {})
    offers = model.get("offers", [])

    print()
    print("=" * 70)
    print("API CONNECTION SUCCESSFUL")
    print("=" * 70)

    print()
    print("CURRENT PAGE:", paging.get("currentPage"))
    print("TOTAL PAGES:", paging.get("totalPages"))
    print("TOTAL OFFERS:", paging.get("total"))
    print("OFFERS RECEIVED:", len(offers))

    # --------------------------------------------------------
    # Проверяваме държавите в получените оферти
    # --------------------------------------------------------

    matches = []

    print()
    print("=" * 70)
    print("CHECKING COUNTRIES")
    print("=" * 70)

    for index, offer in enumerate(offers):

        company = offer.get("company", {})

        country_code = company.get("countryCode")

        if country_code in TARGET_COUNTRIES:

            title = (
                offer.get("title")
                or offer.get("name")
                or "Без заглавие"
            )

            print()
            print(
                f"[{country_code}] "
                f"{TARGET_COUNTRIES[country_code]}"
            )

            print("TITLE:", title)

            matches.append({
                "country": TARGET_COUNTRIES[country_code],
                "country_code": country_code,
                "offer": offer,
            })

    # --------------------------------------------------------
    # Запис
    # --------------------------------------------------------

    with open(
        "offers_ro_gr.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            matches,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # --------------------------------------------------------
    # Статистика
    # --------------------------------------------------------

    ro_count = sum(
        1
        for item in matches
        if item["country_code"] == "RO"
    )

    gr_count = sum(
        1
        for item in matches
        if item["country_code"] == "GR"
    )

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    print("ROMANIA:", ro_count)
    print("GREECE:", gr_count)
    print("TOTAL RO + GR:", len(matches))

    print()
    print("Saved: offers_ro_gr.json")

    print()
    print("=" * 70)
    print("TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    main()
