from evals.graders.base import GraderResult
from graph.model import FeedbackOutput


def grade(feedback: FeedbackOutput) -> GraderResult:
    has_strength = len(feedback.strength) >= 1
    has_improvement = len(feedback.improvement_points) >= 1
    satisfied = sum([has_strength, has_improvement])
    score = satisfied / 2.0
    reasons: list[str] = []
    if not has_strength:
        reasons.append("strength is empty")
    if not has_improvement:
        reasons.append("improvement_points is empty")
    return GraderResult(
        grader_name="feedback_is_actionable",
        score=score,
        passed=satisfied == 2,
        reason="; ".join(reasons) if reasons else "feedback has both strength and improvement_points",
        metadata={
            "has_strength": has_strength,
            "has_improvement_points": has_improvement,
            "n_strength": len(feedback.strength),
            "n_improvement_points": len(feedback.improvement_points),
            "understanding_level": feedback.understanding_level,
        },
    )
