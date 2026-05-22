from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from app.ai.ingest import chunk_text, extract_text_from_bytes
from app.ai.retrieval_pgvector import PGVectorRetrieval
from app.services.queue import Job, RedisJobQueue


@dataclass(slots=True)
class DocumentIngestionResult:
    document_id: str
    chunk_count: int
    chunk_ids: list[str]
    mode: str
    job_id: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "chunk_count": self.chunk_count,
            "chunk_ids": self.chunk_ids,
            "mode": self.mode,
            "job_id": self.job_id,
        }


class DocumentIngestionService:
    def __init__(
        self,
        retriever: PGVectorRetrieval,
        queue: RedisJobQueue | None = None,
    ) -> None:
        self.retriever = retriever
        self.queue = queue

    def enqueue_upload(
        self,
        *,
        document_id: str,
        tenant_id: str,
        filename: str,
        content_type: str | None,
        data: bytes,
        metadata: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> DocumentIngestionResult:
        payload = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "filename": filename,
            "content_type": content_type,
            "metadata": metadata or {},
            "source": source or filename,
            "data_b64": base64.b64encode(data).decode("ascii"),
        }

        if self.queue is None:
            result = self.ingest_payload(payload)
            return DocumentIngestionResult(
                document_id=document_id,
                chunk_count=result["chunk_count"],
                chunk_ids=result["chunk_ids"],
                mode="synchronous",
            )

        job = self.queue.enqueue(job_type="document_ingest", payload=payload)
        return DocumentIngestionResult(
            document_id=document_id,
            chunk_count=0,
            chunk_ids=[],
            mode="queued",
            job_id=job.job_id,
        )

    def ingest_job(self, job: Job) -> DocumentIngestionResult:
        if job.job_type != "document_ingest":
            raise ValueError(f"Unsupported job_type {job.job_type!r}")

        result = self.ingest_payload(job.payload)
        return DocumentIngestionResult(
            document_id=result["document_id"],
            chunk_count=result["chunk_count"],
            chunk_ids=result["chunk_ids"],
            mode="processed",
            job_id=job.job_id,
        )

    def ingest_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        data_b64 = payload.get("data_b64")
        if not isinstance(data_b64, str):
            raise ValueError("data_b64 must be a base64-encoded string")

        filename = str(payload.get("filename") or payload.get("document_id") or "document.txt")
        content_type = payload.get("content_type")
        metadata = payload.get("metadata") or {}
        source = payload.get("source") or filename
        document_id = str(payload["document_id"])
        tenant_id = str(payload.get("tenant_id") or "")

        text = extract_text_from_bytes(filename=filename, data=base64.b64decode(data_b64), content_type=content_type)
        if not text.strip():
            raise ValueError("Document did not contain any extractable text")

        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Document chunking produced no chunks")

        chunk_ids: list[str] = []
        for chunk_index, chunk in enumerate(chunks):
            chunk_id = f"{document_id}:chunk:{chunk_index:04d}"
            chunk_metadata = {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "source": source,
                "filename": filename,
                "content_type": content_type,
                "chunk_index": chunk_index,
                "chunk_count": len(chunks),
                "chunk_type": "document_chunk",
                "source_metadata": metadata,
            }
            self.retriever.index_document(doc_id=chunk_id, content=chunk, metadata=chunk_metadata)
            chunk_ids.append(chunk_id)

        return {
            "document_id": document_id,
            "chunk_count": len(chunk_ids),
            "chunk_ids": chunk_ids,
        }

    @staticmethod
    def parse_metadata_json(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("metadata must decode to an object")
        return parsed
