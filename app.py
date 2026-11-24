"""AskWestern chat page.

    ./.venv/bin/python -m streamlit run app.py

Needs a built index (python build_index.py) and ANTHROPIC_API_KEY in .env.
"""

import os
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Importing this also loads .env.
from askwestern.generate.answer import DEFAULT_MODEL, answer  # noqa: E402

DB_PATH = BASE_DIR / "chroma_db"
COLLECTION = "askwestern"

st.set_page_config(page_title="AskWestern", page_icon="?", layout="centered")


def preflight():
    """Why the page can't work yet, if it can't.

    Deliberately not cached: both checks are cheap (a directory probe and a
    row count, no model load), and caching them means fixing the problem
    while the page is open leaves the error on screen until a restart.
    """
    problems = []

    if not DB_PATH.exists():
        problems.append(
            "**No search index.** Build it once, it takes about 20 seconds:\n\n"
            "```\npython build_index.py\n```"
        )
    else:
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(DB_PATH))
            count = client.get_collection(COLLECTION).count()
            if count == 0:
                problems.append(
                    f"**The index is empty** (collection `{COLLECTION}` has 0 "
                    "chunks). Rebuild it:\n\n```\npython build_index.py\n```"
                )
        except Exception as exc:
            problems.append(
                f"**Couldn't open the index** at `{DB_PATH.name}/`: {exc}\n\n"
                "Rebuild it with `python build_index.py`."
            )

    # Presence only - never render any part of the key.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        problems.append(
            "**No API key.** Put your Anthropic key in `.env`:\n\n"
            "```\nANTHROPIC_API_KEY=sk-ant-...\n```\n\n"
            "`.env.example` has the full list. `.env` is gitignored."
        )

    return problems


def render_sources(citations):
    """One clickable link per source page, deduplicated."""
    if not citations:
        return

    seen, sources = set(), []
    for citation in citations:
        url = citation.get("source_url", "")
        if url and url not in seen:
            seen.add(url)
            sources.append(citation)

    if not sources:
        return

    st.caption("Source" if len(sources) == 1 else "Sources")
    for citation in sources:
        st.link_button(
            citation.get("title") or citation["source_url"],
            citation["source_url"],
        )


def render_referral(referral):
    """The office to contact, copied from the directory."""
    if not referral:
        return

    lines = [f"**{referral.get('office', 'Student Central')}**"]

    page = referral.get("contact_page")
    if page:
        lines.append(f"[Contact page]({page})")

    phone = referral.get("phone")
    if phone:
        lines.append(f"Phone: {phone}")

    email = referral.get("email")
    if email:
        lines.append(f"Email: {email}")

    st.markdown("  \n".join(lines))


def render_details(result):
    """Collapsed by default - for the team, not for students."""
    with st.expander("Details"):
        st.caption(f"Model: {os.environ.get('ASKWESTERN_LLM_MODEL') or DEFAULT_MODEL}")
        st.caption(f"Answered in {result['latency_s']}s")
        retrieved = result.get("retrieved_ids") or []
        st.caption(f"Retrieved {len(retrieved)} chunks")
        if retrieved:
            st.code("\n".join(retrieved), language=None)


def render_result(result):
    if result["refused"]:
        # Refusing correctly is the designed behaviour, not an error.
        st.info(result["answer"])
        render_referral(result.get("referral"))
    else:
        st.write(result["answer"])
        render_sources(result["citations"])

    render_details(result)


problems = preflight()

st.title("AskWestern")
st.caption(
    "Answers from official Western pages, with a link to the page it used. "
    "It only knows the 47 pages we have collected, so it will often say it "
    "doesn't know and point you at the right office instead."
)

if problems:
    st.error("This page isn't ready yet:")
    for problem in problems:
        st.markdown(f"- {problem}")
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["question"])
    with st.chat_message("assistant"):
        render_result(turn["result"])

question = st.chat_input("Ask about deadlines, fees, programs, residence...")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching Western's pages..."):
            result = answer(question)
        render_result(result)

    st.session_state.history.append({"question": question, "result": result})
