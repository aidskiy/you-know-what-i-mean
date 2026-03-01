"""Run Weave Evaluation on design candidates from a round."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import weave  # noqa: E402

from scorers import CompositeScorer  # noqa: E402


@weave.op()
def load_dataset(session_id: str, round_num: int) -> list[dict]:
    """Load round manifest and build evaluation dataset."""
    manifest_path = Path(f"runs/session_{session_id}/round_{round_num}/manifest.json")
    manifest = json.loads(manifest_path.read_text())

    examples = []
    for i, (prompt, img_path) in enumerate(
        zip(manifest["designer_prompts"], manifest["image_paths"]),
    ):
        examples.append({
            "candidate_id": i + 1,
            "designer_prompt": prompt,
            "image_path": img_path,
            "user_prompt": manifest["user_prompt"],
        })
    return examples


@weave.op()
def design_model(candidate_id: int, designer_prompt: str, image_path: str, user_prompt: str) -> dict:
    """Identity model — passes candidate data through for scoring."""
    return {
        "candidate_id": candidate_id,
        "designer_prompt": designer_prompt,
        "image_path": image_path,
        "user_prompt": user_prompt,
    }


async def run_evaluation(session_id: str, round_num: int):
    """Run Weave evaluation and save results."""
    dataset = load_dataset(session_id, round_num)

    evaluation = weave.Evaluation(
        name=f"design-eval-round-{round_num}",
        dataset=dataset,
        scorers=[CompositeScorer()],
    )

    results = await evaluation.evaluate(design_model)

    # Save results locally for quick access
    out_path = Path(f"runs/session_{session_id}/round_{round_num}/eval_results.json")
    out_path.write_text(json.dumps(results, indent=2, default=str))

    print(json.dumps(results, indent=2, default=str))
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate design candidates")
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument("--round", type=int, required=True, help="Round number to evaluate")
    args = parser.parse_args()

    weave.init(project_name=os.environ.get("WANDB_PROJECT", "design-self-improve"))

    print(f"\n▸ Evaluating session {args.session} — Round {args.round}\n")
    asyncio.run(run_evaluation(args.session, args.round))


if __name__ == "__main__":
    main()
