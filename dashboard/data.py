import streamlit as st

from core import load_all


@st.cache_data(ttl=300, show_spinner="Loading data...")
def get_data():
    return load_all()