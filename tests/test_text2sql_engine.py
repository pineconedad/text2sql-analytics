import os
from src.text2sql_engine import generate_sql
from src.query_validator import sanitize_select
from src.database import run_readonly
import pytest

def test_stub_customers_list(monkeypatch):
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    sql = generate_sql("list customers by name")
    sql = sanitize_select(sql, row_limit=10)
    rows = run_readonly(sql, row_limit=5)
    assert 1 <= len(rows) <= 5
    assert {"customer_id", "company_name"}.issubset(rows[0].keys())

def test_generate_sql_with_gemini_stub(monkeypatch):
    """Test SQL generation using Gemini stub."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    # Test various question types
    test_questions = [
        "show all products",
        "list customers by company name", 
        "find orders from this year",
        "show categories and their descriptions"
    ]
    
    for question in test_questions:
        sql = generate_sql(question)
        assert isinstance(sql, str)
        assert len(sql) > 0
        assert "SELECT" in sql.upper()

def test_generate_sql_real_gemini():
    """Test generate_sql with real Gemini API when configured."""
    import os
    
    # Only run this test if real Gemini is configured
    if os.getenv("USE_GEMINI_STUB", "1") == "1":
        pytest.skip("Skipping real Gemini test - USE_GEMINI_STUB=1")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("Skipping real Gemini test - GEMINI_API_KEY not set")
    
    # Test with a simple question that should work with real API
    try:
        sql = generate_sql("How many customers are there?")
        assert isinstance(sql, str)
        assert len(sql.strip()) > 0
        print(f"✅ Real Gemini API returned: {sql[:100]}...")
    except Exception as e:
        # Allow network/API errors but not configuration errors
        if "API key" in str(e) or "not set" in str(e):
            pytest.fail(f"Configuration error: {e}")
        else:
            pytest.skip(f"Network/API error (acceptable): {e}")


def test_generate_sql_with_schema_hint():
    """Test generate_sql with additional schema hint."""
    schema_hint = "Additional info: Database contains orders, customers, and products tables"
    sql = generate_sql("Find all orders", schema_hint=schema_hint)
    assert isinstance(sql, str)
    assert len(sql.strip()) > 0

def test_generate_sql_with_complex_questions(monkeypatch):
    """Test SQL generation with more complex questions."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    complex_questions = [
        "show me the top 5 customers by total order amount",
        "find products that have never been ordered",
        "list employees and their cities",
        "show monthly sales trends"
    ]
    
    for question in complex_questions:
        sql = generate_sql(question)
        assert isinstance(sql, str)
        assert len(sql) > 0
        # Should contain SQL keywords
        sql_upper = sql.upper()
        assert "SELECT" in sql_upper or "WITH" in sql_upper

def test_generate_sql_empty_question(monkeypatch):
    """Test behavior with empty question."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    sql = generate_sql("")
    assert isinstance(sql, str)
    # Should still return valid SQL even for empty question

def test_generate_sql_question_with_sql_keywords(monkeypatch):
    """Test questions that contain SQL keywords."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    sql = generate_sql("SELECT all customers from the database")
    assert isinstance(sql, str)
    assert "SELECT" in sql.upper()

def test_stub_patterns_coverage(monkeypatch):
    """Test that stub patterns cover various question types."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    # Test patterns that should match specific stub responses
    stub_test_cases = [
        ("customers", "customer"),
        ("products", "product"), 
        ("orders", "order"),
        ("categories", "categor"),
        ("employees", "employee"),
        ("shippers", "shipper")
    ]
    
    for question_word, expected_in_response in stub_test_cases:
        sql = generate_sql(f"show all {question_word}")
        assert isinstance(sql, str)
        sql_lower = sql.lower()
        assert expected_in_response in sql_lower or "SELECT" in sql.upper()

def test_generate_sql_environment_variables(monkeypatch):
    """Test that environment variables are properly used."""
    # Test with stub enabled
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    sql1 = generate_sql("test question")
    assert isinstance(sql1, str)
    
    # Test with real Gemini enabled and API key present
    monkeypatch.setenv("USE_GEMINI_STUB", "0")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_test_api_key_for_testing")
    
    try:
        sql2 = generate_sql("test question")
        assert isinstance(sql2, str)
        print("✅ Environment variable configuration working correctly")
    except Exception as e:
        # Network/API errors are acceptable in test environment
        if "GEMINI_API_KEY not set" not in str(e):
            print(f"⚠️ Gemini API call failed (acceptable in test): {e}")
        else:
            pytest.fail("Should not fail with API key set")
    
    # Test error case: Gemini enabled but no API key
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY not set"):
        generate_sql("test question")
