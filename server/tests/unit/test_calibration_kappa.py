"""evals.calibration.kappa.compute_binary_agreement の純算術テスト。"""

from __future__ import annotations

import pytest

from evals.calibration.kappa import compute_binary_agreement


def test_perfect_agreement_returns_kappa_one() -> None:
    result = compute_binary_agreement(
        judge=[True, False, True, False],
        human=[True, False, True, False],
    )
    assert result.n == 4
    assert result.agreement == 1.0
    assert result.kappa == 1.0
    assert result.judge_pass_rate == 0.5
    assert result.human_pass_rate == 0.5


def test_perfect_disagreement_returns_negative_kappa() -> None:
    result = compute_binary_agreement(
        judge=[True, True, False, False],
        human=[False, False, True, True],
    )
    assert result.agreement == 0.0
    assert result.kappa == -1.0


def test_known_kappa_value() -> None:
    # 2x2: a=4 (j=T,h=T), b=2 (j=T,h=F), c=1 (j=F,h=T), d=3 (j=F,h=F), n=10
    # po = (4+3)/10 = 0.7
    # pe = ((4+2)*(4+1) + (1+3)*(2+3)) / 100 = (30 + 20)/100 = 0.5
    # kappa = (0.7 - 0.5) / (1 - 0.5) = 0.4
    result = compute_binary_agreement(
        judge=[True] * 4 + [True] * 2 + [False] * 1 + [False] * 3,
        human=[True] * 4 + [False] * 2 + [True] * 1 + [False] * 3,
    )
    assert result.n == 10
    assert result.agreement == pytest.approx(0.7)
    assert result.kappa == pytest.approx(0.4)


def test_all_true_returns_kappa_one_when_agreed() -> None:
    # pe = 1.0 (everyone always True). Convention: agreement=1.0 → kappa=1.0
    result = compute_binary_agreement(judge=[True] * 5, human=[True] * 5)
    assert result.agreement == 1.0
    assert result.kappa == 1.0


def test_all_true_judge_but_some_false_human() -> None:
    # judge always True, human mixed → pe still equals base-rate product
    # a=3, b=2, c=0, d=0, n=5
    # po = 3/5 = 0.6
    # pe = ((3+2)*(3+0) + (0+0)*(2+0)) / 25 = 15/25 = 0.6
    # kappa = 0
    result = compute_binary_agreement(
        judge=[True, True, True, True, True],
        human=[True, True, True, False, False],
    )
    assert result.agreement == pytest.approx(0.6)
    assert result.kappa == pytest.approx(0.0)


def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        compute_binary_agreement(judge=[True], human=[True, False])


def test_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        compute_binary_agreement(judge=[], human=[])
