# src/database.py
import os
import re
import time
from collections import OrderedDict
from src.query_validator import sanitize_select

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.utils import require_env

# Load env vars when running locally (no-op in Docker where env is injected)
load_dotenv()

# --- Config ---
DB_URL = require_env("DATABASE_URL")
RO_URL = require_env("DB_READONLY_URL")  # readonly connection string
TIMEOUT_MS = int(os.getenv("QUERY_TIMEOUT_SECONDS", "5")) * 1000
ROW_LIMIT = int(os.getenv("ROW_LIMIT", "1000"))

# Optional cache knobs (set to 0 to disable)
_CACHE_TTL = int(os.getenv("QUERY_CACHE_TTL_SECONDS", "30"))       # seconds
_CACHE_MAX = int(os.getenv("QUERY_CACHE_MAX_ROWS", "128"))          # entries

# --- Engines ---
admin_engine = create_engine(DB_URL, pool_pre_ping=True)
ro_engine = create_engine(RO_URL, pool_pre_ping=True)

# --- Simple in-memory TTL + LRU cache ---
# key -> (timestamp, rows)
_cache: "OrderedDict[tuple, tuple[float, list[dict]]]" = OrderedDict()


def _cache_key(sql: str, params: dict | None, row_limit: int | None) -> tuple:
    return (
        sql.strip(),
        tuple(sorted((params or {}).items())),
        int(row_limit or 0),
    )


def _cache_get(key: tuple) -> list[dict] | None:
    if _CACHE_TTL <= 0 or _CACHE_MAX <= 0:
        return None
    hit = _cache.get(key)
    if not hit:
        return None
    ts, rows = hit
    if (time.time() - ts) > _CACHE_TTL:
        # expired
        try:
            del _cache[key]
        except KeyError:
            pass
        return None
    # LRU: move to end on hit
    _cache.move_to_end(key)
    return rows


def _cache_put(key: tuple, rows: list[dict]) -> None:
    if _CACHE_TTL <= 0 or _CACHE_MAX <= 0:
        return
    _cache[key] = (time.time(), rows)
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)  # evict LRU


def run_readonly(sql: str, params: dict | None = None, row_limit: int | None = None) -> list[dict]:
    """
    Execute a safe read-only query on the readonly connection.

    - Enforces statement_timeout.
    - Caps rows via LIMIT.
    - Caches identical queries (sql+params+row_limit) in memory for a short TTL.
    """
    limit = int(row_limit or ROW_LIMIT)
    s = sql.strip()

    # If caller specified row_limit, enforce it by wrapping — this respects any user LIMIT
    if row_limit is not None:
        s = f"SELECT * FROM ({s}) AS _t LIMIT {limit}"
    else:
        # Otherwise, add LIMIT if none exists at the end
        if not re.search(r"\blimit\b\s+\d+\s*$", s, re.I) and not re.search(r"\bfetch\s+first\b", s, re.I):
            s = f"{s}\nLIMIT {limit}"

    key = _cache_key(s, params, limit)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    with ro_engine.connect() as c:
        c.execute(text(f"SET statement_timeout = {TIMEOUT_MS}"))
        rows = [dict(r) for r in c.execute(text(s), params or {}).mappings().all()]

    _cache_put(key, rows)
    return rows

# ---- Execution plan (safe) ----
def explain_sql(sql: str, row_limit: int | None = 50) -> dict:
    """
    Run a safe EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) on a SELECT.
    - Reuses sanitize_select to prevent non-SELECT & to cap rows.
    - Applies statement_timeout.
    Returns a JSON-ready dict with the plan & timings.
    """
    safe_sql = sanitize_select(sql, row_limit=row_limit or 50) # type: ignore

    with ro_engine.connect() as c:
        c.execute(text(f"SET statement_timeout = {TIMEOUT_MS}"))
        # FORMAT JSON returns a single JSON value (list with one dict)
        res = c.execute(
            text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {safe_sql}")
        ).scalar()

    # res looks like: [ { "Plan": {...}, "Planning Time": X, "Execution Time": Y, ... } ]
    top = res[0] if isinstance(res, list) and res else {}
    plan = top.get("Plan", {})
    return {
        "sql": safe_sql,
        "plan": plan,  # full node tree
        "planning_time_ms": top.get("Planning Time"),
        "execution_time_ms": top.get("Execution Time"),
        "jit": top.get("JIT"),
        "triggers": top.get("Triggers"),
    }
