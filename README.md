# You Know What I Mean

Minimal pipeline: **user prompt → 3 designer-style prompts → 3 images (Gemini) → Weights & Biases**.

## Install

```bash
pip install -r requirements.txt
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | **yes** | Google AI Studio / Gemini API key |
| `WANDB_API_KEY` | **yes** | Weights & Biases API key |
| `WANDB_PROJECT` | no | W&B project name (default: `design-self-improve`) |

## Usage

```bash
python main.py "Design a clean nutrition app card with one box and back button"
```

### What happens

1. Gemini generates **3 distinct designer prompts** (minimal, editorial, playful).
2. Each prompt is sent to **Gemini image generation** to produce a PNG.
3. Images and prompts are saved locally under `runs/session_<id>/`.
4. Everything is logged to **W&B**: images, a comparison table, and an artifact bundle.

## Mistral Vibe Skill

This project includes a **Vibe skill** at `.vibe/skills/design-gen/`. Vibe automatically discovers project skills in that directory.

### Setup

1. Open this repo in Vibe.
2. Make sure `GEMINI_API_KEY` and `WANDB_API_KEY` are set in your environment.

### Run via slash command

```
/design3 "Design a clean nutrition app card with one box and back button"
```

The skill is marked `user-invocable: true`, so it appears as a slash command in Vibe. It runs the same pipeline as `main.py` — 3 designer prompts, 3 images, W&B logging.

## Output Structure

```
runs/session_<id>/
├── images/
│   ├── candidate_1.png
│   ├── candidate_2.png
│   └── candidate_3.png
├── prompts/
│   ├── designer_prompt_1.txt
│   ├── designer_prompt_2.txt
│   └── designer_prompt_3.txt
└── session_spec.json
```
