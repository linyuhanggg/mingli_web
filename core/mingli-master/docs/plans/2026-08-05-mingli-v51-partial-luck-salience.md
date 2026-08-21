# Mingli V5.1 Partial Luck Sequence and Salience Signals Plan

日期：2026-08-05
分支：`qoder/mingli-v51-partial-luck-salience-20260805`
基线：`962bd4bc79cb68d59de2731902e492e569d5e950`

## 1. 一句话目标

在不扩大通用 Command/Result Interface 的前提下，让八字 Provider 在只有四柱＋性别时输出可确定的大运顺逆与干支序列（不伪造任何时间字段），并在既有 `interpretive_candidates` 内提供 Provider-owned 的机械 salience 候选信号，同时给 `SKILL.md` 增补两条与术数无关的通用成稿约束。

## 2. 现状代码证据

- `scripts/bazi_fact_adapter.py::build_from_pillars()`（基线 L458-L532）：无论是否提供性别，一律输出
  `luck_cycles = {"status": "not_calculated_missing_birth_datetime_location", "cycles": []}`。
- `scripts/bazi_fact_adapter.py::_luck_cycles()`（基线 L540-L576）：完整出生资料路径已有唯一的顺逆公式
  （`yang_year = POLARITY[year_stem]=="阳"`；`forward = (male and yang) or (female and not yang)`）与运序公式
  （`JIAZI[(month_index + direction * sequence) % 60]`，sequence 1..10），但两个公式内联在完整模式中，部分模式无法复用。
- `scripts/bazi_fact_adapter.py::_interpretive_candidates()`（基线 L195-L266）：已输出
  `strength` / `structure` / `following_and_transformation` 三个非裁决候选；没有跨类的突出结构信号。
- `scripts/adapter_validate.py::_validate_bazi_v51_output()`（基线 L1043-L1097）：仅校验三个既有候选键与神煞层，
  对 `luck_cycles` 部分形状与 salience 信号无任何约束；`natal_static` scope 下 `luck_cycles` 甚至不在必需输出内（L2451-L2453）。
- `resources/runtime/providers/bazi.json`：`finding_bindings` 以 JSON pointer
  `/facts/chart_facts/output/interpretive_candidates` 声明 `finding.interpretive_candidates`；
  `output_bindings` 已包含 `luck_cycles`。`scripts/reading_engine/providers.py::_declared_public_findings()`
  按声明泛型投影，无需修改通用引擎即可把新增内部字段带入 `brief`。
- `scripts/reading_engine/providers.py::BaziProvider.calculate()`（基线 L2341-L2415）每次计算都会调用
  `bazi_calc._validate_facts` → `adapter_validate.validate_payload("bazi", ...)`，因此校验器必须与新形状同步。
- `scripts/export_v51_answer_cases.py` + `tests/replay/mingli-answer-cases.jsonl`：8 个由真实
  `ReadingInterface.execute(Prepare)` 导出的答案 replay 案例；`scripts/test_v51_model_replay.py`
  断言案例数（8）、coverage tags 与 brief 结构闭合。
- 冲突记录：任务必读清单中的 `docs/plans/2026-07-22-mingli-v4-minimal-intelligent-core.md` 与
  `docs/plans/2026-07-28-mingli-v51-portable-vocabulary-data-core.md` 在基线 `962bd4b` 中不存在，
  它们只是旧脏工作树（`mingli-master-release-fix`，HEAD `c8cf4ca`）中的未跟踪用户资产。本轮以
  `962bd4b` 的实际代码为唯一事实来源，未从脏工作树迁移任何内容。

## 3. 保留不变的通用 Interface

- Command 仍只有 `describe` / `prepare` / `complete`；Result 仍只有 `Described` / `Prepared` / `Accepted` / `Stopped`。
- 不修改 `scripts/reading_engine/interface.py`、`interface_contracts.py`、`turns.py`、`contracts.py` 与 `complete` 提交逻辑。
- `Accepted.public_copy` 的最终权威语义不变；`complete` 之后没有语义 gate。
- 不新增通用命令、结果类型、字段、capability_id 或 object_id；`luck_cycle_sequence` 只是 Provider 内部 allowed capability 标记。
- 八字 Provider 的数据目录新增 `overview` dimension_id，用于把“整体看看”保持为一个语义范围，避免空维度自动展开成事业、关系、健康等固定栏目；它不是写进 `SKILL.md` 的通用术语，也不改变 Interface 形状。
- brief 传递依赖既有 `finding_bindings` / `output_bindings` 泛型投影，不加新外部字段。

