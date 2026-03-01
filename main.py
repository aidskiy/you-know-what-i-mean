"""Minimal pipeline: user prompt → 3 designer prompts → 3 images → W&B."""

import argparse
import sys
import time
from pathlib import Path

from prompts import generate_designer_prompts
from gemini_image import generate_image
from critique import critique_candidates
from refine import refine_prompts
from wandb_log import log_session, log_loop


def run_pipeline(user_prompt: str) -> Path:
    """Run the full pipeline once (no self-improvement loop)."""
    session_id = str(int(time.time()))
    session_dir = Path(f"runs/session_{session_id}")
    images_dir = session_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n▸ Session {session_id}")
    print(f"▸ Prompt: {user_prompt}\n")

    # Step 1 – generate 3 designer prompts
    print("[1/3] Generating designer prompts …")
    designer_prompts = generate_designer_prompts(user_prompt)
    for i, dp in enumerate(designer_prompts, 1):
        print(f"  {i}. {dp[:120]}{'…' if len(dp) > 120 else ''}")

    # Step 2 – generate images
    print("\n[2/3] Generating images …")
    image_paths: list[Path] = []
    for i, dp in enumerate(designer_prompts, 1):
        print(f"  Candidate {i} …")
        path = generate_image(dp, images_dir / f"candidate_{i}.png")
        image_paths.append(path)

    # Step 3 – log to W&B
    print("\n[3/3] Logging to W&B …")
    log_session(session_id, user_prompt, designer_prompts, image_paths)

    print(f"\n✓ Done. Outputs in {session_dir}\n")
    return session_dir


def run_loop(user_prompt: str, rounds: int = 3) -> Path:
    """Run the self-improving loop for N rounds."""
    session_id = str(int(time.time()))
    session_dir = Path(f"runs/session_{session_id}")

    print(f"\n▸ Session {session_id}  ({rounds} rounds)")
    print(f"▸ Prompt: {user_prompt}\n")

    rounds_data: list[dict] = []
    prev_prompts: list[str] = []
    critique: dict = {}

    for round_num in range(1, rounds + 1):
        print(f"{'='*60}")
        print(f"  ROUND {round_num}/{rounds}")
        print(f"{'='*60}")

        round_dir = session_dir / f"round_{round_num}"
        images_dir = round_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Generate prompts
        if round_num == 1:
            print("\n[generate] Creating initial designer prompts …")
            designer_prompts = generate_designer_prompts(user_prompt)
        else:
            print("\n[refine] Improving prompts based on critique …")
            designer_prompts = refine_prompts(user_prompt, prev_prompts, critique)

        for i, dp in enumerate(designer_prompts, 1):
            print(f"  {i}. {dp[:120]}{'…' if len(dp) > 120 else ''}")

        # Generate images
        print("\n[image] Generating images …")
        image_paths: list[Path] = []
        for i, dp in enumerate(designer_prompts, 1):
            print(f"  Candidate {i} …")
            path = generate_image(dp, images_dir / f"candidate_{i}.png")
            image_paths.append(path)

        # Critique
        print("\n[critique] Evaluating candidates …")
        critique = critique_candidates(user_prompt, designer_prompts, image_paths)
        winner = critique["winner"]
        for s in critique["scores"]:
            marker = " ◀ winner" if s["candidate"] == winner else ""
            print(f"  Candidate {s['candidate']}: {s['score']}/10 – {s['reasoning']}{marker}")
        print(f"  Suggestions: {critique['improvement_suggestions'][:200]}")

        rounds_data.append({
            "round": round_num,
            "designer_prompts": designer_prompts,
            "image_paths": image_paths,
            "critique": critique,
        })
        prev_prompts = designer_prompts

    # Log everything to W&B
    print(f"\n{'='*60}")
    print("  LOGGING TO W&B")
    print(f"{'='*60}\n")
    log_loop(session_id, user_prompt, rounds_data)

    # Print final summary
    final = rounds_data[-1]["critique"]
    print(f"\n✓ Done. {rounds} rounds completed.")
    print(f"  Final winner: Candidate {final['winner']}")
    print(f"  Final best score: {max(s['score'] for s in final['scores'])}/10")
    print(f"  Outputs in {session_dir}\n")
    return session_dir


def main():
    parser = argparse.ArgumentParser(description="Design generation pipeline")
    parser.add_argument("prompt", help="Your design prompt")
    parser.add_argument(
        "--rounds", type=int, default=3,
        help="Number of self-improvement rounds (default: 3, use 1 for single-shot)",
    )
    args = parser.parse_args()

    if args.rounds < 1:
        print("Error: --rounds must be at least 1")
        sys.exit(1)

    if args.rounds == 1:
        run_pipeline(args.prompt)
    else:
        run_loop(args.prompt, rounds=args.rounds)


if __name__ == "__main__":
    main()
