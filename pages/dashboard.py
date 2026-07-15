import streamlit as st
import plotly.express as px

from utils.mock_data import purchase_data


st.title("📊 Dashboard")


df=purchase_data()


col1,col2,col3=st.columns(3)


with col1:
    st.metric(
        "Orders",
        len(df)
    )


with col2:
    st.metric(
        "Pending Qty",
        df.Pending.sum()
    )


with col3:
    st.metric(
        "Completion %",
        "65%"
    )


fig=px.bar(
    df,
    x="Supplier",
    y="Pending",
    title="Pending Purchase by Supplier"
)


st.plotly_chart(fig,use_container_width=True)


st.dataframe(
    df,
    use_container_width=True
)