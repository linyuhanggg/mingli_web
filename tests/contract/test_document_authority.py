from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_AUDIT_SOURCE = Path(
    "/Users/yuhanglin/.codex/visualizations/2026/08/12/"
    "019ff5b8-ffff-7f42-8629-e68f090ebc05"
)

REQUIRED_AUTHORITIES = (
    ROOT / "docs" / "CHECKLIST.md",
    ROOT / "DESIGN.md",
    ROOT / "CONTEXT.md",
    ROOT / "docs" / "MINGLI_V51_WEB_INTEGRATION.md",
    ROOT / "web" / "AGENTS.md",
    ROOT / "admin" / "AGENTS.md",
    ROOT / "docs" / "adr",
    ROOT / "docs" / "releases" / "evidence",
)

RETIRED_PARALLEL_AUTHORITIES = (
    ROOT / "PRODUCT.md",
    ROOT / "docs" / "PRODUCT_DIRECTION.md",
    ROOT / "docs" / "PRODUCT_BLUEPRINT_WEB_IOS_V2.md",
    ROOT / "docs" / "plans",
    ROOT / "design-system" / "mingli-web",
)

REFERENCE_AUDITS = (
    (
        REFERENCE_AUDIT_SOURCE / "qingnang-audit.md",
        ROOT
        / "docs"
        / "releases"
        / "evidence"
        / "2026-08-12-reference-site-audits"
        / "qingnang-authenticated-product-audit.md",
    ),
    (
        REFERENCE_AUDIT_SOURCE / "metis-live-audit.md",
        ROOT
        / "docs"
        / "releases"
        / "evidence"
        / "2026-08-12-reference-site-audits"
        / "metis-live-responsive-ui-audit.md",
    ),
)

AMENDING_ADR = ROOT / "docs" / "adr" / (
    "0011-rebuild-the-product-surface-from-main-under-a-ui-first-contract.md"
)
AMENDED_ADRS = tuple(
    ROOT / "docs" / "adr" / filename
    for filename in (
        "0006-separate-user-subscriptions-from-model-provider-billing.md",
        "0008-use-channel-neutral-billing-and-unified-entitlements.md",
        "0009-separate-user-from-login-identities.md",
        "0010-replace-agent-loop-with-an-explicit-reading-orchestrator.md",
    )
)
HISTORICAL_ADR_FRAGMENTS = {
    AMENDED_ADRS[0]: "P0 保留两种单次深度解读",
    AMENDED_ADRS[1]: "P0 仍只卖个人命盘深度解读和一事一问·六爻两种单次商品",
    AMENDED_ADRS[2]: "P0 默认支持手机号 OTP 和邮箱 OTP，不把密码作为必做能力",
    AMENDED_ADRS[3]: "P0 产品 capability allowlist 固定为 `bazi`、`fortune`、`liuyao`",
}


def test_only_the_frozen_authority_set_remains() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_AUTHORITIES if not path.exists()]
    revived = [
        str(path.relative_to(ROOT))
        for path in RETIRED_PARALLEL_AUTHORITIES
        if path.exists()
    ]

    assert missing == []
    assert revived == []


def test_reference_site_audits_are_kept_as_repository_evidence() -> None:
    missing = [
        str(copy.relative_to(ROOT))
        for _, copy in REFERENCE_AUDITS
        if not copy.is_file()
    ]
    changed = [
        str(copy.relative_to(ROOT))
        for source, copy in REFERENCE_AUDITS
        if source.is_file()
        and copy.is_file()
        and source.read_bytes() != copy.read_bytes()
    ]

    assert missing == []
    assert changed == []


def test_no_parallel_plan_or_handoff_authority_is_reintroduced() -> None:
    violations = []
    for path in ROOT.rglob("*.md"):
        relative = path.relative_to(ROOT)
        if any(
            part in {".git", ".qoder", ".claude", "node_modules"}
            for part in relative.parts
        ):
            continue
        if relative.parts[:3] == ("docs", "releases", "evidence"):
            continue
        name = path.name.lower()
        if (
            name.startswith("handoff")
            or "blueprint" in name
            or "checklist" in name and relative != Path("docs/CHECKLIST.md")
        ):
            violations.append(str(relative))

    assert violations == []


def test_ui_work_rules_bind_web_and_admin_to_the_same_authorities() -> None:
    required_fragments = (
        "../DESIGN.md",
        "../docs/CHECKLIST.md",
        "../CONTEXT.md",
        "../docs/MINGLI_V51_WEB_INTEGRATION.md",
    )
    violations = [
        f"{path.relative_to(ROOT)}: {fragment}"
        for path in (ROOT / "web" / "AGENTS.md", ROOT / "admin" / "AGENTS.md")
        for fragment in required_fragments
        if fragment not in path.read_text(encoding="utf-8")
    ]

    assert violations == []


def test_amending_adr_and_reciprocal_metadata_are_present() -> None:
    assert AMENDING_ADR.is_file()
    assert "amends:" in AMENDING_ADR.read_text(encoding="utf-8")
    violations = [
        str(path.relative_to(ROOT))
        for path in AMENDED_ADRS
        if "amended_by: 0011-rebuild-the-product-surface-from-main-under-a-ui-first-contract"
        not in path.read_text(encoding="utf-8")
    ]

    assert violations == []


def test_amended_adrs_keep_their_historical_decision_text() -> None:
    violations = [
        str(path.relative_to(ROOT))
        for path, fragment in HISTORICAL_ADR_FRAGMENTS.items()
        if fragment not in path.read_text(encoding="utf-8")
    ]

    assert violations == []


def test_current_authorities_do_not_revive_retired_product_contracts() -> None:
    current_authorities = (
        ROOT / "README.md",
        ROOT / "DESIGN.md",
        ROOT / "CONTEXT.md",
        ROOT / "web" / "AGENTS.md",
        ROOT / "docs" / "MINGLI_V51_WEB_INTEGRATION.md",
    )
    retired_names = (
        "PRODUCT_DIRECTION.md",
        "PRODUCT_BLUEPRINT_WEB_IOS_V2.md",
        "design-system/mingli-web",
    )
    violations = [
        f"{path.relative_to(ROOT)}: {retired_name}"
        for path in current_authorities
        for retired_name in retired_names
        if retired_name in path.read_text(encoding="utf-8")
    ]

    assert violations == []
