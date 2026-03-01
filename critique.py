"""Critique 3 design candidates using Gemini as a multimodal judge."""

import base64
import json
import os
from pathlib import Path

import httpx

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

SYSTEM_INSTRUCTION = """\
You are a senior UI/UX design critic.
You are given a user's original design request and 3 candidate designs (each with its designer prompt and rendered image).

Evaluate each candidate on:
- Fidelity to the user's request
- Visual quality and polish
- Layout and composition
- Typography and colour choices

Return ONLY a JSON object, no markdown, no explanation:
{
  "winner": <1|2|3>,
  "scores": [
    {"candidate": 1, "score": <0-10 float>, "reasoning": "<1-2 sentences>"},
    {"candidate": 2, "score": <0-10 float>, "reasoning": "<1-2 sentences>"},
    {"candidate": 3, "score": <0-10 float>, "reasoning": "<1-2 sentences>"}
  ],
  "improvement_suggestions": "<specific, actionable feedback for the next design iteration>"
}
"""


def critique_candidates(
    user_prompt: str,
    designer_prompts: list[str],
    image_paths: list[Path],
) -> dict:
    """Send all 3 candidates to Gemini for multimodal critique."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    # Build interleaved text + image parts
    parts: list[dict] = [
        {"text": f"Original user request: {user_prompt}\n\n"},
    ]
    for i, (prompt, img_path) in enumerate(zip(designer_prompts, image_paths), 1):
        parts.append({"text": f"--- Candidate {i} ---\nDesigner prompt: {prompt}\nRendered image:"})
        img_bytes = img_path.read_bytes()
        parts.append({
            "inlineData": {
                "mimeType": "image/png",
                "data": base64.b64encode(img_bytes).decode(),
            }
        })

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
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
    critique = json.loads(text)

    # Basic validation
    if "winner" not in critique or "scores" not in critique:
        raise ValueError(f"Invalid critique response: {critique}")

    return critique
