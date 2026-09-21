import requests

url = "https://example.com"

response = requests.get(url, timeout=20)

print("====================================")
print(" B2B YUG MONITOR - WEB TEST")
print("====================================")
print("URL:", url)
print("HTTP status:", response.status_code)
print("Downloaded:", len(response.text), "characters")
print("====================================")
