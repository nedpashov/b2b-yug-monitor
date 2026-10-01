import csv
import os
from datetime import datetime


# ============================================================
# B2B YUG - LEAD AGENT
# VERSION 2
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


def save_csv(rows, filename):

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    if not rows:
        print(f"SAVED EMPTY: {filename}")

        # Create an empty file with headers
        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                "score",
                "priority",
                "country",
                "company_name",
                "product_name",
                "category",
                "description",
                "offer_url",
                "company_id",
                "company_uuid",
                "company_slug",
                "reason",
            ])

        return

    fieldnames = list(rows[0].keys())

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

    print(f"SAVED: {filename}")
    print(f"ROWS: {len(rows)}")


# ============================================================
# LOAD OFFERS
# ============================================================

def load_offers():

    if not os.path.exists(INPUT_FILE):

        print()
        print("ERROR:")
        print(f"Input file not found: {INPUT_FILE}")

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
# SCORE OFFER
# ============================================================

def score_offer(row):

    score = 0
    reasons = []

    company = clean(
        row.get("company_name")
    )

    product = clean(
        row.get("product_name")
    )

    description = clean(
        row.get("description")
    )

    category = clean(
        row.get("category")
    )

    country = clean(
        row.get("country")
    )

    text = (
        f"{product} "
        f"{description} "
        f"{category} "
        f"{company}"
    ).lower()

    # --------------------------------------------------------
    # PACKAGING RELEVANCE
    # --------------------------------------------------------

    packaging_keywords = [
        "packaging",
        "package",
        "pack",
        "packaging material",
        "plastic packaging",
        "food packaging",
        "flexible packaging",
        "paper packaging",
        "cardboard",
        "carton",
        "box",
        "bottle",
        "container",
        "film",
        "bag",
        "pouch",
        "label",
        "wrapping",
    ]

    matched = []

    for keyword in packaging_keywords:

        if keyword in text:

            matched.append(keyword)

    if matched:

        score += min(40, 10 + len(matched) * 5)

        reasons.append(
            "Packaging relevance: "
            + ", ".join(matched[:5])
        )

    # --------------------------------------------------------
    # PRODUCT INFORMATION
    # --------------------------------------------------------

    if product:

        score += 10

        reasons.append(
            "Specific product information available"
        )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    if len(description) >= 50:

        score += 10

        reasons.append(
            "Detailed company/product description"
        )

    # --------------------------------------------------------
    # COMPANY
    # --------------------------------------------------------

    if company:

        score += 10

        reasons.append(
            "Identifiable company"
        )

    # --------------------------------------------------------
    # COMPANY IDENTIFIERS
    # --------------------------------------------------------

    if row.get("company_id"):

        score += 5

    if row.get("company_uuid"):

        score += 5

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if row.get("offer_url"):

        score += 5

        reasons.append(
            "Direct Europages offer URL available"
        )

    # --------------------------------------------------------
    # COUNTRY
    # --------------------------------------------------------

    if country in [
        "Румъния",
        "Гърция",
    ]:

        score += 5

    # --------------------------------------------------------
    # PRIORITY
    # --------------------------------------------------------

    if score >= 80:

        priority = "HIGH"

    elif score >= 60:

        priority = "MEDIUM"

    elif score >= MIN_SCORE:

        priority = "LOW"

    else:

        priority = "IGNORE"

    return score, priority, reasons


# ============================================================
# CREATE LEADS
# ============================================================

