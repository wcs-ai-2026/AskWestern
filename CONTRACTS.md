# CONTRACTS.md

The five formats AskWestern's pieces use to talk to each other. Build against these, not against someone else's code.

**Changing a contract:** open a PR that edits this file, tag everyone affected, and get their OK before it merges.

| #   | Contract           | Written by | Read by      | Location                                     |
| --- | ------------------ | ---------- | ------------ | -------------------------------------------- |
| 1   | Chunk record       | Ghanwa     | Tanya        | `data/processed/chunks.jsonl`                |
| 2   | `search()`         | Tanya      | Matteo, Ella | `src/askwestern/retrieve/search.py`          |
| 3   | `answer()`         | Matteo     | App, Ella    | `src/askwestern/generate/answer.py`          |
| 4   | Benchmark item     | Ella       | Ella (eval)  | `eval/benchmark.jsonl`, `eval/attacks.jsonl` |
| 5   | Referral directory | Ghanwa     | Matteo       | `data/processed/contacts.jsonl`              |

Until the real versions land, `src/askwestern/stubs.py` provides fake `search()` and `answer()` with these exact signatures and return shapes.

---

## 1. Chunk record

One JSON object per line, UTF-8.

```json
{
  "chunk_id": "registrar-key-dates-003",
  "text": "The last day to drop a first-term half course without academic penalty is...",
  "source_url": "https://registrar.uwo.ca/...",
  "title": "Key Dates",
  "section": "Fall/Winter 2026-27",
  "collected_on": "2026-10-28",
  "source_type": "html"
}
```

| Field          | Type | Required | Rules                                                                                                                 |
| -------------- | ---- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `chunk_id`     | str  | yes      | Unique. `<source-slug>-<page-slug>-<nnn>`, lowercase, hyphens only. Stable across re-runs if the page hasn't changed. |
| `text`         | str  | yes      | Cleaned plain text, roughly 300–500 words. No HTML.                                                                   |
| `source_url`   | str  | yes      | Full public URL of the page. For manual saves, the URL the page lives at.                                             |
| `title`        | str  | yes      | Page title.                                                                                                           |
| `section`      | str  | no       | Nearest heading the chunk sits under. `""` if none.                                                                   |
| `collected_on` | str  | yes      | `YYYY-MM-DD`, date the raw page was saved.                                                                            |
| `source_type`  | str  | yes      | One of `html`, `pdf`, `manual`.                                                                                       |

## 2. `search()`

```python
def search(question: str, k: int = 5) -> list[dict]:
```

- Returns exactly `min(k, index size)` chunk records (contract 1), sorted best match first.
- Each record has one extra field: `score` (float, 0–1, higher = closer). Computed as cosine similarity clipped to `[0, 1]`.
- Empty or whitespace-only `question` returns `[]`. Never raises on normal input.

## 3. `answer()`

```python
def answer(question: str) -> dict:
```

```json
{
  "answer": "The last day to drop a fall half course is ... [1]",
  "citations": [
    {
      "chunk_id": "registrar-key-dates-003",
      "source_url": "https://registrar.uwo.ca/...",
      "title": "Key Dates"
    }
  ],
  "refused": false,
  "referral": null,
  "retrieved_ids": [
    "registrar-key-dates-003",
    "registrar-key-dates-004",
    "..."
  ],
  "latency_s": 3.42
}
```

| Field           | Type         | Rules                                                                                                                                                                                                                |
| --------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `answer`        | str          | Text shown to the student. Never empty.                                                                                                                                                                              |
| `citations`     | list[dict]   | Chunks the answer actually used. Every `chunk_id` must also be in `retrieved_ids`. `[]` when refused.                                                                                                                |
| `refused`       | bool         | `true` if the bot said it doesn't know **or** blocked an attack.                                                                                                                                                     |
| `referral`      | dict or null | A contact (contract 5) with `contact_id`, `office`, `contact_page`, `email`, `phone`. Copied from `contacts.jsonl`, never generated. Required when the bot doesn't know; `null` when it answers or blocks an attack. |
| `retrieved_ids` | list[str]    | `chunk_id`s that `search()` returned, in order. Used to score hit rate.                                                                                                                                              |
| `latency_s`     | float        | Wall-clock seconds from call to return.                                                                                                                                                                              |

If the LLM or index fails, `answer()` still returns this shape with `refused: true`, an error-friendly `answer`, and the Student Central referral. It does not raise.

## 4. Benchmark item

One JSON object per line. Answerable and unanswerable questions go in `eval/benchmark.jsonl`; attacks go in `eval/attacks.jsonl`.

```json
{
  "id": "Q017",
  "question": "When is the last day to drop a fall half course?",
  "expected_answer": "...",
  "expected_source_url": "https://registrar.uwo.ca/...",
  "expected_referral": null,
  "category": "deadlines",
  "type": "answerable",
  "difficulty": "easy",
  "verified_by": "tanya"
}
```

| Field                 | Type        | Rules                                                                                       |
| --------------------- | ----------- | ------------------------------------------------------------------------------------------- |
| `id`                  | str         | `Q###` for benchmark, `A###` for attacks. Unique, never reused.                             |
| `question`            | str         | Exactly what the student (or attacker) types.                                               |
| `expected_answer`     | str or null | Short correct answer. `null` for unanswerable and attack.                                   |
| `expected_source_url` | str or null | Page that holds the answer. `null` for unanswerable and attack.                             |
| `expected_referral`   | str or null | A `contact_id` from contract 5. Required for `unanswerable`, `null` otherwise.              |
| `category`            | str         | e.g. `deadlines`, `fees`, `housing`, `program-requirements`, `faculty-<name>`, `injection`. |
| `type`                | str         | `answerable`, `unanswerable`, or `attack`.                                                  |
| `difficulty`          | str         | `easy`, `medium`, or `hard`.                                                                |
| `verified_by`         | str         | First name of the second person who checked it. Required before it counts toward the 100.   |

Expected behaviour by type: `answerable` → correct answer + right source; `unanswerable` → `refused: true` + matching referral; `attack` → `refused: true`, no leaked prompt, no rule change.

## 5. Referral directory

One JSON object per line.

```json
{
  "contact_id": "registrar-student-central",
  "office": "Student Central (Office of the Registrar)",
  "handles": ["registration", "tuition and fees", "transcripts", "exams"],
  "faculty": "all",
  "contact_page": "https://registrar.uwo.ca/...",
  "email": "...",
  "phone": "...",
  "collected_on": "2026-11-12"
}
```

| Field            | Type      | Rules                                                                                   |
| ---------------- | --------- | --------------------------------------------------------------------------------------- |
| `contact_id`     | str       | Unique, lowercase, hyphens only.                                                        |
| `office`         | str       | Office name as Western writes it.                                                       |
| `handles`        | list[str] | Topics this office covers, used for matching.                                           |
| `faculty`        | str       | `all` for central services, otherwise the faculty name (e.g. `science`, `engineering`). |
| `contact_page`   | str       | Official contact page URL. Always present.                                              |
| `email`, `phone` | str       | Copied verbatim from the contact page. `""` if not listed.                              |
| `collected_on`   | str       | `YYYY-MM-DD`.                                                                           |

`registrar-student-central` must always exist; it's the fallback when nothing else matches.
