import streamlit as st


def apply_styles():
    """Light global styling for the app. Safe to call once per page."""
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; }
        [data-testid="stMetricValue"] { font-size: 1.6rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
