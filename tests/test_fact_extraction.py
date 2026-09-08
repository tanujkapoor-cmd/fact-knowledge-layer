"""Provider isolation and extraction-service tests."""

from types import SimpleNamespace

import pytest

from backend.extraction import (
    EvidenceMatchMethod,
    EvidenceVerifier,
    FactCandidate,
    FactCandidateBatch,
    FactExtractionService,
    GeminiStructuredFactAdapter,
    LlmExtractionError,
)
from backend.extraction.openai_adapter import SYSTEM_PROMPT, OpenAIStructuredFactAdapter
from backend.extraction.schemas import AdapterExtractionResult
from backend.ingestion import ParsedPage, ParsedPdf
from backend.ingestion.schemas import PAGE_SEPARATOR
from backend.models import EvidenceStatus


def _page(number: int, text: str, document_start: int = 0) -> ParsedPage:
    return ParsedPage(
        physical_page_number=number,
        text=text,
        page_local_end_offset=len(text),
        document_start_offset=document_start,
        document_end_offset=document_start + len(text),
    )


def _candidate(page_number: int, quote: str) -> FactCandidate:
    return FactCandidate(
        subject="Delhivery",
        predicate="reported revenue",
        value="INR 100 crore",
        unit="crore",
        currency="INR",
        temporal_scope="FY2024",
        evidence_quote=quote,
        page_number=page_number,
    )


class FakeAdapter:
    provider = "fake"
    model = "deterministic-test-model"
    prompt_version = "test-v1"

    def __init__(self, candidates_by_call: list[list[FactCandidate]]) -> None:
        self._candidates_by_call = iter(candidates_by_call)
        self.calls: list[list[int]] = []

    def extract_facts(self, pages: list[ParsedPage]) -> AdapterExtractionResult:
        self.calls.append([page.physical_page_number for page in pages])
        return AdapterExtractionResult(
            candidates=next(self._candidates_by_call),
            request_id=f"request-{len(self.calls)}",
        )


def test_service_retains_failed_fact_but_excludes_it_from_classification() -> None:
    page = _page(1, "Delhivery reported revenue of INR 100 crore in FY2024.")
    fabricated = _candidate(1, "Delhivery reported a profit of INR 900 crore in FY2024.")
    adapter = FakeAdapter([[fabricated]])
    service = FactExtractionService(adapter, EvidenceVerifier())
    document = ParsedPdf(
        sha256="a" * 64,
        page_count=1,
        text=page.text,
        pages=[page],
    )

    run = service.extract_document(document)

    assert len(run.facts) == 1
    assert run.facts[0].evidence.status is EvidenceStatus.FAILED
    assert run.facts[0].confidence.evidence_verification.value == 0.0
    assert run.facts[0].confidence.extraction.value == 1.0
    assert run.facts[0].classification_eligible is False
    assert run.request_ids == ["request-1"]


def test_service_rejects_model_page_outside_supplied_batch() -> None:
    page = _page(1, "Delhivery reported revenue of INR 100 crore in FY2024.")
    wrong_page = _candidate(99, "Delhivery reported revenue of INR 100 crore in FY2024.")
    adapter = FakeAdapter([[wrong_page]])
    document = ParsedPdf(
        sha256="b" * 64,
        page_count=1,
        text=page.text,
        pages=[page],
    )

    record = FactExtractionService(adapter).extract_document(document).facts[0]

    assert record.evidence.status is EvidenceStatus.FAILED
    assert record.confidence.extraction.value == 0.8
    assert "outside" in record.evidence.failure_reason
    assert record.classification_eligible is False


def test_service_batches_without_splitting_pages() -> None:
    first = _page(1, "A" * 10)
    second = _page(2, "B" * 10, document_start=11)
    third = _page(3, "C" * 30, document_start=22)
    document_text = PAGE_SEPARATOR.join(page.text for page in [first, second, third])
    document = ParsedPdf(
        sha256="c" * 64,
        page_count=3,
        text=document_text,
        pages=[first, second, third],
    )
    adapter = FakeAdapter([[], [], []])

    run = FactExtractionService(
        adapter,
        batch_character_limit=15,
        batch_page_limit=2,
    ).extract_document(document)

    assert adapter.calls == [[1], [2], [3]]
    assert run.request_ids == ["request-1", "request-2", "request-3"]


