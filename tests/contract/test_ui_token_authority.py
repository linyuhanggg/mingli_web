from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS_CSS = ROOT / "ui" / "tokens.css"
WEB_GLOBALS = ROOT / "web" / "src" / "app" / "globals.css"
ADMIN_GLOBALS = ROOT / "admin" / "src" / "app" / "globals.css"
APP_CSS_ROOTS = (ROOT / "web" / "src", ROOT / "admin" / "src")

DESIGN_TOKEN_VALUES = {
    "--color-canvas": "#fafafa",
    "--color-surface": "#ffffff",
    "--color-surface-subtle": "#f5f5f5",
    "--color-surface-muted": "#eeeeee",
    "--color-surface-inverse": "#0a0a0a",
    "--color-text": "#0a0a0a",
    "--color-text-secondary": "#525252",
    "--color-text-muted": "#8a8a8a",
    "--color-text-inverse": "#ffffff",
    "--color-border": "#e5e5e5",
    "--color-border-strong": "#d4d4d4",
    "--color-overlay": "rgb(0 0 0 / 42%)",
    "--color-action": "#0a0a0a",
    "--color-action-hover": "#262626",
    "--color-on-action": "#ffffff",
    "--color-focus": "#2563eb",
    "--color-accent": "#2563eb",
    "--color-accent-hover": "#1d4ed8",
    "--color-on-accent": "#ffffff",
    "--color-info": "#2563eb",
    "--color-success": "#137a45",
    "--color-warning": "#946200",
    "--color-danger": "#c62828",
    "--surface-info": "#eef5ff",
    "--surface-success": "#ecf8f1",
    "--surface-warning": "#fff7df",
    "--surface-danger": "#fff0ef",
    "--radius-control": "8px",
    "--radius-card": "8px",
    "--radius-panel": "12px",
    "--radius-pill": "999px",
    "--shadow-float": "0 4px 16px rgb(0 0 0 / 8%)",
    "--shadow-overlay": "0 16px 48px rgb(0 0 0 / 14%)",
    "--target-min": "44px",
    "--target-submit": "48px",
}

BANNED_TOKEN_RE = re.compile(
    r"--(?:ink|ivory|gold|terracotta|moss|amber)-\w+"
    r"|--font-serif\b"
    r"|--shadow-hero-orbit\b"
    r"|--shadow-action\b"
)
TOKEN_DECL_RE = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
VAR_USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")
IMPORT_TOKENS_RE = re.compile(
    r"""@import\s+(?:url\(\s*)?['"]?(?:\.\./)+ui/tokens\.css['"]?\s*\)?\s*;"""
)
SERIF_FAMILY_RE = re.compile(
    r"Songti SC|STSong|Noto Serif SC|Noto Serif CJK SC",
    re.IGNORECASE,
)
FONT_DOMAIN_USE_RE = re.compile(r"var\(\s*--font-domain")
GRADIENT_RE = re.compile(r"(?:linear|radial|conic)-gradient\s*\(")
GLASS_SURFACE_RE = re.compile(
    r"backdrop-filter\s*:"
    r"|background(?:-color|-image)?\s*:[^;{}]*"
    r"var\(\s*--(?:home|paper)-glass(?:-strong)?\b",
    re.IGNORECASE,
)
INFINITE_ANIM_RE = re.compile(r"animation(?:-name)?\s*:[^;]*infinite", re.IGNORECASE)
ORBIT_RE = re.compile(r"archive-orbit|hero-orbit|time-ring|outerRingSpin", re.IGNORECASE)
COLOR_LITERAL_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|rgba?\([^)]*\)"
    r"|hsla?\([^)]*\)",
    re.IGNORECASE,
)
OLD_BRAND_COLOR_RE = re.compile(
    r"169\s+133\s+63"
    r"|193\s+162\s+99"
    r"|168\s+94\s+70"
    r"|136\s+69\s+50"
    r"|248\s+243\s+231"
    r"|255\s+253\s+247"
    r"|223\s+233\s+223"
    r"|18\s+58\s+50"
    r"|10\s+40\s+35"
    r"|16\s+52\s+45"
    r"|45\s+98\s+83"
    r"|#a9853f\b"
    r"|#c1a263\b"
    r"|#a85e46\b"
    r"|#f8f3e7\b"
    r"|#fffdf7\b"
    r"|#123a32\b"
    r"|#0a2823\b",
    re.IGNORECASE,
)
DOMAIN_FONT_ALLOWLIST = {
    "web/src/components/readings/bazi-chart.module.css",
    "web/src/components/readings/liuyao-hexagram.module.css",
}
DOMAIN_FONT_ALLOWED_SELECTORS = {
    ".pillarStem",
    ".pillarBranch",
    ".names dd",
    ".yaoMark",
    ".hexagramGlyph",
}
STATUS_INFINITE_ALLOWLIST = {
    "web/src/components/status-panel.module.css",
    "web/src/components/ui/status.module.css",
    "web/src/components/ui/button.module.css",
    "admin/src/components/ui/status.module.css",
    "admin/src/components/ui/button.module.css",
}
SKIP_DIR_NAMES = {".git", ".next", "node_modules", ".qoder", ".claude", ".runtime"}
WEB_START_SCRIPT = ROOT / "web" / "scripts" / "start-standalone.mjs"
ADMIN_START_SCRIPT = ROOT / "admin" / "scripts" / "start-standalone.mjs"
WEB_NEXT_CONFIG = ROOT / "web" / "next.config.ts"
ADMIN_NEXT_CONFIG = ROOT / "admin" / "next.config.ts"
HOME_CSS_REL = "web/src/app/home.module.css"
HOME_GRADIENT_SELECTORS = {
    ".spotlight",
    ".heroPrimary::before",
    ".quickStartEntry::after",
    ".card::after",
    ".crossCard::after",
    ".leadCard::after",
}
HOME_GLASS_SELECTORS = {
    ".heroSecondary",
    ".crossCard",
    ".auxGrid",
    ".hero",
}


