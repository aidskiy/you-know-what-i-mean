"""Refine designer prompts based on critique feedback."""

import json
import os

import httpx

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

SYSTEM_INSTRUCTION = """\
You are a world-class UI/UX design director iterating on a design.
You are given:
- The original user request
- The 3 designer prompts from the previous round
- A critique with scores, a winner, and improvement suggestions

Your job: produce 3 NEW designer prompts that improve on the previous round.
- Keep what worked well (especially from the winning candidate).
- Address the specific improvement suggestions from the critique.
- Maintain the 3 distinct aesthetic styles (Minimal/Swiss, Editorial/Magazine, Playful/Illustrative).
- Each prompt should be more specific and refined than the previous round.

Return ONLY a JSON array of 3 strings, no markdown, no explanation.
"""


def refine_prompts(
    user_prompt: str,
    previous_prompts: list[str],
    critique: dict,
) -> list[str]:
    """Generate 3 improved designer prompts using critique feedback."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    context = (
        f"Original user request: {user_prompt}\n\n"
        f"Previous designer prompts:\n"
    )
    for i, p in enumerate(previous_prompts, 1):
        context += f"  {i}. {p}\n"
    context += f"\nCritique:\n{json.dumps(critique, indent=2)}\n"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": context}]}],
        "generationConfig": {
            "temperature": 0.8,
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