## 4. 八字 Provider 内部 Seam

在 `scripts/bazi_fact_adapter.py` 内提取三个私有函数，使顺逆与运序只有一个实现：

- `_luck_cycle_direction(pillars, gender) -> bool`：唯一的顺逆规则实现（阳年男/阴年女顺，取年干阴阳）。
- `_luck_cycle_pillar_sequence(pillars, forward) -> list[str]`：唯一的十步干支序列实现（跨六十甲子循环）。
- `_luck_cycles(...)`：完整出生资料路径复用以上两个函数并继续计算起运时间；
  `build_from_pillars()` 复用同样两个函数，只输出 `sequence_only` 部分结果。

## 5. 四柱部分大运的完整状态语义

四柱＋有效性别：

```json
{
  "status": "sequence_only",
  "direction": "forward|reverse",
  "direction_rule": "阳年男/阴年女顺，阴年男/阳年女逆；阴阳取年干",
  "cycles": [{"sequence": 1, "pillar": "…"}, "… 共 10 步，每步只有 sequence 与 pillar"],
  "unavailable": ["start_age", "calendar_year_mapping", "active_cycle", "precise_timing"]
}
```

四柱、无性别：

```json
{
  "status": "not_calculated_missing_gender",
  "cycles": [],
  "unavailable": ["direction", "sequence", "start_age", "calendar_year_mapping", "active_cycle", "precise_timing"]
}
```

约束：部分结果禁止出现 `start_age_years`、`end_age_years`、`approximate_start_datetime`、
`boundary_term`、对应公历年份、当前大运、流年或具体应期；`luck_cycle_timing` 保持 blocked；
无性别时继续返回静态本命事实，不返回 NeedInput、不阻断 prepare、不伪造默认性别、不换 Provider；
非法性别仍按现有 `_normalize_gender` 规则拒绝。

## 6. salience signal 的结构和禁止职责

在既有 `output.interpretive_candidates` 内新增 Provider-owned 的 `salience_signals` 列表；每条：

```json
{
  "signal_id": "Provider 内稳定唯一标识",
  "status": "mechanical_candidate",
  "basis": {"非空机械事实"},
  "hard_verdict": null,
  "boundary": "该信号不能独立推出最终结论"
}
```

生成范围（只从已计算出的确定性事实，没有事实就不生成，不凑数）：

1. 重复出现的天干或地支及其位置；
2. 已计算出的支关系及涉及位置；
3. 月令、季节锚点与日元的原始事实组合；
4. 月令主气是否透出（沿用既有 structure 候选事实）；
5. 已存在的合化/从化候选（保持未裁决）。

禁止：概率/百分比/置信度分数/伪精确 score、最终自然中文答案、把单个信号直接升级为日主身强/身弱或用神等最终裁决、疾病/小人/职业/婚姻/事件结论、神煞升为主判断、生活领域映射进通用层。允许回答根据已计算的季节、月气和元素分布描述某种元素气势偏旺、偏弱或集中；这类气势倾向不等于日主强弱或用神裁决。排序用确定的 Provider 内规则与稳定 tie-breaker，不调用模型。
校验器（`adapter_validate.py`）拒绝：非空 `hard_verdict`、空 `basis`、重复/空 `signal_id`、非法 `status`、空 `boundary`。

## 7. `SKILL.md` 只允许出现的通用约束

只在「协议/成稿」既有小节增补两条对全部 Provider 通用的措辞：

1. `prepare.query` 保留用户最新问题的原始语义范围，只做不改变范围的最小结构化转写；
   不得主动增加用户没有要求的主题、领域、具体事件或固定输出栏目。
2. 用户询问置信度/准确率/把握程度时，只有 `brief` 中存在经过声明和校准的数值才可展示；
   否则只解释 `brief` 已公开的资料完整度、支持范围、未决边界与来源缺口，不生成数字。

