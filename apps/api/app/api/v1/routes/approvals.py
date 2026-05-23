from fastapi import APIRouter, Depends

from app.api.dependencies import get_approval_service, require_permission_dep
from app.core.security import Principal
from app.domain.schemas import ApprovalDecisionRequest, WorkflowEnvelope
from app.services.approvals import ApprovalService

router = APIRouter(prefix="/approval")


@router.post("/respond", response_model=WorkflowEnvelope)
def respond_to_approval(
    payload: ApprovalDecisionRequest,
    principal: Principal = Depends(require_permission_dep("workflow:approve")),
    approval_service: ApprovalService = Depends(get_approval_service),
) -> WorkflowEnvelope:
    workflow = approval_service.respond(payload=payload, principal=principal)
    return WorkflowEnvelope(workflow=workflow)
