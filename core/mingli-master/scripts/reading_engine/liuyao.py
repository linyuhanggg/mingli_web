"""Deterministic Jing-Fang Liuyao fact calculation.

The module accepts only a preserved six-line cast.  It calculates plate facts,
source-declared relations, and narrowly source-bound question-role decisions.
It may identify a specific useful-spirit line only through checked bounded
rules; it never derives a cast from prose or time or creates an event verdict.
"""

from __future__ import annotations

import copy
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import yaml

from . import calendar_core, evidence_rules
from .contracts import FactRef, canonical_digest


SCHEMA_VERSION = "mingli-liuyao-facts-v1"
PROVIDER_VERSION = "1.4.0"
ADAPTER_VERSION = PROVIDER_VERSION
TABLE_PROFILE = "jingfang-eight-palace-najia-v1"
ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = ROOT / "references" / "matrices" / "liuyao-jingfang-tables-v1.yaml"
TABLE_RELATIVE_PATH = "references/matrices/liuyao-jingfang-tables-v1.yaml"
TABLE_SHA256 = "bbc0d53684e6f544b1fc1504b3fccb7ac8c099944d6af058154d1d1535cc5c54"
TRANSACTION_CAST_SEED_KEY = "_transaction_liuyao_cast_seed_v1"
TRANSACTION_CAST_SEED_SOURCE = "transaction_csprng_v1"

STEMS = tuple("甲乙丙丁戊己庚辛壬癸")
BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")
JIAZI = tuple(
    STEMS[index % 10] + BRANCHES[index % 12]
    for index in range(60)
)
RELATIVES = ("兄弟", "子孙", "妻财", "官鬼", "父母")
QUESTION_CLASSES = ("finance",)
FINANCE_ROLE_RULE_ID = "divination/huangjin-ce#HJC-R009"
TWO_PRESENT_USEFUL_SPIRIT_RULE_ID = "divination/zengshan-buyi#ZR-04-04"
SEASONAL_STRENGTH_RULE_ID = "divination/zengshan-buyi#ZR-05-05"


@lru_cache(maxsize=1)
def _tables() -> dict[str, Any]:
    raw = TABLE_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != TABLE_SHA256:
        raise RuntimeError(
            f"Liuyao table hash mismatch: expected {TABLE_SHA256}, got {digest}"
        )
    data = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Liuyao source table must be a mapping")
    if data.get("schema_version") != "mingli-liuyao-jingfang-tables-v1":
        raise RuntimeError("unsupported Liuyao source table schema")
    return data


def source_table_digest() -> str:
    _tables()
    return TABLE_SHA256


def _toggle(bits: str, lines: Sequence[int]) -> str:
    output = list(bits)
    for line in lines:
        index = int(line) - 1
        if index not in range(6):
            raise ValueError(f"invalid Liuyao line number: {line!r}")
        output[index] = "0" if output[index] == "1" else "1"
    return "".join(output)


@lru_cache(maxsize=1)
def _catalog_by_name() -> dict[str, dict[str, Any]]:
    tables = _tables()
    trigram_by_bits = {
        str(profile["bits_bottom_up"]): name
        for name, profile in tables["trigrams"].items()
    }
    catalog: dict[str, dict[str, Any]] = {}
    for palace, palace_profile in tables["palaces"].items():
        pure = str(tables["trigrams"][palace]["bits_bottom_up"]) * 2
        for stage, name in zip(
            tables["palace_stages"], palace_profile["names"]
        ):
            bits = _toggle(pure, stage["change_pattern"])
            lower_bits, upper_bits = bits[:3], bits[3:]
            if lower_bits not in trigram_by_bits or upper_bits not in trigram_by_bits:
                raise RuntimeError("source table generated an unknown trigram")
            catalog[str(name)] = {
                "name": str(name),
                "king_wen_number": int(tables["king_wen_numbers"][name]),
                "bits_bottom_up": bits,
                "lower_trigram": trigram_by_bits[lower_bits],
                "upper_trigram": trigram_by_bits[upper_bits],
                "palace": palace,
                "palace_element": palace_profile["element"],
                "stage": stage["id"],
                "shi_line": int(stage["shi_line"]),
                "ying_line": int(stage["ying_line"]),
                "source_dependency_id": "liuyao.plate.hexagram-palace-shiying",
            }
    if len(catalog) != 64 or len({row["bits_bottom_up"] for row in catalog.values()}) != 64:
        raise RuntimeError("Liuyao eight-palace source table must enumerate 64 plates")
    return catalog


@lru_cache(maxsize=1)
def _catalog_by_bits() -> dict[str, dict[str, Any]]:
    return {
        profile["bits_bottom_up"]: profile
        for profile in _catalog_by_name().values()
    }


def build_hexagram_catalog() -> dict[str, dict[str, Any]]:
    """Return the complete immutable-by-copy eight-palace catalog."""

    return copy.deepcopy(_catalog_by_name())


def _normalize_tosses(tosses: Sequence[int]) -> tuple[int, ...]:
    if isinstance(tosses, (str, bytes)):
        raise ValueError("Liuyao cast must contain six numeric tosses")
    values = tuple(tosses)
    if len(values) != 6 or any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value not in {6, 7, 8, 9}
        for value in values
    ):
        raise ValueError("Liuyao cast requires exactly six tosses valued 6, 7, 8, or 9")
    return tuple(int(value) for value in values)


def cast_from_seed(seed: str) -> dict[str, Any]:
    """Create six reproducible three-coin tosses from a preserved seed."""

    normalized = str(seed or "").strip()
    if not normalized:
        raise ValueError("digital Liuyao cast requires a non-empty seed")
    coin_values: list[list[int]] = []
    coin_faces: list[list[str]] = []
    tosses: list[int] = []
    for toss_index in range(6):
        values: list[int] = []
        faces: list[str] = []
        for coin_index in range(3):
            digest = hashlib.sha256(
                f"liuyao-coin-v1:{normalized}:{toss_index + 1}:{coin_index + 1}".encode(
                    "utf-8"
                )
            ).digest()
            value = 3 if digest[0] & 1 else 2
            values.append(value)
            faces.append("背" if value == 3 else "字")
        coin_values.append(values)
        coin_faces.append(faces)
        tosses.append(sum(values))
    return {
        "seed": normalized,
        "algorithm": "sha256-three-coin-v1",
        "coin_values": coin_values,
        "coin_faces": coin_faces,
        "tosses": tosses,
    }