严禁写入任何具体术数、Provider 名称、排盘术语、生活领域清单、固定输出格式或命理话术。

## 8. 文件级修改清单

| 文件 | 修改 |
| --- | --- |
| `scripts/bazi_fact_adapter.py` | 提取 `_luck_cycle_direction` / `_luck_cycle_pillar_sequence`；`build_from_pillars` 输出部分大运；`_interpretive_candidates` 增加 `salience_signals`；版本字段按需递增 |
| `scripts/adapter_validate.py` | 校验部分大运两种状态形状与禁时字段；校验 `salience_signals` 形状 |
| `scripts/test_bazi_fact_adapter.py` | Task 1 红→绿测试 |
| `scripts/test_v51_bazi_provider_audit.py` | 适配 adapter 版本断言（若递增） |
| `scripts/test_v51_bazi_fortune_completion.py` 等既有断言 | 仅在与新形状冲突时最小适配 |
| `resources/runtime/providers/bazi.json` | 为部分大运/salience 增补 term 显示词，并增加 Provider-owned `overview` 维度（不加新外部 binding 种类） |
| `SKILL.md` | Task 3 两条通用约束 |
| `scripts/test_v4_skill_minimalism.py` | 强化通用约束断言 |
| `scripts/export_v51_answer_cases.py` | 新增四柱＋性别 broad-overview replay 案例 |
| `tests/replay/mingli-answer-cases.jsonl` | exporter 重导出（预期 diff：新增 1 行） |
| `scripts/test_v51_model_replay.py` | 案例数与 coverage 断言适配 |
| `docs/plans/2026-08-05-mingli-v51-partial-luck-salience.md` | 本文档 |

## 9. TDD 步骤

每个 Task 都是：先写失败测试 → 运行记录预期失败 → 最小实现 → 聚焦测试转绿 → 相关回归 → `git diff --check` → 提交。

1. Task 1 红测：四柱＋male 逆排前三步（庚辰/己卯/戊寅）、female 相反方向、无性别状态、中文性别、
   非法性别拒绝、跨甲子循环、部分结果无时间字段、完整出生路径不回归、validator 接受新形状且拒绝违规形状。
2. Task 2 红测：三张结构不同的合成命盘 `salience_signals` 互不相同；同输入重放相同；重复干支/支关系/季节锚点
   可识别；无最终 verdict；validator 拒绝非法信号；finding 经真实 `ReadingInterface` 进入 brief 且引用闭合。
3. Task 3 红测：`test_v4_skill_minimalism.py` 断言 SKILL.md 含两条通用约束的关键措辞、仍无 Provider/术数词。
4. Task 4 红测：`test_v51_model_replay.py` 断言新案例存在、partial luck 无时间字段、salience 在 brief findings、
   噪声词不进 brief、rubric forbidden 覆盖噪声与无校准百分比。

## 10. 分提交计划

1. `fix: derive partial luck-cycle sequence from supplied pillars`
2. `feat: expose provider-owned bazi salience signals`
3. `docs: preserve caller scope in portable drafting`
4. `test: add partial-pillar salience replay coverage`
5. `docs: record partial luck salience execution results`（本文档最终结果）

## 11. 测试命令

```bash
MINGLI_TEST_PYTHON="${MINGLI_PYTHON:-$HOME/.local/share/mingli-master/venv/bin/python}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=scripts

"$MINGLI_TEST_PYTHON" -B -m unittest -v \
  scripts/test_bazi_fact_adapter.py \
  scripts/test_v51_bazi_provider_audit.py \
  scripts/test_v51_provider_finding_contract.py \
  scripts/test_v51_closed_world_brief.py \
  scripts/test_v51_cross_host_contract.py \
  scripts/test_v51_model_replay.py \
  scripts/test_v4_skill_minimalism.py

"$MINGLI_TEST_PYTHON" -B -m unittest discover -s scripts -p 'test_*.py'
```

## 12. 验收标准

