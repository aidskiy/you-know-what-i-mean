"""Refine designer prompts based on critique feedback, audience, and style assignments."""

import json
import os
import random
import time

import httpx

GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

SYSTEM_INSTRUCTION_V2 = """\
You are a world-class UI/UX design director iterating on a design.
You are given:
- The original user request
- The 3 designer prompts from the previous round, each assigned a design style
- 3 tester personas with 6D audience vectors
- A critique with scores, a winner, and improvement suggestions from those testers

Your job: produce 3 NEW designer prompts that improve on the previous round.
- Keep what worked well (especially from the winning candidate).
- Address the specific improvement suggestions from the critique.
- Each prompt MUST keep its assigned design style from the taxonomy.
- Tailor each prompt to better match the audience expectations (based on the tester vectors).
- Each prompt should be more specific and refined than the previous round.

Return ONLY a JSON object, no markdown:
{
  "style_assignments": [
    {"candidate": 1, "style": "<same style as before>"},
    {"candidate": 2, "style": "<same style as before>"},
    {"candidate": 3, "style": "<same style as before>"}
  ],
  "prompts": ["<improved prompt 1>", "<improved prompt 2>", "<improved prompt 3>"]
}
"""

SYSTEM_INSTRUCTION_LEGACY = """\
You are a world-class UI/UX design director iterating on a design.
You are given:
- The original user request
- The 3 designer prompts from the previous round
- A critique with scores, a winner, and improvement suggestions

Your job: produce 3 NEW designer prompts that improve on the previous round.
- Keep what worked well (especially from the winning candidate).
- Address the specific improvement suggestions from the critique.
- Maintain 3 distinct aesthetic styles.
- Each prompt should be more specific and refined than the previous round.

Return ONLY a JSON array of 3 strings, no markdown, no explanation.
"""


def _get_gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def _post_with_retry(url: str, *, params: dict, json_body: dict, timeout: int) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(1, 6):
        try:
            resp = httpx.post(url, params=params, json=json_body, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                wait_s = min(30.0, (2 ** (attempt - 1))) + random.random()
                print(f"    ↻ Gemini {resp.status_code}, retrying in {wait_s:.1f}s (attempt {attempt}/5)")
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
            return resp
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
            last_exc = e
            if attempt >= 5:
                break
            wait_s = min(30.0, (2 ** (attempt - 1))) + random.random()
            time.sleep(wait_s)

    raise RuntimeError(
        "Gemini refine request failed after retries (possible rate limit / quota). "
        "Try again in a minute, or check your Google AI Studio quota."
    ) from last_exc


def refine_prompts_v2(
    user_prompt: str,
    previous_prompts: list[str],
    style_assignments: list[dict],
    testers: dict,
    critique: dict,
) -> dict:
    """Generate 3 improved designer prompts using critique, audience, and style context.

    Returns:
        {"style_assignments": [...], "prompts": ["...", "...", "..."]}
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    # Build context
    tester_summary = ""
    for i, t in enumerate(testers["testers"], 1):
        tester_summary += f"\nTester {i}: {t['name']} – {t['bio']}\n"
        tester_summary += f"  Vector: {json.dumps(t['vector'])}\n"

    style_summary = ""
    for sa in style_assignments:
        style_summary += f"  Candidate {sa['candidate']}: {sa['style']}\n"

    context = (
        f"Original user request: {user_prompt}\n\n"
        f"Style assignments:\n{style_summary}\n"
        f"Previous designer prompts:\n"
    )
    for i, p in enumerate(previous_prompts, 1):
        context += f"  {i}. {p}\n"
    context += f"\nTester personas:{tester_summary}\n"
    context += f"Critique:\n{json.dumps(critique, indent=2)}\n"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION_V2}]},
        "contents": [{"parts": [{"text": context}]}],
        "generationConfig": {
            "temperature": 0.8,
            "responseMimeType": "application/json",
        },
    }

    resp = _post_with_retry(
        GEMINI_TEXT_URL,
        params={"key": api_key},
        json_body=payload,
        timeout=60,
    )

    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)

    if not isinstance(data, dict) or "prompts" not in data:
        raise ValueError(f"Expected JSON object with 'prompts', got: {json.dumps(data)[:300]}")
    if len(data["prompts"]) != 3:
        raise ValueError(f"Expected 3 prompts, got {len(data['prompts'])}")

    return {
        "style_assignments": data.get("style_assignments", style_assignments),
        "prompts": [str(p).strip() for p in data["prompts"]],
    }


# ---------- Backward-compatible legacy refine --------------------------------

def refine_prompts(
    user_prompt: str,
    previous_prompts: list[str],
    critique: dict,
) -> list[str]:
    """Legacy: Generate 3 improved designer prompts (no audience/style context)."""
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    context = (
        f"Original user request: {user_prompt}\n\n"
        f"Previous designer prompts:\n"
    )
    for i, p in enumerate(previous_prompts, 1):
        context += f"  {i}. {p}\n"
    context += f"\nCritique:\n{json.dumps(critique, indent=2)}\n"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION_LEGACY}]},
        "contents": [{"parts": [{"text": context}]}],
        "generationConfig": {
            "temperature": 0.8,
            "responseMimeType": "application/json",
        },
    }

    resp = _post_with_retry(
        GEMINI_TEXT_URL,
        params={"key": api_key},
        json_body=payload,
        timeout=60,
    )

    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    prompts = json.loads(text)

    if not isinstance(prompts, list) or len(prompts) != 3:
        raise ValueError(f"Expected 3 prompts, got: {prompts}")

    return [str(p) for p in prompts]
