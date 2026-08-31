from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

type ContentAccessPhase = Literal["development_free_all_supported"]


@dataclass(frozen=True, slots=True)
class ContentAccessPolicy:
    """Central policy for content visibility at Reading presentation boundaries."""

    phase: ContentAccessPhase

    @property
    def legacy_time_layer_resolution(self) -> Literal["granted"]:
        """Keep the dormant entitlement v1 response readable in development.

        Capability availability and typed ViewModel presence still decide whether
        a layer exists. Billing state does not participate in active visibility.
        """

        return "granted"


ACTIVE_CONTENT_ACCESS_POLICY: Final = ContentAccessPolicy(
    phase="development_free_all_supported"
)
