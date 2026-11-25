import streamlit as st

st.set_page_config(page_title="NexusAI | UAE Distribution", page_icon="📊", layout="wide")

pages = [
    st.Page("views/overview.py", title="Executive overview", icon="📈", default=True),
    st.Page("views/inventory.py", title="Inventory risk", icon="📦"),
]
st.navigation(pages).run()