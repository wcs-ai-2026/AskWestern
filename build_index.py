
import csv
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
import chromadb

# Paths
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "sources" / "sources.csv"
DB_PATH = BASE_DIR / "chroma_db"

USER_AGENT = "AskWesternBot/0.1"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Read the seed set
with open(CSV_PATH, encoding="utf-8-sig", newline="") as file:
    sources = list(csv.DictReader(file))

print(f"Found {len(sources)} sources")

# Initialize ChromaDB
client = chromadb.PersistentClient(path=str(DB_PATH))
collection = client.get_or_create_collection(name="askwestern")

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

robots_cache = {}


def crawling_allowed(url):
    """Check the website's current robots.txt rules."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in robots_cache:
        robots = RobotFileParser()
        robots.set_url(origin + "/robots.txt")

        try:
            response = session.get(
                origin + "/robots.txt",
                timeout=15
            )
            response.raise_for_status()
            robots.parse(response.text.splitlines())
            robots_cache[origin] = robots
        except requests.RequestException:
            print(f"Could not verify robots.txt for {origin}")
            return False

    return robots_cache[origin].can_fetch(USER_AGENT, url)


def fetch_text(url):
    """Download and extract webpage text."""
    response = session.get(url, timeout=20)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")

    if "text/html" not in content_type.lower():
        raise ValueError(f"Unsupported content type: {content_type}")

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup([
        "script", "style", "nav", "footer",
        "header", "noscript"
    ]):
        element.decompose()

    main = soup.find("main")
    content = main if main else soup.body

    if content is None:
        return ""

    text = content.get_text(separator=" ", strip=True)

    # Remove extra whitespace
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text, chunk_size=1000, overlap=200):
    """Split text into overlapping chunks at word boundaries."""
    if not 0 <= overlap < chunk_size:
        raise ValueError("Overlap must be smaller than chunk size")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(start + 1, end - overlap)

        # Avoid beginning in the middle of a word
        while start < len(text) and not text[start - 1].isspace():
            start += 1

    return chunks


# Process all approved sources
successful = 0
failed = 0
skipped = 0

for source in sources:
    source_id = source["source_id"]
    url = source["url"]

    print(f"\nProcessing {source_id}: {url}")

    if source["robots_allowed"].strip().lower() not in (
        "yes",
        "public page not blocked by robots.txt"
    ):
        print("Skipping: crawling permission not confirmed")
        skipped += 1
        continue

    if not crawling_allowed(url):
        print("Skipping: robots.txt permission not confirmed")
        skipped += 1
        continue

    try:
        text = fetch_text(url)

        if not text:
            raise ValueError("No text extracted")

        chunks = chunk_text(
            text,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )

        if not chunks:
            raise ValueError("No chunks created")

        print(f"Created {len(chunks)} chunks")
        
        existing = collection.get(
            where={"source_id": source_id}
        )

        new_ids = [
            f"{source_id}_chunk_{i}"
            for i in range(len(chunks))
        ]

        # Add chunks in batches
        for start in range(0, len(chunks), 32):
            batch = chunks[start:start + 32]

            collection.upsert(
                ids=[
                    f"{source_id}_chunk_{i}"
                    for i in range(start, start + len(batch))
                ],
                documents=batch,
                metadatas=[
                    {
                        "source_id": source_id,
                        "category": source["category"],
                        "url": url,
                        "notes": source["notes"],
                        "chunk_index": i
                    }
                    for i in range(start, start + len(batch))
                ]
            )

        
        # Remove outdated chunks after successful indexing
        new_id_set = set(new_ids)

        outdated_ids = [
            old_id
            for old_id in existing["ids"]
            if old_id not in new_id_set
        ]

        if outdated_ids:
            collection.delete(ids=outdated_ids)

        successful += 1
        print(f"Indexed {source_id} successfully")

    except Exception as error:
        failed += 1
        print(f"Failed: {error}")

    # Avoid sending requests too quickly
    time.sleep(1)



print("\n========== INDEXING SUMMARY ==========")
print(f"Successfully indexed: {successful}")
print(f"Failed: {failed}")
print(f"Skipped: {skipped}")
print(f"Total chunks in database: {collection.count()}")

# Test semantic search
if collection.count() > 0:
    results = collection.query(
        query_texts=["How do I register for courses at Western?"],
        n_results=3
    )

    print("\n========== SEARCH RESULTS ==========")

    for document, metadata in zip(
        results["documents"][0],
        results["metadatas"][0]
    ):
        print(f"\nSource: {metadata['source_id']}")
        print(f"URL: {metadata['url']}")
        print(f"Text: {document[:400]}")
