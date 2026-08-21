#!/usr/bin/env python3
"""Compile and explain the source-bound three-stage Da Liu Ren process."""

from __future__ import annotations

import copy
import re
from typing import Any


SCHEMA_VERSION = "mingli-liuren-process-v1"
STAGE_LABELS = {
    "initial": "初传",
    "middle": "中传",
    "final": "末传",
}
PROCESS_DIMENSIONS = {
    "outcome",
    "general_reading",
    "money_receipt",
    "finance",
    "relationship",
    "work",
    "travel",
    "education",
    "family",
    "children",
}
MONEY_SUBJECTS = (
    "工程款",
    "货款",
    "回款",
    "尾款",
    "工资",
    "薪资",
    "薪水",
    "奖金",
    "佣金",
    "退款",
    "赔款",
    "借款",
)


def _normalized_stages(fact_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    output = fact_snapshot.get("output")
    stages = output.get("three_transmissions") if isinstance(output, dict) else None
    if not isinstance(stages, list) or len(stages) != 3:
        raise ValueError("Da Liu Ren process requires exactly three transmissions")
    normalized: list[dict[str, Any]] = []
    for expected, raw in zip(("initial", "middle", "final"), stages):
        if not isinstance(raw, dict) or raw.get("stage") != expected:
            raise ValueError("Da Liu Ren process stages are missing or out of order")
        normalized.append(
            {
                "stage": expected,
                "label": STAGE_LABELS[expected],
                "branch": str(raw.get("branch") or ""),
                "six_relative": str(raw.get("six_relative") or ""),
                "heavenly_general": str(raw.get("heavenly_general") or ""),
                "season_strength": str(raw.get("season_strength") or ""),
                "is_xunkong": bool(raw.get("is_xunkong")),
            }
        )
    return normalized


def _process_profile(stages: list[dict[str, Any]]) -> str:
    initial, middle, final = stages
    if final["is_xunkong"]:
        return "final_void"
    if middle["is_xunkong"]:
        if initial["is_xunkong"]:
            return "initial_middle_void_final_real_conflict"
        return "middle_void"
    if initial["is_xunkong"]:
        return "initial_void_final_real"
    return "no_stage_void_direction"


def build_liuren_process_context(
    fact_snapshot: dict[str, Any],
    question_contract: dict[str, Any],
) -> dict[str, Any]:
    """Freeze stage facts before any prose maps them onto the question."""

    stages = _normalized_stages(fact_snapshot)
    requested = [
        str(item) for item in question_contract.get("requested_dimensions") or ()
    ]
    applicable = [item for item in requested if item in PROCESS_DIMENSIONS]
    output = fact_snapshot.get("output") or {}
    transmission_method = output.get("transmission_method") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": _process_profile(stages),
        "applicable_dimensions": applicable,
        "stages": copy.deepcopy(stages),
        "transmission_method": {
            "primary": str(transmission_method.get("primary") or ""),
            "use_method": str(transmission_method.get("use_method") or ""),
        },
        "source_rules": ["LM-R10", "LM-R12"],
        "confidence_ceiling": "low",
    }


def _money_subject(query: str) -> str:
    for token in MONEY_SUBJECTS:
        if token in query:
            return f"这笔{token}"
    if re.search(r"到账|入账|回款|收(?:到|回).{0,5}(?:钱|款)|结算", query):
        return "这笔款"
    return "这笔款项"


def _question_subject(query: str, dimension: str) -> str:
    if dimension == "money_receipt":
        return _money_subject(query)
    if dimension == "relationship":
        return "这段关系"
    if dimension == "work":
        if "确认" in query:
            return "这次确认消息"
        if re.search(r"消息|回复|答复|回应|通知|批复", query):
            return "这次消息"
        if "合作" in query:
            return "这次合作"
        if re.search(r"合同|签约|签下来|签单", query):
            return "这份合同"
        if "项目" in query:
            return "这个项目"
        return "这件工作上的事"
    if dimension == "finance":
        return "这件财务上的事"
    if dimension == "travel":
        return "这次出行或变动"
    return "这件事"


def _stage_phrase(stage: dict[str, Any]) -> str:
    status = "空" if stage["is_xunkong"] else "不空"
    details = "·".join(
        item
        for item in (
            stage["six_relative"],
            stage["heavenly_general"],
            stage["season_strength"],
        )
        if item
    )
    suffix = f"（{details}）" if details else ""
    return f"{stage['label']}{stage['branch']}{status}{suffix}"


