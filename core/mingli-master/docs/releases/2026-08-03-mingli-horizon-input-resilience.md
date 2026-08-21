# 命理大师 V5.1 近时范围输入韧性 — Release Evidence（返工）

日期：2026-08-03
分支：`claude/mingli-horizon-resilience-rework-20260803`
工作树：`~/Documents/Codex/2026-08-02/mingli-master-horizon-resilience-rework`
base commit：`2ed239f86ea774b326ee8ebd9dbe034192833a4d`

## 1. 返工背景

上一版 `claude/mingli-horizon-resilience-20260803`（HEAD `3965762`，
旧工作树 `~/Documents/Codex/2026-08-02/mingli-master-judgment-voice`）
被 Codex 拒收，阻塞点：

1. **P1 end-only 单锚点被忽略。** 旧 `_near_time_period_days` 用
   `anchor = start if start is not None else fallback_anchor`，且
   `_target_date` 入口条件是 `horizon.kind == "day" and horizon.start`。
   公开接口已复现：`day` + `start=null` +
   `end=2026-08-05T14:00:00+08:00` 返回 Prepared，但真正计算的是
   `2026-08-03`（reference 民用日），而 `request_view` 仍保留 8 月 5 日
   边界——静默错算；相同形状用于 week 返回 `Stopped.error`。
2. **P2 日期格式闭集被意外放宽。** 旧 `_civil_day` 依赖
   `date/datetime.fromisoformat` 判断格式，后者还接受 `20260803`、
   `2026-W32-1`、`20260803T100000` 等未声明格式，扩大了公开契约。
3. **提交切分不合格。** 旧 `docs:` 提交混入 SKILL.md、Provider manifest、
   vocabulary audit 与 plan/release 文档。

旧分支只读保留，未修改、未删除、未重写。本返工在新工作树从固定基线
`2ed239f` 重新建立干净分支，按正确提交边界重新实现。

### 1b. 第二次验收后的极小返工

第二次验收（2026-08-03）确认主问题已修复，但严格输入闭集仍有一处遗漏：

1. **P2（阻断）**：`_civil_day` 先 `text.strip()` 再校验，`" 2026-08-05 "`
   被静默修正进入 `Prepared`。已改为对原始完整字符串严格检查，不预先
   `strip()`；带首尾空白、纯空白的边界返回带非空 `public_copy` 的
   `Stopped`。
2. **P3（非阻断）**：datetime 正则 `[T ]` 曾接受空格分隔
   `2026-08-05 14:00:00+08:00`。已将公开闭集明确为只接受 `T` 分隔符，
   空格分隔形式返回 `Stopped`。

新增测试：两侧首尾空白、纯空白边界、空格分隔 datetime 的公开接口拒绝
用例，新套件由 49 项增至 52 项。

## 2. 开工检查（新 worktree，首次修改前）

```text
git status --short --branch   -> ## claude/mingli-horizon-resilience-rework-20260803
git rev-parse HEAD            -> 2ed239f86ea774b326ee8ebd9dbe034192833a4d
git diff --stat               -> (空)
```

HEAD 等于基线、工作树 clean、diff 为空。没有 reset / rebase / stash /
clean / amend / 强推 / 删除旧分支。

## 3. 最终归一化规则

单个边界 → 民用日：

- `YYYY-MM-DD` 本身即民用日期，按字面取用。先对**原始完整字符串**做严格
  格式检查（`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`），再交 `date.fromisoformat`
  验证真实年月日；不预先 `strip()`。
- 其他必须是完整 ISO-8601 datetime：严格扩展日期前缀 + `T` 分隔符 +
  明确时间部分（不接受空格分隔）。带时区（偏移或 `Z`）先换算到业务时区
  再取日期；naive 按业务时区解释。`2026-08-03T20:00:00Z` 在
  `Asia/Shanghai` 是 `2026-08-04`。
- `20260803`、`2026-W32-1`、`20260803T100000`、`2026-08`、自然语言、
  **带首尾空白的日期/时刻**、**纯空白边界**、**空格分隔 datetime** 一律
  返回非空 `Stopped`，不猜测周期、不静默修正输入。
- 只有 `None` 或空字符串 `""` 才视为"未提供该边界"（与 null 等价）。

范围成立条件：

- **一个锚点**（边界全空 / 只给 start / 只给 end / 两个边界归一化后同一
  民用日）= 包含该锚点的完整周期。同一天 `00:00:00`–`23:59:59` 描述的就是
  这一天，不是"只有一天的周"。
