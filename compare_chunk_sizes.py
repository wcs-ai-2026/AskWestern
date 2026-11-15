
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import chromadb
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
SEED_DIR = BASE_DIR / "data" / "seed"
CSV_PATH = BASE_DIR / "sources" / "sources.csv"
BENCHMARK_PATH = BASE_DIR / "eval" / "benchmark.jsonl"
DB_PATH = BASE_DIR / "chroma_experiments"

MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Three chunk configurations
CONFIGS = {
    "small": (500, 100),
    "medium": (1000, 200),
    "large": (1500, 300),
}

# Load the embedding model once
print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)

# Create separate experiment database
client = chromadb.PersistentClient(path=str(DB_PATH))


def normalize_url(url):
    """Normalize URL formatting for evaluation."""
    parts = urlsplit(url.strip())
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        parts.query,
        ""
    ))


def extract_text(path):
    """Read and clean a saved HTML page."""
    html = path.read_text(
        encoding="utf-8", errors="replace"
    )
    soup = BeautifulSoup(html, "html.parser")

    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title else path.stem
    )

    for element in soup([
        "script", "style", "nav",
        "footer", "header", "noscript"
    ]):
        element.decompose()

    content = soup.find("main") or soup.body or soup

    text = content.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    return title, text


def chunk_text(text, size, overlap):
    """Split text at word boundaries with overlap."""
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = max(start + 1, end - overlap)

        while (
            start < len(text)
            and start > 0
            and not text[start - 1].isspace()
        ):
            start += 1

    return chunks


# Load source URL mapping
with open(CSV_PATH, encoding="utf-8-sig") as f:
    sources = {
        row["source_id"]: row
        for row in csv.DictReader(f)
    }

# Load answerable benchmark questions
with open(BENCHMARK_PATH, encoding="utf-8") as f:
    questions = [
        json.loads(line)
        for line in f if line.strip()
    ]

questions = [
    q for q in questions
    if q.get("type") == "answerable"
    and q.get("expected_source_url")
]

# Read saved pages once
pages = []

for path in sorted(SEED_DIR.glob("*.html")):
    source = sources.get(path.stem)

    if source is None:
        print(f"Skipping unknown source: {path.name}")
        continue

    title, text = extract_text(path)

    if text:
        pages.append({
            "source_id": path.stem,
            "source_url": source["url"],
            "title": title,
            "text": text
        })

print(f"Loaded {len(pages)} saved HTML pages")
print(f"Loaded {len(questions)} benchmark questions")

if not pages or not questions:
    raise SystemExit("Missing pages or benchmark questions")

# Embed benchmark questions consistently
query_texts = [
    "Represent this sentence for searching relevant passages: "
    + q["question"]
    for q in questions
]

query_embeddings = model.encode(
    query_texts,
    normalize_embeddings=True,
    show_progress_bar=False
).tolist()

summary = []

for name, (size, overlap) in CONFIGS.items():
    print(f"\n========== {name.upper()} ==========")
    print(f"Chunk size: {size}, overlap: {overlap}")

    collection_name = f"askwestern_{name}"



    # Rebuild only this experiment collection
    existing_collections = [
        collection.name
        for collection in client.list_collections()
    ]

    if collection_name in existing_collections:
        client.delete_collection(collection_name)

    collection = client.create_collection(
        name=collection_name,
        configuration={"hnsw": {"space": "cosine"}}
    )

    ids = []
    documents = []
    metadatas = []

    for page in pages:
        chunks = chunk_text(page["text"], size, overlap)

        for i, chunk in enumerate(chunks):
            ids.append(f"{page['source_id']}_{i}")
            documents.append(chunk)
            metadatas.append({
                "source_id": page["source_id"],
                "source_url": page["source_url"],
                "title": page["title"],
                "chunk_index": i
            })

    print(f"Created {len(documents)} chunks")

    # Generate embeddings in batches
    for start in range(0, len(documents), 32):
        end = start + 32
        batch = documents[start:end]

        embeddings = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False
        ).tolist()

        collection.add(
            ids=ids[start:end],
            documents=batch,
            metadatas=metadatas[start:end],
            embeddings=embeddings
        )

    print(f"Stored {collection.count()} chunks")

    hits = 0
    misses = []

    for q, query_embedding in zip(
        questions, query_embeddings
    ):
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(5, collection.count()),
            include=["metadatas"]
        )

        retrieved_urls = [
            normalize_url(m["source_url"])
            for m in result["metadatas"][0]
        ]

        expected = normalize_url(
            q["expected_source_url"]
        )

        hit = expected in retrieved_urls

        if hit:
            hits += 1
        else:
            misses.append(q["id"])

        print(f"{q['id']}: {'HIT' if hit else 'MISS'}")

    rate = hits / len(questions)

    summary.append({
        "configuration": name,
        "chunk_size": size,
        "overlap": overlap,
        "chunks": collection.count(),
        "hits": hits,
        "questions": len(questions),
        "hit_rate_at_5": round(rate, 4),
        "misses": ",".join(misses)
    })

    print(f"Hit Rate@5: {rate:.2%}")

# Save experiment results
results_path = BASE_DIR / "chunk_size_results.csv"

with open(results_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=summary[0].keys()
    )
    writer.writeheader()
    writer.writerows(summary)

print("\n========== FINAL COMPARISON ==========")

for result in summary:
    print(
        f"{result['configuration']}: "
        f"{result['hits']}/{result['questions']} hits, "
        f"{result['hit_rate_at_5']:.2%}, "
        f"{result['chunks']} chunks"
    )

print(f"\nResults saved to {results_path.name}")
