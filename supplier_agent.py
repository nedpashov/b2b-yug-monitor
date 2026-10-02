import csv
import os
import re
from collections import defaultdict
from datetime import datetime


# ============================================================
# B2B YUG SUPPLIER AGENT
# VERSION 1 - SUPPLIER INTELLIGENCE
# ============================================================

INPUT_FILE = "data/latest/offers_ro_gr.csv"

LATEST_SUPPLIERS = "data/latest/suppliers.csv"
LATEST_REPORT = "data/latest/supplier_report.md"

TODAY = datetime.now().strftime("%Y-%m-%d")

HISTORY_DIR = f"data/history/{TODAY}"

HISTORY_SUPPLIERS = f"{HISTORY_DIR}/suppliers.csv"
HISTORY_REPORT = f"{HISTORY_DIR}/supplier_report.md"


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


# ============================================================
# LOAD CSV
# ============================================================

def load_offers(filename):

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
# GROUP OFFERS BY COMPANY
# ============================================================

def group_companies(rows):

    companies = defaultdict(list)

    for row in rows:

        key = company_key(row)

        companies[key].append(row)

    return companies


# ============================================================
# PRODUCT EXTRACTION
# ============================================================

def collect_products(rows):

    products = []

    seen = set()

    for row in rows:

        product = first_non_empty(
            row.get("product_name"),
            row.get("name"),
            row.get("product"),
            row.get("category")
        )

        if not product:
            continue

        key = normalize(product)

        if key in seen:
            continue

        seen.add(key)

        products.append(product)

    return products


# ============================================================
# DESCRIPTION EXTRACTION
# ============================================================

def collect_descriptions(rows):

    descriptions = []

    seen = set()

    for row in rows:

        description = clean(
            row.get("description", "")
        )

        if not description:
            continue

        key = normalize(description)

        if key in seen:
            continue

        seen.add(key)

        descriptions.append(description)

    return descriptions


# ============================================================
# CONTACT INFORMATION
# ============================================================

def find_email(rows):

    email_pattern = (
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )

    possible_fields = [
        "email",
        "email_existing",
        "contact_email",
        "company_email"
    ]

    for row in rows:

        for field in possible_fields:

            value = clean(
                row.get(field, "")
            )

            if value:
                return value

        for value in row.values():

            match = re.search(
                email_pattern,
                str(value)
            )

            if match:
                return match.group(0)

    return ""


def find_phone(rows):

    possible_fields = [
        "phone",
        "telephone",
        "telephone_number",
        "phone_number",
        "mobile"
    ]

    for row in rows:

        for field in possible_fields:

            value = clean(
                row.get(field, "")
            )

            if value:
                return value

    return ""


def find_website(rows):

    possible_fields = [
        "website",
        "company_website",
        "web",
        "website_url"
    ]

    for row in rows:

        for field in possible_fields:

            value = clean(
                row.get(field, "")
            )

            if value:
                return value

    return ""


# ============================================================
# EUROPAGES URL
# ============================================================

def find_europages_url(rows):

    for row in rows:

        url = first_non_empty(
            row.get("offer_url"),
            row.get("url"),
            row.get("link")
        )

        if url:
            return url

    return ""


# ============================================================
# COMPANY PROFILE URL
# ============================================================

def create_company_url(row):

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
# PRICE DETECTION
# ============================================================