- **两个不同民用日**按字面取用，且必须已正好构成该周期（周 = 连续七日）；
  三日、八日、倒序返回非空 `Stopped`，不扩大、不截断、不改写。
- 只有 start/end 都为空时，才使用 `reference_datetime` 的民用日期；
  `reference_datetime` 本身仍是完整参考时刻。

Locality：归一化位于近时 Provider 私有函数 `_near_time_period_days`，
`calculate()` 与 `extend()` **共用同一个**函数，因此
`Prepared.brief.request_view.horizon` 公布的有效范围必然等于真正排过盘的
范围。generic core 未按领域 ID 分支。

## 4. 行为对照（参考时刻 `2026-08-03T10:00:00+08:00`，业务时区 `Asia/Shanghai`）

| 调用形状 | 上一版（拒收前） | 本版 |
| --- | --- | --- |
| 日 + end-only `2026-08-05T14:00:00+08:00` | **Prepared 但算 08-03、view 指 08-05（静默错算）** | **Prepared，view=target=08-05** |
| 周 + end-only `2026-08-05T14:00:00+08:00` | **Stopped.error** | **Prepared `08-03..08-09`** |
| 周 + 同一民用日首尾时刻 | Prepared `08-03..08-09` | 不变 |
| 周 + start-only 锚点 `2026-08-06` | 上一版已修复 | Prepared `08-03..08-09` |
| 周 + 空边界 | Prepared `08-03..08-09` | 不变 |
| 日 + 两个不同民用日 | Stopped | Stopped（保持） |
| `20260803` / `2026-W32-1` / `20260803T100000` | 被旧实现静默接受 | **非空 Stopped** |
| `" 2026-08-05 "`（首尾空白） | **被静默修正为 Prepared** | **非空 Stopped** |
| `"   "`（纯空白边界） | **被当作未提供并 Prepared** | **非空 Stopped** |
| `2026-08-05 14:00:00+08:00`（空格分隔） | **被接受为 Prepared** | **非空 Stopped** |
| `2026-08` / 自然语言 | Stopped | Stopped（保持） |
| 三日 / 八日 / 倒序周范围 | Stopped | Stopped（保持） |

合法 date 与 datetime 输入得到**同一个**有效周：新测试
`test_date_and_datetime_inputs_agree_on_the_same_effective_week` 断言
8 种拼写（含 end-only 与 `Z` 锚点）全部收敛到 `week 2026-08-03..2026-08-09`。

### day/week end-only 实际结果摘要

```text
day  end-only 2026-08-05T14:00:00+08:00 ->
  request_view.horizon.start = 2026-08-05
  request_view.horizon.end   = 2026-08-05
  target_day                 = 2026-08-05

week end-only 2026-08-05T14:00:00+08:00 ->
  request_view.horizon.start = 2026-08-03
  request_view.horizon.end   = 2026-08-09
  available_periods          = 2026-08-03 ... 2026-08-09
```

### strict format 拒绝结果

```text
week + 20260803        -> Stopped（非空 public_copy）
week + 2026-W32-1      -> Stopped（非空 public_copy）
week + 20260803T100000 -> Stopped（非空 public_copy）
week + 2026-08         -> Stopped（非空 public_copy）
week + "这周"          -> Stopped（非空 public_copy）
day  + end=20260803    -> Stopped（非空 public_copy）
day  + " 2026-08-05 "  -> Stopped（非空 public_copy）
week + "   "           -> Stopped（非空 public_copy）
day  + "2026-08-05 14:00:00+08:00" -> Stopped（非空 public_copy）
```

## 5. 修改文件

- `SKILL.md` — 只增加对所有 Provider 通用的调用纪律（时间范围提交方式、
  `stopped` 四种原因的不同处理、对用户可见内容）。未出现任何真实术数
  名称、`object_id`、`capability_id`、别名表或触发词。
- `scripts/reading_engine/providers.py` — 近时 Provider 私有归一化
  （`_strict_civil_date`、`_strict_iso_datetime`、`_civil_day`、
  `_near_time_period_days`），严格格式 + 单锚点（start/end 任一），
  `calculate` 与 `extend` 共用。
- `resources/runtime/providers/fortune.json` — 对应 horizon term 的
  `description`（嵌套 `{name, description}` 形式）说明边界格式与单锚点
  规则，经既有 `PublicTerm.description` 投影；未扩大 Interface schema。
