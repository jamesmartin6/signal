"""LLM client abstraction.

`LLMClient` is deliberately the narrowest possible interface — a system
prompt and a user prompt go in, raw text comes out — because that's exactly
what every pipeline stage's prompt module already produces, and it's what a
real model call looks like. Two implementations exist:

- `AnthropicLLMClient`: calls the real Anthropic API. Used whenever
  `ANTHROPIC_API_KEY` is configured.
- `SimulatedLLMClient` (app/llm/simulator.py): a deterministic, rule-based
  stand-in with the exact same interface, used when no API key is present.
  It reads the same rendered prompts a real model would and returns the same
  shape of text response, which means `get_llm_client()` is the only place
  that needs to know which one is in play — every pipeline stage is written
  once against `LLMClient` and works unmodified against either.

`generate_structured()` is the shared retry-on-validation-failure logic used
by every stage that needs schema-constrained output: call once, and if the
response doesn't parse/validate against the target Pydantic schema, retry
exactly once with the validation error appended to the prompt. A second
failure raises `LLMOutputInvalidError` with everything needed to record a
failed pipeline_stage_results row.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class LLMClient(ABC):
    model_name: str

    @abstractmethod
    def complete(self, *, system: str, user: str) -> str:
        """Return a raw text completion for a system+user prompt pair."""


@dataclass
class LLMCallResult:
    output: BaseModel
    raw_text: str
    model: str
    latency_ms: int
    attempts: int


class LLMOutputInvalidError(Exception):
    def __init__(self, message: str, *, raw_text: str, model: str, latency_ms: int, attempts: int):
        super().__init__(message)
        self.raw_text = raw_text
        self.model = model
        self.latency_ms = latency_ms
        self.attempts = attempts


def _extract_json_text(raw: str) -> str:
    """Models (real or simulated) sometimes wrap JSON in a markdown fence or
    add a sentence before/after it. Pull out the JSON object itself."""
    fence_match = _JSON_FENCE_RE.search(raw)
    if fence_match:
        return fence_match.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw.strip()


def _parse(raw: str, schema: type[T]) -> T:
    json_text = _extract_json_text(raw)
    data = json.loads(json_text)
    return schema.model_validate(data)


def generate_structured(client: LLMClient, *, system: str, user: str, schema: type[T]) -> LLMCallResult:
    start = time.monotonic()
    raw = client.complete(system=system, user=user)

    try:
        parsed = _parse(raw, schema)
        return LLMCallResult(
            output=parsed,
            raw_text=raw,
            model=client.model_name,
            latency_ms=int((time.monotonic() - start) * 1000),
            attempts=1,
        )
    except (json.JSONDecodeError, ValidationError) as first_error:
        retry_user = (
            f"{user}\n\n"
            f"Your previous response could not be validated against the required schema.\n"
            f"Error: {first_error}\n"
            f"Previous response:\n{raw}\n\n"
            "Return ONLY corrected JSON that matches the schema exactly. No prose, no markdown fence."
        )
        raw2 = client.complete(system=system, user=retry_user)
        try:
            parsed = _parse(raw2, schema)
            return LLMCallResult(
                output=parsed,
                raw_text=raw2,
                model=client.model_name,
                latency_ms=int((time.monotonic() - start) * 1000),
                attempts=2,
            )
        except (json.JSONDecodeError, ValidationError) as second_error:
            raise LLMOutputInvalidError(
                str(second_error),
                raw_text=raw2,
                model=client.model_name,
                latency_ms=int((time.monotonic() - start) * 1000),
                attempts=2,
            ) from second_error


class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model

    def complete(self, *, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


_client_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Real Anthropic client if a key is configured, otherwise the
    deterministic simulator. Cached as a singleton for the process lifetime."""
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton

    settings = get_settings()
    if settings.anthropic_api_key:
        _client_singleton = AnthropicLLMClient(settings.anthropic_api_key, settings.anthropic_model)
    else:
        from app.llm.simulator import SimulatedLLMClient

        _client_singleton = SimulatedLLMClient()
    return _client_singleton