def _iter_app_css() -> list[Path]:
    files: list[Path] = []
    for root in APP_CSS_ROOTS:
        for path in root.rglob("*.css"):
            if SKIP_DIR_NAMES.intersection(path.parts):
                continue
            files.append(path)
    return sorted(files)


def _normalize_css_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().rstrip(";").lower()


def _declared_tokens(source: str) -> dict[str, str]:
    declared: dict[str, str] = {}
    for match in re.finditer(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);", source):
        declared[match.group(1)] = match.group(2).strip()
    return declared


# Status colors (success/danger/warning and their surfaces) are reserved for
# genuine states. The misuse checks below assert that they never leak into
# structural/interactive contexts (hover, checked selection, focus, current
# item, busy indicators, or decoration).
STATUS_SEMANTIC_RE = re.compile(r"--(?:color|surface)-(?:success|danger|warning)")
WARNING_RE = re.compile(r"--(?:color|surface)-warning")
DESTRUCTIVE_CONTEXT_RE = re.compile(r"\.(?:destructive|danger)\b")


def _iter_rule_blocks(source: str) -> list[tuple[str, str]]:
    """Yield ``(selector, body)`` for every rule, descending into ``@media``.

    Comments are stripped and non-``@media`` at-rules (``@keyframes``,
    ``@font-face``, …) are skipped so their inner ``from``/``to``/descriptor
    blocks are never mistaken for selectors.
    """
    src = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    blocks: list[tuple[str, str]] = []

    def walk(text: str) -> None:
        i = 0
        n = len(text)
        while i < n:
            brace = text.find("{", i)
            if brace == -1:
                break
            header = text[i:brace].strip()
            depth = 0
            j = brace
            while j < n:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            body = text[brace + 1 : j]
            if header.startswith("@media"):
                walk(body)
            elif not header.startswith("@"):
                blocks.append((header, body))
            i = j + 1

    walk(src)
    return blocks


def _all_rule_blocks() -> list[tuple[str, str, str]]:
    """Yield ``(relative_path, selector, body)`` for every rule in both apps."""
    result: list[tuple[str, str, str]] = []
    for path in _iter_app_css():
        source = path.read_text(encoding="utf-8")
        for selector, body in _iter_rule_blocks(source):
            result.append((str(path.relative_to(ROOT)), selector, body))
    return result


