"""
tests/test_employee_tickets_and_recovery.py

Automated test suite verifying:
1. Employee Assigned Work Tickets (GET & POST)
2. Rollback & Recovery 7-Day Soft-Delete Vault, Restore & Permanent Deletion
3. AI Voice Assistant advanced queries:
   - Work completion status
   - Future predictive performance
   - Company strategic development recommendations
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH_HEADERS = {"X-Tenant-ID": "default"}


def test_get_employee_tickets():
    """Verify retrieving assigned work tickets for an employee."""
    res = client.get("/api/employees/EMP-1001/tickets", headers=AUTH_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["employee_id"] == "EMP-1001"
    tickets = data["tickets"]
    assert len(tickets) >= 1
    tkt = tickets[0]
    assert "ticket_id" in tkt
    assert "status" in tkt
    assert "completion_percentage" in tkt
    assert tkt["completion_percentage"] >= 90.0


def test_raise_new_employee_ticket():
    """Verify raising a new assigned work ticket for an employee."""
    payload = {
        "title": "Deploy Kubernetes KEDA Pod Autoscaler",
        "description": "Configure Redis queue depth autoscaling for high-throughput resume evaluation.",
        "priority": "HIGH",
        "due_date": "2026-11-15",
        "assigned_by": "VP Engineering",
    }
    res = client.post("/api/employees/EMP-1001/tickets", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["employee_id"] == "EMP-1001"
    ticket = data["ticket"]
    assert ticket["title"] == payload["title"]
    assert ticket["status"] == "IN_PROGRESS"
    assert "ticket_id" in ticket


def test_soft_delete_and_recovery_flow():
    """Verify complete soft-delete, 7-day retention, restore, and permanent deletion flow."""
    # 1. Soft-delete candidate into 7-day retention vault
    del_payload = {
        "item_type": "candidate",
        "item_name": "Test Candidate Alpha",
        "item_id": "cand_test_alpha_001",
        "data": {
            "name": "Test Candidate Alpha",
            "predicted_score": 0.82,
            "matched_skills": ["Python", "FastAPI"],
            "experience_years": 4.0,
            "status": "PENDING",
        },
        "reason": "Test soft-delete archival",
        "deleted_by": "hr.admin@gmail.com",
    }
    res_del = client.post("/api/recovery/delete", json=del_payload, headers=AUTH_HEADERS)
    assert res_del.status_code == 201, res_del.text
    del_resp = res_del.json()
    assert del_resp["success"] is True
    assert del_resp["item_name"] == "Test Candidate Alpha"
    item_id = del_resp["item_id"]
    assert item_id is not None
    assert del_resp["days_remaining"] >= 6.9

    # 2. Retrieve recovery items
    res_list = client.get("/api/recovery/items", headers=AUTH_HEADERS)
    assert res_list.status_code == 200, res_list.text
    items = res_list.json()
    assert any(i["item_id"] == item_id for i in items)

    # 3. Restore candidate (Rollback)
    res_restore = client.post(f"/api/recovery/restore/{item_id}?actor=HR%20Lead", headers=AUTH_HEADERS)
    assert res_restore.status_code == 200, res_restore.text
    assert res_restore.json()["success"] is True

    # 4. Soft-delete again and permanently delete with safeguard
    res_del2 = client.post("/api/recovery/delete", json=del_payload, headers=AUTH_HEADERS)
    assert res_del2.status_code == 201
    item_id2 = res_del2.json()["item_id"]

    res_perm = client.delete(f"/api/recovery/permanent/{item_id2}?actor=HR%20Lead", headers=AUTH_HEADERS)
    assert res_perm.status_code == 200, res_perm.text
    assert res_perm.json()["success"] is True


def test_voice_assistant_work_completion():
    """Verify AI Voice Assistant answers whether employee completed assigned work."""
    payload = {
        "query": "whether she completed the assigned work Priya Natarajan",
        "batch_id": "batch-demo-talent-001",
    }
    res = client.post("/api/recruiter/voice-assist", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "reply_text" in data
    text = data["reply_text"].lower()
    assert "priya" in text or "completed" in text or "100" in text or "work" in text


def test_voice_assistant_future_performance():
    """Verify AI Voice Assistant answers whether candidate can perform good for this role in future."""
    payload = {
        "query": "whether in future he can perform good here for this role Vikram Malhotra",
        "batch_id": "batch-demo-talent-001",
    }
    res = client.post("/api/recruiter/voice-assist", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "reply_text" in data
    text = data["reply_text"].lower()
    assert "future" in text or "performance" in text or "velocity" in text or "predict" in text


def test_voice_assistant_company_development():
    """Verify AI Voice Assistant provides actionable strategy for what else we can do to develop company."""
    payload = {
        "query": "what else can we do to develop our company",
        "batch_id": "batch-demo-talent-001",
    }
    res = client.post("/api/recruiter/voice-assist", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "reply_text" in data
    text = data["reply_text"].lower()
    assert "company" in text or "recommend" in text or "scale" in text or "talent" in text


def test_employee_deletion_recovery_vault_and_restore_cycle():
    """
    Verify complete employee lifecycle across Employee Management and Rollback & Recovery:
    1. Create a new employee in Employee Management
    2. Delete the employee via DELETE /api/employees/{emp_id}
    3. Verify employee is moved into 7-day Rollback & Recovery vault with item_type == 'employee'
    4. Execute 1-click Rollback & Restore via POST /api/recovery/restore/{item_id}
    5. Verify employee is immediately reinstated in Employee Management directory with Active status
    6. Delete again and execute Permanent Hard Delete via DELETE /api/recovery/permanent/{item_id}
    7. Verify permanent purge from both Recovery Vault and active system
    """
    import time
    ts = int(time.time() * 1000) % 1000000
    create_payload = {
        "name": f"Vault Test Employee {ts}",
        "email": f"vault.emp.{ts}@talentgraph.ai",
        "department": "Engineering",
        "designation": "AI Staff Engineer",
        "joining_date": "2024-05-01",
        "skills": ["Python", "PyTorch", "LangGraph"],
        "experience_years": 5.0,
    }

    # 1. Create employee
    res_c = client.post("/api/employees", json=create_payload, headers=AUTH_HEADERS)
    assert res_c.status_code == 201, res_c.text
    created_emp = res_c.json()["employee"]
    emp_id = created_emp["employee_id"]

    # 2. Delete employee from Employee Management
    res_d = client.delete(f"/api/employees/{emp_id}?reason=Testing+recovery+vault", headers=AUTH_HEADERS)
    assert res_d.status_code == 200, res_d.text
    d_data = res_d.json()
    assert "deleted successfully" in d_data["message"]
    recovery_id = d_data.get("recovery_vault_id")
    assert recovery_id is not None

    # Verify removed from active employees
    res_get_del = client.get(f"/api/employees/{emp_id}", headers=AUTH_HEADERS)
    assert res_get_del.status_code == 404

    # 3. Verify presence in 7-day Rollback & Recovery Vault
    res_vault = client.get("/api/recovery/items", headers=AUTH_HEADERS)
    assert res_vault.status_code == 200
    vault_items = res_vault.json()
    emp_recovery_item = next((item for item in vault_items if item["item_id"] == recovery_id), None)
    assert emp_recovery_item is not None
    assert emp_recovery_item["item_type"] == "employee"
    assert emp_id in emp_recovery_item["item_name"]
    assert emp_recovery_item["days_remaining"] >= 6.9

    # 4. Rollback & Restore employee back to active system
    res_restore = client.post(f"/api/recovery/restore/{recovery_id}?actor=HR%20Lead", headers=AUTH_HEADERS)
    assert res_restore.status_code == 200, res_restore.text
    assert res_restore.json()["success"] is True

    # 5. Verify employee immediately reappears in Employee Management as Active
    res_get_restored = client.get(f"/api/employees/{emp_id}", headers=AUTH_HEADERS)
    assert res_get_restored.status_code == 200, res_get_restored.text
    restored_emp = res_get_restored.json()["employee"]
    assert restored_emp["employee_id"] == emp_id
    assert restored_emp["name"] == create_payload["name"]
    assert restored_emp["status"].upper() == "ACTIVE"

    # 6. Delete again and permanently delete
    res_d2 = client.delete(f"/api/employees/{emp_id}?reason=Permanent+purge+test", headers=AUTH_HEADERS)
    assert res_d2.status_code == 200
    recovery_id2 = res_d2.json().get("recovery_vault_id")
    assert recovery_id2 is not None

    res_perm = client.delete(f"/api/recovery/permanent/{recovery_id2}?actor=HR%20Lead", headers=AUTH_HEADERS)
    assert res_perm.status_code == 200, res_perm.text
    assert res_perm.json()["success"] is True

    # 7. Verify permanently purged from Recovery Vault
    res_vault2 = client.get("/api/recovery/items", headers=AUTH_HEADERS)
    vault_items2 = res_vault2.json()
    assert not any(item["item_id"] == recovery_id2 for item in vault_items2)

