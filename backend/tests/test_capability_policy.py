import json
from pathlib import Path

from app.readings.capability_policy import (
    RuntimeCapabilityProjection,
    project_capabilities,
)


def _write_rules(root: Path, rows: list[dict[str, object]]) -> None:
    path = root / "references" / "index" / "evidence-rules.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _by_id(root: Path) -> dict[str, RuntimeCapabilityProjection]:
    return {
        item.capability_id: item
        for item in project_capabilities(release_root=root)
    }


def test_capability_tier_follows_runtime_evidence_roles_and_divination_prefixes(
    tmp_path: Path,
) -> None:
    _write_rules(
        tmp_path,
        [
            {
                "system": "bazi",
                "runtime_active": True,
                "evidence_role": "issue_specific_judgment_rule",
            },
            {
                "system": "ziwei",
                "runtime_active": True,
                "evidence_role": "methodology_rule",
            },
            {
                "system": "divination",
                "rule_id": "divination/huangjin-ce#HJC-R009",
                "runtime_active": True,
                "evidence_role": "issue_specific_judgment_rule",
            },
            {
                "system": "divination",
                "rule_id": "divination/zengshan-buyi#ZR-04-04",
                "runtime_active": True,
                "evidence_role": "issue_specific_judgment_rule",
            },
            {
                "system": "divination",
                "rule_id": "divination/meihua-yishu#MR-04-01",
                "runtime_active": True,
                "evidence_role": "issue_specific_judgment_rule",
            },
        ],
    )

    projection = _by_id(tmp_path)

    assert projection["bazi"].tier == "A"
    assert projection["bazi"].judgment_rule_count == 1
    assert projection["ziwei"].tier == "B"
    assert projection["ziwei"].judgment_rule_count == 0
    # 2026-08-21 user decision: Liuyao/Meihua follow the shared tier rule.
    assert projection["liuyao"].tier == "A"
    assert projection["liuyao"].judgment_rule_count == 2
    assert projection["liuyao"].user_decision_pending is False
    assert projection["meihua"].tier == "A"
    assert projection["meihua"].judgment_rule_count == 1
    assert projection["meihua"].user_decision_pending is False


def test_capability_tier_changes_when_runtime_rule_role_changes(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        [
            {
                "system": "bazi",
                "runtime_active": True,
                "evidence_role": "methodology_rule",
            }
        ],
    )
    assert _by_id(tmp_path)["bazi"].tier == "B"

    _write_rules(
        tmp_path,
        [
            {
                "system": "bazi",
                "runtime_active": True,
                "evidence_role": "issue_specific_judgment_rule",
            }
        ],
    )
    assert _by_id(tmp_path)["bazi"].tier == "A"


def test_admitted_v53_projection_matches_the_recorded_runtime_counts() -> None:
    projection = _by_id(
        Path(__file__).parents[1].parent / ".runtime" / "v53-time-check-release"
    )

    assert projection["luming-nayin"].judgment_rule_count == 56
    assert projection["qimen"].judgment_rule_count == 40
    assert projection["bazi"].judgment_rule_count == 19
    assert projection["taiyi"].judgment_rule_count == 15
    assert projection["daliuren"].judgment_rule_count == 5
    assert projection["liuyao"].judgment_rule_count == 2
    assert projection["meihua"].judgment_rule_count == 3
    assert projection["fengshui"].judgment_rule_count == 1
    assert projection["selection"].judgment_rule_count == 1
    assert projection["ziwei"].judgment_rule_count == 0
    assert projection["qizheng"].judgment_rule_count == 0
    assert projection["jianxiang"].judgment_rule_count == 0
    # 2026-08-21 user decision: with judgment rules present, the admitted
    # release now projects Liuyao/Meihua at tier A with no pending flag.
    assert projection["liuyao"].tier == "A"
    assert projection["liuyao"].user_decision_pending is False
    assert projection["meihua"].tier == "A"
    assert projection["meihua"].user_decision_pending is False


async def test_public_capability_endpoint_exposes_runtime_projection(client) -> None:  # type: ignore[no-untyped-def]
    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200, response.text
    payload = response.json()
    capabilities = {item["capability_id"]: item for item in payload["capabilities"]}
    assert payload["source_status"] == "available"
    assert capabilities["bazi"]["tier"] == "A"
    assert payload["runtime_release_profile"] == "v51"
    assert capabilities["bazi"]["judgment_rule_count"] == 18
    assert capabilities["ziwei"]["tier"] == "B"
    assert capabilities["qizheng"]["tier"] == "B"
    assert capabilities["liuyao"]["tier"] == "B"
    assert capabilities["liuyao"]["user_decision_pending"] is False
    assert "secret" not in response.text.lower()
