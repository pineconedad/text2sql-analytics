from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.text2sql_engine import generate_sql
from src.query_validator import sanitize_select
from src.database import run_readonly
from typing import Optional

app = FastAPI(title="Text2SQL Analytics")

@app.get("/health")
def health():
    return {"ok": True}

class AskBody(BaseModel):
    question: str
    row_limit: int | None = 20

@app.post("/ask")
def ask(body: AskBody):
    try:
        sql = generate_sql(body.question)
        safe_sql = sanitize_select(sql, row_limit=body.row_limit or 20)
        rows = run_readonly(safe_sql, row_limit=body.row_limit or 20)
        return {"question": body.question, "sql": safe_sql, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    


class ExplainBody(BaseModel):
    sql: str
    row_limit: Optional[int] = 50

@app.post("/explain")
def explain(body: ExplainBody):
    try:
        from src.database import explain_sql
        out = explain_sql(body.sql, row_limit=body.row_limit or 50)
        return out
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

