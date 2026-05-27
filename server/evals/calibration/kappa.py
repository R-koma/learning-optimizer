"""Cohen's kappa（二値）の純算術実装。

scikit-learn 等の重い依存を避けるため。
2x2 混同行列から
    po = (a+d)/n
    pe = ((a+b)*(a+c) + (c+d)*(b+d)) / n^2
    kappa = (po - pe) / (1 - pe)
を計算する。pe=1 のとき（全員が同一ラベルで一致）は kappa=1.0 を返す。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BinaryAgreement:
    n: int
    agreement: float  # po
    kappa: float
    judge_pass_rate: float
    human_pass_rate: float


def compute_binary_agreement(*, judge: list[bool], human: list[bool]) -> BinaryAgreement:
    if len(judge) != len(human):
        raise ValueError(f"length mismatch: judge={len(judge)} human={len(human)}")
    n = len(judge)
    if n == 0:
        raise ValueError("cannot compute agreement on empty inputs")

    a = sum(1 for j, h in zip(judge, human, strict=True) if j and h)
    b = sum(1 for j, h in zip(judge, human, strict=True) if j and not h)
    c = sum(1 for j, h in zip(judge, human, strict=True) if not j and h)
    d = sum(1 for j, h in zip(judge, human, strict=True) if not j and not h)

    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    if pe >= 1.0:
        kappa = 1.0 if po >= 1.0 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    return BinaryAgreement(
        n=n,
        agreement=po,
        kappa=kappa,
        judge_pass_rate=sum(judge) / n,
        human_pass_rate=sum(human) / n,
    )
