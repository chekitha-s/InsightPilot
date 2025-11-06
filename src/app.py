# src/app.py
import os
import json
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

# Our agent functions (now using Ollama under the hood)
from llm_sql_agent import generate_sql, execute_query

DB_PATH = "db/insightpilot.db"
SCHEMA_PATH = "db/schema_metadata.json"

st.set_page_config(page_title="InsightPilot (Ollama)", layout="wide")

# -----------------------------
# Helpers
# -----------------------------
def get_db_stats():
    if not os.path.exists(DB_PATH):
        return {"rows": 0, "tables": []}
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        rows = cur.execute("SELECT COUNT(*) FROM service_requests;").fetchone()[0]
    except Exception:
        rows = 0
    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
    con.close()
    return {"rows": rows, "tables": [t[0] for t in tables]}

def load_schema():
    if not os.path.exists(SCHEMA_PATH):
        return {}
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def add_history_item(question, sql, df_head):
    if "history" not in st.session_state:
        st.session_state["history"] = []
    st.session_state["history"].insert(
        0,
        {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "sql": sql,
            "preview": df_head.to_dict(orient="records") if df_head is not None else [],
            "rows": 0 if df_head is None else len(df_head),
        },
    )

def render_chart_if_possible(df: pd.DataFrame):
    # If first col is categorical and second is numeric, show bar chart
    if df is None or df.empty or df.shape[1] < 2:
        return
    # Try to find first numeric column (excluding the 1st col if it's numeric counts)
    numeric_cols = df.select_dtypes(include=["float64", "int64", "Int64"]).columns.tolist()
    if len(numeric_cols) == 0:
        return
    # Prefer the second column if numeric; else any numeric column
    y_col = df.columns[1] if df.columns[1] in numeric_cols else numeric_cols[0]
    x_col = df.columns[0]
    try:
        st.subheader("📊 Quick Chart")
        st.bar_chart(df.set_index(x_col)[y_col])
    except Exception:
        pass

# -----------------------------
# Header & Sidebar
# -----------------------------
st.title("🧠 InsightPilot — Conversational Analytics (Local Ollama)")
st.caption("Ask questions in plain English → InsightPilot generates SQL, runs it on SQLite, and shows results & charts.")

with st.sidebar:
    st.header("ℹ️ About this build")
    st.write(
        "- **LLM**: Llama 3 via **Ollama** (local, no API keys)\n"
        "- **DB**: SQLite (`db/insightpilot.db`)\n"
        "- **Data**: NYC 311 Service Requests (last 12 months)\n"
        "- **Safety**: SELECT-only guardrails"
    )
    st.divider()
    stats = get_db_stats()
    st.metric("Rows in service_requests", f"{stats['rows']:,}")
    st.caption(f"Tables: {', '.join(stats['tables']) or '—'}")
    schema = load_schema()
    with st.expander("📚 Schema"):
        if schema:
            st.json(schema, expanded=False)
        else:
            st.info("No schema file found yet.")

# -----------------------------
# Main interaction
# -----------------------------
col_q, col_btn = st.columns([4, 1])
with col_q:
    user_query = st.text_input(
        "🔍 Your question",
        placeholder="e.g., Which borough has the highest average resolution time?",
        label_visibility="collapsed",
    )
with col_btn:
    run_clicked = st.button("Run", use_container_width=True)

if run_clicked and user_query.strip():
    # 1) Generate SQL from the question
    with st.spinner("Generating SQL with Llama 3 (Ollama)..."):
        sql_query = generate_sql(user_query)

    st.subheader("🧾 Generated SQL")
    st.code(sql_query, language="sql")

    # 2) Execute safely and show results
    try:
        with st.spinner("Executing query on SQLite..."):
            df = execute_query(sql_query)

        st.success(f"Returned {len(df)} rows")
        st.dataframe(df, use_container_width=True, height=360)

        # 3) Quick chart if possible
        render_chart_if_possible(df)

        # 4) Downloads
        if not df.empty:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download results (CSV)",
                csv,
                file_name="insightpilot_results.csv",
                mime="text/csv",
            )

        # 5) Add to local history (store only a small preview)
        add_history_item(user_query, sql_query, df.head(20) if not df.empty else None)

    except Exception as e:
        st.error(f"Error while executing SQL: {e}")

st.divider()

# -----------------------------
# History Panel
# -----------------------------
st.subheader("🕘 Query History (local)")
if "history" not in st.session_state or len(st.session_state["history"]) == 0:
    st.caption("No history yet. Run a query to see it here.")
else:
    for i, item in enumerate(st.session_state["history"], start=1):
        with st.expander(f"{i}. [{item['ts']}] {item['question']}"):
            st.code(item["sql"], language="sql")
            prev = pd.DataFrame(item["preview"])
            if not prev.empty:
                st.dataframe(prev, use_container_width=True, height=220)
                st.caption(f"Showing {len(prev)} rows (preview).")
            else:
                st.caption("No results returned.")
