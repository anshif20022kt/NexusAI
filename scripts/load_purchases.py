import csv
import os
import random
from datetime import datetime, timedelta

from odoo_client import Odoo

random.seed(21)
o = Odoo()
TODAY = datetime(2026, 11, 24)

if o.call("purchase.order", "search_count", [("state", "=", "purchase")]):
    raise SystemExit("Purchase orders already exist. Stopping to avoid duplicates.")

# supplier: (typical lead days, on-time probability, monthly price drift, product codes)
SUPPLIERS = {
    "Gulf Grains Import Export FZE": (14, 0.88, 0.003, ["FS001", "FS004", "FS005", "FS006", "FS011"]),
    "Eastern Spice & Oil Trading": (10, 0.92, 0.003, ["FS002", "FS007", "FS008"]),
    "National Sugar & Tea Traders": (7, 0.95, 0.002, ["FS003", "FS009", "FS010"]),
    "Al Safa Beverages Industries": (5, 0.90, 0.004, ["BV001", "BV002", "BV003", "BV004", "BV005"]),
    "Fresh Dairy Distribution Co": (3, 0.96, 0.002, ["BV006"]),
    "Pure Home Care Manufacturing": (12, 0.80, 0.004, ["CH001", "CH002", "CH003", "CH004"]),
    "Paper Plus Packaging LLC": (9, 0.70, 0.006, ["CH005", "CH006", "CH007", "PK001", "PK002", "PK003", "PK004"]),
    "Orient Personal Care FZCO": (15, 0.85, 0.003, ["PC001", "PC002", "PC003", "PC004"]),
}

partners = o.call("res.partner", "search_read", [("name", "in", list(SUPPLIERS))],
                  fields=["id", "name"])
if len(partners) != 8:
    raise SystemExit(f"Expected 8 suppliers, found {len(partners)}")
pid = {p["name"]: p["id"] for p in partners}

prods = o.call("product.product", "search_read", [("default_code", "!=", False)],
               fields=["id", "default_code", "standard_price"])
prod = {p["default_code"]: p for p in prods}

rows = []   # delivery log
all_ids = []
for k in range(36):                      # k = 0 is Dec 2023, k = 35 is Nov 2026
    t = 2023 * 12 + 11 + k
    y, m = t // 12, t % 12 + 1
    trend = 0.76 + 0.0105 * k
    max_day = 23 if (y, m) == (2026, 11) else 28
    month_ids = []

    for sup, (lead, p_on, drift, codes) in SUPPLIERS.items():
        for _ in range(1 + (random.random() < 0.25)):
            odt = datetime(y, m, random.randint(1, max_day), random.randint(8, 16),
                           random.randint(0, 59))
            promised = odt + timedelta(days=lead + random.randint(0, 2))
            chosen = random.sample(codes, min(len(codes), random.randint(2, 3)))
            lines, qty_total = [], 0
            for code in chosen:
                qty = max(10, round(random.randint(40, 160) * trend))
                price = round(prod[code]["standard_price"] * (1 + drift * k)
                              * random.uniform(0.98, 1.02), 2)
                qty_total += qty
                lines.append([0, 0, {
                    "product_id": prod[code]["id"],
                    "product_qty": qty,
                    "price_unit": price,
                    "date_planned": promised.strftime("%Y-%m-%d %H:%M:%S"),
                }])
            oid = o.call("purchase.order", "create", {
                "partner_id": pid[sup],
                "date_order": odt.strftime("%Y-%m-%d %H:%M:%S"),
                "order_line": lines,
            })
            month_ids.append(oid)

            # ---- simulated delivery outcome ----
            if promised > TODAY:
                actual, late, on_time, received, status = "", "", "", "", "open"
            else:
                if random.random() < p_on:
                    act = promised - timedelta(days=random.choice([0, 0, 0, 1]))
                else:
                    act = promised + timedelta(days=random.randint(1, 12 if p_on < 0.8 else 6))
                late = (act - promised).days
                on_time = 1 if late <= 0 else 0
                short = random.random() < (1 - p_on) * 0.8
                received = round(qty_total * (random.uniform(0.85, 0.98) if short else 1.0))
                actual, status = act.strftime("%Y-%m-%d"), "received"
            rows.append({
                "po_id": oid, "supplier": sup,
                "order_date": odt.strftime("%Y-%m-%d"),
                "promised_date": promised.strftime("%Y-%m-%d"),
                "actual_date": actual, "days_late": late, "on_time": on_time,
                "qty_ordered": qty_total, "qty_received": received, "status": status,
            })

    o.call("purchase.order", "write", month_ids, {"state": "purchase"})
    all_ids += month_ids
    print(f"  {y}-{m:02d}: {len(month_ids)} purchase orders created")

# attach the Odoo PO reference (e.g. P00123) to each delivery row
names = {r["id"]: r["name"] for r in o.call("purchase.order", "read", all_ids, fields=["name"])}
for r in rows:
    r["po_name"] = names[r["po_id"]]

out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(out_dir, exist_ok=True)
path = os.path.join(out_dir, "supplier_deliveries.csv")
cols = ["po_name", "po_id", "supplier", "order_date", "promised_date", "actual_date",
        "days_late", "on_time", "qty_ordered", "qty_received", "status"]
with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print("Done. Purchase orders:", len(all_ids), "| delivery log saved to data/supplier_deliveries.csv")
print("On-time delivery rate by supplier (received orders only):")
for sup in SUPPLIERS:
    done = [r for r in rows if r["supplier"] == sup and r["status"] == "received"]
    pct = 100 * sum(r["on_time"] for r in done) / len(done)
    print(f"  {sup}: {pct:.0f}%")
