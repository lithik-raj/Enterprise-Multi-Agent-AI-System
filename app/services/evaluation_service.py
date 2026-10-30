"""
Evaluation Service.

Scores agent outputs across three dimensions:
  - Relevance:     Does the answer address the original task?
  - Completeness:  Does the answer cover all parts of the task?
  - Groundedness:  Is the answer grounded in provided context (not hallucinated)?

Two scoring modes:
  1. LLM-based scoring  — sends eval prompt to the LLM (accurate, slower)
  2. Heuristic scoring  — lightweight fallback using keyword overlap (fast, no API cost)
"""
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class EvaluationResult:
    def __init__(
        self,
        relevance: float,
        completeness: float,
        groundedness: float,
        task_completed: bool,
        issues: list,
        raw_feedback: str = ""
    ):
        self.relevance = relevance
        self.completeness = completeness
        self.groundedness = groundedness
        self.task_completed = task_completed
        self.issues = issues
        self.raw_feedback = raw_feedback

    @property
    def overall_score(self) -> float:
        return round((self.relevance + self.completeness + self.groundedness) / 3, 4)

    def to_dict(self) -> dict:
        return {
            "relevance": self.relevance,
            "completeness": self.completeness,
            "groundedness": self.groundedness,
            "overall_score": self.overall_score,
            "task_completed": self.task_completed,
            "issues": self.issues,
        }


class EvaluationService:
    """Scores agent outputs using LLM or lightweight heuristics."""

    def __init__(self, llm_service=None):
        self._llm = llm_service

    # ── LLM-based scoring ────────────────────────────────────────────────────

    def evaluate_with_llm(
        self,
        task: str,
        answer: str,
        context: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Ask the LLM to evaluate `answer` against `task` and optional `context`.
        Returns structured scores parsed from the LLM's JSON response.
        """
        from app.services.prompt_templates import get_template
        
        if self._llm is None:
            raise RuntimeError("LLM service not configured for EvaluationService")

        ctx_block = f"\nContext:\n{context}" if context else ""
        prompt = (
            f"Original Task:\n{task}"
            f"{ctx_block}"
            f"\n\nAnswer to evaluate:\n{answer}"
        )

        try:
            system_prompt = get_template("evaluation_agent")
            response = self._llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.0)
            raw = response.content
            return self._parse_llm_response(raw)
        except Exception as e:
            logger.error("LLM evaluation failed: %s", e)
            return self._heuristic_evaluate(task, answer, context)

    def _parse_llm_response(self, raw: str) -> EvaluationResult:
        """Try to extract JSON scores from the LLM response."""
        # Find first JSON block in the response
        json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return EvaluationResult(
                    relevance=float(data.get("relevance", 0.5)),
                    completeness=float(data.get("completeness", 0.5)),
                    groundedness=float(data.get("groundedness", 0.5)),
                    task_completed=bool(data.get("task_completed", False)),
                    issues=data.get("issues", []),
                    raw_feedback=raw,
                )
            except (json.JSONDecodeError, ValueError):
                pass
        # Fallback: return a mid-range score with the raw response as feedback
        return EvaluationResult(
            relevance=0.5,
            completeness=0.5,
            groundedness=0.5,
            task_completed=False,
            issues=["Could not parse structured evaluation from LLM response"],
            raw_feedback=raw,
        )

    # ── Heuristic scoring ─────────────────────────────────────────────────────

    def _heuristic_evaluate(
        self,
        task: str,
        answer: str,
        context: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Lightweight evaluation without LLM.
        Uses token overlap as a proxy for relevance/groundedness.
        """
        task_tokens = set(task.lower().split())
        answer_tokens = set(answer.lower().split())

        # Relevance: overlap between task and answer
        if task_tokens:
            relevance = len(task_tokens & answer_tokens) / len(task_tokens)
        else:
            relevance = 0.0

        # Completeness: penalty for very short answers
        words = len(answer.split())
        completeness = min(1.0, words / 50)   # 50 words = fully complete

        # Groundedness: how much of the answer appears in context
        if context:
            ctx_tokens = set(context.lower().split())
            if answer_tokens:
                groundedness = len(answer_tokens & ctx_tokens) / len(answer_tokens)
            else:
                groundedness = 0.0
        else:
            groundedness = 0.5  # unknown if no context

        issues = []
        if relevance < 0.3:
            issues.append("Answer does not appear to address the task.")
        if completeness < 0.3:
            issues.append("Answer is very short and may be incomplete.")
        if context and groundedness < 0.3:
            issues.append("Answer may not be grounded in the provided context.")

        return EvaluationResult(
            relevance=round(relevance, 4),
            completeness=round(completeness, 4),
            groundedness=round(groundedness, 4),
            task_completed=len(issues) == 0,
            issues=issues,
        )

    def evaluate(
        self,
        task: str = "",
        answer: str = "",
        context: Optional[str] = None,
        query: Optional[str] = None,
        response: Optional[str] = None,
        retrieved_context: Optional[str] = None,
        **kwargs,
    ) -> EvaluationResult:
        """
        Main entry point. Uses LLM if available, otherwise heuristic fallback.
        Supports both task/answer and query/response parameter naming conventions.
        """
        actual_task = task or query or ""
        actual_answer = answer or response or ""
        actual_context = context or retrieved_context or None

        if self._llm is not None:
            return self.evaluate_with_llm(task=actual_task, answer=actual_answer, context=actual_context)
        return self._heuristic_evaluate(task=actual_task, answer=actual_answer, context=actual_context)


# ── Singleton factory ─────────────────────────────────────────────────────────
_eval_service: Optional[EvaluationService] = None


def get_evaluation_service(llm_service=None) -> EvaluationService:
    global _eval_service
    if _eval_service is None:
        _eval_service = EvaluationService(llm_service=llm_service)
    return _eval_service
