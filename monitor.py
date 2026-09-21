import requests
import re

url = "https://www.europages.co.uk/en/search?q=packaging"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
}

response = requests.get(url, headers=headers, timeout=30)

html = response.text

print("====================================")
print(" EUROPAGES - API DISCOVERY TEST")
print("====================================")
print("HTTP status:", response.status_code)
print("Downloaded:", len(html), "characters")

# Намираме URL адреси в HTML/JavaScript
urls = re.findall(r'https?://[^"\'\s<>]+', html)

# Показваме само API адреси
api_urls = []

for found_url in urls:
    clean = found_url.replace("\\/", "/")

    if "api." in clean.lower() or "/api/" in clean.lower():
        if clean not in api_urls:
            api_urls.append(clean)

print("\nAPI URLS FOUND")
print("====================================")

for i, api_url in enumerate(api_urls[:30], 1):
    print(f"{i}. {api_url[:500]}")

print("\n====================================")
print("API URL COUNT:", len(api_urls))
print("====================================")
