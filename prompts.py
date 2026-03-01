"""Generate 3 distinct designer-style prompts from a user prompt using Gemini."""

import json
import os

import httpx
import weave

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

SYSTEM_INSTRUCTION = """\
You are a world-class UI/UX design director.
Given a rough product idea, produce exactly 3 distinct visual design prompts.
Each prompt must target a different aesthetic style:
  1. Minimal / Swiss – clean grids, monochrome palette, lots of whitespace.
  2. Editorial / Magazine – bold typography, layered imagery, rich colour.
  3. Playful / Illustrative – rounded shapes, pastel colours, friendly illustrations.

Return ONLY a JSON array of 3 strings, no markdown, no explanation.
Example output:
["prompt 1 text", "prompt 2 text", "prompt 3 text"]
"""


@weave.op()
def generate_designer_prompts(user_prompt: str) -> list[str]:
    """Call Gemini text model to produce 3 designer prompts."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [
            {"parts": [{"text": user_prompt}]}
        ],
        "generationConfig": {
            "temperature": 1.0,
            "responseMimeType": "application/json",
        },
    }

    resp = httpx.post(
        GEMINI_TEXT_URL,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()

    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    prompts = json.loads(text)

    if not isinstance(prompts, list) or len(prompts) != 3:
        raise ValueError(f"Expected 3 prompts, got: {prompts}")

    return [str(p) for p in prompts]
