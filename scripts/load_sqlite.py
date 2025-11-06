import sqlite3
import pandas as pd
import os

os.makedirs("db", exist_ok=True)
df = pd.read_parquet("data/nyc311.parquet")

keep = [
    "unique_key", "created_date", "closed_date", "agency",
    "complaint_type", "descriptor", "borough", "city",
    "incident_zip", "status", "open_data_channel_type",
    "resolution_hours", "latitude", "longitude"
]
df = df[keep].copy()

for c in ["borough", "city", "complaint_type", "descriptor", "status", "open_data_channel_type"]:
    df[c] = df[c].fillna("Unknown")

con = sqlite3.connect("db/insightpilot.db")
cur = con.cursor()

cur.executescript("""
DROP TABLE IF EXISTS service_requests;

CREATE TABLE service_requests (
  unique_key TEXT PRIMARY KEY,
  created_date TEXT,
  closed_date TEXT,
  agency TEXT,
  complaint_type TEXT,
  descriptor TEXT,
  borough TEXT,
  city TEXT,
  incident_zip TEXT,
  status TEXT,
  open_data_channel_type TEXT,
  resolution_hours REAL,
  latitude REAL,
  longitude REAL
);
""")

df.to_sql("service_requests", con, if_exists="append", index=False)

cur.executescript("""
CREATE INDEX IF NOT EXISTS idx_month ON service_requests(created_date);
CREATE INDEX IF NOT EXISTS idx_borough ON service_requests(borough);
CREATE INDEX IF NOT EXISTS idx_type ON service_requests(complaint_type);
""")

con.commit()
con.close()
print("Data loaded into db/insightpilot.db (table: service_requests)")
