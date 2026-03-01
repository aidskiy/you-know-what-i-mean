# mistral_client.py
import os
from mistralai import Mistral

TEXT_MODEL = os.getenv("MISTRAL_TEXT_MODEL", "mistral-large-latest")

def get_client() -> Mistral:
    api_key = os.environ["MISTRAL_API_KEY"]
    return Mistral(api_key=api_key)