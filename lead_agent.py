import csv
import os
from datetime import datetime


# ============================================================
# B2B YUG - COMPANY BASED LEAD AGENT
# ============================================================

INPUT_FILE = "data/latest/offers_ro_gr.csv"

LATEST_DIR = "data/latest"
HISTORY_DIR = "data/history"

MIN_SCORE = 30


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if value is None:
        return ""

    return " ".join(str(value).split()).strip()


def unique_values(values):

    result = []

    seen = set()

    for value in values:

        value = clean(value)

        if not value:
            continue

        if value.lower() in seen:
            continue

        seen.add(value.lower())
        result.append(value)

    return result


def save_csv(rows, filename):

    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True
    )

    fieldnames = [
        "score",
        "priority",
        "country",
        "company_name",
        "products_count",
        "products",
        "categories",
        "description",
        "offer_url",
        "company_id",
        "company_uuid",
        "company_slug",
        "reason",
        "next_action",
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

        if rows:
            writer.writerows(rows)

    if rows:

        print(
            f"SAVED: {filename}"
        )

        print(
            f"ROWS: {len(rows)}"
        )

    else:

        print(
            f"SAVED EMPTY: {filename}"
        )

        print(
            "ROWS: 0"
        )


# ============================================================
# LOAD OFFERS
# ============================================================

def load_offers():

    if not os.path.exists(INPUT_FILE):

        print(
            "ERROR: Input file not found:"
        )

        print(INPUT_FILE)

        return []

    rows = []

    with open(
        INPUT_FILE,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            rows.append({
                key: clean(value)
                for key, value in row.items()
            })

    return rows


# ============================================================
# GROUP COMPANIES
# ============================================================

def company_key(row):

    company_id = clean(
        row.get("company_id")
    )

    company_uuid = clean(
        row.get("company_uuid")
    )

    company_name = clean(
        row.get("company_name")
    )

    country = clean(
        row.get("country")
    )

    if company_id:

        return (
            "ID",
            company_id
        )

    if company_uuid:

        return (
            "UUID",
            company_uuid
        )

    return (
        "NAME",
        country.lower(),
        company_name.lower()
    )


def group_companies(rows):

    companies = {}

    for row in rows:

        key = company_key(row)

        if key not in companies:

            companies[key] = {
                "country": row.get(
                    "country",
                    ""
                ),

                "company_name": row.get(
                    "company_name",
                    ""
                ),

                "company_id": row.get(
                    "company_id",
                    ""
                ),

                "company_uuid": row.get(
                    "company_uuid",
                    ""
                ),

                "company_slug": row.get(
                    "company_slug",
                    ""
                ),

                "offers": [],
            }

        companies[key]["offers"].append(
            row
        )

    return list(
        companies.values()
    )


# ============================================================
# SCORE COMPANY
# ============================================================

def score_company(company):

    offers = company["offers"]

    score = 0

    reasons = []

    all_products = []
    all_categories = []
    all_descriptions = []
    all_urls = []

    for offer in offers:

        all_products.append(
            offer.get(
                "product_name",
                ""
            )
        )

        all_categories.append(
            offer.get(
                "category",
                ""
            )
        )

        all_descriptions.append(
            offer.get(
                "description",
                ""
            )
        )

        all_urls.append(
            offer.get(
                "offer_url",
                ""
            )
        )

    products = unique_values(
        all_products
    )

    categories = unique_values(
        all_categories
    )

    descriptions = unique_values(
        all_descriptions
    )

    urls = unique_values(
        all_urls
    )

    combined_text = " ".join(
        products
        + categories
        + descriptions
    ).lower()

    # --------------------------------------------------------
    # PACKAGING KEYWORDS
    # --------------------------------------------------------

    strong_keywords = [
        "packaging",
        "packaging material",
        "food packaging",
        "plastic packaging",
        "flexible packaging",
        "paper packaging",
        "cardboard packaging",
        "carton packaging",
    ]

    medium_keywords = [
        "cardboard",
        "carton",
        "box",
        "container",
        "bottle",
        "film",
        "bag",
        "pouch",
        "label",
        "wrapping",
        "plastic",
        "paper",
    ]

    strong_matches = []

    for keyword in strong_keywords:

        if keyword in combined_text:

            strong_matches.append(
                keyword
            )

    medium_matches = []

    for keyword in medium_keywords:

        if keyword in combined_text:

            medium_matches.append(
                keyword
            )

    # --------------------------------------------------------
    # SCORE - RELEVANCE
    # --------------------------------------------------------

    if strong_matches:

        score += 35

        reasons.append(
            "Direct packaging relevance: "
            + ", ".join(
                strong_matches[:5]
            )
        )

    elif medium_matches:

        score += 20

        reasons.append(
            "Related packaging products: "
            + ", ".join(
                medium_matches[:6]
            )
        )

    # --------------------------------------------------------
    # MULTIPLE OFFERS
    # --------------------------------------------------------

    if len(offers) >= 3:

        score += 10

        reasons.append(
            "Company has multiple matching offers"
        )

    elif len(offers) >= 2:

        score += 5

        reasons.append(
            "Company has multiple matching offers"
        )

    # --------------------------------------------------------
    # PRODUCT INFORMATION
    # --------------------------------------------------------

    if products:

        score += 10

        reasons.append(
            "Specific products identified"
        )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    long_descriptions = [
        x for x in descriptions
        if len(x) >= 50
    ]

    if long_descriptions:

        score += 10

        reasons.append(
            "Detailed company/product information"
        )

    # --------------------------------------------------------
    # COMPANY
    # --------------------------------------------------------

    if company["company_name"]:

        score += 10

        reasons.append(
            "Identifiable company"
        )

    # --------------------------------------------------------
    # IDENTIFIERS
    # --------------------------------------------------------

    if company["company_id"]:

        score += 5

    elif company["company_uuid"]:

        score += 5

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if urls:

        score += 5

        reasons.append(
            "Direct Europages offer URL available"
        )

    # --------------------------------------------------------
    # CAP
    # --------------------------------------------------------

    score = min(
        score,
        100
    )

    # --------------------------------------------------------
    # PRIORITY
    # --------------------------------------------------------

    if score >= 80:

        priority = "HIGH"

    elif score >= 60:

        priority = "MEDIUM"

    else:

        priority = "LOW"

    # --------------------------------------------------------
    # NEXT ACTION
    # --------------------------------------------------------

    if priority == "HIGH":

        next_action = (
            "Research company contact details "
            "and prepare direct B2B outreach."
        )

    elif priority == "MEDIUM":

        next_action = (
            "Review company website/profile "
            "and verify whether its activity "
            "matches our target offer."
        )

    else:

        next_action = (
            "Keep under observation and collect "
            "more information before contacting."
        )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    description = ""

    if descriptions:

        description = descriptions[0]

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    offer_url = ""

    if urls:

        offer_url = urls[0]

    return {
        "score": score,

        "priority": priority,

        "country": clean(
            company["country"]
        ),

        "company_name": clean(
            company["company_name"]
        ),

        "products_count": len(
            offers
        ),

        "products": " | ".join(
            products
        ),

        "categories": " | ".join(
            categories
        ),

        "description": description,

        "offer_url": offer_url,

        "company_id": clean(
            company["company_id"]
        ),

        "company_uuid": clean(
            company["company_uuid"]
        ),

        "company_slug": clean(
            company["company_slug"]
        ),

        "reason": "; ".join(
            reasons
        ),

        "next_action": next_action,
    }


# ============================================================
# CREATE LEADS
# ============================================================

def create_leads(rows):

    companies = group_companies(
        rows
    )

    leads = []

    for company in companies:

        lead = score_company(
            company
        )

        if lead["score"] >= MIN_SCORE:

            leads.append(
                lead
            )

    leads.sort(
        key=lambda x: (
            x["score"],
            x["products_count"]
        ),
        reverse=True
    )

    return leads, companies


# ============================================================
# CREATE REPORT
# ============================================================

def create_report(
    rows,
    companies,
    leads,
    filename
):

    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True
    )

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    high = [
        x for x in leads
        if x["priority"] == "HIGH"
    ]

    medium = [
        x for x in leads
        if x["priority"] == "MEDIUM"
    ]

    low = [
        x for x in leads
        if x["priority"] == "LOW"
    ]

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "# B2B YUG DAILY LEAD REPORT\n\n"
        )

        f.write(
            f"Date: {today}\n\n"
        )

        f.write("## SUMMARY\n\n")

        f.write(
            f"- Offers analysed: {len(rows)}\n"
        )

        f.write(
            f"- Companies found: {len(companies)}\n"
        )

        f.write(
            f"- Qualified leads: {len(leads)}\n"
        )

        f.write(
            f"- HIGH priority: {len(high)}\n"
        )

        f.write(
            f"- MEDIUM priority: {len(medium)}\n"
        )

        f.write(
            f"- LOW priority: {len(low)}\n\n"
        )

        # ----------------------------------------------------
        # TOP LEADS
        # ----------------------------------------------------

        f.write(
            "## TOP LEADS\n\n"
        )

        if not leads:

            f.write(
                "No qualified leads found.\n\n"
            )

        else:

            for index, lead in enumerate(
                leads[:10],
                start=1
            ):

                f.write(
                    f"### {index}. "
                    f"{lead['company_name']}\n\n"
                )

                f.write(
                    f"- Country: "
                    f"{lead['country']}\n"
                )

                f.write(
                    f"- Score: "
                    f"{lead['score']}\n"
                )

                f.write(
                    f"- Priority: "
                    f"{lead['priority']}\n"
                )

                f.write(
                    f"- Offers: "
                    f"{lead['products_count']}\n"
                )

                f.write(
                    f"- Products: "
                    f"{lead['products']}\n"
                )

                f.write(
                    f"- Categories: "
                    f"{lead['categories']}\n"
                )

                f.write(
                    f"- Why this lead: "
                    f"{lead['reason']}\n"
                )

                f.write(
                    f"- Next action: "
                    f"{lead['next_action']}\n"
                )

                if lead["offer_url"]:

                    f.write(
                        f"- Europages: "
                        f"{lead['offer_url']}\n"
                    )

                f.write("\n")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "B2B YUG LEAD AGENT"
    )
    print(
        "COMPANY-BASED VERSION"
    )
    print("=" * 70)

    print()

    print(
        "INPUT:",
        INPUT_FILE
    )

    rows = load_offers()

    print()

    print(
        "OFFERS LOADED:",
        len(rows)
    )

    if not rows:

        print(
            "No offers available."
        )

        return

    # --------------------------------------------------------
    # CREATE LEADS
    # --------------------------------------------------------

    leads, companies = create_leads(
        rows
    )

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    history_dir = os.path.join(
        HISTORY_DIR,
        today
    )

    # --------------------------------------------------------
    # LATEST
    # --------------------------------------------------------

    latest_leads = os.path.join(
        LATEST_DIR,
        "leads.csv"
    )

    latest_report = os.path.join(
        LATEST_DIR,
        "daily_report.md"
    )

    save_csv(
        leads,
        latest_leads
    )

    create_report(
        rows,
        companies,
        leads,
        latest_report
    )

    print(
        "SAVED:",
        latest_report
    )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    history_leads = os.path.join(
        history_dir,
        "leads.csv"
    )

    history_report = os.path.join(
        history_dir,
        "daily_report.md"
    )

    save_csv(
        leads,
        history_leads
    )

    create_report(
        rows,
        companies,
        leads,
        history_report
    )

    print(
        "SAVED:",
        history_report
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    high = sum(
        1 for x in leads
        if x["priority"] == "HIGH"
    )

    medium = sum(
        1 for x in leads
        if x["priority"] == "MEDIUM"
    )

    low = sum(
        1 for x in leads
        if x["priority"] == "LOW"
    )

    print()
    print("=" * 70)
    print(
        "B2B LEAD AGENT"
    )
    print("=" * 70)

    print()

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
        latest_leads
    )

    print(
        "SAVED:",
        latest_report
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
