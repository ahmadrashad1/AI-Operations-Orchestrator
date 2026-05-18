from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecutionRecord(BaseModel):
    event: str
    metadata: dict[str, Any] = Field(default_factory=dict)
