from __future__ import annotations

from math import pi
from pathlib import Path

import matplotlib.pyplot as plt

from .utils import ensure_dir


def _set_korean_font():
    # 환경별 fallback
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


def save_radar_chart(score_result: dict, out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    _set_korean_font()

    axes = score_result.get("axes", []) or []
    labels = [a["name"] for a in axes]
    values = [int(a["score"]) for a in axes]

    if not labels:
        labels = ["기술성", "양산성", "고객 채택도", "수익성 기여", "확장성", "진입장벽", "투자 지속성"]
        values = [1, 1, 1, 1, 1, 1, 1]

    values += values[:1]
    angles = [n / float(len(labels)) * 2 * pi for n in range(len(labels))]
    angles += angles[:1]

    fig = plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)

    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1)

    plt.xticks(angles[:-1], labels, fontsize=11)
    ax.set_rlabel_position(0)
    plt.yticks([1, 2, 3, 4, 5], ["1", "2", "3", "4", "5"], fontsize=9)
    plt.ylim(0, 5)

    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.15)

    total = score_result.get("total_score", 0)
    max_score = score_result.get("max_score", 35)
    plt.title(f"기술 경쟁력 레이더 차트 ({total}/{max_score})", pad=24, fontsize=14)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path