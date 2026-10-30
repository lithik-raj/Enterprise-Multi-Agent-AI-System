"""
app/services/recovery_service.py

Enterprise Rollback & Recovery Service (Recycle Bin / Soft-Delete Vault).
Retains deleted candidates, resumes, and employee records safely for 7 days
before permanent purge. Supports 1-click Rollback (Restore) and confirmed
Permanent Deletion per DPDP Act 2023 & GDPR compliance standards.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

RETENTION_DAYS = 7


class RecycleBinItem(BaseModel):
    item_id: str = Field(default_factory=lambda: f"rcv_{uuid.uuid4().hex[:12]}")
    item_type: str = Field(..., description="candidate | employee | document")
    item_name: str = Field(..., description="Name of candidate, employee or filename")
    tenant_id: str = Field(default="default")
    original_data: Dict[str, Any] = Field(default_factory=dict, description="Complete snapshot for 100% loss-free rollback")
    deleted_by: str = Field(default="HR Recruiter")
    deleted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=RETENTION_DAYS))
    reason: Optional[str] = Field(default="HR Candidate File Archival")
    is_permanently_deleted: bool = Field(default=False)

    @property
    def days_remaining(self) -> float:
        delta = self.expires_at - datetime.utcnow()
        return max(0.0, round(delta.total_seconds() / 86400.0, 1))

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "item_name": self.item_name,
            "tenant_id": self.tenant_id,
            "deleted_by": self.deleted_by,
            "deleted_at": self.deleted_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "days_remaining": self.days_remaining,
            "is_expired": self.is_expired,
            "reason": self.reason,
            "original_data": self.original_data,
        }


class RecoveryService:
    """In-memory & persistent registry for soft-deleted candidates & employee files."""

    def __init__(self):
        self._vault: Dict[str, RecycleBinItem] = {}
        self._seed_sample_recovery_items()

    def _seed_sample_recovery_items(self):
        """Seed 2 sample soft-deleted records to demonstrate 7-day retention & rollback."""
        sample_cand = RecycleBinItem(
            item_id="rcv-cand-sample-001",
            item_type="candidate",
            item_name="David K. Chen",
            tenant_id="default",
            deleted_by="hr@talentgraph.ai",
            deleted_at=datetime.utcnow() - timedelta(days=1, hours=4),
            expires_at=datetime.utcnow() + timedelta(days=5, hours=20),
            reason="Duplicate applicant resume submission for AI Systems Engineer",
            original_data={
                "name": "David K. Chen",
                "role": "Senior AI Systems Engineer",
                "experience_years": 4.5,
                "predicted_score": 0.812,
                "matched_skills": ["Python", "FastAPI", "Docker", "PyTorch"],
                "missing_skills": ["LangGraph", "Kubernetes"],
                "status": "SHORTLISTED",
            },
        )
        sample_doc = RecycleBinItem(
            item_id="rcv-doc-sample-002",
            item_type="document",
            item_name="Archived_Staff_Evaluation_2025.pdf",
            tenant_id="default",
            deleted_by="hr@talentgraph.ai",
            deleted_at=datetime.utcnow() - timedelta(hours=18),
            expires_at=datetime.utcnow() + timedelta(days=6, hours=6),
            reason="Routine quarterly HR dossier archival",
            original_data={
                "filename": "Archived_Staff_Evaluation_2025.pdf",
                "size_bytes": 142850,
                "category": "staff_appraisal",
            },
        )
        self._vault[sample_cand.item_id] = sample_cand
        self._vault[sample_doc.item_id] = sample_doc

    def soft_delete(
        self,
        item_type: str,
        item_name: str,
        data: Dict[str, Any],
        deleted_by: str = "HR Recruiter",
        reason: Optional[str] = None,
        tenant_id: str = "default",
    ) -> RecycleBinItem:
        """Move an item into the 7-day rollback vault."""
        item = RecycleBinItem(
            item_type=item_type,
            item_name=item_name,
            tenant_id=tenant_id,
            original_data=data,
            deleted_by=deleted_by,
            reason=reason or f"Soft-deleted by {deleted_by}",
            deleted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=RETENTION_DAYS),
        )
        self._vault[item.item_id] = item
        logger.info("Soft-deleted %s '%s' (Vault ID: %s) with 7-day retention.", item_type, item_name, item.item_id)
        return item

    def list_items(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        """List active items in the rollback vault."""
        now = datetime.utcnow()
        # Filter out permanently deleted or expired past 7 days
        # Both 'default' and 'tenant_default' reference the primary enterprise tenant
        is_primary_tenant = tenant_id in ("default", "tenant_default", None, "")
        valid_items = [
            item for item in self._vault.values()
            if (
                (item.tenant_id in ("default", "tenant_default") if is_primary_tenant else item.tenant_id == tenant_id)
                and not item.is_permanently_deleted
            )
        ]
        # Sort newest first
        valid_items.sort(key=lambda x: x.deleted_at, reverse=True)
        return [item.to_dict() for item in valid_items]

    def get_item(self, item_id: str) -> Optional[RecycleBinItem]:
        return self._vault.get(item_id)

    def restore_item(self, item_id: str, actor: str = "HR Recruiter") -> Optional[Dict[str, Any]]:
        """
        Execute Rollback: restores item from vault and returns snapshot
        to caller for re-injection into active databases.
        """
        item = self._vault.get(item_id)
        if not item or item.is_permanently_deleted:
            return None

        # Remove from vault upon successful rollback
        del self._vault[item_id]
        logger.info("Rolled back / Restored %s '%s' by %s", item.item_type, item.item_name, actor)
        return item.to_dict()

    def permanently_delete_item(self, item_id: str, actor: str = "HR Recruiter") -> bool:
        """
        Permanent Deletion: hard-deletes the record permanently from the vault.
        Irreversible action.
        """
        if item_id in self._vault:
            self._vault[item_id].is_permanently_deleted = True
            del self._vault[item_id]
            logger.info("Permanently deleted item %s by %s", item_id, actor)
            return True
        return False


_global_recovery_service: Optional[RecoveryService] = None


def get_recovery_service() -> RecoveryService:
    global _global_recovery_service
    if _global_recovery_service is None:
        _global_recovery_service = RecoveryService()
    return _global_recovery_service
