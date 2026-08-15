#!/usr/bin/env python3
"""Fail-closed synthetic relationship smoke for the admitted real Runtime.

The caller supplies the private Runtime settings through the normal
``MINGLI_*`` environment.  This script prints only release identity, counts,
signal IDs and projection types; it never prints profile data, state tokens,
model credentials or narrative content.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_ROOT = _REPO_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.adapters.runtime import RuntimeStartupError, build_runtime_startup_gate  # noqa: E402
from app.charts.projectors import project_runtime_view_model  # noqa: E402
from app.config import Settings  # noqa: E402
from app.readings.request_compiler import (  # noqa: E402
    ConfirmedProfileVersion,
    compile_relationship_prepare,
)
from app.readings.runtime_contracts import Prepared  # noqa: E402

_GOLDEN_SIGNAL_IDS = {
    "bazi": frozenset(
        {
            "bazi.cross_branch.liu_po.year.hour",
            "bazi.cross_stem.wu_he.year.hour",
            "bazi.cross_stem.wu_he.day.month",
            "bazi.cross_branch.liu_po.day.hour",
            "bazi.cross_branch.san_he.a_month.b_year.b_day",
            "bazi.cross_branch.san_he.a_hour.b_month.b_hour",
        }
    ),
    "ziwei": frozenset(
        {
            "ziwei.cross_palace.liu_po.命宫",
            "ziwei.cross_palace.liu_he.夫妻",
            "ziwei.cross_palace.liu_he.官禄",
            "ziwei.cross_palace.liu_hai.父母",
            "ziwei.cross_palace.liu_hai.疾厄",
            "ziwei.cross_palace.liu_po.福德",
            "ziwei.cross_palace.liu_po.财帛",
            "ziwei.cross_palace.liu_po.迁移",
            "ziwei.cross_palace.liu_he.身宫",
        }
    ),
    "qizheng": frozenset(
        {
            "qizheng.cross_aspect.trine.土星.太阳",
            "qizheng.cross_aspect.square.土星.水星",
            "qizheng.cross_aspect.trine.土星.紫炁",
            "qizheng.cross_aspect.square.太阳.土星",
            "qizheng.cross_aspect.opposition.太阳.太阳",
            "qizheng.cross_aspect.sextile.太阳.紫炁",
            "qizheng.cross_aspect.square.太阴.木星",
            "qizheng.cross_aspect.opposition.太阴.紫炁",
            "qizheng.cross_aspect.sextile.月孛.月孛",
            "qizheng.cross_aspect.square.月孛.火星",
            "qizheng.cross_aspect.square.木星.土星",
            "qizheng.cross_aspect.conjunction.木星.太阳",
            "qizheng.cross_aspect.trine.木星.紫炁",
            "qizheng.cross_aspect.square.水星.土星",
            "qizheng.cross_aspect.opposition.水星.太阳",
            "qizheng.cross_aspect.sextile.水星.紫炁",
            "qizheng.cross_aspect.sextile.火星.土星",
            "qizheng.cross_aspect.opposition.火星.木星",
            "qizheng.cross_aspect.trine.火星.水星",
            "qizheng.cross_aspect.square.火星.紫炁",
            "qizheng.cross_aspect.conjunction.紫炁.火星",
            "qizheng.cross_aspect.opposition.罗睺.太阳",
            "qizheng.cross_aspect.square.罗睺.月孛",
            "qizheng.cross_aspect.sextile.罗睺.火星",
            "qizheng.cross_aspect.conjunction.计都.太阳",
            "qizheng.cross_aspect.square.计都.月孛",
            "qizheng.cross_aspect.trine.计都.火星",
            "qizheng.cross_aspect.square.金星.月孛",
            "qizheng.cross_aspect.trine.金星.木星",
            "qizheng.cross_aspect.opposition.金星.水星",
        }
    ),
}


def _synthetic_profiles() -> tuple[ConfirmedProfileVersion, ConfirmedProfileVersion]:
    return (
        ConfirmedProfileVersion(
            subject_ref="profile-version:synthetic-a",
            birth_datetime="1994-04-30T05:55:00+08:00",
            birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
            timezone="Asia/Shanghai",
            location="上海",
            gender="男",
            time_basis_policy="solar",
            zi_hour_policy="midnight",
            longitude=121.47,
            latitude=31.23,
            coordinate_source="synthetic-relationship-smoke",
        ),
        ConfirmedProfileVersion(
            subject_ref="profile-version:synthetic-b",
            birth_datetime="1992-11-08T14:20:00+08:00",
            birth_datetime_or_four_pillars="1992-11-08T14:20:00+08:00",
            timezone="Asia/Shanghai",
            location="北京",
            gender="女",
            time_basis_policy="solar",
            zi_hour_policy="midnight",
            longitude=116.40,
            latitude=39.90,
            coordinate_source="synthetic-relationship-smoke",
        ),
    )


async def _run() -> int:
    settings = Settings()
    if settings.runtime_release_profile != "v52-relationship":
        print(
            "SMOKE FAIL-CLOSED: set MINGLI_RUNTIME_RELEASE_PROFILE="
            "v52-relationship before running this smoke",
            file=sys.stderr,
        )
        return 2
    try:
        gate = build_runtime_startup_gate(settings)
        described = await gate.startup()
    except (RuntimeStartupError, OSError, ValueError) as error:
        print(
            "SMOKE FAIL-CLOSED: Runtime admission failed: "
            f"{type(error).__name__}",
            file=sys.stderr,
        )
        return 3

    inventory = gate.release_inspector.inspect()
    print(
        "runtime admission: OK "
        f"({settings.runtime_release_profile}, {len(described.capabilities)}/13, "
        f"{inventory.release_manifest_sha256})"
    )
    profiles = _synthetic_profiles()
    routes = (
        ("bazi", "bazi-relationship"),
        ("ziwei", "ziwei-relationship"),
        ("qizheng", "qizheng-relationship"),
    )
    for art_id, product_id in routes:
        command = compile_relationship_prepare(
            action=f"{art_id}_relationship_preview",
            query="synthetic relationship smoke",
            art_id=art_id,
            relationship_type="romantic",
            profiles=profiles,
            dimension_ids=("relationship",),
        )
        result = await gate.runtime.execute(command)
        if not isinstance(result, Prepared):
            print(f"SMOKE FAIL: {art_id} returned {result.kind}", file=sys.stderr)
            return 4
        brief = result.brief.to_dict()
        relationship_facts = [
            fact
            for fact in brief.get("facts") or ()
            if isinstance(fact, dict)
            and str(fact.get("ref") or "").endswith("/relationship_signals")
        ]
        if len(relationship_facts) != 1:
            print(f"SMOKE FAIL: {art_id} relationship fact count is invalid", file=sys.stderr)
            return 4
        signals = relationship_facts[0].get("value")
        if not isinstance(signals, list) or not signals:
            print(f"SMOKE FAIL: {art_id} emitted no relationship signals", file=sys.stderr)
            return 4
        signal_ids = {
            str(signal.get("signal_id") or "")
            for signal in signals
            if isinstance(signal, dict)
        }
        if signal_ids != _GOLDEN_SIGNAL_IDS[art_id]:
            print(
                f"SMOKE FAIL: {art_id} relationship golden IDs changed",
                file=sys.stderr,
            )
            return 4
        for signal in signals:
            if not isinstance(signal, dict):
                print(f"SMOKE FAIL: {art_id} emitted a malformed signal", file=sys.stderr)
                return 4
            refs = signal.get("fact_refs") or ()
            if any("/input/" in str(ref) for ref in refs):
                print(f"SMOKE FAIL: {art_id} relationship signal references input", file=sys.stderr)
                return 4
        view_model = project_runtime_view_model(
            brief,
            product_id=product_id,
            relationship_type="romantic",
        )
        if view_model is None or len(view_model.signals) != len(signals):
            print(
                f"SMOKE FAIL: {art_id} ViewModel projection rejected native signals",
                file=sys.stderr,
            )
            return 4
        print(
            f"{art_id}: PREPARED / {len(signals)} native signals / "
            f"{type(view_model).__name__}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
