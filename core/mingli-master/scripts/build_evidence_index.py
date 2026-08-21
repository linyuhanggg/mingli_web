#!/usr/bin/env python3
"""Compile source-bound substantive rule records into the V5.1 evidence index."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references" / "catalog" / "catalog.json"
DEFAULT_OUTPUT = ROOT / "references" / "index" / "evidence-rules.jsonl"
SCHEMA_VERSION = "mingli-evidence-rule-v1"
LIUREN_SOURCE_TABLE = ROOT / "references" / "matrices" / "liuren-source-tables-v1.yaml"
SELECTION_SOURCE_TABLE = (
    ROOT / "references" / "matrices" / "selection-source-tables-v1.yaml"
)
FENGSHUI_SOURCE_TABLE = (
    ROOT / "references" / "matrices" / "fengshui-source-tables-v1.yaml"
)
PHYSIOGNOMY_SOURCE_TABLE = (
    ROOT / "references" / "matrices" / "physiognomy-source-tables-v1.yaml"
)
EVIDENCE_SCOPE_BINDINGS = (
    ROOT / "references" / "matrices" / "evidence-scope-bindings-v1.yaml"
)
CLASSICAL_EVIDENCE_BINDINGS = (
    ROOT / "references" / "matrices" / "classical-evidence-bindings-v1.json"
)
# Deliberately duplicated in reading_engine/evidence_rules.py.  A generated
# index is admitted only when both build-time and runtime code pin this exact
# independently audited manifest.
CLASSICAL_EVIDENCE_BINDINGS_SHA256 = (
    "73c5a8a5d2041e7d49f838c70d0ca184fee060fd355a8f29b0fd6f9a0a7abc8d"
)
SCOPE_BINDING_PACK_PREFIXES = {
    "bazi": ("bazi/",),
    "ziwei": ("ziwei/",),
    "luming-nayin": ("luming-nayin/",),
    "xingming": ("xingming/",),
    "liuyao": (
        "divination/zengshan-buyi",
        "divination/bushi-zhengzong",
        "divination/huangjin-ce",
        "divination/huozhu-lin",
    ),
    "meihua": (
        "divination/meihua-yishu",
        "divination/zhouyi-zhezhong",
        "divination/huangji-jingshi",
    ),
    "liuren": (
        "san-shi/daliuren-daquan",
        "san-shi/liuren-miben",
        "san-shi/liuren-zhiyin",
    ),
    "selection": ("selection/",),
    "fengshui": ("fengshui/",),
    "physiognomy": ("physiognomy/",),
}
SCOPE_PREDICATE_OPERATORS = {
    "present",
    "nonempty",
    "eq",
    "in",
    "contains",
    "descendant_eq",
    "same_record_fields",
}
SCOPE_EVIDENCE_ROLES = {
    "casting_rule",
    "imagery_correspondence",
    "issue_specific_judgment_rule",
    "methodology_rule",
    "terminology_only",
    "edition_boundary",
    "timing_rule",
    "verdict_prohibited",
}
LUMING_SIXTY_JIAZI = (
    "甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未", "壬申", "癸酉",
    "甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯", "庚辰", "辛巳", "壬午", "癸未",
    "甲申", "乙酉", "丙戌", "丁亥", "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳",
    "甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯",
    "甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑",
    "甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥",
)
RULE_ID_RE = re.compile(r"\b([A-Z]{1,8}(?:-[A-Z0-9~]+){1,5})\b")
FIELD_RE = re.compile(
    r"^-\s+\*\*([^*]+)\*\*\s*[:：]\s*(.*)$"
    r"|^-\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$"
)
SEPARATOR_RE = re.compile(r"^:?-{2,}:?$")
NON_SUBSTANTIVE_MARKERS = (
    "规则统计",
    "短引统计",
    "标题单元统计",
    "采集说明",
    "覆盖率统计",
    "source manifest",
    "source_manifest",
    "validation.md",
    "manifest 校验",
    "文件校验和",
    "输入校验",
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
CLASSICAL_ANCHOR_RE = re.compile(r"^[^#]+#L([1-9][0-9]*)(?:-L?([1-9][0-9]*))?$")


@dataclass(frozen=True)
class RawRule:
    local_id: str
    title: str
    fields: dict[str, str]
    line_start: int
    line_end: int


class _MissingSourceQuote(ValueError):
    """Internal signal for headings that are not substantive rule records."""


def _compact(value: str) -> str:
    return " ".join(str(value or "").replace("`", "").split())


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_predicate_signature(
    required: Any,
    excluded: Any,
) -> str:
    """Hash the exact ordered applicability contract, not its prose label."""

    payload = {"excluded": excluded or [], "required": required or []}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def canonical_rule_record_digest(record: Mapping[str, Any]) -> str:
    """Bind a classical proof to one derived rule without conflating texts."""

    payload = {
        "rule_id": record.get("rule_id"),
        "source_pack": record.get("source_pack"),
        "source_path": record.get("source_path"),
        "source_sha256": record.get("source_sha256"),
        "rule_record_anchor": record.get("source_anchor"),
        "assertion": record.get("quote"),
        "assertion_sha256": record.get("quote_hash"),
        "evidence_role": record.get("evidence_role"),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _classical_binding_digest(binding: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in binding.items() if key != "binding_digest"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_classical_source(source: Any, *, rule_id: str) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        raise ValueError(f"invalid classical source: {rule_id}")
    normalized = dict(source)
    path = str(normalized.get("path") or "")
    pure = Path(path)
    if (
        not path.startswith("references/")
        or pure.is_absolute()
        or ".." in pure.parts
    ):
        raise ValueError(f"classical source path escapes its root: {rule_id}")
    sha256 = str(normalized.get("sha256") or "")
    if SHA256_RE.fullmatch(sha256) is None:
        raise ValueError(f"invalid classical source hash: {rule_id}")
    anchor = str(normalized.get("anchor") or "")
    match = CLASSICAL_ANCHOR_RE.fullmatch(anchor)
    if match is None or (match.group(2) and int(match.group(2)) < int(match.group(1))):
        raise ValueError(f"invalid classical source anchor: {rule_id}")
    quote = str(normalized.get("verbatim_quote") or "")
    if not quote.strip():
        raise ValueError(f"empty classical source quote: {rule_id}")
    quote_sha256 = str(normalized.get("verbatim_quote_sha256") or "")
    if quote_sha256 != hashlib.sha256(quote.encode("utf-8")).hexdigest():
        raise ValueError(f"classical source quote hash mismatch: {rule_id}")
    return normalized


@lru_cache(maxsize=16)
def load_classical_evidence_bindings(
    *,
    root: Path = ROOT,
    manifest_path: Path | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Load the pinned independent source/predicate authorization manifest."""

    path = manifest_path or (
        root / CLASSICAL_EVIDENCE_BINDINGS.relative_to(ROOT)
    )
    rendered = path.read_bytes()
    actual_sha256 = hashlib.sha256(rendered).hexdigest()
    expected = expected_sha256 or CLASSICAL_EVIDENCE_BINDINGS_SHA256
    if actual_sha256 != expected:
        raise ValueError("classical evidence binding manifest hash mismatch")
    payload = json.loads(rendered)
    if payload.get("schema_version") != "mingli-classical-evidence-bindings-v1":
        raise ValueError("unsupported classical evidence binding schema")
    if payload.get("policy") != {
        "unverified_predicate_rules": "runtime_inactive",
        "runtime_requires_external_research_tree": False,
        "source_matching": "exact_only_no_fuzzy_fallback",
    }:
        raise ValueError("classical evidence binding policy drift")
    bindings = payload.get("bindings")
    if not isinstance(bindings, Mapping) or not bindings:
        raise ValueError("classical evidence binding manifest is empty")
    normalized_bindings: dict[str, Any] = {}
    catalog_payload = json.loads(
        (root / CATALOG.relative_to(ROOT)).read_text(encoding="utf-8")
    )
    catalog_sources = {
        f"{item['system']}/{item['slug']}": (
            str(item.get("local_fulltext_path") or ""),
            str(item.get("local_fulltext_sha256") or ""),
        )
        for item in catalog_payload.get("ready_reference_packs") or ()
    }
    for raw_rule_id, raw_binding in bindings.items():
        rule_id = str(raw_rule_id)
        if not isinstance(raw_binding, Mapping):
            raise ValueError(f"invalid classical rule binding: {rule_id}")
        binding = dict(raw_binding)
        if binding.get("rule_id") != rule_id:
            raise ValueError(f"classical rule binding identity mismatch: {rule_id}")
        status = binding.get("verification_status")
        if status not in {"verified", "inactive_unverified"}:
            raise ValueError(f"invalid classical verification status: {rule_id}")
        if binding.get("semantic_verification_status") != status:
            raise ValueError(f"classical semantic verification status drift: {rule_id}")
        for field in ("applicability_signature", "rule_record_digest"):
            if SHA256_RE.fullmatch(str(binding.get(field) or "")) is None:
                raise ValueError(f"invalid classical {field}: {rule_id}")
        mechanical_status = binding.get("mechanical_location_status")
        if mechanical_status not in {"verified_exact", "unverified"}:
            raise ValueError(f"invalid classical location status: {rule_id}")
        sources = binding.get("classical_sources")
        if status == "verified":
            if mechanical_status != "verified_exact":
                raise ValueError(f"semantic verification lacks exact source: {rule_id}")
            if not isinstance(sources, list) or not sources:
                raise ValueError(f"verified rule has no classical source: {rule_id}")
        if mechanical_status == "verified_exact":
            if not isinstance(sources, list) or not sources:
                raise ValueError(f"located rule has no classical source: {rule_id}")
            binding["classical_sources"] = [
                _validate_classical_source(item, rule_id=rule_id) for item in sources
            ]
            source_pack = rule_id.partition("#")[0]
            for source in binding["classical_sources"]:
                if source.get("location") == "release_tree":
                    expected_release = (
                        "references/source-excerpts/qimen-faqiao-chaibu-v1.md"
                        if source_pack == "san-shi/qimen-faqiao"
                        else ""
                    )
                    release_path = root / str(source["path"])
                    if (
                        source["path"] != expected_release
                        or not release_path.is_file()
                        or hashlib.sha256(release_path.read_bytes()).hexdigest()
                        != source["sha256"]
                    ):
                        raise ValueError(f"classical source hash/pack mismatch: {rule_id}")
                else:
                    expected_path, expected_hash = catalog_sources.get(
                        source_pack, ("", "")
                    )
                    if (
                        source["path"] != expected_path
                        or source["sha256"] != expected_hash
                    ):
                        raise ValueError(f"classical source hash/pack mismatch: {rule_id}")
        elif sources != []:
            raise ValueError(f"unlocated rule carries a classical source: {rule_id}")
        if binding.get("binding_digest") != _classical_binding_digest(binding):
            raise ValueError(f"classical binding digest mismatch: {rule_id}")
        normalized_bindings[rule_id] = binding
    return {**payload, "bindings": normalized_bindings}


