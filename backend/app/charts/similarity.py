from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

PILLAR_POSITIONS: tuple[Literal["year", "month", "day", "hour"], ...] = (
    "year",
    "month",
    "day",
    "hour",
)
PillarPosition = Literal["year", "month", "day", "hour"]


class ChartSimilarityInputError(ValueError):
    """Calculated chart facts are not valid for the bounded comparison."""


def compare_bazi_four_pillars(
    left: Mapping[str, object],
    right: Mapping[str, object],
) -> tuple[tuple[PillarPosition, str, str, bool], ...]:
    """Compare exactly the four Runtime-calculated Bazi pillars.

    The function intentionally accepts only calculated fact values.  It does
    not inspect birth timestamps, names, element counts, or interpretive
    findings, and it does not assign a similarity score.
    """

    comparisons: list[tuple[PillarPosition, str, str, bool]] = []
    for position in PILLAR_POSITIONS:
        left_value = left.get(position)
        right_value = right.get(position)
        if (
            not isinstance(left_value, str)
            or not isinstance(right_value, str)
            or len(left_value) != 2
            or len(right_value) != 2
        ):
            raise ChartSimilarityInputError(
                f"calculated four_pillars must contain two-character {position} values"
            )
        comparisons.append((position, left_value, right_value, left_value == right_value))
    return tuple(comparisons)
