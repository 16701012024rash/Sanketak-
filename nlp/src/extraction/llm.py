"""
A thin seam over whichever LLM is serving us.

The point of this file is that nothing above it knows or cares which provider
is in use. Development runs against a hosted free tier for speed; a deployment
at OIL would run an open-weight model on their own hardware. Swapping between
them is one argument, not a rewrite — which is what makes the "runs on your own
servers" claim honest rather than aspirational.

Every backend takes a prompt and returns a JSON object. That is the whole
contract.
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


class LLMError(Exception):
    """The provider failed, or returned something we could not parse."""


def _extract_json(text: str) -> Dict[str, Any]:
    """Pull a JSON object out of a model response.

    Models wrap JSON in prose or ```json fences no matter how firmly you ask
    them not to, so we strip rather than trust.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost braces.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            raise LLMError(f"Response was not valid JSON: {e}\n{text[:500]}") from e
    raise LLMError(f"No JSON object in response:\n{text[:500]}")


class LLMBackend(ABC):
    name: str

    @abstractmethod
    def complete_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        ...

    def complete_json_retrying(self, prompt: str, system: Optional[str] = None,
                               attempts: int = 3) -> Dict[str, Any]:
        """Retry transient provider failures with exponential backoff.

        Rate limits are the deliberate exception: a 429 is raised immediately
        rather than retried, because a quota that has run out will not refill
        within the backoff window and retrying only spends more of it. The
        caller sees the failure while it still has budget to react.
        """
        last: Optional[Exception] = None
        for i in range(attempts):
            try:
                return self.complete_json(prompt, system)
            except Exception as e:  # provider SDKs raise their own types
                last = e
                # A rate limit will not clear in two seconds. Retrying just
                # spends more of the quota that ran out.
                if "429" in str(e) or "rate limit" in str(e).lower():
                    raise LLMError(f"{self.name} rate limited: {e}") from e
                if i < attempts - 1:
                    time.sleep(2 ** i)
        raise LLMError(f"{self.name} failed after {attempts} attempts: {last}")


class GeminiBackend(LLMBackend):
    name = "gemini"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        import google.generativeai as genai
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is not set. Put it in nlp/.env")
        genai.configure(api_key=key)
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._genai = genai

    def complete_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        model = self._genai.GenerativeModel(
            self.model_name,
            system_instruction=system,
            generation_config={"response_mime_type": "application/json",
                               "temperature": 0.0},
        )
        return _extract_json(model.generate_content(prompt).text)


class GroqBackend(LLMBackend):
    name = "groq"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        from groq import Groq
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise LLMError("GROQ_API_KEY is not set. Put it in nlp/.env")
        self.client = Groq(api_key=key)
        self.model_name = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def complete_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return _extract_json(resp.choices[0].message.content)


# Confirmed against this account's /v1/models listing rather than guessed — a
# wrong id does not fail at import, it fails on the first extraction with a
# 404.
#
# Budget tier on purpose. This is schema-constrained extraction: the model
# picks ids from a taxonomy we hand it and copies evidence spans verbatim. It
# is a reading and formatting job, not a reasoning one, and the flagship tiers
# are spend without a matching gain — `_coerce` already discards anything
# outside the taxonomy, so the expensive failure mode is not "wrong id" but
# "plausible id the narrative does not support", which a larger model is not
# obviously better at.
#
# Not gpt-5-mini: it rejects temperature=0.0 outright ("Unsupported value:
# 'temperature' does not support 0.0 with this model"), and determinism at
# temperature 0 is a property this module relies on.
#
# The floating alias is deliberate — it survives snapshot retirement. Pin
# gpt-5.4-mini-2026-03-17 instead if a run needs to be exactly reproducible.
_OPENAI_DEFAULT_MODEL: Optional[str] = "gpt-5.4-mini"


class OpenAIBackend(LLMBackend):
    name = "openai"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        from openai import OpenAI
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("OPENAI_API_KEY is not set. Put it in nlp/.env")
        self.client = OpenAI(api_key=key)
        self.model_name = model or os.getenv("OPENAI_MODEL") or _OPENAI_DEFAULT_MODEL
        if not self.model_name:
            raise LLMError(
                "No OpenAI model chosen. Set OPENAI_MODEL in nlp/.env, or fill "
                "in _OPENAI_DEFAULT_MODEL in this file with an id confirmed "
                "against the account's model listing."
            )

    def complete_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return _extract_json(resp.choices[0].message.content)


def get_backend(name: Optional[str] = None) -> LLMBackend:
    """Pick a backend. Defaults to LLM_PROVIDER in .env, else OpenAI.

    OpenAI is the paid default. Groq and Gemini remain as free-tier fallbacks —
    useful when the credit runs out mid-run, and the reason the provider is a
    single argument rather than a code change.
    """
    name = (name or os.getenv("LLM_PROVIDER", "openai")).lower()
    if name == "openai":
        return OpenAIBackend()
    if name == "gemini":
        return GeminiBackend()
    if name == "groq":
        return GroqBackend()
    raise LLMError(
        f"Unknown provider {name!r}. Use 'openai', 'gemini' or 'groq'."
    )
