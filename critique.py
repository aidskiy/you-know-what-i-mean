"""Critique 3 design candidates using dynamic tester personas from Pass 1."""

import base64
import json
from pathlib import Path

from gemini_client import get_client, TEXT_MODEL


def _image_url(image_path: Path) -> str:
    """Build a data URL from an image file for OpenAI vision."""
    img_bytes = image_path.read_bytes()
    b64 = base64.b64encode(img_bytes).decode()
    return f"data:image/png;base64,{b64}"


def _run_tester_review(
    *,
    system_instruction: str,
    image_paths: list[Path],
) -> dict:
    """Run one tester's multimodal review of all candidates."""
    content: list[dict] = []
    for i, img_path in enumerate(image_paths, 1):
        content.append({"type": "text", "text": f"--- Candidate {i} ---\nDesign screenshot:"})
        content.append({
            "type": "image_url",
            "image_url": {"url": _image_url(img_path)},
        })

    client = get_client()
    resp = client.chat.completions.create(
        model=TEXT_MODEL,
        temperature=0.3,
        max_tokens=3000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": content},
        ],
    )

    review = json.loads(resp.choices[0].message.content)

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
    """Send all 3 candidates to OpenAI for critique.

    Args:
        user_prompt: Original user prompt (not leaked to testers).
        designer_prompts: The 3 designer prompts (not leaked to testers).
        image_paths: Paths to the 3 candidate PNGs.
        tester_system_instructions: 3 system instruction strings from Pass 1.
            If None, uses a generic fallback (backward compat).
    """
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
        review = _run_tester_review(system_instruction=sysinstruct, image_paths=image_paths)
        tester_reviews.append(review)

    critique = _aggregate_tester_reviews(tester_reviews)

    if "winner" not in critique or "scores" not in critique:
        raise ValueError(f"Invalid critique response: {critique}")

    return critique