def _rule_bodies(relative_path: str, expected_selector: str) -> list[str]:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    return [
        body for selector, body in _iter_rule_blocks(source) if selector == expected_selector
    ]


def _rule_body(relative_path: str, expected_selector: str) -> str:
    matches = _rule_bodies(relative_path, expected_selector)
    assert matches, f"expected {relative_path}: {expected_selector} rule"
    return "\n".join(matches)


def _selector_parts(selector: str) -> set[str]:
    return {part.strip() for part in selector.split(",") if part.strip()}


def test_shared_tokens_file_is_the_only_semantic_source() -> None:
    assert TOKENS_CSS.is_file(), "ui/tokens.css must exist as the shared semantic token source"
    copies = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("tokens.css")
        if not SKIP_DIR_NAMES.intersection(path.relative_to(ROOT).parts)
        and path != TOKENS_CSS
    ]
    assert copies == []


def test_web_and_admin_globals_directly_import_shared_tokens() -> None:
    missing = [
        str(path.relative_to(ROOT))
        for path in (WEB_GLOBALS, ADMIN_GLOBALS)
        if not path.is_file() or not IMPORT_TOKENS_RE.search(path.read_text(encoding="utf-8"))
    ]
    assert missing == []


def test_web_and_admin_do_not_redeclare_shared_tokens() -> None:
    shared = set(_declared_tokens(TOKENS_CSS.read_text(encoding="utf-8")))
    duplicates: list[str] = []
    for path in _iter_app_css():
        for name in _declared_tokens(path.read_text(encoding="utf-8")):
            if name in shared:
                duplicates.append(f"{path.relative_to(ROOT)}:{name}")
    assert duplicates == []


def test_design_token_values_are_declared_exactly() -> None:
    source = TOKENS_CSS.read_text(encoding="utf-8")
    declared = _declared_tokens(source)
    missing = [name for name in DESIGN_TOKEN_VALUES if name not in declared]
    mismatched = [
        f"{name}: {declared[name]!r} != {expected!r}"
        for name, expected in DESIGN_TOKEN_VALUES.items()
        if name in declared
        and _normalize_css_value(declared[name]) != _normalize_css_value(expected)
    ]
    assert missing == []
    assert mismatched == []


def test_css_does_not_reference_or_declare_retired_brand_tokens() -> None:
    violations: list[str] = []
    for path in _iter_app_css() + [TOKENS_CSS, ROOT / "ui" / "base.css"]:
        if not path.is_file():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if BANNED_TOKEN_RE.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}:{line.strip()}")
    assert violations == []


def test_static_css_vars_point_at_declared_tokens() -> None:
    shared = set(_declared_tokens(TOKENS_CSS.read_text(encoding="utf-8")))
    if (ROOT / "ui" / "base.css").is_file():
        shared.update(_declared_tokens((ROOT / "ui" / "base.css").read_text(encoding="utf-8")))

    undefined: list[str] = []
    for path in _iter_app_css():
        source = path.read_text(encoding="utf-8")
        local = set(_declared_tokens(source))
        known = shared | local
        for line_no, line in enumerate(source.splitlines(), start=1):
            for name in VAR_USE_RE.findall(line):
                if name not in known:
                    undefined.append(f"{path.relative_to(ROOT)}:{line_no}:{name}")
    assert undefined == []


