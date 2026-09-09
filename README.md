# Fact Knowledge Layer

Fact Knowledge Layer turns PDF reports into an auditable ledger of structured facts. An LLM proposes candidate facts, but deterministic code verifies every quote against the source page, normalizes comparable values, and classifies cross-document relationships with a machine-readable reasoning trace.

The design goal is simple: **no claim without a trail**.

## Setup and Run Instructions

Requirements: Python 3.11-3.14, Node.js 20+, and a Gemini or OpenAI API key.

```bash
git clone https://github.com/tanujkapoor-cmd/fact-knowledge-layer.git
cd fact-knowledge-layer
python -m venv .venv
```

Activate the virtual environment, then install the backend:

```bash
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set one provider key. The default configuration uses Gemini:

```dotenv
FKL_LLM_PROVIDER=gemini
FKL_LLM_MODEL=gemini-3.5-flash-lite
FKL_GEMINI_API_KEY=your_key_here
```

Start the API:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the React interface:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Interactive API documentation is at `http://127.0.0.1:8000/docs`.

Run the verification suite with:

```bash
pytest
cd frontend && npm run lint && npm run build
```

## Video Demo

**Video link placeholder:** `[PASTE THE FINAL PUBLIC VIDEO URL HERE]`

The recording must be three minutes or less. A timed screen plan and exact narration are in
[`docs/video-demo-script.md`](docs/video-demo-script.md). It covers a live PDF upload and the four
cases required by the assignment:

1. corroboration across documents;
2. a genuine or likely contradiction;
3. a difference reconciled by time, scope, units, currency, data vintage, or rounding; and
4. an evidence-verification or provider failure retained with its reason.

The four audited examples used in the recording are saved in
[`sample_data/verified_demo_cases.json`](sample_data/verified_demo_cases.json). Replace the link
placeholder above after recording; do not submit with the placeholder unchanged.

## Interface Screenshots

> **Screenshot placeholder 1 — Upload and source register**

Add a full-width image showing a PDF selected or processing in the left source register, with the
processing status and page checkpoint visible. This demonstrates arbitrary PDF upload, background
processing, and incremental progress.

> **Screenshot placeholder 2 — Fact ledger and evidence dossier**

Add an image with one fact selected in the centre ledger and the right evidence panel open. Make
the physical page, printed page label, verbatim quote, offsets, verification method, provenance,
and separate confidence values readable.

> **Screenshot placeholder 3 — Relationship decision trace**

Add an image of the relationship explorer filtered to `reconciled` or `corroborates`, showing both
facts and the ordered deterministic checks. This is the clearest proof that the LLM does not choose
the relationship label.

> **Screenshot placeholder 4 — Honest failure handling**

Add an image of an excluded fact or failed upload with its precise reason visible. Prefer the saved
unsupported-incorporation example: its quote exists, but the quote does not support that predicate,
so it is excluded from relationship classification.

## Approach

```text
React evidence desk -> FastAPI -> background document pipeline
                                      |-> PyMuPDF page ingestion
                                      |-> provider-isolated LLM extraction
                                      |-> exact/normalized/fuzzy quote recovery
                                      |-> deterministic normalization
                                      |-> deterministic relationship classifier
                                      `-> SQLite evidence and trace store
```

### Evidence before reasoning

PyMuPDF extracts each physical page independently. The system preserves its one-based physical PDF page number, an optional printed page label, document offsets, and page-local offsets. The LLM must return a concise evidence quote and physical page number. A quote enters reasoning only after the verifier finds it on that page; normalized whitespace or de-hyphenation matches are mapped back to the actual source substring so the displayed evidence remains verbatim.

Failed verification is not deleted. It remains visible as a failed fact with a reason and zero evidence-verification confidence, but is excluded from relationship classification.

### Probabilistic extraction, deterministic decisions

The extraction adapter supports Gemini and OpenAI structured output behind the same Pydantic contract. The LLM proposes subject, predicate, value, unit/currency, temporal scope, reporting scope, data vintage, quote, and page.

`backend/reasoning/normalize.py` and `backend/reasoning/classify.py` contain no LLM calls. They canonicalize explicitly configured aliases, parse reporting periods, convert known units using `Decimal`, and compare facts in a fixed order. Relationship candidates are blocked by canonical entity and predicate instead of comparing every fact to every other fact.

`config/aliases.example.json` contains a small reusable starter vocabulary for common financial
and operating metrics. Teams can replace or extend it without modifying reasoning code.

The classifier checks entity, predicate, normalized value, written precision/rounding, time, data vintage, unit, currency, and scope. It returns `corroborates`, `contradicts`, `reconciled`, or `uncertain`, together with every ordered check. An LLM is permitted only to resolve a bounded set of near-name entity ties; it never chooses the relationship label.

### Honest confidence and recovery

The API never combines confidence into one unexplained score:

- extraction confidence measures structured-contract compliance;
- evidence confidence measures source alignment; and
- classification confidence measures how many applicable checks were deterministic.

LLM calls use bounded exponential backoff. Each successful page batch persists facts and a checkpoint, so a retry can continue from compatible work after a transient provider failure. Duplicate completed uploads reuse their SHA-256-addressed result; a duplicate failed upload can explicitly restart or resume.

### API

- `POST /documents` uploads a PDF; add `?retry_failed=true` to retry the same failed bytes.
- `GET /documents/{id}` returns status, failure details, retry count, and checkpoint progress.
- `GET /documents/{id}/facts` returns facts with evidence and separate confidence scores.
- `GET /relationships` returns filterable decisions with both facts and the full trace.

## Evaluation

The repository intentionally does not invent ground truth. After a reviewer hand-labels an exhaustive page scope and selected relationship pairs, run:

```bash
python -m evaluation.export_predictions \
  --api-base http://127.0.0.1:8000 \
  --document DOCUMENT_ID --format evaluation \
  --output evaluation/predictions.json

