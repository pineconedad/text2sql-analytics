# src/query_validator.py
# src/query_validator.py
"""
Query Validator: Sanitizes and validates SQL queries for security and correctness.
"""
import re

_BLOCK = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|VACUUM|ANALYZE)\b", re.I)
_SYS   = re.compile(r"\b(pg_catalog|information_schema)\b", re.I)

def sanitize_select(sql: str, row_limit: int = 1000) -> str:
    """
    Sanitize and validate a SQL SELECT statement.
    Enforces SELECT-only, blocks forbidden keywords, system tables, and enforces LIMIT.
    Args:
        sql (str): Input SQL query.
        row_limit (int): Maximum number of rows to return.
    Returns:
        str: Sanitized SQL query.
    Raises:
        ValueError: If query is empty, contains forbidden keywords, or is not SELECT/CTE.
    """
    if not sql or not sql.strip():
        raise ValueError("Empty SQL")
    s = sql.strip()

    # single statement only
    if ";" in s.strip(";"):
        raise ValueError("Multiple statements not allowed")

    # must start with SELECT or WITH
    u = s.lstrip().upper()
    if not (u.startswith("SELECT") or u.startswith("WITH")):
        raise ValueError("Only SELECT/CTE allowed")

    if _BLOCK.search(s) or _SYS.search(s):
        raise ValueError("Forbidden keyword or system schema")

    # enforce LIMIT if not present at top level (cheap check)
    if re.search(r"\blimit\b\s+\d+\s*$", s, re.I) is None and re.search(r"\bfetch\s+first\b", s, re.I) is None:
        s = f"{s.rstrip()}\nLIMIT {int(row_limit)}"

    return s
