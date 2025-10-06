# scripts/setup_database.py
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path
import os, pathlib

load_dotenv()
from src.utils import require_env
url = require_env("DATABASE_URL")
engine = create_engine(url, pool_pre_ping=True)

# ---------- helpers ----------
def read_csv_safe(path: str) -> pd.DataFrame:
    p = Path(path)
    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(p, encoding="latin-1")

def apply_mapping_ci(df: pd.DataFrame, mapping_lower: dict) -> pd.DataFrame:
    """
    Case-insensitive column renaming:
    mapping_lower keys must be lowercase; values are desired names.
    """
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in mapping_lower:
            rename_map[col] = mapping_lower[key]
        else:
            # fallback: normalize spaces -> underscores
            rename_map[col] = key.replace(" ", "_")
    return df.rename(columns=rename_map)

def to_bool_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().map(
        {"1": True, "true": True, "t": True, "yes": True, "y": True, "0": False, "false": False, "f": False, "no": False, "n": False}
    ).fillna(False)

# ---------- 0) apply schema ----------
schema_sql = pathlib.Path("data/schema/schema.sql").read_text()
with engine.begin() as c:
    c.execute(text(schema_sql))

# Optional: clean tables to avoid duplicates on re-run
with engine.begin() as c:
    for t in ["order_details", "orders", "products", "shippers", "employees", "customers", "categories"]:
        c.execute(text(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE'))

# ---------- 1) lookup tables ----------
cats = read_csv_safe("data/raw/categories.csv")
cats = apply_mapping_ci(cats, {
    "categoryid": "category_id",
    "categoryname": "category_name",
    "description": "description",
})
cats = cats[["category_id","category_name","description"]]
cats.to_sql("categories", engine, if_exists="append", index=False, method="multi", chunksize=1000)

ships = read_csv_safe("data/raw/shippers.csv")
ships = apply_mapping_ci(ships, {
    "shipperid": "shipper_id",
    "companyname": "company_name",
})
ships = ships[["shipper_id","company_name"]]
ships.to_sql("shippers", engine, if_exists="append", index=False, method="multi", chunksize=1000)

# ---------- 2) core entities ----------
cust = read_csv_safe("data/raw/customers.csv")
cust = apply_mapping_ci(cust, {
    "customerid": "customer_id",
    "companyname": "company_name",
    "contactname": "contact_name",
    "contacttitle": "contact_title",
    "city": "city",
    "country": "country",
})
cust = cust[["customer_id","company_name","contact_name","contact_title","city","country"]]
cust["customer_id"] = cust["customer_id"].astype(str)
cust.to_sql("customers", engine, if_exists="append", index=False, method="multi", chunksize=1000)

emps = read_csv_safe("data/raw/employees.csv")
emps = apply_mapping_ci(emps, {
    "employeeid": "employee_id",
    "employeename": "employee_name",
    "title": "title",
    "city": "city",
    "country": "country",
    "reportsto": "reports_to",
})
emps = emps[["employee_id","employee_name","title","city","country","reports_to"]]
emps.to_sql("employees", engine, if_exists="append", index=False, method="multi", chunksize=1000)

prods = read_csv_safe("data/raw/products.csv")
prods = apply_mapping_ci(prods, {
    "productid": "product_id",
    "productname": "product_name",
    "quantityperunit": "quantity_per_unit",
    "unitprice": "unit_price",
    "discontinued": "discontinued",
    "categoryid": "category_id",
})
prods = prods[["product_id","product_name","quantity_per_unit","unit_price","discontinued","category_id"]]
prods["unit_price"] = pd.to_numeric(prods["unit_price"], errors="coerce").fillna(0)
if "discontinued" in prods.columns:
    prods["discontinued"] = to_bool_series(prods["discontinued"])
prods.to_sql("products", engine, if_exists="append", index=False, method="multi", chunksize=1000)

# ---------- 3) orders + lines ----------
orders = read_csv_safe("data/raw/orders.csv")
orders = apply_mapping_ci(orders, {
    "orderid": "order_id",
    "customerid": "customer_id",
    "employeeid": "employee_id",
    "orderdate": "order_date",
    "requireddate": "required_date",
    "shippeddate": "shipped_date",
    "shipperid": "shipper_id",
    "freight": "freight",
})
orders = orders[["order_id","customer_id","employee_id","order_date","required_date","shipped_date","shipper_id","freight"]]
for col in ["order_date","required_date","shipped_date"]:
    orders[col] = pd.to_datetime(orders[col], errors="coerce").dt.date
orders["freight"] = pd.to_numeric(orders["freight"], errors="coerce").fillna(0)
orders.to_sql("orders", engine, if_exists="append", index=False, method="multi", chunksize=1000)

lines = read_csv_safe("data/raw/order_details.csv")
lines = apply_mapping_ci(lines, {
    "orderid": "order_id",
    "productid": "product_id",
    "unitprice": "unit_price",
    "quantity": "quantity",
    "discount": "discount",
})
lines = lines[["order_id","product_id","unit_price","quantity","discount"]]
for col in ["unit_price","discount"]:
    lines[col] = pd.to_numeric(lines[col], errors="coerce").fillna(0)
lines["quantity"] = pd.to_numeric(lines["quantity"], errors="coerce").fillna(0).astype(int)
lines.to_sql("order_details", engine, if_exists="append", index=False, method="multi", chunksize=1000)

print("✅ Loaded: categories, shippers, customers, employees, products, orders, order_details")
