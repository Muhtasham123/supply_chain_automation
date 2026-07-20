"""
chatbot/agent.py — a LangGraph text-to-SQL agent over the supply_chain_db.

Flow (LangGraph):

    generate_sql ──► execute_sql ──► (error & attempts left?) ──► generate_sql
                                   └────────────► summarize ──► END

* generate_sql : Gemini writes ONE read-only PostgreSQL SELECT from the live
                 schema (and the previous error, when retrying).
* execute_sql  : runs the query read-only, returns a DataFrame or an error.
* summarize    : Gemini writes a short natural-language answer about the result.

Public API:
    answer_question(question, api_key=None, model=None) -> {
        "sql": str, "dataframe": pandas.DataFrame | None,
        "answer": str, "error": str | None,
    }

Config via env (all optional, sensible defaults for this project):
    GOOGLE_API_KEY, GEMINI_MODEL,
    PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any, Optional, TypedDict

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Optional hardcoded key/model from chatbot/config.py (fallback to env / sidebar).
try:
    from chatbot.config import OPENAI_API_KEY as _CFG_KEY, OPENAI_MODEL as _CFG_MODEL
except Exception:
    _CFG_KEY, _CFG_MODEL = "", "gpt-4o-mini"

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", _CFG_MODEL or "gpt-4o-mini")
MAX_ROWS = 1000          # safety cap injected into generated queries
MAX_ATTEMPTS = 3         # SQL generation retries on execution error


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db_uri() -> str:
    user = os.getenv("PGUSER", "postgres")
    pwd = os.getenv("PGPASSWORD", "345waleed")
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE", "supply_chain_db")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_db_uri(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_schema() -> str:
    """CREATE-TABLE + a few sample rows for every table, for the LLM prompt."""
    from langchain_community.utilities import SQLDatabase
    db = SQLDatabase(get_engine(), sample_rows_in_table_info=3)
    return db.get_table_info()


# ---------------------------------------------------------------------------
# SQL safety helpers
# ---------------------------------------------------------------------------

_WRITE_WORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|"
    r"comment|merge|replace|call|do|copy|vacuum)\b",
    re.IGNORECASE,
)


def clean_sql(raw: str) -> str:
    """Strip markdown fences / prose and keep the first statement."""
    s = raw.strip()
    s = re.sub(r"^```(?:sql)?", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"```$", "", s).strip()
    # keep only the first statement
    s = s.split(";")[0].strip()
    return s


def is_safe_select(sql: str) -> bool:
    stripped = sql.lstrip().lower()
    return stripped.startswith(("select", "with")) and not _WRITE_WORDS.search(sql)


def add_limit(sql: str, limit: int = MAX_ROWS) -> str:
    if re.search(r"\blimit\b", sql, re.IGNORECASE):
        return sql
    return f"{sql}\nLIMIT {limit}"


def dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make column names unique. A SELECT * across joined tables can return
    repeated names (e.g. import_id, item_code, uom), which pandas allows but
    Streamlit/Arrow rejects. Later duplicates get a _1, _2 … suffix."""
    if not df.columns.duplicated().any():
        return df
    seen: dict = {}
    new_cols = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df = df.copy()
    df.columns = new_cols
    return df


# ---------------------------------------------------------------------------
# Display intent — decide what the user wants back (text / table / chart)
# ---------------------------------------------------------------------------
_CHART_RE = re.compile(
    r"\b(chart|graph|plot|pie|donut|bar|line|trend|visuali[sz]e|histogram)\b", re.I
)
_TABLE_RE = re.compile(
    r"\b(table|list|rows|records|csv|spreadsheet|breakdown)\b"
    r"|\b(show|list|give)\s+(me\s+)?all\b",
    re.I,
)


def detect_display(question: str):
    """Return (mode, chart_type). mode is 'text' | 'table' | 'chart'.
    Default is 'text' (describe only) unless the user explicitly asks for a
    table or a chart."""
    q = question or ""
    if _CHART_RE.search(q):
        ql = q.lower()
        if "pie" in ql or "donut" in ql:
            return "chart", "pie"
        if "line" in ql or "trend" in ql or "over time" in ql:
            return "chart", "line"
        return "chart", "bar"
    if _TABLE_RE.search(q):
        return "table", None
    return "text", None


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
def get_llm():
    api_key = os.getenv("OPENAI_API_KEY") or _CFG_KEY
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key found. Paste it in chatbot/config.py (OPENAI_API_KEY), "
            "set the OPENAI_API_KEY env var, or type it in the app sidebar."
        )
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        temperature=0,
        api_key=api_key,
    )


