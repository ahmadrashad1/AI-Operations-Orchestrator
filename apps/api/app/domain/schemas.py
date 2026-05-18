from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.models import WorkflowState


class WorkflowCreateRequest(BaseModel):
    tenant_id: str | None = None
    workflow_type: str = "procurement"
    request_text: str
    request_data: dict[str, Any] = Field(default_factory=dict)


class WorkflowEnvelope(BaseModel):
    workflow: WorkflowState


class ApprovalDecisionRequest(BaseModel):
    workflow_id: str
    approval_id: str
    decision: Literal["approved", "rejected"]
    comment: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class InternalAgentExecuteRequest(BaseModel):
    workflow_id: str
    agent_name: str


class EventPublishRequest(BaseModel):
    workflow_id: str
    action: str
    metadata: dict[str, Any] = Field(default_factory=dict)

