import streamlit as st


st.title(
    "📑 Custom Report Builder"
)


report=st.selectbox(
    "Select Report",
    [
        "Purchase Report",
        "Stock Report",
        "Import Report"
    ]
)


st.multiselect(
    "Select Information",
    [
        "Supplier",
        "Item",
        "Quantity",
        "Amount",
        "Status",
        "Delay Days"
    ]
)


if st.button("Generate Report"):

    st.success(
        f"{report} Generated"
    )