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
) -> None:
    """Create a W&B run and log all session data."""
    project = os.environ.get("WANDB_PROJECT", "design-self-improve")

    run = wandb.init(
        project=project,
        name=f"session-{session_id}",
        group=session_id,
        config={"user_prompt": user_prompt},
    )

    # --- W&B Table -----------------------------------------------------------
    table = wandb.Table(columns=["candidate_id", "designer_prompt", "image"])
    for i, (prompt, img_path) in enumerate(zip(designer_prompts, image_paths)):
        table.add_data(i + 1, prompt, wandb.Image(str(img_path)))

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
    for i, prompt in enumerate(designer_prompts):
        prompt_path = img_path.parent.parent / "prompts" / f"designer_prompt_{i+1}.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        artifact.add_file(str(prompt_path), name=f"prompts/designer_prompt_{i+1}.txt")

    # images/*.png
    for i, img_path in enumerate(image_paths):
        artifact.add_file(str(img_path), name=f"images/candidate_{i+1}.png")

    # session_spec.json
    spec = {
        "session_id": session_id,
        "user_prompt": user_prompt,
        "designer_prompts": designer_prompts,
        "image_files": [str(p) for p in image_paths],
    }
    spec_path = image_paths[0].parent.parent / "session_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    artifact.add_file(str(spec_path), name="session_spec.json")

    run.log_artifact(artifact)
    run.finish()
    print(f"  ✓ W&B run logged → project={project}  group={session_id}")
