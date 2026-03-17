"""Centralized Mistral client factory.

Every module that needs a ``Mistral`` instance should call
:func:`get_mistral_client` instead of constructing one directly.
This keeps the API-key lookup in a single place and gives a clear
error when the key is missing.
"""

from mistralai import Mistral

from .config import settings


def get_mistral_client() -> Mistral:
    """Create a new Mistral client using the configured API key.

    Raises:
        RuntimeError: If ``MISTRAL_API_KEY`` is not set.
    """
    if not settings.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY not set — cannot create Mistral client")
    return Mistral(api_key=settings.mistral_api_key)
