"""
Employee Management API Router — Phase 25.

REST endpoints for adding, viewing, updating, and deleting internal company staff.
Strictly separated from job applicants and applicant screening runs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.rag.loader import DocumentLoader
from app.services.employee_service import get_employee_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/employees", tags=["Employee Management"])


# ── Request / Response Models ──────────────────────────────────────────────────

class EmployeeCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Employee full name")
    email: str = Field(..., description="Official employee email address")
    department: str = Field(..., min_length=2, max_length=128, description="Department name")
    designation: str = Field(..., min_length=2, max_length=128, description="Role / Job designation")
    joining_date: str = Field(..., description="Joining date in YYYY-MM-DD format")
    employee_id: Optional[str] = Field(None, description="Optional custom employee ID (e.g. EMP-1006). Auto-generated if omitted.")
    skills: Optional[List[str]] = Field(default_factory=list, description="List of technical/professional skills")
    experience_years: Optional[float] = Field(0.0, ge=0.0, le=50.0, description="Years of professional experience")
    resume_text: Optional[str] = Field(None, description="Optional plain-text resume or career background")
    routine_work: Optional[str] = Field(None, description="Daily routine responsibilities and regular tasks")
    status: Optional[str] = Field("ACTIVE", description="ACTIVE | ON_LEAVE | RESIGNED")
    phone: Optional[str] = Field(None, description="Contact phone number")
    location: Optional[str] = Field(None, description="Work location / Office branch")
    notes: Optional[str] = Field(None, description="Internal HR notes")
    actor: Optional[str] = Field("HR Administrator", description="HR user committing this addition")


class EmployeeUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    email: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    joining_date: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = Field(None, ge=0.0, le=50.0)
    routine_work: Optional[str] = Field(None, description="Updated daily routine responsibilities")
    resume_text: Optional[str] = Field(None, description="Updated resume plain text")
    status: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    actor: Optional[str] = Field("HR Administrator", description="HR user executing this edit")


class EmployeeDeleteRequest(BaseModel):
    reason: Optional[str] = Field("Administrative offboarding / record removal", description="HR reason for deletion")
    actor: Optional[str] = Field("HR Administrator", description="HR user authorizing deletion")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="List employee directory with search and filter options",
    status_code=status.HTTP_200_OK,
)
async def list_employees(
    search: Optional[str] = Query(None, description="Search by name, ID, email, or skills"),
    department: Optional[str] = Query(None, description="Filter by department"),
    designation: Optional[str] = Query(None, description="Filter by designation"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ON_LEAVE, RESIGNED)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Returns the company employee directory with real-time search,
    department filters, and high-level directory statistics.
    """
    svc = get_employee_service()
    return svc.list_employees(
        search=search,
        department=department,
        designation=designation,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/meta",
    summary="Get departments and designations metadata for filter dropdowns",
    status_code=status.HTTP_200_OK,
)
async def get_employee_metadata() -> Dict[str, Any]:
    """Returns list of unique departments and designations across the employee pool."""
    svc = get_employee_service()
    return svc.get_metadata()


@router.get(
    "/{emp_id}",
    summary="Get single employee complete profile",
    status_code=status.HTTP_200_OK,
)
async def get_employee(emp_id: str) -> Dict[str, Any]:
    """Returns the full employee profile matching the given employee ID or database ID."""
    svc = get_employee_service()
    emp = svc.get_employee(emp_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{emp_id}' not found.",
        )
    return {"status": "success", "employee": emp}


@router.post(
    "",
    summary="Add a new employee to the directory",
    status_code=status.HTTP_201_CREATED,
)
async def add_employee(payload: EmployeeCreateRequest) -> Dict[str, Any]:
    """
    Adds a new employee record.
    Enforces duplicate validation on Employee ID and Email.
    Preserves an audit log entry of the creation.
    """
    svc = get_employee_service()
    try:
        new_emp = svc.add_employee(
            name=payload.name,
            email=payload.email,
            department=payload.department,
            designation=payload.designation,
            joining_date=payload.joining_date,
            employee_id=payload.employee_id,
            skills=payload.skills,
            experience_years=payload.experience_years or 0.0,
            resume_text=payload.resume_text,
            routine_work=payload.routine_work,
            status=payload.status or "ACTIVE",
            phone=payload.phone,
            location=payload.location,
            notes=payload.notes,
            actor=payload.actor or "HR Administrator",
        )
        return {"status": "success", "message": "Employee added successfully.", "employee": new_emp}
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error adding employee: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add employee: {str(exc)}",
        )


@router.post(
    "/upload",
    summary="Add a new employee with multipart document resume upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_add_employee(
    name: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    designation: str = Form(...),
    joining_date: str = Form(...),
    employee_id: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),  # Comma-separated
    experience_years: Optional[float] = Form(0.0),
    status: Optional[str] = Form("ACTIVE"),
    phone: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    routine_work: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    actor: Optional[str] = Form("HR Administrator"),
    resume_file: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """
    Adds a new employee with an optional uploaded resume document (PDF, DOCX, TXT, MD).
    Parses document contents using DocumentLoader and extracts skills via NLP.
    """
    resume_text = ""
    resume_filename = None

    if resume_file and resume_file.filename:
        resume_filename = resume_file.filename
        try:
            content_bytes = await resume_file.read()
            loader = DocumentLoader()
            resume_text = loader.load_from_bytes(content_bytes, resume_file.filename)
        except Exception as file_err:
            logger.warning("Could not parse employee resume document: %s", file_err)
            resume_text = ""

    # Parse comma-separated skills
    skill_list = []
    if skills:
        skill_list = [s.strip() for s in skills.split(",") if s.strip()]

    svc = get_employee_service()
    try:
        new_emp = svc.add_employee(
            name=name,
            email=email,
            department=department,
            designation=designation,
            joining_date=joining_date,
            employee_id=employee_id,
            skills=skill_list,
            experience_years=experience_years or 0.0,
            resume_text=resume_text,
            resume_filename=resume_filename,
            routine_work=routine_work,
            status=status or "ACTIVE",
            phone=phone,
            location=location,
            notes=notes,
            actor=actor or "HR Administrator",
        )
        return {"status": "success", "message": "Employee added with resume successfully.", "employee": new_emp}
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error adding employee with resume: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add employee: {str(exc)}",
        )


