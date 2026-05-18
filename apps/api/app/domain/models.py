from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class WorkflowStatus(StrEnum):
    pending = "pending"
    waiting_approval = "waiting_approval"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"


class ApprovalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ExtractedRequest(BaseModel):
    category: str
    item_name: str
    quantity: int
    urgency: str = "normal"
    estimated_unit_cost: float
    estimated_cost: float
    department: str = "operations"


class PolicyEvaluation(BaseModel):
    needs_manager_approval: bool
    needs_finance_approval: bool
    requires_human_review: bool = False
    reasons: list[str] = Field(default_factory=list)


class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    role: str
    status: ApprovalStatus = ApprovalStatus.pending
    responded_by: str | None = None
    responded_at: datetime | None = None
    comment: str | None = None


class AuditLogRecord(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    workflow_id: str
    actor: str
    action: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utcnow)


class WorkflowState(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    submitted_by: str
    workflow_type: str = "procurement"
    status: WorkflowStatus = WorkflowStatus.pending
    current_state: str = "created"
    request_text: str
    request_data: dict[str, Any] = Field(default_factory=dict)
    extraction: ExtractedRequest | None = None
    policy_results: PolicyEvaluation | None = None
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    execution_log: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
