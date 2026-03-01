"""Refine designer prompts based on evaluation feedback."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import httpx  # noqa: E402
import weave  # noqa: E402

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
- Evaluation results with scores, reasoning, and improvement suggestions

Your job: produce 3 NEW designer prompts that improve on the previous round.
- Keep what worked well (especially from the highest-scoring candidate).
- Address the specific improvement suggestions from the evaluation.
- Maintain the 3 distinct aesthetic styles (Minimal/Swiss, Editorial/Magazine, Playful/Illustrative).
- Each prompt should be more specific and refined than the previous round.

Return ONLY a JSON array of 3 strings, no markdown, no explanation.
"""


@weave.op()
def refine_prompts(
    user_prompt: str,
    previous_prompts: list[str],
    eval_feedback: dict,
) -> list[str]:
    """Generate 3 improved designer prompts using evaluation feedback."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    context = (
        f"Original user request: {user_prompt}\n\n"
        f"Previous designer prompts:\n"
    )
    for i, p in enumerate(previous_prompts, 1):
        context += f"  {i}. {p}\n"
    context += f"\nEvaluation results:\n{json.dumps(eval_feedback, indent=2)}\n"

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


def main():
    parser = argparse.ArgumentParser(description="Refine prompts based on evaluation")
    parser.add_argument("prompt", help="Original user design prompt")
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument("--round", type=int, required=True, help="Round to refine from")
    args = parser.parse_args()

    weave.init(project_name=os.environ.get("WANDB_PROJECT", "design-self-improve"))

    round_dir = Path(f"runs/session_{args.session}/round_{args.round}")
    eval_path = round_dir / "eval_results.json"
    manifest_path = round_dir / "manifest.json"

    eval_results = json.loads(eval_path.read_text())
    manifest = json.loads(manifest_path.read_text())

    print(f"\n▸ Refining prompts from round {args.round}\n")
    new_prompts = refine_prompts(args.prompt, manifest["designer_prompts"], eval_results)

    # Save refined prompts for next round's generate.py
    out_path = round_dir / "refined_prompts.json"
    out_path.write_text(json.dumps(new_prompts, indent=2))

    for i, p in enumerate(new_prompts, 1):
        print(f"  {i}. {p[:120]}{'…' if len(p) > 120 else ''}")
    print(f"\n  ✓ Saved refined prompts → {out_path}")


if __name__ == "__main__":
    main()
