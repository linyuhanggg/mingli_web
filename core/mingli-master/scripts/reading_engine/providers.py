"""Deterministic calculation providers used by the Mingli v4 transaction."""

from __future__ import annotations

import argparse
import calendar as stdlib_calendar
import copy
import json
import re
import secrets
import subprocess
import uuid
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import adapter_validate
import bazi_calc
import bazi_fact_adapter
import liuren_calc
import near_time_fortune_adapter
import reading_evidence_bundle
import reading_source_plan
import ziwei_fact_adapter
from fact_contracts.bazi import BaziFactContract
from runtime_python import runtime_command

from .contracts import (
    CalculationResult,
    EvidenceBundle,
    FactExtensionResult,
    ProviderAlgorithmDependency,
    ProviderCapability,
    ReadingRequest,
    canonical_digest,
)
from .catalog import CatalogLoader, ProviderDescriptor
from .fact_index import build_fact_index, indexed_fact_payload
from . import (
    calendar_core,
    fengshui,
    physiognomy,
    liuyao,
    luming,
    meihua,
    qimen,
    selection,
    taiyi,
    xingming,
)
from .image_chart import ImageChartVerification, validate_image_chart_transcription
from .intent_frame import IntentFrame
from .provider_protocol import (
    ProviderActionError,
    ProviderContext,
    ProviderNeedInput,
    ProviderPreparation,
    ProviderRequest,
    ProviderUnsupported,
)
from .runtime_context import RuntimeContext
from .structured_input import normalize_structured_chart


GANZHI_RE = re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]")
# Live provider capability declarations, intentionally independent of the
# provenance manifests. The release audit compares the two authorities so a
# manifest edit cannot silently rewrite what live code claims to execute.


def _dependencies(
    *rows: tuple[str, str],
) -> tuple[ProviderAlgorithmDependency, ...]:
    return tuple(
        ProviderAlgorithmDependency(id=dependency_id, version=version)
        for dependency_id, version in rows
    )


# These are executable-provider declarations, intentionally independent of the
# provenance manifest. The release audit compares the two authorities so a
# manifest edit cannot silently rewrite what live code claims to execute.
_ALGORITHM_DEPENDENCY_DECLARATIONS = {
    "bazi": _dependencies(
        ("bazi.calendar.sxtwl-jieqi-four-pillars", "sxtwl-2.0.7/jieqi-month/zi-hour-midnight-v1"),
        ("bazi.luck.major-cycle-three-days-per-year", "sanming-three-days-per-year-v1"),
        ("bazi.relations.ten-gods-hidden-stems-branch-relations", "sanming-ziping-relations-v1"),
        ("bazi.seasonal-tiaohou.day-master-month", "qiongtong-day-master-month-v1"),
        ("bazi.shensha.yima-taohua-auxiliary", "sanming-yima-taohua-auxiliary-v1"),
    ),
    "time-check": _dependencies(
        ("time-check.candidate-hours-over-bazi", "bazi-runtime-candidate-hours-v1"),
        ("time-check.true-solar-time-preservation", "calendar-core-local-apparent-solar-v1"),
        ("time-check.structured-event-evidence", "bazi-year-pillar-event-domain-evidence-v1"),
        (
            "time-check.classical-hour-rectification",
            "sanming-hour-clash-union-xiaoyun-minggong-v1",
        ),
    ),
    "fortune": _dependencies(
        ("fortune.bounded-target-period-over-bazi", "fortune-v6-one-explicit-period"),
    ),
    "ziwei": _dependencies(
        ("ziwei.iztro.natal-palaces-stars-transformations", "iztro-2.5.8/default/fix-leap/zh-CN"),
        ("ziwei.iztro.decadal-year-month-horoscope", "iztro-2.5.8/horoscope-normal-v1"),
        ("ziwei.iztro.leap-hour-major-limit-conventions", "iztro-2.5.8/fix-leap/day-divide-v1"),
        ("ziwei.source-conditioned-patterns", "verified-evidence-rules-v1"),
    ),
    "liuren": _dependencies(
        (
            "liuren.calendar.shared-sxtwl-four-pillars",
            "sxtwl-2.0.7/exact-jie-boundary-v1.2/east-asian-civil-jieqi-v1@1.0.2/five-rat-strict",
        ),
        ("liuren.cast.four-lessons-three-transmissions-nine-methods", "daliuren-nine-method-v2/official-corrected-guiren"),
        ("liuren.timing.initial-group-seasonal-upper", "liuren-miben-LM-R21-v1"),
        ("liuren.dimension-specific-calculated-facts", "liuren-dimension-projection-v1"),
        ("liuren.location.branch-direction-correspondence", "liuren-miben-branch-directions-v1"),
        ("liuren.imagery.general-landing-correspondence", "liuren-miben-general-landing-v1"),
    ),
    "luming-nayin": _dependencies(
        ("luming.nayin.sixty-jiazi-table", "li-xuzhong-sixty-nayin-v1"),
        ("luming.three-yuan-and-taiyuan", "luoluzi-three-yuan/taiyuan-declared-v1"),
        ("luming.relations.lu-ma-gui", "li-xuzhong-lu-ma-gui-v1"),
        ("luming.source-conditioned-patterns", "verified-evidence-rules-v1"),
    ),
    "xingming": _dependencies(
        ("xingming.ephemeris.seven-luminaries", "astronomy-engine-2.1.19/geocentric-ecliptic-of-date-v1"),
        ("xingming.houses.ming-shen-degrees", "xingxue-twelve-house-mingshen-opposition-v1"),
        ("xingming.houses.topocentric-ming-degree", "apparent-sidereal-eastern-ecliptic-horizon-v1"),
        ("xingming.four-residuals.numeric-profiles", "lunar-node-apogee-and-dated-ziqi-calibration-v1"),
        ("xingming.transformations.ten-stem-table", "xingxue-ten-stem-transformations-v1"),
        ("xingming.limits.dongwei-bailiu-table", "dongwei-bailiu-100-years-6-months-v1"),
        ("xingming.source-conditioned-patterns", "verified-evidence-rules-v1"),
    ),
    "liuyao": _dependencies(
        ("liuyao.cast.six-tosses-and-hexagrams", "three-coin-six-toss-preserved-seed-v1"),
        ("liuyao.plate.hexagram-palace-shiying", "jingfang-eight-palace-najia-v1"),
        ("liuyao.plate.najia-six-relatives-hidden-lines", "jingfang-najia-six-relatives-fushen-v1"),
        ("liuyao.plate.six-spirits", "liuyao-six-spirits-day-stem-v1"),
        ("liuyao.calendar.xunkong-month-day-relations", "liuyao-xunkong-month-day-strength-v1"),
        ("liuyao.relations.returning-and-useful-spirit-candidates", "liuyao-returning-relations-candidates-v1"),
    ),
    "meihua": _dependencies(
        ("meihua.cast.explicit-methods-and-moduli", "meihua-explicit-methods-v1"),
        ("meihua.plate.main-mutual-changed", "meihua-mutual-change-v1"),
        ("meihua.body-use-elements-season", "meihua-body-use-five-elements-v1"),
    ),
    "qimen": _dependencies(
        ("qimen.calendar.dun-yuan-ju", "shijia-zhuanpan-chaibu-xieji-v1"),
        ("qimen.plate.instruments-wonders-palaces", "qimen-nine-palace-earth-plate-v1"),
        ("qimen.plate.chief-director-stars-doors-deities", "qimen-rotating-chief-director-v1"),
        ("qimen.markers.xunkong-horse", "qimen-xunkong-hour-horse-v1"),
        ("qimen.patterns.board-predicates", "qimen-forty-pattern-predicate-set-v1"),
    ),
    "taiyi": _dependencies(
        ("taiyi.calendar.annual-epoch-and-scope", "taiyi-jinjing-annual-tang-jiazi-v1"),
        ("taiyi.cycle.six-ji-five-zi-yuan", "taiyi-jinjing-six-ji-five-zi-yuan-v1"),
        ("taiyi.plate.taiyi-tianmu-jishen-shiji", "taiyi-jinjing-annual-yang-core-board-v1"),
        ("taiyi.plate.host-guest-counts-and-generals", "taiyi-jinjing-annual-host-guest-v1"),
        ("taiyi.deities.independent-long-cycle-epochs", "taiyi-jinjing-volume-five-long-cycles-v1"),
        ("taiyi.evidence.board-predicates-and-scope", "taiyi-jinjing-fact-bound-evidence-v1"),
    ),
    "selection": _dependencies(
        ("selection.candidate-calendar-foundation", "selection-candidate-range-v1"),
        ("selection.day-facts.jianchu-mansions-gods", "xieji-official-day-facts-v1"),
        ("selection.hour-facts.ganzhi-and-twelve-gods", "xieji-official-hour-facts-v1"),
        ("selection.event-rules-and-lineage-conflicts", "selection-event-rules-separated-lineages-v1"),
        ("selection.runtime.cnlunar-official-tables", "cnlunar-0.2.4/xieji-official-cnlunar-v1"),
        ("selection.source-conditioned-patterns", "verified-evidence-rules-v1"),
    ),
    "fengshui": _dependencies(
        ("fengshui.observation.compass-layout-contract", "fengshui-observation-compass-v1"),
        ("fengshui.form.observable-site-facts", "fengshui-form-visible-facts-v1"),
        ("fengshui.liqi.bazhai-school", "yangzhai-shishu-bazhai-v1"),
    ),
    "physiognomy": _dependencies(
        ("physiognomy.observation.image-quality-regions", "physiognomy-visible-observation-v1"),
        ("physiognomy.normalization.visible-only-features", "physiognomy-visible-only-normalization-v1"),
        ("physiognomy.evidence.revision-and-source-conflict", "physiognomy-observation-revision-v1"),
    ),
}


def _capability_from_descriptor(
    descriptor: ProviderDescriptor,
) -> ProviderCapability:
    """Bind manifest-owned vocabulary to provider-owned algorithm identity."""

    payload = descriptor.canonical_payload.get("runtime_capability")
    if not isinstance(payload, Mapping):
        raise ProviderActionError(
            "descriptor_invalid",
            "provider manifest has no runtime capability",
        )
    dependencies = _ALGORITHM_DEPENDENCY_DECLARATIONS.get(descriptor.id)
    if not dependencies:
        raise ProviderActionError(
            "descriptor_invalid",
            "provider has no pinned algorithm dependency declaration",
        )
    # Runtime manifests also carry caller-view metadata.  The executable
    # capability contract consumes only its own declared fields; additional
    # manifest-owned projections stay behind the descriptor seam.
    capability_payload = {
        key: value
        for key, value in payload.items()
        if key in ProviderCapability.__dataclass_fields__
    }
    capability_payload["algorithm_dependencies"] = [
        item.to_dict() for item in dependencies
    ]
    return ProviderCapability.from_dict(capability_payload)


# Kept as a read-only compatibility view for provider audits. Every vocabulary
# field is materialized from the bundled manifests; Python no longer owns a
# second capability table.
_RUNTIME_CATALOG = CatalogLoader(
    Path(__file__).resolve().parents[2] / "resources" / "runtime"
).load()
PROVIDER_CAPABILITIES = {
    descriptor.id: _capability_from_descriptor(descriptor)
    for descriptor in _RUNTIME_CATALOG.descriptors
}
_CAPABILITY_SYSTEM_BY_ADAPTER = {
    descriptor.entrypoint.rsplit(":", 1)[-1]: descriptor.id
    for descriptor in _RUNTIME_CATALOG.descriptors
}


def _birth_value(request: Any, field: str) -> Any:
    birth = request.birth_data if isinstance(request.birth_data, dict) else {}
    if field == "birth_datetime":
        return birth.get("birth_datetime") or birth.get("datetime")
    return birth.get(field) or getattr(request, field, None)


STRUCTURED_SYSTEMS: tuple[str, ...] = ()
FORTUNE_REQUIRED_PROFILE_FIELDS = (
    "birth_datetime",
    "timezone",
    "location",
    "gender",
)


