FROM postgres:16

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git ca-certificates postgresql-server-dev-16 \
    && rm -rf /var/lib/apt/lists/*

# Build and install pgvector from source
RUN git clone --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector
