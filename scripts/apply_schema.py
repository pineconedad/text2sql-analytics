from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os, pathlib

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
schema_path = pathlib.Path("data/schema/schema.sql").read_text()

with engine.begin() as c:
    c.execute(text(schema_path))

print("✅ Schema applied.")
