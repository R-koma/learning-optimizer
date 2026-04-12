from datetime import datetime, timedelta


def calculate_next_review(current_review_count: int) -> datetime:
    interval = [1, 3, 7, 14, 30, 60]
    index = min(current_review_count, len(interval) - 1)
    return datetime.now() + timedelta(days=interval[index])
