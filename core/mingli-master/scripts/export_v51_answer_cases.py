#!/usr/bin/env python3
"""Export answer-replay cases through the real portable production seam.

The JSONL is deliberately not hand-authored.  Every ``brief`` below is the
exact result of ``ReadingInterface.execute(Prepare)`` using synthetic inputs
and an isolated temporary store.  The exporter never persists state tokens,
reading ids, private evidence, or staged digests: the drafting boundary is
the public ``ReadingBrief`` and its canonical hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "tests/replay/mingli-answer-cases.jsonl"


_CASE_META: tuple[dict[str, Any], ...] = (
    {
        "case_id": "answer-bazi-career",
        "coverage_tags": [
            "bazi", "direct_answer", "explain_plainly", "paraphrase",
        ],
        "review_rubric": {
            "required": "先给事业主线，再把决定性盘面与现实取舍讲清，并遵守倾向性上限",
            "forbidden": "编造具体公司、职位、金额、履历或保证结果",
        },
    },
    {
        "case_id": "answer-cross-bazi-ziwei",
        "coverage_tags": ["cross_check_bazi_ziwei", "cross_system"],
        "review_rubric": {
            "required": "分别说明两个独立 scope 在事业问题上各自支持什么，再给有边界的综合主线",
            "forbidden": "合并两套符号、按票数裁决或声称交叉后自动提高确定性",
        },
    },
    {
        "case_id": "answer-fortune-week-overview",
        "coverage_tags": [
            "fortune", "broad_overview", "ambient_context_noise",
            "direct_answer",
        ],
        "ambient_context": ["订单", "回款", "对账"],
        "review_rubric": {
            "required": "先用一句话给本周主线，再只展开最关键的节奏和取舍，不带入更早宿主消息的业务主题",
            "forbidden": "订单、回款、对账、客户项目、具体金额、逐字段复述或必然事件",
        },
    },
    {
        "case_id": "answer-bazi-partial-pillars-overview",
        "coverage_tags": [
            "bazi", "broad_overview", "partial_luck_sequence",
            "salience_candidates", "ambient_context_noise", "direct_answer",
        ],
        "ambient_context": ["订单", "回款", "对账"],
        "review_rubric": {
            "required": "先抓住当前盘面最突出的一两条主线直接回答用户的宏观问题；大运只能说顺逆与干支顺序，并如实说明起运时间不可得",
            "forbidden": "起运岁数、对应公历年份、当前大运、流年应期、无校准百分比、订单、回款、对账、固定生活栏目清单",
        },
    },
    {
        "case_id": "answer-liuyao-one-sentence",
        "coverage_tags": ["liuyao", "one_sentence", "short_answer"],
        "review_rubric": {
            "required": "用极简篇幅直接给出动或不动的倾向与一个关键条件",
            "forbidden": "展开成完整报告、罗列全部盘面或写成无条件保证",
        },
    },
    {
        "case_id": "answer-fengshui-zero-evidence",
        "coverage_tags": ["fengshui", "zero_evidence", "scope_boundary"],
        "review_rubric": {
            "required": "只描述本轮公开的空间观察及其可说范围，并明确没有可引用出处",
            "forbidden": "虚构出处、推出个人吉凶、业务结果或住宅之外的信息",
        },
    },
    {
        "case_id": "answer-xingming-continuation",
        "coverage_tags": ["xingming", "continuation", "direct_answer"],
        "review_rubric": {
            "required": "先回答最新问题，结合 prior_answer 继续深入而不重讲整份解读",
            "forbidden": "复述首轮全文、指定具体行业岗位或加入未提供经历",
        },
    },
    {
        "case_id": "answer-bazi-correction",
        "coverage_tags": ["bazi", "correction", "direct_answer"],
        "review_rubric": {
            "required": "只按更正后的公开 brief 重下主结论，不借用旧答案",
            "forbidden": "沿用旧资料、猜测旧结论或追认具体既成事件",
        },
    },
    {
        "case_id": "answer-liuren-horizon-boundary",
        "coverage_tags": ["liuren", "horizon_boundary", "exact_event_boundary"],
        "review_rubric": {
            "required": "说明本轮能判断到的时机粒度，并集中交代 horizon boundary",
            "forbidden": "给出 brief 未支持的具体日期、伪称没有证据或写成必然应期",
        },
    },
)


def scenario_ids() -> tuple[str, ...]:
    """Return the stable case catalog without importing provider runtime."""

    return tuple(item["case_id"] for item in _CASE_META)


def canonical_value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture must be an object: {path}")
    return value


def _birth_facts(value: str = "1994-04-30T05:55:00") -> dict[str, Any]:
    return {
        "birth_datetime": value,
        "birth_datetime_or_four_pillars": value,
        "timezone": "Asia/Shanghai",
        "location": "上海",
        "gender": "female",
        "time_basis_policy": "civil",
        "zi_hour_policy": "midnight",
        "longitude": 121.4737,
        "latitude": 31.2304,
        "coordinate_source": "synthetic-fixture",
    }


def _event_facts() -> dict[str, Any]:
    value = "2026-07-30T12:00:00+08:00"
    return {
        "event_datetime_or_reference_datetime": value,
        "event_datetime": value,
        "reference_datetime": value,
        "timezone": "Asia/Shanghai",
        "location": "上海",
        "time_basis_policy": "civil",
        "longitude": 121.4737,
        "latitude": 31.2304,
        "coordinate_source": "synthetic-fixture",
    }


def _fengshui_spec(root: Path) -> dict[str, Any]:
    fengshui = _load_yaml(root / "references/fixtures/fengshui-v51.yaml")
    return deepcopy(next(
        item["input"]["fengshui_spec"]
        for item in fengshui["complete_observation_fixtures"]
        if item["id"] == "FS-O05"
    ))


def _prepare(
    interface: Any,
    *,
    query: str,
    subject_ref: str,
    capability_id: str,
    object_id: str,
    dimension_ids: tuple[str, ...],
    horizon_kind: str,
    facts: Mapping[str, Any],
    horizon_start: str | None = None,
    horizon_end: str | None = None,
    comparison_id: str | None = None,
    state_token: str | None = None,
    transition: str | None = None,
) -> Any:
    from reading_engine.interface_contracts import (
        ComparisonSelection,
        HorizonSelection,
        IntentSelection,
        Prepare,
    )

    comparisons = (
        (
            ComparisonSelection(
                capability_id=comparison_id,
                requirement="required",
            ),
        )
        if comparison_id
        else ()
    )
    return interface.execute(
        Prepare(
            query=query,
            intent=IntentSelection(
                subject_refs=(subject_ref,),
                object_id=object_id,
                dimension_ids=dimension_ids,
                horizon=HorizonSelection(
                    kind_id=horizon_kind,
                    start=horizon_start,
                    end=horizon_end,
                ),
                capability_id=capability_id,
                comparisons=comparisons,
            ),
            facts={subject_ref: deepcopy(dict(facts))},
            state_token=state_token,
            transition=transition,
        )
    )


def _new_case_config(root: Path, case_id: str) -> dict[str, Any]:
    birth = _birth_facts()
    event = _event_facts()
    fortune = {**birth, "reference_datetime": "2026-07-29T10:00:00+08:00"}
    fengshui_spec = _fengshui_spec(root)
    standard_subject = "subject:synthetic"
    configs: dict[str, dict[str, Any]] = {
        "answer-bazi-career": dict(
            query="看一下这个八字，事业上最该先抓住哪条主线？",
            capability_id="bazi", object_id="natal",
            dimension_ids=("career",), horizon_kind="life", facts=birth,
        ),
        "answer-cross-bazi-ziwei": dict(
            query="用八字和紫微一起看，事业上最重要的主线是什么？",
            capability_id="bazi", comparison_id="ziwei", object_id="natal",
            dimension_ids=("career",), horizon_kind="life", facts=birth,
        ),
        "answer-fortune-week-overview": dict(
            query="算一下这周运势。", capability_id="fortune",
            object_id="near_time_personal", dimension_ids=(),
            horizon_kind="week", horizon_start="2026-07-27",
            horizon_end="2026-08-02", facts=fortune,
        ),
        "answer-bazi-partial-pillars-overview": dict(
            query="只有四柱和性别，帮我整体看看这个八字，也说说目前能确定的大运信息。",
            capability_id="bazi", object_id="natal",
            dimension_ids=("overview",), horizon_kind="life",
            facts={
                "birth_datetime_or_four_pillars": [
                    "乙酉", "辛巳", "丙午", "癸巳",
                ],
                "gender": "male",
            },
        ),
        "answer-liuyao-one-sentence": dict(
            query="一句话回答：这件事现在该不该动？",
            capability_id="liuyao", object_id="concrete_event",
            dimension_ids=("outcome",), horizon_kind="instant",
            facts={**event, "cast": [6, 7, 8, 9, 7, 8]},
        ),
        "answer-fengshui-zero-evidence": dict(
            query="只看这处开口观察，本轮能说明到什么程度？",
            capability_id="fengshui", object_id="spatial_observation",
            dimension_ids=("state",), horizon_kind="instant",
            facts={"fengshui_spec": fengshui_spec},
        ),
        "answer-liuren-horizon-boundary": dict(
            query="什么时候能搬进去？能判断到什么时间粒度？",
            capability_id="liuren", object_id="concrete_event",
            dimension_ids=("timing",), horizon_kind="instant", facts=event,
        ),
    }
    config = configs[case_id]
    config.setdefault("subject_ref", standard_subject)
    return config


def _execute_case(root: Path, case_id: str) -> dict[str, Any]:
    from reading_engine.interface import ReadingInterface
    from reading_engine.interface_contracts import Accepted, Complete, Prepared
    from reading_engine.runtime_context import build_runtime_context

    context = build_runtime_context(
        now_iso="2026-07-29T10:00:00+08:00",
        default_timezone_name="Asia/Shanghai",
    )
    with tempfile.TemporaryDirectory(prefix="mingli-answer-export-") as temporary:
        interface = ReadingInterface(
            skill_root=root,
            store_root=Path(temporary),
            runtime_context=context,
        )
        if case_id == "answer-xingming-continuation":
            config = dict(
                query="先看事业主线。", subject_ref="subject:synthetic",
                capability_id="xingming", object_id="natal",
                dimension_ids=("career",), horizon_kind="year",
                facts=_birth_facts(),
            )
            first = _prepare(interface, **config)
            if not isinstance(first, Prepared):
                raise RuntimeError(f"{case_id}: first Prepare returned {first!r}")
            prior_copy = "上一轮的主线是先把一个方向做深，再谈同时铺开更多选择。"
            accepted = interface.execute(
                Complete(state_token=first.state_token, public_copy=prior_copy)
            )
            if not isinstance(accepted, Accepted):
                raise RuntimeError(f"{case_id}: Complete returned {accepted!r}")
            config["query"] = "那按刚才说的，这几年最该守住的是哪一点？"
            config["state_token"] = accepted.state_token
            result = _prepare(interface, **config)
        elif case_id == "answer-bazi-correction":
            config = dict(
                query="先看事业主线。", subject_ref="subject:synthetic",
                capability_id="bazi", object_id="natal",
                dimension_ids=("career",), horizon_kind="year",
                facts=_birth_facts(),
            )
            first = _prepare(interface, **config)
            if not isinstance(first, Prepared):
                raise RuntimeError(f"{case_id}: first Prepare returned {first!r}")
            accepted = interface.execute(
                Complete(
                    state_token=first.state_token,
                    public_copy="第一轮已经按原资料给过事业主线。",
                )
            )
            if not isinstance(accepted, Accepted):
                raise RuntimeError(f"{case_id}: Complete returned {accepted!r}")
            config.update(
                query="出生时间更正了，请按更正后的资料重新说主结论。",
                facts=_birth_facts("1992-08-17T14:30:00"),
                state_token=accepted.state_token,
                transition="correct",
            )
            result = _prepare(interface, **config)
        else:
            result = _prepare(interface, **_new_case_config(root, case_id))

        if not isinstance(result, Prepared):
            payload = result.to_dict() if hasattr(result, "to_dict") else repr(result)
            raise RuntimeError(f"{case_id}: expected Prepared, got {payload}")
        return result.brief.to_dict()


def generate_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metadata in _CASE_META:
        brief = _execute_case(root, metadata["case_id"])
        row = deepcopy(metadata)
        row["brief_sha256"] = canonical_value_sha256(brief)
        row["brief"] = brief
        rows.append(row)
    return rows


def _render(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(
            row,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
        for row in rows
    )


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def materialize_generation_packets(
    *,
    rows: list[dict[str, Any]],
    output_dir: Path,
    skill_snapshots: tuple[tuple[str, Path], ...],
) -> dict[str, Any]:
    """Freeze the only files a blind drafting task is told to read."""

    labels = [label for label, _ in skill_snapshots]
    if len(skill_snapshots) < 2 or len(set(labels)) != len(labels):
        raise ValueError("at least two uniquely labeled Skill snapshots are required")
    if any(
        not label
        or Path(label).name != label
        or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for character in label)
        for label in labels
    ):
        raise ValueError("Skill snapshot labels must be safe lowercase file names")
    if output_dir.exists():
        raise ValueError(f"packet output already exists: {output_dir}")

    packet_root = output_dir / "generation-packets"
    skill_root = output_dir / "skill-snapshots"
    packet_root.mkdir(parents=True)
    skill_root.mkdir()
    packet_manifest: list[dict[str, Any]] = []
    seen_cases: set[str] = set()
    for row in rows:
        case_id = str(row.get("case_id") or "")
        brief = row.get("brief")
        brief_sha256 = str(row.get("brief_sha256") or "")
        if (
            not case_id
            or case_id in seen_cases
            or not isinstance(brief, dict)
            or canonical_value_sha256(brief) != brief_sha256
        ):
            raise ValueError(f"invalid frozen answer case: {case_id!r}")
        seen_cases.add(case_id)
        packet = {
            "case_id": case_id,
            "brief_sha256": brief_sha256,
            "brief": brief,
        }
        relative = Path("generation-packets") / f"{case_id}.brief.json"
        payload = _canonical_json_bytes(packet)
        (output_dir / relative).write_bytes(payload)
        packet_manifest.append(
            {
                "case_id": case_id,
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    skill_manifest: list[dict[str, Any]] = []
    for label, source in skill_snapshots:
        payload = source.read_bytes()
        if not payload:
            raise ValueError(f"empty Skill snapshot: {source}")
        relative = Path("skill-snapshots") / f"{label}.SKILL.md"
        (output_dir / relative).write_bytes(payload)
        skill_manifest.append(
            {
                "label": label,
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    manifest = {
        "schema_version": "mingli-generation-packet-manifest-v1",
        "case_count": len(packet_manifest),
        "packet_keys": ["case_id", "brief_sha256", "brief"],
        "packets": packet_manifest,
        "skill_snapshots": skill_manifest,
        "isolation": "procedural; enforce an OS sandbox when the host supports it",
    }
    (output_dir / "generation-manifest.json").write_bytes(
        _canonical_json_bytes(manifest)
    )
    return manifest


def _parse_skill_snapshots(values: list[str]) -> tuple[tuple[str, Path], ...]:
    parsed: list[tuple[str, Path]] = []
    for value in values:
        label, separator, path = value.partition("=")
        if not separator or not path:
            raise ValueError("--skill-snapshot must be LABEL=PATH")
        parsed.append((label, Path(path)))
    return tuple(parsed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skill-snapshot", action="append", default=[])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--materialize-packets", type=Path)
    args = parser.parse_args()

    if args.materialize_packets:
        rows = [
            json.loads(line)
            for line in args.output.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        manifest = materialize_generation_packets(
            rows=rows,
            output_dir=args.materialize_packets,
            skill_snapshots=_parse_skill_snapshots(args.skill_snapshot),
        )
        print(
            f"wrote {manifest['case_count']} isolated generation packets to "
            f"{args.materialize_packets}"
        )
        return 0
    if args.skill_snapshot:
        parser.error("--skill-snapshot requires --materialize-packets")

    rendered = _render(generate_rows(ROOT))
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(f"stale production-exported fixture: {args.output}")
            return 1
        print(f"ok: {len(scenario_ids())} production-exported answer cases")
        return 0
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {len(scenario_ids())} cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
