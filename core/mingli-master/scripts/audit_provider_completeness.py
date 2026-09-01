#!/usr/bin/env python3
"""Build and audit the evidence-derived Task 7N provider matrix."""

from __future__ import annotations

import argparse
import contextlib
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import os
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any
from unittest import mock

# This audit imports pinned runtime packages before ``build_matrix`` can set
# its multiprocessing environment guard. Direct invocations must therefore
# disable cache writes at process startup as well as in spawned workers,
# without changing interpreter state when the module is imported as a library.
if __name__ == "__main__":
    sys.dont_write_bytecode = True

import yaml

import audit_algorithm_sources
import audit_bazi_provider
import audit_fengshui_provider
import audit_fortune_provider
import audit_liuren_provider
import audit_liuyao_provider
import audit_luming_provider
import audit_meihua_provider
import audit_physiognomy_provider
import audit_qimen_provider
import audit_selection_provider
import audit_taiyi_provider
import audit_xingming_provider
import audit_ziwei_provider
import audit_test_session
import build_evidence_index
import reading_evidence_bundle
import reading_source_plan
from reading_engine import liuyao, luming
from reading_engine.contracts import (
    AcceptedReading,
    AnswerDraft,
    CalculationResult,
    ClaimTrace,
    FactExtensionResult,
    InternalFailure,
    PreparedReading,
    ReadingRequest,
    canonical_digest,
)
from reading_engine.evidence_rules import load_evidence_rules, match_rule
from reading_engine.fact_index import build_fact_index
from reading_engine.factory import build_production_engine
from reading_engine.catalog import CatalogLoader
from reading_engine.provider_protocol import (
    ProviderContext,
    ProviderPreparation,
    ProviderRequest,
)
from reading_engine.providers import (
    BaziProvider,
    FengshuiProvider,
    FortuneProvider,
    LiurenProvider,
    LiuyaoProvider,
    LumingProvider,
    MeihuaProvider,
    PhysiognomyProvider,
    QimenProvider,
    SelectionProvider,
    STRUCTURED_SYSTEMS,
    TaiyiProvider,
    XingmingProvider,
    ZiweiProvider,
)
from reading_engine.providers import PROVIDER_CAPABILITIES


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "references" / "matrices" / "provider-completeness.yaml"
SCHEMA_VERSION = "mingli-provider-completeness-v1"
RUNTIME_INTEGRITY_ARTIFACTS = (
    "requirements-runtime.lock",
    "requirements-runtime-build.lock",
    "scripts/runtime_python.py",
    "scripts/runtime_launcher.py",
    "scripts/provision_runtime.py",
    "scripts/run_reading_transaction.sh",
)
MATRIX_FINGERPRINT_EXCLUDED_SCRIPTS = {
    "audit_test_session.py",
    "run_test_suite.py",
}
EXPECTED_SYSTEMS = (
    "bazi",
    "fortune",
    "ziwei",
    "luming-nayin",
    "xingming",
    "liuyao",
    "meihua",
    "liuren",
    "qimen",
    "taiyi",
    "selection",
    "fengshui",
    "physiognomy",
)
# Execution order is cost-based only.  The merged public matrix still follows
# EXPECTED_SYSTEMS, so scheduling cannot change the artifact.
MATRIX_EXECUTION_ORDER = (
    "liuren",
    "qimen",
    "selection",
    "taiyi",
    "bazi",
    "ziwei",
    "fortune",
    "liuyao",
    "meihua",
    "luming-nayin",
    "xingming",
    "fengshui",
    "physiognomy",
)
PROVIDER_CLASSES = {
    "bazi": BaziProvider,
    "fortune": FortuneProvider,
    "ziwei": ZiweiProvider,
    "luming-nayin": LumingProvider,
    "xingming": XingmingProvider,
    "liuyao": LiuyaoProvider,
    "meihua": MeihuaProvider,
    "liuren": LiurenProvider,
    "qimen": QimenProvider,
    "taiyi": TaiyiProvider,
    "selection": SelectionProvider,
    "fengshui": FengshuiProvider,
    "physiognomy": PhysiognomyProvider,
}
EXPECTED_PROVIDER_IDENTITIES = {
    "bazi": (
        "reading_engine.providers.BaziProvider",
        "mingli-master.bazi.v7",
        "mingli-bazi-pipeline-v1-interpreted",
    ),
    "fortune": (
        "reading_engine.providers.FortuneProvider",
        "mingli-master.fortune.v6",
        "fortune-public-v6-mechanism-stack",
    ),
    "ziwei": (
        "reading_engine.providers.ZiweiProvider",
        "mingli-master.ziwei.iztro",
        "1.2.0+iztro-2.5.8",
    ),
    "luming-nayin": (
        "reading_engine.providers.LumingProvider",
        "mingli-master.luming-nayin.v1",
        "1.2.0",
    ),
    "xingming": (
        "reading_engine.providers.XingmingProvider",
        "mingli-master.xingming.v1",
        "1.1.0",
    ),
    "liuyao": (
        "reading_engine.providers.LiuyaoProvider",
        "mingli-master.liuyao.v1",
        "1.4.0",
    ),
    "meihua": (
        "reading_engine.providers.MeihuaProvider",
        "mingli-master.meihua.v1",
        "1.1.0",
    ),
    "liuren": (
        "reading_engine.providers.LiurenProvider",
        "mingli-master.liuren.v8",
        "mingli-liuren-pipeline-v6-runtime-contract",
    ),
    "qimen": (
        "reading_engine.providers.QimenProvider",
        "mingli-master.qimen.v1",
        "5.2.0",
    ),
    "taiyi": (
        "reading_engine.providers.TaiyiProvider",
        "mingli-master.taiyi.v1",
        "5.2.0",
    ),
    "selection": (
        "reading_engine.providers.SelectionProvider",
        "mingli-master.selection.v1",
        "1.3.0",
    ),
    "fengshui": (
        "reading_engine.providers.FengshuiProvider",
        "mingli-master.fengshui.v1",
        "1.0.0",
    ),
    "physiognomy": (
        "reading_engine.providers.PhysiognomyProvider",
        "mingli-master.physiognomy.v1",
        "1.1.0",
    ),
}
DEDICATED_AUDIT_MODULES = {
    "bazi": audit_bazi_provider,
    "fortune": audit_fortune_provider,
    "ziwei": audit_ziwei_provider,
    "luming-nayin": audit_luming_provider,
    "xingming": audit_xingming_provider,
    "liuyao": audit_liuyao_provider,
    "meihua": audit_meihua_provider,
    "liuren": audit_liuren_provider,
    "qimen": audit_qimen_provider,
    "taiyi": audit_taiyi_provider,
    "selection": audit_selection_provider,
    "fengshui": audit_fengshui_provider,
    "physiognomy": audit_physiognomy_provider,
}
LIUYAO_RANDOM_CAST_PROOFS = (
    "new_seed_format_valid",
    "new_seed_not_reading_id_derived",
    "public_contract_seed_redacted",
    "stored_request_seed_redacted",
    "private_calculation_seed_persisted",
    "restart_replay_exact",
    "continuation_seed_reused",
    "correction_seed_reused",
    "recast_created_new_reading",
    "recast_seed_distinct",
    "seed_commitment_verified",
    "public_report_seed_redacted",
)

SOURCE_PACKS = {
    "bazi": (
        "bazi/sanming-tonghui",
        "bazi/yuanhai-ziping",
        "bazi/ziping-zhenquan",
        "bazi/ditiansui-chanwei",
        "bazi/qiongtong-baojian",
    ),
    "fortune": (
        "bazi/yuanhai-ziping",
        "bazi/ditiansui-chanwei",
        "bazi/qiongtong-baojian",
    ),
    "ziwei": (
        "ziwei/ziwei-doushu-quanshu",
        "ziwei/taiwei-fu",
    ),
    "luming-nayin": (
        "luming-nayin/li-xuzhong-mingshu",
        "luming-nayin/luoluzi-sanming",
        "luming-nayin/wuxing-jingji",
        "luming-nayin/lantai-miaoxuan",
    ),
    "xingming": (
        "xingming/guotian-jing",
        "xingming/xingming-suyuan",
        "xingming/xingxue-dacheng",
    ),
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
        "san-shi/liuren-zhiyin",
        "san-shi/liuren-miben",
    ),
    "qimen": (
        "san-shi/qimen-dunjia-tongzhi",
        "san-shi/qimen-faqiao",
    ),
    "taiyi": ("san-shi/taiyi-shenshu",),
    "selection": (
        "selection/xieji-bianfang-shu",
        "selection/xingli-kaoyuan",
        "selection/yuqia-ji",
        "selection/donggong-zeri",
    ),
    "fengshui": tuple(
        f"fengshui/{name}"
        for name in (
            "zangfa-daozhang",
            "dutian-baozhao-jing",
            "qingnang-xu",
            "zangshu",
            "tianyu-jing",
            "xuexin-fu",
            "yangzhai-sanyao",
            "yangzhai-shishu",
            "qingnang-jing",
            "hanlong-jing",
            "shenshi-xuankong-xue",
            "huangdi-zhaijing",
            "rudi-yan-quanshu",
            "yilong-jing",
            "qingnang-aoyu",
            "dili-bianzheng",
        )
    ),
    "physiognomy": (
        "physiognomy/liuzhuang-xiangfa",
        "physiognomy/shenxiang-quanbian",
        "physiognomy/mayi-shenxiang",
        "physiognomy/bingjian",
    ),
}


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve one strict RFC 6901 pointer or raise on any missing segment."""

    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("JSON pointer must be empty or start with '/'")

    current = document
    for raw_token in pointer[1:].split("/"):
        token_parts: list[str] = []
        index = 0
        while index < len(raw_token):
            character = raw_token[index]
            if character != "~":
                token_parts.append(character)
                index += 1
                continue
            if index + 1 >= len(raw_token) or raw_token[index + 1] not in "01":
                raise ValueError(f"invalid RFC 6901 escape in {pointer!r}")
            token_parts.append("~" if raw_token[index + 1] == "0" else "/")
            index += 2
        token = "".join(token_parts)
        if isinstance(current, Mapping):
            if token not in current:
                raise KeyError(token)
            current = current[token]
            continue
        if isinstance(current, Sequence) and not isinstance(
            current, (str, bytes, bytearray)
        ):
            if token == "-" or not token.isdigit():
                raise ValueError(f"invalid array index {token!r}")
            if len(token) > 1 and token.startswith("0"):
                raise ValueError(f"non-canonical array index {token!r}")
            current = current[int(token)]
            continue
        raise TypeError(f"cannot descend through {type(current).__name__}")
    return current


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"probe fixture must be an object: {path}")
    return payload


def _physiognomy_intent(subject_ref: str) -> dict[str, Any]:
    return {
        "subject_refs": [subject_ref],
        "calculation_object": "visible_observation",
        "question_dimensions": ["state", "source_comparison"],
        "horizon": {"kind": "instant", "start": None, "end": None},
        "requested_method": "physiognomy",
        "requested_granularity": "region",
        "continuity": {
            "reading_id": None,
            "same_subject": False,
            "same_event": False,
        },
        "facts_present": ["physiognomy_spec"],
        "facts_corrected": [],
        "evidence_questions": ["核对可见观察和来源边界"],
    }


def _representative_request(system: str, *, root: Path) -> ReadingRequest:
    common_birth = {
        "datetime": "2000-10-18T06:45:00",
        "timezone": "Asia/Shanghai",
        "location": "上海",
        "gender": "male",
    }
    if system == "bazi":
        return ReadingRequest(
            query="Task 7N Bazi probe",
            system=system,
            reference_datetime="2026-07-24T12:00:00+08:00",
            timezone="Asia/Shanghai",
            location="上海",
            birth_data=common_birth,
        )
    if system == "fortune":
        return ReadingRequest(
            query="Task 7N Fortune probe",
            system=system,
            reference_datetime="2024-01-01T12:00:00+08:00",
            timezone="Asia/Shanghai",
            location="上海",
            birth_data={
                "birth_datetime": "2000-10-18T06:45:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
                "gender": "male",
            },
        )
    if system == "ziwei":
        return ReadingRequest(
            query="Task 7N Ziwei probe",
            system=system,
            reference_datetime="2026-07-24T12:00:00+08:00",
            timezone="Asia/Shanghai",
            location="上海",
            birth_data={
                "datetime": "1990-01-01T12:00:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
                "gender": "female",
            },
        )
    if system == "luming-nayin":
        return ReadingRequest(
            query="Task 7N Luming probe",
            system=system,
            timezone="Asia/Shanghai",
            location="上海",
            chart_data={"pillars": ["甲子", "丙寅", "壬辰", "辛酉"]},
        )
    if system == "xingming":
        return ReadingRequest(
            query="Task 7N Xingming probe",
            system=system,
            reference_datetime="2026-07-24T12:00:00+08:00",
            timezone="Asia/Shanghai",
            location="上海",
            birth_data={
                "datetime": "2000-01-01T20:00:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
                "longitude": 121.4737,
                "latitude": 31.2304,
                "coordinate_source": "fixture:WGS84",
                "gender": "male",
            },
        )
    if system == "liuyao":
        return ReadingRequest(
            query="Task 7N Liuyao supplied-cast probe",
            system=system,
            event_datetime="2024-02-10T12:00:00",
            timezone="Asia/Shanghai",
            location="上海",
            chart_data={"tosses": [9, 7, 7, 7, 7, 6]},
        )
    if system == "meihua":
        return ReadingRequest(
            query="Task 7N Meihua probe",
            system=system,
            event_datetime="2024-02-10T12:00:00",
            timezone="Asia/Shanghai",
            location="上海",
            chart_data={
                "casting_method": "supplied_hexagram",
                "upper_trigram": "兑",
                "lower_trigram": "离",
                "moving_line": 1,
                "provenance": {"kind": "user_supplied_complete_hexagram"},
            },
        )
    if system == "liuren":
        return ReadingRequest(
            query="Task 7N Liuren probe",
            system=system,
            reference_datetime="2026-07-24T12:00:00+08:00",
            timezone="Asia/Shanghai",
            location="上海",
        )
    if system == "qimen":
        return ReadingRequest(
            query="Task 7N Qimen probe",
            system=system,
            event_datetime="2024-06-21T04:51:00",
            timezone="Asia/Shanghai",
            location="上海",
        )
    if system == "taiyi":
        return ReadingRequest(
            query="Task 7N Taiyi probe",
            system=system,
            reference_datetime="2024-06-21T12:00:00",
            timezone="Asia/Shanghai",
            location="上海",
        )
    if system == "selection":
        return ReadingRequest(
            query="Task 7N Selection probe",
            system=system,
            timezone="Asia/Shanghai",
            location="上海",
            chart_data={
                "selection_spec": {
                    "event_profile": "business_opening_transaction",
                    "requested_actions": ["开市"],
                    "date_range": {
                        "start": "2026-07-24",
                        "end": "2026-07-28",
                    },
                    "hard_constraints": {},
                    "participant_facts": [],
                    "include_folk_comparison": False,
                }
            },
        )
    if system == "fengshui":
        fixture = _load_yaml(root / "references/fixtures/fengshui-v51.yaml")
        case = fixture["complete_observation_fixtures"][0]
        return ReadingRequest(
            query="Task 7N Fengshui probe",
            system=system,
            chart_data=copy.deepcopy(case["input"]),
        )
    if system == "physiognomy":
        fixture = _load_yaml(root / "references/fixtures/physiognomy-v51.yaml")
        spec = copy.deepcopy(fixture["complete_cases"][0]["input"])
        subject_ref = str(spec["subject_ref"])
        return ReadingRequest(
            query="Task 7N Physiognomy probe",
            system=system,
            intent=_physiognomy_intent(subject_ref),
            chart_data={"physiognomy_spec": spec},
            image_supplied=True,
        )
    raise KeyError(f"no Task 7N representative request for {system}")


def _probe_horizon(system: str, kind: str) -> dict[str, Any]:
    if kind in {"instant", "life"}:
        return {"kind": kind}
    if system == "fortune":
        return {"kind": "day", "start": "2024-01-01", "end": "2024-01-01"}
    if system == "taiyi":
        return {"kind": "year", "start": "2024", "end": "2024"}
    if system == "selection":
        ranges = {
            "day": ("2026-07-24", "2026-07-28"),
            "month": ("2026-07", "2026-07"),
            "year": ("2026", "2026"),
        }
        start, end = ranges[kind]
        return {"kind": kind, "start": start, "end": end}
    values = {
        "day": "2026-07-24",
        "month": "2026-07",
        "year": "2026",
    }
    value = values[kind]
    return {"kind": kind, "start": value, "end": value}


@contextlib.contextmanager
def _materialized_bazi_probe_root(root: Path) -> Iterator[Path]:
    """Provide the signed Runtime identity required by the Bazi adapter.

    Source-tree completeness runs do not carry a release manifest, while an
    installed Runtime does.  Materializing the declared production closure
    keeps this probe on the same signed adapter boundary used by hosts instead
    of injecting a source commit or manifest digest into the life-K-line fact.
    """

    manifest_path = root / ".mingli-release-manifest.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        yield root
        return

    # Local import avoids making release_deploy's lazy completeness-registry
    # check a module-import cycle.
    import release_deploy

    selected = release_deploy.tracked_release_files(root)
    source_commit = release_deploy.source_commit(root)
    committed_modes = release_deploy.committed_release_modes(
        root,
        selected,
        source_commit,
    )
    manifest = release_deploy.build_manifest(
        root,
        selected,
        source_commit,
        committed_modes=committed_modes,
    )
    with tempfile.TemporaryDirectory(
        prefix="mingli-bazi-completeness-"
    ) as temporary:
        installed = Path(temporary) / "runtime"
        release_deploy.sync_destination(
            root,
            installed,
            manifest,
            apply=True,
        )
        yield installed


def _bazi_life_kline_probe_request() -> ProviderRequest:
    subject_ref = "profile-version:task7n-bazi-life-kline"
    return ProviderRequest(
        query="Task 7N Bazi life-K-line declaration probe",
        subject_refs=(subject_ref,),
        object_id="life_kline",
        dimension_ids=("overview",),
        horizon={"kind": "life", "start": None, "end": None},
        facts={
            subject_ref: {
                "birth_datetime_or_four_pillars": "2000-10-18T06:45:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海",
                "gender": "male",
                "time_basis_policy": "civil",
            }
        },
    )


@contextlib.contextmanager
def _live_provider_probe(
    system: str,
    *,
    root: Path,
) -> Iterator[
    tuple[
        Any,
        CalculationResult,
        CalculationResult,
        dict[str, tuple[CalculationResult, CalculationResult]],
    ]
]:
    """Run two calculations, seeding adapter-only extension scopes when needed."""

    provider_class = PROVIDER_CLASSES[system]
    if system != "bazi":
        provider = provider_class(root)
        request = _representative_request(system, root=root)
        yield (
            provider,
            provider.calculate(request),
            provider.calculate(request),
            {},
        )
        return

    with _materialized_bazi_probe_root(root) as probe_root:
        provider = provider_class(probe_root)
        descriptor = CatalogLoader(
            probe_root / "resources/runtime"
        ).load().descriptor(system)
        provider.bind_descriptor(descriptor)
        request = _bazi_life_kline_probe_request()
        first_prepared = provider.prepare(request, ProviderContext())
        second_prepared = provider.prepare(request, ProviderContext())
        if not isinstance(first_prepared, ProviderPreparation) or not isinstance(
            second_prepared,
            ProviderPreparation,
        ):
            raise RuntimeError(
                "bazi life-K-line adapter probe did not return ProviderPreparation"
            )
        first = first_prepared.calculation
        second = second_prepared.calculation
        yield provider, first, second, {"life": (first, second)}


def audit_live_provider_contract(
    system: str,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Run a real provider twice and resolve every declared output binding."""

    findings: list[str] = []
    resolved_outputs: list[str] = []
    resolved_extensions: list[str] = []
    extension_digests: dict[str, str] = {}
    deterministic = False
    capability = PROVIDER_CAPABILITIES[system]
    try:
        with _live_provider_probe(system, root=root) as (
            provider,
            first,
            second,
            adapter_extensions,
        ):
            provider_class = PROVIDER_CLASSES[system]
            if first.system != system or second.system != system:
                findings.append(f"{system}: provider returned the wrong system")
            if first.provider_id != provider_class.provider_id:
                findings.append(f"{system}: provider id drift")
            deterministic = first.base().to_dict() == second.base().to_dict()
            if not deterministic:
                findings.append(f"{system}: repeated base calculation drift")

            base_payload = first.base().to_dict()
            for binding in capability.output_bindings:
                try:
                    for pointer in binding.json_pointers:
                        resolve_json_pointer(base_payload, pointer)
                except (IndexError, KeyError, TypeError, ValueError) as exc:
                    findings.append(
                        f"{system}: output binding {binding.name} failed at "
                        f"{pointer}: {type(exc).__name__}"
                    )
                else:
                    resolved_outputs.append(binding.name)

            extensions: dict[str, Any] = {}
            second_extensions: dict[str, Any] = {}
            for kind in capability.horizons:
                horizon = _probe_horizon(system, kind)
                if kind in adapter_extensions:
                    extensions[kind], second_extensions[kind] = (
                        adapter_extensions[kind]
                    )
                else:
                    extensions[kind] = provider.extend(
                        first.base(),
                        tuple(capability.dimensions),
                        horizon,
                    )
                    second_extensions[kind] = provider.extend(
                        second.base(),
                        tuple(capability.dimensions),
                        horizon,
                    )
                first_extension = extensions[kind].fact_extension
                second_extension = second_extensions[kind].fact_extension
                if first_extension is None or second_extension is None:
                    findings.append(f"{system}: {kind} extension missing")
                    continue
                if first_extension.status != "complete":
                    findings.append(
                        f"{system}: declared {kind} extension returned "
                        f"{first_extension.status}"
                    )
                if first_extension.to_dict() != second_extension.to_dict():
                    deterministic = False
                    findings.append(f"{system}: repeated {kind} extension drift")
                extension_digests[kind] = first_extension.extension_digest

            for binding in capability.extension_output_bindings:
                applicable_horizons = binding.horizons or capability.horizons
                try:
                    for kind in applicable_horizons:
                        payload = extensions[kind].to_dict()
                        for pointer in binding.json_pointers:
                            resolve_json_pointer(payload, pointer)
                except (IndexError, KeyError, TypeError, ValueError) as exc:
                    findings.append(
                        f"{system}: extension binding {binding.name} failed at "
                        f"{kind}:{pointer}: {type(exc).__name__}"
                    )
                else:
                    resolved_extensions.append(binding.name)
    except Exception as exc:  # fail closed into a machine-auditable finding
        deterministic = False
        findings.append(f"{system}: live provider probe failed: {type(exc).__name__}: {exc}")

    return {
        "schema_version": "mingli-live-provider-contract-audit-v1",
        "system": system,
        "runs": 2,
        "deterministic": deterministic,
        "resolved_output_bindings": sorted(set(resolved_outputs)),
        "resolved_extension_bindings": sorted(set(resolved_extensions)),
        "extension_digests": extension_digests,
        "findings": list(dict.fromkeys(findings)),
    }


