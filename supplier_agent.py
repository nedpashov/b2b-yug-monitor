
import csv
import os
import re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# B2B YUG SUPPLIER AGENT
# VERSION 2 - INTERNATIONAL SUPPLIER INTELLIGENCE
# ============================================================

INPUT_FILE = "data/latest/offers_yug.csv"

LATEST_SUPPLIERS = "data/latest/suppliers.csv"
LATEST_REPORT = "data/latest/supplier_report.md"

TODAY = datetime.now(
    ZoneInfo("Europe/Sofia")
).strftime("%Y-%m-%d")

HISTORY_DIR = f"data/history/{TODAY}"
HISTORY_SUPPLIERS = f"{HISTORY_DIR}/suppliers.csv"
HISTORY_REPORT = f"{HISTORY_DIR}/supplier_report.md"


def clean(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def normalize(value):
    return clean(value).lower()


def first_non_empty(*values):
    for value in values:
        value = clean(value)
        if value:
            return value
    return ""


def is_true(value):
    return normalize(value) in ("true", "1", "yes", "y", "да")


def load_offers(filename):
    if not os.path.exists(filename):
        print(f"ERROR: INPUT FILE NOT FOUND: {filename}")
        return []

    with open(filename, "r", encoding="utf-8-sig", newline="") as f:
        return [
            {key: clean(value) for key, value in row.items()}
            for row in csv.DictReader(f)
        ]


def company_key(row):
    country = normalize(row.get("country_code"))
    identifier = first_non_empty(
        row.get("company_id"),
        row.get("company_uuid"),
        row.get("company_ep_slug"),
        row.get("company_slug"),
        row.get("company_name")
    )
    return f"{country}|{normalize(identifier)}"


def group_companies(rows):
    companies = defaultdict(list)
    for row in rows:
        if clean(row.get("company_name")):
            companies[company_key(row)].append(row)
    return companies


def unique_values(rows, field):
    values = []
    seen = set()

    for row in rows:
        value = clean(row.get(field))
        if value and normalize(value) not in seen:
            seen.add(normalize(value))
            values.append(value)

    return values


def find_contact(rows, fields):
    for row in rows:
        for field in fields:
            value = clean(row.get(field))
            if value:
                return value
    return ""


def find_email(rows):
    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    for row in rows:
        for field in ("email", "contact_email", "company_email"):
            value = clean(row.get(field))
            if value and re.fullmatch(email_pattern, value):
                return value

        for value in row.values():
            match = re.search(email_pattern, str(value))
            if match:
                return match.group(0)

    return ""


def find_price(rows):
    fields = ("price", "unit_price", "price_value",
              "selling_price", "offer_price")

    for row in rows:
        for field in fields:
            value = clean(row.get(field))
            if value:
                return value

    pattern = r"(?:€|EUR)\s*\d+(?:[.,]\d+)?"

    for row in rows:
        text = " ".join(str(value) for value in row.values())
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return ""


def find_moq(rows):
    fields = (
        "moq", "minimum_order_quantity",
        "min_order_quantity", "minimum_quantity"
    )

    return find_contact(rows, fields)


def classify_supplier(products, descriptions, company_name):
    text = normalize(
        " ".join(products + descriptions + [company_name])
    )

    manufacturer_terms = (
        "manufacturer", "manufacturing", "producer",
        "production", "factory", "produces", "fabrication"
    )

    trader_terms = (
        "wholesale", "wholesaler", "distributor",
        "trading company", "importer", "exporter", "reseller"
    )

    manufacturer = any(term in text for term in manufacturer_terms)
    trader = any(term in text for term in trader_terms)

    if manufacturer and trader:
        return "POSSIBLE MANUFACTURER / TRADER"
    if manufacturer:
        return "POSSIBLE MANUFACTURER"
    if trader:
        return "POSSIBLE TRADER / DISTRIBUTOR"

    return "UNKNOWN - VERIFY"


def calculate_score(rows, products, descriptions):
    score = 0
    text = normalize(" ".join(
        products + descriptions +
        [row.get("company_name", "") for row in rows]
    ))

    keyword_points = {
        "manufacturer": 15,
        "producer": 15,
        "factory": 15,
        "production": 10,
        "packaging": 10,
        "plastic": 5,
        "bag": 5,
        "film": 5,
        "bottle": 5,
        "container": 5,
        "cardboard": 5,
        "corrugated": 5,
        "paper": 3,
        "box": 3,
        "carton": 3,
    }

    matched = []
    for keyword, points in keyword_points.items():
        if keyword in text:
            score += points
            matched.append(keyword)

    if find_price(rows):
        score += 10

    if find_moq(rows):
        score += 5

    if any(is_true(r.get("email_existing")) for r in rows):
        score += 5

    if any(is_true(r.get("is_ep_member")) for r in rows):
        score += 5

    if any(is_true(r.get("is_quick_responder")) for r in rows):
        score += 5

    if len(rows) >= 3:
        score += 5

    return min(score, 100), matched


def build_supplier(rows):
    first = rows[0]

    company_name = first_non_empty(
        first.get("company_name"), "Unknown company"
    )

    products = unique_values(rows, "product_name")
    descriptions = unique_values(rows, "description")
    categories = unique_values(rows, "category")

    price = find_price(rows)
    moq = find_moq(rows)

    score, matched_keywords = calculate_score(
        rows, products, descriptions
    )

    supplier_type = classify_supplier(
        products, descriptions, company_name
    )

    slug = first_non_empty(
        first.get("company_ep_slug"),
        first.get("company_slug")
    )

    if slug.startswith(("http://", "https://")):
        company_url = slug
    elif slug:
        company_url = "https://www.europages.co.uk/" + slug.lstrip("/")
    else:
        company_url = ""

    offer_url = find_contact(rows, ("offer_url", "url", "link"))

    email = find_email(rows)
    phone = find_contact(
        rows, ("phone", "telephone", "telephone_number",
               "phone_number", "mobile")
    )
    website = find_contact(
        rows, ("website", "company_website", "web", "website_url")
    )

    if price:
        price_status = "REAL PRICE - VERIFY SOURCE"
    else:
        price_status = "QUOTATION NEEDED"

    return {
        "country_code": first.get("country_code", ""),
        "country": first_non_empty(
            first.get("country"), first.get("country_code")
        ),
        "company_name": company_name,
        "company_id": first.get("company_id", ""),
        "company_uuid": first.get("company_uuid", ""),
        "supplier_type": supplier_type,
        "products_count": len(products),
        "products": " | ".join(products),
        "categories": " | ".join(categories),
        "price": price,
        "price_status": price_status,
        "moq": moq,
        "score": score,
        "matched_keywords": ", ".join(matched_keywords),
        "email": email,
        "phone": phone,
        "website": website,
        "company_url": company_url,
        "europages_url": offer_url,
        "is_ep_member": first.get("is_ep_member", ""),
        "is_quick_responder": first.get("is_quick_responder", ""),
        "offers_count": len(rows),
        "verification_status": "NOT VERIFIED",
        "next_action": (
            "Verify company; request price, MOQ, capacity, "
            "lead time, delivery terms and documents"
        ),
    }


FIELDS = [
    "country_code", "country", "company_name", "company_id",
    "company_uuid", "supplier_type", "products_count", "products",
    "categories", "price", "price_status", "moq", "score",
    "matched_keywords", "email", "phone", "website",
    "company_url", "europages_url", "is_ep_member",
    "is_quick_responder", "offers_count", "verification_status",
    "next_action"
]


def save_csv(rows, filename):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=FIELDS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"SAVED: {filename}")
    print(f"ROWS: {len(rows)}")


