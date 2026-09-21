import requests
from bs4 import BeautifulSoup

url = "https://www.europages.co.uk/en/search?q=packaging"

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; B2B-YUG-Monitor/1.0)"
}

response = requests.get(url, headers=headers, timeout=30)

print("====================================")
print(" B2B YUG MONITOR - EUROPAGES TEST")
print("====================================")
print("URL:", url)
print("HTTP status:", response.status_code)
print("Downloaded:", len(response.text), "characters")

soup = BeautifulSoup(response.text, "html.parser")

print("Page title:", soup.title.get_text(strip=True) if soup.title else "N/A")

print("====================================")
