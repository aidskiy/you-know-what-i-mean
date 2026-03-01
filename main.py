"""2-pass pipeline: audience → styles → images → critique → refine → W&B."""

import argparse
import json
import sys
import time
from pathlib import Path

from audience import generate_testers
from prompts import generate_designer_prompts, generate_designer_prompts_v2
from gemini_image import generate_image
from critique import critique_candidates
from refine import refine_prompts, refine_prompts_v2
from wandb_log import log_session, log_loop


def _extract_tester_instructions(testers: dict) -> list[str]:
    """Pull the 3 system_instruction strings from the testers dict."""
    return [t["system_instruction"] for t in testers["testers"]]


def _save_testers_json(testers: dict, session_dir: Path) -> Path:
    """Persist testers to disk for debugging / artifact logging."""
    path = session_dir / "testers.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(testers, indent=2), encoding="utf-8")
    return path


def _save_styles_json(style_assignments: list[dict], session_dir: Path) -> Path:
    """Persist style assignments to disk."""
    path = session_dir / "styles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(style_assignments, indent=2), encoding="utf-8")
    return path


def _print_prompts(designer_prompts: list[str], style_assignments: list[dict] | None = None):
    for i, dp in enumerate(designer_prompts, 1):
        style_tag = ""
        if style_assignments:
            sa = next((s for s in style_assignments if s["candidate"] == i), None)
            if sa:
                style_tag = f" [{sa['style']}]"
        print(f"  {i}.{style_tag} {dp[:120]}{'…' if len(dp) > 120 else ''}")


def run_pipeline(user_prompt: str) -> Path:
    """Run the full 2-pass pipeline once (no self-improvement loop)."""
    session_id = str(int(time.time()))
    session_dir = Path(f"runs/session_{session_id}")
    images_dir = session_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n▸ Session {session_id}")
    print(f"▸ Prompt: {user_prompt}\n")

    # Pass 1 – generate tester personas
    print("[1/4] Pass 1: Generating tester personas …")
    testers = generate_testers(user_prompt)
    _save_testers_json(testers, session_dir)
    for i, t in enumerate(testers["testers"], 1):
        v = t["vector"]
        print(f"  Tester {i}: {t['name']} – {v['economic_role']}/{v['price_tolerance']}/{v['emotional_driver']}")

    # Pass 2 – select styles + generate designer prompts
    print("\n[2/4] Pass 2: Selecting styles & generating prompts …")
    pass2 = generate_designer_prompts_v2(user_prompt, testers)
    designer_prompts = pass2["prompts"]
    style_assignments = pass2["style_assignments"]
    _save_styles_json(style_assignments, session_dir)
    _print_prompts(designer_prompts, style_assignments)

    # Generate images
    print("\n[3/4] Generating images …")
    image_paths: list[Path] = []
    for i, dp in enumerate(designer_prompts, 1):
        print(f"  Candidate {i} …")
        path = generate_image(dp, images_dir / f"candidate_{i}.png")
        image_paths.append(path)

    # Log to W&B
    print("\n[4/4] Logging to W&B …")
    log_session(
        session_id, user_prompt, designer_prompts, image_paths,
        testers=testers, style_assignments=style_assignments,
    )

    print(f"\n✓ Done. Outputs in {session_dir}\n")
    return session_dir


def run_loop(user_prompt: str, rounds: int = 3) -> Path:
    """Run the 2-pass self-improving loop for N rounds."""
    session_id = str(int(time.time()))
    session_dir = Path(f"runs/session_{session_id}")

    print(f"\n▸ Session {session_id}  ({rounds} rounds)")
    print(f"▸ Prompt: {user_prompt}\n")

    # Pass 1 – generate tester personas (once, reused across all rounds)
    print("[pass 1] Generating tester personas …")
    testers = generate_testers(user_prompt)
    _save_testers_json(testers, session_dir)
    tester_instructions = _extract_tester_instructions(testers)
    for i, t in enumerate(testers["testers"], 1):
        v = t["vector"]
        print(f"  Tester {i}: {t['name']} – {v['economic_role']}/{v['price_tolerance']}/{v['emotional_driver']}")

    rounds_data: list[dict] = []
    prev_prompts: list[str] = []
    style_assignments: list[dict] = []
    critique: dict = {}

    for round_num in range(1, rounds + 1):
        print(f"\n{'='*60}")
        print(f"  ROUND {round_num}/{rounds}")
        print(f"{'='*60}")

        round_dir = session_dir / f"round_{round_num}"
        images_dir = round_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Pass 2 / Refine
        if round_num == 1:
            print("\n[pass 2] Selecting styles & generating prompts …")
            pass2 = generate_designer_prompts_v2(user_prompt, testers)
            designer_prompts = pass2["prompts"]
            style_assignments = pass2["style_assignments"]
        else:
            print("\n[refine] Improving prompts based on critique …")
            refined = refine_prompts_v2(
                user_prompt, prev_prompts, style_assignments, testers, critique,
            )
            designer_prompts = refined["prompts"]
            style_assignments = refined["style_assignments"]

        _save_styles_json(style_assignments, round_dir)
        _print_prompts(designer_prompts, style_assignments)

        # Generate images
        print("\n[image] Generating images …")
        image_paths: list[Path] = []
        for i, dp in enumerate(designer_prompts, 1):
            print(f"  Candidate {i} …")
            path = generate_image(dp, images_dir / f"candidate_{i}.png")
            image_paths.append(path)

        # Critique (using dynamic tester instructions from Pass 1)
        print("\n[critique] Evaluating candidates …")
        critique = critique_candidates(
            user_prompt, designer_prompts, image_paths,
            tester_system_instructions=tester_instructions,
        )
        winner = critique["winner"]
        for s in critique["scores"]:
            marker = " ◀ winner" if s["candidate"] == winner else ""
            print(f"  Candidate {s['candidate']}: {s['score']}/10 – {s['reasoning'][:100]}{marker}")
        print(f"  Suggestions: {critique['improvement_suggestions'][:200]}")

        rounds_data.append({
            "round": round_num,
            "designer_prompts": designer_prompts,
            "style_assignments": style_assignments,
            "image_paths": image_paths,
            "critique": critique,
        })
        prev_prompts = designer_prompts

    # Log everything to W&B
    print(f"\n{'='*60}")
    print("  LOGGING TO W&B")
    print(f"{'='*60}\n")
    log_loop(session_id, user_prompt, rounds_data, testers=testers)

    # Print final summary
    final = rounds_data[-1]["critique"]
    print(f"\n✓ Done. {rounds} rounds completed.")
    print(f"  Final winner: Candidate {final['winner']}")
    print(f"  Final best score: {max(s['score'] for s in final['scores'])}/10")
    print(f"  Outputs in {session_dir}\n")
    return session_dir


def main():
    parser = argparse.ArgumentParser(description="2-pass design generation pipeline")
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
