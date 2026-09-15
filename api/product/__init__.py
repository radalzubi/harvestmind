"""Application services for the ZAAD operating product.

Everything in this package is *application* code: it reads the operator's vault, stores documents
the operator creates, and formats what the canonical engine produced. None of it computes an
economic quantity, ranks a supplier, or decides anything — those belong to `zaad/` and are frozen.

The boundary in one sentence: **the engine decides, this package fetches and formats.**
"""