- `scripts/audit_v51_vocabulary_locality.py` — `display` 改为嵌套
  `{name, description}` 后，原收集器只读字符串值，会**静默漏掉**该 term
  的标签（术语集 114 → 113，`周` 掉出强制范围）。补上嵌套形式的 `name`
  读取，恢复 114 并保持两种写法都被强制。
- `scripts/test_v51_horizon_input_resilience.py`（新增，52 个测试；返工后由
  49 项增至 52 项）
- `docs/plans/2026-08-03-mingli-horizon-input-resilience.md`（新增）
- `docs/releases/2026-08-03-mingli-horizon-input-resilience.md`（本文档）

未修改：`interface.py`、`interface_contracts.py`、`catalog.py`、其他 12 个
Provider manifest、`storage`/`state_token`/`turns`、13 个 Provider 算法主体、
`references/**`。

> 注意：以上"未修改"声明仅对 2026-08-03 的 horizon-input-resilience 返工
> 成立。2026-08-04 的系统审查返工（见 §9）直接修改了
> `state_token.py`、`turns.py`、`providers.py`、`release_deploy.py`、
> `outcome_store.py`、全部 13 个 provider audit 与 `references/matrices/
> provider-completeness.yaml`，该声明不再描述当前 HEAD。

## 6. 测试与门禁（真实结果，最终工作树）

固定运行时：

```text
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=scripts
~/.local/share/mingli-master/venv/bin/python -B
```

| 命令 | exit code | 数量 | 耗时 |
| --- | --- | --- | --- |
| `-m unittest scripts.test_v51_horizon_input_resilience` | **0** | 52 tests, OK | 27.554s |
| `-m unittest`（10 个既有套件，见下） | **1** | 157 tests, 1 failure | 19.68s |
| `scripts/audit_v51_vocabulary_locality.py --check` | **0** | `findings: []`, `ok: true` | — |
| `scripts/audit_release_archive.py --source .` | **0** | 212 files, `errors: []`, `ok: true` | — |

10 个既有套件：`test_v51_portable_interface`、`test_v51_cross_host_contract`、
`test_v51_model_selection_fallback`、`test_v51_p1_rework`、
`test_v51_bazi_fortune_completion`、`test_v51_fortune_provider_audit`、
`test_v51_conversation_contract`、`test_v51_closed_world_brief`、
`test_v51_catalog_driven_registry`、`test_v4_skill_minimalism`。

本次未运行任何带 `--write` 的 completeness/snapshot 命令；未产生或提交
pyc / `__pycache__` / 测试状态 / 临时日志。

## 7. 基线与候选失败内容级对照

既有失败唯一出现在
`scripts.test_v51_fortune_provider_audit.FortuneFixtureContractTests.test_machine_audit_runs_every_real_provider_case_twice`。

基线（base `2ed239f`，首次修改前）与候选（最终工作树）逐字段一致：

- 测试名称：`test_machine_audit_runs_every_real_provider_case_twice`
- findings：
  `Fortune extension output declaration mismatch`、
  `Fortune boundary oracle exact_li_chun source hash mismatch`
- counts：`oracle_mismatches: 0`、`deterministic_mismatches: 0`、
  `extension_mismatches: 0`、`execution_failures: 0`、
  `source_artifact_mismatches: 1`、`fixture_cases: 36`、
  `provider_calculations: 72`、`provider_extensions: 72`
- source applicability：`fortune.bounded-target-period-over-bazi` 状态
  `blocked`
- traceback 断言点：`assertTrue(report["provider_ready"])`

基线与候选均为 157 tests / 1 failure，数量一致。该失败是既有外部全文/
来源哈希缺口，**未**修改来源路径、伪造古籍或刷新基线掩盖；候选结果未比
基线增加或改变任何失败内容。不使用 stash/checkout 切换基线——新工作树
本身就是从 base 建立，基线测试在首次修改前完成。

## 8. 边界声明

- 未修改 Hermes Gateway 的任何源码、配置、测试或启动项。
- 未访问、监听、绑定或探测生产端口 8642/8645。
- 未启动、停止、重启或 kickstart Gateway。
- 未安装或升级任何依赖；未修改系统 Python、共享 runtime 或虚拟环境。
- 未部署，未修改任何已安装 Skill（家目录下 `.codex`、`.agents` 或
  Hermes 技能目录中的副本）。
