import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.employee_service import get_employee_service
from app.services.scoring_engine import get_unified_scoring_engine
from app.services.ats_service import get_ats_service
from app.services.career_preference_service import get_career_preference_service

def main():
    print("=== 1. VERIFYING 20 EMPLOYEES IN SQL DATABASE ===")
    svc = get_employee_service()
    res = svc.list_employees(limit=100)
    print(f"Total employees in database: {res['total_count']}")
    
    assert res['total_count'] >= 20, f"Expected at least 20 employees, got {res['total_count']}"
    
    # Check EMP-1001 through EMP-1020
    emp_ids = [e['employee_id'] for e in res['employees']]
    for i in range(1001, 1021):
        target_id = f"EMP-{i}"
        assert target_id in emp_ids, f"Missing seed employee {target_id}"
        emp_detail = svc.get_employee(target_id)
        assert emp_detail is not None, f"Could not fetch {target_id}"
        assert emp_detail.get('routine_work'), f"{target_id} has empty routine_work"
        assert emp_detail.get('resume_text'), f"{target_id} has empty resume_text"
        print(f"  [OK] {target_id}: {emp_detail['name']} | Dept: {emp_detail['department']} | Routine length: {len(emp_detail['routine_work'])} | Resume: {emp_detail['resume_filename']}")

    print("\n=== 2. VERIFYING 20 RESUME FILES ON DISK IN data/employee_resumes/ ===")
    resume_dir = Path("data/employee_resumes")
    assert resume_dir.exists(), "Directory data/employee_resumes/ does not exist!"
    resume_files = list(resume_dir.glob("*_Resume.txt"))
    print(f"Found {len(resume_files)} resume text files in {resume_dir.resolve()}:")
    for f in resume_files:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")
    assert len(resume_files) >= 20, f"Expected at least 20 resume files on disk, found {len(resume_files)}"

    print("\n=== 3. VERIFYING SCORING CONSISTENCY ACROSS MODULES ===")
    unified_engine = get_unified_scoring_engine()
    ats_svc = get_ats_service()
    career_svc = get_career_preference_service()

    # Use Priya Natarajan's resume for Senior AI/ML Engineer role
    priya_resume = svc.get_employee("EMP-1001")["resume_text"]
    
    # Unified engine score
    unified_result = unified_engine.evaluate_candidate(
        resume_text=priya_resume,
        target_role="Senior AI/ML Engineer",
        explicit_candidate_skills=svc.get_employee("EMP-1001")["skills"],
        experience_years=svc.get_employee("EMP-1001")["experience_years"],
    )
    print(f"Unified Scoring Engine score: {unified_result['overall_score']}%")

    # ATS evaluation
    ats_result = ats_svc.analyze(
        resume_text=priya_resume,
        target_role_key="ai_ml",
    )
    print(f"ATS Service overall score: {ats_result.overall_score}% (Fit category: {ats_result.score_grade})")

    # Career Preference Matcher evaluation
    from app.services.career_preference_service import CareerPreferenceRequest
    career_resp = career_svc.match_preferences(
        CareerPreferenceRequest(
            resume_text=priya_resume,
            preferred_locations=["bengaluru"],
            target_role="ai_ml",
        )
    )
    assert len(career_resp.matches) > 0, "Expected at least 1 match from CareerPreferenceService"
    # Check calibrated match for AI/ML opening
    ai_matches = [m for m in career_resp.matches if "ai" in m.title.lower() or "ml" in m.title.lower() or "machine learning" in m.title.lower() or m.domain in ["ai_ml", "genai"]]
    assert len(ai_matches) > 0, "Expected at least 1 AI/ML match from CareerPreferenceService"
    top_ai_match = ai_matches[0]
    print(f"Career Preference Matcher AI/ML match: {top_ai_match.company_name} - {top_ai_match.title}")
    print(f"   Composite: {top_ai_match.composite_score}% | Skill score: {top_ai_match.skill_score}%")

    # The scores should all be within a calibrated band (within <= 12 points)
    diff_ats = abs(ats_result.overall_score - unified_result['overall_score'])
    diff_career_skill = abs(top_ai_match.skill_score - unified_result['overall_score'])
    print(f"Difference ATS vs Unified: {diff_ats:.1f} pts")
    print(f"Difference Career Skill vs Unified: {diff_career_skill:.1f} pts")
    assert diff_ats <= 12.0, f"ATS score discrepancy too large: {diff_ats}"
    assert diff_career_skill <= 12.0, f"Career skill score discrepancy too large: {diff_career_skill}"

    print("\n[SUCCESS] All 20 employee seeds, disk resumes, routine work, and unified scoring verified!")

if __name__ == "__main__":
    main()
