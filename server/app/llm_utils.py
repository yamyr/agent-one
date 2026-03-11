"""LLM response safety helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def safe_get_choice(response, context: str = ""):
    """Extract the first choice from an LLM response, raising on empty.

    Args:
        response: The LLM ChatCompletionResponse object.
        context: Optional label for error messages (e.g. "rover", "narrator").

    Returns:
        The first Choice object from response.choices.

    Raises:
        RuntimeError: If response has no choices or choices is None/empty.
    """
    choices = getattr(response, "choices", None)
    if not choices:
        label = f" ({context})" if context else ""
        raise RuntimeError(f"LLM returned empty choices{label}")
    return choices[0]
