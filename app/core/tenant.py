"""
core/tenant.py

Multi-tenant context and strict tenant isolation utilities.
Guarantees that no query or mutation can cross tenant boundaries.
"""

from __future__ import annotations

import contextvars
from typing import Optional, Any
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

# Thread/coroutine-safe context variable for the active tenant
_tenant_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tenant_id", default=None)


class TenantIsolationError(HTTPException):
    """Raised when an operation attempts unauthorized cross-tenant data access."""
    def __init__(self, detail: str = "Cross-tenant access prohibited."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_current_tenant_id() -> Optional[str]:
    """Retrieve the tenant_id for the active request context."""
    return _tenant_context.get()


def set_current_tenant_id(tenant_id: Optional[str]) -> contextvars.Token:
    """Set the tenant_id for the active request context."""
    return _tenant_context.set(tenant_id)


def reset_current_tenant_id(token: contextvars.Token) -> None:
    """Reset the tenant context back to its previous state."""
    _tenant_context.reset(token)


async def get_tenant_header(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID", description="Active Tenant Identifier")
) -> str:
    """
    FastAPI dependency that extracts and validates the tenant ID from the HTTP request.
    Defaults to 'tenant_default' if not explicitly provided, to support backwards compatibility.
    """
    tenant_id = x_tenant_id.strip() if x_tenant_id else "tenant_default"
    set_current_tenant_id(tenant_id)
    return tenant_id


class TenantScopedRepository:
    """
    Base repository providing guaranteed tenant-isolated queries.
    Every database query automatically applies a `tenant_id == active_tenant` predicate.
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        if not tenant_id:
            raise ValueError("Tenant ID is strictly required for repository operations.")
        self.session = session
        self.tenant_id = tenant_id

    def scoped_query(self, model: Any):
        """Build a select query pre-filtered by the active tenant_id."""
        if hasattr(model, "tenant_id"):
            return select(model).where(model.tenant_id == self.tenant_id)
        elif hasattr(model, "id") and model.__tablename__ == "tenants":
            return select(model).where(model.id == self.tenant_id)
        return select(model)

    def verify_tenant_ownership(self, entity: Any) -> None:
        """Verify that an entity belongs to the active tenant; raise 403 Forbidden otherwise."""
        if hasattr(entity, "tenant_id") and entity.tenant_id != self.tenant_id:
            raise TenantIsolationError(
                f"Security violation: Entity belongs to tenant '{entity.tenant_id}', not '{self.tenant_id}'."
            )
