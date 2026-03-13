from datetime import datetime, timedelta


def calculate_next_review(current_review_count: int, understanding_level: str) -> datetime:
    interval = [1, 3, 7, 14, 30, 60]

    # TODO: interval[5]の場合の処理

    current_review_index = current_review_count

    if understanding_level == "high":
        current_review_index += 1
    elif understanding_level == "low":
        current_review_index -= 1

    current_review_index = max(0, min(current_review_index, len(interval) - 1))
    days_to_add = interval[current_review_index]
    return datetime.now() + timedelta(days=days_to_add)
