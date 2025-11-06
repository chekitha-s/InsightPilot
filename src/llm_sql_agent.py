import os
import json
import sqlite3
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_PATH = "db/insightpilot.db"
SCHEMA_PATH = "db/schema_metadata.json"

# Load schema context for Gemini
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

def generate_sql(prompt):
    """Use Gemini to generate a clean and complete SQL query."""
    system_instruction = f"""
    You are an expert data analyst AI.
    You translate English questions into correct SQL SELECT statements for SQLite.

    The database schema is:
    {json.dumps(SCHEMA, indent=2)}

    Requirements:
    - Always use proper column names from the schema.
    - Always include aggregates (AVG, COUNT, SUM) when user asks about 'highest', 'average', or 'total'.
    - Always include column aliases (e.g., AS avg_time).
    - Do NOT return markdown, comments, or code fences.
    - Only produce valid SELECT queries that can be executed on SQLite.
    """

    model = genai.GenerativeModel("gemini-2.5-flash")

    response = model.generate_content([
        system_instruction,
        f"User question: {prompt}",
        "Output only the SQL query text (no formatting)."
    ])

    sql_query = response.text.strip()
    for token in ["```sql", "```", "`"]:
        sql_query = sql_query.replace(token, "")
    sql_query = sql_query.strip().rstrip(";") + ";"

    # Simple fallback check: ensure at least one aggregate function
    if not any(keyword in sql_query.lower() for keyword in ["avg(", "count(", "sum(", "max(", "min("]):
        print("⚠️ SQL missing aggregate — retrying generation...")
        response = model.generate_content([
            system_instruction,
            f"User question: {prompt}. Include relevant aggregates (AVG, COUNT, etc)."
        ])
        sql_query = response.text.strip()
        for token in ["```sql", "```", "`"]:
            sql_query = sql_query.replace(token, "")
        sql_query = sql_query.strip().rstrip(";") + ";"

    return sql_query


def execute_query(sql):
    """Safely execute a SQL query and return a DataFrame."""
    import pandas as pd
    con = sqlite3.connect(DB_PATH)

    if not sql.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    df = pd.read_sql_query(sql, con)
    con.close()
    return df

if __name__ == "__main__":
    print("InsightPilot SQL Agent test")
    question = "Which borough has the highest average resolution time?"
    sql = generate_sql(question)
    print("Gemini-generated SQL:\n", sql)

    try:
        result = execute_query(sql)
        print("\nSample output:")
        print(result.head())
    except Exception as e:
        print("Error:", e)
