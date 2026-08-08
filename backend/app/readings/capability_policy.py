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
P0_EXPOSED_CAPABILITY_IDS: Final = ("bazi", "fortune", "liuyao")


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
        "bazi_deep": ProductRoute("bazi", "natal", "life"),
        "today": ProductRoute("fortune", "near_time_personal", "day"),
        "near_seven": ProductRoute("fortune", "near_time_personal", "week"),
        "liuyao_one_question": ProductRoute(
            "liuyao",
            "concrete_event",
            "instant",
        ),
    }
)


def require_p0_capability(capability_id: str) -> str:
    if capability_id not in P0_EXPOSED_CAPABILITY_IDS:
        raise CapabilityNotExposedError(
            f"capability {capability_id!r} is installed but not exposed in P0"
        )
    return capability_id


def route_for_action(action: str) -> ProductRoute:
    try:
        route = _PRODUCT_ROUTES[action]
    except KeyError as error:
        raise UnsupportedProductActionError(f"unsupported product action: {action!r}") from error
    require_p0_capability(route.capability_id)
    return route
