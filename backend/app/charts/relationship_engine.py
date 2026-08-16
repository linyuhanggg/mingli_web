from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast

from app.charts.contracts import (
    BaziRelationshipV1,
    QizhengRelationshipV1,
    RelationshipSignal,
    RelationshipSubject,
    ZiweiRelationshipV1,
)

RelationshipType = Literal[
    "romantic",
    "married",
    "parent_child",
    "business",
    "work",
    "friend",
]

_RELATIONSHIP_TYPES: frozenset[str] = frozenset(
    {"romantic", "married", "parent_child", "business", "work", "friend"}
)


def _relationship_context(
    brief: Mapping[str, object] | None,
    relationship_type: str | None,
) -> tuple[tuple[RelationshipSubject, RelationshipSubject], RelationshipType] | None:
    if brief is None:
        return None
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return None
    raw_subjects = request_view.get("subject_refs")
    if not isinstance(raw_subjects, (list, tuple)) or len(raw_subjects) != 2:
        return None
    subject_refs = tuple(item for item in raw_subjects if isinstance(item, str) and item.strip())
    if len(subject_refs) != 2 or subject_refs[0] == subject_refs[1]:
        return None

    raw_type = relationship_type or request_view.get("relationship_type")
    if not isinstance(raw_type, str) or raw_type not in _RELATIONSHIP_TYPES:
        return None
    typed_relationship_type = cast(RelationshipType, raw_type)

    raw_labels = request_view.get("subject_labels")
    labels = (
        [item for item in raw_labels if isinstance(item, str) and item.strip()]
        if isinstance(raw_labels, (list, tuple)) and len(raw_labels) == 2
        else []
    )
    if len(labels) != 2:
        labels = ["甲方", "乙方"]

    subjects = (
        RelationshipSubject(
            subject_ref=subject_refs[0],
            profile_version_id=_profile_version_id(subject_refs[0]),
            label=labels[0],
        ),
        RelationshipSubject(
            subject_ref=subject_refs[1],
            profile_version_id=_profile_version_id(subject_refs[1]),
            label=labels[1],
        ),
    )
    return subjects, typed_relationship_type


def _profile_version_id(subject_ref: str) -> str:
    prefix = "profile-version:"
    if subject_ref.startswith(prefix) and subject_ref[len(prefix) :].strip():
        return subject_ref[len(prefix) :]
    return subject_ref


def _native_relationship_signals(
    brief: Mapping[str, object],
    subjects: tuple[RelationshipSubject, RelationshipSubject],
) -> tuple[RelationshipSignal, ...] | None:
    """Project relationship facts already calculated by the Runtime.

    The website deliberately does not derive cross-chart rules from four
    pillars, palaces, or positions. A Runtime release that supports a
    relationship product must publish one calculated ``relationship_signals``
    fact whose entries carry their own source fact references. Until that
    native fact exists, the product remains an honest incomplete slice.
    """

    facts = brief.get("facts")
    if not isinstance(facts, (list, tuple)):
        return None
    expected_subjects = (subjects[0].subject_ref, subjects[1].subject_ref)
    available_fact_refs = {
        ref
        for item in facts
        if isinstance(item, Mapping)
        for ref in (item.get("ref"),)
        if isinstance(ref, str) and ref and "/input/" not in ref
    }
    raw_signals: object | None = None
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        ref = item.get("ref")
        if (
            not isinstance(ref, str)
            or "/input/" in ref
            or ref.rstrip("/").rsplit("/", 1)[-1] != "relationship_signals"
        ):
            continue
        raw_signals = item.get("value")
        break
    if not isinstance(raw_signals, (list, tuple)) or not raw_signals:
        return None

    signals: list[RelationshipSignal] = []
    for raw in raw_signals:
        if not isinstance(raw, Mapping):
            return None
        signal_id = raw.get("signal_id")
        dimension_id = raw.get("dimension_id")
        display_text = raw.get("display_text")
        raw_subject_refs = raw.get("subject_refs")
        raw_fact_refs = raw.get("fact_refs")
        if (
            not isinstance(signal_id, str)
            or not signal_id.strip()
            or dimension_id != "relationship"
            or not isinstance(display_text, str)
            or not display_text.strip()
            or not isinstance(raw_subject_refs, (list, tuple))
            or tuple(raw_subject_refs) != expected_subjects
            or not isinstance(raw_fact_refs, (list, tuple))
            or not raw_fact_refs
        ):
            return None
        fact_refs = tuple(
            ref for ref in raw_fact_refs if isinstance(ref, str) and "/input/" not in ref
        )
        if (
            len(fact_refs) != len(raw_fact_refs)
            or not set(fact_refs) <= available_fact_refs
        ):
            return None
        signals.append(
            RelationshipSignal(
                dimension_id="relationship",
                subject_refs=expected_subjects,
                signal_id=signal_id,
                display_text=display_text,
                fact_refs=fact_refs,
            )
        )
    return tuple(signals)


def _has_capability(brief: Mapping[str, object] | None, capability_id: str) -> bool:
    if brief is None:
        return False
    request_view = brief.get("request_view")
    if not isinstance(request_view, Mapping):
        return False
    capability_ids = request_view.get("capability_ids")
    return isinstance(capability_ids, (list, tuple)) and tuple(capability_ids) == (capability_id,)


def _project_relationship(
    brief: Mapping[str, object] | None,
    *,
    capability_id: str,
    relationship_type: str | None,
    view_type: type[BaziRelationshipV1] | type[ZiweiRelationshipV1] | type[QizhengRelationshipV1],
) -> BaziRelationshipV1 | ZiweiRelationshipV1 | QizhengRelationshipV1 | None:
    context = _relationship_context(brief, relationship_type)
    if context is None or brief is None or not _has_capability(brief, capability_id):
        return None
    subjects, typed_relationship_type = context
    signals = _native_relationship_signals(brief, subjects)
    if signals is None:
        return None
    return view_type(
        subjects=subjects,
        relationship_type=typed_relationship_type,
        signals=signals,
    )


def project_bazi_relationship_view_model(
    brief: Mapping[str, object] | None,
    *,
    relationship_type: str | None = None,
) -> BaziRelationshipV1 | None:
    view = _project_relationship(
        brief,
        capability_id="bazi",
        relationship_type=relationship_type,
        view_type=BaziRelationshipV1,
    )
    return view if isinstance(view, BaziRelationshipV1) else None


def project_ziwei_relationship_view_model(
    brief: Mapping[str, object] | None,
    *,
    relationship_type: str | None = None,
) -> ZiweiRelationshipV1 | None:
    view = _project_relationship(
        brief,
        capability_id="ziwei",
        relationship_type=relationship_type,
        view_type=ZiweiRelationshipV1,
    )
    return view if isinstance(view, ZiweiRelationshipV1) else None


def project_qizheng_relationship_view_model(
    brief: Mapping[str, object] | None,
    *,
    relationship_type: str | None = None,
) -> QizhengRelationshipV1 | None:
    view = _project_relationship(
        brief,
        capability_id="xingming",
        relationship_type=relationship_type,
        view_type=QizhengRelationshipV1,
    )
    return view if isinstance(view, QizhengRelationshipV1) else None