- 未创建 sidecar、常驻进程或新消息服务；未引入 LLM API、模型选择或
  厂商 SDK。
- 未 push。
- 选术仍由宿主模型依据 `describe` 完成：无关键词路由、无 `object_id`
  硬编码分支、无"资料最少优先"。
- `Accepted.public_copy` 之后没有第二层检查；`stopped`/`accepted` 的
  `public_copy` 均非空。
- 本文档只声明"本地返工完成，等待 Codex 独立验收"，不声称生产已发布，
  也不声称 Gateway 状态已通过端口或进程探测（本次禁止访问 Gateway）。

## 9. 2026-08-04 系统审查返工（追加）

本文档发布后，2026-08-04 在同一分支上完成了系统审查返工（见
`<mingli-master-model-selection-worktree>`
的系统审查记录与 `docs/plans/2026-07-31-mingli-model-selection-and-graceful-fallback.md`）。
该返工在 §1 的 base `2ed239f` 之后继续推进。文档此前记录到 2026-08-04 晚段的
第二批极小返工（HEAD `648dad3`）；本轮的最终收口见 §10。

### 第一批（2026-08-04 早段，12 个提交）

- H1/H3 pending 原子转换与 scope 校验（`promote_to_prepared`、advance_lock
  串行化、resume scope conflict）。
- C2 拆分 Provider runtime readiness 与 release source verification；
  13 个 provider 全部 runtime-ready，矩阵重建（`--check` exit 0），矩阵
  policy 如实报告 `research_sources_verified: false`。
- H4 brief evidence 携带 `supports_fact_refs`；C1 `release_deploy.py`
  新增发布期 source-verification gate。
- C3 outcome calibration 从 accepted_claims 空转改为 judgment 派生；
  H6 state_token 权限 0700/0600 + symlink 防护。

### 第二批（验收后极小返工，2026-08-04 晚段）

第一轮验收返回 3 个 P1 + 2 个 P2，均在本批修复：

- P1-1 `rebuild_index` 现在重放 `promote` 事件，修复崩溃后 prepared token
  倒退为 pending；新增崩溃注入测试。
- P1-2 `_verify_release_sources` 从 source checkout 加载 audit 模块并
  从 `DEDICATED_AUDIT_MODULES` 派生 13 模块，发布 gate 校验与部署的是
  同一 checkout。
- P1-3 outcome calibration 只登记有真实 conclusion 的 judgment，占位
  verdict（`caller_review_required`）不再被校准；无 conclusion 时 registry
  为空（停用）。
- H4 evidence fact-ref 映射改为数据驱动（innermost-out 段匹配），并新增
  遍历 13 provider 的闭包测试。
- H6/P2-1 state_token 统一安全原子写（随机临时文件、O_NOFOLLOW、fstat、
  0600、fsync+replace），lineage/rebuild 同样适用；新增权限、symlink、
  重建测试。

### 验证（截至 2026-08-04 晚段，HEAD `648dad3`）

