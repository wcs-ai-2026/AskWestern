"""Contract tests for answer(). No network: search and the model call are faked."""

import pytest

from src.askwestern.generate import answer as answer_mod
from src.askwestern.generate.answer import answer

CONTRACT_KEYS = {
    "answer",
    "citations",
    "refused",
    "referral",
    "retrieved_ids",
    "latency_s",
}

REFERRAL_KEYS = {"contact_id", "office", "contact_page", "email", "phone"}


def fake_hits(n=3):
    return [
        {
            "chunk_id": f"REG001_{i}",
            "text": f"Chunk {i} about tuition deadlines.",
            "source_url": "https://registrar.uwo.ca/student_finances/",
            "title": "Student Finances",
            "section": "",
            "collected_on": "2026-11-14",
            "source_type": "html",
            "score": 0.9 - 0.1 * i,
        }
        for i in range(n)
    ]


@pytest.fixture
def stub(monkeypatch):
    """Point answer() at fake retrieval and a scriptable model reply."""

    def apply(hits=None, reply=None, raises=None):
        monkeypatch.setattr(
            answer_mod, "search", lambda q, k=5: [] if hits is None else hits
        )

        def _model(question, chunks):
            if raises is not None:
                raise raises
            return reply

        monkeypatch.setattr(answer_mod, "_ask_model", _model)

    return apply


def test_contract_shape(stub):
    hits = fake_hits()
    stub(hits, {
        "knows": True,
        "answer": "Tuition is due on the first day of classes.",
        "cited_chunk_ids": ["REG001_0"],
    })

    result = answer("when is tuition due")

    assert set(result.keys()) == CONTRACT_KEYS
    assert isinstance(result["answer"], str) and result["answer"]
    assert isinstance(result["citations"], list)
    assert isinstance(result["refused"], bool)
    assert isinstance(result["retrieved_ids"], list)
    assert isinstance(result["latency_s"], float)
    assert result["refused"] is False
    assert result["referral"] is None


def test_citations_are_subset_of_retrieved(stub):
    hits = fake_hits()
    stub(hits, {
        "knows": True,
        "answer": "Answer.",
        "cited_chunk_ids": ["REG001_0", "REG001_2"],
    })

    result = answer("when is tuition due")

    cited = {c["chunk_id"] for c in result["citations"]}
    assert cited.issubset(set(result["retrieved_ids"]))
    assert cited == {"REG001_0", "REG001_2"}


def test_citation_has_only_contract_fields(stub):
    stub(fake_hits(), {
        "knows": True,
        "answer": "Answer.",
        "cited_chunk_ids": ["REG001_0"],
    })

    citation = answer("when is tuition due")["citations"][0]

    assert set(citation.keys()) == {"chunk_id", "source_url", "title"}


def test_fabricated_chunk_id_is_dropped(stub):
    """The model inventing an id must not reach the caller."""
    stub(fake_hits(), {
        "knows": True,
        "answer": "Answer.",
        "cited_chunk_ids": ["REG001_1", "TOTALLY_MADE_UP_42"],
    })

    result = answer("when is tuition due")

    cited = {c["chunk_id"] for c in result["citations"]}
    assert cited == {"REG001_1"}
    assert "TOTALLY_MADE_UP_42" not in str(result["citations"])


def test_only_fabricated_ids_becomes_a_refusal(stub):
    """If nothing it cited was real, it does not get to claim an answer."""
    stub(fake_hits(), {
        "knows": True,
        "answer": "Confident but uncited.",
        "cited_chunk_ids": ["NOPE_1"],
    })

    result = answer("when is tuition due")

    assert result["refused"] is True
    assert result["citations"] == []
    assert result["referral"] is not None


def test_model_does_not_know(stub):
    stub(fake_hits(), {
        "knows": False,
        "answer": "I don't know - that isn't in the pages I have.",
        "cited_chunk_ids": [],
    })

    result = answer("how do I appeal a parking ticket")

    assert result["refused"] is True
    assert result["citations"] == []
    assert REFERRAL_KEYS.issubset(result["referral"].keys())


def test_no_hits_refuses_and_cites_nothing(stub):
    stub(hits=None, reply=None)

    result = answer("something with no match at all")

    assert result["refused"] is True
    assert result["citations"] == []
    assert result["retrieved_ids"] == []
    assert result["referral"] is not None


@pytest.mark.parametrize("question", ["", "   ", "\n\t "])
def test_empty_question(stub, question):
    stub(fake_hits(), {"knows": True, "answer": "x", "cited_chunk_ids": []})

    result = answer(question)

    assert set(result.keys()) == CONTRACT_KEYS
    assert result["refused"] is True
    assert result["citations"] == []
    assert result["referral"] is not None


def test_failure_returns_contract_shape_without_raising(stub):
    stub(fake_hits(), raises=RuntimeError("API down"))

    result = answer("when is tuition due")

    assert set(result.keys()) == CONTRACT_KEYS
    assert result["refused"] is True
    assert result["citations"] == []
    assert result["answer"]
    assert result["referral"]["contact_id"] == "registrar-student-central"


def test_referral_is_copied_from_the_directory(stub):
    stub(hits=None, reply=None)

    referral = answer("I have a question about OSAP and financial aid")["referral"]
    contacts = answer_mod._contacts()
    match = next(
        c for c in contacts if c["contact_id"] == referral["contact_id"]
    )

    for field in REFERRAL_KEYS:
        assert referral[field] == match.get(field, "")


def test_answer_text_is_never_empty(stub):
    stub(fake_hits(), {"knows": True, "answer": "   ", "cited_chunk_ids": ["REG001_0"]})

    assert answer("when is tuition due")["answer"].strip()


def test_failure_after_search_still_reports_retrieved_ids(stub):
    """A model failure must not erase what retrieval found - the eval reads it."""
    hits = fake_hits()
    stub(hits, raises=RuntimeError("API down"))

    result = answer("when is tuition due")

    assert result["refused"] is True
    assert result["citations"] == []
    assert result["retrieved_ids"] == [c["chunk_id"] for c in hits]
