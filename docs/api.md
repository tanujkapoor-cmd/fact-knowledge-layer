# API Contract

The API is the stable boundary used by the React audit console and any future client. FastAPI also
publishes this contract interactively at `/docs`.

## Upload and processing

`POST /documents` accepts one multipart field named `file`. It hashes the immutable bytes before
processing. A new hash returns `202` with a queued document identifier; a known hash returns the
original identifier with `duplicate_reused: true`. Processing continues in a FastAPI background
task through ingestion, extraction, verification, normalization, and classification.

`GET /documents/{id}` reports the durable status and any failure reason. The in-memory status map
supports the required single-process deployment model, while SQLite remains the source of truth
returned by the API.

## Facts and evidence

`GET /documents/{id}/facts` returns both verified and rejected facts. Every item includes:

- the extracted subject, predicate, value, unit/currency, and temporal wording;
- one-based physical page and optional printed page label;
- the recovered verbatim source quote and page-local half-open offsets;
- verification method and measured similarity;
- separate extraction and evidence-verification confidence objects; and
- `classification_eligible`, which is false when evidence failed.

## Relationships

`GET /relationships` supports optional `classification` and `document_id` filters plus bounded
pagination. Every relationship embeds both complete facts, a classification confidence object,
reconciliation reasons, and the ordered machine-readable reasoning trace. This makes a decision
independently auditable without requesting additional resources.
