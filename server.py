"""Design ~ Storm API server — streams the design pipeline to the frontend via SSE."""

import json
import os
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

import weave

from audience import generate_testers
from prompts import generate_designer_prompts_v2
from fal_image import generate_image
from critique import critique_candidates
from refine import refine_prompts_v2

weave.init(project_name=os.environ.get("WANDB_PROJECT", "design-self-improve"))

app = Flask(__name__)
CORS(app)

RUNS_DIR = Path("runs")


def _build_image_url(image_path: Path) -> str:
    """Convert a local file path to a URL served by this server."""
    rel = image_path.relative_to(RUNS_DIR)
    return f"/files/{rel}"


def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.route("/files/<path:filepath>")
def serve_file(filepath: str):
    """Serve generated images from the runs/ directory."""
    return send_from_directory(str(RUNS_DIR), filepath)


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    """Run the full 2-pass pipeline, streaming progress via SSE."""
    body = request.get_json(force=True)
    user_prompt = body.get("user_prompt", "").strip()
    num_rounds = int(body.get("rounds", 3))

    if not user_prompt:
        return jsonify({"error": "user_prompt is required"}), 400
    if num_rounds < 1 or num_rounds > 10:
        return jsonify({"error": "rounds must be 1-10"}), 400

    def generate():
        try:
            session_id = str(int(time.time()))
            session_dir = RUNS_DIR / f"session_{session_id}"

            yield _sse("status", {"step": "testers", "message": "Generating tester personas…"})

            # --- Pass 1: generate tester personas ---
            print(f"\n[{session_id}] Pass 1: generating testers …")
            testers = generate_testers(user_prompt)

            session_dir.mkdir(parents=True, exist_ok=True)
            (session_dir / "testers.json").write_text(
                json.dumps(testers, indent=2), encoding="utf-8"
            )

            tester_instructions = [t["system_instruction"] for t in testers["testers"]]

            testers_resp = []
            for i, t in enumerate(testers["testers"]):
                testers_resp.append({
                    "tester_id": f"t{i+1}",
                    "name": t["name"],
                    "bio": t.get("bio", ""),
                    "vector": t["vector"],
                })

            yield _sse("testers", {"session_id": session_id, "testers": testers_resp})

            prev_prompts: list[str] = []
            style_assignments: list[dict] = []
            critique: dict = {}

            for round_num in range(1, num_rounds + 1):
                print(f"\n[{session_id}] Round {round_num}/{num_rounds}")

                round_dir = session_dir / f"round_{round_num}"
                images_dir = round_dir / "images"
                images_dir.mkdir(parents=True, exist_ok=True)

                # --- Pass 2 / Refine ---
                yield _sse("status", {
                    "step": "prompts",
                    "round": round_num,
                    "message": f"Round {round_num}: generating prompts…",
                })

                if round_num == 1:
                    pass2 = generate_designer_prompts_v2(user_prompt, testers)
                    designer_prompts = pass2["prompts"]
                    style_assignments = pass2["style_assignments"]
                else:
                    refined = refine_prompts_v2(
                        user_prompt, prev_prompts, style_assignments, testers, critique
                    )
                    designer_prompts = refined["prompts"]
                    style_assignments = refined["style_assignments"]

                (round_dir / "styles.json").write_text(
                    json.dumps(style_assignments, indent=2), encoding="utf-8"
                )

                yield _sse("prompts", {
                    "round": round_num,
                    "style_assignments": style_assignments,
                    "designer_prompts": [
                        {"candidate": i + 1, "prompt": p}
                        for i, p in enumerate(designer_prompts)
                    ],
                })

                # --- Generate images (stream each one) ---
                image_paths: list[Path] = []
                for i, dp in enumerate(designer_prompts, 1):
                    yield _sse("status", {
                        "step": "image",
                        "round": round_num,
                        "candidate": i,
                        "message": f"Round {round_num}: generating image {i}/3…",
                    })
                    path = generate_image(dp, images_dir / f"candidate_{i}.png")
                    image_paths.append(path)

                    yield _sse("image", {
                        "round": round_num,
                        "candidate": i,
                        "url": _build_image_url(path),
                    })

                # --- Critique ---
                yield _sse("status", {
                    "step": "critique",
                    "round": round_num,
                    "message": f"Round {round_num}: evaluating candidates…",
                })

                critique = critique_candidates(
                    user_prompt, designer_prompts, image_paths,
                    tester_system_instructions=tester_instructions,
                )

                yield _sse("critique", {
                    "round": round_num,
                    "critique": {
                        "winner": critique["winner"],
                        "scores": critique["scores"],
                        "improvement_suggestions": critique["improvement_suggestions"],
                        "tester_reviews": critique.get("tester_reviews", []),
                    },
                })

                prev_prompts = designer_prompts

            yield _sse("done", {"session_id": session_id})
            print(f"\n[{session_id}] ✓ Pipeline complete")

        except Exception as e:
            traceback.print_exc()
            yield _sse("error", {"message": str(e)})

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 5001))
    print(f"Starting API server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
