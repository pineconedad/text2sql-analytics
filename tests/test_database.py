# tests/test_database.py
from src.database import run_readonly

def test_ro_simple_select():
    rows = run_readonly("SELECT 1 AS x")
    assert rows and rows[0]["x"] == 1

def test_ro_limit_enforced():
    rows = run_readonly("SELECT generate_series(1, 5000) AS x", row_limit=10)
    assert len(rows) == 10
