# Design ~ Storm

An AI design tool that autonomously adapts designs to your target users. Describe your product, and Design Storm generates multiple UI concepts, critiques them through AI-generated user personas, and iteratively refines the designs — all tracked with Weights & Biases.

Built by **binbin** and **Aida**.

![Design Storm Screenshot](frontend/public/screenshot.png)

## How It Works

1. **Audience generation** — AI creates 3 realistic tester personas with 6-dimensional audience vectors (economic role, price tolerance, emotional driver, tech sophistication, time abundance, risk tolerance).
2. **Design prompts** — A design director agent selects 3 styles from a 10-style taxonomy and writes detailed image-generation prompts tailored to each persona.
3. **Image generation** — Each prompt produces a high-fidelity UI mockup via fal.ai.
4. **Critique** — Each persona reviews all 3 candidates with scores and reasoning, then a winner is selected.
5. **Refinement** — The critique feeds back into prompt generation for the next round, keeping what worked and addressing what didn't.
6. **Repeat** — The loop runs for N rounds (configurable), with each iteration improving on the last.

All calls are traced with [Weave](https://wandb.me/weave) for full observability.

## Stack

| Layer | Technology |
|-------|-----------|
| Text / critique | [Mistral AI](https://mistral.ai) (pixtral-large) via OpenAI-compatible API |
| Image generation | [fal.ai](https://fal.ai) (nano-banana-2) |
| Observability | [Weights & Biases](https://wandb.ai) + Weave |
| Backend | Flask (Python) with SSE streaming |
| Frontend | React + TypeScript + Vite |

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd you-know-what-i-mean
make install

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your keys

# 3. Run both backend and frontend
make dev
```

The frontend opens at `http://localhost:5173` and the API runs on `http://localhost:5001`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | **yes** | Mistral AI API key (text generation + critique) |
| `FAL_KEY` | **yes** | fal.ai API key (image generation) |
| `WANDB_API_KEY` | **yes** | Weights & Biases API key |
| `WANDB_PROJECT` | no | W&B project name (default: `design-self-improve`) |

## Usage

### Web UI (recommended)

Run `make dev`, open the frontend, type a product description (e.g. *"A meditation app for busy professionals"*), set the number of rounds, and hit Run. Results stream in live — personas, prompts, images, and scores appear as they're generated.

Click any image in the timeline to expand it. Use the **Expand** button for a full-screen zoomable canvas view.

### CLI

```bash
make run PROMPT="A meditation app for busy professionals" ROUNDS=3
```

## Project Structure

```
server.py              Flask API server (SSE streaming)
audience.py            Generate 3 tester personas with audience vectors
prompts.py             Select styles + write designer prompts
fal_image.py           Image generation via fal.ai
critique.py            Multimodal persona-based critique
refine.py              Improve prompts from critique feedback
scorers.py             Weave-compatible composite scorer
gemini_client.py       Shared Mistral AI client (OpenAI-compatible)
frontend/              React + TypeScript + Vite app
```

## Output
images/<img width="609" height="459" alt="Screenshot 2026-03-01 at 5 49 46 PM" src="https://github.com/user-attachments/assets/ba58909f-8db7-48bf-a03c-1ec5cd085d4c" />
<img width="159" height="409" alt="Screenshot 2026-03-01 at 5 51 02 PM" src="https://github.com/user-attachments/assets/99e35b47-793d-4f2c-b535-7d799476a721" />
<img width="880" height="442" alt="Screenshot 2026-03-01 at 6 09 54 PM" src="https://github.com/user-attachments/assets/c6631857-b738-4121-b772-2260384ee411" />
<img width="864" height="747" alt="Screenshot 2026-03-01 at 6 11 18 PM" src="https://github.com/user-attachments/assets/f840e14d-3842-4a7e-87e4-31f04a7b786d" />



Each run saves artifacts under `runs/session_<id>/`:

```
runs/session_<id>/
  testers.json                    # Generated personas
  round_1/
    styles.json                   # Style assignments

      candidate_1.png
      candidate_2.png
      candidate_3.png
  round_2/
    ...
```
