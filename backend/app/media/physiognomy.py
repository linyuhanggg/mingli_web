from __future__ import annotations

import hashlib
import hmac
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol, TypedDict
from uuid import UUID, uuid4

from app.readings.runtime_contracts import Prepare

MAX_MEDIA_BYTES = 10 * 1024 * 1024
MIN_PIXEL_AXIS = 640
GUEST_RETENTION = timedelta(hours=24)
USER_RETENTION = timedelta(days=7)
SIGNED_DOWNLOAD_MIN_TTL = timedelta(minutes=1)
SIGNED_DOWNLOAD_MAX_TTL = timedelta(hours=1)
_LOCAL_SIGNED_DOWNLOAD_KEY = b"mingli-local-fake-private-media-download"
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
_PALM_REGIONS = {
    "left_palm",
    "right_palm",
    "life_line",
    "head_line",
    "heart_line",
    "fate_line",
}
_PALM_DESCRIPTORS = {
    "left_palm": {"region_visible", "ridge_visible", "texture_even_visible"},
    "right_palm": {"region_visible", "ridge_visible", "texture_even_visible"},
    "life_line": {
        "region_visible",
        "line_continuous",
        "line_discontinuous",
        "line_deep_visible",
        "line_shallow_visible",
    },
    "head_line": {
        "region_visible",
        "line_continuous",
        "line_discontinuous",
        "line_deep_visible",
        "line_shallow_visible",
    },
    "heart_line": {
        "region_visible",
        "line_continuous",
        "line_discontinuous",
        "line_deep_visible",
        "line_shallow_visible",
    },
    "fate_line": {
        "region_visible",
        "line_continuous",
        "line_discontinuous",
        "line_deep_visible",
        "line_shallow_visible",
    },
}
_POSTURE_REGIONS = {
    "head_posture",
    "shoulder_line",
    "spine_curve",
    "walking_gait",
    "sitting_posture",
}
_POSTURE_DESCRIPTORS = {
    "head_posture": {"region_visible", "level", "forward_tilt", "backward_tilt"},
    "shoulder_line": {"region_visible", "level", "uneven"},
    "spine_curve": {"region_visible", "aligned", "curved"},
    "walking_gait": {"region_visible", "steady", "uneven"},
    "sitting_posture": {"region_visible", "upright", "forward_lean", "uneven"},
}
class _ModeProfile(TypedDict):
    taxonomy: str
    regions: set[str]
    features: set[str]
    descriptors: dict[str, set[str]]


_MODE_PROFILES: dict[str, _ModeProfile] = {
    "face": {
        "taxonomy": "anatomical_face_v1",
        "regions": _FACE_REGIONS,
        "features": _FACE_FEATURES,
        "descriptors": _FACE_DESCRIPTORS,
    },
    "palm": {
        "taxonomy": "anatomical_palm_v1",
        "regions": _PALM_REGIONS,
        "features": _FACE_FEATURES,
        "descriptors": _PALM_DESCRIPTORS,
    },
    "posture": {
        "taxonomy": "posture_observation_v1",
        "regions": _POSTURE_REGIONS,
        "features": _FACE_FEATURES,
        "descriptors": _POSTURE_DESCRIPTORS,
    },
}
_MODE_ORDER = ("face", "palm", "posture")
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


class SignedDownloadInvalidError(PhysiognomyMediaError):
    """The signed download token is malformed or has a bad signature."""


class SignedDownloadExpiredError(PhysiognomyMediaError):
    """The signed download token is past its TTL."""


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


@dataclass(frozen=True, slots=True)
class SignedDownloadTicket:
    asset_id: str
    token: str
    expires_at: datetime
    content_type: str


