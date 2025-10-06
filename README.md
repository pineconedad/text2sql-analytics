# Schema Diagram
![Database Schema](schema_diagram.png)

## Test Coverage Report
To generate an HTML coverage report:
```bash
pytest --cov --cov-report=html
```
Open `htmlcov/index.html` in your browser to view detailed coverage results.
# Architecture Diagram
```
┌────────────┐      ┌─────────────┐      ┌─────────────┐
│  FastAPI   │◄────│  Gemini LLM │◄────│  .env/.py   │
│  /ask API  │     │  or Stub    │     │  Config     │
└─────┬──────┘      └─────┬──────┘      └─────┬──────┘
  │                   │                   │
  ▼                   ▼                   ▼
┌────────────┐      ┌─────────────┐      ┌─────────────┐
│ Query      │      │ Query       │      │ Database    │
│ Validator  │      │ Executor    │      │ (Postgres)  │
└────────────┘      └─────────────┘      └─────────────┘
```

## Database Initialization Guide
1. Ensure PostgreSQL is running (locally or via Docker Compose).
2. Run schema setup:
  ```bash
  python scripts/apply_schema.py
  ```
3. Load CSV data:
  ```bash
  python scripts/setup_database.py
  ```
4. (Optional) Create read-only DB role:
  ```bash
  python scripts/create_readonly_role.py
  ```

## API Key Configuration Instructions
1. Copy `.env.example` to `.env`.
2. Add your Gemini API key:
  ```env
  GEMINI_API_KEY=your_api_key_here
  USE_GEMINI_STUB=0
  GEMINI_MODEL=models/gemini-1.5-flash-002
  ```
3. Restart the app to apply changes.

## Accuracy Metrics Results Table
Sample results from heuristic accuracy tests:

| Query                          | Execution | Result Match | Query Quality | Final Score |
|---------------------------------|-----------|--------------|--------------|-------------|
| List all customer names         |    1      |      1       |     0.75     |    0.95     |
| Top 5 customers by sales        |    1      |      1       |     0.80     |    0.98     |
| Monthly sales trend             |    1      |      0       |     0.60     |    0.68     |
| Average order value per customer|    1      |      1       |     0.70     |    0.94     |

See `tests/test_accuracy/` for details.

## Known Limitations & Future Improvements
- LLM accuracy may vary for complex queries; stub fallback is deterministic but limited.
- Query history tracking and dashboard are not yet implemented.
- Performance monitoring is basic; consider adding more analytics.
- More few-shot examples and schema hints can further improve LLM results.
- Add more granular tests for edge cases and data anomalies.
# Text2SQL Analytics

Natural-language → SQL for a Postgres (Northwind) dataset, with safety rails and full test coverage.

## Features & Deliverables
- **Validator**: SELECT/CTE only, blocks DDL/DML, system tables, user management, and transaction control. Adds LIMIT automatically.
- **Read-only executor**: enforces timeout, row caps, and uses SELECT-only DB user.
- **Model**: Gemini LLM (with an offline stub fallback). Prompt includes schema hints and few-shot examples for accuracy.
- **API**: FastAPI `/ask` endpoint returning JSON rows.
- **Heuristic accuracy tests**: Automated tests score SQL output for execution, result match, and query quality.
- **Security**: Strict query validation, no prohibited operations, environment-based config.
- **Bonus**: In-memory query cache, EXPLAIN plan analysis, REST API, CI/CD pipeline.

## Tech Stack
- Python 3.13, FastAPI, Uvicorn
- SQLAlchemy, psycopg2-binary
- Pandas (CSV → Postgres ETL)
- Docker Compose (Postgres + Adminer + API)
- Pytest (+ coverage), GitHub Actions CI

## Quickstart (Local Dev)
```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env       # keep localhost URLs in this mode
python scripts/apply_schema.py
python scripts/setup_database.py
python -m uvicorn src.api:app --reload
```

Test the API:
```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"top 5 products by revenue","row_limit":5}'
```
Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

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

## Make & Tests
```bash
make test            # uses venv's python -m pytest -q
python -m pytest -q  # same effect
```
CI runs via `.github/workflows/tests.yml` (Postgres service + schema + ETL + tests).

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

## Project Structure
```
.
├── data/
│   ├── raw/                # CSVs (customers, orders, products, etc.)
│   └── schema/
│       └── schema.sql      # Postgres DDL (matches CSVs)
├── scripts/
│   ├── apply_schema.py     # create tables
│   ├── setup_database.py   # load CSVs (FK-safe order)
│   └── ...                 # helpers/patches
├── src/
│   ├── api.py              # FastAPI app (/ask)
│   ├── database.py         # readonly executor + timeout
│   ├── query_validator.py  # SELECT-only, adds LIMIT
│   ├── text2sql_engine.py  # Gemini (or stub) → SQL
│   ├── config.py           # environment config
│   ├── utils.py            # helpers
│   └── ...
├── tests/
│   ├── test_excel_loader.py        # data validation tests
│   ├── test_sql_sanitizer.py       # SQL sanitizer tests
│   ├── test_database.py            # DB executor tests
│   ├── test_pipeline.py            # ETL pipeline tests
│   ├── test_text2sql_engine.py     # engine tests
│   ├── test_query_validator.py     # validator tests
│   └── test_accuracy/
│       ├── test_simple_queries.py
│       ├── test_intermediate_queries.py
│       └── test_complex_queries.py
├── docker-compose.yml      # db + adminer + app
├── Dockerfile              # app container
├── requirements.txt
├── Makefile
└── .github/
    └── workflows/
        └── tests.yml
```

## Heuristic Accuracy & Code Quality
- Heuristic tests score SQL output for execution, result match, and query quality (joins, grouping, filtering, indexing, time).
- All code is modular, type-hinted, and documented with docstrings.
- Security and validation are enforced everywhere.

## Troubleshooting
* **Pytest uses system Python**: run `python -m pytest -q` (forces venv).
* **API in Docker can’t reach DB**: ensure `.env` uses `@db` host (not `@localhost`).
* **Gemini model error (404/unsupported)**: set `GEMINI_MODEL=gemini-1.5-flash-latest` or `gemini-1.5-flash-001`, restart app.
* **Encoding errors on CSV**: loader falls back to `latin-1`; place CSVs in `data/raw/`.