def _verify_research_source_if_present(
    source: Mapping[str, Any],
    *,
    root: Path,
    research_root: Path | None = None,
) -> None:
    relative = Path(str(source["path"]))
    if str(source.get("location")) == "release_tree":
        candidate = root / relative
        base = root
    else:
        if research_root is None:
            raise ValueError(f"classical research source is missing: {relative}")
        candidate = research_root / relative
        base = research_root
    if not candidate.exists():
        if str(source.get("location")) == "release_tree":
            raise ValueError(f"classical release source is missing: {relative}")
        raise ValueError(f"classical research source is missing: {relative}")
    resolved = candidate.resolve(strict=True)
    base = base.resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f"classical source path escapes its root: {relative}")
    if hashlib.sha256(resolved.read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError(f"classical source hash mismatch: {relative}")
    match = CLASSICAL_ANCHOR_RE.fullmatch(str(source["anchor"]))
    assert match is not None
    start = int(match.group(1))
    end = int(match.group(2) or start)
    lines = resolved.read_text(encoding="utf-8", errors="strict").splitlines()
    if end > len(lines):
        raise ValueError(f"classical source anchor exceeds artifact: {relative}")
    excerpt = "\n".join(lines[start - 1 : end])
    if str(source["verbatim_quote"]) not in excerpt:
        raise ValueError(f"classical source quote is outside anchor: {relative}")


def _field_name(value: str) -> str:
    return _compact(value).casefold().replace(" ", "_")


def _validate_scope_predicates(
    predicates: Any,
    *,
    rule_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(predicates, list) or not predicates:
        raise ValueError(f"empty evidence scope predicates: {rule_id}")
    normalized: list[dict[str, Any]] = []
    for raw in predicates:
        if not isinstance(raw, Mapping):
            raise ValueError(f"invalid evidence scope predicate: {rule_id}")
        predicate = dict(raw)
        path_suffix = predicate.get("path_suffix")
        operator = predicate.get("operator")
        if not isinstance(path_suffix, str) or not path_suffix.startswith("/"):
            raise ValueError(f"invalid evidence scope path: {rule_id}")
        if operator not in SCOPE_PREDICATE_OPERATORS:
            raise ValueError(f"invalid evidence scope operator: {rule_id}")
        if operator in {"eq", "contains", "descendant_eq"} and "value" not in predicate:
            raise ValueError(f"evidence scope value missing: {rule_id}")
        if operator == "in" and not isinstance(predicate.get("values"), list):
            raise ValueError(f"evidence scope values missing: {rule_id}")
        if operator == "same_record_fields":
            fields = predicate.get("value")
            if (
                not isinstance(fields, Mapping)
                or len(fields) < 2
                or any(
                    not isinstance(name, str)
                    or not name
                    or "/" in name
                    for name in fields
                )
            ):
                raise ValueError(
                    f"same_record_fields requires at least two named fields: {rule_id}"
                )
        if operator in {"present", "nonempty"} and (
            {"value", "values"} & set(predicate)
        ):
            raise ValueError(
                f"{operator} predicate cannot carry values: {rule_id}"
            )
        normalized.append(predicate)
    if (
        len(normalized) == 1
        and normalized[0]["path_suffix"] == "/fact_layer_status"
    ):
        raise ValueError(
            f"fact_layer_status cannot be the sole evidence proof: {rule_id}"
        )
    canonical = [
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in normalized
    ]
    if len(canonical) != len(set(canonical)):
        raise ValueError(f"duplicate evidence scope predicate: {rule_id}")
    return normalized


def _normalize_scope_binding(
    rule_id: str,
    raw: Any,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"invalid evidence scope binding: {rule_id}")
    pack, separator, local_id = str(rule_id).partition("#")
    if not separator or not pack or not local_id or "#" in local_id:
        raise ValueError(f"invalid evidence scope rule id: {rule_id}")
    route = raw.get("route")
    if route not in SCOPE_BINDING_PACK_PREFIXES:
        raise ValueError(f"invalid evidence scope route: {rule_id}")
    allowed = SCOPE_BINDING_PACK_PREFIXES[str(route)]
    if not any(
        pack == prefix or (prefix.endswith("/") and pack.startswith(prefix))
        for prefix in allowed
    ):
        raise ValueError(f"evidence scope route/pack mismatch: {rule_id}")
    rationale = str(raw.get("rationale") or "").strip()
    if not rationale:
        raise ValueError(f"evidence scope rationale missing: {rule_id}")
    evidence_role = raw.get("evidence_role")
    if evidence_role is not None and evidence_role not in SCOPE_EVIDENCE_ROLES:
        raise ValueError(f"invalid evidence role in scope binding: {rule_id}")
    predicates = _validate_scope_predicates(
        raw.get("predicates"),
        rule_id=rule_id,
    )
    replaces_dimension_rule_id_predicate = raw.get(
        "replaces_dimension_rule_id_predicate",
        False,
    )
    if not isinstance(replaces_dimension_rule_id_predicate, bool):
        raise ValueError(
            f"invalid dimension rule predicate replacement flag: {rule_id}"
        )
    if replaces_dimension_rule_id_predicate and not any(
        predicate.get("operator") == "same_record_fields"
        and isinstance(predicate.get("value"), Mapping)
        and predicate["value"].get("source_rule") == local_id
        for predicate in predicates
    ):
        raise ValueError(
            f"dimension rule predicate replacement lacks same-row source rule: {rule_id}"
        )
    luming_match = re.fullmatch(
        r"luming-nayin/li-xuzhong-mingshu#LX-01-(\d{2})",
        rule_id,
    )
    if luming_match is not None:
        number = int(luming_match.group(1))
        expected_shape = (
            len(predicates) == 1
            and predicates[0].get("path_suffix") == "/four_pillars/year"
            and predicates[0].get("operator") == "eq"
        )
        if not expected_shape:
            raise ValueError(
                f"Luming Jiazi evidence must be restricted to the year pillar: {rule_id}"
            )
        if not 1 <= number <= len(LUMING_SIXTY_JIAZI):
            raise ValueError(f"invalid Luming Jiazi rule number: {rule_id}")
        if predicates[0].get("value") != LUMING_SIXTY_JIAZI[number - 1]:
            raise ValueError(f"Luming Jiazi value mismatch: {rule_id}")
    return {
        "route": str(route),
        "rationale": rationale,
        "predicates": predicates,
        "evidence_role": evidence_role,
        "replaces_dimension_rule_id_predicate": (
            replaces_dimension_rule_id_predicate
        ),
    }


def validate_evidence_scope_bindings(
    payload: Any,
) -> dict[str, dict[str, Any]]:
    """Validate and expand the source-audited rule-to-fact scope matrix."""

    if not isinstance(payload, Mapping):
        raise ValueError("evidence scope binding payload must be an object")
    if payload.get("schema_version") != "mingli-evidence-scope-bindings-v1":
        raise ValueError("unsupported evidence scope binding schema")
    result: dict[str, dict[str, Any]] = {}

    def add(rule_id: str, raw: Any) -> None:
        if rule_id in result:
            raise ValueError(f"duplicate evidence scope rule id: {rule_id}")
        result[rule_id] = _normalize_scope_binding(rule_id, raw)

    bindings = payload.get("bindings") or {}
    if not isinstance(bindings, Mapping):
        raise ValueError("evidence scope bindings must be an object")
    for rule_id, raw in bindings.items():
        add(str(rule_id), raw)

    series = payload.get("series") or []
    if not isinstance(series, list):
        raise ValueError("evidence scope series must be a list")
    for item in series:
        if not isinstance(item, Mapping):
            raise ValueError("invalid evidence scope series")
        route = str(item.get("route") or "")
        source_pack = str(item.get("source_pack") or "")
        rationale = str(item.get("rationale") or "")
        predicate = item.get("predicate")
        values = item.get("values")
        if not source_pack or not isinstance(predicate, Mapping):
            raise ValueError("invalid evidence scope series template")
        if not isinstance(values, Mapping) or not values:
            raise ValueError("empty evidence scope series values")
        for local_id, value in values.items():
            expanded_predicate = dict(predicate)
            if "value" in expanded_predicate or "values" in expanded_predicate:
                raise ValueError("series predicate must not predeclare a value")
            expanded_predicate["value"] = value
            add(
                f"{source_pack}#{local_id}",
                {
                    "route": route,
                    "rationale": rationale,
                    "predicates": [expanded_predicate],
                },
            )
    if not result:
        raise ValueError("evidence scope binding matrix is empty")
    return result


def load_evidence_scope_bindings(
    *,
    root: Path = ROOT,
) -> dict[str, dict[str, Any]]:
    path = root / EVIDENCE_SCOPE_BINDINGS.relative_to(ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    bindings = validate_evidence_scope_bindings(payload)
    policy = payload.get("policy") if isinstance(payload, Mapping) else None
    expected_policy = {
        "unlisted_rules": "disabled",
        "fact_layer_status_alone_forbidden": True,
        "narrower_than_source_scope_is_allowed": True,
    }
    if policy != expected_policy:
        raise ValueError("evidence scope binding policy drift")
    return bindings


def validate_evidence_scope_binding_coverage(
    bindings: Mapping[str, Any],
    compiled_rule_ids: set[str],
) -> None:
    unknown = sorted(set(bindings) - set(compiled_rule_ids))
    if unknown:
        raise ValueError(f"unknown evidence rule in scope bindings: {unknown[0]}")


def _heading_rules(lines: list[str]) -> list[RawRule]:
    headings = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^#{2,5}\s+\S", line)
    ]
    rules: list[RawRule] = []
    for offset, start in enumerate(headings):
        title = re.sub(r"^#{2,5}\s+", "", lines[start]).strip()
        match = RULE_ID_RE.search(title)
        if match is None:
            continue
        end = headings[offset + 1] if offset + 1 < len(headings) else len(lines)
        fields: dict[str, str] = {}
        current: str | None = None
        plain_body: list[str] = []
        for line in lines[start + 1 : end]:
            field_match = FIELD_RE.match(line.strip())
            if field_match:
                name = field_match.group(1) or field_match.group(3) or ""
                value = field_match.group(2) or field_match.group(4) or ""
                current = _field_name(name)
                fields[current] = _compact(value)
                continue
            if current and line.strip() and not line.lstrip().startswith("#"):
                continuation = re.sub(r"^\s*(?:\d+\.|[-*])\s*", "", line)
                fields[current] = _compact(
                    " ".join((fields[current], continuation))
                )
            elif line.strip() and not line.lstrip().startswith(("#", "---")):
                plain_body.append(
                    re.sub(r"^\s*(?:>|\d+\.|[-*])\s*", "", line).strip()
                )
        if not fields and plain_body:
            fields["rule_statement"] = _compact(" ".join(plain_body))
        rules.append(
            RawRule(
                local_id=match.group(1),
                title=_compact(title),
                fields=fields,
                line_start=start + 1,
                line_end=end,
            )
        )
    return rules


def _table_rules(lines: list[str]) -> list[RawRule]:
    rules: list[RawRule] = []
    header: list[str] | None = None
    for line_number, line in enumerate(lines, start=1):
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = [_compact(cell) for cell in line.strip().strip("|").split("|")]
        if not cells or all(SEPARATOR_RE.fullmatch(cell or "-") for cell in cells):
            continue
        normalized = [_field_name(cell) for cell in cells]
        if "id" in normalized and any(
            name in normalized
            for name in ("rule", "statement", "plain_language_rule", "title")
        ):
            header = normalized
            continue
        if header is None or len(cells) != len(header):
            continue
        values = dict(zip(header, cells))
        local_id = values.get("id") or ""
        if RULE_ID_RE.fullmatch(local_id) is None:
            continue
        rules.append(
            RawRule(
                local_id=local_id,
                title=values.get("title") or local_id,
                fields=values,
                line_start=line_number,
                line_end=line_number,
            )
        )
    return rules


def _first(fields: dict[str, str], *names: str) -> str:
    for name in names:
        value = fields.get(name)
        if value:
            return value
    return ""


def _rule_source_binding(raw: RawRule, path: Path) -> dict[str, Any]:
    """Derive the quote and anchor only from one parsed source rule block."""

    quote = _first(
        raw.fields,
        "exact_quote",
        "quote",
        "rule_statement",
        "statement",
        "rule",
        "plain_language_rule",
        "conclusion",
        "decision_effect",
    )
    if not quote:
        raise _MissingSourceQuote(
            f"evidence rule has no source quote: {raw.local_id}"
        )
    block_anchor = f"{path.name}#L{raw.line_start}-L{raw.line_end}"
    anchor = _first(
        raw.fields,
        "source_anchor",
        "normalized_anchor",
        "source_location",
    ) or block_anchor
    if anchor.startswith(f"{path.name}#L") and anchor != block_anchor:
        raise ValueError(
            "evidence source anchor does not cover the rule block: "
            f"{raw.local_id} ({anchor} != {block_anchor})"
        )
    return {
        "quote": quote,
        "source_anchor": anchor,
        "line_start": raw.line_start,
        "line_end": raw.line_end,
    }


@lru_cache(maxsize=128)
def _source_rule_bindings(
    source_path: str,
    source_sha256: str,
) -> dict[str, dict[str, Any]]:
    """Parse a hash-addressed rules file once for compiler and runtime audits."""

    path = Path(source_path)
    content = path.read_bytes()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != source_sha256:
        raise ValueError(f"evidence source hash mismatch: {path}")
    lines = content.decode("utf-8", errors="strict").splitlines()
    raw_rules = {rule.local_id: rule for rule in _heading_rules(lines)}
    for rule in _table_rules(lines):
        raw_rules.setdefault(rule.local_id, rule)
    bindings: dict[str, dict[str, Any]] = {}
    for local_id, raw in raw_rules.items():
        try:
            bindings[local_id] = _rule_source_binding(raw, path)
        except _MissingSourceQuote:
            continue
    return bindings


def validate_source_bound_record(
    record: Mapping[str, Any],
    *,
    source_path: Path,
) -> None:
    """Fail closed unless quote and anchor equal their source rule block."""

    local_id = str(record.get("local_rule_id") or "")
    rule_id = str(record.get("rule_id") or "")
    source_pack = str(record.get("source_pack") or "")
    if not local_id or rule_id != f"{source_pack}#{local_id}":
        raise ValueError(f"evidence rule/source identity mismatch: {rule_id}")
    expected_source_path = f"references/books/{source_pack}/rules.md"
    if str(record.get("source_path") or "") != expected_source_path:
        raise ValueError(f"evidence source path/pack mismatch: {rule_id}")
    source_sha256 = str(record.get("source_sha256") or "")
    try:
        binding = _source_rule_bindings(
            str(source_path.resolve(strict=True)),
            source_sha256,
        )[local_id]
    except KeyError as exc:
        raise ValueError(f"evidence rule is absent from source: {rule_id}") from exc
    if str(record.get("quote") or "") != binding["quote"]:
        raise ValueError(f"evidence quote does not match source: {rule_id}")
    if str(record.get("source_anchor") or "") != binding["source_anchor"]:
        raise ValueError(f"evidence source anchor mismatch: {rule_id}")


def _rule_refs(value: str, *, self_id: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            match
            for match in RULE_ID_RE.findall(value or "")
            if match != self_id
        )
    )


def _qiongtong_predicates(local_id: str) -> list[dict[str, Any]]:
    match = re.fullmatch(r"QR-0([1-5])-0([1-8])", local_id)
    if match is None:
        return []
    stem_pairs = {
        "1": ("甲", "乙"),
        "2": ("丙", "丁"),
        "3": ("戊", "己"),
        "4": ("庚", "辛"),
        "5": ("壬", "癸"),
    }
    seasons = (
        ("寅", "卯", "辰"),
        ("巳", "午", "未"),
        ("申", "酉", "戌"),
        ("亥", "子", "丑"),
    )
    number = int(match.group(2))
    stem = stem_pairs[match.group(1)][0 if number <= 4 else 1]
    branches = seasons[(number - 1) % 4]
    return [
        {
            "path_suffix": "/day_master/stem",
            "operator": "eq",
            "value": stem,
        },
        {
            "path_suffix": "/month_command/branch",
            "operator": "in",
            "values": list(branches),
        },
    ]


def _liuren_predicates(pack: str, title: str) -> list[dict[str, Any]]:
    if not pack.startswith("san-shi/liuren") and pack != "san-shi/daliuren-daquan":
        return []
    methods = (
        "重审",
        "元首",
        "比用",
        "知一",
        "涉害",
        "见机",
        "察微",
        "缀瑕",
        "遥克",
        "蒿矢",
        "弹射",
        "昴星",
        "别责",
        "八专",
        "伏吟",
        "返吟",
        "反吟",
        "井栏",
    )
    selected = [method for method in methods if method in title]
    if not selected:
        return []
    return [
        {
            "path_suffix": "/transmission_method/primary",
            "operator": "in",
            "values": selected,
        }
    ]


def _qimen_predicates(pack: str, local_id: str) -> list[dict[str, Any]]:
    if not pack.startswith("san-shi/qimen"):
        return []
    if re.fullmatch(r"QM-P(?:0[1-9]|[1-3][0-9]|40)", local_id) is None:
        return []
    return [
        {
            "path_suffix": "/named_patterns",
            "operator": "descendant_eq",
            "value": local_id,
        }
    ]


def _taiyi_predicates(pack: str, local_id: str) -> list[dict[str, Any]]:
    if not pack.startswith("san-shi/taiyi"):
        return []
    if re.fullmatch(r"TY-P(?:0[1-9]|10)", local_id):
        return [
            {
                "path_suffix": "/board_predicates",
                "operator": "descendant_eq",
                "value": local_id,
            }
        ]
    return [
        {
            "path_suffix": "/source_rule_ids",
            "operator": "descendant_eq",
            "value": local_id,
        }
    ]


def _selection_predicates(
    root: Path,
    pack: str,
    local_id: str,
) -> list[dict[str, Any]]:
    """Load source-audited Selection rule-to-fact bindings.

    Every Selection rule first proves that the active facts came from the
    deterministic Selection provider.  Its named binding then identifies the
    exact calculated layer that makes the classical record applicable.  Rules
    outside the provider's declared event profiles use the deliberately absent
    ``not_calculated`` contract and therefore cannot leak into retrieval.
    """

    if not pack.startswith("selection/"):
        return []
    if pack == "selection/xingli-kaoyuan" and local_id == "KR-05":
        # The audited five-tigers/five-rats methodology is evidenced by the
        # calculated four pillars themselves.  It must not self-authorize via
        # Selection's active_source_rule_ids contract.
        return []
    path = root / SELECTION_SOURCE_TABLE.relative_to(ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    bindings = payload.get("evidence_fact_bindings") or {}
    if bindings.get("version") != "1.1.0":
        raise ValueError("unsupported Selection evidence-fact binding version")
    contracts = bindings.get("contracts") or {}
    rules = bindings.get("rules") or {}
    contract_id = rules.get(local_id)
    if not isinstance(contract_id, str) or contract_id not in contracts:
        raise ValueError(
            f"Selection rule has no evidence-fact binding: {pack}#{local_id}"
        )
    predicates = contracts[contract_id]
    if not isinstance(predicates, list) or not predicates:
        raise ValueError(f"empty Selection fact contract: {contract_id}")
    allowed = {
        "present",
        "nonempty",
        "eq",
        "in",
        "contains",
        "descendant_eq",
    }
    normalized: list[dict[str, Any]] = [
        {
            "path_suffix": "/fact_layer_status",
            "operator": "eq",
            "value": "deterministic_selection_candidates",
        }
    ]
    for predicate in predicates:
        if not isinstance(predicate, dict):
            raise ValueError(f"invalid Selection fact contract: {contract_id}")
        if predicate.get("operator") not in allowed or not str(
            predicate.get("path_suffix") or ""
        ).startswith("/"):
            raise ValueError(f"invalid Selection fact predicate: {contract_id}")
        normalized_predicate = dict(predicate)
        if normalized_predicate.get("value") == "$local_id":
            normalized_predicate["value"] = local_id
        normalized.append(normalized_predicate)
    return normalized


def _fengshui_predicates(
    root: Path,
    pack: str,
    local_id: str,
) -> list[dict[str, Any]]:
    """Bind every Fengshui record to its exact provider-active pack rule id."""

    if not pack.startswith("fengshui/"):
        return []
    path = root / FENGSHUI_SOURCE_TABLE.relative_to(ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "mingli-fengshui-source-tables-v1":
        raise ValueError("unsupported Fengshui source table schema")
    bindings = payload.get("evidence_binding_contract") or {}
    if bindings.get("version") != "1.0.0":
        raise ValueError("unsupported Fengshui evidence binding version")
    templates = bindings.get("common_predicates") or []
    if not isinstance(templates, list) or len(templates) != 2:
        raise ValueError("Fengshui evidence binding must contain two predicates")
    rule_id = f"{pack}#{local_id}"
    normalized: list[dict[str, Any]] = []
    for template in templates:
        if not isinstance(template, dict):
            raise ValueError("invalid Fengshui evidence predicate")
        predicate = dict(template)
        if predicate.get("value") == "$rule_id":
            predicate["value"] = rule_id
        if (
            not str(predicate.get("path_suffix") or "").startswith("/")
            or predicate.get("operator") not in {
                "present", "eq", "in", "contains", "descendant_eq"
            }
        ):
            raise ValueError("invalid Fengshui evidence predicate")
        normalized.append(predicate)
    expected = [
        {
            "path_suffix": "/fact_layer_status",
            "operator": "eq",
            "value": "observation_driven_fengshui_facts",
        },
        {
            "path_suffix": "/active_source_rule_ids",
            "operator": "descendant_eq",
            "value": rule_id,
        },
    ]
    if normalized != expected:
        raise ValueError(f"invalid Fengshui evidence binding: {rule_id}")
    return normalized


def _physiognomy_table(root: Path) -> dict[str, Any]:
    path = root / PHYSIOGNOMY_SOURCE_TABLE.relative_to(ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "mingli-physiognomy-source-tables-v1":
        raise ValueError("unsupported Physiognomy source table schema")
    bindings = payload.get("evidence_binding_contract") or {}
    if bindings.get("version") != "1.0.0":
        raise ValueError("unsupported Physiognomy evidence binding version")
    return payload


def _physiognomy_predicates(
    root: Path,
    pack: str,
    local_id: str,
) -> list[dict[str, Any]]:
    """Bind every Physiognomy record to its exact provider-active rule id."""

    if not pack.startswith("physiognomy/"):
        return []
    payload = _physiognomy_table(root)
    templates = (payload.get("evidence_binding_contract") or {}).get(
        "required_predicates"
    ) or []
    if not isinstance(templates, list) or len(templates) != 2:
        raise ValueError("Physiognomy evidence binding must contain two predicates")
    rule_id = f"{pack}#{local_id}"
    normalized: list[dict[str, Any]] = []
    for template in templates:
        if not isinstance(template, dict):
            raise ValueError("invalid Physiognomy evidence predicate")
        predicate = dict(template)
        if predicate.get("value") == "$rule_id":
            predicate["value"] = rule_id
        if (
            not str(predicate.get("path_suffix") or "").startswith("/")
            or predicate.get("operator") not in {
                "present", "eq", "in", "contains", "descendant_eq"
            }
        ):
            raise ValueError("invalid Physiognomy evidence predicate")
        normalized.append(predicate)
    expected = [
        {
            "path_suffix": "/fact_layer_status",
            "operator": "eq",
            "value": "observation_driven_physiognomy_facts",
        },
        {
            "path_suffix": "/active_source_rule_ids",
            "operator": "descendant_eq",
            "value": rule_id,
        },
    ]
    if normalized != expected:
        raise ValueError(f"invalid Physiognomy evidence binding: {rule_id}")
    return normalized


def _physiognomy_evidence_role(
    root: Path,
    pack: str,
    local_id: str,
) -> str:
    if not pack.startswith("physiognomy/"):
        return "issue_specific_judgment_rule"
    rule_id = f"{pack}#{local_id}"
    activation = _physiognomy_table(root).get("source_rule_activation") or {}
    roles = activation.get("evidence_roles") or {}
    matched = [
        str(role)
        for role, rule_ids in roles.items()
        if rule_id in set(rule_ids or ())
    ]
    if len(matched) > 1:
        raise ValueError(f"duplicate Physiognomy evidence role: {rule_id}")
    if matched:
        return matched[0]
    return "verdict_prohibited"


def _canonical_system(pack: str, catalog_system: str) -> str:
    if pack.startswith("san-shi/daliuren") or pack.startswith("san-shi/liuren"):
        return "liuren"
    if pack.startswith("san-shi/qimen"):
        return "qimen"
    if pack.startswith("san-shi/taiyi"):
        return "taiyi"
    return catalog_system


def _compile_rule(
    item: dict[str, Any],
    raw: RawRule,
    path: Path,
    *,
    root: Path,
    evidence_role: str,
    dimension_fact_rule: bool,
    scope_bindings: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    pack = f"{item['system']}/{item['slug']}"
    rule_id = f"{pack}#{raw.local_id}"
    fields = raw.fields
    try:
        source_binding = _rule_source_binding(raw, path)
    except _MissingSourceQuote:
        return None
    quote = str(source_binding["quote"])
    chapter = _first(fields, "source_chapter", "chapter", "section")
    anchor = str(source_binding["source_anchor"])
    applicable = _first(
        fields,
        "applicable_to",
        "preconditions",
        "condition",
        "adapter_requirements",
    )
    metadata_probe = " ".join((raw.title, chapter, quote, anchor)).casefold()
    if any(marker.casefold() in metadata_probe for marker in NON_SUBSTANTIVE_MARKERS):
        return None
    topics = tuple(
        value
        for value in dict.fromkeys(
            filter(
                None,
                (
                    re.sub(RULE_ID_RE, "", raw.title).strip(" —-"),
                    chapter,
                    applicable,
                    fields.get("system", ""),
                ),
            )
        )
    )
    scope_binding = scope_bindings.get(rule_id) or {}
    required = [
        *_qiongtong_predicates(raw.local_id),
        *_liuren_predicates(pack, raw.title),
        *_qimen_predicates(pack, raw.local_id),
        *_taiyi_predicates(pack, raw.local_id),
        *_selection_predicates(root, pack, raw.local_id),
        *_fengshui_predicates(root, pack, raw.local_id),
        *_physiognomy_predicates(root, pack, raw.local_id),
        *scope_binding.get("predicates", ()),
    ]
    if dimension_fact_rule and not scope_binding.get(
        "replaces_dimension_rule_id_predicate"
    ):
        required.append(
            {
                "path_suffix": "/source_rule_ids",
                "operator": "descendant_eq",
                "value": raw.local_id,
            }
        )
    conflicts = _rule_refs(fields.get("conflicts", ""), self_id=raw.local_id)
    exceptions = _rule_refs(fields.get("exceptions", ""), self_id=raw.local_id)
    dependencies = _rule_refs(
        " ".join(
            (
                fields.get("depends_on", ""),
                fields.get("dependencies", ""),
                fields.get("preconditions", ""),
            )
        ),
        self_id=raw.local_id,
    )
    relative = path.relative_to(root).as_posix()
    source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "rule_id": rule_id,
        "local_rule_id": raw.local_id,
        "system": _canonical_system(pack, str(item["system"])),
        "source_pack": pack,
        "source_title": str(item["title"]),
        "source_layer": _first(fields, "source_layer")
        or str(item.get("source_layer") or "unspecified"),
        "chapter": chapter,
        "title": raw.title,
        "quote": quote,
        "source_anchor": anchor,
        "source_path": relative,
        "source_sha256": source_sha256,
        "quote_hash": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "topics": list(topics),
        "required_fact_predicates": required,
        "excluded_fact_predicates": [],
        "exception_rule_ids": [f"{pack}#{value}" for value in exceptions],
        "conflict_rule_ids": [f"{pack}#{value}" for value in conflicts],
        "depends_on_rule_ids": [f"{pack}#{value}" for value in dependencies],
        "record_kind": "substantive_rule",
        "evidence_role": evidence_role,
    }
    validate_source_bound_record(payload, source_path=path)
    return payload


def _liuren_evidence_role_map(root: Path) -> dict[tuple[str, str], str]:
    path = root / LIUREN_SOURCE_TABLE.relative_to(ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "mingli-liuren-source-tables-v1":
        raise ValueError("unsupported Liuren source table schema")
    allowed = {
        "casting_rule",
        "imagery_correspondence",
        "issue_specific_judgment_rule",
        "timing_rule",
    }
    result: dict[tuple[str, str], str] = {}
    for pack, roles in (payload.get("evidence_roles") or {}).items():
        for role, local_ids in (roles or {}).items():
            if role not in allowed:
                raise ValueError(f"unsupported Liuren evidence role: {role}")
            for local_id in local_ids or ():
                key = (str(pack), str(local_id))
                if key in result:
                    raise ValueError(f"duplicate Liuren evidence role: {pack}#{local_id}")
                result[key] = str(role)
    if not result:
        raise ValueError("Liuren evidence role matrix is empty")
    return result


def _liuren_dimension_rule_ids(root: Path) -> set[str]:
    path = root / LIUREN_SOURCE_TABLE.relative_to(ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        str(local_id)
        for profile in (payload.get("dimension_profiles") or {}).values()
        for local_id in (profile.get("eligible_rule_ids") or ())
    }


def _apply_classical_evidence_bindings(
    records: list[dict[str, Any]],
    *,
    root: Path,
    verify_research_sources: bool = False,
    research_root: Path | None = None,
) -> None:
    manifest = load_classical_evidence_bindings(root=root)
    bindings = manifest["bindings"]
    predicate_rule_ids = {
        str(record["rule_id"])
        for record in records
        if record["required_fact_predicates"] or record["excluded_fact_predicates"]
    }
    if set(bindings) != predicate_rule_ids:
        missing = sorted(predicate_rule_ids - set(bindings))
        unknown = sorted(set(bindings) - predicate_rule_ids)
        detail = (missing or unknown or ["unknown"])[0]
        raise ValueError(f"classical binding coverage mismatch: {detail}")
    for record in records:
        required = record["required_fact_predicates"]
        excluded = record["excluded_fact_predicates"]
        signature = canonical_predicate_signature(required, excluded)
        record_digest = canonical_rule_record_digest(record)
        binding = bindings.get(record["rule_id"])
        if binding is None:
            record.update(
                {
                    "runtime_active": False,
                    "classical_binding_status": "inactive_unscoped",
                    "applicability_signature": signature,
                    "rule_record_digest": record_digest,
                    "classical_binding_digest": "",
                    "classical_sources": [],
                }
            )
            continue
        if binding["applicability_signature"] != signature:
            raise ValueError(f"classical predicate signature mismatch: {record['rule_id']}")
        if binding["rule_record_digest"] != record_digest:
            raise ValueError(f"classical rule record digest mismatch: {record['rule_id']}")
        sources = list(binding["classical_sources"])
        for source in sources:
            if (
                str(source.get("location")) == "release_tree"
                or verify_research_sources
            ):
                _verify_research_source_if_present(
                    source,
                    root=root,
                    research_root=research_root,
                )
        verified = binding["verification_status"] == "verified"
        record.update(
            {
                "runtime_active": verified,
                "classical_binding_status": binding["verification_status"],
                "applicability_signature": signature,
                "rule_record_digest": record_digest,
                "classical_binding_digest": binding["binding_digest"],
                "classical_sources": sources,
            }
        )


def compile_evidence_rules(
    root: Path = ROOT,
    *,
    enforce_classical_bindings: bool = True,
    verify_research_sources: bool = False,
    research_root: Path | None = None,
) -> list[dict[str, Any]]:
    catalog_path = root / CATALOG.relative_to(ROOT)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    liuren_roles = _liuren_evidence_role_map(root)
    liuren_dimension_rules = _liuren_dimension_rule_ids(root)
    scope_bindings = load_evidence_scope_bindings(root=root)
    compiled: list[dict[str, Any]] = []
    for item in catalog.get("ready_reference_packs") or ():
        pack = f"{item['system']}/{item['slug']}"
        pack_dir = (root / str(item["skill_index_path"])).parent
        path = pack_dir / "rules.md"
        if not path.is_file():
            raise ValueError(f"missing rules file for {item['system']}/{item['slug']}")
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        raw_rules = {rule.local_id: rule for rule in _heading_rules(lines)}
        for rule in _table_rules(lines):
            raw_rules.setdefault(rule.local_id, rule)
        for local_id in sorted(raw_rules):
            canonical_system = _canonical_system(pack, str(item["system"]))
            if canonical_system == "liuren":
                try:
                    evidence_role = liuren_roles[(pack, local_id)]
                except KeyError as exc:
                    raise ValueError(
                        f"Liuren rule has no evidence role: {pack}#{local_id}"
                    ) from exc
            elif canonical_system == "physiognomy":
                evidence_role = _physiognomy_evidence_role(
                    root,
                    pack,
                    local_id,
                )
            else:
                evidence_role = "issue_specific_judgment_rule"
            scoped_role = (scope_bindings.get(f"{pack}#{local_id}") or {}).get(
                "evidence_role"
            )
            if scoped_role is not None:
                evidence_role = str(scoped_role)
            record = _compile_rule(
                item,
                raw_rules[local_id],
                path,
                root=root,
                evidence_role=evidence_role,
                dimension_fact_rule=(
                    canonical_system == "liuren"
                    and local_id in liuren_dimension_rules
                ),
                scope_bindings=scope_bindings,
            )
            if record is not None:
                compiled.append(record)
    compiled.sort(key=lambda item: item["rule_id"])
    duplicates = len(compiled) - len({item["rule_id"] for item in compiled})
    if duplicates:
        raise ValueError(f"duplicate evidence rule ids: {duplicates}")
    validate_evidence_scope_binding_coverage(
        scope_bindings,
        {item["rule_id"] for item in compiled},
    )
    if enforce_classical_bindings:
        _apply_classical_evidence_bindings(
            compiled,
            root=root,
            verify_research_sources=verify_research_sources,
            research_root=research_root,
        )
    return compiled


def render_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for record in records
    )


def audit_checked_evidence_index(
    *,
    root: Path = ROOT,
    checked_path: Path | None = None,
) -> dict[str, Any]:
    """Prove that the checked JSONL is the canonical compiler output."""

    records = compile_evidence_rules(root=root)
    expected = render_jsonl(records)
    path = checked_path or (
        root / DEFAULT_OUTPUT.relative_to(ROOT)
    )
    findings: list[str] = []
    if not path.is_file():
        actual = ""
        findings.append(f"checked evidence index is missing: {path}")
    else:
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(
                "checked evidence index differs from the canonical compiler output"
            )
    return {
        "schema_version": "mingli-evidence-index-canonical-audit-v1",
        "current": not findings,
        "records": len(records),
        "compiled_sha256": hashlib.sha256(expected.encode("utf-8")).hexdigest(),
        "checked_sha256": hashlib.sha256(actual.encode("utf-8")).hexdigest(),
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    records = compile_evidence_rules()
    rendered = render_jsonl(records)
    output = Path(args.output)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit("evidence rule index is stale")
        print(json.dumps({"status": "pass", "records": len(records)}))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(json.dumps({"status": "written", "records": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
