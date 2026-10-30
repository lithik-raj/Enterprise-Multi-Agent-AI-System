"""
Tests for Batch Talent Intelligence Service — Phase 23.

Covers:
  - BatchService candidate ranking and leaderboard ordering
  - Skill overlap computation and match categorization
  - CSV export formatting
  - Batch retrieval and demo seeding
  - API endpoint contract validation
"""

import csv
import io
import pytest
from unittest.mock import patch, MagicMock


# ── BatchService Unit Tests ───────────────────────────────────────────────────

class TestBatchService:
    """Tests for BatchService core logic."""

    def _make_service(self):
        """Create a BatchService with mocked dependencies."""
        with patch("app.services.batch_service.get_ml_inference_engine") as mock_ml, \
             patch("app.services.batch_service.get_nlp_service") as mock_nlp:

            mock_engine = MagicMock()
            mock_engine.predict.return_value = {
                "predicted_score": 0.85,
                "match_category": "Strong Match",
                "is_match": True,
                "confidence": 0.92,
                "features": {
                    "tfidf_cosine_similarity": 0.78,
                    "skill_overlap_ratio": 0.83,
                    "matched_skill_count": 5,
                    "missing_skill_count": 1,
                    "resume_length": 180,
                    "job_length": 120,
                },
            }
            mock_ml.return_value = mock_engine

            mock_nlp_svc = MagicMock()
            mock_nlp_svc.extract_skills_and_entities.return_value = {"skills": ["Python"]}
            mock_nlp.return_value = mock_nlp_svc

            from app.services.batch_service import BatchService
            service = BatchService()
            service.ml_engine = mock_engine
            service.nlp_service = mock_nlp_svc

            return service, mock_engine

    def test_demo_batch_seeded_on_init(self):
        """Verify demo batch is created during initialization."""
        service, _ = self._make_service()
        assert "batch-demo-talent-001" in service.batches
        batch = service.batches["batch-demo-talent-001"]
        assert batch.total_candidates == 4
        assert batch.job_title == "Senior AI/ML Platform Engineer"

    def test_rank_candidates_returns_sorted_leaderboard(self):
        """Verify candidates are sorted descending by predicted score."""
        service, mock_engine = self._make_service()

        scores = [0.45, 0.92, 0.73, 0.61]
        call_count = [0]
        def side_effect_predict(**kwargs):
            score = scores[call_count[0] % len(scores)]
            call_count[0] += 1
            return {
                "predicted_score": score,
                "match_category": "Strong Match" if score >= 0.7 else "Moderate Match" if score >= 0.5 else "Low Match",
                "is_match": score >= 0.7,
                "confidence": 0.85,
                "features": {"tfidf_cosine_similarity": 0.5, "skill_overlap_ratio": 0.5, "matched_skill_count": 3, "missing_skill_count": 2, "resume_length": 100, "job_length": 80},
            }

        mock_engine.predict.side_effect = side_effect_predict

        from app.services.batch_service import CandidateInput
        candidates = [
            CandidateInput(name=f"Candidate {i}", resume_text=f"Resume text for candidate {i} with enough length", experience_years=float(i), extracted_skills=["Python", "ML"])
            for i in range(1, 5)
        ]

        result = service.rank_candidates(
            job_title="Test Job",
            job_description="Test job description with enough text",
            required_skills=["Python", "ML", "Docker"],
            candidates=candidates,
        )

        assert result.total_candidates == 4
        leaderboard_scores = [c.predicted_score for c in result.leaderboard]
        assert leaderboard_scores == sorted(leaderboard_scores, reverse=True), \
            "Leaderboard must be sorted descending by predicted score"

    def test_rank_candidates_computes_skill_overlap(self):
        """Verify skill overlap ratio is computed correctly."""
        service, mock_engine = self._make_service()

        from app.services.batch_service import CandidateInput
        candidate = CandidateInput(
            name="Test Candidate",
            resume_text="AI Engineer with Python, PyTorch, and Docker experience plus more detail",
            experience_years=5.0,
            extracted_skills=["Python", "PyTorch", "Docker"],
        )

        result = service.rank_candidates(
            job_title="AI Engineer",
            job_description="Need AI Engineer with Python, PyTorch, Docker, LangGraph expertise and more skills",
            required_skills=["Python", "PyTorch", "Docker", "LangGraph"],
            candidates=[candidate],
        )

        c = result.leaderboard[0]
        assert c.overlap_ratio == 0.75  # 3/4 skills matched
        assert "python" in [s.lower() for s in c.matched_skills]
        assert "langgraph" in [s.lower() for s in c.missing_skills]

    def test_rank_candidates_statistics(self):
        """Verify batch statistics (mean, highest, lowest) are computed."""
        service, mock_engine = self._make_service()

        from app.services.batch_service import CandidateInput
        candidates = [
            CandidateInput(name="Candidate A", resume_text="Python developer with extensive experience", experience_years=3.0, extracted_skills=["Python"]),
            CandidateInput(name="Candidate B", resume_text="ML expert with deep learning background", experience_years=5.0, extracted_skills=["Python", "ML"]),
        ]

        result = service.rank_candidates(
            job_title="Dev",
            job_description="Looking for software developer with experience",
            required_skills=["Python"],
            candidates=candidates,
        )

        assert result.mean_score > 0
        assert result.highest_score >= result.lowest_score
        assert result.top_candidate_name is not None

    def test_get_batch_returns_none_for_unknown(self):
        """Verify get_batch returns None for non-existent IDs."""
        service, _ = self._make_service()
        assert service.get_batch("nonexistent-batch-id") is None

    def test_export_csv_format(self):
        """Verify CSV export has proper headers and rows."""
        service, _ = self._make_service()
        csv_data = service.export_csv("batch-demo-talent-001")

        reader = csv.reader(io.StringIO(csv_data))
        rows = list(reader)

        # Header row
        assert rows[0][0] == "Rank"
        assert rows[0][1] == "Candidate Name"
        assert "Predicted Compatibility Score" in rows[0][2]

        # Data rows (4 demo candidates)
        assert len(rows) == 5  # 1 header + 4 candidates

    def test_export_csv_raises_for_unknown_batch(self):
        """Verify export raises KeyError for unknown batch."""
        service, _ = self._make_service()
        with pytest.raises(KeyError):
            service.export_csv("nonexistent-batch")

    def test_custom_batch_id(self):
        """Verify custom batch IDs are respected."""
        service, _ = self._make_service()

        from app.services.batch_service import CandidateInput
        candidates = [
            CandidateInput(name="Candidate X", resume_text="Software engineer with Python skills", experience_years=2.0, extracted_skills=["Python"]),
        ]

        result = service.rank_candidates(
            job_title="Role",
            job_description="Need developer for this role position",
            required_skills=["Python"],
            candidates=candidates,
            batch_id="my-custom-batch-123",
        )

        assert result.batch_id == "my-custom-batch-123"
        assert service.get_batch("my-custom-batch-123") is not None


