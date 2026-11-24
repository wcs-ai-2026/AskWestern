"""Build the ChromaDB index that search() reads.

This is the only indexer. It reads the scraped pages in data/raw/ together with
the .json metadata saved beside each one, so every chunk carries the fields the
chunk-record contract requires — including collected_on, which is why it reads
data/raw/ rather than data/seed/ (the seed copies have no metadata).

Chunk size and overlap are the configuration SCRUM-35 measured as best
(500/100, 91.3% hit rate at 5 — see RETRIEVAL_RESULTS.md). compare_chunk_sizes.py
is the experiment that established that; it writes its own throwaway database
and nothing reads its output.

    python build_index.py
"""

import json
import re
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
DB_PATH = BASE_DIR / "chroma_db"

COLLECTION_NAME = "askwestern"
MODEL_NAME = "BAAI/bge-small-en-v1.5"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

BATCH = 32

# Every chunk record must carry these (CONTRACTS.md, contract 1).
REQUIRED_META = ("source_url", "title", "collected_on", "source_type")


def extract_text(path):
    """Read and clean a saved HTML page. Same logic as compare_chunk_sizes.py."""
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    html_title = (
        soup.title.get_text(" ", strip=True) if soup.title else path.stem
    )

    for element in soup([
        "script", "style", "nav", "footer", "header", "noscript"
    ]):
        element.decompose()

    content = soup.find("main") or soup.body or soup

    text = content.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    return html_title, text


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

        while start < len(text) and start > 0 and not text[start - 1].isspace():
            start += 1

    return chunks


def load_pages():
    """Every data/raw page that has usable text and complete metadata."""
    pages = []
    skipped = []

    for path in sorted(RAW_DIR.rglob("*.html")):
        meta_path = path.with_suffix(".json")

        if not meta_path.exists():
            skipped.append((path.stem, "no .json metadata beside it"))
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        missing = [f for f in REQUIRED_META if not meta.get(f)]
        if missing:
            skipped.append((path.stem, f"metadata missing {', '.join(missing)}"))
            continue

        html_title, text = extract_text(path)
        if not text:
            skipped.append((path.stem, "no text extracted"))
            continue

        pages.append({
            "source_id": meta.get("source_id") or path.stem,
            "source_url": meta["source_url"],
            # Ghanwa's curated title, falling back to the page's <title>.
            "title": meta["title"] or html_title,
            "collected_on": meta["collected_on"],
            "source_type": meta["source_type"],
            "text": text,
        })

    return pages, skipped


def main():
    if not RAW_DIR.exists():
        raise SystemExit(f"No scraped pages at {RAW_DIR}")

    pages, skipped = load_pages()

    print(f"Loaded {len(pages)} pages from {RAW_DIR.relative_to(BASE_DIR)}")
    for source_id, why in skipped:
        print(f"  skipped {source_id}: {why}")

    if not pages:
        raise SystemExit("No usable pages - nothing to index")

    print(f"Loading embedding model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(DB_PATH))

    # Rebuild from scratch so a removed page cannot linger in the index.
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
    )

    ids, documents, metadatas = [], [], []

    for page in pages:
        chunks = chunk_text(page["text"], CHUNK_SIZE, CHUNK_OVERLAP)

        for i, chunk in enumerate(chunks):
            ids.append(f"{page['source_id']}_{i}")
            documents.append(chunk)
            metadatas.append({
                "source_id": page["source_id"],
                "source_url": page["source_url"],
                "title": page["title"],
                "collected_on": page["collected_on"],
                "source_type": page["source_type"],
                "section": "",
                "chunk_index": i,
            })

    print(f"Created {len(documents)} chunks at {CHUNK_SIZE}/{CHUNK_OVERLAP}")

    for start in range(0, len(documents), BATCH):
        batch = documents[start:start + BATCH]

        embeddings = model.encode(
            batch, normalize_embeddings=True, show_progress_bar=False
        ).tolist()

        collection.add(
            ids=ids[start:start + BATCH],
            documents=batch,
            metadatas=metadatas[start:start + BATCH],
            embeddings=embeddings,
        )

    print(f"Stored {collection.count()} chunks in {DB_PATH.name}/{COLLECTION_NAME}")


if __name__ == "__main__":
    main()
