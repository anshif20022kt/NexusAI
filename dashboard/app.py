import streamlit as st

st.set_page_config(page_title="NexusAI UAE | Distribution Analytics", page_icon="📊", layout="wide")

pages = [
    st.Page("views/overview.py", title="Executive overview", icon="📈", default=True),
    st.Page("views/inventory.py", title="Inventory risk", icon="📦"),
]
st.navigation(pages).run()

st.divider()
st.caption(
    "Simulated dataset. Not real company data. "
    "Built with Odoo 19, Python and Streamlit. Source: github.com/anshif20022kt/NexusAI"
)