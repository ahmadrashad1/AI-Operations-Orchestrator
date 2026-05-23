from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from app.observability.telemetry import MetricsCollector
try:
    from opentelemetry import trace  # type: ignore
    from opentelemetry.sdk.resources import Resource  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter  # type: ignore
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore
    _OTEL_AVAILABLE = True
except Exception:
    trace = None  # type: ignore
    Resource = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    JaegerExporter = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    _OTEL_AVAILABLE = False

from app.api.v1.router import api_router
from app.bootstrap import get_container, init_container
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run DB migrations and wire services before accepting traffic (production Postgres)."""
    container = init_container()
    _app.state.metrics_collector = container.metrics_collector
    # Start prometheus HTTP server if enabled
    try:
        settings = get_settings()
        if settings.enable_prometheus_server and container.metrics_collector is not None:
            try:
                container.metrics_collector.start_http_server(port=settings.metrics_port)
            except Exception:
                pass
    except Exception:
        pass

    # Initialize basic OpenTelemetry tracing (Jaeger + OTLP) if enabled
    try:
        settings = get_settings()
        if settings.enable_tracing and _OTEL_AVAILABLE:
            resource = Resource.create(attributes={"service.name": settings.app_name})
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
            if settings.jaeger_agent_url:
                try:
                    jaeger_exporter = JaegerExporter(agent_address=settings.jaeger_agent_url)
                    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
                except Exception:
                    pass
            if settings.otlp_endpoint:
                try:
                    otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
                    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                except Exception:
                    pass
    except Exception:
        pass

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-native operational orchestration system",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def collect_request_metrics(request: Request, call_next):
    start = perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid4())
    response = None
    try:
        # If tracing is enabled, create a span around the request
        tracer = trace.get_tracer(__name__) if _OTEL_AVAILABLE and trace is not None else None
        if settings.enable_tracing and _OTEL_AVAILABLE and tracer is not None:
            with tracer.start_as_current_span(f"HTTP {request.method} {request.url.path}") as span:
                span.set_attribute("http.method", request.method)
                span.set_attribute("http.path", request.url.path)
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code if response is not None else 500)
        else:
            response = await call_next(request)
        return response
    finally:
        duration_ms = (perf_counter() - start) * 1000.0
        metrics_collector = getattr(app.state, "metrics_collector", None) or get_container().metrics_collector
        if metrics_collector is not None:
            metrics_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code if response is not None else 500,
                duration_ms=duration_ms,
                request_id=request_id,
            )
        if response is not None:
            response.headers.setdefault("x-request-id", request_id)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "booting",
        "docs": "/docs",
    }
