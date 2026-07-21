import io

import pandas as pd
import plotly.express as px
import streamlit as st

from chatbot.agent import (answer_question, extract_item_query,
                           find_item_candidates, resolve_selections,
                           answer_item_details, detect_date_range_need,
                           parse_date_range, is_pure_format_directive)

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
@st.cache_data(show_spinner=False)
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to an .xlsx file (openpyxl) for download. Cached so a
    given result is serialized ONCE, not rebuilt for every past table message on
    each Streamlit rerun (which grew laggy as the conversation got longer)."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    return buf.getvalue()


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
            "⬇️ Download Excel",
            data=to_excel_bytes(df),
            file_name="query_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_{key}",
        )
        st.caption(f"{len(df)} row(s) · click a column header to sort")


# --------------------------------------------------------------------------
# Conversation state + history
# --------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None        # {"candidates": df, "question": str}
if "pending_dates" not in st.session_state:
    st.session_state.pending_dates = None  # {"question": str} awaiting a date range

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
        pending = st.session_state.pending
        pending_dates = st.session_state.pending_dates
        history = st.session_state.get("last_turn")   # {"question","sql"} of prior turn
        result = None
        asked_question = question                     # what to remember for follow-ups
        try:
            if pending:                                    # resolving an item clarification
                codes = resolve_selections(question, pending["candidates"])
                asked_question = pending["question"]
                if not codes:
                    assistant_msg = {
                        "role": "assistant", "display": "text", "df": None,
                        "content": "I couldn't tell which item(s) you mean — reply with "
                                   "the **item code(s)** or **row number(s)** above "
                                   "(e.g. `1 and 3`, or `all`), or ask a new question.",
                    }
                else:
                    st.session_state.pending = None
                    with st.spinner("Fetching item details…"):
                        result = answer_item_details(codes, pending["question"],
                                                     history=history)
                    assistant_msg = {
                        "role": "assistant",
                        "content": result.get("answer") or "",
                        "df": result.get("dataframe"),
                        "display": result.get("display", "text"),
                        "chart_type": result.get("chart_type"),
                    }
            elif pending_dates:                            # resolving a date-range question
                st.session_state.pending_dates = None
                asked_question = pending_dates["question"]
                date_range = parse_date_range(question)
                span = ("all dates" if not date_range else
                        f"{date_range[0] or '…'} → {date_range[1] or '…'}")
                with st.spinner(f"Querying the database ({span})…"):
                    result = answer_question(asked_question, history=history,
                                             date_range=date_range)
                assistant_msg = {
                    "role": "assistant",
                    "content": result.get("answer") or "",
                    "df": result.get("dataframe"),
                    "display": result.get("display", "text"),
                    "chart_type": result.get("chart_type"),
                }
            elif is_pure_format_directive(question) and not (
                    history and history.get("sql")):
                # Bare format directive ("show me the table") with no previous
                # result to reformat -> ask instead of running a subject-less query
                # (which would otherwise dump a whole table).
                assistant_msg = {
                    "role": "assistant", "display": "text", "df": None,
                    "content": "I don't have a previous result to reformat. What data "
                               "would you like to see as a table or chart? For example: "
                               "*“issuances last month”* or *“imports for supplier SQ”*.",
                }
            else:
                intent = extract_item_query(question)      # fresh question
                cands = (find_item_candidates(intent["keyword"])
                         if intent["is_item_detail"] and intent["keyword"] else None)
                date_need = (detect_date_range_need(question)
                             if cands is None or cands.empty else
                             {"needs_range": False})
                if cands is not None and not cands.empty:
                    st.session_state.pending = {"candidates": cands, "question": question}
                    n = len(cands)
                    kw = intent["keyword"]
                    content = (
                        f"I found **1 item** matching **“{kw}”** — is this the one? "
                        f"Reply **yes** or the item code."
                        if n == 1 else
                        f"I found **{n} items** matching **“{kw}”**. Which one(s)? "
                        f"Reply with the **item code(s)** or **row number(s)** — "
                        f"e.g. `1`, `1 and 3`, or `all`."
                    )
                    assistant_msg = {"role": "assistant", "content": content,
                                     "df": cands, "display": "table"}
                elif date_need.get("needs_range"):
                    st.session_state.pending_dates = {"question": question}
                    eg = ""
                    if date_need.get("default_from") and date_need.get("default_to"):
                        eg = (f" — for example `{date_need['default_from']} to "
                              f"{date_need['default_to']}`")
                    content = (
                        "That data covers a time span. **From when to when** should I look?"
                        f"{eg}\n\nReply with a range like `2026-01-01 to 2026-06-30`, a "
                        "phrase like `last 3 months`, or **`all`** for no date limit."
                    )
                    assistant_msg = {"role": "assistant", "content": content,
                                     "df": None, "display": "text"}
                else:
                    with st.spinner("Querying the database…"):
                        result = answer_question(question, history=history)
                    assistant_msg = {
                        "role": "assistant",
                        "content": result.get("answer") or "",
                        "df": result.get("dataframe"),
                        "display": result.get("display", "text"),
                        "chart_type": result.get("chart_type"),
                    }
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")
            st.stop()

        render_result(assistant_msg, key="new")
        if result and result.get("sql"):          # remember this turn for follow-ups
            st.session_state.last_turn = {
                "question": asked_question,
                "sql": result["sql"],
            }

    st.session_state.messages.append(assistant_msg)
