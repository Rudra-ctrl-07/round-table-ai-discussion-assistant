"""Open Claw — the final synthesis step.

Combined moderation + synthesis: a single LLM call (the moderator seat,
via OpenRouter) produces three things in one response:

  1. A moderator analysis (consensus / disagreements / reliability).
  2. The `===DOCUMENT_1=== ... ===DOCUMENT_2=== ...` block, where
     `document_1` is the polished final answer and `document_2` is a
     transcript (each seat verbatim, then the moderator analysis).

We previously did this in two LLM calls (`moderate` then
`generate_documents`). Combining them saves one round-trip to
OpenRouter (~30s on free tier) and avoids re-asking the same model to
re-read the panel just to summarize it.

Fails soft in two ways:
  - LLM call missing/bad key, timeout, etc. → `document_1` becomes
    `"[Synthesis unavailable: ...]"`, `document_2` is a Python-built
    audit trail assembled locally with no LLM in the loop.
  - LLM returns malformed output (one or both markers missing) →
    same fallback, with a different error message. We never propagate
    the exception.
"""
from __future__ import annotations

from round_table import MODERATOR_SEAT, ask_seat

MARKER_1 = "===DOCUMENT_1==="
MARKER_2 = "===DOCUMENT_2==="

# Marker the LLM must put *before* the moderator analysis section. We
# split the response into [preamble up to this marker, then the rest].
# Any moderator text appearing before the marker is treated as preamble
# and discarded — we want the structured section.
MODERATOR_MARKER = "===MODERATOR_ANALYSIS==="

# Token cap for the combined moderate+synthesis LLM call. Larger than
# the fan-out/moderator cap (800) because the response includes the
# moderator analysis, two full documents, and the marker delimiters.
# Single source of truth — fan-out calls use the default in
# round_table.ask_seat. Bumped from 3000 to 4000 to give Nemotron-Super
# enough room when used as MODERATOR_SEAT (GPT-OSS-20B was fine at
# 3000, but Nemotron-Super produced output that got cut off before
# both markers were emitted).
SYNTHESIS_MAX_TOKENS = 4000


async def generate_documents(
    query: str,
    research_context: dict,
    round_table_responses: list[dict],
) -> dict:
    """Combined moderate + synthesize in a single LLM call.

    Returns `{"moderator_analysis": str, "document_1": str, "document_2": str}`.
    Never raises.
    """
    search_block = _render_search_context(research_context)
    seats_block = _render_seats(round_table_responses)

    prompt = (
        "You are moderating a panel of LLMs that each answered the same "
        "research question, and then producing two final outputs. Do all "
        "of this in ONE response, in EXACTLY this format with these three "
        "markers (so I can parse it programmatically):\n\n"
        f"{MODERATOR_MARKER}\n"
        "[Your moderator analysis: where the panel agrees (consensus), "
        "where they disagree (and what each side argues), and which "
        "response(s) seem most reliable and why. Be concise — 3-5 short "
        "paragraphs, bullet points fine.]\n\n"
        f"{MARKER_1}\n"
        "[A well-researched, clean, structured final answer to the original "
        "question. Incorporate the best insights from the round table and "
        "the moderator's analysis. This should read as a polished, "
        "standalone deliverable — not a summary of what the models said, "
        "but an actual answer to the question.]\n\n"
        f"{MARKER_2}\n"
        "[A labeled compilation: repeat each individual model's response "
        "verbatim under its own heading, then the moderator analysis "
        "from above verbatim at the end. This is the raw transcript/audit "
        "trail — don't editorialize here, just organize it clearly.]\n\n"
        "CRITICAL marker rules — read carefully:\n"
        f"  1. Each of {MODERATOR_MARKER}, {MARKER_1}, and {MARKER_2} "
        "must appear EXACTLY ONCE in your entire response.\n"
        "  2. They are SECTION DELIMITERS, not headings. Use them only to "
        "mark the start of the section they introduce, as shown in the "
        "template above.\n"
        "  3. NEVER restate a marker as a section heading or label "
        "anywhere in the body of a document. For example, do not write a "
        "line like '===MODERATOR_ANALYSIS===' inside document_2 to label "
        "the embedded moderator section.\n"
        "  4. If you want to label a section inside document_2 (e.g. the "
        "embedded moderator analysis at the end), use a plain Markdown "
        "heading like '## Moderator Analysis' instead of repeating a "
        "marker.\n"
        "  5. The text between markers is the only content that will be "
        "extracted for that section — anything outside the markers is "
        "discarded.\n\n"
        "---\n\n"
        f"Original question: {query}\n\n"
        f"Search context used:\n{search_block}\n\n"
        "Individual model responses:\n"
        f"{seats_block}\n"
    )

    try:
        # One call does both jobs now. SYNTHESIS_MAX_TOKENS because the
        # response is the moderator analysis plus two full documents
        # plus markers plus the "CRITICAL marker rules" block in the
        # prompt — Nemotron-Super needs the extra room (GPT-OSS-20B
        # was fine at 3000 but produced tighter output).
        result = await ask_seat(
            MODERATOR_SEAT, prompt, max_tokens=SYNTHESIS_MAX_TOKENS
        )
    except Exception as exc:  # defense in depth; ask_seat already catches
        return _fallback(round_table_responses, str(exc))

    if result.get("error"):
        return _fallback(round_table_responses, result["error"])

    parsed = _parse_combined(result.get("response") or "")
    if parsed is None:
        return _fallback(
            round_table_responses,
            "marker parse failed (model output missing one or more markers)",
        )
    return parsed


