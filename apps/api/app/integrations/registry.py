from __future__ import annotations

from typing import Dict

from app.integrations.base import BaseConnector
from app.integrations.slack import SlackApprovalConnector
from app.integrations.gmail import GmailConnector
from app.integrations.jira import JiraConnector


class ConnectorRegistry:
    """Registry that stores instantiated connectors and allows typed registration.

    It also exposes a factory for known connector types.
    """

    _factory = {
        "slack": SlackApprovalConnector,
        "gmail": GmailConnector,
        "jira": JiraConnector,
    }

    def __init__(self, connectors: list[BaseConnector] | None = None) -> None:
        self._connectors: Dict[str, BaseConnector] = {}
        if connectors:
            for connector in connectors:
                self._connectors[connector.name] = connector

    @property
    def connectors(self) -> list[BaseConnector]:
        return list(self._connectors.values())

    def get(self, name: str) -> BaseConnector | None:
        return self._connectors.get(name)

    def register(self, connector_type: str, config: dict) -> BaseConnector:
        cls = self._factory.get(connector_type)
        if not cls:
            raise ValueError(f"Unknown connector type: {connector_type}")
        # instantiate with config kwargs (best effort)
        connector = cls(**config) if config else cls()
        # ensure connector is valid
        if not connector.authenticate():
            raise ValueError("Failed to authenticate connector with provided configuration")
        self._connectors[connector.name] = connector
        return connector