@router.put(
    "/{emp_id}",
    summary="Edit and update employee details",
    status_code=status.HTTP_200_OK,
)
async def update_employee(emp_id: str, payload: EmployeeUpdateRequest) -> Dict[str, Any]:
    """
    Updates designation, department, skills, experience, or contact details of an employee.
    Records changes in the immutable audit trail.
    """
    svc = get_employee_service()
    update_dict = payload.model_dump(exclude_unset=True)
    actor = update_dict.pop("actor", "HR Administrator")

    try:
        updated = svc.update_employee(emp_id, update_dict, actor=actor)
        return {
            "status": "success",
            "message": f"Employee {updated['name']} ({updated['employee_id']}) updated successfully.",
            "employee": updated,
        }
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error updating employee: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update employee: {str(exc)}",
        )


@router.delete(
    "/{emp_id}",
    summary="Delete an employee record (Isolated from job applicants)",
    status_code=status.HTTP_200_OK,
)
async def delete_employee(
    emp_id: str,
    reason: Optional[str] = Query(None, description="Reason for deletion"),
    actor: Optional[str] = Query("HR Administrator", description="Authorizing HR user"),
) -> Dict[str, Any]:
    """
    Deletes an employee record from the database.
    Preserves an audit log entry documenting the deletion.
    Guarantees that job applicant records and resumes remain intact.
    """
    svc = get_employee_service()
    try:
        result = svc.delete_employee(emp_id, actor=actor, reason=reason)
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error deleting employee: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete employee: {str(exc)}",
        )


@router.get(
    "/{emp_id}/resume",
    summary="Get full resume text and routine scope for an employee",
    status_code=status.HTTP_200_OK,
)
async def get_employee_resume(emp_id: str) -> Dict[str, Any]:
    """
    Returns full resume text, file path on disk, and routine responsibilities for an employee.
    Stored under data/employee_resumes/ for HR analysis.
    """
    svc = get_employee_service()
    res = svc.get_employee_resume(emp_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{emp_id}' not found.",
        )
    return {"status": "success", "resume_info": res}


@router.get(
    "/{emp_id}/resume/download",
    summary="Download raw resume text file from disk",
    status_code=status.HTTP_200_OK,
)
async def download_employee_resume(emp_id: str):
    """
    Downloads the sample resume file stored in data/employee_resumes/.
    """
    svc = get_employee_service()
    res = svc.get_employee_resume(emp_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee '{emp_id}' not found.",
        )

    file_path = res.get("file_path")
    filename = res.get("resume_filename") or f"{emp_id}_Resume.txt"

    if file_path and os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/plain; charset=utf-8",
        )
    elif res.get("resume_text"):
        return PlainTextResponse(
            content=res["resume_text"],
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            media_type="text/plain; charset=utf-8",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No resume document available for employee '{emp_id}'.",
        )


# ── Assigned Work Ticket Slip Endpoints ───────────────────────────────────────

class WorkTicketRaiseRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Ticket title / deliverable name")
    description: str = Field(..., min_length=5, max_length=1000, description="Scope and acceptance criteria")
    priority: str = Field("HIGH", description="CRITICAL | HIGH | MEDIUM | LOW")
    status: str = Field("IN_PROGRESS", description="COMPLETED | IN_PROGRESS | PENDING")
    completion_percentage: int = Field(0, ge=0, le=100, description="Completion percentage 0-100")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")
    actor: Optional[str] = Field("HR Manager", description="Assigning manager / actor")


@router.get(
    "/{emp_id}/tickets",
    summary="List all assigned work tickets and slips for an employee",
    status_code=status.HTTP_200_OK,
)
async def get_employee_tickets(emp_id: str) -> Dict[str, Any]:
    """Returns the work tickets and deliverable slips assigned to an employee."""
    svc = get_employee_service()
    tickets = svc.list_employee_tickets(emp_id)
    return {
        "status": "success",
        "employee_id": emp_id,
        "total_tickets": len(tickets),
        "tickets": tickets,
    }


@router.post(
    "/{emp_id}/tickets",
    summary="Raise new assigned work ticket slip for an employee",
    status_code=status.HTTP_201_CREATED,
)
async def raise_employee_ticket(
    emp_id: str,
    payload: WorkTicketRaiseRequest,
) -> Dict[str, Any]:
    """Raises an assigned work ticket for an employee with status, completion %, and priority."""
    svc = get_employee_service()
    try:
        ticket = svc.raise_employee_ticket(
            emp_id_or_id=emp_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status=payload.status,
            completion_pct=payload.completion_percentage,
            due_date=payload.due_date,
            actor=payload.actor or "HR Manager",
        )
        return {
            "status": "success",
            "employee_id": emp_id,
            "message": f"Assigned work ticket #{ticket['ticket_id']} successfully raised for employee.",
            "ticket": ticket,
        }
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error raising work ticket: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to raise ticket: {str(exc)}",
        )

