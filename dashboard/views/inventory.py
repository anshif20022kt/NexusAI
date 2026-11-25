import pandas as pd
import streamlit as st

from data import get_data

d, source = get_data()
lines, products = d["lines"], d["products"]

st.title("📦 Inventory risk")
st.caption("Stock cover = units on hand divided by average daily demand over the last 90 days.")

days = st.slider("Alert when stock covers fewer than this many days of sales", 5, 90, 21)

recent = lines[lines["date"] >= lines["date"].max() - pd.Timedelta(days=90)]
daily = (recent.groupby("product_id")["qty"].sum() / 90).rename("daily_demand").reset_index()
stock = products.merge(daily, on="product_id", how="left")
stock["cover_days"] = (stock["stock"] / stock["daily_demand"]).round(1)

risk = stock[stock["cover_days"] < days].sort_values("cover_days")
risk = risk[["code", "product", "category", "stock", "daily_demand", "cover_days"]].copy()
risk["daily_demand"] = risk["daily_demand"].round(1)

m1, m2 = st.columns(2)
m1.metric("Products tracked", len(stock))
m2.metric("Products below threshold", len(risk))

if risk.empty:
    st.success("No products below the threshold.")
else:
    st.warning(f"{len(risk)} products need attention")
    st.dataframe(risk, hide_index=True)
st.caption(f"Data: {source}")