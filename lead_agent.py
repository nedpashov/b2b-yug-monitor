import csv
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

TARGET_COUNTRIES = {"RO": "Румъния", "GR": "Гърция"}
LATEST_DIR = "data/latest"
HISTORY_DIR = "data/history"


def get_today():
    return datetime.now(ZoneInfo("Europe/Sofia")).strftime("%Y-%m-%d")


def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path, default=None):
    if not os.path.exists(path):
        return {} if default is None else default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def save_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print("SAVED:", path)
    print("ROWS:", len(rows))


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def truthy(value):
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def company_key(row):
    if row.get("company_id"):
        return f"id:{row.get('country_code','')}:{row['company_id']}"
    if row.get("company_uuid"):
        return f"uuid:{row.get('country_code','')}:{row['company_uuid']}"
    if row.get("company_slug"):
        return f"slug:{row.get('country_code','')}:{row['company_slug']}"
    return f"name:{row.get('country_code','')}:{row.get('company_name','').strip().lower()}"


def offer_key(row):
    if row.get("offer_uuid"):
        return "uuid:" + row["offer_uuid"]
    if row.get("slug_id"):
        return "slugid:" + row["slug_id"]
    if row.get("auction_id") and row.get("offer_slug"):
        return "auction_slug:" + row["auction_id"] + ":" + row["offer_slug"]
    return "slug:" + row.get("offer_slug", "")


def score_lead(row, event_type, new_company=False):
    score = 0
    reasons = []

    if event_type == "NEW OFFER":
        score += 50
        reasons.append("нова оферта")
    elif event_type == "RETURNED OFFER":
        score += 35
        reasons.append("върнала се оферта")
    elif event_type == "CHANGED OFFER":
        score += 20
        reasons.append("променена оферта")

    if new_company:
        score += 25
        reasons.append("нова компания")
    if truthy(row.get("email_existing")):
        score += 10
        reasons.append("има наличен email")
    if truthy(row.get("is_ep_member")):
        score += 5
        reasons.append("Europages member")
    if truthy(row.get("is_quick_responder")):
        score += 5
        reasons.append("Quick Responder")
    if row.get("founding_year"):
        score += 2
    if len(row.get("description", "")) >= 100:
        score += 3

    return min(score, 100), ", ".join(reasons)


def make_leads(today, result_files):
    new_offers = result_files["new_offers"]
    returned_offers = result_files["returned_offers"]
    changed_offers = result_files["changed_offers"]
    new_companies = result_files["new_companies"]

    new_company_keys = {company_key(r) for r in new_companies}
    leads = []
    seen = set()

    groups = [
        ("NEW OFFER", new_offers),
        ("RETURNED OFFER", returned_offers),
        ("CHANGED OFFER", changed_offers),
    ]

    for event_type, rows in groups:
        for row in rows:
            key = offer_key(row)
            if key in seen:
                continue
            seen.add(key)

            is_new_company = company_key(row) in new_company_keys
            score, reasons = score_lead(row, event_type, is_new_company)

            leads.append({
                "date": today,
                "lead_score": score,
                "event_type": event_type,
                "country_code": row.get("country_code", ""),
                "country": row.get(
                    "country",
                    TARGET_COUNTRIES.get(row.get("country_code", ""), "")
                ),
                "company_name": row.get("company_name", ""),
                "company_id": row.get("company_id", ""),
                "company_slug": row.get("company_slug", ""),
                "company_ep_slug": row.get("company_ep_slug", ""),
                "product_name": row.get("product_name", ""),
                "category": row.get("category", ""),
                "description": row.get("description", ""),
                "email_existing": row.get("email_existing", ""),
                "is_ep_member": row.get("is_ep_member", ""),
                "is_quick_responder": row.get("is_quick_responder", ""),
                "founding_year": row.get("founding_year", ""),
                "offer_url": row.get("offer_url", ""),
                "lead_reasons": reasons,
                "recommended_action": (
                    "Провери офертата и компанията; "
                    "ако е релевантна, свържи се с фирмата."
                ),
            })

    leads.sort(
        key=lambda x: (
            -int(x["lead_score"]),
            x["country_code"],
            x["company_name"],
            x["product_name"],
        )
    )
    return leads


