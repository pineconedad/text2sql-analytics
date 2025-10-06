import pytest
from src.query_validator import sanitize_select

def test_block_insert_statements():
    with pytest.raises(ValueError):
        sanitize_select("INSERT INTO customers VALUES (1)")

def test_block_drop_statements():
    with pytest.raises(ValueError):
        sanitize_select("DROP TABLE customers")

def test_allow_select_statements():
    out = sanitize_select("SELECT * FROM customers")
    assert "LIMIT" in out.upper()

def test_sql_injection_prevention():
    with pytest.raises(ValueError):
        sanitize_select("SELECT * FROM customers; DROP TABLE customers;")

def test_query_timeout_enforcement():
    # TODO: Implement test for query timeout enforcement
    pass
