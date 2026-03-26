from datetime import datetime, timedelta

from freezegun import freeze_time

from services.review_scheduler import calculate_next_review

INTERVALS = [1, 3, 7, 14, 30, 60]
FROZEN_TIME = "2026-03-26 12:00:00"


@freeze_time(FROZEN_TIME)
class TestCalculateNextReview:
    """calculate_next_review のユニットテスト"""

    def _expected(self, index: int) -> datetime:
        return datetime(2026, 3, 26, 12) + timedelta(days=INTERVALS[index])

    # --- understanding_level = "high" → index を +1 ---

    def test_high_from_0(self):
        result = calculate_next_review(current_review_count=0, understanding_level="high")
        assert result == self._expected(1)  # 0+1=1 → 3日後

    def test_high_from_2(self):
        result = calculate_next_review(current_review_count=2, understanding_level="high")
        assert result == self._expected(3)  # 2+1=3 → 14日後

    def test_high_at_max_index(self):
        """index 5 (最大) で high → clamp されて 5 のまま"""
        result = calculate_next_review(current_review_count=5, understanding_level="high")
        assert result == self._expected(5)  # min(6, 5)=5 → 60日後

    # --- understanding_level = "low" → index を -1 ---

    def test_low_from_3(self):
        result = calculate_next_review(current_review_count=3, understanding_level="low")
        assert result == self._expected(2)  # 3-1=2 → 7日後

    def test_low_at_min_index(self):
        """index 0 (最小) で low → clamp されて 0 のまま"""
        result = calculate_next_review(current_review_count=0, understanding_level="low")
        assert result == self._expected(0)  # max(-1, 0)=0 → 1日後

    # --- understanding_level = "medium" → index 変更なし ---

    def test_medium_keeps_index(self):
        result = calculate_next_review(current_review_count=2, understanding_level="medium")
        assert result == self._expected(2)  # 2 → 7日後

    def test_medium_at_0(self):
        result = calculate_next_review(current_review_count=0, understanding_level="medium")
        assert result == self._expected(0)  # 0 → 1日後

    def test_medium_at_max(self):
        result = calculate_next_review(current_review_count=5, understanding_level="medium")
        assert result == self._expected(5)  # 5 → 60日後

    # --- 各インターバル値の確認 ---

    def test_all_intervals(self):
        """medium で各 index のインターバル日数を検証"""
        for i, days in enumerate(INTERVALS):
            result = calculate_next_review(current_review_count=i, understanding_level="medium")
            expected = datetime(2026, 3, 26, 12) + timedelta(days=days)
            assert result == expected, f"index={i}, expected {days} days"
