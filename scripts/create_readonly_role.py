from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

SQL = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly') THEN
    CREATE ROLE readonly LOGIN PASSWORD 'readonly';
  END IF;
END$$;

GRANT CONNECT ON DATABASE northwind TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
-- any future tables get SELECT by default
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;
"""

with engine.begin() as c:
    c.execute(text(SQL))

print("✅ Readonly role created/granted.")
