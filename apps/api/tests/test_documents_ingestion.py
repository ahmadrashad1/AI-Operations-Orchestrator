from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from app.bootstrap import get_container
from app.main import app
from app.services.documents import DocumentIngestionResult, DocumentIngestionService

client = TestClient(app)


class FakeRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def index_document(self, doc_id: str, content: str, metadata: dict[str, object] | None = None) -> None:
        self.calls.append({"doc_id": doc_id, "content": content, "metadata": metadata or {}})


class FakeDocumentService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def enqueue_upload(
        self,
        *,
        document_id: str,
        tenant_id: str,
        filename: str,
        content_type: str | None,
        data: bytes,
        metadata: dict[str, object] | None = None,
        source: str | None = None,
    ) -> DocumentIngestionResult:
        self.calls.append(
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "filename": filename,
                "content_type": content_type,
                "data": data,
                "metadata": metadata or {},
                "source": source,
            }
        )
        return DocumentIngestionResult(
            document_id=document_id,
            chunk_count=1,
            chunk_ids=[f"{document_id}:chunk:0000"],
            mode="queued",
            job_id="job-1",
        )


def setup_function() -> None:
    get_container().reset_state()


def test_document_upload_endpoint_enqueues_ingestion_job() -> None:
    container = get_container()
    container.document_service = FakeDocumentService()

    response = client.post(
        "/api/v1/documents/upload",
        data={
            "document_id": "doc-1",
            "tenant_id": "tenant-a",
            "metadata_json": '{"source": "email"}',
            "source": "email",
        },
        files={"file": ("notes.txt", b"Need 5 laptops for the engineering team", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == "doc-1"
    assert body["mode"] == "queued"
    assert body["job_id"] == "job-1"


def test_document_ingestion_service_chunks_and_indexes_text() -> None:
    retriever = FakeRetriever()
    service = DocumentIngestionService(retriever=retriever, queue=None)

    payload = {
        "document_id": "doc-2",
        "tenant_id": "tenant-a",
        "filename": "notes.txt",
        "content_type": "text/plain",
        "metadata": {"source": "ticket"},
        "source": "ticket",
        "data_b64": base64.b64encode(
            b"This is a long note. " * 120
        ).decode("ascii"),
    }

    result = service.ingest_payload(payload)

    assert result["document_id"] == "doc-2"
    assert result["chunk_count"] >= 1
    assert retriever.calls
    assert retriever.calls[0]["doc_id"] == "doc-2:chunk:0000"
