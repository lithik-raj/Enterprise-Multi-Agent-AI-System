"""
app/dependencies.py

FastAPI dependency injection utilities for:
- Settings
- Database sessions
- Tenant isolation context
- User authentication and Role-Based Access Control (RBAC)
"""

from __future__ import annotations

from typing import Callable, List, Optional
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.auth import AuthUser, UserRole, decode_access_token
from app.core.tenant import get_tenant_header, set_current_tenant_id
from app.database.base import get_db

_bearer_security = HTTPBearer(auto_error=False)


def get_app_settings(settings: Settings = Depends(get_settings)) -> Settings:
    """Inject application settings into route handlers."""
    return settings


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer_security),
    tenant_id: str = Depends(get_tenant_header),
) -> AuthUser:
    """
    Extract current authenticated user.
    If a Bearer token is provided, decodes the JWT and validates tenant consistency.
    If no token is supplied, returns a default tenant-scoped recruiter user for seamless local development.
    """
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        token_tenant = payload.get("tenant_id")
        
        # Verify tenant scope consistency
        if token_tenant and tenant_id and tenant_id != "tenant_default" and token_tenant != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token tenant '{token_tenant}' does not match requested tenant '{tenant_id}'.",
            )
        
        user_role_str = payload.get("role", "recruiter")
        try:
            role = UserRole(user_role_str)
        except ValueError:
            role = UserRole.RECRUITER

        user = AuthUser(
            id=payload.get("sub", "user_1"),
            tenant_id=token_tenant or tenant_id,
            email=payload.get("email", "recruiter@talentgraph.ai"),
            role=role,
            full_name=payload.get("full_name", "Recruiter User"),
        )
        set_current_tenant_id(user.tenant_id)
        return user

    # Default developer user scoped to requested tenant
    dev_user = AuthUser(
        id=f"usr_{tenant_id}_default",
        tenant_id=tenant_id,
        email=f"admin@{tenant_id}.ai",
        role=UserRole.ADMIN,
        full_name="Default Admin User",
    )
    set_current_tenant_id(tenant_id)
    return dev_user


def require_roles(allowed_roles: List[UserRole]) -> Callable[[AuthUser], AuthUser]:
    """
    RBAC dependency factory.
    Verifies that the current user possesses one of the allowed roles.
    """
    def _role_checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role '{user.role.value}' does not have permission. Allowed roles: {[r.value for r in allowed_roles]}.",
            )
        return user

    return _role_checker
