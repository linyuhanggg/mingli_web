from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

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
PAID_PRODUCT_IDS: Final = ("bazi-deep", "qimen-deep")
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
        "chart_similarity_preview": ProductRoute("bazi", "natal", "life"),
        "today": ProductRoute("fortune", "near_time_personal", "day"),
        "near_seven": ProductRoute("fortune", "near_time_personal", "week"),
        "liuyao_one_question": ProductRoute(
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
