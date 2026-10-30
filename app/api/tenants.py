"""
app/api/tenants.py

Tenant management endpoints ensuring multi-tenant provisioning and configuration.
All actions strictly isolate data to the caller's tenant.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthUser, UserRole
from app.database.base import get_db
from app.database.models import TenantRecord, UserRecord
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/api/tenants", tags=["Tenants"])


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    plan: str = Field("enterprise", max_length=50)
    settings: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    plan: str
    settings: Dict[str, Any]
    created_at: str


class UpdateSettingsRequest(BaseModel):
    settings: Dict[str, Any]


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    req: CreateTenantRequest,
    db: Session = Depends(get_db),
):
    """Provision a new enterprise tenant."""
    tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
    record = TenantRecord(
        id=tenant_id,
        name=req.name,
        plan=req.plan,
        settings_json=json.dumps(req.settings or {
            "default_weights": {"must_have": 0.50, "experience": 0.25, "semantic": 0.15, "nice_to_have": 0.10},
            "retention_days": 90,
            "cost_cap_usd": 500.0,
        }),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return TenantResponse(
        id=record.id,
        name=record.name,
        plan=record.plan,
        settings=record.settings,
        created_at=str(record.created_at),
    )


@router.get("/current", response_model=TenantResponse)
def get_current_tenant(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for the active tenant."""
    res = db.execute(select(TenantRecord).where(TenantRecord.id == user.tenant_id))
    record = res.scalar_one_or_none()
    if not record:
        # Auto-provision if missing
        record = TenantRecord(
            id=user.tenant_id,
            name=f"Workspace ({user.tenant_id})",
            plan="enterprise",
            settings_json=json.dumps({
                "default_weights": {"must_have": 0.50, "experience": 0.25, "semantic": 0.15, "nice_to_have": 0.10},
                "retention_days": 90,
                "cost_cap_usd": 500.0,
            }),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return TenantResponse(
        id=record.id,
        name=record.name,
        plan=record.plan,
        settings=record.settings,
        created_at=str(record.created_at),
    )


@router.put("/current/settings", response_model=TenantResponse)
def update_tenant_settings(
    req: UpdateSettingsRequest,
    user: AuthUser = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Update settings for the active tenant (Admin role strictly required)."""
    res = db.execute(select(TenantRecord).where(TenantRecord.id == user.tenant_id))
    record = res.scalar_one_or_none()
    if not record:
        record = TenantRecord(
            id=user.tenant_id,
            name=f"Workspace ({user.tenant_id})",
            plan="enterprise",
            settings_json=json.dumps(req.settings),
        )
        db.add(record)
    else:
        record.settings = req.settings
    db.commit()
    db.refresh(record)

    return TenantResponse(
        id=record.id,
        name=record.name,
        plan=record.plan,
        settings=record.settings,
        created_at=str(record.created_at),
    )
