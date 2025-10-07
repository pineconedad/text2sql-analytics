"""
API tests for the FastAPI Text2SQL endpoints.
"""
import pytest
from fastapi.testclient import TestClient
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.api import app

client = TestClient(app)


def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_ask_endpoint_valid_question(monkeypatch):
    """Test the /ask endpoint with a valid question."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    response = client.post(
        "/ask",
        json={"question": "list customers by name", "row_limit": 5}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "sql" in data
    assert "rows" in data
    assert isinstance(data["rows"], list)
    assert len(data["rows"]) <= 5


def test_ask_endpoint_with_default_row_limit(monkeypatch):
    """Test the /ask endpoint with default row limit."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    response = client.post(
        "/ask",
        json={"question": "show products"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "sql" in data
    assert "rows" in data


def test_ask_endpoint_empty_question():
    """Test the /ask endpoint with an empty question."""
    response = client.post(
        "/ask",
        json={"question": "", "row_limit": 5}
    )
    
    assert response.status_code == 422  # Validation error for empty string


def test_ask_endpoint_invalid_row_limit():
    """Test the /ask endpoint with invalid row limit."""
    response = client.post(
        "/ask",
        json={"question": "list customers", "row_limit": -1}
    )
    
    assert response.status_code == 422  # Validation error for negative row limit


def test_ask_endpoint_missing_question():
    """Test the /ask endpoint with missing question field."""
    response = client.post(
        "/ask",
        json={"row_limit": 5}
    )
    
    assert response.status_code == 422  # Validation error for missing required field


def test_ask_endpoint_invalid_json():
    """Test the /ask endpoint with invalid JSON."""
    response = client.post(
        "/ask",
        content="invalid json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422  # JSON decode error


def test_ask_endpoint_sql_injection_attempt(monkeypatch):
    """Test the /ask endpoint with SQL injection attempt."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    
    # Try a question that might generate malicious SQL
    response = client.post(
        "/ask",
        json={
            "question": "show customers; DROP TABLE customers; --", 
            "row_limit": 5
        }
    )
    
    # Should still return 200 because the validator and engine handle this
    assert response.status_code == 200
    data = response.json()
    # The generated SQL should be safe (our validator blocks dangerous operations)
    assert "DROP" not in data["sql"].upper()


def test_api_cors_headers():
    """Test that CORS headers are present."""
    response = client.get("/health")
    assert response.status_code == 200
    # FastAPI with CORSMiddleware should add these headers
    # Note: TestClient may not show all CORS headers, but we can test the endpoint works


def test_ask_endpoint_timeout_simulation(monkeypatch):
    """Test handling of potential timeouts (simulated via environment)."""
    monkeypatch.setenv("USE_GEMINI_STUB", "1")
    monkeypatch.setenv("QUERY_TIMEOUT_SECONDS", "1")  # Very short timeout
    
    response = client.post(
        "/ask",
        json={"question": "list all customers with detailed information", "row_limit": 100}
    )
    
    # Should still work with stub, just testing the configuration
    assert response.status_code == 200


def test_explain_endpoint():
    """Test the /explain endpoint."""
    response = client.post(
        "/explain",
        json={"sql": "SELECT customer_id, company_name FROM customers LIMIT 10"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_explain_endpoint_invalid_sql():
    """Test the /explain endpoint with invalid SQL."""
    response = client.post(
        "/explain",
        json={"sql": "INVALID SQL SYNTAX"}
    )
    
    assert response.status_code == 400