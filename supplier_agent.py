import csv
import os
import re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# B2B YUG SUPPLIER AGENT
# VERSION 3 - INTERNATIONAL SUPPLIER INTELLIGENCE
# Research scores are not profit estimates.
# Prices and supplier types remain unverified until checked.
# ============================================================

INPUT_FILE = "data/latest/offers_yug.csv"
LATEST_SUPPLIERS = "data/latest/suppliers.csv"
LATEST_REPORT = "data/latest/supplier_report.md"

TODAY = datetime.now(ZoneInfo("Europe/Sofia")).strftime("%Y-%m-%d")
HISTORY_DIR = f"data/history/{TODAY}"
HISTORY_SUPPLIERS = f"{HISTORY_DIR}/suppliers.csv"
HISTORY_REPORT = f"{HISTORY_DIR}/supplier_report.md"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
CURRENCY_PRICE_RE = re.compile(
    r"(?:(?:EUR|USD|GBP|RON|BGN|TRY|€|\\$|£)\\s*\\d[\\d\\s.,]*"
    r"|\\d[\\d\\s.,]*\\s*(?:EUR|USD|GBP|RON|BGN|TRY|€|\\$|£))",
    re.IGNORECASE,
)
PRICE_FIELDS = ("price", "unit_price", "price_value", "selling_price",
                "offer_price", "price_text")
MOQ_FIELDS = ("moq", "minimum_order_quantity", "min_order_quantity",
              "minimum_quantity")
EMAIL_FIELDS = ("email", "contact_email", "company_email")
PHONE_FIELDS = ("phone", "telephone", "telephone_number", "phone_number", "mobile")
WEBSITE_FIELDS = ("website", "company_website", "web", "website_url")


