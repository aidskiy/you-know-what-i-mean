"""Minimal pipeline: user prompt → 3 designer prompts → 3 images → W&B."""

import sys
import time
from pathlib import Path

from prompts import generate_designer_prompts
from gemini_image import generate_image
from wandb_log import log_session


def run_pipeline(user_prompt: str) -> Path:
    """Run the full pipeline and return the session directory."""
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py \"<your design prompt>\"")
        sys.exit(1)

    run_pipeline(sys.argv[1])


if __name__ == "__main__":
    main()