def _normalized_subject_token(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _default_profile_changes(
    request: ReadingRequest,
    context: RuntimeContext | None,
    *,
    ensure_datetime_alias: bool,
) -> dict[str, Any] | None:
    """Opt-in default subject data read from the injected runtime context."""

    if context is None or request.birth_data:
        return None
    if request.goal.get("use_default_profile") is not True:
        return None
    profile_source = context.profile_for("current_user")
    if not profile_source:
        return None
    frame = IntentFrame.from_dict(request.intent)
    subject_refs = tuple(
        _normalized_subject_token(value) for value in frame.subject_refs
    )
    goal_subject = request.goal.get("subject")
    if subject_refs != ("current_user",):
        return None
    if goal_subject is not None and _normalized_subject_token(
        goal_subject
    ) != "current_user":
        return None
    if frame.calculation_object not in {"natal", "near_time_personal"}:
        return None
    profile = dict(profile_source)
    if ensure_datetime_alias and not profile.get("datetime"):
        profile["datetime"] = profile.get("birth_datetime")
    return {"birth_data": profile}


def _with_request_changes(
    request: ReadingRequest,
    changes: dict[str, Any] | None,
) -> ReadingRequest:
    if not changes:
        return request
    return ReadingRequest(**{**request.to_dict(), **changes})


def _request_time_basis(
    request: ReadingRequest,
) -> tuple[str, float | None, float | None, str | None]:
    """Read the time-basis policy and coordinates from whichever slot carries them.

    Birth-mode providers keep these on birth_data; event-mode providers keep
    them on metadata. Checking both lets the generic NeedInput check stay free
    of per-provider branching.
    """

    birth = request.birth_data if isinstance(request.birth_data, dict) else {}
    meta = request.metadata if isinstance(request.metadata, dict) else {}
    policy = str(
        birth.get("time_basis_policy")
        or meta.get("time_basis_policy")
        or "civil"
    )
    longitude = birth.get("longitude")
    if longitude is None:
        longitude = meta.get("longitude")
    latitude = birth.get("latitude")
    if latitude is None:
        latitude = meta.get("latitude")
    source = birth.get("coordinate_source") or meta.get("coordinate_source")
    return policy, longitude, latitude, source


_RANGED_HORIZON_KINDS = frozenset({"day", "month", "year"})


def _reference_period(kind: str, reference_datetime: str) -> str | None:
    try:
        moment = datetime.fromisoformat(
            reference_datetime.strip().replace("Z", "+00:00")
        )
    except ValueError:
        return None
    if kind == "day":
        return moment.date().isoformat()
    if kind == "month":
        return moment.strftime("%Y-%m")
    return str(moment.year)


def _resolve_extension_horizon(
    horizon: dict[str, Any],
    reference_datetime: str | None,
) -> dict[str, Any]:
    """Bind a null-bounded ranged horizon to the request reference period."""

    kind = str(horizon.get("kind") or "")
    if (
        kind not in _RANGED_HORIZON_KINDS
        or horizon.get("start")
        or horizon.get("end")
        or not str(reference_datetime or "").strip()
    ):
        return horizon
    period = _reference_period(kind, str(reference_datetime))
    if period is None:
        return horizon
    return {**horizon, "start": period, "end": period}


def _adapter_evidence_goal(request: ReadingRequest) -> dict[str, Any]:
    frame = IntentFrame.from_dict(request.intent)
    goal = dict(request.goal)
    goal["evidence_questions"] = list(frame.evidence_questions)
    dimensions = list(frame.question_dimensions)
    goal["question_dimensions"] = dimensions
    goal["requested_dimensions"] = dimensions
    goal["requested_resolution"] = frame.requested_granularity
    goal["calculation_object"] = frame.calculation_object
    return goal


def _assign_request_slot(
    request_values: dict[str, Any],
    field_id: str,
    slot_spec: Any,
    value: Any,
) -> None:
    """Place one manifest-declared input field into the legacy request."""

    slot: str | None = None
    if isinstance(slot_spec, str):
        slot = slot_spec
    elif isinstance(slot_spec, Mapping):
        if isinstance(value, str):
            slot = slot_spec.get("string")
        elif isinstance(value, Mapping):
            slot = slot_spec.get("mapping")
        elif isinstance(value, (list, tuple)):
            slot = slot_spec.get("list")
        slot = slot or slot_spec.get("default")
    if not isinstance(slot, str) or not slot:
        chart = request_values.setdefault("chart_data", {})
        chart[field_id] = value
        return
    parts = slot.split(".")
    if len(parts) == 1:
        if isinstance(value, Mapping) and isinstance(
            request_values.get(parts[0]), dict
        ):
            request_values[parts[0]].update(dict(value))
        elif isinstance(value, Mapping) and parts[0] in (
            "birth_data",
            "chart_data",
            "metadata",
            "goal",
        ):
            request_values.setdefault(parts[0], {}).update(dict(value))
        else:
            request_values[parts[0]] = value
        return
    node = request_values
    for part in parts[:-1]:
        child = node.setdefault(part, {})
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def _localized_display(display: Any) -> str | None:
    if not isinstance(display, Mapping) or not display:
        return None
    localized = display.get("zh-CN")
    if localized is None:
        localized = next(iter(display.values()))
    if isinstance(localized, str) and localized.strip():
        return localized.strip()
    if isinstance(localized, Mapping):
        name = localized.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _descriptor_term_label(
    descriptor: ProviderDescriptor,
    term_id: str,
) -> str | None:
    terms = descriptor.canonical_payload.get("terms")
    if isinstance(terms, Mapping):
        spec = terms.get(term_id)
        if isinstance(spec, Mapping):
            return _localized_display(spec.get("display"))
    return None


def _input_field_label(descriptor: ProviderDescriptor, field_id: str) -> str:
    for field in descriptor.input_fields:
        if field.id == field_id:
            return _localized_display(field.display) or field_id
    return field_id


def _compact_public_value(value: Any) -> str:
    if isinstance(value, str):
        rendered = value
    else:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    if len(rendered) > 200:
        rendered = rendered[:199] + "…"
    return rendered


def _json_pointer_value(payload: Any, pointer: str) -> tuple[bool, Any]:
    if not pointer.startswith("/"):
        return False, None
    current = payload
    for raw_part in pointer.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index < len(current):
                current = current[index]
                continue
        return False, None
    return True, current


# These are serialization-level public projections, not provider or subject
# vocabulary. A manifest may expose calculated output or fact-extension data,
# but it cannot point a drafting finding at private request, digest, storage
# or injected-cast material.
_PUBLIC_PROJECTION_POINTER_PREFIXES = (
    "/facts/chart_facts/output/",
    "/fact_extension/facts/",
)


def _is_public_projection_pointer(value: object) -> bool:
    return isinstance(value, str) and value.startswith(
        _PUBLIC_PROJECTION_POINTER_PREFIXES
    )


def _binding_pointer_to_index_origin(pointer: str) -> str | None:
    """Map a manifest JSON pointer to the engine-internal fact-index path.

    Manifest pointers address ``calculation.to_dict()`` (``/facts/...`` and
    ``/fact_extension/...``).  The evidence compiler's internal fact refs use
    the flattened index paths ``/chart_facts/...`` and
    ``/fact_extensions/...``.  This one structural rewrite is the only thing
    that maps a declared binding onto an internal origin; it never interprets
    a path segment's name.
    """
    if pointer.startswith("/facts/"):
        return pointer[len("/facts"):]
    if pointer.startswith("/fact_extension/facts/"):
        return "/fact_extensions" + pointer[len("/fact_extension"):]
    return None


def _optional_string_tuple(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        return None
    return items


def _declared_output_projection(
    descriptor: ProviderDescriptor,
    calculation: CalculationResult,
) -> dict[str, Any]:
    runtime = descriptor.canonical_payload.get("runtime_capability")
    if not isinstance(runtime, Mapping):
        return {}
    payload = calculation.to_dict()
    projected: dict[str, Any] = {}
    for group_name in ("output_bindings", "extension_output_bindings"):
        for binding in runtime.get(group_name) or ():
            if not isinstance(binding, Mapping):
                continue
            name = binding.get("name")
            if not isinstance(name, str) or not name:
                continue
            for pointer in binding.get("json_pointers") or ():
                found, value = _json_pointer_value(payload, str(pointer))
                if found:
                    projected[name] = value
                    break
    return projected


def _source_rule_id(tool: object) -> str | None:
    if not isinstance(tool, Mapping):
        return None
    for source in tool.get("source_refs") or ():
        if not isinstance(source, Mapping):
            continue
        pack = source.get("pack")
        rule_id = source.get("rule_id")
        if not isinstance(pack, str) or not pack:
            continue
        if not isinstance(rule_id, str) or not rule_id:
            continue
        return rule_id if "#" in rule_id else f"{pack}#{rule_id}"
    return None


def _exact_rule_evidence_ref(
    rule_id: object,
    evidence_refs: tuple[str, ...],
) -> str | None:
    if not isinstance(rule_id, str) or not rule_id:
        return None
    expected = f"evidence:bazi/{rule_id}"
    return expected if expected in evidence_refs else None


# Verified, runtime-active methodology anchors for the structural claim
# units below.  Each unit renders already-calculated chart facts in the
# reading order that its quoted source states verbatim; none of them may
# carry a strength, structure-success, or fortune verdict.
_BAZI_PILLAR_ROLES_RULE_ID = "bazi/yuanhai-ziping#YR-M01"
_BAZI_THREE_YUAN_RULE_ID = "bazi/ditiansui-chanwei#DR-01-01"
_BAZI_ELEMENT_FLOW_RULE_ID = "bazi/sanming-tonghui#R-01-02"
_BAZI_PILLAR_POSITION_LABELS = {
    "year": "年",
    "month": "月",
    "day": "日",
    "hour": "时",
}


def _bazi_public_claim_findings(
    value: object,
    *,
    subject_ref: str,
    dimension_ids: tuple[str, ...],
    fact_refs: tuple[str, ...],
    public_fact_refs: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    evidence_supports: Mapping[str, tuple[str, ...]],
    chart_output: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Build audited, bounded Bazi prose units from Runtime adjudications.

    These are not life-event verdicts and are not model-authored summaries.
    Each sentence is a deterministic rendering of an already-calculated
    source-bound state, and is emitted only when its exact classical evidence
    survived the public evidence gate in the same prepared turn.
    """

    if not isinstance(value, Mapping) or not fact_refs:
        return ()
    tools = value.get("reasoning_tools")
    if not isinstance(tools, Mapping):
        return ()

    units: list[dict[str, Any]] = []
    # ``fact_refs`` is the manifest-scoped support for the parent
    # interpretive finding. Structural units also read public chart outputs,
    # so bind those values only through fact identities that were actually
    # projected into this brief.
    public_fact_ref_set = frozenset(public_fact_refs)

    def public_chart_fact_ref(output_name: str) -> str | None:
        expected = f"fact:{subject_ref}/calculated/bazi/{output_name}"
        return expected if expected in public_fact_ref_set else None

    def append_unit(
        *,
        unit_id: str,
        text: str,
        rule_id: str | None,
        data: Mapping[str, Any],
        claim_fact_refs: tuple[str, ...] | None = None,
    ) -> None:
        evidence_ref = _exact_rule_evidence_ref(rule_id, evidence_refs)
        if evidence_ref is None or not text.strip():
            return
        base_fact_refs = (
            fact_refs if claim_fact_refs is None else claim_fact_refs
        )
        if not base_fact_refs:
            return
        grounded_fact_refs = tuple(
            dict.fromkeys(
                (
                    *base_fact_refs,
                    *evidence_supports.get(evidence_ref, ()),
                )
            )
        )
        units.append(
            {
                "ref": f"finding:{subject_ref}/bazi/public-claim/{unit_id}",
                "subject_ref": subject_ref,
                "dimension_ids": dimension_ids,
                "kind_id": "kind.tendency",
                "data": dict(data),
                "public_text": text,
                "fact_refs": grounded_fact_refs,
                "evidence_refs": (evidence_ref,),
                # Each bounded sentence carries its own explicit unresolved
                # boundary. Do not inherit a limit scoped to another
                # dimension (for example timing) into a career claim.
                "limit_kind_ids": (),
                "support_mode": "exact",
            }
        )

    strength = value.get("strength")
    if isinstance(strength, Mapping):
        day_element = strength.get("day_element")
        month_element = strength.get("month_command_element")
        seasonal_state = strength.get("seasonal_state")
        seasonal_rule_id = strength.get("seasonal_state_source_rule_id")
        if all(
            isinstance(item, str) and item
            for item in (day_element, month_element, seasonal_state)
        ):
            append_unit(
                unit_id="month-order-state",
                text=(
                    f"月令主气五行为{month_element}，日主五行{day_element}在该月令状态表中为"
                    f"“{seasonal_state}”；这只确定月令季节状态，整盘身强身弱仍未裁定。"
                ),
                rule_id=(
                    seasonal_rule_id
                    if isinstance(seasonal_rule_id, str)
                    else None
                ),
                data={
                    "claim_unit_id": "bazi.month-order-state-v1",
                    "day_element": day_element,
                    "month_command_element": month_element,
                    "seasonal_state": seasonal_state,
                    "hard_verdict": None,
                },
            )

        root_adj = strength.get("day_master_root_support_adjudication")
        if (
            isinstance(root_adj, Mapping)
            and root_adj.get("status") == "adjudicated_root_support_evidence"
        ):
            root_day = root_adj.get("day_master_element")
            root_month = root_adj.get("month_command_element")
            root_state = root_adj.get("seasonal_state")
            support_or_drain = root_adj.get("month_command_support_or_drain")
            same_count = root_adj.get("same_element_occurrences")
            resource_element = root_adj.get("resource_element")
            resource_count = root_adj.get("resource_occurrences")
            all_counts = root_adj.get("all_element_occurrences")
            root_positions = root_adj.get("same_element_root_positions")
            support_count = root_adj.get("visible_support_role_count")
            pressure_count = root_adj.get("visible_pressure_role_count")
            source = (
                root_adj.get("source_ref")
                if isinstance(root_adj.get("source_ref"), Mapping)
                else {}
            )
            pack = source.get("pack")
            local_rule = source.get("rule_id")
            root_rule_id = (
                f"{pack}#{local_rule}"
                if isinstance(pack, str)
                and pack
                and isinstance(local_rule, str)
                and local_rule
                else None
            )
            if (
                all(
                    isinstance(item, str) and item
                    for item in (
                        root_day,
                        root_month,
                        root_state,
                        support_or_drain,
                        resource_element,
                    )
                )
                and isinstance(same_count, int)
                and isinstance(resource_count, int)
                and isinstance(all_counts, Mapping)
                and all(
                    isinstance(all_counts.get(element), int)
                    for element in ("木", "火", "土", "金", "水")
                )
                and isinstance(root_positions, (list, tuple))
                and all(
                    isinstance(item, str) and item for item in root_positions
                )
                and isinstance(support_count, int)
                and isinstance(pressure_count, int)
                and root_adj.get("whole_chart_strength_verdict") is None
                and root_adj.get("useful_god_verdict") is None
            ):
                position_labels = {
                    "year": "年",
                    "month": "月",
                    "day": "日",
                    "hour": "时",
                }
                labeled = [
                    position_labels[item]
                    for item in root_positions
                    if item in position_labels
                ]
                root_clause = (
                    "同党根气未见"
                    if not labeled
                    else "同党根气在" + "、".join(labeled) + "支"
                )
                count_clause = "、".join(
                    f"{element}{all_counts[element]}"
                    for element in ("木", "火", "土", "金", "水")
                )
                append_unit(
                    unit_id="day-master-root-support",
                    text=(
                        f"日主五行{root_day}，月令主气五行为{root_month}，"
                        f"月令对日主为“{root_state}”（{support_or_drain}）；"
                        f"同党出现{same_count}处，印星{resource_element}出现"
                        f"{resource_count}处，五行计数为{count_clause}，"
                        f"{root_clause}，透干生扶{support_count}、"
                        f"克泄{pressure_count}；"
                        "这只是根气与月令生扶、克泄证据，整盘身强身弱仍未裁定，"
                        "用神与吉凶仍未裁定。"
                    ),
                    rule_id=root_rule_id,
                    data={
                        "claim_unit_id": "bazi.day-master-root-support-v1",
                        "day_element": root_day,
                        "month_command_element": root_month,
                        "seasonal_state": root_state,
                        "month_command_support_or_drain": support_or_drain,
                        "same_element_occurrences": same_count,
                        "resource_element": resource_element,
                        "resource_occurrences": resource_count,
                        "same_element_root_positions": list(root_positions),
                        "visible_support_role_count": support_count,
                        "visible_pressure_role_count": pressure_count,
                        "hard_verdict": None,
                    },
                )

    pattern_tool = tools.get("ziping_month_pattern_adjudication")
    pattern_output = (
        pattern_tool.get("output") if isinstance(pattern_tool, Mapping) else None
    )
    if isinstance(pattern_output, Mapping):
        pattern_status = pattern_output.get("status")
        pattern_label = pattern_output.get("pattern_label")
        if (
            pattern_status
            in {"adjudicated_pattern_entry", "exception_requires_external_selection"}
            and isinstance(pattern_label, str)
            and pattern_label
        ):
            if pattern_status == "adjudicated_pattern_entry":
                pattern_text = (
                    f"子平月令入口按日干与月令主气的关系确定为“{pattern_label}”；"
                    "这里只确定格局入口，格局成败、救应、旺衰和行运仍未裁定。"
                )
            else:
                pattern_text = (
                    f"月令落在“{pattern_label}”；此分支仍需另取财官煞食，"
                    "格局成败、旺衰和行运仍未裁定。"
                )
            append_unit(
                unit_id="ziping-pattern-entry",
                text=pattern_text,
                rule_id=_source_rule_id(pattern_tool),
                data={
                    "claim_unit_id": "bazi.ziping-pattern-entry-v1",
                    "status": pattern_status,
                    "pattern_label": pattern_label,
                    "hard_verdict": None,
                },
            )

    tiaohou_tool = tools.get("tiaohou_candidates")
    tiaohou_output = (
        tiaohou_tool.get("output") if isinstance(tiaohou_tool, Mapping) else None
    )
    if (
        isinstance(tiaohou_output, Mapping)
        and tiaohou_output.get("status") == "adjudicated_seasonal_priority"
    ):
        day_stem = tiaohou_output.get("day_stem")
        month_branch = tiaohou_output.get("month_branch")
        priority_stems = tiaohou_output.get("priority_stems")
        if (
            isinstance(day_stem, str)
            and day_stem
            and isinstance(month_branch, str)
            and month_branch
            and isinstance(priority_stems, (list, tuple))
            and priority_stems
            and all(isinstance(item, str) and item for item in priority_stems)
        ):
            ordered = "、".join(priority_stems)
            append_unit(
                unit_id="tiaohou-priority",
                text=(
                    f"按{day_stem}日主、{month_branch}月的已核验调候规则，候选次序为"
                    f"“{ordered}”；当前只记录候选与显藏缺失，唯一用神或吉凶仍未裁定。"
                ),
                rule_id=_source_rule_id(tiaohou_tool),
                data={
                    "claim_unit_id": "bazi.tiaohou-priority-v1",
                    "day_stem": day_stem,
                    "month_branch": month_branch,
                    "priority_stems": list(priority_stems),
                    "hard_verdict": None,
                },
            )

    pillars = (
        chart_output.get("four_pillars")
        if isinstance(chart_output, Mapping)
        else None
    )
    pillar_values: dict[str, str] = {}
    if isinstance(pillars, Mapping):
        for position in ("year", "month", "day", "hour"):
            pillar = pillars.get(position)
            if isinstance(pillar, str) and len(pillar) == 2:
                pillar_values[position] = pillar

    four_pillars_fact_ref = public_chart_fact_ref("four_pillars")
    if len(pillar_values) == 4 and four_pillars_fact_ref is not None:
        append_unit(
            unit_id="pillar-roles",
            text=(
                f"四柱以日干{pillar_values['day'][0]}为主："
                f"年柱{pillar_values['year']}为本，"
                f"月柱{pillar_values['month']}为提纲，"
                f"时柱{pillar_values['hour']}为辅佐；"
                "这只是四柱判读次序的定位，格局、旺衰与吉凶仍未裁定。"
            ),
            rule_id=_BAZI_PILLAR_ROLES_RULE_ID,
            data={
                "claim_unit_id": "bazi.pillar-roles-v1",
                "day_stem": pillar_values["day"][0],
                "year_pillar": pillar_values["year"],
                "month_pillar": pillar_values["month"],
                "day_pillar": pillar_values["day"],
                "hour_pillar": pillar_values["hour"],
                "hard_verdict": None,
            },
            claim_fact_refs=(four_pillars_fact_ref,),
        )

        hidden = (
            chart_output.get("hidden_stems")
            if isinstance(chart_output, Mapping)
            else None
        )
        hidden_by_position: dict[str, tuple[str, ...]] = {}
        if isinstance(hidden, Mapping):
            for position in ("year", "month", "day", "hour"):
                entry = hidden.get(position)
                stems = (
                    entry.get("stems") if isinstance(entry, Mapping) else None
                )
                if (
                    isinstance(stems, (list, tuple))
                    and stems
                    and all(
                        isinstance(item, str) and item for item in stems
                    )
                ):
                    hidden_by_position[position] = tuple(stems)
        hidden_stems_fact_ref = public_chart_fact_ref("hidden_stems")
        if (
            len(hidden_by_position) == 4
            and hidden_stems_fact_ref is not None
        ):
            ordered_positions = ("year", "month", "day", "hour")
            stems_clause = "、".join(
                pillar_values[position][0] for position in ordered_positions
            )
            branches_clause = "、".join(
                pillar_values[position][1] for position in ordered_positions
            )
            hidden_clause = "，".join(
                f"{_BAZI_PILLAR_POSITION_LABELS[position]}"
                f"{pillar_values[position][1]}藏"
                + "".join(hidden_by_position[position])
                for position in ordered_positions
            )
            append_unit(
                unit_id="three-yuan-structure",
                text=(
                    f"四柱天干{stems_clause}为天元；"
                    f"地支{branches_clause}为地元；"
                    f"支中所藏（{hidden_clause}）为人元；"
                    "这只是干支藏三元的结构陈列，格局与吉凶仍未裁定。"
                ),
                rule_id=_BAZI_THREE_YUAN_RULE_ID,
                data={
                    "claim_unit_id": "bazi.three-yuan-structure-v1",
                    "heavenly_stems": [
                        pillar_values[position][0]
                        for position in ordered_positions
                    ],
                    "earthly_branches": [
                        pillar_values[position][1]
                        for position in ordered_positions
                    ],
                    "hidden_stems": {
                        position: list(hidden_by_position[position])
                        for position in ordered_positions
                    },
                    "hard_verdict": None,
                },
                claim_fact_refs=(
                    four_pillars_fact_ref,
                    hidden_stems_fact_ref,
                ),
            )

    flow_strength = value.get("strength")
    if isinstance(flow_strength, Mapping):
        flow_day_element = flow_strength.get("day_element")
        flow_resource_element = flow_strength.get("resource_element")
        flow_counts = flow_strength.get("all_element_occurrences")
        if (
            all(
                isinstance(item, str) and item
                for item in (flow_day_element, flow_resource_element)
            )
            and isinstance(flow_counts, Mapping)
            and all(
                isinstance(flow_counts.get(element), int)
                for element in ("木", "火", "土", "金", "水")
            )
        ):
            count_clause = "、".join(
                f"{element}{flow_counts[element]}"
                for element in ("木", "火", "土", "金", "水")
            )
            append_unit(
                unit_id="element-flow-inventory",
                text=(
                    f"盘中五行（含支藏）出现次数为{count_clause}；"
                    f"五行顺则相生、逆则相克，日主五行为{flow_day_element}，"
                    f"生{flow_day_element}者为{flow_resource_element}；"
                    "这只是五行计数与生克次序的陈列，"
                    "整盘旺衰、喜忌与吉凶仍未裁定。"
                ),
                rule_id=_BAZI_ELEMENT_FLOW_RULE_ID,
                data={
                    "claim_unit_id": "bazi.element-flow-inventory-v1",
                    "day_element": flow_day_element,
                    "resource_element": flow_resource_element,
                    "all_element_occurrences": {
                        element: flow_counts[element]
                        for element in ("木", "火", "土", "金", "水")
                    },
                    "hard_verdict": None,
                },
            )

    return tuple(units)


_BAZI_PRIVATE_PROJECTION_KEYS = frozenset(
    {
        "binding_digest",
        "fact_paths",
        "fact_refs",
        "predicate_audit",
        "rule_record_digest",
        "source_ref",
        "source_refs",
        "tool_digest",
    }
)


def _bazi_public_projection_value(
    value: Any,
    *,
    preserve_pattern_audit: bool = False,
) -> Any:
    """Strip internal evidence plumbing while preserving candidate facts."""

    if isinstance(value, Mapping):
        return {
            str(key): _bazi_public_projection_value(
                item,
                preserve_pattern_audit=(
                    preserve_pattern_audit
                    or str(key) == "source_conditioned_patterns"
                ),
            )
            for key, item in value.items()
            if key not in _BAZI_PRIVATE_PROJECTION_KEYS
            or (
                preserve_pattern_audit
                and key in {"fact_paths", "predicate_audit"}
            )
        }
    if isinstance(value, list):
        return [
            _bazi_public_projection_value(
                item,
                preserve_pattern_audit=preserve_pattern_audit,
            )
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            _bazi_public_projection_value(
                item,
                preserve_pattern_audit=preserve_pattern_audit,
            )
            for item in value
        )
    return copy.deepcopy(value)


def _declared_public_findings(
    descriptor: ProviderDescriptor,
    calculation: CalculationResult,
    *,
    subject_ref: str,
    dimension_ids: tuple[str, ...],
    horizon_kind_id: str,
    fact_refs: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    evidence_supports: Mapping[str, tuple[str, ...]],
    limit_kind_ids: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    """Project provider-declared drafting material from a calculation.

    The generic seam does not interpret the values or name a provider.  A
    manifest chooses the stable id, public kind, supported horizons and JSON
    pointer. This is optional drafting material: a stale declaration is
    skipped so it cannot discard an already-valid deterministic calculation.
    Release auditing validates declarations before they are shipped.
    """

    runtime = descriptor.canonical_payload.get("runtime_capability")
    if not isinstance(runtime, Mapping):
        return ()
    bindings = runtime.get("finding_bindings") or ()
    if not bindings:
        return ()
    payload = calculation.to_dict()
    findings: list[dict[str, Any]] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        binding_id = binding.get("id")
        kind_id = binding.get("kind_id")
        if (
            not isinstance(binding_id, str)
            or not binding_id
            or not isinstance(kind_id, str)
            or not kind_id
        ):
            continue
        declared_horizons = binding.get("horizons")
        if declared_horizons is not None:
            horizons = _optional_string_tuple(declared_horizons)
            if horizons is None:
                continue
            if horizon_kind_id not in horizons:
                continue
        declared_dimensions = binding.get("dimension_ids")
        if declared_dimensions is None:
            effective_dimensions = dimension_ids
        else:
            binding_dimensions = _optional_string_tuple(declared_dimensions)
            if binding_dimensions is None:
                continue
            effective_dimensions = tuple(
                dimension
                for dimension in dimension_ids
                if dimension in binding_dimensions
            )
            if not effective_dimensions:
                continue
        pointers = _optional_string_tuple(binding.get("json_pointers"))
        if not pointers or not all(
            _is_public_projection_pointer(pointer) for pointer in pointers
        ):
            continue
        found = False
        value: Any = None
        for pointer in pointers:
            found, value = _json_pointer_value(payload, pointer)
            if found:
                break
        if not found:
            # A finding enriches an already valid deterministic result.  A
            # calculation variant may legitimately omit this optional shape;
            # never turn that into a delivery blocker.  Release tests pin
            # the required variants for each declared provider projection.
            continue
        claim_source_value = value
        if descriptor.id == "bazi" and binding_id == "interpretive_candidates":
            value = _bazi_public_projection_value(value)
        support_mode = "shared_turn"
        finding_fact_refs = fact_refs
        finding_evidence_refs = evidence_refs
        support_fact_ids = binding.get("support_fact_ids")
        if support_fact_ids is not None:
            declared_support_ids = _optional_string_tuple(support_fact_ids)
            if declared_support_ids:
                candidate_refs = tuple(
                    f"fact:{subject_ref}/calculated/{descriptor.id}/{item}"
                    for item in declared_support_ids
                )
                if set(candidate_refs) <= set(fact_refs):
                    support_mode = "exact"
                    finding_fact_refs = candidate_refs
                    finding_evidence_refs = ()
        findings.append(
            {
                "ref": f"finding:{subject_ref}/{descriptor.id}/{binding_id}",
                "subject_ref": subject_ref,
                "dimension_ids": effective_dimensions,
                "kind_id": kind_id,
                "data": value,
                "fact_refs": finding_fact_refs,
                "evidence_refs": finding_evidence_refs,
                "limit_kind_ids": limit_kind_ids,
                "support_mode": support_mode,
            }
        )
        if descriptor.id == "bazi" and binding_id == "interpretive_candidates":
            chart_found, chart_output = _json_pointer_value(
                payload, "/facts/chart_facts/output"
            )
            findings.extend(
                _bazi_public_claim_findings(
                    claim_source_value,
                    subject_ref=subject_ref,
                    dimension_ids=effective_dimensions,
                    fact_refs=finding_fact_refs,
                    public_fact_refs=fact_refs,
                    evidence_refs=evidence_refs,
                    evidence_supports=evidence_supports,
                    chart_output=(
                        chart_output
                        if chart_found and isinstance(chart_output, Mapping)
                        else None
                    ),
                )
            )
    return tuple(findings)


def _unresolved_boundary_limit(
    calculation: CalculationResult,
) -> dict[str, Any] | None:
    """Project one unresolved boundary signal from shared calendar facts.

    Calculations may contain more than one calendar (for example a natal
    layer plus a civil target period), so discovery is structural rather than
    tied to a provider id or a private path.  Public wording is resolved later
    from the versioned message catalog, never embedded in generic code.
    """

    def unresolved_boundary(value: Any) -> Mapping[str, Any] | None:
        if isinstance(value, Mapping):
            if value.get("schema_version") == calendar_core.SCHEMA_VERSION:
                time_basis = value.get("time_basis")
                boundary = (
                    time_basis.get("boundary")
                    if isinstance(time_basis, Mapping)
                    else None
                )
                if isinstance(boundary, Mapping) and boundary.get(
                    "within_uncertainty"
                ):
                    return boundary
            for child in value.values():
                found = unresolved_boundary(child)
                if found is not None:
                    return found
        elif isinstance(value, (list, tuple)):
            for child in value:
                found = unresolved_boundary(child)
                if found is not None:
                    return found
        return None

    boundary = unresolved_boundary(calculation.facts)
    if boundary is None:
        return None
    distance = boundary.get("distance_seconds")
    detail = ("within_uncertainty",) if distance is None else (
        "within_uncertainty", f"distance_seconds={distance}",
    )
    return {
        "kind_id": "limit.unresolved_time_boundary",
        "detail_ids": tuple(str(item) for item in detail),
    }


def _declared_public_limits(
    descriptor: ProviderDescriptor,
    calculation: CalculationResult,
) -> tuple[dict[str, Any], ...]:
    """Publish provider-declared boundaries without interpreting their data."""

    runtime = descriptor.canonical_payload.get("runtime_capability")
    if not isinstance(runtime, Mapping):
        return ()
    bindings = runtime.get("limit_bindings") or ()
    if not bindings:
        return ()
    payload = calculation.to_dict()
    limits: list[dict[str, Any]] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        kind_id = binding.get("kind_id")
        pointer = binding.get("json_pointer")
        if (
            not isinstance(kind_id, str)
            or not kind_id
            or not isinstance(pointer, str)
            or not pointer
            or "equals" not in binding
            or not _is_public_projection_pointer(pointer)
        ):
            continue
        found, value = _json_pointer_value(payload, pointer)
        if not found or value != binding["equals"]:
            continue
        scope_refs = binding.get("scope_refs") or ()
        detail_ids = binding.get("detail_ids") or ()
        scope_refs = _optional_string_tuple(scope_refs)
        detail_ids = _optional_string_tuple(detail_ids)
        if scope_refs is None or detail_ids is None:
            continue
        limits.append(
            {
                "kind_id": kind_id,
                "public_text": (
                    _descriptor_term_label(descriptor, kind_id) or kind_id
                ),
                "scope_refs": tuple(scope_refs),
                "detail_ids": tuple(detail_ids),
            }
        )
    return tuple(limits)


def _declared_request_view_horizon(
    descriptor: ProviderDescriptor,
    calculation: CalculationResult,
    fallback: Mapping[str, Any],
) -> dict[str, Any]:
    """Use a provider-owned public effective horizon when it is available.

    A host receives the calculated range (for example an implicit period) but
    generic code never knows how that range was derived. A malformed or
    absent optional declaration retains the original public request.
    """

    resolved = {
        "kind": str(fallback.get("kind") or ""),
        "start": fallback.get("start"),
        "end": fallback.get("end"),
    }
    runtime = descriptor.canonical_payload.get("runtime_capability")
    if not isinstance(runtime, Mapping):
        return resolved
    binding = runtime.get("request_view_horizon_binding")
    if not isinstance(binding, Mapping):
        return resolved
    pointer = binding.get("json_pointer")
    if not _is_public_projection_pointer(pointer):
        return resolved
    found, value = _json_pointer_value(calculation.to_dict(), str(pointer))
    if not found or not isinstance(value, Mapping):
        return resolved
    kind = value.get("kind_id", value.get("kind", resolved["kind"]))
    start = value.get("start", resolved["start"])
    end = value.get("end", resolved["end"])
    if not isinstance(kind, str) or not kind:
        return resolved
    if start is not None and not isinstance(start, str):
        return resolved
    if end is not None and not isinstance(end, str):
        return resolved
    return {"kind": kind, "start": start, "end": end}


class _AdapterSeam:
    """Descriptor-bound production seam: one ``prepare`` call per turn.

    Generic code only ever sees ``descriptor`` plus ``prepare``.  Slot
    assembly, default profiles, injected clocks, casting, evidence
    retrieval and the public projection all stay inside the provider that
    owns them; nothing here leaks a private artifact.
    """

    _bound_descriptor: ProviderDescriptor | None = None
    _bound_capability: ProviderCapability | None = None

    def bind_descriptor(self, descriptor: ProviderDescriptor) -> None:
        self._bound_descriptor = descriptor
        self._bound_capability = _capability_from_descriptor(descriptor)

    @property
    def capability(self) -> ProviderCapability:
        if self._bound_capability is not None:
            return self._bound_capability
        system = _CAPABILITY_SYSTEM_BY_ADAPTER.get(type(self).__name__)
        if system is None:
            raise ProviderActionError(
                "descriptor_unbound",
                f"{type(self).__name__} has no catalog capability",
            )
        return PROVIDER_CAPABILITIES[system]

    @property
    def descriptor(self) -> ProviderDescriptor:
        descriptor = self._bound_descriptor
        if descriptor is None:
            raise ProviderActionError(
                "descriptor_unbound",
                f"{type(self).__name__} has no bound catalog descriptor",
            )
        return descriptor

    def _missing_time_basis_inputs(
        self, request: ReadingRequest
    ) -> tuple[str, ...]:
        """Coordinate fields a declared time-basis policy requires but lacks.

        Driven entirely by the provider's own manifest time_semantics block, so
        the generic core never branches on provider id. When the selected
        policy needs measured coordinates and they are absent, the prepare()
        path surfaces a structured, non-empty NeedInput instead of silently
        falling back to civil time or crashing inside the calendar.
        """

        semantics = self.descriptor.canonical_payload.get("time_semantics")
        if not isinstance(semantics, dict):
            return ()
        if str(semantics.get("role") or "") in ("", "not_applicable"):
            return ()
        required = semantics.get("coordinates_required_policies") or ()
        policy, longitude, latitude, source = _request_time_basis(request)
        if policy not in set(required):
            return ()
        missing: list[str] = []
        if longitude is None or latitude is None:
            missing.extend(("longitude", "latitude"))
        if not str(source or "").strip():
            missing.append("coordinate_source")
        return tuple(missing)

    def _unsupported_time_basis_policy(
        self, request: ReadingRequest
    ) -> str | None:
        """Explicitly requested policy this provider does not support, or None.

        Prevents silent downgrade: a civil-only provider that receives an
        apparent-solar policy returns a clear Unsupported instead of ignoring
        it. Driven by the manifest time_semantics, not a per-provider branch.
        """

        semantics = self.descriptor.canonical_payload.get("time_semantics")
        if not isinstance(semantics, dict):
            return None
        if str(semantics.get("role") or "") in ("", "not_applicable"):
            return None
        supported = set(semantics.get("supported_policies") or ())
        birth = request.birth_data if isinstance(request.birth_data, dict) else {}
        meta = request.metadata if isinstance(request.metadata, dict) else {}
        explicit = birth.get("time_basis_policy") or meta.get("time_basis_policy")
        if explicit is None:
            return None
        policy = str(explicit)
        return policy if policy not in supported else None

    def prepare(
        self,
        request: ProviderRequest,
        context: ProviderContext,
    ) -> ProviderPreparation | ProviderNeedInput | ProviderUnsupported:
        descriptor = self.descriptor
        subject_refs = tuple(request.subject_refs) or ("current_user",)
        if len(subject_refs) != 1:
            raise ProviderActionError(
                "subject_scope",
                "one provider preparation must bind exactly one subject",
            )
        primary_subject = subject_refs[0]
        merged_facts = self._merged_subject_facts(
            descriptor, request, context, subject_refs
        )
        dimensions = self._effective_dimensions(descriptor, request)
        lineage = (
            context.prior_lineage
            if isinstance(context.prior_lineage, Mapping)
            else {}
        )
        action = str(lineage.get("action") or "new")
        legacy = self._legacy_request(
            descriptor,
            request,
            merged_facts,
            primary_subject,
            dimensions,
            action,
        )
        enrich = getattr(self, "enrich_request", None)
        if enrich is not None:
            legacy = enrich(
                legacy,
                RuntimeContext(
                    now_iso=context.now_iso,
                    default_timezone_name=context.default_timezone,
                    subject_profiles={
                        str(subject): dict(fields)
                        for subject, fields in context.subject_facts.items()
                    },
                ),
                routed=True,
            )
        legacy = self._clock_defaults(descriptor, legacy, context)
        reject_hook = getattr(self, "reject_reserved_request_fields", None)
        if reject_hook is not None:
            # Providers own their reserved field rules; a violation fails the
            # turn before anything is staged.
            reject_hook(legacy)
        unsupported_hook = getattr(self, "unsupported_request", None)
        if unsupported_hook is not None:
            reason_id = unsupported_hook(legacy)
            if reason_id:
                return ProviderUnsupported(reason_id=str(reason_id))
        unsupported_policy = self._unsupported_time_basis_policy(legacy)
        if unsupported_policy is not None:
            return ProviderUnsupported(
                reason_id="unsupported_time_basis_policy"
            )
        missing = tuple(self.missing_required_inputs(legacy))
        missing += self._missing_time_basis_inputs(legacy)
        if missing:
            return ProviderNeedInput(
                missing_input_groups=tuple((field,) for field in missing)
            )
        provider_request = legacy
        cast_hook = getattr(self, "inject_transaction_cast", None)
        if cast_hook is not None:
            seed = None
            prior_calculation = None
            if isinstance(context.prior_lineage, Mapping):
                prior_calculation = context.prior_lineage.get(
                    "prior_calculation"
                )
            if prior_calculation is not None:
                guard = getattr(self, "correction_replaces_cast", None)
                if guard is not None:
                    message = guard(prior_calculation, legacy)
                    if message:
                        raise ProviderActionError(
                            "action_requires_recast", message
                        )
                seed_hook = getattr(
                    self, "persisted_transaction_cast_seed", None
                )
                if seed_hook is not None:
                    seed = seed_hook(prior_calculation)
            provider_request = cast_hook(legacy, seed)
        prior_calculation = lineage.get("prior_calculation")
        if action == "continue" and isinstance(
            prior_calculation, CalculationResult
        ) and prior_calculation.system == descriptor.id:
            refine = getattr(self, "refine", None)
            calculation = (
                refine(provider_request, prior_calculation)
                if callable(refine)
                else self.calculate(provider_request)
            )
        else:
            calculation = self.calculate(provider_request)
        if calculation.system != descriptor.id:
            raise ProviderActionError(
                "wrong_system", "provider returned the wrong system"
            )
        # Everything past the calculation works from the pre-injection
        # request: turn-scoped private material (such as an injected cast
        # seed) must never reach the staged request or evidence plan.
        calculation = self._extended_calculation(legacy, calculation)
        public_horizon = _declared_request_view_horizon(
            descriptor, calculation, request.horizon
        )
        # An extension that cannot bind the requested horizon never blocks
        # the turn: its dimensions surface as unsupported verdicts in the
        # staged judgment while the deterministic base facts stay usable.
        intent_digest = canonical_digest(legacy.intent)
        bundle, basis_label = self._bound_evidence(
            legacy, calculation, intent_digest
        )
        public_facts, public_provenance = self._public_facts(
            descriptor,
            calculation,
            merged_facts,
            primary_subject,
        )
        public_evidence = self._public_evidence(
            bundle,
            capability_id=descriptor.id,
            provenance=public_provenance,
        )
        policy = descriptor.claim_policy
        allowed_kind_ids = tuple(
            str(kind) for kind in policy["allowed_kind_ids"]
        )
        fact_refs = tuple(fact["ref"] for fact in public_facts)
        evidence_refs = tuple(item["ref"] for item in public_evidence)
        claim_scopes = tuple(
            {
                "subject_ref": primary_subject,
                "dimension_id": str(dimension),
                "allowed_kind_ids": allowed_kind_ids,
                "certainty_ceiling_id": str(policy["certainty_ceiling_id"]),
                "fact_refs": fact_refs,
                "evidence_refs": evidence_refs,
            }
            for dimension in dimensions
        )
        limits: tuple[dict[str, Any], ...] = ()
        # ``no_applicable_counter_evidence`` is retained in the private
        # EvidenceBundle for audit, but it does not mean that the public
        # supporting-source lane is empty.  Publishing the generic
        # source-gap label in that case contradicts a non-empty
        # ``brief.evidence`` collection ("no citable source" beside actual
        # citations).  Only a genuinely empty supporting lane is a public
        # source gap.
        if not bundle.evidence:
            limits = (
                {
                    "kind_id": "limit.source_gap",
                    "public_text": (
                        _descriptor_term_label(descriptor, "limit.source_gap")
                        or "limit.source_gap"
                    ),
                    "detail_ids": tuple(
                        str(gap.reason)
                        for gap in bundle.source_gaps
                        if str(gap.reason) == "zero_applicable_evidence"
                    ),
                },
            )
        limits = (*limits, *_declared_public_limits(descriptor, calculation))
        boundary_limit = _unresolved_boundary_limit(calculation)
        if boundary_limit is not None:
            limits = (*limits, boundary_limit)
        findings = _declared_public_findings(
            descriptor,
            calculation,
            subject_ref=primary_subject,
            dimension_ids=dimensions,
            horizon_kind_id=str(request.horizon.get("kind") or ""),
            fact_refs=fact_refs,
            evidence_refs=evidence_refs,
            evidence_supports={
                str(item["ref"]): tuple(
                    str(ref) for ref in item.get("supports_fact_refs") or ()
                )
                for item in public_evidence
            },
            limit_kind_ids=tuple(
                str(limit["kind_id"]) for limit in limits
            ),
        )
        return ProviderPreparation(
            calculation=calculation,
            public_facts=tuple(public_facts),
            fact_index=(),
            evidence_plan={
                "bundle": bundle,
                "evidence": tuple(public_evidence),
                "request": legacy,
                "reading_id": str(legacy.reading_id),
                "intent_digest": intent_digest,
                "basis_label": basis_label,
                "version": int(request.version),
            },
            claim_scopes=claim_scopes,
            limits=limits,
            provider_id=str(self.provider_id),
            provider_version=str(self.provider_version),
            subject_ref=primary_subject,
            capability_id=descriptor.id,
            independent_lineage_id=descriptor.capability.independent_lineage_id,
            request_view={
                "subject_refs": (primary_subject,),
                "capability_ids": (descriptor.id,),
                "object_id": request.object_id,
                "dimension_ids": tuple(dimensions),
                "horizon": {
                    "kind_id": str(public_horizon.get("kind") or ""),
                    "start": public_horizon.get("start"),
                    "end": public_horizon.get("end"),
                },
            },
            findings=findings,
        )

    # -- private assembly steps --------------------------------------------

    @staticmethod
    def _merged_subject_facts(
        descriptor: ProviderDescriptor,
        request: ProviderRequest,
        context: ProviderContext,
        subject_refs: tuple[str, ...],
    ) -> dict[str, dict[str, Any]]:
        declared = descriptor.input_field_ids()
        merged: dict[str, dict[str, Any]] = {}
        for subject in subject_refs:
            fields = {
                str(field_id): value
                for field_id, value in (
                    request.facts.get(subject) or {}
                ).items()
                if str(field_id) in declared
            }
            defaults = context.subject_facts.get(subject) or {}
            for field_id in declared:
                if field_id not in fields and field_id in defaults:
                    fields[field_id] = defaults[field_id]
            merged[subject] = fields
        for subject, fields in request.facts.items():
            if subject not in merged and fields:
                merged[str(subject)] = dict(fields)
        return merged

    @staticmethod
    def _effective_dimensions(
        descriptor: ProviderDescriptor,
        request: ProviderRequest,
    ) -> tuple[str, ...]:
        dimensions = tuple(str(item) for item in request.dimension_ids)
        if dimensions:
            return dimensions
        capability = descriptor.capability
        return tuple(
            capability.default_dimension_ids or capability.dimension_ids
        )

    @staticmethod
    def _legacy_request(
        descriptor: ProviderDescriptor,
        request: ProviderRequest,
        merged_facts: Mapping[str, Mapping[str, Any]],
        primary_subject: str,
        dimensions: tuple[str, ...],
        action: str,
    ) -> ReadingRequest:
        horizon = dict(request.horizon or {})
        horizon_kind = str(horizon.get("kind") or horizon.get("kind_id") or "")
        intent_payload: dict[str, Any] = {
            "subject_refs": [
                str(subject)
                for subject in (
                    request.scope_subject_refs or request.subject_refs
                )
            ],
            "calculation_object": request.object_id,
            "question_dimensions": list(dimensions),
            "horizon": {
                "kind": horizon_kind,
                "start": horizon.get("start"),
                "end": horizon.get("end"),
            },
            "requested_method": descriptor.id,
            "requested_granularity": horizon_kind,
            "continuity": {
                "reading_id": (
                    str(request.reading_id) if action != "new" else None
                ),
                "same_subject": action != "new",
                "same_event": action == "continue",
            },
            "facts_present": sorted(
                str(field)
                for field in (merged_facts.get(primary_subject) or {})
            ),
            "facts_corrected": [],
            "evidence_questions": [request.query],
        }
        request_values: dict[str, Any] = {
            "query": request.query,
            "action": action,
            "system": descriptor.id,
            "reading_id": request.reading_id or uuid.uuid4().hex,
            "transaction_version": int(request.version),
            "intent": intent_payload,
            "goal": {
                "use_default_profile": True,
                "subject": primary_subject,
            },
        }
        raw_fields = descriptor.canonical_payload.get("input_fields")
        slots: Mapping[str, Any] = (
            raw_fields if isinstance(raw_fields, Mapping) else {}
        )
        for field_id, value in (merged_facts.get(primary_subject) or {}).items():
            field_spec = slots.get(str(field_id))
            slot_spec = (
                field_spec.get("request_slot")
                if isinstance(field_spec, Mapping)
                else None
            )
            _assign_request_slot(
                request_values, str(field_id), slot_spec, value
            )
        return ReadingRequest(**request_values)

    @staticmethod
    def _clock_defaults(
        descriptor: ProviderDescriptor,
        legacy: ReadingRequest,
        context: ProviderContext,
    ) -> ReadingRequest:
        declared = descriptor.input_field_ids()
        changes: dict[str, Any] = {}
        has_moment = bool(legacy.reference_datetime or legacy.event_datetime)
        if not has_moment and context.now_iso:
            if "reference_datetime" in declared:
                changes["reference_datetime"] = context.now_iso
            elif "event_datetime" in declared:
                changes["event_datetime"] = context.now_iso
        if (
            "timezone" in declared
            and not legacy.timezone
            and context.default_timezone
        ):
            changes["timezone"] = context.default_timezone
        legacy = _with_request_changes(legacy, changes)

        semantics = descriptor.canonical_payload.get("time_semantics")
        birth = legacy.birth_data if isinstance(legacy.birth_data, dict) else {}
        metadata = legacy.metadata if isinstance(legacy.metadata, dict) else {}
        explicit_policy = (
            birth.get("time_basis_policy")
            or metadata.get("time_basis_policy")
        )
        request_payload: Any = legacy.to_dict()
        declared_time: Any = request_payload
        input_time_path = (
            str(semantics.get("input_time") or "")
            if isinstance(semantics, Mapping)
            else ""
        )
        for part in input_time_path.split(".") if input_time_path else ():
            declared_time = (
                declared_time.get(part)
                if isinstance(declared_time, Mapping)
                else None
            )
        if (
            explicit_policy is None
            and declared_time not in (None, "")
            and isinstance(semantics, Mapping)
            and str(semantics.get("role") or "") not in ("", "not_applicable")
            and str(semantics.get("default_policy") or "").strip()
        ):
            input_fields = descriptor.canonical_payload.get("input_fields")
            policy_field = (
                input_fields.get("time_basis_policy")
                if isinstance(input_fields, Mapping)
                else None
            )
            if isinstance(policy_field, Mapping):
                request_values = legacy.to_dict()
                _assign_request_slot(
                    request_values,
                    "time_basis_policy",
                    policy_field.get("request_slot"),
                    str(semantics["default_policy"]),
                )
                legacy = ReadingRequest(**request_values)
        return legacy

    def _extended_calculation(
        self,
        request: ReadingRequest,
        calculation: CalculationResult,
    ) -> CalculationResult:
        frame = IntentFrame.from_dict(request.intent)
        extended = self.extend(
            calculation.base(),
            frame.question_dimensions,
            _resolve_extension_horizon(
                frame.horizon.to_dict(),
                request.reference_datetime,
            ),
        )
        if extended.result_hash != calculation.base().result_hash:
            raise ProviderActionError(
                "extension_digest_changed",
                "fact extension changed the base calculation digest",
            )
        if extended.fact_extension is None:
            raise ProviderActionError(
                "extension_missing", "provider returned no fact extension"
            )
        return extended

    def _bound_evidence(
        self,
        request: ReadingRequest,
        calculation: CalculationResult,
        intent_digest: str,
    ) -> tuple[EvidenceBundle, str]:
        reading_id = str(request.reading_id)
        version = int(request.transaction_version or 1)
        goal = _adapter_evidence_goal(request)
        payload = indexed_fact_payload(calculation)
        plan = reading_source_plan.compile_source_plan(
            calculation.system, goal, payload
        )
        fact_index = build_fact_index(
            calculation, reading_id=reading_id, version=version
        )
        bundle = reading_evidence_bundle.compile_evidence_bundle(
            goal,
            payload,
            plan,
            fact_index=fact_index,
            reading_id=reading_id,
            version=version,
        )
        fact_ids = {item.fact_id for item in fact_index}

        def bind(node):
            if node.reading_id and node.reading_id != reading_id:
                raise ProviderActionError(
                    "evidence_binding",
                    "evidence compiler returned cross-reading evidence",
                )
            if not set(node.fact_refs) <= fact_ids:
                raise ProviderActionError(
                    "evidence_binding",
                    "evidence compiler returned an unknown fact reference",
                )
            return replace(node, reading_id=reading_id, version=version)

        bound = EvidenceBundle.create(
            system=bundle.system,
            evidence=tuple(bind(item) for item in bundle.evidence),
            counter_evidence=tuple(
                bind(item) for item in bundle.counter_evidence
            ),
            source_relationships=bundle.source_relationships,
            source_gaps=bundle.source_gaps,
            intent_digest=intent_digest,
        )
        chart_contract = plan.get("chart_contract") or {}
        basis_label = str(chart_contract.get("label") or "确定性事实")
        return bound, basis_label

    def _public_facts(
        self,
        descriptor: ProviderDescriptor,
        calculation: CalculationResult,
        merged_facts: Mapping[str, Mapping[str, Any]],
        primary_subject: str,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """Return the public facts and the internal origin-to-public-ref map.

        The provenance map exists only inside this calculation: every public
        calculated fact carries the engine-internal origin prefix(es) it was
        projected from.  The map is never added to the external ``PublicFact``
        interface and never leaks a private chart path to the host.
        """
        policy = descriptor.claim_policy
        kind_id = str(policy["allowed_kind_ids"][0])
        project_inputs = getattr(self, "project_known_chart_data", None)
        facts_by_ref: dict[str, dict[str, Any]] = {}
        for subject in merged_facts:
            fields = dict(merged_facts[subject])
            if project_inputs is not None:
                # Providers with private caller provenance own the public
                # projection of their supplied fields.
                projected = project_inputs(fields)
                if isinstance(projected, Mapping):
                    fields = {
                        key: projected[key]
                        for key in fields
                        if key in projected
                    }
            for field_id in sorted(fields):
                value = fields[field_id]
                ref = f"fact:{subject}/input/{field_id}"
                label = _input_field_label(descriptor, str(field_id))
                facts_by_ref[ref] = {
                    "ref": ref,
                    "subject_ref": subject,
                    "kind_id": kind_id,
                    "value": value,
                    "display_text": (
                        f"{label}：{_compact_public_value(value)}"
                    ),
                }
        chart_facts = calculation.facts.get("chart_facts")
        if not isinstance(chart_facts, dict):
            chart_facts = calculation.facts
        projection_hook = getattr(self, "public_basis_projection", None)
        if projection_hook is not None:
            visible = projection_hook(chart_facts)
            # Provider-specific hooks may redact or bound the base chart, but
            # they must not silently discard manifest-declared extension
            # outputs. The manifest is the public contract for those fields.
            declared = _declared_output_projection(descriptor, calculation)
            if isinstance(visible, Mapping):
                visible = {**declared, **dict(visible)}
            else:
                visible = declared
        else:
            visible = chart_facts.get("output")
            declared = _declared_output_projection(descriptor, calculation)
            if isinstance(visible, Mapping):
                visible = {
                    **dict(visible),
                    **declared,
                }
            else:
                visible = declared
        if not isinstance(visible, Mapping):
            visible = {}
        provenance: dict[str, str] = self._public_fact_provenance(
            descriptor,
            visible,
            primary_subject,
        )
        for key in sorted(visible):
            ref = f"fact:{primary_subject}/calculated/{descriptor.id}/{key}"
            label = _descriptor_term_label(descriptor, str(key)) or str(key)
            facts_by_ref[ref] = {
                "ref": ref,
                "subject_ref": primary_subject,
                "kind_id": kind_id,
                "value": visible[key],
                "display_text": (
                    f"{label}：{_compact_public_value(visible[key])}"
                ),
            }
        return list(facts_by_ref.values()), provenance

    def _public_fact_provenance(
        self,
        descriptor: ProviderDescriptor,
        visible: Mapping[str, Any],
        primary_subject: str,
    ) -> dict[str, str]:
        """Bind each public calculated key to its declared internal origin.

        Origins come only from manifest output/extension bindings (JSON
        pointers).  A custom projection changes presentation, never the
        provenance vocabulary.  Visibility alone never declares provenance,
        and nothing here interprets a path segment's name or branches on a
        provider id.
        """
        runtime = descriptor.canonical_payload.get("runtime_capability")
        binding_origins: dict[str, set[str]] = {}
        if isinstance(runtime, Mapping):
            for group in ("output_bindings", "extension_output_bindings"):
                for binding in runtime.get(group) or ():
                    name = binding.get("name")
                    if not isinstance(name, str) or not name:
                        continue
                    for pointer in binding.get("json_pointers") or ():
                        origin = _binding_pointer_to_index_origin(str(pointer))
                        if origin is not None:
                            binding_origins.setdefault(name, set()).add(origin)
        provenance: dict[str, str] = {}
        for key in visible:
            str_key = str(key)
            ref = f"fact:{primary_subject}/calculated/{descriptor.id}/{str_key}"
            candidates: set[str] = set(binding_origins.get(str_key, ()))
            for origin in candidates:
                provenance.setdefault(origin, ref)
        return provenance

    @staticmethod
    def _public_evidence(
        bundle: EvidenceBundle,
        *,
        capability_id: str,
        provenance: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        """Project evidence to the host with only declared fact references.

        ``EvidenceNode.fact_refs`` are engine-internal deep chart paths such
        as ``fact:/chart_facts/output/day_master/element``.  Each internal
        path is matched against the public fact's declared origin prefix:
        exactly equal, or a ``/``-bounded ancestor of the internal path.
        When several origins match, the longest declared prefix wins.  Deep
        facts with no declared public origin are omitted rather than leaked
        as internal paths or guessed from a path segment.
        """

        items: dict[str, dict[str, Any]] = {}
        for node in bundle.evidence:
            supports: list[str] = []
            for internal_ref in node.fact_refs:
                text = str(internal_ref)
                if not text.startswith("fact:"):
                    continue
                path = text[len("fact:"):]
                best: tuple[int, str] | None = None
                for origin, public_ref in provenance.items():
                    if path == origin or path.startswith(origin + "/"):
                        if best is None or len(origin) > best[0]:
                            best = (len(origin), public_ref)
                if best is not None and best[1] not in supports:
                    supports.append(best[1])
            citations = tuple(getattr(node, "exact_citations", ()) or ())
            normalized_citations: list[dict[str, str]] = []
            for citation in citations:
                if not isinstance(citation, Mapping):
                    normalized_citations = []
                    break
                verification_status = citation.get("verification_status")
                verbatim_excerpt = citation.get("verbatim_excerpt")
                source_title = citation.get("source_title")
                locator = citation.get("locator")
                rule_id = citation.get("rule_id")
                # Every field below is required by the exact public
                # evidence contract.  In particular, never fall back to
                # node.assertion/node.anchor: those are distilled rule data,
                # not necessarily the original classical passage.
                if (
                    verification_status != "verified_exact"
                    or not isinstance(verbatim_excerpt, str)
                    or not verbatim_excerpt.strip()
                    or not isinstance(source_title, str)
                    or not source_title.strip()
                    or not isinstance(locator, str)
                    or not locator.strip()
                    or rule_id != node.rule_id
                    or not isinstance(rule_id, str)
                    or not rule_id.strip()
                ):
                    normalized_citations = []
                    break
                normalized_citations.append(
                    {
                        "verification_status": verification_status,
                        "verbatim_excerpt": verbatim_excerpt,
                        "source_title": source_title,
                        "locator": locator,
                        "rule_id": rule_id,
                    }
                )
            if not normalized_citations:
                # A rule with no complete set of exact originals is not
                # partially citable.  This preserves the source list without
                # guessing which month/source was intended.
                continue
            first = normalized_citations[0]
            ref = f"evidence:{capability_id}/{node.rule_id}"
            if ref in items:
                continue
            items[ref] = {
                "ref": ref,
                "evidence_ref": ref,
                "verification_status": "verified_exact",
                "verbatim_excerpt": first["verbatim_excerpt"],
                "source_title": first["source_title"],
                "locator": first["locator"],
                "rule_id": node.rule_id,
                # Keep the legacy transport key, but only as the exact
                # original text already admitted above.
                "excerpt": first["verbatim_excerpt"],
                "verbatim_citations": tuple(normalized_citations),
                "supports_fact_refs": tuple(supports),
            }
        return list(items.values())


class _SourceRouteMixin:
    """Provider-owned classical source route data behind one generic seam."""

    SOURCE_ROUTE: dict[str, Any] = {}

    def source_route(
        self,
        goal: Mapping[str, Any],
        facts: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        route = copy.deepcopy(dict(self.SOURCE_ROUTE))
        route["provider_identity"] = {
            "provider_id": self.provider_id,
            "provider_version": str(self.provider_version),
        }
        return route

    def source_plan(
        self,
        goal: Mapping[str, Any],
        facts: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(goal, Mapping):
            raise ValueError("source planning goal must be an object")
        return reading_source_plan.compile_plan(
            self.source_route(goal, facts),
            dict(goal),
            dict(facts) if isinstance(facts, Mapping) else facts,
            extend=getattr(self, "extend_source_plan", None),
        )


# ---- Bazi-owned Qiongtong applicability data (provider locality) ----

QIONGTONG_MATRIX_PATH = (
    Path(__file__).resolve().parents[2]
    / "references/matrices/qiongtong-applicability.yaml"
)
QIONGTONG_MATRIX_RELATIVE = "references/matrices/qiongtong-applicability.yaml"
_STEM_ELEMENT = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
_QIONGTONG_MATRIX_CACHE: dict[str, Any] | None = None


def load_qiongtong_matrix() -> dict[str, Any]:
    """Load and validate the Qiongtong applicability YAML (bazi-owned data)."""

    global _QIONGTONG_MATRIX_CACHE
    if _QIONGTONG_MATRIX_CACHE is not None:
        return _QIONGTONG_MATRIX_CACHE
    if not QIONGTONG_MATRIX_PATH.is_file():
        raise ValueError(
            f"Qiongtong applicability matrix is missing: {QIONGTONG_MATRIX_RELATIVE}"
        )
    import hashlib

    import yaml

    raw = QIONGTONG_MATRIX_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("qiongtong-applicability.yaml must load as a mapping")
    month_groups_raw = data.get("month_groups")
    if not isinstance(month_groups_raw, dict) or set(month_groups_raw.keys()) != {
        "三春", "三夏", "三秋", "三冬",
    }:
        raise ValueError(
            "qiongtong-applicability.yaml: month_groups must cover 三春/三夏/三秋/三冬"
        )
    month_groups: dict[str, tuple[str, ...]] = {}
    for group, branches in month_groups_raw.items():
        if not isinstance(branches, list) or len(branches) != 3:
            raise ValueError(
                f"qiongtong-applicability.yaml: month_groups[{group}] must have 3 branches"
            )
        month_groups[group] = tuple(branches)
    chapters_raw = data.get("chapters")
    if not isinstance(chapters_raw, list):
        raise ValueError("qiongtong-applicability.yaml: chapters must be a list")
    chapters: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for item in chapters_raw:
        if not isinstance(item, dict):
            raise ValueError("qiongtong chapter entry must be a mapping")
        stem = item.get("day_master")
        group = item.get("month_group")
        heading = item.get("heading")
        cid = item.get("id")
        if not (isinstance(stem, str) and stem in _STEM_ELEMENT):
            raise ValueError(f"qiongtong chapter has invalid day_master: {stem!r}")
        if not (isinstance(group, str) and group in month_groups):
            raise ValueError(f"qiongtong chapter has invalid month_group: {group!r}")
        if not isinstance(heading, str) or not heading:
            raise ValueError(f"qiongtong chapter has invalid heading: {heading!r}")
        if not isinstance(cid, str) or not cid:
            raise ValueError(f"qiongtong chapter has invalid id: {cid!r}")
        key = (stem, group)
        if key in seen_keys:
            raise ValueError(
                f"qiongtong chapter has duplicate (day_master, month_group)={key}"
            )
        seen_keys.add(key)
        chapters.append({
            "id": cid,
            "day_master": stem,
            "month_group": group,
            "heading": heading,
        })
    if len(chapters) != 40:
        raise ValueError(
            f"qiongtong-applicability.yaml must have exactly 40 chapters, got {len(chapters)}"
        )
    chapter_by_key = {
        (item["day_master"], item["month_group"]): item["heading"]
        for item in chapters
    }
    _QIONGTONG_MATRIX_CACHE = {
        "sha256": sha,
        "path": QIONGTONG_MATRIX_RELATIVE,
        "month_groups": month_groups,
        "chapters": chapters,
        "chapter_by_key": chapter_by_key,
    }
    return _QIONGTONG_MATRIX_CACHE


def _normalized_bazi_context(
    facts: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    """Return `{day_master, month_branch}` from either fact-layer shape."""

    if not isinstance(facts, Mapping):
        return {"day_master": None, "month_branch": None}
    wrapped = facts.get("chart_facts")
    if isinstance(wrapped, Mapping):
        facts = wrapped
    for path in (
        (facts.get("output") or {}),
        (facts.get("mechanism_stack") or {}).get("natal_baseline") or {},
        (facts.get("birth_fact_layer") or {}),
    ):
        if not isinstance(path, Mapping) or not path:
            continue
        dm = path.get("day_master")
        mc = path.get("month_command")
        stem = dm.get("stem") if isinstance(dm, Mapping) else None
        branch = mc.get("branch") if isinstance(mc, Mapping) else None
        if stem or branch:
            return {"day_master": stem, "month_branch": branch}
    return {"day_master": None, "month_branch": None}


def _resolve_qiongtong_chapter(
    day_master: str | None,
    month_branch: str | None,
) -> str | None:
    if not isinstance(day_master, str) or not day_master:
        return None
    if not isinstance(month_branch, str) or not month_branch:
        return None
    matrix = load_qiongtong_matrix()
    month_group = next(
        (
            group
            for group, branches in matrix["month_groups"].items()
            if month_branch in branches
        ),
        None,
    )
    if month_group is None:
        return None
    return matrix["chapter_by_key"].get((day_master, month_group))


def _qiongtong_plan_extension(
    plan: dict[str, Any],
    facts: Mapping[str, Any] | None,
) -> None:
    """Attach Qiongtong applicability when the plan pulls the Qiongtong pack."""

    selected = {
        str(source.get("pack"))
        for source in plan.get("sources") or ()
        if isinstance(source, Mapping)
    }
    if "bazi/qiongtong-baojian" not in selected:
        return
    context = _normalized_bazi_context(facts)
    day_master = context.get("day_master")
    month_branch = context.get("month_branch")
    matrix = load_qiongtong_matrix()
    chapter = _resolve_qiongtong_chapter(day_master, month_branch)
    plan["qiongtong_applicability"] = {
        "day_master": day_master,
        "month_branch": month_branch,
        "applicable_chapter": chapter,
        "resolution": (
            "applicable" if chapter else "insufficient_fact_layer"
        ),
        "filter_note": (
            "BM25 must not surface Qiongtong chapters outside applicable_chapter"
            " once resolution is 'applicable'"
        ),
        "matrix_source": {
            "path": matrix["path"],
            "sha256": matrix["sha256"],
        },
    }
    plan["pack_chapter_filters"] = {
        "bazi/qiongtong-baojian": {
            "applicable_chapter": chapter,
            "exempt_roles": ["methodology_rule"],
        }
    }
    plan["extension_applicability_conditions"] = [
        {
            "id": "source:qiongtong-applicable-chapter",
            "kind": "source_applicability",
            "fact_path": "qiongtong_applicability.applicable_chapter",
            "satisfied": bool(
                plan["qiongtong_applicability"]["resolution"] == "applicable"
                and chapter
            ),
        }
    ]


def _month_key(value: object) -> str:
    text = str(value or "")
    if re.fullmatch(r"\d{4}-\d{2}", text):
        datetime.strptime(text, "%Y-%m")
        return text
    return date.fromisoformat(text).strftime("%Y-%m")


def _day_key(value: object, *, timezone_name: str = "") -> str:
    text = str(value or "")
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None and timezone_name:
            parsed = parsed.astimezone(ZoneInfo(timezone_name))
        return parsed.date().isoformat()


def _chart_digest(facts: dict[str, Any]) -> str:
    return canonical_digest(
        {
            "system": facts.get("system"),
            "fact_layer_status": facts.get("fact_layer_status"),
            "calendar_normalization": facts.get("calendar_normalization"),
            "output": facts.get("output"),
        }
    )


def _public_calendar_normalization(
    calendar: Mapping[str, Any],
) -> dict[str, Any]:
    """Expose time-basis verification without reproducing birth input."""

    def selected(source: object, keys: tuple[str, ...]) -> dict[str, Any]:
        if not isinstance(source, Mapping):
            return {}
        return {
            key: source[key]
            for key in keys
            if key in source and source[key] is not None
        }

    time_basis = calendar.get("time_basis")
    true_solar_time = calendar.get("true_solar_time")
    convention = calendar.get("calendar_convention")
    time_basis_mapping = (
        time_basis if isinstance(time_basis, Mapping) else {}
    )
    algorithm = time_basis_mapping.get("algorithm")
    boundary = time_basis_mapping.get("boundary")
    public: dict[str, Any] = {
        "status": calendar.get("status"),
        "algorithm_version": calendar.get("algorithm_version"),
        "time_basis": {
            **selected(
                time_basis_mapping,
                (
                    "policy",
                    "standard_meridian_degrees",
                    "longitude_correction_seconds",
                    "equation_of_time_seconds",
                    "total_correction_seconds",
                ),
            ),
            "algorithm": selected(
                algorithm,
                ("id", "version", "source", "uncertainty_seconds"),
            ),
            "boundary": selected(
                boundary,
                ("distance_seconds", "correction_changes_hour_branch", "within_uncertainty"),
            ),
        },
        "true_solar_time": selected(
            true_solar_time,
            (
                "status",
                "policy",
                "longitude_correction_seconds",
                "equation_of_time_seconds",
                "total_correction_seconds",
            ),
        ),
        "calendar_convention": selected(
            convention,
            ("id", "version", "year_boundary", "month_boundary", "day_rollover", "hour_basis", "zi_hour_policy"),
        ),
    }
    # These fields are copied from the Runtime's calculated calendar fact.
    # The public seam does not derive them from civil-time strings, branch
    # labels, or UI state.  Supplied-four-pillars payloads intentionally omit
    # the calculated-only fields because they have no birth instant to bind.
    effective_datetime = calendar.get("effective_datetime")
    if effective_datetime is not None:
        public["effective_datetime"] = effective_datetime

    day_boundary = calendar.get("day_boundary")
    if isinstance(day_boundary, Mapping):
        public["day_boundary"] = selected(
            day_boundary,
            ("correction_crossed_date", "zi_policy_advanced_day_pillar"),
        )

    changed_pillars = calendar.get("changed_pillars")
    if isinstance(changed_pillars, (list, tuple)):
        public["changed_pillars"] = list(changed_pillars)

    solar_terms_value = calendar.get("solar_terms")
    if isinstance(solar_terms_value, Mapping):
        def public_term(value: object) -> dict[str, Any] | None:
            if not isinstance(value, Mapping):
                return None
            return {
                key: value.get(key)
                for key in (
                    "name",
                    "index",
                    "is_month_boundary_jie",
                    "datetime",
                    "instant_utc",
                )
            }

        public["solar_terms"] = {
            "previous": public_term(solar_terms_value.get("previous")),
            "next": public_term(solar_terms_value.get("next")),
            "month_switch_policy": solar_terms_value.get(
                "month_switch_policy"
            ),
        }
    else:
        public["solar_terms"] = None
    return public


def _bound_calendar_digest(facts: Mapping[str, Any]) -> str | None:
    calendar = facts.get("calendar_normalization")
    if not isinstance(calendar, Mapping) or calendar.get("status") != "calculated":
        return None
    return calendar_core.validate_calendar_digest(calendar)


def _attach_extension(
    calculation: CalculationResult,
    requested_dimensions: tuple[str, ...],
    horizon: dict[str, Any],
    *,
    status: Literal["complete", "partial", "unsupported"],
    facts: dict[str, Any],
    unsupported_dimensions: tuple[str, ...] = (),
    rule_traces: tuple[dict[str, Any], ...] = (),
) -> CalculationResult:
    base = calculation.base()
    if status != "unsupported":
        capability = PROVIDER_CAPABILITIES[base.system]
        horizon_kind = str(horizon.get("kind") or "")
        undeclared_dimensions = tuple(
            dimension
            for dimension in requested_dimensions
            if dimension not in capability.dimensions
        )
        unexpected_horizon_fields = set(horizon) - {
            "kind",
            "start",
            "end",
            "target_date",
        }
        if (
            undeclared_dimensions
            or horizon_kind not in capability.horizons
            or unexpected_horizon_fields
            or (
                "target_date" in horizon
                and (base.system != "ziwei" or horizon_kind != "month")
            )
        ):
            status = "unsupported"
            facts = {}
            unsupported_dimensions = requested_dimensions
            rule_traces = ()
        elif horizon_kind == "life" and (
            horizon.get("start") is not None or horizon.get("end") is not None
        ):
            status = "unsupported"
            facts = {}
            unsupported_dimensions = requested_dimensions
            rule_traces = ()
        elif horizon_kind == "instant" and (
            (horizon.get("start") is None) != (horizon.get("end") is None)
            or (
                horizon.get("start") is not None
                and horizon.get("start") != horizon.get("end")
            )
        ):
            status = "unsupported"
            facts = {}
            unsupported_dimensions = requested_dimensions
            rule_traces = ()
    extension = FactExtensionResult.create(
        system=base.system,
        base_calculation_digest=base.result_hash,
        requested_dimensions=requested_dimensions,
        horizon=horizon,
        status=status,
        facts=facts,
        unsupported_dimensions=unsupported_dimensions,
        rule_traces=rule_traces,
    )
    return base.with_fact_extension(extension)


def _unsupported_extension(
    calculation: CalculationResult,
    requested_dimensions: tuple[str, ...],
    horizon: dict[str, Any],
) -> CalculationResult:
    return _attach_extension(
        calculation,
        requested_dimensions,
        horizon,
        status="unsupported",
        facts={},
        unsupported_dimensions=requested_dimensions,
    )


def _bind_request_semantics(
    input_payload: Mapping[str, Any], request: ReadingRequest
) -> dict[str, Any]:
    """Include the exact structured calculation envelope in the input hash."""

    envelope = request.to_dict()
    system = str(request.system or "")
    calculation_fields_by_system = {
        "bazi": (
            "reference_datetime",
            "timezone",
            "location",
            "birth_data",
            "chart_data",
            "metadata",
            "image_supplied",
            "transcribed_chart",
        ),
        "fortune": (
            "reference_datetime",
            "timezone",
            "location",
            "birth_data",
            "metadata",
        ),
        "ziwei": ("timezone", "location", "birth_data"),
        "luming-nayin": (
            "timezone",
            "location",
            "birth_data",
            "chart_data",
            "metadata",
        ),
        "xingming": ("timezone", "location", "birth_data", "metadata"),
        "liuyao": (
            "reference_datetime",
            "timezone",
            "location",
            "chart_data",
            "event_datetime",
            "metadata",
        ),
        "meihua": (
            "reference_datetime",
            "timezone",
            "location",
            "chart_data",
            "event_datetime",
            "metadata",
        ),
        "liuren": (
            "reference_datetime",
            "timezone",
            "location",
            "event_datetime",
            "metadata",
        ),
        "qimen": (
            "reference_datetime",
            "timezone",
            "location",
            "event_datetime",
            "metadata",
        ),
        "taiyi": ("reference_datetime", "timezone", "location", "metadata"),
        "selection": ("timezone", "location", "chart_data", "metadata"),
        "fengshui": ("chart_data",),
        "physiognomy": ("chart_data", "goal"),
    }
    common_calendar_metadata = {
        "longitude",
        "latitude",
        "coordinate_source",
        "zi_hour_policy",
        "time_basis_policy",
    }
    metadata_fields_by_system = {
        "bazi": {"image_chart_transcription"},
        "fortune": {"target_date"},
        "luming-nayin": {"luming_taiyuan_profile"},
        "xingming": {
            "xingming_house_profile",
            "xingming_pseudo_point_profile",
        },
        "liuyao": common_calendar_metadata
        | {
            liuyao.TRANSACTION_CAST_SEED_KEY,
            "requested_useful_spirit_relatives",
        },
        "meihua": common_calendar_metadata,
        "liuren": common_calendar_metadata | {"target_relative"},
        "qimen": common_calendar_metadata,
        "taiyi": common_calendar_metadata,
        "selection": {"longitude", "latitude", "coordinate_source"},
    }
    calculation_fields = calculation_fields_by_system.get(system, ())
    semantics = {
        field: copy.deepcopy(envelope[field]) for field in calculation_fields
    }
    if "metadata" in semantics:
        allowed_metadata = metadata_fields_by_system.get(system, set())
        semantics["metadata"] = {
            key: copy.deepcopy(value)
            for key, value in semantics["metadata"].items()
            if key in allowed_metadata
        }
    bound = copy.deepcopy(dict(input_payload))
    bound["request_semantics"] = semantics
    return bound


def _unique_rule_traces(
    traces: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for trace in traces:
        digest = canonical_digest(trace)
        if digest in seen:
            continue
        seen.add(digest)
        unique.append(trace)
    return tuple(unique)


def _selection_horizon_date_range(horizon: Mapping[str, Any]) -> dict[str, str]:
    kind = str(horizon.get("kind") or "")
    start = horizon.get("start")
    end = horizon.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        raise ValueError("Selection horizon bounds must be strings")
    if kind == "day":
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    elif kind == "month":
        if re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", start) is None or re.fullmatch(
            r"\d{4}-(?:0[1-9]|1[0-2])", end
        ) is None:
            raise ValueError("Selection month horizon must use YYYY-MM")
        start_year, start_month = (int(item) for item in start.split("-"))
        end_year, end_month = (int(item) for item in end.split("-"))
        start_date = date(start_year, start_month, 1)
        end_date = date(
            end_year,
            end_month,
            stdlib_calendar.monthrange(end_year, end_month)[1],
        )
    elif kind == "year":
        if re.fullmatch(r"\d{4}", start) is None or re.fullmatch(
            r"\d{4}", end
        ) is None:
            raise ValueError("Selection year horizon must use YYYY")
        start_date = date(int(start), 1, 1)
        end_date = date(int(end), 12, 31)
    else:
        raise ValueError("unsupported Selection horizon kind")
    day_count = (end_date - start_date).days + 1
    if day_count < 1 or day_count > selection.MAX_RANGE_DAYS:
        raise ValueError("Selection horizon exceeds the bounded range")
    return {"start": start_date.isoformat(), "end": end_date.isoformat()}


def _fengshui_incomplete_dimensions(output: Mapping[str, Any]) -> set[str]:
    """Map concrete observation gaps to the dimensions they cannot support."""

    incomplete: set[str] = set()
    critical_missing = tuple(
        str(item) for item in output.get("critical_missing") or ()
    )
    for code in critical_missing:
        if code.startswith("form_observation:"):
            incomplete.update({"current_state", "location", "state"})
        elif code.startswith(
            (
                "door_direction_measurement:",
                "bazhai_origin_door",
                "confirmed_facing_measurement",
            )
        ):
            incomplete.update({"direction", "location"})
        else:
            incomplete.update({"current_state", "direction", "location", "state"})
    return incomplete


class LiurenProvider(_AdapterSeam, _SourceRouteMixin):
    provider_id = "mingli-master.liuren.v8"
    SOURCE_ROUTE = {
        "plan_system": "liuren",
        "subsystem": None,
        "registry_route": "liuren",
        "packs": [
            "san-shi/daliuren-daquan",
            "san-shi/liuren-zhiyin",
            "san-shi/liuren-miben",
        ],
        "layers": [
            "four_lessons", "three_transmissions", "question_rules", "timing",
        ],
        "chart": {
            "label": "课象",
            "required_fields": [
                "day_hour", "month_general", "lesson_method", "four_lessons",
                "three_transmissions", "xunkong",
            ],
            "fact_paths": {
                "lesson_method": "output.transmission_method.primary",
            },
        },
    }

    def source_route(
        self,
        goal: Mapping[str, Any],
        facts: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        route = super().source_route(goal, facts)
        question_dimensions = list(goal.get("question_dimensions") or ())
        requested_dimensions = list(
            goal.get("requested_dimensions") or question_dimensions
        )
        dimensions = {
            str(item) for item in (*question_dimensions, *requested_dimensions)
        }
        # A matching casting rule may document the calculated method identity;
        # its role remains explicit so it cannot be mistaken for a judgment.
        roles = {"casting_rule", "issue_specific_judgment_rule"}
        if "timing" in dimensions:
            roles.add("timing_rule")
        if dimensions & {
            "state", "current_state", "location", "location_direction",
        }:
            roles.add("imagery_correspondence")
        route["allowed_evidence_roles"] = sorted(roles)
        return route
    provider_version = liuren_calc.CALCULATION_CONTRACT
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        missing: list[str] = []
        if not (request.event_datetime or request.reference_datetime):
            missing.append("event_datetime_or_reference_datetime")
        if not request.timezone:
            missing.append("timezone")
        return tuple(missing)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def enrich_request(
        self,
        request: ReadingRequest,
        context: RuntimeContext | None,
        *,
        routed: bool = True,
    ) -> ReadingRequest:
        """Fill instant-event defaults from the injected clock and timezone."""

        if context is None or not context.default_timezone_name:
            return request
        frame = IntentFrame.from_dict(request.intent)
        if (
            frame.calculation_object != "concrete_event"
            or frame.horizon.kind != "instant"
        ):
            return request
        changes: dict[str, Any] = {}
        if not request.event_datetime and not request.reference_datetime:
            changes["reference_datetime"] = context.now_iso or "now"
        if not request.timezone:
            changes["timezone"] = context.default_timezone_name
        return _with_request_changes(request, changes)

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        if not request.timezone:
            raise ValueError("Liuren calculation requires timezone")
        timezone_name = request.timezone
        location = request.location or liuren_calc.DEFAULT_CIVIL_CHINA_LOCATION
        source_datetime = request.event_datetime or request.reference_datetime
        if not source_datetime:
            raise ValueError(
                "Liuren calculation requires event_datetime or reference_datetime"
            )
        civil_datetime = liuren_calc._resolve_datetime(
            source_datetime, timezone_name
        )
        zi_hour_policy = str(request.metadata.get("zi_hour_policy") or "midnight")
        time_basis_policy = str(
            request.metadata.get("time_basis_policy") or "civil"
        )
        input_payload = {
            "question": request.query,
            "datetime": civil_datetime,
            "timezone": timezone_name,
            "location": location,
            "guiren_profile": "official-corrected",
            "day_night_profile": "civil-double-hour",
            "zi_hour_policy": zi_hour_policy,
            "biezhe_profile": "daliuren-daquan-body-branch",
            "longitude": request.metadata.get("longitude"),
            "latitude": request.metadata.get("latitude"),
            "coordinate_source": request.metadata.get("coordinate_source"),
            "coordinate_accuracy_meters": request.metadata.get("coordinate_accuracy_meters"),
            "target_relative": request.metadata.get("target_relative"),
            "time_basis_policy": time_basis_policy,
        }
        args = argparse.Namespace(
            timezone=timezone_name,
            location=input_payload["location"],
            guiren_profile=input_payload["guiren_profile"],
            day_night_profile=input_payload["day_night_profile"],
            zi_hour_policy=input_payload["zi_hour_policy"],
            biezhe_profile=input_payload["biezhe_profile"],
            longitude=input_payload["longitude"],
            latitude=input_payload["latitude"],
            coordinate_source=input_payload["coordinate_source"],
            coordinate_accuracy_meters=input_payload["coordinate_accuracy_meters"],
            time_basis_policy=time_basis_policy,
        )
        facts = liuren_calc._run_adapter(
            self.skill_dir,
            args,
            request.query,
            civil_datetime,
        )
        facts.setdefault("adapter", {})["generated_at"] = (
            "deterministic-chart-identity"
        )
        liuren_calc._validate_facts(self.skill_dir, facts)
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("Da Liu Ren requires shared calendar facts")
        return CalculationResult.create(
            system="liuren",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": _chart_digest(facts),
                "calendar_digest": calendar_digest,
                "target_relative": request.metadata.get("target_relative"),
                "chart_facts": facts,
            },
            diagnostics=(
                "deterministic_chart_validated",
                "caller_owned_evidence_planning",
            ),
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "liuren":
            raise ValueError("Da Liu Ren refinement requires a Da Liu Ren calculation")
        del request
        return previous

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "liuren":
            raise ValueError("Da Liu Ren extension requires a Da Liu Ren calculation")
        try:
            target_relative = base.facts.get("target_relative")
            facts = liuren_calc.extend_liuren_facts(
                base.facts["chart_facts"],
                requested_dimensions=requested_dimensions,
                horizon=horizon,
                target_relative=(
                    str(target_relative) if target_relative is not None else None
                ),
            )
        except (KeyError, TypeError, ValueError):
            return _unsupported_extension(
                base, requested_dimensions, horizon
            )
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts=facts,
            rule_traces=_unique_rule_traces(
                tuple(facts.get("rule_traces") or ())
                + tuple((facts.get("timing") or {}).get("rule_trace") or ())
            ),
        )


class BaziProvider(_AdapterSeam, _SourceRouteMixin):
    provider_id = "mingli-master.bazi.v7"
    provider_version = bazi_calc.CALCULATION_CONTRACT
    _REASONING_DOMAIN_BY_DIMENSION = {
        "career": "work",
        "work": "work",
        "money": "finance",
        "health": "health",
        "location": "travel",
        "relationship": "relationship",
        "education": "education",
    }

    @classmethod
    def _reasoning_domains(cls, request: ReadingRequest) -> tuple[str, ...]:
        """Map only explicit Bazi dimensions to existing core tools."""

        if not request.intent:
            return ()
        dimensions = IntentFrame.from_dict(request.intent).question_dimensions
        return tuple(
            dict.fromkeys(
                cls._REASONING_DOMAIN_BY_DIMENSION[dimension]
                for dimension in dimensions
                if dimension in cls._REASONING_DOMAIN_BY_DIMENSION
            )
        )

    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        if chart.get("pillars") or chart.get("four_pillars"):
            return ()
        birth_datetime = _birth_value(request, "birth_datetime")
        if birth_datetime:
            required = ("timezone", "location", "gender")
            return tuple(field for field in required if not _birth_value(request, field))
        return ("birth_datetime_or_four_pillars",)

    SOURCE_ROUTE = {
        "plan_system": "bazi",
        "subsystem": None,
        "registry_route": "bazi",
        "packs": [
            "bazi/sanming-tonghui",
            "bazi/yuanhai-ziping",
            "bazi/ziping-zhenquan",
            "bazi/ditiansui-chanwei",
            "bazi/qiongtong-baojian",
        ],
        "layers": ["source_anchor", "pattern", "strength_flow", "tiaohou"],
        "chart": {
            "label": "四柱",
            "required_fields": [
                "four_pillars",
                "hidden_stems",
                "ten_gods",
                "month_command",
                "seasonal_profile",
                "tiaohou_markers",
            ],
        },
        "compatible_rule_systems": ["bazi"],
    }
    extend_source_plan = staticmethod(_qiongtong_plan_extension)

    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def public_basis_projection(
        self, chart_facts: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Keep exact rule identities public without leaking internal paths."""

        output = chart_facts.get("output")
        if not isinstance(output, Mapping):
            return {}
        return _bazi_public_projection_value(output)

    def enrich_request(
        self,
        request: ReadingRequest,
        context: RuntimeContext | None,
        *,
        routed: bool = True,
    ) -> ReadingRequest:
        """Read the opted-in default natal profile from the runtime context."""

        changes = _default_profile_changes(
            request,
            context,
            ensure_datetime_alias=routed,
        )
        return _with_request_changes(request, changes)

    def _arguments(
        self,
        request: ReadingRequest,
        image_verification: ImageChartVerification,
    ) -> argparse.Namespace:
        birth = request.birth_data
        civil_datetime = birth.get("birth_datetime") or birth.get("datetime")
        if civil_datetime:
            expected_pillars = list(birth.get("expected_pillars") or ()) or None
            if image_verification.ok and image_verification.pillars:
                expected_pillars = list(image_verification.pillars)
            return argparse.Namespace(
                mode="birth",
                civil_datetime=str(civil_datetime),
                timezone=str(
                    birth.get("timezone") or request.timezone or "Asia/Shanghai"
                ),
                location=str(birth.get("location") or request.location or ""),
                gender=str(birth.get("gender") or ""),
                expected_pillars=expected_pillars,
                zi_hour_policy=str(birth.get("zi_hour_policy") or "midnight"),
                longitude=birth.get("longitude"),
                latitude=birth.get("latitude"),
                coordinate_source=birth.get("coordinate_source"),
                coordinate_accuracy_meters=birth.get("coordinate_accuracy_meters"),
                time_basis_policy=str(birth.get("time_basis_policy") or "civil"),
                reasoning_domains=list(self._reasoning_domains(request)),
                pillars=None,
                source="text",
                source_ref=None,
            )
        supplied_pillars = request.chart_data.get(
            "pillars"
        ) or request.chart_data.get("four_pillars")
        tokens = (
            list(image_verification.pillars)
            if request.image_supplied and image_verification.ok
            else list(supplied_pillars)
            if isinstance(supplied_pillars, (list, tuple))
            else GANZHI_RE.findall(request.transcribed_chart or "")
        )
        if len(tokens) < 4:
            raise RuntimeError("four validated pillars are required")
        return argparse.Namespace(
            mode="pillars",
            civil_datetime=None,
            timezone=request.timezone or "Asia/Shanghai",
            location=request.location or "",
            gender=str(birth.get("gender") or "") or None,
            expected_pillars=None,
            zi_hour_policy="midnight",
            longitude=None,
            latitude=None,
            coordinate_source=None,
            coordinate_accuracy_meters=None,
            time_basis_policy="civil",
            reasoning_domains=list(self._reasoning_domains(request)),
            pillars=tokens[:4],
            source="image" if request.image_supplied else "text",
            source_ref=(
                "transcribed_chart" if request.image_supplied else "user_text"
            ),
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        image_verification = validate_image_chart_transcription(
            image_supplied=request.image_supplied,
            transcribed_chart=request.transcribed_chart,
            metadata=request.metadata,
        )
        if not image_verification.ok:
            raise RuntimeError(
                "image chart transcription is not verified: "
                + str(image_verification.missing_fact)
            )
        args = self._arguments(request, image_verification)
        reading_timezone = str(
            request.birth_data.get("timezone")
            or request.timezone
            or "Asia/Shanghai"
        )
        reference_datetime = (
            bazi_calc._resolve_as_of(request.reference_datetime, reading_timezone)
            if request.reference_datetime
            else None
        )
        input_payload = {
            "mode": args.mode,
            "question": request.query,
            "reference_datetime": reference_datetime,
            "timezone": args.timezone,
            "location": args.location,
            "gender": args.gender,
            "birth_datetime": args.civil_datetime,
            "pillars": args.pillars,
            "expected_pillars": args.expected_pillars,
            "source": args.source,
            "zi_hour_policy": args.zi_hour_policy,
            "longitude": args.longitude,
            "latitude": args.latitude,
            "coordinate_source": args.coordinate_source,
            "coordinate_accuracy_meters": args.coordinate_accuracy_meters,
            "time_basis_policy": args.time_basis_policy,
        }
        question_contract = {
            "domains": list(args.reasoning_domains),
            "gender": args.gender,
        }
        if args.mode == "birth":
            engine_request: (
                bazi_fact_adapter.BaziBirthEngineRequest
                | bazi_fact_adapter.BaziPillarsEngineRequest
            ) = bazi_fact_adapter.BaziBirthEngineRequest(
                civil_datetime=str(args.civil_datetime),
                timezone_name=str(args.timezone),
                location=str(args.location),
                gender=str(args.gender),
                expected_pillars=(
                    tuple(args.expected_pillars)
                    if args.expected_pillars is not None
                    else None
                ),
                zi_hour_policy=str(args.zi_hour_policy),
                longitude=args.longitude,
                latitude=args.latitude,
                coordinate_source=args.coordinate_source,
                coordinate_accuracy_meters=args.coordinate_accuracy_meters,
                time_basis_policy=str(args.time_basis_policy),
                question_contract=question_contract,
            )
        else:
            engine_request = bazi_fact_adapter.BaziPillarsEngineRequest(
                pillars=tuple(args.pillars),
                gender=args.gender,
                source=str(args.source),
                source_ref=args.source_ref,
                question_contract=question_contract,
            )
        engine_adapter = bazi_fact_adapter.BaziEngineAdapter()
        try:
            engine_result = engine_adapter.adapt(engine_request)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from None
        facts = engine_result.canonical_facts.to_payload()
        if facts.get("conflicts"):
            raise RuntimeError(
                "Bazi birth data conflict with the supplied four pillars"
            )
        facts.setdefault("adapter", {})["generated_at"] = (
            "deterministic-chart-identity"
        )
        bazi_calc._validate_facts(self.skill_dir, facts)
        calendar = facts.get("calendar_normalization")
        if isinstance(calendar, Mapping):
            facts["public_calendar_normalization"] = _public_calendar_normalization(
                calendar
            )
        facts = BaziFactContract().bind_canonical_facts(
            facts,
            engine_result.provenance,
        ).to_payload()
        calendar_digest = _bound_calendar_digest(facts)
        result_facts = {
            "chart_digest": _chart_digest(facts),
            "natal_fact_digest": bazi_fact_adapter.natal_fact_digest(facts),
            "chart_facts": facts,
        }
        if calendar_digest:
            result_facts["calendar_digest"] = calendar_digest
        diagnostics = [
            "deterministic_chart_validated",
            "tiaohou_fact_layer_present",
            "caller_owned_evidence_planning",
        ]
        if isinstance(facts["calendar_normalization"].get("lunar_date"), dict):
            diagnostics.append("lunar_and_solar_terms_calculated")
        else:
            diagnostics.append("supplied_four_pillars_static_only")
        if request.image_supplied:
            result_facts["image_transcription_verification"] = (
                image_verification.to_dict()
            )
            diagnostics.append("image_transcription_dual_pass_validated")
        return CalculationResult.create(
            system="bazi",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts=result_facts,
            diagnostics=tuple(diagnostics),
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "bazi":
            raise ValueError("Bazi refinement requires a Bazi calculation")
        del request
        return previous

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "bazi":
            raise ValueError("Bazi extension requires a Bazi calculation")
        chart_facts = base.facts.get("chart_facts") or {}
        kind = str(horizon.get("kind") or "")
        try:
            if kind == "year":
                start = int(str(horizon.get("start") or ""))
                end = int(str(horizon.get("end") or start))
                facts = {
                    "year_layers": bazi_fact_adapter.build_year_fact_extensions(
                        chart_facts,
                        start_year=start,
                        end_year=end,
                    )
                }
            elif kind == "month":
                start = _month_key(horizon.get("start"))
                end = _month_key(horizon.get("end") or start)
                facts = {
                    "month_layers": bazi_fact_adapter.build_month_fact_extensions(
                        chart_facts,
                        start_month=start,
                        end_month=end,
                    )
                }
            elif kind == "day":
                timezone_name = str(
                    (chart_facts.get("calendar_normalization") or {}).get("timezone")
                    or ""
                )
                start = _day_key(
                    horizon.get("start"),
                    timezone_name=timezone_name,
                )
                end = _day_key(
                    horizon.get("end") or start,
                    timezone_name=timezone_name,
                )
                facts = {
                    "day_layers": bazi_fact_adapter.build_day_fact_extensions(
                        chart_facts,
                        start_date=start,
                        end_date=end,
                    )
                }
            elif kind in {"instant", "natal", "life"} and not (
                horizon.get("start") or horizon.get("end")
            ):
                # The scope mirrors the requested dimensions verbatim: a
                # provider-owned overview dimension stays one semantic unit
                # instead of fanning out into the default domain list.
                facts = {
                    "dimension_fact_scope": {
                        dimension: {
                            "scope": "calculated_natal_chart",
                            "base_calculation_digest": base.result_hash,
                        }
                        for dimension in requested_dimensions
                    }
                }
            else:
                return _unsupported_extension(
                    base, requested_dimensions, horizon
                )
        except (KeyError, TypeError, ValueError):
            return _unsupported_extension(base, requested_dimensions, horizon)
        traces = _unique_rule_traces(
            tuple(
                trace
                for collection in (
                    facts.get("year_layers")
                    or facts.get("month_layers")
                    or facts.get("day_layers")
                    or {}
                ).values()
                for trace in collection.get("rule_trace") or ()
            )
        )
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts=facts,
            rule_traces=traces,
        )


class LumingProvider(_AdapterSeam, _SourceRouteMixin):
    """Early-Luming fact provider built on the shared four-pillar authority."""

    provider_id = "mingli-master.luming-nayin.v1"
    SOURCE_ROUTE = {
        "plan_system": "luming-nayin",
        "subsystem": None,
        "registry_route": "luming-nayin",
        "packs": [
            "luming-nayin/li-xuzhong-mingshu",
            "luming-nayin/luoluzi-sanming",
            "luming-nayin/wuxing-jingji",
            "luming-nayin/lantai-miaoxuan",
        ],
        "layers": [
            "sixty_jiazi_nayin",
            "three_yuan_profiles",
            "taiyuan_convention",
            "source_named_relations",
            "source_conditioned_patterns",
        ],
        "chart": {
            "label": "早期禄命确定性事实",
            "required_fields": ["pillars", "three_yuan_profiles", "relations"],
        },
    }
    provider_version = luming.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        if chart.get("pillars") or chart.get("four_pillars"):
            return ()
        birth_datetime = _birth_value(request, "birth_datetime")
        if birth_datetime:
            required = ("timezone", "location")
            return tuple(field for field in required if not _birth_value(request, field))
        return ("birth_datetime_or_four_pillars",)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        taiyuan_profile = request.metadata.get("luming_taiyuan_profile")
        selected_profile = (
            str(taiyuan_profile) if taiyuan_profile is not None else None
        )
        birth = request.birth_data
        civil_datetime = birth.get("birth_datetime") or birth.get("datetime")
        if civil_datetime:
            timezone_name = str(
                birth.get("timezone") or request.timezone or ""
            )
            location = str(birth.get("location") or request.location or "")
            if not timezone_name or not location:
                raise ValueError(
                    "early-Luming birth calculation requires timezone and location"
                )
            facts = luming.build_from_birth(
                str(civil_datetime),
                timezone_name=timezone_name,
                location=location,
                expected_pillars=list(birth.get("expected_pillars") or ()) or None,
                zi_hour_policy=str(birth.get("zi_hour_policy") or "midnight"),
                taiyuan_profile=selected_profile,
                longitude=birth.get("longitude"),
                latitude=birth.get("latitude"),
                coordinate_source=birth.get("coordinate_source"),
                coordinate_accuracy_meters=birth.get(
                    "coordinate_accuracy_meters"
                ),
                time_basis_policy=str(birth.get("time_basis_policy") or "civil"),
            )
            pillars = dict(facts["calendar_normalization"]["ganzhi"])
            input_payload = {
                "mode": "birth",
                "birth_datetime": str(civil_datetime),
                "timezone": timezone_name,
                "location": location,
                "pillars": pillars,
                "taiyuan_profile": selected_profile,
            }
        else:
            supplied = request.chart_data.get("pillars") or request.chart_data.get(
                "four_pillars"
            )
            if not isinstance(supplied, (list, tuple)):
                raise ValueError(
                    "early-Luming calculation requires birth data or four pillars"
                )
            facts = luming.build_fact_layer(
                list(supplied),
                taiyuan_profile=selected_profile,
                source="user_chart",
                source_ref="chart_data.pillars",
                input_provenance={
                    "authority": "shared-sexagenary-four-pillar-contract",
                    "source_mode": "supplied_four_pillars",
                },
            )
            pillars = {
                position: str(supplied[index])
                for index, position in enumerate(("year", "month", "day", "hour"))
            }
            input_payload = {
                "mode": "supplied_four_pillars",
                "pillars": pillars,
                "taiyuan_profile": selected_profile,
            }
        luming.validate_fact_layer(facts)
        calendar_digest = _bound_calendar_digest(facts)
        result_facts: dict[str, Any] = {
            "chart_digest": _chart_digest(facts),
            "natal_fact_digest": facts["natal_fact_digest"],
            "chart_facts": facts,
        }
        if calendar_digest:
            result_facts["calendar_digest"] = calendar_digest
        input_payload["calendar_digest"] = calendar_digest
        return CalculationResult.create(
            system="luming-nayin",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts=result_facts,
            diagnostics=(
                "shared_four_pillar_foundation_validated",
                "early_luming_source_profiles_separated",
                "sixty_nayin_complete",
                "lu_ma_gui_relations_calculated_without_verdict",
                "source_conditioned_rule_applicability_adjudicated_without_life_verdict",
                "caller_owned_evidence_planning",
            ),
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "luming-nayin":
            raise ValueError("early-Luming refinement system mismatch")
        del request
        return previous

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "luming-nayin":
            raise ValueError("early-Luming extension system mismatch")
        if str(horizon.get("kind") or "") not in {"life", "natal"} or (
            horizon.get("start") or horizon.get("end")
        ):
            return _unsupported_extension(base, requested_dimensions, horizon)
        facts = {
            "dimension_fact_scope": {
                dimension: {
                    "scope": "calculated_early_luming_natal_facts",
                    "natal_fact_digest": base.facts["natal_fact_digest"],
                }
                for dimension in requested_dimensions
            }
        }
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts=facts,
            rule_traces=(
                {
                    "source_dependency_id": "luming.nayin.sixty-jiazi-table",
                    "role": "natal fact scope",
                },
                {
                    "source_dependency_id": "luming.three-yuan-and-taiyuan",
                    "role": "source-specific three-yuan scope",
                },
                {
                    "source_dependency_id": "luming.relations.lu-ma-gui",
                    "role": "neutral relation scope",
                },
            ),
        )


class LiuyaoProvider(_AdapterSeam, _SourceRouteMixin):
    """Complete deterministic Jingfang eight-palace Liuyao provider."""

    provider_id = "mingli-master.liuyao.v1"
    _USEFUL_SPIRIT_RELATIVES_BY_DIMENSION = {
        "career": ("官鬼",),
        "work": ("官鬼",),
        "money": ("妻财",),
        "relationship": ("官鬼", "妻财"),
        "health": ("官鬼", "子孙"),
        "education": ("父母",),
        "location": ("父母",),
    }

    @classmethod
    def _requested_useful_spirit_relatives(
        cls, request: ReadingRequest
    ) -> tuple[str, ...]:
        """Route explicit product dimensions to useful-spirit candidates.

        The source procedure classifies the question before selecting a useful
        spirit.  Product dimensions are the only structured classification the
        Runtime receives here, so this method deliberately emits candidates
        only.  It never turns the selected relative into a result or verdict.
        An explicit internal metadata value remains authoritative for callers
        that already performed a more specific question classification.
        """

        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        question_class = liuyao.normalize_question_class(
            chart.get("question_class")
        )
        if question_class == "finance":
            return ("妻财", "子孙")

        if "requested_useful_spirit_relatives" in request.metadata:
            raw = request.metadata.get("requested_useful_spirit_relatives")
            if isinstance(raw, (str, bytes)):
                raise ValueError(
                    "requested useful-spirit relatives must be structured values"
                )
            return tuple(str(item) for item in (raw or ()))

        if not request.intent:
            return ()
        dimensions = IntentFrame.from_dict(request.intent).question_dimensions
        relatives: list[str] = []
        for dimension in dimensions:
            for relative in cls._USEFUL_SPIRIT_RELATIVES_BY_DIMENSION.get(
                dimension, ()
            ):
                if relative not in relatives:
                    relatives.append(relative)
        return tuple(relatives)

    SOURCE_ROUTE = {
        "plan_system": "divination",
        "subsystem": "liuyao",
        "registry_route": "liuyao",
        "packs": [
            "divination/zengshan-buyi",
            "divination/bushi-zhengzong",
            "divination/huangjin-ce",
            "divination/huozhu-lin",
        ],
        "layers": [
            "hexagram",
            "najia",
            "useful_spirit",
            "prosperity",
            "event_rules",
            "source_conditioned_patterns",
        ],
        "chart": {
            "label": "卦象",
            "required_fields": [
                "primary_hexagram",
                "changed_hexagram",
                "moving_lines",
                "shi_ying",
                "six_relatives",
                "changed_six_relatives",
                "changed_plate_lines",
                "six_spirits",
                "najia",
                "changed_najia",
                "xunkong",
                "hidden_lines",
                "month_day_strength",
                "relation_facts",
                "shi_ying_moving_relations",
                "useful_spirit_candidates",
                "casting_method",
                "source_conditioned_patterns",
            ],
        },
    }
    provider_version = liuyao.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        tosses = chart.get("tosses")
        raw_method = chart.get("casting_method")
        complete_cast = (
            isinstance(tosses, (list, tuple))
            and len(tosses) == 6
            and all(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value in {6, 7, 8, 9}
                for value in tosses
            )
        )
        digital = raw_method == "digital_coin"
        missing: list[str] = []
        if not complete_cast and not digital:
            missing.append("cast")
        if not (request.event_datetime or request.reference_datetime):
            missing.append("event_datetime")
        if not request.timezone:
            missing.append("timezone")
        if not request.location:
            missing.append("location")
        return tuple(missing)

    recast_replaces_chart_data = True

    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    @staticmethod
    def unsupported_request(request: ReadingRequest) -> str | None:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        if chart.get("casting_method") == "time":
            return "casting_method_unsupported"
        return None

    def reject_reserved_request_fields(self, request: ReadingRequest) -> None:
        """Keep the CSPRNG seed transaction-owned."""

        reserved = liuyao.TRANSACTION_CAST_SEED_KEY
        if reserved in request.metadata or any(
            key in request.chart_data
            for key in (reserved, "seed", "cast_seed")
        ):
            raise ValueError("Liuyao transaction cast seed is internal-only")

    def persisted_transaction_cast_seed(
        self, calculation: CalculationResult
    ) -> str | None:
        """Replay the stored seed when a correction reuses the same cast."""

        if calculation.system != "liuyao":
            return None
        chart_facts = calculation.facts.get("chart_facts")
        if not isinstance(chart_facts, Mapping):
            raise ValueError("stored Liuyao chart facts are missing")
        output = chart_facts.get("output")
        casting = output.get("casting") if isinstance(output, Mapping) else None
        if not isinstance(casting, Mapping):
            raise ValueError("stored Liuyao cast is missing")
        if casting.get("method") != "digital_coin":
            return None
        if calculation.provider_version != liuyao.ADAPTER_VERSION:
            raise ProviderActionError(
                "action_requires_recast",
                "Legacy Liuyao digital casts require an explicit recast action.",
            )
        adapter = chart_facts.get("adapter")
        if (
            not isinstance(adapter, Mapping)
            or adapter.get("version") != liuyao.ADAPTER_VERSION
            or casting.get("seed_source")
            != liuyao.TRANSACTION_CAST_SEED_SOURCE
        ):
            raise ProviderActionError(
                "action_requires_recast",
                "Unverified Liuyao digital seed provenance requires an explicit recast action.",
            )
        return liuyao.normalize_transaction_cast_seed(casting.get("seed"))

    def correction_replaces_cast(
        self,
        calculation: CalculationResult,
        request: ReadingRequest,
    ) -> str | None:
        """If correction requests a different cast method or tosses, return message."""

        supplied = request.chart_data
        if not any(key in supplied for key in ("casting_method", "tosses")):
            return None
        blocked = "Changing a Liuyao cast requires an explicit recast action."
        chart_facts = calculation.facts.get("chart_facts")
        output = (
            chart_facts.get("output") if isinstance(chart_facts, Mapping) else None
        )
        casting = output.get("casting") if isinstance(output, Mapping) else None
        if not isinstance(casting, Mapping):
            return blocked
        prior_method = str(casting.get("method") or "")
        requested_method = supplied.get("casting_method")
        if requested_method is None and "tosses" in supplied:
            requested_method = "supplied_complete_cast"
        if requested_method is not None and str(requested_method) != prior_method:
            return blocked
        if "tosses" in supplied:
            try:
                requested_tosses = tuple(
                    int(value) for value in supplied.get("tosses") or ()
                )
                prior_tosses = tuple(
                    int(value) for value in casting.get("tosses") or ()
                )
            except (TypeError, ValueError):
                return blocked
            if requested_tosses != prior_tosses:
                return blocked
        return None

    def inject_transaction_cast(
        self, request: ReadingRequest, seed: str | None
    ) -> ReadingRequest:
        """Inject or generate the deterministic CSPRNG seed for digital casts."""

        if (
            request.chart_data.get("tosses") is not None
            or request.chart_data.get("casting_method") != "digital_coin"
        ):
            return request
        effective_seed = liuyao.normalize_transaction_cast_seed(
            seed or secrets.token_hex(32)
        )
        return ReadingRequest(
            **{
                **request.to_dict(),
                "metadata": {
                    **request.metadata,
                    liuyao.TRANSACTION_CAST_SEED_KEY: effective_seed,
                },
            }
        )

    def public_basis_projection(
        self, chart_facts: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Privacy-safe basis text for the host."""

        projected = liuyao.public_projection(chart_facts)
        visible = projected.get("output")
        if not isinstance(visible, dict):
            return projected
        return visible

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        validation = liuyao.validate_fact_layer(facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Liuyao fact validation failed: "
                + ", ".join(validation["codes"])
            )
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("Liuyao requires shared calendar facts")
        diagnostics = (
            "complete_cast_preserved",
            "eight_palace_najia_facts_validated",
            "calendar_relations_calculated_without_verdict",
            "useful_spirit_candidates_require_evidence_adjudication",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "cast_reused_without_recast",
                "caller_owned_evidence_planning",
            )
        return CalculationResult.create(
            system="liuyao",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": facts["fact_digest"],
                "calendar_digest": calendar_digest,
                "fact_digest": facts["fact_digest"],
                "cast_digest": facts["output"]["casting"]["cast_digest"],
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        civil_datetime = request.event_datetime or request.reference_datetime
        timezone_name = str(request.timezone or "")
        location = str(request.location or "")
        if not civil_datetime or not timezone_name or not location:
            raise ValueError(
                "Liuyao calculation requires event datetime, timezone, and location"
            )
        method = str(chart.get("casting_method") or "")
        if isinstance(chart.get("casting_method"), Mapping):
            raise ValueError("Liuyao casting_method must be a structured method id")
        calendar = calendar_core.normalize_calendar(
            str(civil_datetime),
            timezone_name=timezone_name,
            location=location,
            longitude=request.metadata.get("longitude"),
            latitude=request.metadata.get("latitude"),
            coordinate_source=request.metadata.get("coordinate_source"),
            coordinate_accuracy_meters=request.metadata.get("coordinate_accuracy_meters"),
            zi_hour_policy=str(request.metadata.get("zi_hour_policy") or "midnight"),
            time_basis_policy=str(request.metadata.get("time_basis_policy") or "civil"),
        )
        if chart.get("tosses") is not None:
            if method not in {"", "supplied_complete_cast"}:
                raise ValueError("supplied Liuyao tosses cannot declare another casting method")
            tosses = chart["tosses"]
            casting: dict[str, Any] = {
                "method": "supplied_complete_cast",
                "provenance": copy.deepcopy(
                    dict(chart.get("provenance") or {"kind": "user_supplied_cast"})
                ),
            }
        elif method == "digital_coin":
            seed = liuyao.normalize_transaction_cast_seed(
                request.metadata.get(liuyao.TRANSACTION_CAST_SEED_KEY)
            )
            generated = liuyao.cast_from_seed(seed)
            tosses = generated["tosses"]
            casting = {
                "method": "digital_coin",
                **generated,
                "seed_source": liuyao.TRANSACTION_CAST_SEED_SOURCE,
            }
        else:
            raise ValueError(
                "Liuyao requires a complete supplied cast or explicit digital_coin"
            )
        requested_relatives = self._requested_useful_spirit_relatives(request)
        question_class = liuyao.normalize_question_class(
            chart.get("question_class")
        )
        facts = liuyao.build_fact_layer(
            tosses,
            calendar_facts=calendar,
            casting=casting,
            requested_useful_spirit_relatives=tuple(requested_relatives),
            question_class=question_class,
        )
        cast = facts["output"]["casting"]
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "event_datetime": str(civil_datetime),
                "timezone": timezone_name,
                "location": location,
                "casting_method": cast["method"],
                "cast_seed": cast.get("seed"),
                "tosses": cast["tosses"],
                "calendar_digest": facts["calendar_normalization"]["calendar_digest"],
                "requested_useful_spirit_relatives": list(requested_relatives),
                "question_class": question_class,
            },
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "liuyao":
            raise ValueError("Liuyao refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "chart_digest": previous.facts["chart_digest"],
                "refined_from": previous.result_hash,
                "cast_seed": facts["output"]["casting"].get("seed"),
                "tosses": facts["output"]["casting"]["tosses"],
            },
            refined_from=previous.result_hash,
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "liuyao":
            raise ValueError("Liuyao extension system mismatch")
        if str(horizon.get("kind") or "instant") != "instant":
            return _unsupported_extension(base, requested_dimensions, horizon)
        chart = base.facts["chart_facts"]["output"]
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts={
                "selection_status": "evidence_bound",
                "requested_dimensions": list(requested_dimensions),
                "useful_spirit_candidates": copy.deepcopy(
                    chart["useful_spirit_candidates"]
                ),
                "line_facts": copy.deepcopy(chart["lines"]),
                "changed_plate_lines": copy.deepcopy(
                    chart["changed_plate_lines"]
                ),
                "returning_relations": copy.deepcopy(chart["relation_facts"]),
                "shi_ying_moving_relations": copy.deepcopy(
                    chart["shi_ying_moving_relations"]
                ),
            },
            rule_traces=(
                {
                    "source_dependency_id": "liuyao.relations.returning-and-useful-spirit-candidates",
                    "role": "calculated candidate scope without verdict",
                },
            ),
        )


class MeihuaProvider(_AdapterSeam, _SourceRouteMixin):
    """Deterministic Meihua provider for caller-declared casting methods."""

    provider_id = "mingli-master.meihua.v1"
    SOURCE_ROUTE = {
        "plan_system": "divination",
        "subsystem": "meihua",
        "registry_route": "meihua",
        "packs": [
            "divination/meihua-yishu",
            "divination/zhouyi-zhezhong",
            "divination/huangji-jingshi",
        ],
        "layers": ["hexagram", "body_use", "moving_line", "yi_context"],
        "chart": {
            "label": "卦象",
            "required_fields": [
                "primary_hexagram",
                "mutual_hexagram",
                "changed_hexagram",
                "moving_lines",
                "body_use",
                "body_relation_facts",
                "seasonal_strength",
                "casting_method",
            ],
        },
    }
    provider_version = meihua.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        method = chart.get("casting_method")
        missing: list[str] = []

        def positive_integer(field: str) -> bool:
            value = chart.get(field)
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value > 0
            )

        def nonempty_mapping(field: str) -> bool:
            value = chart.get(field)
            return isinstance(value, dict) and bool(value)

        def trigram(field: str) -> bool:
            return chart.get(field) in {"乾", "兑", "离", "震", "巽", "坎", "艮", "坤"}

        if method == "time":
            pass
        elif method == "supplied_number":
            if not positive_integer("number"):
                missing.append("number")
            if not nonempty_mapping("provenance"):
                missing.append("provenance")
        elif method == "sound_count":
            if not positive_integer("count"):
                missing.append("count")
            if not nonempty_mapping("observation_source"):
                missing.append("observation_source")
        elif method == "observation":
            if not trigram("upper_trigram"):
                missing.append("upper_trigram")
            if not trigram("lower_trigram"):
                missing.append("lower_trigram")
            if not nonempty_mapping("observation_source"):
                missing.append("observation_source")
        elif method == "supplied_hexagram":
            if not trigram("upper_trigram"):
                missing.append("upper_trigram")
            if not trigram("lower_trigram"):
                missing.append("lower_trigram")
            if not positive_integer("moving_line") or int(chart.get("moving_line") or 0) > 6:
                missing.append("moving_line")
            if not nonempty_mapping("provenance"):
                missing.append("provenance")
        else:
            missing.append("casting_method")
        if not (request.event_datetime or request.reference_datetime):
            missing.append("event_datetime")
        if not request.timezone:
            missing.append("timezone")
        if not request.location:
            missing.append("location")
        return tuple(missing)

    recast_replaces_chart_data = True

    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        validation = meihua.validate_fact_layer(facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Meihua fact validation failed: "
                + ", ".join(validation["codes"])
            )
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("Meihua requires shared calendar facts")
        diagnostics = (
            "explicit_casting_method_preserved",
            "main_mutual_changed_hexagrams_validated",
            "body_use_and_seasonal_facts_without_verdict",
            "liuyao_line_facts_excluded",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "meihua_plate_reused_without_recast",
                "caller_owned_evidence_planning",
            )
        return CalculationResult.create(
            system="meihua",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": facts["fact_digest"],
                "calendar_digest": calendar_digest,
                "fact_digest": facts["fact_digest"],
                "casting_digest": facts["output"]["casting"]["casting_digest"],
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        civil_datetime = request.event_datetime or request.reference_datetime
        timezone_name = str(request.timezone or "")
        location = str(request.location or "")
        if not civil_datetime or not timezone_name or not location:
            raise ValueError(
                "Meihua calculation requires event datetime, timezone, and location"
            )
        if isinstance(chart.get("casting_method"), Mapping):
            raise ValueError("Meihua casting_method must be a structured method id")
        calendar = calendar_core.normalize_calendar(
            str(civil_datetime),
            timezone_name=timezone_name,
            location=location,
            longitude=request.metadata.get("longitude"),
            latitude=request.metadata.get("latitude"),
            coordinate_source=request.metadata.get("coordinate_source"),
            coordinate_accuracy_meters=request.metadata.get("coordinate_accuracy_meters"),
            zi_hour_policy=str(request.metadata.get("zi_hour_policy") or "midnight"),
            time_basis_policy=str(request.metadata.get("time_basis_policy") or "civil"),
        )
        facts = meihua.build_from_method(chart, calendar_facts=calendar)
        casting = facts["output"]["casting"]
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "event_datetime": str(civil_datetime),
                "timezone": timezone_name,
                "location": location,
                "casting_method": casting["method"],
                "casting_digest": casting["casting_digest"],
                "calendar_digest": facts["calendar_digest"],
            },
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "meihua":
            raise ValueError("Meihua refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "chart_digest": previous.facts["chart_digest"],
                "refined_from": previous.result_hash,
                "casting_digest": previous.facts["casting_digest"],
            },
            refined_from=previous.result_hash,
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "meihua":
            raise ValueError("Meihua extension system mismatch")
        if str(horizon.get("kind") or "instant") != "instant":
            return _unsupported_extension(base, requested_dimensions, horizon)
        unsupported = tuple(
            dimension
            for dimension in requested_dimensions
            if dimension not in self.capability.dimensions
        )
        if unsupported:
            return _unsupported_extension(base, requested_dimensions, horizon)
        output = base.facts["chart_facts"]["output"]
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts={
                "requested_dimensions": list(requested_dimensions),
                "body_use": copy.deepcopy(output["body_use"]),
                "body_relation_facts": copy.deepcopy(
                    output["body_relation_facts"]
                ),
                "seasonal_strength": copy.deepcopy(output["seasonal_strength"]),
                "interpretive_candidates": copy.deepcopy(
                    output["interpretive_candidates"]
                ),
                "mutual_hexagram": copy.deepcopy(output["mutual_hexagram"]),
                "changed_hexagram": copy.deepcopy(output["changed_hexagram"]),
                "moving_lines": copy.deepcopy(output["moving_lines"]),
            },
            rule_traces=(
                {
                    "source_dependency_id": "meihua.body-use-elements-season",
                    "role": "calculated relation and seasonal scope without verdict",
                },
                {
                    "source_dependency_id": (
                        "meihua.classical-adjudication.body-use-candidates"
                    ),
                    "role": (
                        "source-adjudicated relation polarity; question and event "
                        "synthesis still pending"
                    ),
                },
            ),
        )


class QimenProvider(_AdapterSeam, _SourceRouteMixin):
    """Deterministic source-profile Qimen provider for one event instant."""

    provider_id = "mingli-master.qimen.v1"
    SOURCE_ROUTE = {
        "plan_system": "qimen",
        "subsystem": None,
        "registry_route": "qimen",
        "packs": [
            "san-shi/qimen-dunjia-tongzhi",
            "san-shi/qimen-faqiao",
        ],
        "layers": ["ju", "chief", "palaces", "instruments_wonders", "patterns"],
        "chart": {
            "label": "盘面",
            "required_fields": [
                "ju", "chief", "palaces", "instruments_wonders",
                "stars_doors_deities", "xunkong",
            ],
        },
    }
    provider_version = qimen.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        missing: list[str] = []
        event_instant = request.event_datetime or request.reference_datetime
        if not event_instant or str(event_instant).strip().lower() == "now":
            missing.append("event_datetime")
        if not request.timezone:
            missing.append("timezone")
        if not request.location:
            missing.append("location")
        return tuple(missing)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        validation = qimen.validate_fact_layer(facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Qimen fact validation failed: "
                + ", ".join(validation["codes"])
            )
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("Qimen requires shared calendar facts")
        diagnostics = (
            "source_profile_shijia_zhuanpan_chaibu",
            "complete_nine_palace_board_validated",
            "named_pattern_identities_are_source_adjudicated_not_event_verdicts",
            "alternative_school_profiles_not_merged",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "qimen_plate_reused_without_recast",
                "caller_owned_evidence_planning",
            )
        return CalculationResult.create(
            system="qimen",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": facts["fact_digest"],
                "calendar_digest": calendar_digest,
                "fact_digest": facts["fact_digest"],
                "board_digest": facts["output"]["board_digest"],
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        civil_datetime = request.event_datetime or request.reference_datetime
        timezone_name = str(request.timezone or "")
        location = str(request.location or "")
        if (
            not civil_datetime
            or str(civil_datetime).strip().lower() == "now"
            or not timezone_name
            or not location
        ):
            raise ValueError(
                "Qimen calculation requires an exact event datetime, timezone, and location"
            )
        calendar = calendar_core.normalize_calendar(
            str(civil_datetime),
            timezone_name=timezone_name,
            location=location,
            longitude=request.metadata.get("longitude"),
            latitude=request.metadata.get("latitude"),
            coordinate_source=request.metadata.get("coordinate_source"),
            coordinate_accuracy_meters=request.metadata.get("coordinate_accuracy_meters"),
            zi_hour_policy=str(request.metadata.get("zi_hour_policy") or "midnight"),
            time_basis_policy=str(request.metadata.get("time_basis_policy") or "civil"),
        )
        facts = qimen.build_fact_layer(calendar)
        output = facts["output"]
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "event_datetime": str(civil_datetime),
                "timezone": timezone_name,
                "location": location,
                "profile_id": qimen.TABLE_PROFILE,
                "calendar_digest": facts["calendar_digest"],
                "board_digest": output["board_digest"],
            },
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "qimen":
            raise ValueError("Qimen refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "chart_digest": previous.facts["chart_digest"],
                "refined_from": previous.result_hash,
                "board_digest": previous.facts["board_digest"],
            },
            refined_from=previous.result_hash,
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "qimen":
            raise ValueError("Qimen extension system mismatch")
        if str(horizon.get("kind") or "instant") != "instant":
            return _unsupported_extension(base, requested_dimensions, horizon)
        unsupported = tuple(
            dimension
            for dimension in requested_dimensions
            if dimension not in self.capability.dimensions
        )
        if unsupported:
            return _unsupported_extension(base, requested_dimensions, horizon)
        output = base.facts["chart_facts"]["output"]
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts={
                "status": "calculated_board_scope_not_verdict",
                "requested_dimensions": list(requested_dimensions),
                "ju": copy.deepcopy(output["ju"]),
                "chief": copy.deepcopy(output["chief"]),
                "director": copy.deepcopy(output["director"]),
                "palaces": copy.deepcopy(output["palaces"]),
                "xunkong": copy.deepcopy(output["xunkong"]),
                "horse": copy.deepcopy(output["horse"]),
                "named_patterns": copy.deepcopy(output["named_patterns"]),
            },
            rule_traces=tuple(
                {
                    "source_dependency_id": dependency,
                    "role": "calculated board fact without verdict",
                }
                for dependency in qimen.SOURCE_DEPENDENCIES
            ),
        )


class TaiyiProvider(_AdapterSeam, _SourceRouteMixin):
    """Deterministic annual Taiyi provider with an explicit macro scope."""

    provider_id = "mingli-master.taiyi.v1"
    SOURCE_ROUTE = {
        "plan_system": "taiyi",
        "subsystem": None,
        "registry_route": "taiyi",
        "packs": ["san-shi/taiyi-shenshu"],
        "layers": [
            "calendar",
            "epoch",
            "cycle",
            "board",
            "host_guest",
            "long_cycle_deities",
            "board_predicates",
            "scope",
        ],
        "chart": {
            "label": "太乙年计盘",
            "required_fields": [
                "calendar",
                "epoch",
                "cycle",
                "board",
                "host_guest",
                "long_cycle_deities",
                "scope_contract",
            ],
        },
        "scope_requirement": {"calculation_object": "macro_historical"},
    }
    provider_version = taiyi.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        missing: list[str] = []
        reference_instant = request.reference_datetime
        if not reference_instant or str(reference_instant).strip().lower() == "now":
            missing.append("reference_datetime")
        if not request.timezone:
            missing.append("timezone")
        if not request.location:
            missing.append("location")
        return tuple(missing)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        validation = taiyi.validate_fact_layer(facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Taiyi fact validation failed: "
                + ", ".join(validation["codes"])
            )
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("Taiyi requires shared calendar facts")
        diagnostics = (
            "source_profile_taiyi_jinjing_annual_yang",
            "complete_72_board_cycle_validated",
            "long_cycle_epochs_kept_separate",
            "annual_macro_historical_scope_only",
            "board_pattern_identities_are_source_adjudicated_not_event_verdicts",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "taiyi_board_reused_without_recalculation",
                "caller_owned_evidence_planning",
            )
        output = facts["output"]
        return CalculationResult.create(
            system="taiyi",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": facts["fact_digest"],
                "calendar_digest": calendar_digest,
                "fact_digest": facts["fact_digest"],
                "board_digest": output["board_digest"],
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        reference_datetime = str(request.reference_datetime or "")
        timezone_name = str(request.timezone or "")
        location = str(request.location or "")
        if (
            not reference_datetime
            or reference_datetime.strip().lower() == "now"
            or not timezone_name
            or not location
        ):
            raise ValueError(
                "Taiyi calculation requires an exact reference datetime, timezone, and location"
            )
        calendar = calendar_core.normalize_calendar(
            reference_datetime,
            timezone_name=timezone_name,
            location=location,
            longitude=request.metadata.get("longitude"),
            latitude=request.metadata.get("latitude"),
            coordinate_source=request.metadata.get("coordinate_source"),
            coordinate_accuracy_meters=request.metadata.get("coordinate_accuracy_meters"),
            zi_hour_policy=str(request.metadata.get("zi_hour_policy") or "midnight"),
            time_basis_policy=str(request.metadata.get("time_basis_policy") or "civil"),
        )
        facts = taiyi.build_fact_layer(calendar)
        output = facts["output"]
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "reference_datetime": reference_datetime,
                "timezone": timezone_name,
                "location": location,
                "profile_id": taiyi.TABLE_PROFILE,
                "declared_scope": taiyi.FACT_LAYER_SCOPE,
                "calendar_digest": facts["calendar_digest"],
                "board_digest": output["board_digest"],
            },
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "taiyi":
            raise ValueError("Taiyi refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "chart_digest": previous.facts["chart_digest"],
                "refined_from": previous.result_hash,
                "board_digest": previous.facts["board_digest"],
                "declared_scope": taiyi.FACT_LAYER_SCOPE,
            },
            refined_from=previous.result_hash,
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "taiyi":
            raise ValueError("Taiyi extension system mismatch")
        if str(horizon.get("kind") or "year") != "year":
            return _unsupported_extension(base, requested_dimensions, horizon)
        unsupported = tuple(
            dimension
            for dimension in requested_dimensions
            if dimension not in self.capability.dimensions
        )
        if unsupported:
            return _unsupported_extension(base, requested_dimensions, horizon)
        output = base.facts["chart_facts"]["output"]
        calculated_year = str(output["calendar"]["lunar_year"])
        requested_start = str(horizon.get("start") or calculated_year)
        requested_end = str(horizon.get("end") or requested_start)
        if requested_start != calculated_year or requested_end != calculated_year:
            return _unsupported_extension(base, requested_dimensions, horizon)
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts={
                "status": "calculated_annual_board_scope_not_verdict",
                "requested_dimensions": list(requested_dimensions),
                "calendar": copy.deepcopy(output["calendar"]),
                "cycle": copy.deepcopy(output["cycle"]),
                "board": copy.deepcopy(output["board"]),
                "host_guest": copy.deepcopy(output["host_guest"]),
                "long_cycle_deities": copy.deepcopy(output["long_cycle_deities"]),
                "board_predicates": copy.deepcopy(output["board_predicates"]),
                "scope_contract": copy.deepcopy(output["scope_contract"]),
            },
            rule_traces=tuple(
                {
                    "source_dependency_id": dependency,
                    "role": "calculated annual board fact without event verdict",
                }
                for dependency in taiyi.SOURCE_DEPENDENCIES
            ),
        )


class SelectionProvider(_AdapterSeam, _SourceRouteMixin):
    """Deterministic bounded candidate generator and explainable ranker."""

    provider_id = "mingli-master.selection.v1"
    SOURCE_ROUTE = {
        "plan_system": "selection",
        "subsystem": None,
        "registry_route": "selection",
        "packs": [
            "selection/xieji-bianfang-shu",
            "selection/xingli-kaoyuan",
        ],
        "default_comparison_packs": [
            "selection/yuqia-ji",
            "selection/donggong-zeri",
        ],
        "layers": [
            "calendar_candidates",
            "jianchu_mansions_gods",
            "hour_facts",
            "event_profile",
            "official_yiji",
            "participant_conflicts",
            "explainable_ranking",
            "lineage_disagreements",
            "source_conditioned_patterns",
        ],
        "chart": {
            "label": "候选日课",
            "required_fields": [
                "event_profile",
                "calendar_candidates",
                "date_time_candidates",
                "eligible_candidates",
                "eligible_date_time_candidates",
                "eliminations",
                "ranking",
                "lineage_policy",
                "source_conditioned_patterns",
            ],
        },
    }

    def source_route(
        self,
        goal: Mapping[str, Any],
        facts: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        route = super().source_route(goal, facts)
        chart_facts = (
            (facts or {}).get("chart_facts")
            if isinstance((facts or {}).get("chart_facts"), Mapping)
            else facts or {}
        )
        selection_spec = (
            (chart_facts.get("input") or {}).get("selection_spec")
            if isinstance(chart_facts, Mapping)
            else {}
        )
        route["active_default_comparison_packs"] = (
            list(route.get("default_comparison_packs") or ())
            if isinstance(selection_spec, Mapping)
            and selection_spec.get("include_folk_comparison") is True
            else []
        )
        return route
    provider_version = selection.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        spec = chart.get("selection_spec")
        spec = spec if isinstance(spec, dict) else {}
        missing: list[str] = []
        if not spec.get("event_profile"):
            missing.append("event_profile")
        if (
            spec.get("event_profile")
            and spec.get("event_profile") != "generic_selection"
            and (
                not isinstance(spec.get("requested_actions"), list)
                or not spec.get("requested_actions")
            )
        ):
            missing.append("requested_actions")
        date_range = spec.get("date_range")
        if not (
            isinstance(date_range, dict)
            and date_range.get("start")
            and date_range.get("end")
        ):
            missing.append("date_range")
        if not request.timezone:
            missing.append("timezone")
        if not request.location:
            missing.append("location")
        return tuple(missing)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def public_basis_projection(
        self, chart_facts: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Bound large candidate lists while keeping complete counts visible."""

        visible = chart_facts.get("output")
        if not isinstance(visible, Mapping):
            visible = chart_facts
        selection_output = visible
        ranking = (
            dict(selection_output.get("ranking") or {})
            if isinstance(selection_output.get("ranking"), Mapping)
            else {}
        )
        count_fields = (
            "calendar_candidates",
            "date_time_candidates",
            "eligible_candidates",
            "eligible_date_time_candidates",
            "eliminations",
            "source_conditioned_patterns",
        )
        complete_counts = {
            field: len(selection_output.get(field) or [])
            for field in count_fields
            if isinstance(selection_output.get(field), list)
        }
        for field in (
            "ordered_candidate_ids",
            "eligible_candidate_ids",
            "ordered_date_time_candidate_ids",
            "eligible_date_time_candidate_ids",
        ):
            values = ranking.get(field)
            if isinstance(values, list):
                complete_counts[f"ranking.{field}"] = len(values)
                ranking[field] = values[:12]
        return {
            "event_profile": selection_output.get("event_profile"),
            "calendar_candidates": (
                selection_output.get("calendar_candidates") or []
            )[:12],
            "date_time_candidates": (
                selection_output.get("date_time_candidates") or []
            )[:12],
            "eligible_candidates": (
                selection_output.get("eligible_candidates") or []
            )[:12],
            "eligible_date_time_candidates": selection_output.get(
                "eligible_date_time_candidates"
            )
            [:12]
            if isinstance(
                selection_output.get("eligible_date_time_candidates"), list
            )
            else [],
            "eliminations": (selection_output.get("eliminations") or [])[:12],
            "no_valid_candidate": selection_output.get("no_valid_candidate"),
            "ranking": ranking,
            "lineage_policy": selection_output.get("lineage_policy") or {},
            "source_conditioned_patterns": list(
                selection_output.get("source_conditioned_patterns") or []
            )[:12],
            "basis_projection": {
                "candidate_limit_per_list": 12,
                "complete_counts": complete_counts,
                "full_facts_remain_in_calculation_record": True,
            },
        }

    def public_extension_projection(
        self, extension: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Bound the requested extension facts to the same public budget."""

        projected = dict(extension)
        extension_facts = dict(projected.get("facts") or {})
        projected_counts: dict[str, int] = {}
        for field in (
            "calendar_candidates",
            "date_time_candidates",
            "eligible_candidates",
            "eligible_date_time_candidates",
            "source_conditioned_patterns",
        ):
            rows = extension_facts.get(field)
            if isinstance(rows, list):
                projected_counts[field] = len(rows)
        ranking = extension_facts.get("ranking")
        if not isinstance(ranking, Mapping):
            ranking = {}
        projected["facts"] = {
            "status": extension_facts.get("status"),
            "event_profile": extension_facts.get("event_profile"),
            "eligible_candidate_ids": list(
                ranking.get("eligible_candidate_ids") or []
            )[:12],
            "eligible_date_time_candidate_ids": list(
                ranking.get("eligible_date_time_candidate_ids") or []
            )[:12],
            "source_conditioned_patterns": list(
                extension_facts.get("source_conditioned_patterns") or []
            )[:12],
            "basis_projection": {
                "candidate_limit_per_list": 12,
                "complete_counts": projected_counts,
                "full_facts_remain_in_calculation_record": True,
            },
        }
        return projected

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        validation = selection.validate_fact_layer(facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Selection fact validation failed: "
                + ", ".join(validation["codes"])
            )
        diagnostics = (
            "deterministic_selection_candidates",
            "official_and_folk_lineages_separated",
            "explainable_ranking_without_opaque_score",
            "candidate_facts_are_not_event_guarantees",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "selection_candidates_reused_without_recalculation",
                "caller_owned_evidence_planning",
            )
        calendar_digest = canonical_digest(
            facts["calendar_normalization"]["calendar_digests"]
        )
        return CalculationResult.create(
            system="selection",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": facts["fact_digest"],
                "fact_digest": facts["fact_digest"],
                "calendar_digest": calendar_digest,
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        raw = request.chart_data if isinstance(request.chart_data, dict) else {}
        spec = raw.get("selection_spec")
        if not isinstance(spec, Mapping):
            raise ValueError("Selection requires chart_data.selection_spec")
        timezone_name = str(request.timezone or "")
        location = str(request.location or "")
        facts = selection.build_fact_layer(
            spec,
            timezone_name=timezone_name,
            location=location,
            longitude=request.metadata.get("longitude"),
            latitude=request.metadata.get("latitude"),
            coordinate_source=request.metadata.get("coordinate_source"),
        )
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "selection_spec": facts["input"]["selection_spec"],
                "timezone": timezone_name,
                "location": location,
                "normalized_input": {
                    "selection_spec": facts["input"]["selection_spec"],
                    "timezone": timezone_name,
                    "location": location,
                    "longitude": request.metadata.get("longitude"),
                    "latitude": request.metadata.get("latitude"),
                    "coordinate_source": request.metadata.get(
                        "coordinate_source"
                    ),
                },
            },
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "selection":
            raise ValueError("Selection refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "chart_digest": previous.facts["chart_digest"],
                "refined_from": previous.result_hash,
            },
            refined_from=previous.result_hash,
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "selection":
            raise ValueError("Selection extension system mismatch")
        unsupported = tuple(
            dimension
            for dimension in requested_dimensions
            if dimension not in self.capability.dimensions
        )
        chart_facts = base.facts.get("chart_facts") or {}
        input_facts = chart_facts.get("input") or {}
        try:
            requested_range = _selection_horizon_date_range(horizon)
            spec = copy.deepcopy(dict(input_facts["selection_spec"]))
            spec["date_range"] = requested_range
            extension_facts = selection.build_fact_layer(
                spec,
                timezone_name=str(input_facts.get("timezone") or ""),
                location=str(input_facts.get("location") or ""),
                longitude=input_facts.get("longitude"),
                latitude=input_facts.get("latitude"),
                coordinate_source=input_facts.get("coordinate_source"),
            )
        except (KeyError, TypeError, ValueError):
            return _unsupported_extension(base, requested_dimensions, horizon)
        if unsupported:
            return _unsupported_extension(base, requested_dimensions, horizon)
        output = extension_facts["output"]
        compact_days = [
            {
                "candidate_id": row["candidate_id"],
                "civil_date": row["civil_date"],
                "best_date_time_basis": copy.deepcopy(
                    row["best_date_time_basis"]
                ),
                "eligibility": copy.deepcopy(row["eligibility"]),
                "rejection_reasons": copy.deepcopy(row["rejection_reasons"]),
                "ranking_components": copy.deepcopy(row["ranking_components"]),
                "active_source_rule_ids": list(row["active_source_rule_ids"]),
            }
            for row in output["calendar_candidates"]
        ]
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts={
                "status": "calculated_bounded_selection_scope_not_event_guarantee",
                "event_profile": output["event_profile"],
                "calendar_candidates": compact_days,
                "date_time_candidates": [
                    copy.deepcopy(row["best_date_time_basis"])
                    for row in output["calendar_candidates"]
                ],
                "eligible_candidates": list(
                    output["ranking"]["eligible_candidate_ids"]
                ),
                "eligible_date_time_candidates": list(
                    output["ranking"]["eligible_date_time_candidate_ids"]
                ),
                "eliminations": copy.deepcopy(output["eliminations"]),
                "ranking": copy.deepcopy(output["ranking"]),
                "lineage_policy": copy.deepcopy(output["lineage_policy"]),
                "source_conditioned_patterns": copy.deepcopy(
                    output["source_conditioned_patterns"]
                ),
            },
            rule_traces=tuple(
                {
                    "source_dependency_id": dependency,
                    "role": "calculated Selection fact without event guarantee",
                }
                for dependency in selection.SOURCE_DEPENDENCIES
            ),
        )


def _parse_reference(request: ReadingRequest, timezone_name: str) -> datetime:
    timezone = ZoneInfo(timezone_name)
    if not request.reference_datetime or request.reference_datetime == "now":
        return datetime.now(timezone)
    parsed = datetime.fromisoformat(request.reference_datetime)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


_EXTENDED_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_EXTENDED_DATETIME_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}"
    r"(:[0-9]{2}(\.[0-9]+)?)?"
    r"(Z|[+-][0-9]{2}:[0-9]{2}(:[0-9]{2})?)?$"
)


def _strict_civil_date(text: str) -> date | None:
    """Parse a strict ``YYYY-MM-DD`` literal, or return None.

    ``date.fromisoformat`` alone would also accept compact dates and ISO
    week-dates; the public contract declares only the extended spelling, so
    the full string is matched first and the real month/day values are then
    verified by ``fromisoformat``.
    """

    if not _EXTENDED_DATE_RE.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _strict_iso_datetime(text: str) -> datetime | None:
    """Parse a full ISO-8601 extended datetime, or return None.

    The literal must carry a strict ``YYYY-MM-DD`` date prefix followed by an
    explicit time part.  Naive values are read in the caller's timezone, aware
    values (offset or uppercase ``Z``) are converted by the caller.  Basic
    datetime spellings (``20260803T100000``), a bare date smuggled in as
    midnight, ISO week-dates and partial month tokens are all refused here.
    """

    if not _EXTENDED_DATETIME_RE.fullmatch(text):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _civil_day(text: str, timezone_name: str) -> date:
    """Resolve one caller-supplied boundary to the civil day it denotes.

    A bare ``YYYY-MM-DD`` is a civil date and is taken as written.  Anything
    else must be a full ISO-8601 instant with the ``T`` separator, and an
    instant only names a civil day once it is placed in a zone: an aware value
    (offset or ``Z``) is converted into this provider's business timezone
    first, a naive value is read as already being in it.
    ``2026-08-03T20:00:00Z`` is therefore 2026-08-04 in ``Asia/Shanghai`` --
    truncating the text would have answered for the wrong day.

    The full submitted string is validated as-is, never trimmed first: a
    leading/trailing-space padded literal, a whitespace-only literal, a
    compact date, an ISO week-date, a basic datetime, a space-separated
    datetime, a partial month or prose are all refused so the caller gets a
    real Stopped instead of a silently repaired or guessed period.
    """

    civil_date = _strict_civil_date(text)
    if civil_date is not None:
        return civil_date
    moment = _strict_iso_datetime(text)
    if moment is None:
        raise ValueError(
            "horizon boundary must be YYYY-MM-DD or a full ISO-8601 datetime"
        )
    if moment.tzinfo is None:
        return moment.date()
    return moment.astimezone(ZoneInfo(timezone_name)).date()


def _near_time_period_days(
    kind: str,
    start_text: Any,
    end_text: Any,
    *,
    timezone_name: str,
    fallback_anchor: date,
) -> tuple[date, ...]:
    """The exact civil days one near-time horizon resolves to.

    Both the calculation and the public projection resolve the caller's
    boundaries through this one function, so the range a host is told about is
    always the range that was actually cast.  Either boundary may carry the
    anchor: absent, one boundary, or two boundaries inside the same civil day
    all select the period containing that anchor, so an ``end``-only request
    binds its own day instead of falling back to the reference.  Two distinct
    civil days are taken literally and must already form the exact period, so
    a partial or reversed span raises instead of being widened into something
    the user never asked for.
    """

    # Only a null or empty literal is an absent boundary.  Anything else --
    # including whitespace-only or padded text -- is validated as-is below and
    # refused, never silently repaired into an absent or trimmed value.
    start = (
        _civil_day(str(start_text), timezone_name)
        if start_text is not None and str(start_text) != ""
        else None
    )
    end = (
        _civil_day(str(end_text), timezone_name)
        if end_text is not None and str(end_text) != ""
        else None
    )
    if start is None and end is None:
        anchor = fallback_anchor
        single_anchor = True
    elif end is None:
        anchor = start
        single_anchor = True
    elif start is None:
        anchor = end
        single_anchor = True
    elif start == end:
        anchor = start
        single_anchor = True
    else:
        anchor = start
        single_anchor = False
    if kind == "day":
        if not single_anchor:
            raise ValueError("daily fortune requires one exact target day")
        return (anchor,)
    if kind != "week":
        raise ValueError(f"unsupported fortune horizon: {kind}")
    if single_anchor:
        first = anchor - timedelta(days=anchor.weekday())
        last = first + timedelta(days=6)
    else:
        first, last = anchor, end
    if last - first != timedelta(days=6):
        raise ValueError("weekly fortune requires one exact seven-day range")
    return tuple(first + timedelta(days=index) for index in range(7))


def _target_date(request: ReadingRequest, timezone_name: str) -> date:
    configured = request.metadata.get("target_date")
    if configured:
        return _civil_day(str(configured), timezone_name)
    reference_day = _parse_reference(request, timezone_name).date()
    if request.intent:
        horizon = IntentFrame.from_dict(request.intent).horizon
        if horizon.kind == "day" and (horizon.start or horizon.end):
            return _near_time_period_days(
                horizon.kind,
                horizon.start,
                horizon.end,
                timezone_name=timezone_name,
                fallback_anchor=reference_day,
            )[0]
    return reference_day


def _target_dates(request: ReadingRequest, timezone_name: str) -> tuple[date, ...]:
    if not request.intent:
        return (_target_date(request, timezone_name),)
    frame = IntentFrame.from_dict(request.intent)
    if frame.horizon.kind != "week":
        return (_target_date(request, timezone_name),)
    # The reference stays a full instant; only its civil date can anchor a
    # week, and it is used solely when the caller named no boundary at all.
    return _near_time_period_days(
        "week",
        frame.horizon.start,
        frame.horizon.end,
        timezone_name=timezone_name,
        fallback_anchor=_parse_reference(request, timezone_name).date(),
    )


def _resolved_profile(
    request: ReadingRequest,
    default_profile: Mapping[str, Any],
) -> dict[str, Any]:
    identity_fields = (
        "birth_datetime",
        "datetime",
        "timezone",
        "location",
        "gender",
    )
    request_has_identity = any(
        request.birth_data.get(field) for field in identity_fields
    )
    profile = dict(request.birth_data if request_has_identity else default_profile)
    if request_has_identity:
        if request.timezone and not profile.get("timezone"):
            profile["timezone"] = request.timezone
        if request.location and not profile.get("location"):
            profile["location"] = request.location
    if not profile.get("birth_datetime") and profile.get("datetime"):
        profile["birth_datetime"] = profile["datetime"]
    missing = [
        field for field in FORTUNE_REQUIRED_PROFILE_FIELDS if not profile.get(field)
    ]
    if missing:
        raise ValueError("daily fortune requires a validated natal profile")
    expected = list(profile.get("expected_pillars") or ())
    if expected and len(expected) != 4:
        raise ValueError("expected_pillars must contain four pillars")
    profile["expected_pillars"] = expected
    return profile


class FortuneProvider(_AdapterSeam, _SourceRouteMixin):
    provider_id = "mingli-master.fortune.v6"
    provider_version = near_time_fortune_adapter.CONTRACT_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        required = ("birth_datetime", "timezone", "location", "gender")
        missing = [field for field in required if not _birth_value(request, field)]
        if not request.reference_datetime:
            missing.append("reference_datetime")
        return tuple(missing)

    SOURCE_ROUTE = {
        "plan_system": "fortune",
        "subsystem": None,
        "registry_route": "fortune",
        "packs": [
            "bazi/yuanhai-ziping",
            "bazi/ditiansui-chanwei",
            "bazi/qiongtong-baojian",
        ],
        "layers": ["day_master", "strength_flow", "tiaohou", "luck_transit"],
        "chart": {
            "label": "时势",
            "required_fields": ["natal_pillars", "active_luck_cycle", "target_day"],
            "fact_paths": {
                "natal_pillars": "birth_fact_layer.natal_pillars",
                "active_luck_cycle": "birth_fact_layer.active_luck_cycle",
                "target_day": "calendar_normalization.ganzhi.day",
            },
        },
        "compatible_rule_systems": ["bazi"],
    }
    extend_source_plan = staticmethod(_qiongtong_plan_extension)

    def __init__(
        self,
        skill_dir: str | Path,
        profile: Mapping[str, Any] | None = None,
    ) -> None:
        self.skill_dir = Path(skill_dir).resolve()
        self.profile = dict(profile or {})

    def enrich_request(
        self,
        request: ReadingRequest,
        context: RuntimeContext | None,
        *,
        routed: bool = True,
    ) -> ReadingRequest:
        """Read the opted-in default natal profile from the runtime context."""

        changes = _default_profile_changes(
            request,
            context,
            ensure_datetime_alias=False,
        )
        return _with_request_changes(request, changes)

    def _run_adapter(
        self,
        *,
        profile: dict[str, Any],
        request: ReadingRequest,
        target: date,
    ) -> dict[str, Any]:
        command = [
            *runtime_command(),
            str(self.skill_dir / "scripts" / "near_time_fortune_adapter.py"),
            "--birth-datetime",
            str(profile["birth_datetime"]),
            "--timezone",
            str(profile["timezone"]),
            "--location",
            str(profile["location"]),
            "--gender",
            str(profile["gender"]),
            "--window",
            f"{target.isoformat()} 00:00-{target.isoformat()} 23:59",
            "--at",
            request.reference_datetime or "now",
            "--zi-hour-policy",
            str(profile.get("zi_hour_policy") or "midnight"),
            "--source-tool",
            "adapter",
        ]
        if profile["expected_pillars"]:
            command.extend(
                [
                    "--expected-pillars",
                    *(str(item) for item in profile["expected_pillars"]),
                ]
            )
        if profile.get("longitude") is not None:
            command.extend(["--longitude", str(profile["longitude"])])
        if profile.get("latitude") is not None:
            command.extend(["--latitude", str(profile["latitude"])])
        if profile.get("coordinate_source"):
            command.extend(
                ["--coordinate-source", str(profile["coordinate_source"])]
            )
        if profile.get("coordinate_accuracy_meters") is not None:
            command.extend(
                ["--coordinate-accuracy-meters", str(profile["coordinate_accuracy_meters"])]
            )
        command.extend(
            ["--time-basis-policy", str(profile.get("time_basis_policy") or "civil")]
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "near-time adapter failed")
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError("near-time adapter returned a non-object")
        return payload

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        diagnostics = (
            "deterministic_calendar_validated",
            "natal_luck_and_tiaohou_present",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "daily_chart_reused_without_recalculation",
                "caller_owned_evidence_planning",
            )
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("daily fortune requires shared calendar facts")
        natal_fact_digest = str(
            (facts.get("birth_fact_layer") or {}).get("natal_fact_digest")
            or ""
        )
        if not re.fullmatch(r"[0-9a-f]{64}", natal_fact_digest):
            raise RuntimeError("daily fortune requires a deterministic natal fact digest")
        return CalculationResult.create(
            system="fortune",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "calendar_digest": calendar_digest,
                "natal_fact_digest": natal_fact_digest,
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        if not request.reference_datetime:
            raise ValueError("Fortune calculation requires reference_datetime")
        profile = _resolved_profile(request, self.profile)
        timezone_name = str(profile["timezone"])
        targets = _target_dates(request, timezone_name)
        period_facts = {
            target.isoformat(): self._run_adapter(
                profile=profile,
                request=request,
                target=target,
            )
            for target in targets
        }
        for period in period_facts.values():
            birth_adapter = (
                period.get("birth_fact_layer", {}).get("adapter", {})
                if isinstance(period.get("birth_fact_layer"), dict)
                else {}
            )
            if isinstance(birth_adapter, dict):
                birth_adapter["generated_at"] = "deterministic-chart-identity"
        facts = copy.deepcopy(period_facts[targets[0].isoformat()])
        facts["period_fact_layers"] = period_facts
        validation = adapter_validate.validate_payload("fortune", facts)
        if not validation["ok"]:
            raise RuntimeError(
                "near-time fact validation failed: "
                + ", ".join(validation["codes"])
            )
        birth_fact_layer = facts.get("birth_fact_layer")
        calendar = (
            birth_fact_layer.get("calendar_normalization")
            if isinstance(birth_fact_layer, Mapping)
            else None
        )
        if not isinstance(calendar, Mapping):
            raise RuntimeError("daily fortune requires natal calendar facts")
        facts["public_calendar_normalization"] = _public_calendar_normalization(
            calendar
        )
        input_payload = {
            "query": request.query,
            "reference_datetime": request.reference_datetime,
            "target_period": {
                "start": targets[0].isoformat(),
                "end": targets[-1].isoformat(),
            },
            "profile": profile,
        }
        return self._compile(request, facts, input_payload=input_payload)

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "fortune":
            raise ValueError("daily-fortune refinement system mismatch")
        del request
        return previous

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "fortune":
            raise ValueError("daily-fortune extension system mismatch")
        chart_facts = base.facts.get("chart_facts") or {}
        target = str(chart_facts.get("target_date") or "")
        period_layers = chart_facts.get("period_fact_layers") or {}
        kind = str(horizon.get("kind") or "")
        # Resolve the caller's boundaries exactly the way the calculation did,
        # in the business timezone the calendar already settled on, so the
        # published range is the range that was cast.  An unresolvable horizon
        # is not a crash here: it simply binds nothing and the extension is
        # reported as unsupported.
        timezone_name = str(
            (chart_facts.get("calendar_normalization") or {}).get("timezone") or ""
        )
        effective: tuple[date, ...] = ()
        if timezone_name and target:
            try:
                effective = _near_time_period_days(
                    kind,
                    horizon.get("start"),
                    horizon.get("end"),
                    timezone_name=timezone_name,
                    fallback_anchor=date.fromisoformat(target),
                )
            except ValueError:
                effective = ()
        if not effective:
            return _unsupported_extension(base, requested_dimensions, horizon)
        requested_start = effective[0].isoformat()
        requested_end = effective[-1].isoformat()
        if kind == "week" and isinstance(period_layers, Mapping):
            available_periods = tuple(sorted(str(item) for item in period_layers))
            if (
                len(available_periods) == 7
                and requested_start == available_periods[0]
                and requested_end == available_periods[-1]
            ):
                target_period_facts = {
                    period: self._period_public_facts(period_layers[period])
                    for period in available_periods
                }
                period_markers = [
                    self._period_marker(period_layers[period])
                    for period in available_periods
                ]
                return _attach_extension(
                    base,
                    requested_dimensions,
                    horizon,
                    status="complete",
                    facts={
                        "target_period": {
                            "kind": "week",
                            "start": requested_start,
                            "end": requested_end,
                        },
                        "available_periods": list(available_periods),
                        "target_period_facts": target_period_facts,
                        "period_markers": period_markers,
                    },
                    rule_traces=(
                        {
                            "rule_id": "fortune.exact-seven-day-period-v1",
                            "source_dependency_id": "fortune.bounded-target-period-over-bazi",
                            "operation": "compose seven calculated daily fact layers into one bounded period",
                        },
                    ),
                )
        if (
            not target
            or kind not in {"day", "instant"}
            or requested_start != target
            or requested_end != target
        ):
            return _unsupported_extension(base, requested_dimensions, horizon)
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts={
                "target_period": {
                    "kind": "day",
                    "start": target,
                    "end": target,
                },
                "available_periods": [target],
                "target_period_facts": {
                    "calendar_normalization": copy.deepcopy(
                        chart_facts.get("calendar_normalization") or {}
                    ),
                    "active_luck_cycle": copy.deepcopy(
                        (chart_facts.get("birth_fact_layer") or {}).get(
                            "active_luck_cycle"
                        )
                    ),
                    "active_luck_cycle_detail": copy.deepcopy(
                        (chart_facts.get("birth_fact_layer") or {}).get(
                            "active_luck_cycle_detail"
                        )
                    ),
                    "transit_layers": copy.deepcopy(
                        chart_facts.get("transit_layers") or {}
                    ),
                    "bazi_day_fact_layer": copy.deepcopy(
                        chart_facts.get("bazi_day_fact_layer") or {}
                    ),
                    "selected_bazi_day_segment": copy.deepcopy(
                        chart_facts.get("selected_bazi_day_segment") or {}
                    ),
                    "mechanism_stack": copy.deepcopy(
                        chart_facts.get("mechanism_stack") or {}
                    ),
                    "hour_profiles": copy.deepcopy(
                        chart_facts.get("hour_profiles") or []
                    ),
                },
                "period_markers": [self._period_marker(chart_facts)],
            },
            rule_traces=(
                {
                    "rule_id": "fortune.single-target-day-v1",
                    "source_dependency_id": "fortune.bounded-target-period-over-bazi",
                    "operation": "bind the already-calculated daily fact layer to exactly one target date",
                },
            ),
        )

    @staticmethod
    def _period_public_facts(facts: Mapping[str, Any]) -> dict[str, Any]:
        birth = facts.get("birth_fact_layer") or {}
        return {
            "calendar_normalization": copy.deepcopy(
                facts.get("calendar_normalization") or {}
            ),
            "active_luck_cycle": copy.deepcopy(birth.get("active_luck_cycle")),
            "active_luck_cycle_detail": copy.deepcopy(
                birth.get("active_luck_cycle_detail")
            ),
            "transit_layers": copy.deepcopy(facts.get("transit_layers") or {}),
            "bazi_day_fact_layer": copy.deepcopy(
                facts.get("bazi_day_fact_layer") or {}
            ),
            "selected_bazi_day_segment": copy.deepcopy(
                facts.get("selected_bazi_day_segment") or {}
            ),
            "mechanism_stack": copy.deepcopy(facts.get("mechanism_stack") or {}),
        }

    @staticmethod
    def _period_marker(facts: Mapping[str, Any]) -> dict[str, Any]:
        """Publish a compact, deterministic period surface for natural prose.

        The full calculated day layer remains in the private calculation and
        extension record.  This view contains only the stable data needed to
        explain a requested period without making the caller ingest a large
        implementation trace or invent a semantic verdict.
        """

        calendar = facts.get("calendar_normalization")
        calendar = calendar if isinstance(calendar, Mapping) else {}
        ganzhi = calendar.get("ganzhi")
        ganzhi = ganzhi if isinstance(ganzhi, Mapping) else {}
        birth = facts.get("birth_fact_layer")
        birth = birth if isinstance(birth, Mapping) else {}
        transits = facts.get("transit_layers")
        transits = transits if isinstance(transits, Mapping) else {}
        day = transits.get("day")
        day = day if isinstance(day, Mapping) else {}
        day_relations = day.get("branch_relations_to_natal")
        relations = []
        for relation in day_relations if isinstance(day_relations, list) else ():
            if not isinstance(relation, Mapping):
                continue
            relations.append(
                {
                    key: relation[key]
                    for key in (
                        "relation",
                        "natal_position",
                        "natal_position_label",
                        "transit_branch",
                    )
                    if key in relation
                }
            )
        claim_contract = facts.get("public_claim_contract")
        claim_contract = (
            claim_contract if isinstance(claim_contract, Mapping) else {}
        )
        mechanism_stack = facts.get("mechanism_stack")
        mechanism_stack = (
            mechanism_stack if isinstance(mechanism_stack, Mapping) else {}
        )
        return {
            "date": str(facts.get("target_date") or calendar.get("solar_date") or ""),
            "day_pillar": str(day.get("pillar") or ganzhi.get("day") or ""),
            "day_role": str(day.get("stem_ten_god") or ""),
            "active_luck_cycle": birth.get("active_luck_cycle"),
            "relations": relations,
            "primary_mechanism_ids": list(
                claim_contract.get("primary_mechanism_ids") or ()
            ),
            "decisive_mechanism_ids": list(
                claim_contract.get("decisive_mechanism_ids") or ()
            ),
            "specific_event_policy": str(
                claim_contract.get("specificity_policy") or ""
            ),
            "unresolved_boundaries": list(
                mechanism_stack.get("unresolved_boundaries") or ()
            ),
        }


class XingmingProvider(_AdapterSeam, _SourceRouteMixin):
    """Ephemeris-backed Qizheng Siyu and Xingming calculation provider."""

    provider_id = "mingli-master.xingming.v1"
    SOURCE_ROUTE = {
        "plan_system": "xingming",
        "subsystem": None,
        "registry_route": "xingming",
        "packs": [
            "xingming/guotian-jing",
            "xingming/xingming-suyuan",
            "xingming/xingxue-dacheng",
        ],
        "layers": [
            "ephemeris",
            "positions",
            "houses",
            "ming_shen",
            "transformations",
            "limits",
            "source_conditioned_patterns",
            "source_comparison",
        ],
        "chart": {
            "label": "星盘",
            "required_fields": [
                "ephemeris",
                "positions",
                "houses",
                "ming_shen",
                "transformations",
                "major_limits",
                "source_conditioned_patterns",
            ],
        },
    }
    provider_version = xingming.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        required = ("birth_datetime", "timezone", "location")
        missing = [field for field in required if not _birth_value(request, field)]
        birth = request.birth_data if isinstance(request.birth_data, dict) else {}
        if birth.get("longitude") is None or birth.get("latitude") is None:
            missing.append("longitude_latitude")
        if not birth.get("coordinate_source"):
            missing.append("coordinate_source")
        return tuple(missing)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        validation = xingming.validate_fact_layer(facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Xingming fact validation failed: "
                + ", ".join(validation["codes"])
            )
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("Xingming requires shared calendar facts")
        output = facts["output"]
        diagnostics = (
            "pinned_ephemeris_positions_validated",
            "eleven_classical_points_complete",
            "twelve_houses_and_mingshen_complete",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "chart_reused_without_recalculation",
                "caller_owned_evidence_planning",
            )
        return CalculationResult.create(
            system="xingming",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": _chart_digest(facts),
                "natal_fact_digest": facts["natal_fact_digest"],
                "calendar_digest": calendar_digest,
                "ephemeris_digest": output["ephemeris"]["ephemeris_digest"],
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        birth = request.birth_data
        civil_datetime = birth.get("birth_datetime") or birth.get("datetime")
        timezone_name = str(birth.get("timezone") or request.timezone or "")
        location = str(birth.get("location") or request.location or "")
        if not civil_datetime or not timezone_name or not location:
            raise ValueError(
                "Xingming calculation requires birth datetime, timezone, and location"
            )
        facts = xingming.build_from_birth(
            str(civil_datetime),
            timezone_name=timezone_name,
            location=location,
            longitude=birth.get("longitude"),
            latitude=birth.get("latitude"),
            coordinate_source=birth.get("coordinate_source"),
            coordinate_accuracy_meters=birth.get("coordinate_accuracy_meters"),
            zi_hour_policy=str(birth.get("zi_hour_policy") or "midnight"),
            time_basis_policy=str(birth.get("time_basis_policy") or "civil"),
            house_profile=str(
                request.metadata.get("xingming_house_profile")
                or xingming.HOUSE_PROFILE
            ),
            pseudo_point_profile=str(
                request.metadata.get("xingming_pseudo_point_profile")
                or xingming.PSEUDO_POINT_PROFILE
            ),
        )
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "birth_datetime": str(civil_datetime),
                "timezone": timezone_name,
                "location": location,
                "longitude": birth.get("longitude"),
                "latitude": birth.get("latitude"),
                "coordinate_source": birth.get("coordinate_source"),
                "coordinate_accuracy_meters": birth.get(
                    "coordinate_accuracy_meters"
                ),
                "calendar_digest": facts["calendar_normalization"]["calendar_digest"],
                "natal_fact_digest": facts["natal_fact_digest"],
            },
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "xingming":
            raise ValueError("Xingming refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            request,
            facts,
            input_payload={
                "question": request.query,
                "chart_digest": previous.facts["chart_digest"],
                "refined_from": previous.result_hash,
            },
            refined_from=previous.result_hash,
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "xingming":
            raise ValueError("Xingming extension system mismatch")
        try:
            facts = xingming.build_horizon_fact_extension(
                base.facts["chart_facts"],
                horizon=horizon,
            )
        except (KeyError, TypeError, ValueError):
            return _unsupported_extension(base, requested_dimensions, horizon)
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts=facts,
            rule_traces=tuple(facts.get("rule_trace") or ()),
        )


class FengshuiProvider(_AdapterSeam, _SourceRouteMixin):
    provider_id = "mingli-master.fengshui.v1"
    intake_spec_field = "fengshui_spec"
    intake_spec_merge = "deep"
    atomic_child_merge_fields = ("fengshui_spec",)

    def merge_intake_spec(
        self,
        original_spec: Mapping[str, Any],
        supplied_spec: Mapping[str, Any],
        missing_facts: set[str],
        original_action: str | None,
    ) -> dict[str, Any] | None:
        del original_spec, original_action
        filtered = fengshui.filtered_intake_spec(supplied_spec, missing_facts)
        return filtered or None
    SOURCE_ROUTE = {
        "plan_system": "fengshui",
        "subsystem": None,
        "registry_route": "fengshui",
        "packs": [],
        "layers": [],
        "chart": {
            "label": "宅局事实",
            "required_fields": [
                "active_subprofiles",
                "observation_provenance",
                "compass",
                "building_chronology",
                "layout_graph",
                "form",
                "liqi",
                "active_source_rule_ids",
                "conflicts",
                "uncertainties",
                "critical_missing",
            ],
        },
        "pack_policy": "subset",
        "pack_scope_error": (
            "goal.source_packs exceeds the active Fengshui subprofile/source scope"
        ),
        "comparison_allowed": False,
        "comparison_error": (
            "Fengshui comparison packs require a separately calculated school profile"
        ),
    }

    def source_route(
        self,
        goal: Mapping[str, Any],
        facts: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        route = super().source_route(goal, facts)
        chart_facts = (
            (facts or {}).get("chart_facts")
            if isinstance((facts or {}).get("chart_facts"), Mapping)
            else facts or {}
        )
        output = (
            chart_facts.get("output")
            if isinstance(chart_facts, Mapping)
            and isinstance(chart_facts.get("output"), Mapping)
            else {}
        )
        active_subprofiles = list(output.get("active_subprofiles") or ())
        packs: list[str] = []
        layers: list[str] = []
        if not output:
            # Planning-only callers still need a conservative, real source
            # entry. Exact evidence remains inactive until provider facts and
            # pack-qualified active rule ids exist.
            packs.extend(
                (
                    "fengshui/huangdi-zhaijing",
                    "fengshui/yangzhai-shishu",
                )
            )
            layers.append("observation_intake_prerequisites")
        if "form" in active_subprofiles:
            form = (
                output.get("form")
                if isinstance(output.get("form"), Mapping)
                else {}
            )
            observations = (
                form.get("observations")
                if isinstance(form.get("observations"), list)
                else []
            )
            form_rule_ids = [
                rule_id
                for observation in observations
                if isinstance(observation, Mapping)
                for rule_id in observation.get("source_rule_ids") or ()
                if isinstance(rule_id, str) and rule_id.startswith("fengshui/")
            ]
            packs.extend(
                rule_id.split("#", 1)[0]
                for rule_id in form_rule_ids
                if "#" in rule_id
            )
            layers.extend(("observation_provenance", "form", "layout_graph"))
        liqi = (
            output.get("liqi")
            if isinstance(output.get("liqi"), Mapping)
            else {}
        )
        if "liqi" in active_subprofiles:
            if liqi.get("selected_school") != "bazhai":
                raise ValueError(
                    "Fengshui source planning supports only selected Bazhai facts"
                )
            layers.extend(("compass", "building_chronology", "liqi.bazhai"))
        active_rule_ids = output.get("active_source_rule_ids")
        if isinstance(active_rule_ids, list):
            packs.extend(
                rule_id.split("#", 1)[0]
                for rule_id in active_rule_ids
                if isinstance(rule_id, str)
                and rule_id.startswith("fengshui/")
                and "#" in rule_id
            )
        route["packs"] = list(dict.fromkeys(packs))
        route["layers"] = list(dict.fromkeys(layers))
        return route
    provider_version = fengshui.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        spec = chart.get("fengshui_spec")
        if not isinstance(spec, dict):
            return ("fengshui_spec",)
        subprofiles = spec.get("subprofiles")
        if not isinstance(subprofiles, list) or not subprofiles:
            return ("subprofiles",)
        if "form" in subprofiles:
            requested = spec.get("requested_form_variables")
            if not isinstance(requested, list) or not requested:
                return ("requested_form_variables",)
        for field, expected_type in (
            ("liqi", dict),
            ("compass_measurements", list),
            ("assets", list),
            ("observations", list),
            ("layout_graph", dict),
        ):
            if not isinstance(spec.get(field), expected_type):
                return (field,)
        return fengshui.required_intake_facts(spec)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def _compile(
        self,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        diagnostics: tuple[str, ...],
    ) -> CalculationResult:
        report = fengshui.validate_fact_layer(facts)
        if not report["ok"]:
            raise RuntimeError(
                "Fengshui fact validation failed: " + ", ".join(report["codes"])
            )
        adapter_report = adapter_validate.validate_payload("fengshui", facts)
        if not adapter_report["ok"]:
            raise RuntimeError(
                "Fengshui adapter validation failed: "
                + ", ".join(adapter_report["codes"])
            )
        digest = str(facts["fact_digest"])
        return CalculationResult.create(
            system="fengshui",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=input_payload,
            facts={
                "chart_digest": digest,
                "fact_digest": digest,
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        spec = request.chart_data.get("fengshui_spec")
        if not isinstance(spec, Mapping):
            raise ValueError("Fengshui calculation requires chart_data.fengshui_spec")
        facts = fengshui.build_fact_layer(spec)
        return self._compile(
            facts,
            input_payload=_bind_request_semantics(
                {
                    "fengshui_spec": facts["input"]["fengshui_spec"],
                    "input_digest": facts["input"]["input_digest"],
                    "source_table_sha256": fengshui.SOURCE_TABLE_SHA256,
                    "rule_profile": fengshui.TABLE_PROFILE,
                },
                request,
            ),
            diagnostics=(
                "observation_driven_fengshui_facts_validated",
                "selected_school_only",
                "caller_owned_evidence_planning",
            ),
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "fengshui":
            raise ValueError("Fengshui refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            facts,
            input_payload=_bind_request_semantics(
                {
                    "fact_digest": previous.facts["fact_digest"],
                    "intent_digest": canonical_digest(request.intent),
                    "refined_from": previous.result_hash,
                },
                request,
            ),
            diagnostics=(
                "fengshui_observations_reused_without_invention",
                "caller_owned_evidence_planning",
            ),
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "fengshui":
            raise ValueError("Fengshui extension system mismatch")
        supported_dimensions = set(self.capability.dimensions)
        unsupported = tuple(
            dimension
            for dimension in requested_dimensions
            if dimension not in supported_dimensions
        )
        if (
            str(horizon.get("kind") or "") != "instant"
            or horizon.get("start") is not None
            or horizon.get("end") is not None
            or unsupported
        ):
            return _unsupported_extension(base, requested_dimensions, horizon)
        output = base.facts["chart_facts"]["output"]
        incomplete = _fengshui_incomplete_dimensions(output)
        incomplete_dimensions = tuple(
            dimension
            for dimension in requested_dimensions
            if dimension in incomplete
        )
        if incomplete_dimensions == requested_dimensions:
            return _unsupported_extension(
                base,
                requested_dimensions,
                horizon,
            )
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="partial" if incomplete_dimensions else "complete",
            facts={
                "status": "observed_spatial_scope_not_outcome_verdict",
                "requested_dimensions": list(requested_dimensions),
                "fact_digest": base.facts["fact_digest"],
                "compass": copy.deepcopy(output["compass"]),
                "form": copy.deepcopy(output["form"]),
                "liqi": copy.deepcopy(output["liqi"]),
                "conflicts": copy.deepcopy(output["conflicts"]),
                "uncertainties": copy.deepcopy(output["uncertainties"]),
                "critical_missing": copy.deepcopy(output["critical_missing"]),
            },
            unsupported_dimensions=incomplete_dimensions,
        )


class PhysiognomyProvider(_AdapterSeam, _SourceRouteMixin):
    """Normalize caller-transcribed visible observations without doing vision."""

    provider_id = "mingli-master.physiognomy.v1"
    SOURCE_PRIORITY = (
        "physiognomy/liuzhuang-xiangfa",
        "physiognomy/shenxiang-quanbian",
        "physiognomy/mayi-shenxiang",
    )
    SOURCE_ROUTE = {
        "plan_system": "physiognomy",
        "subsystem": None,
        "registry_route": "physiognomy",
        "packs": [],
        "layers": [],
        "chart": {
            "label": "可见观察事实",
            "required_fields": [
                "observation_scope",
                "normalized_visible_observations",
                "missing_targets",
                "observation_conflicts",
                "cross_capture_variations",
                "source_layers",
                "source_disagreements",
                "active_source_rule_ids",
                "source_conditioned_patterns",
                "uncertainties",
                "critical_missing",
            ],
        },
        "pack_policy": "locked",
        "comparison_allowed": False,
        "comparison_error": (
            "Physiognomy comparison packs require separately active, safe source rules"
        ),
        "allowed_evidence_roles": [
            "edition_boundary",
            "methodology_rule",
            "terminology_only",
        ],
        "semantic_term_projections": [
            {
                "path_contains": "/source_comparison/",
                "leaves": ["title", "summary"],
                "requires_dimension": "source_comparison",
                "requires_questions": True,
            }
        ],
    }

    def source_route(
        self,
        goal: Mapping[str, Any],
        facts: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        route = super().source_route(goal, facts)
        chart_facts = (
            (facts or {}).get("chart_facts")
            if isinstance((facts or {}).get("chart_facts"), Mapping)
            else facts or {}
        )
        output = (
            chart_facts.get("output")
            if isinstance(chart_facts, Mapping)
            and isinstance(chart_facts.get("output"), Mapping)
            else {}
        )
        active_rule_ids = output.get("active_source_rule_ids")
        if not isinstance(active_rule_ids, list):
            active_rule_ids = []
        if any(
            not isinstance(rule_id, str)
            or not rule_id.startswith("physiognomy/")
            or "#" not in rule_id
            for rule_id in active_rule_ids
        ):
            raise ValueError(
                "Physiognomy active source rule ids must be pack-qualified"
            )
        active_packs = {
            rule_id.split("#", 1)[0]
            for rule_id in active_rule_ids
        }
        packs = [
            pack
            for pack in self.SOURCE_PRIORITY
            if pack in active_packs
        ]
        if set(packs) != active_packs:
            raise ValueError(
                "Physiognomy active packs must follow declared source-layer priority"
            )
        route["packs"] = packs
        route["layers"] = [
            "normalized_visible_observations",
            "capture_quality_and_uncertainty",
            "historical_terminology",
            "source_layers_and_disagreements",
            "source_conditioned_patterns",
        ] if active_rule_ids else ["observation_intake_prerequisites"]
        return route
    provider_version = physiognomy.ADAPTER_VERSION
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        chart = request.chart_data if isinstance(request.chart_data, dict) else {}
        spec = chart.get("physiognomy_spec")
        if not isinstance(spec, dict):
            return ("physiognomy_spec",)
        return physiognomy.required_intake_facts(spec)

    recast_replaces_chart_data = True
    recast_resets_media = True
    extension_is_private = True
    intake_spec_field = "physiognomy_spec"
    intake_spec_merge = "replace"
    intake_spec_accepts_image = True

    def merge_intake_spec(
        self,
        original_spec: Mapping[str, Any],
        supplied_spec: Mapping[str, Any],
        missing_facts: set[str],
        original_action: str | None,
    ) -> dict[str, Any] | None:
        if original_action == "correct":
            return physiognomy.merge_correction_resume_spec(
                original_spec,
                supplied_spec,
                missing_facts,
            )
        return physiognomy.merge_resume_spec(
            original_spec,
            supplied_spec,
            missing_facts,
        )

    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    # ---- provider-owned lifecycle and privacy rules -------------------

    def public_basis_projection(
        self, chart_facts: Mapping[str, Any]
    ) -> dict[str, Any]:
        return physiognomy.public_projection(chart_facts)

    def enrich_request(
        self,
        request: ReadingRequest,
        context: RuntimeContext | None,
        *,
        routed: bool = True,
    ) -> ReadingRequest:
        """Normalize the routed envelope to the observation contract.

        The generic seam goal profile does not apply here, and a spec
        that carries assets or image transcriptions is by definition a
        caller-side vision transcription, so the envelope flag is a
        deterministic function of the spec itself.
        """

        changes: dict[str, Any] = {}
        goal = request.goal
        allowed_goal_fields = {
            "source_packs",
            "comparison_packs",
            "evidence_questions",
            "counter_evidence_questions",
            "question_dimensions",
            "requested_dimensions",
            "requested_resolution",
            "calculation_object",
        }
        if not isinstance(goal, Mapping) or set(goal) - allowed_goal_fields:
            changes["goal"] = {}
        spec = request.chart_data.get("physiognomy_spec")
        if not request.image_supplied and isinstance(spec, Mapping):
            observations = spec.get("observations") or []
            has_image = bool(spec.get("assets")) or (
                isinstance(observations, list)
                and any(
                    isinstance(item, Mapping)
                    and item.get("source_type") == "image_transcription"
                    for item in observations
                )
            )
            if has_image:
                changes["image_supplied"] = True
        return _with_request_changes(request, changes)

    def validate_new_request(self, request: ReadingRequest) -> None:
        physiognomy.validate_request_envelope(request)
        spec = request.chart_data.get("physiognomy_spec")
        if isinstance(spec, Mapping):
            frame = IntentFrame.from_dict(request.intent)
            if tuple(frame.subject_refs) != (
                str(spec.get("subject_ref") or ""),
            ):
                raise ValueError(
                    "Physiognomy request subject binding mismatch"
                )

    def validate_incoming_recast(self, request: ReadingRequest) -> None:
        physiognomy.validate_request_envelope(request)

    def validate_outgoing_recast(self, request: ReadingRequest) -> None:
        physiognomy.validate_no_raw_media(request)
        if "physiognomy_spec" in request.chart_data:
            raise ValueError(
                "cross-system recast may not retain Physiognomy chart data"
            )

    def validate_bound_action(
        self,
        request: ReadingRequest,
        prior_request: ReadingRequest,
    ) -> None:
        physiognomy.validate_request_envelope(request)
        original_spec = prior_request.chart_data.get("physiognomy_spec")
        frame = IntentFrame.from_dict(request.intent)
        subject_ref = (
            str(original_spec.get("subject_ref") or "")
            if isinstance(original_spec, Mapping)
            else ""
        )
        if tuple(frame.subject_refs) != (subject_ref,):
            raise ProviderActionError(
                "action_requires_recast",
                "A Physiognomy continuation or correction must keep the "
                "single bound subject; use recast for a subject change.",
            )
        if request.action == "continue" and (
            bool(request.chart_data)
            or request.image_supplied
            or bool(str(request.transcribed_chart or "").strip())
        ):
            raise ProviderActionError(
                "action_requires_correct_or_recast",
                "A Physiognomy continuation cannot silently accept a new "
                "capture or observation; use correct for same-capture "
                "supersession or recast for a new capture.",
            )

    def merge_correction_chart_data(
        self,
        prior_request: ReadingRequest,
        request: ReadingRequest,
    ) -> dict[str, Any]:
        original_spec = prior_request.chart_data.get("physiognomy_spec")
        supplied_spec = request.chart_data.get("physiognomy_spec")
        if not isinstance(original_spec, Mapping) or not isinstance(
            supplied_spec, Mapping
        ):
            raise ProviderActionError(
                "action_requires_correct",
                "Physiognomy correction requires explicit same-capture "
                "user_correction observations.",
            )
        try:
            merged_spec = physiognomy.merge_correction_spec(
                original_spec,
                supplied_spec,
            )
        except physiognomy.RecastRequired as exc:
            raise ProviderActionError(
                "action_requires_recast", str(exc)
            ) from exc
        return {"physiognomy_spec": merged_spec}

    def public_missing_facts(
        self,
        request: ReadingRequest,
        missing_facts: tuple[str, ...],
    ) -> tuple[str, ...]:
        spec = request.chart_data.get("physiognomy_spec")
        if isinstance(spec, Mapping):
            return physiognomy.public_missing_facts(spec, missing_facts)
        return missing_facts

    def project_known_chart_data(
        self, chart_data: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        spec = chart_data.get("physiognomy_spec")
        if isinstance(spec, Mapping):
            return {
                "physiognomy_spec": physiognomy.intake_public_projection(spec)
            }
        return None

    def validate_published_question(
        self,
        prior_request: ReadingRequest,
        question: str,
    ) -> None:
        spec = prior_request.chart_data.get("physiognomy_spec")
        private_payload: Mapping[str, Any] = {
            "subject_ref": (
                prior_request.intent.get("subject_refs") or [""]
            )[0]
        }
        if isinstance(spec, Mapping):
            private_payload = physiognomy.build_fact_layer(spec)
        if physiognomy.public_copy_contains_private_provenance(
            private_payload,
            question,
        ):
            raise ValueError(
                "published intake question contains private or protocol text"
            )

    def validate_intake_supplement(self, supplement: ReadingRequest) -> None:
        physiognomy.validate_request_envelope(
            supplement,
            require_image_presence=False,
        )

    def validate_intake_merged(self, merged: ReadingRequest) -> None:
        physiognomy.validate_request_envelope(merged)

    def public_copy_privacy_violation(
        self,
        calculation: CalculationResult,
        public_copy: str,
    ) -> bool:
        chart_facts = calculation.facts.get("chart_facts")
        if not isinstance(chart_facts, Mapping):
            raise ValueError(
                "Physiognomy calculation is missing its fact layer"
            )
        return physiognomy.public_copy_contains_private_provenance(
            chart_facts,
            public_copy,
        )

    def _compile(
        self,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        diagnostics: tuple[str, ...],
    ) -> CalculationResult:
        report = physiognomy.validate_fact_layer(facts)
        if not report["ok"]:
            raise RuntimeError(
                "Physiognomy fact validation failed: "
                + ", ".join(report["codes"])
            )
        adapter_report = adapter_validate.validate_payload("physiognomy", facts)
        if not adapter_report["ok"]:
            raise RuntimeError(
                "Physiognomy adapter validation failed: "
                + ", ".join(adapter_report["codes"])
            )
        digest = str(facts["fact_digest"])
        return CalculationResult.create(
            system="physiognomy",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=input_payload,
            facts={
                "chart_digest": digest,
                "fact_digest": digest,
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        physiognomy.validate_request_envelope(request)
        if set(request.chart_data) != {"physiognomy_spec"}:
            raise ValueError(
                "Physiognomy calculation requires exact chart_data.physiognomy_spec"
            )
        spec = request.chart_data.get("physiognomy_spec")
        if not isinstance(spec, Mapping):
            raise ValueError(
                "Physiognomy calculation requires chart_data.physiognomy_spec"
            )
        frame = IntentFrame.from_dict(request.intent)
        subject_ref = str(spec.get("subject_ref") or "").strip()
        if tuple(frame.subject_refs) != (subject_ref,):
            raise ValueError("Physiognomy request subject binding mismatch")
        facts = physiognomy.build_fact_layer(spec)
        return self._compile(
            facts,
            input_payload=_bind_request_semantics(
                {
                    "physiognomy_spec": facts["input"]["physiognomy_spec"],
                    "input_digest": facts["input"]["input_digest"],
                    "source_table_sha256": physiognomy.SOURCE_TABLE_SHA256,
                    "rule_profile": physiognomy.TABLE_PROFILE,
                },
                request,
            ),
            diagnostics=(
                "observation_driven_physiognomy_facts_validated",
                "provider_did_not_perform_vision",
                "historical_terminology_not_subject_verdict",
                "caller_owned_evidence_planning",
            ),
        )

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "physiognomy":
            raise ValueError("Physiognomy refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(
            facts,
            input_payload=_bind_request_semantics(
                {
                    "fact_digest": previous.facts["fact_digest"],
                    "intent_digest": canonical_digest(request.intent),
                    "refined_from": previous.result_hash,
                },
                request,
            ),
            diagnostics=(
                "physiognomy_observations_reused_without_invention",
                "provider_did_not_perform_vision",
                "caller_owned_evidence_planning",
            ),
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "physiognomy":
            raise ValueError("Physiognomy extension system mismatch")
        supported = set(self.capability.dimensions)
        unsupported = tuple(
            item for item in requested_dimensions if item not in supported
        )
        if (
            str(horizon.get("kind") or "") != "instant"
            or horizon.get("start") is not None
            or horizon.get("end") is not None
            or unsupported
        ):
            return _unsupported_extension(base, requested_dimensions, horizon)
        chart = base.facts["chart_facts"]
        critical_missing = tuple(chart["output"]["critical_missing"])
        incomplete_dimensions = tuple(
            dimension
            for dimension in requested_dimensions
            if critical_missing and dimension == "state"
        )
        if incomplete_dimensions == requested_dimensions:
            return _unsupported_extension(
                base,
                requested_dimensions,
                horizon,
            )
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="partial" if incomplete_dimensions else "complete",
            facts={
                **physiognomy.public_projection(chart),
                "critical_missing": list(critical_missing),
                "fact_digest": base.facts["fact_digest"],
            },
            unsupported_dimensions=incomplete_dimensions,
        )


class StructuredChartProvider:
    provider_version = "2.0.0"

    def __init__(self, skill_dir: str | Path, system: str) -> None:
        if system not in STRUCTURED_SYSTEMS:
            raise ValueError(f"unsupported structured route: {system}")
        self.skill_dir = Path(skill_dir).resolve()
        self.system = system
        self.canonical = system
        self.provider_id = f"mingli-master.{system}.structured-v2"
        self.capability = PROVIDER_CAPABILITIES[system]

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return normalize_structured_chart(self.system, raw)

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        refined_from: str | None = None,
    ) -> CalculationResult:
        case_payload = {
            "system": self.system,
            "chart_digest": canonical_digest(facts),
            "refined_from": refined_from,
        }
        diagnostics = (
            "validated_user_provided_chart",
            "no_recalculation_claim",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "chart_reused_without_recast",
                "caller_owned_evidence_planning",
            )
        return CalculationResult.create(
            system=self.system,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=case_payload,
            facts={
                "chart_digest": canonical_digest(facts),
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        return self._compile(request, self._normalize(request.chart_data))

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != self.system:
            raise ValueError("structured chart refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        return self._compile(request, facts, refined_from=previous.result_hash)

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        if calculation.system != self.system:
            raise ValueError("structured chart extension system mismatch")
        return _unsupported_extension(
            calculation, requested_dimensions, horizon
        )


def _ziwei_chart_digest(facts: dict[str, Any]) -> str:
    return canonical_digest(
        {
            "system": facts["system"],
            "calendar_normalization": facts["calendar_normalization"],
            "output": facts["output"],
            "rule_profile": facts["adapter"]["rule_profile"],
            "dependency": facts["adapter"]["dependency"],
        }
    )


class ZiweiProvider(_AdapterSeam, _SourceRouteMixin):
    provider_id = "mingli-master.ziwei.iztro"
    SOURCE_ROUTE = {
        "plan_system": "ziwei",
        "subsystem": None,
        "registry_route": "ziwei",
        "packs": ["ziwei/ziwei-doushu-quanshu", "ziwei/taiwei-fu"],
        "layers": [
            "palaces",
            "stars",
            "sihua",
            "limits",
            "source_conditioned_patterns",
        ],
        "chart": {
            "label": "命盘",
            "required_fields": [
                "ming_shen",
                "palaces",
                "stars",
                "sihua",
                "major_limits",
                "source_conditioned_patterns",
            ],
        },
    }
    provider_version = (
        f"{ziwei_fact_adapter.ADAPTER_VERSION}+iztro-{ziwei_fact_adapter.IZTRO_VERSION}"
    )
    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        required = ("birth_datetime", "timezone", "location", "gender")
        missing = [field for field in required if not _birth_value(request, field)]
        return tuple(missing)


    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def _compile(
        self,
        request: ReadingRequest,
        facts: dict[str, Any],
        *,
        input_payload: dict[str, Any],
        refined_from: str | None = None,
    ) -> CalculationResult:
        diagnostics = (
            "vendored_iztro_chart_validated",
            "twelve_palaces_complete",
            "caller_owned_evidence_planning",
        )
        if refined_from:
            diagnostics = (
                "chart_reused_without_recast",
                "caller_owned_evidence_planning",
            )
        calendar_digest = _bound_calendar_digest(facts)
        if calendar_digest is None:
            raise RuntimeError("Ziwei requires shared calendar facts")
        return CalculationResult.create(
            system="ziwei",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload=_bind_request_semantics(input_payload, request),
            facts={
                "chart_digest": _ziwei_chart_digest(facts),
                "natal_fact_digest": ziwei_fact_adapter.natal_fact_digest(facts),
                "calendar_digest": calendar_digest,
                "chart_facts": facts,
            },
            diagnostics=diagnostics,
        )

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        birth = request.birth_data
        birth_datetime = str(_birth_value(request, "birth_datetime"))
        engine_request = ziwei_fact_adapter.ZiweiNormalizedEngineRequest(
            civil_datetime=birth_datetime,
            timezone_name=str(birth.get("timezone") or request.timezone),
            location=str(birth.get("location") or request.location),
            gender=str(birth["gender"]),
            longitude=birth.get("longitude"),
            latitude=birth.get("latitude"),
            coordinate_source=birth.get("coordinate_source"),
            coordinate_accuracy_meters=birth.get("coordinate_accuracy_meters"),
            zi_hour_policy=str(birth.get("zi_hour_policy") or "midnight"),
            time_basis_policy=str(birth.get("time_basis_policy") or "civil"),
        )
        engine_result = ziwei_fact_adapter.ZiweiEngineAdapter().adapt(
            engine_request
        )
        facts = engine_result.canonical_facts.to_payload()
        facts["adapter"]["generated_at"] = "deterministic-chart-identity"
        facts = (
            ziwei_fact_adapter.ZiweiEngineAdapter()
            .bind_canonical_facts(engine_request, facts)
            .canonical_facts.to_payload()
        )
        validation = adapter_validate.validate_payload("ziwei", facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Ziwei fact validation failed: " + ", ".join(validation["codes"])
            )
        input_payload = {
            "question": request.query,
            "birth_datetime": birth_datetime,
            "timezone": birth.get("timezone") or request.timezone,
            "location": birth.get("location") or request.location,
            "gender": birth["gender"],
            "longitude": birth.get("longitude"),
            "latitude": birth.get("latitude"),
            "coordinate_source": birth.get("coordinate_source"),
            "coordinate_accuracy_meters": birth.get("coordinate_accuracy_meters"),
            "zi_hour_policy": birth.get("zi_hour_policy") or "midnight",
            "time_basis_policy": birth.get("time_basis_policy") or "civil",
        }
        return self._compile(request, facts, input_payload=input_payload)

    def refine(
        self,
        request: ReadingRequest,
        previous: CalculationResult,
    ) -> CalculationResult:
        if previous.system != "ziwei":
            raise ValueError("Ziwei refinement system mismatch")
        facts = copy.deepcopy(previous.facts["chart_facts"])
        input_payload = {
            "question": request.query,
            "chart_digest": previous.facts["chart_digest"],
            "refined_from": previous.result_hash,
        }
        return self._compile(
            request,
            facts,
            input_payload=input_payload,
            refined_from=previous.result_hash,
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "ziwei":
            raise ValueError("Ziwei extension system mismatch")
        kind = str(horizon.get("kind") or "")
        if kind in {"instant", "natal", "life"} and not (
            horizon.get("start") or horizon.get("end")
        ):
            return _attach_extension(
                base,
                requested_dimensions,
                horizon,
                status="complete",
                facts={
                    "dimension_fact_scope": {
                        dimension: {
                            "scope": "calculated_natal_ziwei_chart",
                            "base_calculation_digest": base.result_hash,
                        }
                        for dimension in requested_dimensions
                    }
                },
            )
        try:
            facts = ziwei_fact_adapter.build_horizon_fact_extensions(
                base.facts.get("chart_facts") or {},
                horizon=horizon,
            )
        except (KeyError, TypeError, ValueError):
            return _unsupported_extension(base, requested_dimensions, horizon)
        validation = adapter_validate.validate_ziwei_extension(facts)
        if not validation["ok"]:
            raise RuntimeError(
                "Ziwei temporal fact validation failed: "
                + ", ".join(validation["codes"])
            )
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts=facts,
            rule_traces=tuple(facts.get("rule_trace") or ()),
        )



class TimeCheckProvider(_AdapterSeam, _SourceRouteMixin):
    """Enumerate twelve Bazi hour candidates and apply classical 校时.

    Plain-text event labels remain facts-only input.  Structured event dates
    still produce bounded year-pillar evidence ranking.  Classical
    rectification then eliminates candidates by known-range intersection and,
    when two or more dated events exist, by hour-pillar / 命宫 / 小运 branch
    polarity against those events.  The 定盘 conclusion is a remaining-hour
    adjudication, not a life-event or 用神 verdict.
    """

    provider_id = "mingli-master.time-check.v1"
    provider_version = "time-check-classical-rectification-v1"
    HOUR_BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
    # The civil-day projection follows the release's selection time table:
    # Zi crosses midnight, while the remaining branches occupy consecutive
    # two-hour half-open intervals.  Keep the source table's interval shape
    # here because the time-check range is a branch eligibility constraint,
    # not a test against one arbitrary representative minute.
    HOUR_BRANCH_SEGMENTS = {
        "子": ((0, 60), (23 * 60, 24 * 60)),
        "丑": ((60, 180),),
        "寅": ((180, 300),),
        "卯": ((300, 420),),
        "辰": ((420, 540),),
        "巳": ((540, 660),),
        "午": ((660, 780),),
        "未": ((780, 900),),
        "申": ((900, 1020),),
        "酉": ((1020, 1140),),
        "戌": ((1140, 1260),),
        "亥": ((1260, 1380),),
    }
    EVENT_DOMAIN_ROLES = {
        "career": frozenset(("正官", "七杀", "正印", "偏印", "食神", "伤官")),
        "education": frozenset(("正印", "偏印", "食神", "伤官")),
        "finance": frozenset(("正财", "偏财")),
        "relationship": frozenset(("正官", "七杀", "正财", "偏财")),
        "family": frozenset(("正印", "偏印", "正财", "偏财", "比肩", "劫财")),
        "location": frozenset(),
        "health": frozenset(),
    }
    POSITIVE_BRANCH_RELATIONS = frozenset(("六合", "三合", "三会"))
    NEGATIVE_BRANCH_RELATIONS = frozenset(("六冲", "六害", "六破", "三刑"))
    HOUR_POSITIVE_RELATIONS = frozenset(("六合", "三合", "三会", "同支"))
    RECTIFICATION_RULE_IDS = (
        "bazi/sanming-tonghui#R-02-06",
        "bazi/sanming-tonghui#R-02-07",
        "bazi/sanming-tonghui#R-02-10",
        "bazi/sanming-tonghui#R-02-14",
        "bazi/sanming-tonghui#R-02-17",
        "bazi/sanming-tonghui#R-02-18",
    )
    SOURCE_ROUTE = copy.deepcopy(BaziProvider.SOURCE_ROUTE)
    SOURCE_ROUTE.update(
        {
            "plan_system": "time-check",
            "registry_route": "time-check",
            "compatible_rule_systems": ["bazi"],
        }
    )
    # Bazi exposes this hook as a static function.  Keep the reuse static as
    # well; assigning the bare function would bind ``self`` on this class and
    # make source-plan compilation fail before the calculation is published.
    extend_source_plan = staticmethod(BaziProvider.extend_source_plan)

    @staticmethod
    def missing_required_inputs(
        request: ReadingRequest,
    ) -> tuple[str, ...]:
        birth = request.birth_data if isinstance(request.birth_data, dict) else {}
        required = (
            "time_check_date",
            "time_range_start",
            "time_range_end",
            "timezone",
            "location",
            "gender",
        )
        return tuple(
            field
            for field in required
            if not str(birth.get(field) or getattr(request, field, "")).strip()
        )

    @staticmethod
    def _parse_clock(value: object, *, field: str) -> tuple[int, int]:
        text = str(value or "").strip()
        match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", text)
        if match is None:
            raise RuntimeError(f"time-check {field} must use HH:MM")
        return int(match.group(1)), int(match.group(2))

    @classmethod
    def _candidate_datetimes(
        cls,
        *,
        date_value: object,
        timezone_name: str,
        range_start: object,
        range_end: object,
    ) -> tuple[tuple[str, datetime, bool], ...]:
        try:
            local_date = date.fromisoformat(str(date_value))
            timezone = ZoneInfo(timezone_name)
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            raise RuntimeError("time-check date or timezone is invalid") from None
        start_hour, start_minute = cls._parse_clock(
            range_start,
            field="time_range_start",
        )
        end_hour, end_minute = cls._parse_clock(
            range_end,
            field="time_range_end",
        )
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute

        if start_minutes <= end_minutes:
            time_window_segments = ((start_minutes, min(end_minutes + 1, 24 * 60)),)
        else:
            time_window_segments = (
                (start_minutes, 24 * 60),
                (0, end_minutes + 1),
            )

        def intersects_window(branch: str) -> bool:
            return any(
                window_start < branch_end and branch_start < window_end
                for branch_start, branch_end in cls.HOUR_BRANCH_SEGMENTS[branch]
                for window_start, window_end in time_window_segments
            )

        candidates: list[tuple[str, datetime, bool]] = []
        # A representative instant at the middle of each traditional
        # two-hour branch keeps the candidate set deterministic and avoids
        # pretending that a free-form range itself selects an hour.
        for index, branch in enumerate(cls.HOUR_BRANCHES):
            # The representative hours are 00:00, 02:00, …, 22:00.  In
            # particular, 00:00 is the civil-date projection of Zi under the
            # release's midnight policy; starting at 01:30 would label an
            # actual Chou hour as Zi.
            minutes = index * 120
            candidate = datetime(
                local_date.year,
                local_date.month,
                local_date.day,
                minutes // 60,
                minutes % 60,
                tzinfo=timezone,
            )
            candidates.append((branch, candidate, intersects_window(branch)))
        return tuple(candidates)

    def __init__(self, skill_dir: str | Path) -> None:
        self.skill_dir = Path(skill_dir).resolve()

    def public_basis_projection(
        self,
        chart_facts: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        output = chart_facts.get("output")
        return output if isinstance(output, Mapping) else {}

    @staticmethod
    def _event_datetime(
        value: object,
        *,
        timezone_name: str,
    ) -> datetime:
        text = str(value or "").strip()
        if not text:
            raise ValueError("event occurred_at is required")
        timezone = ZoneInfo(timezone_name)
        if len(text) == 10:
            event_date = date.fromisoformat(text)
            return datetime(
                event_date.year,
                event_date.month,
                event_date.day,
                12,
                0,
                tzinfo=timezone,
            )
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            parsed = parsed.replace(tzinfo=timezone)
        return parsed.astimezone(timezone)

    @classmethod
    def _structured_events(
        cls,
        birth: Mapping[str, Any],
        *,
        timezone_name: str,
        location: str,
    ) -> tuple[tuple[dict[str, Any], ...], str]:
        raw_events = birth.get("known_event_facts")
        if raw_events is None:
            return (), "not_supplied"
        if not isinstance(raw_events, (list, tuple)) or not raw_events:
            return (), "invalid_structured_events"
        events: list[dict[str, Any]] = []
        for raw in raw_events:
            if not isinstance(raw, Mapping):
                return (), "invalid_structured_events"
            event_id = str(raw.get("event_id") or "").strip()
            domain = str(raw.get("domain") or "").strip()
            occurred_at = str(raw.get("occurred_at") or "").strip()
            if (
                not event_id
                or len(event_id) > 80
                or domain not in cls.EVENT_DOMAIN_ROLES
                or not occurred_at
            ):
                return (), "invalid_structured_events"
            try:
                event_datetime = cls._event_datetime(
                    occurred_at,
                    timezone_name=timezone_name,
                )
                normalized = calendar_core.normalize_calendar(
                    event_datetime.isoformat(),
                    timezone_name=timezone_name,
                    location=location,
                    zi_hour_policy="midnight",
                    time_basis_policy="civil",
                )
                year_pillar = str(normalized["ganzhi"]["year"])
            except (TypeError, ValueError, ZoneInfoNotFoundError, KeyError):
                return (), "invalid_structured_events"
            events.append(
                {
                    "event_id": event_id,
                    "domain": domain,
                    "occurred_at": event_datetime.isoformat(),
                    "year_pillar": year_pillar,
                }
            )
        if len({event["event_id"] for event in events}) != len(events):
            return (), "invalid_structured_events"
        return tuple(events), "structured_valid"

    @staticmethod
    def _branch_relation_types(
        natal_branch: str,
        event_branch: str,
    ) -> tuple[str, ...]:
        if natal_branch == event_branch:
            return ("同支",)
        found: list[str] = []
        pair = {natal_branch, event_branch}
        for relation_type, patterns in bazi_fact_adapter.PAIR_RELATIONS.items():
            if any(pair == set(pattern) for pattern in patterns):
                found.append(relation_type)
        return tuple(found)

    @classmethod
    def _event_evidence(
        cls,
        candidate: Mapping[str, Any],
        event: Mapping[str, Any],
    ) -> dict[str, Any]:
        pillars = candidate.get("four_pillars")
        day_master = candidate.get("day_master")
        if not isinstance(pillars, Mapping) or not isinstance(day_master, Mapping):
            return {
                "event_id": str(event["event_id"]),
                "matched": False,
                "evidence_score": 0,
                "relations": [],
                "event_year_ten_god": None,
                "reasons": ["candidate_chart_facts_missing"],
            }
        year_pillar = str(event["year_pillar"])
        event_stem, event_branch = year_pillar[0], year_pillar[1]
        day_stem = str(day_master.get("stem") or "")
        event_year_ten_god = (
            bazi_fact_adapter._ten_god(day_stem, event_stem)
            if day_stem in bazi_fact_adapter.STEMS
            else None
        )
        relations: list[dict[str, Any]] = []
        for position in ("year", "month", "day", "hour"):
            pillar = pillars.get(position)
            if not isinstance(pillar, str) or len(pillar) < 2:
                continue
            relation_types = cls._branch_relation_types(pillar[1], event_branch)
            for relation_type in relation_types:
                relations.append(
                    {
                        "natal_position": position,
                        "natal_branch": pillar[1],
                        "event_branch": event_branch,
                        "relation_type": relation_type,
                    }
                )
        has_positive_relation = any(
            relation["relation_type"] in cls.POSITIVE_BRANCH_RELATIONS
            for relation in relations
        )
        has_negative_relation = any(
            relation["relation_type"] in cls.NEGATIVE_BRANCH_RELATIONS
            for relation in relations
        )
        # Aggregate relation signals by presence, not traversal order.  A
        # candidate can retain both supporting and counter evidence; neither
        # signal is allowed to overwrite the other merely because its branch
        # happened to be visited later.
        relation_score = (2 if has_positive_relation else 0) - (
            2 if has_negative_relation else 0
        )
        domain = str(event["domain"])
        role_score = int(
            event_year_ten_god in cls.EVENT_DOMAIN_ROLES[domain]
        )
        score = relation_score + role_score
        reasons: list[str] = []
        if has_positive_relation:
            reasons.append("positive_branch_relation")
        if has_negative_relation:
            reasons.append("negative_branch_relation")
        if role_score:
            reasons.append("domain_ten_god_role")
        if not reasons:
            reasons.append("no_supporting_or_opposing_signal")
        return {
            "event_id": str(event["event_id"]),
            # A counter relation is evidence against a candidate, not a
            # successful event match.  Domain role evidence may still make a
            # candidate positive when both signals are present.
            "matched": score > 0,
            "evidence_score": score,
            "relations": relations,
            "event_year_ten_god": event_year_ten_god,
            "reasons": reasons,
        }

    @classmethod
    def _xiaoyun_pillar(
        cls,
        hour_pillar: str,
        year_pillar: object,
        gender: str,
        birth_date: str,
        event: Mapping[str, Any],
    ) -> str | None:
        if (
            not gender
            or not birth_date
            or hour_pillar not in bazi_fact_adapter.JIAZI
            or not isinstance(year_pillar, str)
            or not year_pillar
        ):
            return None
        year_stem = year_pillar[0]
        if year_stem not in bazi_fact_adapter.POLARITY:
            return None
        yang_year = bazi_fact_adapter.POLARITY[year_stem] == "阳"
        forward = (gender == "male" and yang_year) or (
            gender == "female" and not yang_year
        )
        occurred_at = event.get("occurred_at")
        if not occurred_at:
            return None
        try:
            born = date.fromisoformat(str(birth_date)[:10])
            occurred = cls._event_datetime(
                occurred_at,
                timezone_name="Asia/Shanghai",
            )
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            return None
        age_years = occurred.year - born.year
        if age_years < 0 or age_years > 120:
            return None
        index = bazi_fact_adapter.JIAZI.index(hour_pillar)
        step = 1 if forward else -1
        return bazi_fact_adapter.JIAZI[(index + step * age_years) % 60]

    @classmethod
    def _hour_event_score(
        cls,
        candidate: Mapping[str, Any],
        event: Mapping[str, Any],
        *,
        gender: str = "",
        birth_date: str = "",
    ) -> tuple[int, tuple[str, ...]]:
        pillars = candidate.get("four_pillars")
        day_master = candidate.get("day_master")
        if not isinstance(pillars, Mapping) or not isinstance(day_master, Mapping):
            return 0, ("candidate_chart_facts_missing",)
        hour_pillar = pillars.get("hour")
        if not isinstance(hour_pillar, str) or len(hour_pillar) < 2:
            return 0, ("hour_pillar_missing",)
        year_pillar = str(event["year_pillar"])
        if len(year_pillar) < 2:
            return 0, ("event_year_pillar_missing",)
        event_branch = year_pillar[1]
        hour_branch = hour_pillar[1]
        reasons: list[str] = []
        score = 0
        hour_relations = cls._branch_relation_types(hour_branch, event_branch)
        if any(item in cls.HOUR_POSITIVE_RELATIONS for item in hour_relations):
            score += 2
            reasons.append("hour_positive_branch_relation")
        if any(item in cls.NEGATIVE_BRANCH_RELATIONS for item in hour_relations):
            score -= 2
            reasons.append("hour_negative_branch_relation")
        day_stem = str(day_master.get("stem") or "")
        if day_stem in bazi_fact_adapter.STEMS:
            hour_god = bazi_fact_adapter._ten_god(day_stem, hour_pillar[0])
            if hour_god in cls.EVENT_DOMAIN_ROLES.get(str(event["domain"]), ()):
                score += 1
                reasons.append("hour_stem_domain_ten_god")
        try:
            ming_gong = bazi_fact_adapter._san_yuan(
                {
                    "year": str(pillars["year"]),
                    "month": str(pillars["month"]),
                    "day": str(pillars["day"]),
                    "hour": hour_pillar,
                }
            )["ming_gong"]
            ming_relations = cls._branch_relation_types(ming_gong[1], event_branch)
            if any(item in cls.HOUR_POSITIVE_RELATIONS for item in ming_relations):
                score += 1
                reasons.append("ming_gong_positive_branch_relation")
            if any(item in cls.NEGATIVE_BRANCH_RELATIONS for item in ming_relations):
                score -= 1
                reasons.append("ming_gong_negative_branch_relation")
        except (KeyError, TypeError, ValueError, IndexError):
            pass
        xiaoyun = cls._xiaoyun_pillar(
            hour_pillar,
            pillars.get("year"),
            gender,
            birth_date,
            event,
        )
        if xiaoyun:
            xiaoyun_relations = cls._branch_relation_types(xiaoyun[1], event_branch)
            if any(item in cls.HOUR_POSITIVE_RELATIONS for item in xiaoyun_relations):
                score += 1
                reasons.append("xiaoyun_positive_branch_relation")
            if any(item in cls.NEGATIVE_BRANCH_RELATIONS for item in xiaoyun_relations):
                score -= 1
                reasons.append("xiaoyun_negative_branch_relation")
        if not reasons:
            reasons.append("no_hour_level_signal")
        return score, tuple(reasons)

    @classmethod
    def _rectification_conclusion(
        cls,
        *,
        remaining_ids: list[str],
        status: str,
        basis: str,
        selected_candidate_id: str | None,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "selected_candidate_id": selected_candidate_id,
            "remaining_candidate_ids": remaining_ids,
            "basis": basis,
            "rule_ids": list(cls.RECTIFICATION_RULE_IDS),
        }

    @classmethod
    def _range_only_conclusion(
        cls,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        remaining_ids = [
            item["candidate_id"]
            for item in candidates
            if item.get("within_known_time_range")
        ]
        if len(remaining_ids) == 1:
            return cls._rectification_conclusion(
                remaining_ids=remaining_ids,
                status="hour_determined",
                basis="known_time_range_unique",
                selected_candidate_id=remaining_ids[0],
            )
        if not remaining_ids:
            return cls._rectification_conclusion(
                remaining_ids=[],
                status="no_valid_candidate",
                basis="known_time_range_empty",
                selected_candidate_id=None,
            )
        return cls._rectification_conclusion(
            remaining_ids=remaining_ids,
            status="not_attempted",
            basis="structured_events_not_supplied",
            selected_candidate_id=None,
        )

    @classmethod
    def _apply_classical_rectification(
        cls,
        candidates: list[dict[str, Any]],
        ranked: list[dict[str, Any]],
        event_matches: list[dict[str, Any]],
        events: tuple[dict[str, Any], ...],
        *,
        gender: str = "",
        birth_date: str = "",
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        if not events:
            return ranked, event_matches, cls._range_only_conclusion(candidates)
        by_id = {item["candidate_id"]: item for item in candidates}
        hour_nets: dict[str, int] = {}
        for row in ranked:
            candidate = by_id[row["candidate_id"]]
            hour_nets[row["candidate_id"]] = sum(
                cls._hour_event_score(
                    candidate,
                    event,
                    gender=gender,
                    birth_date=birth_date,
                )[0]
                for event in events
            )
        has_positive_hour = any(
            row.get("eligible") and hour_nets[row["candidate_id"]] > 0
            for row in ranked
        )
        eligibility_changed = False
        if len(events) >= 2 and has_positive_hour:
            for row in ranked:
                if row["elimination_reasons"]:
                    continue
                if hour_nets[row["candidate_id"]] < 0:
                    row["elimination_reasons"] = [
                        "no_hour_support_for_structured_events"
                    ]
                    row["eligible"] = False
                    row["matched_event_ids"] = []
                    eligibility_changed = True
        if eligibility_changed:
            ranked.sort(
                key=lambda row: (
                    not row["eligible"],
                    -int(row["evidence_score"]),
                    str(row["candidate_id"]),
                )
            )
            for rank, row in enumerate(ranked, start=1):
                row["rank"] = rank
            for match in event_matches:
                match["matched_candidate_ids"] = [
                    row["candidate_id"]
                    for row in ranked
                    if row["eligible"]
                    and match["event_id"] in row["matched_event_ids"]
                ]
        remaining_ids = [
            row["candidate_id"]
            for row in ranked
            if not row["elimination_reasons"]
        ]
        if len(remaining_ids) == 1:
            conclusion = cls._rectification_conclusion(
                remaining_ids=remaining_ids,
                status="hour_determined",
                basis="classical_rectification_unique_remaining",
                selected_candidate_id=remaining_ids[0],
            )
        elif not remaining_ids:
            conclusion = cls._rectification_conclusion(
                remaining_ids=[],
                status="no_valid_candidate",
                basis="classical_rectification_all_eliminated",
                selected_candidate_id=None,
            )
        else:
            conclusion = cls._rectification_conclusion(
                remaining_ids=remaining_ids,
                status="remaining_ambiguous",
                basis="classical_rectification_multiple_remaining",
                selected_candidate_id=None,
            )
        return ranked, event_matches, conclusion

    @classmethod
    def _rank_candidates(
        cls,
        candidates: list[dict[str, Any]],
        events: tuple[dict[str, Any], ...],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rows: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            evidence = [
                cls._event_evidence(candidate, event)
                for event in events
            ]
            eligible = bool(candidate["within_known_time_range"])
            matched_event_ids = (
                [item["event_id"] for item in evidence if item["matched"]]
                if eligible
                else []
            )
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "hour_branch": candidate["hour_branch"],
                    "eligible": eligible,
                    "evidence_score": sum(
                        int(item["evidence_score"]) for item in evidence
                    ),
                    "matched_event_ids": matched_event_ids,
                    "elimination_reasons": []
                    if eligible
                    else ["outside_known_time_range"],
                    "event_evidence": evidence,
                    "_input_index": index,
                }
            )
        rows.sort(
            key=lambda row: (
                not row["eligible"],
                -int(row["evidence_score"]),
                int(row["_input_index"]),
            )
        )
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
            row.pop("_input_index", None)
        event_matches = []
        for event in events:
            matched = [
                row["candidate_id"]
                for row in rows
                if row["eligible"] and event["event_id"] in row["matched_event_ids"]
            ]
            event_matches.append(
                {
                    "event_id": event["event_id"],
                    "domain": event["domain"],
                    "occurred_at": event["occurred_at"],
                    "year_pillar": event["year_pillar"],
                    "matched_candidate_ids": matched,
                }
            )
        return rows, event_matches

    def calculate(self, request: ReadingRequest) -> CalculationResult:
        birth = request.birth_data if isinstance(request.birth_data, dict) else {}
        timezone_name = str(birth.get("timezone") or request.timezone or "")
        location = str(birth.get("location") or request.location or "")
        gender = str(birth.get("gender") or "")
        time_basis_policy = str(
            birth.get("time_basis_policy") or "local_apparent_solar-v1"
        )
        candidates: list[dict[str, Any]] = []
        bazi = BaziProvider(self.skill_dir)
        for branch, candidate_datetime, in_known_range in self._candidate_datetimes(
            date_value=birth.get("time_check_date"),
            timezone_name=timezone_name,
            range_start=birth.get("time_range_start"),
            range_end=birth.get("time_range_end"),
        ):
            candidate_request = ReadingRequest(
                query=request.query,
                system="bazi",
                birth_data={
                    "birth_datetime": candidate_datetime.isoformat(),
                    "timezone": timezone_name,
                    "location": location,
                    "gender": gender,
                    "longitude": birth.get("longitude"),
                    "latitude": birth.get("latitude"),
                    "coordinate_source": birth.get("coordinate_source"),
                    "coordinate_accuracy_meters": birth.get(
                        "coordinate_accuracy_meters"
                    ),
                    "time_basis_policy": time_basis_policy,
                    "zi_hour_policy": str(
                        birth.get("zi_hour_policy") or "midnight"
                    ),
                },
                timezone=timezone_name,
                location=location,
            )
            calculation = bazi.calculate(candidate_request)
            chart_facts = calculation.facts.get("chart_facts") or {}
            output = chart_facts.get("output") or {}
            calendar_facts = chart_facts.get("calendar_normalization") or {}
            candidates.append(
                {
                    "candidate_id": f"hour-{branch}",
                    "hour_branch": branch,
                    "local_civil_datetime": candidate_datetime.isoformat(),
                    "within_known_time_range": in_known_range,
                    "bazi_chart_digest": calculation.facts.get("chart_digest"),
                    "four_pillars": output.get("four_pillars"),
                    "day_master": output.get("day_master"),
                    "calendar_normalization": {
                        "schema_version": calendar_facts.get("schema_version"),
                        "calendar_digest": calendar_facts.get("calendar_digest"),
                        "timezone": calendar_facts.get("timezone"),
                        "time_basis": calendar_facts.get("time_basis"),
                        "local_datetime": calendar_facts.get("local_datetime"),
                        "normalized_datetime": calendar_facts.get(
                            "normalized_datetime"
                        ),
                    },
                }
            )
        events = birth.get("known_events")
        labels_event_count = (
            len(events) if isinstance(events, (list, tuple)) else 0
        )
        structured_events, event_input_status = self._structured_events(
            birth,
            timezone_name=timezone_name,
            location=location,
        )
        event_count = (
            len(structured_events)
            if birth.get("known_event_facts") is not None
            else labels_event_count
        )
        ranked_candidates: list[dict[str, Any]] = []
        event_matches: list[dict[str, Any]] = []
        birth_date = str(birth.get("time_check_date") or "")
        if event_input_status == "structured_valid":
            ranked_candidates, event_matches = self._rank_candidates(
                candidates,
                structured_events,
            )
            ranked_candidates, event_matches, rectification = (
                self._apply_classical_rectification(
                    candidates,
                    ranked_candidates,
                    event_matches,
                    structured_events,
                    gender=gender,
                    birth_date=birth_date,
                )
            )
        else:
            rectification = self._range_only_conclusion(candidates)
        has_ranked_evidence = bool(ranked_candidates)
        output = {
            "candidate_count": len(candidates),
            "candidates": candidates,
            "known_time_range": {
                "date": str(birth.get("time_check_date")),
                "start": str(birth.get("time_range_start")),
                "end": str(birth.get("time_range_end")),
            },
            "time_basis_policy": time_basis_policy,
            "known_event_count": event_count,
            "event_input_status": event_input_status,
            "candidate_rankings": ranked_candidates,
            "event_matches": event_matches,
            "ranking_status": (
                "candidate_evidence_ranked" if has_ranked_evidence else "not_ranked"
            ),
            "event_matching_status": (
                "structured_evidence" if has_ranked_evidence else "not_calculated"
            ),
            "rectification_status": rectification["status"],
            "rectification_conclusion": rectification,
        }
        return CalculationResult.create(
            system="time-check",
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            input_payload={
                "date": str(birth.get("time_check_date")),
                "range_start": str(birth.get("time_range_start")),
                "range_end": str(birth.get("time_range_end")),
                "timezone": timezone_name,
                "location": location,
                "gender": gender,
                "time_basis_policy": time_basis_policy,
                "longitude": birth.get("longitude"),
                "latitude": birth.get("latitude"),
                "coordinate_source": birth.get("coordinate_source"),
                "known_event_count": event_count,
                "structured_event_count": len(structured_events),
            },
            facts={
                "chart_facts": {
                    "output": output,
                    "fact_layer_status": "complete",
                }
            },
            diagnostics=(
                "deterministic_twelve_hour_candidates",
                "bazi_runtime_reused",
                "true_solar_time_preserved",
                (
                    "structured_event_evidence_compared"
                    if has_ranked_evidence
                    else "event_matching_not_calculated"
                ),
                (
                    "candidate_evidence_ranked"
                    if has_ranked_evidence
                    else "candidate_ranking_not_calculated"
                ),
                f"classical_rectification_{rectification['status']}",
            ),
        )

    def extend(
        self,
        calculation: CalculationResult,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> CalculationResult:
        base = calculation.base()
        if base.system != "time-check":
            raise ValueError("time-check extension requires a time-check calculation")
        kind = str(horizon.get("kind") or "")
        if kind not in {"natal", "life"} or horizon.get("start") or horizon.get("end"):
            return _unsupported_extension(base, requested_dimensions, horizon)
        return _attach_extension(
            base,
            requested_dimensions,
            horizon,
            status="complete",
            facts={
                "dimension_fact_scope": {
                    dimension: {
                        "scope": "twelve_deterministic_hour_candidates",
                        "base_calculation_digest": base.result_hash,
                    }
                    for dimension in requested_dimensions
                }
            },
        )


_PROVIDER_ADAPTER_TYPES = (
    BaziProvider,
    FengshuiProvider,
    FortuneProvider,
    LiurenProvider,
    LiuyaoProvider,
    LumingProvider,
    MeihuaProvider,
    PhysiognomyProvider,
    QimenProvider,
    SelectionProvider,
    TaiyiProvider,
    TimeCheckProvider,
    XingmingProvider,
    ZiweiProvider,
)


def missing_required_inputs(system: str, request: ReadingRequest) -> tuple[str, ...]:
    """Audit/test convenience dispatch over provider-owned intake checks."""

    descriptor = _RUNTIME_CATALOG.descriptor(system)
    _, _, class_name = descriptor.entrypoint.partition(":")
    provider_type = globals().get(class_name)
    if provider_type not in _PROVIDER_ADAPTER_TYPES:
        raise ValueError(f"unknown provider system: {system}")
    return provider_type.missing_required_inputs(request)

__all__ = [
    "PROVIDER_CAPABILITIES",
    "missing_required_inputs",
    "BaziProvider",
    "FengshuiProvider",
    "FortuneProvider",
    "LiurenProvider",
    "LiuyaoProvider",
    "MeihuaProvider",
    "PhysiognomyProvider",
    "QimenProvider",
    "SelectionProvider",
    "TaiyiProvider",
    "TimeCheckProvider",
    "STRUCTURED_SYSTEMS",
    "StructuredChartProvider",
    "XingmingProvider",
    "ZiweiProvider",
]
