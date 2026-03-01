"""Generate a PNG image from a text prompt using OpenAI image generation."""

import base64
from pathlib import Path

import weave

from gemini_client import get_client, IMAGE_MODEL


@weave.op()
def generate_image(prompt: str, output_path: str | Path) -> Path:
    """Generate a single PNG image and save it to output_path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = get_client()
    resp = client.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        n=1,
        size="1024x1024",
        quality="medium",
    )

    img_bytes = base64.b64decode(resp.data[0].b64_json)
    output_path.write_bytes(img_bytes)
    print(f"  ✓ Saved image → {output_path}")
    return output_path
