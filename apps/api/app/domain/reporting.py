from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TenantReportingSummary(BaseModel):
    tenant_id: str
    workflow_count: int
    workflows_by_status: dict[str, int] = Field(default_factory=dict)
    pending_approvals: int
    audit_event_count: int
    recent_workflow_ids: list[str] = Field(default_factory=list)
    recent_actions: list[str] = Field(default_factory=list)
    generated_at: datetime