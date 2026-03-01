"""Pick the best candidate across all rounds and produce final output."""

import argparse
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import weave  # noqa: E402


@weave.op()
def finalize_session(session_id: str) -> dict:
    """Find the best candidate across all rounds and create a summary."""
    session_dir = Path(f"runs/session_{session_id}")
    round_dirs = sorted(session_dir.glob("round_*"))

    best = {"score": -1, "round": 0, "candidate_id": 0, "image_path": "", "prompt": ""}
    trajectory = []

    for round_dir in round_dirs:
        eval_path = round_dir / "eval_results.json"
        manifest_path = round_dir / "manifest.json"
        if not eval_path.exists() or not manifest_path.exists():
            continue

        eval_results = json.loads(eval_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        round_num = manifest["round"]

        # Extract per-candidate scores from eval results
        round_scores = []
        if isinstance(eval_results, dict) and "rows" in eval_results:
            for row in eval_results["rows"]:
                score = row.get("scores", {}).get("CompositeScorer", {}).get("overall", 0)
                round_scores.append(score)
                cid = row.get("candidate_id", len(round_scores))
                if score > best["score"]:
                    best = {
                        "score": score,
                        "round": round_num,
                        "candidate_id": cid,
                        "image_path": manifest["image_paths"][cid - 1],
                        "prompt": manifest["designer_prompts"][cid - 1],
                    }

        trajectory.append({
            "round": round_num,
            "scores": round_scores,
            "best": max(round_scores) if round_scores else 0,
            "avg": sum(round_scores) / len(round_scores) if round_scores else 0,
        })

    # Copy winner to final/
    final_dir = session_dir / "final"
    final_dir.mkdir(exist_ok=True)
    if best["image_path"] and Path(best["image_path"]).exists():
        shutil.copy2(best["image_path"], final_dir / "winner.png")
        (final_dir / "winner_prompt.txt").write_text(best["prompt"], encoding="utf-8")

    summary = {
        "session_id": session_id,
        "total_rounds": len(round_dirs),
        "trajectory": trajectory,
        "winner": best,
    }

    summary_path = session_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description="Finalize session — pick winner")
    parser.add_argument("--session", required=True, help="Session ID")
    args = parser.parse_args()

    weave.init(project_name=os.environ.get("WANDB_PROJECT", "design-self-improve"))

    print(f"\n▸ Finalizing session {args.session}\n")
    finalize_session(args.session)


if __name__ == "__main__":
    main()
