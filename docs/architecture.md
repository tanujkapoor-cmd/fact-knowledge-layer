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

## Extraction boundary

The application depends on a provider-neutral `FactExtractionAdapter`. The OpenAI implementation
uses schema-constrained Pydantic output, but its response remains an untrusted candidate until the
evidence verifier accepts it. PDF page text is sent as source data with its physical page number;
the model is instructed not to follow instructions embedded in that text.

Pages are batched without splitting a physical page. Batch limits are configurable and do not
depend on document names or expected schemas. Each returned page number must belong to the batch
the model received.

Evidence alignment runs in this order:

1. Exact substring match.
2. Whitespace and line-hyphenation-normalized match.
3. Conservative fuzzy alignment for sufficiently long quotes.
4. Explicit failure with a reason.

Every successful method maps back to the original page offsets. The stored quote is always sliced
from the original extracted page text, even when normalized or fuzzy alignment found it.

## Deterministic normalization

Normalization is a pure transformation with a versioned contract. It canonicalizes entity and
predicate comparison keys, converts supported scales and physical units with `Decimal` arithmetic,
and parses common reporting periods into inclusive date boundaries. Unknown text, units, and date
phrases remain explicit rather than being guessed.

Currency aliases may be canonicalized without an exchange rate. Cross-currency conversion occurs
only when the caller supplies a dated rate table and target currency. Rates use a documented
`rates_to_base` convention, so the same fact and rate table always yield the same amount. The fiscal
year start month is configuration (`4` for the supplied Indian reporting context), not inferred from
a filename or hidden global state.

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

The classifier emits candidates only inside an exact canonical entity-and-predicate block and,
by default, only across different documents. Its trace always contains the complete ordered
decision tree. Exact same representations corroborate; equivalent values converted from different
units or currencies reconcile; different periods or scopes reconcile unequal values. Missing or
incompatible comparison context is uncertain. A contradiction is emitted only after every
deterministic context check has failed to explain unequal values.

## Confidence contracts

Confidence is deliberately plural. Extraction confidence reports the fraction of explicit
structured-contract checks passed and warns that it is not a truth estimate. Evidence confidence
is the measured source-alignment similarity (or zero for a failed quote). Classification confidence
is the fraction of applicable trace checks resolved conclusively without a judgment-required
outcome. Skipped checks are not counted. These scores are never averaged into a single number.

## Runtime constraints

- FastAPI background work opens a new database session; request-scoped sessions are never
  reused after a response.
- The required in-memory status registry assumes a single API process. Deployment therefore
  uses one Uvicorn worker unless the status design is deliberately replaced in a future scope.
- SQLite uses foreign-key enforcement, a busy timeout, short transactions, and WAL mode for
  file-backed databases.
- Secrets and uploaded documents are never committed to Git.

## Persistence and incremental processing

SQLite stores immutable document hashes, page text and offsets, extracted facts (including failed
evidence), normalized payloads, and deterministic relationship traces. Relationships use a unique
canonical fact-pair key, so processing a new document compares it with eligible existing facts but
does not duplicate earlier decisions. A failed background run records the exception type and
message on the document instead of silently disappearing.

## Phase boundaries

The project is implemented in the ten user-approved phases. Each phase must pass its relevant
tests, be committed separately, and stop for review. Deployment is an optional eleventh phase
after the required system is complete. No README is created by this implementation.

## Verification boundary

The final acceptance suite maps directly to the required classifier outcomes, all four contextual
reconciliation reasons, unresolved comparisons, complete ordered traces, fabricated-quote
rejection, and classification exclusion for failed evidence. An AST guard covers the complete
reasoning package so an LLM SDK cannot be introduced there accidentally.
