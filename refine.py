"""Refine designer prompts based on critique feedback, audience, and style assignments."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import weave  # noqa: E402

from gemini_client import get_client, TEXT_MODEL  # noqa: E402

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
- Evaluation results with scores, reasoning, and improvement suggestions

Your job: produce 3 NEW designer prompts that improve on the previous round.
- Keep what worked well (especially from the winning candidate).
- Address the specific improvement suggestions from the critique.
- Maintain 3 distinct aesthetic styles.
- Each prompt should be more specific and refined than the previous round.
"""

REFINE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "refined_prompts",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "minimal_swiss": {"type": "string"},
                "editorial_magazine": {"type": "string"},
                "playful_illustrative": {"type": "string"},
            },
            "required": ["minimal_swiss", "editorial_magazine", "playful_illustrative"],
            "additionalProperties": False,
        },
    },
}


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

    client = get_client()
    resp = client.chat.completions.create(
        model=TEXT_MODEL,
        temperature=0.8,
        max_tokens=4000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION_V2},
            {"role": "user", "content": context},
        ],
    )

    data = json.loads(resp.choices[0].message.content)

    if not isinstance(data, dict) or "prompts" not in data:
        raise ValueError(f"Expected JSON object with 'prompts', got: {json.dumps(data)[:300]}")
    if len(data["prompts"]) != 3:
        raise ValueError(f"Expected 3 prompts, got {len(data['prompts'])}")

    return {
        "style_assignments": data.get("style_assignments", style_assignments),
        "prompts": [str(p).strip() for p in data["prompts"]],
    }


# ---------- Backward-compatible legacy refine --------------------------------

@weave.op()
def refine_prompts(
    user_prompt: str,
    previous_prompts: list[str],
    eval_feedback: dict,
) -> list[str]:
    """Legacy: Generate 3 improved designer prompts (no audience/style context)."""
    context = (
        f"Original user request: {user_prompt}\n\n"
        f"Previous designer prompts:\n"
    )
    for i, p in enumerate(previous_prompts, 1):
        context += f"  {i}. {p}\n"
    context += f"\nEvaluation results:\n{json.dumps(eval_feedback, indent=2)}\n"

    client = get_client()
    resp = client.chat.completions.create(
        model=TEXT_MODEL,
        temperature=0.8,
        max_tokens=2000,
        response_format=REFINE_SCHEMA,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION_LEGACY},
            {"role": "user", "content": context},
        ],
    )

    data = json.loads(resp.choices[0].message.content)
    prompts = [data["minimal_swiss"], data["editorial_magazine"], data["playful_illustrative"]]

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
