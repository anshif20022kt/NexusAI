import random
from datetime import datetime, timedelta

from odoo_client import Odoo

random.seed(5)
o = Odoo()
TODAY = datetime(2026, 11, 24)

if o.call("crm.lead", "search_count",
          [("type", "=", "opportunity"), ("active", "in", [True, False])]):
    raise SystemExit("Opportunities already exist. Stopping to avoid duplicates.")

uae = o.find("res.country", [("code", "=", "AE")])

PROSPECTS = [
    ("Zenith Hospitality Group", "Dubai"), ("Sandstone Catering Co", "Abu Dhabi"),
    ("Palm Jumeirah Beach Club Supplies", "Dubai"), ("Desert Rose Bakery Chain", "Sharjah"),
    ("Capital Gate Staff Meals LLC", "Abu Dhabi"), ("Gulf Harvest Mini Markets", "Ajman"),
    ("Al Dhafra Labour Camp Catering", "Abu Dhabi"), ("Skyline Corporate Cafeterias", "Dubai"),
    ("Mangrove Resort Provisions", "Ras Al Khaimah"), ("Lulu Valley Grocers", "Al Ain"),
    ("Creek Side Cafes LLC", "Dubai"), ("Sharjah Campus Dining Services", "Sharjah"),
    ("East Coast Fresh Trading", "Fujairah"), ("Burj Plaza Residence Supplies", "Dubai"),
    ("Oasis Healthcare Catering", "Al Ain"),
]
prospect_ids = []
for name, city in PROSPECTS:
    prospect_ids.append(o.call("res.partner", "create", {
        "name": name, "is_company": True, "company_type": "company",
        "city": city, "country_id": uae,
    }))

# existing customers = partners that already have confirmed sales orders
customer_ids = list({r["partner_id"][0] for r in o.call(
    "sale.order", "search_read", [("state", "=", "sale")], fields=["partner_id"])})

stages = o.call("crm.stage", "search_read", [], fields=["name", "sequence", "is_won"],
                order="sequence")
open_stages = [s for s in stages if not s["is_won"]]
won_stage = next((s for s in stages if s["is_won"]), None)
if len(open_stages) < 3 or not won_stage:
    raise SystemExit(f"Unexpected CRM stages: {[s['name'] for s in stages]}")
open_stages = open_stages[:3]

TITLES = ["Annual supply contract", "Quarterly replenishment agreement",
          "Hotel and catering package", "New outlet launch supply",
          "Private-label beverages programme", "Bulk staples framework deal"]

# (outcome, stage index or None, how many)
PLAN = [("open", 0, 10), ("open", 1, 9), ("open", 2, 8), ("won", None, 10), ("lost", None, 8)]
OPEN_PROB = [10, 30, 60]

created = 0
weighted = 0.0
for outcome, idx, count in PLAN:
    for _ in range(count):
        pool = prospect_ids if outcome == "open" and random.random() < 0.7 else prospect_ids + customer_ids
        partner = random.choice(pool)
        pname = o.call("res.partner", "read", [partner], fields=["name"])[0]["name"]
        revenue = int(random.triangular(15000, 250000, 50000) / 500) * 500
        vals = {
            "name": f"{random.choice(TITLES)} - {pname}",
            "type": "opportunity",
            "partner_id": partner,
            "expected_revenue": revenue,
            "priority": random.choice(["0", "1", "2", "3"]),
        }
        if outcome == "open":
            vals["stage_id"] = open_stages[idx]["id"]
            vals["probability"] = OPEN_PROB[idx]
            vals["date_deadline"] = (TODAY + timedelta(days=random.randint(7, 120))).strftime("%Y-%m-%d")
            weighted += revenue * OPEN_PROB[idx] / 100
        elif outcome == "won":
            vals["stage_id"] = won_stage["id"]
            vals["probability"] = 100
            vals["date_deadline"] = (TODAY - timedelta(days=random.randint(5, 180))).strftime("%Y-%m-%d")
        else:
            vals["stage_id"] = open_stages[random.randint(0, 2)]["id"]
            vals["date_deadline"] = (TODAY - timedelta(days=random.randint(5, 180))).strftime("%Y-%m-%d")
        lead_id = o.call("crm.lead", "create", vals)
        if outcome == "lost":
            o.call("crm.lead", "write", [lead_id], {"active": False, "probability": 0})
        created += 1

print("Done. Prospects created:", len(prospect_ids), "| opportunities created:", created)
print("Weighted open pipeline (AED):", round(weighted))
