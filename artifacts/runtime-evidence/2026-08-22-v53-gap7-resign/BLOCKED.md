# T-0821-GAP-7 V53 重签 — BLOCKED

日期：2026-08-22 07:20 CST。未生成新制品，未改旧树。

## 现行签名树（回滚点，未动）

- 路径：`.runtime/v53-time-check-release`
- 目录 mtime：2026-08-18 20:27:41
- managed files：220（walk 221 = 220 + 清单）
- `source_commit`：`663543e65ae037843b03dca1dec9486293affc9d`
- 清单 SHA-256：`c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b`
- 备份仍在：`v53-time-check-release-before-g1-20260818/`、`v53-time-check-release-before-k-20260818/`
- 签名 `scripts/reading_engine/providers.py` **不含** `bazi.pillar-roles-v1` / `bazi.three-yuan-structure-v1` / `bazi.element-flow-inventory-v1`

## 源码 vs 制品漂移（实测）

`python3 -B artifacts/runtime-evidence/2026-08-19-v53-core-signed-filediff.py`

- signed_walk=220 / both=220 / same_hash=213 / **diff_hash=7**
- 七文件：`resources/runtime/providers/time-check.json`、`resources/runtime/providers/ziwei.json`、`scripts/bazi_fact_adapter.py`、`scripts/bazi_reasoning_tools.py`、`scripts/fact_contracts/bazi.py`、`scripts/reading_engine/providers.py`、`scripts/reading_evidence_bundle.py`
- 其中后两份 + `scripts/test_v51_bazi_public_claim_units.py` 相对父仓 HEAD `35151ace9e2e6f181c4fe05fc9f652ae95756d08` **未提交**（GAP-1，+229/−10）
- 前五份已在父仓移植提交 `35151ace` 内，相对签名 `663543e65ae037843b03dca1dec9486293affc9d` 仍漂移

## 源码测试（绿，未进制品）

```
cd core/mingli-master/scripts && PYTHONDONTWRITEBYTECODE=1 \
  ~/.local/share/mingli-master/venv/bin/python -m unittest test_v51_bazi_public_claim_units -v
```

Ran 2 tests in 1.045s：**OK**。公开深读默认查询金样发射 7 个 Claim Unit，含 GAP-1 三新单元。

## 门禁实测失败

1. `make mingli-core-status` → `core_source=missing_or_not_git:.../core/mingli-master`（exit 2）。`core/mingli-master/.git` 不存在。
2. `core/README.md`：移植时原版 `.git` 挪到 `core/.mingli-master-skill.git/`，故意不再让 core 像独立仓库。该备份 HEAD = `663543e…`（与现行签名同一提交，**无 GAP-1**）。
3. `git -C core/mingli-master` 上溯父仓。父仓 HEAD `35151ace`「chore(git): track transplanted mingli-master source」；工作树大量他单未提交 diff。
4. `release_deploy.py --source core/mingli-master --destination .runtime/v53-time-check-release-gap7-20260822 --research-root ~/.codex/skills/mingli-master`（无 `--apply`）→ `release deployment failed: source worktree must be clean before deployment`。**新目录未创建**。
5. `require_clean_source` 看的是 `git -C source status`；无嵌套 git 时看到整棵脏父仓。即使只想签 GAP-1，本单禁止 commit / reset / stash。

## 未做（避免伪造）

- 未手改 `.runtime/**`
- 未在脏树或临时提交上编造 `source_commit`
- 未跑新树 describe / evidence-index / 7 单元制品探针（没有新树）
- 未改 `scripts/verify_frozen_runtime_release.py` 钉死的旧哈希

## 解开条件（交项目经理）

必须同时满足，且需**明确授权 commit**（本单目前禁止）：

1. 嵌套 git：或恢复 `core/mingli-master/.git` 指向 `core/.mingli-master-skill.git`（与 `core/README.md` 移植政策冲突，需裁决），或把门禁改为认父仓 git（要改门禁脚本，本单未做）。
2. 把 GAP-1 三文件打进该 git 的真实 commit；若嵌套 git 停在 `663543e`，还需纳入上述另外 5 个已在父仓 HEAD 的漂移文件，否则新树仍与可见源码不一致。
3. 父仓其余脏文件保持不动；用嵌套 git 或独立 worktree，使 `require_clean_source` 只看到 core 干净树。
4. 再走 `release_deploy.py` 写**新目录**，旧 `.runtime/v53-time-check-release` 不动。Lexar exFAT `noowners` 下 G1 曾遇 0644→0700；若 CLI `--apply` 因 mode 回滚，仍只用同一模块的 `build_manifest` + `sync_destination`，禁止手改。
