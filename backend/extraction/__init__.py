"""Structured fact extraction and deterministic evidence verification."""

from backend.extraction.adapter import FactExtractionAdapter
from backend.extraction.errors import LlmConfigurationError, LlmExtractionError
from backend.extraction.gemini_adapter import GeminiStructuredFactAdapter
from backend.extraction.openai_adapter import OpenAIStructuredFactAdapter
from backend.extraction.schemas import (
    AdapterExtractionResult,
    EvidenceMatchMethod,
    EvidenceVerification,
    ExtractedFactRecord,
    ExtractionCheckpoint,
    ExtractionRun,
    FactCandidate,
    FactCandidateBatch,
)
from backend.extraction.service import FactExtractionService
from backend.extraction.verifier import EvidenceVerifier

__all__ = [
    "AdapterExtractionResult",
    "EvidenceMatchMethod",
    "EvidenceVerification",
    "EvidenceVerifier",
    "ExtractedFactRecord",
    "ExtractionRun",
    "ExtractionCheckpoint",
    "FactCandidate",
    "FactCandidateBatch",
    "FactExtractionAdapter",
    "FactExtractionService",
    "GeminiStructuredFactAdapter",
    "LlmConfigurationError",
    "LlmExtractionError",
    "OpenAIStructuredFactAdapter",
]
