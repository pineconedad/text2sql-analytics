"""
Pytest configuration and fixtures for database setup/teardown.
"""
import pytest
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()
from src.utils import require_env

@pytest.fixture(scope="session")
def test_engine():
    """
    Create a test database engine for the entire test session.
    Uses the same database as the main app but ensures clean state.
    """
    url = require_env("DATABASE_URL")
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def clean_database(test_engine):
    """
    Clean database state before each test function.
    Truncates all tables to ensure isolated test runs.
    """
    # Clean up before test
    with test_engine.begin() as conn:
        # Truncate in reverse dependency order to avoid FK violations
        tables = ["order_details", "orders", "products", "employees", "customers", "categories", "shippers"]
        for table in tables:
            conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
    
    yield test_engine
    
    # Clean up after test (optional, but good practice)
    with test_engine.begin() as conn:
        tables = ["order_details", "orders", "products", "employees", "customers", "categories", "shippers"]
        for table in tables:
            conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))

@pytest.fixture(scope="function")
def sample_data(clean_database):
    """
    Insert minimal sample data for tests that need actual data.
    """
    engine = clean_database
    
    with engine.begin() as conn:
        # Insert sample categories
        conn.execute(text("""
            INSERT INTO categories (category_id, category_name, description) VALUES
            (1, 'Test Category', 'Test Description')
        """))
        
        # Insert sample customers
        conn.execute(text("""
            INSERT INTO customers (customer_id, company_name, contact_name, city, country) VALUES
            ('TEST1', 'Test Company', 'Test Contact', 'Test City', 'Test Country')
        """))
        
        # Insert sample employees
        conn.execute(text("""
            INSERT INTO employees (employee_id, employee_name, title, city, country) VALUES
            (1, 'Test Employee', 'Test Title', 'Test City', 'Test Country')
        """))
        
        # Insert sample shippers
        conn.execute(text("""
            INSERT INTO shippers (shipper_id, company_name) VALUES
            (1, 'Test Shipper')
        """))
        
        # Insert sample products
        conn.execute(text("""
            INSERT INTO products (product_id, product_name, unit_price, category_id) VALUES
            (1, 'Test Product', 10.00, 1)
        """))
        
        # Insert sample orders
        conn.execute(text("""
            INSERT INTO orders (order_id, customer_id, employee_id, shipper_id, freight) VALUES
            (1, 'TEST1', 1, 1, 5.00)
        """))
        
        # Insert sample order details
        conn.execute(text("""
            INSERT INTO order_details (order_id, product_id, unit_price, quantity, discount) VALUES
            (1, 1, 10.00, 2, 0.0)
        """))
    
    yield engine