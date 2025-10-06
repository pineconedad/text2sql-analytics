import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
from src.utils import require_env
url = require_env("DATABASE_URL")
engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    user = conn.execute(text("SELECT current_user")).scalar()
    print("✅ Connected as:", user)
