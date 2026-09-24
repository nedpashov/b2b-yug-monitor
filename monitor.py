import requests
import json
import time
import uuid

BASE_URL = (
    "https://www.europages.co.uk/"
    "search-api-proxy/online.aiSearch.productTextSearch"
)

KEYWORD = "packaging"

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

params = {
    "callerIdentity": "preciseIntention",
    "enCores": KEYWORD,
    "multiProTest": "true",
    "query": KEYWORD,
    "keywordsTranslate": KEYWORD,
    "pageSize": "30",

    "llmIntentionType": "preciseIntention",

    "multiProProduct": "Hello! How can I assist you today?",
    "coreProduct": KEYWORD,
    "multiCores": "Hello! How can I assist you today?",

    "requestId": uuid.uuid4().hex,

    "searchQuery": KEYWORD,
    "multiSearchQuery": "Hello! How can I assist you today?",

    "langident": "bg",
    "language": "bg",
    "site": "ep",

    # Генерираме нов session ID за всяко изпълнение
    "ufsSessionId": uuid.uuid4().hex[:16],

    "startTime": str(int(time.time() * 1000)),

    "verified": "false",
    "topResponder": "false",
    "isQuickResponder": "false",

    "source": "web",

    "currency": "EUR",
    "terminalType": "pc",
    "country": "bg",

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


print("=" * 60)
print(" B2B YUG MONITOR - EUROPAGES TEST")
print("=" * 60)
print("Search:", KEYWORD)
print("Session:", params["ufsSessionId"])
print()


try:

    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=60
    )

    print("HTTP STATUS:", response.status_code)
    print()

    if response.status_code != 200:

        print("SERVER RESPONSE:")
        print(response.text[:3000])

        raise SystemExit(1)

    data = response.json()

    print("JSON RESPONSE: OK")
    print()

    # Запазваме целия отговор
    with open(
        "europages_raw.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("Saved: europages_raw.json")
    print()

    # Намираме offers
    offers = []

    if isinstance(data, dict):

        model = data.get("model", {})

        if isinstance(model, dict):

            offers = model.get(
                "offers",
                []
            )

    print("OFFERS FOUND:", len(offers))
    print()


    # Показваме първите 10 оферти

    for i, offer in enumerate(
        offers[:10],
        1
    ):

        company = (
            offer.get("company")
            or {}
        )

        price = (
            offer.get("price")
            or {}
        )

        moq = (
            offer.get(
                "minimumOrderQuantity"
            )
            or {}
        )


        # Фирма

        company_name = company.get(
            "name",
            "N/A"
        )


        # Държава

        country = company.get(
            "countryCode",
            "N/A"
        )


        # Продукт

        product = offer.get(
            "name",
            "N/A"
        )


        # Цена

        if price:

            price_min = price.get(
                "min"
            )

            price_max = price.get(
                "max"
            )

            currency = price.get(
                "currency",
                ""
            )

            kind = price.get(
                "kind",
                ""
            )


            if price_max is not None:

                price_text = (
                    f"{price_min} - "
                    f"{price_max} "
                    f"{currency}"
                )

            elif kind == "from":

                price_text = (
                    f"from {price_min} "
                    f"{currency}"
                )

            else:

                price_text = (
                    f"{price_min} "
                    f"{currency}"
                )

        else:

            price_text = "N/A"


        # MOQ

        if moq:

            moq_text = (
                f"{moq.get('value', 'N/A')} "
                f"{moq.get('unit', '')}"
            )

        else:

            moq_text = "N/A"


        # Europages URL

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


        print("-" * 60)
        print(f"#{i}")
        print("Company:", company_name)
        print("Country:", country)
        print("Product:", product)
        print("Price:", price_text)
        print("MOQ:", moq_text)
        print("URL:", offer_url)


    print()
    print("=" * 60)
    print("TEST FINISHED")
    print("=" * 60)


except Exception as e:

    print("=" * 60)
    print("ERROR")
    print("=" * 60)

    print(
        type(e).__name__,
        str(e)
    )
