# Always load .env for environment variables
from dotenv import load_dotenv
load_dotenv()
# src/text2sql_engine.py
# src/text2sql_engine.py
"""
Text2SQL Engine: Generates SQL from natural language using Gemini LLM or stub fallback.
"""
import os
from typing import Optional

# Dynamic check for stub mode (evaluated at runtime, not import time)

# You can expand this later or generate from the DB metadata
SCHEMA_HINT = """
Tables:
    customers(customer_id, company_name, contact_name, contact_title, city, country)
    products(product_id, product_name, unit_price, category_id, discontinued)
    orders(order_id, customer_id, employee_id, order_date, shipped_date, shipper_id, freight)
    order_details(order_id, product_id, unit_price, quantity, discount)
    categories(category_id, category_name)
    employees(employee_id, first_name, last_name, title)
    shippers(shipper_id, company_name)
"""

# ---------- STUB: predictable, offline SQL ----------
def _stub_generate(question: str) -> str:
    """
    Generate predictable SQL for offline testing and fallback.
    Args:
        question (str): Natural language question.
    Returns:
        str: SQL query string.
    """
    q = question.lower().strip()
    if "list all customer names" in q or "list customers by name" in q:
        return "SELECT customer_id, company_name FROM customers ORDER BY company_name"
    if "top 5 customers by the total sales amount" in q:
        return "SELECT o.customer_id, SUM(od.unit_price * od.quantity) AS total_sales FROM orders o JOIN order_details od ON o.order_id = od.order_id GROUP BY o.customer_id ORDER BY total_sales DESC LIMIT 5"
    if "monthly sales trend" in q or "total sales amount for each month" in q:
        return "SELECT DATE_TRUNC('month', o.order_date) AS month, SUM(od.unit_price * od.quantity) AS sales FROM orders o JOIN order_details od ON o.order_id = od.order_id WHERE o.order_date >= CURRENT_DATE - INTERVAL '1 year' GROUP BY month ORDER BY month"
    if "top 3 products by quantity sold" in q or "top products by region" in q:
        return "SELECT c.country AS region, p.product_name, SUM(od.quantity) AS sales FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_details od ON o.order_id = od.order_id JOIN products p ON od.product_id = p.product_id GROUP BY region, p.product_name ORDER BY region, sales DESC LIMIT 3"
    if "for each customer, show their company name and the total number of orders" in q or "customer orders" in q:
        return "SELECT c.customer_id, c.company_name, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.company_name"
    if "total number of orders for each country" in q or "orders by country" in q:
        return "SELECT c.country, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.country"
    if "average value of their orders" in q or "average order value per customer" in q:
        return "SELECT c.customer_id, c.company_name, AVG(od.unit_price * od.quantity) AS avg_order_value FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_details od ON o.order_id = od.order_id GROUP BY c.customer_id, c.company_name"
    if "list all company names of customers" in q or ("customers" in q and ("list" in q or "show" in q or "name" in q)):
        return "SELECT company_name FROM customers ORDER BY company_name"
    if "show the names of all products" in q or ("products" in q and ("list" in q or "show" in q or "name" in q)):
        return "SELECT product_name FROM products ORDER BY product_name"
    if "list the order dates for all orders" in q or ("orders" in q and "date" in q):
        return "SELECT order_date FROM orders ORDER BY order_date"
    return "SELECT 1"

def generate_sql(question: str, schema_hint: Optional[str] = None) -> str:
    """
    Generate SQL for a natural-language question using Gemini LLM or stub.
    Args:
        question (str): Natural language question.
        schema_hint (Optional[str]): Optional schema hint for prompt.
    Returns:
        str: SQL query string.
    """
    # Check stub mode dynamically (allows tests to change environment)
    use_stub = os.getenv("USE_GEMINI_STUB", "1") == "1"
    if use_stub:
        return _stub_generate(question)

    # ---------- REAL GEMINI PATH ----------
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key) # type: ignore

    # allow override via .env; default to a widely available alias
    model_name = model_name = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash-002")


    FEW_SHOTS = [
        {"q": "Show all product names.", "sql": "SELECT product_name FROM products ORDER BY product_name"},
        {"q": "Show each customer and their total number of orders.", "sql": "SELECT c.customer_id, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id"},
        {"q": "Show total orders by country.", "sql": "SELECT c.country, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.country"},
        {"q": "What is the average order value per customer?", "sql": "SELECT o.customer_id, AVG(od.unit_price * od.quantity) AS avg_order_value FROM orders o JOIN order_details od ON o.order_id = od.order_id GROUP BY o.customer_id"},
        {"q": "For each customer, show their company name and the total number of orders they have placed.", "sql": "SELECT c.customer_id, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id"},
        {"q": "Show the total number of orders for each country.", "sql": "SELECT c.country, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.country"},
        {"q": "For each customer, show their company name and the average value of their orders.", "sql": "SELECT o.customer_id, AVG(od.unit_price * od.quantity) AS avg_order_value FROM orders o JOIN order_details od ON o.order_id = od.order_id GROUP BY o.customer_id"},
    ]

    schema_hint = schema_hint or SCHEMA_HINT
    examples = "\n\n".join([f"Q: {ex['q']}\nSQL: {ex['sql'].strip()}" for ex in FEW_SHOTS])

    prompt = f"""You are a Text-to-SQL assistant for **PostgreSQL**.

RULES:
- Output ONE statement only, SELECT or WITH…SELECT (no extra text).
- Use only these tables/columns (Postgres names & syntax):
{schema_hint}
- Never write DDL/DML; no INSERT/UPDATE/DELETE/ALTER/TRUNCATE; no pg_catalog/information_schema.
- Prefer explicit JOINs and proper GROUP BY.

Examples:
{examples}

Now answer:
Q: {question}
SQL:
"""

    # try preferred model, then fallbacks; final fallback to stub
    for candidate in (model_name, "models/gemini-1.5-flash", "models/gemini-1.5-flash-001"):

        try:
            model = genai.GenerativeModel(candidate) # type: ignore
            resp = model.generate_content(prompt)
            sql = (resp.text or "").strip().strip("`")
            if sql:
                return sql
        except Exception:
            continue

    # last resort
    return _stub_generate(question)
