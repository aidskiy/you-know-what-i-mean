from dotenv import load_dotenv
load_dotenv()

import os
import fal_client

key = os.getenv("FAL_KEY")
if not key:
  raise RuntimeError("Set FAL_KEY in env or .env")

print("Testing fal.ai image generation...")

result = fal_client.run(
  "fal-ai/fast-sdxl",
  arguments={"prompt": "a cute cat, realistic, orange"},
)

print("✅ Success")
print(result)