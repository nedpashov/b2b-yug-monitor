import json

with open("europages_raw.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 60)
print("EUROPAGES JSON")
print("=" * 60)

print("\nОсновни полета:")

if isinstance(data, dict):
    for key in data:
        print("-", key)

elif isinstance(data, list):
    print("JSON е LIST")
    print("Брой елементи:", len(data))

print("\nТърсим pagination полета...")

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

            key_text = str(key).lower()

            if any(word in key_text for word in keywords):
                print()
                print("PATH:", path)
                print("KEY :", key)
                print("VALUE:", str(value)[:300])

            search(value, path + "." + str(key))

    elif isinstance(obj, list):

        for i, item in enumerate(obj):
            search(item, path + f"[{i}]")

search(data)

print("\n" + "=" * 60)
print("ГОТОВО")
print("=" * 60)
