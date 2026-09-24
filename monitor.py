import requests

URL = "https://www.europages.co.uk/search-api-proxy/online.aiSearch.productTextSearch"

params = {
    "callerIdentity": "preciseIntention",
    "enCores": "packaging",
    "multiProTest": "true",
    "query": "packaging",
    "keywordsTranslate": "packaging",
    "pageSize": 30,
    "llmIntentionType": "preciseIntention",
    "coreProduct": "packaging",
    "searchQuery": "packaging",
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
}

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "bg,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
    "referer": "https://www.europages.co.uk/bg/products?q=packaging",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0",
}

response = requests.get(
    URL,
    params=params,
    headers=headers,
    timeout=30
)

print("=" * 70)
print("EUROPAGES TEST")
print("=" * 70)

print("HTTP STATUS:", response.status_code)

print()
print("URL:")
print(response.url)

print()

if response.status_code != 200:
    print("ERROR RESPONSE:")
    print(response.text[:2000])
else:

    data = response.json()

    model = data.get("model", {})
    paging = model.get("paging", {})

    print("SUCCESS")
    print()
    print("CURRENT PAGE:", paging.get("currentPage"))
    print("TOTAL PAGES:", paging.get("totalPages"))
    print("TOTAL OFFERS:", paging.get("total"))
    print("OFFERS RECEIVED:", len(model.get("offers", [])))

    offers = model.get("offers", [])

    if offers:
        first = offers[0]

        print()
        print("FIRST OFFER:")

        print(
            first.get("title")
            or first.get("name")
            or "NO TITLE"
        )

print()
print("=" * 70)
