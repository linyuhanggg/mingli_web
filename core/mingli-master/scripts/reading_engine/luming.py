"""Deterministic early-Luming and sixty-Jiazi Nayin facts.

This module deliberately does not expose modern Bazi Ten-God calculations.  It
keeps the Li Xuzhong three-lives convention and the Luoluzi hidden-stem
three-yuan convention as separately named source lineages.
"""

from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from typing import Any, Iterator, Mapping, Sequence

from . import calendar_core
from . import evidence_rules
from .contracts import FactRef


SCHEMA_VERSION = "mingli-early-luming-facts-v1"
PROVIDER_VERSION = "1.2.0"
ADAPTER_VERSION = PROVIDER_VERSION
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
POSITIONS = ("year", "month", "day", "hour")
JIAZI = tuple(
    STEMS[index % len(STEMS)] + BRANCHES[index % len(BRANCHES)]
    for index in range(60)
)

_NAYIN_PAIRS = (
    "海中金", "炉中火", "大林木", "路旁土", "剑锋金", "山头火",
    "涧下水", "城头土", "白蜡金", "杨柳木", "泉中水", "屋上土",
    "霹雳火", "松柏木", "长流水", "沙中金", "山下火", "平地木",
    "壁上土", "金箔金", "覆灯火", "天河水", "大驿土", "钗钏金",
    "桑柘木", "大溪水", "沙中土", "天上火", "石榴木", "大海水",
)
NAYIN_BY_JIAZI = {
    ganzhi: _NAYIN_PAIRS[index // 2] for index, ganzhi in enumerate(JIAZI)
}

# The order is retained from the early-Luming source table, rather than from a
# modern Ten-God implementation.
HIDDEN_STEMS_BY_BRANCH: dict[str, tuple[str, ...]] = {
    "子": ("癸",),
    "丑": ("己", "癸", "辛"),
    "寅": ("甲", "丙", "戊"),
    "卯": ("乙",),
    "辰": ("戊", "乙", "癸"),
    "巳": ("丙", "戊", "庚"),
    "午": ("丁", "己"),
    "未": ("己", "丁", "乙"),
    "申": ("庚", "壬", "戊"),
    "酉": ("辛",),
    "戌": ("戊", "辛", "丁"),
    "亥": ("壬", "甲"),
}

LU_BY_STEM = {
    "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
    "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
}
TIANYI_BY_STEM: dict[str, tuple[str, str]] = {
    **{stem: ("丑", "未") for stem in "甲戊庚"},
    **{stem: ("子", "申") for stem in "乙己"},
    **{stem: ("亥", "酉") for stem in "丙丁"},
    "辛": ("午", "寅"),
    **{stem: ("卯", "巳") for stem in "壬癸"},
}
YIMA_BY_BRANCH = {
    **{branch: "申" for branch in "寅午戌"},
    **{branch: "寅" for branch in "申子辰"},
    **{branch: "亥" for branch in "巳酉丑"},
    **{branch: "巳" for branch in "亥卯未"},
}

# Li Xuzhong records a second, full-pillar recension beside the familiar
# branch-only Tianyi table.  It is emitted separately and never silently
# substituted for the branch table.
GUI_FULL_PILLAR_BY_STEM: dict[str, tuple[str, str]] = {
    **{stem: ("乙丑", "癸未") for stem in "甲戊庚"},
    "乙": ("庚子", "戊申"),
    "己": ("丙子", "甲申"),
    **{stem: ("丁酉", "乙亥") for stem in "丙丁"},
    "辛": ("丙寅", "戊午"),
    **{stem: ("乙卯", "癸巳") for stem in "壬癸"},
}

TAIYUAN_PROFILES = {
    "wuxing-jingji-use-taiyuan-v1": "calculate",
    "wuxing-jingji-no-taiyuan-v1": "exclude",
}

RULE_APPLICABILITY_UNRESOLVED_CHECKS = (
    "多条规则的并见、冲突、依赖与例外",
    "胎元、禄马贵与四柱纳音的整体权衡",
    "现实人生结论、吉凶等级与时限",
)


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _normalize_pillars(value: Mapping[str, str] | Sequence[str]) -> dict[str, str]:
    if isinstance(value, Mapping):
        pillars = {position: str(value.get(position) or "") for position in POSITIONS}
    else:
        rows = [str(item) for item in value]
        if len(rows) != len(POSITIONS):
            raise ValueError("early Luming calculation requires exactly four pillars")
        pillars = dict(zip(POSITIONS, rows))
    invalid = [item for item in pillars.values() if item not in NAYIN_BY_JIAZI]
    if invalid:
        raise ValueError(f"invalid sexagenary pillar(s): {invalid}")
    return pillars


def nayin_for(ganzhi: str) -> str:
    try:
        return NAYIN_BY_JIAZI[str(ganzhi)]
    except KeyError as exc:
        raise ValueError(f"invalid sexagenary value: {ganzhi!r}") from exc


def nayin_fact(ganzhi: str) -> dict[str, Any]:
    value = str(ganzhi)
    name = nayin_for(value)
    index = JIAZI.index(value) + 1
    return {
        "ganzhi": value,
        "name": name,
        "element": name[-1],
        "cycle_index": index,
        "source_row_id": f"LX-Q{index:03d}",
        "source_dependency_id": "luming.nayin.sixty-jiazi-table",
    }


def calculate_taiyuan(month_pillar: str) -> str:
    month = str(month_pillar)
    if month not in NAYIN_BY_JIAZI:
        raise ValueError(f"invalid month pillar: {month!r}")
    stem = STEMS[(STEMS.index(month[0]) + 1) % len(STEMS)]
    branch = BRANCHES[(BRANCHES.index(month[1]) + 3) % len(BRANCHES)]
    taiyuan = stem + branch
    if taiyuan not in NAYIN_BY_JIAZI:  # guards table/formula parity drift
        raise RuntimeError("Taiyuan formula produced a non-sexagenary pair")
    return taiyuan


def _matched_branch_positions(pillars: Mapping[str, str], target: str) -> list[str]:
    return [position for position in POSITIONS if pillars[position][1] == target]


def _matched_pillar_positions(
    pillars: Mapping[str, str], candidates: Sequence[str]
) -> list[str]:
    allowed = set(candidates)
    return [position for position in POSITIONS if pillars[position] in allowed]


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Build the same stable paths used by the Runtime fact index."""

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


@lru_cache(maxsize=64)
def _verified_source_rule(rule_id: str) -> evidence_rules.EvidenceRule:
    """Resolve exactly one active, classically verified Luming rule."""

    matches = [
        rule
        for rule in evidence_rules.production_evidence_rules()
        if rule.system == "luming-nayin" and rule.rule_id == rule_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Luming applicability requires exactly one evidence rule: {rule_id}"
        )
    rule = matches[0]
    if (
        not rule.runtime_active
        or rule.classical_binding_status != "verified"
        or not rule.classical_binding_digest
    ):
        raise RuntimeError(f"Luming source rule is not verified: {rule_id}")
    return rule


def _rule_applicability_adjudication(
    rule: evidence_rules.EvidenceRule,
) -> dict[str, Any]:
    verified = _verified_source_rule(rule.rule_id)
    return {
        "status": "adjudicated_rule_applicability",
        "decision_scope": "luming_nayin_source_rule_applicability",
        "rule_id": verified.rule_id,
        "local_rule_id": verified.local_rule_id,
        "rule_title": verified.title,
        "evidence_role": verified.evidence_role,
        "hard_verdict": None,
        "life_verdict": None,
        "source_ref": {
            "pack": verified.source_pack,
            "rule_id": verified.local_rule_id,
            "source_anchor": f"{verified.source_path}#{verified.local_rule_id}",
            "verification_status": verified.classical_binding_status,
            "binding_digest": verified.classical_binding_digest,
        },
        "unresolved_checks": list(RULE_APPLICABILITY_UNRESOLVED_CHECKS),
    }


def _valid_rule_applicability(row: Mapping[str, Any]) -> bool:
    rule_id = row.get("rule_id")
    if not isinstance(rule_id, str):
        return False
    try:
        rule = _verified_source_rule(rule_id)
    except RuntimeError:
        return False
    return row.get("applicability_adjudication") == (
        _rule_applicability_adjudication(rule)
    )


def _source_conditioned_patterns(output: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Adjudicate verified source-rule applicability without a life verdict."""

    indexed = {"chart_facts": {"output": output}}
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.luming-nayin.v1",
            provider_version=PROVIDER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.system != "luming-nayin":
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
                "source_dependency_id": "luming.source-conditioned-patterns",
                "applicability_adjudication": _rule_applicability_adjudication(
                    rule
                ),
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def _relation_facts(pillars: Mapping[str, str]) -> dict[str, Any]:
    lu: list[dict[str, Any]] = []
    ma: list[dict[str, Any]] = []
    gui: list[dict[str, Any]] = []
    for anchor in ("year", "day"):
        stem = pillars[anchor][0]
        branch = pillars[anchor][1]
        lu_target = LU_BY_STEM[stem]
        ma_target = YIMA_BY_BRANCH[branch]
        tianyi = list(TIANYI_BY_STEM[stem])
        full_pillars = list(GUI_FULL_PILLAR_BY_STEM[stem])
        common = {
            "anchor": anchor,
            "anchor_pillar": pillars[anchor],
            "status": "calculated_relation_not_verdict",
            "source_dependency_id": "luming.relations.lu-ma-gui",
        }
        lu.append(
            {
                **common,
                "relation": "干禄",
                "target_branch": lu_target,
                "matched_positions": _matched_branch_positions(pillars, lu_target),
            }
        )
        ma.append(
            {
                **common,
                "relation": "驿马",
                "target_branch": ma_target,
                "matched_positions": _matched_branch_positions(pillars, ma_target),
            }
        )
        gui.append(
            {
                **common,
                "relation": "天乙贵人",
                "recension": "tianyi-branch-v1",
                "candidates": tianyi,
                "matched_positions": [
                    position
                    for position in POSITIONS
                    if pillars[position][1] in set(tianyi)
                ],
            }
        )
        gui.append(
            {
                **common,
                "relation": "本家贵人命",
                "recension": "li-xuzhong-full-pillar-v1",
                "candidates": full_pillars,
                "matched_positions": _matched_pillar_positions(pillars, full_pillars),
            }
        )
    return {
        "lu": lu,
        "ma": ma,
        "gui": gui,
        "interpretation_status": "facts_only",
        "school_boundary": (
            "early-Luming source-named relations; not modern Bazi Ten Gods, "
            "Ziwei stars, or a verdict"
        ),
    }


def _taiyuan_fact(month_pillar: str, profile: str | None) -> dict[str, Any]:
    base = {
        "selected_profile": profile,
        "disputed": True,
        "source_dependency_id": "luming.three-yuan-and-taiyuan",
        "convention_conflict": (
            "Five-position sources calculate Taiyuan; the competing no-Taiyuan "
            "profile excludes it. No profile is selected silently."
        ),
    }
    if profile is None:
        return {**base, "status": "not_requested"}
    try:
        action = TAIYUAN_PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"unsupported early-Luming Taiyuan profile: {profile!r}") from exc
    if action == "exclude":
        return {**base, "status": "excluded_by_selected_profile"}
    ganzhi = calculate_taiyuan(month_pillar)
    return {
        **base,
        "status": "calculated",
        "ganzhi": ganzhi,
        "nayin": nayin_for(ganzhi),
        "formula": "month stem +1; month branch +3",
    }


