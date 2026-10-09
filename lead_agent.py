import csv
import os
import re
from collections import defaultdict
from datetime import datetime


# ============================================================
# B2B YUG LEAD AGENT
# VERSION 4 - SALES INTELLIGENCE
# ============================================================

INPUT_FILE = "data/latest/offers_yug.csv"
LATEST_LEADS = "data/latest/leads.csv"
LATEST_REPORT = "data/latest/daily_report.md"

TODAY = datetime.now().strftime("%Y-%m-%d")

HISTORY_DIR = f"data/history/{TODAY}"

HISTORY_LEADS = f"{HISTORY_DIR}/leads.csv"
HISTORY_REPORT = f"{HISTORY_DIR}/daily_report.md"


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


def is_true(value):
    return normalize(value) in [
        "true",
        "1",
        "yes",
        "y",
        "да",
    ]


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
# FIND FIELDS
# ============================================================

def find_field(row, possible_names):

    for name in possible_names:

        if name in row:

            value = clean(
                row.get(name)
            )

            if value:
                return value

    return ""


def find_email(row):

    value = find_field(
        row,
        [
            "email",
            "email_existing",
            "contact_email",
            "company_email",
        ]
    )

    if value:
        return value

    email_pattern = (
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )

    for field_value in row.values():

        match = re.search(
            email_pattern,
            str(field_value)
        )

        if match:
            return match.group(0)

    return ""


def find_phone(row):

    return find_field(
        row,
        [
            "phone",
            "telephone",
            "telephone_number",
            "phone_number",
            "mobile",
            "contact_phone",
        ]
    )


