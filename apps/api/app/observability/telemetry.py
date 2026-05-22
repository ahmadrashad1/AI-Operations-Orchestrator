from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    name: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class RequestMetric(BaseModel):
    method: str
    path: str
    status_code: int
    duration_ms: float
    request_id: str | None = None


class TelemetrySnapshot(BaseModel):
    total_requests: int
    requests_by_method: dict[str, int]
    requests_by_status: dict[str, int]
    requests_by_path: dict[str, int]
    average_duration_ms: float
    recent_requests: list[RequestMetric]


@dataclass(slots=True)
class _RequestStat:
    method: str
    path: str
    status_code: int
    duration_ms: float
    request_id: str | None = None


class MetricsCollector:
    def __init__(self, recent_limit: int = 100) -> None:
        self._lock = Lock()
        self._recent_requests: deque[_RequestStat] = deque(maxlen=recent_limit)
        self._method_counts: Counter[str] = Counter()
        self._status_counts: Counter[str] = Counter()
        self._path_counts: Counter[str] = Counter()
        self._durations_ms: list[float] = []

    def emit(self, event: TelemetryEvent) -> TelemetryEvent:
        return event

    def record_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str | None = None,
    ) -> None:
        with self._lock:
            self._recent_requests.append(
                _RequestStat(
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    request_id=request_id,
                )
            )
            self._method_counts[method] += 1
            self._status_counts[str(status_code)] += 1
            self._path_counts[path] += 1
            self._durations_ms.append(duration_ms)

    def snapshot(self) -> TelemetrySnapshot:
        with self._lock:
            average_duration_ms = (
                sum(self._durations_ms) / len(self._durations_ms) if self._durations_ms else 0.0
            )
            recent_requests = [
                RequestMetric(
                    method=request.method,
                    path=request.path,
                    status_code=request.status_code,
                    duration_ms=request.duration_ms,
                    request_id=request.request_id,
                )
                for request in self._recent_requests
            ]
            return TelemetrySnapshot(
                total_requests=len(self._durations_ms),
                requests_by_method=dict(self._method_counts),
                requests_by_status=dict(self._status_counts),
                requests_by_path=dict(self._path_counts),
                average_duration_ms=average_duration_ms,
                recent_requests=recent_requests,
            )

    def clear(self) -> None:
        with self._lock:
            self._recent_requests.clear()
            self._method_counts.clear()
            self._status_counts.clear()
            self._path_counts.clear()
            self._durations_ms.clear()