def _derive_output(
    pillars: Mapping[str, str], taiyuan_profile: str | None
) -> dict[str, Any]:
    tianyuan = [pillars[position][0] for position in POSITIONS]
    diyuan = [pillars[position][1] for position in POSITIONS]
    nayin = [nayin_for(pillars[position]) for position in POSITIONS]
    hidden = [list(HIDDEN_STEMS_BY_BRANCH[pillars[position][1]]) for position in POSITIONS]
    pillar_facts = {
        position: {
            "ganzhi": pillars[position],
            "stem": pillars[position][0],
            "branch": pillars[position][1],
            "nayin": nayin_fact(pillars[position]),
        }
        for position in POSITIONS
    }
    output = {
        "four_pillars": copy.deepcopy(dict(pillars)),
        "nayin": {
            position: pillar_facts[position]["nayin"]["name"]
            for position in POSITIONS
        },
        "fact_scope": "early_luming_natal_facts",
        "pillars": {
            position: pillar_facts[position]
            for position in POSITIONS
        },
        "three_yuan_profiles": {
            "li_xuzhong": {
                "profile": "stem-lu/branch-ming/nayin-shen-v1",
                "tianyuan": tianyuan,
                "diyuan": diyuan,
                "renyuan_nayin": nayin,
                "source_dependency_id": "luming.three-yuan-and-taiyuan",
            },
            "luoluzi": {
                "profile": "stem/branch/hidden-stem-v1",
                "tianyuan": tianyuan,
                "zhiyuan": diyuan,
                "renyuan_hidden_stems": hidden,
                "source_dependency_id": "luming.three-yuan-and-taiyuan",
            },
        },
        "taiyuan": _taiyuan_fact(pillars["month"], taiyuan_profile),
        "relations": _relation_facts(pillars),
        "interpretation_status": "facts_only",
        "independent_lineage": "early-luming-nayin",
    }
    output["source_conditioned_patterns"] = _source_conditioned_patterns(output)
    return output


