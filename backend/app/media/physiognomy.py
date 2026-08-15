from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol
from uuid import UUID, uuid4

from app.readings.runtime_contracts import Prepare

MAX_MEDIA_BYTES = 10 * 1024 * 1024
MIN_PIXEL_AXIS = 640
GUEST_RETENTION = timedelta(hours=24)
USER_RETENTION = timedelta(days=7)
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
_MEDIA_TYPES = {"image/jpeg", "image/png", "image/heic"}
_OBSERVATION_MODES = {"face", "palm", "posture", "combined"}
_FACE_REGIONS = {
    "forehead",
    "left_eyebrow",
    "right_eyebrow",
    "left_eye",
    "right_eye",
    "nose",
    "mouth",
    "chin",
    "jawline",
    "left_ear",
    "right_ear",
    "left_cheek",
    "right_cheek",
    "complexion",
}
_FACE_FEATURES = {"visible_morphology"}
_FACE_DESCRIPTORS = {
    "forehead": {
        "region_visible",
        "relative_width_broad",
        "relative_width_narrow",
        "contour_rounded",
        "contour_flat",
    },
    "left_eyebrow": {
        "region_visible",
        "line_straight",
        "line_curved",
        "density_even",
        "density_sparse_visible",
    },
    "right_eyebrow": {
        "region_visible",
        "line_straight",
        "line_curved",
        "density_even",
        "density_sparse_visible",
    },
    "left_eye": {"region_visible", "aperture_open", "aperture_narrow", "alignment_level"},
    "right_eye": {"region_visible", "aperture_open", "aperture_narrow", "alignment_level"},
    "nose": {
        "region_visible",
        "bridge_straight",
        "tip_rounded",
        "relative_width_broad",
        "relative_width_narrow",
    },
    "mouth": {
        "region_visible",
        "lip_line_straight",
        "lip_line_curved",
        "mouth_closed",
        "mouth_open",
    },
    "chin": {"region_visible", "contour_rounded", "contour_square", "contour_pointed"},
    "jawline": {"region_visible", "outline_rounded", "outline_angular"},
    "left_ear": {"region_visible", "outline_visible", "partially_visible"},
    "right_ear": {"region_visible", "outline_visible", "partially_visible"},
    "left_cheek": {"region_visible", "contour_full_relative", "contour_flat_relative"},
    "right_cheek": {"region_visible", "contour_full_relative", "contour_flat_relative"},
    "complexion": {"region_visible"},
}
_TEXT_QUALITY = {
    "lighting": "not_applicable",
    "camera_angle": "caller_description",
    "focus": "not_applicable",
    "resolution": "not_applicable",
    "filtering": "not_applicable",
    "color_fidelity": "not_applicable",
}
_OPAQUE_SUBJECT_REF_RE = re.compile(r"^sid-[0-9a-f]{32,64}$")

type OwnerKind = Literal["guest", "user"]
type ObservationMode = Literal["face", "palm", "posture", "combined"]
type MediaStatus = Literal["ready", "deleted", "expired"]


class PhysiognomyMediaError(ValueError):
    """The media or its observation contract cannot be accepted."""


class ConsentRequiredError(PhysiognomyMediaError):
    """The caller has not granted the independent photo-processing consent."""


class MediaValidationError(PhysiognomyMediaError):
    """The uploaded bytes or metadata are outside the media contract."""


class MediaQualityError(PhysiognomyMediaError):
    """The upload cannot support the minimum deterministic quality gate."""


class MediaNotFoundError(PhysiognomyMediaError):
    """The requested private media asset is not known to the adapter."""


class MediaNotReadyError(PhysiognomyMediaError):
    """The asset is no longer available for a Runtime input."""


class UnsupportedObservationModeError(PhysiognomyMediaError):
    """The current Runtime release does not support this observation mode."""


@dataclass(frozen=True, slots=True)
class MediaAuditEvent:
    action: str
    asset_id: str
    owner_kind: OwnerKind
    status: MediaStatus
    reason: str | None = None


