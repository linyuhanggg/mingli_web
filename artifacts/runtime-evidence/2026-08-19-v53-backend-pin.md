# 2026-08-19 backend 配置/启动门禁 vs 准入 V53（只读）

准入树仍是 `.runtime/v53-time-check-release`：inspector `c451de5e…` / source `663543e…` / 220 文件。
本笔记只对照，不改 FastAPI、不改合同、不覆盖 `.runtime`、不 resign、不改 env。

## 复跑

```bash
python3 /Volumes/Lexar/code/mingli_web/artifacts/runtime-evidence/2026-08-19-v53-backend-pin.py
```

实跑：`hard_pin_ok=True`，21 项里 19 对齐、2 差异。stdout 见同目录 `2026-08-19-v53-backend-pin.stdout.txt`。

## 代码门禁：对齐

`backend/app/config.py` 的 `_RUNTIME_RELEASE_PROFILES["v53-time-check"]` 钉死：

| 字段 | 值 | 对照树 |
|---|---|---|
| `release_manifest_sha256` | `c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b` | inspector 对齐 |
| `source_commit` | `663543e65ae037843b03dca1dec9486293affc9d` | manifest.source_commit 对齐 |
| `manifest_digest`（describe） | `3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc` | 1994 describe 对齐 |
| `capability_shape_sha256` | `fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042` | 写在 profile 里 |
| `release_name` | `mingli-master-portable-core` | 对齐 |

`backend/app/adapters/runtime.py`：

- `V53_TIME_CHECK_RELEASE_FILE_COUNT = 220`（对上树）
- `build_runtime_startup_gate`：profile ≠ v51 时，env 里的 expected describe / shape 必须等于上表，否则 `RuntimeStartupError`
- `FileSystemRuntimeReleaseInspector` 再核 inspector / source / 文件数 / capability ids
- `OneShotMingliRuntimeAdapter` 再核 describe digest + capability shape

`backend/app/readings/capability_policy.py`：`v53-time-check` → `.runtime/v53-time-check-release`；V53 capability 14 项含 `time-check`。
`backend/tests/mingli_paths.py`：测试默认 release root 就是这棵树。

没混：config 无 `53e200e1`；`bef3df25` 只在 `v52-relationship` 另一档，不进 V53 profile。
production 禁止 `v53-time-check`（local/test only）。Settings 默认 `runtime_release_profile=v51`，这是设计，不是钉错；live one-shot 必须自己设 `MINGLI_RUNTIME_RELEASE_PROFILE=v53-time-check`。

## 差异：Mac mini 私有 smoke env 过期

`~/.config/mingli/local-real-model.env`（仓库外，未改）：

| 键 | 现状 | 应对齐 |
|---|---|---|
| `MINGLI_RUNTIME_RELEASE_PROFILE` | `v53-time-check` | 对齐 |
| `MINGLI_RUNTIME_RELEASE_ROOT` | Lexar `.runtime/v53-time-check-release` | 对齐 |
| `MINGLI_RUNTIME_ADAPTER` | `one-shot` | 对齐 |
| `MINGLI_RUNTIME_EXPECTED_MANIFEST_DIGEST` | `3f8863b3…`（2026-08-17 G1 残留） | 应为 `3403992c…` |
| `MINGLI_RUNTIME_EXPECTED_CAPABILITY_SHAPE_SHA256` | `3bf92ce5…`（同上） | 应为 `fb9da7fa…` |

用这份 env 直接走 `build_runtime_startup_gate` 会因 digest ≠ profile 被拒。后端 live Worker 当天已按 `c451de5e` / `663543e` 过阶段 M，说明 Worker 没用这份过期 expected，或另有覆盖。本刀不改这份 env。

`infra/fateradar-test.env.example` 仍是 `MINGLI_RUNTIME_ADAPTER=fake`，占位，不是 live pin。

## 裁定建议

- 仓库里的 backend 门禁仍钉 `c451de5e` / `663543e` / 220 / describe `3403992c`。不 resign，不改 FastAPI。
- 过期的是本机 smoke env 两个 expected 字段，不是代码。要不要改 env 是消费/后端的刀。

## 2026-08-19 17:47 本机 env 对齐

只改了 `~/.config/mingli/local-real-model.env` 两个 expected：
- `MINGLI_RUNTIME_EXPECTED_MANIFEST_DIGEST` → `3403992cb31aebea19e69ec3b1280a5ef02718c5f9ca3e3f94448ef7b039facc`
- `MINGLI_RUNTIME_EXPECTED_CAPABILITY_SHAPE_SHA256` → `fb9da7fa1969e449e91222a0f10a2076da2e8cca43d1083b531aa218ff31e042`

profile / root / adapter 未动。mode 仍 600。仓库和 `.runtime` 未动。
复跑 pin：`hard_pin_ok=True`，`align=21` `diff=0`。那两项不再漂移。
