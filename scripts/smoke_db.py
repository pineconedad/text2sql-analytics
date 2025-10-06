import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()  # read from .env

url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/northwind")
engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1 AS ok"))
    print("✅ Database connection successful:", result.scalar())
