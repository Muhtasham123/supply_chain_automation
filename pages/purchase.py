import streamlit as st
from utils.mock_data import purchase_data


st.title("📦 Purchase Management")


df=purchase_data()


supplier = st.selectbox(
    "Supplier",
    ["All"]+
    list(df.Supplier.unique())
)


if supplier!="All":

    df=df[
        df.Supplier==supplier
    ]


status=st.radio(
    "Status",
    [
        "All",
        "Pending",
        "Completed"
    ]
)


if status=="Pending":

    df=df[df.Pending>0]


elif status=="Completed":

    df=df[df.Pending==0]


st.dataframe(
    df,
    use_container_width=True
)