# src/text2sql_engine.py
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
"""

# ---------- STUB: predictable, offline SQL ----------
def _stub_generate(question: str) -> str:
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
    """Return SQL for a natural-language question. Uses STUB by default."""
    if USE_STUB:
        return _stub_generate(question)

    # ---------- REAL GEMINI PATH ----------
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)

    # allow override via .env; default to a widely available alias
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")

    FEW_SHOTS = [
        {
            "q": "list customers by name",
            "sql": "SELECT customer_id, company_name FROM customers ORDER BY company_name"
        },
        {
            "q": "top 5 products by revenue",
            "sql": """
            SELECT p.product_id, p.product_name, SUM(od.quantity * od.unit_price) AS revenue
            FROM order_details od
            JOIN products p ON p.product_id = od.product_id
            GROUP BY p.product_id, p.product_name
            ORDER BY revenue DESC
            LIMIT 5
            """
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
    for candidate in (model_name, "gemini-1.5-flash-001", "gemini-1.5-flash"):
        try:
            model = genai.GenerativeModel(candidate)
            resp = model.generate_content(prompt)
            sql = (resp.text or "").strip().strip("`")
            if sql:
                return sql
        except Exception:
            continue

    # last resort
    return _stub_generate(question)
