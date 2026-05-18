from __future__ import annotations

from app.integrations.base import BaseConnector


class ConnectorRegistry:
    def __init__(self, connectors: list[BaseConnector]) -> None:
        self._connectors = {connector.name: connector for connector in connectors}

    def get(self, name: str) -> BaseConnector | None:
        return self._connectors.get(name)

