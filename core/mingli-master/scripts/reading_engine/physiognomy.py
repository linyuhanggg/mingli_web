"""Bounded normalization for caller-transcribed visible observations.

The provider deliberately does not decode, fetch, inspect, compare, or identify
images.  Image-capable callers may supply a hash-bound neutral transcription;
this module validates its visibility, capture quality, revision lineage, and
source applicability without creating any unobserved or diagnostic feature.
"""

from __future__ import annotations

import copy
import base64
import binascii
import html
import hashlib
import math
import re
import unicodedata
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

import yaml

from . import evidence_rules
from .contracts import FactRef, canonical_digest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_TABLE_PATH = ROOT / "references/matrices/physiognomy-source-tables-v1.yaml"
SOURCE_TABLE_SHA256 = "e8c499b22fd15ba1e1b6b31d304b77891727c827682d8e58ebc95f7a2adad08d"
SOURCE_TABLE_SCHEMA = "mingli-physiognomy-source-tables-v1"
INPUT_SCHEMA_VERSION = "mingli-physiognomy-input-v1"
FACT_SCHEMA_VERSION = "mingli-physiognomy-facts-v1"
FACT_LAYER_STATUS = "observation_driven_physiognomy_facts"
FACT_LAYER_SCOPE = "caller_transcribed_visible_observations_only"
ADAPTER_VERSION = "1.1.0"
TABLE_PROFILE = "visible-observation-source-layering-v1"
VALIDATION_ATTESTATION = {
    "ok": True,
    "system": "physiognomy",
    "validator": "mingli-master.physiognomy.validate_fact_layer",
}
SOURCE_DEPENDENCIES = (
    "physiognomy.observation.image-quality-regions",
    "physiognomy.normalization.visible-only-features",
    "physiognomy.evidence.revision-and-source-conflict",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RAW_MEDIA_SCAN_MAX_CHARS = 1_000_000
PERCENT_DECODE_MAX_ROUNDS = 16
BASE64_CANDIDATE_RE = re.compile(r"(?<![A-Za-z0-9+/_-])[A-Za-z0-9+/_-]{12,}={0,2}(?![A-Za-z0-9+/_=-])")
FOLDED_BASE64_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9+/_-])"
    r"(?:[A-Za-z0-9+/_-][ \t\r\n]*){12,}"
    r"(?:=[ \t\r\n]*){0,2}"
    r"(?![A-Za-z0-9+/_=-])"
)
HTML_MARKUP_RE = re.compile(
    r"<!--|-->|<![A-Za-z]|<!\[|<\?|"
    r"</?[A-Za-z][A-Za-z0-9-]*"
    r"(?=[/>]|\s+(?:[A-Za-z_:]|/?>))",
    re.IGNORECASE | re.DOTALL,
)
MEDIA_PATH_EXTENSION_RE = re.compile(
    r"\.(?:png|jpe?g|gif|webp|heic|svg)"
    r"(?:\?[^\s'\"“”‘’()\[\]{}<>，。！？；：、]{0,4096})?"
    r"(?=$|[\s'\"“”‘’()\[\]{}<>，。！？；：、])",
    re.IGNORECASE,
)
CLEAR_FILE_LOCATOR_RE = re.compile(
    r"(?:^|[\s'\"“”‘’(\[<{，。！？；：、])(?:"
    r"file\s*:\s*/+"
    r"|~[\\/]"
    r"|[A-Za-z]:[\\/]"
    r"|\\\\[^\\/\s]+[\\/]"
    r"|/(?:[^/\s'\"“”‘’()\[\]{}<>，。！？；：、]+/)+"
    r"[^/\s'\"“”‘’()\[\]{}<>，。！？；：、]+"
    r")",
    re.IGNORECASE,
)


def _is_security_ignorable(character: str) -> bool:
    codepoint = ord(character)
    return (
        unicodedata.category(character) == "Cf"
        or codepoint == 0x034F
        or 0x115F <= codepoint <= 0x1160
        or 0x17B4 <= codepoint <= 0x17B5
        or 0x180B <= codepoint <= 0x180F
        or codepoint == 0x2065
        or codepoint == 0x3164
        or 0xFE00 <= codepoint <= 0xFE0F
        or codepoint == 0xFFA0
        or 0xFFF0 <= codepoint <= 0xFFF8
        or 0x1BCA0 <= codepoint <= 0x1BCA3
        or 0x1D173 <= codepoint <= 0x1D17A
        or 0xE0000 <= codepoint <= 0xE0FFF
    )


def _normalize_security_layer(value: str) -> str:
    rendered = unicodedata.normalize("NFKC", value)
    rendered = rendered.replace("⁄", "/").replace("∕", "/")
    return "".join(
        character
        for character in rendered
        if not _is_security_ignorable(character)
    )


def _canonical_security_text(value: str) -> str:
    rendered = _normalize_security_layer(value)
    if len(rendered) > RAW_MEDIA_SCAN_MAX_CHARS:
        return rendered
    for _ in range(PERCENT_DECODE_MAX_ROUNDS):
        decoded = _normalize_security_layer(
            html.unescape(urllib.parse.unquote(rendered))
        )
        if decoded == rendered:
            return rendered
        rendered = decoded
    if _normalize_security_layer(
        html.unescape(urllib.parse.unquote(rendered))
    ) != rendered:
        raise ValueError("security text exceeds percent-decoding limit")
    return rendered


def _markdown_pairs(value: str) -> dict[int, int]:
    pairs: dict[int, int] = {}
    stacks: dict[str, list[int]] = {"[": [], "(": []}
    closing_to_opening = {"]": "[", ")": "("}
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character in stacks:
            stacks[character].append(index)
            continue
        opening = closing_to_opening.get(character)
        if opening and stacks[opening]:
            pairs[stacks[opening].pop()] = index
    return pairs


def _markdown_visible_security_text(value: str) -> str:
    """Approximate CommonMark visible text for security scanning only."""

    pairs = _markdown_pairs(value)
    hidden_intervals: list[tuple[int, int]] = []
    for bracket_index, label_end in pairs.items():
        if value[bracket_index] != "[":
            continue
        cursor = label_end + 1
        while cursor < len(value) and value[cursor] in " \t":
            cursor += 1
        destination_end = pairs.get(cursor)
        if (
            destination_end is not None
            and value[cursor] in "(["
        ):
            hidden_intervals.append((cursor, destination_end))
    hidden_intervals.sort()
    merged: list[tuple[int, int]] = []
    for start, end in hidden_intervals:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    output: list[str] = []
    cursor = 0
    for start, end in merged:
        output.append(value[cursor:start])
        cursor = end + 1
    output.append(value[cursor:])
    rendered = "".join(output)
    rendered = re.sub(
        r"\\([\\`*_{}\[\]()#+\-.!~>])",
        r"\1",
        rendered,
    )
    rendered = re.sub(r"[`*~\[\]()#]", "", rendered)
    rendered = re.sub(r"(?m)^[ \t]{0,3}(?:#{1,6}|>)[ \t]*", "", rendered)
    return rendered


def _security_text_candidates(value: str) -> tuple[str, ...]:
    visible = _markdown_visible_security_text(value)
    aggressive = visible.replace("_", "")
    return tuple(dict.fromkeys((value, visible, aggressive)))


def _has_image_magic(decoded: bytes) -> bool:
    probe = decoded[:32].lstrip().lower()
    return (
        decoded.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a"))
        or decoded.startswith(b"RIFF") and decoded[8:12] == b"WEBP"
        or probe.startswith(b"<svg")
        or len(decoded) >= 12 and decoded[4:12] in {b"ftypheic", b"ftypheix", b"ftypavif"}
    )


