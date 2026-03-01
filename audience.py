"""Pass 1: Generate 3 tester personas with 6D audience vectors and critique system instructions."""

import json
import os
import random
import time

import httpx

GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

SYSTEM_INSTRUCTION = """\
You are a user-research strategist.
Given a product description, generate 3 DISTINCT tester personas who might use this product.
Each tester must have a different perspective and background.

For each tester, provide:
1. A short name and one-line bio.
2. A 6-dimensional audience vector with EXACTLY these fields and allowed values:
   - economic_role: one of "B2C", "B2B", "Prosumer"
   - price_tolerance: one of "Low", "Mid", "Premium"
   - emotional_driver: one of "Optimization", "Identity", "Security", "Status", "Convenience", "Exploration", "Control"
   - technical_sophistication: one of "Low", "Medium", "High"
   - time_abundance: one of "High", "Low"
   - risk_tolerance: one of "High", "Low"
3. A system_instruction string (2-4 sentences) that tells this persona how to evaluate a UI screenshot.
   The instruction must:
   - Describe the persona's mindset and priorities (derived from the vector).
   - Tell them to guess what the app does from the screenshot alone.
   - Tell them to score each candidate 0-10 and explain likes/dislikes/confusing parts.
   - NOT reveal the original product description.

Return ONLY a JSON object, no markdown:
{
  "testers": [
    {
      "name": "...",
      "bio": "...",
      "vector": {
        "economic_role": "...",
        "price_tolerance": "...",
        "emotional_driver": "...",
        "technical_sophistication": "...",
        "time_abundance": "...",
        "risk_tolerance": "..."
      },
      "system_instruction": "..."
    }
  ]
}
"""

VALID_VECTORS = {
    "economic_role": {"B2C", "B2B", "Prosumer"},
    "price_tolerance": {"Low", "Mid", "Premium"},
    "emotional_driver": {"Optimization", "Identity", "Security", "Status", "Convenience", "Exploration", "Control"},
    "technical_sophistication": {"Low", "Medium", "High"},
    "time_abundance": {"High", "Low"},
    "risk_tolerance": {"High", "Low"},
}


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
        "Gemini audience request failed after retries (possible rate limit / quota). "
        "Try again in a minute, or check your Google AI Studio quota."
    ) from last_exc


def _validate_vector(vector: dict) -> bool:
    """Return True if all 6D fields are present and have valid values."""
    for field, allowed in VALID_VECTORS.items():
        if field not in vector or vector[field] not in allowed:
            return False
    return True


def _append_json_schema_to_instruction(raw_instruction: str) -> str:
    """Ensure each tester system_instruction includes the expected output schema."""
    schema_hint = (
        "\n\nFor EACH of the 3 candidate designs, return JSON with this schema:\n"
        '{"tester": "<your name>", "candidates": ['
        '{"candidate": 1, "what_app_does": "...", "clarity_signals": ["..."], '
        '"confusing_parts": ["..."], "likes": ["..."], "dislikes": ["..."], "score": 0-10}'
        '], "overall_feedback": "..."}\n'
        "Return ONLY JSON, no markdown, no extra text."
    )
    if "candidates" not in raw_instruction:
        return raw_instruction.strip() + schema_hint
    return raw_instruction.strip()


def generate_testers(user_prompt: str) -> dict:
    """Pass 1: Generate 3 tester personas with 6D vectors and critique system instructions.

    Returns:
        {
            "testers": [
                {
                    "name": str,
                    "bio": str,
                    "vector": { 6D fields },
                    "system_instruction": str,  # ready to use in critique
                },
                ...
            ]
        }
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
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
    data = json.loads(text)

    if not isinstance(data, dict) or "testers" not in data:
        raise ValueError(f"Expected {{'testers': [...]}} , got: {json.dumps(data)[:300]}")

    testers = data["testers"]
    if not isinstance(testers, list) or len(testers) != 3:
        raise ValueError(f"Expected 3 testers, got {len(testers) if isinstance(testers, list) else type(testers)}")

    # Validate and enrich each tester
    for i, t in enumerate(testers):
        if "vector" not in t or not isinstance(t["vector"], dict):
            raise ValueError(f"Tester {i+1} missing 'vector': {json.dumps(t)[:200]}")
        if not _validate_vector(t["vector"]):
            print(f"    ⚠ Tester {i+1} vector has invalid values, proceeding anyway: {t['vector']}")
        if "system_instruction" not in t or not t["system_instruction"].strip():
            raise ValueError(f"Tester {i+1} missing 'system_instruction'")
        # Ensure the system_instruction includes the JSON output schema
        t["system_instruction"] = _append_json_schema_to_instruction(t["system_instruction"])

    return data
