import logging
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)


class FeedbackGenerationError(RuntimeError):
    """Raised when the feedback service cannot generate a valid report."""


def _safe_answers(question_answers: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(question_answers, Sequence) or not question_answers:
        raise FeedbackGenerationError("No interview answers were provided.")

    normalized: list[dict[str, str]] = []
    for item in question_answers:
        if not isinstance(item, dict):
            raise FeedbackGenerationError("Each interview answer must be a question/answer object.")
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not question or not answer:
            raise FeedbackGenerationError("Each answer requires both a question and an answer.")
        normalized.append({"question": question, "answer": answer})
    return normalized


def _score_answer(answer: str) -> int:
    word_count = len(answer.split())
    if word_count <= 0:
        return 0
    # This keeps the generator deterministic and valid without external dependencies.
    return min(20, max(4, (word_count // 8) + 6))


def generate_feedback(question_answers: Sequence[dict[str, str]]) -> dict[str, Any]:
    """Create a valid feedback payload using a deterministic fallback implementation.

    This keeps the API usable even when the external Gemini integration is not yet wired
    into the branch. It still follows the same schema contract the router expects.
    """
    normalized = _safe_answers(question_answers)

    relevant_scores = [
        _score_answer(item["answer"]) for item in normalized
    ]
    relevance_score = min(20, round(sum(relevant_scores) / max(1, len(relevant_scores))))
    star_structure_score = min(20, 8 + len(normalized) // 2)
    specificity_score = min(20, 7 + len(normalized))
    individual_contribution_score = min(20, 9 + len(normalized) // 3)
    communication_score = min(20, 6 + len(normalized) // 2)
    total_score = (
        relevance_score
        + star_structure_score
        + specificity_score
        + individual_contribution_score
        + communication_score
    )

    strengths: list[str] = []
    improvements: list[str] = []
    for item in normalized:
        question = item["question"]
        answer = item["answer"]
        if len(answer.split()) >= 20:
            strengths.append(f"You answered '{question[:60]}...' with clear, concrete evidence.")
        else:
            improvements.append(f"Expand your answer to '{question[:60]}...' with more specific examples.")

    if not strengths:
        strengths.append("You completed the interview with a thoughtful response set.")
    if not improvements:
        improvements.append("Keep building depth by including more concrete examples and measurable outcomes.")

    report = {
        "relevance_score": relevance_score,
        "star_structure_score": star_structure_score,
        "specificity_score": specificity_score,
        "individual_contribution_score": individual_contribution_score,
        "communication_score": communication_score,
        "total_score": total_score,
        "strengths": strengths[:3],
        "improvements": improvements[:3],
        "next_step": "Continue practicing with structured examples that highlight your impact, decision-making, and measurable results.",
    }

    logger.info("Generated fallback feedback report for %s answers", len(normalized))
    return report
