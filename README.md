# Text2SQL Analytics

Natural-language → SQL for a Postgres (Northwind) dataset, with safety rails:
- **Validator**: SELECT/CTE only, blocks DDL/DML, adds LIMIT.
- **Read-only executor**: enforces timeout + row caps.
- **Model**: Gemini (with an **offline stub** fallback).
- **API**: FastAPI `/ask` endpoint returning JSON rows.

---

## Tech Stack
- Python 3.13, FastAPI, Uvicorn
- SQLAlchemy, psycopg2-binary
- Pandas (CSV → Postgres ETL)
- Docker Compose (Postgres + Adminer + API)
- Pytest (+ coverage), GitHub Actions CI

---

## Quickstart (Local Dev)

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env       # keep localhost URLs in this mode
python scripts/apply_schema.py
python scripts/setup_database.py
python -m uvicorn src.api:app --reload
````

Test the API:

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"top 5 products by revenue","row_limit":5}'
```

Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Quickstart (Docker)

```bash
cp .env.example .env
# In .env, set DB host to "db" for Docker:
# DATABASE_URL=postgresql://postgres:postgres@db:5432/northwind
# DB_READONLY_URL=postgresql://readonly:readonly@db:5432/northwind

docker compose up --build -d
```

Test:

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"top 5 products by revenue","row_limit":5}'
```

Adminer: [http://127.0.0.1:8080](http://127.0.0.1:8080) (System: PostgreSQL; Server: db; User: postgres; Pass: postgres; DB: northwind)

---

## Environment

`.env.example` (copy to `.env`):

```env
# Local dev (Mac terminal):
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/northwind
DB_READONLY_URL=postgresql://readonly:readonly@localhost:5432/northwind

# Docker Compose (API inside container):
# DATABASE_URL=postgresql://postgres:postgres@db:5432/northwind
# DB_READONLY_URL=postgresql://readonly:readonly@db:5432/northwind

# Model config
GEMINI_API_KEY=your_api_key_here
USE_GEMINI_STUB=1              # 1 = offline stub, 0 = real Gemini
GEMINI_MODEL=gemini-1.5-flash-latest

# Safety knobs
QUERY_TIMEOUT_SECONDS=5
ROW_LIMIT=1000
```

Switching to real Gemini:

```env
USE_GEMINI_STUB=0
GEMINI_API_KEY=sk-...
```

---

## Make & Tests

```bash
make test            # uses venv's python -m pytest -q
python -m pytest -q  # same effect
```

CI runs via `.github/workflows/tests.yml` (Postgres service + schema + ETL + tests).

---

## API

### `POST /ask`

Request:

```json
{ "question": "top 5 products by revenue", "row_limit": 5 }
```

Response:

```json
{
  "question": "...",
  "sql": "SELECT ... LIMIT 5",
  "rows": [ { "...": "..." } ]
}
```

Interactive docs: `/docs`

---

## Project Structure

```
.
├── data/
│   ├── raw/              # CSVs (customers, orders, products, etc.)
│   └── schema/schema.sql # Postgres DDL (matches CSVs)
├── scripts/
│   ├── apply_schema.py   # create tables
│   ├── setup_database.py # load CSVs (FK-safe order)
│   └── ...               # helpers/patches
├── src/
│   ├── api.py            # FastAPI app (/ask)
│   ├── database.py       # readonly executor + timeout
│   ├── query_validator.py# SELECT-only, adds LIMIT
│   └── text2sql_engine.py# Gemini (or stub) → SQL
├── tests/                # unit + integration tests
├── docker-compose.yml    # db + adminer + app
├── Dockerfile            # app container
├── requirements.txt
├── Makefile
└── .github/workflows/tests.yml
```

---

## Troubleshooting

* **Pytest uses system Python**: run `python -m pytest -q` (forces venv).
* **API in Docker can’t reach DB**: ensure `.env` uses `@db` host (not `@localhost`).
* **Gemini model error (404/unsupported)**: set `GEMINI_MODEL=gemini-1.5-flash-latest` or `gemini-1.5-flash-001`, restart app.
* **Encoding errors on CSV**: loader falls back to `latin-1`; place CSVs in `data/raw/`.

---

