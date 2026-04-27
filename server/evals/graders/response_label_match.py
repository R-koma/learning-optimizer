from evals.graders.base import GraderResult

LEARNING_END_SIGNAL = "LEARNING_END"


def predict_label(response_content: str) -> str:
    return LEARNING_END_SIGNAL if response_content.strip() == LEARNING_END_SIGNAL else "CONTINUE"


def grade(*, response_content: str, expected_label: str) -> GraderResult:
    actual_label = predict_label(response_content)
    matched = actual_label == expected_label
    return GraderResult(
        grader_name="response_label_match",
        score=1.0 if matched else 0.0,
        passed=matched,
        reason=(
            f"label match: {actual_label}"
            if matched
            else f"label mismatch: expected={expected_label}, actual={actual_label}"
        ),
        metadata={"actual_label": actual_label, "expected_label": expected_label},
    )
