"""Chinese presentation labels for internal ViewModel keys.

Frontend owners must render these labels instead of dumping raw English keys.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.charts.contracts import PublicKeyLabel

MEIHUA_PUBLIC_LABELS: tuple[tuple[str, str], ...] = (
    ("upper", "上卦"),
    ("lower", "下卦"),
    ("body", "体卦"),
    ("use", "用卦"),
    ("primary", "本卦"),
    ("mutual", "互卦"),
    ("changed", "变卦"),
    ("primary_hexagram", "本卦"),
    ("mutual_hexagram", "互卦"),
    ("changed_hexagram", "变卦"),
    ("calculated_relation_not_verdict", "关系已计算，尚非断语"),
    ("calculated_strength_not_verdict", "旺衰已计算，尚非断语"),
    ("autumn", "秋"),
    ("spring", "春"),
    ("summer", "夏"),
    ("winter", "冬"),
)

DALIUREN_PUBLIC_LABELS: tuple[tuple[str, str], ...] = (
    ("transmissions_to_day", "传至日辰"),
    ("initial_final_relation", "初末关系"),
    ("subject_object_relation", "主客关系"),
    ("stage_flow", "三传流转"),
)


def public_key_labels(pairs: Sequence[tuple[str, str]]) -> tuple[PublicKeyLabel, ...]:
    return tuple(PublicKeyLabel(key=key, label=label) for key, label in pairs)
