import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

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

print("\nPAGE TITLE:")
print(soup.title.get_text(" ", strip=True) if soup.title else "N/A")

print("\nLINKS CONTAINING PRODUCT/COMPANY INFORMATION:")
print("------------------------------------")

count = 0

for link in soup.find_all("a", href=True):
    text = link.get_text(" ", strip=True)

    if len(text) >= 5:
        href = urljoin(url, link["href"])

        # Показваме само първите 30 смислени връзки
        print(f"{count + 1}. {text[:150]}")
        print(f"   {href}")

        count += 1

        if count >= 30:
            break

print("\n====================================")
print("TOTAL LINKS FOUND:", len(soup.find_all("a", href=True)))
print("====================================")