def natal_fact_digest(snapshot: Mapping[str, Any]) -> str:
    adapter = dict(snapshot.get("adapter") or {})
    adapter.pop("generated_at", None)
    calendar = snapshot.get("calendar_normalization") or {}
    identity = {
        "schema_version": snapshot.get("schema_version"),
        "system": snapshot.get("system"),
        "fact_layer_status": snapshot.get("fact_layer_status"),
        "fact_layer_scope": snapshot.get("fact_layer_scope"),
        "adapter": adapter,
        "normalized_input": (snapshot.get("input") or {}).get("normalized_input"),
        "calendar_digest": (
            calendar.get("calendar_digest") if isinstance(calendar, Mapping) else None
        ),
        "output": snapshot.get("output"),
        "source_lineage": snapshot.get("source_lineage"),
    }
    return _canonical_digest(identity)


def build_fact_layer(
    pillars: Mapping[str, str] | Sequence[str],
    *,
    taiyuan_profile: str | None = None,
    calendar_normalization: Mapping[str, Any] | None = None,
    input_provenance: Mapping[str, Any] | None = None,
    source: str = "calculated_or_validated_four_pillars",
    source_ref: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_pillars(pillars)
    calendar = copy.deepcopy(dict(calendar_normalization or {}))
    if calendar:
        if calendar.get("status") == "calculated":
            calendar_core.validate_calendar_digest(calendar)
        if dict(calendar.get("ganzhi") or {}) != normalized:
            raise ValueError("shared calendar pillars do not match early-Luming input")
    else:
        calendar = {
            "status": "unavailable_from_supplied_four_pillars",
            "ganzhi": copy.deepcopy(normalized),
        }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": "luming-nayin",
        "fact_layer_status": "calculated_early_luming_facts",
        "fact_layer_scope": "natal_static",
        "adapter": {
            "name": "mingli-master.early-luming",
            "version": PROVIDER_VERSION,
            "rule_profile": "early-luming-independent-lineage-v1",
            "generated_at": "deterministic-chart-identity",
        },
        "input": {
            "source": source,
            "source_ref": source_ref,
            "provenance": copy.deepcopy(dict(input_provenance or {})),
            "normalized_input": {
                "pillars": copy.deepcopy(normalized),
                "taiyuan_profile": taiyuan_profile,
            },
        },
        "calendar_normalization": calendar,
        "output": _derive_output(normalized, taiyuan_profile),
        "source_lineage": {
            "calculation": [
                {
                    "pack": "luming-nayin/li-xuzhong-mingshu",
                    "role": "sixty-Jiazi Nayin, three lives, and noble recensions",
                },
                {
                    "pack": "luming-nayin/luoluzi-sanming",
                    "role": "stem, branch, and hidden-human three-yuan profile",
                },
                {
                    "pack": "luming-nayin/wuxing-jingji",
                    "role": "hidden stems, Lu/Ma/Gui tables, and Taiyuan conflict",
                },
            ],
            "interpretation": [
                {
                    "pack": "luming-nayin/lantai-miaoxuan",
                    "role": "source-conditioned pattern interpretation only",
                }
            ],
        },
        "capabilities": {
            "allowed": ["early_luming_natal_facts", "source_bound_relations"],
            "blocked": ["modern_ten_god_translation", "unsourced_temporal_projection"],
        },
    }
    if calendar.get("status") == "calculated":
        payload["calendar_digest"] = calendar["calendar_digest"]
    payload["natal_fact_digest"] = natal_fact_digest(payload)
    return payload


