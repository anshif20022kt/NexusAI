import os
import xmlrpc.client
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "snapshot"
TABLES = ["products", "orders", "lines", "purchases", "leads"]
DATE_COLS = {"orders": ["date"], "lines": ["date"], "purchases": ["date"], "leads": ["deadline"]}


def _id(v):
    return v[0] if isinstance(v, (list, tuple)) else None


def _name(v):
    return v[1] if isinstance(v, (list, tuple)) else None


def from_odoo():
    url, db = os.getenv("ODOO_URL"), os.getenv("ODOO_DB")
    email, pw = os.getenv("ODOO_EMAIL"), os.getenv("ODOO_PASSWORD")
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, email, pw, {})
    if not uid:
        raise RuntimeError("Odoo login failed")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    def read(model, domain, fields, context=None):
        kwargs = {"fields": fields}
        if context:
            kwargs["context"] = context
        rows = models.execute_kw(db, uid, pw, model, "search_read", [domain], kwargs)
        return pd.DataFrame(rows)

    # products
    p = read("product.product", [("default_code", "!=", False)],
             ["default_code", "name", "categ_id", "qty_available", "standard_price"])
    p["category"] = p["categ_id"].map(_name)
    products = p.rename(columns={"id": "product_id", "default_code": "code", "name": "product",
                                 "qty_available": "stock", "standard_price": "cost"})[
        ["product_id", "code", "product", "category", "stock", "cost"]]

    # customers
    partners = read("res.partner", [("is_company", "=", True)], ["name", "city"])
    partners = partners.rename(columns={"id": "customer_id", "name": "customer"})

    # sales orders
    o = read("sale.order", [("state", "=", "sale")], ["date_order", "partner_id"])
    o["customer_id"] = o["partner_id"].map(_id)
    o["date"] = pd.to_datetime(o["date_order"])
    o["month"] = o["date"].dt.strftime("%Y-%m")
    orders = o.rename(columns={"id": "order_id"})[["order_id", "date", "month", "customer_id"]]
    orders = orders.merge(partners, on="customer_id", how="left")

    # sales order lines
    l = read("sale.order.line", [("state", "=", "sale")],
             ["order_id", "product_id", "product_uom_qty", "price_subtotal"])
    l["order_id"] = l["order_id"].map(_id)
    l["product_id"] = l["product_id"].map(_id)
    l = l.rename(columns={"product_uom_qty": "qty", "price_subtotal": "revenue"})[
        ["order_id", "product_id", "qty", "revenue"]]
    lines = l.merge(orders[["order_id", "date", "month", "customer", "city"]],
                    on="order_id", how="left")
    lines = lines.merge(products[["product_id", "code", "product", "category"]],
                        on="product_id", how="left")

    # purchase orders
    po = read("purchase.order", [("state", "=", "purchase")],
              ["name", "partner_id", "date_order", "amount_untaxed"])
    po["supplier"] = po["partner_id"].map(_name)
    po["date"] = pd.to_datetime(po["date_order"])
    po["month"] = po["date"].dt.strftime("%Y-%m")
    purchases = po.rename(columns={"id": "po_id", "name": "po_name", "amount_untaxed": "amount"})[
        ["po_id", "po_name", "supplier", "date", "month", "amount"]]

    # CRM opportunities (including lost ones, which are archived)
    ld = read("crm.lead", [("type", "=", "opportunity")],
              ["name", "partner_id", "stage_id", "expected_revenue", "probability",
               "active", "date_deadline"], context={"active_test": False})
    ld["customer"] = ld["partner_id"].map(_name)
    ld["stage"] = ld["stage_id"].map(_name)
    ld["deadline"] = pd.to_datetime(ld["date_deadline"], errors="coerce")
    ld["status"] = ld.apply(
        lambda r: "Lost" if not r["active"] else ("Won" if r["probability"] == 100 else "Open"),
        axis=1)
    leads = ld.rename(columns={"id": "lead_id", "name": "opportunity", "expected_revenue": "value"})[
        ["lead_id", "opportunity", "customer", "stage", "value", "probability", "status", "deadline"]]

    return {"products": products, "orders": orders, "lines": lines,
            "purchases": purchases, "leads": leads}


def save_snapshot(data):
    SNAP.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        data[name].to_csv(SNAP / f"{name}.csv", index=False)


def read_snapshot():
    out = {}
    for name in TABLES:
        out[name] = pd.read_csv(SNAP / f"{name}.csv", parse_dates=DATE_COLS.get(name, []))
    return out


def load_all():
    """Live Odoo data if reachable, otherwise the saved snapshot (demo mode)."""
    if os.getenv("DEMO_MODE") == "1" or not os.getenv("ODOO_URL"):
        return read_snapshot(), "snapshot (demo mode)"
    try:
        return from_odoo(), "live from Odoo"
    except Exception:
        if (SNAP / "orders.csv").exists():
            return read_snapshot(), "snapshot (Odoo not reachable)"
        raise