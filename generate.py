"""Generate 3 designer prompts and 3 images for a single round."""

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import weave  # noqa: E402

from prompts import generate_designer_prompts  # noqa: E402
from gemini_image import generate_image  # noqa: E402


@weave.op()
def generate_round(
    user_prompt: str,
    session_id: str,
    round_num: int,
    refined_prompts: list[str] | None = None,
) -> dict:
    """Generate prompts + images for one round. Returns metadata dict."""
    round_dir = Path(f"runs/session_{session_id}/round_{round_num}")
    images_dir = round_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if refined_prompts:
        designer_prompts = refined_prompts
        print(f"  Using {len(refined_prompts)} refined prompts from previous round")
    else:
        print("  Generating initial designer prompts …")
        designer_prompts = generate_designer_prompts(user_prompt)

    for i, dp in enumerate(designer_prompts, 1):
        print(f"  {i}. {dp[:120]}{'…' if len(dp) > 120 else ''}")

    print("\n  Generating images …")
    image_paths = []
    for i, dp in enumerate(designer_prompts, 1):
        print(f"  Candidate {i} …")
        path = generate_image(dp, images_dir / f"candidate_{i}.png")
        image_paths.append(str(path))

    result = {
        "session_id": session_id,
        "round": round_num,
        "user_prompt": user_prompt,
        "designer_prompts": designer_prompts,
        "image_paths": image_paths,
    }

    # Save round manifest
    manifest_path = round_dir / "manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2))
    print(f"\n  ✓ Round {round_num} complete → {round_dir}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate design candidates for one round")
    parser.add_argument("prompt", help="User design prompt")
    parser.add_argument("--round", type=int, default=1, help="Round number")
    parser.add_argument("--session", default=None, help="Session ID (default: timestamp)")
    parser.add_argument(
        "--refined-prompts-file", default=None,
        help="Path to JSON file with refined prompts from previous round",
    )
    args = parser.parse_args()

    session_id = args.session or str(int(time.time()))

    weave.init(project_name=os.environ.get("WANDB_PROJECT", "design-self-improve"))

    refined = None
    if args.refined_prompts_file:
        refined = json.loads(Path(args.refined_prompts_file).read_text())

    print(f"\n▸ Session {session_id} — Round {args.round}")
    print(f"▸ Prompt: {args.prompt}\n")

    result = generate_round(args.prompt, session_id, args.round, refined)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
