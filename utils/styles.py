import streamlit as st


def apply_styles():

    st.markdown(
    """
    <style>

    .stMetric {
        background-color:#f5f7fa;
        padding:15px;
        border-radius:10px;
    }


    h1 {
        color:#0B3D91;
    }


    h2,h3 {
        color:#333333;
    }


    </style>

    """,
    unsafe_allow_html=True
    )