"""Pass 2: Select 3 design styles from taxonomy and generate audience-aligned prompts."""

import json
import os
import random
import time

import httpx

GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

DESIGN_STYLES = [
    "Minimalist/Flat",
    "Neumorphism",
    "Glassmorphism",
    "Brutalist/Raw",
    "Dark Mode First/Cyber",
    "Material Design",
    "Editorial/Typography-forward",
    "Playful/Illustration-heavy",
    "High-tech/AI aesthetic",
    "Skeuomorphic",
]

PASS2_SYSTEM_INSTRUCTION = """\
You are a world-class UI/UX design director.

You are given:
- A product description.
- 3 tester personas, each with a 6-dimensional audience vector.
- A design style taxonomy (10 styles).

Your job:
1. Analyse the audience vectors to understand WHO will use this product.
2. Pick 3 DIFFERENT styles from the taxonomy that would best serve these audiences.
   Choose styles that are diverse from each other AND suited to the audience mix.
3. For each chosen style, write ONE detailed image-generation prompt that:
   - Targets that specific visual style.
   - Is tailored to the audience's expectations (e.g. a Premium/Status audience expects polish;
     a Low-tech-sophistication audience needs simple, obvious layouts).
   - Describes a single UI screen with specific elements, colours, typography, and layout.

Return ONLY a JSON object, no markdown:
{
  "style_assignments": [
    {"candidate": 1, "style": "<exact style name from taxonomy>"},
    {"candidate": 2, "style": "<exact style name from taxonomy>"},
    {"candidate": 3, "style": "<exact style name from taxonomy>"}
  ],
  "prompts": ["<prompt 1>", "<prompt 2>", "<prompt 3>"]
}
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
        "Gemini request failed after retries (possible rate limit / quota). "
        "Try again in a minute, or check your Google AI Studio quota."
    ) from last_exc


def generate_designer_prompts_v2(user_prompt: str, testers: dict) -> dict:
    """Pass 2: Use tester personas + audience vectors to select 3 styles and generate prompts.

    Args:
        user_prompt: The original user product description.
        testers: Output from audience.generate_testers().

    Returns:
        {
            "style_assignments": [{"candidate": 1, "style": "..."}, ...],
            "prompts": ["...", "...", "..."],
        }
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    # Build context with testers and taxonomy
    tester_summary = ""
    for i, t in enumerate(testers["testers"], 1):
        tester_summary += f"\nTester {i}: {t['name']} – {t['bio']}\n"
        tester_summary += f"  Vector: {json.dumps(t['vector'])}\n"

    context = (
        f"Product description:\n{user_prompt}\n\n"
        f"Tester personas:{tester_summary}\n"
        f"Design style taxonomy:\n"
        + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(DESIGN_STYLES))
    )

    payload = {
        "system_instruction": {"parts": [{"text": PASS2_SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": context}]}],
        "generationConfig": {
            "temperature": 0.9,
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

    # Validate
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got: {type(data)}")
    if "prompts" not in data or not isinstance(data["prompts"], list) or len(data["prompts"]) != 3:
        raise ValueError(f"Expected 3 prompts, got: {json.dumps(data)[:300]}")
    if "style_assignments" not in data or len(data["style_assignments"]) != 3:
        raise ValueError(f"Expected 3 style_assignments, got: {json.dumps(data)[:300]}")

    # Validate style names (warn but don't fail)
    for sa in data["style_assignments"]:
        if sa.get("style") not in DESIGN_STYLES:
            print(f"    ⚠ Style '{sa.get('style')}' not in taxonomy, proceeding anyway")

    return {
        "style_assignments": data["style_assignments"],
        "prompts": [str(p).strip() for p in data["prompts"]],
    }


# ---------- Backward-compatible v1 (kept for --rounds 1 single-shot) ---------

def generate_designer_prompts(user_prompt: str) -> list[str]:
    """Legacy: generate 3 prompts without audience context (calls v2 internally would
    need testers, so this falls back to a simple single-call approach)."""
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    fallback_instruction = (
        "You are a world-class UI/UX design director.\n"
        "Given a product idea, produce exactly 3 distinct image-generation prompts, "
        "each in a different visual style chosen from: "
        + ", ".join(DESIGN_STYLES) + ".\n\n"
        "Return ONLY a JSON array of 3 strings, no markdown."
    )

    payload = {
        "system_instruction": {"parts": [{"text": fallback_instruction}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 1.0,
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
