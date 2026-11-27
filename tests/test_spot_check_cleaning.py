import hashlib 
import re
from pathlib import Path
from src.askwestern.ingest.clean import clean_html, deduplicate_chunks

#im using the seed pages to test on
SEED_DIR = Path("data/seed")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def chunk_text(text, chunk_size=1000, overlap=200):
#split the text using the same logic as build index
    if not 0 <= overlap < chunk_size: #throw error if chunk size is not greater than the overlap
        raise ValueError("Invalid Error")

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

        while start < len(text) and not text[start - 1].isspace():
            start += 1

    return chunks

def main():
    html_files = sorted(SEED_DIR.glob("*html"))
    if not html_files:
        print("no see html found")
        return

    all_chunks = []

    for path in html_files:
        html = path.read_text(encoding="utf-8", errors="replace")
        text = clean_html(html)

        if not text:
            continue

        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        for c in chunks:
            all_chunks.append((path.name, c))

    print(f"html files processed: {len(html_files)}")
    print(f"Chunks before deduplication: {len(all_chunks)}")

    #remoce the exact duplicates but keep the source info
    unique_chunks = []
    seen = set()

    for fileName, c in all_chunks:
        normalized = re.sub(r"\s+", " ", c).strip()
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        unique_chunks.append((fileName, normalized))

    print(f"Chunks after deduplication: {len(unique_chunks)}")
    print(f"Duplicates removed: {len(all_chunks) - len(unique_chunks)}")

    if len(unique_chunks) < 10:
        print("not enough unique chunks for a 10-chunk spot check")
        return

    print("\n========== 10 CHUNK SPOT CHECK ==========")
    
    # Select one chunk from each of 10 different pages.
    selected_chunks = []
    selected_sources = set()

    for filename, chunk in unique_chunks:
        if filename in selected_sources:
            continue

        selected_sources.add(filename)
        selected_chunks.append((filename, chunk))

        if len(selected_chunks) == 10:
            break

    if len(selected_chunks) < 10:
        print("Not enough distinct sources for the spot-check.")
        return

    print("\n========== 10-SOURCE SPOT-CHECK ==========")

    for i, (filename, chunk) in enumerate(selected_chunks, start=1):
        print(f"\n--- CHUNK {i} ---")
        print(f"Source: {filename}")
        print(f"Characters: {len(chunk)}")
        print(f"Text: {chunk}")

    # Select one chunk from each of 10 different pages.
    selected_chunks = []
    selected_sources = set()

    for filename, chunk in unique_chunks:
        if filename in selected_sources:
            continue

        selected_sources.add(filename)
        selected_chunks.append((filename, chunk))

        if len(selected_chunks) == 10:
            break

    if len(selected_chunks) < 10:
        print("Not enough distinct sources for the spot-check.")
        return

    print("\n========== 10-SOURCE SPOT-CHECK ==========")

    for i, (filename, chunk) in enumerate(selected_chunks, start=1):
        print(f"\n--- CHUNK {i} ---")
        print(f"Source: {filename}")
        print(f"Characters: {len(chunk)}")
        print(f"Text: {chunk}")



if __name__ == "__main__":
    main()
