# tests/test_query_validator.py
import pytest
from src.query_validator import sanitize_select

def test_allow_select_adds_limit():
    out = sanitize_select("SELECT 1")
    assert "LIMIT" in out.upper()

def test_preserve_existing_limit():
    out = sanitize_select("select * from customers limit 5")
    assert out.strip().lower().endswith("limit 5")

def test_allow_cte():
    out = sanitize_select("with t as (select 1) select * from t")
    assert "LIMIT" in out.upper()

def test_block_insert():
    with pytest.raises(ValueError):
        sanitize_select("INSERT INTO customers values (1)")

def test_block_ddl():
    with pytest.raises(ValueError):
        sanitize_select("DROP TABLE customers")

def test_block_system_catalog():
    with pytest.raises(ValueError):
        sanitize_select("SELECT * FROM pg_catalog.pg_tables")

def test_block_multi_statements():
    with pytest.raises(ValueError):
        sanitize_select("SELECT 1; SELECT 2")

def test_empty_sql():
    with pytest.raises(ValueError):
        sanitize_select("")
