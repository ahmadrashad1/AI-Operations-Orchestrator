"""PGVector-backed retrieval implementation.

The database schema is owned by Alembic migrations. This runtime layer only
handles embedding generation, inserts, and nearest-neighbor search.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import create_engine, text as sa_text

from app.ai.embeddings import get_embedding


class RetrievalResult:
    def __init__(
        self,
        id: str,
        score: float,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
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

    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        embedding = self._embedding_literal(get_embedding(content))
        with self.engine.begin() as conn:
            conn.execute(
                sa_text(
                    """
                    INSERT INTO documents (id, text, metadata, embedding)
                    VALUES (:id, :text, :metadata, CAST(:embedding AS vector))
                    ON CONFLICT (id)
                    DO UPDATE SET
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """
                ),
                {"id": doc_id, "text": content, "metadata": metadata or {}, "embedding": embedding},
            )

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        embedding = self._embedding_literal(get_embedding(query))
        with self.engine.begin() as conn:
            stmt = sa_text(
                """
                SELECT
                    id,
                    text,
                    metadata,
                    (embedding <-> CAST(:embedding AS vector)) AS distance
                FROM documents
                ORDER BY embedding <-> CAST(:embedding AS vector)
                LIMIT :limit
                """
            )
            rows = conn.execute(stmt, {"embedding": embedding, "limit": top_k}).fetchall()
            results: list[RetrievalResult] = []
            for r in rows:
                metadata = r[2]
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                results.append(
                    RetrievalResult(
                        id=r[0],
                        score=float(r[3]),
                        text=r[1],
                        metadata=metadata,
                    )
                )
            return results

    @staticmethod
    def _embedding_literal(values: list[float]) -> str:
        return "[" + ",".join(str(value) for value in values) + "]"
