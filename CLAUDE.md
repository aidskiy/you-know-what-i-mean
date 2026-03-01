# Design Self-Improvement Pipeline

AI-driven design generation with automatic evaluation and iterative refinement.
Claude Code is the orchestrator — it runs scripts, inspects results via W&B MCP tools, and decides when to iterate.

## Environment

- **Required env vars**: `GEMINI_API_KEY`, `WANDB_API_KEY`
- **W&B project**: `WANDB_PROJECT` (default: `design-self-improve`)
- **Python deps**: `pip install -r requirements.txt`
- **W&B MCP Server**: configured in `.mcp.json` (hosted at `https://mcp.withwandb.com/mcp`)

## Workflow: Self-Improving Design Loop

When the user provides a design prompt, run this loop:

### Step 1: Generate (Round 1)

```bash
python generate.py "<user_prompt>" --round 1 --session <timestamp>
```

This produces 3 designer prompts (Minimal/Swiss, Editorial/Magazine, Playful/Illustrative) and 3 images.
Outputs saved to `runs/session_<id>/round_1/`. All calls traced to Weave via `@weave.op()`.

### Step 2: Evaluate

```bash
python evaluate.py --session <session_id> --round 1
```

Runs a Weave Evaluation with `CompositeScorer` — scores each candidate on fidelity (0-10) and quality (0-10) via Gemini multimodal. Results saved to `eval_results.json` and logged to Weave.

### Step 3: Inspect Results via W&B MCP

Use `query_weave_traces_tool` to read the evaluation results from Weave.
Look for the evaluation traces for the current project. Extract:
- Per-candidate scores (fidelity, quality, overall)
- Improvement suggestions
- Best score and average score

Also read `runs/session_<id>/round_<N>/eval_results.json` for quick local access.

### Step 4: Decide

Apply these rules:
- If **best_score >= 8.0** AND **round >= 2**: STOP — quality is sufficient
- If **round >= 5**: STOP — max rounds reached
- If scores are **stagnating** (improved < 0.3 from previous round): STOP
- Otherwise: CONTINUE to Step 5

Explain your reasoning when deciding to continue or stop.

### Step 5: Refine

```bash
python refine.py "<user_prompt>" --session <session_id> --round <current_round>
```

This reads the evaluation results, generates 3 improved prompts, and saves them to `refined_prompts.json`.
Then generate the next round:

```bash
python generate.py "<user_prompt>" --round <next_round> --session <session_id> \
  --refined-prompts-file runs/session_<id>/round_<current>/refined_prompts.json
```

Go back to Step 2.

### Step 6: Finalize

```bash
python finalize.py --session <session_id>
```

This picks the best candidate across all rounds and copies it to `runs/session_<id>/final/`.

Then use `create_wandb_report_tool` to create a W&B Report summarizing:
- The user's original prompt
- Score trajectory across rounds (best and average per round)
- The winning design and its prompt
- Key improvements made across rounds

## File Overview

| File | Purpose |
|------|---------|
| `generate.py` | Single-round: 3 prompts + 3 images → Weave traced |
| `evaluate.py` | Weave Evaluation with CompositeScorer |
| `scorers.py` | Gemini multimodal scorer (fidelity + quality) |
| `refine.py` | Generate improved prompts from eval feedback |
| `finalize.py` | Pick best candidate, create summary |
| `prompts.py` | Gemini text → 3 designer prompts (Weave traced) |
| `gemini_image.py` | Gemini image generation (Weave traced) |