def test_ui_uses_noto_sans_sc_and_limits_serif_to_domain_token() -> None:
    tokens = TOKENS_CSS.read_text(encoding="utf-8")
    assert "Noto Sans SC" in tokens
    assert "--font-sans" in tokens
    assert "--font-domain" in tokens
    assert "Songti SC" in tokens
    domain_decl = _declared_tokens(tokens)["--font-domain"]
    assert "Songti SC" in domain_decl

    for path in (WEB_GLOBALS, ADMIN_GLOBALS):
        source = path.read_text(encoding="utf-8")
        uses_sans = (
            "Noto Sans SC" in source
            or "var(--font-sans)" in source
            or IMPORT_TOKENS_RE.search(source) is not None
        )
        assert uses_sans, f"{path.relative_to(ROOT)} must keep Noto Sans SC via shared tokens"

    serif_leaks: list[str] = []
    for path in _iter_app_css():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if SERIF_FAMILY_RE.search(line):
                serif_leaks.append(f"{path.relative_to(ROOT)}:{line_no}:{line.strip()}")
    assert serif_leaks == []

    for match in SERIF_FAMILY_RE.finditer(tokens):
        around = tokens[max(0, match.start() - 80) : match.end() + 20]
        assert "--font-domain" in around


def test_retired_brand_rgb_is_absent_from_app_css() -> None:
    violations: list[str] = []
    for path in _iter_app_css() + [TOKENS_CSS, ROOT / "ui" / "base.css"]:
        if not path.is_file():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if OLD_BRAND_COLOR_RE.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}:{line.strip()}")
    assert violations == []


def test_business_css_does_not_scatter_hardcoded_colors() -> None:
    violations: list[str] = []
    for path in _iter_app_css():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.split("/*", 1)[0].strip()
            if not stripped or stripped.startswith("*"):
                continue
            if COLOR_LITERAL_RE.search(stripped):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}:{stripped}")
    assert violations == []


def test_gradients_and_glass_effects_are_banned() -> None:
    violations: list[str] = []
    for path in _iter_app_css():
        rel = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8")
        if rel == HOME_CSS_REL:
            for selector, body in _iter_rule_blocks(source):
                has_gradient = GRADIENT_RE.search(body) is not None
                has_glass = GLASS_SURFACE_RE.search(body) is not None
                if not has_gradient and not has_glass:
                    continue
                if has_gradient:
                    violations.extend(
                        f"{rel}: {part}: homepage gradient is not approved"
                        for part in sorted(_selector_parts(selector) - HOME_GRADIENT_SELECTORS)
                    )
                if has_glass:
                    violations.extend(
                        f"{rel}: {part}: homepage glass is not approved"
                        for part in sorted(_selector_parts(selector) - HOME_GLASS_SELECTORS)
                    )
            continue
        for line_no, line in enumerate(source.splitlines(), start=1):
            if GRADIENT_RE.search(line) or GLASS_SURFACE_RE.search(line):
                violations.append(f"{rel}:{line_no}:{line.strip()}")

    for path in (TOKENS_CSS, ROOT / "ui" / "base.css"):
        if not path.is_file():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if GRADIENT_RE.search(line) or GLASS_SURFACE_RE.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}:{line.strip()}")
    assert violations == []


def test_decorative_orbit_rings_and_infinite_ornament_are_gone() -> None:
    violations: list[str] = []
    for path in _iter_app_css():
        rel = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            if ORBIT_RE.search(line):
                violations.append(f"{rel}:{line_no}:{line.strip()}")
            if INFINITE_ANIM_RE.search(line) and rel not in STATUS_INFINITE_ALLOWLIST:
                violations.append(f"{rel}:{line_no}:{line.strip()}")
    assert violations == []


def test_font_domain_is_limited_to_chart_glyphs() -> None:
    leaks: list[str] = []
    for path in _iter_app_css():
        rel = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8")
        if rel not in DOMAIN_FONT_ALLOWLIST:
            for line_no, line in enumerate(source.splitlines(), start=1):
                if FONT_DOMAIN_USE_RE.search(line):
                    leaks.append(f"{rel}:{line_no}:{line.strip()}")
            continue
        current_selectors: list[str] = []
        for line_no, line in enumerate(source.splitlines(), start=1):
            if "{" in line:
                current_selectors = [part.strip() for part in line.split("{", 1)[0].split(",")]
            if FONT_DOMAIN_USE_RE.search(line) and not any(
                selector in DOMAIN_FONT_ALLOWED_SELECTORS for selector in current_selectors
            ):
                leaks.append(f"{rel}:{line_no}:{','.join(current_selectors)}:{line.strip()}")
    assert leaks == []


