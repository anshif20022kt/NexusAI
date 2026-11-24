import os
import xmlrpc.client

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("ODOO_URL")
DB = os.getenv("ODOO_DB")
EMAIL = os.getenv("ODOO_EMAIL")
PASSWORD = os.getenv("ODOO_PASSWORD")

st.set_page_config(page_title="NexusAI | UAE Distribution", page_icon="📊", layout="wide")


@st.cache_data(ttl=300)
def load_data():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, EMAIL, PASSWORD, {})
    if not uid:
        raise RuntimeError("Odoo login failed. Check your .env file.")
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    def read(model, domain, fields):
        return pd.DataFrame(
            models.execute_kw(DB, uid, PASSWORD, model, "search_read",
                              [domain], {"fields": fields})
        )

    orders = read("sale.order", [("state", "=", "sale")],
                  ["date_order", "partner_id", "amount_untaxed", "amount_tax", "amount_total"])
    lines = read("sale.order.line", [("state", "=", "sale")],
                 ["order_id", "product_id", "product_uom_qty", "price_subtotal"])
    products = read("product.product", [("default_code", "!=", False)],
                    ["default_code", "name", "categ_id", "qty_available"])
    partners = read("res.partner", [("is_company", "=", True)], ["name", "city"])

    # Odoo returns links as [id, name]; keep what we need
    orders["date"] = pd.to_datetime(orders["date_order"])
    orders["month"] = orders["date"].dt.to_period("M").astype(str)
    orders["partner_id"] = orders["partner_id"].apply(lambda v: v[0])
    partners = partners.rename(columns={"id": "partner_id", "name": "customer"})
    orders = orders.merge(partners, on="partner_id", how="left")

    lines["order_id"] = lines["order_id"].apply(lambda v: v[0])
    lines["product_id"] = lines["product_id"].apply(lambda v: v[0])
    products["category"] = products["categ_id"].apply(lambda v: v[1])
    products = products.rename(columns={"id": "product_id", "name": "product"})

    order_info = orders.rename(columns={"id": "order_id"})[["order_id", "date", "month", "city"]]
    lines = lines.merge(order_info, on="order_id", how="left")
    lines = lines.merge(products[["product_id", "product", "category"]], on="product_id", how="left")
    return orders, lines, products


try:
    orders, lines, products = load_data()
except Exception as e:
    st.error(f"Could not load data from Odoo: {e}")
    st.stop()

st.title("📊 NexusAI: UAE Distribution Dashboard")
st.caption("Live data from Odoo 19. Simulated UAE wholesale distributor dataset. All amounts in AED, excluding VAT unless stated.")

# ---------- KPI row ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Revenue (ex-VAT)", f"{orders['amount_untaxed'].sum():,.0f} AED")
k2.metric("VAT collected (5%)", f"{orders['amount_tax'].sum():,.0f} AED")
k3.metric("Orders", f"{len(orders):,}")
k4.metric("Average order value", f"{orders['amount_untaxed'].mean():,.0f} AED")

# ---------- Monthly revenue ----------
monthly = orders.groupby("month", as_index=False)["amount_untaxed"].sum()
fig = px.bar(monthly, x="month", y="amount_untaxed",
             labels={"month": "Month", "amount_untaxed": "Revenue (AED)"},
             title="Monthly revenue")
st.plotly_chart(fig)

# ---------- Category, city ----------
c1, c2 = st.columns(2)
cat = lines.groupby("category", as_index=False)["price_subtotal"].sum()
c1.plotly_chart(px.pie(cat, names="category", values="price_subtotal",
                       title="Revenue by category"))
city = orders.groupby("city", as_index=False)["amount_untaxed"].sum().sort_values("amount_untaxed")
c2.plotly_chart(px.bar(city, x="amount_untaxed", y="city", orientation="h",
                       labels={"amount_untaxed": "Revenue (AED)", "city": "City"},
                       title="Revenue by city"))

# ---------- Top products ----------
top = (lines.groupby("product", as_index=False)["price_subtotal"].sum()
       .sort_values("price_subtotal").tail(10))
st.plotly_chart(px.bar(top, x="price_subtotal", y="product", orientation="h",
                       labels={"price_subtotal": "Revenue (AED)", "product": "Product"},
                       title="Top 10 products by revenue"))

# ---------- Stock risk ----------
st.subheader("⚠️ Stock risk")
days = st.slider("Alert when stock covers fewer than this many days of sales", 5, 90, 21)

recent = lines[lines["date"] >= lines["date"].max() - pd.Timedelta(days=90)]
daily = (recent.groupby("product_id")["product_uom_qty"].sum() / 90).reset_index(name="daily_demand")
stock = products.merge(daily, on="product_id", how="left")
stock["cover_days"] = (stock["qty_available"] / stock["daily_demand"]).round(1)
risk = stock[stock["cover_days"] < days].sort_values("cover_days")
risk = risk[["default_code", "product", "category", "qty_available", "daily_demand", "cover_days"]]
risk["daily_demand"] = risk["daily_demand"].round(1)

if risk.empty:
    st.success("No products below the threshold.")
else:
    st.warning(f"{len(risk)} products need attention")
    st.dataframe(risk, hide_index=True)