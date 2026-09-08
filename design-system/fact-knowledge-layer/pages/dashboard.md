# Dashboard Page Overrides

> **PROJECT:** Fact Knowledge Layer
> **Generated:** 2026-09-08 10:56:22
> **Page Type:** Evidence review workspace

> ⚠️ **IMPORTANT:** Rules in this file **override** the Master file (`design-system/MASTER.md`).
> Only deviations from the Master are documented here. For all other rules, refer to the Master.

---

## Page-Specific Rules

### Layout Overrides

- **Max Width:** 1240px
- **Grid:** Two-column intake area followed by full-width audit views

### Spacing Overrides

- **Content Density:** Medium-high — compact orientation, detailed review on demand

### Typography Overrides

- No overrides — use Master typography

### Color Overrides

- No overrides — use Master colors

### Component Overrides

- Keep upload, source guarantees, and pipeline sequence visible without scrolling on desktop.
- Keep connection settings collapsed by default so the product workflow remains primary.
- Use native safe components for document-derived values and source quotes.
- Treat verified, rejected, reconciled, and uncertain states as first-class outcomes.

---

## Page-Specific Components

- **Evidence contract:** Locates, quotes, and auditability guarantees beside the uploader.
- **Process strip:** Ingest → extract → verify → reason.
- **Guided empty states:** Explain the next action without inventing demo data.
- **Confidence badges:** Separate extraction, evidence, and classification confidence.

---

## Recommendations

- Keep motion subtle and respect reduced-motion preferences.
- Make the LLM boundary clear: extraction is model-assisted; verification and classification are auditable code.
- Prefer JSON export and reasoning traces over decorative charts.
- Never obscure failures; retain rejected evidence as a visible audit outcome.
