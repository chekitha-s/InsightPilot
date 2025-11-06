import os, json, sqlite3
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "db/insightpilot.db"
SCHEMA_PATH = "db/schema_metadata.json"

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

llm = Ollama(model="llama3") 


def generate_sql(prompt):
    """Generate SQL using local Ollama model."""
    system_prompt = f"""
You are a data analyst. Translate the question into a valid SQLite SELECT query.
Database schema:
{json.dumps(SCHEMA, indent=2)}

Rules:
- Use correct column names.
- Only SELECT statements (no INSERT/UPDATE/DELETE).
- Add aggregates (AVG, COUNT, SUM) when appropriate.
Return ONLY the SQL query text.
"""

    full_prompt = f"{system_prompt}\nUser: {prompt}\nSQL:"
    sql_query = llm.invoke(full_prompt).strip()

    # Clean up possible markdown fences/backticks
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
