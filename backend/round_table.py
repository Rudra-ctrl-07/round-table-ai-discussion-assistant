"""Round Table — fan a single research question out to N LLM "seats" in parallel,
then summarize agreement/disagreement with a moderator seat.

Every step fails soft: a missing API key, an unknown model, a 5xx, or a
timeout becomes a structured error in the response dict, never an
exception. This way a single broken provider can never crash /query.

All seats (including the moderator) run through OpenRouter with a
single `OPENROUTER_API_KEY`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------- config

SEATS: list[dict] = [
    {"seat_name": "GPT-OSS-20B",           "model": "openai/gpt-oss-20b:free"},
    {"seat_name": "Nemotron-3-Super-120B", "model": "nvidia/nemotron-3-super-120b-a12b:free"},
    {"seat_name": "Nemotron-Nano-9B",      "model": "nvidia/nemotron-nano-9b-v2:free"},
]

# Used by moderate() to pick the moderator's seat. Picked by name so
# SEATS remains the single source of truth for model strings.
# Chosen: GPT-OSS-20B — the only non-Google/non-NVIDIA free general
# chat model in the live OpenRouter free list. Two reasons to prefer
# it over Gemma 4 31B here:
#   1. Different provider (OpenAI vs Google) means it has a separate
#      rate-limit pool from the rest of the seats. With Gemma as both
#      a fan-out seat and the moderator, we were hitting "429 Too Many
#      Requests" on the moderator and synthesis calls after the fan-out.
#   2. The fan-out and the moderator/synthesis calls are sequential
#      (not concurrent) — see submit_query in app.py — so it's safe to
#      reuse the same model in both roles. Used for both the
#      panel-summary call (moderate) and the final synthesis
#      (open_claw.generate_documents).
#
# TEMPORARY: switched to Nemotron-3-Super-120B while GPT-OSS-20B is
# being rate-limited (returning 429s on every fan-out call this
# evening). This means the moderator/synthesis call now shares a
# provider with the fan-out seats, so a single rate-limit pool. If
# GPT-OSS-20B comes back, switch back to it (or keep this if it
# works fine — the marker-cleanup verification is the priority
# right now).
MODERATOR_SEAT: dict = next(s for s in SEATS if s["seat_name"] == "Nemotron-3-Super-120B")

# Per-call budget. Generous because free-tier models are slow.
SEAT_TIMEOUT_SECONDS = 30.0

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# --------------------------------------------------------------------- prompts


def _build_prompt(query: str, search_results: list[dict]) -> str:
    """Assemble the single shared prompt sent to every seat."""
    if not search_results:
        results_block = "(no web results available — answer from general knowledge if possible, or say you cannot find relevant information)"
    else:
        lines = []
        for i, r in enumerate(search_results, start=1):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            lines.append(f"[{i}] {title} — {snippet} ({link})")
        results_block = "\n".join(lines)

    return (
        "You are a research analyst. Use the following web search results to "
        "answer the user's question. Be concise and cite the source numbers "
        "in brackets like [1], [2] when you reference them.\n\n"
        f"Search results:\n{results_block}\n\n"
        f"User question: {query}\n\n"
        "Answer:"
    )


def _build_moderator_prompt(responses: list[dict]) -> str:
    """Assemble the prompt that asks the moderator to summarize the panel."""
    lines = []
    for r in responses:
        lines.append(f"- {r['seat_name']}: {r['response']}")
    panel = "\n".join(lines)
    return (
        "You are moderating a panel of LLMs that each answered the same "
        "research question. Summarize:\n"
        "1. Where the responses agree (consensus).\n"
        "2. Where they disagree (and what each side argues).\n"
        "3. Which response(s) seem most reliable, and why.\n\n"
        "Be concise (3-5 short paragraphs). Use bullet points for clarity.\n\n"
        f"Responses:\n{panel}"
    )


# --------------------------------------------------------------------- public


async def run_round_table(query: str, research_context: dict) -> list[dict]:
    """Async parallel fan-out: 3 LLM seats, all running concurrently.

    Awaited directly from submit_query (which is already async). Don't
    wrap this in asyncio.run — that would raise "cannot be called from
    a running event loop" because FastAPI/Starlette handlers already
    run on a loop.
    """
    prompt = _build_prompt(query, research_context.get("search_results", []) or [])
    return await asyncio.gather(*(ask_seat(seat, prompt) for seat in SEATS))



async def ask_seat(seat: dict, prompt: str, max_tokens: int = 800) -> dict:
    """Dispatch a single seat call. Always returns a dict, never raises.

    All seats go through OpenRouter — there's only one provider now.
    `max_tokens` defaults to 800 for fan-out / moderator calls; the
    synthesis caller (open_claw.generate_documents) overrides it because
    two full documents plus markers don't fit in 800 tokens.
    """
    name = seat.get("seat_name", "<unnamed>")
    model = seat.get("model", "")
    try:
        return await _ask_openrouter(name, model, prompt, max_tokens=max_tokens)
    except Exception as exc:  # last-resort net
        logger.warning("ask_seat %s: unexpected error: %s", name, exc)
        return {"seat_name": name, "response": None, "error": str(exc)}


# --------------------------------------------------------------------- impl


async def _ask_openrouter(
    seat_name: str, model: str, prompt: str, max_tokens: int = 800
) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"seat_name": seat_name, "response": None,
                "error": "missing API key (OPENROUTER_API_KEY)"}

    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}
    # Lower temperature reduces drift into non-English tokens; capping
    # max_tokens prevents runaway generations that degrade near the end.
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    timeout = httpx.Timeout(SEAT_TIMEOUT_SECONDS)

    # 429s from OpenRouter are transient but the free-tier limits can
    # sit on a 1-2 minute window — 3s isn't enough. Two retries with
    # exponential backoff (10s, then 30s), capped at ~45s of waiting
    # so this can't blow past reasonable request timeouts. Other
    # errors fail immediately.
    backoff_seconds = (10, 30)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(OPENROUTER_ENDPOINT, headers=headers, json=body)
            for delay in backoff_seconds:
                if resp.status_code != 429:
                    break
                logger.info(
                    "openrouter seat %s hit 429, retrying after %ds", seat_name, delay
                )
                await asyncio.sleep(delay)
                resp = await client.post(
                    OPENROUTER_ENDPOINT, headers=headers, json=body
                )
        resp.raise_for_status()
        try:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError) as parse_exc:
            # 200 OK but the body isn't the expected shape. Log the
            # FULL raw body so we can see what OpenRouter actually
            # returned — could be a content-filter response, a wrapped
            # error object, or something else.
            logger.warning(
                "openrouter seat %s: 200 OK but parse failed (%s). "
                "status=%s, raw body: %s",
                seat_name, parse_exc, resp.status_code, resp.text,
            )
            return {
                "seat_name": seat_name, "response": None,
                "error": f"parse failed: {parse_exc}",
            }
        return {"seat_name": seat_name, "response": text, "error": None}
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as exc:
        logger.warning("openrouter seat %s failed: %s", seat_name, exc)
        return {"seat_name": seat_name, "response": None, "error": str(exc)}