def find_price(rows):

    possible_fields = [
        "price",
        "unit_price",
        "price_value",
        "selling_price",
        "offer_price"
    ]

    for row in rows:

        for field in possible_fields:

            value = clean(
                row.get(field, "")
            )

            if value:

                return value

    # Try to find price inside text
    price_pattern = (
        r"(?:€|EUR)\s*\d+(?:[.,]\d+)?"
    )

    for row in rows:

        text = " ".join(
            str(value)
            for value in row.values()
        )

        match = re.search(
            price_pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(0)

    return ""


# ============================================================
# MOQ DETECTION
# ============================================================

def find_moq(rows):

    possible_fields = [
        "moq",
        "minimum_order_quantity",
        "min_order_quantity",
        "minimum_quantity"
    ]

    for row in rows:

        for field in possible_fields:

            value = clean(
                row.get(field, "")
            )

            if value:

                return value

    return ""


# ============================================================
# SUPPLIER KEYWORDS
# ============================================================

SUPPLIER_KEYWORDS = {

    "manufacturer": 20,
    "manufacturer of": 20,
    "producer": 20,
    "production": 15,
    "factory": 20,
    "manufacturer and": 15,

    "packaging": 15,
    "packaging material": 15,
    "packaging materials": 15,

    "plastic": 10,
    "plastics": 10,

    "bag": 10,
    "bags": 10,

    "film": 10,
    "films": 10,

    "bottle": 10,
    "bottles": 10,

    "container": 10,
    "containers": 10,

    "box": 10,
    "boxes": 10,

    "carton": 10,
    "cartons": 10,

    "cardboard": 10,
    "corrugated": 10,

    "paper": 5,

    "labels": 8,
    "label": 8,

    "printing": 5
}


# ============================================================
# SUPPLIER SCORE
# ============================================================

def calculate_supplier_score(rows):

    score = 0

    text_parts = []

    for row in rows:

        text_parts.append(
            row.get("product_name", "")
        )

        text_parts.append(
            row.get("description", "")
        )

        text_parts.append(
            row.get("category", "")
        )

        text_parts.append(
            row.get("company_name", "")
        )

    text = normalize(
        " ".join(text_parts)
    )

    matched_keywords = []

    for keyword, points in SUPPLIER_KEYWORDS.items():

        if keyword in text:

            score += points

            matched_keywords.append(
                keyword
            )

    # Price available
    price = find_price(rows)

    if price:

        score += 10

    # MOQ available
    moq = find_moq(rows)

    if moq:

        score += 5

    first = rows[0]

    # Europages member
    if normalize(
        first.get("is_ep_member", "")
    ) in ["true", "1", "yes"]:

        score += 5

    # Quick responder
    if normalize(
        first.get("is_quick_responder", "")
    ) in ["true", "1", "yes"]:

        score += 5

    if score > 100:

        score = 100

    return score, matched_keywords


# ============================================================
# SUPPLIER TYPE
# ============================================================

def determine_supplier_type(
    products,
    descriptions
):

    text = normalize(
        " ".join(
            products + descriptions
        )
    )

    if any(
        word in text
        for word in [
            "manufacturer",
            "producer",
            "factory",
            "production"
        ]
    ):

        return "MANUFACTURER"

    return "SUPPLIER"


# ============================================================
# PRICE STATUS
# ============================================================

def determine_price_status(price):

    if price:

        return "REAL PRICE"

    return "QUOTATION NEEDED"


# ============================================================
# SUPPLIER OPPORTUNITY
# ============================================================

def create_supplier_opportunity(
    products,
    descriptions,
    price,
    moq
):

    text = normalize(
        " ".join(
            products + descriptions
        )
    )

    if any(
        word in text
        for word in [
            "plastic",
            "polyethylene",
            "polypropylene",
            "film",
            "bag"
        ]
    ):

        opportunity = (
            "Potential sourcing opportunity "
            "for plastic/flexible packaging."
        )

    elif any(
        word in text
        for word in [
            "cardboard",
            "carton",
            "corrugated",
            "paper"
        ]
    ):

        opportunity = (
            "Potential sourcing opportunity "
            "for paper/cardboard packaging."
        )

    elif any(
        word in text
        for word in [
            "bottle",
            "container"
        ]
    ):

        opportunity = (
            "Potential sourcing opportunity "
            "for bottles/containers."
        )

    else:

        opportunity = (
            "Potential sourcing opportunity "
            "for packaging products/services."
        )

    if price:

        opportunity += (
            " Published price available."
        )

    else:

        opportunity += (
            " Supplier quotation required."
        )

    if moq:

        opportunity += (
            f" MOQ information: {moq}."
        )

    return opportunity


# ============================================================
# BUILD SUPPLIER
# ============================================================

def build_supplier(rows):

    first = rows[0]

    company_name = first_non_empty(
        first.get("company_name"),
        "Unknown company"
    )

    country = first_non_empty(
        first.get("country"),
        first.get("country_code")
    )

    country_code = first.get(
        "country_code",
        ""
    )

    products = collect_products(
        rows
    )

    descriptions = collect_descriptions(
        rows
    )

    score, matched_keywords = (
        calculate_supplier_score(rows)
    )

    supplier_type = determine_supplier_type(
        products,
        descriptions
    )

    price = find_price(
        rows
    )

    moq = find_moq(
        rows
    )

    price_status = determine_price_status(
        price
    )

    email = find_email(
        rows
    )

    phone = find_phone(
        rows
    )

    website = find_website(
        rows
    )

    europages_url = find_europages_url(
        rows
    )

    company_url = create_company_url(
        first
    )

    opportunity = create_supplier_opportunity(
        products,
        descriptions,
        price,
        moq
    )

    return {

        "country_code":
            country_code,

        "country":
            country,

        "company_name":
            company_name,

        "company_id":
            first.get(
                "company_id",
                ""
            ),

        "company_uuid":
            first.get(
                "company_uuid",
                ""
            ),

        "supplier_type":
            supplier_type,

        "products_count":
            len(products),

        "products":
            " | ".join(products),

        "price":
            price,

        "price_status":
            price_status,

        "moq":
            moq,

        "score":
            score,

        "matched_keywords":
            ", ".join(
                matched_keywords
            ),

        "supplier_opportunity":
            opportunity,

        "email":
            email,

        "phone":
            phone,

        "website":
            website,

        "company_url":
            company_url,

        "europages_url":
            europages_url,

        "is_ep_member":
            first.get(
                "is_ep_member",
                ""
            ),

        "is_quick_responder":
            first.get(
                "is_quick_responder",
                ""
            )
    }


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(
    rows,
    filename
):

    os.makedirs(
        os.path.dirname(filename)
        or ".",
        exist_ok=True
    )

    fieldnames = [

        "country_code",
        "country",
        "company_name",
        "company_id",
        "company_uuid",

        "supplier_type",

        "products_count",
        "products",

        "price",
        "price_status",
        "moq",

        "score",
        "matched_keywords",

        "supplier_opportunity",

        "email",
        "phone",
        "website",

        "company_url",
        "europages_url",

        "is_ep_member",
        "is_quick_responder"
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

        writer.writerows(
            rows
        )

    print()
    print(
        "SAVED:",
        filename
    )

    print(
        "ROWS:",
        len(rows)
    )


# ============================================================
# REPORT
# ============================================================

def create_report(
    suppliers,
    offers_count
):

    lines = []

    lines.append(
        "# B2B YUG SUPPLIER REPORT"
    )

    lines.append("")

    lines.append(
        f"Date: {TODAY}"
    )

    lines.append(
        f"Offers analysed: {offers_count}"
    )

    lines.append(
        f"Suppliers found: {len(suppliers)}"
    )

    lines.append("")

    # Price statistics

    real_price = sum(
        1
        for supplier in suppliers
        if supplier["price_status"]
        == "REAL PRICE"
    )

    quotation_needed = sum(
        1
        for supplier in suppliers
        if supplier["price_status"]
        == "QUOTATION NEEDED"
    )

    lines.append(
        "## Price Information"
    )

    lines.append("")

    lines.append(
        f"- REAL PRICE: {real_price}"
    )

    lines.append(
        f"- QUOTATION NEEDED: {quotation_needed}"
    )

    lines.append("")

    # Top suppliers

    lines.append(
        "## Supplier Opportunities"
    )

    lines.append("")

    for index, supplier in enumerate(
        suppliers,
        start=1
    ):

        lines.append(
            f"### {index}. "
            f"{supplier['company_name']}"
        )

        lines.append("")

        lines.append(
            f"- Country: "
            f"{supplier['country']}"
        )

        lines.append(
            f"- Type: "
            f"{supplier['supplier_type']}"
        )

        lines.append(
            f"- Score: "
            f"{supplier['score']}"
        )

        lines.append(
            f"- Products: "
            f"{supplier['products'] or 'N/A'}"
        )

        lines.append(
            f"- Price: "
            f"{supplier['price'] or 'N/A'}"
        )

        lines.append(
            f"- Price status: "
            f"{supplier['price_status']}"
        )

        lines.append(
            f"- MOQ: "
            f"{supplier['moq'] or 'N/A'}"
        )

        lines.append(
            f"- Opportunity: "
            f"{supplier['supplier_opportunity']}"
        )

        if supplier["email"]:

            lines.append(
                f"- Email: "
                f"{supplier['email']}"
            )

        if supplier["phone"]:

            lines.append(
                f"- Phone: "
                f"{supplier['phone']}"
            )

        if supplier["website"]:

            lines.append(
                f"- Website: "
                f"{supplier['website']}"
            )

        if supplier["company_url"]:

            lines.append(
                f"- Company profile: "
                f"{supplier['company_url']}"
            )

        if supplier["europages_url"]:

            lines.append(
                f"- Europages: "
                f"{supplier['europages_url']}"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "B2B YUG SUPPLIER AGENT"
    )

    print(
        "VERSION 1 - SUPPLIER INTELLIGENCE"
    )

    print("=" * 70)

    print()

    print(
        "INPUT:",
        INPUT_FILE
    )

    rows = load_offers(
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

    companies = group_companies(
        rows
    )

    suppliers = []

    for company_rows in companies.values():

        supplier = build_supplier(
            company_rows
        )

        suppliers.append(
            supplier
        )

    # Highest score first

    suppliers.sort(
        key=lambda x: (
            x["score"],
            x["products_count"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # SAVE LATEST
    # --------------------------------------------------------

    save_csv(
        suppliers,
        LATEST_SUPPLIERS
    )

    report = create_report(
        suppliers,
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

        f.write(
            report
        )

    print()

    print(
        "SAVED:",
        LATEST_REPORT
    )

    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    save_csv(
        suppliers,
        HISTORY_SUPPLIERS
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

        f.write(
            report
        )

    print(
        "SAVED:",
        HISTORY_REPORT
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    real_price = sum(
        1
        for supplier in suppliers
        if supplier["price_status"]
        == "REAL PRICE"
    )

    quotation_needed = sum(
        1
        for supplier in suppliers
        if supplier["price_status"]
        == "QUOTATION NEEDED"
    )

    print()

    print("=" * 70)

    print(
        "B2B YUG SUPPLIER AGENT"
    )

    print("=" * 70)

    print(
        "OFFERS ANALYSED:",
        len(rows)
    )

    print(
        "COMPANIES FOUND:",
        len(companies)
    )

    print(
        "SUPPLIERS:",
        len(suppliers)
    )

    print(
        "REAL PRICE:",
        real_price
    )

    print(
        "QUOTATION NEEDED:",
        quotation_needed
    )

    if suppliers:

        print()

        print(
            "TOP SUPPLIER:",
            suppliers[0]["company_name"]
        )

        print(
            "TOP SCORE:",
            suppliers[0]["score"]
        )

    else:

        print()

        print(
            "TOP SUPPLIER: none"
        )

        print(
            "TOP SCORE: 0"
        )

    print()

    print(
        "SAVED:",
        LATEST_SUPPLIERS
    )

    print(
        "SAVED:",
        LATEST_REPORT
    )

    print()

    print("=" * 70)

    print(
        "SUPPLIER AGENT COMPLETE"
    )

    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