class _FakeResponses:
    def __init__(self, parsed: FactCandidateBatch) -> None:
        self._parsed = parsed
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self._parsed, _request_id="req-openai-1")


def test_openai_adapter_uses_pydantic_responses_api_without_storing() -> None:
    candidate = _candidate(1, "Delhivery reported revenue of INR 100 crore in FY2024.")
    responses = _FakeResponses(FactCandidateBatch(facts=[candidate]))
    client = SimpleNamespace(responses=responses)
    adapter = OpenAIStructuredFactAdapter(model="gpt-5-mini", client=client)
    page = _page(1, "Delhivery reported revenue of INR 100 crore in FY2024.")

    result = adapter.extract_facts([page])

    assert result.candidates == [candidate]
    assert result.request_id == "req-openai-1"
    assert responses.kwargs["model"] == "gpt-5-mini"
    assert responses.kwargs["text_format"] is FactCandidateBatch
    assert responses.kwargs["store"] is False
    assert responses.kwargs["input"][0]["content"] == SYSTEM_PROMPT
    assert "physical_page_number" in responses.kwargs["input"][1]["content"]
    assert EvidenceMatchMethod.EXACT.value == "exact"


def test_structured_schema_requires_nullable_fact_fields() -> None:
    required = set(FactCandidate.model_json_schema()["required"])

    assert required == {
        "subject",
        "predicate",
        "value",
        "unit",
        "currency",
        "temporal_scope",
        "evidence_quote",
        "page_number",
    }


def test_openai_adapter_rejects_missing_structured_payload() -> None:
    responses = _FakeResponses(FactCandidateBatch(facts=[]))
    responses._parsed = None
    adapter = OpenAIStructuredFactAdapter(
        client=SimpleNamespace(responses=responses),
    )

    with pytest.raises(LlmExtractionError, match="no structured"):
        adapter.extract_facts([_page(1, "Some source text")])


class _FakeGeminiModels:
    def __init__(self, parsed: FactCandidateBatch | None, text: str | None = None) -> None:
        self._parsed = parsed
        self._text = text
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            parsed=self._parsed,
            text=self._text,
            response_id="req-gemini-1",
        )


def test_gemini_adapter_uses_pydantic_structured_output() -> None:
    candidate = _candidate(1, "Delhivery reported revenue of INR 100 crore in FY2024.")
    models = _FakeGeminiModels(FactCandidateBatch(facts=[candidate]))
    adapter = GeminiStructuredFactAdapter(
        model="gemini-3.8-flash",
        client=SimpleNamespace(models=models),
    )

    result = adapter.extract_facts(
        [_page(1, "Delhivery reported revenue of INR 100 crore in FY2024.")]
    )

    assert result.candidates == [candidate]
    assert result.request_id == "req-gemini-1"
    assert models.kwargs["model"] == "gemini-3.8-flash"
    assert models.kwargs["config"].response_mime_type == "application/json"
    assert models.kwargs["config"].response_schema is FactCandidateBatch
    assert models.kwargs["config"].system_instruction == SYSTEM_PROMPT
    assert "physical_page_number" in models.kwargs["contents"]


def test_gemini_adapter_validates_json_text_fallback() -> None:
    candidate = _candidate(1, "Delhivery reported revenue of INR 100 crore in FY2024.")
    models = _FakeGeminiModels(None, FactCandidateBatch(facts=[candidate]).model_dump_json())
    adapter = GeminiStructuredFactAdapter(client=SimpleNamespace(models=models))

    result = adapter.extract_facts([_page(1, "Some source text")])

    assert result.candidates == [candidate]


def test_gemini_adapter_rejects_missing_structured_payload() -> None:
    models = _FakeGeminiModels(None)
    adapter = GeminiStructuredFactAdapter(client=SimpleNamespace(models=models))

    with pytest.raises(LlmExtractionError, match="no structured"):
        adapter.extract_facts([_page(1, "Some source text")])
