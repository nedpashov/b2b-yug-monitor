import csv
import os
import re
from collections import defaultdict
from datetime import datetime


# ============================================================
# B2B YUG LEAD AGENT
# VERSION 3 - CONTACT & SALES INTELLIGENCE
# ============================================================

INPUT_FILE = "data/latest/offers_ro_gr.csv"

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
# FIND CONTACT / WEBSITE FIELDS
# ============================================================

def find_field(row, possible_names):

    for name in possible_names:

        if name in row:

            value = clean(row.get(name))

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

    # Try to find email inside any field
    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

    for field_value in row.values():

        match = re.search(
            email_pattern,
            str(field_value)
        )

        if match:
            return match.group(0)

    return ""


def find_phone(row):

    value = find_field(
        row,
        [
            "phone",
            "telephone",
            "telephone_number",
            "phone_number",
            "mobile",
        ]
    )

    return value


def find_website(row):

    value = find_field(
        row,
        [
            "website",
            "company_website",
            "web",
            "website_url",
        ]
    )

    return value


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
# COMPANY GROUPING
# ============================================================

def group_companies(rows):

    companies = defaultdict(list)

    for row in rows:

        key = company_key(row)

        companies[key].append(row)

    return companies


# ============================================================
# PRODUCT TEXT
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
# DESCRIPTION TEXT
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
# COMPANY PROFILE URL
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

POSITIVE_KEYWORDS = {

    "packaging": 15,
    "packaging material": 15,
    "packaging materials": 15,
    "plastic": 8,
    "plastics": 8,
    "bags": 8,
    "bag": 8,
    "film": 8,
    "films": 8,
    "bottle": 8,
    "bottles": 8,
    "container": 8,
    "containers": 8,
    "box": 8,
    "boxes": 8,
    "carton": 8,
    "cartons": 8,
    "food packaging": 15,
    "industrial packaging": 15,
    "flexible packaging": 15,
    "labels": 8,
    "label": 8,
    "printing": 5,
    "paper": 5,
    "cardboard": 8,
    "corrugated": 8,
}


# ============================================================
# SCORE
# ============================================================

def calculate_score(rows):

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

    text = normalize(
        " ".join(text_parts)
    )

    matched_keywords = []

    for keyword, points in POSITIVE_KEYWORDS.items():

        if keyword in text:

            score += points

            matched_keywords.append(
                keyword
            )

    # Multiple products
    product_count = len(
        collect_products(rows)
    )

    if product_count >= 3:
        score += 10

    elif product_count == 2:
        score += 5

    # Europages membership indicators
    first = rows[0]

    if normalize(
        first.get("is_ep_member", "")
    ) in ["true", "1", "yes"]:

        score += 5

    if normalize(
        first.get("is_wlw_member", "")
    ) in ["true", "1", "yes"]:

        score += 3

    # Responder
    if normalize(
        first.get("is_quick_responder", "")
    ) in ["true", "1", "yes"]:

        score += 5

    if score > 100:
        score = 100

    return score, matched_keywords


# ============================================================
# PRIORITY
# ============================================================

def get_priority(score):

    if score >= 75:
        return "HIGH"

    if score >= 50:
        return "MEDIUM"

    return "LOW"


# ============================================================
# WHY LEAD
# ============================================================

def create_reason(
    rows,
    score,
    matched_keywords
):

    reasons = []

    product_count = len(
        collect_products(rows)
    )

    if product_count:

        reasons.append(
            f"{product_count} relevant product/offering"
            + ("s" if product_count != 1 else "")
        )

    if matched_keywords:

        keywords = ", ".join(
            matched_keywords[:5]
        )

        reasons.append(
            f"relevant keywords: {keywords}"
        )

    first = rows[0]

    if normalize(
        first.get("is_quick_responder", "")
    ) in ["true", "1", "yes"]:

        reasons.append(
            "company is marked as quick responder"
        )

    if normalize(
        first.get("is_ep_member", "")
    ) in ["true", "1", "yes"]:

        reasons.append(
            "Europages member"
        )

    if not reasons:

        reasons.append(
            "company matches the monitored packaging search"
        )

    return "; ".join(reasons)


