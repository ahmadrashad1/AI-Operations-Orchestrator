from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueueMessage(BaseModel):
    queue_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class QueueRouter:
    def publish(self, message: QueueMessage) -> QueueMessage:
        return message

