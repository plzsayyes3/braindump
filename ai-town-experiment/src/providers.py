from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResult:
    text: str
    model: str
    provider: str
    usage: dict[str, Any]


def _require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def call_openai(system_prompt: str, user_prompt: str, max_tokens: int) -> ProviderResult:
    from openai import OpenAI

    model = _require(os.getenv("OPENAI_MODEL"), "OPENAI_MODEL")
    client = OpenAI(api_key=_require(os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY"))
    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=user_prompt,
        max_output_tokens=max_tokens,
    )
    usage = {}
    if getattr(response, "usage", None):
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
            "total_tokens": getattr(response.usage, "total_tokens", None),
        }
    return ProviderResult(
        text=response.output_text,
        model=model,
        provider="openai",
        usage=usage,
    )


def call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int) -> ProviderResult:
    import anthropic

    model = _require(os.getenv("ANTHROPIC_MODEL"), "ANTHROPIC_MODEL")
    client = anthropic.Anthropic(api_key=_require(os.getenv("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    usage = {
        "input_tokens": getattr(response.usage, "input_tokens", None),
        "output_tokens": getattr(response.usage, "output_tokens", None),
    }
    return ProviderResult(text=text, model=model, provider="anthropic", usage=usage)


def call_gemini(system_prompt: str, user_prompt: str, max_tokens: int) -> ProviderResult:
    from google import genai
    from google.genai import types

    model = _require(os.getenv("GEMINI_MODEL"), "GEMINI_MODEL")
    client = genai.Client(api_key=_require(os.getenv("GEMINI_API_KEY"), "GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
        ),
    )
    usage_meta = getattr(response, "usage_metadata", None)
    usage = {}
    if usage_meta:
        usage = {
            "input_tokens": getattr(usage_meta, "prompt_token_count", None),
            "output_tokens": getattr(usage_meta, "candidates_token_count", None),
            "total_tokens": getattr(usage_meta, "total_token_count", None),
        }
    return ProviderResult(text=response.text or "", model=model, provider="google", usage=usage)


def call_provider(faction: str, system_prompt: str, user_prompt: str, max_tokens: int) -> ProviderResult:
    if faction == "chatgpt":
        return call_openai(system_prompt, user_prompt, max_tokens)
    if faction == "claude":
        return call_anthropic(system_prompt, user_prompt, max_tokens)
    if faction == "gemini":
        return call_gemini(system_prompt, user_prompt, max_tokens)
    raise ValueError(f"Unknown faction: {faction}")
