from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class MetricsCollector:
    def emit(self, event: TelemetryEvent) -> TelemetryEvent:
        return event
