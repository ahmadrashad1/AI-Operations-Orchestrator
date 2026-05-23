from __future__ import annotations

from collections import Counter as _Counter, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any
import threading
import time
try:
    from prometheus_client import (
        Counter as PromCounter,
        Gauge as PromGauge,
        start_http_server,
        CollectorRegistry,
        generate_latest,
    )
    _PROM_AVAILABLE = True
except Exception:
    PromCounter = None  # type: ignore
    PromGauge = None  # type: ignore
    start_http_server = None  # type: ignore
    CollectorRegistry = None  # type: ignore
    generate_latest = None  # type: ignore
    _PROM_AVAILABLE = False

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
        self._method_counts: _Counter[str] = _Counter()
        self._status_counts: _Counter[str] = _Counter()
        self._path_counts: _Counter[str] = _Counter()
        self._durations_ms: list[float] = []
        # Prometheus metrics
        if _PROM_AVAILABLE:
            self._registry = CollectorRegistry()
            self._prom_total = PromCounter(
                "aiops_total_requests",
                "Total number of requests recorded",
                registry=self._registry,
            )
            self._prom_by_method = PromCounter(
                "aiops_requests_by_method",
                "Requests partitioned by HTTP method",
                ["method"],
                registry=self._registry,
            )
            self._prom_by_status = PromCounter(
                "aiops_requests_by_status",
                "Requests partitioned by HTTP status code",
                ["status"],
                registry=self._registry,
            )
            self._prom_by_path = PromCounter(
                "aiops_requests_by_path",
                "Requests partitioned by request path",
                ["path"],
                registry=self._registry,
            )
            self._prom_avg_duration = PromGauge(
                "aiops_average_request_duration_ms",
                "Average request duration in ms",
                registry=self._registry,
            )
        else:
            self._registry = None
            self._prom_total = None
            self._prom_by_method = None
            self._prom_by_status = None
            self._prom_by_path = None
            self._prom_avg_duration = None

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
            # update prometheus metrics if available
            if _PROM_AVAILABLE and getattr(self, "_prom_total", None) is not None:
                try:
                    self._prom_total.inc()
                    self._prom_by_method.labels(method=method).inc()
                    self._prom_by_status.labels(status=str(status_code)).inc()
                    # path may be high-cardinality; keep label but it's up to deployer
                    self._prom_by_path.labels(path=path).inc()
                    # recompute avg quickly
                    avg = sum(self._durations_ms) / len(self._durations_ms)
                    self._prom_avg_duration.set(avg)
                except Exception:
                    # ensure metrics collection doesn't break the app
                    pass

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

    def prometheus_metrics(self) -> bytes:
        """Return the Prometheus exposition for the in-process registry."""
        if not _PROM_AVAILABLE or self._registry is None or generate_latest is None:
            return b""
        try:
            return generate_latest(self._registry)
        except Exception:
            return b""

    def start_http_server(self, port: int = 9187) -> None:
        # Start prometheus_client HTTP server in a background thread bound to our registry
        # prometheus_client.start_http_server doesn't accept a registry argument until v0.14,
        # so we use a small local HTTP server when needed. For compatibility, attempt start_http_server first.
        # If prometheus_client is available and start_http_server is callable, use it.
        if _PROM_AVAILABLE and start_http_server is not None:
            try:
                start_http_server(port)
                return
            except TypeError:
                # fall through to custom HTTP server
                pass
            # fallback: serve generate_latest on a tiny thread
            def _serve() -> None:
                from http.server import HTTPServer, BaseHTTPRequestHandler

                class _Handler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        if self.path == "/metrics":
                            data = generate_latest(self._registry)
                            self.send_response(200)
                            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                            self.send_header("Content-Length", str(len(data)))
                            self.end_headers()
                            self.wfile.write(data)
                        else:
                            self.send_response(404)
                            self.end_headers()

                httpd = HTTPServer(("", port), _Handler)
                httpd.serve_forever()

            t = threading.Thread(target=_serve, daemon=True)
            t.start()