def create_report(suppliers, offers_count):
    lines = [
        "# B2B YUG SUPPLIER REPORT",
        "",
        f"Date: {TODAY}",
        f"Offers analysed: {offers_count}",
        f"Unique companies: {len(suppliers)}",
        "",
        "IMPORTANT: Supplier scores are research priorities, not profit estimates.",
        "Verification status is NOT VERIFIED until due diligence is completed.",
        "",
        "## Price information",
        "",
    ]

    real_prices = sum(
        1 for s in suppliers if s["price"]
    )
    quotations = len(suppliers) - real_prices

    lines.append(f"- Offers with a detected price: {real_prices}")
    lines.append(f"- Suppliers requiring a quotation: {quotations}")
    lines.extend(["", "## Supplier shortlist", ""])

    for index, supplier in enumerate(suppliers, start=1):
        lines.extend([
            f"### {index}. {supplier['company_name']}",
            "",
            f"- Country: {supplier['country']}",
            f"- Type: {supplier['supplier_type']}",
            f"- Research score: {supplier['score']}",
            f"- Products: {supplier['products'] or 'N/A'}",
            f"- Categories: {supplier['categories'] or 'N/A'}",
            f"- Price: {supplier['price'] or 'N/A'}",
            f"- Price status: {supplier['price_status']}",
            f"- MOQ: {supplier['moq'] or 'N/A'}",
            f"- Verification: {supplier['verification_status']}",
            f"- Email: {supplier['email'] or 'Not found'}",
            f"- Phone: {supplier['phone'] or 'Not found'}",
            f"- Website: {supplier['website'] or 'Not found'}",
            f"- Company profile: {supplier['company_url'] or 'Not found'}",
            f"- Offer URL: {supplier['europages_url'] or 'Not found'}",
            f"- Next action: {supplier['next_action']}",
            "",
        ])

    return "\n".join(lines)


def main():
    print("=" * 68)
    print("B2B YUG SUPPLIER AGENT")
    print("VERSION 2 - INTERNATIONAL SUPPLIER INTELLIGENCE")
    print("=" * 68)
    print(f"INPUT: {INPUT_FILE}")

    rows = load_offers(INPUT_FILE)
    print(f"OFFERS LOADED: {len(rows)}")

    if not rows:
        print("No offers loaded. Check input path and CSV contents.")
        return

    companies = group_companies(rows)
    suppliers = [
        build_supplier(company_rows)
        for company_rows in companies.values()
    ]

    suppliers.sort(
        key=lambda s: (s["score"], s["products_count"]),
        reverse=True
    )

    save_csv(suppliers, LATEST_SUPPLIERS)

    report = create_report(suppliers, len(rows))
    os.makedirs("data/latest", exist_ok=True)

    with open(LATEST_REPORT, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"SAVED: {LATEST_REPORT}")

    save_csv(suppliers, HISTORY_SUPPLIERS)

    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(HISTORY_REPORT, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"SAVED: {HISTORY_REPORT}")
    print()
    print(f"OFFERS ANALYSED: {len(rows)}")
    print(f"COMPANIES FOUND: {len(companies)}")
    print(f"SUPPLIERS: {len(suppliers)}")

    if suppliers:
        top = suppliers[0]
        print(f"TOP SUPPLIER: {top['company_name']}")
        print(f"COUNTRY: {top['country']}")
        print(f"SCORE: {top['score']}")
        print(f"PRICE STATUS: {top['price_status']}")
        print(f"VERIFICATION: {top['verification_status']}")

    print("SUPPLIER AGENT COMPLETE")


if __name__ == "__main__":
    main()

