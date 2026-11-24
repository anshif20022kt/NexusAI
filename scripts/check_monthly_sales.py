import os
import xmlrpc.client

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("ODOO_URL")
DB = os.getenv("ODOO_DB")
EMAIL = os.getenv("ODOO_EMAIL")
PASSWORD = os.getenv("ODOO_PASSWORD")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, EMAIL, PASSWORD, {})
if not uid:
    raise SystemExit("Login failed. Check the values in your .env file.")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
orders = models.execute_kw(
    DB, uid, PASSWORD, "sale.order", "search_read",
    [[("state", "=", "sale")]],
    {"fields": ["date_order", "amount_total", "partner_id"]},
)

df = pd.DataFrame(orders)
df["date_order"] = pd.to_datetime(df["date_order"])
monthly = (
    df.groupby(df["date_order"].dt.to_period("M"))["amount_total"]
    .agg(orders="count", revenue_aed="sum")
    .round(0)
)
print(monthly)
print("Total revenue (AED):", round(df["amount_total"].sum()))