def make_report(today, summary, leads, current_offers, current_companies):
    ro_offers = sum(1 for r in current_offers if r.get("country_code") == "RO")
    gr_offers = sum(1 for r in current_offers if r.get("country_code") == "GR")

    ro_companies = {
        company_key(r)
        for r in current_companies
        if r.get("country_code") == "RO"
    }
    gr_companies = {
        company_key(r)
        for r in current_companies
        if r.get("country_code") == "GR"
    }

    lines = [
        f"# B2B YUG Daily Lead Report — {today}",
        "",
        "## Daily summary",
        "",
        f"- Search: **{summary.get('search', '')}**",
        f"- Romania: **{ro_offers} offers / {len(ro_companies)} companies**",
        f"- Greece: **{gr_offers} offers / {len(gr_companies)} companies**",
        f"- Total RO + GR: **{len(current_offers)} offers / {len(current_companies)} companies**",
        f"- 🆕 New offers: **{summary.get('new_offers', 0)}**",
        f"- 🏢 New companies: **{summary.get('new_companies', 0)}**",
        f"- 🔄 Changed offers: **{summary.get('changed_offers', 0)}**",
        f"- ↩ Returned offers: **{summary.get('returned_offers', 0)}**",
        f"- ❌ Removed offers: **{summary.get('removed_offers', 0)}**",
        "",
        "## Leads to review",
        "",
    ]

    if not leads:
        lines.append("No actionable new, returned or changed offers today.")
    else:
        for i, lead in enumerate(leads[:20], 1):
            lines.extend([
                f"### {i}. {lead['company_name']} — {lead['product_name']}",
                f"- **Score:** {lead['lead_score']}/100",
                f"- **Event:** {lead['event_type']}",
                f"- **Country:** {lead['country']}",
                f"- **Reasons:** {lead['lead_reasons']}",
                f"- **Email existing:** {lead['email_existing'] or 'unknown'}",
                f"- **EP member:** {lead['is_ep_member'] or 'unknown'}",
                f"- **Quick responder:** {lead['is_quick_responder'] or 'unknown'}",
                f"- **Offer:** {lead['offer_url'] or 'no URL'}",
                "",
            ])

    lines.extend([
        "## Scoring",
        "",
        "The score is a transparent rule-based signal, not a guarantee of commercial value:",
        "- New offer: +50",
        "- Returned offer: +35",
        "- Changed offer: +20",
        "- New company: +25",
        "- Existing email signal: +10",
        "- Europages member: +5",
        "- Quick Responder: +5",
        "- Founding year present: +2",
        "- Detailed description (100+ characters): +3",
    ])

    return "\n".join(lines) + "\n"


def main():
    today = get_today()
    history_dir = os.path.join(HISTORY_DIR, today)
    os.makedirs(history_dir, exist_ok=True)

    summary = load_json(
        os.path.join(history_dir, "summary.json"),
        {}
    )

    current_offers = load_csv(
        os.path.join(LATEST_DIR, "offers_ro_gr.csv")
    )
    current_companies = load_csv(
        os.path.join(LATEST_DIR, "companies_ro_gr.csv")
    )

    result_files = {}
    for name in [
        "new_offers",
        "returned_offers",
        "changed_offers",
        "new_companies",
    ]:
        result_files[name] = load_csv(
            os.path.join(history_dir, f"{name}.csv")
        )

    leads = make_leads(today, result_files)

    lead_fields = [
        "date",
        "lead_score",
        "event_type",
        "country_code",
        "country",
        "company_name",
        "company_id",
        "company_slug",
        "company_ep_slug",
        "product_name",
        "category",
        "description",
        "email_existing",
        "is_ep_member",
        "is_quick_responder",
        "founding_year",
        "offer_url",
        "lead_reasons",
        "recommended_action",
    ]

    save_csv(
        leads,
        os.path.join(LATEST_DIR, "leads.csv"),
        lead_fields,
    )
    save_csv(
        leads,
        os.path.join(history_dir, "leads.csv"),
        lead_fields,
    )

    save_json(
        leads,
        os.path.join(LATEST_DIR, "leads.json"),
    )
    save_json(
        leads,
        os.path.join(history_dir, "leads.json"),
    )

    report = make_report(
        today,
        summary,
        leads,
        current_offers,
        current_companies,
    )

    for path in [
        os.path.join(LATEST_DIR, "daily_report.md"),
        os.path.join(history_dir, "daily_report.md"),
    ]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        print("SAVED:", path)

    print()
    print("=" * 70)
    print("B2B LEAD AGENT")
    print("=" * 70)
    print("LEADS:", len(leads))
    print(
        "TOP LEAD:",
        leads[0]["company_name"] if leads else "none"
    )
    print(
        "TOP SCORE:",
        leads[0]["lead_score"] if leads else 0
    )
    print(
        "SAVED:",
        os.path.join(LATEST_DIR, "leads.csv")
    )
    print(
        "SAVED:",
        os.path.join(LATEST_DIR, "daily_report.md")
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