固定运行时 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts
~/.local/share/mingli-master/venv/bin/python -B`：

- `test_v51_pending_atomicity`（含崩溃恢复、权限、symlink）12 tests OK。
- `test_v51_outcome_calibration` 36 tests OK。
- `test_v51_evidence_fact_ref_closure`（13 provider 数据驱动）OK。
- `test_v51_model_replay` 35 tests OK；`test_release_deploy` 含 source-gate
  绑定测试 OK。
- `audit_v51_vocabulary_locality.py --check` ok；`audit_release_archive.py
  --source .` 212 files ok。
- `audit_provider_completeness.py --check` exit 0（13/13 ready）。

未部署、未安装、未触碰 Gateway/8642/8645；未 push。

## 10. 2026-08-04 最终收口返工（最后一次）

### 10.1 施工起点与提交

本轮只处理冻结的 4 项收口问题（H4 证据真实闭环、release source gate
checkout 隔离、StateTokenStore 三个安全边界、发布文档去自引用），不扩大范围。

施工起始基线：`97500f7aee9dc34b6a936d72f10ca3a6595740bd`
（分支 `claude/mingli-horizon-resilience-rework-20260803`，工作树 clean）。

| 提交 | 主题 | 涉及文件 |
| --- | --- | --- |
| `52a574e` | test: freeze final mingli closure regressions | `scripts/test_v51_evidence_fact_ref_closure.py`、`scripts/test_release_deploy.py`、`scripts/test_v51_state_token.py` |
| `bff5a99` | fix: bind public evidence through declared fact provenance | `scripts/reading_engine/providers.py`、`resources/runtime/providers/fortune.json`、`scripts/test_v51_evidence_fact_ref_closure.py` |
| `687b962` | fix: isolate release audits to the selected checkout | `scripts/release_deploy.py` |
| `cd070b6` | fix: close remaining private token store boundaries | `scripts/reading_engine/state_token.py` |

文档提交之前的代码验收基准 SHA：`cd070b6`（本 §10 只记录本轮实际运行，不声称
文档提交本身等于最终 HEAD）。

### 10.2 H4：公开 evidence 必须绑定真实 public fact

旧实现按 internal fact ref 的路径片段从内向外猜测 public fact key，且原闭包
测试只用统一 `HorizonSelection(kind_id="life")`，绝大多数 Provider 未进入
`Prepared`，fortune 周运的 evidence `supports_fact_refs` 为空。

新实现删除段名猜测，改为显式 provenance seam：

- 每个 public calculated fact 在生成时携带其 internal fact origin/prefix；
- manifest `output_bindings` / `extension_output_bindings` 的 JSON pointer 经
  结构化改写映射到内部 fact-index 路径（`/facts/...` → `/chart_facts/...`，
  `/fact_extension/...` → `/fact_extensions/...`），不对路径段做语义解释；
- 默认 `/chart_facts/output/<key>` 投影生成对应明确 origin；
- 使用自定义 `public_basis_projection` 的 Provider（liuyao、selection、
  physiognomy）各自声明 `public_basis_origins`，通用核心不按 provider_id 分支；
- internal fact ref 与 origin 只允许完全匹配或以 `/` 为边界的祖先前缀匹配，
  多候选取最长前缀；无公开 origin 的 evidence 留在核心内部，不进入
  `supports_fact_refs`。

fortune 扩展最小 public basis projection：新增 `day_master` 与 `month_command`
两个 binding（不重算、不编造），使 Qiongtong evidence 绑定到真实非日历事实。
provenance 只在内部计算过程中存在，未新增到外部 `PublicFact` Interface。

### 10.3 release source gate 隔离

`_verify_release_sources` 改为在一次性发布期隔离子进程中执行：子进程重建
import path 到 `--source` 的 `scripts` 目录、清空 `PYTHONPATH`，父进程的
`sys.path`、`sys.modules` 与之前验证过的另一个 checkout 均不影响；每个加载的
audit 模块的真实文件路径必须位于 `source/scripts` 下，否则 fail-closed。
审计 registry 仍是唯一权威来源，13 个 audit 从 source 的
`audit_provider_completeness.DEDICATED_AUDIT_MODULES` 派生，未硬编码 13 个
静态布尔值。缺少 research root 时继续 fail-closed；任一 Provider 未 verified
时拒绝发布。

### 10.4 StateTokenStore 三个安全边界

- **broken log symlink**：`_append_log_line` 改为 `os.open` +
  `O_APPEND | O_CREAT | O_WRONLY`（平台支持时加 `O_NOFOLLOW`），`fstat` 验证
  普通文件且 owner 为当前用户，mode 0600，flush/fsync 后返回。broken symlink
  被拒绝，外部 victim 不被创建或修改。
- **index 目录 symlink**：每次 rebuild/write（`_write_index_entry`、
  `rebuild_index`、`claim_lineage`）前用已有 private-directory seam 重新验证
  `index` 目录；symlink 或非目录直接拒绝，不沿 index symlink 写出 root。
- **rebuild 权限**：`rebuild_index` 不再用普通 `.mkdir(..., exist_ok=True)`
  留下受 umask 影响的 0755 目录，统一走 seam，保证 root 0700、index 0700、
  log/index/lineage 文件 0600。

### 10.5 本轮实际验证（真实运行，2026-08-04）

固定运行时 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts
~/.local/share/mingli-master/venv/bin/python -B`：