def normalize_transaction_cast_seed(seed: object) -> str:
    """Validate the persisted 256-bit CSPRNG seed used by the transaction."""

    normalized = str(seed or "").strip()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise ValueError(
            "digital Liuyao requires a 256-bit transaction CSPRNG seed"
        )
    return normalized


def transaction_cast_seed_commitment(seed: object) -> str:
    """Return the public, domain-separated commitment for a private cast seed."""

    normalized = normalize_transaction_cast_seed(seed)
    return hashlib.sha256(
        f"liuyao-seed-commitment-v1:{normalized}".encode("utf-8")
    ).hexdigest()


def normalize_question_class(value: object) -> str | None:
    """Validate the explicit issue class used by source-conditioned rules."""

    if value is None:
        return None
    normalized = str(value).strip()
    if normalized not in QUESTION_CLASSES:
        raise ValueError(
            "unsupported Liuyao question class: "
            f"{value!r}; available classes: {list(QUESTION_CLASSES)!r}"
        )
    return normalized


def public_projection(facts: Mapping[str, Any]) -> dict[str, Any]:
    """Project persisted Liuyao facts without disclosing replayable seed material."""

    projected = copy.deepcopy(dict(facts))
    output = projected.get("output")
    casting = output.get("casting") if isinstance(output, dict) else None
    if isinstance(casting, dict) and casting.get("method") == "digital_coin":
        seed = casting.get("seed")
        public_casting = {
            key: copy.deepcopy(casting[key])
            for key in (
                "method",
                "algorithm",
                "coin_values",
                "coin_faces",
                "tosses",
                "seed_source",
                "provenance",
                "source_dependency_id",
                "cast_digest",
            )
            if key in casting
        }
        public_casting["seed_commitment"] = transaction_cast_seed_commitment(seed)
        output["casting"] = public_casting
    return projected


def _normalize_casting(
    tosses: Sequence[int], casting: Mapping[str, Any]
) -> dict[str, Any]:
    values = _normalize_tosses(tosses)
    method = str(casting.get("method") or "")
    if method == "supplied_complete_cast":
        normalized: dict[str, Any] = {
            "method": method,
            "tosses": list(values),
            "provenance": copy.deepcopy(
                dict(casting.get("provenance") or {"kind": "user_supplied_cast"})
            ),
        }
    elif method == "digital_coin":
        if casting.get("seed_source") != TRANSACTION_CAST_SEED_SOURCE:
            raise ValueError(
                "digital Liuyao seed provenance must be transaction_csprng_v1"
            )
        generated = cast_from_seed(
            normalize_transaction_cast_seed(casting.get("seed"))
        )
        if tuple(generated["tosses"]) != values:
            raise ValueError("digital Liuyao tosses do not reproduce from the preserved seed")
        for field in ("coin_values", "coin_faces"):
            supplied = casting.get(field)
            if supplied is not None and supplied != generated[field]:
                raise ValueError(f"digital Liuyao {field} conflicts with preserved seed")
        normalized = {
            "method": method,
            **generated,
            "seed_source": TRANSACTION_CAST_SEED_SOURCE,
            "provenance": {
                "kind": "transaction_created_digital_coin_cast",
                "generated_once_and_preserved": True,
            },
        }
    else:
        raise ValueError(
            "Liuyao accepts only supplied_complete_cast or digital_coin"
        )
    normalized["source_dependency_id"] = "liuyao.cast.six-tosses-and-hexagrams"
    normalized["cast_digest"] = canonical_digest(normalized)
    return normalized


def _line_states(tosses: Sequence[int]) -> tuple[str, str, list[int]]:
    tables = _tables()
    main = "".join(str(tables["line_states"][value]["main"]) for value in tosses)
    changed = "".join(
        str(tables["line_states"][value]["changed"]) for value in tosses
    )
    moving = [
        index
        for index, value in enumerate(tosses, start=1)
        if tables["line_states"][value]["moving"]
    ]
    return main, changed, moving


def _najia(bits: str) -> list[dict[str, str]]:
    tables = _tables()
    trigram_by_bits = {
        str(profile["bits_bottom_up"]): profile
        for profile in tables["trigrams"].values()
    }
    lower = trigram_by_bits[bits[:3]]
    upper = trigram_by_bits[bits[3:]]
    rows: list[dict[str, str]] = []
    for stem, branches in (
        (lower["inner_stem"], lower["inner_branches"]),
        (upper["outer_stem"], upper["outer_branches"]),
    ):
        for branch in branches:
            rows.append(
                {
                    "stem": stem,
                    "branch": branch,
                    "ganzhi": stem + branch,
                    "element": tables["branch_elements"][branch],
                    "source_dependency_id": "liuyao.plate.najia-six-relatives-hidden-lines",
                }
            )
    return rows


def _element_relation(actor: str, target: str, actor_label: str, target_label: str) -> str:
    tables = _tables()["five_element_relations"]
    if actor == target:
        return "比和"
    if tables["generates"][actor] == target:
        return f"{actor_label}生{target_label}"
    if tables["generates"][target] == actor:
        return f"{target_label}生{actor_label}"
    if tables["controls"][actor] == target:
        return f"{actor_label}克{target_label}"
    if tables["controls"][target] == actor:
        return f"{target_label}克{actor_label}"
    raise RuntimeError("incomplete five-element relation table")


def _six_relative(palace_element: str, line_element: str) -> str:
    tables = _tables()["five_element_relations"]
    relatives = tables["six_relatives"]
    if line_element == palace_element:
        return relatives["same_as_palace"]
    if tables["generates"][palace_element] == line_element:
        return relatives["palace_generates_line"]
    if tables["generates"][line_element] == palace_element:
        return relatives["line_generates_palace"]
    if tables["controls"][palace_element] == line_element:
        return relatives["palace_controls_line"]
    if tables["controls"][line_element] == palace_element:
        return relatives["line_controls_palace"]
    raise RuntimeError("incomplete six-relative relation table")


