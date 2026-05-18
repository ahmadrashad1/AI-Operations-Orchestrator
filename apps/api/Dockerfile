FROM python:3.12-slim

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

RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

