"""Typed-enough HTTP adapter keeping Streamlit rendering free of request details."""

from typing import Any

import httpx


class ApiClientError(RuntimeError):
    """A user-displayable backend communication failure."""


class FactKnowledgeApi:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
        )

    def _json(self, response: httpx.Response) -> Any:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ApiClientError(f"Backend returned {response.status_code}: {detail}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError("Backend returned an invalid JSON response") from exc

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ApiClientError(f"Cannot reach the FastAPI service at {self.base_url}") from exc
        return self._json(response)

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def upload_document(self, name: str, payload: bytes) -> dict[str, Any]:
        return self._request(
            "POST",
            "/documents",
            files={"file": (name, payload, "application/pdf")},
        )

    def document_status(self, document_id: str) -> dict[str, Any]:
        return self._request("GET", f"/documents/{document_id}")

    def facts(self, document_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/documents/{document_id}/facts")

    def relationships(
        self,
        *,
        classification: str | None = None,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            key: value
            for key, value in {
                "classification": classification,
                "document_id": document_id,
            }.items()
            if value
        }
        return self._request("GET", "/relationships", params=params)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
