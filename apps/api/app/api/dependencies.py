from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.bootstrap import get_container
from app.core.security import Principal, get_current_principal
from app.db.repositories import BaseUserRepository
from app.integrations.registry import ConnectorRegistry
from app.observability.telemetry import MetricsCollector
from app.services.documents import DocumentIngestionService
from app.services.reporting import ReportingService
from app.services.tenants import TenantService
from app.services.users import UserService
from app.core.rbac import require_permission


def get_workflow_service():
    return get_container().workflow_service


def get_approval_service():
    return get_container().approval_service


def get_audit_service():
    return get_container().audit_service


def get_reporting_service() -> ReportingService:
    return get_container().reporting_service


def get_metrics_collector() -> MetricsCollector:
    return get_container().metrics_collector


def get_document_service() -> DocumentIngestionService:
    service = getattr(get_container(), "document_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document ingestion store is unavailable (PostgreSQL required).",
        )
    return service


def get_user_repository() -> BaseUserRepository:
    repo = get_container().user_repository
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication store is unavailable (PostgreSQL required).",
        )
    return repo


def get_token_blacklist_repository():
    repo = getattr(get_container(), "token_blacklist_repository", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token blacklist store is unavailable.",
        )
    return repo


def get_user_service() -> UserService:
    svc = getattr(get_container(), "user_service", None)
    if svc is None:
        # try to build from repository
        repo = get_user_repository()
        svc = UserService(repo)
        # cache for future calls
        setattr(get_container(), "user_service", svc)
    return svc


def get_connector_registry() -> ConnectorRegistry:
    reg = getattr(get_container(), "connector_registry", None)
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connector registry is unavailable.",
        )
    return reg


def get_tenant_service() -> TenantService:
    svc = getattr(get_container(), "tenant_service", None)
    if svc is None:
        repo = getattr(get_container(), "tenant_repository", None)
        if repo is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tenant store is unavailable.",
            )
        svc = TenantService(repo)
        setattr(get_container(), "tenant_service", svc)
    return svc


def get_permission_repository():
    repo = getattr(get_container(), "permission_repository", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Permission store is unavailable.",
        )
    return repo


def require_roles(*allowed_roles: str) -> Callable[[Principal], Principal]:
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_any_role(*allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The authenticated principal does not have access to this resource.",
            )
        return principal

    return dependency


# Re-export require_permission for route modules to import from dependencies
def require_permission_dep(permission: str) -> Callable[[Principal], Principal]:
    return require_permission(permission)
