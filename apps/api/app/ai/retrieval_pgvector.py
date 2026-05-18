"""PGVector-backed retrieval implementation (minimal).

This implementation expects Postgres with the `vector` extension installed.
It creates a `documents` table (if missing) and provides `index_document`
and `search` operations using the `<->` operator for nearest neighbor search.

Notes:
- This is a pragmatic convenience implementation; for production use, ensure
  pgvector extension is installed and the vector column is properly indexed.
"""
from __future__ import annotations

import json
from typing import Any, List

from sqlalchemy import text, create_engine

from app.ai.embeddings import get_embedding


class RetrievalResult:
    def __init__(self, id: str, score: float, text: str, metadata: dict[str, Any] | None = None) -> None:
        self.id = id
        self.score = score
        self.text = text
        self.metadata = metadata or {}


class PGVectorRetrieval:
    def __init__(self, db_url: str | None = None) -> None:
        from app.core.config import get_settings

        settings = get_settings()
        self.db_url = db_url or settings.database_url
        self.engine = create_engine(self.db_url)
        # Ensure table exists (idempotent)
        with self.engine.begin() as conn:
            # Create extension if not exists and documents table
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        metadata JSONB,
                        embedding vector(1536)
                    )
                    """
                )
            )
            # Create index for fast similarity search
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding)"))

    def index_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        emb = get_embedding(text)
        emb_list = "{" + ",".join(str(x) for x in emb) + "}"
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO documents (id, text, metadata, embedding)
                    VALUES (:id, :text, :metadata, :embedding)
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """
                ),
                {"id": doc_id, "text": text, "metadata": json.dumps(metadata or {}), "embedding": emb_list},
            )

    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        emb = get_embedding(query)
        emb_list = "{" + ",".join(str(x) for x in emb) + "}"
        with self.engine.begin() as conn:
            stmt = text(
                "SELECT id, text, metadata, embedding, (embedding <-> :q) AS distance FROM documents ORDER BY embedding <-> :q LIMIT :k"
            )
            rows = conn.execute(stmt, {"q": emb_list, "k": top_k}).fetchall()
            results: List[RetrievalResult] = []
            for r in rows:
                meta = r[2]
                score = float(r[4])
                results.append(RetrievalResult(id=r[0], score=score, text=r[1], metadata=meta))
            return results
