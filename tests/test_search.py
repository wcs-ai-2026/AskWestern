
import pytest

from src.askwestern.retrieve.search import search


def test_empty_question():
    """An empty question should return no results."""
    assert search("") == []


def test_whitespace_question():
    """Whitespace-only questions should return no results."""
    assert search("   ") == []


def test_invalid_k():
    """Invalid result counts should return no results."""
    assert search("When do classes start?", k=0) == []
    assert search("When do classes start?", k=-1) == []


def test_search_returns_five_results():
    """A normal question should return five results."""
    results = search("When do fall classes start?", k=5)

    assert len(results) == 5


def test_search_respects_k():
    """Search should return the requested number of chunks."""
    results = search("How do I apply for OSAP?", k=3)

    assert len(results) == 3


def test_result_fields():
    """Results should contain all required contract fields."""
    results = search("What are the residence fees?")

    required_fields = {
        "chunk_id",
        "text",
        "source_url",
        "title",
        "section",
        "collected_on",
        "source_type",
        "score",
    }

    for result in results:
        assert required_fields.issubset(result.keys())
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0


def test_relevant_source():
    """The correct source should appear for an OSAP question."""
    results = search("How do I apply for OSAP?", k=5)

    assert any(
        "ontario_student_assistance_program_osap"
        in result["source_url"]
        for result in results
    )
