"""Score AskWestern against the benchmark and save a dated results file.

v0 scores retrieval hit rate only, as defined in ``eval/README.md``: an
answerable question is a hit if its ``expected_source_url`` is the
``source_url`` of one of the top 5 chunks ``search()`` returns. Unanswerable
questions are recorded but not scored.

Run ``python eval/run_eval.py`` from the repo root. It writes
``eval/results/YYYY-MM-DD.csv`` (overwriting a same-day run) and prints the
hit rate.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Swap for askwestern.retrieve.search once the real search() lands.
from askwestern.stubs import search  # noqa: E402


BENCHMARK = ROOT / "eval" / "benchmark.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"
K = 5

COLUMNS = [
    "id",
    "type",
    "category",
    "difficulty",
    "question",
    "expected_source_url",
    "retrieved_urls",
    "hit",
]

# returns a list of questions from benchmark.jsonl - reads one line at a time
def load_benchmark(path: Path) -> List[Dict[str, Any]]:
    """Read one benchmark item (contract 4) per non-blank line."""
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def score(item: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve for one question and return its results row."""
    urls = [chunk["source_url"] for chunk in search(item["question"], k=K)]
    hit = ""
    if item["type"] == "answerable":
        hit = int(item["expected_source_url"] in urls)
    return {
        "id": item["id"],
        "type": item["type"],
        "category": item["category"],
        "difficulty": item["difficulty"],
        "question": item["question"],
        "expected_source_url": item.get("expected_source_url") or "",
        "retrieved_urls": " | ".join(urls),
        "hit": hit,
    }

#scores each question, save the CSV and prints dated result to results folder
def main() -> None:
    rows = [score(item) for item in load_benchmark(BENCHMARK)]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{date.today().isoformat()}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    scored = [row["hit"] for row in rows if row["hit"] != ""]
    hits = sum(scored)
    pct = 100 * hits / len(scored) if scored else 0.0
    print(f"Hit rate: {hits}/{len(scored)} = {pct:.0f}%")
    print(f"Results saved to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