_SQL_SYSTEM = """You are a senior PostgreSQL analyst for a supply-chain database.
Write exactly ONE read-only SQL query (a single SELECT, optionally a leading CTE
with WITH) that answers the user's question.

Rules:
- PostgreSQL dialect only. Read-only: never INSERT/UPDATE/DELETE/DDL.
- Return ONLY the SQL. No explanation, no markdown fences, no trailing semicolon.
- Use case-insensitive matching for text filters (ILIKE '%value%').
- Prefer explicit column lists over SELECT * when the user asks for specific fields.
- Only use tables and columns that appear in the schema below.
- `item_code` is an opaque code (e.g. '26487-60'), NOT a product name. The
  transaction tables (stock, issuance, import_item, purchases_data,
  store_requisition) carry only `item_code`; the human-readable name/specs live
  in the `items` table (columns: item, group_name, material_standard,
  item_category, specs). Whenever the user names a product / material / keyword
  (e.g. 'pipe', 'resin', 'steel', 'bearing'), you MUST JOIN that transaction
  table to items ON item_code and filter with ILIKE on items.item (and those
  descriptive columns). NEVER put a product name in an item_code filter. Also
  join to items whenever you need to show the item name.
  Worked example — "supplier of our last purchase of resin":
      SELECT p.purchase, p.supplier
      FROM purchases_data p JOIN items i ON p.item_code = i.item_code
      WHERE i.item ILIKE '%resin%'
      ORDER BY p.purchase DESC NULLS LAST
      LIMIT 1
- Two SEPARATE domains share this database and must NEVER be joined to each other:
    * IMPORTS: import_details, import_item, shipment_details, payment_history.
      `shipment_details` IS the import shipment table (one row per batch / B/L),
      linked via import_details.import_id. Use it for "import shipments".
    * EXPORTS / logistics: exports, export_shipments, export_documents,
      shipment_containers, packing_details, shifting_movements.
  Never use export_shipments for an imports question (or vice-versa); their id
  columns are unrelated, so joining across the two domains is always wrong.
- Import progress/status is import_details.current_status, with values like:
  'Arrived at Works', 'Under Production', 'In Transit', 'Ready Awaiting Sailing',
  'Under Custom Clearance', 'LC in Process', 'Costing in Process', 'Order Cancelled'.
  Treat "ongoing" / "in progress" / "currently" (not yet completed) as:
  current_status NOT IN ('Arrived at Works', 'Order Cancelled').
- For "next", "upcoming", "soonest", or "when will ... arrive / happen" questions
  about a FUTURE event, filter the relevant date column to `>= CURRENT_DATE` and
  ORDER BY it ASC, so you return the soonest upcoming date — never a past/overdue
  one. (e.g. WHERE sd.eta_final >= CURRENT_DATE ORDER BY sd.eta_final ASC LIMIT 1).
- An import shipment is "overdue" / "delayed" / "late" / "past due" when its ETA
  has already passed but it still hasn't arrived:
      sd.eta_final < CURRENT_DATE
      AND id.current_status NOT IN ('Arrived at Works', 'Order Cancelled')
  Order by sd.eta_final ASC (most overdue first); (CURRENT_DATE - sd.eta_final)
  gives the days overdue.
- Many numeric columns contain NULLs. When ranking / sorting for "top", "highest",
  "lowest", "largest" etc., append NULLS LAST (e.g. ORDER BY col DESC NULLS LAST)
  so real values rank first, and consider filtering `WHERE col IS NOT NULL`.
- For SUM/AVG/MAX/MIN over a column, NULLs are ignored automatically — that's fine.
- For "per day" / "average per day" / "daily average" of a measure (e.g. issuance,
  consumption, purchases), divide the TOTAL by the number of days:
  SUM(measure) / NULLIF(COUNT(DISTINCT date_col), 0). NEVER use
  AVG(measure) / COUNT(days) — that is mathematically wrong.
- purchases_data has THREE dates with distinct meanings:
    * ppc_store  = the date the demand / requirement was raised (demand placed).
    * required_d = the date the item is REQUIRED BY (deadline; often in the future).
    * purchase   = the date it was actually purchased.
  Average "delay from demand to purchase" / procurement lead time =
  AVG(purchase - ppc_store) — a plain average of the day-differences across the
  matching rows. Do NOT divide by COUNT(DISTINCT date); that per-day rule is only
  for "per day / daily average", NOT for average delays or lead times.
  NEVER use required_d as the demand date — it is the required-by deadline and
  gives meaningless negative delays when items are bought ahead of the deadline.
- If the user asks for "all"/"list", cap results with LIMIT {max_rows} unless they
  ask for a specific number.
- You can also provide visualizations if user asks and if it is possible using simple html.
- If user asks for quantity try to display uom of the item as well if possible.
-always try to use terms that match with database column values
-whenever the user asks for the stock you must concatenate the uom after it.
-User can give these aliases when asking qcl is (Qadcast (Pvt) Ltd.), qbl2 is qadri brothers unit 2, qen is (Qadri Engineering (Pvt) Ltd.), qe is qadbros engineering.

Database schema:
{schema}"""

