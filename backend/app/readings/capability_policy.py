import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal

V51_RELEASE_CAPABILITY_IDS: Final = (
    "bazi",
    "fengshui",
    "fortune",
    "liuren",
    "liuyao",
    "luming-nayin",
    "meihua",
    "physiognomy",
    "qimen",
    "selection",
    "taiyi",
    "xingming",
    "ziwei",
)
V53_TIME_CHECK_RELEASE_CAPABILITY_IDS: Final = (
    *V51_RELEASE_CAPABILITY_IDS[:11],
    "time-check",
    *V51_RELEASE_CAPABILITY_IDS[11:],
)
P0_EXPOSED_CAPABILITY_IDS: Final = ("bazi", "fortune", "liuyao")
P10_EXPOSED_CAPABILITY_IDS: Final = (
    "bazi",
    "fengshui",
    "fortune",
    "liuren",
    "liuyao",
    "luming-nayin",
    "meihua",
    "physiognomy",
    "selection",
    "taiyi",
    "qimen",
    "xingming",
    "ziwei",
    "time-check",
)
RELATIONSHIP_PRODUCT_IDS: Final = (
    "bazi-relationship",
    "ziwei-relationship",
    "qizheng-relationship",
)
PAID_PRODUCT_IDS: Final = ("bazi-deep", "qimen-deep", "liuyao-deep")
CAPABILITY_LABELS: Final = MappingProxyType(
    {
        "bazi": "八字",
        "fengshui": "风水",
        "fortune": "日运/近时运势",
        "liuren": "大六壬",
        "liuyao": "六爻",
        "luming-nayin": "禄命/纳音",
        "meihua": "梅花易数",
        "physiognomy": "相法",
        "qimen": "奇门遁甲",
        "selection": "择日",
        "taiyi": "太乙",
        "time-check": "寻时定盘",
        "xingming": "星命/七政四余",
        "ziwei": "紫微斗数",
    }
)


class CapabilityNotExposedError(ValueError):
    """A runtime capability is not selectable by the current product version."""


class UnsupportedProductActionError(ValueError):
    """The request did not originate from a frozen product action."""


@dataclass(frozen=True, slots=True)
class ProductRoute:
    capability_id: str
    object_id: str
    horizon_id: str


_PRODUCT_ROUTES = MappingProxyType(
    {
        "profile_preview": ProductRoute("bazi", "natal", "life"),
        "bazi_year_preview": ProductRoute("bazi", "natal", "year"),
        "bazi_month_preview": ProductRoute("bazi", "natal", "month"),
        "bazi_day_preview": ProductRoute("bazi", "natal", "day"),
        "bazi_deep": ProductRoute("bazi", "natal", "life"),
        "five_elements_facts_preview": ProductRoute("bazi", "natal", "life"),
        "life_kline_series_preview": ProductRoute("bazi", "life_kline", "life"),
        "chart_similarity_preview": ProductRoute("bazi", "natal", "life"),
        "today": ProductRoute("fortune", "near_time_personal", "day"),
        "near_seven": ProductRoute("fortune", "near_time_personal", "week"),
        "liuyao_one_question": ProductRoute(
            "liuyao",
            "concrete_event",
            "instant",
        ),
        "liuyao_deep": ProductRoute(
            "liuyao",
            "concrete_event",
            "instant",
        ),
        # Wenshi uses Liuyao as the Runtime primary and required comparisons
        # for Qimen and Daliuren. Product identity is persisted separately.
        "wenshi_one_question": ProductRoute(
            "liuyao",
            "concrete_event",
            "instant",
        ),
        "ziwei_preview": ProductRoute("ziwei", "natal", "life"),
        "ziwei_year_preview": ProductRoute("ziwei", "natal", "year"),
        "ziwei_month_preview": ProductRoute("ziwei", "natal", "month"),
        "qizheng_preview": ProductRoute("xingming", "natal", "life"),
        "qizheng_year_preview": ProductRoute("xingming", "natal", "year"),
        "qizheng_month_preview": ProductRoute("xingming", "natal", "month"),
        "qizheng_day_preview": ProductRoute("xingming", "natal", "day"),
        # Canwen keeps 八字 as the primary brief and binds selected
        # 紫微/七政 providers as required comparisons.  The current view
        # exposes Runtime-declared scope alignment and missing cross-art
        # contracts; substantive synthesis remains a separate boundary.
        "canwen_preview": ProductRoute("bazi", "natal", "life"),
        # Hecan uses the same required natal comparison providers, but keeps
        # a distinct product identity so its strict ViewModel cannot be
        # mistaken for a question-led Canwen result.
        "hecan_preview": ProductRoute("bazi", "natal", "life"),
        "bazi_relationship_preview": ProductRoute("bazi", "natal", "life"),
        "ziwei_relationship_preview": ProductRoute("ziwei", "natal", "life"),
        "qizheng_relationship_preview": ProductRoute("xingming", "natal", "life"),
        # Meihua accepts five explicit Runtime casting-method contracts; the
        # product must never substitute a time cast for another method.
        "meihua_preview": ProductRoute("meihua", "concrete_event", "instant"),
        "luming_nayin_preview": ProductRoute("luming-nayin", "natal", "life"),
        # The public Rhythm tool is a facts-only projection of the existing
        # Luming/Nayin Provider.  It does not introduce a second sound or
        # naming algorithm behind the same Runtime capability.
        "rhythm_preview": ProductRoute("luming-nayin", "natal", "life"),
        "time_check_preview": ProductRoute("time-check", "natal", "life"),
        "taiyi_preview": ProductRoute("taiyi", "macro_historical", "year"),
        "selection_preview": ProductRoute(
            "selection", "calendar_choice", "year"
        ),
        "fengshui_preview": ProductRoute(
            "fengshui", "spatial_observation", "instant"
        ),
        "physiognomy_preview": ProductRoute(
            "physiognomy", "visible_observation", "instant"
        ),
        "qimen_one_question": ProductRoute("qimen", "concrete_event", "instant"),
        "qimen_deep": ProductRoute("qimen", "concrete_event", "instant"),
        "liuren_one_question": ProductRoute(
            "liuren",
            "concrete_event",
            "instant",
        ),
        "liuren_timing_question": ProductRoute(
            "liuren",
            "concrete_event",
            "month",
        ),
    }
)


