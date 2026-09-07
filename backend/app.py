"""Round Table FastAPI backend.

Serves the Round Table research-query frontend. The SQLite file lives
in the sibling ./db directory; CORS is wide-open in dev so the
frontend (and static files) can communicate seamlessly.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from google_search import search_google
from db import (
    create_query,
    init_db,
    list_queries,
    update_moderator_analysis,
    update_results,
    update_round_table_responses,
    update_search_results,
)
from open_claw import generate_documents
from round_table import run_round_table

# Load environment variables from .env before initializing
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Make sure the schema exists before the first request lands."""
    init_db()
    yield


app = FastAPI(title="Round Table API", lifespan=lifespan)

# Permissive CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for UI
UI_DIR = Path(__file__).resolve().parent.parent / "UI"
if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


class QueryRequest(BaseModel):
    """Body for POST /query."""

    user_input: str


class QueryResponse(BaseModel):
    """Response for POST /query.

    `query_id` lets the frontend correlate this submission with a row
    in /history. Full search_results are returned via /history to keep
    the response payload small.
    """

    query_id: int
    document_1: str
    document_2: str


@app.get("/")
def read_index():
    """Serve the main frontend UI at the root path."""
    index_path = UI_DIR / "code.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "ok", "message": "Round Table API is running."}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — returns 200 + {"status": "ok"} as long as process is up."""
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
async def submit_query(body: QueryRequest) -> QueryResponse:
    """Log submission, run web research, run 3 LLM seats, synthesize, and store.

    Persists before processing so partial failures still produce a record in /history.
    """
    query = body.user_input.strip()
    if not query:
        raise HTTPException(status_code=400, detail="user_input must not be empty")

    query_id = create_query(query)
    results = {"search_results": search_google(query)}
    update_search_results(query_id, results.get("search_results", []))

    seats = await run_round_table(query, results)
    update_round_table_responses(query_id, seats)

    docs = await generate_documents(
        query=query,
        research_context=results,
        round_table_responses=seats,
    )
    update_moderator_analysis(query_id, docs.get("moderator_analysis", ""))
    update_results(query_id, docs["document_1"], docs["document_2"])

    return QueryResponse(
        query_id=query_id,
        document_1=docs["document_1"],
        document_2=docs["document_2"],
    )


@app.get("/history")
def history(limit: int = 100) -> list[dict]:
    """Past queries, most recent first."""
    return list_queries(limit=limit)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
