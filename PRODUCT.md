# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are analysts, auditors, reviewers, and researchers working with reports and other PDF source documents. They need to identify useful claims, verify each claim against its exact source, and understand whether related claims across documents agree, conflict, or differ for explainable contextual reasons.

## Product Purpose

Fact Knowledge Layer turns PDF documents into a reviewable ledger of structured facts. Success means every extracted fact remains traceable to page-level verbatim evidence, unverified claims are exposed rather than hidden, and cross-document relationship decisions can be inspected and reproduced.

## Positioning

The product separates probabilistic extraction from deterministic verification and reasoning. The LLM proposes structured fact candidates; source alignment, normalization, relationship classification, and confidence reporting preserve an auditable boundary between model output and trusted evidence.

## Operating Context

Users upload PDF source documents, follow processing status, review extracted facts in a ledger, inspect the exact evidence passage and page reference for a selected fact, and examine deterministic relationships between facts. The application is also evaluated through its GitHub repository, saved sample output, and a short demonstration video.

## Capabilities and Constraints

- PDF ingestion preserves physical page numbers, optional printed page labels, and page-local character offsets.
- Each fact contains a subject, predicate, value, optional unit or currency, temporal scope, evidence quote, verification result, and separate confidence measures.
- Whitespace- or hyphenation-normalized quote matches recover the actual source substring for display.
- Unverified facts remain visible as failures but are excluded from relationship classification by default.
- Relationship candidates are blocked by canonical entity and predicate.
- Relationship classes are corroborates, contradicts, reconciled, and uncertain.
- Relationship decisions include a machine-readable ordered reasoning trace.
- Normalization and classification are deterministic; LLM access is isolated behind a provider adapter.
- Duplicate uploads are detected by document hash and can reuse existing work.
- The backend is FastAPI with SQLite and background processing through FastAPI BackgroundTasks.
- The frontend is React, TypeScript, Vite, Tailwind CSS, shadcn/Radix primitives, and Motion.
- The project intentionally does not use a graph database, vector database, RAG retrieval stack, multi-agent framework, Celery, or Redis.

## Brand Commitments

The product name is **Fact Knowledge Layer**. Its voice is precise, credible, quiet, intelligent, editorial, professional, information-dense, and deliberate. It should communicate source provenance, verifiable claims, exact evidence recovery, confidence, deterministic relationships, auditability, and traceability. It must not present itself as a cyberpunk security console, a marketing site, or a generic AI dashboard.

## Evidence on Hand

- Official assignment: `C:/Users/tanuj/Downloads/superjoin-vit-2026-assignment.pdf`
- Starter dataset archive: `C:/Users/tanuj/Downloads/starter-datasets.zip`
- Current working React application and FastAPI backend in this repository.
- No testimonials, customer logos, production usage claims, or externally validated performance benchmarks are available and none should be fabricated.
- Evaluation ground truth will be hand-labelled by the project owner; the application must not invent it.

## Product Principles

1. Evidence before assertion: a fact is useful only when its source can be inspected.
2. Honest uncertainty: failed verification and ambiguous comparisons remain visible.
3. Deterministic decisions: relationship labels must be reproducible from explicit checks.
4. Progressive disclosure: lead with the review task and reveal technical provenance on demand.
5. Provider independence: model choice may change without changing the evidence or reasoning contract.

## Accessibility & Inclusion

The web interface must support keyboard operation, visible focus, semantic status communication, sufficient contrast, reduced-motion preferences, and responsive use from mobile through desktop viewports.
