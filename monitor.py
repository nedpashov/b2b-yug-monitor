import requests
import json

url = "https://www.europages.co.uk/search-api-proxy/online.aiSearch.productTextSearch"

params = {
    "callerIdentity": "preciseIntention",
    "enCores": "packaging",
    "multiProTest": "true",
    "query": "packaging",
    "keywordsTranslate": "packaging",
    "pageSize": "30",
    "llmIntentionType": "preciseIntention",
    "coreProduct": "packaging",
    "searchQuery": "packaging",
    "langident": "bg",
    "language": "bg",
    "site": "ep",
    "ufsSessionId": "a003b2c433e44763",
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
    "allowTestData": "false"
}

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.europages.co.uk/bg/products?q=packaging"
}

print("=" * 70)
print("EUROPAGES - JSON STRUCTURE TEST")
print("=" * 70)

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30
)

print("HTTP STATUS:", response.status_code)

if response.status_code != 200:
    print("\nSERVER RESPONSE:")
    print(response.text[:2000])
    raise SystemExit(1)

data = response.json()

print("\nJSON RECEIVED")
print("-" * 70)

if isinstance(data, dict):

    print("\nTOP LEVEL KEYS:")

    for key in data.keys():
        print("-", key)

elif isinstance(data, list):

    print("JSON TYPE: LIST")
    print("ITEMS:", len(data))


print("\nSEARCHING FOR PAGINATION FIELDS...")
print("-" * 70)

keywords = [
    "page",
    "total",
    "count",
    "offset",
    "start",
    "next",
    "cursor"
]


def search(obj, path="root"):

    if isinstance(obj, dict):

        for key, value in obj.items():

            key_lower = str(key).lower()

            if any(word in key_lower for word in keywords):

                print()
                print("PATH :", path)
                print("KEY  :", key)
                print("VALUE:", str(value)[:500])

            search(value, path + "." + str(key))

    elif isinstance(obj, list):

        for i, item in enumerate(obj):

            search(
                item,
                path + f"[{i}]"
            )


search(data)

print("\n" + "=" * 70)
print("TEST FINISHED")
print("=" * 70)
