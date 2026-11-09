# AskWestern


## Chunking and Embedding

This project uses ChromaDB to create a local vector database
of Western University information for semantic search.

### Setup

1. Create a virtual environment:

   python3 -m venv .venv

2. Activate the environment (Mac/Linux):

   source .venv/bin/activate

3. Install dependencies:

   pip install -r requirements.txt

### Build the Index

Run:

   python build_index.py

The script:
- Reads seed URLs from sources/sources.csv
- Checks crawling permissions
- Extracts text from approved webpages
- Splits text into overlapping chunks
- Generates embeddings using ChromaDB's default embedding model
- Stores chunks and source metadata in a local ChromaDB index
- Tests semantic search with a sample query

### Configuration

- Chunk size: 1000 characters
- Chunk overlap: 200 characters
- Embedding model: all-MiniLM-L6-v2 (ChromaDB default)
- Database directory: chroma_db/
- Collection name: askwestern

### Results

Initial indexing:
- 47 seed sources
- 37 successfully indexed
- 10 skipped
- 845 chunks stored

The local database is excluded from Git.
Run the script to regenerate it.
