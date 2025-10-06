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

USE_STUB = os.getenv("USE_GEMINI_STUB", "1") == "1"  # default: stub ON

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
    if "customers" in q and ("list" in q or "show" in q or "name" in q):
        return "SELECT customer_id, company_name FROM customers ORDER BY company_name"
    if "top" in q and "products" in q and "revenue" in q:
        return """
        SELECT p.product_id, p.product_name, SUM(od.quantity * od.unit_price) AS revenue
        FROM order_details od
        JOIN products p ON p.product_id = od.product_id
        GROUP BY p.product_id, p.product_name
        ORDER BY revenue DESC
        """
    if "orders" in q and "count" in q:
        return "SELECT COUNT(*) AS order_count FROM orders"
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
    if USE_STUB:
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
        {
            "q": "List all customer names.",
            "sql": "SELECT company_name FROM customers ORDER BY company_name"
        },
        {
            "q": "Show all product names.",
            "sql": "SELECT product_name FROM products ORDER BY product_name"
        },
        {
            "q": "List all order dates.",
            "sql": "SELECT order_date FROM orders ORDER BY order_date"
        },
        {
            "q": "Show each customer and their total number of orders.",
            "sql": "SELECT c.customer_id, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id"
        },
        {
            "q": "Show total orders by country.",
            "sql": "SELECT c.country, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.country"
        },
        {
            "q": "What is the average order value per customer?",
            "sql": "SELECT o.customer_id, AVG(od.unit_price * od.quantity) AS avg_order_value FROM orders o JOIN order_details od ON o.order_id = od.order_id GROUP BY o.customer_id"
        },
        {
            "q": "Find the top 5 customers by total sales amount.",
            "sql": "SELECT o.customer_id, SUM(od.unit_price * od.quantity) AS total_sales FROM orders o JOIN order_details od ON o.order_id = od.order_id GROUP BY o.customer_id ORDER BY total_sales DESC LIMIT 5"
        },
        {
            "q": "Show monthly sales trend for the last year.",
            "sql": "SELECT DATE_TRUNC('month', o.order_date) AS month, SUM(od.unit_price * od.quantity) AS sales FROM orders o JOIN order_details od ON o.order_id = od.order_id WHERE o.order_date >= CURRENT_DATE - INTERVAL '1 year' GROUP BY month ORDER BY month"
        },
        {
            "q": "Find top 3 products sold in each region.",
            "sql": "SELECT c.country AS region, p.product_name, SUM(od.quantity) AS sales FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_details od ON o.order_id = od.order_id JOIN products p ON od.product_id = p.product_id GROUP BY region, p.product_name ORDER BY region, sales DESC LIMIT 3"
        },
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
