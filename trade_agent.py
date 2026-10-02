import csv
import os
import re
from collections import defaultdict
from datetime import datetime


# ============================================================
# B2B YUG TRADE AGENT
# VERSION 1 - BUY / SELL OPPORTUNITY ANALYSIS
# ============================================================

INPUT_FILE = "data/latest/offers_ro_gr.csv"

LATEST_TRADES = "data/latest/trade_opportunities.csv"
LATEST_REPORT = "data/latest/trade_report.md"

TODAY = datetime.now().strftime("%Y-%m-%d")
HISTORY_DIR = f"data/history/{TODAY}"

HISTORY_TRADES = f"{HISTORY_DIR}/trade_opportunities.csv"
HISTORY_REPORT = f"{HISTORY_DIR}/trade_report.md"


# ============================================================
# HELPERS
# ============================================================

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


def safe_int(value):
    try:
        return int(float(value))
    except Exception:
        return 0


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(filename):

    if not os.path.exists(filename):

        print()
        print("ERROR: INPUT FILE NOT FOUND")
        print(filename)

        return []

    with open(
        filename,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        rows = []

        for row in reader:

            rows.append(
                {
                    key: clean(value)
                    for key, value in row.items()
                }
            )

    return rows


# ============================================================
# PRODUCT CLASSIFICATION
# ============================================================

PRODUCT_RULES = {

    "plastic_flexible_packaging": [
        "plastic",
        "polypropylene",
        "polyethylene",
        "pp ",
        "pe ",
        "big bag",
        "big bags",
        "bag",
        "bags",
        "film",
        "films",
        "woven",
        "woven bag",
        "u-panel",
        "fbc",
    ],

    "paper_cardboard_packaging": [
        "paper",
        "cardboard",
        "carton",
        "cartons",
        "box",
        "boxes",
        "paper box",
        "corrugated",
        "paper bowl",
        "paper cup",
    ],

    "food_packaging": [
        "food packaging",
        "food",
        "takeaway",
        "take away",
        "pasta box",
        "menu box",
        "cake box",
        "soup bowl",
        "fresh products",
        "vegetables",
        "fruit",
    ],

    "bags": [
        "bag",
        "bags",
        "sack",
        "sacks",
    ],

    "containers": [
        "container",
        "containers",
        "bottle",
        "bottles",
    ],

    "printing_labels": [
        "label",
        "labels",
        "printing",
        "printed",
    ],
}


def classify_product(text):

    text = normalize(text)

    matches = []

    for category, keywords in PRODUCT_RULES.items():

        for keyword in keywords:

            if keyword in text:

                matches.append(category)
                break

    if not matches:
        return "general_packaging"

    # Prefer food packaging when detected
    if "food_packaging" in matches:
        return "food_packaging"

    if "plastic_flexible_packaging" in matches:
        return "plastic_flexible_packaging"

    if "paper_cardboard_packaging" in matches:
        return "paper_cardboard_packaging"

    return matches[0]


# ============================================================
# BUYER PROFILE
# ============================================================

BUYER_PROFILES = {

    "plastic_flexible_packaging": (
        "food producers, agricultural producers, "
        "chemical companies, construction-material producers, "
        "feed producers and distributors"
    ),

    "paper_cardboard_packaging": (
        "food manufacturers, bakeries, restaurants, "
        "catering companies, e-commerce companies and retailers"
    ),

    "food_packaging": (
        "restaurants, food manufacturers, bakeries, "
        "catering companies, takeaway businesses and food distributors"
    ),

    "bags": (
        "food producers, agricultural companies, "
        "industrial manufacturers and distributors"
    ),

    "containers": (
        "food producers, beverage companies, "
        "chemical companies and distributors"
    ),

    "printing_labels": (
        "food producers, beverage companies, "
        "manufacturers and retailers"
    ),

    "general_packaging": (
        "manufacturers, distributors, food companies "
        "and industrial businesses"
    ),
}


# ============================================================
# PRODUCT TEXT
# ============================================================

def get_product(row):

    return first_non_empty(
        row.get("product_name"),
        row.get("name"),
        row.get("product"),
        row.get("category"),
        "Unknown product"
    )


def get_description(row):

    return clean(
        row.get("description", "")
    )


# ============================================================
# OFFER URL
# ============================================================

def get_offer_url(row):

    return first_non_empty(
        row.get("offer_url"),
        row.get("url"),
        row.get("link")
    )


# ============================================================
# COMPANY URL
# ============================================================

def get_company_url(row):

    slug = first_non_empty(
        row.get("company_ep_slug"),
        row.get("company_slug")
    )

    if not slug:
        return ""

    if slug.startswith("http://"):
        return slug

    if slug.startswith("https://"):
        return slug

    return (
        "https://www.europages.co.uk/"
        + slug.lstrip("/")
    )


# ============================================================
# COMPANY KEY
# ============================================================

def company_key(row):

    country = normalize(
        row.get("country_code", "")
    )

    company_id = normalize(
        row.get("company_id", "")
    )

    company_uuid = normalize(
        row.get("company_uuid", "")
    )

    company_name = normalize(
        row.get("company_name", "")
    )

    if company_id:
        return f"{country}|id|{company_id}"

    if company_uuid:
        return f"{country}|uuid|{company_uuid}"

    return f"{country}|name|{company_name}"


# ============================================================
# TRADE SCORE
# ============================================================

def calculate_trade_score(
    product_text,
    description,
    row
):

    text = normalize(
        product_text + " " + description
    )

    score = 0
    signals = []

    # Packaging relevance
    if "packag" in text:
        score += 15
        signals.append("packaging")

    # Strong commercial products
    strong_keywords = {
        "big bag": 15,
        "big bags": 15,
        "u-panel": 15,
        "bag": 8,
        "bags": 8,
        "plastic": 10,
        "polypropylene": 10,
        "paper": 8,
        "cardboard": 8,
        "carton": 8,
        "boxes": 8,
        "food": 10,
        "takeaway": 10,
    }

    for keyword, points in strong_keywords.items():

        if keyword in text:

            score += points
            signals.append(keyword)

    # MOQ is commercially useful
    if "moq" in text:

        score += 5
        signals.append("MOQ information")

    # Customizable product
    if any(
        word in text
        for word in [
            "custom",
            "customizable",
            "personalized",
            "personalised"
        ]
    ):

        score += 5
        signals.append("customizable")

    # Company membership
    if normalize(
        row.get("is_ep_member", "")
    ) in ["true", "1", "yes"]:

        score += 5
        signals.append("Europages member")

    # Quick responder
    if normalize(
        row.get("is_quick_responder", "")
    ) in ["true", "1", "yes"]:

        score += 5
        signals.append("quick responder")

    if score > 100:
        score = 100

    return score, signals


# ============================================================
# TRADE TYPE
# ============================================================

def determine_trade_type(category):

    if category in [
        "plastic_flexible_packaging",
        "paper_cardboard_packaging",
        "food_packaging",
        "bags",
        "containers",
        "printing_labels"
    ]:

        return "BUY → SELL"

    return "POTENTIAL BUY → SELL"


# ============================================================
# BUILD OPPORTUNITY
# ============================================================

def build_opportunity(row):

    company = first_non_empty(
        row.get("company_name"),
        "Unknown company"
    )

    country = first_non_empty(
        row.get("country"),
        row.get("country_code")
    )

    country_code = row.get(
        "country_code",
        ""
    )

    product = get_product(row)

    description = get_description(row)

    full_text = (
        product
        + " "
        + description
    )

    category = classify_product(
        full_text
    )

    score, signals = calculate_trade_score(
        product,
        description,
        row
    )

    buyer_profile = BUYER_PROFILES.get(
        category,
        BUYER_PROFILES["general_packaging"]
    )

    offer_url = get_offer_url(row)

    company_url = get_company_url(row)

    trade_type = determine_trade_type(
        category
    )

    return {

        "country_code":
            country_code,

        "country":
            country,

        "supplier":
            company,

        "supplier_company_id":
            row.get("company_id", ""),

        "supplier_company_uuid":
            row.get("company_uuid", ""),

        "product":
            product,

        "product_category":
            category,

        "description":
            description,

        "trade_type":
            trade_type,

        "potential_buyers":
            buyer_profile,

        "buy_price":
            "",

        "sell_price":
            "",

        "transport_cost":
            "",

        "estimated_margin":
            "",

        "profit_status":
            "PRICE DATA NEEDED",

        "trade_score":
            score,

        "signals":
            ", ".join(signals),

        "offer_url":
            offer_url,

        "company_url":
            company_url,
    }


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def deduplicate_opportunities(rows):

    result = []
    seen = set()

    for row in rows:

        key = (
            normalize(row["country_code"]),
            normalize(row["supplier"]),
            normalize(row["product"])
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(row)

    return result


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(rows, filename):

    os.makedirs(
        os.path.dirname(filename) or ".",
        exist_ok=True
    )

    fieldnames = [

        "country_code",
        "country",
        "supplier",
        "supplier_company_id",
        "supplier_company_uuid",
        "product",
        "product_category",
        "description",
        "trade_type",
        "potential_buyers",
        "buy_price",
        "sell_price",
        "transport_cost",
        "estimated_margin",
        "profit_status",
        "trade_score",
        "signals",
        "offer_url",
        "company_url",
    ]

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(rows)

    print()
    print("SAVED:", filename)
    print("ROWS:", len(rows))


# ============================================================
# REPORT
# ============================================================

def create_report(
    opportunities,
    offers_count
):

    lines = []

    lines.append(
        "# B2B YUG TRADE OPPORTUNITY REPORT"
    )

    lines.append("")

    lines.append(
        f"Date: {TODAY}"
    )

    lines.append(
        f"Offers analysed: {offers_count}"
    )

    lines.append(
        f"Trade opportunities: {len(opportunities)}"
    )

    lines.append("")

    lines.append(
        "## IMPORTANT"
    )

    lines.append("")

    lines.append(
        "This version identifies potential BUY → SELL "
        "opportunities from the monitored supplier offers."
    )

    lines.append("")

    lines.append(
        "Actual buy price, sell price and transport cost "
        "are not invented. They must be obtained before "
        "calculating a real profit margin."
    )

    lines.append("")

    # --------------------------------------------------------
    # TOP OPPORTUNITIES
    # --------------------------------------------------------

    lines.append(
        "## Top Opportunities"
    )

    lines.append("")

    for index, opportunity in enumerate(
        opportunities[:20],
        start=1
    ):

        lines.append(
            f"### {index}. {opportunity['product']}"
        )

        lines.append("")

        lines.append(
            f"- Supplier: {opportunity['supplier']}"
        )

        lines.append(
            f"- Country: {opportunity['country']}"
        )

        lines.append(
            f"- Category: {opportunity['product_category']}"
        )

        lines.append(
            f"- Trade type: {opportunity['trade_type']}"
        )

        lines.append(
            f"- Potential buyers: "
            f"{opportunity['potential_buyers']}"
        )

        lines.append(
            f"- Trade score: "
            f"{opportunity['trade_score']}"
        )

        lines.append(
            f"- Signals: "
            f"{opportunity['signals'] or 'none'}"
        )

        lines.append(
            "- Buy price: NOT AVAILABLE"
        )

        lines.append(
            "- Sell price: NOT AVAILABLE"
        )

        lines.append(
            "- Transport: NOT AVAILABLE"
        )

        lines.append(
            "- Margin: CANNOT CALCULATE YET"
        )

        if opportunity["company_url"]:

            lines.append(
                f"- Company: "
                f"{opportunity['company_url']}"
            )

        if opportunity["offer_url"]:

            lines.append(
                f"- Offer: "
                f"{opportunity['offer_url']}"
            )

        lines.append("")

    # --------------------------------------------------------
    # ALL OPPORTUNITIES TABLE
    # --------------------------------------------------------

    lines.append(
        "## All Opportunities"
    )

    lines.append("")

    lines.append(
        "| # | Supplier | Country | Product | Category | Score |"
    )

    lines.append(
        "|---|---|---|---|---|---:|"
    )

    for index, opportunity in enumerate(
        opportunities,
        start=1
    ):

        supplier = opportunity["supplier"]
        country = opportunity["country"]
        product = opportunity["product"]
        category = opportunity["product_category"]
        score = opportunity["trade_score"]

        lines.append(
            f"| {index} | {supplier} | {country} | "
            f"{product} | {category} | {score} |"
        )

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "B2B YUG TRADE AGENT"
    )

    print(
        "VERSION 1 - BUY / SELL OPPORTUNITY ANALYSIS"
    )

    print("=" * 70)

    print()

    print(
        "INPUT:",
        INPUT_FILE
    )

    rows = load_csv(
        INPUT_FILE
    )

    print(
        "OFFERS LOADED:",
        len(rows)
    )

    if not rows:

        print()
        print(
            "NO OFFERS AVAILABLE."
        )

        return

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    opportunities = []

    for row in rows:

        opportunity = build_opportunity(
            row
        )

        opportunities.append(
            opportunity
        )

    opportunities = deduplicate_opportunities(
        opportunities
    )

    # Highest trade score first
    opportunities.sort(
        key=lambda x: x["trade_score"],
        reverse=True
    )

    # --------------------------------------------------------
    # SAVE LATEST
    # --------------------------------------------------------

    save_csv(
        opportunities,
        LATEST_TRADES
    )

    report = create_report(
        opportunities,
        len(rows)
    )

    os.makedirs(
        "data/latest",
        exist_ok=True
    )

    with open(
        LATEST_REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report)

    print()
    print(
        "SAVED:",
        LATEST_REPORT
    )

    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    save_csv(
        opportunities,
        HISTORY_TRADES
    )

    os.makedirs(
        HISTORY_DIR,
        exist_ok=True
    )

    with open(
        HISTORY_REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report)

    print(
        "SAVED:",
        HISTORY_REPORT
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)

    print(
        "B2B TRADE AGENT"
    )

    print("=" * 70)

    print(
        "OFFERS ANALYSED:",
        len(rows)
    )

    print(
        "TRADE OPPORTUNITIES:",
        len(opportunities)
    )

    if opportunities:

        print()

        print(
            "TOP OPPORTUNITY:"
        )

        print(
            opportunities[0]["product"]
        )

        print(
            "SUPPLIER:",
            opportunities[0]["supplier"]
        )

        print(
            "COUNTRY:",
            opportunities[0]["country"]
        )

        print(
            "CATEGORY:",
            opportunities[0]["product_category"]
        )

        print(
            "TRADE SCORE:",
            opportunities[0]["trade_score"]
        )

    print()

    print(
        "SAVED:",
        LATEST_TRADES
    )

    print(
        "SAVED:",
        LATEST_REPORT
    )

    print()

    print("=" * 70)

    print(
        "TRADE AGENT COMPLETE"
    )

    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
