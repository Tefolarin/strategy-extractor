"""
Streamlit app: upload a financial statement, get back its strategy,
initiatives, and performance drivers.

Run with:
    streamlit run app.py
"""

import tempfile
from pathlib import Path

import streamlit as st

from src.pipeline import run

st.set_page_config(page_title="Strategy Extractor", page_icon="\U0001F4CA", layout="centered")

st.title("Strategy Extractor")
st.caption(
    "Upload a 10-K or annual report. It reads the document itself, retrieves "
    "the passages that actually discuss strategy and performance, and asks "
    "Claude to summarize them — grounded in the text, not general knowledge "
    "about the company."
)

with st.sidebar:
    st.header("Anthropic API key")
    api_key = st.text_input(
        "Paste your key",
        type="password",
        help="Get one at console.anthropic.com. It's used only for this "
        "session's request and is never stored or logged.",
    )
    st.markdown("---")
    st.caption(
        "No key is saved anywhere — it lives in this browser tab only, "
        "for the life of this session."
    )

uploaded = st.file_uploader("Financial statement (PDF)", type=["pdf"])

analyze_clicked = st.button("Analyze", type="primary", disabled=not (uploaded and api_key))

if uploaded and not api_key:
    st.info("Add your Anthropic API key in the sidebar to run the analysis.")

if analyze_clicked and uploaded and api_key:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / uploaded.name
        pdf_path.write_bytes(uploaded.getvalue())

        with st.spinner("Reading document and building a local search index..."):
            try:
                result = run(pdf_path, api_key)
            except Exception as exc:  # surfaced to the user, not swallowed
                st.error(f"Couldn't complete the analysis: {exc}")
                st.stop()

        st.success(
            f"Analyzed {result.source_pages} pages, grounded on "
            f"{result.chunks_used} retrieved passages."
        )
        st.markdown(result.strategy_brief)
