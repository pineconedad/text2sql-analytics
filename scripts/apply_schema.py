from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os, pathlib

from src.utils import require_env

load_dotenv()
url = require_env("DATABASE_URL")
engine = create_engine(url, pool_pre_ping=True)
schema_path = pathlib.Path("data/schema/schema.sql").read_text()

with engine.begin() as c:
    c.execute(text(schema_path))

print("✅ Schema applied.")
