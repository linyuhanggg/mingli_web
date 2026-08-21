#!/usr/bin/env python3
"""Freeze a raw annual Yang source projection from one fixed kintaiyi checkout.

This generator never imports or executes the upstream package. It parses the
fixed source literals used by the annual Yang-board implementation and replays
two explicitly labelled derivations, preserving exact code origins and known
disagreements for later canonical replay.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "references/fixtures/kintaiyi-taiyi-v51.yaml"
COMMIT = "68892c6bfe3a9635ff4a19a5f14559fff1adf4ab"
REPOSITORY = "https://github.com/kentang2017/kintaiyi"
IMPLEMENTATION_SHA256 = "042f7118ebeb5f10e2464f55463e8bf35c4736eecef6e3816f97a1391ac65f5e"
CONFIG_SHA256 = "c5766a6435c91c82bd6241cf73c7852325cd432a820d5c227887b1137050510e"
LICENSE_SHA256 = "098b60569fd0fa7dd7b320ec29c62d778ffe6f0d76107de061056e6f4475de24"
BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _safe_literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Call):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "list"
            and len(node.args) == 1
            and not node.keywords
        ):
            return list(_safe_literal(node.args[0]))
        raise ValueError("unsupported source call in frozen projection")
    if isinstance(node, ast.Dict):
        return {
            _safe_literal(key): _safe_literal(value)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.List):
        return [_safe_literal(item) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_safe_literal(item) for item in node.elts)
    return ast.literal_eval(node)


def _assignment(tree: ast.AST, name: str, *, scope: str | None = None) -> Any:
    nodes: list[ast.AST] = list(getattr(tree, "body", ()))
    if scope is not None:
        selected = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == scope
        )
        nodes = list(selected.body)
    for node in nodes:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return _safe_literal(node.value)
    raise ValueError(f"missing fixed upstream assignment: {scope or '<module>'}.{name}")


def _one_based_mod(value: int, modulus: int) -> int:
    return (value - 1) % modulus + 1


def _year_branch(lunar_year: int) -> str:
    return BRANCHES[(lunar_year - 4) % 12]


def _jishen(year_branch: str) -> str:
    reversed_branches = list(reversed(BRANCHES))
    start = reversed_branches.index("寅")
    rotated = reversed_branches[start:] + reversed_branches[:start]
    return dict(zip(BRANCHES, rotated))[year_branch]


def _git_commit(upstream_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=upstream_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_projection(upstream_root: Path) -> dict[str, Any]:
    implementation = upstream_root / "src/kintaiyi/kintaiyi.py"
    config = upstream_root / "src/kintaiyi/config.py"
    license_path = upstream_root / "LICENSE"
    identities = (
        (_git_commit(upstream_root), COMMIT, "commit"),
        (_sha256(implementation), IMPLEMENTATION_SHA256, "implementation"),
        (_sha256(config), CONFIG_SHA256, "config"),
        (_sha256(license_path), LICENSE_SHA256, "license"),
    )
    for actual, expected, label in identities:
        if actual != expected:
            raise ValueError(f"kintaiyi {label} identity mismatch: {actual}")

    implementation_tree = ast.parse(implementation.read_text(encoding="utf-8"))
    config_tree = ast.parse(config.read_text(encoding="utf-8"))
    offsets = _assignment(implementation_tree, "tndict", scope="accnum")
    offset = int(offsets[1])
    taiyi_palaces = list(_assignment(config_tree, "taiyi_pai"))
    wanchang_positions = _assignment(config_tree, "skyeyes_dict")["陽"]
    shiji_positions = _assignment(config_tree, "sf_list")
    calculations = _assignment(config_tree, "yangcal", scope="find_cal")
    if not all(
        len(values) == 72
        for values in (
            taiyi_palaces,
            wanchang_positions,
            shiji_positions,
            calculations,
        )
    ):
        raise ValueError("kintaiyi annual Yang-board literals are not complete")

    raw_cases = []
    for bureau in range(1, 73):
        lunar_year = 1899 + bureau
        accumulated_year = lunar_year + offset
        resolved_bureau = _one_based_mod(accumulated_year, 72)
        if resolved_bureau != bureau:
            raise ValueError("selected projection years no longer map to bureaus 1..72")
        host, guest, fixed = (int(value) for value in calculations[bureau - 1])
        raw_cases.append(
            {
                "id": f"kintaiyi-raw-bureau-{bureau:02d}",
                "input": {"lunar_year": lunar_year},
                "raw": {
                    "accumulated_year": accumulated_year,
                    "bureau": bureau,
                    "taiyi_palace_literal": taiyi_palaces[bureau - 1],
                    "wenchang_position_literal": wanchang_positions[bureau - 1],
                    "shiji_position_literal": shiji_positions[bureau - 1],
                    "host_count_literal": host,
                    "guest_count_literal": guest,
                    "fixed_count_literal": fixed,
                    "jishen_mapping": _jishen(_year_branch(lunar_year)),
                },
            }
        )

    return {
        "schema_version": "kintaiyi-taiyi-raw-v1",
        "source": {
            "repository": REPOSITORY,
            "commit": COMMIT,
            "license": "MIT",
            "license_path": "LICENSE",
            "license_sha256": LICENSE_SHA256,
            "implementation_path": "src/kintaiyi/kintaiyi.py",
            "implementation_sha256": IMPLEMENTATION_SHA256,
            "config_path": "src/kintaiyi/config.py",
            "config_sha256": CONFIG_SHA256,
            "role": "raw engineering comparator only; never classical authority",
        },
        "generator": {
            "path": "scripts/fixtures/kintaiyi_taiyi_fixture_generator.py",
            "sha256": _sha256(Path(__file__)),
            "execution": "AST literal projection; upstream package is never imported or executed",
        },
        "projection_contract": {
            "annual_method": "金镜年计阳遁",
            "projection_kind": "static source projection with literal tables and labelled derivations; not pan() output",
            "upstream_origins": {
                "accumulated_year": "Taiyi.accnum tndict[1] plus lunar year",
                "bureau": "Taiyi.kook annual modulus",
                "taiyi_palace_literal": "config.taiyi_pai via Taiyi.ty_gong; pan field 太乙",
                "wenchang_position_literal": "config.skyeyes_dict[陽] via Taiyi.skyeyes",
                "shiji_position_literal": "config.sf_list via Taiyi.sf",
                "host_count_literal": "config.find_cal yangcal row 0; annual Yang 立成",
                "guest_count_literal": "config.find_cal yangcal row 1; annual Yang 立成",
                "fixed_count_literal": "config.find_cal yangcal row 2; annual Yang 立成",
                "jishen_mapping": "derived by replaying Taiyi.__init__ jigod_map with the annual branch",
            },
            "raw_to_canonical_mapping": {
                "bureau": "bureau",
                "taiyi_palace_literal": "taiyi",
                "wenchang_position_literal": "tianmu_position",
                "shiji_position_literal": "shiji",
                "host_count_literal": "host_count",
                "guest_count_literal": "guest_count",
                "jishen_mapping": "jishen",
            },
            "known_primary_source_differences": [30, 44, 66],
        },
        "raw_cases_sha256": _canonical_sha256(raw_cases),
        "raw_cases": raw_cases,
    }


def _render(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = _render(build_projection(args.upstream_root.resolve()))
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit("frozen kintaiyi projection is stale")
        print("kintaiyi raw projection: OK")
        return 0
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output} with 72 raw cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
