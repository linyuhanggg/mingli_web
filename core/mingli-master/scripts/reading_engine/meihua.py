"""Deterministic Meihua Yishu facts for explicit source-declared methods.

The caller supplies the method and its structured facts.  This module performs
calendar normalization dependent arithmetic and plate construction only; it
does not classify prose observations or turn body/use relations into verdicts.
"""

from __future__ import annotations

import copy
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Mapping

import yaml

from . import calendar_core, evidence_rules
from .contracts import FactRef, canonical_digest


SCHEMA_VERSION = "mingli-meihua-facts-v1"
PROVIDER_VERSION = "1.1.0"
ADAPTER_VERSION = PROVIDER_VERSION
TABLE_PROFILE = "meihua-explicit-methods-v1"
ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = ROOT / "references" / "matrices" / "meihua-source-tables-v1.yaml"
TABLE_RELATIVE_PATH = "references/matrices/meihua-source-tables-v1.yaml"
TABLE_SHA256 = "2a506471d4fe5c5ab0380af621123fe141a3833663f3497def46f78fd73e8e4a"
BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")
METHODS = (
    "time",
    "supplied_number",
    "sound_count",
    "observation",
    "supplied_hexagram",
)
METHOD_FACT_FIELDS = {
    "time": frozenset({"casting_method"}),
    "supplied_number": frozenset({"casting_method", "number", "provenance"}),
    "sound_count": frozenset({"casting_method", "count", "observation_source"}),
    "observation": frozenset(
        {"casting_method", "upper_trigram", "lower_trigram", "observation_source"}
    ),
    "supplied_hexagram": frozenset(
        {"casting_method", "upper_trigram", "lower_trigram", "moving_line", "provenance"}
    ),
}


@lru_cache(maxsize=1)
def _tables() -> dict[str, Any]:
    raw = TABLE_PATH.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != TABLE_SHA256:
        raise RuntimeError(
            f"Meihua source table hash mismatch: expected {TABLE_SHA256}, got {actual}"
        )
    payload = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Meihua source table must be a mapping")
    if payload.get("schema_version") != "mingli-meihua-source-tables-v1":
        raise RuntimeError("unsupported Meihua source table schema")
    return payload


def source_table_digest() -> str:
    _tables()
    return TABLE_SHA256