def create_leads(rows):

    leads = []

    seen = set()

    for row in rows:

        score, priority, reasons = score_offer(
            row
        )

        if score < MIN_SCORE:

            continue

        company_id = clean(
            row.get("company_id")
        )

        company_uuid = clean(
            row.get("company_uuid")
        )

        company_name = clean(
            row.get("company_name")
        )

        product_name = clean(
            row.get("product_name")
        )

        # ----------------------------------------------------
        # Avoid exact duplicate leads
        # ----------------------------------------------------

        key = (
            company_id,
            company_uuid,
            company_name,
            product_name,
        )

        if key in seen:

            continue

        seen.add(key)

        leads.append({

            "score":
                score,

            "priority":
                priority,

            "country":
                clean(row.get("country")),

            "company_name":
                company_name,

            "product_name":
                product_name,

            "category":
                clean(row.get("category")),

            "description":
                clean(row.get("description")),

            "offer_url":
                clean(row.get("offer_url")),

            "company_id":
                company_id,

            "company_uuid":
                company_uuid,

            "company_slug":
                clean(row.get("company_slug")),

            "reason":
                "; ".join(reasons),
        })

    # --------------------------------------------------------
    # Sort by score
    # --------------------------------------------------------

    leads.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return leads


# ============================================================
# CREATE DAILY REPORT
# ============================================================

def create_report(
    rows,
    leads,
    report_file
):

    os.makedirs(
        os.path.dirname(report_file),
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
        report_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("# B2B YUG DAILY LEAD REPORT\n\n")

        f.write(
            f"Date: {today}\n\n"
        )

        f.write("## SUMMARY\n\n")

        f.write(
            f"- Offers analysed: {len(rows)}\n"
        )

        f.write(
            f"- Leads: {len(leads)}\n"
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

        if leads:

            top = leads[0]

            f.write("## TOP LEAD\n\n")

            f.write(
                f"**{top['company_name']}**\n\n"
            )

            f.write(
                f"- Country: {top['country']}\n"
            )

            f.write(
                f"- Product: {top['product_name']}\n"
            )

            f.write(
                f"- Score: {top['score']}\n"
            )

            f.write(
                f"- Priority: {top['priority']}\n"
            )

            f.write(
                f"- Reason: {top['reason']}\n"
            )

            if top["offer_url"]:

                f.write(
                    f"- Offer: {top['offer_url']}\n"
                )

            f.write("\n")

        else:

            f.write(
                "## TOP LEAD\n\n"
            )

            f.write(
                "No qualifying leads found.\n\n"
            )

        # ----------------------------------------------------
        # ALL LEADS
        # ----------------------------------------------------

        f.write("## ALL LEADS\n\n")

        for index, lead in enumerate(
            leads,
            start=1
        ):

            f.write(
                f"### {index}. "
                f"{lead['company_name']}\n\n"
            )

            f.write(
                f"- Country: {lead['country']}\n"
            )

            f.write(
                f"- Product: {lead['product_name']}\n"
            )

            f.write(
                f"- Score: {lead['score']}\n"
            )

            f.write(
                f"- Priority: {lead['priority']}\n"
            )

            f.write(
                f"- Reason: {lead['reason']}\n"
            )

            if lead["offer_url"]:

                f.write(
                    f"- Offer URL: "
                    f"{lead['offer_url']}\n"
                )

            f.write("\n")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("B2B YUG LEAD AGENT")
    print("VERSION 2 - REAL OFFER ANALYSIS")
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

        print()
        print(
            "No offers available."
        )

        return

    # --------------------------------------------------------
    # CREATE LEADS
    # --------------------------------------------------------

    leads = create_leads(
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
    # SAVE LATEST
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
        leads,
        latest_report
    )

    print(
        "SAVED:",
        latest_report
    )

    # --------------------------------------------------------
    # SAVE HISTORY
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

    high_count = sum(
        1 for x in leads
        if x["priority"] == "HIGH"
    )

    medium_count = sum(
        1 for x in leads
        if x["priority"] == "MEDIUM"
    )

    low_count = sum(
        1 for x in leads
        if x["priority"] == "LOW"
    )

    print()
    print("=" * 70)
    print("B2B LEAD AGENT")
    print("=" * 70)

    print()
    print(
        "OFFERS ANALYSED:",
        len(rows)
    )

    print(
        "LEADS:",
        len(leads)
    )

    print(
        "HIGH:",
        high_count
    )

    print(
        "MEDIUM:",
        medium_count
    )

    print(
        "LOW:",
        low_count
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
    print("LEAD AGENT COMPLETE")
    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
