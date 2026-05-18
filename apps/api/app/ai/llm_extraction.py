"""LLM-backed extraction with Redis caching and deterministic fallback.

Behavior:
- If `OPENAI_API_KEY` is set and `openai` is importable, perform a structured
  extraction call to the LLM and validate against the domain schema.
- If LLM is unavailable or fails, fall back to `RequestExtractionAgent`.
- Cache successful extraction results in Redis keyed by sha256(request_text).
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    openai = None

import redis
from pydantic import ValidationError

from app.ai.extraction import RequestExtractionAgent
from app.domain.models import ExtractedRequest
from app.core.config import get_settings


class LLMExtractionAgent:
    def __init__(self, settings=None, redis_url: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.redis_url = redis_url or self.settings.redis_url
        self.cache = None
        try:
            self.cache = redis.from_url(self.redis_url, decode_responses=True)
        except Exception:
            self.cache = None
        self.heuristic = RequestExtractionAgent()
        self.openai_key = os.getenv("OPENAI_API_KEY")

        if openai and self.openai_key:
            openai.api_key = self.openai_key

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"extraction_cache:{digest}"

    def _call_llm(self, request_text: str) -> dict[str, Any]:
        """Call the OpenAI completion endpoint with a structured prompt.

        Note: This is intentionally conservative and expects JSON output.
        """
        if not openai or not self.openai_key:
            raise RuntimeError("OpenAI not configured")

        prompt = (
            "Extract procurement request details as JSON with keys:"
            " category, item_name, quantity, urgency, estimated_unit_cost, estimated_cost, department.\n"
            f"Request: {request_text}\n\nRespond with only valid JSON."
        )

        resp = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512,
        )

        # Accept content from assistant
        content = resp["choices"][0]["message"]["content"]
        return json.loads(content)

    def extract(self, request_text: str) -> ExtractedRequest:
        # Try cache first
        key = self._cache_key(request_text)
        if self.cache:
            try:
                cached = self.cache.get(key)
                if cached:
                    data = json.loads(cached)
                    return ExtractedRequest(**data)
            except Exception:
                pass

        # Try LLM
        if openai and self.openai_key:
            try:
                extracted = self._call_llm(request_text)
                # Validate and construct model
                model = ExtractedRequest(**extracted)
                # Cache
                if self.cache:
                    try:
                        self.cache.set(key, json.dumps(model.model_dump()), ex=60 * 60 * 24)  # 24h
                    except Exception:
                        pass
                return model
            except (ValidationError, RuntimeError, json.JSONDecodeError, Exception):
                # Fall back to heuristics
                pass

        # Fallback deterministic extraction
        return self.heuristic.extract(request_text)
