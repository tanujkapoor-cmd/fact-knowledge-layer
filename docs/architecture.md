# Architecture Contract

This document fixes the dependency direction and correctness rules for the Fact Knowledge
Layer. Later phases may extend these components, but must not reverse the dependencies or
weaken the invariants.

## Components and dependency direction

```text
Streamlit UI -> FastAPI API -> pipeline orchestration
                                  |-> ingestion adapter (PyMuPDF)
                                  |-> extraction adapter (LLM)
                                  |-> evidence verifier
                                  |-> deterministic reasoning
                                  `-> persistence repositories (SQLite)
```

The domain models and deterministic reasoning code are at the center. They do not import
FastAPI, Streamlit, SQLAlchemy, PyMuPDF, or an LLM SDK. Infrastructure adapters convert
external data into validated domain objects before invoking deterministic logic.

## Processing lifecycle

```text
queued -> ingesting -> extracting -> verifying -> normalizing -> classifying -> completed
                                                                           `-> failed
```

1. Validate an uploaded PDF and calculate its SHA-256 hash.
2. Reuse an existing completed document when the hash already exists.
3. Extract text page by page while preserving one-based physical page numbers and offsets.
4. Ask the LLM adapter for schema-constrained candidate facts.
5. Verify every quote against its source page and recover the actual source substring.
6. Retain failed candidates with a reason, but exclude them from relationship classification.
7. Normalize verified facts with pure deterministic functions.
8. Block relationship candidates by canonical entity and predicate.
9. Classify candidates with ordered deterministic checks and persist the full reasoning trace.

## Evidence invariants

- Physical PDF page numbers are one-based.
- A printed page label is optional and never replaces the physical page number.
- Offsets are page-local, use Python slice semantics, and satisfy `start_offset < end_offset`.
- For verified evidence, `page.text[start_offset:end_offset]` equals the stored quote exactly.
- Normalized or fuzzy matching may locate a quote, but the stored quote is recovered from the
  source page and is therefore genuinely verbatim.
- A failed verification records its reason and is visible to users.

## Reasoning invariants

- Normalization and classification are deterministic and have no LLM dependency.
- Classification checks entity, predicate, normalized equality, and then explanatory context
  such as time, unit, currency, or scope before deciding contradiction.
- An LLM may only break an explicitly ambiguous entity tie or verbalize a completed decision.
- The LLM never selects or changes a relationship classification.
- Every relationship includes an ordered, machine-readable reasoning trace.
- Extraction, evidence-verification, and classification confidence remain separate scores.

## Runtime constraints

- FastAPI background work opens a new database session; request-scoped sessions are never
  reused after a response.
- The required in-memory status registry assumes a single API process. Deployment therefore
  uses one Uvicorn worker unless the status design is deliberately replaced in a future scope.
- SQLite uses foreign-key enforcement, a busy timeout, short transactions, and WAL mode for
  file-backed databases.
- Secrets and uploaded documents are never committed to Git.

## Phase boundaries

The project is implemented in the ten user-approved phases. Each phase must pass its relevant
tests, be committed separately, and stop for review. Deployment is an optional eleventh phase
after the required system is complete. No README is created by this implementation.
