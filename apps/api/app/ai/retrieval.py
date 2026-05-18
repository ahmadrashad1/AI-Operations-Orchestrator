from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PolicyDocument(BaseModel):
    document_id: str
    title: str
    source: str
    snippets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRetriever:
    def search(self, query: str, tenant_id: str) -> list[PolicyDocument]:
        return [
            PolicyDocument(
                document_id="policy-demo-001",
                title="Default Procurement Policy",
                source="bootstrap",
                snippets=[
                    f"Retrieval for tenant '{tenant_id}' is not wired yet.",
                    f"Search query received: '{query}'.",
                ],
            )
        ]