@dataclass(frozen=True, slots=True)
class SignedDownloadPayload:
    asset_id: str
    content_type: str
    payload: bytes


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
    """Validate private media and emit only caller-normalized observations."""

    def __init__(
        self,
        *,
        store: PrivateMediaStore,
        audit_sink: Callable[[MediaAuditEvent], None] | None = None,
        signing_key: bytes | None = None,
    ) -> None:
        self.store = store
        self.audit_sink = audit_sink
        self._signing_key = (
            bytes(signing_key) if signing_key is not None else _LOCAL_SIGNED_DOWNLOAD_KEY
        )
        self._assets: dict[str, PhysiognomyMediaAsset] = {}
        self._signed_downloads: dict[str, datetime] = {}

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
            ) = _observation_fields(raw, mode=asset.mode)
            key = (region, feature_kind)
            target_id = target_ids.get(key)
            if target_id is None:
                target_id = f"tid-{uuid4().hex}"
                target_ids[key] = target_id
                targets.append(
                    {
                        "target_id": target_id,
                        "taxonomy": _taxonomy_for(asset.mode, region),
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
            "observation_scope": asset.mode,
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

    def issue_signed_download(
        self,
        asset_id: str,
        *,
        owner_kind: OwnerKind,
        owner_id: UUID,
        ttl: timedelta,
        now: datetime,
    ) -> SignedDownloadTicket:
        asset = self.get(asset_id)
        if asset.owner_kind != owner_kind or asset.owner_id != owner_id:
            raise MediaNotFoundError("physiognomy media asset not found")
        if asset.status != "ready":
            raise MediaNotReadyError("physiognomy media is no longer available")
        if ttl < SIGNED_DOWNLOAD_MIN_TTL or ttl > SIGNED_DOWNLOAD_MAX_TTL:
            raise MediaValidationError(
                "signed download ttl must be between 1 minute and 1 hour"
            )
        issued_at = _aware_utc(now)
        expires_at = min(issued_at + ttl, asset.expires_at)
        if expires_at <= issued_at:
            raise MediaNotReadyError("physiognomy media is no longer available")
        expires_unix = int(expires_at.timestamp())
        token = ".".join(
            (
                "v1",
                asset.asset_id,
                str(expires_unix),
                self._signature(asset, expires_unix),
            )
        )
        self._signed_downloads[token] = expires_at
        return SignedDownloadTicket(
            asset_id=asset.asset_id,
            token=token,
            expires_at=expires_at,
            content_type=asset.content_type,
        )

    def download_signed(
        self,
        token: str,
        *,
        now: datetime,
        owner_kind: OwnerKind | None = None,
        owner_id: UUID | None = None,
    ) -> SignedDownloadPayload:
        asset_id, expires_unix, signature = parse_signed_download_token(token)
        asset = self.get(asset_id)
        if (
            owner_kind is not None
            and owner_id is not None
            and (asset.owner_kind != owner_kind or asset.owner_id != owner_id)
        ):
            raise MediaNotFoundError("physiognomy media asset not found")
        expected = self._signature(asset, expires_unix)
        if len(signature) != len(expected) or not hmac.compare_digest(signature, expected):
            raise SignedDownloadInvalidError("signed download token is invalid")
        current = _aware_utc(now)
        expires_at = datetime.fromtimestamp(expires_unix, tz=UTC)
        if expires_at <= current:
            raise SignedDownloadExpiredError("signed download token has expired")
        if asset.status != "ready" or asset.expires_at <= current:
            raise MediaNotReadyError("physiognomy media is no longer available")
        payload = self.store.read(asset.object_key)
        return SignedDownloadPayload(
            asset_id=asset.asset_id,
            content_type=asset.content_type,
            payload=payload,
        )

    def purge_expired_signed_downloads(self, *, now: datetime) -> tuple[str, ...]:
        current = _aware_utc(now)
        expired = tuple(
            token
            for token, expires_at in self._signed_downloads.items()
            if expires_at <= current
        )
        for token in expired:
            self._signed_downloads.pop(token, None)
        return expired

    def _signature(self, asset: PhysiognomyMediaAsset, expires_unix: int) -> str:
        message = (
            f"v1|{asset.asset_id}|{asset.owner_kind}|{asset.owner_id}|{expires_unix}"
        )
        return hmac.new(
            self._signing_key,
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _audit(self, event: MediaAuditEvent) -> None:
        if self.audit_sink is not None:
            self.audit_sink(event)


def parse_signed_download_token(token: str) -> tuple[str, int, str]:
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != "v1" or not parts[1] or not parts[3]:
        raise SignedDownloadInvalidError("signed download token is invalid")
    try:
        expires_unix = int(parts[2])
    except ValueError as error:
        raise SignedDownloadInvalidError("signed download token is invalid") from error
    return parts[1], expires_unix, parts[3]


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
    *,
    mode: ObservationMode,
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
    profile = _profile_for(mode, region)
    if profile is None or feature_kind not in profile["features"]:
        raise MediaValidationError("structured observation is outside the selected mode contract")
    if descriptor not in profile["descriptors"][region]:
        raise MediaValidationError("structured observation descriptor is not admitted")
    if visibility not in {"full", "partial"}:
        raise MediaQualityError("only visible or partially visible observations can be confirmed")
    uncertainty = _bounded_number(raw.get("uncertainty", 0), label="uncertainty")
    occlusion = _bounded_number(raw.get("occlusion", 0), label="occlusion")
    return region, feature_kind, descriptor, visibility, uncertainty, occlusion


def _profile_for(mode: ObservationMode, region: str) -> _ModeProfile | None:
    profiles = _MODE_PROFILES
    if mode == "combined":
        for candidate in _MODE_ORDER:
            profile = profiles[candidate]
            if region in profile["regions"]:
                return profile
        return None
    selected_profile = profiles.get(mode)
    if selected_profile is not None and region in selected_profile["regions"]:
        return selected_profile
    return None


def _taxonomy_for(mode: ObservationMode, region: str) -> str:
    profile = _profile_for(mode, region)
    if profile is None:
        raise MediaValidationError("structured observation region is not admitted")
    return str(profile["taxonomy"])


def _bounded_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MediaValidationError(f"observation {label} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise MediaValidationError(f"observation {label} must be in [0, 1]")
    return result
