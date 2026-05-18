from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.ai.retrieval_pgvector import PGVectorRetrieval

router = APIRouter(prefix="/documents")


class IndexRequest(BaseModel):
    document_id: str
    text: str
    metadata: dict[str, Any] | None = None


@router.post("/index")
def index_document(payload: IndexRequest, settings=Depends(get_settings)) -> dict:
    try:
        retriever = PGVectorRetrieval(db_url=settings.database_url)
        retriever.index_document(doc_id=payload.document_id, text=payload.text, metadata=payload.metadata)
        return {"status": "ok", "document_id": payload.document_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = 5


@router.post("/search")
def search_documents(payload: SearchRequest, settings=Depends(get_settings)) -> dict:
    try:
        retriever = PGVectorRetrieval(db_url=settings.database_url)
        results = retriever.search(payload.query, top_k=payload.top_k or 5)
        return {"results": [dict(id=r.id, score=r.score, text=r.text, metadata=r.metadata) for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
