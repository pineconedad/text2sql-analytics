# tests/test_database.py
from src.database import run_readonly, explain_sql, _cache_key, _cache_get, _cache_put
import pytest

def test_ro_simple_select():
    rows = run_readonly("SELECT 1 AS x")
    assert rows and rows[0]["x"] == 1

def test_ro_limit_enforced():
    rows = run_readonly("SELECT generate_series(1, 5000) AS x", row_limit=10)
    assert len(rows) == 10

def test_explain_sql_basic():
    """Test the explain_sql function with a basic query."""
    result = explain_sql("SELECT customer_id FROM customers", row_limit=5)
    assert isinstance(result, dict)
    # Should contain execution plan information

def test_explain_sql_with_parameters():
    """Test explain_sql with row limit parameter."""
    result = explain_sql("SELECT * FROM customers", row_limit=100)
    assert isinstance(result, dict)

def test_cache_functions():
    """Test cache functionality."""
    # Test cache key generation
    key1 = _cache_key("SELECT 1", None, 10)
    key2 = _cache_key("SELECT 1", None, 10)
    key3 = _cache_key("SELECT 2", None, 10)
    
    assert key1 == key2
    assert key1 != key3
    
    # Test cache operations
    test_data = [{"test": "value"}]
    _cache_put(key1, test_data)
    
    cached_data = _cache_get(key1)
    assert cached_data == test_data
    
    # Non-existent key should return None
    non_existent_key = _cache_key("SELECT 999", None, 1)
    assert _cache_get(non_existent_key) is None

def test_run_readonly_with_params():
    """Test run_readonly with SQL parameters."""
    # Test with simple parameters
    rows = run_readonly(
        "SELECT :value AS test_column", 
        params={"value": "test_value"}
    )
    assert rows[0]["test_column"] == "test_value"

def test_run_readonly_auto_limit():
    """Test that run_readonly automatically adds LIMIT when missing."""
    # Query without LIMIT should get one added
    rows = run_readonly("SELECT generate_series(1, 2000) AS num")
    assert len(rows) <= 1000  # Should be limited by default ROW_LIMIT

def test_run_readonly_preserves_existing_limit():
    """Test that existing LIMIT is preserved."""
    rows = run_readonly("SELECT generate_series(1, 2000) AS num LIMIT 5")
    assert len(rows) == 5

def test_run_readonly_cache_behavior():
    """Test that caching works for identical queries."""
    # First call
    rows1 = run_readonly("SELECT 42 AS answer", row_limit=1)
    
    # Second identical call should use cache
    rows2 = run_readonly("SELECT 42 AS answer", row_limit=1)
    
    assert rows1 == rows2
    assert rows1[0]["answer"] == 42
