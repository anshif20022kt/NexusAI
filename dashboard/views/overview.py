import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from data import get_data

d, source = get_data()
lines = d["lines"]

st.title("📈 Executive overview")
st.caption("Simulated UAE wholesale distributor on Odoo 19. All amounts in AED, excluding VAT.")

months = sorted(lines["month"].unique())
with st.sidebar:
    st.header("Filters")
    default_start = months[-12] if len(months) >= 12 else months[0]
    start, end = st.select_slider("Period", options=months, value=(default_start, months[-1]))
    all_cats = sorted(lines["category"].dropna().unique())
    all_cities = sorted(lines["city"].dropna().unique())
    cats = st.multiselect("Category", all_cats, default=all_cats)
    cities = st.multiselect("City", all_cities, default=all_cities)
    compare = st.radio("Compare with", ["None", "Previous period", "Same period last year"])
    st.caption(f"Data: {source}")

if not cats or not cities:
    st.warning("Select at least one category and one city.")
    st.stop()


def months_between(a, b):
    pa, pb = pd.Period(a), pd.Period(b)
    return (pb.year - pa.year) * 12 + (pb.month - pa.month) + 1


def span(df, a, b):
    return df[(df["month"] >= a) & (df["month"] <= b)]


n = months_between(start, end)
ps, pe = pd.Period(start), pd.Period(end)
if compare == "Previous period":
    cs, ce = ps - n, ps - 1
elif compare == "Same period last year":
    cs, ce = ps - 12, pe - 12
else:
    cs = ce = None

seg = lines[lines["category"].isin(cats) & lines["city"].isin(cities)]
cur = span(seg, start, end)
comp = span(seg, str(cs), str(ce)) if cs is not None else None
if comp is not None and comp.empty:
    st.info("No data exists for the comparison period, so no comparison is shown.")
    comp = None


def kpis(df):
    revenue = df["revenue"].sum()
    orders = df["order_id"].nunique()
    return {"Revenue": revenue, "Orders": orders,
            "Average order": revenue / orders if orders else 0,
            "Units sold": df["qty"].sum()}


k_cur = kpis(cur)
k_comp = kpis(comp) if comp is not None else None


def delta(name):
    if not k_comp or not k_comp[name]:
        return None
    return f"{(k_cur[name] / k_comp[name] - 1) * 100:+.1f}% vs comparison"


c = st.columns(5)
c[0].metric("Revenue", f"{k_cur['Revenue']:,.0f} AED", delta("Revenue"))
c[1].metric("Output VAT (5%)", f"{k_cur['Revenue'] * 0.05:,.0f} AED", delta("Revenue"))
c[2].metric("Orders", f"{k_cur['Orders']:,}", delta("Orders"))
c[3].metric("Average order", f"{k_cur['Average order']:,.0f} AED", delta("Average order"))
c[4].metric("Units sold", f"{k_cur['Units sold']:,.0f}", delta("Units sold"))

# ---------- monthly revenue with optional comparison overlay ----------
labels = [str(p) for p in pd.period_range(start, end, freq="M")]
cur_m = cur.groupby("month")["revenue"].sum().reindex(labels, fill_value=0)
fig = go.Figure()
fig.add_bar(x=labels, y=cur_m.values, name="Selected period")
if comp is not None:
    comp_labels = [str(p) for p in pd.period_range(str(cs), str(ce), freq="M")]
    comp_m = comp.groupby("month")["revenue"].sum().reindex(comp_labels)
    fig.add_scatter(x=labels, y=comp_m.values, name=f"Comparison ({comp_labels[0]} to {comp_labels[-1]})",
                    mode="lines+markers")
fig.update_layout(title="Monthly revenue (AED)", yaxis_title="AED", legend=dict(orientation="h"))
st.plotly_chart(fig)

# ---------- breakdowns ----------
b1, b2 = st.columns(2)
cat = cur.groupby("category", as_index=False)["revenue"].sum().sort_values("revenue")
b1.plotly_chart(px.bar(cat, x="revenue", y="category", orientation="h",
                       labels={"revenue": "Revenue (AED)", "category": ""},
                       title="Revenue by category"))
city = cur.groupby("city", as_index=False)["revenue"].sum().sort_values("revenue")
b2.plotly_chart(px.bar(city, x="revenue", y="city", orientation="h",
                       labels={"revenue": "Revenue (AED)", "city": ""},
                       title="Revenue by city"))

top = cur.groupby("product", as_index=False)["revenue"].sum().sort_values("revenue").tail(10)
st.plotly_chart(px.bar(top, x="revenue", y="product", orientation="h",
                       labels={"revenue": "Revenue (AED)", "product": ""},
                       title="Top 10 products"))

# ---------- head-to-head ----------
st.subheader("Head-to-head comparison")
st.caption("Uses the selected period only. Category and city filters are ignored here.")
base = span(lines, start, end)
dim = st.radio("Compare by", ["City", "Category", "Customer"], horizontal=True)
col = {"City": "city", "Category": "category", "Customer": "customer"}[dim]
options = sorted(base[col].dropna().unique())
if len(options) < 2:
    st.info("Not enough values to compare.")
else:
    ca, cb = st.columns(2)
    a = ca.selectbox(f"{dim} A", options, index=0)
    b = cb.selectbox(f"{dim} B", options, index=1)
    pair = base[base[col].isin([a, b])]
    monthly = pair.groupby(["month", col], as_index=False)["revenue"].sum()
    st.plotly_chart(px.line(monthly, x="month", y="revenue", color=col, markers=True,
                            labels={"revenue": "Revenue (AED)", "month": "Month"},
                            title=f"{a} vs {b}"))
    summary = (pair.groupby(col)
               .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"), units=("qty", "sum"))
               .round(0))
    st.dataframe(summary)