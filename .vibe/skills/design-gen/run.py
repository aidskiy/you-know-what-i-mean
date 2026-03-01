"""Vibe skill entrypoint – wraps the existing pipeline."""

import os
import sys

# Ensure the project root is on the import path so we can reuse the pipeline.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from main import run_pipeline  # noqa: E402


def run():
    # Vibe passes the user prompt as a CLI argument.
    if len(sys.argv) < 2:
        print("Error: No prompt provided.")
        print('Usage: /design3 "your design prompt here"')
        sys.exit(1)

    user_prompt = sys.argv[1]

    # Validate required env vars early.
    missing = [v for v in ("GEMINI_API_KEY", "WANDB_API_KEY") if not os.environ.get(v)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    run_pipeline(user_prompt)


if __name__ == "__main__":
    run()
