from fastapi import APIRouter, Depends

from app.api.dependencies import get_workflow_service, require_permission_dep
from app.core.security import Principal
from app.domain.schemas import WorkflowCreateRequest, WorkflowEnvelope
from app.services.workflows import WorkflowService

router = APIRouter(prefix="/workflow")


@router.post("/create", response_model=WorkflowEnvelope)
def create_workflow(
    payload: WorkflowCreateRequest,
    principal: Principal = Depends(require_permission_dep("workflow:create")),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowEnvelope:
    workflow = workflow_service.create_workflow(payload=payload, principal=principal)
    return WorkflowEnvelope(workflow=workflow)


@router.get("/{workflow_id}", response_model=WorkflowEnvelope)
def get_workflow(
    workflow_id: str,
    principal: Principal = Depends(require_permission_dep("workflow:view")),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowEnvelope:
    workflow = workflow_service.get_workflow(workflow_id=workflow_id, principal=principal)
    return WorkflowEnvelope(workflow=workflow)