def six_spirits_for(day_stem: str) -> list[str]:
    tables = _tables()
    stem = str(day_stem)
    if stem not in tables["six_spirit_start"]:
        raise ValueError(f"invalid day stem: {day_stem!r}")
    cycle = list(tables["six_spirit_cycle"])
    start = cycle.index(tables["six_spirit_start"][stem])
    return [cycle[(start + index) % 6] for index in range(6)]


def xunkong_for(day_ganzhi: str) -> list[str]:
    day = str(day_ganzhi)
    if day not in JIAZI:
        raise ValueError(f"invalid sexagenary day: {day_ganzhi!r}")
    cycle_start = JIAZI[(JIAZI.index(day) // 10) * 10]
    return list(_tables()["xunkong"][cycle_start])


def _branch_relation(left: str, right: str) -> str:
    tables = _tables()
    if tables["branch_clashes"].get(left) == right:
        return "冲"
    if tables["branch_combinations"].get(left) == right:
        return "合"
    return "无直接冲合"


def _shared_trines(left: str, right: str) -> list[list[str]]:
    return [
        list(group)
        for group in _tables()["branch_relations"]["trines"]
        if left in group and right in group
    ]


def _strength_state(line_element: str, month_element: str) -> str:
    tables = _tables()["five_element_relations"]
    if line_element == month_element:
        return "旺"
    if tables["generates"][month_element] == line_element:
        return "相"
    if tables["generates"][line_element] == month_element:
        return "休"
    if tables["controls"][line_element] == month_element:
        return "囚"
    return "死"


def calculate_line_relations(
    *,
    line_branch: str,
    line_element: str,
    month_branch: str,
    day_branch: str,
) -> dict[str, Any]:
    """Calculate neutral month/day relations for one line."""

    tables = _tables()
    for branch in (line_branch, month_branch, day_branch):
        if branch not in tables["branch_elements"]:
            raise ValueError(f"invalid earthly branch: {branch!r}")
    if line_element != tables["branch_elements"][line_branch]:
        raise ValueError("line element conflicts with the source branch table")
    month_element = tables["branch_elements"][month_branch]
    day_element = tables["branch_elements"][day_branch]
    month_relation = _branch_relation(line_branch, month_branch)
    day_relation = _branch_relation(line_branch, day_branch)
    return {
        "seasonal_state": _strength_state(line_element, month_element),
        "month": {
            "branch": month_branch,
            "element": month_element,
            "branch_relation": month_relation,
            "shared_trines": _shared_trines(line_branch, month_branch),
            "element_relation": _element_relation(
                line_element, month_element, "爻", "月"
            ),
            "break": month_relation == "冲",
        },
        "day": {
            "branch": day_branch,
            "element": day_element,
            "branch_relation": day_relation,
            "shared_trines": _shared_trines(line_branch, day_branch),
            "element_relation": _element_relation(
                line_element, day_element, "爻", "日"
            ),
            "clash": day_relation == "冲",
        },
        "fact_status": "calculated_relation_not_verdict",
        "source_dependency_id": "liuyao.calendar.xunkong-month-day-relations",
    }


def _changed_relation(original: Mapping[str, str], changed: Mapping[str, str]) -> dict[str, Any]:
    tables = _tables()
    source_element = changed["element"]
    target_element = original["element"]
    relations: list[str] = []
    if source_element == target_element:
        relations.append("比和")
    elif tables["five_element_relations"]["generates"][source_element] == target_element:
        relations.append("回头生")
    elif tables["five_element_relations"]["controls"][source_element] == target_element:
        relations.append("回头克")
    else:
        relations.append(
            _element_relation(source_element, target_element, "变爻", "本爻")
        )
    branch_pair = original["branch"] + changed["branch"]
    branch_relation = _branch_relation(original["branch"], changed["branch"])
    if branch_relation == "冲":
        relations.append("回头冲")
    elif branch_relation == "合":
        relations.append("回头合")
    if branch_pair in tables["advance_pairs"]:
        relations.append("化进神")
    if branch_pair in tables["retreat_pairs"]:
        relations.append("化退神")
    return {
        "original": copy.deepcopy(dict(original)),
        "changed": copy.deepcopy(dict(changed)),
        "relations": relations,
        "fact_status": "calculated_relation_not_verdict",
        "source_dependency_id": "liuyao.relations.returning-and-useful-spirit-candidates",
    }


def _hidden_lines(
    primary: Mapping[str, Any], represented_lines: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    represented_relatives = {
        str(line["six_relative"]) for line in represented_lines
    }
    missing = set(RELATIVES) - represented_relatives
    if not missing:
        return []
    pure_name = str(primary["palace"]) + ("为" + {
        "乾": "天", "兑": "泽", "离": "火", "震": "雷",
        "巽": "风", "坎": "水", "艮": "山", "坤": "地",
    }[str(primary["palace"])])
    pure = _catalog_by_name()[pure_name]
    pure_najia = _najia(pure["bits_bottom_up"])
    hidden: list[dict[str, Any]] = []
    emitted: set[str] = set()
    for index, najia in enumerate(pure_najia, start=1):
        relative = _six_relative(str(primary["palace_element"]), najia["element"])
        if relative in missing:
            hidden.append(
                {
                    "line": index,
                    "najia": copy.deepcopy(najia),
                    "six_relative": relative,
                    "source_plate": pure_name,
                    "status": "source_derived_hidden_line_candidate",
                    "source_dependency_id": "liuyao.plate.najia-six-relatives-hidden-lines",
                }
            )
            emitted.add(relative)
    if emitted != missing:
        raise RuntimeError("pure palace plate did not supply every missing relative")
    return hidden


def _candidate_pool(
    lines: Sequence[Mapping[str, Any]], hidden: Sequence[Mapping[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    pool: dict[str, list[dict[str, Any]]] = {relative: [] for relative in RELATIVES}
    for line in lines:
        pool[str(line["six_relative"])].append(
            {
                "source": "visible_line",
                "line": line["line"],
                "moving": line["moving"],
                "roles": copy.deepcopy(line["roles"]),
                "najia": copy.deepcopy(line["najia"]),
                "xunkong": line["xunkong"],
                "month_day_strength": copy.deepcopy(line["month_day_strength"]),
            }
        )
        changed = line.get("changed_line")
        if changed:
            pool[str(changed["six_relative"])].append(
                {
                    "source": "changed_line",
                    "line": line["line"],
                    "moving": True,
                    "roles": copy.deepcopy(line["roles"]),
                    "najia": copy.deepcopy(changed["najia"]),
                    "xunkong": changed["xunkong"],
                    "month_day_strength": copy.deepcopy(
                        changed["month_day_strength"]
                    ),
                }
            )
    for line in hidden:
        pool[str(line["six_relative"])].append(
            {
                "source": "hidden_line",
                "line": line["line"],
                "moving": False,
                "roles": [],
                "najia": copy.deepcopy(line["najia"]),
                "xunkong": line["xunkong"],
                "month_day_strength": copy.deepcopy(line["month_day_strength"]),
            }
        )
    if any(not rows for rows in pool.values()):
        raise RuntimeError("useful-spirit candidate pool must cover all five relatives")
    return pool


def _useful_spirit_chain_candidates(
    candidate_pool: Mapping[str, Sequence[Mapping[str, Any]]],
    requested: Sequence[str],
) -> dict[str, Any]:
    """Build source-bound 用神/原神/忌神/仇神 candidate chains.

    The classical procedure first identifies a question-specific useful
    spirit, then relates the five-element candidates around it.  This helper
    performs only that mechanical candidate expansion.  It intentionally
    leaves prosperity, movement, emptiness, school differences, and the final
    event judgment to the interpretation layer.
    """

    tables = _tables()["five_element_relations"]
    chains: list[dict[str, Any]] = []
    for requested_relative in requested:
        target_rows = candidate_pool.get(str(requested_relative)) or ()
        target_elements = sorted(
            {
                str((candidate.get("najia") or {}).get("element"))
                for candidate in target_rows
                if isinstance(candidate.get("najia"), Mapping)
                and candidate["najia"].get("element")
            }
        )
        for target_element in target_elements:
            generator = next(
                element
                for element, generated in tables["generates"].items()
                if generated == target_element
            )
            adverse = next(
                element
                for element, controlled in tables["controls"].items()
                if controlled == target_element
            )
            enemy = next(
                element
                for element, controlled in tables["controls"].items()
                if controlled == generator
                and tables["generates"].get(element) == adverse
            )

            def rows_for_element(element: str) -> list[dict[str, Any]]:
                return [
                    copy.deepcopy(dict(candidate))
                    for relative in RELATIVES
                    for candidate in (candidate_pool.get(relative) or ())
                    if str((candidate.get("najia") or {}).get("element"))
                    == element
                ]

            chains.append(
                {
                    "requested_relative": str(requested_relative),
                    "target_element": target_element,
                    "status": "candidate_only",
                    "candidates": {
                        "用神": rows_for_element(target_element),
                        "原神": rows_for_element(generator),
                        "忌神": rows_for_element(adverse),
                        "仇神": rows_for_element(enemy),
                    },
                    "requires_school_adjudication": True,
                    "source_dependency_id": (
                        "liuyao.interpretation.useful-spirit-chain-candidates"
                    ),
                }
            )
    return {
        "status": "candidate_only" if chains else "not_requested",
        "chains": chains,
        "fact_status": "calculated_relation_not_verdict",
        "source_dependency_id": (
            "liuyao.interpretation.useful-spirit-chain-candidates"
        ),
    }


def _useful_spirit_strength_evidence(
    candidate_pool: Mapping[str, Sequence[Mapping[str, Any]]],
    requested: Sequence[str],
) -> dict[str, Any]:
    """Project month/day strength signals for requested useful-spirit rows.

    Zengshan Buyi's prosperity layer needs the month/day state of the useful
    spirit.  This helper exposes those mechanical signals per candidate; it
    deliberately does not rank candidates or turn them into a verdict.
    """

    seasonal_rule = (
        _verified_evidence_rule(SEASONAL_STRENGTH_RULE_ID)
        if requested
        else None
    )
    seasonal_source_ref = (
        {
            "pack": seasonal_rule.source_pack,
            "rule_id": seasonal_rule.local_rule_id,
            "source_anchor": (
                f"{seasonal_rule.source_path}#{seasonal_rule.local_rule_id}"
            ),
            "verification_status": seasonal_rule.classical_binding_status,
            "binding_digest": seasonal_rule.classical_binding_digest,
        }
        if seasonal_rule is not None
        else None
    )
    by_relative: dict[str, dict[str, Any]] = {}
    for relative in requested:
        rows: list[dict[str, Any]] = []
        for candidate in candidate_pool.get(str(relative)) or ():
            strength = candidate.get("month_day_strength") or {}
            seasonal_state = str(strength.get("seasonal_state") or "")
            month = strength.get("month") or {}
            day = strength.get("day") or {}
            signals: list[dict[str, Any]] = []
            if seasonal_state in {"旺", "相"}:
                signals.append(
                    {
                        "signal": "seasonal_support",
                        "value": seasonal_state,
                        "status": "candidate_signal",
                    }
                )
            elif seasonal_state in {"休", "囚", "死"}:
                signals.append(
                    {
                        "signal": "seasonal_weakening",
                        "value": seasonal_state,
                        "status": "candidate_signal",
                    }
                )
            if seasonal_state not in {"旺", "相", "休", "囚", "死"}:
                raise RuntimeError("Liuyao candidate has no calculated seasonal state")
            if bool(month.get("break")):
                signals.append(
                    {
                        "signal": "month_break",
                        "value": True,
                        "status": "candidate_signal",
                    }
                )
            if bool(day.get("clash")):
                signals.append(
                    {
                        "signal": "day_clash",
                        "value": True,
                        "status": "candidate_signal",
                    }
                )
            if bool(candidate.get("xunkong")):
                signals.append(
                    {
                        "signal": "xunkong",
                        "value": True,
                        "status": "candidate_signal",
                    }
                )
            if bool(candidate.get("moving")):
                signals.append(
                    {
                        "signal": "moving_line",
                        "value": True,
                        "status": "candidate_signal",
                    }
                )
            rows.append(
                {
                    "source": str(candidate.get("source") or ""),
                    "line": int(candidate["line"]),
                    "moving": bool(candidate.get("moving")),
                    "xunkong": bool(candidate.get("xunkong")),
                    "najia": copy.deepcopy(dict(candidate.get("najia") or {})),
                    "month_day_strength": copy.deepcopy(dict(strength)),
                    "seasonal_adjudication": {
                        "status": "adjudicated_seasonal_strength_band",
                        "decision_scope": (
                            "liuyao_candidate_month_order_strength_band"
                        ),
                        "candidate_source": str(candidate.get("source") or ""),
                        "line": int(candidate["line"]),
                        "line_element": str(
                            (candidate.get("najia") or {}).get("element") or ""
                        ),
                        "month_element": str(month.get("element") or ""),
                        "seasonal_state": seasonal_state,
                        "strength_band": (
                            "旺相" if seasonal_state in {"旺", "相"} else "休囚"
                        ),
                        "whole_candidate_strength_verdict": None,
                        "outcome_verdict": None,
                        "source_ref": copy.deepcopy(seasonal_source_ref),
                        "unresolved_checks": [
                            "日辰生克冲合与暗动",
                            "旬空、月破与冲实填实",
                            "动爻生克与回头生克",
                            "综合旺衰、成败与应期",
                        ],
                    },
                    "signals": signals,
                    "status": "candidate_only",
                    "hard_verdict": None,
                }
            )
        by_relative[str(relative)] = {
            "status": "candidate_only" if rows else "not_available",
            "candidates": rows,
            "hard_verdict": None,
        }
    return {
        "status": "candidate_only" if requested else "not_requested",
        "by_relative": by_relative,
        "source_rules": (
            [
                {
                    **copy.deepcopy(seasonal_source_ref),
                    "role": "useful_spirit_month_order_strength_band",
                }
            ]
            if seasonal_source_ref is not None
            else []
        ),
        "fact_status": "calculated_relation_not_verdict",
        "hard_verdict": None,
        "requires_school_adjudication": True,
        "source_dependency_id": "liuyao.interpretation.useful-spirit-strength-evidence",
    }


def _node_relation(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    source_label: str,
    target_label: str,
) -> dict[str, Any]:
    source_najia = source["najia"]
    target_najia = target["najia"]
    return {
        "source_line": int(source["line"]),
        "source_roles": copy.deepcopy(list(source.get("roles") or ())),
        "source_role_label": source_label,
        "source_najia": copy.deepcopy(dict(source_najia)),
        "target_source": str(target["source"]),
        "target_line": int(target["line"]),
        "target_roles": copy.deepcopy(list(target.get("roles") or ())),
        "target_role_label": target_label,
        "target_relative": str(target["six_relative"]),
        "target_najia": copy.deepcopy(dict(target_najia)),
        "branch_relation": _branch_relation(
            str(source_najia["branch"]), str(target_najia["branch"])
        ),
        "shared_trines": _shared_trines(
            str(source_najia["branch"]), str(target_najia["branch"])
        ),
        "element_relation": _element_relation(
            str(source_najia["element"]),
            str(target_najia["element"]),
            source_label,
            target_label,
        ),
        "fact_status": "calculated_relation_not_verdict",
        "source_dependency_id": "liuyao.relations.returning-and-useful-spirit-candidates",
    }


def _relation_graph(
    lines: Sequence[Mapping[str, Any]],
    candidate_pool: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    shi_line: int,
    ying_line: int,
) -> dict[str, Any]:
    shi = lines[shi_line - 1]
    ying = lines[ying_line - 1]
    shi_ying = _node_relation(
        shi,
        {
            "source": "visible_line",
            "line": ying["line"],
            "roles": ying["roles"],
            "six_relative": ying["six_relative"],
            "najia": ying["najia"],
        },
        source_label="世",
        target_label="应",
    )
    shi_ying.update({"shi_line": shi_line, "ying_line": ying_line})
    candidate_rows = [
        {
            **copy.deepcopy(dict(candidate)),
            "six_relative": relative,
        }
        for relative in RELATIVES
        for candidate in candidate_pool[relative]
    ]
    moving_relations = [
        _node_relation(
            line,
            candidate,
            source_label="动爻",
            target_label="候选",
        )
        for line in lines
        if line["moving"]
        for candidate in candidate_rows
    ]
    return {
        "shi_ying": shi_ying,
        "moving_to_candidates": moving_relations,
        "fact_status": "calculated_relation_not_verdict",
        "source_dependency_id": "liuyao.relations.returning-and-useful-spirit-candidates",
    }


def _fact_digest(payload: Mapping[str, Any]) -> str:
    identity = copy.deepcopy(dict(payload))
    identity.pop("fact_digest", None)
    return canonical_digest(identity)


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Build stable fact paths consumed by the source-evidence matcher."""

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
    """Expose matched divination predicates without creating a verdict."""

    indexed = {"chart_facts": {"output": dict(output)}}
    fact_refs = tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="mingli-master.liuyao.v1",
            provider_version=PROVIDER_VERSION,
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )
    matches: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if rule.system != "divination":
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
                "source_dependency_id": "liuyao.source-conditioned-patterns",
            }
        )
    return sorted(matches, key=lambda item: str(item["rule_id"]))


def _verified_evidence_rule(rule_id: str) -> evidence_rules.EvidenceRule:
    """Resolve one checked rule and require an active classical binding."""

    rule = next(
        (
            item
            for item in evidence_rules.production_evidence_rules()
            if item.rule_id == rule_id
        ),
        None,
    )
    if rule is None:
        raise RuntimeError(f"runtime evidence rule is missing: {rule_id}")
    if (
        not rule.runtime_active
        or rule.classical_binding_status != "verified"
        or not rule.classical_binding_digest
    ):
        raise RuntimeError(f"runtime evidence rule is not verified: {rule_id}")
    return rule


def _useful_spirit_role_adjudication(
    *,
    question_class: str | None,
    candidate_pool: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Adjudicate only the six-relative role set authorized by HJC-R009.

    HJC-R009 authorizes the primary/supporting/obstacle relatives for an
    explicit finance question and a sole visible primary line may be identified
    by uniqueness.  ZR-04-04 additionally authorizes the moving line when the
    primary relative appears on exactly two visible lines and only one moves.
    Same-motion or non-visible candidates remain unresolved; no branch judges
    strength, rescue, outcome, or timing.
    """

    if question_class is None:
        return {
            "status": "not_requested",
            "decision_scope": None,
            "question_class": None,
            "primary_relative": None,
            "supporting_relatives": [],
            "obstacle_attention_relatives": [],
            "specific_line_selection": None,
            "hard_verdict": None,
            "source_ref": None,
            "unresolved_checks": ["需要显式结构化问题类别"],
        }
    if question_class != "finance":
        raise ValueError(f"unsupported Liuyao question class: {question_class!r}")
    if not candidate_pool.get("妻财") or not candidate_pool.get("子孙"):
        raise RuntimeError(
            "finance role adjudication requires calculated 妻财 and 子孙 candidates"
        )

    role_rule = _verified_evidence_rule(FINANCE_ROLE_RULE_ID)
    visible_candidates = [
        candidate
        for candidate in candidate_pool["妻财"]
        if candidate.get("source") == "visible_line"
    ]
    visible_candidate_lines = sorted(
        {int(candidate["line"]) for candidate in visible_candidates}
    )
    moving_visible_candidate_lines = sorted(
        {
            int(candidate["line"])
            for candidate in visible_candidates
            if candidate.get("moving") is True
        }
    )
    visible_candidate_count = len(visible_candidate_lines)
    moving_visible_candidate_count = len(moving_visible_candidate_lines)
    role_source_ref = {
        "pack": role_rule.source_pack,
        "rule_id": role_rule.local_rule_id,
        "source_anchor": f"{role_rule.source_path}#{role_rule.local_rule_id}",
        "verification_status": role_rule.classical_binding_status,
        "binding_digest": role_rule.classical_binding_digest,
    }
    if len(visible_candidate_lines) == 1:
        specific_line = visible_candidate_lines[0]
        specific_line_adjudication = {
            "status": "adjudicated_unique_visible_line",
            "decision_scope": "finance_primary_relative_line_identity",
            "primary_relative": "妻财",
            "visible_candidate_count": visible_candidate_count,
            "visible_candidate_lines": visible_candidate_lines,
            "moving_visible_candidate_count": moving_visible_candidate_count,
            "moving_visible_candidate_lines": moving_visible_candidate_lines,
            "specific_line_selection": specific_line,
            "derivation_basis": (
                "verified_role_plus_runtime_unique_visible_candidate"
            ),
            "selection_source_ref": role_source_ref,
            "hard_verdict": None,
        }
        unresolved_checks = [
            "月日旺衰与空破冲合",
            "动变生克与救应",
            "成败、应期与事件结果",
        ]
    elif (
        visible_candidate_count == 2
        and moving_visible_candidate_count == 1
    ):
        line_rule = _verified_evidence_rule(TWO_PRESENT_USEFUL_SPIRIT_RULE_ID)
        specific_line = moving_visible_candidate_lines[0]
        specific_line_adjudication = {
            "status": "adjudicated_single_moving_visible_line",
            "decision_scope": "finance_primary_relative_line_identity",
            "primary_relative": "妻财",
            "visible_candidate_count": visible_candidate_count,
            "visible_candidate_lines": visible_candidate_lines,
            "moving_visible_candidate_count": moving_visible_candidate_count,
            "moving_visible_candidate_lines": moving_visible_candidate_lines,
            "specific_line_selection": specific_line,
            "derivation_basis": (
                "verified_two_present_rule_plus_runtime_single_moving_candidate"
            ),
            "selection_source_ref": {
                "pack": line_rule.source_pack,
                "rule_id": line_rule.local_rule_id,
                "source_anchor": f"{line_rule.source_path}#{line_rule.local_rule_id}",
                "verification_status": line_rule.classical_binding_status,
                "binding_digest": line_rule.classical_binding_digest,
            },
            "hard_verdict": None,
        }
        unresolved_checks = [
            "月日旺衰与空破冲合",
            "动变生克与救应",
            "成败、应期与事件结果",
        ]
    elif visible_candidate_lines:
        specific_line = None
        specific_line_adjudication = {
            "status": "unresolved_multiple_visible_lines",
            "decision_scope": "finance_primary_relative_line_identity",
            "primary_relative": "妻财",
            "visible_candidate_count": visible_candidate_count,
            "visible_candidate_lines": visible_candidate_lines,
            "moving_visible_candidate_count": moving_visible_candidate_count,
            "moving_visible_candidate_lines": moving_visible_candidate_lines,
            "specific_line_selection": None,
            "derivation_basis": (
                "verified_role_plus_runtime_multiple_visible_candidates"
            ),
            "selection_source_ref": None,
            "hard_verdict": None,
        }
        unresolved_checks = [
            (
                "两个可见妻财爻同动静，须结合完整旺衰取舍"
                if visible_candidate_count == 2
                else "多个可见妻财爻的取舍"
            ),
            "月日旺衰与空破冲合",
            "动变生克与救应",
            "成败、应期与事件结果",
        ]
    else:
        specific_line = None
        specific_line_adjudication = {
            "status": "unresolved_no_visible_line",
            "decision_scope": "finance_primary_relative_line_identity",
            "primary_relative": "妻财",
            "visible_candidate_count": 0,
            "visible_candidate_lines": [],
            "moving_visible_candidate_count": 0,
            "moving_visible_candidate_lines": [],
            "specific_line_selection": None,
            "derivation_basis": (
                "verified_role_plus_runtime_no_visible_candidate"
            ),
            "selection_source_ref": None,
            "hard_verdict": None,
        }
        unresolved_checks = [
            "妻财伏神或变爻的取用",
            "月日旺衰与空破冲合",
            "动变生克与救应",
            "成败、应期与事件结果",
        ]
    return {
        "status": "adjudicated_question_role_set",
        "decision_scope": "finance_useful_spirit_role_set",
        "question_class": "finance",
        "primary_relative": "妻财",
        "supporting_relatives": ["子孙"],
        "obstacle_attention_relatives": ["兄弟", "官鬼", "父母"],
        "specific_line_selection": specific_line,
        "specific_line_adjudication": specific_line_adjudication,
        "hard_verdict": None,
        "source_ref": role_source_ref,
        "unresolved_checks": unresolved_checks,
    }


def build_fact_layer(
    tosses: Sequence[int],
    *,
    calendar_facts: Mapping[str, Any],
    casting: Mapping[str, Any],
    requested_useful_spirit_relatives: Sequence[str] = (),
    question_class: object = None,
) -> dict[str, Any]:
    values = _normalize_tosses(tosses)
    calendar = copy.deepcopy(dict(calendar_facts))
    calendar_core.validate_calendar_digest(calendar)
    ganzhi = calendar.get("ganzhi") or {}
    month_ganzhi = str(ganzhi.get("month") or "")
    day_ganzhi = str(ganzhi.get("day") or "")
    if month_ganzhi not in JIAZI or day_ganzhi not in JIAZI:
        raise ValueError("Liuyao requires shared calendar month and day Ganzhi")
    normalized_casting = _normalize_casting(values, casting)
    normalized_question_class = normalize_question_class(question_class)
    main_bits, changed_bits, moving_lines = _line_states(values)
    primary = copy.deepcopy(_catalog_by_bits()[main_bits])
    changed = copy.deepcopy(_catalog_by_bits()[changed_bits])
    main_najia = _najia(main_bits)
    changed_najia = _najia(changed_bits)
    spirits = six_spirits_for(day_ganzhi[0])
    void_branches = xunkong_for(day_ganzhi)
    changed_plate_lines = [
        {
            "line": index,
            "yin_yang": "阳" if changed_bits[index - 1] == "1" else "阴",
            "najia": copy.deepcopy(najia),
            "six_relative": _six_relative(
                primary["palace_element"], najia["element"]
            ),
            "xunkong": najia["branch"] in void_branches,
            "month_day_strength": calculate_line_relations(
                line_branch=najia["branch"],
                line_element=najia["element"],
                month_branch=month_ganzhi[1],
                day_branch=day_ganzhi[1],
            ),
            "source_dependency_id": "liuyao.plate.najia-six-relatives-hidden-lines",
        }
        for index, najia in enumerate(changed_najia, start=1)
    ]
    lines: list[dict[str, Any]] = []
    for index, (value, najia, changed_line) in enumerate(
        zip(values, main_najia, changed_najia), start=1
    ):
        line: dict[str, Any] = {
            "line": index,
            "state": _tables()["line_states"][value]["name"],
            "yin_yang": "阳" if main_bits[index - 1] == "1" else "阴",
            "moving": index in moving_lines,
            "najia": copy.deepcopy(najia),
            "six_relative": _six_relative(
                primary["palace_element"], najia["element"]
            ),
            "six_spirit": spirits[index - 1],
            "roles": [
                role
                for role, target in (
                    ("世", primary["shi_line"]),
                    ("应", primary["ying_line"]),
                )
                if index == target
            ],
            "xunkong": najia["branch"] in void_branches,
            "month_day_strength": calculate_line_relations(
                line_branch=najia["branch"],
                line_element=najia["element"],
                month_branch=month_ganzhi[1],
                day_branch=day_ganzhi[1],
            ),
        }
        if index in moving_lines:
            line["changed_line"] = copy.deepcopy(
                changed_plate_lines[index - 1]
            )
            line["changed_relation"] = _changed_relation(najia, changed_line)
        lines.append(line)
    represented_lines = list(lines) + [
        line["changed_line"] for line in lines if line.get("changed_line")
    ]
    hidden = _hidden_lines(primary, represented_lines)
    for hidden_line in hidden:
        hidden_line["xunkong"] = (
            hidden_line["najia"]["branch"] in void_branches
        )
        hidden_line["month_day_strength"] = calculate_line_relations(
            line_branch=hidden_line["najia"]["branch"],
            line_element=hidden_line["najia"]["element"],
            month_branch=month_ganzhi[1],
            day_branch=day_ganzhi[1],
        )
    candidate_pool = _candidate_pool(lines, hidden)
    relation_graph = _relation_graph(
        lines,
        candidate_pool,
        shi_line=primary["shi_line"],
        ying_line=primary["ying_line"],
    )
    requested = tuple(dict.fromkeys(str(item) for item in requested_useful_spirit_relatives))
    invalid_requested = [item for item in requested if item not in RELATIVES]
    if invalid_requested:
        raise ValueError(
            "requested useful-spirit relatives must be structured six-relative values"
        )
    useful_spirit_chain = _useful_spirit_chain_candidates(
        candidate_pool, requested
    )
    useful_spirit_strength = _useful_spirit_strength_evidence(
        candidate_pool, requested
    )
    useful_spirit_selection: dict[str, Any] = {
        "status": "evidence_bound",
        "reason": "school-dependent adjudication is outside deterministic calculation",
        "query_word_matching": False,
        "source_dependency_id": "liuyao.relations.returning-and-useful-spirit-candidates",
        "chain_candidates": useful_spirit_chain,
        "strength_evidence": useful_spirit_strength,
        "role_adjudication": _useful_spirit_role_adjudication(
            question_class=normalized_question_class,
            candidate_pool=candidate_pool,
        ),
    }
    if normalized_question_class is not None:
        useful_spirit_selection["question_context"] = {
            "question_class": normalized_question_class,
            "classification_source": "explicit_structured_input",
        }
    output: dict[str, Any] = {
        "casting": normalized_casting,
        "casting_method": normalized_casting["method"],
        "primary_hexagram": primary,
        "changed_hexagram": changed,
        "moving_lines": moving_lines,
        "shi_ying": {"shi": primary["shi_line"], "ying": primary["ying_line"]},
        "najia": copy.deepcopy(main_najia),
        "changed_najia": copy.deepcopy(changed_najia),
        "six_relatives": [line["six_relative"] for line in lines],
        "changed_six_relatives": [
            line["six_relative"] for line in changed_plate_lines
        ],
        "six_spirits": spirits,
        "xunkong": {
            "day_ganzhi": day_ganzhi,
            "void_branches": void_branches,
            "source_dependency_id": "liuyao.calendar.xunkong-month-day-relations",
        },
        "six_spirit_profile": {
            "day_stem": day_ganzhi[0],
            "source_dependency_id": "liuyao.plate.six-spirits",
        },
        "calendar": {
            "month_ganzhi": month_ganzhi,
            "month_branch": month_ganzhi[1],
            "day_ganzhi": day_ganzhi,
            "day_stem": day_ganzhi[0],
            "day_branch": day_ganzhi[1],
        },
        "lines": lines,
        "changed_plate_lines": changed_plate_lines,
        "hidden_lines": hidden,
        "month_day_strength": [
            copy.deepcopy(line["month_day_strength"]) for line in lines
        ],
        "relation_facts": [
            copy.deepcopy(line.get("changed_relation"))
            for line in lines
            if line.get("changed_relation")
        ],
        "shi_ying_moving_relations": relation_graph,
        "useful_spirit_candidates": candidate_pool,
        "requested_useful_spirit_candidates": {
            relative: copy.deepcopy(candidate_pool[relative])
            for relative in requested
        },
        "useful_spirit_selection": useful_spirit_selection,
        "interpretation_status": "facts_only",
    }
    output["source_conditioned_patterns"] = _source_conditioned_patterns(output)
    input_payload: dict[str, Any] = {
        "normalized_tosses": list(values),
        "requested_useful_spirit_relatives": list(requested),
    }
    if normalized_question_class is not None:
        input_payload["question_class"] = normalized_question_class
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": "liuyao",
        "fact_layer_status": "calculated_liuyao_facts",
        "adapter": {
            "name": "mingli-master.liuyao",
            "version": PROVIDER_VERSION,
            "rule_profile": TABLE_PROFILE,
            "source_artifact": TABLE_RELATIVE_PATH,
            "source_artifact_sha256": TABLE_SHA256,
            "generated_at": "deterministic-chart-identity",
        },
        "input": input_payload,
        "calendar_normalization": calendar,
        "calendar_digest": calendar["calendar_digest"],
        "output": output,
        "source_lineage": {
            "calculation": [
                {
                    "pack": "divination/bushi-zhengzong",
                    "role": "cast states, eight palaces, Najia, Shi/Ying, six spirits, Xunkong, hidden lines",
                },
                {
                    "pack": "divination/huozhu-lin",
                    "role": "Najia branch and six-relative calculation lineage",
                },
            ],
            "interpretation": [
                {
                    "pack": "divination/zengshan-buyi",
                    "role": "event-specific evidence and exception adjudication",
                },
                {
                    "pack": "divination/huangjin-ce",
                    "role": "useful/adverse spirit prosperity adjudication",
                },
            ],
        },
        "capabilities": {
            "allowed": [
                "deterministic_plate",
                "month_day_relations",
                "useful_spirit_candidate_pool",
                "source_bound_question_role_adjudication",
                "source_bound_specific_line_adjudication",
            ],
            "blocked": [
                "query_keyword_useful_spirit_selection",
                "time_based_meihua_casting",
                "unsourced_verdict",
            ],
        },
    }
    payload["fact_digest"] = _fact_digest(payload)
    return payload


def validate_fact_layer(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute the complete plate and fail closed on any fact mutation."""

    codes: list[str] = []
    try:
        adapter = payload.get("adapter") or {}
        if adapter.get("source_artifact_sha256") != source_table_digest():
            codes.append("liuyao_source_table_digest_mismatch")
        calendar = payload.get("calendar_normalization") or {}
        try:
            calendar_core.validate_calendar_digest(calendar)
        except (KeyError, TypeError, ValueError):
            codes.append("liuyao_calendar_digest_mismatch")
        output = payload.get("output") or {}
        casting = output.get("casting") or {}
        if casting.get("method") == "digital_coin":
            try:
                normalize_transaction_cast_seed(casting.get("seed"))
            except ValueError:
                codes.append("liuyao_invalid_transaction_seed")
        input_payload = payload.get("input") or {}
        rebuilt = build_fact_layer(
            input_payload.get("normalized_tosses") or (),
            calendar_facts=calendar,
            casting=casting,
            requested_useful_spirit_relatives=input_payload.get(
                "requested_useful_spirit_relatives"
            )
            or (),
            question_class=input_payload.get("question_class"),
        )
        if output != rebuilt["output"]:
            codes.append("liuyao_output_mismatch")
        if payload.get("fact_digest") != _fact_digest(payload):
            codes.append("liuyao_fact_digest_mismatch")
        if payload.get("fact_digest") != rebuilt["fact_digest"]:
            codes.append("liuyao_recomputed_digest_mismatch")
    except (KeyError, TypeError, ValueError, RuntimeError):
        codes.append("liuyao_invalid_fact_structure")
    unique = list(dict.fromkeys(codes))
    return {"ok": not unique, "codes": unique}


__all__ = [
    "ADAPTER_VERSION",
    "BRANCHES",
    "JIAZI",
    "PROVIDER_VERSION",
    "QUESTION_CLASSES",
    "RELATIVES",
    "STEMS",
    "TABLE_SHA256",
    "TRANSACTION_CAST_SEED_KEY",
    "TRANSACTION_CAST_SEED_SOURCE",
    "build_fact_layer",
    "build_hexagram_catalog",
    "calculate_line_relations",
    "cast_from_seed",
    "normalize_transaction_cast_seed",
    "normalize_question_class",
    "public_projection",
    "six_spirits_for",
    "source_table_digest",
    "transaction_cast_seed_commitment",
    "validate_fact_layer",
    "xunkong_for",
]