def clean(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def normalize(value):
    return clean(value).casefold()


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
    try:
        with open(filename, "r", encoding="utf-8-sig", newline="") as f:
            return [{k: clean(v) for k, v in row.items()}
                    for row in csv.DictReader(f)]
    except (OSError, csv.Error) as exc:
        print(f"ERROR: COULD NOT READ INPUT CSV: {exc}")
        return []


def company_key(row):
    country = normalize(row.get("country_code"))
    identifier = first_non_empty(
        row.get("company_id"), row.get("company_uuid"),
        row.get("company_ep_slug"), row.get("company_slug"),
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
    result, seen = [], set()
    for row in rows:
        value = clean(row.get(field))
        marker = normalize(value)
        if value and marker not in seen:
            seen.add(marker)
            result.append(value)
    return result


def find_contact(rows, fields):
    for row in rows:
        for field in fields:
            value = clean(row.get(field))
            if value:
                return value
    return ""


def find_email(rows):
    # Prefer explicit email columns; otherwise search the downloaded source data.
    for row in rows:
        for field in EMAIL_FIELDS:
            match = EMAIL_RE.search(clean(row.get(field)))
            if match:
                return match.group(0)
    for row in rows:
        for value in row.values():
            match = EMAIL_RE.search(str(value))
            if match:
                return match.group(0)
    return ""


def find_price(rows):
    # A detected price is not a verified or binding supplier quotation.
    for row in rows:
        for field in PRICE_FIELDS:
            value = clean(row.get(field))
            if value:
                return value, "STRUCTURED PRICE FIELD - VERIFY SOURCE"

    # Search offer text only, not IDs, phone numbers, or arbitrary CSV values.
    for row in rows:
        text = " ".join(clean(row.get(f)) for f in
                        ("product_name", "description", "category"))
        match = CURRENCY_PRICE_RE.search(text)
        if match:
            return match.group(0).strip(), "CURRENCY AMOUNT IN OFFER TEXT - VERIFY SOURCE"
    return "", "NO PRICE FOUND"


def find_moq(rows):
    return find_contact(rows, MOQ_FIELDS)


def make_company_url(rows):
    slug = ""
    for row in rows:
        slug = first_non_empty(row.get("company_ep_slug"), row.get("company_slug"))
        if slug:
            break
    if not slug:
        return ""
    if slug.startswith(("http://", "https://")):
        return slug
    return "https://www.europages.co.uk/" + slug.lstrip("/")


def classify_supplier(products, descriptions, company_name):
    text = normalize(" ".join(products + descriptions + [company_name]))
    manufacturer_terms = (
        "manufacturer", "manufacturing", "producer", "production",
        "factory", "produces", "fabrication"
    )
    trader_terms = (
        "wholesale", "wholesaler", "distributor", "trading company",
        "importer", "exporter", "reseller"
    )
    manufacturer = any(term in text for term in manufacturer_terms)
    trader = any(term in text for term in trader_terms)
    if manufacturer and trader:
        return "POSSIBLE MANUFACTURER / TRADER - VERIFY"
    if manufacturer:
        return "POSSIBLE MANUFACTURER - VERIFY"
    if trader:
        return "POSSIBLE TRADER / DISTRIBUTOR - VERIFY"
    return "UNKNOWN - VERIFY"


def calculate_score(rows, products, descriptions):
    """Research-priority score only; not a probability, profit, or verification."""
    text = normalize(" ".join(
        products + descriptions + [r.get("company_name", "") for r in rows]
    ))
    keyword_points = {
        "manufacturer": 15, "producer": 15, "factory": 15,
        "production": 10, "packaging": 10, "plastic": 5, "bag": 5,
        "film": 5, "bottle": 5, "container": 5, "cardboard": 5,
        "corrugated": 5, "paper": 3, "box": 3, "carton": 3,
    }
    score, matched = 0, []
    for keyword, points in keyword_points.items():
        if keyword in text:
            score += points
            matched.append(keyword)
    price, _ = find_price(rows)
    if price:
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
    company_name = first_non_empty(first.get("company_name"), "Unknown company")
    products = unique_values(rows, "product_name")
    descriptions = unique_values(rows, "description")
    categories = unique_values(rows, "category")
    price, price_evidence = find_price(rows)
    moq = find_moq(rows)
    score, matched = calculate_score(rows, products, descriptions)
    supplier_type = classify_supplier(products, descriptions, company_name)

    email = find_email(rows)
    phone = find_contact(rows, PHONE_FIELDS)
    website = find_contact(rows, WEBSITE_FIELDS)
    company_url = make_company_url(rows)
    offer_url = find_contact(rows, ("offer_url", "url", "link"))

    if price:
        price_status = "REAL PRICE - VERIFY SOURCE"
    elif not products and not descriptions:
        price_status = "INSUFFICIENT DATA"
    else:
        price_status = "QUOTATION NEEDED"

    return {
        "country_code": first.get("country_code", ""),
        "country": first_non_empty(first.get("country"), first.get("country_code")),
        "company_name": company_name,
        "company_id": first.get("company_id", ""),
        "company_uuid": first.get("company_uuid", ""),
        "supplier_type": supplier_type,
        "products_count": len(products),
        "products": " | ".join(products),
        "categories": " | ".join(categories),
        "price": price,
        "price_status": price_status,
        "price_evidence": price_evidence,
        "moq": moq,
        "score": score,
        "matched_keywords": ", ".join(matched),
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
            "Verify company identity and contact details; request written price, "
            "currency, unit, MOQ, capacity, lead time, delivery terms and documents"
        ),
    }


FIELDS = [
    "country_code", "country", "company_name", "company_id", "company_uuid",
    "supplier_type", "products_count", "products", "categories", "price",
    "price_status", "price_evidence", "moq", "score", "matched_keywords",
    "email", "phone", "website", "company_url", "europages_url",
    "is_ep_member", "is_quick_responder", "offers_count",
    "verification_status", "next_action",
]


def save_csv(rows, filename):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    temp_name = filename + ".tmp"
    with open(temp_name, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_name, filename)
    print(f"SAVED: {filename}")
    print(f"ROWS: {len(rows)}")


def create_report(suppliers, offers_count):
    prices = sum(1 for s in suppliers if s["price"])
    quotations = sum(1 for s in suppliers if s["price_status"] == "QUOTATION NEEDED")
    insufficient = sum(1 for s in suppliers if s["price_status"] == "INSUFFICIENT DATA")
    lines = [
        "# B2B YUG SUPPLIER REPORT", "",
        f"Date: {TODAY}",
        f"Offers analysed: {offers_count}",
        f"Unique companies: {len(suppliers)}", "",
        "> Supplier scores are research priorities, not profit estimates.",
        "> Supplier type is inferred from listing text and must be verified.",
        "> A detected price is not a confirmed quotation or final purchase price.",
        "> Verification remains NOT VERIFIED until due diligence is completed.",
        "", "## Price information", "",
        f"- Suppliers with a detected price: {prices}",
        f"- Suppliers requiring a quotation: {quotations}",
        f"- Suppliers with insufficient product data: {insufficient}",
        "", "## Supplier shortlist", "",
    ]
    for index, s in enumerate(suppliers, start=1):
        lines.extend([
            f"### {index}. {s['company_name']}", "",
            f"- Country: {s['country'] or 'N/A'}",
            f"- Type: {s['supplier_type']}",
            f"- Research priority score: {s['score']}/100",
            f"- Products: {s['products'] or 'N/A'}",
            f"- Categories: {s['categories'] or 'N/A'}",
            f"- Detected price: {s['price'] or 'N/A'}",
            f"- Price status: {s['price_status']}",
            f"- Price evidence: {s['price_evidence']}",
            f"- MOQ: {s['moq'] or 'Not found'}",
            f"- Verification: {s['verification_status']}",
            f"- Email: {s['email'] or 'Not found in source data'}",
            f"- Phone: {s['phone'] or 'Not found in source data'}",
            f"- Website: {s['website'] or 'Not found in source data'}",
            f"- Company profile: {s['company_url'] or 'Not found'}",
            f"- Offer URL: {s['europages_url'] or 'Not found'}",
            f"- Next action: {s['next_action']}", "",
        ])
    return "\n".join(lines)


def main():
    print("=" * 68)
    print("B2B YUG SUPPLIER AGENT")
    print("VERSION 3 - INTERNATIONAL SUPPLIER INTELLIGENCE")
    print("=" * 68)
    print(f"DATE: {TODAY}")
    print(f"INPUT: {INPUT_FILE}")

    rows = load_offers(INPUT_FILE)
    print(f"OFFERS LOADED: {len(rows)}")
    if not rows:
        print("No offers loaded. Check input path and CSV contents.")
        return

    companies = group_companies(rows)
    suppliers = [build_supplier(group) for group in companies.values()]
    suppliers.sort(
        key=lambda s: (int(s.get("score", 0)), int(s.get("offers_count", 0))),
        reverse=True,
    )

    save_csv(suppliers, LATEST_SUPPLIERS)
    report = create_report(suppliers, len(rows))
    os.makedirs(os.path.dirname(LATEST_REPORT), exist_ok=True)
    with open(LATEST_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"SAVED: {LATEST_REPORT}")

    save_csv(suppliers, HISTORY_SUPPLIERS)
    with open(HISTORY_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"SAVED: {HISTORY_REPORT}")

    print()
    print("=" * 68)
    print("B2B YUG SUPPLIER AGENT RESULT")
    print("=" * 68)
    print(f"OFFERS ANALYSED: {len(rows)}")
    print(f"COMPANIES FOUND: {len(companies)}")
    print(f"SUPPLIERS: {len(suppliers)}")
    print(f"SUPPLIERS WITH DETECTED PRICE: {sum(1 for s in suppliers if s['price'])}")
    print("SUPPLIERS NEEDING QUOTATION: " + str(
        sum(1 for s in suppliers if s["price_status"] == "QUOTATION NEEDED")
    ))
    if suppliers:
        top = suppliers[0]
        print(f"TOP SUPPLIER: {top['company_name']}")
        print(f"COUNTRY: {top['country']}")
        print(f"RESEARCH PRIORITY SCORE: {top['score']}/100")
        print(f"PRICE STATUS: {top['price_status']}")
        print(f"VERIFICATION: {top['verification_status']}")
    print("SUPPLIER AGENT COMPLETE")


if __name__ == "__main__":
    main()
