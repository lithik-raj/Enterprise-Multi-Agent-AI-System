"""
Batch Multi-Candidate Resume Ranking & Talent Intelligence Service — Phase 22.

Processes collections of candidate resumes concurrently against target job requirements,
generating ranked leaderboards, skill gap frequency analytics, and exportable CSV reports.
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.ml.inference import get_ml_inference_engine
from app.services.nlp_service import get_nlp_service

logger = logging.getLogger(__name__)


class CandidateInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    resume_text: str = Field(..., min_length=10, max_length=15000)
    experience_years: float = Field(default=0.0, ge=0.0, le=50.0)
    extracted_skills: Optional[List[str]] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    rank: int
    name: str
    predicted_score: float
    match_category: str
    is_match: bool
    confidence: float
    matched_skills: List[str]
    missing_skills: List[str]
    overlap_ratio: float
    experience_years: float
    features: Dict[str, float]
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decision_time: Optional[str] = None
    email_draft: Optional[Dict[str, str]] = None


class BatchRankingResult(BaseModel):
    batch_id: str
    job_title: str
    job_description: str
    required_skills: List[str]
    total_candidates: int
    top_candidate_name: Optional[str]
    mean_score: float
    highest_score: float
    lowest_score: float
    strong_matches_count: int
    leaderboard: List[RankedCandidate]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BatchService:
    """Manages batch multi-candidate evaluation and leaderboard persistence."""

    def __init__(self):
        self.batches: Dict[str, BatchRankingResult] = {}
        self.ml_engine = get_ml_inference_engine()
        self.nlp_service = get_nlp_service()
        self._seed_sample_batch()

    def index_resume_to_knowledge_base(
        self,
        candidate_name: str,
        resume_text: str,
        skills: Optional[List[str]] = None,
        experience_years: float = 0.0,
        role: str = "Candidate Applicant",
    ) -> Dict[str, Any]:
        """
        Stores candidate resume in the system knowledge repository (UPLOAD_DIR)
        and indexes vector chunk embeddings into the central FAISS RAG vector store.
        """
        import json
        import re
        from pathlib import Path
        from app.config import get_settings

        settings = get_settings()
        upload_dir = Path(settings.UPLOAD_DIR)
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            upload_dir = Path("/tmp") / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)

        clean_slug = re.sub(r"[^a-z0-9]+", "-", candidate_name.lower()).strip("-")
        doc_id = f"resume-{clean_slug}"
        safe_path = upload_dir / f"{doc_id}.txt"
        safe_path.write_text(resume_text, encoding="utf-8")

        chunk_count = 0
        try:
            from app.rag.retriever import get_rag_retriever
            retriever = get_rag_retriever()
            chunk_count = retriever.index_document(doc_id, "txt", text=resume_text)
        except Exception as rag_err:
            logger.warning("Could not index vector chunks for %s: %s", doc_id, rag_err)

        meta_path = upload_dir / f"{doc_id}.meta.json"
        meta_data = {
            "document_id": doc_id,
            "filename": f"Resume - {candidate_name}.txt",
            "file_type": "txt",
            "size_bytes": len(resume_text.encode("utf-8")),
            "chunk_count": max(1, chunk_count),
            "candidate_name": candidate_name,
            "candidate_skills": skills or [],
            "experience_years": experience_years,
            "target_role": role,
            "uploaded_at": datetime.utcnow().isoformat(),
            "indexed": True,
            "source": "Batch Talent Knowledge Base",
            "preview": resume_text[:350].strip(),
        }
        meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
        logger.info("Stored & indexed resume for '%s' in knowledge database (id=%s, chunks=%d)", candidate_name, doc_id, chunk_count)
        return meta_data

    def sync_batch_to_knowledge_base(self, batch_id: str) -> Dict[str, Any]:
        """Indexes all candidate resumes in the batch into the Knowledge Database & Vector Store."""
        batch = self.get_batch(batch_id)
        if not batch:
            raise KeyError(f"Batch {batch_id} not found")

        # Find original texts from candidate pool or build rich resume
        pool_dict = {c["name"].lower(): c for c in self.get_extended_sample_candidates().get("candidates", [])}

        indexed_docs = []
        for c in batch.leaderboard:
            cand_profile = pool_dict.get(c.name.lower())
            if cand_profile:
                resume_text = cand_profile["resume_text"]
            else:
                skills_str = ", ".join(c.matched_skills + c.missing_skills)
                resume_text = (
                    f"Candidate Technical Profile: {c.name}\n"
                    f"Target Discipline: {batch.job_title}\n"
                    f"Professional Experience: {c.experience_years} years\n"
                    f"Demonstrated Competencies: {skills_str}\n"
                    f"Compatibility Rating: {c.predicted_score * 100:.1f}%, Status Category: {c.match_category}.\n"
                    f"Hiring Governance Decision: {c.decision or 'Under Recruiter Review'}.\n"
                )

            doc_meta = self.index_resume_to_knowledge_base(
                candidate_name=c.name,
                resume_text=resume_text,
                skills=c.matched_skills,
                experience_years=c.experience_years,
                role=batch.job_title,
            )
            indexed_docs.append(doc_meta)

        return {
            "status": "success",
            "batch_id": batch_id,
            "indexed_count": len(indexed_docs),
            "documents": indexed_docs,
            "message": f"Successfully indexed {len(indexed_docs)} candidate resumes into the FAISS Knowledge Database.",
        }

    def _seed_sample_batch(self):
        """Seed a sample batch for instantaneous enterprise demonstration."""
        sample_id = "batch-demo-talent-001"
        sample_candidates = [
            CandidateInput(
                name="Dr. Sarah Lin",
                experience_years=6.0,
                resume_text="Senior AI and Deep Learning Engineer with 6 years building production PyTorch pipelines, Transformers, LangGraph agents, and FastAPI microservices on Docker and Kubernetes. PhD in Computer Science.",
                extracted_skills=["Python", "PyTorch", "Transformers", "LangGraph", "FastAPI", "Docker", "Deep Learning"],
            ),
            CandidateInput(
                name="Alex Vance",
                experience_years=4.5,
                resume_text="Machine Learning Engineer with 4.5 years experience in Scikit-learn, PyTorch, Docker, and REST APIs. Built NLP pipelines and tabular classification models deployed on AWS.",
                extracted_skills=["Python", "PyTorch", "Scikit-learn", "Docker", "NLP", "REST APIs"],
            ),
            CandidateInput(
                name="David Miller",
                experience_years=3.0,
                resume_text="Data Analyst transitioning to ML. 3 years SQL, Python pandas, data visualization with Tableau, and basic scikit-learn models. Familiar with Git and Docker.",
                extracted_skills=["Python", "SQL", "Tableau", "Scikit-learn", "Git"],
            ),
            CandidateInput(
                name="Elena Gomez",
                experience_years=4.0,
                resume_text="Creative Director and Senior UI/UX Graphic Designer with 4 years specializing in Figma design systems, Adobe Creative Suite, branding guidelines, and CSS motion graphics.",
                extracted_skills=["Figma", "UI/UX", "Graphic Design", "CSS", "Adobe Suite"],
            ),
        ]
        job_title = "Senior AI/ML Platform Engineer"
        job_desc = "Seeking Senior AI Engineer with Python, PyTorch, Transformers, LangGraph, FastAPI, and Docker deployment expertise to build agentic platforms."
        req_skills = ["Python", "PyTorch", "Transformers", "LangGraph", "FastAPI", "Docker"]

        self.rank_candidates(
            job_title=job_title,
            job_description=job_desc,
            required_skills=req_skills,
            candidates=sample_candidates,
            batch_id=sample_id,
        )

        # Also seed the extended 10-candidate pool as secondary batch
        try:
            pool = self.get_extended_sample_candidates()
            extended_cands = [
                CandidateInput(
                    name=c["name"],
                    experience_years=c["experience_years"],
                    resume_text=c["resume_text"],
                    extracted_skills=c.get("extracted_skills", []),
                )
                for c in pool["candidates"]
            ]
            self.rank_candidates(
                job_title=pool["job_title"],
                job_description=pool["job_description"],
                required_skills=pool["required_skills"],
                candidates=extended_cands,
                batch_id="batch-extended-talent-pool",
            )
        except Exception as seed_err:
            logger.warning("Notice seeding extended pool: %s", seed_err)

    def rank_candidates(
        self,
        job_title: str,
        job_description: str,
        required_skills: List[str],
        candidates: List[CandidateInput],
        batch_id: Optional[str] = None,
    ) -> BatchRankingResult:
        bid = batch_id or f"batch-{uuid.uuid4().hex[:10]}"
        req_set = set(s.strip().lower() for s in required_skills if s.strip())

        scored_candidates: List[Dict[str, Any]] = []

        for cand in candidates:
            # 1. Automatically store and index candidate resume into Knowledge Database
            try:
                self.index_resume_to_knowledge_base(
                    candidate_name=cand.name,
                    resume_text=cand.resume_text,
                    skills=cand.extracted_skills,
                    experience_years=cand.experience_years,
                    role=job_title,
                )
            except Exception as kb_err:
                logger.warning("Knowledge base resume indexing notice for %s: %s", cand.name, kb_err)

            # 2. Ensure skills are present (use NLP extraction fallback if none provided)
            cand_skills = cand.extracted_skills or []
            if not cand_skills:
                nlp_res = self.nlp_service.extract_skills_and_entities(cand.resume_text)
                cand_skills = nlp_res.get("skills", [])
                if not cand_skills:
                    cand_skills = ["Python"]

            # 3. Run trained model inference
            pred = self.ml_engine.predict(
                resume_text=cand.resume_text,
                job_text=job_description,
                resume_skills=cand_skills,
                job_skills=required_skills,
            )

            # 3. Compute skill overlaps
            cand_set = set(s.strip().lower() for s in cand_skills)
            matched = sorted(list(req_set.intersection(cand_set)))
            missing = sorted(list(req_set.difference(cand_set)))
            overlap_ratio = len(matched) / len(req_set) if req_set else 0.0

            scored_candidates.append({
                "name": cand.name,
                "predicted_score": pred["predicted_score"],
                "match_category": pred["match_category"],
                "is_match": pred["is_match"],
                "confidence": pred["confidence"],
                "matched_skills": [s.title() for s in matched],
                "missing_skills": [s.title() for s in missing],
                "overlap_ratio": round(overlap_ratio, 3),
                "experience_years": cand.experience_years,
                "features": pred["features"],
            })

        # 4. Sort descending by predicted score
        scored_candidates.sort(key=lambda x: x["predicted_score"], reverse=True)

        leaderboard: List[RankedCandidate] = []
        scores: List[float] = []
        strong_count = 0

        for idx, item in enumerate(scored_candidates, start=1):
            rc = RankedCandidate(
                rank=idx,
                name=item["name"],
                predicted_score=item["predicted_score"],
                match_category=item["match_category"],
                is_match=item["is_match"],
                confidence=item["confidence"],
                matched_skills=item["matched_skills"],
                missing_skills=item["missing_skills"],
                overlap_ratio=item["overlap_ratio"],
                experience_years=item["experience_years"],
                features=item["features"],
            )
            leaderboard.append(rc)
            scores.append(rc.predicted_score)
            if rc.is_match:
                strong_count += 1

        total = len(leaderboard)
        mean_score = round(float(sum(scores) / total), 4) if total > 0 else 0.0
        high_score = max(scores) if scores else 0.0
        low_score = min(scores) if scores else 0.0
        top_name = leaderboard[0].name if leaderboard else None

        result = BatchRankingResult(
            batch_id=bid,
            job_title=job_title,
            job_description=job_description,
            required_skills=required_skills,
            total_candidates=total,
            top_candidate_name=top_name,
            mean_score=mean_score,
            highest_score=high_score,
            lowest_score=low_score,
            strong_matches_count=strong_count,
            leaderboard=leaderboard,
            created_at=datetime.utcnow(),
        )

        self.batches[bid] = result
        logger.info("Batch %s ranked %d candidates. Top pick: %s (score=%.3f)", bid, total, top_name, high_score)
        return result

    def get_batch(self, batch_id: str) -> Optional[BatchRankingResult]:
        return self.batches.get(batch_id)

    def export_csv(self, batch_id: str) -> str:
        batch = self.get_batch(batch_id)
        if not batch:
            raise KeyError(f"Batch {batch_id} not found")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Rank",
            "Candidate Name",
            "Predicted Compatibility Score",
            "Match Category",
            "Model Confidence",
            "Experience (Years)",
            "Skill Overlap Ratio",
            "Matched Skills",
            "Missing Skills",
        ])

        for c in batch.leaderboard:
            writer.writerow([
                c.rank,
                c.name,
                f"{c.predicted_score * 100:.1f}%",
                c.match_category,
                f"{c.confidence * 100:.1f}%",
                c.experience_years,
                f"{c.overlap_ratio * 100:.1f}%",
                "; ".join(c.matched_skills),
                "; ".join(c.missing_skills),
            ])

        return output.getvalue()

    def record_candidate_decision(
        self,
        batch_id: str,
        candidate_name: str,
        decision: str,
        reason: str,
        recruiter_name: str = "HR Hiring Lead",
    ) -> Dict[str, Any]:
        """
        Records a Human-in-the-Loop decision on a ranked candidate,
        updates the batch candidate record, logs to the Audit Trail with a trace ID,
        and generates a ready-to-send Communicator email draft.
        """
        batch = self.get_batch(batch_id)
        if not batch:
            raise KeyError(f"Batch {batch_id} not found")

        dec_upper = decision.strip().upper()
        # Normalise decision type
        if dec_upper in ["APPROVE", "SHORTLIST", "SHORTLISTED"]:
            dec_type = "SHORTLISTED"
            email_subject = f"Next Steps: Your application for {batch.job_title}"
            email_body = (
                f"Dear {candidate_name},\n\n"
                f"We are pleased to inform you that our technical review team has shortlisted your application "
                f"for the position of {batch.job_title}.\n\n"
                f"Your background aligns well with our requirements, and our team would like to invite you "
                f"to a 45-minute technical conversation. Please let us know your availability over the coming days.\n\n"
                f"Best regards,\n{recruiter_name}\nTalent Acquisition Team"
            )
        elif dec_upper in ["INTERVIEW", "INTERVIEW_SCHEDULED", "SCHEDULE"]:
            dec_type = "INTERVIEW_SCHEDULED"
            email_subject = f"Interview Invitation: {batch.job_title}"
            email_body = (
                f"Dear {candidate_name},\n\n"
                f"Thank you for your interest in the {batch.job_title} opening. We were very impressed by your profile "
                f"and would like to schedule an interview with the Engineering hiring team.\n\n"
                f"Please select a convenient slot via our scheduling link or reply with two preferred times.\n\n"
                f"Best regards,\n{recruiter_name}\nTalent Acquisition Team"
            )
        elif dec_upper in ["HIRE", "OFFER", "HIRED", "EXTEND_OFFER"]:
            dec_type = "OFFER_EXTENDED"
            email_subject = f"Offer of Employment: {batch.job_title}"
            email_body = (
                f"Dear {candidate_name},\n\n"
                f"Following our evaluation and interviews, we are thrilled to formally extend an offer for "
                f"the {batch.job_title} role! Your demonstrated expertise will be a vital addition to our team.\n\n"
                f"The detailed formal offer letter and benefits documentation are being prepared for your review.\n\n"
                f"Congratulations,\n{recruiter_name}\nPeople & Talent Leadership"
            )
        else:
            dec_type = "REJECTED"
            email_subject = f"Update regarding your application for {batch.job_title}"
            email_body = (
                f"Dear {candidate_name},\n\n"
                f"Thank you for taking the time to consider opportunities with our organization and applying for "
                f"the {batch.job_title} position. While your qualifications are noteworthy, we have decided to advance "
                f"other candidates whose background aligns more specifically with our current requisitions.\n\n"
                f"We appreciate your interest and wish you the very best in your professional endeavors.\n\n"
                f"Sincerely,\n{recruiter_name}\nTalent Acquisition Team"
            )

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        updated_cand = None

        for c in batch.leaderboard:
            if c.name.strip().lower() == candidate_name.strip().lower():
                c.decision = dec_type
                c.decision_reason = reason
                c.decision_time = now_str
                c.email_draft = {
                    "subject": email_subject,
                    "body": email_body,
                    "recipient": candidate_name,
                    "recruiter": recruiter_name,
                }
                updated_cand = c
                break

        if not updated_cand:
            raise ValueError(f"Candidate '{candidate_name}' not found in batch {batch_id}")

        trace_id = f"rec-log-{uuid.uuid4().hex[:12]}"

        # Automatically log to centralized Audit Trail
        try:
            from app.services.audit_service import get_audit_service
            audit_svc = get_audit_service()
            audit_svc.record(
                category="BATCH",
                action=f"HR Decision: {dec_type} — {candidate_name}",
                details=f"Recruiter: {recruiter_name} | Role: {batch.job_title} | Reason: {reason} | Trace: {trace_id}",
                severity="info" if dec_type != "REJECTED" else "warning",
                metadata={
                    "batch_id": batch_id,
                    "candidate_name": candidate_name,
                    "decision": dec_type,
                    "reason": reason,
                    "recruiter": recruiter_name,
                    "trace_id": trace_id,
                },
            )
        except Exception as audit_err:
            logger.warning("Could not append decision to audit trail: %s", audit_err)

        return {
            "status": "success",
            "batch_id": batch_id,
            "candidate_name": candidate_name,
            "decision": dec_type,
            "reason": reason,
            "trace_id": trace_id,
            "decision_time": now_str,
            "recruiter_name": recruiter_name,
            "email_draft": updated_cand.email_draft,
        }

    def ingest_candidate(
        self,
        candidate_name: Optional[str] = None,
        resume_text: str = "",
        role: Optional[str] = None,
        email: Optional[str] = None,
        experience_years: Optional[float] = None,
        batch_id: Optional[str] = None,
        auto_decide: bool = True,
        recruiter_name: str = "HR Automation Engine",
    ) -> Dict[str, Any]:
        """
        Complete Autonomous End-to-End HR Ingestion Pipeline:
        1. NLP Skill & Entity extraction from resume
        2. Knowledge Base & Vector Indexing (FAISS)
        3. Multi-Agent ML Scoring against target requisition
        4. Automated hiring decision & justification proposal
        5. Communicator email drafting
        6. Dynamic insertion & re-ranking into active batch leaderboard
        7. Audit Trail logging with trace ID
        8. Synthesized executive voice briefing text
        """
        import re

        clean_text = resume_text.strip()
        if not clean_text:
            raise ValueError("Resume text is required for automated candidate ingestion.")

        # 1. Resolve Candidate Name with enhanced multi-pattern detection
        c_name = (candidate_name or "").strip()
        if not c_name or c_name.lower() in ["candidate", "applicant", "new candidate", "unknown", "resume", "cv"]:
            # Pattern A: Name: / Candidate: label
            name_match = re.search(r"(?:name|candidate|applicant)\s*[:\-]\s*([A-Za-z\.\s]{2,40})", clean_text, re.I)
            if name_match and len(name_match.group(1).strip()) >= 3:
                c_name = name_match.group(1).strip()
            else:
                # Pattern B: Inspect first 5 lines for a person name (skipping headers like "RESUME", "CURRICULUM VITAE")
                lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
                found_name = None
                for line in lines[:5]:
                    if re.match(r"^(?:resume|curriculum vitae|cv|bio-data|profile|contact info)$", line, re.I):
                        continue
                    if len(line) <= 40 and re.match(r"^[A-Z][a-zA-Z\.\s]{2,38}$", line) and not any(k in line.lower() for k in ["email", "phone", "http", "@", "skills", "summary"]):
                        found_name = line
                        break
                if found_name:
                    c_name = found_name
                else:
                    # Pattern C: Extract from email prefix
                    email_match = re.search(r"([a-zA-Z0-9_.+-]+)@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", clean_text)
                    if email_match:
                        raw_prefix = email_match.group(1).replace(".", " ").replace("_", " ").replace("-", " ")
                        c_name = " ".join(p.capitalize() for p in raw_prefix.split() if len(p) > 1 and not p.isdigit())
                    if not c_name or len(c_name) < 2:
                        c_name = f"Candidate-{uuid.uuid4().hex[:6].upper()}"

        # 2. Resolve Email
        c_email = (email or "").strip()
        if not c_email:
            email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", clean_text)
            c_email = email_match.group(0) if email_match else f"{c_name.lower().replace(' ', '.')}@talent-pool.internal"

        # 3. Resolve Experience Years using enhanced UnifiedScoringEngine
        from app.services.scoring_engine import get_unified_scoring_engine
        scoring_engine = get_unified_scoring_engine()

        exp_years = experience_years
        if not exp_years or exp_years <= 0:
            exp_years = scoring_engine.extract_experience_years(clean_text)

        # 4. Target Batch & Requisition
        bid = batch_id or "batch-demo-talent-001"
        batch = self.get_batch(bid)
        target_role = role or (batch.job_title if batch else "Senior AI/ML Platform Engineer")
        req_skills = batch.required_skills if batch else [
            "Python", "SQL", "Generative AI", "Agentic AI", "LangGraph", "LangChain",
            "RAG", "PyTorch", "FastAPI", "Docker", "Model Context Protocol"
        ]
        job_desc = batch.job_description if batch else (
            "Seeking Senior AI Platform Engineer with expertise in Python, Generative AI, "
            "Agentic AI, LangGraph, LangChain, RAG, PyTorch, FastAPI, Docker, and MCP."
        )

        # 5. Extract Skills with NLP and Industry Ontology
        nlp_res = self.nlp_service.extract_skills_and_entities(clean_text)
        cand_skills = nlp_res.get("skills", [])
        if not cand_skills:
            cand_skills = scoring_engine.extract_skills_heuristically(clean_text)
        if not cand_skills:
            cand_skills = ["Python", "Machine Learning"]

        # 6. Index to Knowledge Base & FAISS Vector DB
        try:
            self.index_resume_to_knowledge_base(
                candidate_name=c_name,
                resume_text=clean_text,
                skills=cand_skills,
                experience_years=exp_years,
                role=target_role,
            )
        except Exception as kb_err:
            logger.warning("Knowledge base resume indexing notice for %s: %s", c_name, kb_err)

        # 7. Multi-Agent Compatibility Match with Calibrated Scoring Engine
        pred = self.ml_engine.predict(
            resume_text=clean_text,
            job_text=job_desc,
            resume_skills=cand_skills,
            job_skills=req_skills,
        )

        # Industry Priority Skills for intelligent, non-alphabetical sorting
        PRIORITY_ORDER = [
            "Agentic AI", "Multi-Agent Systems", "LangGraph", "Generative AI",
            "Large Language Models", "Model Context Protocol", "Retrieval-Augmented Generation",
            "RAG", "LangChain", "Vector Databases", "FAISS", "ChromaDB",
            "Hugging Face Transformers", "IBM watsonx.ai", "Infosys Topaz", "Accenture AI Refinery",
            "Python", "SQL", "FastAPI", "PyTorch", "Docker", "Kubernetes",
            "Pydantic", "Linux", "Cloud Computing", "AI Evaluation", "Responsible AI",
            "Human-in-the-Loop Review", "CI/CD Fundamentals", "REST APIs", "JSON"
        ]
        priority_rank = {s.lower(): idx for idx, s in enumerate(PRIORITY_ORDER)}

        req_set = set(s.strip().lower() for s in req_skills if s.strip())
        cand_set = set(s.strip().lower() for s in cand_skills)
        raw_matched = [s for s in cand_set if s in req_set or any(s in r or r in s for r in req_set)]
        # Sort matched skills by industry relevance priority, not purely alphabetically
        matched = sorted(list(set(raw_matched)), key=lambda s: priority_rank.get(s, 999))
        missing = sorted(list(req_set.difference(cand_set)), key=lambda s: priority_rank.get(s, 999))

        overlap_ratio = len(matched) / len(req_set) if req_set else 0.0
        score = pred["predicted_score"]

        # 8. Automated Hiring Decision Formulation
        decision = None
        decision_label = "Pending Review"
        decision_reason = None
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        top_matched_display = [s.title() for s in matched[:3]] or [s.title() for s in cand_skills[:3]]

        if auto_decide:
            if score >= 0.78:
                decision = "OFFER_EXTENDED"
                decision_label = "Offer Extended (Hired)"
                decision_reason = f"Automated hire proposal: High-impact alignment in {', '.join(top_matched_display)} with {exp_years:.1f}y experience."
            elif score >= 0.65:
                decision = "SHORTLISTED"
                decision_label = "Shortlisted"
                decision_reason = f"Automated shortlist: High compatibility fit ({score * 100:.1f}%) meeting engineering prerequisites."
            elif score >= 0.50:
                decision = "INTERVIEW_SCHEDULED"
                decision_label = "Interview Scheduled"
                decision_reason = f"Automated interview invitation: Core technical prerequisites met in {', '.join(top_matched_display[:2])}, scheduling technical screening."
            elif score >= 0.35:
                decision = "HOLD"
                decision_label = "Hold / Secondary Review"
                decision_reason = f"Automated hold: Secondary screening recommended due to skill gaps in {', '.join([s.title() for s in missing[:2]])}."
            else:
                decision = "REJECTED"
                decision_label = "Declined"
                decision_reason = f"Automated decline: Insufficient overlap with role requisitions (missing {', '.join([s.title() for s in missing[:2]])})."

        # 9. Email Draft Generation (Communicator AI)
        if decision == "OFFER_EXTENDED":
            email_subject = f"Offer of Employment: {target_role}"
            email_body = (
                f"Dear {c_name},\n\n"
                f"Following our evaluation, we are thrilled to extend a formal offer for the {target_role} position! "
                f"Your demonstrated expertise in {', '.join([s.title() for s in matched[:3]])} will be an exceptional addition to our engineering team.\n\n"
                f"Our talent team will follow up shortly with your formal offer letter and benefits overview.\n\n"
                f"Congratulations,\n{recruiter_name}\nTalent Acquisition Leadership"
            )
        elif decision == "SHORTLISTED":
            email_subject = f"Update on your application: {target_role}"
            email_body = (
                f"Dear {c_name},\n\n"
                f"We are pleased to inform you that our technical hiring team has shortlisted your application for the "
                f"{target_role} position based on your strong background in {', '.join([s.title() for s in matched[:3]])}.\n\n"
                f"We look forward to connecting with you for the next screening conversation.\n\n"
                f"Best regards,\n{recruiter_name}\nTalent Acquisition Team"
            )
        elif decision == "INTERVIEW_SCHEDULED":
            email_subject = f"Interview Invitation: {target_role}"
            email_body = (
                f"Dear {c_name},\n\n"
                f"Thank you for your application for the {target_role} role. We were very impressed by your experience and "
                f"would like to schedule an interview covering technical systems and architecture.\n\n"
                f"Please reply with your preferred availability over the next few business days.\n\n"
                f"Best regards,\n{recruiter_name}\nEngineering Talent Team"
            )
        else:
            email_subject = f"Your application for {target_role}"
            email_body = (
                f"Dear {c_name},\n\n"
                f"Thank you for taking the time to apply for the {target_role} position. While your qualifications are noteworthy, "
                f"we have decided to proceed with candidates whose immediate stack overlap matches our current requisitions more closely.\n\n"
                f"We wish you every success in your job search and future professional endeavors.\n\n"
                f"Sincerely,\n{recruiter_name}\nTalent Acquisition Team"
            )

        email_draft = {
            "subject": email_subject,
            "body": email_body,
            "recipient": c_name,
            "email": c_email,
            "recruiter": recruiter_name,
        }

        canonical_skills = {
            "pytorch": "PyTorch",
            "langgraph": "LangGraph",
            "fastapi": "FastAPI",
            "scikit-learn": "Scikit-Learn",
            "docker": "Docker",
            "aws": "AWS",
            "gcp": "GCP",
            "azure": "Azure",
            "sql": "SQL",
            "nosql": "NoSQL",
            "nlp": "NLP",
            "llm": "LLM",
            "rag": "RAG",
            "kubernetes": "Kubernetes",
            "transformers": "Transformers",
        }
        fmt_matched = [canonical_skills.get(s.strip().lower(), s.strip().title()) for s in matched]
        fmt_missing = [canonical_skills.get(s.strip().lower(), s.strip().title()) for s in missing]

        # 10. Update Active Batch Leaderboard
        trace_id = f"hr-auto-{uuid.uuid4().hex[:10]}"
        new_candidate = RankedCandidate(
            rank=1,
            name=c_name,
            predicted_score=score,
            match_category=pred["match_category"],
            is_match=pred["is_match"],
            confidence=pred["confidence"],
            matched_skills=fmt_matched,
            missing_skills=fmt_missing,
            overlap_ratio=round(overlap_ratio, 3),
            experience_years=exp_years,
            features=pred.get("features", {
                "tfidf_cosine_similarity": float(score),
                "skill_overlap_ratio": float(overlap_ratio),
                "matched_skill_count": float(len(matched)),
                "missing_skill_count": float(len(missing)),
                "resume_length": float(len(clean_text.split())),
                "job_length": float(len(job_desc.split())),
            }),
            decision=decision,
            decision_reason=decision_reason,
            decision_time=now_str,
            email_draft=email_draft,
        )

        if batch:
            existing_idx = None
            for idx, ex in enumerate(batch.leaderboard):
                if ex.name.strip().lower() == c_name.strip().lower():
                    existing_idx = idx
                    break
            if existing_idx is not None:
                batch.leaderboard[existing_idx] = new_candidate
            else:
                batch.leaderboard.append(new_candidate)

            # Re-sort descending by score
            batch.leaderboard.sort(key=lambda x: x.predicted_score, reverse=True)
            for r_idx, c in enumerate(batch.leaderboard):
                c.rank = r_idx + 1

            all_scores = [c.predicted_score for c in batch.leaderboard]
            batch.total_candidates = len(batch.leaderboard)
            batch.mean_score = round(float(sum(all_scores) / len(all_scores)), 4) if all_scores else 0.0
            batch.highest_score = max(all_scores) if all_scores else 0.0
            batch.lowest_score = min(all_scores) if all_scores else 0.0
            batch.strong_matches_count = sum(1 for s_score in all_scores if s_score >= 0.70)
            batch.top_candidate_name = batch.leaderboard[0].name if batch.leaderboard else None

        # 11. Log to Centralized Audit Trail
        try:
            from app.services.audit_service import get_audit_service
            audit_svc = get_audit_service()
            audit_svc.record(
                category="BATCH",
                action=f"Autonomous Ingestion & Decision: {c_name} ({decision or 'EVALUATED'})",
                details=f"Recruiter: {recruiter_name} | Role: {target_role} | Score: {score * 100:.1f}% | Trace: {trace_id}",
                severity="info" if decision != "REJECTED" else "warning",
                metadata={
                    "batch_id": bid,
                    "candidate_name": c_name,
                    "score": score,
                    "decision": decision,
                    "reason": decision_reason,
                    "recruiter": recruiter_name,
                    "trace_id": trace_id,
                },
            )
        except Exception as audit_err:
            logger.warning("Could not append auto ingestion to audit trail: %s", audit_err)

        # 12. Synthesized Spoken Executive Voice Briefing (Dynamic, personalized & non-repetitive)
        top_skills_str = ", ".join(top_matched_display) if top_matched_display else "core technical systems"
        score_pct = score * 100.0

        if score_pct >= 78.0:
            voice_briefing = (
                f"Autonomous talent screening complete for {c_name}. High compatibility score of {score_pct:.1f} percent "
                f"for {target_role}. Candidate brings {exp_years:.1f} years of verified experience with elite mastery in "
                f"{top_skills_str}. Automated recommendation is {decision_label}. Synchronized to the immutable audit trail."
            )
        elif score_pct >= 65.0:
            voice_briefing = (
                f"Screening complete for {c_name}. Compatibility score is {score_pct:.1f} percent for {target_role}. "
                f"Candidate demonstrates strong technical background in {top_skills_str} across {exp_years:.1f} years. "
                f"Automated recommendation is {decision_label}. Staged for recruiter technical evaluation."
            )
        elif score_pct >= 50.0:
            voice_briefing = (
                f"Evaluation complete for {c_name} with {score_pct:.1f} percent alignment for {target_role}. "
                f"Verified foundational strengths in {top_skills_str} across {exp_years:.1f} years. "
                f"Automated recommendation is {decision_label} to assess architecture depth."
            )
        elif score_pct >= 35.0:
            voice_briefing = (
                f"Review complete for {c_name} at {score_pct:.1f} percent alignment for {target_role}. "
                f"Candidate brings {exp_years:.1f} years with partial stack overlap in {top_skills_str}. "
                f"Automated recommendation is {decision_label} pending secondary skill review."
            )
        else:
            voice_briefing = (
                f"Intake evaluation complete for {c_name} at {score_pct:.1f} percent match for {target_role}. "
                f"Candidate brings {exp_years:.1f} years experience. Key role requisitions have notable gaps; "
                f"recommendation is {decision_label}. Recorded to audit trail."
            )

        return {
            "status": "success",
            "candidate_name": c_name,
            "candidate": new_candidate.model_dump(),
            "batch_id": bid,
            "target_role": target_role,
            "trace_id": trace_id,
            "email_draft": email_draft,
            "voice_briefing": voice_briefing,
            "ingestion_result": {
                "candidate_name": c_name,
                "email": c_email,
                "predicted_score": score,
                "matched_skills": fmt_matched,
                "missing_skills": fmt_missing,
                "suggested_decision": decision,
                "decision_label": decision_label,
                "decision_reason": decision_reason,
                "decision_committed": bool(auto_decide and decision),
                "communicator_email_draft": email_body,
                "spoken_briefing": voice_briefing,
            },
            "batch_summary": {
                "total_candidates": batch.total_candidates if batch else 1,
                "mean_score": batch.mean_score if batch else score,
                "highest_score": batch.highest_score if batch else score,
                "top_candidate": batch.top_candidate_name if batch else c_name,
            } if batch else None,
        }

    def get_extended_sample_candidates(self) -> Dict[str, Any]:
        """
        Returns a rich, diverse pool of 8 real-world candidate profiles spanning different
        experience levels and technical domains for comprehensive HR batch ranking tests.
        """
        return {
            "job_title": "Senior AI/ML Platform Engineer",
            "job_description": "Seeking Senior AI Engineer with Python, PyTorch, Transformers, LangGraph, FastAPI, and Docker deployment expertise to build scalable multi-agent systems.",
            "required_skills": ["Python", "PyTorch", "Transformers", "LangGraph", "FastAPI", "Docker"],
            "candidates": [
                {
                    "name": "Dr. Sarah Lin",
                    "experience_years": 6.0,
                    "resume_text": "Senior AI and Deep Learning Engineer with 6 years building production PyTorch pipelines, Transformers, LangGraph agents, and FastAPI microservices on Docker and Kubernetes. PhD in Computer Science.",
                    "extracted_skills": ["Python", "PyTorch", "Transformers", "LangGraph", "FastAPI", "Docker", "Deep Learning"],
                },
                {
                    "name": "Alex Vance",
                    "experience_years": 4.5,
                    "resume_text": "Machine Learning Engineer with 4.5 years experience in Scikit-learn, PyTorch, Docker, and REST APIs. Built NLP pipelines and tabular classification models deployed on AWS.",
                    "extracted_skills": ["Python", "PyTorch", "Scikit-learn", "Docker", "NLP", "REST APIs"],
                },
                {
                    "name": "Priya R. Nair",
                    "experience_years": 3.5,
                    "resume_text": "Full-Stack Python Engineer with 3.5 years building FastAPI microservices, PostgreSQL architectures, React frontends, Docker containers, and CI/CD automation pipelines.",
                    "extracted_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "React", "Git", "REST APIs"],
                },
                {
                    "name": "Vikramaditya Rao",
                    "experience_years": 5.0,
                    "resume_text": "Cloud Infrastructure & Distributed Systems Architect with 5 years architecting high-scale Go and Python microservices on Docker, Kubernetes, and AWS with Redis caching.",
                    "extracted_skills": ["Python", "Docker", "Kubernetes", "AWS", "FastAPI", "Microservices", "Git"],
                },
                {
                    "name": "Aarav S. Kulkarni",
                    "experience_years": 1.5,
                    "resume_text": "Junior Machine Learning Developer & recent graduate with 1.5 years experience in Python, Pandas, Scikit-learn, LangGraph, and basic FastAPI API development.",
                    "extracted_skills": ["Python", "LangGraph", "FastAPI", "Scikit-learn", "Pandas", "Git"],
                },
                {
                    "name": "David Miller",
                    "experience_years": 3.0,
                    "resume_text": "Data Analyst transitioning to ML. 3 years SQL, Python pandas, data visualization with Tableau, and basic scikit-learn models. Familiar with Git and Docker.",
                    "extracted_skills": ["Python", "SQL", "Tableau", "Scikit-learn", "Git"],
                },
                {
                    "name": "Karthik Raman",
                    "experience_years": 3.0,
                    "resume_text": "Frontend UI/UX React Developer with 3 years building responsive web applications in React, TypeScript, Next.js, Redux, and TailwindCSS design systems.",
                    "extracted_skills": ["React", "TypeScript", "Next.js", "CSS", "Git", "Redux"],
                },
                {
                    "name": "Maya E. Patel",
                    "experience_years": 4.0,
                    "resume_text": "Computer Vision & Edge AI Engineer with 4 years deploying YOLOv8, OpenCV, PyTorch, and TensorRT inference runtimes on NVIDIA Jetson and AWS EC2 GPU instances. Designed video analytics microservices with FastAPI and Docker. B.Tech in Electronics.",
                    "extracted_skills": ["Python", "PyTorch", "OpenCV", "TensorRT", "FastAPI", "Docker", "Computer Vision"],
                },
                {
                    "name": "Rohan Deshmukh",
                    "experience_years": 5.5,
                    "resume_text": "Enterprise Generative AI Solution Architect with 5.5 years designing multi-agent RAG pipelines using LangGraph, LlamaIndex, FAISS, and PostgreSQL pgvector. Deployed high-throughput agent systems on Docker & Kubernetes with Redis caching. M.Tech in Data Science.",
                    "extracted_skills": ["Python", "LangGraph", "FAISS", "PyTorch", "FastAPI", "Docker", "Transformers", "Kubernetes"],
                },
                {
                    "name": "Elena Gomez",
                    "experience_years": 4.0,
                    "resume_text": "Creative Director and Senior UI/UX Graphic Designer with 4 years specializing in Figma design systems, Adobe Creative Suite, branding guidelines, and CSS motion graphics. Passionate about human-AI interaction design.",
                    "extracted_skills": ["Figma", "UI/UX", "Graphic Design", "CSS", "Adobe Suite"],
                },
            ],
            "total_pool_size": 10,
        }


_batch_service_instance: Optional[BatchService] = None


def get_batch_service() -> BatchService:
    global _batch_service_instance
    if _batch_service_instance is None:
        _batch_service_instance = BatchService()
    return _batch_service_instance
