import random
from datetime import datetime

from odoo_client import Odoo

random.seed(11)
o = Odoo()

# ---- Safety check: stop if older history already exists ----
already = o.call("sale.order", "search_count",
                 [("state", "=", "sale"), ("date_order", "<", "2025-12-01 00:00:00")])
if already:
    raise SystemExit(f"{already} older orders already exist. Stopping to avoid duplicates.")

CUSTOMERS = [
    "Al Noor Fresh Supermarket LLC", "Gulf Basket Trading LLC", "Marina Mart Grocery",
    "Desert Palm Hypermarket", "Corniche Daily Needs LLC", "Sahara Cash & Carry",
    "Falcon Catering Services", "Pearl Hotel Supplies LLC", "Oasis Canteen Solutions",
    "Emirates Family Mart", "Blue Dune Restaurants Group", "Al Wasl Minimarket",
    "Khalifa Staff Catering LLC", "Mirage Cafe Chain", "Coral Bay Resort Supplies",
    "Nakheel Fresh Foods Trading", "Horizon School Canteens", "Silver Sands Cafeteria",
    "Qasr Al Bahr Grocery", "Metro Value Stores LLC",
]
# Month index at which a customer starts ordering (0 = Dec 2023). Others start at 0.
JOIN_MONTH = {
    "Nakheel Fresh Foods Trading": 3, "Coral Bay Resort Supplies": 6,
    "Horizon School Canteens": 9, "Silver Sands Cafeteria": 12,
    "Qasr Al Bahr Grocery": 15, "Metro Value Stores LLC": 18,
}

partners = o.call("res.partner", "search_read", [("name", "in", CUSTOMERS)],
                  fields=["id", "name"])
if len(partners) != 20:
    raise SystemExit(f"Expected 20 customers, found {len(partners)}")
pid_by_name = {p["name"]: p["id"] for p in partners}

codes = (
    [f"FS{i:03d}" for i in range(1, 12)] + [f"BV{i:03d}" for i in range(1, 7)]
    + [f"CH{i:03d}" for i in range(1, 8)] + [f"PC{i:03d}" for i in range(1, 5)]
    + [f"PK{i:03d}" for i in range(1, 5)]
)
prods = o.call("product.product", "search_read", [("default_code", "in", codes)],
               fields=["id", "default_code", "categ_id"])
if len(prods) != 32:
    raise SystemExit(f"Expected 32 products, found {len(prods)}")

BASE = {"Food Staples": 20, "Beverages": 15, "Cleaning and Household": 12,
        "Personal Care": 10, "Packaging and Disposables": 10}
SEASON = {
    "Beverages": {5: 1.2, 6: 1.5, 7: 1.6, 8: 1.6, 9: 1.4, 10: 1.2, 12: 0.9, 1: 0.9},
    "Food Staples": {12: 1.1},
    "Cleaning and Household": {},
    "Personal Care": {12: 1.1},
    "Packaging and Disposables": {12: 1.2, 1: 1.2, 7: 0.85, 8: 0.85},
}
# Ramadan moves about 11 days earlier every year
RAMADAN = {(2024, 3): 1.3, (2024, 4): 1.25, (2025, 2): 1.15, (2025, 3): 1.4}

total = 0
for k in range(24):                      # k = 0 is Dec 2023, k = 23 is Nov 2025
    t = 2023 * 12 + 11 + k
    y, m = t // 12, t % 12 + 1
    trend = 1 + 0.01 * (k - 24)          # 0.76 up to 0.99, joins the existing data
    n_orders = round(25 * (0.8 + 0.2 * (k + 1) / 24))
    active = [pid_by_name[n] for n in CUSTOMERS if JOIN_MONTH.get(n, 0) <= k]
    ramadan = RAMADAN.get((y, m), 1.0)

    ids = []
    for _ in range(n_orders):
        dt = datetime(y, m, random.randint(1, 28), random.randint(7, 17),
                      random.randint(0, 59)).strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        for p in random.sample(prods, random.randint(3, 7)):
            cat = p["categ_id"][1]
            f = SEASON.get(cat, {}).get(m, 1.0)
            if cat == "Food Staples":
                f *= ramadan
                if p["default_code"] == "FS008" and ramadan > 1.0:
                    f *= 2.0             # dates sell strongly in Ramadan
            elif cat == "Cleaning and Household":
                f *= 1 + (ramadan - 1) / 2
            qty = max(1, round(BASE[cat] * f * trend * random.uniform(0.6, 1.4)))
            lines.append([0, 0, {"product_id": p["id"], "product_uom_qty": qty}])
        oid = o.call("sale.order", "create", {
            "partner_id": random.choice(active),
            "date_order": dt,
            "order_line": lines,
        })
        ids.append(oid)

    o.call("sale.order", "write", ids, {"state": "sale"})
    total += len(ids)
    print(f"  {y}-{m:02d}: {len(ids)} orders created")

print("Done. New orders added:", total)
print("Confirmed orders in Odoo now:",
      o.call("sale.order", "search_count", [("state", "=", "sale")]))