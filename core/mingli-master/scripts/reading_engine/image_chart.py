"""Machine-check the model's transcription of an attached Bazi chart."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
VALID_GANZHI = {
    STEMS[index % len(STEMS)] + BRANCHES[index % len(BRANCHES)]
    for index in range(60)
}
GANZHI_RE = re.compile(f"[{STEMS}][{BRANCHES}]")


@dataclass(frozen=True)
class ImageChartVerification:
    ok: bool
    missing_fact: str | None
    status: str
    pillars: tuple[str, ...] = ()
    uncertain_positions: tuple[str, ...] = ()
    source_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["pillars"] = list(self.pillars)
        payload["uncertain_positions"] = list(self.uncertain_positions)
        return payload


def _pillars(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    normalized = tuple(str(item).strip() for item in value)
    if any(item not in VALID_GANZHI for item in normalized):
        return None
    return normalized


def validate_image_chart_transcription(
    *,
    image_supplied: bool,
    transcribed_chart: str | None,
    metadata: dict[str, Any],
) -> ImageChartVerification:
    if not image_supplied:
        return ImageChartVerification(True, None, "not_applicable")
    if not str(transcribed_chart or "").strip():
        return ImageChartVerification(False, "image_transcription", "missing_transcription")

    record = metadata.get("image_chart_transcription")
    if not isinstance(record, dict):
        return ImageChartVerification(
            False,
            "image_transcription_verification",
            "missing_dual_pass_record",
        )
    uncertainties = tuple(
        str(item).strip()
        for item in record.get("uncertain_positions") or ()
        if str(item).strip()
    )
    if uncertainties:
        return ImageChartVerification(
            False,
            "unclear_chart_characters",
            "unclear_characters",
            uncertain_positions=uncertainties,
            source_ref=str(record.get("source_ref") or "") or None,
        )

    source_ref = str(record.get("source_ref") or "").strip()
    if not source_ref:
        return ImageChartVerification(
            False,
            "image_transcription_verification",
            "missing_source_reference",
        )
    primary = _pillars(record.get("primary_pass"))
    secondary = _pillars(record.get("secondary_pass"))
    if primary is None or secondary is None:
        return ImageChartVerification(
            False,
            "invalid_image_chart",
            "invalid_ganzhi_or_pillar_count",
            source_ref=source_ref,
        )
    transcribed = tuple(GANZHI_RE.findall(str(transcribed_chart)))
    if primary != secondary or transcribed[:4] != primary or len(transcribed) != 4:
        return ImageChartVerification(
            False,
            "image_transcription_mismatch",
            "dual_pass_or_text_mismatch",
            source_ref=source_ref,
        )
    return ImageChartVerification(
        True,
        None,
        "dual_pass_structurally_validated",
        pillars=primary,
        source_ref=source_ref,
    )


__all__ = [
    "ImageChartVerification",
    "VALID_GANZHI",
    "validate_image_chart_transcription",
]
