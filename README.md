# Strategy Extractor

Upload a company's 10-K or annual report. Get back its core strategy, top
growth initiatives, and performance drivers — grounded in what the document
actually says, not general knowledge about the company.

## The Business Problem

Reading a 10-K to build a competitive profile is a multi-hour task: wading
through hundreds of pages to find the handful of paragraphs in the
Management Discussion and Analysis section that actually describe where the
company is headed and why its numbers moved. Strategy and corporate
development teams do this constantly, for every company they track.

## The Technical Solution

A retrieval-augmented generation (RAG) pipeline, not a document summarizer:

1. **Extract** — `pdfplumber` pulls the raw text out of the uploaded PDF.
2. **Chunk** — the text is split into overlapping passages
   (`langchain-text-splitters`), so no single idea gets cut in half at a
   chunk boundary.
3. **Embed & index** — each passage is embedded locally with a small
   sentence-transformers model and indexed in FAISS. This runs entirely on
   your own machine — no data leaves it at this stage.
4. **Retrieve** — the passages most relevant to a fixed set of strategy
   questions (overarching strategy, growth initiatives, performance
   drivers, risks) are pulled out of the index.
5. **Synthesize** — *only those retrieved passages*, not the whole
   document, are sent to Claude Haiku with a prompt that explicitly
   forbids adding outside knowledge. If the excerpts don't support a
   section, the model says so instead of inventing one.

Steps 1–4 need no API key and cost nothing. Step 5 is the only step that
calls out to a paid API.

## Running It

```bash
pip install -r requirements.txt
streamlit run app.py
```

Paste your own Anthropic API key into the sidebar (get one at
[console.anthropic.com](https://console.anthropic.com)) — it's used for
that session's request only and is never stored or logged anywhere. The
app has nothing to configure beyond that.

### Trying it on a real filing

The app works on any financial statement PDF. To try it on something real
rather than a toy example, download any public company's 10-K yourself —
for example, Alphabet's:

```bash
python scripts/fetch_sample_filing.py
```

This saves a real 10-K to `data/sample_filing.pdf` (gitignored — filings
like this aren't something this repo redistributes). Then upload that file
in the app. You can point the script at any other public 10-K PDF with
`--url`.

## Repository Structure

```
├── app.py                        # Streamlit UI
├── src/
│   └── pipeline.py                # extract -> chunk -> embed -> retrieve -> synthesize
├── scripts/
│   └── fetch_sample_filing.py     # grabs a real public 10-K to test against
├── data/                          # downloaded/uploaded filings (not committed)
├── requirements.txt
└── README.md
```

## Notes

- Embeddings run locally (sentence-transformers), so only the handful of
  retrieved passages — not the full filing — are ever sent to the Anthropic
  API.
- Works on filings with a text layer. A scanned filing with no embedded
  text (image-only) won't extract anything — OCR isn't wired up here.
- The retrieval queries are tuned for MD&A-style strategy language; it'll
  work on most annual reports and 10-Ks without changes, but a very
  differently structured document may need the query list in
  `src/pipeline.py` adjusted.

---
Built by [Tosin Folarin](https://www.linkedin.com/in/folarintosin/) — strategy and product leader across payments, card products, and management consulting.
