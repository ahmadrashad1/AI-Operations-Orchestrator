FROM python:3.12-slim AS base

WORKDIR /service
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=5

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY alembic.ini ./
# Must not be named `alembic/` — that shadows the installed `alembic` package on sys.path.
COPY alembic ./migrations
COPY app ./app
COPY scripts ./scripts

RUN sed -i 's/^script_location = alembic/script_location = migrations/' alembic.ini

FROM base AS prod

RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test

# Install development build tools and development dependencies (tests, linters, testcontainers, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install --no-cache-dir '.[dev]'

# Copy tests into the image so pytest can run without bind-mounting source.
COPY tests ./tests

# Ensure tests run in development mode by default inside the test image.
ENV APP_ENVIRONMENT=development
ENV APP_DATABASE_URL=postgresql+psycopg://orchestrator:orchestrator@postgres:5432/orchestrator
ENV APP_REDIS_URL=redis://redis:6379/0
ENV APP_JWT_SECRET_KEY=dev-secret-change-in-production-use-long-random-string

# Default test command when running this image directly.
CMD ["pytest", "-q", "tests"]