def test_checked_selection_never_uses_status_semantic_colors() -> None:
    violations = [
        f"{rel}: {selector}"
        for rel, selector, body in _all_rule_blocks()
        if ":checked" in selector and STATUS_SEMANTIC_RE.search(body)
    ]
    assert violations == []


def test_ordinary_hover_never_uses_status_semantic_colors() -> None:
    violations: list[str] = []
    for rel, selector, body in _all_rule_blocks():
        if ":hover" not in selector or not STATUS_SEMANTIC_RE.search(body):
            continue
        # Destructive controls legitimately keep their danger tint on hover.
        if DESTRUCTIVE_CONTEXT_RE.search(selector):
            continue
        violations.append(f"{rel}: {selector}")
    assert violations == []


def test_focus_never_uses_status_semantic_colors() -> None:
    violations = [
        f"{rel}: {selector}"
        for rel, selector, body in _all_rule_blocks()
        if ":focus" in selector and STATUS_SEMANTIC_RE.search(body)
    ]
    assert violations == []


def test_busy_states_never_use_warning_colors() -> None:
    busy_re = re.compile(r"loading|processing|pending|busy", re.IGNORECASE)
    violations = [
        f"{rel}: {selector}"
        for rel, selector, body in _all_rule_blocks()
        if busy_re.search(selector) and WARNING_RE.search(body)
    ]
    assert violations == []


def test_current_or_selected_never_uses_status_semantic_colors() -> None:
    current_re = re.compile(
        r'aria-current|aria-selected|data-state\s*=\s*["\'](?:checked|selected|active|current)["\']'
    )
    violations = [
        f"{rel}: {selector}"
        for rel, selector, body in _all_rule_blocks()
        if current_re.search(selector) and STATUS_SEMANTIC_RE.search(body)
    ]
    assert violations == []


def test_dark_backgrounds_use_inverse_text_not_secondary() -> None:
    dark_bg_re = re.compile(r"(?<![\w-])background\s*:\s*var\(--color-(?:surface-inverse|action)\)")
    secondary_text_re = re.compile(r"(?<![\w-])color\s*:\s*var\(--color-text-(?:secondary|muted)\)")
    violations = [
        f"{rel}: {selector}"
        for rel, selector, body in _all_rule_blocks()
        if dark_bg_re.search(body) and secondary_text_re.search(body)
    ]
    assert violations == []


def test_canvas_token_is_not_used_as_foreground_text() -> None:
    violations = [
        f"{rel}: {selector}"
        for rel, selector, body in _all_rule_blocks()
        if re.search(r"(?<![\w-])color\s*:\s*var\(--color-canvas\)", body)
    ]
    assert violations == []


def test_real_dark_ancestor_descendants_use_inverse_text() -> None:
    """Guard reachable dark surfaces whose text is styled in separate rules.

    These are explicit production combinations, not a general cascade parser:
    each tuple names the real dark ancestor and the descendant rule rendered
    inside it. Light-card overrides remain separate below.
    """
    combinations = (
        (
            "web/src/components/dashboard-hub.module.css",
            ".continueCard",
            ".continueCopy .kicker",
        ),
        (
            "web/src/components/private-shell.module.css",
            ".aside",
            ".aside .archiveLabel",
        ),
        (
            "web/src/components/editorial-page.module.css",
            ".pipeline",
            ".pipeline li::before",
        ),
        (
            "web/src/components/app-surface.module.css",
            ".rail",
            ".railMeta dt",
        ),
        (
            "web/src/components/readings/time-layer-tabs.module.css",
            '.tab[data-active="true"]',
            '.tab[data-active="true"] .tabSummary',
        ),
        (
            "web/src/components/readings/time-layer-tabs.module.css",
            '.tab[data-active="true"]',
            '.tab[data-active="true"] .tabStatus',
        ),
    )

    failures: list[str] = []
    for rel, ancestor, descendant in combinations:
        ancestor_body = _rule_body(rel, ancestor)
        descendant_matches = _rule_bodies(rel, descendant)
        descendant_body = "\n".join(descendant_matches)
        if not re.search(
            r"background\s*:\s*var\(--color-(?:surface-inverse|action)\)",
            ancestor_body,
        ):
            failures.append(f"{rel}: {ancestor} is no longer a dark surface")
        if not descendant_matches or not re.search(
            r"color\s*:\s*(?:var\(--color-(?:text-inverse|on-action)\)"
            r"|color-mix\([^;{}]*var\(--color-(?:text-inverse|on-action)\))",
            descendant_body,
        ):
            failures.append(f"{rel}: {ancestor} -> {descendant}")

    assert failures == []

