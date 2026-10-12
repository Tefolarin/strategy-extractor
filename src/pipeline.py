"""
pipeline.py

Turns an uploaded financial statement (10-K, annual report, etc.) into a
structured strategy brief: core strategy, top initiatives, and performance
drivers, grounded strictly in the document's own text.

Stages:
  1. extract_text   - pull raw text out of the PDF
  2. chunk_text     - split it into overlapping passages
  3. build_index     - embed each passage locally and index it in FAISS
  4. retrieve        - pull the passages most relevant to a set of strategy
                        questions (MD&A-style topics)
  5. synthesize       - send only those passages to Claude and ask for a
                        rigid, source-grounded executive summary

No step after (3) needs network access except (5), and (5) is the only step
that costs money or needs an API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import anthropic
import pdfplumber
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
TOP_K_PER_QUERY = 4

# These stand in for what an analyst would actually look for in an MD&A
# section. Each one pulls a different slice of the document into context.
RETRIEVAL_QUERIES = [
    "overarching corporate strategy and long-term priorities",
    "growth initiatives, new investments, and strategic projects",
    "revenue performance, margins, and key financial drivers",
    "risks, headwinds, and challenges facing the business",
]

SYSTEM_PROMPT = """You are a careful equity research analyst. You only use \
the excerpts you are given. You never add outside knowledge about the \
company, and you never guess at numbers that are not in the text. If the \
excerpts don't support a section, say so plainly instead of inventing \
content."""

USER_PROMPT_TEMPLATE = """Here are excerpts pulled from a company's \
financial filing:

---
{context}
---

Based strictly on the excerpts above, produce an executive brief with \
exactly these three sections:

1. **Core Strategy** - the firm's overarching strategic direction, in 2-3 \
sentences.
2. **Top Initiatives** - up to 3 concrete, actionable growth initiatives, \
each one sentence.
3. **Performance Drivers** - the main factors driving (or dragging on) \
financial performance, in 2-3 sentences.

If the excerpts don't clearly support one of these sections, say "Not \
clearly addressed in the provided excerpts" for that section instead of \
making something up."""


@dataclass
class AnalysisResult:
    strategy_brief: str
    chunks_used: int
    source_pages: int


def extract_text(pdf_path: str | Path) -> str:
    """Pull raw text out of every page of the PDF."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return "\n\n".join(pages)


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    # Drop near-empty chunks (headers, page numbers, table fragments)
    return [c for c in chunks if len(c.strip()) > 40]


def build_index(chunks: list[str]) -> FAISS:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return FAISS.from_texts(chunks, embeddings)


def retrieve(index: FAISS, queries: list[str] = RETRIEVAL_QUERIES, k: int = TOP_K_PER_QUERY) -> list[str]:
    seen: dict[str, None] = {}
    for query in queries:
        for doc in index.similarity_search(query, k=k):
            seen.setdefault(doc.page_content, None)
    return list(seen.keys())


def synthesize(api_key: str, context_chunks: list[str], model: str = "claude-haiku-5-5") -> str:
    client = anthropic.Anthropic(api_key=api_key)
    context = "\n\n---\n\n".join(context_chunks)
    message = client.messages.create(
        model=model,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(context=context)}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def run(pdf_path: str | Path, api_key: str) -> AnalysisResult:
    """End-to-end: PDF path in, structured strategy brief out."""
    text = extract_text(pdf_path)
    if not text.strip():
        raise ValueError(
            "No extractable text found in this PDF. It may be a scanned "
            "image without a text layer — OCR isn't wired up here."
        )

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("Document text was too short to analyze.")

    index = build_index(chunks)
    relevant = retrieve(index)
    brief = synthesize(api_key, relevant)

    return AnalysisResult(strategy_brief=brief, chunks_used=len(relevant), source_pages=page_count)
