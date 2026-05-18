from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ConnectorDispatch(BaseModel):
    connector: str
    status: str
    payload: dict[str, Any]
    idempotency_key: str


class BaseConnector(ABC):
    name: str

    @abstractmethod
    def authenticate(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def validate(self, payload: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def execute(self, payload: dict[str, Any], idempotency_key: str) -> ConnectorDispatch:
        raise NotImplementedError