| 命令 | exit | 数量 | failures/errors/skips | 耗时 |
| --- | --- | --- | --- | --- |
| §9.1 冻结聚焦（`test_v51_evidence_fact_ref_closure` + `test_release_deploy` + `test_v51_state_token` + `test_v51_pending_atomicity`） | 0 | 53 tests | 0 | 430.052s |
| §9.2 核心回归（`test_v51_pending_atomicity`、`test_v51_p1_rework`、`test_v4_followup_state`、`test_v51_outcome_calibration`、`test_v51_model_replay`、`test_v51_evidence_fact_ref_closure`、`test_v51_closed_world_brief`、`test_v51_portable_interface`、`test_v51_catalog_driven_registry`、`test_v4_skill_minimalism`） | 0 | 198 tests | 0 | 23.383s |
| `scripts/audit_v51_vocabulary_locality.py --check` | 0 | `findings: []`, `ok: true` | — | 0.10s |
| `scripts/audit_release_archive.py --source .` | 0 | 212 files, `errors: []`, `ok: true` | — | 0.15s |
| `scripts/audit_provider_completeness.py --check`（重建矩阵后） | 0 | 13 providers `provider_ready: true`, `findings: []` | — | 约 45 分钟（含初次漂移、`--write` 重建、重建后 `--check` 三轮完整运行） |

说明：原文档所称的"195 项核心回归"在本轮实际为 **198 tests**（新增的冻结测试
计入后数量变化），本轮如实报告 198，不再沿用旧数字。`test_release_deploy`
内的慢速 source-gate 测试也在 §9.1 内实际运行（合计 430s），不是被跳过或
mock。

### 10.6 H4 覆盖与 fortune 周运

本轮 H4 闭包测试从 catalog 动态取 13 个 Provider 集合，被测试集合与 catalog
完全相等；每个 Provider 使用 manifest 声明的 object/horizon 与各自可成立的
输入夹具，13 个 Provider 全部进入 `Prepared`（无 `continue`、无 `skipTest`）。
每个公开 evidence 断言 `supports_fact_refs` 非空、全部 ref 存在于 brief facts、
无内部路径泄露。

各 Provider 进入 Prepared 的 public evidence 数量与空 supports 数量：

| Provider | evidence 数量 | 空 supports |
| --- | --- | --- |
| bazi | 3 | 0 |
| fortune | 2 | 0 |
| liuren | 2 | 0 |
| meihua | 1 | 0 |
| physiognomy | 2 | 0 |
| qimen | 2 | 0 |
| taiyi | 2 | 0 |
| xingming | 2 | 0 |
| fengshui | 0 | 0 |
| liuyao | 0 | 0 |
| luming-nayin | 0 | 0 |
| selection | 0 | 0 |
| ziwei | 0 | 0 |

catalog Provider 集合 = 上述 13 个，实际进入 Prepared 的集合完全相等
（13/13）；空 supports 总数 = 0。零 evidence 的 Provider（fengshui、
liuyao、luming-nayin、selection、ziwei）仍完成 Prepared 流程，并按其真实
projection/binding 声明直接验证 provenance 映射（见 `_assert_declared_
projection_provenance`），未因零 evidence 跳过。

fortune 周运回归（确定性输入）中每条 evidence 绑定的 public fact refs：

- `evidence:fortune/bazi/ditiansui-chanwei#DR-01-01` →
  `fact:current_user/calculated/fortune/calendar_normalization`
- `evidence:fortune/bazi/qiongtong-baojian#QR-02-01` →
  `fact:current_user/calculated/fortune/day_master`、
  `fact:current_user/calculated/fortune/month_command`
- `evidence:fortune/bazi/qiongtong-baojian#QTB-M01` →
  `fact:current_user/calculated/fortune/day_master`、
  `fact:current_user/calculated/fortune/month_command`

三条 evidence 全部非空且绑定正确，不再把所有证据错误绑定到
`calendar_normalization`。未解析或检查自然语言 `public_copy`。

### 10.7 release A/B 对抗与 state token 安全测试

- **A/B checkout 对抗**：父解释器预加载 checkout A 的 audit 桩模块后，gate
  验证 checkout B，断言 `provider_source_verification` 全部为 B 的 `verified`
  标记、覆盖集合与 B 的 registry 一致；A 的缓存不能影响 B。审计模块真实路径
  逃出 source 的用例 fail-closed。不实际执行部署。
- **state token 安全测试**：broken log symlink 被拒绝且 victim 不存在或原内容
  不变；index 目录 symlink 被拒绝且外部目录无新增 index/lineage 文件；
  umask 022 下 rebuild 后 index 仍为 0700、root 0700、文件 0600；正常
  issue→resolve→promote→accept→rebuild 仍通过；并发 resume/lineage 现有测试
  继续通过。

### 10.8 边界声明（本轮）

