"""Independent declarative reference evaluator for Selection event facts.

This module deliberately consumes only public day-record primitives plus the
versioned source table.  It never reads the provider's ``event_specific_facts``
output and never calls its private event-fact evaluator.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Mapping

from cnlunar import Lunar, config as cnlunar_config


REFERENCE_EVALUATOR_ID = "independent_declarative_reference_evaluator_v1"
REFERENCE_EVALUATOR_VERSION = "1.1.0"
BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")
STEMS = tuple("甲乙丙丁戊己庚辛壬癸")


def _clean_unique(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _folk_hits(
    lunar_month: int,
    lunar_day: int,
    day_ganzhi: str,
    table: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rules = {str(row["id"]): row for row in table["folk_rules"]}
    hits: list[dict[str, Any]] = []
    if f"{lunar_month}-{lunar_day}" in rules["folk.yang-gong-thirteen"][
        "lunar_month_days"
    ]:
        hits.append(
            {
                "id": "folk.yang-gong-thirteen",
                "status": "comparison_only",
                "source": "玉匣记",
            }
        )
    if lunar_day in [int(item) for item in rules["folk.month-taboo"]["lunar_days"]]:
        hits.append(
            {
                "id": "folk.month-taboo",
                "status": "comparison_only",
                "source": "玉匣记",
            }
        )
    taboo = (
        str(cnlunar_config.pengTatooList[STEMS.index(day_ganzhi[0])])
        + "；"
        + str(cnlunar_config.pengTatooList[10 + BRANCHES.index(day_ganzhi[1])])
    )
    hits.append(
        {
            "id": "folk.pengzu",
            "status": "comparison_only_not_general_elimination",
            "source": "玉匣记",
            "text": taboo,
        }
    )
    return hits


def _reference_directional_facts(
    raw_input: Mapping[str, Any],
    calendar: Mapping[str, Any],
    table: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute direction formulas from immutable tables, not provider output."""

    year_ganzhi = str(calendar["ganzhi"]["year"])
    month_branch = str(calendar["ganzhi"]["month"])[1]
    year_stem, year_branch = year_ganzhi
    context = raw_input.get("directional_context") or {}
    site_branch = str(context["site_branch"]) if context.get("site_branch") else None
    site_mountain = (
        str(context["site_mountain"]) if context.get("site_mountain") else None
    )
    formulas = table["directional_formulas"]
    dajiangjun = str(formulas["dajiangjun_by_year_branch"][year_branch])
    jinshen = [
        str(item) for item in formulas["jinshen_qisha_by_year_stem"][year_stem]
    ]
    luohou = str(formulas["xunshan_luohou_by_year_branch"][year_branch])

    def three_sha(branch: str) -> dict[str, str]:
        for trine, values in table["gods"]["three_sha_by_trine"].items():
            if branch in str(trine):
                return {
                    "jie_sha_branch": str(values["jie_sha"]),
                    "zai_sha_branch": str(values["zai_sha"]),
                    "sui_sha_branch": str(values["sui_sha"]),
                }
        raise ValueError("reference direction branch is invalid")

    hits: list[dict[str, str]] = []
    if site_branch:
        annual = three_sha(year_branch)
        monthly = three_sha(month_branch)
        opposites = table["branch_opposites"]
        checks = (
            ("annual_tai_sui", year_branch),
            ("annual_sui_po", str(opposites[year_branch])),
            ("annual_jie_sha", annual["jie_sha_branch"]),
            ("annual_zai_sha", annual["zai_sha_branch"]),
            ("annual_sui_sha", annual["sui_sha_branch"]),
            ("monthly_build", month_branch),
            ("monthly_break", str(opposites[month_branch])),
            ("monthly_jie_sha", monthly["jie_sha_branch"]),
            ("monthly_zai_sha", monthly["zai_sha_branch"]),
            ("monthly_sui_sha", monthly["sui_sha_branch"]),
            ("annual_dajiangjun", dajiangjun),
            *(("annual_jinshen_qisha", branch) for branch in jinshen),
        )
        hits = [
            {
                "code": code,
                "site_branch": site_branch,
                "matched_branch": branch,
            }
            for code, branch in checks
            if site_branch == branch
        ]
    return {
        "site_branch": site_branch,
        "site_mountain": site_mountain,
        "dajiangjun_branch": dajiangjun,
        "jinshen_qisha_branches": jinshen,
        "xunshan_luohou_mountain": luohou,
        "evaluated_hits": hits,
    }


