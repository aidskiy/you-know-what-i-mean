"""Shared fal.ai client for image generation."""

import os
import fal_client

IMAGE_MODEL = "fal-ai/nano-banana-2"


def run_image(prompt: str, **kwargs):
    """Run fal image generation."""
    api_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")

    if not api_key:
        raise RuntimeError("FAL_KEY not set")

    # fal_client automatically reads FAL_KEY from env,
    # so we don’t actually need to manually attach it.
    return fal_client.run(
        IMAGE_MODEL,
        arguments={
            "prompt": prompt,
            **kwargs,
        },
    )