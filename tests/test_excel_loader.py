import pytest
from src.data_loader import load_csv

def test_load_valid_excel_file():
    df = load_csv('data/raw/customers.csv')
    assert not df.empty
    assert set(['customerID', 'companyName']).issubset(df.columns)

def test_handle_missing_values():
    df = load_csv('data/raw/customers.csv')
    # Simulate missing values check
    missing = df.isnull().sum().sum()
    assert missing == 0  # No missing values expected in sample

def test_data_type_validation():
    df = load_csv('data/raw/customers.csv')
    # Check that customerID is string, companyName is string
    assert df['customerID'].dtype == object
    assert df['companyName'].dtype == object

def test_foreign_key_detection():
    # For demo, just check that customerID is unique (simulates FK integrity)
    df = load_csv('data/raw/customers.csv')
    assert df['customerID'].is_unique

def test_duplicate_row_detection():
    df = load_csv('data/raw/customers.csv')
    # Check for duplicate rows
    duplicates = df.duplicated().sum()
    assert duplicates == 0  # No duplicates expected in sample