# ── Batch API Integration Tests ───────────────────────────────────────────────

class TestBatchAPI:
    """Tests for the Batch API router endpoints."""

    @pytest.fixture
    def client(self):
        """Create a FastAPI test client with mocked dependencies."""
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

            # Reset singleton to pick up mocks
            import app.services.batch_service as bs
            bs._batch_service_instance = None

            from fastapi.testclient import TestClient
            from app.main import app
            with TestClient(app) as c:
                yield c

            bs._batch_service_instance = None

    def test_get_samples_endpoint(self, client):
        """Verify /api/batch/samples returns sample candidates."""
        res = client.get("/api/batch/samples")
        assert res.status_code == 200
        data = res.json()
        assert "candidates" in data
        assert len(data["candidates"]) >= 4
        assert "job_title" in data
        assert "required_skills" in data

    def test_rank_endpoint(self, client):
        """Verify POST /api/batch/rank creates a ranked batch."""
        payload = {
            "job_title": "Test Engineer Role",
            "job_description": "Need test engineer with Python and testing skills plus automation experience",
            "required_skills": ["Python", "Testing"],
            "candidates": [
                {
                    "name": "Alice Test",
                    "resume_text": "Python test engineer with 5 years of experience in testing frameworks",
                    "experience_years": 5.0,
                    "extracted_skills": ["Python", "Testing"],
                }
            ],
        }
        res = client.post("/api/batch/rank", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_candidates"] == 1
        assert data["job_title"] == "Test Engineer Role"
        assert len(data["leaderboard"]) == 1

    def test_get_demo_batch(self, client):
        """Verify GET /api/batch/{demo_id} returns the seeded batch."""
        res = client.get("/api/batch/batch-demo-talent-001")
        assert res.status_code == 200
        data = res.json()
        assert data["batch_id"] == "batch-demo-talent-001"
        assert data["total_candidates"] == 4

    def test_export_csv_endpoint(self, client):
        """Verify CSV export endpoint returns downloadable CSV."""
        res = client.get("/api/batch/batch-demo-talent-001/export")
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("content-type", "")
        assert "attachment" in res.headers.get("content-disposition", "")

    def test_get_nonexistent_batch_returns_404(self, client):
        """Verify 404 for non-existent batch ID."""
        res = client.get("/api/batch/nonexistent-id-xyz")
        assert res.status_code == 404

    def test_get_extended_pool_endpoint(self, client):
        """Verify GET /api/batch/pool returns realistic candidate profiles."""
        res = client.get("/api/batch/pool")
        assert res.status_code == 200
        data = res.json()
        assert data["total_pool_size"] >= 8
        assert len(data["candidates"]) >= 8
        names = [c["name"] for c in data["candidates"]]
        assert "Dr. Sarah Lin" in names
        assert "Alex Vance" in names
        assert "Priya R. Nair" in names
        assert "Vikramaditya Rao" in names

    def test_record_candidate_decision_endpoint(self, client):
        """Verify POST /api/batch/{batch_id}/decide logs decision and returns email draft."""
        payload = {
            "candidate_name": "Dr. Sarah Lin",
            "decision": "SHORTLIST",
            "reason": "Strong PyTorch and LangGraph production expertise",
            "recruiter_name": "Senior Tech Recruiter",
        }
        res = client.post("/api/batch/batch-demo-talent-001/decide", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["candidate_name"] == "Dr. Sarah Lin"
        assert data["decision"] == "SHORTLISTED"
        assert data["trace_id"].startswith("rec-log-")
        assert "Dear Dr. Sarah Lin" in data["email_draft"]["body"]

        # Check candidate updated in batch
        batch_res = client.get("/api/batch/batch-demo-talent-001")
        assert batch_res.status_code == 200
        batch = batch_res.json()
        sarah = next(c for c in batch["leaderboard"] if c["name"] == "Dr. Sarah Lin")
        assert sarah["decision"] == "SHORTLISTED"
        assert sarah["decision_reason"] == "Strong PyTorch and LangGraph production expertise"