def build_from_birth(
    civil_datetime: str,
    *,
    timezone_name: str,
    location: str,
    expected_pillars: Sequence[str] | None = None,
    zi_hour_policy: str = "midnight",
    taiyuan_profile: str | None = None,
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
    coordinate_accuracy_meters: float | None = None,
    time_basis_policy: str = "civil",
) -> dict[str, Any]:
    calendar = calendar_core.normalize_calendar(
        civil_datetime,
        timezone_name=timezone_name,
        location=location,
        longitude=longitude,
        latitude=latitude,
        coordinate_source=coordinate_source,
        coordinate_accuracy_meters=coordinate_accuracy_meters,
        zi_hour_policy=zi_hour_policy,
        time_basis_policy=time_basis_policy,
    )
    pillars = dict(calendar["ganzhi"])
    if expected_pillars is not None:
        expected = _normalize_pillars(expected_pillars)
        if expected != pillars:
            raise ValueError("birth data conflicts with supplied early-Luming pillars")
    facts = build_fact_layer(
        pillars,
        taiyuan_profile=taiyuan_profile,
        calendar_normalization=calendar,
        source="shared_calendar_birth_calculation",
        source_ref=str(civil_datetime),
    )
    facts["input"]["normalized_input"].update(
        {
            "birth_datetime": str(civil_datetime),
            "timezone": timezone_name,
            "location": location,
            "zi_hour_policy": zi_hour_policy,
            "time_basis_policy": time_basis_policy,
        }
    )
    facts["natal_fact_digest"] = natal_fact_digest(facts)
    return facts


