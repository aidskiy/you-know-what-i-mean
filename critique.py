"""Critique 3 design candidates using dynamic tester personas from Pass 1."""

import base64
import json
import os
import random
import time
from pathlib import Path

import httpx

GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


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
        "Gemini critique request failed after retries (possible rate limit / quota). "
        "Try again in a minute, or check your Google AI Studio quota."
    ) from last_exc


def _run_tester_review(
    *,
    api_key: str,
    system_instruction: str,
    image_paths: list[Path],
) -> dict:
    """Run one tester's multimodal review of all candidates."""
    parts: list[dict] = []
    for i, img_path in enumerate(image_paths, 1):
        parts.append({"text": f"--- Candidate {i} ---\nDesign screenshot:"})
        img_bytes = img_path.read_bytes()
        parts.append(
            {
                "inlineData": {
                    "mimeType": "image/png",
                    "data": base64.b64encode(img_bytes).decode(),
                }
            }
        )

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }

    resp = _post_with_retry(
        GEMINI_TEXT_URL,
        params={"key": api_key},
        json_body=payload,
        timeout=90,
    )

    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    review = json.loads(text)

    if not isinstance(review, dict) or "candidates" not in review:
        raise ValueError(f"Invalid tester review response: {review}")
    return review


def _aggregate_tester_reviews(tester_reviews: list[dict]) -> dict:
    """Merge 3 tester reviews into a single critique with averaged scores."""
    scores_by_candidate: dict[int, list[float]] = {1: [], 2: [], 3: []}
    reasons_by_candidate: dict[int, list[str]] = {1: [], 2: [], 3: []}

    for tr in tester_reviews:
        for c in tr.get("candidates", []):
            cid = int(c.get("candidate"))
            score = float(c.get("score"))
            scores_by_candidate.setdefault(cid, []).append(score)

            app_guess = str(c.get("what_app_does", "")).strip()
            cues = c.get("clarity_signals", [])
            if isinstance(cues, list):
                cues_text = "; ".join(str(x) for x in cues[:2] if str(x).strip())
            else:
                cues_text = ""

            reason = app_guess
            if cues_text:
                reason = f"{reason} (cues: {cues_text})" if reason else f"cues: {cues_text}"
            reason = reason.strip() or "No reasoning provided"
            reasons_by_candidate.setdefault(cid, []).append(reason)

    averaged: list[dict] = []
    for cid in (1, 2, 3):
        vals = scores_by_candidate.get(cid, [])
        avg = sum(vals) / len(vals) if vals else 0.0
        reason = " | ".join(reasons_by_candidate.get(cid, [])[:3])
        averaged.append({"candidate": cid, "score": round(avg, 2), "reasoning": reason[:240]})

    winner = max(averaged, key=lambda s: s["score"])["candidate"]
    improvement_suggestions = "\n".join(
        str(tr.get("overall_feedback", "")).strip() for tr in tester_reviews if str(tr.get("overall_feedback", "")).strip()
    ).strip()[:1200]

    if not improvement_suggestions:
        improvement_suggestions = "Improve clarity of what the app does: add stronger labels, clearer hierarchy, and more obvious primary action."

    return {
        "winner": winner,
        "scores": averaged,
        "improvement_suggestions": improvement_suggestions,
        "tester_reviews": tester_reviews,
    }


def critique_candidates(
    user_prompt: str,
    designer_prompts: list[str],
    image_paths: list[Path],
    tester_system_instructions: list[str] | None = None,
) -> dict:
    """Send all 3 candidates to Gemini for critique.

    Args:
        user_prompt: Original user prompt (not leaked to testers).
        designer_prompts: The 3 designer prompts (not leaked to testers).
        image_paths: Paths to the 3 candidate PNGs.
        tester_system_instructions: 3 system instruction strings from Pass 1.
            If None, uses a generic fallback (backward compat).
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    # Fallback if no dynamic testers provided
    if tester_system_instructions is None:
        tester_system_instructions = [
            (
                "You are a first-time app user. You do NOT know what this app is. "
                "For EACH of the 3 candidate designs: guess what the app does, list clarity signals, "
                "confusing parts, likes, dislikes, and give a score 0-10.\n\n"
                'Return ONLY JSON: {"tester": "Tester 1", "candidates": ['
                '{"candidate": 1, "what_app_does": "...", "clarity_signals": ["..."], '
                '"confusing_parts": ["..."], "likes": ["..."], "dislikes": ["..."], "score": 0-10}], '
                '"overall_feedback": "..."}'
            ),
            (
                "You are a skeptical user scanning a UI for 5 seconds. You do NOT know what the app is. "
                "For EACH of the 3 candidates: guess purpose, identify cues, identify confusion, "
                "note what feels polished vs cheap, score 0-10.\n\n"
                'Return ONLY JSON using the same schema.'
            ),
            (
                "You are a friendly non-designer user. You do NOT know what the app is. "
                "For EACH of the 3 candidates: explain what you think it does, what elements communicate that, "
                "what you like, what you'd change, score 0-10.\n\n"
                'Return ONLY JSON using the same schema.'
            ),
        ]

    if len(tester_system_instructions) != 3:
        raise ValueError(f"Expected 3 tester system instructions, got {len(tester_system_instructions)}")

    tester_reviews = []
    for i, sysinstruct in enumerate(tester_system_instructions, 1):
        print(f"    Tester {i} reviewing …")
        review = _run_tester_review(api_key=api_key, system_instruction=sysinstruct, image_paths=image_paths)
        tester_reviews.append(review)

    critique = _aggregate_tester_reviews(tester_reviews)

    if "winner" not in critique or "scores" not in critique:
        raise ValueError(f"Invalid critique response: {critique}")

    return critique
