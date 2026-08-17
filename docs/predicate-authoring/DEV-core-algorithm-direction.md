# 核心算法开发方向与权威开发文档

> 本文档是当前核心算法工作流的唯一权威来源。接手者按此文档施工并自检；
> 标「已核验」的事实都在本机 `core/mingli-master` 实测过，直接依赖，不要另找做法。
> 最后核验日期：2026-08-17。

---

## 0. 一句话现状

**排盘层已是三家产品里最准的，断法层零产出，而卡点只有一个：人工语义核对是所有输出的唯一闸门。**

已核验的当前状态：

```
规则总数                1328
  已激活 (runtime_active)  192
  有谓词但未激活            394   ← 闲置库存
  连谓词都没写              742

394 条闲置库存按角色
  issue_specific_judgment_rule   303
  verdict_prohibited              82   （全部为相法，设计上永不出断语）
  其他                             9

394 条按术数（导航内 vs 导航外）
  导航内：选择 66 / 八字 22 / 紫微 12 / 太乙 11 / 六爻+梅花 9 / 大六壬 9 / 禄命 4 / 七政 3  = 136
  导航外：风水 171 / 相法 87                                                  = 258
```

关键机制事实（`scripts/reading_engine/evidence_rules.py:421`）：

```python
if not rule.runtime_active or not rule.required_fact_predicates:
    return False, (), ()
```

而 `runtime_active` 由审计状态唯一决定（同文件 `_validate_rule`）：

```python
expected_active = binding["verification_status"] == "verified"
```

**所以那 394 条写好的谓词连 matcher 都进不去，产出恒为零。**谓词施工现在已经不是瓶颈
（工具链齐备、可外包），人工核对是。

---

## 1. 方向：三条腿

### A · 让「来源命中」成为可交付内容，不必等 verified

未核对的规则目前完全沉默。但一条规则同时具备这两个性质时，它已经可以作为**原文出处**呈现：

- 谓词命中（机器可判定）
- 引文与原文逐字一致、`quote_hash` 与 `source_sha256` 校验通过（机器可判定）

缺的只是「这个谓词是否忠实表达了原文条件」这一项人工判断。而**展示原文出处并不需要那一项**——
需要它的是「据此下断语」。

所以：开一条独立的展示通道，把「已机械校验、未语义审计」的命中送到结果层，
明确标注状态，只呈现原文，不改写成断语。

这是唯一能立刻把 394 条库存变成用户可见价值的路径，而且不新增任何算法风险。
竞品无法复制——它们的引文根本不存在（实测：qingnang 标注为《子平真诠·论财》的
「偏财源活，最宜食伤生扶；忌比劫劫夺」在全文库四组关键词零命中，且原文立场相反）。

### B · 把语义核对从逐条人工降为可抽检流程

机械前置全部自动化（引文哈希、锚点可解析、路径白名单、判别力区间、rationale 非样板），
人工只做抽样，按批次接受率决定整批去留。目标是清空导航内 136 条积压。

### C · 受限裁决，按已核验规则逐条推进

模板已有且已验证：六爻求财 `HJC-R009`——盘内恰有一个可见妻财爻时定位具体爻位，
多现返回 `unresolved_multiple_visible_lines`，无则 `unresolved_no_visible_line`。
典籍无歧义处下断，有歧义处明说不裁。这才是付费深度的来源。

### 为什么是 A → B → C

- A 用现有库存立刻产出，零新增算法，风险最低
- B 解开吞吐，但在 A 落地前无法验证「核对完真的有用」
- C 依赖 A/B 的产出量，且需要逐条源头审计，最慢

**本文档规定阶段 0 与阶段 A。**B 和 C 的详细设计等 A 的实际产出再定，不在此预先冻结。

---

## 2. 阶段 0：解开三个当前阻塞

这三条不解开，后面任何施工都会重复踩。

### 0.1 SPEC.md 的死循环

`docs/predicate-authoring/SPEC.md` 第 50 行仍写着
`references/matrices/classical-evidence-bindings-v1.json` 是「绝对不要碰」，
但引擎要求**每条带谓词的规则必须有对应 binding 条目，且键集完全相等**
（`build_evidence_index.py:1213` `_apply_classical_evidence_bindings`，判断是 `!=` 不是子集）。

按 SPEC 逐字执行必然编译失败。上一轮外包就死在这里。

现在已有受支持的工具 `scripts/sync_binding_stubs.py`。要做的：

- 把该文件从「绝对不要碰」移出，改写为：**只能经 `sync_binding_stubs.py` 生成
  `inactive_unverified` 桩，不得手写 `verified` / `verified_exact`**
- 在 SPEC 第 8 节自检流程里，把 `sync_binding_stubs.py` 插入到「写完谓词」与
  「跑 verify_predicates」之间，作为必经步骤

### 0.2 `verify_predicates.py` 在本机不可用

