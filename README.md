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
FKL_LLM_MODEL=gemini-3.7-flash
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

The final three-minute walkthrough still needs to be recorded and linked here before submission. It should show one PDF upload followed by these four saved cases:

1. corroboration across documents;
2. a genuine or likely contradiction;
3. a difference reconciled by time, scope, units, currency, data vintage, or rounding; and
4. an evidence-verification or provider failure retained with its reason.

This is deliberately marked as pending rather than linking to fabricated footage.

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
`gemini-3.5-flash-lite` and extraction prompt v3. The run retained 1,240 candidates: 1,019 with
verified source evidence and 221 rejected evidence matches. Deterministic blocking produced eight
relationships: one corroboration, four contradictions, one contextual reconciliation, and two
uncertain decisions.

These counts prove the complete pipeline and all four UI states execute; they are **not accuracy
scores**. In particular, some contradiction candidates expose extraction errors even though their
quotes are real. Human labels are still required before making quality claims. The full auditable
API export is in `sample_data/delhivery_sample_output.json`; the neutral scoring export is in
`evaluation/predictions.sample.json`.

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
- The human-labelled starter-dataset evaluation and demo-video link remain manual submission steps.

## Additional Notes

The architecture reflects a principle from enterprise AI systems: the model interprets unstructured material, while deterministic services and trusted source text decide what can be relied on. No graph database, vector database, RAG stack, multi-agent framework, Celery, or Redis is used because none is necessary for the supplied document scale.

Detailed contracts live in `docs/architecture.md`, `docs/api.md`, `docs/frontend.md`, and `docs/evaluation.md`. Credentials, uploaded PDFs, local databases, and evaluation results are excluded from Git.