def _positive_integer(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _trigram_number(name: str) -> int:
    target = str(name)
    for number, profile in _tables()["trigrams"].items():
        if profile["name"] == target:
            return int(number)
    raise ValueError(f"invalid Meihua trigram: {name!r}")


def trigram_for_number(value: int) -> dict[str, Any]:
    number = _positive_integer(value, label="trigram number")
    normalized = (number - 1) % 8 + 1
    profile = copy.deepcopy(_tables()["trigrams"][normalized])
    profile["number"] = normalized
    profile["source_dependency_id"] = "meihua.cast.explicit-methods-and-moduli"
    return profile


def _moving_line(value: int) -> int:
    total = _positive_integer(value, label="moving total")
    return (total - 1) % 6 + 1


def _hexagram_from_trigrams(upper: str, lower: str) -> dict[str, Any]:
    upper_number = _trigram_number(upper)
    lower_number = _trigram_number(lower)
    trigrams = _tables()["trigrams"]
    upper_profile = trigrams[upper_number]
    lower_profile = trigrams[lower_number]
    name = _tables()["hexagram_names"][f"{upper}/{lower}"]
    return {
        "name": name,
        "upper_trigram": upper,
        "lower_trigram": lower,
        "upper_number": upper_number,
        "lower_number": lower_number,
        "lines_bottom_up": [
            int(bit)
            for bit in str(lower_profile["bits_bottom_up"])
            + str(upper_profile["bits_bottom_up"])
        ],
        "source_dependency_id": "meihua.plate.main-mutual-changed",
    }


def _hexagram_from_bits(bits: list[int]) -> dict[str, Any]:
    if len(bits) != 6 or any(value not in {0, 1} for value in bits):
        raise ValueError("Meihua hexagram requires six binary lines")
    by_bits = {
        str(profile["bits_bottom_up"]): str(profile["name"])
        for profile in _tables()["trigrams"].values()
    }
    lower_bits = "".join(str(value) for value in bits[:3])
    upper_bits = "".join(str(value) for value in bits[3:])
    return _hexagram_from_trigrams(by_bits[upper_bits], by_bits[lower_bits])


@lru_cache(maxsize=1)
def _hexagram_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    names = [str(row["name"]) for row in _tables()["trigrams"].values()]
    for upper in names:
        for lower in names:
            profile = _hexagram_from_trigrams(upper, lower)
            catalog[profile["name"]] = profile
    if len(catalog) != 64:
        raise RuntimeError("Meihua source table must contain 64 unique hexagrams")
    return catalog


def build_hexagram_catalog() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(_hexagram_catalog())


def _body_use(primary: Mapping[str, Any], moving_line: int) -> dict[str, Any]:
    use_position = "lower" if moving_line <= 3 else "upper"
    body_position = "upper" if use_position == "lower" else "lower"
    body_name = str(primary[f"{body_position}_trigram"])
    use_name = str(primary[f"{use_position}_trigram"])
    body_element = _tables()["trigrams"][_trigram_number(body_name)]["element"]
    use_element = _tables()["trigrams"][_trigram_number(use_name)]["element"]
    relation = _relation_to_body(use_element, body_element, actor_label="用")
    return {
        "body": {
            "position": body_position,
            "trigram": body_name,
            "element": body_element,
        },
        "use": {
            "position": use_position,
            "trigram": use_name,
            "element": use_element,
        },
        "relation": relation,
        "status": "calculated_relation_not_verdict",
        "source_dependency_id": "meihua.body-use-elements-season",
    }


def _relation_to_body(
    actor_element: str, body_element: str, *, actor_label: str
) -> str:
    relations = _tables()["five_element_relations"]
    if actor_element == body_element:
        return "比和"
    if relations["generates"][actor_element] == body_element:
        return f"{actor_label}生体"
    if relations["generates"][body_element] == actor_element:
        return f"体生{actor_label}"
    if relations["controls"][actor_element] == body_element:
        return f"{actor_label}克体"
    if relations["controls"][body_element] == actor_element:
        return f"体克{actor_label}"
    raise RuntimeError("incomplete Meihua five-element relation table")


def _body_relation_facts(
    *,
    primary: Mapping[str, Any],
    mutual: Mapping[str, Any],
    changed: Mapping[str, Any],
    moving_line: int,
) -> list[dict[str, Any]]:
    body_use = _body_use(primary, moving_line)
    body = body_use["body"]
    nodes = [
        ("primary_use", body_use["use"]["position"], body_use["use"]["trigram"], "用"),
        ("mutual", "lower", mutual["lower_trigram"], "互下"),
        ("mutual", "upper", mutual["upper_trigram"], "互上"),
        ("changed", "lower", changed["lower_trigram"], "变下"),
        ("changed", "upper", changed["upper_trigram"], "变上"),
    ]
    facts: list[dict[str, Any]] = []
    for source_plate, position, trigram, label in nodes:
        element = _tables()["trigrams"][_trigram_number(str(trigram))]["element"]
        facts.append(
            {
                "source_plate": source_plate,
                "position": position,
                "trigram": trigram,
                "element": element,
                "body": copy.deepcopy(body),
                "relation": _relation_to_body(
                    element, str(body["element"]), actor_label=label
                ),
                "status": "calculated_relation_not_verdict",
                "source_dependency_id": "meihua.body-use-elements-season",
            }
        )
    return facts


_RELATION_CANDIDATE_KEYS = {
    "用生体": "use_generates_body",
    "体生用": "body_generates_use",
    "用克体": "use_controls_body",
    "体克用": "body_controls_use",
    "比和": "same_element",
}
_MEIHUA_ACTOR_LABELS = frozenset({"用", "互下", "互上", "变下", "变上"})
_RELATION_SOURCE_POLARITY = {
    "use_generates_body": "supportive",
    "actor_generates_body": "supportive",
    "body_generates_use": "depleting",
    "body_generates_actor": "depleting",
    "use_controls_body": "adverse",
    "actor_controls_body": "adverse",
    "body_controls_use": "favorable",
    "body_controls_actor": "favorable",
    "same_element": "harmonious",
}
RELATION_ADJUDICATION_UNRESOLVED_CHECKS = (
    "具体问题中的体用取义、领域例外与外应",
    "本卦、互卦、变卦关系的并见权重及月令旺衰",
    "现实事件成败、吉凶程度与应期",
)


def _relation_candidate_key(relation: str) -> str:
    """Normalize primary, mutual and changed body/use relation labels.

    The fact layer names the actor by plate position (for example
    ``互下生体`` and ``体生变上``).  Those labels share the same five-element
    relation vocabulary as the primary ``用`` relation, but they cannot be
    looked up as one of the five primary strings verbatim.
    """

    direct = _RELATION_CANDIDATE_KEYS.get(relation)
    if direct is not None:
        return direct
    if relation.endswith("生体"):
        actor = relation[:-2]
        if actor in _MEIHUA_ACTOR_LABELS:
            return "actor_generates_body"
    if relation.endswith("克体"):
        actor = relation[:-2]
        if actor in _MEIHUA_ACTOR_LABELS:
            return "actor_controls_body"
    if relation.startswith("体生"):
        actor = relation[2:]
        if actor in _MEIHUA_ACTOR_LABELS:
            return "body_generates_actor"
    if relation.startswith("体克"):
        actor = relation[2:]
        if actor in _MEIHUA_ACTOR_LABELS:
            return "body_controls_actor"
    raise RuntimeError(f"unsupported Meihua body relation: {relation}")


@lru_cache(maxsize=3)
def _verified_relation_rule(local_rule_id: str) -> evidence_rules.EvidenceRule:
    matches = [
        rule
        for rule in evidence_rules.production_evidence_rules()
        if rule.system == "divination" and rule.local_rule_id == local_rule_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Meihua relation adjudication requires exactly one evidence rule: "
            f"{local_rule_id}"
        )
    rule = matches[0]
    if (
        not rule.runtime_active
        or rule.classical_binding_status != "verified"
        or not rule.classical_binding_digest
    ):
        raise RuntimeError(
            f"Meihua relation rule is not source verified: {local_rule_id}"
        )
    return rule


def _relation_source_ref(local_rule_id: str) -> dict[str, str]:
    rule = _verified_relation_rule(local_rule_id)
    return {
        "pack": rule.source_pack,
        "rule_id": rule.local_rule_id,
        "source_anchor": f"{rule.source_path}#{rule.local_rule_id}",
        "verification_status": rule.classical_binding_status,
        "binding_digest": rule.classical_binding_digest,
    }


def _relation_adjudication(
    *,
    relation_key: str,
    source_plate: str,
) -> dict[str, Any]:
    try:
        source_polarity = _RELATION_SOURCE_POLARITY[relation_key]
    except KeyError as exc:
        raise RuntimeError(
            f"unsupported Meihua relation adjudication key: {relation_key}"
        ) from exc
    rule_ids = ["MR-04-02", "MR-04-01"]
    if source_plate in {"mutual", "changed"}:
        rule_ids.append("MR-04-04")
    return {
        "status": "adjudicated_relation_polarity",
        "decision_scope": "meihua_body_use_relation",
        "relation_key": relation_key,
        "source_polarity": source_polarity,
        "hard_verdict": None,
        "event_verdict": None,
        "source_refs": [_relation_source_ref(rule_id) for rule_id in rule_ids],
        "unresolved_checks": list(RELATION_ADJUDICATION_UNRESOLVED_CHECKS),
    }


def _valid_relation_candidate(candidate: Mapping[str, Any]) -> bool:
    relation_key = candidate.get("relation_key")
    source_plate = candidate.get("source_plate")
    if not isinstance(relation_key, str) or not isinstance(source_plate, str):
        return False
    try:
        expected = _relation_adjudication(
            relation_key=relation_key,
            source_plate=source_plate,
        )
    except RuntimeError:
        return False
    return (
        candidate.get("status") == "relation_adjudicated_not_event_verdict"
        and candidate.get("verification_status") == "verified"
        and candidate.get("hard_verdict") is None
        and candidate.get("relation_adjudication") == expected
    )


def _valid_interpretive_adjudication(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    candidates = value.get("relation_candidates")
    return (
        value.get("status") == "source_adjudicated_relations"
        and value.get("verification_status") == "verified"
        and value.get("hard_verdict") is None
        and value.get("requires_classical_adjudication") is False
        and value.get("requires_synthesis_adjudication") is True
        and isinstance(candidates, list)
        and bool(candidates)
        and all(
            isinstance(candidate, Mapping)
            and _valid_relation_candidate(candidate)
            for candidate in candidates
        )
    )


def _interpretive_candidates(
    *,
    body_relation_facts: list[dict[str, Any]],
    seasonal_strength: Mapping[str, Any],
) -> dict[str, Any]:
    """Adjudicate each source relation while withholding event synthesis."""

    seasonal_keys = {
        ("primary_use", "upper"): "use",
        ("primary_use", "lower"): "use",
        ("mutual", "upper"): "mutual_upper",
        ("mutual", "lower"): "mutual_lower",
        ("changed", "upper"): "changed_upper",
        ("changed", "lower"): "changed_lower",
    }
    candidates: list[dict[str, Any]] = []
    for relation_fact in body_relation_facts:
        relation = str(relation_fact["relation"])
        relation_key = _relation_candidate_key(relation)
        seasonal_key = seasonal_keys.get(
            (str(relation_fact["source_plate"]), str(relation_fact["position"]))
        )
        seasonal = seasonal_strength.get(seasonal_key) if seasonal_key else None
        candidates.append(
            {
                "candidate_id": (
                    f"meihua.{relation_fact['source_plate']}."
                    f"{relation_fact['position']}.{relation_key}"
                ),
                "source_plate": str(relation_fact["source_plate"]),
                "position": str(relation_fact["position"]),
                "relation": relation,
                "relation_key": relation_key,
                "actor": {
                    "trigram": str(relation_fact["trigram"]),
                    "element": str(relation_fact["element"]),
                },
                "body": copy.deepcopy(relation_fact["body"]),
                "seasonal_state": (
                    str(seasonal["state"])
                    if isinstance(seasonal, Mapping) and seasonal.get("state")
                    else None
                ),
                "rule_id": "MR-04-02",
                "status": "relation_adjudicated_not_event_verdict",
                "hard_verdict": None,
                "verification_status": "verified",
                "source_pack": "divination/meihua-yishu",
                "source_anchor": (
                    "references/books/divination/meihua-yishu/rules.md#MR-04-02"
                ),
                "source_dependency_id": (
                    "meihua.classical-adjudication.body-use-candidates"
                ),
                "relation_adjudication": _relation_adjudication(
                    relation_key=relation_key,
                    source_plate=str(relation_fact["source_plate"]),
                ),
            }
        )
    return {
        "schema_version": "mingli-meihua-interpretive-candidates-v1",
        "status": "source_adjudicated_relations",
        "hard_verdict": None,
        "verification_status": "verified",
        "relation_candidates": candidates,
        "requires_classical_adjudication": False,
        "requires_synthesis_adjudication": True,
        "boundary": (
            "body/use relation polarity is source-adjudicated; multiple relations, "
            "seasonal strength and question scope still require synthesis before "
            "吉凶、成败、应期 or any final conclusion"
        ),
    }


def cast_from_totals(
    *,
    upper_total: int,
    lower_total: int,
    moving_total: int,
) -> dict[str, Any]:
    """Build main, mutual, changed, and body/use facts from fixed totals."""

    upper = trigram_for_number(upper_total)
    lower = trigram_for_number(lower_total)
    moving_line = _moving_line(moving_total)
    primary = _hexagram_from_trigrams(upper["name"], lower["name"])
    changed_bits = list(primary["lines_bottom_up"])
    changed_bits[moving_line - 1] = 1 - changed_bits[moving_line - 1]
    changed = _hexagram_from_bits(changed_bits)
    mutual_source = "primary"
    mutual_bits_source = list(primary["lines_bottom_up"])
    exception_profile = None
    if primary["name"] in {"乾为天", "坤为地"}:
        mutual_source = "changed"
        mutual_bits_source = list(changed["lines_bottom_up"])
        exception_profile = "pure_qian_kun"
    mutual_bits = mutual_bits_source[1:4] + mutual_bits_source[2:5]
    mutual = _hexagram_from_bits(mutual_bits)
    mutual["source_plate"] = mutual_source
    mutual["exception_profile"] = exception_profile
    body_use = _body_use(primary, moving_line)
    return {
        "upper_trigram": copy.deepcopy(upper),
        "lower_trigram": copy.deepcopy(lower),
        "moving_line": moving_line,
        "moving_lines": [moving_line],
        "primary_hexagram": primary,
        "mutual_hexagram": mutual,
        "changed_hexagram": changed,
        "body_use": body_use,
        "body_relation_facts": _body_relation_facts(
            primary=primary,
            mutual=mutual,
            changed=changed,
            moving_line=moving_line,
        ),
        "totals": {
            "upper": int(upper_total),
            "lower": int(lower_total),
            "moving": int(moving_total),
        },
    }


def seasonal_strength_for(trigram: str, month_branch: str) -> dict[str, Any]:
    name = str(trigram)
    _trigram_number(name)
    branch = str(month_branch)
    season = _tables()["season_by_month_branch"].get(branch)
    if season is None:
        raise ValueError(f"invalid calendar month branch: {month_branch!r}")
    profile = _tables()["seasonal_strength"][season]
    state = "平"
    if name in profile["旺"]:
        state = "旺"
    elif name in profile["衰"]:
        state = "衰"
    return {
        "trigram": name,
        "month_branch": branch,
        "season": season,
        "state": state,
        "status": "calculated_strength_not_verdict",
        "source_dependency_id": "meihua.body-use-elements-season",
    }


def _required_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{label} must be a non-empty structured object")
    return copy.deepcopy(dict(value))


def _method_totals(
    method_facts: Mapping[str, Any], calendar: Mapping[str, Any]
) -> tuple[int, int, int, dict[str, Any], dict[str, Any]]:
    method = str(method_facts.get("casting_method") or "")
    if method not in METHODS:
        raise ValueError("Meihua requires one explicit supported casting_method")
    ganzhi = calendar.get("ganzhi") or {}
    lunar = (
        calendar.get("effective_lunar_date")
        or calendar.get("lunar_date")
        or {}
    )
    hour_ganzhi = str(ganzhi.get("hour") or "")
    if len(hour_ganzhi) != 2 or hour_ganzhi[1] not in BRANCHES:
        raise ValueError("Meihua requires shared calendar hour Ganzhi")
    hour_number = BRANCHES.index(hour_ganzhi[1]) + 1
    provenance: dict[str, Any]
    inputs: dict[str, Any]
    if method == "time":
        lunar_year = _positive_integer(lunar.get("year"), label="lunar year")
        year_number = (lunar_year - 4) % 12 + 1
        month = _positive_integer(lunar.get("month"), label="lunar month")
        day = _positive_integer(lunar.get("day"), label="lunar day")
        upper_total = year_number + month + day
        lower_total = upper_total + hour_number
        moving_total = lower_total
        inputs = {
            "lunar_year": lunar_year,
            "year_branch_number": year_number,
            "lunar_month": month,
            "lunar_day": day,
            "lunar_leap_month": bool(lunar.get("is_leap_month")),
            "hour_branch_number": hour_number,
        }
        provenance = {
            "kind": "shared_calendar_time_cast",
            "calendar_digest": calendar["calendar_digest"],
        }
    elif method in {"supplied_number", "sound_count"}:
        field = "number" if method == "supplied_number" else "count"
        number = _positive_integer(method_facts.get(field), label=field)
        provenance_field = (
            "provenance" if method == "supplied_number" else "observation_source"
        )
        provenance = _required_mapping(
            method_facts.get(provenance_field), label=provenance_field
        )
        upper_total = number
        lower_total = hour_number
        moving_total = number + hour_number
        inputs = {field: number, "hour_branch_number": hour_number}
    elif method == "observation":
        upper_name = str(method_facts.get("upper_trigram") or "")
        lower_name = str(method_facts.get("lower_trigram") or "")
        upper_total = _trigram_number(upper_name)
        lower_total = _trigram_number(lower_name)
        moving_total = upper_total + lower_total + hour_number
        provenance = _required_mapping(
            method_facts.get("observation_source"), label="observation_source"
        )
        inputs = {
            "upper_trigram": upper_name,
            "lower_trigram": lower_name,
            "hour_branch_number": hour_number,
        }
    else:
        upper_name = str(method_facts.get("upper_trigram") or "")
        lower_name = str(method_facts.get("lower_trigram") or "")
        upper_total = _trigram_number(upper_name)
        lower_total = _trigram_number(lower_name)
        moving_total = _positive_integer(
            method_facts.get("moving_line"), label="moving line"
        )
        if moving_total > 6:
            raise ValueError("supplied Meihua moving line must be within 1..6")
        provenance = _required_mapping(
            method_facts.get("provenance"), label="provenance"
        )
        inputs = {
            "upper_trigram": upper_name,
            "lower_trigram": lower_name,
            "moving_line": moving_total,
        }
    inputs["hour_branch_number"] = hour_number
    return upper_total, lower_total, moving_total, inputs, provenance


def _fact_digest(payload: Mapping[str, Any]) -> str:
    identity = copy.deepcopy(dict(payload))
    identity.pop("fact_digest", None)
    return canonical_digest(identity)


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Build the stable paths consumed by the source-evidence matcher."""

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
    output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Expose verified casting/plate rules without creating a verdict."""

    indexed = {"chart_facts": {"output": dict(output)}}
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.meihua.v1",
            provider_version=PROVIDER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )
    allowed_packs = frozenset(
        {
            "divination/huangji-jingshi",
            "divination/meihua-yishu",
            "divination/zhouyi-zhezhong",
        }
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.source_pack not in allowed_packs:
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
                "source_dependency_id": "meihua.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def build_from_method(
    method_facts: Mapping[str, Any],
    *,
    calendar_facts: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(method_facts, Mapping):
        raise ValueError("Meihua method facts must be a structured object")
    method = str(method_facts.get("casting_method") or "")
    if method not in METHODS:
        raise ValueError("Meihua requires one explicit supported casting_method")
    unexpected = sorted(set(method_facts) - METHOD_FACT_FIELDS[method])
    if unexpected:
        raise ValueError(
            "Meihua method facts contain unsupported fields: "
            + ", ".join(str(field) for field in unexpected)
        )
    calendar = copy.deepcopy(dict(calendar_facts))
    calendar_core.validate_calendar_digest(calendar)
    upper_total, lower_total, moving_total, inputs, provenance = _method_totals(
        method_facts, calendar
    )
    plate = cast_from_totals(
        upper_total=upper_total,
        lower_total=lower_total,
        moving_total=moving_total,
    )
    casting = {
        "method": method,
        "inputs": inputs,
        "provenance": provenance,
        "natural_language_classification": False,
        "source_dependency_id": "meihua.cast.explicit-methods-and-moduli",
    }
    casting["casting_digest"] = canonical_digest(casting)
    month_ganzhi = str((calendar.get("ganzhi") or {}).get("month") or "")
    if len(month_ganzhi) != 2 or month_ganzhi[1] not in BRANCHES:
        raise ValueError("Meihua requires shared Jie-bounded calendar month")
    body_use = plate["body_use"]
    seasonal = {
        "body": seasonal_strength_for(
            body_use["body"]["trigram"], month_ganzhi[1]
        ),
        "use": seasonal_strength_for(
            body_use["use"]["trigram"], month_ganzhi[1]
        ),
        "primary_upper": seasonal_strength_for(
            plate["primary_hexagram"]["upper_trigram"], month_ganzhi[1]
        ),
        "primary_lower": seasonal_strength_for(
            plate["primary_hexagram"]["lower_trigram"], month_ganzhi[1]
        ),
        "mutual_upper": seasonal_strength_for(
            plate["mutual_hexagram"]["upper_trigram"], month_ganzhi[1]
        ),
        "mutual_lower": seasonal_strength_for(
            plate["mutual_hexagram"]["lower_trigram"], month_ganzhi[1]
        ),
        "changed_upper": seasonal_strength_for(
            plate["changed_hexagram"]["upper_trigram"], month_ganzhi[1]
        ),
        "changed_lower": seasonal_strength_for(
            plate["changed_hexagram"]["lower_trigram"], month_ganzhi[1]
        ),
    }
    interpretive_candidates = _interpretive_candidates(
        body_relation_facts=plate["body_relation_facts"],
        seasonal_strength=seasonal,
    )
    output = {
        "system_identity": "meihua-yishu",
        "casting": casting,
        "casting_method": method,
        **plate,
        "seasonal_strength": seasonal,
        "interpretive_candidates": interpretive_candidates,
        "source_conditioned_patterns": _source_conditioned_patterns(
            {
                "totals": {
                    "upper": int(upper_total),
                    "lower": int(lower_total),
                    "moving": int(moving_total),
                },
                "upper_trigram": plate["upper_trigram"],
                "lower_trigram": plate["lower_trigram"],
                "primary_hexagram": plate["primary_hexagram"],
            }
        ),
        "calendar": {
            "month_ganzhi": month_ganzhi,
            "month_branch": month_ganzhi[1],
            "hour_ganzhi": calendar["ganzhi"]["hour"],
        },
        "interpretation_status": "facts_only",
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": "meihua",
        "fact_layer_status": "calculated_meihua_facts",
        "adapter": {
            "name": "mingli-master.meihua",
            "version": PROVIDER_VERSION,
            "rule_profile": TABLE_PROFILE,
            "source_artifact": TABLE_RELATIVE_PATH,
            "source_artifact_sha256": TABLE_SHA256,
            "generated_at": "deterministic-chart-identity",
        },
        "input": {
            "normalized_method_facts": copy.deepcopy(dict(method_facts)),
        },
        "calendar_normalization": calendar,
        "calendar_digest": calendar["calendar_digest"],
        "output": output,
        "source_lineage": {
            "calculation": [
                {
                    "pack": "divination/meihua-yishu",
                    "role": "casting, mutual/change, body/use, and season tables",
                },
                {
                    "pack": "divination/huangji-jingshi",
                    "role": "pre-heaven trigram number lineage only",
                },
            ],
            "interpretation": [
                {
                    "pack": "divination/zhouyi-zhezhong",
                    "role": "hexagram and line interpretation only",
                }
            ],
        },
        "capabilities": {
            "allowed": ["explicit_method_cast", "body_use_relations", "seasonal_facts"],
            "blocked": [
                "implicit_random_method",
                "natural_language_observation_classification",
                "liuyao_najia_or_six_relatives",
                "unsourced_verdict",
            ],
        },
    }
    payload["fact_digest"] = _fact_digest(payload)
    return payload


def validate_fact_layer(payload: Mapping[str, Any]) -> dict[str, Any]:
    codes: list[str] = []
    try:
        if (payload.get("adapter") or {}).get(
            "source_artifact_sha256"
        ) != source_table_digest():
            codes.append("meihua_source_table_digest_mismatch")
        calendar = payload.get("calendar_normalization") or {}
        try:
            calendar_core.validate_calendar_digest(calendar)
        except (KeyError, TypeError, ValueError):
            codes.append("meihua_calendar_digest_mismatch")
        method_facts = (payload.get("input") or {}).get(
            "normalized_method_facts"
        ) or {}
        rebuilt = build_from_method(method_facts, calendar_facts=calendar)
        if not _valid_interpretive_adjudication(
            (payload.get("output") or {}).get("interpretive_candidates")
        ):
            codes.append("meihua_invalid_relation_adjudication")
        if payload.get("output") != rebuilt["output"]:
            codes.append("meihua_output_mismatch")
        if payload.get("fact_digest") != _fact_digest(payload):
            codes.append("meihua_fact_digest_mismatch")
        if payload.get("fact_digest") != rebuilt["fact_digest"]:
            codes.append("meihua_recomputed_digest_mismatch")
    except (KeyError, TypeError, ValueError, RuntimeError):
        codes.append("meihua_invalid_fact_structure")
    unique = list(dict.fromkeys(codes))
    return {"ok": not unique, "codes": unique}


__all__ = [
    "ADAPTER_VERSION",
    "METHODS",
    "METHOD_FACT_FIELDS",
    "PROVIDER_VERSION",
    "TABLE_RELATIVE_PATH",
    "TABLE_SHA256",
    "build_from_method",
    "build_hexagram_catalog",
    "cast_from_totals",
    "seasonal_strength_for",
    "source_table_digest",
    "trigram_for_number",
    "validate_fact_layer",
]