def _looks_like_base64_image(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 12 or len(compact) % 4 == 1:
        return False
    padded = compact + "=" * (-len(compact) % 4)
    for altchars in (None, b"-_"):
        try:
            decoded = base64.b64decode(padded, altchars=altchars, validate=True)
        except (binascii.Error, ValueError):
            continue
        if _has_image_magic(decoded):
            return True
    return False


def _contains_base64_image(value: str) -> bool:
    if _looks_like_base64_image(value):
        return True
    return any(
        _looks_like_base64_image(match.group(0))
        for pattern in (BASE64_CANDIDATE_RE, FOLDED_BASE64_CANDIDATE_RE)
        for match in pattern.finditer(value)
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return value


def _identifier(value: Any, *, label: str, namespace: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    result = value.strip()
    if (
        len(result) < OPAQUE_IDENTIFIER_MIN_LENGTH
        or len(result) > 160
        or OPAQUE_IDENTIFIER_RE.fullmatch(result) is None
    ):
        raise ValueError(f"{label} is not a valid opaque identifier")
    if not result.startswith(f"{namespace}-"):
        raise ValueError(f"{label} is not in the required opaque identifier namespace")
    return result


def _number(value: Any, *, label: str, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{label} must be in [{minimum}, {maximum}]")
    return result


def _positive_integer(value: Any, *, label: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > maximum
    ):
        raise ValueError(
            f"{label} must be a positive integer no greater than {maximum}"
        )
    return value


def _assert_keys(
    value: Mapping[str, Any],
    *,
    allowed: Iterable[str],
    required: Iterable[str],
    label: str,
) -> None:
    allowed_set = set(allowed)
    required_set = set(required)
    unknown = sorted(set(value) - allowed_set)
    missing = sorted(required_set - set(value))
    if unknown:
        raise ValueError(f"{label} contains forbidden or unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{label} is missing required fields: {', '.join(missing)}")


@lru_cache(maxsize=1)
def source_table() -> dict[str, Any]:
    actual = _sha256(SOURCE_TABLE_PATH)
    if actual != SOURCE_TABLE_SHA256:
        raise RuntimeError(
            "Physiognomy source table hash mismatch: "
            f"expected {SOURCE_TABLE_SHA256}, got {actual}"
        )
    payload = yaml.safe_load(SOURCE_TABLE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Physiognomy source table must be a mapping")
    if payload.get("schema_version") != SOURCE_TABLE_SCHEMA:
        raise RuntimeError("unsupported Physiognomy source table schema")
    if payload.get("profile_id") != TABLE_PROFILE:
        raise RuntimeError("Physiognomy source table profile mismatch")
    profiles = payload.get("source_profiles")
    if not isinstance(profiles, dict) or set(profiles) != {
        "liuzhuang_xiangfa",
        "shenxiang_quanbian",
        "mayi_shenxiang",
    }:
        raise RuntimeError("Physiognomy source table must retain exactly three source layers")
    for profile in profiles.values():
        rules_path = ROOT / str(profile.get("release_rules_path") or "")
        expected = str(profile.get("release_rules_sha256") or "")
        if not rules_path.is_file() or _sha256(rules_path) != expected:
            raise RuntimeError("Physiognomy release source rule hash mismatch")
        if profile.get("verdict_prohibited") is not True:
            raise RuntimeError("Physiognomy source layers must prohibit verdict projection")
    activation = payload.get("source_rule_activation") or {}
    safe_ids = activation.get("safe_rule_ids") or []
    if not safe_ids or len(safe_ids) != len(set(safe_ids)):
        raise RuntimeError("Physiognomy safe source rule allowlist is invalid")
    if any(not str(item).startswith("physiognomy/") or "#" not in str(item) for item in safe_ids):
        raise RuntimeError("Physiognomy source rule ids must be pack-qualified")
    return payload


SAFE_SOURCE_RULE_IDS = tuple(source_table()["source_rule_activation"]["safe_rule_ids"])
OPAQUE_IDENTIFIER_MIN_LENGTH = int(
    source_table()["privacy_contract"]["opaque_identifier_min_length"]
)
OPAQUE_IDENTIFIER_RE = re.compile(
    str(source_table()["privacy_contract"]["opaque_identifier_pattern"])
)


def _selected_source_packs(
    table: Mapping[str, Any],
    profile_ids: Iterable[str],
) -> set[str]:
    profiles = table["source_profiles"]
    return {
        str(profiles[profile_id]["pack"])
        for profile_id in profile_ids
    }


def _filter_source_rule_ids(
    rule_ids: Iterable[Any],
    selected_packs: set[str],
) -> list[str]:
    return [
        str(rule_id)
        for rule_id in rule_ids
        if str(rule_id).split("#", 1)[0] in selected_packs
    ]


def _mode_contract(scope: str) -> dict[str, Any]:
    """Resolve the source-table contract for one observation mode.

    Face remains the original contract. Palm and posture deliberately expose
    only caller-transcribed visible morphology; they do not inherit face
    regions, color claims, or face-specific source terminology. Combined is a
    deterministic union of the three mode contracts and never becomes a new
    inference rule.
    """

    table = source_table()
    contract = table["observation_contract"]
    allowed_scopes = set(contract.get("allowed_scopes") or ("face",))
    if scope not in allowed_scopes:
        raise ValueError("Physiognomy observation_scope is unsupported")

    source_profiles = ["liuzhuang_xiangfa", "shenxiang_quanbian", "mayi_shenxiang"]
    selected_packs = _selected_source_packs(table, source_profiles)
    face_taxonomy = str(contract["taxonomies"][0])
    base: dict[str, Any] = {
        "accepted_source_types": list(contract["accepted_source_types"]),
        "taxonomies": list(contract["taxonomies"]),
        "allowed_regions": list(contract["allowed_regions"]),
        "allowed_feature_kinds": list(contract["allowed_feature_kinds"]),
        "capture_color_regions": list(contract["capture_color_regions"]),
        "descriptors": copy.deepcopy(contract["descriptors"]),
        "region_taxonomies": {
            str(region): face_taxonomy
            for region in contract["allowed_regions"]
        },
        "source_profiles": source_profiles,
        "baseline_rule_ids": _filter_source_rule_ids(
            table["source_rule_activation"].get("baseline_methodology") or (),
            selected_packs,
        ),
        "region_rule_ids": _filter_source_rule_ids(
            table["source_rule_activation"].get("any_active_visible_region") or (),
            selected_packs,
        ),
        "capture_color_rule_ids": _filter_source_rule_ids(
            table["source_rule_activation"].get("active_capture_color") or (),
            selected_packs,
        ),
    }
    if scope == "face":
        return base

    if scope == "combined":
        for mode in ("palm", "posture"):
            profile = _mode_contract(mode)
            base["taxonomies"].extend(profile["taxonomies"])
            base["allowed_regions"].extend(profile["allowed_regions"])
            base["allowed_feature_kinds"].extend(profile["allowed_feature_kinds"])
            base["capture_color_regions"].extend(profile["capture_color_regions"])
            base["source_profiles"].extend(profile["source_profiles"])
            base["region_taxonomies"].update(profile["region_taxonomies"])
            base["baseline_rule_ids"].extend(profile["baseline_rule_ids"])
            base["region_rule_ids"].extend(profile["region_rule_ids"])
            base["capture_color_rule_ids"].extend(profile["capture_color_rule_ids"])
            for feature_kind, regions in profile["descriptors"].items():
                base["descriptors"].setdefault(feature_kind, {}).update(
                    copy.deepcopy(regions)
                )
        for key in (
            "taxonomies",
            "allowed_regions",
            "allowed_feature_kinds",
            "capture_color_regions",
            "source_profiles",
            "baseline_rule_ids",
            "region_rule_ids",
            "capture_color_rule_ids",
        ):
            base[key] = list(dict.fromkeys(base[key]))
        return base

    profile = contract["mode_profiles"].get(scope)
    if not isinstance(profile, Mapping):
        raise RuntimeError(f"Physiognomy mode profile is missing: {scope}")
    mode_source_profiles = list(profile["source_profiles"])
    mode_selected_packs = _selected_source_packs(table, mode_source_profiles)
    mode_taxonomy = str(profile["taxonomies"][0])
    resolved = {
        "accepted_source_types": list(contract["accepted_source_types"]),
        "taxonomies": list(profile["taxonomies"]),
        "allowed_regions": list(profile["allowed_regions"]),
        "allowed_feature_kinds": list(profile["allowed_feature_kinds"]),
        "capture_color_regions": list(profile["capture_color_regions"]),
        "descriptors": copy.deepcopy(profile["descriptors"]),
        "region_taxonomies": {
            str(region): mode_taxonomy
            for region in profile["allowed_regions"]
        },
        "source_profiles": mode_source_profiles,
        "baseline_rule_ids": _filter_source_rule_ids(
            table["source_rule_activation"].get("baseline_methodology") or (),
            mode_selected_packs,
        ),
        "region_rule_ids": _filter_source_rule_ids(
            profile.get("active_source_rule_ids")
            or table["source_rule_activation"].get("any_active_visible_region")
            or (),
            mode_selected_packs,
        ),
        "capture_color_rule_ids": [],
    }
    return resolved


def _raw_media_key_paths(value: Any, *, path: str = "request") -> tuple[str, ...]:
    def key_token(raw: Any) -> str:
        return re.sub(
            r"[^a-z0-9]", "", _canonical_security_text(str(raw)).casefold()
        )

    forbidden = {
        key_token(item)
        for item in source_table()["observation_contract"]["forbidden_raw_media_fields"]
    }
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            try:
                normalized_key = key_token(key)
            except ValueError:
                found.append(child)
                continue
            if normalized_key in forbidden:
                found.append(child)
            found.extend(_raw_media_key_paths(item, path=child))
    elif isinstance(value, (list, tuple)):
        if (
            len(value) >= 3
            and all(
                isinstance(item, int)
                and not isinstance(item, bool)
                and 0 <= item <= 255
                for item in value
            )
            and _has_image_magic(bytes(value))
        ):
            found.append(path)
            return tuple(found)
        for index, item in enumerate(value):
            found.extend(_raw_media_key_paths(item, path=f"{path}[{index}]"))
    elif isinstance(value, (bytes, bytearray, memoryview)):
        found.append(path)
    elif isinstance(value, str):
        try:
            rendered = _canonical_security_text(value.strip())
        except ValueError:
            found.append(path)
            return tuple(found)
        candidates = _security_text_candidates(rendered)
        if (
            len(rendered) > RAW_MEDIA_SCAN_MAX_CHARS
            or HTML_MARKUP_RE.search(rendered)
            or any(
                re.search(
                    r"data\s*:\s*image|base64\s*,",
                    candidate,
                    re.IGNORECASE,
                )
                or re.search(
                    r"(?<![A-Za-z0-9+.-])"
                    r"(?:[A-Za-z][A-Za-z0-9+.-]{0,31}\s*://|(?:blob|cid)\s*:)",
                    candidate,
                    re.IGNORECASE,
                )
                or CLEAR_FILE_LOCATOR_RE.search(candidate)
                or re.search(r"<\s*svg\b", candidate, re.IGNORECASE)
                or MEDIA_PATH_EXTENSION_RE.search(candidate)
                or _contains_base64_image(candidate)
                for candidate in candidates
            )
        ):
            found.append(path)
    return tuple(found)


def validate_no_raw_media(request: Any) -> None:
    """Reject raw-media fields in any request section before persistence."""

    serializer = getattr(request, "to_dict", None)
    request_payload = serializer() if callable(serializer) else {
        "query": getattr(request, "query", None),
        "chart_data": getattr(request, "chart_data", {}),
        "metadata": getattr(request, "metadata", {}),
        "birth_data": getattr(request, "birth_data", {}),
        "goal": getattr(request, "goal", {}),
        "intent": getattr(request, "intent", {}),
        "transcribed_chart": getattr(request, "transcribed_chart", None),
    }
    raw_paths = _raw_media_key_paths(request_payload)
    if raw_paths:
        raise ValueError(
            "Physiognomy request contains forbidden raw media fields: "
            + ", ".join(raw_paths)
        )
    transcribed = str(getattr(request, "transcribed_chart", None) or "").strip()
    if re.search(r"data\s*:\s*image|base64\s*,", transcribed, re.IGNORECASE):
        raise ValueError("request transcribed_chart contains forbidden raw media")


def validate_request_envelope(
    request: Any,
    *,
    require_image_presence: bool = True,
) -> None:
    """Reject raw media and non-route chart fields before any persistence."""

    validate_no_raw_media(request)
    unused_context = {
        field: getattr(request, field, None)
        for field in (
            "reference_datetime",
            "timezone",
            "location",
            "event_datetime",
        )
        if getattr(request, field, None) is not None
    }
    if unused_context:
        raise ValueError(
            "Physiognomy request contains unused time or location fields: "
            + ", ".join(sorted(unused_context))
        )
    if getattr(request, "birth_data", None):
        raise ValueError("Physiognomy request must not contain birth_data")
    if getattr(request, "system_hint", None) is not None:
        raise ValueError("Physiognomy request must not contain a legacy system_hint")
    metadata = getattr(request, "metadata", None)
    if not isinstance(metadata, Mapping) or set(metadata) - {"root_query"}:
        raise ValueError("Physiognomy metadata contains unsupported fields")
    if "root_query" in metadata and not isinstance(metadata["root_query"], str):
        raise TypeError("Physiognomy metadata.root_query must be text")
    goal = getattr(request, "goal", None)
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
        raise ValueError("Physiognomy goal contains unsupported fields")
    list_goal_fields = allowed_goal_fields - {
        "requested_resolution",
        "calculation_object",
    }
    for field in list_goal_fields & set(goal):
        value = goal[field]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise TypeError(f"Physiognomy goal.{field} must be a text list")
    for field in {"requested_resolution", "calculation_object"} & set(goal):
        if not isinstance(goal[field], str):
            raise TypeError(f"Physiognomy goal.{field} must be text")
    intent = getattr(request, "intent", None)
    intent_fields = {
        "subject_refs",
        "calculation_object",
        "question_dimensions",
        "horizon",
        "requested_method",
        "requested_granularity",
        "continuity",
        "facts_present",
        "facts_corrected",
        "evidence_questions",
    }
    if not isinstance(intent, Mapping) or set(intent) != intent_fields:
        raise ValueError("Physiognomy intent must use the exact IntentFrame schema")
    subject_refs = intent.get("subject_refs")
    if not isinstance(subject_refs, list) or len(subject_refs) != 1:
        raise ValueError(
            "Physiognomy request subject binding requires exactly one opaque identifier"
        )
    _identifier(
        subject_refs[0],
        label="Physiognomy intent subject_ref",
        namespace="sid",
    )
    horizon = intent.get("horizon")
    continuity = intent.get("continuity")
    if not isinstance(horizon, Mapping) or set(horizon) != {"kind", "start", "end"}:
        raise ValueError("Physiognomy intent.horizon contains unsupported fields")
    if not isinstance(continuity, Mapping) or set(continuity) != {
        "reading_id",
        "same_subject",
        "same_event",
    }:
        raise ValueError("Physiognomy intent.continuity contains unsupported fields")
    chart_data = getattr(request, "chart_data", None)
    if not isinstance(chart_data, Mapping):
        raise TypeError("Physiognomy chart_data must be an object")
    extra_chart_fields = sorted(set(chart_data) - {"physiognomy_spec"})
    if extra_chart_fields:
        raise ValueError(
            "Physiognomy chart_data contains non-route fields: "
            + ", ".join(extra_chart_fields)
        )
    if str(getattr(request, "transcribed_chart", None) or "").strip():
        raise ValueError(
            "Physiognomy accepts only structured observations, not transcribed_chart"
        )
    spec = chart_data.get("physiognomy_spec")
    if not isinstance(spec, Mapping):
        return
    observations = spec.get("observations") or []
    if not isinstance(observations, list):
        return
    image_observation_present = any(
        isinstance(item, Mapping)
        and item.get("source_type") == "image_transcription"
        for item in observations
    )
    assets = spec.get("assets") or []
    if require_image_presence and (image_observation_present or bool(assets)) and getattr(
        request,
        "image_supplied",
        False,
    ) is not True:
        raise ValueError(
            "Physiognomy image transcription requires request image presence"
        )


def source_table_digest() -> str:
    source_table()
    return SOURCE_TABLE_SHA256


def _normalize_quality(raw: Any) -> dict[str, str]:
    quality = _mapping(raw, label="asset quality")
    required = {
        "lighting",
        "camera_angle",
        "focus",
        "resolution",
        "filtering",
        "color_fidelity",
    }
    _assert_keys(quality, allowed=required, required=required, label="asset quality")
    table = source_table()
    contract = table["quality_contract"]
    enums = {
        "lighting": set(contract["lighting"]),
        "camera_angle": set(table["visibility_contract"]["camera_angles"]),
        "focus": set(contract["focus"]),
        "resolution": set(contract["resolution"]),
        "filtering": set(contract["filtering"]),
        "color_fidelity": set(contract["color_fidelity"]),
    }
    normalized: dict[str, str] = {}
    for key, allowed in enums.items():
        value = str(quality.get(key) or "")
        if value not in allowed:
            raise ValueError(f"asset quality {key} has an unsupported value")
        normalized[key] = value
    return normalized


def _normalize_assets(
    raw_assets: Any,
    *,
    subject_ref: str,
    scope: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = _list(raw_assets, label="assets")
    normalized: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    capture_ids: set[str] = set()
    asset_hashes: set[str] = set()
    table = source_table()
    mode_contract = _mode_contract(scope)
    if scope != "face" and rows:
        raise ValueError(
            "non-face Physiognomy modes require caller-transcribed observations without image assets"
        )
    visibility = table["visibility_contract"]
    asset_contract = table["asset_contract"]
    allowed_regions = set(mode_contract["allowed_regions"])
    required = {
        "asset_id", "capture_id", "subject_ref", "media_type", "sha256",
        "byte_length", "pixel_width", "pixel_height", "pose_family",
        "visible_subject_sides", "framing", "supplied_visible_regions", "quality",
    }
    allowed = required | {"synthetic", "no_real_person"}
    for index, raw in enumerate(rows):
        asset = _mapping(raw, label=f"assets[{index}]")
        _assert_keys(asset, allowed=allowed, required=required, label=f"assets[{index}]")
        asset_id = _identifier(asset.get("asset_id"), label="asset_id", namespace="aid")
        if asset_id in by_id:
            raise ValueError("asset ids must be unique")
        capture_id = _identifier(asset.get("capture_id"), label="capture_id", namespace="cid")
        asset_subject = _identifier(
            asset.get("subject_ref"), label="asset subject_ref", namespace="sid"
        )
        if asset_subject != subject_ref:
            raise ValueError("asset subject_ref must match physiognomy subject_ref")
        media_type = str(asset.get("media_type") or "")
        if media_type not in {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}:
            raise ValueError("asset media_type must be an admitted image type")
        digest = str(asset.get("sha256") or "")
        if not SHA256_RE.fullmatch(digest):
            raise ValueError("asset sha256 must be lowercase hexadecimal")
        if capture_id in capture_ids or digest in asset_hashes:
            raise ValueError("asset capture/hash binding must be one-to-one")
        capture_ids.add(capture_id)
        asset_hashes.add(digest)
        pose = str(asset.get("pose_family") or "")
        side = str(asset.get("visible_subject_sides") or "")
        framing = str(asset.get("framing") or "")
        if pose not in set(visibility["pose_families"]):
            raise ValueError("asset pose_family is unsupported")
        if side not in set(visibility["visible_subject_sides"]):
            raise ValueError("asset visible_subject_sides is unsupported")
        if framing not in set(visibility["framing"]):
            raise ValueError("asset framing is unsupported")
        if pose == "left_profile" and side != "left":
            raise ValueError("left_profile must name the subject's visible left side")
        if pose == "right_profile" and side != "right":
            raise ValueError("right_profile must name the subject's visible right side")
        if pose == "three_quarter_left" and side != "left":
            raise ValueError(
                "three_quarter_left must name the subject's visible left side"
            )
        if pose == "three_quarter_right" and side != "right":
            raise ValueError(
                "three_quarter_right must name the subject's visible right side"
            )
        if pose == "frontal" and side != "bilateral":
            raise ValueError("frontal pose must declare bilateral subject sides")
        quality = _normalize_quality(asset.get("quality"))
        if quality["camera_angle"] not in set(visibility["pose_angle_compatibility"][pose]):
            raise ValueError("asset pose_family and camera angle are inconsistent")
        supplied = _list(asset.get("supplied_visible_regions"), label="supplied_visible_regions")
        if len(supplied) != len(set(supplied)) or any(item not in allowed_regions for item in supplied):
            raise ValueError("supplied_visible_regions contains duplicate or unsupported regions")
        ceiling = set(visibility["pose_region_ceiling"][pose])
        if not set(supplied) <= ceiling:
            raise ValueError("supplied visible region exceeds pose visibility coverage")
        framing_ceiling = set(visibility["framing_region_ceiling"][framing])
        if not set(supplied) <= framing_ceiling:
            raise ValueError(
                "supplied visible region exceeds framing visibility coverage"
            )
        side_ceiling = set(visibility["subject_side_region_ceiling"][side])
        if pose == "detail" and not set(supplied) <= side_ceiling:
            raise ValueError(
                "supplied visible region exceeds declared subject-side visibility"
            )
        item = {
            "asset_id": asset_id,
            "capture_id": capture_id,
            "subject_ref": asset_subject,
            "media_type": media_type,
            "sha256": digest,
            "byte_length": _positive_integer(
                asset.get("byte_length"),
                label="asset byte_length",
                maximum=int(asset_contract["maximum_byte_length"]),
            ),
            "pixel_width": _positive_integer(
                asset.get("pixel_width"),
                label="asset pixel_width",
                maximum=int(asset_contract["maximum_pixel_axis"]),
            ),
            "pixel_height": _positive_integer(
                asset.get("pixel_height"),
                label="asset pixel_height",
                maximum=int(asset_contract["maximum_pixel_axis"]),
            ),
            "pose_family": pose,
            "visible_subject_sides": side,
            "framing": framing,
            "supplied_visible_regions": list(supplied),
            "quality": quality,
        }
        if "synthetic" in asset:
            if not isinstance(asset["synthetic"], bool):
                raise TypeError("asset synthetic must be boolean")
            item["synthetic"] = asset["synthetic"]
        if "no_real_person" in asset:
            if not isinstance(asset["no_real_person"], bool):
                raise TypeError("asset no_real_person must be boolean")
            item["no_real_person"] = asset["no_real_person"]
        normalized.append(item)
        by_id[asset_id] = item
    return normalized, by_id


def _normalize_targets(
    raw_targets: Any,
    *,
    scope: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = _list(raw_targets, label="requested_targets")
    normalized: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    semantic_keys: set[tuple[str, str, str]] = set()
    contract = _mode_contract(scope)
    allowed_regions = set(contract["allowed_regions"])
    allowed_kinds = set(contract["allowed_feature_kinds"])
    required = {"target_id", "taxonomy", "region", "feature_kind", "required"}
    for index, raw in enumerate(rows):
        target = _mapping(raw, label=f"requested_targets[{index}]")
        _assert_keys(target, allowed=required, required=required, label=f"requested_targets[{index}]")
        target_id = _identifier(target.get("target_id"), label="target_id", namespace="tid")
        if target_id in by_id:
            raise ValueError("target ids must be unique")
        taxonomy = str(target.get("taxonomy") or "")
        region = str(target.get("region") or "")
        feature_kind = str(target.get("feature_kind") or "")
        required_flag = target.get("required")
        if taxonomy not in set(contract["taxonomies"]):
            raise ValueError("target taxonomy is unsupported")
        if region not in allowed_regions:
            raise ValueError("target region is unsupported")
        if taxonomy != contract["region_taxonomies"].get(region):
            raise ValueError("target taxonomy does not match its region")
        if feature_kind not in allowed_kinds:
            raise ValueError("target feature_kind is unsupported")
        if feature_kind == "capture_color" and region not in set(contract["capture_color_regions"]):
            raise ValueError("capture_color is only admitted for configured regions")
        semantic_key = (taxonomy, region, feature_kind)
        if semantic_key in semantic_keys:
            raise ValueError(
                "requested targets contain a duplicate semantic target"
            )
        semantic_keys.add(semantic_key)
        if not isinstance(required_flag, bool):
            raise TypeError("target required must be boolean")
        item = {
            "target_id": target_id,
            "taxonomy": taxonomy,
            "region": region,
            "feature_kind": feature_kind,
            "required": required_flag,
        }
        normalized.append(item)
        by_id[target_id] = item
    return normalized, by_id


def _normalize_anchor(raw: Any) -> dict[str, Any]:
    anchor = _mapping(raw, label="region_anchor")
    required = {"kind", "x", "y", "width", "height"}
    _assert_keys(anchor, allowed=required, required=required, label="region_anchor")
    if anchor.get("kind") != "normalized_bbox":
        raise ValueError("region_anchor kind must be normalized_bbox")
    x = _number(anchor.get("x"), label="region_anchor.x")
    y = _number(anchor.get("y"), label="region_anchor.y")
    width = _number(anchor.get("width"), label="region_anchor.width")
    height = _number(anchor.get("height"), label="region_anchor.height")
    if width <= 0.0 or height <= 0.0 or x + width > 1.0 or y + height > 1.0:
        raise ValueError("region_anchor bbox must have positive in-bounds coverage")
    return {"kind": "normalized_bbox", "x": x, "y": y, "width": width, "height": height}


def _normalize_text_quality(raw: Any) -> dict[str, str]:
    quality = _mapping(raw, label="non-image observation quality")
    expected = dict(source_table()["quality_contract"]["non_image_quality"])
    _assert_keys(quality, allowed=expected, required=expected, label="non-image observation quality")
    if dict(quality) != expected:
        raise ValueError("non-image observation quality must use the fixed sentinels")
    return expected


def _observation_quality_status(observation: Mapping[str, Any], asset: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    table = source_table()["quality_contract"]
    if float(observation["occlusion"]) > float(table["maximum_occlusion_inclusive"]):
        reasons.append("occlusion_above_threshold")
    if float(observation["uncertainty"]) > float(table["maximum_uncertainty_inclusive"]):
        reasons.append("uncertainty_above_threshold")
    if observation["visibility"] in {"not_visible", "uncertain"}:
        reasons.append(f"visibility_{observation['visibility']}")
    if asset is None:
        return not reasons, reasons
    quality = asset["quality"]
    feature_kind = str(observation["feature_kind"])
    policy = table[feature_kind]
    if feature_kind == "visible_morphology":
        for field in ("lighting", "focus", "resolution", "filtering"):
            if quality[field] in set(policy[f"disallowed_{field}"]):
                reasons.append(f"{field}_{quality[field]}")
    else:
        checks = {
            "allowed_regions": observation["region"],
            "allowed_lighting": quality["lighting"],
            "allowed_camera_angles": quality["camera_angle"],
            "allowed_focus": quality["focus"],
            "allowed_resolution": quality["resolution"],
            "allowed_filtering": quality["filtering"],
            "allowed_color_fidelity": quality["color_fidelity"],
        }
        for key, value in checks.items():
            if value not in set(policy[key]):
                reasons.append(f"{key.removeprefix('allowed_')}_{value}")
    return not reasons, reasons


def _normalize_observations(
    raw_observations: Any,
    *,
    assets: Mapping[str, dict[str, Any]],
    targets: Mapping[str, dict[str, Any]],
    scope: str,
) -> list[dict[str, Any]]:
    rows = _list(raw_observations, label="observations")
    normalized: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    contract = _mode_contract(scope)
    descriptors = contract["descriptors"]
    allowed_source_types = set(contract["accepted_source_types"])
    common_required = {
        "observation_id", "target_id", "source_type", "region", "feature_kind",
        "visibility", "value", "occlusion", "uncertainty",
    }
    for index, raw in enumerate(rows):
        observation = _mapping(raw, label=f"observations[{index}]")
        source_type = str(observation.get("source_type") or "")
        if source_type not in allowed_source_types:
            raise ValueError("observation source_type is unsupported")
        image_fields = {"asset_id", "asset_sha256", "region_anchor"}
        text_fields = {"source_ref", "quality"}
        if source_type == "image_transcription":
            provenance_fields = image_fields | {
                "transcription_actor",
                "provider_performed_vision",
            }
        elif source_type in {"user_text", "user_file"}:
            provenance_fields = text_fields
        elif "asset_id" in observation:
            provenance_fields = image_fields | {"supersedes_observation_id"}
        else:
            provenance_fields = text_fields | {"supersedes_observation_id"}
        _assert_keys(
            observation,
            allowed=common_required | provenance_fields,
            required=common_required | provenance_fields,
            label=f"observations[{index}]",
        )
        observation_id = _identifier(
            observation.get("observation_id"), label="observation_id", namespace="oid"
        )
        if observation_id in identifiers:
            raise ValueError("observation ids must be unique")
        identifiers.add(observation_id)
        target_id = _identifier(
            observation.get("target_id"), label="observation target_id", namespace="tid"
        )
        target = targets.get(target_id)
        if target is None:
            raise ValueError("observation target_id does not identify a requested target")
        region = str(observation.get("region") or "")
        feature_kind = str(observation.get("feature_kind") or "")
        if region != target["region"] or feature_kind != target["feature_kind"]:
            raise ValueError("observation region and feature must match its requested target")
        if feature_kind == "capture_color" and source_type in {
            "user_text",
            "user_file",
        }:
            raise ValueError(
                "capture_color requires calibrated image-bound provenance"
            )
        if (
            feature_kind == "capture_color"
            and source_type == "user_correction"
            and "asset_id" not in observation
        ):
            raise ValueError(
                "capture_color correction requires calibrated image-bound provenance"
            )
        visibility = str(observation.get("visibility") or "")
        if visibility not in {"full", "partial", "not_visible", "uncertain"}:
            raise ValueError("observation visibility is unsupported")
        raw_value = observation.get("value")
        descriptor: str | None = None
        if visibility in {"full", "partial"}:
            value = _mapping(raw_value, label="observation value")
            _assert_keys(value, allowed={"descriptor"}, required={"descriptor"}, label="observation value")
            descriptor = str(value.get("descriptor") or "")
            admitted_descriptors = (
                descriptors.get(feature_kind, {}).get(region, [])
                if isinstance(descriptors, Mapping)
                else []
            )
            if descriptor not in set(admitted_descriptors):
                raise ValueError(
                    "observation descriptor is not admitted for its feature kind"
                )
        elif raw_value is not None:
            raise ValueError("not-visible or uncertain observations must have null value")
        item: dict[str, Any] = {
            "observation_id": observation_id,
            "target_id": target_id,
            "source_type": source_type,
            "region": region,
            "feature_kind": feature_kind,
            "visibility": visibility,
            "value": None if descriptor is None else {"descriptor": descriptor},
            "occlusion": _number(observation.get("occlusion"), label="observation occlusion"),
            "uncertainty": _number(observation.get("uncertainty"), label="observation uncertainty"),
        }
        if source_type in {"image_transcription", "user_correction"} and "asset_id" in observation:
            asset_id = _identifier(
                observation.get("asset_id"), label="observation asset_id", namespace="aid"
            )
            asset = assets.get(asset_id)
            if asset is None:
                raise ValueError("observation asset_id does not identify a supplied asset")
            asset_sha = str(observation.get("asset_sha256") or "")
            if asset_sha != asset["sha256"]:
                raise ValueError("observation asset hash does not match the supplied asset")
            if region not in set(asset["supplied_visible_regions"]):
                raise ValueError("observation region is not visible in asset coverage")
            item.update(
                {
                    "asset_id": asset_id,
                    "asset_sha256": asset_sha,
                    "capture_id": asset["capture_id"],
                    "region_anchor": _normalize_anchor(observation.get("region_anchor")),
                }
            )
            anchor = item["region_anchor"]
            minimum_pixels = float(
                source_table()["visibility_contract"][
                    "minimum_region_anchor_pixels_per_axis"
                ]
            )
            if (
                float(anchor["width"]) * int(asset["pixel_width"]) < minimum_pixels
                or float(anchor["height"]) * int(asset["pixel_height"]) < minimum_pixels
            ):
                raise ValueError(
                    "region anchor must cover at least one source pixel per axis"
                )
            admitted_poses = (
                source_table()["visibility_contract"]
                .get("descriptor_pose_compatibility", {})
                .get(str(descriptor), [])
            )
            if admitted_poses and asset["pose_family"] not in set(admitted_poses):
                raise ValueError(
                    "observation descriptor is not admitted for this image pose or view"
                )
            context = (
                source_table()["visibility_contract"]
                .get("descriptor_context_requirements", {})
                .get(str(descriptor), {})
            )
            if context:
                if asset["framing"] not in set(context.get("allowed_framings") or ()):
                    raise ValueError(
                        "observation descriptor lacks the required image framing context"
                    )
                required_regions = set(context.get("required_regions") or ())
                required_regions.update(
                    (context.get("required_regions_by_observed_region") or {}).get(
                        region,
                        (),
                    )
                )
                if not required_regions <= set(asset["supplied_visible_regions"]):
                    raise ValueError(
                        "observation descriptor lacks required visible comparison context"
                    )
            if source_type == "image_transcription":
                if observation.get("transcription_actor") != "current_vision_capable_caller":
                    raise ValueError("image transcription requires the current vision-capable caller")
                if observation.get("provider_performed_vision") is not False:
                    raise ValueError("provider_performed_vision must be false")
                item["transcription_actor"] = "current_vision_capable_caller"
                item["provider_performed_vision"] = False
        elif source_type == "image_transcription":
            raise ValueError("image transcription requires asset hash and region anchor")
        else:
            source_ref = _identifier(
                observation.get("source_ref"), label="observation source_ref", namespace="rid"
            )
            item["source_ref"] = source_ref
            item["quality"] = _normalize_text_quality(observation.get("quality"))
        supersedes = observation.get("supersedes_observation_id")
        if source_type == "user_correction":
            item["supersedes_observation_id"] = _identifier(
                supersedes, label="supersedes_observation_id", namespace="oid"
            )
        elif supersedes is not None:
            raise ValueError("only a user_correction may supersede an observation")
        asset = assets.get(str(item.get("asset_id") or ""))
        eligible, reasons = _observation_quality_status(item, asset)
        item["quality_eligible"] = eligible
        item["quality_reasons"] = reasons
        normalized.append(item)

    by_id = {item["observation_id"]: item for item in normalized}
    successors: dict[str, str] = {}
    position = {item["observation_id"]: index for index, item in enumerate(normalized)}
    for item in normalized:
        parent_id = item.get("supersedes_observation_id")
        if not parent_id:
            continue
        parent = by_id.get(str(parent_id))
        if parent is None:
            raise ValueError("user correction supersedes an unknown observation")
        if position[str(parent_id)] >= position[item["observation_id"]]:
            raise ValueError("user correction lineage must be acyclic and forward-only")
        if parent_id in successors:
            raise ValueError("an observation may have only one correction successor")
        for field in ("target_id", "region", "feature_kind"):
            if item.get(field) != parent.get(field):
                raise ValueError(
                    "user correction must keep target, region, and feature"
                )
        parent_is_image = bool(parent.get("asset_id"))
        item_is_image = bool(item.get("asset_id"))
        if parent_is_image != item_is_image:
            raise ValueError(
                "user correction must keep the original provenance medium"
            )
        provenance_fields = (
            ("asset_id", "asset_sha256", "capture_id")
            if parent_is_image
            else ("source_ref",)
        )
        for field in provenance_fields:
            if item.get(field) != parent.get(field):
                raise ValueError(
                    "user correction must keep original provenance identity"
                )
        successors[str(parent_id)] = item["observation_id"]
    return normalized


def _source_layers(scope: str) -> list[dict[str, Any]]:
    table = source_table()
    profiles = table["source_profiles"]
    selected_profiles = set(_mode_contract(scope)["source_profiles"])
    return [
        {
            "pack": profile["pack"],
            "title": profile["title"],
            "source_layer": profile["source_layer"],
            "evidence_role": profile["evidence_role"],
            "edition_caveat": profile.get("edition_caveat"),
            "verdict_prohibited": True,
        }
        for source_layer in table["source_layer_contract"]["priority_order"]
        for profile_id, profile in profiles.items()
        if profile_id in selected_profiles
        and str(profile["source_layer"]) == str(source_layer)
    ]


def _build_fact_layer(spec: Mapping[str, Any]) -> dict[str, Any]:
    source_table()
    spec = _mapping(spec, label="physiognomy_spec")
    root_allowed = {
        "schema_version", "observation_scope", "subject_ref", "requested_targets",
        "assets", "observations", "confirmed_observation_ids",
        "comparison_relations", "source_layer_policy",
    }
    _assert_keys(
        spec,
        allowed=root_allowed,
        required=root_allowed,
        label="physiognomy_spec",
    )
    if spec.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError("unsupported Physiognomy input schema")
    scope = str(spec.get("observation_scope") or "")
    mode_contract = _mode_contract(scope)
    if spec.get("source_layer_policy") != "terminology_and_methodology_only":
        raise ValueError("Physiognomy source layer policy must prohibit subject verdicts")
    subject_ref = _identifier(spec.get("subject_ref"), label="subject_ref", namespace="sid")
    targets, target_by_id = _normalize_targets(spec.get("requested_targets"), scope=scope)
    assets, asset_by_id = _normalize_assets(
        spec.get("assets"), subject_ref=subject_ref, scope=scope
    )
    observations = _normalize_observations(
        spec.get("observations"),
        assets=asset_by_id,
        targets=target_by_id,
        scope=scope,
    )

    confirmed = _list(spec.get("confirmed_observation_ids"), label="confirmed_observation_ids")
    confirmed_ids = [
        _identifier(item, label="confirmed_observation_id", namespace="oid")
        for item in confirmed
    ]
    if len(confirmed_ids) != len(set(confirmed_ids)):
        raise ValueError("confirmed observation ids must be unique")
    known_ids = {item["observation_id"] for item in observations}
    if not set(confirmed_ids) <= known_ids:
        raise ValueError("confirmed observation id is unknown")
    comparisons = _list(spec.get("comparison_relations"), label="comparison_relations")
    if comparisons:
        for row in comparisons:
            relation = _mapping(row, label="comparison relation")
            required = {"relation", "target_id", "observation_ids"}
            _assert_keys(relation, allowed=required, required=required, label="comparison relation")
            if relation.get("relation") != "same_target_user_confirmed":
                raise ValueError("unsupported comparison relation")
            if relation.get("target_id") not in target_by_id:
                raise ValueError("comparison relation target is unknown")
            relation_ids = [
                _identifier(item, label="comparison observation_id", namespace="oid")
                for item in _list(
                    relation.get("observation_ids"),
                    label="comparison observation_ids",
                )
            ]
            if (
                len(relation_ids) < 2
                or len(relation_ids) != len(set(relation_ids))
                or not set(relation_ids) <= known_ids
            ):
                raise ValueError("comparison relation requires known observations")
            related = [
                next(
                    item
                    for item in observations
                    if item["observation_id"] == observation_id
                )
                for observation_id in relation_ids
            ]
            if any(
                item["target_id"] != relation["target_id"]
                for item in related
            ):
                raise ValueError(
                    "comparison relation observations must share its target"
                )
            scopes = {
                str(item.get("capture_id") or item.get("source_ref") or "")
                for item in related
            }
            if len(scopes) < 2:
                raise ValueError(
                    "comparison relation requires distinct provenance scopes"
                )

    superseded = {
        str(item["supersedes_observation_id"])
        for item in observations
        if item.get("supersedes_observation_id")
    }
    leaves = [item for item in observations if item["observation_id"] not in superseded]
    candidate_rows = [item for item in leaves if item["quality_eligible"]]
    conflicts: list[dict[str, Any]] = []
    conflict_ids: set[str] = set()
    unresolved_conflict_ids: set[str] = set()
    confirmed_set = set(confirmed_ids)
    all_by_capture_target: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in leaves:
        capture_key = str(
            item.get("capture_id") or f"nonimage:{item.get('source_ref')}"
        )
        all_by_capture_target.setdefault(
            (item["target_id"], capture_key),
            [],
        ).append(item)
    for (target_id, _), group in sorted(all_by_capture_target.items()):
        visible_rows = [
            item for item in group if item["visibility"] in {"full", "partial"}
        ]
        unavailable_rows = [
            item
            for item in group
            if item["visibility"] in {"not_visible", "uncertain"}
        ]
        if not visible_rows or not unavailable_rows:
            continue
        selected = [
            item for item in group if item["observation_id"] in confirmed_set
        ]
        resolution = selected[0]["observation_id"] if len(selected) == 1 else None
        conflict_ids.update(
            item["observation_id"]
            for item in group
            if resolution != item["observation_id"]
        )
        if resolution is None:
            unresolved_conflict_ids.update(
                item["observation_id"] for item in group
            )
        conflicts.append(
            {
                "code": "same_capture_contradictory_visibility",
                "target_id": target_id,
                "capture_scope": "same_capture",
                "observation_count": len(group),
                "resolved_by_observation_id": resolution,
                "blocking": resolution is None,
            }
        )
    by_capture_target: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in candidate_rows:
        capture_key = str(item.get("capture_id") or f"nonimage:{item.get('source_ref')}")
        by_capture_target.setdefault((item["target_id"], capture_key), []).append(item)
    for (target_id, capture_key), group in sorted(by_capture_target.items()):
        descriptors = {
            str((item.get("value") or {}).get("descriptor"))
            for item in group
            if item.get("value")
        }
        if len(descriptors) <= 1:
            continue
        selected = [item for item in group if item["observation_id"] in confirmed_set]
        if len(selected) == 1:
            conflict_ids.update(
                item["observation_id"] for item in group if item is not selected[0]
            )
            resolution = selected[0]["observation_id"]
        else:
            conflict_ids.update(item["observation_id"] for item in group)
            unresolved_conflict_ids.update(
                item["observation_id"] for item in group
            )
            resolution = None
        conflicts.append(
            {
                "code": "same_capture_contradictory_descriptors",
                "target_id": target_id,
                "capture_scope": "same_capture",
                "observation_count": len(group),
                "resolved_by_observation_id": resolution,
                "blocking": resolution is None,
            }
        )
    active = [item for item in candidate_rows if item["observation_id"] not in conflict_ids]

    cross_capture: list[dict[str, Any]] = []
    by_target: dict[str, list[dict[str, Any]]] = {}
    for item in active:
        by_target.setdefault(item["target_id"], []).append(item)
    for target_id, group in sorted(by_target.items()):
        captures = {str(item.get("capture_id") or item.get("source_ref")) for item in group}
        descriptors = {str((item.get("value") or {}).get("descriptor")) for item in group}
        if len(captures) > 1 and len(descriptors) > 1:
            cross_capture.append(
                {
                    "code": "different_capture_or_lighting_kept_separate",
                    "target_id": target_id,
                    "capture_count": len(captures),
                    "descriptor_count": len(descriptors),
                    "auto_equivalent": False,
                }
            )

    missing_targets: list[dict[str, Any]] = []
    uncertainties: list[dict[str, Any]] = []
    critical_missing: list[str] = []
    active_target_ids = {item["target_id"] for item in active}
    for item in leaves:
        if (
            item["observation_id"] in conflict_ids
            and item["observation_id"] not in unresolved_conflict_ids
        ):
            continue
        if not item["quality_eligible"]:
            uncertainties.append(
                {
                    "target_id": item["target_id"],
                    "region": item["region"],
                    "reason_codes": list(item["quality_reasons"]),
                }
            )
    unresolved_target_ids = {
        str(row["target_id"])
        for row in conflicts
        if row["blocking"]
    }
    effective_leaves_by_target: dict[str, list[dict[str, Any]]] = {}
    for item in leaves:
        if item["observation_id"] not in conflict_ids:
            effective_leaves_by_target.setdefault(
                str(item["target_id"]), []
            ).append(item)
    for target in targets:
        if (
            target["target_id"] in active_target_ids
            and target["target_id"] not in unresolved_target_ids
        ):
            continue
        target_leaves = effective_leaves_by_target.get(target["target_id"], [])
        visible_in_any = any(
            target["region"] in set(asset["supplied_visible_regions"])
            for asset in assets
        )
        unresolved_conflict = any(
            row["target_id"] == target["target_id"] and row["blocking"]
            for row in conflicts
        )
        if unresolved_conflict:
            reason = "unresolved_or_low_quality_observation"
            code = f"observation_resolution:{target['target_id']}"
        elif target_leaves:
            if all(item["visibility"] == "not_visible" for item in target_leaves):
                reason = "not_visible_in_supplied_view"
                code = f"visible_observation:{target['target_id']}"
            else:
                reason = "unresolved_or_low_quality_observation"
                code = f"observation_resolution:{target['target_id']}"
        elif not visible_in_any and assets:
            reason = "not_visible_in_supplied_view"
            code = f"visible_observation:{target['target_id']}"
        else:
            reason = "no_supplied_observation"
            code = f"visible_observation:{target['target_id']}"
        missing_targets.append(
            {
                "target_id": target["target_id"],
                "region": target["region"],
                "feature_kind": target["feature_kind"],
                "required": target["required"],
                "reason": reason,
            }
        )
        if target["required"]:
            critical_missing.append(code)
    if not targets:
        critical_missing.append("requested_targets")

    active_rule_ids: list[str] = []
    if active:
        active_rule_ids.extend(mode_contract["baseline_rule_ids"])
        active_rule_ids.extend(mode_contract["region_rule_ids"])
    if any(item["feature_kind"] == "capture_color" for item in active):
        active_rule_ids.extend(mode_contract["capture_color_rule_ids"])
    active_rule_ids = sorted(set(active_rule_ids))
    if not set(active_rule_ids) <= set(SAFE_SOURCE_RULE_IDS):
        raise RuntimeError("Physiognomy source activation escaped its safe allowlist")

    selected_packs = _selected_source_packs(
        source_table(), mode_contract["source_profiles"]
    )
    active_rule_packs = {
        str(rule_id).split("#", 1)[0]
        for rule_id in active_rule_ids
    }
    if not active_rule_packs <= selected_packs:
        raise RuntimeError(
            "Physiognomy source activation escaped the selected source layers"
        )

    normalized_visible = [
        {
            "region": item["region"],
            "feature_kind": item["feature_kind"],
            "descriptor": item["value"]["descriptor"],
            "visibility": item["visibility"],
            "quality_status": "eligible",
            "quality": copy.deepcopy(
                (
                    asset_by_id[str(item.get("asset_id"))]["quality"]
                    if item.get("asset_id")
                    else item["quality"]
                )
            ),
            "occlusion": item["occlusion"],
            "uncertainty": item["uncertainty"],
            "capture_scope": "asset_scoped" if item.get("asset_id") else "caller_text_scoped",
        }
        for item in active
    ]
    accepted_observation_fact_keys = sorted(
        {
            f"{item['feature_kind']}|{item['region']}"
            for item in active
        }
    )
    source_layers = _source_layers(scope)
    source_disagreements = [
        disagreement
        for disagreement in source_table()["source_layer_contract"]["disagreements"]
        if all(
            str(source) in selected_packs
            for source in disagreement.get("sources") or ()
        )
    ]
    normalized_spec = copy.deepcopy(dict(spec))
    payload: dict[str, Any] = {
        "schema_version": FACT_SCHEMA_VERSION,
        "system": "physiognomy",
        "fact_layer_status": FACT_LAYER_STATUS,
        "fact_layer_scope": FACT_LAYER_SCOPE,
        "adapter": {
            "name": "mingli-master.physiognomy",
            "version": ADAPTER_VERSION,
            "rule_profile": TABLE_PROFILE,
            "generated_at": "deterministic-visible-observation-normalization",
        },
        "source_table": {
            "path": "references/matrices/physiognomy-source-tables-v1.yaml",
            "sha256": SOURCE_TABLE_SHA256,
            "profile_id": TABLE_PROFILE,
        },
        "input": {
            "physiognomy_spec": normalized_spec,
            "input_digest": canonical_digest(normalized_spec),
        },
        "calendar_normalization": {
            "status": "not_applicable",
            "reason": "capture_bound_visible_observation_without_time_calculation",
        },
        "observation_provenance": {
            "subject_ref": subject_ref,
            "assets": [
                {
                    "asset_id": item["asset_id"],
                    "capture_id": item["capture_id"],
                    "sha256": item["sha256"],
                    "pose_family": item["pose_family"],
                    "framing": item["framing"],
                    "quality": copy.deepcopy(item["quality"]),
                }
                for item in assets
            ],
            "observation_ids": [item["observation_id"] for item in observations],
            "source_types": sorted({item["source_type"] for item in observations}),
            "provider_performed_vision": False,
            "identity_verified": False,
            "raw_media_retained": False,
        },
        "output": {
            "observation_scope": scope,
            "requested_targets": copy.deepcopy(targets),
            "normalized_visible_observations": normalized_visible,
            "accepted_observation_fact_keys": accepted_observation_fact_keys,
            "active_observation_ids": [item["observation_id"] for item in active],
            "superseded_observation_ids": sorted(superseded),
            "observation_records": copy.deepcopy(observations),
            "missing_targets": missing_targets,
            "observation_conflicts": conflicts,
            "cross_capture_variations": cross_capture,
            "uncertainties": uncertainties,
            "source_layers": source_layers,
            "source_disagreements": source_disagreements,
            "active_source_rule_ids": active_rule_ids,
            "critical_missing": list(dict.fromkeys(critical_missing)),
            "safety_boundaries": {
                "visible_observation_only": True,
                "provider_performed_vision": False,
                "no_biometric_or_identity_inference": True,
                "no_health_personality_wealth_lifespan_or_protected_attribute_inference": True,
                "historical_terminology_is_not_subject_verdict": True,
            },
        },
        "source_dependency_ids": list(SOURCE_DEPENDENCIES),
        "trace": [
            "validated caller-transcribed visible observations without image decoding",
            "intersected pose ceiling, supplied coverage, and explicit region anchor",
            "kept captures and lighting conditions separate without equivalence inference",
            "retained source layers and disagreements without verdict projection",
        ],
    }
    payload["output"]["source_conditioned_patterns"] = _source_conditioned_patterns(
        {
            "fact_layer_status": payload["fact_layer_status"],
            "output": {
                "active_source_rule_ids": active_rule_ids,
                "accepted_observation_fact_keys": accepted_observation_fact_keys,
            },
        }
    )
    payload["fact_digest"] = fact_digest(payload)
    return payload


def fact_digest(payload: Mapping[str, Any]) -> str:
    normalized = copy.deepcopy(dict(payload))
    normalized.pop("fact_digest", None)
    normalized.pop("validation", None)
    return canonical_digest(normalized)


def build_fact_layer(spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = _build_fact_layer(spec)
    payload["validation"] = copy.deepcopy(VALIDATION_ATTESTATION)
    report = validate_fact_layer(payload)
    if not report["ok"]:
        raise RuntimeError(
            "Physiognomy fact validation failed: " + ", ".join(report["codes"])
        )
    return payload


def required_intake_facts(spec: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(item) for item in _build_fact_layer(spec)["output"]["critical_missing"])


def validate_fact_layer(payload: Mapping[str, Any]) -> dict[str, Any]:
    codes: list[str] = []
    if not isinstance(payload, Mapping):
        return {"ok": False, "system": "physiognomy", "codes": ["physiognomy_payload_not_object"]}
    if payload.get("schema_version") != FACT_SCHEMA_VERSION:
        codes.append("physiognomy_schema_mismatch")
    if payload.get("system") != "physiognomy":
        codes.append("physiognomy_system_mismatch")
    if payload.get("fact_layer_status") != FACT_LAYER_STATUS:
        codes.append("physiognomy_fact_status_mismatch")
    if payload.get("validation") != VALIDATION_ATTESTATION:
        codes.append("physiognomy_validation_attestation_mismatch")
    if (payload.get("observation_provenance") or {}).get("provider_performed_vision") is not False:
        codes.append("physiognomy_provider_vision_forbidden")
    if payload.get("fact_digest") != fact_digest(payload):
        codes.append("physiognomy_fact_digest_mismatch")
    output = payload.get("output")
    if not isinstance(output, Mapping):
        codes.append("physiognomy_output_missing")
    else:
        active_ids = output.get("active_source_rule_ids")
        if not isinstance(active_ids, list) or not set(active_ids) <= set(SAFE_SOURCE_RULE_IDS):
            codes.append("physiognomy_unqualified_source_rule_id")
        safety = output.get("safety_boundaries")
        expected_safety = {
            "visible_observation_only": True,
            "provider_performed_vision": False,
            "no_biometric_or_identity_inference": True,
            "no_health_personality_wealth_lifespan_or_protected_attribute_inference": True,
            "historical_terminology_is_not_subject_verdict": True,
        }
        if not isinstance(safety, Mapping) or dict(safety) != expected_safety:
            codes.append("physiognomy_safety_boundary_missing")
    spec = (payload.get("input") or {}).get("physiognomy_spec") if isinstance(payload.get("input"), Mapping) else None
    if isinstance(spec, Mapping):
        try:
            expected = _build_fact_layer(spec)
        except (KeyError, TypeError, ValueError, RuntimeError):
            codes.append("physiognomy_embedded_input_invalid")
        else:
            actual = copy.deepcopy(dict(payload))
            actual.pop("validation", None)
            if actual != expected:
                codes.append("physiognomy_fact_replay_mismatch")
    else:
        codes.append("physiognomy_embedded_input_missing")
    return {"ok": not codes, "system": "physiognomy", "codes": list(dict.fromkeys(codes))}


def indexed_fact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the only Physiognomy facts allowed into FactRef/evidence indexes."""

    report = validate_fact_layer(payload)
    if not report["ok"]:
        raise ValueError("invalid Physiognomy fact layer")
    output = payload["output"]
    target_regions = {
        str(item.get("target_id")): str(item.get("region"))
        for item in output["requested_targets"]
        if isinstance(item, Mapping)
    }
    target_features = {
        str(item.get("target_id")): str(item.get("feature_kind"))
        for item in output["requested_targets"]
        if isinstance(item, Mapping)
    }
    missing_targets = [
        {
            "region": item.get("region"),
            "feature_kind": item.get("feature_kind"),
            "required": item.get("required"),
            "reason": item.get("reason"),
        }
        for item in output["missing_targets"]
        if isinstance(item, Mapping)
    ]
    uncertainties = [
        {
            "region": item.get("region"),
            "feature_kind": target_features.get(str(item.get("target_id"))),
            "reason_codes": copy.deepcopy(item.get("reason_codes") or []),
        }
        for item in output["uncertainties"]
        if isinstance(item, Mapping)
    ]
    observation_conflicts = [
        {
            "region": target_regions.get(str(item.get("target_id"))),
            "feature_kind": target_features.get(str(item.get("target_id"))),
            "capture_scope": item.get("capture_scope"),
            "observation_count": item.get("observation_count"),
            "blocking": item.get("blocking"),
            "resolved": bool(item.get("resolved_by_observation_id")),
        }
        for item in output["observation_conflicts"]
        if isinstance(item, Mapping)
    ]
    cross_capture_variations = [
        {
            "region": target_regions.get(str(item.get("target_id"))),
            "feature_kind": target_features.get(str(item.get("target_id"))),
            "capture_count": item.get("capture_count"),
            "descriptor_count": item.get("descriptor_count"),
            "auto_equivalent": item.get("auto_equivalent"),
        }
        for item in output["cross_capture_variations"]
        if isinstance(item, Mapping)
    ]
    source_comparison = {
        "sources": [
            {
                "title": item.get("title"),
                "edition_caveat": item.get("edition_caveat"),
            }
            for item in output["source_layers"]
            if isinstance(item, Mapping)
        ],
        "disagreements_retained": bool(output["source_disagreements"]),
        "disagreements": [
            {
                "sources": copy.deepcopy(item.get("public_sources") or []),
                "summary": item.get("public_summary"),
            }
            for item in output["source_disagreements"]
            if isinstance(item, Mapping)
        ],
        "forced_resolution": False,
    }
    indexed = {
        "fact_layer_status": payload["fact_layer_status"],
        "output": {
            "observation_scope": payload["input"]["physiognomy_spec"]["observation_scope"],
            "normalized_visible_observations": copy.deepcopy(output["normalized_visible_observations"]),
            "accepted_observation_fact_keys": copy.deepcopy(
                output["accepted_observation_fact_keys"]
            ),
            "missing_targets": missing_targets,
            "uncertainties": uncertainties,
            "observation_conflicts": observation_conflicts,
            "cross_capture_variations": cross_capture_variations,
            "source_comparison": source_comparison,
            "active_source_rule_ids": copy.deepcopy(output["active_source_rule_ids"]),
        },
    }
    indexed["output"]["source_conditioned_patterns"] = _source_conditioned_patterns(
        indexed
    )
    return indexed


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Build stable paths consumed by the source-evidence matcher."""

    if isinstance(value, Mapping) and value:
        for key in sorted(value, key=str):
            token = _escape_fact_token(str(key))
            yield from _fact_leaves(value[key], f"{path}/{token}")
        return
    if isinstance(value, (list, tuple)) and value:
        for index, item in enumerate(value):
            yield from _fact_leaves(item, f"{path}/{index}")
        return
    yield path or "/", value


def _source_conditioned_patterns(
    indexed: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Expose matched observation predicates without creating a person verdict."""

    fact_payload = {"chart_facts": copy.deepcopy(dict(indexed))}
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.physiognomy.v1",
            provider_version=ADAPTER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(fact_payload)
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.system != "physiognomy":
            continue
        matched, fact_ids, predicate_audit = evidence_rules.match_rule(
            rule, fact_refs
        )
        if not matched:
            continue
        matches.append(
            {
                "rule_id": rule.rule_id,
                "local_rule_id": rule.local_rule_id,
                "title": rule.title,
                "source_pack": rule.source_pack,
                "source_anchor": rule.source_anchor,
                "status": "predicate_matched_not_verdict",
                "fact_paths": list(fact_ids),
                "predicate_audit": list(predicate_audit),
                "source_dependency_id": "physiognomy.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def _private_string_values(
    value: Any,
    *,
    private_fields: frozenset[str],
    sensitive_field: str | None = None,
) -> set[str]:
    values: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            values.update(
                _private_string_values(
                    item,
                    private_fields=private_fields,
                    sensitive_field=(
                        str(key)
                        if str(key) in private_fields
                        else sensitive_field
                    ),
                )
            )
        return values
    if isinstance(value, (list, tuple)):
        for item in value:
            values.update(
                _private_string_values(
                    item,
                    private_fields=private_fields,
                    sensitive_field=sensitive_field,
                )
            )
        return values
    if sensitive_field and isinstance(value, str) and value:
        values.add(value)
        canonical = _canonical_security_text(value).casefold()
        if OPAQUE_IDENTIFIER_RE.fullmatch(canonical):
            values.add(canonical.split("-", 1)[1])
        if sensitive_field == "subject_ref":
            structural = {
                "subject",
                "private",
                "fixture",
                "synthetic",
                "anonymous",
                "anon",
                "user",
            }
            values.update(
                token
                for token in re.split(r"[._:-]+", value.casefold())
                if len(token) >= 4 and token not in structural
            )
    elif (
        sensitive_field
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        values.add(str(value))
    return values


_PUBLIC_NUMBER_RE = re.compile(
    r"(?<![\d.])"
    r"(?P<numerator>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"(?:\s*/\s*(?P<denominator>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?))?"
    r"(?P<percent>\s*[%％])?"
    r"(?![\d.])"
)


def _public_numeric_tokens(text: str) -> tuple[tuple[int, int, float], ...]:
    values: list[tuple[int, int, float]] = []
    for match in _PUBLIC_NUMBER_RE.finditer(text):
        try:
            value = float(match.group("numerator"))
            denominator = match.group("denominator")
            if denominator is not None:
                divisor = float(denominator)
                if divisor == 0.0:
                    continue
                value /= divisor
            if match.group("percent"):
                value /= 100.0
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(value):
            values.append((match.start(), match.end(), value))
    return tuple(values)


def _region_anchor_values(payload: Mapping[str, Any]) -> tuple[tuple[float, ...], ...]:
    spec = (
        (payload.get("input") or {}).get("physiognomy_spec")
        if isinstance(payload.get("input"), Mapping)
        else None
    )
    if not isinstance(spec, Mapping):
        return ()
    anchors: list[tuple[float, ...]] = []
    for observation in spec.get("observations") or ():
        if not isinstance(observation, Mapping):
            continue
        anchor = observation.get("region_anchor")
        if not isinstance(anchor, Mapping):
            continue
        try:
            values = tuple(
                float(anchor[field])
                for field in ("x", "y", "width", "height")
            )
        except (KeyError, TypeError, ValueError):
            continue
        anchors.append(values)
    return tuple(anchors)


def _contains_region_anchor_values(
    payload: Mapping[str, Any],
    public_copy: str,
) -> bool:
    anchors = _region_anchor_values(payload)
    tokens = _public_numeric_tokens(public_copy)
    label_patterns = {
        0: re.compile(r"(?:横坐标|横座標|(?<![a-z0-9_])x)\s*[:=：]?\s*$", re.IGNORECASE),
        1: re.compile(r"(?:纵坐标|縱坐標|(?<![a-z0-9_])y)\s*[:=：]?\s*$", re.IGNORECASE),
        2: re.compile(r"(?:宽度|寬度|(?<![a-z0-9_])width)\s*[:=：]?\s*$", re.IGNORECASE),
        3: re.compile(r"(?:高度|(?<![a-z0-9_])height)\s*[:=：]?\s*$", re.IGNORECASE),
    }
    for anchor in anchors:
        for token_start, _, value in tokens:
            prefix = public_copy[max(0, token_start - 32) : token_start]
            if any(
                pattern.search(prefix)
                and math.isclose(value, anchor[index], rel_tol=1e-9, abs_tol=1e-9)
                for index, pattern in label_patterns.items()
            ):
                return True
        for left, (token_start, _, _) in enumerate(tokens):
            segment = [
                item[2]
                for item in tokens[left:]
                if item[1] - token_start <= 160
            ]
            if all(
                any(
                    math.isclose(value, expected, rel_tol=1e-9, abs_tol=1e-9)
                    for value in segment
                )
                for expected in anchor
            ):
                return True
    return False


def _structural_tokens(value: Any) -> tuple[set[str], set[str]]:
    keys: set[str] = set()
    strings: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(_canonical_security_text(str(key)).casefold())
            child_keys, child_strings = _structural_tokens(item)
            keys.update(child_keys)
            strings.update(child_strings)
    elif isinstance(value, (list, tuple)):
        for item in value:
            child_keys, child_strings = _structural_tokens(item)
            keys.update(child_keys)
            strings.update(child_strings)
    elif isinstance(value, str) and value:
        strings.add(_canonical_security_text(value).casefold())
    return keys, strings


def _private_structural_tokens(
    payload: Mapping[str, Any],
) -> tuple[set[str], set[str]]:
    """Derive the private protocol complement from the public projection."""

    internal_keys, internal_strings = _structural_tokens(payload)
    safe_payload: Mapping[str, Any] = {}
    if payload.get("system") == "physiognomy" and "output" in payload:
        try:
            safe_payload = public_projection(payload)
        except (KeyError, TypeError, ValueError, RuntimeError):
            safe_payload = {}
    safe_keys, safe_strings = _structural_tokens(safe_payload)
    private_keys = {
        token
        for token in internal_keys - safe_keys
        if len(token) >= 8
    }
    private_strings = {
        token
        for token in internal_strings - safe_strings
        if len(token) >= 8
    }
    return private_keys, private_strings


def _contains_bounded_private_token(rendered: str, token: str) -> bool:
    canonical = _canonical_security_text(token).casefold()
    if not canonical:
        return False
    return re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(canonical)}(?![A-Za-z0-9_])",
        rendered,
    ) is not None


def _contains_private_value(rendered: str, value: str) -> bool:
    canonical = _canonical_security_text(value).casefold()
    if not canonical:
        return False
    if re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?",
        canonical,
    ):
        expected = float(canonical)
        return any(
            math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-12)
            for _, _, value in _public_numeric_tokens(rendered)
        )
    return canonical in rendered


def public_copy_contains_private_provenance(
    payload: Mapping[str, Any],
    public_copy: str,
) -> bool:
    """Detect exact internal field names or values in a public answer."""

    if not isinstance(public_copy, str):
        return True
    if _raw_media_key_paths(public_copy, path="public_copy"):
        return True
    privacy = source_table()["privacy_contract"]
    forbidden_tokens = tuple(
        _canonical_security_text(str(item)).casefold()
        for item in privacy["public_copy_forbidden_tokens"]
    )
    private_fields = frozenset(
        str(item) for item in privacy["private_fact_fields"]
    )
    rendered = _canonical_security_text(public_copy)
    if HTML_MARKUP_RE.search(rendered):
        return True
    rendered_candidates = tuple(
        item.casefold() for item in _security_text_candidates(rendered)
    )
    if any(
        _contains_bounded_private_token(candidate, token)
        for candidate in rendered_candidates
        for token in forbidden_tokens
    ):
        return True
    private_keys, private_strings = _private_structural_tokens(payload)
    if any(
        _contains_bounded_private_token(candidate, token)
        for candidate in rendered_candidates
        for token in private_keys
    ):
        return True
    if any(
        _contains_private_value(candidate, token)
        for candidate in rendered_candidates
        for token in private_strings
    ):
        return True
    if any(
        _contains_region_anchor_values(payload, candidate)
        for candidate in rendered_candidates
    ):
        return True
    return any(
        _contains_private_value(candidate, value)
        for candidate in rendered_candidates
        for value in _private_string_values(
            payload,
            private_fields=private_fields,
        )
    )


def public_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a privacy-safe public basis without opaque IDs or image provenance."""

    indexed = indexed_fact_payload(payload)
    output = indexed["output"]
    output.pop("active_source_rule_ids", None)
    output.pop("source_conditioned_patterns", None)
    return {
        "scope": "仅整理可见观察、质量、不确定性与古籍术语边界，不作个人结论",
        **output,
    }


def intake_public_projection(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Expose only the visible pending scope needed to phrase an intake question."""

    facts = build_fact_layer(spec)
    visible = public_projection(facts)
    return {
        "observation_scope": spec.get("observation_scope"),
        "requested_regions": [
            {
                "region": item.get("region"),
                "feature_kind": item.get("feature_kind"),
                "required": item.get("required"),
            }
            for item in spec.get("requested_targets") or ()
            if isinstance(item, Mapping)
        ],
        "normalized_visible_observations": visible["normalized_visible_observations"],
        "missing_targets": visible["missing_targets"],
        "uncertainties": visible["uncertainties"],
        "observation_conflicts": visible["observation_conflicts"],
        "cross_capture_variations": visible["cross_capture_variations"],
    }


def public_missing_facts(
    spec: Mapping[str, Any],
    missing_facts: Iterable[str],
) -> tuple[str, ...]:
    """Map private target ids to semantic regions for the public intake result."""

    target_semantics = {
        str(item.get("target_id")): (
            str(item.get("region")),
            str(item.get("feature_kind")),
        )
        for item in spec.get("requested_targets") or ()
        if isinstance(item, Mapping)
    }
    region_counts: dict[str, int] = {}
    for region, _ in target_semantics.values():
        region_counts[region] = region_counts.get(region, 0) + 1
    projected: list[str] = []
    for raw in missing_facts:
        item = str(raw)
        prefix, separator, target_id = item.partition(":")
        if separator and prefix in {"visible_observation", "observation_resolution"}:
            semantic = target_semantics.get(target_id)
            if not semantic:
                raise ValueError("Physiognomy public intake target mapping is missing")
            region, feature_kind = semantic
            suffix = (
                f":{feature_kind}"
                if region_counts.get(region, 0) > 1
                else ""
            )
            item = f"{prefix}:{region}{suffix}"
        projected.append(item)
    return tuple(dict.fromkeys(projected))


class RecastRequired(ValueError):
    """Stored observation identity cannot be safely reused by a correction."""


def merge_unique_rows(
    existing: list[Any],
    supplied: list[Any],
    *,
    id_field: str,
    label: str,
) -> list[Any]:
    result = copy.deepcopy(existing)
    by_id = {
        str(item.get(id_field)): item
        for item in result
        if isinstance(item, Mapping) and item.get(id_field)
    }
    for raw in supplied:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{label} rows must be objects")
        identifier = str(raw.get(id_field) or "")
        if not identifier:
            raise ValueError(f"{label} requires {id_field}")
        if identifier in by_id:
            if dict(by_id[identifier]) != dict(raw):
                raise ValueError(f"{label} duplicate id changes an accepted record")
            continue
        item = copy.deepcopy(dict(raw))
        result.append(item)
        by_id[identifier] = item
    return result


def merge_correction_spec(
    original: Mapping[str, Any],
    supplied: Mapping[str, Any],
) -> dict[str, Any]:
    """Append same-capture correction events while preserving immutable intake."""

    immutable = {
        "schema_version",
        "observation_scope",
        "subject_ref",
        "requested_targets",
        "source_layer_policy",
    }
    allowed = immutable | {
        "assets", "observations", "confirmed_observation_ids", "comparison_relations"
    }
    if set(supplied) - allowed:
        raise ValueError("unsupported Physiognomy correction field")
    for field in immutable:
        if field in supplied and supplied[field] != original.get(field):
            raise RecastRequired(
                "Physiognomy scope or subject change requires recast"
            )
    if "assets" in supplied and supplied["assets"] != original.get("assets"):
        raise RecastRequired(
            "new Physiognomy asset or capture requires recast"
        )
    new_observations = supplied.get("observations") or []
    if not isinstance(new_observations, list):
        raise ValueError("Physiognomy correction observations must be a list")
    if any(
        not isinstance(item, Mapping)
        or item.get("source_type") != "user_correction"
        or not item.get("supersedes_observation_id")
        for item in new_observations
    ):
        raise ValueError(
            "Physiognomy correct requires explicit user_correction supersession events"
        )
    merged = copy.deepcopy(dict(original))
    merged["observations"] = merge_unique_rows(
        list(original.get("observations") or []),
        new_observations,
        id_field="observation_id",
        label="Physiognomy observations",
    )
    confirmed = supplied.get("confirmed_observation_ids") or []
    if not isinstance(confirmed, list):
        raise ValueError("confirmed_observation_ids must be a list")
    merged["confirmed_observation_ids"] = list(
        dict.fromkeys([*(original.get("confirmed_observation_ids") or []), *confirmed])
    )
    relations = supplied.get("comparison_relations") or []
    if not isinstance(relations, list):
        raise ValueError("comparison_relations must be a list")
    merged["comparison_relations"] = [
        *(original.get("comparison_relations") or []),
        *copy.deepcopy(relations),
    ]
    if not new_observations and not confirmed and not relations:
        raise ValueError("Physiognomy correction supplies no revision event")
    return merged


def pending_target_ids(missing_facts: set[str]) -> set[str]:
    prefixes = ("visible_observation:", "observation_resolution:")
    return {
        fact.split(":", 1)[1]
        for fact in missing_facts
        if fact.startswith(prefixes) and ":" in fact
    }


def validate_pending_controls(
    *,
    confirmed_observation_ids: Any,
    comparison_relations: Any,
    observation_targets: Mapping[str, str],
    pending_ids: set[str],
) -> None:
    if not isinstance(confirmed_observation_ids, list):
        raise ValueError("confirmed_observation_ids must be a list")
    if any(
        observation_targets.get(str(identifier)) not in pending_ids
        for identifier in confirmed_observation_ids
    ):
        raise ValueError("confirmed observation is outside the pending target scope")
    if not isinstance(comparison_relations, list):
        raise ValueError("comparison_relations must be a list")
    for relation in comparison_relations:
        if not isinstance(relation, Mapping):
            raise ValueError("comparison relation must be an object")
        target_id = str(relation.get("target_id") or "")
        observation_ids = relation.get("observation_ids") or []
        if (
            target_id not in pending_ids
            or not isinstance(observation_ids, list)
            or any(
                observation_targets.get(str(identifier)) != target_id
                for identifier in observation_ids
            )
        ):
            raise ValueError("comparison relation is outside the pending target scope")


def merge_resume_spec(
    original: Mapping[str, Any],
    supplied: Mapping[str, Any],
    missing_facts: set[str],
) -> dict[str, Any] | None:
    """Append only observations authorized by the immutable pending target ids."""

    if "physiognomy_spec" in missing_facts:
        return copy.deepcopy(dict(supplied))
    adding_targets = "requested_targets" in missing_facts
    allowed_children = {
        "assets",
        "observations",
        "confirmed_observation_ids",
        "comparison_relations",
    }
    if adding_targets:
        allowed_children.add("requested_targets")
    if set(supplied) - allowed_children:
        raise ValueError("resume may not change Physiognomy scope or requested targets")
    merged = copy.deepcopy(dict(original))
    if adding_targets:
        existing_targets = merged.get("requested_targets") or []
        supplied_targets = supplied.get("requested_targets") or []
        if not isinstance(existing_targets, list) or not isinstance(
            supplied_targets, list
        ):
            raise ValueError("Physiognomy requested_targets must be lists")
        if not supplied_targets:
            raise ValueError("resume supplies no requested Physiognomy target")
        merged["requested_targets"] = merge_unique_rows(
            existing_targets,
            supplied_targets,
            id_field="target_id",
            label="Physiognomy requested_targets",
        )
        pending_ids = {
            str(item.get("target_id"))
            for item in supplied_targets
            if isinstance(item, Mapping) and item.get("target_id")
        }
        if len(pending_ids) != len(supplied_targets):
            raise ValueError("resume target rows require unique target_id values")
    else:
        pending_ids = pending_target_ids(missing_facts)
    if not pending_ids:
        return None
    supplied_observations = supplied.get("observations") or []
    if not isinstance(supplied_observations, list):
        raise ValueError("Physiognomy resume observations must be a list")
    if any(
        not isinstance(item, Mapping)
        or str(item.get("target_id") or "") not in pending_ids
        for item in supplied_observations
    ):
        raise ValueError("resume observation is outside the pending target scope")
    supplied_confirmed = supplied.get("confirmed_observation_ids") or []
    if not isinstance(supplied_confirmed, list):
        raise ValueError("confirmed_observation_ids must be a list")
    supplied_relations = supplied.get("comparison_relations") or []
    if (
        not adding_targets
        and not supplied_observations
        and not supplied_confirmed
        and not supplied_relations
    ):
        raise ValueError("resume supplies none of the pending Physiognomy observations")

    existing_assets = merged.get("assets") or []
    supplied_assets = supplied.get("assets") or []
    if not isinstance(existing_assets, list) or not isinstance(supplied_assets, list):
        raise ValueError("Physiognomy assets must be lists")
    merged["assets"] = merge_unique_rows(
        existing_assets,
        supplied_assets,
        id_field="asset_id",
        label="Physiognomy assets",
    )
    existing_observations = merged.get("observations") or []
    if not isinstance(existing_observations, list):
        raise ValueError("Physiognomy observations must be a list")
    merged["observations"] = merge_unique_rows(
        existing_observations,
        supplied_observations,
        id_field="observation_id",
        label="Physiognomy observations",
    )
    known = {
        str(item.get("observation_id")): str(item.get("target_id"))
        for item in merged["observations"]
        if isinstance(item, Mapping)
    }
    validate_pending_controls(
        confirmed_observation_ids=supplied_confirmed,
        comparison_relations=supplied_relations,
        observation_targets=known,
        pending_ids=pending_ids,
    )
    merged["confirmed_observation_ids"] = list(
        dict.fromkeys(
            [
                *(merged.get("confirmed_observation_ids") or []),
                *supplied_confirmed,
            ]
        )
    )
    merged["comparison_relations"] = [
        *(merged.get("comparison_relations") or []),
        *copy.deepcopy(supplied_relations),
    ]
    referenced_assets = {
        str(item.get("asset_id"))
        for item in supplied_observations
        if isinstance(item, Mapping) and item.get("asset_id")
    }
    supplied_asset_ids = {
        str(item.get("asset_id"))
        for item in supplied_assets
        if isinstance(item, Mapping) and item.get("asset_id")
    }
    if not supplied_asset_ids <= referenced_assets:
        raise ValueError("resume may add only assets used by pending observations")
    return merged


def merge_correction_resume_spec(
    original: Mapping[str, Any],
    supplied: Mapping[str, Any],
    missing_facts: set[str],
) -> dict[str, Any]:
    """Resume a bound correction without admitting a new capture or asset."""

    pending_ids = pending_target_ids(missing_facts)
    if not pending_ids:
        raise ValueError("Physiognomy correction resume has no pending target")
    if "assets" in supplied:
        raise RecastRequired(
            "new Physiognomy asset or capture requires recast"
        )
    observations = supplied.get("observations") or []
    if not isinstance(observations, list):
        raise ValueError("Physiognomy correction observations must be a list")
    known_targets = {
        str(item.get("observation_id")): str(item.get("target_id"))
        for item in original.get("observations") or ()
        if isinstance(item, Mapping)
    }
    for item in observations:
        if not isinstance(item, Mapping):
            raise ValueError("Physiognomy correction observation must be an object")
        target_id = str(item.get("target_id") or "")
        parent_id = str(item.get("supersedes_observation_id") or "")
        if target_id not in pending_ids or known_targets.get(parent_id) != target_id:
            raise ValueError(
                "Physiognomy correction resume is outside the pending target lineage"
            )
    observation_targets = dict(known_targets)
    observation_targets.update(
        {
            str(item.get("observation_id")): str(item.get("target_id"))
            for item in observations
            if isinstance(item, Mapping)
        }
    )
    validate_pending_controls(
        confirmed_observation_ids=supplied.get("confirmed_observation_ids") or [],
        comparison_relations=supplied.get("comparison_relations") or [],
        observation_targets=observation_targets,
        pending_ids=pending_ids,
    )
    return merge_correction_spec(original, supplied)


__all__ = [
    "ADAPTER_VERSION",
    "FACT_LAYER_STATUS",
    "FACT_SCHEMA_VERSION",
    "INPUT_SCHEMA_VERSION",
    "RecastRequired",
    "SAFE_SOURCE_RULE_IDS",
    "SOURCE_DEPENDENCIES",
    "SOURCE_TABLE_SHA256",
    "TABLE_PROFILE",
    "build_fact_layer",
    "fact_digest",
    "intake_public_projection",
    "indexed_fact_payload",
    "merge_correction_spec",
    "validate_pending_controls",
    "pending_target_ids",
    "merge_resume_spec",
    "merge_correction_resume_spec",
    "merge_unique_rows",
    "public_projection",
    "public_missing_facts",
    "public_copy_contains_private_provenance",
    "required_intake_facts",
    "source_table",
    "source_table_digest",
    "validate_fact_layer",
    "validate_no_raw_media",
    "validate_request_envelope",
]