- 未部署、未安装、未 push。
- 未访问或修改 Hermes Gateway 源码、运行目录、`$HOME/.hermes/` 下
  任何文件；未访问、探测、停止、启动或重启 8642/8645。
- 未安装任何依赖。
- 未修改 13 个 Provider 的既有计算公式、古籍语料或确定性计算结果；fortune
  仅扩展其 manifest 的 public basis projection 声明（`day_master`、
  `month_command`），不重算、不编造事实。
- 未新增关键词路由、术语字典、中文术语正则、固定回答模板或 provider fallback
  顺序；未解析或拦截 `public_copy`。

### 10.9 provider completeness 本轮结果

`scripts/audit_provider_completeness.py --check` 本轮真实运行：

1. 初次 `--check`（本轮实施完成后）：exit 1，原因 `provider matrix differs
   from the canonical live snapshot`——fortune manifest 新增 `day_master` /
   `month_command` 两个 public basis projection binding（H4 必需）后，live
   快照与已提交矩阵不一致，属声明快照漂移而非 provider 失败。
2. `--write` 重建矩阵快照（本轮运行）：`provider_count: 13`、
   `provider_ready: true`、`findings: []`，exit 0。
3. 重建后再次 `--check`（本轮运行）：**exit 0**，`provider_count: 13`、
   `provider_ready: true`、`findings: []`。

矩阵 diff 只含 fortune 的 `output_bindings`（新增 day_master、month_command）、
`outputs` 与 live `resolved_output_bindings` 对应行及 generator_input_fingerprint，
无任何其它 Provider 或算法声明变化。

## 11. Codex 最终收口（2026-08-04 至 2026-08-05）

本节记录在 10.x 回执之后完成的最后一轮独立验收返工；它只追加当前事实，
不改写前几轮历史结果。

本轮生产与测试实现分别落在 `aab86f5`（portable core boundaries）和
`f03d65d`（canonical matrix input isolation）；本节文档提交只记录验证事实。

### 11.1 关闭的六个问题

1. release source gate 删除了把任意内部 `TypeError` 当作旧签名兼容的无参
   重试。13 个现有 audit 都显式接受 `research_root`；任何异常现在直接
   fail-closed。父、子进程同时清除环境中的 `MINGLI_RESEARCH_ROOT`，来源树只
   接受显式参数。
2. token log、index record、lineage claim 的读写与 lock 全部改用 no-follow fd；
   `fstat` 校验普通文件与当前 owner，权限收口到 0600。不存在安全
   `O_NOFOLLOW` 能力的平台直接失败，不静默降级。损坏的派生 index 仍返回
   miss，并从权威 append-only log 重建，不破坏原有崩溃恢复合同。
3. 默认与自定义 public projection 缺少显式 origin 时，都不再根据同名
   output key 猜测 provenance；无声明即无 public fact binding。八字真实证据
   因此暴露的 `day_master` 缺口只补进 Provider manifest 的 output binding，
   没有在通用核心增加术语分支。
4. 新问题未显式提交 `capability_id` 时，即使只有一个结构候选，核心也返回
   非空 `Stopped.need_input`；语义选术始终由宿主模型依据 `describe` 完成。
5. fortune 时间边界只显式接受 `day` 与 `week`；未知 kind 在 Provider 边界
   fail-closed，不再被当作日运。
6. 删除了 horizon 测试中手工维护的领域 ID 清单；通用层词汇约束只调用公开、
   manifest-driven 的 vocabulary locality audit。

`Complete(state_token, public_copy)`、`Accepted.public_copy` 和外部 Result 类型均
未变化；没有增加 claim-trace、正文解析或第二层交付拦截。

### 11.2 TDD 红灯证据

生产代码修改前新增并真实运行两组对抗测试：

- release/token 组：5 tests，5 failures。分别证明内部 `TypeError` 可错误发布、
  index/lineage/log 读取跟随 symlink、lock symlink 会触碰外部 victim。
- provenance/selection/horizon 组：3 tests，3 failures。分别证明缺 origin 时仍
  猜测绑定、单候选会被核心自动选择、未知 horizon 会按 day 处理。

最小实现完成后，同一批测试全部转绿。

独立审查随后发现两项遗漏：损坏 index 的 JSON 异常落在 repair 捕获区外，且
`claim_lineage()` 的既有 claim 判断仍使用 `exists()+read_text()`；另发现默认
projection 仍保留隐式 origin。新增 4 项冻结测试（损坏 index 恢复、claim 写入
路径 symlink、默认 projection 无 binding、八字证据显式绑定）后全部转绿。

