"""
agents/communicator_agent.py

Communicator Agent: Generates tailored candidate communication drafts.
Strict Human-in-the-Loop rule:
  - Drafts candidate emails (interview invitations, polite status updates, polite rejections)
  - NEVER sends emails automatically. Every draft requires explicit recruiter review and click-to-send.
"""

from __future__ import annotations

import logging
from typing import Optional
from pydantic import BaseModel, Field

from app.agents.extractor_agent import ExtractedCandidateProfile
from app.agents.explainer_agent import MatchExplanation

logger = logging.getLogger(__name__)


class EmailDraft(BaseModel):
    """Pydantic-validated output of the Communicator Agent."""
    recipient_email: str = Field(..., description="Candidate contact email")
    recipient_name: str = Field(..., description="Candidate name")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Formatted email content")
    action_type: str = Field(..., description="'interview_invitation', 'polite_rejection', 'keep_on_file'")
    auto_send_blocked: bool = Field(True, description="Strict safety constraint: automated sending is permanently blocked")
    requires_human_approval: bool = Field(True, description="Human recruiter approval strictly required before dispatch")


class CommunicatorAgent:
    """Specialist agent drafting candidate communications following human recruiter decisions."""

    def draft_communication(
        self,
        candidate_profile: ExtractedCandidateProfile,
        job_title: str,
        company_name: str,
        decision: str,  # 'approve', 'reject', 'hold'
        explanation: Optional[MatchExplanation] = None,
        recruiter_note: Optional[str] = None,
    ) -> EmailDraft:
        """
        Synthesizes candidate profile, decision, and explanation into an email draft.
        """
        name = candidate_profile.name or "Candidate"
        email = candidate_profile.email or "candidate@example.com"
        decision_clean = decision.lower().strip()

        if decision_clean in ["approve", "interview"]:
            subject = f"Interview Invitation: {job_title} at {company_name}"
            body = (
                f"Dear {name},\n\n"
                f"Thank you for applying to the {job_title} position at {company_name}.\n\n"
                f"We were very impressed by your background and qualifications, particularly your expertise in "
                f"{', '.join(candidate_profile.skills[:3]) if candidate_profile.skills else 'software engineering'}. "
                f"We would love to invite you to an introductory interview with our hiring team to discuss the role.\n\n"
                f"Please reply with your availability over the next few business days.\n\n"
                f"Best regards,\n"
                f"The Talent Acquisition Team\n"
                f"{company_name}"
            )
            action = "interview_invitation"

        elif decision_clean in ["reject", "decline"]:
            subject = f"Update regarding your application for {job_title} at {company_name}"
            body = (
                f"Dear {name},\n\n"
                f"Thank you for taking the time to consider {company_name} and applying for the {job_title} role.\n\n"
                f"After careful review of your qualifications, we have decided to proceed with other candidates whose experience "
                f"more closely aligns with our specific technical requirements at this time.\n\n"
                f"We genuinely appreciate your interest and wish you every success in your professional journey.\n\n"
                f"Sincerely,\n"
                f"The Talent Acquisition Team\n"
                f"{company_name}"
            )
            action = "polite_rejection"

        else:  # 'hold'
            subject = f"Application Status: {job_title} at {company_name}"
            body = (
                f"Dear {name},\n\n"
                f"Thank you for applying for the {job_title} role at {company_name}.\n\n"
                f"Our team is currently reviewing applicant pools for this opening and will keep your profile active for upcoming review cycles.\n\n"
                f"We will update you as soon as next steps are determined.\n\n"
                f"Best regards,\n"
                f"The Talent Acquisition Team\n"
                f"{company_name}"
            )
            action = "keep_on_file"

        return EmailDraft(
            recipient_email=email,
            recipient_name=name,
            subject=subject,
            body=body,
            action_type=action,
            auto_send_blocked=True,
            requires_human_approval=True,
        )
