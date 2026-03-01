"""Weave-compatible scorers for design evaluation."""

import base64
import json
import os

import httpx
import weave

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def _image_part(image_path: str) -> dict:
    """Build a Gemini inlineData part from an image file."""
    img_bytes = open(image_path, "rb").read()
    return {
        "inlineData": {
            "mimeType": "image/png",
            "data": base64.b64encode(img_bytes).decode(),
        }
    }


def _call_gemini(parts: list[dict]) -> dict:
    """Call Gemini text model with multimodal parts, return parsed JSON."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }
    resp = httpx.post(
        GEMINI_TEXT_URL,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


class CompositeScorer(weave.Scorer):
    """Scores a design candidate on fidelity and visual quality via Gemini."""

    @weave.op()
    def score(self, output: dict) -> dict:
        user_prompt = output["user_prompt"]
        prompt_text = (
            f"You are a senior UI/UX design critic.\n"
            f"Score this design on two axes (0-10 each):\n"
            f"1. Fidelity: how well it matches the user request: \"{user_prompt}\"\n"
            f"2. Quality: visual polish, layout, typography, colour\n\n"
            f"Designer prompt used: {output['designer_prompt']}\n\n"
            f"Return ONLY JSON:\n"
            f'{{"fidelity": <float>, "quality": <float>, "overall": <float>, '
            f'"reasoning": "<2 sentences>", "suggestions": "<actionable improvement>"}}'
        )
        parts = [{"text": prompt_text}, _image_part(output["image_path"])]
        return _call_gemini(parts)
