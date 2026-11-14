# Evaluation

Every week, `run_eval.py` sends each question in `benchmark.jsonl` through `answer()`, scores the output with the six metrics below, and saves a dated results file in `eval/results/`. The scoreboard charts these scores over the semester.

All scores use only fields from `CONTRACTS.md`: the benchmark item (contract 4), the `answer()` output (contract 3), and `chunks.jsonl` (contract 1) for looking up a chunk's URL or text.

## Summary

| Metric | Questions scored | A question passes when | Owner |
| --- | --- | --- | --- |
| Hit rate | answerable | The expected page is in the top 5 retrieved chunks | Tanya |
| Correctness | answerable | The answer matches the expected answer | Ella |
| Faithfulness | answerable, not refused | Scored 0–1: share of the answer's claims supported by the retrieved chunks | Matteo |
| Citation accuracy | answerable | The expected page is one of the citations | Ella |
| Refusal rate | unanswerable | The bot says it doesn't know | Matteo |
| Referral accuracy | unanswerable | The bot refers the student to the expected contact | Matteo |

Each score is reported as a percentage with the count, e.g. `18/23 = 78%`. Faithfulness is reported as the average score.

## Summit targets

| Target | Counts as a pass when |
| --- | --- |
| 80%+ of questions answered correctly with the right source | Correctness **and** citation accuracy both pass |
| 90%+ of unanswerable questions handled properly | Refusal **and** referral accuracy both pass |

## Metrics

### 1. Hit rate

Did search find the right page?

- **Scored on:** `answerable` questions
- **Pass:** `expected_source_url` matches the `source_url` of any chunk in `retrieved_ids` (top 5). Look up each chunk's URL in `chunks.jsonl`.

### 2. Correctness

Is the answer right?

- **Scored on:** `answerable` questions
- **Pass:** An LLM judge compares `answer` with `expected_answer` and says it has the key facts (dates, amounts, names, conditions) without contradicting them. The wording doesn't need to match.
- **Fail:** The bot refuses (`refused: true`), or the answer is wrong or missing key facts.
- The judge model, prompt and temperature (0) stay fixed between runs so weekly scores can be compared.

### 3. Faithfulness

Does the answer stick to our pages, or is it made up?

- **Scored on:** `answerable` questions where `refused` is `false`
- **Score:** Ragas faithfulness, from 0 to 1: the share of claims in `answer` that are supported by the text of the `retrieved_ids` chunks. The reported number is the average.
- An answer can be correct but not faithful, if it came from the model's own knowledge instead of our pages. This metric catches that.

### 4. Citation accuracy

Does it link to the right page?

- **Scored on:** `answerable` questions
- **Pass:** `expected_source_url` matches one of `citations[].source_url`.
- **Fail:** The bot refuses (no citations), or none of the citations match.

### 5. Refusal rate

Does it say "I don't know" when the answer isn't in our pages?

- **Scored on:** `unanswerable` questions
- **Pass:** `refused` is `true`.
- Attacks in `attacks.jsonl` also set `refused`, but they're scored separately as the attack block rate.

### 6. Referral accuracy

Does it send the student to the right office?

- **Scored on:** `unanswerable` questions
- **Pass:** `referral.contact_id` equals `expected_referral`.
- **Fail:** `referral` is `null`, or it names a different contact.