它现在默认 `--runtime .runtime/v53-time-check-release`，而该目录本机从未创建
（`ls -d .runtime` → No such file or directory）。源码树也不是签名 release（无
`.mingli-release-manifest.json`），所以默认参数下必然退出。

拆分源码树与签名 Runtime 这个架构判断是对的，要保留。要做的：

- 缺签名 Runtime 时**不要直接退出**，回退到源码树取盘面事实，并在输出里显式打印
  一行警告说明「本次用源码树而非签名 release，结果不能用于生产准入判定」
- 保留 `--runtime` 参数供有签名 release 时使用

### 0.3 `sync_binding_stubs.py` 用 `python3` 跑不动

第 39 行进程内 `import build_evidence_index`，而该模块需要 `yaml`，只存在于
Runtime venv。工具已有 `--python` 参数并用于第 211/218 行的子进程调用，但没用于这个
import。结果是文档里写 `python3 scripts/sync_binding_stubs.py` 的命令全部失败。

要做的：把需要编译器的部分改为经 `--python` 走子进程（与 `verify_predicates.py`
的做法一致），让工具在系统 `python3` 下可直接运行。

---

## 3. 阶段 A：未审计来源展示通道

### 3.1 不可以改的东西

**不要放宽 `runtime_active`。**它与审计状态的绑定是这套系统唯一的人工门禁：

```python
expected_active = binding["verification_status"] == "verified"
if rule.runtime_active is not expected_active: raise ValueError(...)
```

放宽它等于让未审计规则冒充已审计，整个来源可追溯性作废。

**不要复用 `source_conditioned_patterns`。**该字段的 `status` 在后端合同里是
`Literal["predicate_matched_not_verdict"]`（`backend/app/charts/contracts.py` 385/746/869/935
四处），语义是「已审计规则的谓词命中」。把未审计命中混进去会污染已有语义。

### 3.2 设计

新增一条**并行、独立命名**的通道。

**Runtime 侧**

1. `scripts/reading_engine/evidence_rules.py` 增加 `match_rule_pending_audit(rule, facts)`：
   - 准入条件：`rule.runtime_active is False`
     且 `rule.classical_binding_status == "inactive_unverified"`
     且有谓词
   - 谓词求值复用现有 `_predicate_matches`，语义必须与 `match_rule` 完全一致
   - **不修改现有 `match_rule` 的任何行为**
2. 每个已接通 Provider 增加输出 `source_candidate_patterns`，条目形状与
   `source_conditioned_patterns` 平行，但：
   - `status` 固定为 `"predicate_matched_pending_audit"`
   - 必须携带 `rule_id`、`source_title`、`source_anchor`、`quote`、`quote_hash`、
     `source_sha256`、命中的 fact paths、predicate audit
   - **不得携带 `verdict` 字段**（任何情况）

**Backend 侧**

3. 新增 Pydantic 模型与 `Literal["predicate_matched_pending_audit"]`，接入对应
   Provider 的 ViewModel 与 `reading-document/v1` Schema，字段缺失时 fail-closed
4. 现有 `source_conditioned_patterns` 的合同**不改一个字**

**Web 侧**

5. 结果页新增独立分区呈现该通道，与已审计来源分区**视觉上明确分开**

### 3.3 产品约束（不可协商）

这条通道的全部正当性来自「只呈现原文、不改写」。以下三条违反任何一条，整个阶段 A 变成
和竞品一样的编造：

1. **必须原样呈现 `quote`。**不得摘要、不得改写、不得让模型转述成白话断语。
2. **必须显示状态标签**，文案明确表达「来源命中，语义未经审计」。不得用
   「可能」「参考」这类模糊词代替状态。
3. **必须显示出处锚点**（书名 + 行号），使用户可回查原文。

模型成稿层（`brief` → `complete`）对该通道的引用同样受限：可以说「《某书》某条在本盘
条件成立，原文为……」，**不得**说「所以你……」。

---

## 4. 验收

### 4.1 阶段 0

```bash
# 0.1 SPEC 死循环已解开
grep -n "sync_binding_stubs" docs/predicate-authoring/SPEC.md
# 必须在第 1 节与第 8 节各至少出现一次；第 50 行不再把该文件列为「绝对不要碰」
```

```bash
# 0.2 verify_predicates 在无签名 Runtime 时可用且有警告
python3 scripts/verify_predicates.py --route ziwei --since snapshots/ziwei-before.json
# 必须正常跑完并打印「用源码树而非签名 release」的警告，退出码 0 或 1（不得是 2）
```

```bash
# 0.3 sync_binding_stubs 在系统 python3 下可跑
python3 scripts/sync_binding_stubs.py --dry-run
# 必须正常输出，不得出现 ModuleNotFoundError
```

### 4.2 阶段 A

