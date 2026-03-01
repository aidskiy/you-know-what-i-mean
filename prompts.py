"""Generate 3 distinct designer-style prompts from a user prompt using OpenAI."""

import json

import weave

from gemini_client import get_client, TEXT_MODEL

SYSTEM_INSTRUCTION = """\
You are a world-class UI/UX design director.
Given a rough product idea, produce exactly 3 distinct visual design prompts.
Each prompt must target a different aesthetic style:
  1. Minimal / Swiss – clean grids, monochrome palette, lots of whitespace.
  2. Editorial / Magazine – bold typography, layered imagery, rich colour.
  3. Playful / Illustrative – rounded shapes, pastel colours, friendly illustrations.
"""

PROMPTS_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "designer_prompts",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "minimal_swiss": {"type": "string"},
                "editorial_magazine": {"type": "string"},
                "playful_illustrative": {"type": "string"},
            },
            "required": ["minimal_swiss", "editorial_magazine", "playful_illustrative"],
            "additionalProperties": False,
        },
    },
}


@weave.op()
def generate_designer_prompts(user_prompt: str) -> list[str]:
    """Call OpenAI to produce 3 designer prompts."""
    client = get_client()
    resp = client.chat.completions.create(
        model=TEXT_MODEL,
        temperature=1.0,
        max_tokens=2000,
        response_format=PROMPTS_SCHEMA,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
    )

    data = json.loads(resp.choices[0].message.content)
    prompts = [data["minimal_swiss"], data["editorial_magazine"], data["playful_illustrative"]]

    return [str(p) for p in prompts]