### 11.3 最终验证

固定运行时：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts
$HOME/.local/share/mingli-master/venv/bin/python -B`。

全量测试改由 `scripts/run_test_suite.py` 调度。协调器最多使用 6 个线程监督
独立 Python 子进程，每个测试文件拥有独立解释器；80 个无共享状态模块进入
并行 lane，8 个 release、provider completeness、state/store/atomicity 模块在
并行 lane 完成后串行运行。`--research-root` 是显式、经校验后转交子进程的
测试参数，不是生产核心接口，也不允许从任意当前目录或缓存模块猜测来源。

完整测试的真实收敛过程如下：

1. 接手基线：88 modules / 1415 tests / 17 failed modules / 4021.50s。13 个
   Provider 来源失败来自未显式提供 research root，其余失败暴露旧测试仍假定
   单候选自动选术、source finding 固定处于顶层，以及文档含本机绝对路径；均未
   被写成通过。
2. 第一轮实现后：88 modules / 1418 tests / 1 failed module / 4391.08s；
   `test_v51_provider_completeness` 113/113 通过。唯一失败是 selection 对抗测试
   只读取顶层 `findings`，没有合并真实 `source_verification.findings`。
3. 修正 finding 分层后，selection 聚焦回归 66/66 通过（365.83s）；矩阵输入
   fingerprint 同时排除纯 `test_*.py` 变化，但继续覆盖 runtime、audit、manifest。
4. 最终全量：**88 modules / 1419 tests / 0 failed modules / 4352.25s**。
   其中 `test_release_deploy` 21/21（378.28s）、
   `test_v51_provider_completeness` 114/114（2389.30s）、
   `test_v51_state_token` 23/23、`test_v4_followup_state` 9/9。

| 门禁 | exit | 结果 |
| --- | --- | --- |
| `scripts/run_test_suite.py --jobs 6 --research-root <authoritative-research-root>` | 0 | 88 modules，1419 tests，0 failed modules，4352.25s |
| vocabulary locality | 0 | `findings: []`，`ok: true` |
| release archive | 0 | 212 files，`errors: []` |
| Skill `quick_validate.py .` | 0 | `Skill is valid!` |
| `git diff --check` | 0 | clean |
| `__pycache__` / `*.pyc` / `*.pyo` 检查 | 0 | 无命中 |

Provider matrix 使用官方生成器完成 fail-closed 闭环：

1. 初次 `--check`：exit 1，仅报告 canonical live snapshot 漂移；
2. 首次 `--write`：exit 1，真实暴露 bazi 专项 audit 在 Python 中重复维护旧
   outputs 清单；未写成“成功”；
3. 将该审计改为验证 manifest 的 `outputs ↔ output_bindings` 闭包，并继续由
   真实 calculation 验证每个声明输出存在；bazi 专项 audit exit 0；
4. 再次 `--write`：exit 0，13/13 `provider_ready: true`，`findings: []`；
5. 独立再次 `--check`：exit 0，13/13 `provider_ready: true`，`findings: []`。

最终矩阵 `--write` 与独立 `--check` 均为 13/13 `provider_ready: true`、
`findings: []`。canonical matrix 构建显式屏蔽外部 `MINGLI_RESEARCH_ROOT`，因此
机器环境不会改变提交快照；全文来源验证仍由显式 research root 的 release gate
完成。fingerprint 忽略纯测试文件，但继续覆盖运行时、专项 audit 与 Provider
manifest，避免新增测试导致无语义的 canonical snapshot 漂移。

本轮矩阵变化来自显式 provenance 绑定闭包：bazi 的 `day_master`，Liuyao 的公开
projection，physiognomy 的 `accepted_observation_fact_keys`，selection 的
`no_valid_candidate`，以及新的 generator input fingerprint；不是“只改 bazi”。
通用 Python 核心没有新增这些 Provider 词汇，Provider 计算公式、算法结果、fixture
和古籍语料均未变化。

### 11.4 边界

- 未部署、未安装、未 push；未修改任何已安装 Skill。
- 未访问或修改 Hermes Gateway、`$HOME/.hermes/` 或 8642/8645。
- 未安装依赖，未修改 Provider 计算公式、确定性结果或古籍语料。
- 未新增关键词路由、术语字典、固定回答模板、sidecar 或常驻进程。