def test_account_identity_card_is_not_styled_as_an_overlay() -> None:
    identity_card = _rule_body(
        "web/src/components/account-center.module.css", ".identityCard"
    )
    assert "box-shadow: var(--shadow-overlay)" not in identity_card


def test_real_decorative_and_domain_highlights_do_not_use_status_colors() -> None:
    bounded_rules = (
        ("web/src/components/dashboard-hub.module.css", ".periodIcon"),
        (
            "web/src/components/readings/liuyao-hexagram.module.css",
            '.line[data-moving="true"]',
        ),
    )
    violations: list[str] = []
    for rel, selector in bounded_rules:
        body = _rule_body(rel, selector)
        if WARNING_RE.search(body):
            violations.append(f"{rel}: {selector}")
        if "background: var(--color-surface-muted)" not in body:
            violations.append(f"{rel}: {selector} must use a neutral highlight")
    assert violations == []

    moving = _rule_body(
        "web/src/components/readings/liuyao-hexagram.module.css", ".moving"
    )
    assert STATUS_SEMANTIC_RE.search(moving) is None
    assert "border-color: var(--color-border-strong)" in moving
    assert "color: var(--color-text)" in moving

    liuyao = (ROOT / "web/src/components/readings/liuyao-hexagram.tsx").read_text(
        encoding="utf-8"
    )
    assert '{line.moving ? "动爻" : "静爻"}' in liuyao


def test_structural_components_do_not_decorate_with_status_colors() -> None:
    """Purely structural/selection surfaces carry no genuine status state.

    A success/danger/warning token in these files can only mean decoration, so
    the contract forbids it. This catches cases like a decorative digest bar
    or an informational notice painted with a status color.
    """
    structural_files = {
        "web/src/components/algorithm-scope.module.css",
        "web/src/components/reading-anatomy.module.css",
        "web/src/components/profile-archive.module.css",
    }
    violations = [
        f"{rel}: {selector}"
        for rel, selector, body in _all_rule_blocks()
        if rel in structural_files and STATUS_SEMANTIC_RE.search(body)
    ]
    assert violations == []


def test_spinner_animations_disable_under_prefers_reduced_motion() -> None:
    base = (ROOT / "ui" / "base.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in base

    spinner_modules = (
        "web/src/components/ui/button.module.css",
        "web/src/components/ui/status.module.css",
        "admin/src/components/ui/button.module.css",
        "admin/src/components/ui/status.module.css",
    )
    for rel in spinner_modules:
        source = (ROOT / rel).read_text(encoding="utf-8")
        assert "@keyframes" in source, rel
        assert "prefers-reduced-motion" in source, rel
        assert "animation: none" in source, rel


def test_standalone_start_uses_a_single_root_server_path() -> None:
    for path in (WEB_START_SCRIPT, ADMIN_START_SCRIPT, WEB_NEXT_CONFIG, ADMIN_NEXT_CONFIG):
        assert path.is_file(), path
    for path in (WEB_START_SCRIPT, ADMIN_START_SCRIPT):
        source = path.read_text(encoding="utf-8")
        assert 'resolve(runtimeRoot, "server.js")' in source
        assert "APP_NAME" in source
        assert "existsSync(nested" not in source
        assert "canonicalServer" not in source
    for path in (WEB_NEXT_CONFIG, ADMIN_NEXT_CONFIG):
        source = path.read_text(encoding="utf-8")
        assert "outputFileTracingRoot" in source
        assert "turbopack" in source
        assert "standalone" in source
