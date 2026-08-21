# 命理大师 V5.1 模型选术与无资料降级 — Release Evidence

## 1. 审查范围与基线

- 工作树：`<mingli-master-worktree>`
- 分支：`claude/mingli-model-selection-fallback`
- fixed base：`2e9c8a4920313510e5cb9a4341c8425499df6fed`
- 本次接手起点：`b124825c444f5c48c8245669465c99fa99565c1f`
- 本次没有修改、重置或清理旧权威树，也没有重写既有提交。

本次追加提交：

1. `0d5cbf4 test: expose complete model-selection transaction gaps`
2. `f5dea73 test: reject capability switch during transition`
3. `95ecb72 fix: make model-selection transactions recoverable`
4. `d18d448 docs: define model-selected fallback contract`
5. 本文档由最后一个 evidence-only 提交保存。

## 2. 最终行为结论

- 宿主模型只依据缓存的 `describe` 选择 capability；通用 core 和
  `SKILL.md` 没有真实术数名称、关键词表、别名表或按资料最少选术。
- capability 的专业说明只位于各自 manifest；13 个 Provider 的算法、
  语料和确定性计算体系没有重写。
- 显式 capability 缺资料只产生该能力的 `NeedInput` 与 opaque token；
  核心不循环试其他 Provider。用户无法补资料时，宿主最多改选一次，
  丢弃 pending token 后以无 token 新建独立根。
- `IntentSelection.comparisons` 是唯一新写入格式；每项显式区分
  `required` / `optional`。旧 `comparison_capability_ids` 只在读取历史
  pending 状态时迁移为 required，不再出现在新接口文档。
- comparison 解析使用逐轮冻结的 `ResolvedComparison`，不再修改共享
  catalog descriptor。optional comparison 在多主体场景中整体原子成功
  或整体跳过，失败留下 `limit.comparison_skipped`，不会泄漏部分结果。
- required comparison 的 `NeedInput → supplement → Prepared → Accepted`
  已可恢复；pending 状态同时保存 capability 与 requirement。
- 无 token 的相同请求是两个独立用户轮次，各建新根；token replay 才
  提供幂等。scope 或 capability 切换不占用旧 lineage 槽位。
- `correct` / `restart` 不能同时改换主体、对象或 capability；矛盾请求
  返回非空 `Stopped.conflict`。
- publishability 统一检查 fact、evidence、claim scope、finding 和 limit
  的引用闭包。没有事实或 claim scope 返回非空 `Stopped.unsupported`；
  内部断链返回非空 `Stopped.error`；零证据但有合法 scope 时保留
  `Prepared` 并加入 `limit.source_gap`。
- `Accepted.public_copy` 仍是最终结果；本次没有增加外部验签、observer、
  sidecar、Gateway 命理分支或第二层交付拦截。

## 3. 快速门禁（通过）

固定运行时：

```text
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=scripts
$HOME/.local/share/mingli-master/venv/bin/python -B
```

### P1 专项

```text
python -m unittest scripts.test_v51_p1_rework
```

- exit code：`0`
- 结果：`Ran 32 tests in 0.080s — OK`
- 覆盖：独立新根、无 token 重复请求、transition 冲突、pending engine
  seam、required comparison 恢复、旧 pending 迁移、optional 原子降级、
  publishability 引用闭包、生产 manifest 描述。

### 接口与跨宿主组合回归

```text
python -m unittest \
  scripts.test_v51_p1_rework \
  scripts.test_v51_model_selection_fallback \
  scripts.test_v51_catalog_driven_registry \
  scripts.test_v51_portable_interface \
  scripts.test_v4_followup_state \
  scripts.test_v51_closed_world_brief \
  scripts.test_v51_cross_host_contract \
  scripts.test_v4_skill_minimalism \
  scripts.test_v51_release_surface \
  scripts.test_v51_conversation_contract \
  scripts.test_v4_request_contract \
  scripts.test_single_authority_contract
```

- exit code：`0`
- 结果：`Ran 163 tests in 10.451s — OK`

### 架构审计

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `python scripts/audit_v51_vocabulary_locality.py --check` | 0 | `ok: true`，`findings: []` |
| `python scripts/audit_release_archive.py --source .` | 0 | `ok: true`，`file_count: 212`，`surface: mingli-runtime-closure-v1` |

## 4. 慢速全仓库结果（基线不通过，未掩盖）

```text
python -m unittest discover -s scripts -p 'test_*.py'
```

- exit code：`1`
- 结果：`Ran 1286 tests in 3479.683s`
- 汇总：`FAILED (failures=35, errors=59)`
- 错误的共同根因：仓库中的 source locator 明确落到
  `__missing_external_research__/references/fulltext/...`，当前工作树不含
  这些外部古籍全文，因此精确行号/哈希绑定测试抛 `FileNotFoundError`。
- 失败的共同根因：依赖上述来源绑定的 Provider completeness/readiness
  返回 false，包括 source hash、classical witness、research source
  verification 等检查。
- 本次 163 项接口、事务、跨宿主与 skill-locality 组合测试全部通过；
  全量输出未显示本次 model-selection / fallback 状态机的新失败。

独立执行：

```text
python scripts/audit_provider_completeness.py --check
```

- exit code：`1`
- 终端摘要：`provider matrix differs from the canonical live snapshot`
- fixed base 的既有 release evidence 记录了同形态失败。本次没有运行
  `--write`，没有伪造 readiness，也没有为了通过审计搬入外部语料。

这些缺口属于既有 Provider 研究来源闭包，不在本次“模型选术与无资料
降级”事务返工范围内；它们仍是独立发布风险，不应被解释为已解决。

## 5. 非生产副作用证明

- 未运行部署、安装、provision 或 runtime launcher。
- 未修改已安装的 Codex/Hermes skill 副本。
- 未启动、停止或重启 Gateway；最终检查 PID 仍为 `64543`，启动时间仍
  为 `Thu Jul 30 12:08:42 2026`。
- 未访问、监听或绑定生产端口 `8642` / `8645`。
- 未 push 远端。
- 未加入 LLM API、模型供应商、Hermes 私有接口、Gateway import、
  observer、guard、外部摘要验签或第二套账本。

## 6. 交付判定

本次返工范围通过：外部协议保持 `execute(Command) -> Result`，新请求、
补资料、比较、续问、纠正、重起、零证据和内部断链都有确定且非空的
结果；宿主负责语义选择，核心负责结构、状态、确定性计算和原子提交。

全仓库尚不能宣称“所有 Provider 研究来源已闭包”：缺失外部全文与
provider readiness 基线仍为红，必须作为后续独立工作处理。
