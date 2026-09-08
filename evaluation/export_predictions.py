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
    args = parser.parse_args()

    with httpx.Client(base_url=args.api_base, timeout=60) as client:
        documents = [_get(client, f"/documents/{document_id}") for document_id in args.document_ids]
        facts = {
            document["id"]: _get(client, f"/documents/{document['id']}/facts")
            for document in documents
        }
        relationships = _get(client, "/relationships?limit=500")

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
