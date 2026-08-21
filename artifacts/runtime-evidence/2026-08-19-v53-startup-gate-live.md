# 2026-08-19 已对齐 env 实跑启动门禁

不改仓库，不覆盖 `.runtime`，不改合同，不 resign。
env：`~/.config/mingli/local-real-model.env`（digest `3403992c` / shape `fb9da7fa`）。

## 命令

仓库根目录下的官方 smoke 脚本会被本机绑定拦住，改用等价路径：`Settings()` 读这份 env → `build_runtime_startup_gate` → `gate.startup()`。

```bash
cd /Volumes/Lexar/code/mingli_web/backend
uv run python -c '
import asyncio, os
from pathlib import Path
env = Path.home()/".config/mingli/local-real-model.env"
for line in env.read_text(encoding="utf-8").splitlines():
    s=line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k,v=s.split("=",1)
    os.environ[k.strip()]=v.strip().strip("\"").strip("\x27")
from app.config import Settings
from app.adapters.runtime import (
    RuntimeStartupError,
    build_runtime_startup_gate,
    runtime_capability_shape_sha256,
)
async def main():
    settings = Settings()
    print("adapter", settings.runtime_adapter)
    print("profile", settings.runtime_release_profile)
    print("release_root", settings.runtime_release_root)
    print("expected_describe", settings.runtime_expected_manifest_digest)
    print("expected_shape", settings.runtime_expected_capability_shape_sha256)
    try:
        described = await build_runtime_startup_gate(settings).startup()
    except RuntimeStartupError as exc:
        print("GATE REJECTED"); print("error", exc); return 3
    print("GATE OK")
    print("describe_digest", described.manifest_digest)
    print("describe_shape", runtime_capability_shape_sha256(described.capabilities))
    print("capability_count", len(described.capabilities))
    return 0
raise SystemExit(asyncio.run(main()))
'
```

等价官方入口（未在本机直接跑通 `.sh` 绑定）：`scripts/run_local_real_runtime_smoke.sh --skip-model`。

## 结果

| 项 | 值 |
|---|---|
| GATE | OK（未因 digest/shape 被拒） |
| adapter | `one-shot` |
| profile | `v53-time-check` |
| release_root | `/Volumes/Lexar/code/mingli_web/.runtime/v53-time-check-release` |
| expected describe | `3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc` |
| describe digest | 同上 |
| expected shape | `fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042` |
| describe shape | 同上 |
| capability_count | 14 |

未改 FastAPI、未覆盖 `.runtime`、未改合同。
