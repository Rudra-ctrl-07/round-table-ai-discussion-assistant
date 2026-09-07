"""Tavily Search API wrapper.

Thin client around https://api.tavily.com/search. Returns plain dicts
(title / snippet / link) so the rest of the pipeline doesn't need to
know about Tavily's response shape. Designed to fail soft: any error
logs a warning and returns [], so a broken search provider never
crashes a /query request.
"""
from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

TAVILY_ENDPOINT = "https://api.tavily.com/search"
HTTP_TIMEOUT_SECONDS = 10.0


def search_google(query: str, num_results: int = 5) -> list[dict]:
    """Search the web via Tavily.

    Returns a list of {"title", "snippet", "link"} dicts (up to
    `num_results`). Returns [] on any failure so callers can treat an
    empty result as a soft "nothing found."

    Named `search_google` to keep the public interface unchanged so
    agent.py and any other callers need no edits.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.warning("Tavily: missing TAVILY_API_KEY; returning []")
        return []

    body = {
        "api_key": api_key,
        "query": query,
        "max_results": max(1, min(num_results, 10)),
        "search_depth": "basic",
        "include_answer": False,
    }

    try:
        resp = httpx.post(TAVILY_ENDPOINT, json=body, timeout=HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("Tavily call failed for %r: %s; returning []", query, exc)
        return []

    items = data.get("results") or []
    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("content", ""),
            "link": item.get("url", ""),
        }
        for item in items
    ]
