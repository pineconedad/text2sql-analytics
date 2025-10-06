from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
e = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

SQL = """
-- if orders has ship_via but not shipper_id: rename
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='orders' AND column_name='ship_via'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='orders' AND column_name='shipper_id'
  ) THEN
    EXECUTE 'ALTER TABLE public.orders RENAME COLUMN ship_via TO shipper_id';
  END IF;
END$$;

-- if still no shipper_id at all, add it
ALTER TABLE public.orders
  ADD COLUMN IF NOT EXISTS shipper_id INTEGER;

-- ensure shippers table exists (FK target); create minimal if missing
CREATE TABLE IF NOT EXISTS public.shippers (
  shipper_id   INTEGER PRIMARY KEY,
  company_name VARCHAR(100) NOT NULL
);

-- add FK (if not already present)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema='public' AND table_name='orders'
      AND constraint_type='FOREIGN KEY' AND constraint_name='orders_shipper_id_fkey'
  ) THEN
    ALTER TABLE public.orders
      ADD CONSTRAINT orders_shipper_id_fkey
      FOREIGN KEY (shipper_id) REFERENCES public.shippers(shipper_id)
      ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
END$$;
"""

with e.begin() as c:
  c.execute(text(SQL))

print("✅ Patched orders.shipper_id & FK (if needed).")