def product_actions_for_capability(capability_id: str) -> tuple[str, ...]:
    return tuple(
        action
        for action, route in _PRODUCT_ROUTES.items()
        if route.capability_id == capability_id
    )


def require_p0_capability(capability_id: str) -> str:
    if capability_id not in P0_EXPOSED_CAPABILITY_IDS:
        raise CapabilityNotExposedError(
            f"capability {capability_id!r} is installed but not exposed in P0"
        )
    return capability_id


def require_public_runtime_capabilities(
    capability_ids: Iterable[str],
    *,
    environment: str,
    real_traffic_enabled: bool,
) -> None:
    """Keep non-P0 Runtime products out of real public traffic.

    Local and test stacks intentionally exercise the installed P10 providers.
    A production or explicitly real-traffic stack may only create readings
    whose complete Runtime capability set is already in P0.
    """
    if environment != "production" and not real_traffic_enabled:
        return
    for capability_id in dict.fromkeys(capability_ids):
        require_p0_capability(capability_id)


def require_public_product_exposure(
    product_id: str | None,
    *,
    environment: str,
    real_traffic_enabled: bool,
) -> None:
    """Keep relationship products out of production until their full gate closes.

    Relationship products deliberately reuse the single-art Runtime capability
    IDs, so a capability-only gate would incorrectly treat Bazi relationship as
    a P0 product.  Local and test stacks still exercise the real integration.
    """
    if environment != "production" and not real_traffic_enabled:
        return
    if product_id in (*RELATIONSHIP_PRODUCT_IDS, *PAID_PRODUCT_IDS):
        raise CapabilityNotExposedError(
            f"product {product_id!r} is not exposed in production yet"
        )


def route_for_action(action: str) -> ProductRoute:
    try:
        route = _PRODUCT_ROUTES[action]
    except KeyError as error:
        raise UnsupportedProductActionError(f"unsupported product action: {action!r}") from error
    if route.capability_id not in P10_EXPOSED_CAPABILITY_IDS:
        raise CapabilityNotExposedError(
            f"capability {route.capability_id!r} is not exposed in the current product"
        )
    return route


CapabilityTier = Literal["A", "B", "C"]
JUDGMENT_ROLE: Final = "issue_specific_judgment_rule"

_LOCAL_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / ".runtime"
_LOCAL_RELEASE_DIRS: Final = {
    "v51": "v51-release",
    "v51-extension-facts": "v51-release",
    "v52-relationship": "v52-relationship-release",
    "v53-time-check": "v53-time-check-release",
}

# This maps public products to the Runtime system that owns their rules. It
# deliberately contains no tier or count. Those values are read from the
# admitted release evidence index below.
_PRODUCT_SYSTEMS: Final[tuple[tuple[str, str, str | None], ...]] = (
    ("bazi", "八字", "bazi"),
    ("luming-nayin", "禄命纳音", "luming-nayin"),
    ("ziwei", "紫微", "ziwei"),
    ("qizheng", "七政四余", "xingming"),
    ("liuyao", "六爻", "divination"),
    ("meihua", "梅花易数", "divination"),
    ("qimen", "奇门遁甲", "qimen"),
    ("daliuren", "大六壬", "liuren"),
    ("taiyi", "太乙", "taiyi"),
    ("selection", "择日", "selection"),
    ("fengshui", "风水", "fengshui"),
    ("jianxiang", "见相", "physiognomy"),
    ("fortune", "日运与近时运势", None),
)

