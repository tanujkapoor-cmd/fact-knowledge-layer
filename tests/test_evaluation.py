"""Synthetic metric tests; no starter-document ground truth is invented here."""

import json
import subprocess
import sys
from pathlib import Path

from backend.models import RelationshipType
from evaluation import GroundTruthDataset, PredictionDataset, evaluate


def _fact(identifier: str, value: str, *, page: int = 1, quote: str | None = None):
    return {
        "id": identifier,
        "document_key": "synthetic.pdf",
        "subject": "Acme Ltd.",
        "predicate": "revenue",
        "value": value,
        "unit": None,
        "currency": "INR",
        "temporal_scope": "FY2024",
        "physical_page_number": page,
        "evidence_quote": quote or f"Revenue was INR {value}.",
    }


def test_extraction_metrics_are_scoped_and_match_normalized_values() -> None:
    ground_truth = GroundTruthDataset.model_validate(
        {
            "scope": [{"document_key": "synthetic.pdf", "physical_pages": [1]}],
            "facts": [_fact("gt-1", "1,000")],
            "relationships": [],
        }
    )
    predictions = PredictionDataset.model_validate(
        {
            "facts": [
                _fact("pred-1", "1000"),
                _fact("pred-fp", "999"),
                {**_fact("outside-scope", "777", page=2)},
            ],
            "relationships": [],
        }
    )

    metrics = evaluate(ground_truth, predictions).extraction

    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 0
    assert metrics.precision == 0.5
    assert metrics.recall == 1.0
    assert metrics.exact_evidence_quote_rate == 0.0


def test_relationship_confusion_matrix_counts_wrong_and_missing_predictions() -> None:
    facts = [_fact("gt-1", "100"), _fact("gt-2", "120"), _fact("gt-3", "140")]
    ground_truth = GroundTruthDataset.model_validate(
        {
            "scope": [{"document_key": "synthetic.pdf"}],
            "facts": facts,
            "relationships": [
                {
                    "id": "rel-1",
                    "fact_a_id": "gt-1",
                    "fact_b_id": "gt-2",
                    "classification": "contradicts",
                },
                {
                    "id": "rel-2",
                    "fact_a_id": "gt-2",
                    "fact_b_id": "gt-3",
                    "classification": "reconciled",
                },
            ],
        }
    )
    predictions = PredictionDataset.model_validate(
        {
            "facts": [
                {**facts[0], "id": "pred-1"},
                {**facts[1], "id": "pred-2"},
                {**facts[2], "id": "pred-3"},
            ],
            "relationships": [
                {
                    "id": "pred-rel-1",
                    "fact_a_id": "pred-1",
                    "fact_b_id": "pred-2",
                    "classification": "uncertain",
                }
            ],
        }
    )

    metrics = evaluate(ground_truth, predictions).relationships
    contradiction_row = metrics.confusion_matrix[
        metrics.labels.index(RelationshipType.CONTRADICTS.value)
    ]
    reconciled_row = metrics.confusion_matrix[
        metrics.labels.index(RelationshipType.RECONCILED.value)
    ]

    assert contradiction_row[metrics.prediction_labels.index("uncertain")] == 1
    assert reconciled_row[metrics.prediction_labels.index("missing")] == 1
    assert metrics.accuracy == 0.0
    assert metrics.missing_predictions == 1


def test_evaluation_cli_prints_and_saves_results(tmp_path: Path) -> None:
    ground_truth_path = tmp_path / "ground_truth.json"
    predictions_path = tmp_path / "predictions.json"
    output_path = tmp_path / "results.json"
    fact = _fact("fact-1", "100")
    ground_truth_path.write_text(
        json.dumps(
            {
                "scope": [{"document_key": "synthetic.pdf"}],
                "facts": [fact],
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )
    predictions_path.write_text(
        json.dumps({"facts": [fact], "relationships": []}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "evaluation.run_eval",
            "--ground-truth",
            str(ground_truth_path),
            "--predictions",
            str(predictions_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "precision=1.000 recall=1.000" in completed.stdout
    assert json.loads(output_path.read_text(encoding="utf-8"))["extraction"]["precision"] == 1.0
