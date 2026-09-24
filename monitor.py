import requests
import json
from datetime import datetime

BASE_URL = "https://www.europages.co.uk/search-api-proxy/online.aiSearch.productTextSearch"

KEYWORD = "packaging"

params = {
    "callerIdentity": "preciseIntention",
    "enCores": KEYWORD,
    "multiProTest": "true",
    "query": KEYWORD,
    "keywordsTranslate": KEYWORD,
    "pageSize": "30",
    "llmIntentionType": "preciseIntention",
    "coreProduct": KEYWORD,
    "searchQuery": KEYWORD,
    "langident": "bg",
    "language": "bg",
    "site": "ep",
    "source": "web",
    "currency": "EUR",
    "terminalType": "pc",
    "country": "bg",
    "history": "true",
    "topLevelDomain": "uk",
    "verified": "false",
    "topResponder": "false",
    "isQuickResponder": "false",
    "needReasoning": "true",
    "allowTestData": "false",
}

headers = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
    ),
    "Referer": "https://www.europages.co.uk/bg/products?q=packaging",
}

print("=" * 60)
print(" B2B YUG MONITOR - EUROPAGES TEST")
print("=" * 60)
print("Search:", KEYWORD)
print()

try:
    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=60
    )

    print("HTTP STATUS:", response.status_code)
    print("URL:", response.url[:300])
    print()

    response.raise_for_status()

    data = response.json()

    print("JSON RESPONSE: OK")
    print()

    # Запазваме суровия резултат за проверка
    with open("europages_raw.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Saved: europages_raw.json")

    # Търсим offers
    offers = []

    if isinstance(data, dict):
        model = data.get("model", {})

        if isinstance(model, dict):
            offers = model.get("offers", [])

    print("OFFERS FOUND:", len(offers))
    print()

    # Показваме първите 10
    for i, offer in enumerate(offers[:10], 1):

        company = offer.get("company", {})
        price = offer.get("price", {})
        moq = offer.get("minimumOrderQuantity", {})

        company_name = company.get("name", "N/A")
        country = company.get("countryCode", "N/A")

        product = offer.get("name", "N/A")

        if price:
            price_min = price.get("min")
            price_max = price.get("max")
            currency = price.get("currency", "")

            if price_max is not None:
                price_text = f"{price_min} - {price_max} {currency}"
            else:
                price_text = f"{price_min} {currency}"
        else:
            price_text = "N/A"

        if moq:
            moq_text = f"{moq.get('value', 'N/A')} {moq.get('unit', '')}"
        else:
            moq_text = "N/A"

        slug = offer.get("slug", "")
        url = ""

        if slug:
            url = "https://www.europages.co.uk/" + slug

        print("-" * 60)
        print(f"#{i}")
        print("Company:", company_name)
        print("Country:", country)
        print("Product:", product)
        print("Price:", price_text)
        print("MOQ:", moq_text)
        print("URL:", url)

    print()
    print("=" * 60)
    print("TEST FINISHED")
    print("=" * 60)

except Exception as e:
    print("=" * 60)
    print("ERROR")
    print("=" * 60)
    print(type(e).__name__, str(e))
