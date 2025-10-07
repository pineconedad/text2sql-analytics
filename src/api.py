from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.text2sql_engine import generate_sql
from src.query_validator import sanitize_select
from src.database import run_readonly
from typing import Optional
import time
from datetime import datetime, timezone

app = FastAPI(
    title="Text2SQL Analytics API",
    description="Convert natural language questions to SQL queries and execute them",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "Text2SQL Analytics API", 
        "version": "1.0.0",
        "endpoints": ["/health", "/ask", "/explain"]
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

class AskBody(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question to convert to SQL")
    row_limit: int | None = Field(None, ge=1, le=10000, description="Maximum number of rows to return (1-10000)")

@app.post("/ask")
def ask(body: AskBody):
    try:
        start_time = time.time()
        
        sql = generate_sql(body.question)
        safe_sql = sanitize_select(sql, row_limit=body.row_limit or 1000)
        rows = run_readonly(safe_sql, row_limit=body.row_limit or 1000)
        
        execution_time_ms = round((time.time() - start_time) * 1000, 2)
        
        return {
            "question": body.question,
            "sql": safe_sql,
            "rows": rows,
            "execution_time_ms": execution_time_ms,
            "row_count": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class ExplainBody(BaseModel):
    sql: str = Field(..., min_length=1, description="SQL query to explain")
    row_limit: Optional[int] = Field(50, ge=1, le=1000, description="Row limit for explain query")

@app.post("/explain")
def explain(body: ExplainBody):
    try:
        from src.database import explain_sql
        result = explain_sql(body.sql, row_limit=body.row_limit or 50)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

