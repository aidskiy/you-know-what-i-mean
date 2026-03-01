"""Shared OpenAI API client for text generation, scoring, and image generation."""

import os

from openai import OpenAI

_client = None


def get_client() -> OpenAI:
    """Lazily initialize and return the OpenAI client."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key)
    return _client


TEXT_MODEL = "gpt-4o"
IMAGE_MODEL = "gpt-image-1"
