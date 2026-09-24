import requests
import json
import time
import uuid

BASE_URL = (
    "https://www.europages.co.uk/"
    "search-api-proxy/online.aiSearch.productTextSearch"
)

KEYWORD = "packaging"

TARGET_COUNTRIES = {
    "RO": "Румъния",
    "GR": "Гърция",
}

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "bg,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
    ),
    "Referer": (
        "https://www.europages.co.uk/bg/products?q=packaging"
    ),
}


def search_europages(country_code):
    """
    Изпълнява едно търсене в Europages
    за конкретна държава.
    """

    params = {
        "callerIdentity": "preciseIntention",
        "enCores": KEYWORD,
        "multiProTest": "true",
        "query": KEYWORD,
        "keywordsTranslate": KEYWORD,
        "pageSize": "30",

        "llmIntentionType": "preciseIntention",

        "multiProProduct":
            "Hello! How can I assist you today?",

        "coreProduct": KEYWORD,

        "multiCores":
            "Hello! How can I assist you today?",

        "requestId": uuid.uuid4().hex,

        "searchQuery": KEYWORD,

        "multiSearchQuery":
            "Hello! How can I assist you today?",

        "langident": "bg",
        "language": "bg",
        "site": "ep",

        "ufsSessionId":
            uuid.uuid4().hex[:16],

        "startTime":
            str(int(time.time() * 1000)),

        "verified": "false",
        "topResponder": "false",
        "isQuickResponder": "false",

        "source": "web",

        "currency": "EUR",
        "terminalType": "pc",

        # Държавата, която тестваме
        "country": country_code,

        "history": "true",
        "topLevelDomain": "uk",

        "abTestGroups": "{}",

        "userAgent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
        ),

        "needReasoning": "true",
        "allowTestData": "false",

        "rawQueryStruct": json.dumps(
            {
                "core product": [KEYWORD],
                "product_attributes": {
                    KEYWORD: {}
                }
            },
            separators=(",", ":")
        ),

        "blockDisplayType": json.dumps(
            [
                {
                    "displayType": "pvMatch",
                    "blockType": "hangingArea"
                }
            ],
            separators=(",", ":")
        ),
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=60
    )

    print(
        f"HTTP STATUS ({country_code}):",
        response.status_code
    )

    if response.status_code != 200:
        print("SERVER RESPONSE:")
        print(response.text[:2000])
        return []

    data = response.json()

    # Запазваме суровия резултат
    filename = (
        f"europages_raw_{country_code}.json"
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

    model = data.get("model", {})

    if not isinstance(model, dict):
        return []

    offers = model.get("offers", [])

    if not isinstance(offers, list):
        return []

    return offers


def format_price(price):

    if not price:
        return "N/A"

    price_min = price.get("min")
    price_max = price.get("max")
    currency = price.get(
        "currency",
        ""
    )

    kind = price.get(
        "kind",
        ""
    )

    if price_max is not None:
        return (
            f"{price_min} - "
            f"{price_max} "
            f"{currency}"
        )

    if kind == "from":
        return (
            f"from {price_min} "
            f"{currency}"
        )

    if price_min is not None:
        return (
            f"{price_min} "
            f"{currency}"
        )

    return "N/A"


def format_moq(moq):

    if not moq:
        return "N/A"

    value = moq.get(
        "value",
        "N/A"
    )

    unit = moq.get(
        "unit",
        ""
    )

    return f"{value} {unit}".strip()


def main():

    print("=" * 70)
    print(" B2B YUG MONITOR - EUROPAGES")
    print("=" * 70)
    print("Search:", KEYWORD)
    print(
        "Countries:",
        ", ".join(TARGET_COUNTRIES.values())
    )
    print()

    all_results = []

    for country_code, country_name in TARGET_COUNTRIES.items():

        print("=" * 70)
        print(
            f" SEARCHING: {country_name} "
            f"({country_code})"
        )
        print("=" * 70)

        try:

            offers = search_europages(
                country_code
            )

            print(
                "OFFERS RECEIVED:",
                len(offers)
            )

            country_results = []

            for offer in offers:

                company = (
                    offer.get("company")
                    or {}
                )

                # Допълнителна проверка:
                # вземаме само реално съответстващата държава
                actual_country = company.get(
                    "countryCode",
                    ""
                ).upper()

                if actual_country != country_code:
                    continue

                company_name = company.get(
                    "name",
                    "N/A"
                )

                product = offer.get(
                    "name",
                    "N/A"
                )

                description = offer.get(
                    "description",
                    ""
                )

                price = format_price(
                    offer.get("price")
                )

                moq = format_moq(
                    offer.get(
                        "minimumOrderQuantity"
                    )
                )

                slug = offer.get(
                    "slug",
                    ""
                )

                if slug:

                    offer_url = (
                        "https://www.europages.co.uk/"
                        + slug
                    )

                else:

                    offer_url = "N/A"

                result = {
                    "country": country_name,
                    "countryCode": country_code,
                    "company": company_name,
                    "product": product,
                    "description": description,
                    "price": price,
                    "moq": moq,
                    "offerUuid": offer.get(
                        "uuid"
                    ),
                    "companyUuid": company.get(
                        "uuid"
                    ),
                    "url": offer_url,
                    "image": (
                        offer.get("image", {})
                        .get("url")
                    ),
                }

                country_results.append(
                    result
                )
                all_results.append(
                    result
                )

            print(
                "MATCHING OFFERS:",
                len(country_results)
            )

            for i, result in enumerate(
                country_results[:10],
                1
            ):

                print("-" * 70)
                print(f"#{i}")
                print(
                    "Company:",
                    result["company"]
                )
                print(
                    "Country:",
                    result["country"]
                )
                print(
                    "Product:",
                    result["product"]
                )
                print(
                    "Price:",
                    result["price"]
                )
                print(
                    "MOQ:",
                    result["moq"]
                )
                print(
                    "URL:",
                    result["url"]
                )

        except Exception as e:

            print(
                "ERROR:",
                type(e).__name__,
                str(e)
            )

    # Запазваме чистия резултат
    with open(
        "offers_ro_gr.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_results,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)
    print(" FINAL RESULT")
    print("=" * 70)

    print(
        "TOTAL RO + GR OFFERS:",
        len(all_results)
    )

    print(
        "Saved: offers_ro_gr.json"
    )

    print("=" * 70)
    print("TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    main()

