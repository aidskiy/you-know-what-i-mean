"""Weave-compatible scorers for design evaluation."""

import base64
import json

import weave

from gemini_client import get_client, TEXT_MODEL


def _image_url(image_path: str) -> str:
    """Build a data URL from an image file for OpenAI vision."""
    img_bytes = open(image_path, "rb").read()
    b64 = base64.b64encode(img_bytes).decode()
    return f"data:image/png;base64,{b64}"


class CompositeScorer(weave.Scorer):
    """Scores a design candidate on fidelity and visual quality via OpenAI."""

    @weave.op()
    def score(self, output: dict) -> dict:
        user_prompt = output["user_prompt"]
        prompt_text = (
            f"You are a senior UI/UX design critic.\n"
            f"Score this design on two axes (0-10 each):\n"
            f"1. Fidelity: how well it matches the user request: \"{user_prompt}\"\n"
            f"2. Quality: visual polish, layout, typography, colour\n\n"
            f"Designer prompt used: {output['designer_prompt']}\n\n"
            f"Return ONLY JSON:\n"
            f'{{"fidelity": <float>, "quality": <float>, "overall": <float>, '
            f'"reasoning": "<2 sentences>", "suggestions": "<actionable improvement>"}}'
        )

        client = get_client()
        resp = client.chat.completions.create(
            model=TEXT_MODEL,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": _image_url(output["image_path"])},
                        },
                    ],
                }
            ],
        )

        text = resp.choices[0].message.content
        return json.loads(text)