def _predicate_witness_fact_ids(predicate: Any, facts: Sequence[Any]) -> set[str]:
    """Independently identify every fact that can witness one predicate."""

    suffix = str(predicate.path_suffix)
    operator = str(predicate.operator)
    nested = suffix + "/"
    candidates = [
        fact
        for fact in facts
        if fact.path.endswith(suffix)
        or (
            operator in {"present", "nonempty", "descendant_eq", "same_record_fields"}
            and nested in fact.path
        )
    ]
    if operator == "present":
        return {fact.fact_id for fact in candidates}
    if operator == "nonempty":
        return {
            fact.fact_id
            for fact in candidates
            if nested in fact.path
            or (
                fact.path.endswith(suffix)
                and fact.value is not None
                and (
                    not isinstance(
                        fact.value,
                        (str, bytes, bytearray, dict, list, tuple, set),
                    )
                    or bool(fact.value)
                )
            )
        }
    if operator == "same_record_fields":
        required = predicate.value if isinstance(predicate.value, dict) else {}
        grouped: dict[str, list[Any]] = {}
        for fact in candidates:
            before, separator, after = fact.path.partition(nested)
            if not separator or "/" not in after:
                continue
            child = after.split("/", 1)[0]
            grouped.setdefault(f"{before}{nested}{child}", []).append(fact)
        record_roots = {
            root
            for root, entries in grouped.items()
            if all(
                any(
                    fact.path == f"{root}/{field}" and fact.value == expected
                    for fact in entries
                )
                for field, expected in required.items()
            )
        }
        return {
            fact.fact_id
            for fact in candidates
            if any(
                fact.path == root or fact.path.startswith(root + "/")
                for root in record_roots
            )
        }
    if operator == "descendant_eq":
        matching_roots: set[str] = set()
        for fact in candidates:
            if fact.value != predicate.value:
                continue
            before, _, after = fact.path.partition(nested)
            matching_roots.add(f"{before}{nested}{after.split('/', 1)[0]}")
        return {
            fact.fact_id
            for fact in candidates
            if any(
                fact.path == root or fact.path.startswith(root + "/")
                for root in matching_roots
            )
        }
    if operator == "eq":
        return {
            fact.fact_id
            for fact in candidates
            if fact.path.endswith(suffix) and fact.value == predicate.value
        }
    if operator == "in":
        return {
            fact.fact_id
            for fact in candidates
            if fact.path.endswith(suffix) and fact.value in predicate.values
        }
    if operator == "contains":
        return {
            fact.fact_id
            for fact in candidates
            if fact.path.endswith(suffix)
            and isinstance(fact.value, (tuple, list, set, str))
            and predicate.value in fact.value
        }
    return set()


def _audit_source_pack_replays(
    system: str,
    *,
    source_family: Mapping[str, Any],
    rules: Sequence[Any],
    fixture_replays: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive per-pack source proofs only from ready fixture-bound results.

    The caller cannot report match ids or aggregate counts into this contract.
    Every positive is recomputed from a captured ``CalculationResult`` and every
    required predicate is then deprived of its concrete witness facts.
    """

    required_always = tuple(
        str(pack) for pack in source_family.get("required_always") or ()
    )
    conditional = source_family.get("required_when_active_subprofile") or {}
    comparison_only = tuple(
        str(pack) for pack in source_family.get("comparison_only") or ()
    )
    required_roles_by_pack = source_family.get("required_roles_by_pack") or {}
    if not isinstance(required_roles_by_pack, Mapping):
        required_roles_by_pack = {}
    if not isinstance(conditional, Mapping):
        conditional = {}
    conditional_packs = tuple(
        dict.fromkeys(
            str(pack)
            for family in conditional.values()
            if isinstance(family, Mapping)
            for pack in family.get("packs") or ()
        )
    )
    all_packs = tuple(
        dict.fromkeys((*required_always, *conditional_packs, *comparison_only))
    )
    family_findings: list[str] = []
    overlap = set(required_always) & set(comparison_only)
    overlap.update(set(conditional_packs) & set(comparison_only))
    if overlap:
        family_findings.append(
            f"{system}: source packs have conflicting runtime roles: {sorted(overlap)}"
        )

    accepted_replays: list[
        tuple[str, CalculationResult, tuple[Any, ...], frozenset[str]]
    ] = []
    activated_required_packs: set[str] = set(required_always)
    for raw in fixture_replays:
        if raw.get("ready") is not True or raw.get("fixture_input_bound") is not True:
            continue
        calculation = raw.get("calculation")
        case_id = str(raw.get("case_id") or "")
        runtime_enabled_raw = raw.get("runtime_enabled_rule_ids")
        if (
            not case_id
            or not isinstance(calculation, CalculationResult)
            or not isinstance(runtime_enabled_raw, Sequence)
            or isinstance(runtime_enabled_raw, (str, bytes, bytearray))
        ):
            continue
        try:
            CalculationResult.from_dict(calculation.to_dict())
            fact_index = build_fact_index(
                calculation,
                reading_id="7" * 32,
                version=1,
            )
        except (KeyError, TypeError, ValueError):
            continue
        accepted_replays.append(
            (
                case_id,
                calculation,
                fact_index,
                frozenset(str(rule_id) for rule_id in runtime_enabled_raw),
            )
        )
        selected = raw.get("required_source_packs") or ()
        if isinstance(selected, Sequence) and not isinstance(
            selected, (str, bytes, bytearray)
        ):
            activated_required_packs.update(
                str(pack) for pack in selected if str(pack) in conditional_packs
            )

    pack_reports: dict[str, Any] = {}
    for pack in all_packs:
        pack_rules = [rule for rule in rules if rule.source_pack == pack]
        bound_rules = [
            rule
            for rule in pack_rules
            if rule.runtime_active
            and rule.classical_binding_status == "verified"
            and rule.classical_sources
            and rule.required_fact_predicates
        ]
        positive_cases: dict[str, list[str]] = {}
        negative_mutation_rule_ids: list[str] = []
        mutation_findings: list[str] = []
        covered_roles: set[str] = set()
        for rule in bound_rules:
            rule_positive_cases: list[str] = []
            mutation_closed = False
            for case_id, _calculation, facts, runtime_enabled in accepted_replays:
                if rule.rule_id not in runtime_enabled:
                    continue
                matched, _fact_ids, _predicate_audit = match_rule(rule, facts)
                if not matched:
                    continue
                rule_positive_cases.append(case_id)
                every_mutation_rejected = True
                for predicate_index, predicate in enumerate(
                    rule.required_fact_predicates
                ):
                    witness_ids = _predicate_witness_fact_ids(predicate, facts)
                    mutated_facts = tuple(
                        fact for fact in facts if fact.fact_id not in witness_ids
                    )
                    mutation_matched, _ids, _audit = match_rule(rule, mutated_facts)
                    if not witness_ids or mutation_matched:
                        every_mutation_rejected = False
                        mutation_findings.append(
                            f"{pack}/{rule.rule_id}: predicate mutation "
                            f"{predicate_index} did not fail closed"
                        )
                if every_mutation_rejected:
                    mutation_closed = True
            if rule_positive_cases:
                positive_cases[rule.rule_id] = sorted(set(rule_positive_cases))
                covered_roles.add(str(rule.evidence_role))
            if mutation_closed:
                negative_mutation_rule_ids.append(rule.rule_id)

        # A conditional family is mandatory only when a real source plan selected
        # it, or when its own verified rules actually activated on fixture facts.
        if pack in conditional_packs and positive_cases:
            activated_required_packs.add(pack)
        mandatory = pack in activated_required_packs and pack not in comparison_only
        required_roles = sorted(
            str(role) for role in required_roles_by_pack.get(pack) or ()
        )
        positive_ids = sorted(positive_cases)
        mutation_ids = sorted(set(negative_mutation_rule_ids))
        pack_findings: list[str] = []
        if mandatory and not bound_rules:
            pack_findings.append(f"{pack}: no verified predicate-bound rules")
        if mandatory and not positive_ids:
            pack_findings.append(f"{pack}: no positive fixture provider replay")
        if mandatory and set(positive_ids) - set(mutation_ids):
            pack_findings.append(f"{pack}: predicate mutation proof is incomplete")
        missing_roles = sorted(set(required_roles) - covered_roles)
        if mandatory and missing_roles:
            pack_findings.append(f"{pack}: required roles not covered: {missing_roles}")
        if mandatory:
            pack_findings.extend(mutation_findings)
        proof_ready = (
            bool(bound_rules)
            and bool(positive_ids)
            and set(positive_ids) <= set(mutation_ids)
            and set(required_roles) <= covered_roles
            and not mutation_findings
        )
        pack_reports[pack] = {
            "plan_required": pack in required_always,
            "conditional_runtime_required": pack in activated_required_packs
            and pack in conditional_packs,
            "comparison_only": pack in comparison_only,
            "mandatory": mandatory,
            "runtime_status": "active" if positive_ids else "inactive_unmatched",
            "indexed_rules": len(pack_rules),
            "verified_classical_anchors": len(bound_rules),
            "predicate_bound_rules": len(bound_rules),
            "positive_replay_rule_ids": positive_ids,
            "positive_replay_cases": positive_cases,
            "negative_mutation_rule_ids": mutation_ids,
            "required_roles": required_roles,
            "covered_roles": sorted(covered_roles),
            "findings": pack_findings,
            "ready": (not mandatory) or proof_ready,
        }

    derived_ready = bool(accepted_replays) and not family_findings and all(
        report["ready"] for report in pack_reports.values()
    )
    findings = [*family_findings]
    if not accepted_replays:
        findings.append(f"{system}: no ready fixture-bound provider replays")
    findings.extend(
        f"{system}: {finding}"
        for report in pack_reports.values()
        if report["mandatory"]
        for finding in report["findings"]
    )
    return {
        "schema_version": "mingli-provider-source-pack-replay-audit-v1",
        "system": system,
        "required_always": list(required_always),
        "required_when_active_subprofile": copy.deepcopy(dict(conditional)),
        "comparison_only": list(comparison_only),
        "required_roles_by_pack": {
            str(pack): [str(role) for role in roles]
            for pack, roles in required_roles_by_pack.items()
        },
        "accepted_fixture_replay_count": len(accepted_replays),
        "accepted_fixture_case_ids": sorted(
            {
                case_id
                for case_id, _calculation, _facts, _runtime_enabled in accepted_replays
            }
        ),
        "packs": pack_reports,
        "ready": derived_ready,
        "findings": list(dict.fromkeys(findings)),
    }


def _source_pack_replay_findings(
    system: str,
    report: Mapping[str, Any],
) -> list[str]:
    """Recompute route readiness without trusting aggregate self-report fields."""

    findings: list[str] = []
    packs = report.get("packs") or {}
    if not isinstance(packs, Mapping):
        return [f"{system}: source pack replay packs must be an object"]
    if int(report.get("accepted_fixture_replay_count") or 0) < 1:
        findings.append(f"{system}: source pack replay has no accepted fixture case")
    if report.get("findings"):
        findings.append(f"{system}: source pack replay audit has findings")
    required = set(str(pack) for pack in report.get("required_always") or ())
    comparison = set(str(pack) for pack in report.get("comparison_only") or ())
    for pack in sorted(required):
        row = packs.get(pack)
        if not isinstance(row, Mapping):
            findings.append(f"{system}: missing mandatory source pack {pack}")
            continue
        if row.get("mandatory") is not True or row.get("ready") is not True:
            findings.append(f"{system}: mandatory source pack is not ready: {pack}")
    for pack, raw in packs.items():
        if not isinstance(raw, Mapping):
            findings.append(f"{system}: invalid source pack report: {pack}")
            continue
        if str(pack) in comparison and raw.get("mandatory") is True:
            findings.append(
                f"{system}: comparison-only source pack became mandatory: {pack}"
            )
        if raw.get("mandatory") is True and (
            raw.get("ready") is not True or raw.get("findings")
        ):
            findings.append(f"{system}: mandatory source pack proof failed: {pack}")
        if raw.get("mandatory") is True:
            required_roles = {
                str(role) for role in raw.get("required_roles") or ()
            }
            covered_roles = {
                str(role) for role in raw.get("covered_roles") or ()
            }
            if not required_roles or not required_roles <= covered_roles:
                findings.append(
                    f"{system}: mandatory source pack roles are not covered: {pack}"
                )
            positive = {
                str(rule_id)
                for rule_id in raw.get("positive_replay_rule_ids") or ()
            }
            negative = {
                str(rule_id)
                for rule_id in raw.get("negative_mutation_rule_ids") or ()
            }
            if not positive or not positive <= negative:
                findings.append(
                    f"{system}: mandatory source pack replay is not mutation-closed: {pack}"
                )
    derived_ready = (
        int(report.get("accepted_fixture_replay_count") or 0) > 0
        and not findings
        and not report.get("findings")
    )
    if bool(report.get("ready")) != derived_ready:
        findings.append(f"{system}: source pack aggregate ready is not derived")
    return list(dict.fromkeys(findings))


def audit_source_applicability(
    system: str,
    *,
    root: Path = ROOT,
    fixture_replays: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prove pack-local predicates against captured fixture provider results."""

    findings: list[str] = []
    registry = reading_source_plan.load_runtime_source_registry()
    source_family = registry["routes"].get(system)
    if not isinstance(source_family, Mapping):
        findings.append(f"{system}: runtime source family is missing")
        source_family = {
            "required_always": [],
            "required_when_active_subprofile": {},
            "comparison_only": [],
            "required_roles_by_pack": {},
        }
    try:
        index_audit = build_evidence_index.audit_checked_evidence_index(root=root)
        findings.extend(
            f"{system}: {item}" for item in index_audit.get("findings") or ()
        )
        rules = load_evidence_rules(
            root / "references/index/evidence-rules.jsonl",
            root=root,
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        findings.append(
            f"{system}: evidence index/classical binding audit failed: "
            f"{type(exc).__name__}: {exc}"
        )
        rules = ()
    report = _audit_source_pack_replays(
        system,
        source_family=source_family,
        rules=rules,
        fixture_replays=fixture_replays or (),
    )
    if fixture_replays is None:
        findings.append(
            f"{system}: source audit requires captured fixture provider replays"
        )
    report["registry_path"] = registry["path"]
    report["registry_sha256"] = registry["sha256"]
    report["findings"] = list(dict.fromkeys([*findings, *report["findings"]]))
    report["ready"] = not report["findings"] and not _source_pack_replay_findings(
        system, report
    )
    return report


def _liuyao_lifecycle_request(
    *,
    query: str,
    cast: Any = None,
    event_datetime: str = "2024-02-10T12:00:00",
) -> ProviderRequest:
    facts: dict[str, Any] = {
        "event_datetime": event_datetime,
        "timezone": "Asia/Shanghai",
        "location": "上海",
    }
    if cast is not None:
        facts["cast"] = cast
    return ProviderRequest(
        query=query,
        subject_refs=("task7n:liuyao-lifecycle",),
        object_id="concrete_event",
        dimension_ids=("outcome", "timing"),
        horizon={"kind": "instant", "start": None, "end": None},
        facts={"task7n:liuyao-lifecycle": facts},
    )


def _accept_lifecycle_turn(engine: Any, state_token: str | None) -> AcceptedReading:
    accepted = engine.complete_turn(
        str(state_token),
        "已列明确定性卦象事实。\n仅依据本次卦象与绑定来源回答。",
    )
    if not isinstance(accepted, AcceptedReading):
        raise RuntimeError(f"Liuyao lifecycle could not accept reading: {accepted!r}")
    return accepted


def _public_payload_contains_private_liuyao_seed(
    value: Any,
    *,
    raw_seeds: Sequence[str],
) -> bool:
    forbidden_keys = {
        "seed",
        "cast_seed",
        liuyao.TRANSACTION_CAST_SEED_KEY,
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in forbidden_keys:
                return True
            if _public_payload_contains_private_liuyao_seed(
                item,
                raw_seeds=raw_seeds,
            ):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return any(
            _public_payload_contains_private_liuyao_seed(
                item,
                raw_seeds=raw_seeds,
            )
            for item in value
        )
    if isinstance(value, str):
        if value in raw_seeds or value.endswith("/casting/seed"):
            return True
        return any(seed and seed in value for seed in raw_seeds)
    return False


def audit_liuyao_transaction_lifecycle(*, root: Path = ROOT) -> dict[str, Any]:
    """Replay the private digital-cast state machine through restart and recast."""

    findings: list[str] = []
    checks = {
        "fresh_casts_are_distinct": False,
        "restart_replay_matches": False,
        "continue_preserves_cast": False,
        "continue_preserves_chart_facts": False,
        "continue_skips_recalculation": False,
        "correct_preserves_cast": False,
        "cast_correction_requires_recast": False,
        "public_seed_redacted": False,
        "seed_values_match_csprng_calls": False,
        "all_public_contracts_seed_redacted": False,
        "recast_restart_replay_matches": False,
        "public_casting_schema_exact": False,
        "supplied_to_digital_requires_recast": False,
        "supplied_toss_change_requires_recast": False,
        "digital_toss_injection_requires_recast": False,
        "same_cast_correction_preserves_cast": False,
    }
    random_seed_calls = 0
    try:
        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "reading_engine.providers.secrets.token_hex",
            side_effect=("1" * 64, "2" * 64),
        ) as token_hex:
            engine = build_production_engine(skill_dir=root, store_root=temporary)
            first_turn = engine.prepare_turn(
                engine.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N fresh digital Liuyao cast",
                    cast="digital_coin",
                ),
            )
            first = first_turn.result
            if not isinstance(first, PreparedReading):
                raise RuntimeError(f"fresh cast failed: {first!r}")
            first_internal = engine.store.load_prepared(first.reading_id)
            first_cast = first_internal.calculation.facts["chart_facts"]["output"][
                "casting"
            ]
            checks["public_seed_redacted"] = bool(
                first.calculation is None
                and not _public_payload_contains_private_liuyao_seed(
                    first.to_dict(),
                    raw_seeds=(first_cast["seed"],),
                )
                and any(
                    item.path.endswith("/casting/seed_commitment")
                    for item in first.fact_index
                )
            )
            first_accepted = _accept_lifecycle_turn(engine, first_turn.state_token)
            public_contracts: list[Mapping[str, Any]] = [
                first.to_dict(),
                first_accepted.to_dict(),
            ]

            restarted = build_production_engine(
                skill_dir=root,
                store_root=temporary,
            )
            restarted_cast = restarted.store.load(first_accepted.reading_id).calculation.facts[
                "chart_facts"
            ]["output"]["casting"]
            replay = liuyao.cast_from_seed(restarted_cast["seed"])
            checks["restart_replay_matches"] = all(
                replay[field] == restarted_cast[field]
                for field in ("coin_values", "coin_faces", "tosses")
            )

            seed_calls_before_continue = token_hex.call_count
            continued_turn = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N continue same cast",
                    cast="digital_coin",
                ),
                state_token=first_turn.state_token,
            )
            continued = continued_turn.result
            checks["continue_skips_recalculation"] = (
                token_hex.call_count == seed_calls_before_continue
            )
            if not isinstance(continued, PreparedReading):
                raise RuntimeError(f"continue failed: {continued!r}")
            continued_cast = restarted.store.load_prepared(
                continued.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            checks["continue_preserves_cast"] = continued_cast == first_cast
            continued_chart = restarted.store.load_prepared(
                continued.reading_id
            ).calculation.facts["chart_facts"]
            checks["continue_preserves_chart_facts"] = (
                continued_chart
                == first_internal.calculation.facts["chart_facts"]
            )
            continued_accepted = _accept_lifecycle_turn(
                restarted, continued_turn.state_token
            )
            public_contracts.extend(
                (continued.to_dict(), continued_accepted.to_dict())
            )

            corrected_turn = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N correct non-cast fact",
                    cast="digital_coin",
                ),
                state_token=continued_turn.state_token,
                transition="correct",
            )
            corrected = corrected_turn.result
            if not isinstance(corrected, PreparedReading):
                raise RuntimeError(f"correct failed: {corrected!r}")
            corrected_cast = restarted.store.load_prepared(
                corrected.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            checks["correct_preserves_cast"] = corrected_cast == first_cast
            corrected_accepted = _accept_lifecycle_turn(
                restarted, corrected_turn.state_token
            )
            public_contracts.extend(
                (corrected.to_dict(), corrected_accepted.to_dict())
            )

            rejected = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N forbidden cast correction",
                    cast={
                        "casting_method": "supplied_complete_cast",
                        "tosses": [7, 7, 7, 7, 7, 7],
                    },
                ),
                state_token=corrected_turn.state_token,
                transition="correct",
            ).result
            checks["cast_correction_requires_recast"] = bool(
                isinstance(rejected, InternalFailure)
                and rejected.code == "action_requires_recast"
            )
            digital_toss_injection = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N forbidden digital toss injection",
                    cast={
                        "casting_method": "digital_coin",
                        "tosses": [7, 7, 7, 7, 7, 7],
                    },
                ),
                state_token=corrected_turn.state_token,
                transition="correct",
            ).result
            checks["digital_toss_injection_requires_recast"] = bool(
                isinstance(digital_toss_injection, InternalFailure)
                and digital_toss_injection.code == "action_requires_recast"
            )

            recast_turn = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N explicit new-event recast",
                    cast="digital_coin",
                    event_datetime="2024-02-11T12:00:00",
                ),
                state_token=corrected_turn.state_token,
                transition="restart",
            )
            recast = recast_turn.result
            if not isinstance(recast, PreparedReading):
                raise RuntimeError(f"recast failed: {recast!r}")
            recast_cast = restarted.store.load_prepared(
                recast.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            checks["fresh_casts_are_distinct"] = bool(
                recast_cast["seed"] != first_cast["seed"]
                and recast_cast["cast_digest"] != first_cast["cast_digest"]
            )
            recast_accepted = _accept_lifecycle_turn(
                restarted, recast_turn.state_token
            )
            public_contracts.extend((recast.to_dict(), recast_accepted.to_dict()))
            recast_restarted = build_production_engine(
                skill_dir=root,
                store_root=temporary,
            )
            persisted_recast = recast_restarted.store.load(
                recast_accepted.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            recast_replay = liuyao.cast_from_seed(persisted_recast["seed"])
            checks["recast_restart_replay_matches"] = bool(
                persisted_recast == recast_cast
                and all(
                    recast_replay[field] == persisted_recast[field]
                    for field in ("coin_values", "coin_faces", "tosses")
                )
            )
            checks["seed_values_match_csprng_calls"] = bool(
                first_cast["seed"] == "1" * 64
                and recast_cast["seed"] == "2" * 64
                and first_cast.get("seed_source")
                == liuyao.TRANSACTION_CAST_SEED_SOURCE
                and recast_cast.get("seed_source")
                == liuyao.TRANSACTION_CAST_SEED_SOURCE
                and any(
                    item.value
                    == liuyao.transaction_cast_seed_commitment(first_cast["seed"])
                    for item in first.fact_index
                    if item.path.endswith("/casting/seed_commitment")
                )
                and any(
                    item.value
                    == liuyao.transaction_cast_seed_commitment(recast_cast["seed"])
                    for item in recast.fact_index
                    if item.path.endswith("/casting/seed_commitment")
                )
            )
            checks["all_public_contracts_seed_redacted"] = not any(
                _public_payload_contains_private_liuyao_seed(
                    payload,
                    raw_seeds=(first_cast["seed"], recast_cast["seed"]),
                )
                for payload in public_contracts
            )

            supplied_turn = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N supplied cast correction guard",
                    cast=[9, 7, 7, 7, 7, 6],
                    event_datetime="2024-02-12T12:00:00",
                ),
            )
            supplied = supplied_turn.result
            if not isinstance(supplied, PreparedReading):
                raise RuntimeError(f"supplied cast failed: {supplied!r}")
            supplied_cast = restarted.store.load_prepared(
                supplied.reading_id
            ).calculation.facts["chart_facts"]["output"]["casting"]
            supplied_accepted = _accept_lifecycle_turn(
                restarted, supplied_turn.state_token
            )
            supplied_to_digital = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N forbidden supplied-to-digital correction",
                    cast="digital_coin",
                    event_datetime="2024-02-12T12:00:00",
                ),
                state_token=supplied_turn.state_token,
                transition="correct",
            ).result
            checks["supplied_to_digital_requires_recast"] = bool(
                isinstance(supplied_to_digital, InternalFailure)
                and supplied_to_digital.code == "action_requires_recast"
            )
            supplied_toss_change = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N forbidden supplied toss correction",
                    cast=[7, 7, 7, 7, 7, 7],
                    event_datetime="2024-02-12T12:00:00",
                ),
                state_token=supplied_turn.state_token,
                transition="correct",
            ).result
            checks["supplied_toss_change_requires_recast"] = bool(
                isinstance(supplied_toss_change, InternalFailure)
                and supplied_toss_change.code == "action_requires_recast"
            )
            same_supplied = restarted.prepare_turn(
                restarted.providers["liuyao"].descriptor,
                _liuyao_lifecycle_request(
                    query="Task 7N same supplied cast annotation",
                    cast=[9, 7, 7, 7, 7, 6],
                    event_datetime="2024-02-12T12:00:00",
                ),
                state_token=supplied_turn.state_token,
                transition="correct",
            ).result
            if isinstance(same_supplied, PreparedReading):
                same_supplied_cast = restarted.store.load_prepared(
                    same_supplied.reading_id
                ).calculation.facts["chart_facts"]["output"]["casting"]
                checks["same_cast_correction_preserves_cast"] = (
                    same_supplied_cast == supplied_cast
                )

            expected_casting_keys = {
                "method",
                "algorithm",
                "coin_values",
                "coin_faces",
                "tosses",
                "seed_source",
                "provenance",
                "source_dependency_id",
                "cast_digest",
                "seed_commitment",
            }
            public_digital_contracts = (first, continued, corrected, recast)
            checks["public_casting_schema_exact"] = all(
                {
                    item.path.split("/chart_facts/output/casting/", 1)[1].split("/", 1)[0]
                    for item in prepared.fact_index
                    if "/chart_facts/output/casting/" in item.path
                }
                == expected_casting_keys
                for prepared in public_digital_contracts
            )
            random_seed_calls = token_hex.call_count
            if token_hex.call_args_list != [mock.call(32), mock.call(32)]:
                findings.append("Liuyao transaction did not request two 256-bit seeds")
    except Exception as exc:
        findings.append(f"{type(exc).__name__}: {exc}")
    for name, passed in checks.items():
        if not passed:
            findings.append(f"Liuyao transaction lifecycle failed: {name}")
    if random_seed_calls != 2:
        findings.append(
            f"Liuyao transaction lifecycle made {random_seed_calls} random seed calls"
        )
    return {
        "schema_version": "mingli-liuyao-transaction-lifecycle-audit-v1",
        **checks,
        "random_seed_calls": random_seed_calls,
        "ready": not findings,
        "findings": findings,
    }


