"""Expected failures raised by the PDF ingestion boundary."""


class PdfIngestionError(ValueError):
    """Base class for PDF input that cannot be ingested."""


class EmptyPdfError(PdfIngestionError):
    """The supplied file has no bytes or no pages."""


class InvalidPdfError(PdfIngestionError):
    """The supplied bytes do not represent a readable PDF."""


class PasswordProtectedPdfError(PdfIngestionError):
    """The PDF requires a password before its text can be read."""
