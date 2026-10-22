"""Turn raw diagnostic data into a short spoken answer using Amazon Bedrock.

How Bedrock is used:
  - boto3 client "bedrock-runtime", region from AWS_REGION
  - Converse API with model BEDROCK_MODEL_ID (any Converse-capable model)
  - A system prompt asks for 2-4 short, friendly, spoken-style sentences with
    exactly one concrete suggestion, based only on the JSON we send.
If Bedrock isn't configured or the call fails, we fall back to a template so a
live demo never breaks.
"""

import json
import logging
import os

log = logging.getLogger("rabi.explain")

SYSTEM_PROMPT = (
    "You are Rabi, a warm, practical companion for developers, speaking through a voice assistant. "
    "You get JSON from checks on the user's Mac. Reply in 2 to 4 short spoken sentences: say what is "
    "going on in plain words, then give exactly one concrete suggestion. Use only facts in the JSON; "
    "never invent numbers or apps. No markdown, lists, or emojis, because this will be read aloud."
)


def bedrock_configured() -> bool:
    return bool(os.getenv("BEDROCK_MODEL_ID") and os.getenv("AWS_REGION"))


def _client():
    import boto3  # imported lazily so tests and template mode don't need AWS set up

    return boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])


def ask_bedrock(topic: str, data: dict) -> str:
    """Call the Bedrock Converse API and return the model's text."""
    resp = _client().converse(
        modelId=os.environ["BEDROCK_MODEL_ID"],
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{
            "role": "user",
            "content": [{"text": f"Topic: {topic}\nData:\n{json.dumps(data, default=str)}"}],
        }],
        # Low temperature: we want grounded explanations, not creativity.
        inferenceConfig={"maxTokens": 200, "temperature": 0.3},
    )
    parts = resp["output"]["message"]["content"]
    return " ".join(p["text"] for p in parts if "text" in p).strip()


def explain(topic: str, data: dict) -> dict:
    """Explain `data` for speech. Always returns text; 'source' says where it came from."""
    if bedrock_configured():
        try:
            text = ask_bedrock(topic, data)
            if text:
                return {"text": text, "source": "bedrock"}
        except Exception as e:  # any AWS/network/model error -> template, never a crash
            log.warning("Bedrock failed, using template: %s", e)
    from rabi.templates import template_explanation

    return {"text": template_explanation(topic, data), "source": "template"}
