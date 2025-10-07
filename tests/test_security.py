"""
Security tests for database permissions and readonly user validation.
"""
import pytest
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()
from src.utils import require_env


def test_readonly_user_permissions():
    """
    Test that the readonly user can only perform SELECT operations 
    and cannot perform any write operations (INSERT, UPDATE, DELETE, DDL).
    """
    # Test admin connection first
    admin_url = require_env("DATABASE_URL")
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    
    with admin_engine.connect() as conn:
        admin_user = conn.execute(text("SELECT current_user")).scalar()
        print(f"✅ Admin connected as: {admin_user}")
        
        # Verify we can read from tables as admin
        result = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        assert isinstance(result, int), "Admin should be able to read from customers table"
    
    # Test readonly connection
    readonly_url = require_env("DB_READONLY_URL")
    readonly_engine = create_engine(readonly_url, pool_pre_ping=True)
    
    with readonly_engine.connect() as conn:
        readonly_user = conn.execute(text("SELECT current_user")).scalar()
        print(f"✅ Readonly connected as: {readonly_user}")
        
        # Verify readonly user is different from admin
        assert readonly_user == 'readonly', f"Expected 'readonly' user, got '{readonly_user}'"
        
        # Test that readonly user can SELECT from tables
        result = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        assert isinstance(result, int), "Readonly user should be able to read from customers table"
        
        # Test that readonly user can SELECT from other tables
        tables_to_test = ['products', 'orders', 'categories', 'employees', 'shippers']
        for table in tables_to_test:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                assert isinstance(result, int), f"Readonly user should be able to read from {table} table"
                print(f"✅ Can read from {table}")
            except Exception as e:
                pytest.fail(f"Readonly user cannot read from {table}: {e}")


def test_readonly_user_cannot_write():
    """
    Test that the readonly user cannot perform any write operations.
    """
    readonly_url = require_env("DB_READONLY_URL")
    readonly_engine = create_engine(readonly_url, pool_pre_ping=True)
    
    # Test INSERT is blocked (separate connection to avoid transaction abort)
    with readonly_engine.connect() as conn:
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("INSERT INTO customers (customer_id, company_name) VALUES ('TEST99', 'Test Company')"))
        error_msg = str(exc_info.value).lower()
        assert "permission denied" in error_msg or "access denied" in error_msg or "must be owner" in error_msg
        print("✅ INSERT blocked for readonly user")
    
    # Test UPDATE is blocked (separate connection to avoid transaction abort)
    with readonly_engine.connect() as conn:
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("UPDATE customers SET company_name = 'Updated' WHERE customer_id = 'ALFKI'"))
        error_msg = str(exc_info.value).lower()
        assert "permission denied" in error_msg or "access denied" in error_msg or "must be owner" in error_msg
        print("✅ UPDATE blocked for readonly user")
    
    # Test DELETE is blocked (separate connection to avoid transaction abort)
    with readonly_engine.connect() as conn:
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("DELETE FROM customers WHERE customer_id = 'ALFKI'"))
        error_msg = str(exc_info.value).lower()
        assert "permission denied" in error_msg or "access denied" in error_msg or "must be owner" in error_msg
        print("✅ DELETE blocked for readonly user")


def test_readonly_user_cannot_ddl():
    """
    Test that the readonly user cannot perform DDL operations.
    """
    readonly_url = require_env("DB_READONLY_URL")
    readonly_engine = create_engine(readonly_url, pool_pre_ping=True)
    
    # Test CREATE TABLE is blocked (separate connection to avoid transaction abort)
    with readonly_engine.connect() as conn:
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("CREATE TABLE test_table (id INT)"))
        error_msg = str(exc_info.value).lower()
        assert "permission denied" in error_msg or "access denied" in error_msg or "must be owner" in error_msg
        print("✅ CREATE TABLE blocked for readonly user")
    
    # Test DROP TABLE is blocked (separate connection to avoid transaction abort)
    with readonly_engine.connect() as conn:
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("DROP TABLE IF EXISTS customers"))
        error_msg = str(exc_info.value).lower()
        assert "permission denied" in error_msg or "access denied" in error_msg or "must be owner" in error_msg
        print("✅ DROP TABLE blocked for readonly user")
    
    # Test ALTER TABLE is blocked (separate connection to avoid transaction abort)
    with readonly_engine.connect() as conn:
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("ALTER TABLE customers ADD COLUMN test_col VARCHAR(10)"))
        error_msg = str(exc_info.value).lower()
        assert "permission denied" in error_msg or "access denied" in error_msg or "must be owner" in error_msg
        print("✅ ALTER TABLE blocked for readonly user")


def test_readonly_user_cannot_access_system_tables():
    """
    Test that the readonly user cannot access sensitive system tables.
    """
    readonly_url = require_env("DB_READONLY_URL")
    readonly_engine = create_engine(readonly_url, pool_pre_ping=True)
    
    with readonly_engine.connect() as conn:
        # Test access to pg_user is limited
        try:
            result = conn.execute(text("SELECT * FROM pg_user")).fetchall()
            # If this succeeds, readonly user should not see sensitive info
            for row in result:
                # The readonly user should not see password hashes or admin users
                assert row[0] == 'readonly', f"Readonly user should only see itself, but saw: {row[0]}"
        except Exception:
            # It's also acceptable if access is completely denied
            print("✅ System table access appropriately restricted")
        
        # Test that readonly user cannot view roles with passwords
        with pytest.raises(Exception):
            conn.execute(text("SELECT rolname, rolpassword FROM pg_authid")).fetchall()
        print("✅ Cannot access password information")


def test_database_security_configuration():
    """
    Test overall database security configuration.
    """
    admin_url = require_env("DATABASE_URL")
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    
    with admin_engine.connect() as conn:
        # Verify readonly role exists
        result = conn.execute(text("SELECT COUNT(*) FROM pg_roles WHERE rolname = 'readonly'")).scalar()
        assert result == 1, "Readonly role should exist"
        print("✅ Readonly role exists")
        
        # Verify readonly role has login capability
        result = conn.execute(text("SELECT rolcanlogin FROM pg_roles WHERE rolname = 'readonly'")).scalar()
        assert result is True, "Readonly role should have login capability"
        print("✅ Readonly role can login")
        
        # Verify readonly role is not a superuser
        result = conn.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = 'readonly'")).scalar()
        assert result is False, "Readonly role should not be a superuser"
        print("✅ Readonly role is not superuser")
        
        # Verify readonly role cannot create databases
        result = conn.execute(text("SELECT rolcreatedb FROM pg_roles WHERE rolname = 'readonly'")).scalar()
        assert result is False, "Readonly role should not be able to create databases"
        print("✅ Readonly role cannot create databases")
        
        # Verify readonly role cannot create other roles
        result = conn.execute(text("SELECT rolcreaterole FROM pg_roles WHERE rolname = 'readonly'")).scalar()
        assert result is False, "Readonly role should not be able to create roles"
        print("✅ Readonly role cannot create other roles")


if __name__ == "__main__":
    # Allow running this test file directly for manual testing
    test_readonly_user_permissions()
    test_readonly_user_cannot_write()
    test_readonly_user_cannot_ddl()
    test_readonly_user_cannot_access_system_tables()
    test_database_security_configuration()
    print("🔒 All security tests passed!")