见任务书第十二节：通用 Command/Result/字段 Interface 不扩大；四柱＋性别得到顺逆与干支序列且无伪造时间字段；
四柱无性别仍可静态分析；完整出生资料计算不回归；salience 只有机械候选无 verdict；
brief 可见 salience finding；SKILL.md 无 Provider/命理专门术语；query 不被扩写成固定栏目；
无校准数据不输出百分比；环境业务记忆不进 brief；所有失败结果非空；未动 Gateway/端口/依赖/部署/push。

## 13. deletion test

1. 删除 `salience_signals`：模型仍能从 `brief` 的零散公开事实推导，但必须重新自行扫描重复、支关系与季节锚点——
   信号在 Provider 内一次计算、处处复用，证明它提供真实 Leverage 而非装饰。
2. 删除任何假设中的自动路由器、内容门禁或外部验签器：`describe/prepare/complete` 与 `Accepted.public_copy`
   能力完整保留，证明这些 Module 本就不应引入。
3. 删除本次 `SKILL.md` 两条通用约束：所有确定性计算与校验不受影响，只影响宿主调用纪律，
   证明其职责局限于通用调用协议层。
4. 八字顺逆/运序/salience 规则只存在于 `bazi_fact_adapter.py`（八字 Provider 内部），改一次即影响所有宿主，符合 Locality。
5. Codex、Hermes、Claude Code 等宿主仍只调用同一 JSON Adapter，不需要理解部分大运或 salience 的内部实现。

## 14. 明确非目标

任务书第十一节全部 15 项（关键词自动选术、自动附加 Provider、多体系并跑、裁判服务、`complete` 语义验义、
`Accepted` 后拦截、自动修稿、数值置信度、固定模板、`SKILL.md` 专门命理规则、五行数量直下结论、
小人/疾病默认话术、重写 13 Provider、改 Hermes Gateway 等）本轮一律不做。

## 15. 实际执行结果和最终 commit hashes

所有命令均在本 worktree（或注明的基线 worktree）以固定运行时
`~/.local/share/mingli-master/venv/bin/python`（CPython 3.14.6）执行，
`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=scripts`。

### 基线（962bd4b）

- 聚焦 7 文件（本 worktree 施工前）：`unittest -v …` → **89 tests, OK**（25.99s）。
- 完整基线（干净基线 worktree `…/2026-08-02/mingli-master-horizon-resilience-rework`，
  `scripts/run_test_suite.py -j 3 --research-root ~/.codex/skills/mingli-master`）：
  **88 modules / 1419 tests / 0 failed**（4862.43s）。
- 同基线在平铺单进程 `unittest discover` 模式下另有一个已知环境性失败（见下）。
- 首次尝试的两次全量运行因未设 `MINGLI_RESEARCH_ROOT` 导致大量语料验证模块失败，
  均已作废并在设置权威语料根（只读使用 `~/.codex/skills/mingli-master`，未修改安装）后重跑。

### 最终 HEAD（4096a61）

- 聚焦 7 文件：`unittest -v scripts/test_bazi_fact_adapter.py … scripts/test_v4_skill_minimalism.py`
  → **108 tests, OK**（32.52s）。
- 规范并行 runner（README 声明协议，每测试文件独立子进程）：
  `scripts/run_test_suite.py -j 3 --research-root ~/.codex/skills/mingli-master`
  → **88 modules / 1438 tests / 0 failed**（4611.30s）。
- 任务书指定的平铺命令 `unittest discover -s scripts -p 'test_*.py'`（带 research root）
  → **1438 tests, 1 failure**：
  `test_release_deploy.ReleaseCheckoutIsolationTests.test_gate_audits_checkout_b_even_when_a_is_preloaded`
  （`AssertionError: 13 != 2`）。该失败在干净基线 962bd4b 上以同一平铺模式逐字复现：
  平铺单进程下真实 `audit_provider_completeness`（13 模块注册表）先于测试 stub 被
  缓存进 `sys.modules`，而该隔离测试的前置断言假定每文件独立子进程（规范 runner
  的隔离模式，其下该模块 21/21 PASS）。属基线既有的运行模式条件，与本任务无关，
  本轮未修改无关测试。