def evaluate_event_fact(
    field: str,
    raw_input: Mapping[str, Any],
    day_record: Mapping[str, Any],
    source_table: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one source-table formula without provider event-fact output."""

    definition = source_table["event_fact_definitions"][field]
    kind = str(definition["kind"])
    good_gods = _clean_unique(day_record["daily_shensha"]["good_gods"])
    bad_gods = _clean_unique(day_record["daily_shensha"]["bad_gods"])
    all_gods = set(good_gods) | set(bad_gods)
    calendar = day_record["calendar"]
    lunar = calendar["lunar_date"]
    day_ganzhi = str(calendar["ganzhi"]["day"])
    jianchu = str(day_record["jianchu"]["value"])
    directions = _reference_directional_facts(raw_input, calendar, source_table)
    participants = copy.deepcopy(day_record["participant_clashes"])
    official_rules = day_record["official_event_rules"]
    yi_matches = list(official_rules["yi_matches"])
    ji_matches = list(official_rules["ji_matches"])
    universal_avoidance = bool(official_rules["universal_avoidance"])

    if kind == "record":
        key = str(definition["record"])
        aliases = {
            "annual_three_sha": day_record["annual_gods"]["three_sha"],
            "monthly_three_sha": day_record["monthly_gods"]["three_sha"],
            "taisui_suipo": {
                "tai_sui_branch": day_record["annual_gods"]["tai_sui_branch"],
                "sui_po_branch": day_record["annual_gods"]["sui_po_branch"],
            },
        }
        value = aliases.get(key, day_record.get(key))
        active = bool(value)
        value = copy.deepcopy(value)
    elif kind in {"god_presence", "official_rejected_rule"}:
        names = [str(item) for item in definition.get("names") or ()]
        if not names and kind == "god_presence":
            active = bool(all_gods)
            value = {
                "matched_good_gods": good_gods,
                "matched_bad_gods": bad_gods,
            }
        else:
            matched = [name for name in names if name in all_gods]
            value = {
                "declared_names": names,
                "matched_good_gods": [name for name in names if name in good_gods],
                "matched_bad_gods": [name for name in names if name in bad_gods],
            }
            if kind == "official_rejected_rule":
                value["authority_status"] = "rejected_by_official_primary"
                value["observed_but_not_ranked"] = matched
                active = False
            else:
                active = bool(matched)
    elif kind == "mixed_official_and_rejected":
        official = [str(item) for item in definition.get("official_names") or ()]
        rejected = [str(item) for item in definition.get("rejected_names") or ()]
        official_matches = [name for name in official if name in all_gods]
        active = bool(official_matches)
        value = {
            "official_matches": official_matches,
            "officially_rejected_layer": rejected,
            "rejected_observed_but_not_ranked": [
                name for name in rejected if name in all_gods
            ],
        }
    elif kind in {"good_gods", "bad_gods"}:
        value = good_gods if kind == "good_gods" else bad_gods
        active = bool(value)
    elif kind == "hour_path":
        value = [
            {
                "branch": row["branch"],
                "path_god": row["twelve_path_god"],
                "class": row["class"],
                "eligible": row["hard_constraint_eligible"],
            }
            for row in day_record["hour_facts"]
        ]
        active = any(row["class"] == "huang" and row["eligible"] for row in value)
    elif kind == "event_yiji":
        value = {
            "yi_matches": yi_matches,
            "ji_matches": ji_matches,
            "universal_avoidance": universal_avoidance,
        }
        active = bool(yi_matches or ji_matches or universal_avoidance)
    elif kind == "conflicts":
        official_yiji = day_record["official_yiji"]
        value = {
            "yi_ji_overlap": sorted(
                set(official_yiji["yi"]) & set(official_yiji["ji"])
            ),
            "universal_avoidance": universal_avoidance,
            "directional_hits": copy.deepcopy(directions.get("evaluated_hits") or []),
            "participant_clashes": participants,
        }
        active = any(
            (
                value["yi_ji_overlap"],
                universal_avoidance,
                value["directional_hits"],
                participants,
            )
        )
    elif kind == "fixed_day_set":
        declared = [str(item) for item in definition.get("day_ganzhi") or ()]
        active = day_ganzhi in declared
        value = {
            "day_ganzhi": day_ganzhi,
            "matched": active,
            "authority": definition.get("authority"),
        }
    elif kind == "lunar_zhoutang":
        runtime = Lunar(
            datetime.fromisoformat(f"{raw_input['date']}T12:00:00"),
            godType="8char",
            year8Char="beginningOfSpring",
        )
        positions = ("翁", "第", "灶", "妇", "厨", "夫", "姑", "堂")
        lunar_day = int(lunar["day"])
        index = (
            (5 + lunar_day - 1) % 8
            if runtime.lunarMonthLong
            else (3 - lunar_day + 1) % 8
        )
        position = positions[index]
        active = False
        value = {
            "lunar_month_size": "large" if runtime.lunarMonthLong else "small",
            "lunar_day": lunar_day,
            "position": position,
            "calculated_favorable_in_rejected_method": position
            in {"第", "堂", "厨", "灶"},
            "authority_status": definition.get("authority"),
            "rank_effect": "none",
        }
    elif kind == "participant_clashes":
        value = participants
        active = bool(value)
    elif kind == "jianchu_membership":
        favorable = [str(item) for item in definition.get("favorable") or ()]
        active = jianchu in favorable
        value = {"jianchu": jianchu, "favorable": favorable}
    elif kind == "direction_formula":
        formula = str(definition["formula"])
        calculated = copy.deepcopy(
            {
                "dajiangjun": directions["dajiangjun_branch"],
                "jinshen_qisha": directions["jinshen_qisha_branches"],
                "xunshan_luohou": directions["xunshan_luohou_mountain"],
            }[formula]
        )
        site_field = "site_mountain" if formula == "xunshan_luohou" else "site_branch"
        site_value = directions.get(site_field)
        matched = (
            site_value in calculated
            if isinstance(calculated, list)
            else site_value == calculated
        )
        applicable_actions = [
            str(item) for item in definition.get("applicable_actions") or ()
        ]
        explicitly_exempt_actions = [
            str(item)
            for item in definition.get("explicitly_exempt_actions") or ()
        ]
        requested_actions = _clean_unique(raw_input.get("requested_actions") or [])
        applicable = (
            not applicable_actions
            or bool(set(requested_actions) & set(applicable_actions))
        ) and not bool(set(requested_actions) & set(explicitly_exempt_actions))
        active = matched and applicable
        value = {
            "formula": formula,
            "value": calculated,
            "site_field": site_field,
            "site_value": site_value,
            "matched": matched,
        }
        if applicable_actions or explicitly_exempt_actions:
            value.update(
                {
                    "applicable": applicable,
                    "applicable_actions": applicable_actions,
                    "explicitly_exempt_actions": explicitly_exempt_actions,
                    "requested_actions": requested_actions,
                }
            )
    elif kind == "directional_hits":
        hits = copy.deepcopy(directions.get("evaluated_hits") or [])
        active = bool(hits)
        value = {"site_branch": directions.get("site_branch"), "hits": hits}
    elif kind == "lunar_month_day_set":
        key = f"{abs(int(lunar['month']))}-{int(lunar['day'])}"
        declared = [str(item) for item in definition.get("values") or ()]
        active = key in declared
        value = {"lunar_month_day": key, "authority": definition.get("authority")}
    elif kind == "lunar_day_set":
        declared = [int(item) for item in definition.get("values") or ()]
        lunar_day = int(lunar["day"])
        active = lunar_day in declared
        value = {"lunar_day": lunar_day, "authority": definition.get("authority")}
    elif kind == "seasonal_branch_set":
        lunar_month = abs(int(lunar["month"]))
        season = next(
            (
                str(name)
                for name, months in definition["lunar_month_seasons"].items()
                if lunar_month in [int(item) for item in months]
            ),
            "",
        )
        taboo_branch = str(definition["taboo_branches"].get(season) or "")
        day_branch = day_ganzhi[1]
        matched = bool(taboo_branch and day_branch == taboo_branch)
        applicable_actions = [
            str(item) for item in definition.get("applicable_actions") or ()
        ]
        requested_actions = _clean_unique(raw_input.get("requested_actions") or [])
        applicable = not applicable_actions or bool(
            set(requested_actions) & set(applicable_actions)
        )
        active = matched and applicable
        value = {
            "lunar_month": lunar_month,
            "season": season,
            "day_branch": day_branch,
            "taboo_branch": taboo_branch,
            "matched": matched,
            "applicable": applicable,
            "applicable_actions": applicable_actions,
            "requested_actions": requested_actions,
            "authority": definition.get("authority"),
        }
    elif kind == "composite":
        gods = [str(item) for item in definition.get("gods") or ()]
        jianchu_values = [str(item) for item in definition.get("jianchu") or ()]
        matched_gods = [name for name in gods if name in all_gods]
        active = jianchu in jianchu_values or bool(matched_gods)
        value = {"jianchu": jianchu, "matched_gods": matched_gods}
    elif kind == "renshen_location":
        medical = source_table["folk_medical_tables"]
        active = True
        value = {
            "day_ganzhi": day_ganzhi,
            "stem_location": str(medical["renshen_by_day_stem"][day_ganzhi[0]]),
            "branch_location": str(
                medical["renshen_by_day_branch"][day_ganzhi[1]]
            ),
            "hour_locations": [
                {
                    "hour_branch": branch,
                    "location": str(medical["renshen_by_hour_branch"][branch]),
                }
                for branch in BRANCHES
            ],
            "authority": "folk_comparison_only",
        }
    elif kind == "day_ganzhi_set":
        declared = [
            str(item)
            for item in source_table["folk_medical_tables"][str(definition["table"])]
        ]
        active = day_ganzhi in declared
        value = {
            "day_ganzhi": day_ganzhi,
            "values": declared,
            "authority": "folk_comparison_only",
        }
    elif kind == "folk_comparison":
        hits = _folk_hits(
            abs(int(lunar["month"])), int(lunar["day"]), day_ganzhi, source_table
        )
        active = bool([item for item in hits if item["id"] != "folk.pengzu"])
        value = {
            "enabled_in_output": bool(raw_input.get("include_folk_comparison", False)),
            "rank_effect": "none",
            "hits": hits,
        }
    elif kind == "medical_policy":
        active = True
        value = {"policy": "professional_medical_care_controls"}
    else:
        raise ValueError(f"unsupported reference formula kind: {kind}")

    return {"active": bool(active), "kind": kind, "value": value}