def _provider_runtime(system: str) -> dict[str, Any]:
    provider_class = PROVIDER_CLASSES[system]
    expected_class, expected_id, expected_version = EXPECTED_PROVIDER_IDENTITIES[system]
    observed_class = f"{provider_class.__module__}.{provider_class.__qualname__}"
    observed_id = str(provider_class.provider_id)
    observed_version = str(provider_class.provider_version)
    return {
        "class": observed_class,
        "provider_id": observed_id,
        "provider_version": observed_version,
        "expected_class": expected_class,
        "expected_provider_id": expected_id,
        "expected_provider_version": expected_version,
        "identity_matches": (
            observed_class == expected_class
            and observed_id == expected_id
            and observed_version == expected_version
        ),
        "generic": (
            provider_class.__name__ == "StructuredChartProvider"
            or "structured" in observed_id.casefold()
        ),
    }


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


_AUDIT_LABEL_FIELDS = frozenset(
    {"audit_nonce", "case_id", "fixture_id", "source_anchor"}
)
_REQUEST_ENVELOPE_FIELDS = frozenset(
    {
        "question",
        "query",
        "action",
        "reading_id",
        "intake_id",
        "system_hint",
        "system",
        "intent",
        "goal",
    }
)


def _semantic_audit_payload(value: Any, *, top_level: bool = False) -> Any:
    """Remove audit-only labels before deriving semantic replay identity."""

    if isinstance(value, Mapping):
        return {
            str(key): _semantic_audit_payload(item)
            for key, item in value.items()
            if str(key) not in _AUDIT_LABEL_FIELDS
            and not (top_level and str(key) in _REQUEST_ENVELOPE_FIELDS)
        }
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_semantic_audit_payload(item) for item in value]
    return copy.deepcopy(value)


def _declared_input_digests_have_preimages(payload: Mapping[str, Any]) -> bool:
    declared: list[str] = []
    semantic_candidates: list[Any] = []

    def collect_declared(value: Any) -> None:
        if isinstance(value, Mapping):
            digest = value.get("input_digest")
            if isinstance(digest, str) and digest:
                declared.append(digest)
            for item in value.values():
                collect_declared(item)
        elif isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        ):
            for item in value:
                collect_declared(item)

    def collect_semantics(value: Any) -> None:
        if isinstance(value, Mapping):
            without_digests = {
                str(key): copy.deepcopy(item)
                for key, item in value.items()
                if str(key) != "input_digest"
            }
            if without_digests:
                semantic_candidates.append(without_digests)
            for item in without_digests.values():
                collect_semantics(item)
        elif isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        ):
            semantic_candidates.append(copy.deepcopy(value))
            for item in value:
                collect_semantics(item)

    collect_declared(payload)
    if not declared:
        return True
    request_semantics = payload.get("request_semantics")
    if not isinstance(request_semantics, Mapping):
        return False
    collect_semantics(request_semantics)
    candidate_digests = {
        canonical_digest(item) for item in semantic_candidates
    }
    return all(digest in candidate_digests for digest in declared)


def _dedicated_audit_projection(report: Mapping[str, Any]) -> dict[str, Any]:
    projected = {
        "schema_version": str(report.get("schema_version") or ""),
        "system": str(report.get("system") or ""),
        "status": str(report.get("status") or ""),
        "provider_ready": bool(report.get("provider_ready")),
        "provider": _plain(report.get("provider") or {}),
        "counts": _plain(report.get("counts") or {}),
        "random_cast_contract": _plain(
            report.get("random_cast_contract") or {}
        ),
        "findings": [str(item) for item in report.get("findings") or ()],
    }
    if "calendar_month_general_closure_ready" in report:
        projected["calendar_month_general_closure_ready"] = (
            report.get("calendar_month_general_closure_ready") is True
        )
    return projected


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_case_ids(value: Any) -> set[str]:
    identifiers: set[str] = set()
    if isinstance(value, Mapping):
        for key in ("id", "case_id", "fixture_id", "example_id"):
            candidate = value.get(key)
            if isinstance(candidate, (str, int)) and str(candidate).strip():
                identifiers.add(str(candidate))
        for item in value.values():
            identifiers.update(_fixture_case_ids(item))
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        for item in value:
            identifiers.update(_fixture_case_ids(item))
    return identifiers


def _fixture_case_categories(value: Any) -> dict[str, set[str]]:
    categories: dict[str, set[str]] = {}
    if isinstance(value, Mapping):
        identifier = next(
            (
                str(value.get(key))
                for key in ("id", "case_id", "fixture_id", "example_id")
                if value.get(key)
            ),
            None,
        )
        category = value.get("category")
        if identifier is not None and isinstance(category, str) and category.strip():
            categories.setdefault(identifier, set()).add(category.strip())
        for item in value.values():
            for case_id, names in _fixture_case_categories(item).items():
                categories.setdefault(case_id, set()).update(names)
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        for item in value:
            for case_id, names in _fixture_case_categories(item).items():
                categories.setdefault(case_id, set()).update(names)
    return categories


def _module_fixture_case_ids(module: Any, *, root: Path) -> set[str]:
    identifiers: set[str] = set()
    for name, raw_path in vars(module).items():
        if "FIXTURE" not in name or "SHA" in name:
            continue
        if not isinstance(raw_path, (str, Path)):
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        if path.suffix.casefold() not in {".yaml", ".yml"} or not path.is_file():
            continue
        try:
            identifiers.update(_fixture_case_ids(_load_yaml(path)))
        except (OSError, ValueError, yaml.YAMLError):
            continue
    return identifiers


def _module_fixture_case_categories(
    module: Any,
    *,
    root: Path,
) -> dict[str, set[str]]:
    categories: dict[str, set[str]] = {}
    for name, raw_path in vars(module).items():
        if "FIXTURE" not in name or "SHA" in name:
            continue
        if not isinstance(raw_path, (str, Path)):
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        if path.suffix.casefold() not in {".yaml", ".yml"} or not path.is_file():
            continue
        try:
            payload = _fixture_case_categories(_load_yaml(path))
        except (OSError, ValueError, yaml.YAMLError):
            continue
        for case_id, names in payload.items():
            categories.setdefault(case_id, set()).update(names)
    return categories


def _module_fixture_case_bindings(
    module: Any,
    *,
    root: Path,
    system: str | None = None,
) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for name, raw_path in vars(module).items():
        if "FIXTURE" not in name or "SHA" in name:
            continue
        if not isinstance(raw_path, (str, Path)):
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        if path.suffix.casefold() not in {".yaml", ".yml"} or not path.is_file():
            continue
        try:
            payload = _fixture_case_bindings(
                _load_yaml(path),
                system=system,
            )
        except (OSError, ValueError, yaml.YAMLError):
            continue
        for case_id, binding in payload.items():
            existing = bindings.get(case_id)
            if existing is not None and existing != binding:
                raise ValueError(
                    f"ambiguous module fixture semantic binding: {case_id}"
                )
            bindings[case_id] = binding
    return bindings


def _fixture_case_id_aliases(identifiers: set[str]) -> set[str]:
    """Include the explicit audit labels derived from fixture-owned identifiers."""

    aliases = set(identifiers)
    for identifier in identifiers:
        aliases.update(
            {
                f"source-example-{identifier}",
                f"taiyuan-{identifier}",
                f"calendar-{identifier}",
            }
        )
    return aliases


_FIXTURE_NON_INPUT_KEYS = frozenset(
    {
        "id",
        "case_id",
        "fixture_id",
        "example_id",
        "category",
        "source",
        "source_id",
        "source_anchor",
        "source_heading",
        "anchor",
        "oracle",
        "source_contract",
        "comparator_case_id",
        "bureau",
        "primary",
        "changed",
        "mutual",
        "moving_lines",
    }
)


def _fixture_input_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    explicit = record.get("input")
    if isinstance(explicit, Mapping):
        return copy.deepcopy(dict(explicit))
    return {
        str(key): copy.deepcopy(value)
        for key, value in record.items()
        if str(key) not in _FIXTURE_NON_INPUT_KEYS
        and not str(key).startswith("expected")
    }


