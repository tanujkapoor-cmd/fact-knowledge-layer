"""Export persisted API results into sample and evaluation JSON contracts."""

import argparse
import json
from pathlib import Path
from typing import Any

import httpx


def _get(client: httpx.Client, path: str) -> Any:
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a completed knowledge layer.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--document", action="append", required=True, dest="document_ids")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--format",
        choices=("sample", "evaluation"),
        default="sample",
        dest="output_format",
        help="sample keeps full audit payloads; evaluation emits the scoring contract",
    )
    args = parser.parse_args()

    with httpx.Client(base_url=args.api_base, timeout=60) as client:
        documents = [_get(client, f"/documents/{document_id}") for document_id in args.document_ids]
        facts = {
            document["id"]: _get(client, f"/documents/{document['id']}/facts")
            for document in documents
        }
        relationships = _get(client, "/relationships?limit=500")

    if args.output_format == "evaluation":
        document_keys = {document["id"]: document["sha256"] for document in documents}
        fact_ids = {fact["id"] for items in facts.values() for fact in items}
        payload = {
            "facts": [
                {
                    "id": fact["id"],
                    "document_key": document_keys[fact["document_id"]],
                    "subject": fact["subject"],
                    "predicate": fact["predicate"],
                    "value": fact["value"],
                    "unit": fact["unit"],
                    "currency": fact["currency"],
                    "temporal_scope": fact["temporal_scope"],
                    "physical_page_number": fact["evidence"]["physical_page_number"],
                    "evidence_quote": fact["evidence"]["quote"],
                }
                for items in facts.values()
                for fact in items
                if fact["evidence"]["status"] == "verified"
            ],
            "relationships": [
                {
                    "id": relationship["id"],
                    "fact_a_id": relationship["fact_a"]["id"],
                    "fact_b_id": relationship["fact_b"]["id"],
                    "classification": relationship["classification"],
                }
                for relationship in relationships
                if relationship["fact_a"]["id"] in fact_ids
                and relationship["fact_b"]["id"] in fact_ids
            ],
        }
    else:
        payload = {
            "generated_from": args.api_base,
            "documents": documents,
            "facts_by_document": facts,
            "relationships": relationships,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Saved {sum(len(items) for items in facts.values())} facts and "
        f"{len(relationships)} relationships to {args.output}"
    )


if __name__ == "__main__":
    main()
