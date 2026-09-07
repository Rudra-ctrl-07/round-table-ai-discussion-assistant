"""One-off: build demo_insurance/notes.json with pull instructions and previews."""
import json
import urllib.request


def main() -> None:
    hist = json.loads(
        urllib.request.urlopen("http://127.0.0.1:8000/history?limit=50", timeout=30)
        .read()
        .decode("utf-8")
    )
    by_id = {row["id"]: row for row in hist}

    with open("D:/PROJECTS/RT/demo_insurance/index.json", "r", encoding="utf-8") as f:
        idx = json.load(f)

    for r in idx:
        qid = r["query_id"]
        row = by_id.get(qid)
        if not row:
            r["first_line_preview"] = "(row not found)"
            continue
        d1 = row.get("final_document_1") or ""
        # First non-empty line of document_1
        preview = ""
        for line in d1.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("|"):
                preview = stripped
                break
        if not preview:
            preview = d1[:160]
        r["first_line_preview"] = preview[:200]
        r["final_document_1_length"] = len(d1)
        r["final_document_2_length"] = len(row.get("final_document_2") or "")
        r["moderator_analysis_length"] = len(row.get("moderator_analysis") or "")

    notes = {
        "purpose": (
            "Insurance for tomorrow's live demo. If OpenRouter is flaky live, "
            "show these from /history instead of gambling on a fresh run."
        ),
        "how_to_pull": [
            "curl http://127.0.0.1:8000/history?limit=50",
            "Find rows whose 'id' is in this index.",
            "Each row has final_document_1, final_document_2, moderator_analysis "
            "already populated as plain text — paste straight into the demo UI "
            "or your slides.",
        ],
        "demo_picker": [
            "Q1 microservices-vs-monoliths (qid "
            + str(idx[0]["query_id"])
            + "): broad technical trade-off, good opener.",
            "Q2 kubernetes-year-one (qid "
            + str(idx[1]["query_id"])
            + "): concrete infrastructure decision, practical.",
            "Q3 b2b-saas-pricing (qid "
            + str(idx[2]["query_id"])
            + "): goes outside pure tech into business strategy, "
            "shows the round table works on non-engineering questions too.",
        ],
        "runs": idx,
    }

    with open("D:/PROJECTS/RT/demo_insurance/notes.json", "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)

    print("Wrote D:/PROJECTS/RT/demo_insurance/notes.json")
    for r in idx:
        print(f"  qid={r['query_id']:>3}  fallback={r['used_fallback']}  preview: {r['first_line_preview']}")


if __name__ == "__main__":
    main()