import re


def _parse_combined(text: str) -> dict | None:
    """Split a combined response into moderator analysis + two documents.

    Required markers: `===MODERATOR_ANALYSIS===`, `===DOCUMENT_1===`,
    `===DOCUMENT_2===`. Any of them missing → return None so the caller
    can fall back to the Python-built transcript.
    """
    mod_pattern = r"(?:[#*\s]*)(===\s*MODERATOR_ANALYSIS\s*===)"
    doc1_pattern = r"(?:[#*\s]*)(===\s*DOCUMENT_1\s*===)"
    doc2_pattern = r"(?:[#*\s]*)(===\s*DOCUMENT_2\s*===)"

    mod_match = re.search(mod_pattern, text, re.IGNORECASE)
    doc1_match = re.search(doc1_pattern, text, re.IGNORECASE)
    doc2_match = re.search(doc2_pattern, text, re.IGNORECASE)

    if not (mod_match and doc1_match and doc2_match):
        return None

    mod_end = mod_match.end()
    doc1_start, doc1_end = doc1_match.span()
    doc2_start, doc2_end = doc2_match.span()

    if not (mod_end <= doc1_start < doc1_end <= doc2_start):
        return None

    return {
        "moderator_analysis": text[mod_end:doc1_start].strip(),
        "document_1": text[doc1_end:doc2_start].strip(),
        "document_2": text[doc2_end:].strip(),
    }


def _fallback(responses, error) -> dict:
    """Document 1 is a clear 'unavailable' notice. Document 2 is a
    Python-built transcript so the audit trail is still useful even
    when the synthesizer is down. Moderator analysis is empty so the
    /history row has a coherent record.
    """
    return {
        "moderator_analysis": "",
        "document_1": f"[Synthesis unavailable: {error}]",
        "document_2": _build_transcript(responses),
    }


# --------------------------------------------------------------------- render


def _render_seats(responses) -> str:
    """Per-seat block for the prompt, matching the spec's exact format."""
    blocks = []
    for r in responses or []:
        name = r.get("seat_name", "<unnamed>")
        body = r.get("response")
        if body:
            blocks.append(f"### {name}\n{body}")
        else:
            err = r.get("error") or "no response"
            blocks.append(f"### {name}\n[No response — error: {err}]")
    return "\n\n".join(blocks) if blocks else "(no model responses)"


def _render_search_context(research_context) -> str:
    """[i] title — snippet (link) — same numbering used in round_table
    so the model sees consistent formatting across the pipeline."""
    results = (research_context or {}).get("search_results") or []
    if not results:
        return "(no web results available)"
    lines = []
    for i, r in enumerate(results, start=1):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        lines.append(f"[{i}] {title} — {snippet} ({link})")
    return "\n".join(lines)


def _build_transcript(responses) -> str:
    """Pure-Python audit trail. Used as a fallback when the LLM
    moderator/synthesis call fails — assembled locally with no LLM
    in the loop. We don't have moderator analysis to embed here (the
    call failed), so we just list the seats."""
    blocks = []
    for r in responses or []:
        name = r.get("seat_name", "<unnamed>")
        body = r.get("response")
        if body:
            blocks.append(f"### {name}\n{body}")
        else:
            err = r.get("error") or "no response"
            blocks.append(f"### {name}\n[No response — error: {err}]")
    blocks.append("### Moderator\n[Moderator analysis unavailable — synthesis call failed]")
    return "\n\n".join(blocks)
