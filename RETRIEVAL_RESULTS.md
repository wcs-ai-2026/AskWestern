
# AskWestern Retrieval Evaluation

## Overview

Implemented a local ChromaDB retrieval system using
BAAI/bge-small-en-v1.5 embeddings.

Evaluated three chunk configurations using 47 saved
Western University HTML pages and 23 answerable
benchmark questions.

## Chunk-Size Comparison

| Configuration | Size | Overlap | Chunks | Hits | Hit Rate@5 |
|---|---:|---:|---:|---:|---:|
| Small | 500 | 100 | 1778 | 21/23 | 91.30% |
| Medium | 1000 | 200 | 892 | 20/23 | 86.96% |
| Large | 1500 | 300 | 602 | 20/23 | 86.96% |

## Recommendation

The 500-character chunk configuration with 100-character
overlap achieved the highest Hit Rate@5.

This configuration is recommended for further testing,
although the result should be validated on the full
processed dataset and a larger benchmark.

## Missed Questions

- Small: Q010, Q011
- Medium: Q010, Q011, Q012
- Large: Q010, Q011, Q012

## Search Function

Implemented search(question, k=5) to retrieve matching
chunks with source information and cosine similarity scores.

## Testing

- 7 automated pytest tests passed.
- Empty questions return no results.
- Search respects the requested number of results.
- Search returns required field names and similarity scores.
- Search retrieves relevant sources for sample questions.

## Limitations

- The experiments use the available 47 seed HTML pages.
- The full processed-data handoff is not yet available.
- Collection dates and section metadata still need
  integration from the ingestion pipeline.
- Chunk IDs must be aligned with CONTRACTS.md before
  the final production index is built.
- Chunk size and overlap both varied between experiments.

## Next Steps

Integrate the full processed dataset, complete the
metadata contract, and repeat retrieval evaluation.


## Reproducing Results

Create and activate a Python virtual environment.

Install dependencies:

    python -m pip install -r requirements.txt

Build the three experiment indexes:

    python compare_chunk_sizes.py

Test retrieval using the best-performing collection:

    python evaluate_retrieval.py

Run automated search tests:

    python -m pytest tests/test_search.py -v

The generated ChromaDB databases are stored locally
and are not committed to GitHub.

Run the indexing script before using search() on
a new machine.
