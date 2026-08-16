from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "contracts" / "openapi" / "v1.yaml"
ADMIN_OPENAPI_PATH = ROOT / "contracts" / "openapi" / "admin-v1.yaml"
PRICING_PATH = ROOT / "web" / "src" / "app" / "pricing" / "page.tsx"


def _openapi(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        document: dict[str, Any] = yaml.safe_load(stream)
    return document


def test_subscription_and_wallet_routes_remain_closed() -> None:
    forbidden_route_terms = ("subscription", "wallet", "topup", "recharge")

    for openapi_path in (OPENAPI_PATH, ADMIN_OPENAPI_PATH):
        paths = _openapi(openapi_path)["paths"]
        assert all(
            not any(term in path.lower() for term in forbidden_route_terms)
            for path in paths
        )

    pricing = PRICING_PATH.read_text(encoding="utf-8")
    assert "当前不开放自动续费、代币余额、充值钱包或永久无限 AI" in pricing
    assert "按钮点击不会被写成已付款" in pricing
