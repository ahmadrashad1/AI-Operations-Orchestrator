from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.dependencies import get_document_service
from app.services.documents import DocumentIngestionService

router = APIRouter(prefix="/documents")


class IndexRequest(BaseModel):
    document_id: str
    text: str
    metadata: dict[str, Any] | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = 5


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_id: str = Form(...),
    tenant_id: str = Form(...),
    metadata_json: str | None = Form(default=None),
    source: str | None = Form(default=None),
    document_service: DocumentIngestionService = Depends(get_document_service),
) -> dict[str, Any]:
    try:
        metadata = DocumentIngestionService.parse_metadata_json(metadata_json)
        payload = await file.read()
        result = document_service.enqueue_upload(
            document_id=document_id,
            tenant_id=tenant_id,
            filename=file.filename or document_id,
            content_type=file.content_type,
            data=payload,
            metadata=metadata,
            source=source,
        )
        return result.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/index")
def index_document(
    payload: IndexRequest,
    document_service: DocumentIngestionService = Depends(get_document_service),
) -> dict[str, Any]:
    try:
        result = document_service.retriever.index_document(
            doc_id=payload.document_id,
            content=payload.text,
            metadata=payload.metadata,
        )
        return {"status": "ok", "document_id": payload.document_id, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/search")
def search_documents(
    payload: SearchRequest,
    document_service: DocumentIngestionService = Depends(get_document_service),
) -> dict[str, Any]:
    try:
        results = document_service.retriever.search(payload.query, top_k=payload.top_k or 5)
        return {"results": [dict(id=r.id, score=r.score, text=r.text, metadata=r.metadata) for r in results]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