@dataclass(slots=True)
class PhysiognomyMediaAsset:
    asset_id: str
    owner_kind: OwnerKind
    owner_id: UUID
    object_key: str
    content_type: str
    byte_size: int
    width: int
    height: int
    mode: ObservationMode
    created_at: datetime
    expires_at: datetime
    status: MediaStatus = "ready"
    deleted_at: datetime | None = None


class PrivateMediaStore(Protocol):
    def put(self, object_key: str, payload: bytes) -> None:
        """Write one private object under an adapter-generated key."""

    def read(self, object_key: str) -> bytes:
        """Read one private object for an owner-scoped operation."""

    def delete(self, object_key: str) -> None:
        """Delete one private object; repeated deletion is idempotent."""


class InMemoryPrivateMediaStore:
    """Small local/test store; production must provide object storage instead."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, object_key: str, payload: bytes) -> None:
        if object_key in self._objects:
            raise MediaValidationError("private media object key already exists")
        self._objects[object_key] = bytes(payload)

    def read(self, object_key: str) -> bytes:
        try:
            return self._objects[object_key]
        except KeyError as error:
            raise MediaNotFoundError("private media object not found") from error

    def delete(self, object_key: str) -> None:
        self._objects.pop(object_key, None)

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._objects))


class LocalPrivateMediaStore:
    """Filesystem store for local development, never exposed as a public path."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, object_key: str) -> Path:
        candidate = (self.root / object_key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise MediaValidationError("private media object key escapes storage root")
        return candidate

    def put(self, object_key: str, payload: bytes) -> None:
        path = self._path(object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise MediaValidationError("private media object key already exists")
        path.write_bytes(payload)

    def read(self, object_key: str) -> bytes:
        path = self._path(object_key)
        try:
            return path.read_bytes()
        except FileNotFoundError as error:
            raise MediaNotFoundError("private media object not found") from error

    def delete(self, object_key: str) -> None:
        self._path(object_key).unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class PhysiognomyRuntimeInput:
    subject_ref: str
    dimension_ids: tuple[str, ...]
    physiognomy_spec: Mapping[str, object]

    def to_prepare(self, *, query: str, action: str) -> Prepare:
        from app.readings.request_compiler import compile_physiognomy_prepare

        return compile_physiognomy_prepare(
            action=action,
            query=query,
            subject_ref=self.subject_ref,
            physiognomy_spec=self.physiognomy_spec,
            dimension_ids=self.dimension_ids,
        )


class PhysiognomyMediaAdapter:
    """Validate private media and emit only caller-normalized face observations."""

    def __init__(
        self,
        *,
        store: PrivateMediaStore,
        audit_sink: Callable[[MediaAuditEvent], None] | None = None,
    ) -> None:
        self.store = store
        self.audit_sink = audit_sink
        self._assets: dict[str, PhysiognomyMediaAsset] = {}

    def ingest(
        self,
        *,
        owner_kind: OwnerKind,
        owner_id: UUID,
        content_type: str,
        filename: str,
        payload: bytes,
        width: int,
        height: int,
        consent: bool,
        mode: ObservationMode,
        now: datetime,
    ) -> PhysiognomyMediaAsset:
        del filename
        if not consent:
            raise ConsentRequiredError("independent photo-processing consent is required")
        if owner_kind not in {"guest", "user"}:
            raise MediaValidationError("unsupported media owner kind")
        if mode not in _OBSERVATION_MODES:
            raise MediaValidationError("unsupported physiognomy observation mode")
        if content_type not in _MEDIA_TYPES:
            raise MediaValidationError("unsupported physiognomy media type")
        if not isinstance(payload, bytes) or not payload or len(payload) > MAX_MEDIA_BYTES:
            raise MediaValidationError("physiognomy media byte size is outside the limit")
        if not _matches_container(content_type, payload):
            raise MediaValidationError("physiognomy media container does not match its type")
        if (
            isinstance(width, bool)
            or not isinstance(width, int)
            or isinstance(height, bool)
            or not isinstance(height, int)
            or width < MIN_PIXEL_AXIS
            or height < MIN_PIXEL_AXIS
        ):
            raise MediaQualityError(
                f"physiognomy media must be at least {MIN_PIXEL_AXIS}px on both axes"
            )
        created_at = _aware_utc(now)
        retention = GUEST_RETENTION if owner_kind == "guest" else USER_RETENTION
        asset_id = str(uuid4())
        object_key = f"private/physiognomy/{asset_id}"
        self.store.put(object_key, payload)
        asset = PhysiognomyMediaAsset(
            asset_id=asset_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
            object_key=object_key,
            content_type=content_type,
            byte_size=len(payload),
            width=width,
            height=height,
            mode=mode,
            created_at=created_at,
            expires_at=created_at + retention,
        )
        self._assets[asset_id] = asset
        self._audit(
            MediaAuditEvent(
                action="physiognomy_media.accepted",
                asset_id=asset_id,
                owner_kind=owner_kind,
                status=asset.status,
            )
        )
        return asset

    def restore(self, asset: PhysiognomyMediaAsset) -> None:
        """Rehydrate owner-scoped metadata after an application restart."""

        self._assets[asset.asset_id] = asset

    def get(self, asset_id: str) -> PhysiognomyMediaAsset:
        try:
            return self._assets[asset_id]
        except KeyError as error:
            raise MediaNotFoundError("physiognomy media asset not found") from error

    def delete(self, asset_id: str, *, now: datetime) -> PhysiognomyMediaAsset:
        asset = self.get(asset_id)
        if asset.status == "ready":
            self.store.delete(asset.object_key)
            asset.status = "deleted"
            asset.deleted_at = _aware_utc(now)
            self._audit(
                MediaAuditEvent(
                    action="physiognomy_media.deleted",
                    asset_id=asset.asset_id,
                    owner_kind=asset.owner_kind,
                    status=asset.status,
                )
            )
        return asset

    def expire(self, *, now: datetime) -> tuple[str, ...]:
        current = _aware_utc(now)
        expired: list[str] = []
        for asset in self._assets.values():
            if asset.status != "ready" or asset.expires_at > current:
                continue
            self.store.delete(asset.object_key)
            asset.status = "expired"
            asset.deleted_at = current
            expired.append(asset.asset_id)
            self._audit(
                MediaAuditEvent(
                    action="physiognomy_media.expired",
                    asset_id=asset.asset_id,
                    owner_kind=asset.owner_kind,
                    status=asset.status,
                )
            )
        return tuple(expired)

    def build_runtime_input(
        self,
        *,
        asset_id: str,
        subject_ref: str,
        observations: Sequence[Mapping[str, object]],
        dimension_ids: tuple[str, ...],
    ) -> PhysiognomyRuntimeInput:
        asset = self.get(asset_id)
        if asset.status != "ready":
            raise MediaNotReadyError("physiognomy media is no longer available")
        if asset.mode != "face":
            raise UnsupportedObservationModeError(
                "the current physiognomy Runtime contract only supports face observations"
            )
        if _OPAQUE_SUBJECT_REF_RE.fullmatch(subject_ref) is None:
            raise MediaValidationError("physiognomy subject_ref must be an opaque sid identifier")
        if not observations:
            raise MediaValidationError("at least one structured observation is required")

        target_ids: dict[tuple[str, str], str] = {}
        targets: list[dict[str, object]] = []
        normalized: list[dict[str, object]] = []
        for raw in observations:
            (
                region,
                feature_kind,
                descriptor,
                visibility,
                uncertainty,
                occlusion,
            ) = _observation_fields(raw)
            key = (region, feature_kind)
            target_id = target_ids.get(key)
            if target_id is None:
                target_id = f"tid-{uuid4().hex}"
                target_ids[key] = target_id
                targets.append(
                    {
                        "target_id": target_id,
                        "taxonomy": "anatomical_face_v1",
                        "region": region,
                        "feature_kind": feature_kind,
                        "required": True,
                    }
                )
            observation_id = f"oid-{uuid4().hex}"
            normalized.append(
                {
                    "observation_id": observation_id,
                    "target_id": target_id,
                    "source_type": "user_file",
                    "region": region,
                    "feature_kind": feature_kind,
                    "visibility": visibility,
                    "value": {"descriptor": descriptor},
                    "occlusion": occlusion,
                    "uncertainty": uncertainty,
                    "source_ref": f"rid-{uuid4().hex}",
                    "quality": dict(_TEXT_QUALITY),
                }
            )

        spec: dict[str, object] = {
            "schema_version": "mingli-physiognomy-input-v1",
            "observation_scope": "face",
            "subject_ref": subject_ref,
            "requested_targets": targets,
            "assets": [],
            "observations": normalized,
            "confirmed_observation_ids": [
                str(item["observation_id"]) for item in normalized
            ],
            "comparison_relations": [],
            "source_layer_policy": "terminology_and_methodology_only",
        }
        return PhysiognomyRuntimeInput(
            subject_ref=subject_ref,
            dimension_ids=dimension_ids,
            physiognomy_spec=spec,
        )

    def _audit(self, event: MediaAuditEvent) -> None:
        if self.audit_sink is not None:
            self.audit_sink(event)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MediaValidationError("media timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _matches_container(content_type: str, payload: bytes) -> bool:
    if content_type == "image/jpeg":
        return payload.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return payload.startswith(_PNG_SIGNATURE)
    return (
        len(payload) >= 12
        and payload[4:8] == b"ftyp"
        and payload[8:12] in _HEIC_BRANDS
    )


def image_dimensions(content_type: str, payload: bytes) -> tuple[int, int]:
    """Read dimensions from the admitted container without decoding pixels."""

    if content_type == "image/png":
        if len(payload) < 24 or payload[12:16] != b"IHDR":
            raise MediaQualityError("PNG dimensions cannot be verified")
        return int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")
    if content_type == "image/jpeg":
        return _jpeg_dimensions(payload)
    if content_type == "image/heic":
        marker = payload.find(b"ispe")
        if marker >= 0 and len(payload) >= marker + 16:
            return (
                int.from_bytes(payload[marker + 8 : marker + 12], "big"),
                int.from_bytes(payload[marker + 12 : marker + 16], "big"),
            )
        raise MediaQualityError("HEIC dimensions cannot be verified")
    raise MediaValidationError("unsupported physiognomy media type")


def _jpeg_dimensions(payload: bytes) -> tuple[int, int]:
    if not payload.startswith(b"\xff\xd8\xff"):
        raise MediaQualityError("JPEG dimensions cannot be verified")
    index = 2
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while index + 3 < len(payload):
        if payload[index] != 0xFF:
            index += 1
            continue
        while index < len(payload) and payload[index] == 0xFF:
            index += 1
        if index >= len(payload):
            break
        marker = payload[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(payload):
            break
        segment_length = int.from_bytes(payload[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > len(payload):
            break
        if marker in sof_markers and segment_length >= 7:
            height = int.from_bytes(payload[index + 3 : index + 5], "big")
            width = int.from_bytes(payload[index + 5 : index + 7], "big")
            return width, height
        index += segment_length
    raise MediaQualityError("JPEG dimensions cannot be verified")


def _observation_fields(
    raw: Mapping[str, object],
) -> tuple[str, str, str, str, float, float]:
    allowed = {
        "region",
        "feature_kind",
        "descriptor",
        "visibility",
        "uncertainty",
        "occlusion",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise MediaValidationError(
            f"structured observation contains unsupported fields: {sorted(unknown)!r}"
        )
    values = [raw.get(key) for key in ("region", "feature_kind", "descriptor", "visibility")]
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise MediaValidationError("structured observation text fields are required")
    region, feature_kind, descriptor, visibility = (str(item).strip() for item in values)
    if region not in _FACE_REGIONS or feature_kind not in _FACE_FEATURES:
        raise MediaValidationError("structured observation is outside the face contract")
    if descriptor not in _FACE_DESCRIPTORS[region]:
        raise MediaValidationError("structured observation descriptor is not admitted")
    if visibility not in {"full", "partial"}:
        raise MediaQualityError("only visible or partially visible observations can be confirmed")
    uncertainty = _bounded_number(raw.get("uncertainty", 0), label="uncertainty")
    occlusion = _bounded_number(raw.get("occlusion", 0), label="occlusion")
    return region, feature_kind, descriptor, visibility, uncertainty, occlusion


def _bounded_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MediaValidationError(f"observation {label} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise MediaValidationError(f"observation {label} must be in [0, 1]")
    return result
