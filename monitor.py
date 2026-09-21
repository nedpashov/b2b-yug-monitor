import requests
import re

url = "https://www.europages.co.uk/en/search?q=packaging"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
}

response = requests.get(url, headers=headers, timeout=30)

html = response.text

print("====================================")
print(" EUROPAGES - NUXT DATA TEST")
print("====================================")
print("HTTP status:", response.status_code)
print("Downloaded:", len(html), "characters")

# Търсим всички script тагове
scripts = re.findall(
    r"<script[^>]*>(.*?)</script>",
    html,
    re.IGNORECASE | re.DOTALL
)

print("\nSCRIPT TAGS FOUND:", len(scripts))
print("====================================")

found = 0

for i, script in enumerate(scripts):

    lower = script.lower()

    if "__nuxt__" in lower or "supplier" in lower or "product" in lower:

        print(f"\n--- SCRIPT {i} ---")
        print("Length:", len(script))

        # Показваме само първите 3000 символа
        print(script[:3000])

        print("\n------------------------------------")

        found += 1

        if found >= 5:
            break

print("\n====================================")
print("RELEVANT SCRIPTS FOUND:", found)
print("====================================")
