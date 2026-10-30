"""
app/api/auth.py

Authentication endpoints for TalentGraph.
Allows users to register, log in to receive signed JWT tokens, and fetch profile details.
"""

from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    AuthUser,
    UserRole,
    create_access_token,
    hash_password,
    verify_password,
)
from app.core.tenant import get_tenant_header
from app.database.base import get_db
from app.database.models import TenantRecord, UserRecord
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    role: UserRole = Field(UserRole.RECRUITER)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    email: str
    role: str
    full_name: Optional[str] = None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    req: RegisterRequest,
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
):
    """Register a new user within the specified tenant context."""
    # Ensure tenant exists
    tenant_res = db.execute(select(TenantRecord).where(TenantRecord.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        tenant = TenantRecord(
            id=tenant_id,
            name=f"Workspace ({tenant_id})",
            plan="enterprise",
        )
        db.add(tenant)
        db.flush()

    # Check for existing email in this tenant
    existing_res = db.execute(
        select(UserRecord).where(UserRecord.tenant_id == tenant_id, UserRecord.email == req.email)
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{req.email}' already exists in tenant '{tenant_id}'.",
        )

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    user = UserRecord(
        id=user_id,
        tenant_id=tenant_id,
        email=req.email,
        role=req.role.value,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    auth_user = AuthUser(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=req.role,
        full_name=user.full_name,
    )
    token = create_access_token(auth_user)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


@router.post("/login", response_model=TokenResponse)
def login_user(
    req: LoginRequest,
    tenant_id: str = Depends(get_tenant_header),
    db: Session = Depends(get_db),
):
    """Authenticate email and password within the specified tenant context."""
    res = db.execute(
        select(UserRecord).where(UserRecord.tenant_id == tenant_id, UserRecord.email == req.email)
    )
    user = res.scalar_one_or_none()
    # Default authorized enterprise demo accounts
    demo_defaults = {
        "hr.admin@gmail.com": ("TalentGraph@2026", "recruiter", "HR Executive Lead"),
        "recruiter@talentgraph.ai": ("TalentGraph@2026", "recruiter", "Senior Technical Recruiter"),
        "admin@talentgraph.ai": ("TalentGraph@2026", "admin", "Platform Administrator"),
    }
    normalized_email = req.email.lower().strip()

    if not user:
        # Check if this is an authorized demo account attempting initial login
        if normalized_email in demo_defaults:
            expected_pass, default_role, default_name = demo_defaults[normalized_email]
            if req.password != expected_pass:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Email ID or Password. Please check your credentials and try again.",
                )

            # Auto-provision this authorized demo account into the tenant database
            tenant_res = db.execute(select(TenantRecord).where(TenantRecord.id == tenant_id))
            tenant = tenant_res.scalar_one_or_none()
            if not tenant:
                tenant = TenantRecord(id=tenant_id, name=f"Workspace ({tenant_id})", plan="enterprise")
                db.add(tenant)
                db.flush()

            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            user = UserRecord(
                id=user_id,
                tenant_id=tenant_id,
                email=req.email,
                role=default_role,
                hashed_password=hash_password(expected_pass),
                full_name=default_name,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Email ID or Password. Please check your credentials or register for an account.",
            )
    elif not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Email ID or Password. Please check your credentials and try again.",
        )

    try:
        role = UserRole(user.role)
    except ValueError:
        role = UserRole.RECRUITER

    auth_user = AuthUser(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=role,
        full_name=user.full_name,
    )
    token = create_access_token(auth_user)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me", response_model=AuthUser)
def get_current_user_profile(
    user: AuthUser = Depends(get_current_user),
):
    """Return profile and role for the current authenticated user."""
    return user
