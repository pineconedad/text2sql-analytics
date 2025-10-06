import os
from src.text2sql_engine import generate_sql
from src.query_validator import sanitize_select
from src.database import run_readonly

def test_stub_customers_list(monkeypatch):
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    sql = generate_sql("list customers by name")
    sql = sanitize_select(sql, row_limit=10)
    rows = run_readonly(sql, row_limit=5)
    assert 1 <= len(rows) <= 5
    assert {"customer_id", "company_name"}.issubset(rows[0].keys())
