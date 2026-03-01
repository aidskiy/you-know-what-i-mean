---
name: design-gen
description: Generate and evaluate UI design candidates using OpenAI + fal.ai with Weave tracing and W&B MCP self-improvement
user-invocable: true
compatibility: Python 3.11+
allowed-tools:
  - bash
---

# /design3

Generate 3 distinct designer-style UI images from a single user prompt, evaluate them with AI scoring, and iterate using W&B MCP tools. This skill powers the design generation pipeline used in the current product.

## Command

```
/design3 "Design a clean nutrition app card with one box and back button"
```

## Environment Variables

| Variable | Required | Default |
|---|---|---|
| `OPENAI_API_KEY` | **yes** | — |
| `FAL_API_KEY` | **yes** | — |
| `WANDB_API_KEY` | **yes** | — |
| `WANDB_PROJECT` | no | `design-self-improve` |

## What It Does

1. **Generates 3 designer prompts** (minimal, editorial, playful) via **OpenAI GPT-4o**.
2. **Creates 3 PNG images** via **fal.ai nano-banana-2 model**.
3. **Evaluates candidates** with AI scoring and critique.
4. **Refines prompts** based on feedback for iterative improvement.
5. **All calls traced** to **W&B Weave** via `@weave.op()`.
6. **Saves results** locally under `runs/session_<id>/` with full artifact logging.

## How It Helped Build This Product

This skill is the core engine behind the current design generation flow:
- **Prompt Architecture**: Powers the two-pass system (tester personas → designer prompts)
- **Image Pipeline**: Replaced Gemini with fal.ai for faster, higher-quality outputs
- **Evaluation Framework**: AI scoring and critique drives the refinement loop
- **Experiment Tracking**: W&B integration enables systematic improvement
- **Frontend Integration**: Results feed directly into the Timeline canvas UI

## Entrypoint

```bash
python .vibe/skills/design-gen/run.py "<user prompt>"
```
