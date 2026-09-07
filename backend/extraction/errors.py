"""Failures raised at the LLM extraction boundary."""


class LlmExtractionError(RuntimeError):
    """The model call failed or returned no structured result."""


class LlmConfigurationError(LlmExtractionError):
    """The LLM adapter cannot be created from the supplied configuration."""
