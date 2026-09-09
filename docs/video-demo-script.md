# Three-minute submission video

This version includes one real upload but does not wait for a large starter PDF. Use
`output/pdf/quick-demo-company-update.pdf`, which is a one-page text PDF made for the live check.
Keep the README and `sample_data/verified_demo_cases.json` open in separate tabs. Never show `.env`,
the Gemini key, or the Render environment-variable page.

## Exact walkthrough and narration

### 0:00-0:15 - Introduce the project

**On screen:** GitHub repository, then click the live application link.

**Say:** “This is my Fact Knowledge Layer for Superjoin. It extracts facts from PDFs, verifies each
fact against exact source text, and explains relationships across documents. My main rule is that
the model can propose a fact, but it cannot approve its own evidence or relationship label.”

### 0:15-0:38 - Upload the one-page PDF

**On screen:** Click **Upload PDF**, choose `quick-demo-company-update.pdf`, and click **Register &
extract**. Point to the source status while it processes. Do not wait silently; continue speaking.

**Say:** “I am uploading a new one-page business update. FastAPI hashes the file for duplicate
reuse and processes it with a background task. PyMuPDF keeps the physical page, printed label and
character offsets. Extraction runs in checkpoints, so a provider retry does not throw away work.”

### 0:38-1:02 - Show exact evidence

**On screen:** Open the README’s first interface image while the upload completes. Point to the
claim, quote, page 51, printed label 100-101, offsets and two confidence values.

**Say:** “Here is a completed starter-document fact. Gemini returned a structured candidate, then
the verifier independently recovered this exact source passage. Extraction confidence and evidence
confidence are separate because valid JSON does not prove that a claim is supported.”

### 1:02-1:25 - Corroboration

**On screen:** Open case 1 in `sample_data/verified_demo_cases.json`. Show both quotes and the first
three reasoning checks.

**Say:** “The first relationship is corroboration. The prospectus and annual report both give June
twenty-second, twenty-eleven as Delhivery’s incorporation date. Entity, predicate and normalized
date all match, so deterministic code returns corroborates.”

### 1:25-1:48 - Likely contradiction

**On screen:** Scroll to case 2 and show values 23,381 and 18,527 with their page references.

**Say:** “The second case is a manually validated likely contradiction. The same annual report
gives two different permanent-employee totals for the same year end, and the page context does not
explain the difference. Evaluation records this as missing because production candidate generation
is intentionally cross-document.”

### 1:48-2:12 - Contextual reconciliation

**On screen:** Show the README reconciliation screenshot. Point to the `time_period` step.

**Say:** “The third case initially looks inconsistent: EBITDA margin is negative 8.29 percent in
Fiscal 2019 and positive 1.6 percent in FY24. The values differ, but so do the reporting periods.
The trace therefore returns reconciled, not contradicted.”

### 2:12-2:34 - Handled failure

**On screen:** Show the README unsupported-claim screenshot and its exclusion reason.

**Say:** “This is a handled extraction failure. The model read 2011 from a corporate identity
number as an incorporation date. The quote exists, but it does not support that predicate. The
fact stays visible and is excluded from relationship classification.”

### 2:34-2:55 - Architecture, evaluation and close

**On screen:** Scroll to the README architecture and evaluation table, then return to the app.

**Say:** “The LLM is isolated behind an extraction adapter. Normalization and classification are
pure deterministic Python, and every relationship stores its ordered trace. The checked-in manual
evaluation covers fifteen facts and eight relationship pairs. The system is small, inspectable and
clear about its current limitations.”

## Final check

- A new PDF is visibly uploaded and enters processing.
- The first three cases show evidence plus reasoning.
- The failure case shows its exact handling.
- No secret or environment-variable screen is visible.
- The recording is under three minutes and its public URL replaces the README placeholder.
