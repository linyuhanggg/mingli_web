#!/usr/bin/env python3
"""Benchmark the Web Runtime + configured DeepSeek model on a question PDF.

This is a test harness only. It does not change the Runtime, Provider, model
adapter, Web API, or Worker. The question pages are sent to the model first;
the answer page is opened only after every model result has been collected.

Usage::

    set -a
    . ~/.config/mingli/local-real-model.env
    set +a
    uv run --project backend python scripts/benchmark_web_core_questions.py \
        --pdf /path/to/试题-答案-提示词.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.adapters.model import DEEPSEEK_MODEL_ID
from app.adapters.runtime import build_runtime_startup_gate
from app.config import Settings
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_bazi_prepare,
    compile_ziwei_prepare,
)
from app.readings.runtime_contracts import Prepared


_QUESTION_START = re.compile(r"(?m)^\s*Q\s*([0-9]{1,2})\s*[.．、:：)]")
_OPTION_START = re.compile(r"^\s*[A-D]\s*[.．、:：)]")
_CUT_AFTER_QUESTION = re.compile(
    r"案例\s*[1-8]|参考答案|正确答案|答案|提示词|附录"
)
_ANSWER_PAIR = re.compile(r"(?<!\d)(\d{1,2})\s*[.．、:：)]\s*([ABCD])\b")


@dataclass(frozen=True, slots=True)
class ProfileSpec:
    case_id: str
    system: str
    birth_datetime: str
    timezone: str
    location: str
    gender: str
    question_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class QuestionGroup:
    group_id: str
    case_id: str
    question_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ModelResult:
    group_id: str
    question_numbers: tuple[int, ...]
    answers: dict[int, str]
    usage: dict[str, Any] | None


PROFILES: tuple[ProfileSpec, ...] = (
    ProfileSpec(
        "case-1", "bazi", "1951-11-14T10:00:00+08:00", "Asia/Shanghai",
        "广东", "女", (1, 2, 3, 4, 5),
    ),
    ProfileSpec(
        "case-2", "bazi", "1987-07-05T12:00:00+08:00", "Asia/Hong_Kong",
        "香港", "女", (6, 7, 8, 9, 10),
    ),
    ProfileSpec(
        "case-3", "bazi", "1983-04-21T06:30:00+09:00", "Asia/Tokyo",
        "宫崎，日本", "男", (11, 12, 13, 14, 15),
    ),
    ProfileSpec(
        "case-4", "ziwei", "1993-04-08T23:34:00+08:00", "Asia/Singapore",
        "新加坡", "男", (16, 17, 18, 19, 20),
    ),
    ProfileSpec(
        "case-5", "bazi", "1988-01-10T08:12:00+08:00", "Asia/Kuala_Lumpur",
        "马来西亚", "男", (21, 22, 23, 24, 25),
    ),
    ProfileSpec(
        "case-6", "ziwei", "1973-08-24T00:35:00+08:00", "Asia/Kuala_Lumpur",
        "马来西亚", "男", (26, 27, 28, 29, 30),
    ),
    ProfileSpec(
        "case-7", "ziwei", "1988-02-15T16:50:00+08:00", "Asia/Taipei",
        "台湾", "女", (31, 32, 33, 34, 35),
    ),
    ProfileSpec(
        "case-8", "bazi", "1970-07-22T16:00:00+08:00", "Asia/Shanghai",
        "北京", "男", (36, 37, 38, 39, 40),
    ),
)


def question_groups() -> tuple[QuestionGroup, ...]:
    """Make one model call per item while reusing each case's Web Brief.

    The public Bazi/Ziwei preview compilers currently expose the ``life``
    horizon. The harness therefore keeps that request contract intact and
    does not forge a year-horizon intent after compilation. Single-item model
    calls make the score measure answer selection rather than five-item
    batching behavior.
    """

    return tuple(
        QuestionGroup(
            group_id=f"{profile.case_id}-q{number}",
            case_id=profile.case_id,
            question_numbers=(number,),
        )
        for profile in PROFILES
        for number in profile.question_numbers
    )


def case_groups() -> tuple[QuestionGroup, ...]:
    """Return the eight exact Web preview requests used to build Briefs."""

    return tuple(
        QuestionGroup(
            group_id=f"{profile.case_id}-brief",
            case_id=profile.case_id,
            question_numbers=profile.question_numbers,
        )
        for profile in PROFILES
    )


def _pdftotext(pdf: Path, *, first_page: int | None = None, last_page: int | None = None) -> str:
    command = ["pdftotext", "-layout"]
    if first_page is not None:
        command.extend(["-f", str(first_page)])
    if last_page is not None:
        command.extend(["-l", str(last_page)])
    command.extend([str(pdf), "-"])
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise RuntimeError("pdftotext is required for PDF extraction") from error
    return completed.stdout


def extract_questions(pdf: Path, *, first_page: int, last_page: int) -> dict[int, str]:
    """Extract Q1-Q40 and stop each item before case/answer material."""

    text = _pdftotext(pdf, first_page=first_page, last_page=last_page)
    starts = list(_QUESTION_START.finditer(text))
    ids = [int(match.group(1)) for match in starts]
    if ids != list(range(1, 41)):
        raise RuntimeError(f"expected Q1-Q40 on question pages, found {ids!r}")

    questions: dict[int, str] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        segment_lines = text[match.start():end].splitlines()
        option_lines = [
            line_index
            for line_index, line in enumerate(segment_lines)
            if _OPTION_START.match(line)
        ]
        if len(option_lines) < 4:
            raise RuntimeError(f"Q{match.group(1)} has fewer than four options")

        cut = len(segment_lines)
        for line_index in range(option_lines[3] + 1, len(segment_lines)):
            if _CUT_AFTER_QUESTION.search(segment_lines[line_index]):
                cut = line_index
                break
        question = "\n".join(segment_lines[:cut]).strip()
        if re.search(r"参考答案|正确答案|提示词|附录", question):
            raise RuntimeError(f"answer/prompt material leaked into Q{match.group(1)}")
        questions[int(match.group(1))] = question
    return questions


def extract_answer_key(pdf: Path) -> dict[int, str]:
    """Read the answer table only after all model calls have completed."""

    text = _pdftotext(pdf)
    headings = list(re.finditer(r"第十六届全球算命大赛\s*答案", text))
    if not headings:
        # pdftotext may preserve the source's unusual spacing/characters.
        headings = list(re.finditer(r"答案\s*\n", text))
    if not headings:
        raise RuntimeError("answer heading not found after model run")

    tail = text[headings[-1].end():]
    answers: dict[int, str] = {}
    for match in _ANSWER_PAIR.finditer(tail):
        number = int(match.group(1))
        if 1 <= number <= 40:
            answers.setdefault(number, match.group(2))
        if len(answers) == 40:
            break
    if set(answers) != set(range(1, 41)):
        raise RuntimeError(f"answer table did not contain Q1-Q40: {sorted(answers)}")
    return answers

def _profile(spec: ProfileSpec) -> ConfirmedProfileVersion:
    return ConfirmedProfileVersion(
        subject_ref=f"profile-version:{spec.case_id}",
        birth_datetime=spec.birth_datetime,
        birth_datetime_or_four_pillars=spec.birth_datetime,
        timezone=spec.timezone,
        location=spec.location,
        gender=spec.gender,
        time_basis_policy="civil",
        zi_hour_policy="midnight",
        longitude=None,
        latitude=None,
        coordinate_source=None,
    )


def _query(
    spec: ProfileSpec,
    group: QuestionGroup,
    questions: dict[int, str],
) -> str:
    profile_text = (
        f"{spec.case_id}：{spec.gender}命，出生时间 {spec.birth_datetime}，"
        f"时区 {spec.timezone}，地点 {spec.location}。"
    )
    question_text = "\n\n".join(questions[number] for number in group.question_numbers)
    return (
        f"{profile_text}\n本次使用 Web 核心公开的本命/终身事实层。\n"
        "这是测试题。只依据 Prepared Brief 的确定性事实回答。"
        "严格输出 JSON：{\"answers\":{\"Q编号\":\"A或B或C或D\"}}。"
        "覆盖本组全部题号，每题只选一个选项，不解释，不输出其他字段。\n\n"
        + question_text
    )


def _parse_model_answers(value: object, question_numbers: tuple[int, ...]) -> dict[int, str]:
    answers: dict[int, str] = {}
    if not isinstance(value, dict):
        return answers
    for key, raw_value in value.items():
        number_match = re.search(r"\d+", str(key))
        choice = str(raw_value).strip().upper()
        if number_match and choice in {"A", "B", "C", "D"}:
            number = int(number_match.group())
            if number in question_numbers:
                answers[number] = choice
    return answers


async def _ask_deepseek(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    group: QuestionGroup,
    question_text: str,
    brief: dict[str, Any],
) -> ModelResult:
    endpoint = settings.model_base_url.rstrip("/") + settings.model_endpoint_path
    payload = {
        "model": DEEPSEEK_MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是严格的命理选择题测试模型。只根据用户给出的题目和 "
                    "Prepared Brief 事实作答。禁止使用外部答案、答案页、提示词或"
                    "虚构事实。只输出合法 JSON。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "questions": question_text,
                        "prepared_brief": brief,
                        "output_schema": {
                            "answers": {
                                f"Q{number}": "A|B|C|D"
                                for number in group.question_numbers
                            }
                        },
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
        ],
        "temperature": settings.model_temperature,
        "max_tokens": settings.model_max_output_tokens,
        "response_format": {"type": "json_object"},
        "stream": False,
        "enable_thinking": False,
    }
    # The production adapter's Candidate schema cannot represent A/B/C/D.
    # This test-only request mirrors its approved transport/model settings and
    # changes only the response contract to the benchmark's answer object.
    response = await client.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key.get_secret_value()}",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Content-Type": "application/json",
            "User-Agent": "FateRadar-ModelPort/1",
        },
        json=payload,
    )
    response.raise_for_status()
    decoded = response.json()
    content = decoded["choices"][0]["message"]["content"]
    model_json = json.loads(content)
    answers = _parse_model_answers(model_json.get("answers"), group.question_numbers)
    if set(answers) != set(group.question_numbers):
        raise RuntimeError(
            f"{group.group_id} model omitted answers: "
            f"expected {group.question_numbers}, got {sorted(answers)}"
        )
    return ModelResult(
        group_id=group.group_id,
        question_numbers=group.question_numbers,
        answers=answers,
        usage=decoded.get("usage") if isinstance(decoded.get("usage"), dict) else None,
    )


def _score(model_answers: dict[int, str], answer_key: dict[int, str]) -> tuple[int, list[int]]:
    wrong = [number for number in range(1, 41) if model_answers[number] != answer_key[number]]
    return 40 - len(wrong), wrong


async def run(args: argparse.Namespace) -> int:
    pdf = Path(args.pdf).expanduser().resolve()
    questions = extract_questions(
        pdf,
        first_page=args.question_first_page,
        last_page=args.question_last_page,
    )
    brief_groups = case_groups()
    groups = question_groups()
    profile_by_case = {profile.case_id: profile for profile in PROFILES}

    print(f"questions_extracted={len(questions)}")
    print(f"question_pages={args.question_first_page}-{args.question_last_page}")
    print(f"runtime_briefs={len(brief_groups)}")
    print(f"model_calls={len(groups)}")
    print("answer_key=withheld_until_after_model_calls")

    settings = Settings()
    if settings.model_adapter != "deepseek" or settings.deepseek_api_key is None:
        raise RuntimeError("real DeepSeek configuration is required")

    gate = build_runtime_startup_gate(settings)
    await gate.startup()
    briefs: dict[str, dict[str, Any]] = {}
    for brief_group in brief_groups:
        spec = profile_by_case[brief_group.case_id]
        profile = _profile(spec)
        query = _query(spec, brief_group, questions)
        if spec.system == "bazi":
            command = compile_bazi_prepare(
                action="profile_preview",
                query=query,
                profile=profile,
                dimension_ids=("overview", "career"),
            )
        else:
            command = compile_ziwei_prepare(
                action="ziwei_preview",
                query=query,
                profile=profile,
                dimension_ids=(
                    "career", "health", "location", "outcome",
                    "relationship", "state", "timing",
                ),
            )
        prepared = await gate.runtime.execute(command)
        if not isinstance(prepared, Prepared):
            raise RuntimeError(f"{brief_group.group_id} Runtime result: {prepared.to_dict()}")
        briefs[spec.case_id] = prepared.brief.to_dict()
        print(
            f"runtime {brief_group.group_id} prepared="
            f"{len(json.dumps(briefs[spec.case_id], ensure_ascii=False))} chars",
            flush=True,
        )

    model_answers: dict[int, str] = {}
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.model_connect_timeout_seconds,
            read=settings.model_read_timeout_seconds,
            write=settings.model_connect_timeout_seconds,
            pool=settings.model_connect_timeout_seconds,
        ),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        for index, group in enumerate(groups, start=1):
            spec = profile_by_case[group.case_id]
            question_text = "\n\n".join(
                questions[number] for number in group.question_numbers
            )
            result = await _ask_deepseek(
                client,
                settings,
                group=group,
                question_text=question_text,
                brief=briefs[spec.case_id],
            )
            model_answers.update(result.answers)
            answer_text = " ".join(
                f"Q{number}={result.answers[number]}"
                for number in group.question_numbers
            )
            print(
                f"[{index}/{len(groups)}] {group.group_id} "
                f"{answer_text}",
                flush=True,
            )

    # Deliberate ordering: answer key is not touched until all model calls end.
    answer_key = extract_answer_key(pdf)
    score, wrong = _score(model_answers, answer_key)
    print("answer_key=loaded_after_model_calls")
    for profile in PROFILES:
        numbers = profile.question_numbers
        case_score = sum(model_answers[number] == answer_key[number] for number in numbers)
        print(
            f"{profile.case_id} {case_score}/5 "
            + " ".join(f"Q{number}={model_answers[number]}" for number in numbers)
        )
    print(f"score={score}/40 accuracy={score / 40:.1%}")
    print("wrong_questions=" + ",".join(f"Q{number}" for number in wrong))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="question/answer PDF")
    parser.add_argument("--question-first-page", type=int, default=1)
    parser.add_argument("--question-last-page", type=int, default=13)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
