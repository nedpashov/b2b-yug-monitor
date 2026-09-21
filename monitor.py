import requests
from bs4 import BeautifulSoup

url = "https://www.europages.co.uk/en/search?q=packaging"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
}

response = requests.get(url, headers=headers, timeout=30)

print("====================================")
print(" B2B YUG MONITOR - EUROPAGES")
print("====================================")
print("HTTP status:", response.status_code)
print("Downloaded:", len(response.text), "characters")

soup = BeautifulSoup(response.text, "html.parser")

# Търсим текстови блокове, които приличат на резултати
keywords = [
    "Minimum order",
    "Contact supplier",
    "Türkiye",
    "Turkey",
    "Greece",
    "Serbia",
    "North Macedonia"
]

found = 0
seen = set()

print("\nPOSSIBLE B2B RESULTS")
print("====================================")

for element in soup.find_all(["div", "article", "section", "li"]):

    text = element.get_text(" ", strip=True)

    if len(text) < 80 or len(text) > 1500:
        continue

    if not any(keyword.lower() in text.lower() for keyword in keywords):
        continue

    # Премахваме дублиращи се блокове
    clean_text = " ".join(text.split())

    if clean_text in seen:
        continue

    seen.add(clean_text)

    print(f"\n--- RESULT {found + 1} ---")
    print(clean_text[:1000])

    found += 1

    if found >= 10:
        break

print("\n====================================")
print("RESULTS FOUND:", found)
print("====================================")