_PRODUCT_ALIASES: Final = {
    "bazi-deep": "bazi",
    "qimen-deep": "qimen",
    "liuyao-deep": "liuyao",
    "qizheng-relationship": "qizheng",
    "ziwei-relationship": "ziwei",
    "bazi-relationship": "bazi",
    "life-kline-series": "bazi",
    "liuren": "daliuren",
}

_DIVINATION_PREFIXES: Final = {
    "liuyao": (
        "divination/huangjin-ce#",
        "divination/zengshan-buyi#",
    ),
    "meihua": ("divination/meihua-yishu#",),
}


@dataclass(frozen=True, slots=True)
class RuntimeCapabilityProjection:
    capability_id: str
    label: str
    tier: CapabilityTier
    source_system: str | None
    runtime_active_rule_count: int
    judgment_rule_count: int
    source_status: Literal["available", "unavailable"]
    user_decision_pending: bool = False


def evidence_rules_path(
    release_root: Path | None,
    release_profile: str = "v53-time-check",
) -> Path:
    resolved_root = release_root
    if resolved_root is None:
        resolved_root = _LOCAL_RUNTIME_ROOT / _LOCAL_RELEASE_DIRS.get(
            release_profile,
            "v53-time-check-release",
        )
    return resolved_root / "references" / "index" / "evidence-rules.jsonl"


def _rule_belongs_to_product(row: dict[str, object], product_id: str) -> bool:
    if row.get("system") != "divination":
        return False
    rule_id = row.get("rule_id")
    if not isinstance(rule_id, str):
        return False
    return any(rule_id.startswith(prefix) for prefix in _DIVINATION_PREFIXES[product_id])


def _counts_from_rows(
    rows: list[dict[str, object]],
) -> tuple[Counter[str], Counter[str]]:
    active: Counter[str] = Counter()
    judgment: Counter[str] = Counter()
    for row in rows:
        if row.get("runtime_active") is not True:
            continue
        system = row.get("system")
        if isinstance(system, str):
            active[system] += 1
        if row.get("evidence_role") == JUDGMENT_ROLE and isinstance(system, str):
            judgment[system] += 1
    for product_id in ("liuyao", "meihua"):
        active[product_id] = sum(
            1
            for row in rows
            if row.get("runtime_active") is True
            and _rule_belongs_to_product(row, product_id)
        )
        judgment[product_id] = sum(
            1
            for row in rows
            if row.get("runtime_active") is True
            and row.get("evidence_role") == JUDGMENT_ROLE
            and _rule_belongs_to_product(row, product_id)
        )
    return active, judgment


def _read_counts(path: Path) -> tuple[Counter[str], Counter[str]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return _counts_from_rows(rows)


def _tier_for(
    product_id: str,
    *,
    active_count: int,
    judgment_count: int,
    source_available: bool,
) -> tuple[CapabilityTier, bool]:
    if not source_available or active_count == 0:
        return "C", False
    # The index has two Liuyao and three Meihua judgment rules. The product
    # decision is explicitly pending, so both remain B until user approval.
    if product_id in {"liuyao", "meihua"}:
        return "B", judgment_count > 0
    return ("A", False) if judgment_count > 0 else ("B", False)


def project_capabilities(
    *,
    release_root: Path | None,
    release_profile: str = "v53-time-check",
) -> tuple[RuntimeCapabilityProjection, ...]:
    path = evidence_rules_path(release_root, release_profile)
    source_available = path.is_file()
    active: Counter[str] = Counter()
    judgment: Counter[str] = Counter()
    if source_available:
        active, judgment = _read_counts(path)

    projections: list[RuntimeCapabilityProjection] = []
    for product_id, label, source_system in _PRODUCT_SYSTEMS:
        count_key = product_id if product_id in {"liuyao", "meihua"} else source_system
        active_count = active[count_key] if count_key is not None else 0
        judgment_count = judgment[count_key] if count_key is not None else 0
        tier, pending = _tier_for(
            product_id,
            active_count=active_count,
            judgment_count=judgment_count,
            source_available=source_available,
        )
        projections.append(
            RuntimeCapabilityProjection(
                capability_id=product_id,
                label=label,
                tier=tier,
                source_system=source_system,
                runtime_active_rule_count=active_count,
                judgment_rule_count=judgment_count,
                source_status="available" if source_available else "unavailable",
                user_decision_pending=pending,
            )
        )
    return tuple(projections)


def project_capability(
    *,
    capability_id: str,
    product_id: str | None,
    release_root: Path | None,
    release_profile: str = "v53-time-check",
) -> RuntimeCapabilityProjection:
    raw_id = product_id or capability_id
    requested_id = _PRODUCT_ALIASES.get(raw_id, raw_id)
    if requested_id == "xingming":
        requested_id = "qizheng"
    for projection in project_capabilities(
        release_root=release_root,
        release_profile=release_profile,
    ):
        if projection.capability_id == requested_id:
            return projection
    return RuntimeCapabilityProjection(
        capability_id=requested_id,
        label=requested_id,
        tier="C",
        source_system=None,
        runtime_active_rule_count=0,
        judgment_rule_count=0,
        source_status="unavailable",
    )
