# T-0821-GAP-7 V53 重签 — DONE

日期：2026-08-22 07:43 CST。用户裁决：认父仓 git，只提交 GAP-1 + 门禁，写新 runtime 目录。

## 新制品（回滚点仍是旧树）

- 新路径：`.runtime/v53-time-check-release-gap7-20260822`
- 清单 SHA-256：`d45bb86d88b13daf50aa62ea7ee699c291dde5cd480fd76205a27371cd21bb3b`
- `source_commit`：`025511b782e9d6a22cd675e3e1a6ee9df96ffa25`
- 受管文件：221（+ 清单 = 222 个普通文件）
- 旧 `.runtime/v53-time-check-release`：mtime 仍为 2026-08-18 20:27:41，`source_commit` 仍为 `663543e65ae037843b03dca1dec9486293affc9d`，未手改

## 父仓 commit（用户已授权，未 push）

`025511b` `fix(core): sign bazi claim units from the parent-repo commit`

只纳入：

- `core/mingli-master/scripts/reading_engine/providers.py`
- `core/mingli-master/scripts/reading_evidence_bundle.py`
- `core/mingli-master/scripts/test_v51_bazi_public_claim_units.py`
- `core/mingli-master/scripts/release_deploy.py`
- `core/mingli-master/scripts/test_release_deploy.py`
- `scripts/check_mingli_core_workspace.py`

未纳入（与 Claim Unit 无关，不阻塞重签，因为不在 runtime closure）：姓名分析 / 解梦 / 相法 / 跨术合成的 fixtures、矩阵、provider 与合同测试。五术 UI 脏文件未动。

## 门禁收窄（未放宽哈希/签名）

- `make mingli-core-status` 认父仓：`core_source=.../core/mingli-master`，`core_git_root=/Volumes/Lexar/code/mingli_web`
- `release_deploy.require_clean_source` 只检查 runtime closure 路径 + 门禁脚本；父仓其余脏路径忽略
- `ls-files` / `ls-tree` 按 `core/mingli-master/` 前缀剥离，制品路径仍相对 core 根
- `test_release_deploy.py` 25 tests OK（含父仓子目录用例）

## 部署过程

1. CLI `--apply` 用 venv Python 跑完 13 路源码核验，随后 `mode mismatch: SKILL.md expected 644, got 700` 回滚。新目录只留下空目录。旧树未覆盖。
2. 按派单：仍只用同一模块的 `build_manifest` + `sync_destination`。清单 mode 取工作树 `0700`（本卷 noowners 与 G1 旧制品一致），`verified=True`，复制 221 文件。未手改字节。

## 验证（对新路径）

- describe：`kind=described`，14 capabilities：bazi / fengshui / fortune / liuren / liuyao / luming-nayin / meihua / physiognomy / qimen / selection / taiyi / time-check / xingming / ziwei
- 证据索引：`python scripts/build_evidence_index.py --check` → `{"status": "pass", "records": 1328}`
- 默认深读「请围绕事业主线生成八字结构化深读。」（乙酉/辛巳/丙午/癸巳）：7 个带 `public_text` 的 Claim Unit 全发射：
  - `bazi.month-order-state-v1`
  - `bazi.day-master-root-support-v1`
  - `bazi.ziping-pattern-entry-v1`
  - `bazi.tiaohou-priority-v1`
  - `bazi.pillar-roles-v1`
  - `bazi.three-yuan-structure-v1`
  - `bazi.element-flow-inventory-v1`

制品 `providers.py` 含三新 id。未改 `scripts/verify_frozen_runtime_release.py` 钉死的旧哈希。

## 默认 status 脚本

`check_mingli_core_workspace.py` 默认仍对照旧 `.runtime/v53-time-check-release`，会报相对旧树 7 文件漂移。这是预期：本单不切换默认 runtime 指针。