def summarize_liuren_process(
    context: dict[str, Any],
    *,
    dimension: str,
    verdict: str,
    query: str,
    target_signal: dict[str, Any] | None = None,
) -> tuple[str, str | None, str | None]:
    """Render frozen stage facts without inventing a second calculation."""

    if context.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid Da Liu Ren process context")
    stages = context.get("stages") or []
    if len(stages) != 3:
        raise ValueError("Da Liu Ren process context has no complete three stages")
    initial, middle, final = stages
    subject = _question_subject(query, dimension)
    profile = str(context.get("profile") or "")

    if dimension == "money_receipt" and not any(
        stage.get("six_relative") == "妻财" for stage in stages
    ):
        process = "、".join(_stage_phrase(stage) for stage in stages)
        return (
            f"{subject}所需的妻财类神没有进入三传；三传过程是{process}。"
            "这能说明事情怎样推进，却不足以直接判到账或不到账。",
            None,
            "缺少款项类神时，不能用通用过程规则替代到账方向规则。",
        )

    if profile == "initial_void_final_real":
        opening = (
            f"{subject}有落实迹象，但不是一开始就顺。"
            if dimension == "money_receipt"
            else f"{subject}不是一开始就顺。"
        )
        conclusion = (
            f"{opening}{_stage_phrase(initial)}，发端容易悬着；"
            f"{_stage_phrase(middle)}，事情开始有承接；{_stage_phrase(final)}，后段转实。"
            "按原典‘先虽无着，后却有成’的阶段规则，直断是先卡后成，"
            "后面仍有推进到实处的机会。"
        )
        uncertainty = (
            "这里断的是先虚后实的过程方向；仍要受事项条件、填实与三传生克制约，"
            "不能当成无条件必成。"
        )
        return conclusion, None, uncertainty

    if profile == "initial_middle_void_final_real_conflict":
        conclusion = (
            f"{subject}的三段信号互相牵制：{_stage_phrase(initial)}，"
            f"{_stage_phrase(middle)}，推进到中段容易停住；{_stage_phrase(final)}，"
            "末段又出现落点。直断是中途反复，不能按一路顺成来看。"
        )
        return conclusion, None, "初末规则与中传空的规则相冲，结论保留为低置信混合方向。"

    if profile == "middle_void":
        conclusion = (
            f"{subject}开头能动，但{_stage_phrase(middle)}，按阶段规则像是将成而中止；"
            f"即使{_stage_phrase(final)}，也要先解决中段断点。"
        )
        return conclusion, None, "中传空只说明当前过程的断点，不等于现实条件永远无法改变。"

    if profile == "final_void":
        conclusion = (
            f"{subject}前面即使有动作，走到{_stage_phrase(final)}仍落空。"
            "按末传归计，眼下不宜把它断成能够完整落实。"
        )
        return conclusion, None, "末传空是当前课内的结果阻力，不是对现实事件作永久保证。"

    process = "、".join(_stage_phrase(stage) for stage in stages)
    if (
        isinstance(target_signal, dict)
        and target_signal.get("domain") == "message_or_document"
        and target_signal.get("present_in_transmissions") is True
    ):
        stage_label = STAGE_LABELS.get(str(target_signal.get("stage") or ""), "三传")
        branch = str(target_signal.get("branch") or "")
        strength = str(target_signal.get("season_strength") or "")
        general = str(target_signal.get("heavenly_general") or "")
        location = f"{stage_label}{branch}" if branch else stage_label
        modifier = (
            f"，所乘{general}只作后置成色修饰，不能单独翻转方向"
            if general
            else ""
        )
        if target_signal.get("is_xunkong") is True:
            target_reading = (
                f"父母类神虽落在{location}，但逢空，说明消息有名而未实{modifier}"
            )
        elif strength in {"旺", "相"}:
            target_reading = (
                f"父母类神落在{location}且得{strength}气，消息本身有承接力{modifier}"
            )
        elif strength in {"囚", "死"}:
            target_reading = (
                f"父母类神落在{location}，说明确有消息落点；但为{strength}气，"
                f"明确度和落实度要打折{modifier}"
            )
        else:
            target_reading = f"父母类神落在{location}，消息进入课传，但力量普通{modifier}"
        if verdict == "support":
            return (
                f"{subject}偏有回应或落点，不像完全等不到；{target_reading}。"
                f"三传依次为{process}。",
                None,
                "这里的支持方向不等于无条件正式敲定；类神衰空与天将只能据实保留为限制。",
            )
        if verdict == "oppose":
            return (
                f"{subject}眼下较难形成你要的明确落点；{target_reading}。"
                f"三传依次为{process}。",
                None,
                "这是当前课内的阻力方向，不是对现实沟通作永久保证。",
            )
        if verdict == "mixed":
            return (
                f"{subject}有回应迹象，但能否成为明确确认仍相互牵制；"
                f"{target_reading}。三传依次为{process}。",
                None,
                "类神存在与其衰空条件方向相反，不能删掉其中一边。",
            )
    if dimension == "money_receipt" and verdict == "support":
        return (
            f"{subject}有落实迹象，不像完全落空；三传过程为{process}。",
            None,
            "主断落在款项有承接；是否落账以账户实际变动校验。",
        )
    if verdict == "support":
        return f"{subject}的承接条件较强；三传依次为{process}。", None, None
    if verdict == "oppose":
        return f"{subject}眼下阻力较强；三传依次为{process}。", None, None
    return (
        f"{subject}的三传依次为{process}，过程事实完整，但现有适用规则不足以定成单一方向。",
        None,
        "保留未决是因为缺少可适用的定向规则，不是因为没有起课。",
    )


__all__ = [
    "PROCESS_DIMENSIONS",
    "build_liuren_process_context",
    "summarize_liuren_process",
]
