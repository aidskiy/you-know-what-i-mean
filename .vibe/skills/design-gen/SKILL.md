---
name: design-gen
description: Generate 3 UI design images from 3 designer prompt variants and log to W&B
user-invocable: true
compatibility: Python 3.11+
allowed-tools:
  - bash
---

# /design3

Generate 3 distinct designer-style UI images from a single user prompt and log everything to Weights & Biases.

## Command

```
/design3 "Design a clean nutrition app card with one box and back button"
```

## Environment Variables

| Variable | Required | Default |
|---|---|---|
| `GEMINI_API_KEY` | **yes** | — |
| `WANDB_API_KEY` | **yes** | — |
| `WANDB_PROJECT` | no | `design-self-improve` |

## What It Does

1. Takes the user prompt and sends it to **Gemini Flash** to produce 3 designer prompts (minimal, editorial, playful styles).
2. Each designer prompt is sent to **Gemini image generation** to produce a PNG.
3. Images and prompts are saved locally under `runs/session_<id>/`.
4. Logs a **W&B Table** (3 rows: candidate_id, designer_prompt, image) and a **W&B Artifact** containing prompts, images, and a `session_spec.json`.

## Entrypoint

```bash
python .vibe/skills/design-gen/run.py "<user prompt>"
```
