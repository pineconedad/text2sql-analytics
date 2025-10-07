"""
Additional database tests to improve coverage.
"""
import pytest
from src.database import run_readonly, explain_sql, _cache_get, _cache_put, _cache_key
import time


def test_database_caching():
    """Test that the database caching system works correctly."""
    # Clear any existing cache first by running a unique query
    sql1 = "SELECT 12345 AS unique_test_value"
    sql2 = "SELECT 67890 AS another_unique_value"
    
    # First call should hit the database
    start_time = time.time()
    result1 = run_readonly(sql1, row_limit=10)
    first_call_time = time.time() - start_time
    
    # Second call should hit the cache (should be faster)
    start_time = time.time()
    result2 = run_readonly(sql1, row_limit=10)
    second_call_time = time.time() - start_time
    
    # Results should be identical
    assert result1 == result2
    assert result1[0]["unique_test_value"] == 12345
    
    # Different query should not hit cache
    result3 = run_readonly(sql2, row_limit=10)
    assert result3[0]["another_unique_value"] == 67890


def test_database_cache_key_generation():
    """Test cache key generation for different parameters."""
    key1 = _cache_key("SELECT 1", None, 100)
    key2 = _cache_key("SELECT 1", None, 100)
    key3 = _cache_key("SELECT 1", None, 200)
    key4 = _cache_key("SELECT 1", {"param": "value"}, 100)
    
    # Same parameters should generate same key
    assert key1 == key2
    
    # Different parameters should generate different keys
    assert key1 != key3  # Different row_limit
    assert key1 != key4  # Different params


def test_database_cache_operations():
    """Test direct cache operations."""
    test_key = ("test_sql", "test_params", 100)
    test_data = [{"test": "data"}]
    
    # Initially should return None
    assert _cache_get(test_key) is None
    
    # After putting data, should return it
    _cache_put(test_key, test_data)
    cached_result = _cache_get(test_key)
    assert cached_result == test_data


def test_explain_sql():
    """Test SQL explain functionality."""
    sql = "SELECT customer_id, company_name FROM customers LIMIT 5"
    
    explain_result = explain_sql(sql)
    
    assert isinstance(explain_result, dict)
    assert "plan" in explain_result
    assert "execution_time_ms" in explain_result
    assert explain_result["execution_time_ms"] >= 0


def test_run_readonly_with_params():
    """Test run_readonly with parameters."""
    # Test with simple parameterized query
    sql = "SELECT :test_param as param_value"
    params = {"test_param": "hello_world"}
    
    result = run_readonly(sql, params=params, row_limit=1)
    
    assert len(result) == 1
    assert result[0]["param_value"] == "hello_world"


def test_run_readonly_limit_wrapping():
    """Test that row_limit properly wraps queries."""
    # This query would return many rows without limit
    sql = "SELECT generate_series(1, 100) AS number"
    
    result = run_readonly(sql, row_limit=5)
    
    assert len(result) == 5
    assert result[0]["number"] == 1
    assert result[4]["number"] == 5


def test_run_readonly_existing_limit_preserved():
    """Test that existing LIMIT in query is preserved."""
    sql = "SELECT generate_series(1, 100) AS number LIMIT 3"
    
    # Even with row_limit=10, should respect the existing LIMIT 3
    result = run_readonly(sql, row_limit=10)
    
    assert len(result) == 3


def test_run_readonly_no_limit_adds_default():
    """Test that queries without limit get default limit added."""
    sql = "SELECT 1 AS test_value"
    
    # Should add default limit from ROW_LIMIT config
    result = run_readonly(sql)
    
    assert len(result) == 1
    assert result[0]["test_value"] == 1


def test_database_connection_reuse():
    """Test that multiple queries work correctly (connection pooling)."""
    queries = [
        "SELECT 1 AS first",
        "SELECT 2 AS second", 
        "SELECT 3 AS third"
    ]
    
    results = []
    for sql in queries:
        result = run_readonly(sql, row_limit=1)
        results.append(result[0])
    
    assert results[0]["first"] == 1
    assert results[1]["second"] == 2
    assert results[2]["third"] == 3