def _system_fixture_input_projection(
    system: str | None,
    record: Mapping[str, Any],
    projection: Mapping[str, Any],
    *,
    fixture: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = copy.deepcopy(dict(projection))
    if system is None:
        return normalized
    category = str(record.get("category") or "")
    if system == "bazi" and category == "luck_cycle_boundary":
        instant = str(normalized.get("instant") or "")
        civil_date = instant.split("T", 1)[0]
        return {
            "gender": normalized.get("gender"),
            "kind": "day",
            "start": civil_date,
            "end": civil_date,
        }
    if system == "bazi" and category == "long_horizon":
        return {
            "kind": str(normalized.get("kind") or ""),
            "start": str(normalized.get("start")),
            "end": str(normalized.get("end")),
        }
    if system == "fortune":
        profile_id = str(record.get("profile_id") or "")
        profiles = fixture.get("natal_profiles") or {}
        profile = profiles.get(profile_id) if isinstance(profiles, Mapping) else None
        reference = str(record.get("reference_datetime") or "")
        target_date = reference.split("T", 1)[0]
        return {
            **(copy.deepcopy(dict(profile)) if isinstance(profile, Mapping) else {}),
            "reference_datetime": reference,
            "kind": str((record.get("horizon") or {}).get("kind") or ""),
            "start": target_date,
            "end": target_date,
        }
    if system == "liuren" and set(normalized) == {
        "day",
        "hour",
        "month_general",
    }:
        return {
            "event_datetime": (
                audit_liuren_provider._provider_datetime_for_classical_input(
                    normalized
                )
            ),
            "timezone": "Asia/Shanghai",
            "location": "上海",
        }
    if system == "liuyao" and isinstance(
        record.get("calendar_witness"), Mapping
    ):
        return {
            "calendar_witness": copy.deepcopy(record["calendar_witness"]),
            "casting_method": "supplied_complete_cast",
            "tosses": copy.deepcopy(record.get("tosses") or ()),
        }
    if system == "liuyao" and record.get("tosses") is not None:
        return {"tosses": copy.deepcopy(record.get("tosses") or ())}
    if system == "selection" and isinstance(record.get("input"), Mapping):
        supplied = record["input"]
        time_value = str(supplied.get("time") or "")
        return {
            "date": supplied.get("date"),
            "time": time_value[:5],
            "timezone": supplied.get("timezone"),
            "location": supplied.get("location"),
        }
    if system == "taiyi" and record.get("lunar_year") is not None:
        return {"lunar_year": record.get("lunar_year")}
    if system == "fengshui" and category == "low_quality":
        base_case = records.get("FS-O01") or {}
        base = copy.deepcopy(
            ((base_case.get("input") or {}).get("fengshui_spec") or {})
        )
        mutation = record.get("mutation") or {}
        observations = base.get("observations") or []
        if observations:
            observations[0].setdefault("quality", {})[
                str(mutation.get("quality_field") or "")
            ] = mutation.get("value")
        return {"fengshui_spec": base}
    if system == "fengshui" and category == "invalid_scope_school":
        mutation = record.get("mutation") or {}
        base_case = records.get(str(mutation.get("base_case") or "")) or {}
        base = copy.deepcopy(
            ((base_case.get("input") or {}).get("fengshui_spec") or {})
        )
        base["property_scope"] = mutation.get("property_scope")
        return {"fengshui_spec": base}
    if system == "luming-nayin":
        cycle = list(fixture.get("nayin_cycle") or ())
        if record.get("month_pillar") is not None and cycle:
            taiyuan_cases = list(fixture.get("taiyuan_cases") or ())
            index = next(
                (
                    item_index
                    for item_index, item in enumerate(taiyuan_cases)
                    if item is record or item == record
                ),
                -1,
            )
            if index >= 0:
                return {
                    "pillars": [
                        str(cycle[(index * 11 + 3) % 60][0]),
                        str(record.get("month_pillar") or ""),
                        str(cycle[(index * 11 + 19) % 60][0]),
                        str(cycle[(index * 11 + 37) % 60][0]),
                    ]
                }
        if record.get("pillars") is not None and cycle:
            examples = list(fixture.get("source_examples") or ())
            index = next(
                (
                    item_index
                    for item_index, item in enumerate(examples)
                    if item is record or item == record
                ),
                -1,
            )
            if index >= 0:
                return {
                    "pillars": audit_luming_provider._complete_source_example(
                        record,
                        cycle,
                        index,
                    )
                }
    if "input" not in record:
        accepted = {
            "datetime",
            "event_datetime",
            "timezone",
            "location",
            "zi_hour_policy",
            "date",
            "time",
            "gender",
            "target_date",
            "kind",
            "start",
            "end",
            "pillars",
            "casting_method",
        }
        return {
            str(key): copy.deepcopy(value)
            for key, value in record.items()
            if str(key) in accepted
        }
    return normalized


def _fixture_binding_surfaces(
    system: str | None,
    identifier: str,
    record: Mapping[str, Any],
    normalized: Mapping[str, Any],
    *,
    fixture: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    calculation: dict[str, Any] = {}
    extension: dict[str, Any] = {}
    category = str(record.get("category") or "")
    if system is None:
        if set(normalized) <= {"kind", "start", "end", "target_date"}:
            extension = copy.deepcopy(dict(normalized))
        else:
            calculation = copy.deepcopy(dict(normalized))
    elif system == "bazi":
        supplied = record.get("input") or {}
        base_birth = {
            "datetime": "2000-10-18T06:45:00",
            "timezone": "Asia/Shanghai",
            "location": "上海",
            "gender": "male",
        }
        if category.endswith("dispute"):
            calculation = {"chart_data": {"pillars": supplied.get("pillars")}}
        elif category == "seasonal_extreme":
            calculation = {
                "birth_data": {
                    **base_birth,
                    "datetime": supplied.get("datetime"),
                }
            }
        elif category == "luck_cycle_boundary":
            instant = str(supplied.get("instant") or "")
            calculation = {
                "reference_datetime": instant,
                "birth_data": {
                    **base_birth,
                    "gender": supplied.get("gender"),
                },
            }
            civil_date = instant.split("T", 1)[0]
            extension = {
                "kind": "day",
                "start": civil_date,
                "end": civil_date,
            }
        elif category == "long_horizon":
            calculation = {"birth_data": base_birth}
            extension = {
                "kind": supplied.get("kind"),
                "start": str(supplied.get("start")),
                "end": str(supplied.get("end")),
            }
    elif system == "fortune":
        calculation = {
            "reference_datetime": normalized.get("reference_datetime"),
            "birth_data": {
                key: normalized.get(key)
                for key in (
                    "birth_datetime",
                    "timezone",
                    "location",
                    "gender",
                )
            },
        }
        extension = {
            key: normalized.get(key) for key in ("kind", "start", "end")
        }
    elif system == "liuren":
        calculation = {
            key: value
            for key, value in {
                "event_datetime": normalized.get("event_datetime")
                or normalized.get("datetime"),
                "timezone": normalized.get("timezone"),
                "location": normalized.get("location"),
            }.items()
            if value is not None
        }
        if record.get("zi_hour_policy") is not None:
            calculation["metadata"] = {
                "zi_hour_policy": record.get("zi_hour_policy")
            }
    elif system == "liuyao":
        if isinstance(record.get("calendar_witness"), Mapping):
            witness = record["calendar_witness"]
            tosses = list(record.get("tosses") or ())
        elif category or record.get("tosses") is not None:
            witness = {
                "event_datetime": record.get("datetime")
                or "2024-02-10T12:00:00",
                "timezone": record.get("timezone") or "Asia/Shanghai",
                "location": record.get("location") or "上海",
                "zi_hour_policy": record.get("zi_hour_policy") or "midnight",
            }
            tosses = list(
                record.get("tosses")
                or ([7, 7, 7, 7, 7, 7])
            )
        else:
            witness = {}
            tosses = []
        calculation = {
            "event_datetime": witness.get("event_datetime"),
            "timezone": witness.get("timezone"),
            "location": witness.get("location"),
            "chart_data": {
                "casting_method": "supplied_complete_cast",
                "tosses": tosses,
            },
            "metadata": {
                "zi_hour_policy": witness.get("zi_hour_policy")
            },
        }
    elif system == "qimen":
        calculation = {
            "event_datetime": normalized.get("datetime")
            or normalized.get("event_datetime"),
            "timezone": normalized.get("timezone") or "Asia/Shanghai",
            "location": normalized.get("location") or "上海",
        }
    elif system == "selection":
        supplied = record.get("input") or {}
        civil_date = str(supplied.get("date") or record.get("date") or "")
        calculation = {
            "timezone": supplied.get("timezone") or "Asia/Shanghai",
            "location": supplied.get("location") or "上海",
            "chart_data": {
                "selection_spec": {
                    "event_profile": supplied.get("event_profile")
                    or "generic_selection",
                    "requested_actions": list(
                        supplied.get("requested_actions") or []
                    ),
                    **(
                        {"requested_scopes": list(supplied["requested_scopes"])}
                        if supplied.get("requested_scopes")
                        else {}
                    ),
                    **(
                        {"directional_context": dict(supplied["directional_context"])}
                        if supplied.get("directional_context")
                        else {}
                    ),
                    "date_range": {"start": civil_date, "end": civil_date},
                    "hard_constraints": {
                        "time_windows": [{"start": "12:00", "end": "12:01"}]
                    },
                    "participant_facts": [],
                    "include_folk_comparison": False,
                }
            },
        }
    elif system == "ziwei":
        supplied = record.get("input") or {}
        contract = fixture.get("provider_contract") or {}
        timezone_name = supplied.get("timezone") or contract.get("timezone")
        location = supplied.get("location") or contract.get("location")
        calculation = {
            "timezone": timezone_name,
            "location": location,
            "birth_data": {
                "datetime": supplied.get("datetime"),
                "timezone": timezone_name,
                "location": location,
                "gender": supplied.get("gender"),
                "zi_hour_policy": supplied.get("zi_hour_policy") or "midnight",
            },
        }
        target_date = str(supplied.get("target_date") or "")
        if target_date:
            extension = {
                "kind": "month",
                "start": target_date[:7],
                "end": target_date[:7],
                "target_date": target_date,
            }
    elif system == "fengshui":
        calculation = {"chart_data": copy.deepcopy(dict(normalized))}
    elif system == "physiognomy":
        calculation = {
            "chart_data": {
                "physiognomy_spec": copy.deepcopy(dict(normalized))
            }
        }
    elif system == "meihua":
        event_datetime = normalized.get("event_datetime") or normalized.get(
            "datetime"
        )
        calculation = {
            "event_datetime": event_datetime,
            "chart_data": {
                key: copy.deepcopy(value)
                for key, value in normalized.items()
                if key
                in {
                    "casting_method",
                    "upper_trigram",
                    "lower_trigram",
                }
            },
        }
        if record.get("timezone") is not None:
            calculation.update(
                {
                    "timezone": record.get("timezone"),
                    "location": record.get("location"),
                    "metadata": {
                        "zi_hour_policy": record.get("zi_hour_policy")
                    },
                }
            )
            calculation["chart_data"] = {"casting_method": "time"}
        elif category == "classical_case":
            replay = fixture.get("provider_replay") or {}
            source_table = _load_yaml(
                ROOT / str(fixture.get("source_table") or "")
            )
            source_input = record.get("input") or {}
            calculation = {
                "event_datetime": replay.get("event_datetime"),
                "timezone": replay.get("timezone"),
                "location": replay.get("location"),
                "chart_data": {
                    "casting_method": "supplied_hexagram",
                    "upper_trigram": audit_meihua_provider._trigram_name(
                        source_table,
                        int(source_input["upper_total"]),
                    ),
                    "lower_trigram": audit_meihua_provider._trigram_name(
                        source_table,
                        int(source_input["lower_total"]),
                    ),
                    "moving_line": (
                        int(source_input["moving_total"]) - 1
                    )
                    % 6
                    + 1,
                    "provenance": {
                        "kind": "source_anchored_totals",
                        "source_input_totals": copy.deepcopy(
                            dict(source_input)
                        ),
                    },
                },
                "metadata": {
                    "zi_hour_policy": replay.get("zi_hour_policy")
                },
            }
    elif system == "taiyi":
        lunar_year = record.get("lunar_year")
        calculation = {
            "reference_datetime": (
                f"{int(lunar_year):04d}-07-01T12:00:00+08:00"
                if lunar_year is not None
                else record.get("datetime")
            ),
            "timezone": record.get("timezone") or "Asia/Shanghai",
            "location": record.get("location") or "上海",
        }
    elif system == "xingming":
        calculation = {
            "timezone": record.get("timezone"),
            "location": record.get("location"),
            "birth_data": {
                "datetime": record.get("datetime"),
                "timezone": record.get("timezone"),
                "location": record.get("location"),
                "longitude": record.get("longitude"),
                "latitude": record.get("latitude"),
                "coordinate_source": record.get("coordinate_source"),
            },
        }
    elif system == "luming-nayin":
        if record.get("datetime") is not None:
            calculation = {
                "timezone": record.get("timezone"),
                "location": record.get("location"),
                "birth_data": {
                    "datetime": record.get("datetime"),
                    "timezone": record.get("timezone"),
                    "location": record.get("location"),
                    "zi_hour_policy": record.get("zi_hour_policy") or "midnight",
                },
            }
        else:
            calculation = {
                "chart_data": {"pillars": copy.deepcopy(normalized.get("pillars"))}
            }
            if record.get("month_pillar") is not None:
                calculation["metadata"] = {
                    "luming_taiyuan_profile": "wuxing-jingji-use-taiyuan-v1"
                }
    else:
        calculation = copy.deepcopy(dict(normalized))
    calculation = _plain(calculation) if calculation else {}
    extension = _plain(extension) if extension else {}
    return calculation, extension


def _semantic_input_leaves(value: Any) -> tuple[tuple[str, str], ...]:
    leaves: list[tuple[str, str]] = []

    def pointer_token(item: Any) -> str:
        return str(item).replace("~", "~0").replace("/", "~1")

    def visit(item: Any, *, pointer: str = "") -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                normalized_key = str(key)
                if normalized_key in _AUDIT_LABEL_FIELDS:
                    continue
                visit(
                    child,
                    pointer=f"{pointer}/{pointer_token(normalized_key)}",
                )
        elif isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            for index, child in enumerate(item):
                visit(child, pointer=f"{pointer}/{index}")
        elif pointer:
            leaves.append((pointer, canonical_digest(item)))

    visit(value)
    return tuple(sorted(leaves))


def _unconsumed_fixture_semantic_leaves(
    projection: Mapping[str, Any],
    calculation_projection: Mapping[str, Any],
    extension_projection: Mapping[str, Any],
    *,
    system: str | None,
) -> tuple[str, ...]:
    """Return fixture input leaves absent from the request surfaces they derive."""

    available = Counter(
        digest
        for _pointer, digest in _semantic_input_leaves(
            {
                "calculation": calculation_projection,
                "extension": extension_projection,
            }
        )
    )
    unconsumed: list[str] = []
    for pointer, digest in _semantic_input_leaves(projection):
        if available[digest] > 0:
            available[digest] -= 1
            continue
        # Taiyi's integer lunar year is deterministically converted into the
        # ISO reference datetime committed by the calculation request.
        if system == "taiyi" and pointer == "/lunar_year":
            continue
        unconsumed.append(pointer)
    return tuple(unconsumed)


def _payload_contains_projection(payload: Any, projection: Any) -> bool:
    if isinstance(projection, Mapping):
        if not projection:
            return isinstance(payload, Mapping) and not payload
        return isinstance(payload, Mapping) and all(
            key in payload
            and _payload_contains_projection(payload[key], expected)
            for key, expected in projection.items()
        )
    if isinstance(projection, Sequence) and not isinstance(
        projection,
        (str, bytes, bytearray),
    ):
        return (
            isinstance(payload, Sequence)
            and not isinstance(payload, (str, bytes, bytearray))
            and len(payload) == len(projection)
            and all(
                _payload_contains_projection(actual, expected)
                for actual, expected in zip(payload, projection)
            )
        )
    return type(payload) is type(projection) and payload == projection


def _payload_commits_structured_projection(payload: Any, projection: Any) -> bool:
    """Require an exact path/order/type commitment inside the hashed payload."""

    if not isinstance(payload, Mapping):
        return False
    request_semantics = payload.get("request_semantics")
    return _payload_contains_projection(request_semantics, projection)


def _fixture_case_bindings(
    value: Any,
    *,
    system: str | None = None,
) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    records: dict[str, Mapping[str, Any]] = {}

    def collect_records(item: Any) -> None:
        if isinstance(item, Mapping):
            identifier = next(
                (
                    str(item.get(key))
                    for key in ("id", "case_id", "fixture_id", "example_id")
                    if item.get(key)
                ),
                None,
            )
            if identifier is not None:
                if identifier in records and records[identifier] != item:
                    raise ValueError(
                        f"duplicate fixture case id has conflicting records: {identifier}"
                    )
                records[identifier] = item
            for child in item.values():
                collect_records(child)
        elif isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            for child in item:
                collect_records(child)

    collect_records(value)

    def register(
        identifier: str,
        projection: Mapping[str, Any],
        *,
        source_record: Mapping[str, Any] | None = None,
        override: bool = False,
    ) -> None:
        if not projection:
            return
        normalized_projection = _plain(projection)
        calculation_projection, extension_projection = (
            _fixture_binding_surfaces(
                system,
                identifier,
                source_record or projection,
                normalized_projection,
                fixture=value if isinstance(value, Mapping) else {},
            )
        )
        if not calculation_projection and not extension_projection:
            return
        identity_projection = _plain(
            _fixture_input_projection(source_record or projection)
        )
        binding = {
            "identity_digest": canonical_digest(identity_projection),
            "identity_projection": identity_projection,
            "input_projection": normalized_projection,
            "calculation_projection": calculation_projection,
            "extension_projection": extension_projection,
            "unconsumed_semantic_leaves": _unconsumed_fixture_semantic_leaves(
                normalized_projection,
                calculation_projection,
                extension_projection,
                system=system,
            ),
            "binding_surface": (
                "calculation_and_extension"
                if calculation_projection and extension_projection
                else "calculation"
                if calculation_projection
                else "extension"
            ),
        }
        for alias in _fixture_case_id_aliases({identifier}):
            existing = bindings.get(alias)
            if existing is not None and existing != binding and not override:
                raise ValueError(f"ambiguous fixture semantic binding: {alias}")
            bindings[alias] = binding

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            identifier = next(
                (
                    str(item.get(key))
                    for key in ("id", "case_id", "fixture_id", "example_id")
                    if item.get(key)
                ),
                None,
            )
            if identifier is not None:
                input_case = item.get("input_case")
                referenced = records.get(str(input_case or ""))
                projection = (
                    _fixture_input_projection(referenced)
                    if referenced is not None
                    else _fixture_input_projection(item)
                )
                projection = _system_fixture_input_projection(
                    system,
                    referenced if referenced is not None else item,
                    projection,
                    fixture=value if isinstance(value, Mapping) else {},
                    records=records,
                )
                register(
                    identifier,
                    projection,
                    source_record=referenced if referenced is not None else item,
                )
            cycle = item.get("nayin_cycle")
            if isinstance(cycle, Sequence) and not isinstance(
                cycle,
                (str, bytes, bytearray),
            ):
                for index, row in enumerate(cycle):
                    if (
                        isinstance(row, Sequence)
                        and not isinstance(row, (str, bytes, bytearray))
                        and len(row) >= 2
                    ):
                        ganzhi = str(row[0])
                        pillars = [
                            str(cycle[(index + offset) % len(cycle)][0])
                            for offset in range(4)
                        ]
                        register(
                            f"nayin-cycle-{ganzhi}",
                            {"pillars": pillars},
                            source_record={"pillars": pillars},
                        )
            for child in item.values():
                visit(child)
        elif isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            for child in item:
                visit(child)

    visit(value)

    def apply_exact_method_cases(item: Any) -> None:
        if isinstance(item, Mapping):
            exact_cases = item.get("exact_method_cases")
            if isinstance(exact_cases, Mapping):
                for identifier, projection in exact_cases.items():
                    if isinstance(projection, Mapping):
                        register(
                            str(identifier),
                            projection,
                            source_record=projection,
                            override=True,
                        )
            for child in item.values():
                apply_exact_method_cases(child)
        elif isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            for child in item:
                apply_exact_method_cases(child)

    apply_exact_method_cases(value)
    return bindings


def _extension_status_is_ready(
    extension: FactExtensionResult | None,
    *,
    capability: Any,
    requested_dimensions: tuple[str, ...],
) -> bool:
    if extension is None:
        return False
    if extension.status == "complete":
        return bool(extension.facts) and not extension.unsupported_dimensions
    supported_dimensions = set(requested_dimensions) - set(
        extension.unsupported_dimensions
    )
    return (
        capability.mode == "observation_driven_ready"
        and extension.status == "partial"
        and bool(extension.facts)
        and bool(extension.unsupported_dimensions)
        and bool(supported_dimensions)
        and set(extension.unsupported_dimensions).issubset(requested_dimensions)
    )


def _horizon_is_valid(
    horizon: Mapping[str, Any], *, system: str | None = None
) -> bool:
    if set(horizon) - {"kind", "start", "end", "target_date"}:
        return False
    kind = str(horizon.get("kind") or "")
    if kind in {"instant", "life"}:
        return set(horizon) == {"kind"}
    start = horizon.get("start")
    end = horizon.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        return False
    try:
        if kind == "day":
            start_value: Any = date.fromisoformat(start)
            end_value: Any = date.fromisoformat(end)
        elif kind == "month":
            if re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", start) is None or re.fullmatch(
                r"\d{4}-(?:0[1-9]|1[0-2])", end
            ) is None:
                return False
            start_value = start
            end_value = end
        elif kind == "year":
            if re.fullmatch(r"\d{4}", start) is None or re.fullmatch(
                r"\d{4}", end
            ) is None:
                return False
            start_value = int(start)
            end_value = int(end)
        else:
            return False
    except ValueError:
        return False
    if start_value > end_value:
        return False
    target = horizon.get("target_date")
    if target is None:
        return True
    if system != "ziwei" or kind != "month":
        return False
    if not isinstance(target, str):
        return False
    try:
        target_date = date.fromisoformat(target)
    except ValueError:
        return False
    if kind == "day":
        return start_value <= target_date <= end_value
    if kind == "month":
        return start <= target[:7] <= end
    if kind == "year":
        return int(start) <= target_date.year <= int(end)
    return False


def _fixture_case_category_aliases(
    categories: Mapping[str, set[str]],
) -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    for identifier, names in categories.items():
        for alias in _fixture_case_id_aliases({identifier}):
            aliases.setdefault(alias, set()).update(names)
    return aliases


def _first_count(counts: Mapping[str, Any], *keys: str) -> tuple[str, int]:
    for key in keys:
        if key in counts:
            try:
                return key, int(counts[key])
            except (TypeError, ValueError):
                return key, 0
    return "missing", 0


def _boundary_categories(
    report: Mapping[str, Any],
) -> list[str]:
    declared = report.get("boundary_categories")
    if isinstance(declared, Sequence) and not isinstance(declared, str):
        return sorted({str(item) for item in declared if str(item).strip()})
    return []


BOUNDARY_ALGORITHM_PROOFS: dict[tuple[str, str], str] = {
    ("liuyao", "hexagram_catalog"): "liuyao.plate.hexagram-palace-shiying",
    ("liuyao", "six_spirit_day_stem"): "liuyao.plate.six-spirits",
    ("liuyao", "xunkong_cycle"): "liuyao.calendar.xunkong-month-day-relations",
    ("fengshui", "compass_boundary"): (
        "fengshui.observation.compass-layout-contract"
    ),
}
BOUNDARY_ALGORITHM_COUNT_PROOFS: dict[tuple[str, str], dict[str, Any]] = {
    ("liuyao", "hexagram_catalog"): {
        "counts": {"hexagrams": 64, "source_table_cases": 64},
        "zero_counts": ("provider_mismatches",),
    },
    ("liuyao", "xunkong_cycle"): {
        "counts": {"xunkong_boundaries": 6},
        "zero_counts": ("provider_mismatches",),
    },
    ("liuyao", "six_spirit_day_stem"): {
        "counts": {"day_stem_boundaries": 10},
        "zero_counts": ("provider_mismatches",),
    },
    ("fengshui", "compass_boundary"): {
        "counts": {"compass_boundary_checks": 48},
        "zero_counts": (
            "compass_boundary_mismatches",
            "compass_reference_mismatches",
        ),
    },
}
BOUNDARY_LIFECYCLE_PROOFS: dict[tuple[str, str], str] = {
    ("liuyao", "random_cast_lifecycle"): (
        "liuyao.transaction.random-cast-lifecycle"
    ),
}

BOUNDARY_AGGREGATE_PROOFS: dict[tuple[str, str], dict[str, Any]] = {
    ("liuyao", "calendar_witness"): {
        "case_prefix": "zengshan-",
        "expected_case_count": 30,
        "counts": {"complete_reference_cases": 30, "fixture_oracle_cases": 30},
        "zero_counts": ("provider_mismatches", "determinism_mismatches"),
    },
    ("liuyao", "moving_lines"): {
        "case_ids": {
            "stable-all-yang",
            "all-old-yang",
            "all-old-yin",
            "middle-pair",
        },
        "expected_case_count": 4,
        "counts": {"moving_boundaries": 4},
        "zero_counts": ("provider_mismatches", "determinism_mismatches"),
    },
    ("liuren", "classical_source_plate"): {
        "case_prefix": "daquan-L",
        "excluded_case_prefix": "daquan-L7774-",
        "expected_case_count": 23,
        "counts": {"complete_source_plates": 23, "classical_cases": 39},
    },
    ("qimen", "external_reference"): {
        "case_prefix": "qimen-go-",
        "expected_case_count": 30,
        "counts": {"external_reference_boards": 30},
        "zero_counts": (
            "external_reference_mismatches",
            "independent_oracle_mismatches",
        ),
    },
    ("taiyi", "annual_external_reference"): {
        "case_prefix": "kintaiyi-",
        "expected_case_count": 30,
        "counts": {"external_reference_boards": 30},
        "zero_counts": (
            "external_reference_mismatches",
            "external_raw_mismatches",
            "source_board_mismatches",
        ),
    },
    ("selection", "external_reference"): {
        "case_prefix": "lunar-python-",
        "expected_case_count": 30,
        "counts": {
            "external_reference_cases": 30,
            "published_calendar_cases": 30,
        },
        "zero_counts": (
            "external_unexplained_mismatches",
            "published_calendar_mismatches",
            "published_source_verification_failures",
        ),
    },
    ("meihua", "calendar_witness"): {
        "boundary_categories": {
            "solar_term_boundary",
            "day_rollover",
            "leap_month",
            "timezone_boundary",
            "seasonal_boundary",
        },
        "expected_case_count": 8,
        "counts": {"calendar_boundaries": 8},
        "zero_counts": ("provider_mismatches", "determinism_mismatches"),
    },
    ("meihua", "seasonal_profile"): {
        "boundary_categories": {"seasonal_boundary"},
        "expected_case_count": 1,
        "counts": {"seasonal_profiles": 5},
        "zero_counts": ("provider_mismatches", "determinism_mismatches"),
    },
    ("fengshui", "complete"): {
        "case_prefix": "FS-O",
        "minimum_case_count": 20,
        "minimum_counts": {"complete_observation_fixtures": 20},
        "zero_counts": ("fixture_mismatches", "oracle_mismatches"),
    },
    ("fengshui", "correction"): {
        "case_ids": {"FS-O20"},
        "expected_case_count": 1,
        "minimum_counts": {"complete_observation_fixtures": 20},
        "zero_counts": ("fixture_mismatches", "oracle_mismatches"),
    },
    ("fengshui", "missing"): {
        "boundary_categories": {"partial"},
        "case_ids": {"FS-PARTIAL-01"},
        "expected_case_count": 1,
        "counts": {"partial_fixtures": 1},
        "zero_counts": ("special_case_mismatches", "oracle_mismatches"),
    },
    ("physiognomy", "complete"): {
        "case_prefix": "complete-",
        "minimum_case_count": 20,
        "minimum_counts": {"complete_fixtures": 20},
        "zero_counts": ("fixture_mismatches", "oracle_mismatches"),
    },
    ("physiognomy", "conflict"): {
        "boundary_categories": {"contradictory"},
        "expected_case_count": 1,
        "counts": {"boundary_fixtures": 5},
        "zero_counts": ("boundary_mismatches", "oracle_mismatches"),
    },
    ("physiognomy", "correction"): {
        "boundary_categories": {"corrected_to_missing"},
        "expected_case_count": 1,
        "counts": {"boundary_fixtures": 5},
        "zero_counts": ("boundary_mismatches", "oracle_mismatches"),
    },
    ("physiognomy", "low_quality"): {
        "boundary_categories": {"low_light", "filtered"},
        "expected_case_count": 2,
        "counts": {"boundary_fixtures": 5},
        "zero_counts": ("boundary_mismatches", "oracle_mismatches"),
    },
    ("physiognomy", "missing"): {
        "boundary_categories": {"hidden_side", "corrected_to_missing"},
        "expected_case_count": 2,
        "counts": {"boundary_fixtures": 5},
        "zero_counts": ("boundary_mismatches", "oracle_mismatches"),
    },
}
for _system in ("liuren", "selection"):
    for _horizon in ("day", "month", "instant" if _system == "liuren" else "year"):
        BOUNDARY_AGGREGATE_PROOFS[(_system, _horizon)] = {
            "horizon_kind": _horizon,
            "expected_case_count": 13 if _system == "liuren" else 10,
        }


def _expected_boundary_proof(system: str, category: str) -> tuple[str, str]:
    key = (system, category)
    if key in BOUNDARY_ALGORITHM_PROOFS:
        return "algorithm_invariant", BOUNDARY_ALGORITHM_PROOFS[key]
    if key in BOUNDARY_LIFECYCLE_PROOFS:
        return "transaction_lifecycle", BOUNDARY_LIFECYCLE_PROOFS[key]
    return "provider_replay", f"provider_replay:{system}:{category}"


def _boundary_proof_declarations(
    system: str,
    categories: Sequence[Any],
) -> list[dict[str, str]]:
    declarations: list[dict[str, str]] = []
    for category in sorted(
        {str(item) for item in categories if str(item).strip()}
    ):
        proof_mode, proof_id = _expected_boundary_proof(system, category)
        declarations.append(
            {
                "category": category,
                "proof_mode": proof_mode,
                "proof_id": proof_id,
            }
        )
    return declarations


def _boundary_proof_summary(
    system: str,
    *,
    declared_categories: Sequence[Any],
    proof_declarations: Sequence[Any],
    dedicated_runtime_replay: Mapping[str, Any],
    dedicated_counts: Mapping[str, Any] | None = None,
    algorithm: Mapping[str, Any],
    transaction_lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify every boundary declaration against centrally observed evidence."""

    declared = sorted(
        {str(category) for category in declared_categories if str(category).strip()}
    )
    findings: list[str] = []
    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(proof_declarations):
        if not isinstance(raw, Mapping):
            findings.append(f"boundary proof {index} must be an object")
            continue
        row = {
            "category": str(raw.get("category") or ""),
            "proof_mode": str(raw.get("proof_mode") or ""),
            "proof_id": str(raw.get("proof_id") or ""),
        }
        if not all(row.values()):
            findings.append(f"boundary proof {index} has empty identity fields")
        normalized.append(row)

    categories = [row["category"] for row in normalized]
    proof_ids = [row["proof_id"] for row in normalized]
    duplicate_categories = sorted(
        {category for category in categories if categories.count(category) > 1}
    )
    duplicate_proof_ids = sorted(
        {proof_id for proof_id in proof_ids if proof_ids.count(proof_id) > 1}
    )
    if duplicate_categories:
        findings.append(
            f"duplicate category proof declarations: {duplicate_categories}"
        )
    if duplicate_proof_ids:
        findings.append(f"duplicate proof_id declarations: {duplicate_proof_ids}")

    dedicated_counts = dedicated_counts or {}
    replay_rows = dedicated_runtime_replay.get("provider_boundary_replays") or ()
    if not isinstance(replay_rows, Sequence) or isinstance(
        replay_rows, (str, bytes, bytearray)
    ):
        replay_rows = ()
    case_replays = dedicated_runtime_replay.get("case_replays") or ()
    if not isinstance(case_replays, Sequence) or isinstance(
        case_replays, (str, bytes, bytearray)
    ):
        case_replays = ()
    dependencies = algorithm.get("dependencies") or ()
    if not isinstance(dependencies, Sequence) or isinstance(
        dependencies, (str, bytes, bytearray)
    ):
        dependencies = ()

    proof_results: list[dict[str, Any]] = []
    verified_categories: set[str] = set()
    for declaration in normalized:
        category = declaration["category"]
        mode = declaration["proof_mode"]
        proof_id = declaration["proof_id"]
        expected_mode, expected_id = _expected_boundary_proof(system, category)
        proof_findings: list[str] = []
        case_ids: list[str] = []
        if proof_id != expected_id:
            proof_findings.append(
                f"{category}: unknown proof_id {proof_id!r}; expected {expected_id!r}"
            )
        if mode != expected_mode:
            proof_findings.append(
                f"{category}: proof mode mismatch; expected {expected_mode!r}"
            )
        if not proof_findings and mode == "provider_replay":
            candidates = [
                row
                for row in replay_rows
                if isinstance(row, Mapping)
                and category in set(row.get("categories") or ())
            ]
            aggregate = BOUNDARY_AGGREGATE_PROOFS.get((system, category))
            if not candidates and aggregate:
                all_rows = [
                    row
                    for row in (*case_replays, *replay_rows)
                    if isinstance(row, Mapping)
                ]
                by_case_id = {
                    str(row.get("case_id") or ""): row for row in all_rows
                }
                selected = list(by_case_id.values())
                if aggregate.get("case_prefix"):
                    prefix = str(aggregate["case_prefix"])
                    selected = [
                        row
                        for row in selected
                        if str(row.get("case_id") or "").startswith(prefix)
                    ]
                if aggregate.get("excluded_case_prefix"):
                    prefix = str(aggregate["excluded_case_prefix"])
                    selected = [
                        row
                        for row in selected
                        if not str(row.get("case_id") or "").startswith(prefix)
                    ]
                if aggregate.get("case_ids"):
                    required_ids = set(aggregate["case_ids"])
                    selected = [
                        row
                        for row in selected
                        if str(row.get("case_id") or "") in required_ids
                    ]
                if aggregate.get("boundary_categories"):
                    aliases = set(aggregate["boundary_categories"])
                    selected = [
                        row
                        for row in selected
                        if aliases & set(row.get("categories") or ())
                    ]
                if aggregate.get("horizon_kind"):
                    horizon_kind = str(aggregate["horizon_kind"])
                    selected = [
                        row
                        for row in selected
                        if horizon_kind
                        in set(row.get("extension_horizon_kinds") or ())
                    ]
                candidates = selected
                expected_count = aggregate.get("expected_case_count")
                minimum_count = aggregate.get("minimum_case_count")
                if expected_count is not None and len(candidates) != int(expected_count):
                    label = (
                        f"horizon kind {aggregate['horizon_kind']!r} "
                        if aggregate.get("horizon_kind")
                        else ""
                    )
                    proof_findings.append(
                        f"{category}: {label}provider case count "
                        f"{len(candidates)} != {expected_count}"
                    )
                if minimum_count is not None and len(candidates) < int(minimum_count):
                    proof_findings.append(
                        f"{category}: provider case count {len(candidates)} "
                        f"< minimum {minimum_count}"
                    )
                for field, expected in (aggregate.get("counts") or {}).items():
                    if dedicated_counts.get(field) != expected:
                        proof_findings.append(
                            f"{category}: dedicated count {field!r} "
                            f"!= {expected}"
                        )
                for field, minimum in (aggregate.get("minimum_counts") or {}).items():
                    observed = dedicated_counts.get(field)
                    if not isinstance(observed, int) or observed < int(minimum):
                        proof_findings.append(
                            f"{category}: dedicated count {field!r} "
                            f"< minimum {minimum}"
                        )
                for field in aggregate.get("zero_counts") or ():
                    if dedicated_counts.get(field) != 0:
                        proof_findings.append(
                            f"{category}: dedicated mismatch count {field!r} is not zero"
                        )
            if not candidates:
                proof_findings.append(f"{category}: no provider case was observed")
            elif not all(
                row.get("ready") is True
                and row.get("fixture_input_bound") is True
                and str(row.get("case_id") or "").strip()
                for row in candidates
            ):
                proof_findings.append(
                    f"{category}: provider case is not ready and fixture-bound"
                )
            elif (
                dedicated_runtime_replay.get("case_replay_ready") is not True
                or dedicated_runtime_replay.get("provider_boundary_replay_ready")
                is not True
            ):
                proof_findings.append(
                    f"{category}: provider replay observer is not ready"
                )
            else:
                case_ids = sorted(str(row["case_id"]) for row in candidates)
        elif not proof_findings and mode == "algorithm_invariant":
            dependency = next(
                (
                    row
                    for row in dependencies
                    if isinstance(row, Mapping) and row.get("id") == proof_id
                ),
                None,
            )
            if not (
                algorithm.get("verified") is True
                and algorithm.get("provenance_complete") is True
                and isinstance(dependency, Mapping)
                and dependency.get("status") == "verified"
                and dependency.get("independent_sample_id")
                and dependency.get("primary_source_hashes")
            ):
                proof_findings.append(
                    f"{category}: algorithm invariant is not independently verified"
                )
            count_contract = BOUNDARY_ALGORITHM_COUNT_PROOFS.get(
                (system, category)
            )
            if count_contract is None:
                proof_findings.append(
                    f"{category}: algorithm invariant has no dedicated count contract"
                )
            else:
                for field, expected in count_contract["counts"].items():
                    if dedicated_counts.get(field) != expected:
                        proof_findings.append(
                            f"{category}: dedicated count {field!r} != {expected}"
                        )
                for field in count_contract["zero_counts"]:
                    if dedicated_counts.get(field) != 0:
                        proof_findings.append(
                            f"{category}: dedicated mismatch count {field!r} is not zero"
                        )
        elif not proof_findings and mode == "transaction_lifecycle":
            if not (
                transaction_lifecycle.get("ready") is True
                and not transaction_lifecycle.get("findings")
            ):
                proof_findings.append(
                    f"{category}: transaction lifecycle proof is not ready"
                )
        verified = not proof_findings
        if verified:
            verified_categories.add(category)
        findings.extend(proof_findings)
        proof_results.append(
            {
                **declaration,
                "case_ids": case_ids,
                "verified": verified,
                "findings": proof_findings,
            }
        )

    declared_set = set(declared)
    proof_category_set = set(categories)
    for category in sorted(declared_set - proof_category_set):
        findings.append(f"declared boundary category {category!r} has no proof")
    for category in sorted(proof_category_set - declared_set):
        findings.append(f"boundary proof category {category!r} is not declared")
    if verified_categories != declared_set:
        findings.append(
            "declared boundary categories differ from centrally verified categories"
        )
    if duplicate_categories or duplicate_proof_ids:
        verified_categories = set()

    findings = list(dict.fromkeys(findings))
    return {
        "schema_version": "mingli-boundary-proof-summary-v1",
        "declared_categories": declared,
        "verified_categories": sorted(verified_categories),
        "proofs": proof_results,
        "ready": not findings,
        "findings": findings,
    }


def _algorithm_summary(
    system: str,
    *,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    global_audit: Mapping[str, Any],
    reported_counts: Mapping[str, Any],
    live_dependencies: Sequence[Any],
    runtime_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    provider = (manifest.get("providers") or {}).get(system) or {}
    raw_dependencies = provider.get("dependencies") or []
    dependencies: list[dict[str, Any]] = []
    provenance_complete = bool(raw_dependencies)
    for raw in raw_dependencies:
        if not isinstance(raw, Mapping):
            provenance_complete = False
            continue
        convention = raw.get("convention") or {}
        sources = [
            source
            for source in raw.get("primary_sources") or ()
            if isinstance(source, Mapping)
        ]
        sample = raw.get("independent_test_sample") or {}
        references = [
            reference
            for reference in raw.get("engineering_references") or ()
            if isinstance(reference, Mapping)
        ]
        source_artifact = raw.get("source_artifact") or {}
        runtime_binding = raw.get("runtime_binding") or {}
        artifact_hashes = sorted(
            {
                str(value)
                for reference in references
                for key, value in reference.items()
                if key.endswith("sha256") and str(value).strip()
            }
            | {
                str(source_artifact.get("sha256"))
                if source_artifact.get("sha256")
                else ""
            }
            - {""}
        )
        primary_source_hashes = sorted(
            str(source.get("sha256") or "") for source in sources
        )
        dependency = {
            "id": str(raw.get("id") or ""),
            "category": str(raw.get("category") or ""),
            "version": str(raw.get("version") or ""),
            "status": str(raw.get("status") or ""),
            "convention_id": str(convention.get("id") or ""),
            "convention_version": str(convention.get("version") or ""),
            "convention_disputed": convention.get("disputed"),
            "primary_source_hashes": primary_source_hashes,
            "independent_sample_id": str(sample.get("id") or ""),
            "engineering_reference_versions": sorted(
                f"{reference.get('name')}@{reference.get('version')}"
                for reference in references
                if reference.get("name") and reference.get("version")
            ),
            "artifact_hashes": artifact_hashes,
            "runtime_binding": _plain(runtime_binding),
        }
        dependencies.append(dependency)
        provenance_complete = provenance_complete and bool(
            dependency["id"]
            and dependency["version"]
            and dependency["status"] == "verified"
            and dependency["convention_id"]
            and dependency["convention_version"]
            and primary_source_hashes
            and all(len(item) == 64 for item in primary_source_hashes)
            and dependency["independent_sample_id"]
        )
    reported_key, reported_count = _first_count(
        reported_counts,
        "algorithm_dependencies",
    )
    global_findings = [str(item) for item in global_audit.get("findings") or ()]
    system_findings = [
        item
        for item in global_findings
        if item.startswith("matrix:") or item.startswith(f"provider {system}")
    ]
    dependency_count_matches = reported_count == len(dependencies)
    manifest_identity = sorted(
        (dependency["id"], dependency["version"])
        for dependency in dependencies
    )
    live_identity = sorted(
        (str(getattr(item, "id", "")), str(getattr(item, "version", "")))
        for item in live_dependencies
    )
    live_declarations_match = live_identity == manifest_identity
    runtime_identity_matches: bool | None = None
    if runtime_identity is not None:
        dependency_id = str(runtime_identity.get("dependency_id") or "")
        matching = next(
            (
                dependency
                for dependency in dependencies
                if dependency["id"] == dependency_id
            ),
            None,
        )
        binding = (matching or {}).get("runtime_binding") or {}
        runtime_identity_matches = bool(matching) and all(
            (
                runtime_identity.get("algorithm_version")
                == binding.get("calendar_algorithm_version"),
                runtime_identity.get("convention_id")
                == binding.get("calendar_convention_id"),
                str(runtime_identity.get("convention_version") or "")
                == str(binding.get("calendar_convention_version") or ""),
                runtime_identity.get("engine") == binding.get("engine"),
                str(runtime_identity.get("engine_version") or "")
                == str(binding.get("engine_version") or ""),
                sorted(runtime_identity.get("zi_hour_policies") or ())
                == sorted(binding.get("zi_hour_policies") or ()),
            )
        )
    return {
        "manifest_sha256": manifest_sha256,
        "source_audit_status": str(provider.get("source_audit_status") or ""),
        "dependency_count": len(dependencies),
        "reported_dependency_count_key": reported_key,
        "reported_dependency_count": reported_count,
        "dependency_count_matches": dependency_count_matches,
        "live_declared_dependencies": [
            {"id": dependency_id, "version": version}
            for dependency_id, version in live_identity
        ],
        "live_declarations_match": live_declarations_match,
        "runtime_identity": _plain(runtime_identity or {}),
        "runtime_identity_matches": runtime_identity_matches,
        "dependencies": dependencies,
        "research_sources_verified": bool(
            global_audit.get("research_sources_verified")
        ),
        "provenance_complete": bool(provenance_complete),
        "verified": bool(global_audit.get("ok"))
        and not system_findings
        and dependency_count_matches
        and live_declarations_match
        and bool(provenance_complete),
        "findings": system_findings,
    }


def _entry_readiness_findings(
    system: str,
    entry: Mapping[str, Any],
) -> list[str]:
    findings: list[str] = []
    if not isinstance(entry, Mapping):
        return [f"{system}: provider entry must be an object"]

    def section(name: str) -> Mapping[str, Any]:
        value = entry.get(name)
        if isinstance(value, Mapping):
            return value
        findings.append(f"{system}: {name} must be an object")
        return {}

    def safe_int(value: Any, label: str) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            findings.append(f"{system}: {label} must be an integer")
            return 0

    declaration = section("declaration")
    runtime = section("runtime")
    fixtures = section("fixtures")
    dedicated = section("dedicated_audit")
    dedicated_runtime = section("dedicated_runtime_replay")
    algorithm = section("algorithm")
    live = section("live_contract")
    source = section("source_applicability")
    transaction_lifecycle = section("transaction_lifecycle")
    declared_boundary_categories = fixtures.get("boundary_categories") or ()
    if not isinstance(declared_boundary_categories, Sequence) or isinstance(
        declared_boundary_categories, (str, bytes, bytearray)
    ):
        declared_boundary_categories = ()
    boundary_proof_summary = _boundary_proof_summary(
        system,
        declared_categories=declared_boundary_categories,
        proof_declarations=_boundary_proof_declarations(
            system,
            declared_boundary_categories,
        ),
        dedicated_runtime_replay=dedicated_runtime,
        dedicated_counts=(dedicated.get("counts") or {}),
        algorithm=algorithm,
        transaction_lifecycle=transaction_lifecycle,
    )
    if entry.get("boundary_proof_summary") != boundary_proof_summary:
        findings.append(f"{system}: boundary proof summary is not centrally derived")
    findings.extend(
        f"{system}: boundary proof {item}"
        for item in boundary_proof_summary["findings"]
    )
    if declaration.get("mode") not in {"calculation", "observation_driven_ready"}:
        findings.append(f"{system}: unavailable or unsupported provider mode")
    for field in (
        "objects",
        "horizons",
        "dimensions",
        "outputs",
        "extension_outputs",
        "output_bindings",
        "extension_output_bindings",
    ):
        if not declaration.get(field):
            findings.append(f"{system}: declaration has empty {field}")
    if not isinstance(runtime, Mapping) or runtime.get("generic"):
        findings.append(f"{system}: generic or placeholder provider remains")
    expected_identity = EXPECTED_PROVIDER_IDENTITIES.get(system)
    if expected_identity is None:
        findings.append(f"{system}: release provider identity contract is missing")
        expected_class = expected_id = expected_version = ""
    else:
        expected_class, expected_id, expected_version = expected_identity
    runtime_identity_matches = (
        isinstance(runtime, Mapping)
        and runtime.get("class") == expected_class
        and runtime.get("provider_id") == expected_id
        and runtime.get("provider_version") == expected_version
        and runtime.get("expected_class") == expected_class
        and runtime.get("expected_provider_id") == expected_id
        and runtime.get("expected_provider_version") == expected_version
        and runtime.get("identity_matches") is True
    )
    if not runtime_identity_matches:
        findings.append(f"{system}: release provider identity drift")
    if not str(runtime.get("provider_version") or "").strip():
        findings.append(f"{system}: provider version is empty")
    qualifying = safe_int(fixtures.get("qualifying_cases"), "qualifying_cases")
    minimum = safe_int(fixtures.get("minimum_cases"), "minimum_cases") or 1
    if qualifying < minimum:
        findings.append(
            f"{system}: fixture count {qualifying} is below required {minimum}"
        )
    if not fixtures.get("boundary_categories"):
        findings.append(f"{system}: fixture boundary coverage is empty")
    if safe_int(fixtures.get("boundary_case_count"), "boundary_case_count") < 1:
        findings.append(f"{system}: no dedicated boundary cases were executed")
    sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
    if sha256_pattern.fullmatch(str(fixtures.get("sha256") or "")) is None:
        findings.append(f"{system}: fixture sha256 is missing")
    dedicated_fixture_sha256 = fixtures.get("dedicated_reported_sha256")
    if sha256_pattern.fullmatch(str(dedicated_fixture_sha256 or "")) is None:
        findings.append(f"{system}: dedicated fixture sha256 is missing")
    if sha256_pattern.fullmatch(
        str(fixtures.get("dedicated_expected_sha256") or "")
    ) is None:
        findings.append(f"{system}: fixed expected fixture sha256 is missing")
    if not fixtures.get("dedicated_hash_matches"):
        findings.append(f"{system}: fixture hash differs from dedicated audit")
    route_owned = safe_int(fixtures.get("route_owned_cases"), "route_owned_cases")
    if route_owned < minimum:
        findings.append(
            f"{system}: route-owned replay count {route_owned} is below required {minimum}"
        )
    if route_owned != qualifying:
        findings.append(f"{system}: qualifying and route-owned replay counts differ")
    if fixtures.get("route_owned_count_key") != "route_owned_cases":
        findings.append(f"{system}: route-owned case count is not explicit")
    distinct_route_owned = safe_int(
        fixtures.get("distinct_route_owned_cases"),
        "distinct_route_owned_cases",
    )
    if distinct_route_owned != route_owned:
        findings.append(f"{system}: route-owned case ids are missing or duplicated")
    if not fixtures.get("route_owned_ids_match_fixture"):
        findings.append(f"{system}: route-owned case ids are not fixture-bound")
    if not isinstance(dedicated, Mapping) or not dedicated.get("provider_ready"):
        findings.append(f"{system}: dedicated provider audit is not ready")
    if dedicated.get("findings"):
        findings.append(f"{system}: dedicated provider audit has findings")
    if dedicated.get("status") != "pass":
        findings.append(f"{system}: dedicated provider audit status is not pass")
    if not str(dedicated.get("schema_version") or "").strip():
        findings.append(f"{system}: dedicated audit schema is missing")
    if dedicated.get("system") != system:
        findings.append(f"{system}: dedicated audit system identity mismatch")
    dedicated_provider = dedicated.get("provider") or {}
    if (
        not isinstance(dedicated_provider, Mapping)
        or dedicated_provider.get("provider_id") != expected_id
        or str(dedicated_provider.get("provider_version") or "")
        != expected_version
    ):
        findings.append(f"{system}: dedicated provider identity mismatch")
    dedicated_counts = dedicated.get("counts") or {}
    if not isinstance(dedicated_counts, Mapping):
        dedicated_counts = {}
    provider_calculations = safe_int(
        dedicated_counts.get("provider_calculations"),
        "provider_calculations",
    )
    determinism_checks = safe_int(
        dedicated_counts.get("determinism_checks"),
        "determinism_checks",
    )
    if provider_calculations < 2 * route_owned:
        findings.append(f"{system}: dedicated provider replay count is incomplete")
    if determinism_checks < route_owned:
        findings.append(f"{system}: dedicated determinism replay count is incomplete")
    observed_calculations = safe_int(
        dedicated_runtime.get("calculation_runs"),
        "observed calculation_runs",
    )
    observed_inputs = safe_int(
        dedicated_runtime.get("distinct_input_hashes"),
        "observed distinct_input_hashes",
    )
    observed_effective_inputs = safe_int(
        dedicated_runtime.get("distinct_effective_case_digests"),
        "observed distinct_effective_case_digests",
    )
    observed_deterministic = safe_int(
        dedicated_runtime.get("deterministic_input_replays"),
        "observed deterministic_input_replays",
    )
    fixture_boundary_categories = set(
        dedicated_runtime.get("fixture_boundary_categories") or ()
    )
    observed_boundary_categories = set(
        dedicated_runtime.get("provider_boundary_categories") or ()
    )
    declared_boundary_categories = set(fixtures.get("boundary_categories") or ())
    replay_required_categories = (
        declared_boundary_categories & fixture_boundary_categories
    )
    observed_replay_failures: list[str] = []
    if observed_calculations < 2 * route_owned:
        observed_replay_failures.append("calculation_runs")
    if observed_inputs < route_owned:
        observed_replay_failures.append("distinct_input_hashes")
    if observed_effective_inputs < minimum:
        observed_replay_failures.append("distinct_effective_inputs")
    if dedicated_runtime.get("effective_cases_are_distinct") is not True:
        observed_replay_failures.append("effective_case_uniqueness")
    if observed_deterministic < route_owned:
        observed_replay_failures.append("deterministic_input_replays")
    if not dedicated_runtime.get("provider_identity_matches"):
        observed_replay_failures.append("provider_identity")
    if not dedicated_runtime.get("case_ids_fixture_bound"):
        observed_replay_failures.append("fixture_binding")
    if not dedicated_runtime.get("case_replay_ready"):
        observed_replay_failures.append("case_replay")
    if not dedicated_runtime.get("provider_boundary_replay_ready"):
        observed_replay_failures.append("boundary_replay")
    if not replay_required_categories:
        observed_replay_failures.append("boundary_category_binding")
    elif not replay_required_categories <= observed_boundary_categories:
        observed_replay_failures.append("boundary_category_coverage")
    if safe_int(
        dedicated_runtime.get("case_replay_count"),
        "observed case_replay_count",
    ) != route_owned:
        observed_replay_failures.append("case_replay_count")
    if dedicated_runtime.get("findings"):
        observed_replay_failures.append("runtime_findings")
    if observed_replay_failures:
        findings.append(
            f"{system}: observed dedicated provider replay is incomplete "
            f"({', '.join(observed_replay_failures)})"
        )
    if not isinstance(algorithm, Mapping) or not algorithm.get("verified"):
        findings.append(f"{system}: algorithm provenance audit is not verified")
    if not algorithm.get("provenance_complete"):
        findings.append(f"{system}: algorithm provenance is incomplete")
    if not algorithm.get("dependency_count_matches"):
        findings.append(f"{system}: algorithm dependency count drift")
    if not algorithm.get("live_declarations_match"):
        findings.append(f"{system}: live algorithm dependency declarations drift")
    if system == "liuren" and algorithm.get("runtime_identity_matches") is not True:
        findings.append(f"{system}: runtime algorithm identity drift")
    if (
        system == "liuren"
        and dedicated.get("calendar_month_general_closure_ready") is not True
    ):
        findings.append(f"{system}: calendar/month-general closure failed")
    if not isinstance(live, Mapping) or live.get("runs") != 2:
        findings.append(f"{system}: live provider was not run twice")
    if not live.get("deterministic") or live.get("findings"):
        findings.append(f"{system}: live provider contract failed")
    if set(live.get("resolved_output_bindings") or ()) != set(
        declaration.get("outputs") or ()
    ):
        findings.append(f"{system}: declared output bindings are unresolved")
    if set(live.get("resolved_extension_bindings") or ()) != set(
        declaration.get("extension_outputs") or ()
    ):
        findings.append(f"{system}: declared extension bindings are unresolved")
    if not isinstance(source, Mapping):
        findings.append(f"{system}: source applicability audit is missing")
    else:
        findings.extend(_source_pack_replay_findings(system, source))
    if system == "liuyao" and (
        not isinstance(transaction_lifecycle, Mapping)
        or not transaction_lifecycle.get("ready")
        or transaction_lifecycle.get("findings")
    ):
        findings.append(f"{system}: transaction lifecycle audit failed")
    if system == "liuyao":
        random_cast_contract = dedicated.get("random_cast_contract") or {}
        expected_random_fields = {
            "schema_version",
            "ready",
            "new_cast_count",
            "token_hex_call_count",
            "token_hex_32_byte_requests",
            *LIUYAO_RANDOM_CAST_PROOFS,
        }
        random_contract_ready = (
            isinstance(random_cast_contract, Mapping)
            and set(random_cast_contract) == expected_random_fields
            and random_cast_contract.get("schema_version")
            == "mingli-liuyao-random-cast-contract-v1"
            and random_cast_contract.get("ready") is True
            and random_cast_contract.get("new_cast_count") == 2
            and random_cast_contract.get("token_hex_call_count") == 2
            and random_cast_contract.get("token_hex_32_byte_requests") == 2
            and all(
                random_cast_contract.get(proof) is True
                for proof in LIUYAO_RANDOM_CAST_PROOFS
            )
        )
        if not random_contract_ready:
            findings.append(f"{system}: random cast contract audit failed")
    return list(dict.fromkeys(findings))


def _matrix_input_fingerprint(root: Path) -> str:
    """Hash every generator input so the process cache cannot become stale."""

    root = root.resolve()
    digest = hashlib.sha256()
    candidates: list[Path] = []
    for relative in ("scripts", "references", "vendor"):
        directory = root / relative
        if directory.is_dir():
            candidates.extend(path for path in directory.rglob("*") if path.is_file())
    for relative in (
        "requirements.txt",
        "SKILL.md",
        "requirements-runtime.lock",
        "requirements-runtime-build.lock",
    ):
        path = root / relative
        if path.is_file():
            candidates.append(path)
    checked_matrix = (root / "references/matrices/provider-completeness.yaml").resolve()
    for path in sorted(set(candidates), key=lambda item: item.as_posix()):
        if path.resolve() == checked_matrix:
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.parent == root / "scripts":
            if path.name.startswith("test_"):
                continue
            if path.name in MATRIX_FINGERPRINT_EXCLUDED_SCRIPTS:
                continue
        relative = path.resolve().relative_to(root).as_posix()
        payload = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def _runtime_integrity_artifact_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in RUNTIME_INTEGRITY_ARTIFACTS:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"runtime integrity artifact is missing or unsafe: {relative}")
        hashes[relative] = _sha256(path)
    return hashes


def _run_dedicated_provider_audit(
    *,
    module: Any,
    provider_class: type,
    fixture_path: Path,
    expected_system: str,
    expected_identity: tuple[str, str, str],
    known_case_ids: set[str],
    case_categories: Mapping[str, set[str]],
    fixture_case_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    qualifying_case_ids: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Observe real provider calls independently of the dedicated report fields."""

    observed: list[dict[str, Any]] = []
    observed_extensions: list[dict[str, Any]] = []
    findings: list[str] = []
    provider_name = provider_class.__name__
    original_calculate = provider_class.calculate
    original_extend = getattr(provider_class, "extend", None)
    original_result_create = CalculationResult.create
    original_extension_create = FactExtensionResult.create
    calculations_by_object_id: dict[int, Any] = {}
    extended_results_by_object_id: dict[int, list[CalculationResult]] = {}
    cases_by_calculation_object: dict[int, list[str]] = {}
    request_digest_by_calculation_object: dict[int, str] = {}
    created_results: list[
        tuple[CalculationResult, dict[str, Any], str, str]
    ] = []
    created_extensions: list[FactExtensionResult] = []

    def active_case_ids(request: ReadingRequest) -> list[str]:
        query = str(request.query or "")
        query_matches = sorted(
            (
                case_id
                for case_id in known_case_ids
                if query == case_id or query.endswith(f" {case_id}")
            ),
            key=len,
            reverse=True,
        )
        if query_matches:
            return [query_matches[0]]
        return []

    def calculation_request_digest(request: ReadingRequest) -> str:
        return canonical_digest(
            _semantic_audit_payload(request.to_dict(), top_level=True)
        )

    def provider_input_payload_digest(payload: Mapping[str, Any]) -> str:
        normalized = _semantic_audit_payload(payload, top_level=True)
        return canonical_digest(normalized)

    def observed_result_create(cls: type, **kwargs: Any) -> CalculationResult:
        del cls
        result = original_result_create(**kwargs)
        input_payload = kwargs.get("input_payload")
        if isinstance(input_payload, Mapping):
            captured_payload = copy.deepcopy(dict(input_payload))
            created_results.append(
                (
                    result,
                    captured_payload,
                    canonical_digest(captured_payload),
                    provider_input_payload_digest(captured_payload),
                )
            )
        return result

    def observed_extension_create(
        cls: type,
        **kwargs: Any,
    ) -> FactExtensionResult:
        del cls
        extension = original_extension_create(**kwargs)
        created_extensions.append(extension)
        return extension

    def observed_calculate(self: Any, request: ReadingRequest) -> Any:
        case_ids = active_case_ids(request)
        semantic_request = _semantic_audit_payload(
            request.to_dict(),
            top_level=True,
        )
        captured_semantic_payload: dict[str, Any] | None = None
        request_digest = canonical_digest(request.to_dict())
        effective_request_digest = calculation_request_digest(request)
        capture_start = len(created_results)
        try:
            result = original_calculate(self, request)
        except Exception as exc:
            observed.append(
                {
                    "outcome": "rejection",
                    "system": expected_system,
                    "provider_id": expected_identity[1],
                    "provider_version": expected_identity[2],
                    "request_digest": request_digest,
                    "calculation_request_digest": effective_request_digest,
                    "exception_type": type(exc).__name__,
                    "exception_digest": canonical_digest(
                        {"type": type(exc).__name__, "message": str(exc)}
                    ),
                    "case_ids": case_ids,
                    "calculation_object_id": None,
                    "semantic_request": semantic_request,
                    "provider_input_payload": None,
                }
            )
            raise
        captures = created_results[capture_start:]
        provider_input_digest = ""
        if len(captures) != 1:
            findings.append(
                "provider calculation must create exactly one captured result"
            )
        else:
            captured_result, captured_payload, raw_input_digest, semantic_digest = (
                captures[0]
            )
            captured_semantic_payload = _semantic_audit_payload(
                captured_payload,
                top_level=True,
            )
            if raw_input_digest != str(result.input_hash):
                findings.append(
                    "provider returned input hash does not match its captured input payload"
                )
            elif captured_result is not result:
                findings.append(
                    "provider returned a different result than its captured input result"
                )
            elif not _declared_input_digests_have_preimages(captured_payload):
                findings.append(
                    "provider input_digest has no captured semantic preimage"
                )
            else:
                try:
                    CalculationResult.from_dict(result.to_dict())
                except (KeyError, TypeError, ValueError):
                    findings.append(
                        "provider returned a calculation with invalid artifact digests"
                    )
                else:
                    provider_input_digest = semantic_digest
        object_id = id(result)
        observed.append(
            {
                "outcome": "success",
                "system": str(result.system),
                "input_hash": str(result.input_hash),
                "result_hash": str(result.result_hash),
                "provider_id": str(result.provider_id),
                "provider_version": str(result.provider_version),
                "request_digest": request_digest,
                "calculation_request_digest": effective_request_digest,
                "provider_input_payload_digest": provider_input_digest,
                "facts_digest": canonical_digest(result.facts),
                "case_ids": case_ids,
                "calculation_object_id": object_id,
                "semantic_request": semantic_request,
                "provider_input_payload": captured_semantic_payload,
            }
        )
        calculations_by_object_id[object_id] = result
        cases_by_calculation_object[object_id] = list(case_ids)
        request_digest_by_calculation_object[object_id] = provider_input_digest
        return result

    def observed_extend(
        self: Any,
        calculation: Any,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
    ) -> Any:
        assert original_extend is not None
        object_id = id(calculation)
        base_request_digest = request_digest_by_calculation_object.get(object_id)
        if (
            calculations_by_object_id.get(object_id) is not calculation
            or not base_request_digest
        ):
            # Restart/replay lifecycle probes can rehydrate a calculation that
            # was not returned by this route observer.  Their extension belongs
            # to the lifecycle audit, not to a route-owned replay.
            return original_extend(
                self, calculation, requested_dimensions, horizon
            )
        extension_request_digest = canonical_digest(
            {
                "base_provider_input_payload_digest": base_request_digest or "",
                "requested_dimensions": list(requested_dimensions),
                "horizon": _semantic_audit_payload(horizon),
            }
        )
        semantic_extension_request_digest = canonical_digest(
            {
                "requested_dimensions": list(requested_dimensions),
                "horizon": _semantic_audit_payload(horizon),
            }
        )
        case_ids = list(cases_by_calculation_object.get(object_id, ()))
        semantic_horizon = _semantic_audit_payload(horizon)
        extension_capture_start = len(created_extensions)
        try:
            result = original_extend(
                self, calculation, requested_dimensions, horizon
            )
        except Exception as exc:
            observed_extensions.append(
                {
                    "case_ids": case_ids,
                    "outcome": "rejection",
                    "extension_request_digest": extension_request_digest,
                    "semantic_extension_request_digest": (
                        semantic_extension_request_digest
                    ),
                    "calculation_object_id": object_id,
                    "semantic_horizon": semantic_horizon,
                    "requested_dimensions": tuple(requested_dimensions),
                    "exception_digest": canonical_digest(
                        {"type": type(exc).__name__, "message": str(exc)}
                    ),
                }
            )
            raise
        extension = (
            result.fact_extension
            if isinstance(result, CalculationResult)
            else None
        )
        extension_captures = created_extensions[extension_capture_start:]
        try:
            if not isinstance(result, CalculationResult):
                raise TypeError("extension did not return a calculation")
            CalculationResult.from_dict(result.to_dict())
            if len(extension_captures) != 1:
                raise ValueError(
                    "provider extension must create exactly one extension artifact"
                )
            if extension_captures[0] is not extension:
                raise ValueError(
                    "provider returned a different extension than it created"
                )
            capability = PROVIDER_CAPABILITIES[expected_system]
            horizon_kind = str(horizon.get("kind") or "")
            extension_request_allowed = (
                set(requested_dimensions).issubset(capability.dimensions)
                and horizon_kind in capability.horizons
                and _horizon_is_valid(horizon, system=expected_system)
            )
            extension_status_ready = _extension_status_is_ready(
                extension,
                capability=capability,
                requested_dimensions=requested_dimensions,
            )
            usable = (
                extension_request_allowed
                and extension is not None
                and extension_status_ready
                and extension.system == expected_system
                and extension.base_calculation_digest
                == calculation.base().result_hash
                and extension.requested_dimensions == requested_dimensions
                and extension.horizon == horizon
                and result.result_hash == calculation.base().result_hash
                and result.provider_id == calculation.provider_id
                and result.provider_version == calculation.provider_version
            )
        except (KeyError, TypeError, ValueError):
            usable = False
        observed_extensions.append(
            {
                "case_ids": case_ids,
                "outcome": "success" if usable else "non_calculated",
                "extension_request_digest": extension_request_digest,
                "semantic_extension_request_digest": (
                    semantic_extension_request_digest
                ),
                "extension_result_digest": (
                    extension.extension_digest if usable else ""
                ),
                "calculation_object_id": object_id,
                "semantic_horizon": semantic_horizon,
                "requested_dimensions": tuple(requested_dimensions),
            }
        )
        if usable:
            extended_results_by_object_id.setdefault(object_id, []).append(result)
        return result

    def extension_replay_contract(
        case_id: str,
    ) -> tuple[list[str], list[str], bool]:
        calls = [
            call for call in observed_extensions if case_id in call["case_ids"]
        ]
        if not calls:
            binding = (fixture_case_bindings or {}).get(case_id) or {}
            return (
                [],
                [],
                not bool(binding.get("extension_projection")),
            )
        request_digests = sorted(
            {str(call["extension_request_digest"]) for call in calls}
        )
        result_digests: list[str] = []
        calculation_object_ids = {
            call.get("calculation_object_id")
            for call in observed
            if call.get("outcome") == "success"
            and case_id in call.get("case_ids", ())
            and call.get("calculation_object_id") is not None
        }
        ready = len(request_digests) == 1 and len(calculation_object_ids) >= 2
        for request_digest in request_digests:
            replay = [
                call
                for call in calls
                if call["extension_request_digest"] == request_digest
            ]
            replay_results = sorted(
                {
                    str(call.get("extension_result_digest") or "")
                    for call in replay
                    if call.get("outcome") == "success"
                    and call.get("extension_result_digest")
                }
            )
            result_digests.extend(replay_results)
            replay_object_ids = {
                call.get("calculation_object_id")
                for call in replay
                if call.get("calculation_object_id") is not None
            }
            if (
                len(replay) < 2
                or replay_object_ids != calculation_object_ids
                or {call.get("outcome") for call in replay} != {"success"}
                or len(replay_results) != 1
            ):
                ready = False
        return request_digests, sorted(set(result_digests)), ready

    def extension_semantic_request_digests(case_id: str) -> list[str]:
        return sorted(
            {
                str(call.get("semantic_extension_request_digest") or "")
                for call in observed_extensions
                if case_id in call.get("case_ids", ())
                and call.get("outcome") == "success"
                and call.get("semantic_extension_request_digest")
            }
        )

    def extension_horizon_kinds(case_id: str) -> list[str]:
        return sorted(
            {
                str((call.get("semantic_horizon") or {}).get("kind") or "")
                for call in observed_extensions
                if case_id in call.get("case_ids", ())
                and call.get("outcome") == "success"
                and isinstance(call.get("semantic_horizon"), Mapping)
                and str((call.get("semantic_horizon") or {}).get("kind") or "")
            }
        )

    def calls_are_fixture_bound(
        case_id: str,
        calls: Sequence[Mapping[str, Any]],
    ) -> bool:
        if not calls:
            return False
        if fixture_case_bindings is None:
            return True
        binding = fixture_case_bindings.get(case_id)
        if not isinstance(binding, Mapping):
            return False
        if binding.get("unconsumed_semantic_leaves"):
            return False
        calculation_projection = binding.get("calculation_projection") or {}
        extension_projection = binding.get("extension_projection") or {}
        if not calculation_projection and not extension_projection:
            return False
        semantic_requests = [call.get("semantic_request") for call in calls]
        if any(request != semantic_requests[0] for request in semantic_requests[1:]):
            return False
        if calculation_projection and not all(
            _payload_contains_projection(request, calculation_projection)
            for request in semantic_requests
        ):
            return False
        successful_calls = [
            call for call in calls if call.get("outcome") == "success"
        ]
        if calculation_projection and successful_calls and not all(
            _payload_commits_structured_projection(
                call.get("provider_input_payload"), calculation_projection
            )
            for call in successful_calls
        ):
            return False
        calculation_object_ids = {
            call.get("calculation_object_id")
            for call in calls
            if call.get("calculation_object_id") is not None
        }
        extension_calls = [
            extension_call
            for extension_call in observed_extensions
            if extension_call.get("calculation_object_id")
            in calculation_object_ids
            and case_id in extension_call.get("case_ids", ())
        ]
        matching_extension_requests: set[str] = set()
        for extension_call in extension_calls:
            request_digest = str(
                extension_call.get("extension_request_digest") or ""
            )
            if (
                request_digest
                and extension_call.get("outcome") == "success"
                and _payload_contains_projection(
                    extension_call.get("semantic_horizon"),
                    extension_projection,
                )
            ):
                matching_extension_requests.add(request_digest)
        return not extension_projection or bool(matching_extension_requests)

    if getattr(module, provider_name, None) is not provider_class:
        report = {
            "schema_version": "dedicated-audit-observer-error",
            "provider_ready": False,
            "status": "fail",
            "counts": {},
            "findings": [f"dedicated module does not expose {provider_name}"],
        }
        findings.extend(report["findings"])
    else:
        audit_function = getattr(module, module.__name__)
        try:
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    mock.patch.object(
                        CalculationResult,
                        "create",
                        classmethod(observed_result_create),
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        FactExtensionResult,
                        "create",
                        classmethod(observed_extension_create),
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        provider_class,
                        "calculate",
                        observed_calculate,
                    )
                )
                if callable(original_extend):
                    stack.enter_context(
                        mock.patch.object(
                            provider_class,
                            "extend",
                            observed_extend,
                        )
                    )
                report = audit_function(fixture_path=fixture_path)
        except Exception as exc:
            report = {
                "schema_version": "dedicated-audit-exception",
                "provider_ready": False,
                "status": "fail",
                "counts": {},
                "findings": [f"{type(exc).__name__}: {exc}"],
            }
    grouped: dict[str, list[str]] = {}
    for call in observed:
        if call["outcome"] != "success":
            continue
        grouped.setdefault(call["input_hash"], []).append(call["result_hash"])
    deterministic_replays = sum(
        1
        for results in grouped.values()
        if len(results) >= 2 and len(set(results)) == 1
    )
    expected_class, expected_id, expected_version = expected_identity
    observed_class = f"{provider_class.__module__}.{provider_class.__qualname__}"
    provider_identity_matches = (
        any(call["outcome"] == "success" for call in observed)
        and observed_class == expected_class
        and all(
            call["system"] == expected_system
            and call["provider_id"] == expected_id
            and call["provider_version"] == expected_version
            for call in observed
        )
    )
    if not observed:
        findings.append("dedicated audit made no observable provider calculations")
    if not provider_identity_matches:
        findings.append("observed dedicated provider identity mismatch")
    route_case_ids = [str(item) for item in report.get("route_owned_case_ids") or ()]
    route_case_id_set = set(route_case_ids)
    case_ids_fixture_bound = (
        bool(route_case_ids)
        and len(route_case_id_set) == len(route_case_ids)
        and route_case_id_set.issubset(known_case_ids)
        and (
            qualifying_case_ids is None
            or route_case_id_set == set(qualifying_case_ids)
        )
    )
    if not case_ids_fixture_bound:
        findings.append("route-owned case ids are not fixture-bound")
    case_replays: list[dict[str, Any]] = []
    for case_id in route_case_ids:
        calls = [
            call
            for call in observed
            if call["outcome"] == "success" and case_id in call["case_ids"]
        ]
        input_hashes = sorted({call["input_hash"] for call in calls})
        result_hashes = sorted({call["result_hash"] for call in calls})
        request_digests = sorted({call["request_digest"] for call in calls})
        calculation_request_digests = sorted(
            {call["calculation_request_digest"] for call in calls}
        )
        provider_input_payload_digests = sorted(
            {
                call["provider_input_payload_digest"]
                for call in calls
                if call["provider_input_payload_digest"]
            }
        )
        facts_digests = sorted({call["facts_digest"] for call in calls})
        fixture_input_bound = calls_are_fixture_bound(case_id, calls)
        fixture_identity_digest = str(
            ((fixture_case_bindings or {}).get(case_id) or {}).get(
                "identity_digest"
            )
            or ""
        )
        fixture_semantic_digest = (
            canonical_digest(
                {
                    "calculation_projection": (
                        ((fixture_case_bindings or {}).get(case_id) or {}).get(
                            "calculation_projection"
                        )
                        or {}
                    ),
                    "extension_projection": (
                        ((fixture_case_bindings or {}).get(case_id) or {}).get(
                            "extension_projection"
                        )
                        or {}
                    ),
                }
            )
            if fixture_case_bindings is not None
            else ""
        )
        (
            extension_request_digests,
            extension_result_digests,
            extension_replay_ready,
        ) = extension_replay_contract(case_id)
        semantic_extension_request_digests = (
            extension_semantic_request_digests(case_id)
        )
        effective_case_digest = (
            (
                canonical_digest(
                    {
                        "fixture_semantic_digest": fixture_semantic_digest,
                        "semantic_extension_request_digests": (
                            semantic_extension_request_digests
                        ),
                    }
                )
                if fixture_semantic_digest
                else canonical_digest(
                    {
                        "calculation_request_digest": calculation_request_digests[0],
                        "semantic_extension_request_digests": (
                            semantic_extension_request_digests
                        ),
                    }
                )
            )
            if len(calculation_request_digests) == 1
            and len(provider_input_payload_digests) == 1
            and extension_replay_ready
            and fixture_input_bound
            and (fixture_case_bindings is None or fixture_identity_digest)
            else ""
        )
        case_replays.append(
            {
                "case_id": case_id,
                "calls": len(calls),
                "input_hashes": input_hashes,
                "result_hashes": result_hashes,
                "request_digests": request_digests,
                "calculation_request_digests": calculation_request_digests,
                "provider_input_payload_digests": provider_input_payload_digests,
                "facts_digests": facts_digests,
                "fixture_input_bound": fixture_input_bound,
                "fixture_identity_digest": fixture_identity_digest,
                "extension_request_digests": extension_request_digests,
                "semantic_extension_request_digests": (
                    semantic_extension_request_digests
                ),
                "extension_horizon_kinds": extension_horizon_kinds(case_id),
                "extension_result_digests": extension_result_digests,
                "extension_replay_ready": extension_replay_ready,
                "effective_case_digest": effective_case_digest,
                "ready": len(calls) >= 2
                and len(request_digests) == 1
                and len(calculation_request_digests) == 1
                and len(provider_input_payload_digests) == 1
                and len(input_hashes) == 1
                and len(result_hashes) == 1
                and len(facts_digests) == 1
                and fixture_input_bound
                and extension_replay_ready,
            }
        )
    distinct_route_request_digests = {
        digest for row in case_replays for digest in row["request_digests"]
    }
    distinct_calculation_request_digests = {
        digest
        for row in case_replays
        for digest in row["calculation_request_digests"]
    }
    distinct_provider_input_payload_digests = {
        digest
        for row in case_replays
        for digest in row["provider_input_payload_digests"]
    }
    distinct_effective_case_digests = {
        row["effective_case_digest"]
        for row in case_replays
        if row["ready"] and row["effective_case_digest"]
    }
    case_replay_ready = (
        case_ids_fixture_bound
        and all(row["ready"] for row in case_replays)
        and len(distinct_route_request_digests) == len(route_case_ids)
        and (
            fixture_case_bindings is not None
            or len(distinct_calculation_request_digests) == len(route_case_ids)
        )
        and len(distinct_effective_case_digests) == len(route_case_ids)
    )
    if any(not row["fixture_input_bound"] for row in case_replays):
        findings.append(
            "route-owned replay provider input is not bound to fixture semantic input"
        )
    if not case_replay_ready:
        findings.append("route-owned case ids are not bound to deterministic provider replays")
    observed_case_ids = sorted(
        {
            case_id
            for call in observed
            for case_id in call["case_ids"]
            if case_id in case_categories
        }
    )
    provider_boundary_replays: list[dict[str, Any]] = []
    for case_id in observed_case_ids:
        calls = [call for call in observed if case_id in call["case_ids"]]
        fixture_input_bound = calls_are_fixture_bound(case_id, calls)
        fixture_identity_digest = str(
            ((fixture_case_bindings or {}).get(case_id) or {}).get(
                "identity_digest"
            )
            or ""
        )
        fixture_semantic_digest = (
            canonical_digest(
                {
                    "calculation_projection": (
                        ((fixture_case_bindings or {}).get(case_id) or {}).get(
                            "calculation_projection"
                        )
                        or {}
                    ),
                    "extension_projection": (
                        ((fixture_case_bindings or {}).get(case_id) or {}).get(
                            "extension_projection"
                        )
                        or {}
                    ),
                }
            )
            if fixture_case_bindings is not None
            else ""
        )
        outcomes = sorted({call["outcome"] for call in calls})
        request_digests = sorted({call["request_digest"] for call in calls})
        calculation_request_digests = sorted(
            {call["calculation_request_digest"] for call in calls}
        )
        provider_input_payload_digests = sorted(
            {
                call["provider_input_payload_digest"]
                for call in calls
                if call.get("provider_input_payload_digest")
            }
        )
        (
            extension_request_digests,
            extension_result_digests,
            extension_replay_ready,
        ) = extension_replay_contract(case_id)
        semantic_extension_request_digests = (
            extension_semantic_request_digests(case_id)
        )
        effective_case_digest = (
            (
                canonical_digest(
                    {
                        "fixture_semantic_digest": fixture_semantic_digest,
                        "semantic_extension_request_digests": (
                            semantic_extension_request_digests
                        ),
                    }
                )
                if fixture_semantic_digest
                else canonical_digest(
                    {
                        "calculation_request_digest": calculation_request_digests[0],
                        "semantic_extension_request_digests": (
                            semantic_extension_request_digests
                        ),
                    }
                )
            )
            if len(calculation_request_digests) == 1
            and extension_replay_ready
            and fixture_input_bound
            else ""
        )
        input_hashes = sorted(
            {call["input_hash"] for call in calls if call["outcome"] == "success"}
        )
        result_hashes = sorted(
            {call["result_hash"] for call in calls if call["outcome"] == "success"}
        )
        exception_digests = sorted(
            {
                call["exception_digest"]
                for call in calls
                if call["outcome"] == "rejection"
            }
        )
        ready = (
            len(calls) >= 2
            and len(outcomes) == 1
            and len(request_digests) == 1
            and fixture_input_bound
        )
        ready = ready and len(calculation_request_digests) == 1
        if outcomes == ["success"]:
            ready = (
                ready
                and len(provider_input_payload_digests) == 1
                and len(input_hashes) == 1
                and len(result_hashes) == 1
                and extension_replay_ready
            )
        elif outcomes == ["rejection"]:
            ready = ready and len(exception_digests) == 1
        else:
            ready = False
        provider_boundary_replays.append(
            {
                "case_id": case_id,
                "categories": sorted(case_categories[case_id]),
                "calls": len(calls),
                "outcome": outcomes[0] if len(outcomes) == 1 else "mixed",
                "request_digests": request_digests,
                "calculation_request_digests": calculation_request_digests,
                "provider_input_payload_digests": provider_input_payload_digests,
                "extension_request_digests": extension_request_digests,
                "semantic_extension_request_digests": (
                    semantic_extension_request_digests
                ),
                "extension_horizon_kinds": extension_horizon_kinds(case_id),
                "extension_result_digests": extension_result_digests,
                "extension_replay_ready": extension_replay_ready,
                "effective_case_digest": effective_case_digest,
                "input_hashes": input_hashes,
                "result_hashes": result_hashes,
                "exception_digests": exception_digests,
                "fixture_input_bound": fixture_input_bound,
                "fixture_identity_digest": fixture_identity_digest,
                "ready": ready,
            }
        )
    successful_boundary_replays = [
        row for row in provider_boundary_replays if row["outcome"] == "success"
    ]
    ready_rejection_replays = [
        row
        for row in provider_boundary_replays
        if row["outcome"] == "rejection" and row["ready"]
    ]
    distinct_rejection_semantic_digests = {
        digest
        for row in ready_rejection_replays
        for digest in row["calculation_request_digests"]
    }
    rejection_semantics_are_distinct = (
        len(distinct_rejection_semantic_digests)
        == len(ready_rejection_replays)
    )
    ready_boundary_candidates = [
        row for row in successful_boundary_replays if row["ready"]
    ]
    ready_boundary_rows = [
        copy.deepcopy(row)
        for row in sorted(
            ready_boundary_candidates,
            key=lambda item: (
                item["case_id"] not in set(route_case_ids),
                item["case_id"],
            ),
        )
    ]
    distinct_boundary_request_digests = {
        digest for row in ready_boundary_rows for digest in row["request_digests"]
    }
    distinct_boundary_calculation_request_digests = {
        digest
        for row in ready_boundary_rows
        for digest in row["calculation_request_digests"]
    }
    distinct_boundary_effective_case_digests = {
        row["effective_case_digest"]
        for row in ready_boundary_rows
        if row["effective_case_digest"]
    }
    provider_boundary_categories = sorted(
        {
            category
            for row in ready_boundary_rows
            for category in row["categories"]
        }
    )
    if rejection_semantics_are_distinct:
        provider_boundary_categories = sorted(
            set(provider_boundary_categories)
            | {
                category
                for row in ready_rejection_replays
                for category in row["categories"]
            }
        )
    provider_boundary_replay_ready = (
        bool(ready_boundary_rows)
        and all(row["ready"] for row in provider_boundary_replays)
        and rejection_semantics_are_distinct
        and len(distinct_boundary_request_digests) == len(ready_boundary_rows)
        and len(distinct_boundary_effective_case_digests)
        == len(ready_boundary_rows)
    )
    if not provider_boundary_replay_ready:
        findings.append("no fixture-categorized provider boundary replay was observed")
    fixture_boundary_categories = sorted(
        {category for names in case_categories.values() for category in names}
    )
    fixture_source_replays: list[dict[str, Any]] = []
    source_capability = PROVIDER_CAPABILITIES.get(expected_system)
    source_goal = {
        "evidence_questions": ["Task 7N fixture source applicability proof"],
        "question_dimensions": list(source_capability.dimensions)
        if source_capability is not None
        else [],
        "requested_dimensions": list(source_capability.dimensions)
        if source_capability is not None
        else [],
        "calculation_object": source_capability.objects[0]
        if source_capability is not None
        else "synthetic_test_object",
    }
    for row in case_replays:
        if row.get("ready") is not True:
            continue
        case_id = str(row["case_id"])
        object_ids = {
            int(call["calculation_object_id"])
            for call in observed
            if call.get("outcome") == "success"
            and case_id in call.get("case_ids", ())
            and call.get("calculation_object_id") is not None
        }
        for object_id in sorted(object_ids):
            base = calculations_by_object_id.get(object_id)
            calculations = [
                *extended_results_by_object_id.get(object_id, ()),
                *([base] if isinstance(base, CalculationResult) else []),
            ]
            for calculation in calculations:
                try:
                    source_plan = reading_source_plan.compile_source_plan(
                        expected_system,
                        source_goal,
                        calculation.facts,
                    )
                    required_source_packs = list(
                        source_plan.get("required_packs") or ()
                    )
                    source_fact_index = build_fact_index(
                        calculation,
                        reading_id="7" * 32,
                        version=1,
                    )
                    eligible_groups = reading_evidence_bundle._eligible_rules(
                        source_plan,
                        source_fact_index,
                    )
                    runtime_enabled_rule_ids = sorted(
                        {
                            rule.rule_id
                            for entries in eligible_groups.values()
                            for rule, _fact_refs, _audit in entries
                        }
                    )
                except (KeyError, TypeError, ValueError):
                    required_source_packs = []
                    runtime_enabled_rule_ids = []
                fixture_source_replays.append(
                    {
                        "case_id": case_id,
                        "fixture_input_bound": row["fixture_input_bound"] is True,
                        "ready": True,
                        "calculation": calculation,
                        "required_source_packs": required_source_packs,
                        "runtime_enabled_rule_ids": runtime_enabled_rule_ids,
                    }
                )
    source_pack_replay = audit_source_applicability(
        expected_system,
        root=ROOT,
        fixture_replays=fixture_source_replays,
    )
    telemetry = {
        "schema_version": "mingli-dedicated-runtime-replay-audit-v2",
        "calculation_runs": len(observed),
        "distinct_input_hashes": len(grouped),
        "deterministic_input_replays": deterministic_replays,
        "provider_identity_matches": provider_identity_matches,
        "case_ids_fixture_bound": case_ids_fixture_bound,
        "case_replay_count": sum(1 for row in case_replays if row["ready"]),
        "distinct_route_request_digests": len(distinct_route_request_digests),
        "distinct_calculation_request_digests": len(
            distinct_calculation_request_digests
        ),
        "calculation_request_cases_are_distinct": (
            len(distinct_calculation_request_digests) == len(route_case_ids)
        ),
        "distinct_provider_input_payload_digests": len(
            distinct_provider_input_payload_digests
        ),
        "provider_input_payloads_are_distinct": (
            len(distinct_provider_input_payload_digests) == len(route_case_ids)
        ),
        "distinct_effective_case_digests": len(distinct_effective_case_digests),
        "effective_cases_are_distinct": (
            len(distinct_effective_case_digests) == len(route_case_ids)
        ),
        "case_replay_ready": case_replay_ready,
        "case_replays": case_replays,
        "provider_boundary_case_count": len(ready_boundary_rows),
        "provider_boundary_rejection_case_count": sum(
            1 for _row in ready_rejection_replays
        )
        if rejection_semantics_are_distinct
        else 0,
        "rejection_semantics_are_distinct": rejection_semantics_are_distinct,
        "distinct_boundary_request_digests": len(
            distinct_boundary_request_digests
        ),
        "distinct_boundary_calculation_request_digests": len(
            distinct_boundary_calculation_request_digests
        ),
        "distinct_boundary_effective_case_digests": len(
            distinct_boundary_effective_case_digests
        ),
        "provider_boundary_categories": provider_boundary_categories,
        "fixture_boundary_categories": fixture_boundary_categories,
        "provider_boundary_replay_ready": provider_boundary_replay_ready,
        "provider_boundary_replays": provider_boundary_replays,
        "source_pack_replay": source_pack_replay,
        "findings": findings,
    }
    return report, telemetry


def _build_matrix_uncached(
    root_text: str,
    input_fingerprint: str,
    systems: Sequence[str] | None = None,
) -> dict[str, Any]:
    root = Path(root_text).resolve()
    if root != ROOT.resolve():
        raise ValueError(
            "detached provider matrix audits require an isolated subprocess "
            "with that root's scripts on PYTHONPATH"
        )
    current_fingerprint = _matrix_input_fingerprint(root)
    if input_fingerprint != current_fingerprint:
        raise ValueError("provider matrix input fingerprint is stale")
    algorithm_manifest_path = (
        root / "references" / "matrices" / "algorithm-source-dependencies.yaml"
    )
    algorithm_manifest = yaml.safe_load(
        algorithm_manifest_path.read_text(encoding="utf-8")
    )
    global_algorithm_audit = audit_algorithm_sources.audit_matrix(
        algorithm_manifest,
        root=root,
        systems=EXPECTED_SYSTEMS,
    )
    algorithm_manifest_sha256 = _sha256(algorithm_manifest_path)
    selected_systems = EXPECTED_SYSTEMS if systems is None else tuple(systems)
    providers: dict[str, Any] = {}
    for system in selected_systems:
        capability = PROVIDER_CAPABILITIES[system]
        threshold = 20 if capability.mode == "observation_driven_ready" else 30
        module = DEDICATED_AUDIT_MODULES[system]
        fixture_relative = Path(module.FIXTURE).relative_to(ROOT)
        fixture_path = root / fixture_relative
        fixture_payload = _load_yaml(fixture_path)
        fixture_case_bindings = _fixture_case_bindings(
            fixture_payload,
            system=system,
        )
        for case_id, binding in _module_fixture_case_bindings(
            module,
            root=root,
            system=system,
        ).items():
            existing = fixture_case_bindings.get(case_id)
            if existing is not None and existing != binding:
                raise ValueError(
                    f"conflicting fixture semantic binding: {system}/{case_id}"
                )
            fixture_case_bindings[case_id] = binding
        fixture_declared_ids = _fixture_case_ids(fixture_payload)
        fixture_declared_ids.update(
            _module_fixture_case_ids(module, root=root)
        )
        fixture_case_categories = _fixture_case_categories(fixture_payload)
        for case_id, names in _module_fixture_case_categories(
            module,
            root=root,
        ).items():
            fixture_case_categories.setdefault(case_id, set()).update(names)
        fixture_case_categories = _fixture_case_category_aliases(
            fixture_case_categories
        )
        fixture_declared_ids = _fixture_case_id_aliases(fixture_declared_ids)
        if system == "luming-nayin":
            fixture_declared_ids.update(
                f"nayin-cycle-{ganzhi}" for ganzhi in luming.JIAZI
            )
        report, dedicated_runtime_replay = _run_dedicated_provider_audit(
            module=module,
            provider_class=PROVIDER_CLASSES[system],
            fixture_path=fixture_path,
            expected_system=system,
            expected_identity=EXPECTED_PROVIDER_IDENTITIES[system],
            known_case_ids=fixture_declared_ids,
            case_categories=fixture_case_categories,
            fixture_case_bindings=fixture_case_bindings,
        )
        # Only matrix builds publish session reports.  Direct calls from
        # mutation-contract tests exercise the observer with stub providers
        # and must never leak synthetic reports into a shared test session.
        audit_test_session.publish_report(system, report)
        counts = report.get("counts") or {}
        if not isinstance(counts, Mapping):
            counts = {}
        count_key, qualifying_cases = _first_count(
            counts,
            "qualifying_provider_cases",
            "qualifying_cases",
        )
        route_count_key, route_owned_cases = _first_count(
            counts,
            "route_owned_cases",
        )
        fixture_sha256 = _sha256(fixture_path)
        report_fixture = report.get("fixture") or {}
        fixture_artifacts = report.get("fixture_artifacts") or {}
        reported_sha256 = (
            report_fixture.get("sha256")
            if isinstance(report_fixture, Mapping)
            else None
        ) or (
            fixture_artifacts.get("route_fixture_sha256")
            if isinstance(fixture_artifacts, Mapping)
            else None
        ) or report.get("fixture_sha256")
        report_expected_sha256 = (
            report_fixture.get("expected_sha256")
            if isinstance(report_fixture, Mapping)
            else None
        ) or (
            fixture_artifacts.get("expected_route_fixture_sha256")
            if isinstance(fixture_artifacts, Mapping)
            else None
        )
        expected_sha256 = getattr(
            module,
            "EXPECTED_FIXTURE_SHA256",
            getattr(module, "FIXTURE_SHA256", None),
        )
        dedicated_hash_matches = (
            isinstance(reported_sha256, str)
            and reported_sha256 == fixture_sha256
            and isinstance(expected_sha256, str)
            and expected_sha256 == fixture_sha256
            and (
                report_expected_sha256 is None
                or report_expected_sha256 == expected_sha256
            )
        )
        route_owned_case_ids = report.get("route_owned_case_ids") or ()
        if not isinstance(route_owned_case_ids, Sequence) or isinstance(
            route_owned_case_ids, (str, bytes, bytearray)
        ):
            route_owned_case_ids = ()
        normalized_route_ids = [str(item) for item in route_owned_case_ids]
        live_contract = audit_live_provider_contract(system, root=root)
        source_applicability = dedicated_runtime_replay.get("source_pack_replay") or {
            "schema_version": "mingli-provider-source-pack-replay-audit-v1",
            "system": system,
            "required_always": [],
            "required_when_active_subprofile": {},
            "comparison_only": [],
            "accepted_fixture_replay_count": 0,
            "accepted_fixture_case_ids": [],
            "packs": {},
            "ready": False,
            "findings": [f"{system}: fixture source replay telemetry is missing"],
        }
        transaction_lifecycle = (
            audit_liuyao_transaction_lifecycle(root=root)
            if system == "liuyao"
            else {}
        )
        entry: dict[str, Any] = {
            "declaration": capability.to_dict(),
            "runtime": _provider_runtime(system),
            "fixtures": {
                "path": fixture_relative.as_posix(),
                "sha256": fixture_sha256,
                "dedicated_reported_sha256": (
                    str(reported_sha256) if reported_sha256 is not None else None
                ),
                "dedicated_expected_sha256": (
                    str(expected_sha256) if expected_sha256 is not None else None
                ),
                "dedicated_report_expected_sha256": (
                    str(report_expected_sha256)
                    if report_expected_sha256 is not None
                    else None
                ),
                "dedicated_hash_matches": dedicated_hash_matches,
                "qualifying_layer": "complete_provider_result",
                "qualifying_count_key": count_key,
                "qualifying_cases": qualifying_cases,
                "route_owned_count_key": route_count_key,
                "route_owned_cases": route_owned_cases,
                "distinct_route_owned_cases": len(
                    set(normalized_route_ids)
                ),
                "route_owned_case_ids": normalized_route_ids,
                "route_owned_ids_match_fixture": bool(normalized_route_ids)
                and set(normalized_route_ids).issubset(fixture_declared_ids),
                "minimum_cases": threshold,
                "boundary_categories": _boundary_categories(report),
                "boundary_case_count": int(counts.get("boundary_case_count") or 0),
            },
            "algorithm": _algorithm_summary(
                system,
                manifest=algorithm_manifest,
                manifest_sha256=algorithm_manifest_sha256,
                global_audit=global_algorithm_audit,
                reported_counts=counts,
                live_dependencies=capability.algorithm_dependencies,
                runtime_identity=(
                    report.get("calendar_identity")
                    if isinstance(report.get("calendar_identity"), Mapping)
                    else None
                ),
            ),
            "dedicated_audit": _dedicated_audit_projection(report),
            "dedicated_runtime_replay": _plain(dedicated_runtime_replay),
            "live_contract": _plain(live_contract),
            "source_applicability": _plain(source_applicability),
            "transaction_lifecycle": _plain(transaction_lifecycle),
        }
        entry["boundary_proof_summary"] = _boundary_proof_summary(
            system,
            declared_categories=entry["fixtures"]["boundary_categories"],
            proof_declarations=_boundary_proof_declarations(
                system,
                entry["fixtures"]["boundary_categories"],
            ),
            dedicated_runtime_replay=entry["dedicated_runtime_replay"],
            dedicated_counts=entry["dedicated_audit"]["counts"],
            algorithm=entry["algorithm"],
            transaction_lifecycle=entry["transaction_lifecycle"],
        )
        readiness_findings = _entry_readiness_findings(system, entry)
        entry["readiness_findings"] = readiness_findings
        entry["ready"] = not readiness_findings
        providers[system] = entry
    matrix = {
        "schema_version": SCHEMA_VERSION,
        "policy": {
            "generated_from_live_declarations_and_audits": True,
            "ready_is_derived": True,
            "generic_provider_forbidden": True,
            "determinism_runs": 2,
            "minimum_calculation_fixtures": 30,
            "minimum_observation_fixtures": 20,
            "unbound_evidence_rules_fail_closed": True,
            "mandatory_source_packs_proved_individually": True,
            "source_predicates_mutation_replayed": True,
            "research_sources_verified": bool(
                global_algorithm_audit.get("research_sources_verified")
            ),
            "runtime_preimport_integrity_required": True,
            "hash_locked_runtime_required": True,
        },
        "inputs": {
            "generator_input_fingerprint": input_fingerprint,
            "algorithm_source_manifest_sha256": algorithm_manifest_sha256,
            "evidence_index_sha256": _sha256(
                root / "references" / "index" / "evidence-rules.jsonl"
            ),
            "evidence_scope_bindings_sha256": _sha256(
                root
                / "references"
                / "matrices"
                / "evidence-scope-bindings-v1.yaml"
            ),
            "classical_evidence_bindings_sha256": _sha256(
                root
                / "references"
                / "matrices"
                / "classical-evidence-bindings-v1.json"
            ),
            "runtime_source_families_sha256": _sha256(
                root
                / "references"
                / "matrices"
                / "runtime-source-families-v1.yaml"
            ),
            "runtime_integrity_artifacts": _runtime_integrity_artifact_hashes(root),
        },
        "providers": providers,
    }
    ending_fingerprint = _matrix_input_fingerprint(root)
    if ending_fingerprint != input_fingerprint:
        raise ValueError("provider matrix inputs changed during generation")
    return matrix


def _matrix_jobs(system_count: int) -> int:
    configured = os.environ.get("MINGLI_MATRIX_JOBS")
    if configured is None:
        jobs = min(4, max(1, (os.cpu_count() or 1) - 1))
    else:
        try:
            jobs = int(configured)
        except ValueError as exc:
            raise ValueError("MINGLI_MATRIX_JOBS must be a positive integer") from exc
        if jobs < 1:
            raise ValueError("MINGLI_MATRIX_JOBS must be a positive integer")
    return max(1, min(jobs, max(1, system_count)))


def _build_provider_partition(
    root_text: str,
    input_fingerprint: str,
    system: str,
) -> dict[str, Any]:
    audit_test_session.mark_started(system)
    try:
        return _build_matrix_uncached(
            root_text,
            input_fingerprint,
            systems=(system,),
        )
    except BaseException as exc:
        audit_test_session.mark_failed(system, f"{type(exc).__name__}: {exc}")
        raise


def _merge_provider_partitions(
    systems: Sequence[str],
    partitions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not systems:
        raise ValueError("cannot merge an empty provider partition set")
    first_system = systems[0]
    first = partitions.get(first_system)
    if first is None:
        raise ValueError(f"missing provider partition: {first_system}")
    merged = copy.deepcopy(dict(first))
    providers: dict[str, Any] = {}
    for system in systems:
        partition = partitions.get(system)
        if partition is None:
            raise ValueError(f"missing provider partition: {system}")
        entries = partition.get("providers")
        if not isinstance(entries, Mapping) or system not in entries:
            raise ValueError(f"invalid provider partition: {system}")
        providers[system] = copy.deepcopy(entries[system])
    merged["providers"] = providers
    return merged


def build_matrix(
    *,
    root: Path = ROOT,
    jobs: int | None = None,
) -> dict[str, Any]:
    resolved = root.resolve()
    if resolved != ROOT.resolve():
        raise ValueError(
            "detached provider matrix audits require an isolated subprocess "
            "with that root's scripts on PYTHONPATH"
        )
    fingerprint = _matrix_input_fingerprint(resolved)
    # The checked matrix is a portable runtime-readiness snapshot.  External
    # fulltext verification belongs to release_deploy's explicit
    # ``--research-root`` gate; allowing a developer shell variable to alter
    # this snapshot would make the same checkout differ across hosts.
    missing = object()
    previous_research_root: object = os.environ.pop(
        "MINGLI_RESEARCH_ROOT",
        missing,
    )
    # Spawned partition workers do not inherit the parent's ``-B`` flag.  If
    # one of them writes bytecode into the pinned runtime site-packages, the
    # runtime integrity probe fails closed for every later audit, so bytecode
    # writes are disabled for the whole generation window and then restored.
    previous_bytecode_guard: object = os.environ.pop(
        "PYTHONDONTWRITEBYTECODE",
        missing,
    )
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        worker_count = _matrix_jobs(len(EXPECTED_SYSTEMS)) if jobs is None else jobs
        if worker_count < 1:
            raise ValueError("matrix jobs must be at least 1")
        worker_count = min(worker_count, max(1, len(EXPECTED_SYSTEMS)))
        if worker_count == 1 or len(EXPECTED_SYSTEMS) <= 1:
            generated = _build_matrix_uncached(str(resolved), fingerprint)
        else:
            partitions: dict[str, Mapping[str, Any]] = {}
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(
                        _build_provider_partition,
                        str(resolved),
                        fingerprint,
                        system,
                    ): system
                    for system in MATRIX_EXECUTION_ORDER
                    if system in EXPECTED_SYSTEMS
                }
                for future in as_completed(futures):
                    system = futures[future]
                    partitions[system] = future.result()
            generated = _merge_provider_partitions(EXPECTED_SYSTEMS, partitions)
            if _matrix_input_fingerprint(resolved) != fingerprint:
                raise ValueError("provider matrix inputs changed during generation")
    finally:
        os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        if previous_bytecode_guard is not missing:
            os.environ["PYTHONDONTWRITEBYTECODE"] = str(previous_bytecode_guard)
        if previous_research_root is not missing:
            os.environ["MINGLI_RESEARCH_ROOT"] = str(previous_research_root)
    return copy.deepcopy(generated)


def audit_matrix(
    payload: Mapping[str, Any],
    *,
    root: Path = ROOT,
    canonical: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    findings: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        findings.append("matrix schema_version mismatch")
    canonical = (
        build_matrix(root=root)
        if canonical is None
        else copy.deepcopy(dict(canonical))
    )
    if payload.get("policy") != canonical["policy"]:
        findings.append("matrix policy drift from live generator")
    if payload.get("inputs") != canonical["inputs"]:
        findings.append("matrix input hashes drift from live artifacts")
    providers = payload.get("providers")
    if not isinstance(providers, Mapping):
        findings.append("matrix providers must be an object")
        providers = {}
    actual_systems = set(providers)
    expected_systems = set(EXPECTED_SYSTEMS)
    if actual_systems != expected_systems:
        findings.append(
            "provider route set mismatch: "
            f"missing={sorted(expected_systems - actual_systems)} "
            f"extra={sorted(actual_systems - expected_systems)}"
        )
    if STRUCTURED_SYSTEMS:
        findings.append(f"generic structured providers remain: {STRUCTURED_SYSTEMS!r}")
    for system in sorted(expected_systems & actual_systems):
        entry = providers[system]
        if not isinstance(entry, Mapping):
            findings.append(f"{system}: provider entry must be an object")
            continue
        canonical_entry = canonical["providers"][system]
        for field in (
            "declaration",
            "runtime",
            "fixtures",
            "algorithm",
            "dedicated_audit",
            "dedicated_runtime_replay",
            "live_contract",
            "source_applicability",
            "transaction_lifecycle",
            "boundary_proof_summary",
        ):
            if entry.get(field) != canonical_entry[field]:
                label = "fixture" if field == "fixtures" else field
                findings.append(
                    f"{system}: {label} drift from canonical live audit"
                )
        derived_findings = _entry_readiness_findings(system, entry)
        if entry.get("readiness_findings") != derived_findings:
            findings.append(f"{system}: readiness findings are not derived")
        if bool(entry.get("ready")) != (not derived_findings):
            findings.append(f"{system}: ready is not derived from verified checks")
        findings.extend(derived_findings)
        if entry.get("ready") != canonical_entry["ready"]:
            findings.append(f"{system}: ready drift from canonical live audit")
        if not entry.get("ready"):
            findings.append(f"{system}: provider is not ready")
    return {
        "schema_version": "mingli-provider-completeness-audit-v1",
        "provider_ready": not findings,
        "provider_count": len(actual_systems),
        "findings": findings,
    }


def render_matrix(payload: Mapping[str, Any]) -> str:
    return yaml.safe_dump(
        copy.deepcopy(dict(payload)),
        allow_unicode=True,
        sort_keys=True,
        width=100,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    args = parser.parse_args(argv)

    generated = build_matrix(root=ROOT)
    rendered = render_matrix(generated)
    report = audit_matrix(generated, root=ROOT, canonical=generated)
    if args.check:
        if not args.matrix.is_file():
            print(f"provider matrix missing: {args.matrix}", file=sys.stderr)
            return 1
        if args.matrix.read_text(encoding="utf-8") != rendered:
            print("provider matrix differs from the canonical live snapshot", file=sys.stderr)
            return 1
    if args.write and report["provider_ready"]:
        expected_fingerprint = generated["inputs"][
            "generator_input_fingerprint"
        ]
        if _matrix_input_fingerprint(ROOT) != expected_fingerprint:
            print(
                "provider matrix inputs changed before publication",
                file=sys.stderr,
            )
            return 1
        args.matrix.write_text(rendered, encoding="utf-8")
    print(yaml.safe_dump(report, allow_unicode=True, sort_keys=True).strip())
    return 0 if report["provider_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
