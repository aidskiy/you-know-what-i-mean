---
name: design-gen
description: Generate 3 UI design candidates with Weave-traced evaluation and self-improvement via W&B MCP
user-invocable: true
compatibility: Python 3.11+
allowed-tools:
  - bash
---

# /design3

Generate 3 distinct designer-style UI images from a single user prompt, evaluate them, and iterate using W&B MCP tools.

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

1. Generates 3 designer prompts (minimal, editorial, playful) via **Gemini Flash**.
2. Generates 3 PNG images via **Gemini image generation**.
3. All calls traced to **W&B Weave** via `@weave.op()`.
4. For the full self-improvement loop, see `CLAUDE.md` — Claude Code orchestrates evaluation, refinement, and reporting via W&B MCP tools.

## Entrypoint

```bash
python .vibe/skills/design-gen/run.py "<user prompt>"
```
