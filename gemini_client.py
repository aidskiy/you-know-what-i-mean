"""Shared API client for text generation (Mistral AI) via OpenAI-compatible endpoint."""

import os

from openai import OpenAI

_client = None


def get_client() -> OpenAI:
    """Lazily initialize and return the Mistral-backed OpenAI-compatible client."""
    global _client
    if _client is None:
        api_key = os.environ.get("MISTRAL_API_KEY", "")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY environment variable is not set")
        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.mistral.ai/v1",
        )
    return _client


# Pixtral Large supports vision (multimodal) — needed by critique.py and scorers.py
TEXT_MODEL = "pixtral-large-latest"
IMAGE_MODEL = "gpt-image-1"  # unused — image generation uses fal_image.py
