from src.query_validator import sanitize_select
from src.database import run_readonly

def test_pipeline_customers_head():
    sql = sanitize_select("select customer_id, company_name from customers")
    rows = run_readonly(sql, row_limit=5)
    assert 1 <= len(rows) <= 5
    assert {"customer_id", "company_name"}.issubset(rows[0].keys())
