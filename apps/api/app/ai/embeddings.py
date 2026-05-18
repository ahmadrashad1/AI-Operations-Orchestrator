"""Embedding utilities with OpenAI fallback.

Provides `get_embedding(text)` which returns a list[float].
If OpenAI is configured (OPENAI_API_KEY), it uses OpenAI embeddings; otherwise
it returns a deterministic pseudo-embedding derived from a SHA256 digest.
"""
from __future__ import annotations

import hashlib
import os
from typing import List

try:
    import openai
except Exception:  # pragma: no cover
    openai = None


def _pseudo_embedding(text: str, dim: int = 1536) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals: List[float] = []
    for i in range(dim):
        vals.append(float(digest[i % len(digest)]) / 255.0)
    return vals


def get_embedding(text: str, model: str | None = None) -> List[float]:
    model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    api_key = os.getenv("OPENAI_API_KEY")
    if openai and api_key:
        try:
            openai.api_key = api_key
            resp = openai.Embedding.create(input=text, model=model)
            emb = resp["data"][0]["embedding"]
            return [float(x) for x in emb]
        except Exception:
            pass
    # Fallback
    return _pseudo_embedding(text)
