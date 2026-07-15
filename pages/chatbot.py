import streamlit as st


st.title(
    "🤖 Supply Chain Assistant"
)


question=st.chat_input(
    "Ask your question..."
)


if question:

    with st.chat_message("user"):
        st.write(question)


    with st.chat_message("assistant"):

        st.write(
        """
        Example Response:

        23 purchase orders are delayed.

        Highest delay supplier:
        ABC Steel

        Average delay:
        18 days

        """
        )