# AskWestern

A chatbot for Western students. You ask it something — a deadline, fees, program
requirements, residence, anything on Western's public sites — and it answers
using only official Western pages, with a link to where it found the answer. If
the answer isn't in our pages, it says so and points you to the right office
instead of guessing.

What we're aiming for by the tech summit:

- 80% of benchmark questions answered correctly, with the right source
- 90% of unanswerable questions handled properly ("I don't know" + a referral)
- 90% of prompt-injection attempts blocked
- answers in under 10 seconds

## Status

**Week 1. Stubs only; none of the real pipeline exists yet.**

`src/askwestern/stubs.py` provides fake `search()` and `answer()` with the exact
signatures and return shapes the real ones will have, so you can build and test
your own piece before the pipeline lands. It has no retrieval and no model
behind it — five hand-written paragraphs and positional scores. Every answer it
gives is invented. Nothing it says is a real fact about Western.

The Streamlit chat page and scoreboard come later. Today "running the app" means
running the stubs, as below.

## What you need

- **Python 3.11** — the version everyone on the team uses
- git

Check what you have:

```bash
python3.11 --version
```

No Python 3.11? On macOS: `brew install python@3.11`.

## Setup

```bash
git clone https://github.com/wcs-ai-2026/AskWestern.git
cd AskWestern
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate` instead.

Then make your own `.env`:

```bash
cp .env.example .env
```

You don't need to put anything in `.env` to run the stubs — they read no
environment variables. Fill it in when you start on a piece that needs a key.
`.env` is gitignored; never commit it.

## Run it

```bash
python src/askwestern/stubs.py
```

No `src/` directory? The stubs land on `main` with SCRUM-17. Until that merges,
pull them into your checkout with:

```bash
git checkout origin/SCRUM-17/stubs -- src
```

You should see two blocks of JSON: a `search()` result (three chunk records,
each with a `score`) and an `answer()` result (an answer string, one citation,
and `refused`, `referral`, `retrieved_ids`, `latency_s`). If you see those, your
setup is working.

## Use the stubs from your own code

The package lives under `src/`, so point Python at it:

```bash
PYTHONPATH=src python -c "from askwestern.stubs import search, answer; print(answer('when is the drop deadline')['citations'])"
```

In a script:

```python
from askwestern.stubs import search, answer

hits = search("when is the drop deadline", k=3)   # list of chunk records
result = answer("when is the drop deadline")      # the answer dict
```

Build against the shapes these return, not against this file — it gets deleted
once the real `search()` and `answer()` land, and anything written against the
shapes will keep working.

## Layout

```
AskWestern/
├── README.md
├── CONTRACTS.md           # the five formats — read this first
├── requirements.txt
├── .env.example
├── sources/
│   └── sources.csv        # the pages we're allowed to use
├── data/
│   └── seed/              # the 47 collected pages
├── eval/
│   └── benchmark.jsonl    # the question benchmark
└── src/
    └── askwestern/
        ├── __init__.py
        └── stubs.py       # fake search() and answer() — week 1
```

As the real pieces land they go in `src/askwestern/retrieve/search.py` and
`src/askwestern/generate/answer.py`.

## The contracts

Five formats the pieces use to talk to each other — chunk records, `search()`,
`answer()`, benchmark items and the referral directory. **Build against those,
not against someone else's code.**

They live in `CONTRACTS.md` at the repo root. Read it before you start on your
piece.

Changing a contract means a PR that edits that file, with the people affected
signing off before it merges.

## Who owns what

| Who | Owns |
| --- | --- |
| Matteo (lead dev) | repo rules, contracts, stubs, the LLM choice, `answer()`, citations, the "I don't know" + referral logic, the chat page, PR review |
| Ghanwa (ingestion) | the source list, seed pages, scraper, PDF parser, cleaning and dedupe, the contacts list |
| Tanya (retrieval) | chunking, embeddings, the Chroma index, `search()` |
| Ella (eval & security) | the question benchmark, the eval script, the attack set, the scoreboard |

One branch per Jira ticket, PRs reviewed by Matteo. Swapping anything in the
stack is fine if there's a reason — add a line to `DECISIONS.md` saying why.

## Scraping rules

Public Western pages only, nothing behind a login. Check `robots.txt`, wait at
least a second between requests, and use a user-agent that says this is the WCS
AskWestern project (`.env.example` sets both). Save the raw page and the date it
was collected, so answers can show an "as of" date. If a site doesn't allow
scraping, save those pages by hand and mark them as manual.

## Troubleshooting

**`python3.11: command not found`** — install it (`brew install python@3.11` on
macOS). Plain `python3` may be older; the team is on 3.11.

**`ModuleNotFoundError: No module named 'askwestern'`** — you're importing
without `PYTHONPATH=src`, or the venv isn't active. Run `source
.venv/bin/activate` and prefix with `PYTHONPATH=src`.

**`pip install` fails** — check the venv is active (your prompt should show
`.venv`). The stubs need no dependencies, so `python src/askwestern/stubs.py`
works even if the install didn't.
