import random
from datetime import datetime
from odoo_client import Odoo

random.seed(7)
o = Odoo()

if o.call("sale.order", "search_count", [("state", "=", "sale")]):
    raise SystemExit("Sales history already exists. Stopping to avoid duplicates.")

CUSTOMERS = [
    "Al Noor Fresh Supermarket LLC", "Gulf Basket Trading LLC", "Marina Mart Grocery",
    "Desert Palm Hypermarket", "Corniche Daily Needs LLC", "Sahara Cash & Carry",
    "Falcon Catering Services", "Pearl Hotel Supplies LLC", "Oasis Canteen Solutions",
    "Emirates Family Mart", "Blue Dune Restaurants Group", "Al Wasl Minimarket",
    "Khalifa Staff Catering LLC", "Mirage Cafe Chain", "Coral Bay Resort Supplies",
    "Nakheel Fresh Foods Trading", "Horizon School Canteens", "Silver Sands Cafeteria",
    "Qasr Al Bahr Grocery", "Metro Value Stores LLC",
]
partner_ids = o.call("res.partner", "search", [("name", "in", CUSTOMERS)])
print("Customers found:", len(partner_ids), "(expected 20)")

codes = (
    [f"FS{i:03d}" for i in range(1, 12)] + [f"BV{i:03d}" for i in range(1, 7)]
    + [f"CH{i:03d}" for i in range(1, 8)] + [f"PC{i:03d}" for i in range(1, 5)]
    + [f"PK{i:03d}" for i in range(1, 5)]
)
prods = o.call("product.product", "search_read", [("default_code", "in", codes)],
               fields=["id", "default_code", "categ_id", "qty_available"])
print("Products found:", len(prods), "(expected 32)")
if len(partner_ids) != 20 or len(prods) != 32:
    raise SystemExit("Counts do not match. Run load_master_data.py first.")

# ---------- 1. Opening stock ----------
wh = o.call("stock.warehouse", "search_read", [], fields=["lot_stock_id"], limit=1)
loc = wh[0]["lot_stock_id"][0]
low_ids = set(random.sample([p["id"] for p in prods], 6))
quant_ids = []
for p in prods:
    if p["qty_available"] > 0:
        continue
    qty = random.randint(5, 25) if p["id"] in low_ids else random.randint(80, 800)
    qid = o.call("stock.quant", "create",
                 {"product_id": p["id"], "location_id": loc, "inventory_quantity": qty},
                 context={"inventory_mode": True})
    quant_ids.append(qid)
if quant_ids:
    o.call("stock.quant", "action_apply_inventory", quant_ids,
           context={"inventory_mode": True})
print("Opening stock loaded for", len(quant_ids), "products")

# ---------- 2. Sales history ----------
BASE = {"Food Staples": 20, "Beverages": 15, "Cleaning and Household": 12,
        "Personal Care": 10, "Packaging and Disposables": 10}
SEASON = {
    "Beverages": {5: 1.2, 6: 1.5, 7: 1.6, 8: 1.6, 9: 1.4, 10: 1.2, 12: 0.9, 1: 0.9},
    "Food Staples": {2: 1.4, 3: 1.3, 12: 1.1},
    "Cleaning and Household": {2: 1.2, 3: 1.1},
    "Personal Care": {12: 1.1},
    "Packaging and Disposables": {12: 1.2, 1: 1.2, 7: 0.85, 8: 0.85},
}

months = [(2025, 12)] + [(2026, m) for m in range(1, 12)]
order_ids = []
for idx, (y, m) in enumerate(months):
    last = (y, m) == (2026, 11)
    max_day = 23 if last else 28
    n_orders = 25 * max_day // 28
    trend = 1 + 0.01 * idx
    for _ in range(n_orders):
        dt = datetime(y, m, random.randint(1, max_day), random.randint(7, 17),
                      random.randint(0, 59)).strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        for p in random.sample(prods, random.randint(3, 7)):
            cat = p["categ_id"][1]
            f = SEASON.get(cat, {}).get(m, 1.0)
            if p["default_code"] == "FS008" and m in (2, 3):
                f *= 2.0
            qty = max(1, round(BASE[cat] * f * trend * random.uniform(0.6, 1.4)))
            lines.append([0, 0, {"product_id": p["id"], "product_uom_qty": qty}])
        oid = o.call("sale.order", "create", {
            "partner_id": random.choice(partner_ids),
            "date_order": dt,
            "order_line": lines,
        })
        order_ids.append(oid)
    print(f"  {y}-{m:02d}: {n_orders} orders created")

o.call("sale.order", "write", order_ids, {"state": "sale"})
print("Done. Confirmed sales orders:", len(order_ids))
