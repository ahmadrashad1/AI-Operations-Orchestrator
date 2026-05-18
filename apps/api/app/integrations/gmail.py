from __future__ import annotations

from typing import Any

from app.integrations.base import BaseConnector, ConnectorDispatch


class GmailConnector(BaseConnector):
    name = "gmail"

    def authenticate(self) -> bool:
        return True

    def validate(self, payload: dict[str, Any]) -> bool:
        return "subject" in payload and "recipient" in payload

    def execute(self, payload: dict[str, Any], idempotency_key: str) -> ConnectorDispatch:
        return ConnectorDispatch(
            connector=self.name,
            status="queued",
            payload=payload,
            idempotency_key=idempotency_key,
        )

