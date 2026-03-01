"""Generate a PNG image from a text prompt using Gemini image generation."""

import base64
import os
from pathlib import Path

import httpx
import weave

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash-exp-image-generation:generateContent"
)


@weave.op()
def generate_image(prompt: str, output_path: str | Path) -> Path:
    """Generate a single PNG image and save it to output_path."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
        },
    }

    resp = httpx.post(
        GEMINI_IMAGE_URL,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()

    # Walk through parts to find the inline image data
    parts = resp.json()["candidates"][0]["content"]["parts"]
    for part in parts:
        inline = part.get("inlineData")
        if inline and inline.get("mimeType", "").startswith("image/"):
            img_bytes = base64.b64decode(inline["data"])
            output_path.write_bytes(img_bytes)
            print(f"  ✓ Saved image → {output_path}")
            return output_path

    raise RuntimeError("No image data returned by Gemini")
