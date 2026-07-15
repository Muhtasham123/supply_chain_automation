import streamlit as st
from utils.mock_data import stock_data


st.title("🏭 Inventory Management")


df=stock_data()


st.dataframe(
    df,
    use_container_width=True
)


status=st.selectbox(
    "Stock Status",
    df.Status.unique()
)


st.write(
    df[df.Status==status]
)