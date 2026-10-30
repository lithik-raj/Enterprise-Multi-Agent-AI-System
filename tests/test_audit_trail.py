"""
Tests for Audit Trail & System Observability Service — Phase 24.

Covers:
  - AuditService event recording and retrieval
  - Category-based filtering
  - Statistics aggregation
  - Startup seed events
  - API endpoint contract validation
"""

import pytest
from unittest.mock import patch, MagicMock


# ── AuditService Unit Tests ──────────────────────────────────────────────────

class TestAuditService:
    """Tests for AuditService core logic."""

    def _make_service(self):
        from app.services.audit_service import AuditService
        return AuditService()

    def test_seed_events_on_init(self):
        """Verify startup seed events are created during initialization."""
        service = self._make_service()
        trail = service.get_trail(limit=100)
        assert len(trail) >= 10, "Should have at least 10 seeded startup events"

    def test_record_event(self):
        """Verify a new event can be recorded and retrieved."""
        service = self._make_service()
        initial_count = len(service.get_trail(limit=500))

        event = service.record(
            category="TEST",
            action="Test action performed",
            details="Testing the audit service",
            severity="info",
        )

        assert event.event_id is not None
        assert event.category == "TEST"
        assert event.action == "Test action performed"

        trail = service.get_trail(limit=500)
        assert len(trail) == initial_count + 1

    def test_trail_ordered_newest_first(self):
        """Verify trail returns events in reverse chronological order."""
        service = self._make_service()

        service.record(category="TEST", action="First event")
        service.record(category="TEST", action="Second event")
        service.record(category="TEST", action="Third event")

        trail = service.get_trail(limit=5)
        assert trail[0]["action"] == "Third event"
        assert trail[1]["action"] == "Second event"
        assert trail[2]["action"] == "First event"

    def test_category_filter(self):
        """Verify trail can be filtered by category."""
        service = self._make_service()

        service.record(category="ALPHA", action="Alpha event 1")
        service.record(category="BETA", action="Beta event 1")
        service.record(category="ALPHA", action="Alpha event 2")

        alpha_trail = service.get_trail(limit=100, category="ALPHA")
        for evt in alpha_trail:
            assert evt["category"] == "ALPHA"

        beta_trail = service.get_trail(limit=100, category="BETA")
        for evt in beta_trail:
            assert evt["category"] == "BETA"

    def test_limit_parameter(self):
        """Verify limit parameter restricts returned events."""
        service = self._make_service()

        for i in range(20):
            service.record(category="BULK", action=f"Bulk event {i}")

        limited = service.get_trail(limit=5)
        assert len(limited) == 5

    def test_stats_aggregation(self):
        """Verify statistics are correctly aggregated by category."""
        service = self._make_service()
        stats = service.get_stats()

        assert stats["total_events"] > 0
        assert stats["security_events"] >= 3  # 3 security seed events
        assert stats["last_event_time"] is not None
        assert isinstance(stats["total_events"], int)

    def test_stats_updated_on_record(self):
        """Verify stats update when new events are recorded."""
        service = self._make_service()
        initial_total = service.get_stats()["total_events"]

        service.record(category="SECURITY", action="New security event")
        updated = service.get_stats()

        assert updated["total_events"] == initial_total + 1
        assert updated["security_events"] > 0

    def test_error_severity_counted(self):
        """Verify error-severity events increment error count."""
        service = self._make_service()
        initial_errors = service.get_stats()["error_count"]

        service.record(category="SYSTEM", action="Critical failure", severity="error")
        service.record(category="SYSTEM", action="Fatal crash", severity="critical")

        stats = service.get_stats()
        assert stats["error_count"] == initial_errors + 2

    def test_max_trail_size_respected(self):
        """Verify the trail doesn't exceed MAX_TRAIL_SIZE."""
        from app.services.audit_service import MAX_TRAIL_SIZE
        service = self._make_service()

        for i in range(MAX_TRAIL_SIZE + 100):
            service.record(category="OVERFLOW", action=f"Event {i}")

        trail = service.get_trail(limit=MAX_TRAIL_SIZE + 50)
        assert len(trail) <= MAX_TRAIL_SIZE

    def test_metadata_preserved(self):
        """Verify custom metadata is stored in the event."""
        service = self._make_service()

        event = service.record(
            category="API",
            action="Request processed",
            metadata={"endpoint": "/api/health", "method": "GET", "status": 200},
        )

        assert event.metadata["endpoint"] == "/api/health"
        assert event.metadata["status"] == 200


# ── Audit API Integration Tests ──────────────────────────────────────────────

class TestAuditAPI:
    """Tests for the Audit Trail API router endpoints."""

    @pytest.fixture
    def client(self):
        """Create a FastAPI test client."""
        # Reset singleton to get fresh service
        import app.services.audit_service as audit_mod
        audit_mod._audit_service_instance = None

        with patch("app.services.batch_service.get_ml_inference_engine") as mock_ml, \
             patch("app.services.batch_service.get_nlp_service") as mock_nlp:

            mock_engine = MagicMock()
            mock_engine.predict.return_value = {
                "predicted_score": 0.80,
                "match_category": "Strong Match",
                "is_match": True,
                "confidence": 0.88,
                "features": {"tfidf_cosine_similarity": 0.7, "skill_overlap_ratio": 0.8, "matched_skill_count": 4, "missing_skill_count": 1, "resume_length": 150, "job_length": 100},
            }
            mock_ml.return_value = mock_engine

            mock_nlp_svc = MagicMock()
            mock_nlp_svc.extract_skills_and_entities.return_value = {"skills": ["Python"]}
            mock_nlp.return_value = mock_nlp_svc

            import app.services.batch_service as bs
            bs._batch_service_instance = None

            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app) as c:
                yield c

            audit_mod._audit_service_instance = None
            bs._batch_service_instance = None

    def test_get_trail_endpoint(self, client):
        """Verify GET /api/audit/trail returns events."""
        res = client.get("/api/audit/trail")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "action" in data[0]
        assert "category" in data[0]
        assert "timestamp" in data[0]

    def test_get_trail_with_limit(self, client):
        """Verify limit query parameter works."""
        res = client.get("/api/audit/trail?limit=3")
        assert res.status_code == 200
        data = res.json()
        assert len(data) <= 3

    def test_get_trail_with_category_filter(self, client):
        """Verify category filter works."""
        res = client.get("/api/audit/trail?category=SECURITY")
        assert res.status_code == 200
        data = res.json()
        for evt in data:
            assert evt["category"] == "SECURITY"

    def test_get_stats_endpoint(self, client):
        """Verify GET /api/audit/stats returns statistics."""
        res = client.get("/api/audit/stats")
        assert res.status_code == 200
        data = res.json()
        assert "total_events" in data
        assert "api_events" in data
        assert "security_events" in data
        assert data["total_events"] > 0

    def test_record_event_endpoint(self, client):
        """Verify POST /api/audit/record creates a new event."""
        payload = {
            "category": "CUSTOM",
            "action": "Custom audit event for testing",
            "details": "Test details",
            "severity": "warning",
        }
        res = client.post("/api/audit/record", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "recorded"
        assert "event_id" in data

    def test_recorded_event_appears_in_trail(self, client):
        """Verify a recorded event appears in subsequent trail queries."""
        client.post("/api/audit/record", json={
            "category": "VERIFY",
            "action": "Verification event for audit test",
        })

        res = client.get("/api/audit/trail?limit=5")
        data = res.json()
        actions = [e["action"] for e in data]
        assert "Verification event for audit test" in actions
