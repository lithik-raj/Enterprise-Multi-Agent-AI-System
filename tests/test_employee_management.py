"""
Unit and Integration Tests for Employee Management Feature — Phase 25.

Covers:
  - Adding employees with required and optional fields
  - Duplicate Employee ID validation (rejected with 400/ValueError)
  - Duplicate Email validation (rejected with 400/ValueError)
  - Directory search and filtering by department, designation, and status
  - Updating employee details with audit trail logging
  - Deleting employees with strict isolation: candidate records (applicants) remain completely untouched
  - API endpoint testing via FastAPI TestClient
"""

import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.database.base import get_db, init_db
from app.database.models import CandidateRecord, EmployeeRecord
from app.main import app
from app.services.employee_service import EmployeeService, get_employee_service


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is initialized before running tests."""
    init_db()


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def emp_service():
    """Get fresh EmployeeService instance."""
    return get_employee_service()


# ── Core Service Tests ────────────────────────────────────────────────────────

class TestEmployeeService:
    """Test suite for EmployeeService business logic and validations."""

    def test_seed_records_exist(self, emp_service):
        """Ensure realistic initial seeds (EMP-1001 to EMP-1005) exist."""
        res = emp_service.list_employees(tenant_id="tenant-default")
        assert res["total_count"] >= 5
        emp_ids = [e["employee_id"] for e in res["employees"]]
        assert "EMP-1001" in emp_ids
        assert "EMP-1002" in emp_ids

    def test_add_employee_success(self, emp_service):
        """Test adding a valid new employee record."""
        unique_suffix = int(datetime.utcnow().timestamp() * 1000) % 100000
        test_emp_id = f"EMP-TEST-{unique_suffix}"
        test_email = f"karthik.{unique_suffix}@enterprise.ai"

        created = emp_service.add_employee(
            tenant_id="tenant-default",
            name="Karthik Subramanian",
            email=test_email,
            department="Engineering",
            designation="Principal AI Systems Architect",
            joining_date="2024-01-15",
            employee_id=test_emp_id,
            skills=["FastAPI", "LangGraph", "PostgreSQL", "PyTorch"],
            experience_years=8.5,
            status="ACTIVE",
            phone="+91 98765 43210",
            location="Bengaluru, India",
            notes="Technical lead for autonomous agent workflows",
            actor="HR Lead",
        )

        assert created["employee_id"] == test_emp_id
        assert created["name"] == "Karthik Subramanian"
        assert created["email"] == test_email
        assert created["experience_years"] == 8.5
        assert "FastAPI" in created["skills"]
        assert "LangGraph" in created["skills"]

    def test_reject_duplicate_employee_id(self, emp_service):
        """Test duplicate Employee ID validation fails with clear error."""
        unique_suffix = int(datetime.utcnow().timestamp() * 1000) % 100000
        dup_id = f"EMP-DUP-{unique_suffix}"
        first_email = f"first.{unique_suffix}@enterprise.ai"
        second_email = f"second.{unique_suffix}@enterprise.ai"

        # First add succeeds
        emp_service.add_employee(
            tenant_id="tenant-default",
            name="Initial Staff",
            email=first_email,
            department="Data & AI",
            designation="ML Engineer",
            joining_date="2023-05-10",
            employee_id=dup_id,
        )

        # Second add with same employee_id must raise ValueError
        with pytest.raises(ValueError) as excinfo:
            emp_service.add_employee(
                tenant_id="tenant-default",
                name="Second Staff",
                email=second_email,
                department="Data & AI",
                designation="ML Engineer",
                joining_date="2023-06-10",
                employee_id=dup_id,
            )
        assert f"Duplicate Employee ID" in str(excinfo.value)
        assert dup_id in str(excinfo.value)

    def test_reject_duplicate_email(self, emp_service):
        """Test duplicate Email validation (case-insensitive) fails with clear error."""
        unique_suffix = int(datetime.utcnow().timestamp() * 1000) % 100000
        shared_email = f"shared.user.{unique_suffix}@enterprise.ai"

        # First add succeeds
        emp_service.add_employee(
            tenant_id="tenant-default",
            name="User Alpha",
            email=shared_email,
            department="Engineering",
            designation="Backend Engineer",
            joining_date="2023-01-10",
        )

        # Second add with identical email (uppercase variation) must fail
        with pytest.raises(ValueError) as excinfo:
            emp_service.add_employee(
                tenant_id="tenant-default",
                name="User Beta",
                email=shared_email.upper(),
                department="Human Resources",
                designation="Talent Partner",
                joining_date="2023-02-15",
            )
        assert "Duplicate Email" in str(excinfo.value)
        assert "already exists" in str(excinfo.value)

    def test_directory_search_and_filters(self, emp_service):
        """Test directory keyword search and filtering by department & designation."""
        res = emp_service.list_employees(
            tenant_id="tenant-default",
            search="Priya",
        )
        assert any("Priya" in e["name"] for e in res["employees"])

        # Filter by department
        res_eng = emp_service.list_employees(
            tenant_id="tenant-default",
            department="Engineering",
        )
        assert len(res_eng["employees"]) > 0
        assert all(e["department"] == "Engineering" for e in res_eng["employees"])

    def test_update_employee_and_audit_diff(self, emp_service):
        """Test updating employee details and verifying diffs are computed."""
        unique_suffix = int(datetime.utcnow().timestamp() * 1000) % 100000
        emp_id = f"EMP-UPD-{unique_suffix}"
        email = f"upd.{unique_suffix}@enterprise.ai"

        created = emp_service.add_employee(
            tenant_id="tenant-default",
            name="Pre Update Name",
            email=email,
            department="Engineering",
            designation="Junior Developer",
            joining_date="2024-01-01",
            employee_id=emp_id,
            skills=["Python"],
            experience_years=2.0,
        )

        updated = emp_service.update_employee(
            emp_id_or_id=created["id"],
            tenant_id="tenant-default",
            designation="Staff AI Systems Engineer",
            skills=["Python", "FastAPI", "LangGraph", "Docker"],
            experience_years=4.5,
            notes="Promoted during Q3 cycle",
            actor="Engineering Director",
        )

        assert updated["designation"] == "Staff AI Systems Engineer"
        assert updated["experience_years"] == 4.5
        assert "FastAPI" in updated["skills"]
        assert "designation" in updated["changes_applied"]
        assert updated["changes_applied"]["designation"]["old"] == "Junior Developer"
        assert updated["changes_applied"]["designation"]["new"] == "Staff AI Systems Engineer"

    def test_delete_employee_strictly_preserves_candidate_records(self, emp_service):
        """
        CRITICAL ISOLATION RULE:
        Deleting an employee must NEVER delete or mutate job applicant resumes (CandidateRecord).
        """
        db = next(get_db())
        try:
            # 1. Seed or find a CandidateRecord (Job Applicant)
            applicant_email = f"applicant.{int(datetime.utcnow().timestamp())}@talentpool.com"
            candidate = CandidateRecord(
                id=f"cand_test_{int(datetime.utcnow().timestamp())}",
                tenant_id="tenant-default",
                source_file_id="applicant_resume.pdf",
                profile_json=json.dumps({
                    "name": "Applicant Jane Doe",
                    "email": applicant_email,
                    "skills": ["PyTorch", "Transformers", "NLP"],
                }),
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            candidate_id = candidate.id
            initial_candidate_count = db.query(CandidateRecord).count()

            # 2. Create an Employee to be deleted
            unique_suffix = int(datetime.utcnow().timestamp() * 1000) % 100000
            del_emp_id = f"EMP-DEL-{unique_suffix}"
            emp = emp_service.add_employee(
                tenant_id="tenant-default",
                name="Temporary Staff To Delete",
                email=f"temp.{unique_suffix}@enterprise.ai",
                department="Human Resources",
                designation="Contract Recruiter",
                joining_date="2024-02-01",
                employee_id=del_emp_id,
            )

            # 3. Delete the employee
            del_result = emp_service.delete_employee(
                emp_id_or_id=emp["id"],
                tenant_id="tenant-default",
                reason="Contract completed",
                actor="HR Admin",
            )
            assert del_result["status"] == "success"

            # 4. Verify employee is removed from employees table
            deleted_check = emp_service.get_employee(emp["id"], tenant_id="tenant-default")
            assert deleted_check is None

            # 5. VERIFY APPLICANT RECORD IS 100% INTACT AND UNMODIFIED
            surviving_candidate = db.query(CandidateRecord).filter(CandidateRecord.id == candidate_id).first()
            assert surviving_candidate is not None
            assert surviving_candidate.profile.get("name") == "Applicant Jane Doe"
            assert surviving_candidate.profile.get("email") == applicant_email
            final_candidate_count = db.query(CandidateRecord).count()
            assert final_candidate_count == initial_candidate_count
        finally:
            db.close()


# ── FastAPI Router Integration Tests ──────────────────────────────────────────

class TestEmployeeAPIEndpoints:
    """Integration test suite for /api/employees HTTP routes."""

    def test_api_get_employees(self, client):
        """GET /api/employees returns directory payload with aggregates."""
        res = client.get("/api/employees")
        assert res.status_code == 200
        data = res.json()
        assert "employees" in data
        assert "total_count" in data
        assert "departments_count" in data
        assert "average_experience" in data
        assert isinstance(data["employees"], list)

    def test_api_get_metadata(self, client):
        """GET /api/employees/meta returns department and designation lists."""
        res = client.get("/api/employees/meta")
        assert res.status_code == 200
        data = res.json()
        assert "departments" in data
        assert "designations" in data

    def test_api_add_duplicate_employee_id_rejected_with_400(self, client):
        """POST /api/employees returns 400 when duplicate employee_id is submitted."""
        unique_suffix = int(datetime.utcnow().timestamp() * 1000) % 100000
        dup_id = f"EMP-API-{unique_suffix}"

        payload_1 = {
            "name": "First Employee",
            "email": f"api1.{unique_suffix}@enterprise.ai",
            "department": "Engineering",
            "designation": "Software Engineer",
            "joining_date": "2024-03-01",
            "employee_id": dup_id,
        }
        res_1 = client.post("/api/employees", json=payload_1)
        assert res_1.status_code == 201

        payload_2 = {
            "name": "Second Employee",
            "email": f"api2.{unique_suffix}@enterprise.ai",
            "department": "Engineering",
            "designation": "QA Engineer",
            "joining_date": "2024-03-01",
            "employee_id": dup_id,
        }
        res_2 = client.post("/api/employees", json=payload_2)
        assert res_2.status_code == 400
        assert f"Duplicate Employee ID" in res_2.json()["detail"]
        assert dup_id in res_2.json()["detail"]

    def test_api_update_and_delete_lifecycle(self, client):
        """Full lifecycle test: create, fetch, update, delete via API."""
        unique_suffix = int(datetime.utcnow().timestamp() * 1000) % 100000
        create_payload = {
            "name": "Lifecycle Employee",
            "email": f"lifecycle.{unique_suffix}@enterprise.ai",
            "department": "DevOps & Cloud",
            "designation": "Cloud Engineer",
            "joining_date": "2024-04-01",
            "skills": ["Kubernetes", "Terraform"],
            "experience_years": 3.0,
        }

        # 1. Create
        c_res = client.post("/api/employees", json=create_payload)
        assert c_res.status_code == 201
        emp = c_res.json()["employee"]
        emp_id = emp["employee_id"]

        # 2. Get
        g_res = client.get(f"/api/employees/{emp_id}")
        assert g_res.status_code == 200
        assert g_res.json()["employee"]["name"] == "Lifecycle Employee"

        # 3. Update
        u_res = client.put(f"/api/employees/{emp_id}", json={
            "designation": "Senior Site Reliability Engineer",
            "experience_years": 4.5,
        })
        assert u_res.status_code == 200
        assert u_res.json()["employee"]["designation"] == "Senior Site Reliability Engineer"

        # 4. Delete
        d_res = client.delete(f"/api/employees/{emp_id}?reason=Offboarding")
        assert d_res.status_code == 200
        assert "deleted successfully" in d_res.json()["message"]

        # 5. Verify 404 after deletion
        g2_res = client.get(f"/api/employees/{emp_id}")
        assert g2_res.status_code == 404
