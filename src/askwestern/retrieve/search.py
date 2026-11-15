
from pathlib import Path

import chromadb

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "askwestern"


def search(question: str, k: int = 5) -> list[dict]:
    """Return the top k relevant chunks from the local index."""

    if not isinstance(question, str) or not question.strip():
        return []

    if not isinstance(k, int) or k <= 0:
        return []

    try:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)

        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_texts=[question],
            n_results=min(k, count),
            include=["documents", "metadatas", "distances"]
        )

        chunks = []

        for chunk_id, document, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            # Provisional similarity score for the original L2 index
            score = max(0.0, min(1.0, 1.0 - distance / 2.0))

            chunks.append({
                "chunk_id": chunk_id,
                "text": document,
                "source_url": metadata.get("url", ""),
                "title": metadata.get("notes", ""),
                "section": "",
                "collected_on": "",
                "source_type": "html",
                "score": float(score)
            })

        return chunks

    except Exception as error:
        print(f"Search error: {error}")
        return []


if __name__ == "__main__":
    results = search("When do fall classes start at Western?")

    print(f"Found {len(results)} results")

    for result in results:
        print(result["source_url"], result["score"])
