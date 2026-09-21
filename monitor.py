import requests
import re

url = "https://www.europages.co.uk/en/search?q=packaging"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
}

response = requests.get(url, headers=headers, timeout=30)

html = response.text

print("====================================")
print(" EUROPAGES STRUCTURE TEST")
print("====================================")
print("HTTP status:", response.status_code)
print("Downloaded:", len(html), "characters")

tests = [
    "SNI PACKAGING",
    "Türkiye",
    "Minimum order",
    "Contact supplier",
    "__NEXT_DATA__",
    "application/ld+json",
    "__NUXT__",
    "product",
    "supplier"
]

print("\nSEARCHING RAW PAGE")
print("====================================")

for word in tests:
    count = html.lower().count(word.lower())
    print(f"{word}: {count}")

print("\nCONTEXT AROUND 'SNI PACKAGING'")
print("====================================")

match = re.search("SNI PACKAGING", html, re.IGNORECASE)

if match:
    start = max(0, match.start() - 500)
    end = min(len(html), match.end() + 1500)

    print(html[start:end])
else:
    print("SNI PACKAGING not found in raw HTML")

print("\n====================================")
