# Three-minute submission video

Keep the final recording between 2:40 and 2:55. Use the local app with the completed starter-data
database so the results are already available. Keep the repository open in a second tab and enlarge
the browser to at least 1440 px. Do not show `.env`, the Gemini key, Render environment variables,
or any secret-bearing terminal output.

## Before recording

1. Start the backend and React UI using the README commands.
2. Confirm the three starter documents are visible and the relationship filters have results.
3. Keep `sample_data/verified_demo_cases.json` open in GitHub or VS Code as a fallback for the
   manually validated contradiction and handled failure.
4. Prepare a small, text-based PDF for the live upload. Do not wait for a 100-page extraction during
   the recording.
5. Close personal tabs and notifications; zoom so evidence quotes and traces are readable.

## Exact walkthrough and narration

### 0:00–0:18 — Repository and problem

**On screen:** Show the GitHub repository title, then scroll just enough to show the architecture
summary and live-demo link.

**Say:** “This is my Fact Knowledge Layer for Superjoin. It accepts unseen PDFs, extracts atomic
facts, grounds each fact in its source page, and explains cross-document relationships. The design
principle is simple: no claim without a trail.”

### 0:18–0:42 — Upload and background processing

**On screen:** Open the application, upload the prepared small PDF, and point to its changing status
and page progress in the source register. Then select one of the completed starter documents.

**Say:** “I upload a PDF through React. FastAPI hashes it for duplicate reuse and processes it in the
background. PyMuPDF preserves physical pages, printed labels, and offsets. Extraction runs in page
batches, with checkpoints so a transient model failure does not discard completed work.”

### 0:42–1:08 — Facts and exact evidence

**On screen:** Select a verified fact. In the evidence dossier, point to the claim, verbatim source
quote, physical page, printed label, offsets, and the two fact confidence values.

**Say:** “Gemini proposes facts through a strict Pydantic schema, but is not trusted for grounding.
The verifier independently finds the quote and recovers the actual source substring after text
normalization. Extraction and evidence confidence remain separate because schema compliance is not
source support.”

### 1:08–1:30 — Case one: corroboration

**On screen:** Open the incorporation-date corroboration. Show the prospectus evidence on physical
page 30, printed page 105, and annual-report evidence on physical page 51, printed pages 100–101.
Show the first three reasoning checks.

**Say:** “Case one is corroboration. The prospectus and annual report both state June twenty-second,
twenty-eleven as the incorporation date. The normalized entities, predicates, and complete dates
match, so deterministic code returns corroborates.”

### 1:30–1:52 — Case two: likely contradiction

**On screen:** Open `sample_data/verified_demo_cases.json` at the employee-count case, then show the
two evidence passages or the saved page references: annual-report physical pages 34 and 51.

**Say:** “Case two is a manually validated likely contradiction. The annual report states
twenty-three thousand three hundred eighty-one permanent employees for March thirty-first,
twenty-twenty-four, while its year-end table reports eighteen thousand five hundred twenty-seven.
No disclosed context reconciles them. Because production blocking is cross-document, evaluation
honestly marks this same-document pair as missing.”

### 1:52–2:16 — Case three: reconciliation

**On screen:** Return to the relationship explorer and open the EBITDA-margin reconciliation. Point
to Fiscal 2019 at negative 8.29% and FY24 at positive 1.6%, then the `time_period` reasoning step.

**Say:** “Case three looks contradictory until context is checked. EBITDA margin is negative 8.29%
in Fiscal 2019 and positive 1.6% in FY24. The ordered trace checks rounding and then time. Different
periods explain the difference, so it returns reconciled.”

### 2:16–2:35 — Case four: handled failure

**On screen:** Show the excluded incorporation claim in the saved cases or UI. Highlight the exact
quote and the classification-exclusion reason.

**Say:** “Case four is a handled failure. The model mistakes 2011 inside a corporate identity number
for an incorporation date. The quote exists, so alignment stays verified, but a separate support
guard finds no incorporation cue. The fact remains auditable and is excluded from relationships.”

### 2:35–2:55 — Architecture, evaluation, and close

**On screen:** Briefly show `backend/reasoning/normalize.py`, `backend/reasoning/classify.py`, then
the evaluation result in the README. End on the application.

**Say:** “The LLM extracts candidates; normalization and classification are deterministic. The
checked-in evaluation uses fifteen labelled facts and eight relationship pairs, with exact quotes
and an explicit missing column. The result is general, inspectable, and honest about limitations.”

## Final recording checklist

- The recording visibly shows a PDF entering processing.
- The first three required cases show both source evidence and reasoning.
- The fourth case explains the failure and the implemented handling.
- No API key or `.env` contents appear.
- The final video is public or link-accessible, at most three minutes, and its URL replaces the
  README placeholder.