def validate_facts(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Independently recompute all mechanical early-Luming facts."""

    codes: list[str] = []
    try:
        normalized_input = dict((payload.get("input") or {}).get("normalized_input") or {})
        pillars = _normalize_pillars(normalized_input.get("pillars") or {})
        profile = normalized_input.get("taiyuan_profile")
        expected_output = _derive_output(pillars, profile)
        actual_output = payload.get("output")
        if actual_output != expected_output:
            # Emit specific high-signal codes before the aggregate mismatch.
            actual_pillars = (actual_output or {}).get("pillars") or {}
            if any(
                ((actual_pillars.get(position) or {}).get("nayin") or {}).get("name")
                != nayin_for(pillars[position])
                for position in POSITIONS
            ):
                codes.append("luming_nayin_mismatch")
            actual_relations = (actual_output or {}).get("relations") or {}
            expected_relations = expected_output["relations"]
            if actual_relations.get("lu") != expected_relations["lu"]:
                codes.append("luming_lu_relation_mismatch")
            if actual_relations.get("ma") != expected_relations["ma"]:
                codes.append("luming_ma_relation_mismatch")
            if actual_relations.get("gui") != expected_relations["gui"]:
                codes.append("luming_gui_relation_mismatch")
            actual_patterns = (actual_output or {}).get(
                "source_conditioned_patterns"
            )
            if actual_patterns != expected_output["source_conditioned_patterns"]:
                codes.append("luming_source_pattern_mismatch")
            codes.append("luming_output_mismatch")
        patterns = (actual_output or {}).get("source_conditioned_patterns") or ()
        if not isinstance(patterns, list) or any(
            not isinstance(row, Mapping)
            or row.get("status") != "predicate_matched_not_verdict"
            or "verdict" in row
            or not _valid_rule_applicability(row)
            for row in patterns
        ):
            codes.append("luming_invalid_source_pattern")
        rendered = json.dumps(actual_output, ensure_ascii=False).lower()
        if "ten_god" in rendered or "十神" in rendered:
            codes.append("luming_modern_bazi_leak")
        calendar = payload.get("calendar_normalization") or {}
        if isinstance(calendar, Mapping) and calendar.get("status") == "calculated":
            try:
                calendar_core.validate_calendar_digest(calendar)
            except (KeyError, TypeError, ValueError):
                codes.append("luming_calendar_digest_mismatch")
        if payload.get("natal_fact_digest") != natal_fact_digest(payload):
            codes.append("luming_natal_digest_mismatch")
    except (KeyError, TypeError, ValueError):
        codes.append("luming_invalid_fact_structure")
    unique = list(dict.fromkeys(codes))
    return {"ok": not unique, "codes": unique}


def validate_fact_layer(payload: Mapping[str, Any]) -> None:
    """Raise when the independently recomputed fact layer does not match."""

    report = validate_facts(payload)
    if not report["ok"]:
        raise ValueError(
            "invalid early-Luming fact layer: " + ", ".join(report["codes"])
        )


__all__ = [
    "BRANCHES",
    "ADAPTER_VERSION",
    "GUI_FULL_PILLAR_BY_STEM",
    "HIDDEN_STEMS_BY_BRANCH",
    "JIAZI",
    "LU_BY_STEM",
    "NAYIN_BY_JIAZI",
    "PROVIDER_VERSION",
    "STEMS",
    "TIANYI_BY_STEM",
    "YIMA_BY_BRANCH",
    "build_fact_layer",
    "build_from_birth",
    "calculate_taiyuan",
    "natal_fact_digest",
    "nayin_fact",
    "nayin_for",
    "validate_facts",
    "validate_fact_layer",
]
