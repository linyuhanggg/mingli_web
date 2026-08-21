#!/usr/bin/env python3
"""Read-only: backend config / startup gate vs admitted signed V53.

Does not edit FastAPI, contracts, .runtime, or env files.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path("/Volumes/Lexar/code/mingli_web")
SIGNED = ROOT / ".runtime/v53-time-check-release"
MANIFEST = SIGNED / ".mingli-release-manifest.json"
CFG = ROOT / "backend/app/config.py"
ADAPT = ROOT / "backend/app/adapters/runtime.py"
POL = ROOT / "backend/app/readings/capability_policy.py"
PATHS = ROOT / "backend/tests/mingli_paths.py"
EXAMPLE_ENV = ROOT / "infra/fateradar-test.env.example"
LOCAL_ENV = Path.home() / ".config/mingli/local-real-model.env"
DESCRIBE = Path("/tmp/mingli-oneshot-v53-time-check-20260819/out/describe.stdout.json")

HEX64 = re.compile(r"[0-9a-f]{64}")


def grab_hex_after(text: str, name: str) -> str | None:
    i = text.find(name)
    if i < 0:
        return None
    m = HEX64.search(text[i : i + 400])
    return m.group(0) if m else None


def grab_quoted(text: str, name: str) -> str | None:
    m = re.search(rf'{re.escape(name)}\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def grab_int(text: str, name: str) -> int | None:
    m = re.search(rf"{re.escape(name)}\s*=\s*(\d+)", text)
    return int(m.group(1)) if m else None


def load_dotenv_keys(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def row(name: str, expected: object, actual: object, note: str = "") -> dict:
    ok = expected == actual
    return {
        "check": name,
        "align": bool(ok),
        "expected": expected,
        "actual": actual,
        "note": note,
    }


def main() -> int:
    man_bytes = MANIFEST.read_bytes()
    inspector = hashlib.sha256(man_bytes).hexdigest()
    man = json.loads(man_bytes)
    source = man.get("source_commit")
    nfiles = len(man.get("files") or {})

    describe_digest = None
    describe_caps = None
    if DESCRIBE.is_file():
        desc = json.loads(DESCRIBE.read_text(encoding="utf-8"))
        describe_digest = desc.get("manifest_digest")
        caps = desc.get("capabilities")
        if isinstance(caps, list):
            describe_caps = [
                c.get("id") if isinstance(c, dict) else c for c in caps
            ]

    cfg = CFG.read_text(encoding="utf-8")
    adapt = ADAPT.read_text(encoding="utf-8")
    pol = POL.read_text(encoding="utf-8")
    paths = PATHS.read_text(encoding="utf-8")
    example = EXAMPLE_ENV.read_text(encoding="utf-8") if EXAMPLE_ENV.is_file() else ""

    # profile block
    i = cfg.find('"v53-time-check"')
    # last/profile dict: search after _RUNTIME_RELEASE_PROFILES
    prof_i = cfg.find("_RUNTIME_RELEASE_PROFILES")
    j = cfg.find('"v53-time-check":', prof_i)
    sub = cfg[j : j + 700]
    cfg_describe = HEX64.search(sub[sub.find("manifest_digest") :]).group(0) if "manifest_digest" in sub else None
    # but manifest_digest is a name ref; use constant
    cfg_describe = grab_hex_after(cfg, "_V53_TIME_CHECK_DESCRIBE_MANIFEST_DIGEST")
    cfg_shape = HEX64.search(sub[sub.find("capability_shape_sha256") :]).group(0)
    cfg_inspector = HEX64.search(sub[sub.find("release_manifest_sha256") :]).group(0)
    cfg_source = re.search(r'"source_commit":\s*"([0-9a-f]+)"', sub).group(1)
    cfg_name = re.search(r'"release_name":\s*"([^"]+)"', sub).group(1)

    file_count = grab_int(adapt, "V53_TIME_CHECK_RELEASE_FILE_COUNT")
    default_profile = grab_quoted(cfg, "runtime_release_profile")
    if default_profile is None:
        m = re.search(r"runtime_release_profile:\s*RuntimeReleaseProfile\s*=\s*\"([^\"]+)\"", cfg)
        default_profile = m.group(1) if m else None

    prod_forbids_v53 = (
        'raise ValueError("selected Runtime release is local/test only")' in cfg
        and '"v53-time-check"' in cfg[cfg.find("if self.environment == \"production\""):]
    )
    leftover_53e = "53e200e1" in cfg or "53e200e1" in adapt
    v52_in_v53_block = "bef3df25" in sub
    v52_present_as_other_profile = "v52-relationship" in cfg and "bef3df25" in cfg

    map_ok = (
        '"v53-time-check": "v53-time-check-release"' in pol
        or '"v53-time-check":"v53-time-check-release"' in pol.replace(" ", "")
    )
    tests_default = ".runtime" in paths and "v53-time-check-release" in paths

    expected_caps = (
        "bazi",
        "fengshui",
        "fortune",
        "liuren",
        "liuyao",
        "luming-nayin",
        "meihua",
        "physiognomy",
        "qimen",
        "selection",
        "taiyi",
        "time-check",
        "xingming",
        "ziwei",
    )
    pol_has_time_check = '"time-check"' in pol[pol.find("V53_TIME_CHECK_RELEASE_CAPABILITY_IDS") : pol.find("P0_EXPOSED")]

    env = load_dotenv_keys(LOCAL_ENV)
    env_profile = env.get("MINGLI_RUNTIME_RELEASE_PROFILE")
    env_root = env.get("MINGLI_RUNTIME_RELEASE_ROOT")
    env_describe = env.get("MINGLI_RUNTIME_EXPECTED_MANIFEST_DIGEST")
    env_shape = env.get("MINGLI_RUNTIME_EXPECTED_CAPABILITY_SHAPE_SHA256")
    env_adapter = env.get("MINGLI_RUNTIME_ADAPTER")

    rows = [
        row("tree.inspector", inspector, inspector, "sha256(.mingli-release-manifest.json)"),
        row("config.v53.release_manifest_sha256", inspector, cfg_inspector, "backend/app/config.py profile"),
        row("config.v53.source_commit", source, cfg_source, "backend/app/config.py profile"),
        row("config.v53.release_name", "mingli-master-portable-core", cfg_name),
        row(
            "config.v53.describe_digest",
            describe_digest,
            cfg_describe,
            "matches 1994 describe.stdout.json + _V53_TIME_CHECK_DESCRIBE_MANIFEST_DIGEST",
        ),
        row("adapter.V53_TIME_CHECK_RELEASE_FILE_COUNT", nfiles, file_count, "backend/app/adapters/runtime.py"),
        row(
            "policy.map v53-time-check -> v53-time-check-release",
            True,
            map_ok,
            "backend/app/readings/capability_policy.py _LOCAL_RELEASE_DIRS",
        ),
        row(
            "policy.V53 caps include time-check (14)",
            True,
            pol_has_time_check,
        ),
        row(
            "tests.mingli_paths default release root",
            True,
            tests_default,
            "MINGLI_RUNTIME_TEST_RELEASE_ROOT defaults to .runtime/v53-time-check-release",
        ),
        row(
            "config has no leftover 53e200e1",
            False,
            leftover_53e,
            "old unsigned/wrong digest must stay absent",
        ),
        row(
            "v53 profile block has no V52 inspector",
            False,
            v52_in_v53_block,
            "bef3df25 must stay on v52-relationship only",
        ),
        row(
            "v52-relationship still a separate profile",
            True,
            v52_present_as_other_profile,
            "do not mix into V53 admission",
        ),
        row(
            "production forbids v53-time-check",
            True,
            prod_forbids_v53,
            "local/test only; production still v51 path",
        ),
        row(
            "Settings default runtime_release_profile is v51 (by design)",
            "v51",
            default_profile,
            "not a pin miss; live one-shot must set MINGLI_RUNTIME_RELEASE_PROFILE=v53-time-check",
        ),
        row(
            "local-real-model.env profile",
            "v53-time-check",
            env_profile,
            str(LOCAL_ENV),
        ),
        row(
            "local-real-model.env release root",
            str(SIGNED),
            env_root,
        ),
        row(
            "local-real-model.env adapter",
            "one-shot",
            env_adapter,
        ),
        row(
            "local-real-model.env expected describe digest",
            cfg_describe,
            env_describe,
            "STALE if != 3403992c; 3f8863b3 is 2026-08-17 G1 leftover",
        ),
        row(
            "local-real-model.env expected capability_shape",
            cfg_shape,
            env_shape,
            "STALE if != fb9da7fa; 3bf92ce5 is 2026-08-17 G1 leftover",
        ),
        row(
            "example env is fake (no V53 pin)",
            "fake",
            next(
                (
                    line.split("=", 1)[1].strip()
                    for line in example.splitlines()
                    if line.startswith("MINGLI_RUNTIME_ADAPTER=")
                ),
                None,
            ),
            "infra/fateradar-test.env.example placeholder stays fake; not a live pin",
        ),
        row(
            "describe capabilities == V53 14-set",
            list(expected_caps),
            describe_caps,
            "1994 describe.stdout.json",
        ),
    ]

    n_align = sum(1 for r in rows if r["align"])
    n_diff = sum(1 for r in rows if not r["align"])
    hard_pin_ok = all(
        r["align"]
        for r in rows
        if r["check"]
        in {
            "config.v53.release_manifest_sha256",
            "config.v53.source_commit",
            "config.v53.describe_digest",
            "adapter.V53_TIME_CHECK_RELEASE_FILE_COUNT",
            "policy.map v53-time-check -> v53-time-check-release",
            "config has no leftover 53e200e1",
            "v53 profile block has no V52 inspector",
        }
    )

    report = {
        "tree": {
            "inspector": inspector,
            "source_commit": source,
            "files": nfiles,
            "path": str(SIGNED),
        },
        "config_v53_profile": {
            "describe": cfg_describe,
            "capability_shape": cfg_shape,
            "inspector": cfg_inspector,
            "source": cfg_source,
            "release_name": cfg_name,
        },
        "hard_pin_ok": hard_pin_ok,
        "align": n_align,
        "diff": n_diff,
        "rows": rows,
    }

    print(f"TREE inspector={inspector}")
    print(f"TREE source={source}")
    print(f"TREE files={nfiles}")
    print(f"CFG describe={cfg_describe}")
    print(f"CFG shape={cfg_shape}")
    print(f"CFG inspector={cfg_inspector}")
    print(f"CFG source={cfg_source}")
    print(f"hard_pin_ok={hard_pin_ok}")
    print(f"align={n_align} diff={n_diff}")
    print("")
    print(f"{'ALIGN':<6} {'CHECK':<52} NOTE")
    for r in rows:
        flag = "OK" if r["align"] else "DIFF"
        print(f"{flag:<6} {r['check']:<52} {r['note']}")
        if not r["align"]:
            print(f"       expected={r['expected']}")
            print(f"       actual  ={r['actual']}")

    out_json = Path("/tmp/v53-backend-pin.json")
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON {out_json}")
    return 0 if hard_pin_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
