"""Tests for the Streamlit-to-FastAPI boundary."""

import httpx
import pytest

from frontend.api_client import ApiClientError, FactKnowledgeApi


def test_frontend_client_sends_upload_and_relationship_filters() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/documents":
            return httpx.Response(202, json={"id": "doc-1", "status": "queued"})
        return httpx.Response(200, json=[])

    with FactKnowledgeApi(
        "http://testserver/",
        transport=httpx.MockTransport(handler),
    ) as api:
        assert api.upload_document("report.pdf", b"%PDF-test")["status"] == "queued"
        assert api.relationships(classification="uncertain", document_id="doc-1") == []

    assert requests[0].url.path == "/documents"
    assert b"report.pdf" in requests[0].content
    assert requests[1].url.params["classification"] == "uncertain"
    assert requests[1].url.params["document_id"] == "doc-1"


def test_frontend_client_surfaces_backend_detail() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(404, json={"detail": "Document not found"})
    )

    with FactKnowledgeApi("http://testserver", transport=transport) as api:
        with pytest.raises(ApiClientError, match="Document not found"):
            api.facts("missing")


def test_frontend_client_rejects_non_json_success() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="not-json"))

    with FactKnowledgeApi("http://testserver", transport=transport) as api:
        with pytest.raises(ApiClientError, match="invalid JSON"):
            api.health()


def test_frontend_client_turns_connection_failure_into_clear_error() -> None:
    def fail(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with FactKnowledgeApi(
        "http://offline-service",
        transport=httpx.MockTransport(fail),
    ) as api:
        with pytest.raises(ApiClientError, match="Cannot reach"):
            api.health()
