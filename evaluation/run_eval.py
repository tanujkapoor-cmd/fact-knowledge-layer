"""CLI for scoring user-authored labels against exported system predictions."""

import argparse
import json
from pathlib import Path
from typing import Any

from evaluation.metrics import evaluate
from evaluation.schemas import GroundTruthDataset, PredictionDataset


def _load(path: Path, model_type: Any) -> Any:
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def _print_results(results: Any) -> None:
    extraction = results.extraction
    relationships = results.relationships
    print("Extraction")
    print(
        f"  precision={extraction.precision:.3f} "
        f"recall={extraction.recall:.3f} "
        f"TP={extraction.true_positives} "
        f"FP={extraction.false_positives} "
        f"FN={extraction.false_negatives}"
    )
    quote_rate = extraction.exact_evidence_quote_rate
    print(
        "  exact evidence quote rate=" + (f"{quote_rate:.3f}" if quote_rate is not None else "n/a")
    )
    print("\nRelationship confusion matrix (rows=actual, columns=predicted)")
    print("  actual\\predicted\t" + "\t".join(relationships.prediction_labels))
    for label, row in zip(relationships.labels, relationships.confusion_matrix, strict=True):
        print(f"  {label}\t" + "\t".join(str(value) for value in row))
    print(
        f"  accuracy={relationships.accuracy:.3f} "
        f"evaluated={relationships.evaluated_pairs} "
        f"missing={relationships.missing_predictions}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate extracted facts and deterministic relationship labels."
    )
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/results/eval_results.json"),
    )
    args = parser.parse_args()

    ground_truth = _load(args.ground_truth, GroundTruthDataset)
    predictions = _load(args.predictions, PredictionDataset)
    results = evaluate(ground_truth, predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    _print_results(results)
    print(f"\nSaved machine-readable results to {args.output}")


if __name__ == "__main__":
    main()
