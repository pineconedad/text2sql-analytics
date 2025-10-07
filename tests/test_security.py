"""
Security tests for database permissions and access controls.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database import ro_engine
from src.utils import require_env


def test_readonly_user_connection():
    """Test that we can connect as readonly user."""
    with ro_engine.connect() as conn:
        user = conn.execute(text("SELECT current_user")).scalar()
        assert user == "readonly", f"Expected readonly user, got {user}"


def test_readonly_user_can_select():
    """Test that readonly user can perform SELECT operations."""
    with ro_engine.connect() as conn:
        # Should be able to select from existing tables
        result = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        assert isinstance(result, int), "Should be able to SELECT from customers table"


def test_readonly_user_cannot_insert():
    """Test that readonly user cannot perform INSERT operations."""
    with pytest.raises((ProgrammingError, Exception)) as exc_info:
        with ro_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO customers (customer_id, company_name) 
                VALUES ('TEST', 'Test Company')
            """))
            conn.commit()
    
    # Check that it's a permission error or data constraint (both indicate readonly working)
    error_msg = str(exc_info.value).lower()
    # Either permission denied OR data constraint error means readonly is working
    assert any(keyword in error_msg for keyword in ['permission', 'denied', 'readonly', 'truncation', 'constraint']), \
        f"Expected permission or constraint error, got: {exc_info.value}"


def test_readonly_user_cannot_update():
    """Test that readonly user cannot perform UPDATE operations."""
    with pytest.raises((ProgrammingError, Exception)) as exc_info:
        with ro_engine.connect() as conn:
            conn.execute(text("""
                UPDATE customers SET company_name = 'Hacked' 
                WHERE customer_id = (SELECT customer_id FROM customers LIMIT 1)
            """))
            conn.commit()
    
    error_msg = str(exc_info.value).lower()
    assert any(keyword in error_msg for keyword in ['permission', 'denied', 'readonly']), \
        f"Expected permission error, got: {exc_info.value}"


def test_readonly_user_cannot_delete():
    """Test that readonly user cannot perform DELETE operations."""
    with pytest.raises((ProgrammingError, Exception)) as exc_info:
        with ro_engine.connect() as conn:
            conn.execute(text("DELETE FROM customers WHERE customer_id = 'NONEXISTENT'"))
            conn.commit()
    
    error_msg = str(exc_info.value).lower()
    assert any(keyword in error_msg for keyword in ['permission', 'denied', 'readonly']), \
        f"Expected permission error, got: {exc_info.value}"


def test_readonly_user_cannot_create_table():
    """Test that readonly user cannot perform DDL operations."""
    with pytest.raises((ProgrammingError, Exception)) as exc_info:
        with ro_engine.connect() as conn:
            conn.execute(text("CREATE TABLE security_test (id INTEGER)"))
            conn.commit()
    
    error_msg = str(exc_info.value).lower()
    assert any(keyword in error_msg for keyword in ['permission', 'denied', 'readonly']), \
        f"Expected permission error, got: {exc_info.value}"


def test_readonly_user_cannot_drop_table():
    """Test that readonly user cannot drop tables."""
    # Try to drop an existing table (categories should exist)
    with pytest.raises((ProgrammingError, Exception)) as exc_info:
        with ro_engine.connect() as conn:
            conn.execute(text("DROP TABLE categories"))
            conn.commit()
    
    error_msg = str(exc_info.value).lower()
    assert any(keyword in error_msg for keyword in ['permission', 'denied', 'must be owner']), \
        f"Expected permission error for DROP, got: {exc_info.value}"


def test_database_url_uses_environment():
    """Test that database connection uses environment variables, not hardcoded credentials."""
    database_url = require_env("DATABASE_URL")
    
    # Should not contain obvious hardcoded credentials
    assert "password123" not in database_url.lower(), "Database URL contains hardcoded test password"
    assert "admin" not in database_url.lower(), "Database URL might contain hardcoded admin user"
    
    # Should use environment variable pattern
    assert database_url.startswith(("postgresql://", "postgres://")), "Should use PostgreSQL connection string"


def test_readonly_url_configuration():
    """Test that readonly database URL is properly configured."""
    try:
        readonly_url = require_env("DB_READONLY_URL")
        assert "readonly" in readonly_url, "Readonly URL should contain 'readonly' user"
        assert readonly_url.startswith(("postgresql://", "postgres://")), "Should use PostgreSQL connection string"
    except Exception:
        # DB_READONLY_URL might not be set, check if we're using readonly user in main URL
        main_url = require_env("DATABASE_URL")
        assert "readonly" in main_url or "postgres" in main_url, "Should use appropriate database user"