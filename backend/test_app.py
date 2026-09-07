"""Test suite for Round Table backend and modules.

Covers database operations, API routes (/health, /history, /query),
Tavily search wrapper fallback, and open_claw marker parser robustness.
"""
from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from app import app
from db import create_query, get_conn, init_db, list_queries, update_results, update_search_results
from google_search import search_google
from open_claw import _fallback, _parse_combined


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initialize DB schema before each test."""
    init_db()


def test_health_endpoint():
    """Verify GET /health returns status ok."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_lifecycle():
    """Verify SQLite CRUD helpers."""
    qid = create_query("Test query for unit test")
    assert isinstance(qid, int) and qid > 0

    update_search_results(qid, [{"title": "Test", "snippet": "Snippet", "link": "http://test.com"}])
    update_results(qid, "Doc 1 content", "Doc 2 content")

    queries = list_queries(limit=10)
    matching = [q for q in queries if q["id"] == qid]
    assert len(matching) == 1
    row = matching[0]
    assert row["user_input"] == "Test query for unit test"
    assert row["final_document_1"] == "Doc 1 content"
    assert row["final_document_2"] == "Doc 2 content"


def test_parse_combined_exact():
    """Verify open_claw parser with exact standard markers."""
    text = (
        "===MODERATOR_ANALYSIS===\n"
        "Moderator analysis text.\n"
        "===DOCUMENT_1===\n"
        "Polished answer document.\n"
        "===DOCUMENT_2===\n"
        "Audit trail document."
    )
    result = _parse_combined(text)
    assert result is not None
    assert result["moderator_analysis"] == "Moderator analysis text."
    assert result["document_1"] == "Polished answer document."
    assert result["document_2"] == "Audit trail document."


def test_parse_combined_markdown_headings():
    """Verify open_claw parser with markdown headings around markers."""
    text = (
        "### ===MODERATOR_ANALYSIS===\n"
        "Moderator analysis text with headings.\n"
        "### ===DOCUMENT_1===\n"
        "Polished answer document.\n"
        "### ===DOCUMENT_2===\n"
        "Audit trail document."
    )
    result = _parse_combined(text)
    assert result is not None
    assert result["moderator_analysis"] == "Moderator analysis text with headings."
    assert result["document_1"] == "Polished answer document."
    assert result["document_2"] == "Audit trail document."


def test_parse_combined_missing_marker():
    """Verify open_claw parser returns None when markers are missing."""
    text = "===MODERATOR_ANALYSIS===\nSome text without doc markers."
    result = _parse_combined(text)
    assert result is None


def test_fallback():
    """Verify open_claw fallback dictionary generation."""
    responses = [{"seat_name": "GPT-OSS-20B", "response": "Hello world"}]
    fb = _fallback(responses, "Timeout error")
    assert fb["moderator_analysis"] == ""
    assert "[Synthesis unavailable: Timeout error]" in fb["document_1"]
    assert "GPT-OSS-20B" in fb["document_2"]


def test_google_search_no_key(monkeypatch):
    """Verify Tavily search returns [] cleanly when API key is missing."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    results = search_google("test")
    assert results == []


def test_history_endpoint():
    """Verify GET /history endpoint returns a list."""
    client = TestClient(app)
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_index_endpoint():
    """Verify GET / serves the UI page."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
