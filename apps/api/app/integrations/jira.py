from __future__ import annotations

from typing import Any

from app.integrations.base import BaseConnector, ConnectorDispatch


class JiraConnector(BaseConnector):
    name = "jira"

    def authenticate(self) -> bool:
        return True

    def validate(self, payload: dict[str, Any]) -> bool:
        return "project_key" in payload and "summary" in payload

    def execute(self, payload: dict[str, Any], idempotency_key: str) -> ConnectorDispatch:
        return ConnectorDispatch(
            connector=self.name,
            status="queued",
            payload=payload,
            idempotency_key=idempotency_key,
        )