```bash
# A1 编译与启动不受影响
cd core/mingli-master && PYTHONDONTWRITEBYTECODE=1 \
  ~/.local/share/mingli-master/venv/bin/python scripts/build_evidence_index.py --check
cd core/mingli-master && echo '{"kind":"describe"}' | PYTHONDONTWRITEBYTECODE=1 \
  ~/.local/share/mingli-master/venv/bin/python scripts/runtime_launcher.py
# 前者 status=pass；后者 kind=described 且 capabilities=14
```

```bash
# A2 新通道在真盘上有产出：紫微那 12 条待核对规则必须出现在 source_candidate_patterns
# 用 360 张基准盘跑，至少一张盘的该字段非空，且每条 status 均为
# predicate_matched_pending_audit、均不含 verdict 字段
python3 scripts/verify_predicates.py --route ziwei --since snapshots/ziwei-before.json
```

```bash
# A3 旧通道未被污染：已审计规则的 source_conditioned_patterns 必须与阶段 A 之前逐字节一致
# 做法：阶段 A 施工前先存一份基线，施工后比对
```

```bash
# A4 越界扫描必须 clean：任何盘的任何输出都不得出现 verdict 字段
# verify_predicates.py 的第 4 项已覆盖，必须显示 clean
```

```bash
# A5 全仓门禁
make check
# Backend / Web / Admin 全绿，Ruff、mypy、两端 lint/typecheck/production build 通过
```

判据说明：

- **A2 是阶段 A 成立的标志。**当前紫微那 12 条待核对规则产出为零，跑通它意味着
  394 条库存开始出货。
- **A3 是最重要的回归。**新通道不得改变任何已审计输出。
- **A4 是红线。**出现 `verdict` 即整批打回。

---

## 5. 不在本文档范围

| 项目 | 归属 |
|---|---|
| 阶段 B（抽检式语义核对流程） | 等阶段 A 产出后另开文档 |
| 阶段 C（受限裁决扩展） | 同上 |
| 风水 171 / 相法 87 条库存 | 这两门 Provider 需要现场资料与影像输入，探测尚未跑通 |
| qimen / taiyi 的新谓词 | 编译器 route 白名单不含这两个 |
| `.runtime/v53-time-check-release` 签名发布 | 独立的发布工作，不阻塞阶段 0/A |
| 给 394 条库存做语义核对 | 那是阶段 B，本阶段只让它们能展示 |

---

## 6. 附录

### 6.1 代码位置索引（已核验）

`core/mingli-master/scripts/reading_engine/evidence_rules.py`

| 位置 | 内容 |
|---|---|
| 421 | `match_rule` 的激活门禁（阶段 A 不得修改） |
| 255 / 265 | `runtime_active` 与审计状态的绑定校验 |
| `_predicate_matches` | 谓词求值，新通道必须复用 |

`core/mingli-master/scripts/build_evidence_index.py`

| 位置 | 内容 |
|---|---|
| 1213 | `_apply_classical_evidence_bindings`，键集相等检查 |
| 1278 | `compile_evidence_rules(enforce_classical_bindings=False)` |
| 146 / 156 / 172 | 三个摘要函数 |

`backend/app/charts/contracts.py`：385 / 746 / 869 / 935 四处
`Literal["predicate_matched_not_verdict"]`

各 Provider 的 `_source_conditioned_patterns()`：`fengshui.py:812`、`liuyao.py:906`、
`luming.py:250` 等，新通道按此形状平行实现。

### 6.2 现有工具链

| 工具 | 用途 |
|---|---|
| `scripts/sync_binding_stubs.py` | 谓词与 binding 桩双向同步 + pin 同步 |
| `scripts/verify_predicates.py` | 五项机械验收：编译 / 路径 / 命中 / 判别力 / 越界 |
| `scripts/baseline_charts.py` | 360 张确定性基准盘（30 日期 × 12 时辰交叉积） |
| `scripts/verify_citation.py` | 引文真伪核验（全文库比对） |
| `scripts/list_unscoped_rules.py` | 列出待写谓词的规则 |
| `scripts/fact_path_inventory.py` | 导出 Provider 可寻址 fact path |

### 6.3 一个必踩的坑

所有调用 `~/.local/share/mingli-master/venv/bin/python` 的命令都要带
`PYTHONDONTWRITEBYTECODE=1`。漏了会往 venv 写 `__pycache__`，触发运行时完整性校验，
之后八字之类的 Provider 会以一个完全看不懂的错误失败：

```
"The V4 transaction did not produce a complete result."
```

补救：

```bash
find ~/.local/share/mingli-master/venv -type d -name __pycache__ -exec rm -rf {} +
```

### 6.4 相关文档

- `docs/predicate-authoring/SPEC.md` — 谓词施工规范（阶段 0.1 要改它）
- `docs/predicate-authoring/DEV-binding-stub-sync.md` — 桩同步工具开发文档（已完成）
- `docs/releases/evidence/2026-08-18-binding-manifest-baselines/` — binding manifest 可回滚基线