- `audit_provider_completeness.py --check` → provider_ready: true，findings: []（13/13）。
- `export_v51_answer_cases.py --check` → ok: 9 production-exported answer cases。
- `git diff --check` → 无输出；工作树干净。
- 测试总数 1419 → 1438（+19 为本轮新增测试）。

### Commits（962bd4b → HEAD）

1. `151bc5d` fix: derive partial luck-cycle sequence from supplied pillars（Task 1 + 本计划文档）
2. `8597ccc` feat: expose provider-owned bazi salience signals（Task 2）
3. `80f2780` docs: preserve caller scope in portable drafting（Task 3）
4. `5dafba1` test: add partial-pillar salience replay coverage（Task 4）
5. `4096a61` chore: refresh provider completeness matrix for bazi 1.2.0（Task 7N 矩阵哈希快照刷新）
6. 本文档结果记录为最后一个 docs commit。

### replay fixture 预期 diff 确认

与干净基线代码重导出结果逐字段对比：新增 1 案例；3 个 bazi 案例仅增加
`salience_signals`与版本绑定的 `base_calculation_digest`；其余 5 案例 0 diff。
已提交的 JSONL 同时吸收了一处基线既有的 fixture 陈旧（`supports_fact_refs`，
基线 `--check` 本就报 stale），已在提交说明中如实记录。

### 未完成项（如实声明）

- 本轮只准备了 replay generation packet 所需的数据与导出器能力；**未运行真实独立盲审**，
  不宣称表达质量已通过；盲审留待 Codex 验收流程。
- 未部署、未同步安装、未 push。

### 返工轮（Codex 验收退回后的定点返工，2026-08-06）

主体实现保留，不推翻重写。针对阻断项逐条 TDD 返工：

1. `cf1d3eb` **fix: fail closed on supplied-pillars luck shapes** —— supplied-pillars
   payload 改为精确闭集 schema：缺 luck_cycles、未知/伪装 status、未声明字段、多余
   unavailable 项、任意位置的时间字段、与 scope 矛盾的 capability 状态全部拒绝；
   新增独立重算 oracle（自带干支表，不依赖生成器）核对顺逆、方向规则与十步序列；
   salience_signals 在该 scope 下必须存在且闭集字段，拒绝 confidence/probability/score/
   裁决字段。11 个对抗性篡改测试钉住全部拒绝（含 Codex 构造的 7 类反例）。
2. `77fdec2` **feat: publish partial luck timing boundaries as prepared limits** ——
   bazi manifest 新增两条 `limit_bindings`（按 luck_cycles.status 指针 equals 匹配）：
   `limit.partial_luck_timing`（四项时间不可得）与 `limit.partial_luck_no_gender`
   （外加顺逆与排序不可得），带中文公开措辞并进入 brief 词汇表；完整出生资料
   brief 不携带。不再依赖嵌套 warning。
3. `8e37f77` **fix: keep broad overviews inside a single overview dimension** ——
   bazi manifest 新增 Provider-owned `overview` 维度（manifest 数据，未写入 SKILL.md）；
   宽泛总览案例显式提交 `("overview",)`，request_view 与 claim_scopes 精确等于
   `overview`，不再展开七领域；life/natal 的 dimension_fact_scope 按请求维度原样构建；
   空维度回退默认维度的通用行为未改。
4. `419c07b` **docs: replace legacy Hermes gate reference with provider-local
   boundaries** —— `references/bazi-input-and-image-gate.md` 重写为纯 Provider 内部
   输入/事实边界说明：删除 delivery guard、shell 命令与临时路径、旧 gate_check、
   固定可见状态标签；sequence_only 语义（可谈顺逆与排序、不可谈时间）取代旧的
   全面禁谈；同步修正 regression YAML 中依赖固定标签的条目；minimalism 测试钉住
   新边界并禁回旧词。
5. `ae3d767` **test: add fresh-context blind prediction material with gates** ——
   新增真实新上下文盲测材料：针对冻结 brief 手写的自然中文预测（非模板），
   claim traces 闭合到公开 facts/evidence；机械门禁钉住 brief 摘要绑定、rubric
   禁词（噪声词/百分比/时间伪造）、引用闭合；不内嵌 review，无独立评审时 scorer
   拒绝评分。独立盲审仍待验收方执行。
