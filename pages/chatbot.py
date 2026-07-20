import pandas as pd
import plotly.express as px
import streamlit as st

from chatbot.agent import answer_question

st.title("🤖 Supply Chain Assistant")
st.caption("Ask a question about your data — I'll query the database and show the results.")


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    if st.button("Clear conversation"):
        st.session_state.pop("messages", None)
        st.rerun()


# --------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------
def render_chart(df: pd.DataFrame, chart_type: str, key: str):
    """Draw a simple pie/bar/line from the result. x = first categorical column,
    y = first numeric column. Falls back to a table if there's nothing to plot."""
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols]
    if not num_cols:
        st.info("Nothing numeric to chart — showing the data instead.")
        st.dataframe(df, width="stretch", hide_index=True)
        return
    y = num_cols[0]
    x = cat_cols[0] if cat_cols else df.columns[0]
    d = df.head(30)
    if chart_type == "pie":
        fig = px.pie(d, names=x, values=y, title=f"{y} by {x}")
    elif chart_type == "line":
        fig = px.line(d, x=x, y=y, markers=True, title=f"{y} by {x}")
    else:
        fig = px.bar(d, x=x, y=y, title=f"{y} by {x}")
    st.plotly_chart(fig, width="stretch", key=f"chart_{key}")
    if len(df) > 30:
        st.caption("Showing the first 30 rows in the chart.")


def render_result(msg: dict, key: str):
    """Render one assistant turn. Text always; table or chart only if asked."""
    if msg.get("content"):
        st.markdown(msg["content"])

    df = msg.get("df")
    display = msg.get("display", "text")
    if not isinstance(df, pd.DataFrame) or df.empty:
        return

    if display == "chart":
        render_chart(df, msg.get("chart_type") or "bar", key)
    elif display == "table":
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button(
            "⬇️ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="query_result.csv",
            mime="text/csv",
            key=f"dl_{key}",
        )
        st.caption(f"{len(df)} row(s) · click a column header to sort")


# --------------------------------------------------------------------------
# Conversation state + history
# --------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_result(msg, key=f"hist_{i}")


# --------------------------------------------------------------------------
# New question
# --------------------------------------------------------------------------
question = st.chat_input("e.g. Show all imports for supplier SQ with their PKR value")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Querying the database…"):
                result = answer_question(question)
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")
            st.stop()

        assistant_msg = {
            "role": "assistant",
            "content": result.get("answer") or "",
            "df": result.get("dataframe"),
            "display": result.get("display", "text"),
            "chart_type": result.get("chart_type"),
        }
        render_result(assistant_msg, key="new")
        if result.get("error"):
            st.caption(f"⚠️ query error: {result['error']}")

    st.session_state.messages.append(assistant_msg)
