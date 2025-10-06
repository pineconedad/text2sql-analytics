import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DB_READONLY_URL")
engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    user = conn.execute(text("SELECT current_user")).scalar()
    print("✅ Connected as:", user)
