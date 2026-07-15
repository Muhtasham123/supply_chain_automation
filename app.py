import streamlit as st
from utils.styles import apply_styles

st.set_page_config(
    page_title="Qadri Supply Chain Intelligence",
    page_icon="🏭",
    layout="wide"
)

apply_styles()

st.sidebar.title("🏭 Qadri Supply Chain AI")

st.sidebar.info(
    """
    AI Powered Supply Chain
    Analytics Platform
    """
)


st.title("Qadri Supply Chain Intelligence")

st.subheader("Management Overview")

col1,col2,col3,col4 = st.columns(4)


with col1:
    st.metric(
        "Total Purchase Orders",
        "245"
    )

with col2:
    st.metric(
        "Pending Orders",
        "65"
    )

with col3:
    st.metric(
        "Delayed Orders",
        "23"
    )

with col4:
    st.metric(
        "Purchase Value",
        "PKR 125M"
    )


st.divider()

st.success(
    "System Prototype Successfully Loaded"
)

st.write(
"""
Use the navigation menu on the left to explore:
- Purchase Analytics
- Inventory
- Import Tracking
- Custom Reports
- AI Assistant
"""
)