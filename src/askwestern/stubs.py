"""Fake ``search()`` and ``answer()`` so the rest of AskWestern can be built now.

Placeholders for contracts 2 and 3 in ``CONTRACTS.md``, with the exact
signatures and return shapes of the real functions. Anything written against
these keeps working once ``retrieve/search.py`` and ``generate/answer.py`` land.

This is as dumb as it can be on purpose. There is no retrieval: ``search()``
returns the first ``k`` chunks in index order and the ``score`` values are
positional placeholders, not similarities. ``answer()`` always answers, citing
the top chunk, and never refuses. No files, no model, no network.

Chunk ``text`` is invented and runs under the real 300-500 word target; every
other field follows contract 1. Nothing here is a real fact about Western.

Run ``python src/askwestern/stubs.py`` to print one of each shape.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

__all__ = ["search", "answer", "FAKE_CHUNKS", "STUDENT_CENTRAL"]

# Fixed, so repeated calls return byte-identical records.
_COLLECTED_ON = "2026-11-08"

# Chunk records, contract 1. URLs are real pages from sources/sources.csv; the
# text is invented and marked so a raw result shown in a UI is not quotable.
FAKE_CHUNKS: List[Dict[str, Any]] = [
    {
        "chunk_id": "registrar-important-dates-001",
        "text": (
            "FAKE TEXT. The last day to drop a first-term half course without "
            "academic penalty is November 12. First-term full courses must be "
            "dropped by November 30."
        ),
        "source_url": "https://registrar.uwo.ca/resources/important_dates_and_deadlines.html",
        "title": "Important Dates and Deadlines",
        "section": "Fall/Winter 2026-27",
        "collected_on": _COLLECTED_ON,
        "source_type": "html",
    },
    {
        "chunk_id": "registrar-fees-refunds-001",
        "text": (
            "FAKE TEXT. Tuition for the fall term is due in full by the first "
            "day of classes in September. A refund schedule applies to courses "
            "dropped in the first six weeks."
        ),
        "source_url": "https://registrar.uwo.ca/student_finances/fees_refunds/index.html",
        "title": "Fees and Refunds",
        "section": "Payment Deadlines",
        "collected_on": _COLLECTED_ON,
        "source_type": "html",
    },
    {
        "chunk_id": "residence-fees-payment-001",
        "text": (
            "FAKE TEXT. Residence fees are billed in two instalments, one in "
            "August and one in December, and cover the room plus the meal plan "
            "attached to that building."
        ),
        "source_url": "https://residence.uwo.ca/applying/fees_and_payment",
        "title": "Residence Fees and Payment",
        "section": "Fee Schedule",
        "collected_on": _COLLECTED_ON,
        "source_type": "html",
    },
    {
        "chunk_id": "calendar-examinations-001",
        "text": (
            "FAKE TEXT. Final examinations are scheduled by the Registrar and "
            "the timetable is published roughly six weeks before the "
            "examination period."
        ),
        "source_url": (
            "https://westerncalendar.uwo.ca/PolicyPages.cfm?PolicyCategoryID=5"
            "&command=showCategory&SelectedCalendar=Live&ArchiveID="
        ),
        "title": "Academic Policy: Examinations",
        "section": "Final Examinations",
        "collected_on": _COLLECTED_ON,
        "source_type": "html",
    },
    {
        "chunk_id": "student-health-wellness-001",
        "text": (
            "FAKE TEXT. Student Health Services provides medical appointments, "
            "mental health counselling and immunization clinics on campus."
        ),
        "source_url": "https://www.uwo.ca/health/index.html",
        "title": "Health and Wellness",
        "section": "Services",
        "collected_on": _COLLECTED_ON,
        "source_type": "html",
    },
]

# Referral, contract 5, with the five fields contract 3 asks for. Only used for
# the one case search() cannot serve: a question with no words in it.
STUDENT_CENTRAL: Dict[str, Any] = {
    "contact_id": "registrar-student-central",
    "office": "Student Central (Office of the Registrar)",
    "contact_page": "https://registrar.uwo.ca/student_support/student_central/index.html",
    "email": "",
    "phone": "",
}


def search(question: str, k: int = 5) -> List[Dict[str, Any]]:
    """Fake retrieval. Contract 2.

    Returns ``min(k, index size)`` chunk records, each a copy of a contract-1
    chunk plus ``score`` (float in ``[0, 1]``, higher = closer).

    The order is index order and the scores step down by rank, so the shape and
    the sort are right while the ranking means nothing. An empty or
    whitespace-only ``question`` returns ``[]``. Never raises: a non-string
    question, or a ``k`` that is not a positive int, also returns ``[]``.
    """
    if not isinstance(question, str) or not question.strip():
        return []
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        return []

    hits = []
    for rank, chunk in enumerate(FAKE_CHUNKS[:k]):
        record = dict(chunk)
        record["score"] = round(0.9 - 0.1 * rank, 2)
        hits.append(record)
    return hits


def answer(question: str) -> Dict[str, Any]:
    """Fake end-to-end answering. Contract 3.

    Always returns the contract-3 dict and never raises. Always answers, citing
    the top chunk, so ``refused`` is false and ``referral`` is null -- except
    for an empty question, which has nothing to retrieve against and comes back
    refused with the Student Central referral.

    ``citations`` is always a subset of ``retrieved_ids``. ``latency_s`` is
    measured, not invented; it is just very small.
    """
    started = time.perf_counter()
    hits = search(question, k=5)

    if not hits:
        return {
            "answer": (
                "I need a question to work with. Try asking about deadlines, "
                "fees, residence or exams."
            ),
            "citations": [],
            "refused": True,
            "referral": dict(STUDENT_CENTRAL),
            "retrieved_ids": [],
            "latency_s": round(time.perf_counter() - started, 4),
        }

    top = hits[0]
    return {
        "answer": (
            "Stub answer for {question!r}. The real pipeline will write this "
            "from the cited page. [1]".format(question=question)
        ),
        "citations": [
            {
                "chunk_id": top["chunk_id"],
                "source_url": top["source_url"],
                "title": top["title"],
            }
        ],
        "refused": False,
        "referral": None,
        "retrieved_ids": [hit["chunk_id"] for hit in hits],
        "latency_s": round(time.perf_counter() - started, 4),
    }


if __name__ == "__main__":
    print(json.dumps(search("when is the drop deadline", k=3), indent=2))
    print(json.dumps(answer("when is the drop deadline"), indent=2))