python -m evaluation.run_eval \
  --ground-truth evaluation/ground_truth.json \
  --predictions evaluation/predictions.json \
  --output evaluation/results/eval_results.json
```

The harness reports extraction precision/recall, exact-evidence-quote rate, and a four-class relationship confusion matrix with an explicit `missing` prediction column. See `docs/evaluation.md` for the label contract.

### Starter-dataset smoke run

On 9 September 2026, all three Delhivery starter PDFs completed with a real Gemini key using
`gemini-3.5-flash-lite` and extraction prompt v4. The clean run retained 2,298 candidates. Evidence
alignment verified 1,812 quotes; 1,806 facts were eligible for comparison and six aligned quotes
were separately excluded because they did not semantically support an incorporation-date claim.
Deterministic blocking produced 210 cross-document relationships: three corroborations, 143
contextual reconciliations, and 64 uncertain decisions. A false contradiction caused by an entity
suffix collision was found during manual review and fixed rather than presented as a success.

The hand-labelled set contains 15 facts and eight relationship pairs. The current result is 100%
recall and an exact-quote rate of 100% on those labels, with 7/8 relationship decisions correct. The
reported extraction precision of 13.5% is deliberately conservative because every additional
verified candidate on the selected dense pages counts as a false positive. The one missing
relationship is a likely contradiction inside one PDF; production relationship generation is
intentionally cross-document only. These are prototype measurements, not general accuracy claims.

The full API export is in `sample_data/delhivery_sample_output.json`, the evaluation inputs are in
`evaluation/ground_truth.json` and `evaluation/predictions.corrected.json`, and machine-readable
results are in `evaluation/results/eval_results.json`.

## Deployment

Live demo: **https://fact-knowledge-layer-w8jv.onrender.com/**

API documentation: **https://fact-knowledge-layer-w8jv.onrender.com/docs**

The included multi-stage `Dockerfile` builds the React client and serves it from the FastAPI process. `render.yaml` defines a single-worker Render service, matching the assignment's simple in-memory background-status constraint. Set `FKL_GEMINI_API_KEY` in the host's secret environment variables—never commit it.

SQLite on a free ephemeral container is suitable for a short demonstration but not durable production storage. Attach a persistent disk at `/data` or use a managed relational database for longer-lived deployment.

## Limitations and Next Steps

- Scanned/image-only PDFs need OCR; the current parser expects extractable text.
- Multi-column and chart-heavy pages can produce imperfect reading order.
- Entity aliases are conservative and externally configured; the bounded LLM tie-break can still be wrong.
- Currency conversion requires an explicit dated rate table and is not guessed from current market data.
- Background tasks and the status dictionary assume one Uvicorn worker; a durable job queue would be needed at larger scale.
- Free-tier model capacity can return transient `503` responses. Retries and checkpoints preserve the failure honestly, but cannot create provider capacity.
- Relationship candidate generation intentionally compares facts across different documents. The
  manually validated same-document employee-count discrepancy is therefore recorded as a known
  missing relationship rather than silently injected into the production result.
- The final demo-video URL and four UI screenshots are submission-owner placeholders in this README.

## Additional Notes

The architecture reflects a principle from enterprise AI systems: the model interprets unstructured material, while deterministic services and trusted source text decide what can be relied on. No graph database, vector database, RAG stack, multi-agent framework, Celery, or Redis is used because none is necessary for the supplied document scale.

Detailed contracts live in `docs/architecture.md`, `docs/api.md`, `docs/frontend.md`, and `docs/evaluation.md`. Credentials, uploaded PDFs, local databases, and evaluation results are excluded from Git.