_SUMMARY_SYSTEM = """You are a helpful supply-chain data assistant. Given the user's
question and the query result, write a brief, direct answer in plain English
(2-4 sentences max). The full result is already shown to the user as a table, so
do NOT repeat every row — highlight the key numbers / findings. If the result is
empty, say that no matching records were found."""


# ---------------------------------------------------------------------------
# LangGraph
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    question: str
    sql: str
    data: Any            # pandas.DataFrame | None
    error: Optional[str]
    answer: str
    attempts: int


def _generate_sql(state: AgentState) -> AgentState:
    llm = get_llm()
    system = _SQL_SYSTEM.format(schema=get_schema(), max_rows=MAX_ROWS)
    human = f"Question: {state['question']}"
    if state.get("error"):
        human += (
            f"\n\nYour previous query failed:\n{state['sql']}\n\n"
            f"PostgreSQL error:\n{state['error']}\n\nFix it and return corrected SQL."
        )
    raw = llm.invoke([("system", system), ("human", human)]).content
    sql = add_limit(clean_sql(raw))
    attempt = state.get("attempts", 0) + 1
    print(f"\n[chatbot] Q: {state['question']}", flush=True)
    print(f"[chatbot] SQL (attempt {attempt}):\n{sql}", flush=True)
    return {"sql": sql, "attempts": attempt}


def _execute_sql(state: AgentState) -> AgentState:
    sql = state.get("sql", "")
    if not is_safe_select(sql):
        return {"data": None, "error": "Only read-only SELECT queries are allowed."}
    try:
        with get_engine().connect() as conn:
            df = pd.read_sql_query(text(sql), conn)
        df = dedupe_columns(df)
        print(f"[chatbot] rows returned: {len(df)}", flush=True)
        return {"data": df, "error": None}
    except Exception as exc:  # surfaced back to the model for a retry
        err = str(exc).strip()
        print(f"[chatbot] SQL error: {err}", flush=True)
        return {"data": None, "error": err}


def _route_after_execute(state: AgentState) -> str:
    if state.get("error") and state.get("attempts", 0) < MAX_ATTEMPTS:
        return "retry"
    return "summarize"


def _summarize(state: AgentState) -> AgentState:
    if state.get("error"):
        return {
            "answer": "Sorry — I couldn't answer that from the database "
                      f"(the query kept failing). Last error: {state['error']}"
        }
    df: pd.DataFrame = state["data"]
    n = len(df)
    if n == 0:
        return {"answer": "No matching records were found."}
    preview = df.head(20).to_string(index=False)
    llm = get_llm()
    human = (
        f"Question: {state['question']}\n\n"
        f"Result: {n} row(s). Preview (first 20):\n{preview}"
    )
    answer = llm.invoke([("system", _SUMMARY_SYSTEM), ("human", human)]).content
    return {"answer": answer}


@lru_cache(maxsize=1)
def get_graph():
    from langgraph.graph import StateGraph, START, END
    g = StateGraph(AgentState)
    g.add_node("generate_sql", _generate_sql)
    g.add_node("execute_sql", _execute_sql)
    g.add_node("summarize", _summarize)
    g.add_edge(START, "generate_sql")
    g.add_edge("generate_sql", "execute_sql")
    g.add_conditional_edges(
        "execute_sql", _route_after_execute,
        {"retry": "generate_sql", "summarize": "summarize"},
    )
    g.add_edge("summarize", END)
    return g.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def answer_question(question: str, api_key: Optional[str] = None,
                    model: Optional[str] = None) -> dict:
    """Run the agent and return {sql, dataframe, answer, error}."""
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if model:
        os.environ["OPENAI_MODEL"] = model

    final: AgentState = get_graph().invoke(
        {"question": question, "attempts": 0, "error": None}
    )
    df = final.get("data")
    display, chart_type = detect_display(question)
    # No data (error/empty) -> just describe, never a table/chart.
    if final.get("error") or not isinstance(df, pd.DataFrame) or df.empty:
        display, chart_type = "text", None
    print(f"[chatbot] answer: {final.get('answer', '')}", flush=True)
    print(f"[chatbot] display: {display}"
          + (f" ({chart_type})" if chart_type else "") + "\n", flush=True)
    return {
        "sql": final.get("sql"),
        "dataframe": df if isinstance(df, pd.DataFrame) else None,
        "answer": final.get("answer", ""),
        "error": final.get("error"),
        "display": display,
        "chart_type": chart_type,
    }