def find_website(row):

    return find_field(
        row,
        [
            "website",
            "company_website",
            "web",
            "website_url",
        ]
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
# GROUP COMPANIES
# ============================================================

def group_companies(rows):

    companies = defaultdict(list)

    for row in rows:

        key = company_key(row)

        companies[key].append(row)

    return companies


# ============================================================
# PRODUCTS
# ============================================================

def collect_products(rows):

    products = []

    seen = set()

    for row in rows:

        product = first_non_empty(
            row.get("product_name"),
            row.get("name"),
            row.get("product"),
            row.get("category"),
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
# DESCRIPTIONS
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
# EUROPAGES URL
# ============================================================

def find_europages_url(rows):

    for row in rows:

        url = first_non_empty(
            row.get("offer_url"),
            row.get("url"),
            row.get("link"),
        )

        if url:
            return url

    return ""


# ============================================================
# COMPANY URL
# ============================================================

def create_company_url(row):

    slug = first_non_empty(
        row.get("company_ep_slug"),
        row.get("company_slug"),
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
# SALES KEYWORDS
# ============================================================

KEYWORDS = {

    # Core packaging
    "packaging": 15,
    "packaging material": 15,
    "packaging materials": 15,
    "food packaging": 18,
    "industrial packaging": 18,
    "flexible packaging": 18,

    # Plastic
    "plastic": 10,
    "plastics": 10,
    "polyethylene": 12,
    "polypropylene": 12,
    "pet": 8,
    "pvc": 8,

    # Bags / films
    "bag": 10,
    "bags": 10,
    "film": 10,
    "films": 10,
    "stretch film": 14,
    "shrink film": 14,

    # Containers
    "bottle": 10,
    "bottles": 10,
    "container": 10,
    "containers": 10,
    "jerrycan": 8,
    "drum": 8,

    # Paper
    "paper": 7,
    "cardboard": 10,
    "carton": 10,
    "cartons": 10,
    "corrugated": 12,

    # Labels / printing
    "label": 8,
    "labels": 8,
    "printing": 6,
    "printed packaging": 15,

    # Industrial
    "pallet": 7,
    "pallets": 7,
    "industrial": 5,
}


# ============================================================
# TEXT ANALYSIS
# ============================================================

def collect_text(rows):

    parts = []

    for row in rows:

        parts.append(
            row.get("product_name", "")
        )

        parts.append(
            row.get("description", "")
        )

        parts.append(
            row.get("category", "")
        )

    return normalize(
        " ".join(parts)
    )


# ============================================================
# SCORE
# ============================================================

def calculate_score(rows):

    text = collect_text(rows)

    score = 0

    matched_keywords = []

    for keyword, points in KEYWORDS.items():

        if keyword in text:

            score += points

            matched_keywords.append(
                keyword
            )

    products = collect_products(rows)

    product_count = len(products)

    # Product diversity
    if product_count >= 5:

        score += 15

    elif product_count >= 3:

        score += 10

    elif product_count == 2:

        score += 5

    # Europages indicators
    first = rows[0]

    if is_true(
        first.get("is_ep_member", "")
    ):

        score += 5

    if is_true(
        first.get("is_wlw_member", "")
    ):

        score += 3

    if is_true(
        first.get("is_quick_responder", "")
    ):

        score += 8

    # Contact availability
    contact_bonus = 0

    for row in rows:

        if find_email(row):

            contact_bonus += 8
            break

    if contact_bonus:

        score += contact_bonus

    for row in rows:

        if find_phone(row):

            score += 5
            break

    # Company profile
    if create_company_url(first):

        score += 4

    # Website
    for row in rows:

        if find_website(row):

            score += 4
            break

    # Cap
    if score > 100:

        score = 100

    return score, matched_keywords


# ============================================================
# PRIORITY
# ============================================================

def get_priority(score):

    if score >= 70:
        return "HIGH"

    if score >= 45:
        return "MEDIUM"

    return "LOW"


# ============================================================
# LEAD TYPE
# ============================================================

def determine_lead_type(
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
            "plastic",
            "polyethylene",
            "polypropylene",
            "film",
            "bag",
            "pet",
            "pvc",
        ]
    ):

        return "Plastic / flexible packaging"

    if any(
        word in text
        for word in [
            "cardboard",
            "carton",
            "corrugated",
            "paper",
        ]
    ):

        return "Paper / cardboard packaging"

    if any(
        word in text
        for word in [
            "bottle",
            "container",
            "jerrycan",
            "drum",
        ]
    ):

        return "Containers / bottles"

    if any(
        word in text
        for word in [
            "label",
            "labels",
            "printing",
        ]
    ):

        return "Labels / printing"

    return "General packaging"


# ============================================================
# SALES OPPORTUNITY
# ============================================================

def create_sales_opportunity(
    products,
    descriptions
):

    lead_type = determine_lead_type(
        products,
        descriptions
    )

    mapping = {

        "Plastic / flexible packaging":
            "Potential B2B opportunity related to plastic or flexible packaging.",

        "Paper / cardboard packaging":
            "Potential B2B opportunity related to paper, cardboard or corrugated packaging.",

        "Containers / bottles":
            "Potential B2B opportunity related to containers or bottles.",

        "Labels / printing":
            "Potential B2B opportunity related to labels, printing or printed packaging.",

        "General packaging":
            "Potential B2B opportunity related to packaging products or services.",
    }

    return mapping.get(
        lead_type,
        mapping["General packaging"]
    )


# ============================================================
# WHY LEAD
# ============================================================

def create_reason(
    rows,
    matched_keywords
):

    reasons = []

    products = collect_products(rows)

    if products:

        reasons.append(
            f"{len(products)} distinct product/offering(s)"
        )

    if matched_keywords:

        reasons.append(
            "keywords: "
            + ", ".join(
                matched_keywords[:6]
            )
        )

    first = rows[0]

    if is_true(
        first.get("is_quick_responder", "")
    ):

        reasons.append(
            "quick responder"
        )

    if is_true(
        first.get("is_ep_member", "")
    ):

        reasons.append(
            "Europages member"
        )

    has_email = any(
        find_email(row)
        for row in rows
    )

    has_phone = any(
        find_phone(row)
        for row in rows
    )

    has_website = any(
        find_website(row)
        for row in rows
    )

    if has_email:

        reasons.append(
            "email available in source data"
        )

    if has_phone:

        reasons.append(
            "phone available in source data"
        )

    if has_website:

        reasons.append(
            "website available in source data"
        )

    if not reasons:

        reasons.append(
            "matches monitored packaging search"
        )

    return "; ".join(reasons)


# ============================================================
# BUILD LEAD
# ============================================================

def build_lead(rows):

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

    products = collect_products(rows)

    descriptions = collect_descriptions(rows)

    score, matched_keywords = calculate_score(
        rows
    )

    priority = get_priority(score)

    email = ""

    phone = ""

    website = ""

    for row in rows:

        email = first_non_empty(
            email,
            find_email(row)
        )

        phone = first_non_empty(
            phone,
            find_phone(row)
        )

        website = first_non_empty(
            website,
            find_website(row)
        )

    europages_url = find_europages_url(
        rows
    )

    company_url = create_company_url(
        first
    )

    lead_type = determine_lead_type(
        products,
        descriptions
    )

    reason = create_reason(
        rows,
        matched_keywords
    )

    opportunity = create_sales_opportunity(
        products,
        descriptions
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

        "products_count":
            len(products),

        "products":
            " | ".join(products),

        "lead_type":
            lead_type,

        "score":
            score,

        "priority":
            priority,

        "lead_reason":
            reason,

        "sales_opportunity":
            opportunity,

        "email":
            email,

        "phone":
            phone,

        "website":
            website,

        "europages_url":
            europages_url,

        "company_url":
            company_url,

        "founding_year":
            first.get(
                "founding_year",
                ""
            ),

        "distribution_area":
            first.get(
                "distribution_area",
                ""
            ),

        "is_ep_member":
            first.get(
                "is_ep_member",
                ""
            ),

        "is_wlw_member":
            first.get(
                "is_wlw_member",
                ""
            ),

        "is_quick_responder":
            first.get(
                "is_quick_responder",
                ""
            ),
    }


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
        "company_name",
        "company_id",
        "company_uuid",
        "products_count",
        "products",
        "lead_type",
        "score",
        "priority",
        "lead_reason",
        "sales_opportunity",
        "email",
        "phone",
        "website",
        "europages_url",
        "company_url",
        "founding_year",
        "distribution_area",
        "is_ep_member",
        "is_wlw_member",
        "is_quick_responder",
    ]

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()

        writer.writerows(rows)

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
    leads,
    offers_count
):

    lines = []

    lines.append(
        "# B2B YUG DAILY LEAD REPORT"
    )

    lines.append("")

    lines.append(
        f"Date: {TODAY}"
    )

    lines.append(
        f"Offers analysed: {offers_count}"
    )

    lines.append(
        f"Companies analysed: {len(leads)}"
    )

    lines.append("")

    high = sum(
        1
        for lead in leads
        if lead["priority"] == "HIGH"
    )

    medium = sum(
        1
        for lead in leads
        if lead["priority"] == "MEDIUM"
    )

    low = sum(
        1
        for lead in leads
        if lead["priority"] == "LOW"
    )

    lines.append(
        "## Lead Summary"
    )

    lines.append("")

    lines.append(
        f"- HIGH: {high}"
    )

    lines.append(
        f"- MEDIUM: {medium}"
    )

    lines.append(
        f"- LOW: {low}"
    )

    lines.append("")

    # --------------------------------------------------------
    # TOP LEADS
    # --------------------------------------------------------

    if leads:

        lines.append(
            "## Top Leads"
        )

        lines.append("")

        for index, lead in enumerate(
            leads[:5],
            start=1
        ):

            lines.append(
                f"### {index}. {lead['company_name']}"
            )

            lines.append("")

            lines.append(
                f"- Country: {lead['country']}"
            )

            lines.append(
                f"- Score: {lead['score']}"
            )

            lines.append(
                f"- Priority: {lead['priority']}"
            )

            lines.append(
                f"- Lead type: {lead['lead_type']}"
            )

            lines.append(
                f"- Products: "
                f"{lead['products'] or 'N/A'}"
            )

            lines.append(
                f"- Why: "
                f"{lead['lead_reason']}"
            )

            lines.append(
                f"- Opportunity: "
                f"{lead['sales_opportunity']}"
            )

            if lead["email"]:

                lines.append(
                    f"- Email: {lead['email']}"
                )

            if lead["phone"]:

                lines.append(
                    f"- Phone: {lead['phone']}"
                )

            if lead["website"]:

                lines.append(
                    f"- Website: {lead['website']}"
                )

            if lead["company_url"]:

                lines.append(
                    f"- Company profile: "
                    f"{lead['company_url']}"
                )

            lines.append("")

    # --------------------------------------------------------
    # ALL LEADS TABLE
    # --------------------------------------------------------

    lines.append(
        "## All Leads"
    )

    lines.append("")

    lines.append(
        "| # | Company | Country | Score | Priority | Lead type | Products |"
    )

    lines.append(
        "|---:|---|---|---:|---|---|---:|"
    )

    for index, lead in enumerate(
        leads,
        start=1
    ):

        products_count = lead[
            "products_count"
        ]

        lines.append(
            f"| {index} | "
            f"{lead['company_name']} | "
            f"{lead['country']} | "
            f"{lead['score']} | "
            f"{lead['priority']} | "
            f"{lead['lead_type']} | "
            f"{products_count} |"
        )

    lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "B2B YUG LEAD AGENT"
    )

    print(
        "VERSION 4 - SALES INTELLIGENCE"
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

    leads = []

    for company_rows in companies.values():

        lead = build_lead(
            company_rows
        )

        leads.append(
            lead
        )

    # Highest score first
    leads.sort(
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
        leads,
        LATEST_LEADS
    )

    report = create_report(
        leads,
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
        leads,
        HISTORY_LEADS
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

    high = sum(
        1
        for lead in leads
        if lead["priority"] == "HIGH"
    )

    medium = sum(
        1
        for lead in leads
        if lead["priority"] == "MEDIUM"
    )

    low = sum(
        1
        for lead in leads
        if lead["priority"] == "LOW"
    )

    print()
    print("=" * 70)

    print(
        "B2B LEAD AGENT"
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
        "QUALIFIED LEADS:",
        len(leads)
    )

    print(
        "HIGH:",
        high
    )

    print(
        "MEDIUM:",
        medium
    )

    print(
        "LOW:",
        low
    )

    if leads:

        print()

        print(
            "TOP LEAD:",
            leads[0]["company_name"]
        )

        print(
            "TOP SCORE:",
            leads[0]["score"]
        )

    else:

        print()

        print(
            "TOP LEAD: none"
        )

        print(
            "TOP SCORE: 0"
        )

    print()

    print(
        "SAVED:",
        LATEST_LEADS
    )

    print(
        "SAVED:",
        LATEST_REPORT
    )

    print()

    print("=" * 70)

    print(
        "LEAD AGENT COMPLETE"
    )

    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
