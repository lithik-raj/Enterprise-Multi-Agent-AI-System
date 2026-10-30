"""
services/cost_service.py

Tenant Cost Tracking and Budget Cap Enforcement.
Tracks cumulative screening spend per tenant and enforces configurable spending limits.
Prevents unintended cloud/LLM cost overruns.
"""

from __future__ import annotations

import logging
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import RunRecord, TenantRecord

logger = logging.getLogger(__name__)


class CostCapExceededError(HTTPException):
    """Raised when an operation would cause a tenant to exceed its allocated budget cap."""
    def __init__(self, tenant_id: str, current_spend: float, cost_cap: float):
        detail = (
            f"Tenant '{tenant_id}' has exceeded its budget cap. "
            f"Current spend: ${current_spend:.2f}, Cap: ${cost_cap:.2f}. "
            f"Upgrade plan or increase cost cap in tenant settings to resume screening."
        )
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class CostService:
    """Manages tenant billing usage and cost cap enforcement."""

    COST_PER_RESUME_USD = 0.005  # Average cost per resume screened

    def get_tenant_spend(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Calculates total historical spend and remaining budget for a tenant."""
        tenant = db.execute(select(TenantRecord).where(TenantRecord.id == tenant_id)).scalar_one_or_none()
        cost_cap = 500.0
        if tenant and tenant.settings and "cost_cap_usd" in tenant.settings:
            cost_cap = float(tenant.settings["cost_cap_usd"])

        # Aggregate total cost across runs
        total_spent = db.execute(
            select(func.coalesce(func.sum(RunRecord.cost), 0.0)).where(RunRecord.tenant_id == tenant_id)
        ).scalar_one()

        remaining = max(0.0, cost_cap - total_spent)

        return {
            "tenant_id": tenant_id,
            "cost_cap_usd": round(cost_cap, 2),
            "total_spent_usd": round(total_spent, 4),
            "remaining_budget_usd": round(remaining, 4),
            "is_capped": total_spent >= cost_cap,
        }

    def verify_budget_availability(
        self,
        tenant_id: str,
        resume_count: int,
        db: Session,
    ) -> float:
        """
        Validates whether the tenant has enough budget to screen the requested batch.
        Raises CostCapExceededError if the cost cap is violated.
        Returns the estimated cost.
        """
        spend_info = self.get_tenant_spend(tenant_id, db)
        estimated_cost = resume_count * self.COST_PER_RESUME_USD

        if spend_info["total_spent_usd"] + estimated_cost > spend_info["cost_cap_usd"]:
            raise CostCapExceededError(
                tenant_id=tenant_id,
                current_spend=spend_info["total_spent_usd"],
                cost_cap=spend_info["cost_cap_usd"],
            )

        return estimated_cost
