"""Log images, prompts, and artifacts to Weights & Biases."""

import json
import os
from pathlib import Path

import wandb


def log_session(
    session_id: str,
    user_prompt: str,
    designer_prompts: list[str],
    image_paths: list[Path],
    testers: dict | None = None,
    style_assignments: list[dict] | None = None,
) -> None:
    """Create a W&B run and log all session data (single-round)."""
    project = os.environ.get("WANDB_PROJECT", "design-self-improve")

    config = {"user_prompt": user_prompt}
    if testers:
        config["testers"] = [
            {"name": t["name"], "vector": t["vector"]}
            for t in testers.get("testers", [])
        ]
    if style_assignments:
        config["style_assignments"] = style_assignments

    run = wandb.init(
        project=project,
        name=f"session-{session_id}",
        group=session_id,
        config=config,
    )

    # --- W&B Table -----------------------------------------------------------
    columns = ["candidate_id", "designer_prompt", "image"]
    if style_assignments:
        columns.insert(2, "style")

    table = wandb.Table(columns=columns)
    for i, (prompt, img_path) in enumerate(zip(designer_prompts, image_paths)):
        row = [i + 1, prompt]
        if style_assignments:
            sa = next((s for s in style_assignments if s["candidate"] == i + 1), {})
            row.append(sa.get("style", ""))
        row.append(wandb.Image(str(img_path)))
        table.add_data(*row)

    run.log({"candidates": table})

    # Log each image individually as well
    for i, img_path in enumerate(image_paths):
        run.log({f"candidate_{i+1}": wandb.Image(str(img_path))})

    # --- Artifact -------------------------------------------------------------
    artifact = wandb.Artifact(
        name=f"session-{session_id}-candidates",
        type="design-candidates",
    )

    # prompts/*.txt
    session_dir = image_paths[0].parent.parent
    for i, prompt in enumerate(designer_prompts):
        prompt_path = session_dir / "prompts" / f"designer_prompt_{i+1}.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        artifact.add_file(str(prompt_path), name=f"prompts/designer_prompt_{i+1}.txt")

    # images/*.png
    for i, img_path in enumerate(image_paths):
        artifact.add_file(str(img_path), name=f"images/candidate_{i+1}.png")

    # testers.json
    if testers:
        testers_path = session_dir / "testers.json"
        if testers_path.exists():
            artifact.add_file(str(testers_path), name="testers.json")

    # styles.json
    if style_assignments:
        styles_path = session_dir / "styles.json"
        if styles_path.exists():
            artifact.add_file(str(styles_path), name="styles.json")

    # session_spec.json
    spec = {
        "session_id": session_id,
        "user_prompt": user_prompt,
        "designer_prompts": designer_prompts,
        "image_files": [str(p) for p in image_paths],
    }
    if style_assignments:
        spec["style_assignments"] = style_assignments
    spec_path = session_dir / "session_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    artifact.add_file(str(spec_path), name="session_spec.json")

    run.log_artifact(artifact)
    run.finish()
    print(f"  ✓ W&B run logged → project={project}  group={session_id}")


def log_loop(
    session_id: str,
    user_prompt: str,
    rounds_data: list[dict],
    testers: dict | None = None,
) -> None:
    """Log a multi-round self-improving session to W&B.

    rounds_data is a list of dicts, one per round:
      {
        "round": int,
        "designer_prompts": list[str],
        "style_assignments": list[dict],  # optional
        "image_paths": list[Path],
        "critique": dict,
      }
    """
    project = os.environ.get("WANDB_PROJECT", "design-self-improve")

    config = {
        "user_prompt": user_prompt,
        "total_rounds": len(rounds_data),
    }
    if testers:
        config["testers"] = [
            {"name": t["name"], "vector": t["vector"]}
            for t in testers.get("testers", [])
        ]

    run = wandb.init(
        project=project,
        name=f"loop-{session_id}",
        group=session_id,
        config=config,
    )

    # --- Per-round table with all candidates across rounds -------------------
    table = wandb.Table(columns=[
        "round", "candidate_id", "style", "designer_prompt", "image", "score", "reasoning",
    ])

    for rd in rounds_data:
        round_num = rd["round"]
        critique = rd["critique"]
        scores_by_id = {s["candidate"]: s for s in critique["scores"]}
        styles = rd.get("style_assignments", [])

        for i, (prompt, img_path) in enumerate(
            zip(rd["designer_prompts"], rd["image_paths"]),
        ):
            cid = i + 1
            score_info = scores_by_id.get(cid, {})
            sa = next((s for s in styles if s.get("candidate") == cid), {})
            table.add_data(
                round_num,
                cid,
                sa.get("style", ""),
                prompt,
                wandb.Image(str(img_path)),
                score_info.get("score", 0),
                score_info.get("reasoning", ""),
            )

    run.log({"all_candidates": table})

    # --- Score trajectory (line chart) ---------------------------------------
    for rd in rounds_data:
        round_num = rd["round"]
        critique = rd["critique"]
        best_score = max(s["score"] for s in critique["scores"])
        avg_score = sum(s["score"] for s in critique["scores"]) / len(critique["scores"])
        run.log({
            "round": round_num,
            "best_score": best_score,
            "avg_score": avg_score,
            "winner": critique["winner"],
        })

    # --- Artifact with all rounds --------------------------------------------
    artifact = wandb.Artifact(
        name=f"loop-{session_id}-all-rounds",
        type="design-loop",
    )

    session_dir = rounds_data[0]["image_paths"][0].parent.parent

    # testers.json (saved by main.py at session root)
    if testers:
        testers_path = session_dir / "testers.json"
        if testers_path.exists():
            artifact.add_file(str(testers_path), name="testers.json")

    for rd in rounds_data:
        round_num = rd["round"]
        round_prefix = f"round_{round_num}"

        for i, prompt in enumerate(rd["designer_prompts"]):
            prompt_path = rd["image_paths"][0].parent / f"designer_prompt_{i+1}.txt"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(prompt, encoding="utf-8")
            artifact.add_file(
                str(prompt_path),
                name=f"{round_prefix}/prompts/designer_prompt_{i+1}.txt",
            )

        for i, img_path in enumerate(rd["image_paths"]):
            artifact.add_file(
                str(img_path),
                name=f"{round_prefix}/images/candidate_{i+1}.png",
            )

        # styles.json per round
        styles = rd.get("style_assignments", [])
        if styles:
            styles_path = rd["image_paths"][0].parent / "styles.json"
            if styles_path.exists():
                artifact.add_file(str(styles_path), name=f"{round_prefix}/styles.json")

        # critique.json per round
        critique_path = rd["image_paths"][0].parent / "critique.json"
        critique_path.write_text(json.dumps(rd["critique"], indent=2), encoding="utf-8")
        artifact.add_file(str(critique_path), name=f"{round_prefix}/critique.json")

    # session_spec.json
    spec = {
        "session_id": session_id,
        "user_prompt": user_prompt,
        "total_rounds": len(rounds_data),
        "final_winner": rounds_data[-1]["critique"]["winner"],
        "final_scores": rounds_data[-1]["critique"]["scores"],
    }
    if testers:
        spec["testers"] = [
            {"name": t["name"], "vector": t["vector"]}
            for t in testers.get("testers", [])
        ]
    spec_path = session_dir / "session_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    artifact.add_file(str(spec_path), name="session_spec.json")

    run.log_artifact(artifact)
    run.finish()
    print(f"  ✓ W&B loop logged → project={project}  group={session_id}")
