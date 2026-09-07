"""End-to-end API, persistence, deduplication, and background pipeline tests."""

from uuid import uuid4

import pymupdf
from fastapi.testclient import TestClient

from backend.extraction import AdapterExtractionResult, FactCandidate
from backend.ingestion import ParsedPage


def _pdf_bytes(text: str) -> bytes:
    document = pymupdf.open()
    try:
        page = document.new_page()
        page.insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


class ContentAwareAdapter:
    provider = "fake"
    model = "api-test-model"
    prompt_version = "api-test-v1"

    def extract_facts(self, pages: list[ParsedPage]) -> AdapterExtractionResult:
        source = " ".join(page.text.strip() for page in pages)
        value = "120" if "120" in source else "100"
        quote = f"Acme revenue was {value} in FY2024."
        if "unverified" in source:
            quote = "This fabricated quote is absent from the PDF."
        return AdapterExtractionResult(
            candidates=[
                FactCandidate(
                    subject="Acme Ltd.",
                    predicate="revenue",
                    value=value,
                    unit=None,
                    currency=None,
                    temporal_scope="FY2024",
                    evidence_quote=quote,
                    page_number=pages[0].physical_page_number,
                )
            ],
            request_id="fake-request",
        )


def _install_fake_adapter(client: TestClient) -> None:
    client.app.state.extraction_adapter_factory = ContentAwareAdapter


def test_upload_to_relationship_workflow_persists_grounded_responses(client: TestClient) -> None:
    _install_fake_adapter(client)
    first_upload = client.post(
        "/documents",
        files={
            "file": ("first.pdf", _pdf_bytes("Acme revenue was 100 in FY2024."), "application/pdf")
        },
    )
    second_upload = client.post(
        "/documents",
        files={
            "file": ("second.pdf", _pdf_bytes("Acme revenue was 120 in FY2024."), "application/pdf")
        },
    )

    assert first_upload.status_code == second_upload.status_code == 202
    first_id = first_upload.json()["id"]
    second_id = second_upload.json()["id"]
    assert client.get(f"/documents/{first_id}").json()["status"] == "completed"
    facts = client.get(f"/documents/{first_id}/facts").json()
    assert facts[0]["evidence"]["quote"] == "Acme revenue was 100 in FY2024."
    assert facts[0]["evidence"]["start_offset"] == 0
    assert facts[0]["confidence"]["extraction"]["value"] == 1.0
    assert facts[0]["confidence"]["evidence_verification"]["value"] == 1.0

    relationships = client.get("/relationships", params={"classification": "contradicts"}).json()
    assert len(relationships) == 1
    assert relationships[0]["classification"] == "contradicts"
    assert relationships[0]["classification_confidence"]["value"] == 1.0
    assert len(relationships[0]["reasoning_trace"]) == 7
    assert {
        relationships[0]["fact_a"]["document_id"],
        relationships[0]["fact_b"]["document_id"],
    } == {
        first_id,
        second_id,
    }


def test_duplicate_upload_reuses_document_and_does_not_repeat_work(client: TestClient) -> None:
    _install_fake_adapter(client)
    payload = _pdf_bytes("Acme revenue was 100 in FY2024.")

    first = client.post("/documents", files={"file": ("first.pdf", payload, "application/pdf")})
    duplicate = client.post(
        "/documents", files={"file": ("renamed.pdf", payload, "application/pdf")}
    )

    assert duplicate.json()["duplicate_reused"] is True
    assert duplicate.json()["id"] == first.json()["id"]
    assert len(client.get(f"/documents/{first.json()['id']}/facts").json()) == 1


def test_failed_evidence_is_visible_but_ineligible(client: TestClient) -> None:
    _install_fake_adapter(client)
    response = client.post(
        "/documents",
        files={
            "file": (
                "failed-evidence.pdf",
                _pdf_bytes("unverified source marker"),
                "application/pdf",
            )
        },
    )

    facts = client.get(f"/documents/{response.json()['id']}/facts").json()
    assert facts[0]["evidence"]["status"] == "failed"
    assert facts[0]["evidence"]["failure_reason"]
    assert facts[0]["classification_eligible"] is False
    assert facts[0]["confidence"]["evidence_verification"]["value"] == 0.0


def test_invalid_pdf_and_unknown_document_return_honest_states(client: TestClient) -> None:
    _install_fake_adapter(client)
    upload = client.post(
        "/documents",
        files={"file": ("broken.pdf", b"not a pdf", "application/pdf")},
    )

    status_response = client.get(f"/documents/{upload.json()['id']}")
    assert status_response.json()["status"] == "failed"
    assert "InvalidPdfError" in status_response.json()["failure_reason"]
    assert client.get(f"/documents/{uuid4()}/facts").status_code == 404


def test_upload_rejects_wrong_extension_and_empty_file(client: TestClient) -> None:
    wrong_type = client.post("/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    empty = client.post("/documents", files={"file": ("empty.pdf", b"", "application/pdf")})

    assert wrong_type.status_code == 415
    assert empty.status_code == 400