6. `add3ee7` **chore: refresh completeness matrix fingerprint for fail-closed
   validator** —— adapter_validate 变更引起的单行指纹刷新。
7. `70d4012` **fix: declare overview in the executable bazi capability contract**
   —— overview 最初只进了 caller-view 能力块，manifest 往返审计发现可执行
   runtime_capability 契约缺该维度；补齐 runtime_capability.dimensions 与
   default_dimension_ids，保持“默认集==全部维度”的既有钉住不变式：真正未指定的
   宽泛请求仍映射到全部声明维度，显式提交 overview 则保持单一语义单元。
8. 最后 commit：第二次矩阵哈希刷新（manifest 维度变更引起 live-audit 漂移）+
   本文档结果记录。

全量并行 runner 第一次跑出 1 个失败模块（`test_v51_catalog_driven_registry` 的
manifest 往返断言），根因即第 7 条的契约块遗漏，修复后复绿；其余 87 模块全部
PASS，未发现与本任务无关的新失败。

返工轮验证数字（全部在 aee0a88 之后的工作树上实测）：

- 聚焦 7 文件套件：`unittest -v scripts/test_bazi_fact_adapter.py …` →
  **129 tests, OK**（29.03s；基线 89，+40 为本分支两轮累计新增，其中返工轮 +21）。
- 完整回归（规范并行 runner，`-j 3 --research-root ~/.codex/skills/mingli-master`）：
  **88 modules / 1459 tests / 0 failed modules**（4470.73s；基线 1419 → 1459）。
  第一次全量出现的唯一失败模块（catalog 往返）已按第 7 条修复并复绿。
- `audit_provider_completeness.py --write` → provider_ready true, findings []（13/13）；
  两次刷新均为纯哈希 diff（第二次含一条 `overview` 维度快照行）。
- `export_v51_answer_cases.py --check` → ok: 9 production-exported answer cases；
  重导出相对上一提交仅新案例 1 行变化。
- `git diff --check` 无输出；工作树干净；脏树 7 项用户资产与干净基线 worktree
  保持原样；未碰 Gateway、8642/8645、部署、依赖；未 push。

### Codex 二次验收定点返工（2026-08-07）

本轮只收口二次验收发现的真实漏洞与记录错误，没有增加语义 gate：

1. supplied-pillars 校验只接受 `male` / `female` / 缺省性别；标准化四柱必须四项齐全且均为合法六十甲子，不能再以空字典跳过 oracle；公开四柱、历法归一化结果与标准化输入必须一致。`fact_layer_status`、scope、input mode、adapter profile 与 luck status 任一出现 supplied-pillars 标记，就进入同一套严格校验，不能靠改一个状态名绕过。blocked capabilities 必须与该部分资料范围精确一致；列表重复、交叉、布尔值冒充序号、对象或数组冒充状态等畸形 JSON 都稳定返回校验错误，不再抛异常。无性别时仍须显式输出空 cycles，避免“没算”和“字段丢了”混为一谈。
2. broad-overview replay 明确询问“整体＋目前能确定的大运信息”，horizon 从错误的 `year` 改为 `life`，通过真实 `Prepare` 重新导出并绑定新 brief digest。
3. 手写预测保留“火气集中、偏旺”的计算性判断，把“四个算多数”改为“八个中占四个、最显眼”，把“没有出生时间”改为“缺少完整出生日期时刻”，并删除没有真实采集依据的 usage 数字；claim trace 补齐四柱事实引用，使“明面八个干支”的表述可直接追溯。
4. 保留 Provider-owned `overview`；本文前部已改为“不扩大通用 Command/Result/字段 Interface”，消除与实际实现的文字冲突；同步修正 adapter 顶部对部分大运能力的过期说明。

验证：聚焦 7 文件 **147 tests / 0 failed**（32.84s）；Provider matrix **13/13 ready、findings=[]**；真实 answer exporter `--check` 为 9 cases；规范全量 runner **123 targets / 90 modules / 1515 tests / 0 failed modules / 512.09s**（8 分 32 秒）。全程未碰 Gateway、8642/8645、部署或依赖。
