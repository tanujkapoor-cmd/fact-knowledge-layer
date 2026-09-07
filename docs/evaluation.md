# Evaluation Workflow

The harness intentionally contains no labels for the supplied PDFs. Create two JSON files that
follow GroundTruthDataset and PredictionDataset in evaluation/schemas.py, then run:

    python -m evaluation.run_eval --ground-truth path/to/labels.json --predictions path/to/predictions.json

Use any stable document_key consistently in both files, preferably a SHA-256 hash or the original
file name. Ground-truth scope must identify every document and physical page that was labeled
exhaustively. Set physical_pages to null only when the complete document was exhaustively labeled.
This prevents unlabeled pages from being counted as false positives.

Fact matching is deterministic: document scope and one-based physical page must match, followed by
canonical entity, canonical predicate, normalized value/unit/currency, and normalized temporal
scope. Precision and recall are computed only inside the declared scope. Exact evidence-quote rate
is reported separately for matched facts.

Relationship labels reference fact IDs in their own file. After matching facts, the harness scores
the hand-selected relationship pairs and prints a four-class confusion matrix. A fifth predicted
column named missing makes absent relationship decisions visible rather than silently dropping
them. The same results are saved as JSON under evaluation/results/ by default.