# ============================================================
# SALES OPPORTUNITY
# ============================================================

def create_sales_opportunity(
    products,
    descriptions
):

    text = normalize(
        " ".join(products + descriptions)
    )

    if any(
        word in text
        for word in [
            "plastic",
            "polyethylene",
            "polypropylene",
            "film",
            "bag",
        ]
    ):

        return (
            "Potential opportunity related to "
            "plastic/flexible packaging."
        )

    if any(
        word in text
        for word in [
            "cardboard",
            "carton",
            "corrugated",
            "paper",
        ]
    ):

        return (
            "Potential opportunity related to "
            "paper/cardboard packaging."
        )

    if any(
        word in text
        for word in [
            "bottle",
            "container",
        ]
    ):

        return (
            "Potential opportunity related to "
            "containers/bottles."
        )

    return (
        "Potential B2B opportunity related to "
        "packaging products or services."
    )


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

    website = find_website(first)

    email = find_email(first)

    phone = find_phone(first)

    europages_url = find_europages_url(rows)

    company_url = create_company_url(
        first
    )

    reason = create_reason(
        rows,
        score,
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

        "score":
            score,

        "priority":
            priority,

        "lead_reason":
            reason,

        "sales_opportunity":
            opportunity,

        "website":
            website,

        "email":
            email,

        "phone":
            phone,

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

    fieldnames = []

    if rows:

        fieldnames = list(
            rows[0].keys()
        )

    else:

        fieldnames = [
            "country_code",
            "country",
            "company_name",
            "company_id",
            "company_uuid",
            "products_count",
            "products",
            "score",
            "priority",
            "lead_reason",
            "sales_opportunity",
            "website",
            "email",
            "phone",
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
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(rows)

    print()
    print("SAVED:", filename)
    print("ROWS:", len(rows))


# ============================================================
# DAILY REPORT
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

    lines.append(
        "## Lead Summary"
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
        f"- HIGH: {high}"
    )

    lines.append(
        f"- MEDIUM: {medium}"
    )

    lines.append(
        f"- LOW: {low}"
    )

    lines.append("")

    if leads:

        top = leads[0]

        lines.append(
            "## Top Lead"
        )

        lines.append("")

        lines.append(
            f"**{top['company_name']}**"
        )

        lines.append("")

        lines.append(
            f"- Country: {top['country']}"
        )

        lines.append(
            f"- Score: {top['score']}"
        )

        lines.append(
            f"- Priority: {top['priority']}"
        )

        lines.append(
            f"- Products: {top['products'] or 'N/A'}"
        )

        lines.append(
            f"- Why: {top['lead_reason']}"
        )

        lines.append(
            f"- Opportunity: {top['sales_opportunity']}"
        )

        if top["email"]:
            lines.append(
                f"- Email: {top['email']}"
            )

        if top["phone"]:
            lines.append(
                f"- Phone: {top['phone']}"
            )

        if top["website"]:
            lines.append(
                f"- Website: {top['website']}"
            )

        if top["europages_url"]:
            lines.append(
                f"- Europages: {top['europages_url']}"
            )

        lines.append("")

    lines.append(
        "## All Leads"
    )

    lines.append("")

    for index, lead in enumerate(
        leads,
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
            f"- Products: {lead['products'] or 'N/A'}"
        )

        lines.append(
            f"- Why: {lead['lead_reason']}"
        )

        lines.append(
            f"- Opportunity: {lead['sales_opportunity']}"
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
                f"- Company profile: {lead['company_url']}"
            )

        if lead["europages_url"]:
            lines.append(
                f"- Europages offer: {lead['europages_url']}"
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
        "VERSION 3 - CONTACT & SALES INTELLIGENCE"
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
    # SAVE
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
    # HISTORY
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
