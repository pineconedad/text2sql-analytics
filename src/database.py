import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
RO_URL = os.getenv("DB_READONLY_URL") or DB_URL
TIMEOUT_MS = int(os.getenv("QUERY_TIMEOUT_SECONDS", "5")) * 1000
ROW_LIMIT = int(os.getenv("ROW_LIMIT", "1000"))

admin_engine = create_engine(DB_URL, pool_pre_ping=True)
ro_engine = create_engine(RO_URL, pool_pre_ping=True)

def run_readonly(sql: str, params: dict | None = None, row_limit: int | None = None):
    limit = row_limit or ROW_LIMIT
    s = sql.strip()

    # If caller specified a row_limit, enforce it by wrapping the query.
    # This respects any existing LIMIT but still caps to our requested limit.
    if row_limit is not None:
        s = f"SELECT * FROM ({s}) AS _t LIMIT {int(limit)}"
    else:
        # Otherwise, only add a LIMIT if none exists
        if not re.search(r"\blimit\b\s+\d+\s*$", s, re.I) and not re.search(r"\bfetch\s+first\b", s, re.I):
            s = f"{s}\nLIMIT {int(limit)}"

    with ro_engine.connect() as c:
        c.execute(text(f"SET statement_timeout = {TIMEOUT_MS}"))
        return [dict(r) for r in c.execute(text(s), params or {}).mappings().all()]
