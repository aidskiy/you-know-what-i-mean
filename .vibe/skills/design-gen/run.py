"""Vibe skill entrypoint – runs a single generation round."""

import os
import sys
import time

# Ensure the project root is on the import path.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

import weave  # noqa: E402
from generate import generate_round  # noqa: E402


def run():
    if len(sys.argv) < 2:
        print("Error: No prompt provided.")
        print('Usage: /design3 "your design prompt here"')
        sys.exit(1)

    user_prompt = sys.argv[1]

    missing = [v for v in ("GEMINI_API_KEY", "WANDB_API_KEY") if not os.environ.get(v)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    weave.init(project_name=os.environ.get("WANDB_PROJECT", "design-self-improve"))
    session_id = str(int(time.time()))
    generate_round(user_prompt, session_id, round_num=1)


if __name__ == "__main__":
    run()
