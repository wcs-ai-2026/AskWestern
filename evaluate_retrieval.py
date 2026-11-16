
import json
from pathlib import Path

from src.askwestern.retrieve.search import search

BASE_DIR = Path(__file__).resolve().parent
BENCHMARK_PATH = BASE_DIR / "eval" / "benchmark.jsonl"


def evaluate_hit_rate(k=5):
    """Measure how often the expected source appears in top-k results."""

    with open(BENCHMARK_PATH, encoding="utf-8") as file:
        questions = [
            json.loads(line)
            for line in file
            if line.strip()
        ]

    answerable = [
        q for q in questions
        if q.get("type") == "answerable"
        and q.get("expected_source_url")
    ]

    hits = 0

    for question in answerable:
        results = search(question["question"], k=k)

        retrieved_urls = [
            result["source_url"] for result in results
        ]

        expected_url = question["expected_source_url"]
        found = expected_url in retrieved_urls

        if found:
            hits += 1

        status = "HIT" if found else "MISS"
        print(f"{question['id']}: {status}")

    total = len(answerable)
    hit_rate = hits / total if total else 0

    print("\n========== RETRIEVAL EVALUATION ==========")
    print(f"Answerable questions: {total}")
    print(f"Hits: {hits}")
    print(f"Misses: {total - hits}")
    print(f"Hit Rate@{k}: {hit_rate:.2%}")

    return hit_rate


if __name__ == "__main__":
    evaluate_hit_rate(k=5)
