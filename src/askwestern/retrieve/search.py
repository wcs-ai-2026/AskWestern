
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "chroma_experiments"

COLLECTION_NAME = "askwestern_small"
MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model = None


def get_model():
    """Load the embedding model only when needed."""
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def search(question: str, k: int = 5) -> list[dict]:
    """Retrieve the top-k matching chunks from ChromaDB."""

    if not isinstance(question, str) or not question.strip():
        return []

    if not isinstance(k, int) or k <= 0:
        return []

    try:
        client = chromadb.PersistentClient(path=str(DB_PATH))
        collection = client.get_collection(
            name=COLLECTION_NAME
        )

        count = collection.count()

        if count == 0:
            return []

        # Use the same embedding model as the index
        query_text = (
            "Represent this sentence for searching relevant passages: "
            + question
        )

        query_embedding = get_model().encode(
            query_text,
            normalize_embeddings=True
        ).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
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
            # Cosine similarity = 1 - cosine distance
            score = max(0.0, min(1.0, 1.0 - distance))

            chunks.append({
                "chunk_id": chunk_id,
                "text": document,
                "source_url": metadata.get("source_url", ""),
                "title": metadata.get("title", ""),
                "section": metadata.get("section", ""),
                "collected_on": metadata.get("collected_on", ""),
                "source_type": metadata.get("source_type", "html"),
                "score": float(score)
            })

        return chunks

    except Exception as error:
        print(f"Search error: {error}")
        return []


if __name__ == "__main__":
    question = "When do fall classes start at Western?"

    results = search(question)

    print(f"Found {len(results)} results\n")

    for result in results:
        print(f"Source: {result['source_url']}")
        print(f"Score: {result['score']:.3f}")
        print(f"Text: {result['text'][:200]}\n")
