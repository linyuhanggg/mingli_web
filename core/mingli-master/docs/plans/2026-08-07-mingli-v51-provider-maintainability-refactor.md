# 命理大师 V5.1 — Provider 可维护性重构一期（FactContract Seam）

日期：2026-08-07
分支：`qoder/mingli-v51-provider-maintainability-20260807`
前置 checkpoint：`b5b2863 fix: harden partial bazi fact boundaries`（上一轮 partial-luck-salience 返工的 9 个用户资产文件，已独立保护）
基线：HEAD 之前为 `de32270`（main，a74ce2f + 5 个测试加速 commits）；聚焦 7 文件 147 tests / 0 failed（33.57s）。

## 0. 文档与代码冲突记录（按任务要求以当前运行代码为事实）

1. Nowledge Mem 历史记录的源仓库为 `mingli-master-release-fix`，本轮实际权威工作树为
   `mingli-master-latest`；历史 canonical 记录的任务坐标（Task 7N）不适用于本轮，
   以本仓库 `docs/plans/2026-08-05-mingli-v51-partial-luck-salience.md` 与实际 git 状态为准。
2. 记忆记录 main HEAD 为 `a74ce2f`；实际 main 在其后有 5 个已提交的测试加速 commits
   （e225f50..de32270），任务基线数字（1515 tests / 512.09s）与该状态吻合，不构成冲突。
3. 交接文件（/tmp/mingli-v51-handoff-*.md）已被系统清理，不存在；上下文全部来自仓库内文档。
4. 安装的 runtime venv（~/.local/share/mingli-master/venv）存在外部进程反复生成的
   未入清单 pyc（如 `sxtwl.cpython-314.pyc`），被 runtime_python.py 完整性守卫拒绝。
   按任务第七节处置：不修改安装目录；复制 venv 到 mktemp 临时目录，删除副本中
   `__pycache__`，`MINGLI_PYTHON` 指向副本，`PYTHONDONTWRITEBYTECODE=1`。
   实测环境契约（本轮所有测试统一使用）：
   `/tmp/mingli-runtime.*/venv/bin/python -B` + `PYTHONPATH=scripts`
   + `MINGLI_RESEARCH_ROOT=~/.codex/skills/mingli-master`，且不设置 `MINGLI_STORE_ROOT`
   （设置它会使 CLI 子进程 store 根漂移，产生 unknown_state_token 假失败）。

## 1. 当前问题图

`scripts/adapter_validate.py`（3046 行）是唯一的 fact-layer 校验入口，13 个 system 的
事实校验全部堆在一个 `validate_payload` 里，按 system 用 if/elif 分派：

- fortune / selection / fengshui / physiognomy 已经委托给各自 engine 的
  `validate_fact_layer`（这是正确方向，但入口仍靠 system 字符串 if/elif）。
- bazi、ziwei、liuren、qimen、taiyi 的专属校验函数仍内嵌在本文件中。
- 八字是其中最大的一块：`_validate_bazi_v51_output`（1043-1126）、
  `BAZI_PARTIAL_*` 常量集与闭集 schema（1129-1212）、独立 oracle
  `_bazi_partial_luck_oracle`（1214-1237）、`_validate_bazi_supplied_salience`
  （1240-1275）、`_validate_bazi_supplied_pillar_luck`（1278-1458）、
  `_validate_bazi_partial_luck`（1461-1573），合计约 530 行。
- `validate_payload` 中还有三处八字专属特判：`bazi_static_scope` 改写
  required_outputs（2927-2929）、八字输出校验调用（2934-2936）、
  natal_static 缩减 required_calendar（2999）。

后果：任何 Provider 加算法或改事实形状都要碰这个 3000 行通用文件；Provider 领域
规则（六十甲子、大运顺逆）寄居在通用校验文件而不是 Provider-owned 模块；每加一个
Provider 都要在 dispatch 里再加一段 if/elif。

## 2. 目标 Module / Interface / Seam

新增内部 Seam：`scripts/fact_contracts/`（Provider-owned FactContract）。

```
scripts/fact_contracts/
  __init__.py   # 包初始化，公开 resolve 接口
  common.py     # 通用契约基类、finding 组装、声明性 required 集合裁剪的通用组合逻辑
  registry.py   # 从 Provider catalog 读取可选 fact_contract entrypoint，受 skill root 约束
  bazi.py       # 八字事实契约：闭集 schema、BAZI_PARTIAL_* 常量、独立 oracle、salience 校验
```

### Interface（内部）

```python
class FactContract(Protocol):
    contract_id: str
    def required_output_ids(self, payload, base_required) -> tuple[str, ...]: ...
    def required_calendar_keys(self, payload, base_required) -> tuple[str, ...]: ...
    def validate_output(self, payload, output) -> list[dict[str, str]]: ...
```

- `required_output_ids`：接收通用 REQUIRED_OUTPUTS[system]，返回按本 Provider 事实
  形状裁剪后的集合（八字 natal_static 剔除 luck_cycles）。
- `required_calendar_keys`：同理（natal_static 只要求 status+ganzhi）。
- `validate_output`：返回结构化 findings（`{"code","message","level"}`），与现有
  finding 形状一致；任何异常由 facade 捕获并转成明确 error finding，绝不向上抛。

### Seam 的边界（任务书第三节）

FactContract 负责：事实形状、字段一致性、版本/状态约束、独立重算或独立 oracle、
明确非空的错误结果。
FactContract 禁止负责：最终中文质量判断、关键词路由、模型选择、固定答案模板、
complete 之后再次拦截、Gateway 验签、LLM/供应商调用。

### 外部接口完全不变

- describe / prepare / complete；Described / Prepared / Accepted / Stopped 不变。
- `Accepted.public_copy` 仍是最终权威结果；complete 之后没有第二层拦截。
- `adapter_validate.validate_payload(system, payload, ...)` 的签名、返回形状
  （`{"ok","system","findings","codes"}`）与 finding 内容/顺序保持逐字段兼容。
- 调用方（bazi_calc._validate_facts 等 76 处）不需要任何修改。

## 3. 发现机制（复用现有 catalog，不建平行插件系统）

- Provider manifest 允许一个**可选**顶层键 `"fact_contract": "<module>:<Class>"`，
  语义与现有 `"entrypoint"` 键完全同构。catalog.py 不做顶层键白名单，
  `FORBIDDEN_ROUTING_KEYS`（keywords/aliases/synonyms/regex）递归拒绝保持不变，
  新增键不改变 describe 的外部命令与结果类型，不新增任何 object_id/dimension_id。
- `fact_contracts/registry.py` 用现有 `CatalogLoader(resources/runtime).load()`
  读取 catalog，按 `descriptor.id == canonical_system(system)` 找到 descriptor，
  读 `canonical_payload.get("fact_contract")`。
- entrypoint 解析复用 ProviderRegistry 同款守卫：`module:Class` 形式、
  `importlib.import_module` 后校验 `Path(module.__file__).resolve()` 必须
  `is_relative_to(skill_root)`，拒绝路径逃逸与标准库/任意动态 import。
- 失败语义（fail-closed，永不空回复）：
  - manifest 声明了 fact_contract 但加载失败（import 错误、类缺失、接口缺失、
    entrypoint 逃逸）→ facade 追加一条明确 error finding（如
    `fact_contract_load_failed:<system>`），该 payload 判 ok=False。
  - 畸形 JSON → CatalogLoader 抛 CatalogError → registry 捕获并同样转为 finding。
  - 未声明 fact_contract 的 system → 走 adapter_validate 内遗留实现（本轮 12 个）。
- 通用 dispatch 不再新增 if/elif：`validate_payload` 中用一次
  `contract = resolve_fact_contract(system)`；contract 存在时 required 集合与
  output findings 由 contract 提供，不存在时走原路径。以后迁移第 2..13 个 Provider
  只改 manifest 一行 + 新增该 Provider 的 contract 模块，不动 dispatch。

## 4. 为什么不一次拆 13 个 Provider

1. 每个 system 的事实形状、oracle、状态约束都不同，一次搬迁 = 一次全系统行为回归
   风险，无法用等价性测试逐个钉住。
2. 本轮目标是证明扩展路径存在且安全；八字是最复杂的一块（约 530 行 + 独立 oracle），
   八字迁移成功即证明该 Seam 能容纳最难的情形。
3. 未迁移 Provider 继续走原实现，行为零变化；迁移可以逐 Provider 独立提交、独立回滚。

## 5. 文件级迁移清单（本轮）

| 来源（adapter_validate.py） | 去向 |
| --- | --- |
| `_validate_bazi_v51_output`（1043-1126） | `fact_contracts/bazi.py` |
| `BAZI_PARTIAL_*` 常量集、闭集 schema（1129-1212） | `fact_contracts/bazi.py` |
| `_bazi_partial_luck_oracle`（1214-1237） | `fact_contracts/bazi.py`（仍与生成器 bazi_calc 分离） |
| `_validate_bazi_supplied_salience`（1240-1275） | `fact_contracts/bazi.py` |
| `_validate_bazi_supplied_pillar_luck`（1278-1458） | `fact_contracts/bazi.py` |
| `_validate_bazi_partial_luck`（1461-1573） | `fact_contracts/bazi.py` |
| `bazi_static_scope` 三处特判（2927-2929/2934-2936/2999） | 由 contract 的 `required_output_ids` / `required_calendar_keys` / `validate_output` 承接，dispatch 变为 domain-free |
| 通用 envelope、finding/report 组装、REQUIRED_* 表 | 留在 adapter_validate.py（facade）与 `fact_contracts/common.py` |
| ziwei/liuren/qimen/taiyi/fortune/selection/fengshui/physiognomy 校验 | 原地不动 |

独立 oracle 约束：bazi.py 的六十甲子/顺逆重算保持自包含，禁止 import
`bazi_calc` 或任何生成器计算函数（validator 不得“自己证明自己”）。

## 6. 提交顺序与回滚方式

| # | 提交 | 内容 | 回滚 |
| --- | --- | --- | --- |
| 0 | `fix: harden partial bazi fact boundaries`（已完成 b5b2863） | 9 个用户资产 checkpoint | `git revert b5b2863` |
| 1 | `docs: add provider maintainability refactor plan` | 本文档 | `git revert` |
| 2 | `test: characterize fact validation compatibility` | 钉住 validate_payload 现有返回形状的 characterization 测试（迁移前后都必须绿；迁移后等价性由它保证）。新增 seam/deletion/locality 测试在提交 3-5 走红→绿 | `git revert` |
| 3 | `refactor: add internal fact contract seam` | fact_contracts 包 + registry + facade 接线（未挂任何 manifest，行为零变化） | `git revert` |
| 4 | `refactor: move bazi validation behind fact contract` | 八字代码物理迁移 + bazi.json 挂 fact_contract | `git revert` |
| 5 | `test: add extension locality and deletion coverage` | locality/deletion/manifest 回归测试 | `git revert` |
| 6 | `docs: document adding algorithms and classical sources` | docs/maintainers/ADDING_ALGORITHM_OR_CLASSICAL_SOURCE.md | `git revert` |
| 7 | `chore: refresh generated matrices and replay artifacts` | audit_provider_completeness.py --write 等 | `git revert` |
| 8 | `docs: record final verification` | 最终验证记录 | `git revert` |

## 7. Deletion test

`scripts/test_v51_fact_contracts.py` 的 `BaziContractDeletionTests` 包含行为级
删除测试：以**临时 catalog 目录 + `catalog_root` 注入**构造一份删去 bazi manifest
`fact_contract` 键的 catalog 副本（八字契约模块本身不动），通过私有
`_validate_payload(..., catalog_root=...)` 测试入口注入；公开
`validate_payload` 的签名保持不变。对同一份由
`bazi_fact_adapter.py` 真实生成并篡改起运年龄的 payload 断言：生产 catalog 下
partial-luck oracle finding 存在，删除声明后所有 bazi_ 前缀 codes 消失且 facade
走遗留路径——证明八字契约确实被该 Seam 承载，而不是死代码。全程 in-process
调用 `validate_payload`（仅 payload 生成用 subprocess），不破坏真实工作树，也不以
读源码字符串代替行为。

独立验收返工（2026-08-07）补充了验收语义：仅证明"字符串消失"方向错误，
系统还必须能识别不可用状态。`test_deleting_the_contract_reports_the_unavailable_state`
在同一断连制品上运行八字 conformance，断言 facade 返回完整报告信封且含
error 级结构化 finding `fact_contract_unavailable`（消息含系统名），把"已知
Provider 的契约被断开"与"真正未知的体系"（保持冻结的 `unknown_system`）
区分开。字符串消失断言保留为 `test_deleting_the_contract_removes_every_bazi_code`。

## 8. 新增算法标准路径（第五节第 5 条）

给现有 Provider 增加算法，只改：
1. 该 Provider 自己的算法/adapter（如 scripts/bazi_calc.py 或 Provider 模块）；
2. `references/matrices/algorithm-source-dependencies.yaml` 中声明来源/版本/适用范围；
3. 增加独立 oracle、冻结 fixture 或 replay；
4. 仅当对外能力变化时才改 Provider manifest（capability/outputs）。

不改 transaction、complete、Gateway、宿主 Adapter；通用层不加 system-specific if/elif。
机器证明：`test_v51_fact_contracts.py` 中的 algorithm-locality 测试用临时 fixture
声明一条算法依赖，断言现有 `audit_algorithm_sources.py` 审计流程能发现并验证它，
且不触碰通用核心。不增加假的生产算法。

## 9. 新增古籍标准路径（第五节第 6 条）

见提交 6 的 `docs/maintainers/ADDING_ALGORITHM_OR_CLASSICAL_SOURCE.md`，要点：
本地 research fulltext（不入发布）→ 可发布 distilled rules / reference pack →
source manifest（版本/底本/anchor/SHA-256）→ classical evidence binding →
evidence scope binding → applicability 条件 → counter-evidence/冲突版本 →
build_evidence_index.py / audit_provider_completeness.py 生成与审计。
新增古籍不改 Gateway/transaction/中文模板，原则上不改 Python 路由；零命中保持零命中。
机器证明：locality 测试用临时目录合成一本 fixture 古籍，断言证据索引能收录它且
Python 路由文件无需任何修改。不增加假的生产古籍。

## 10. 测试命令与验收标准

环境（固定契约）：

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts
export MINGLI_RESEARCH_ROOT="$HOME/.codex/skills/mingli-master"
export MINGLI_PYTHON=/tmp/mingli-runtime.*/venv/bin/python   # pyc 隔离副本
unset MINGLI_STORE_ROOT
PY=/tmp/mingli-runtime.*/venv/bin/python
```

命令：

```bash
$PY -B -m unittest scripts/test_v51_fact_contracts.py -v          # 新增测试
$PY -B -m unittest scripts/test_adapter_validate.py ... (聚焦 7 文件)  # 八字聚焦
$PY -B -m unittest scripts/test_v51_catalog_driven_registry.py -v # catalog/registry
$PY -B scripts/export_v51_answer_cases.py --check                 # answer exporter
$PY -B scripts/audit_provider_completeness.py --check             # 13/13
$PY -B scripts/run_test_suite.py                                  # 全量 runner（≤10 分钟）
git diff --check && git status --short --branch
```

验收：任务书第八节全部条款；尤其——validate_payload 返回逐字段兼容；八字专属知识
从 adapter_validate.py 消失；新增 FactContract/算法/古籍的 locality 行为测试通过；
13 Provider 可用；全量 0 失败；Gateway/SKILL.md/complete/部署未触碰；未 push。

## 11. 实施期偏离记录（兜底原则）

1. **replaces_legacy_validation 接管标志**（提交 5 之前发现）：契约若只作为
   "附加校验"叠加在遗留校验器之上，迁移既有 system 会产生双重 findings。
   修正：契约声明 `replaces_legacy_validation = True` 后，facade 放弃该
   system 的遗留 required 表、taiyi/divination override 与遗留专属校验器，
   契约全权负责。八字契约的 required 输出集合改为契约自持（逐字冻结自
   迁移前的 facade 表），报告与迁移前逐字段一致。
2. **release closure 必须显式收录 fact_contracts**（提交 3aa1c7f）：
   `release/runtime-closure-v1.json` 是显式 allow-list，新包不在其中导致
   全新安装上 prepare 直接 stopped/error。修复为添加
   `scripts/fact_contracts/*.py` 模式（与 `scripts/reading_engine/*.py`
   同形）。教训：任何新增运行时 Python 包必须同时进入 closure allow-list，
   该要求已隐含在 test_v51_release_surface 中。
3. **validate_output 仍受 `and output` 守卫**：空 output 不进入契约的
   output 级复算，与迁移前 facade 行为一致；characterization 测试冻结了
   该语义。注意：payload 级状态检查不在该守卫内——八字契约的冲突状态
   （`validate_conflict_state`）在契约存在时无条件执行，与迁移前 facade
   对冲突状态的无条件上报逐字一致（评审 F3 修复后语义）。
4. **finding 顺序与公开签名已恢复兼容**：第三次独立验收指出原实现把
   payload-level 冲突 finding 移到 missing-output 之后，并在公开
   `validate_payload` 上暴露了测试用 `catalog_root`。现已把冲突 hook 恢复到
   通用 envelope findings 之前；catalog 注入下沉到私有 `_validate_payload`，
   由顺序断言与 `inspect.signature` 回归测试冻结。
5. **catalog 本体损坏时的 declared 判定降级（已知残余缝隙）**：加载失败
   异常路径的 is_declared 兜底需要重走 CatalogLoader；当 catalog 本体损坏
   （非 UTF-8、manifest 解析失败等）时，兜底同样失败，declared 判定降级为
   False，已声明系统的报告会同时附带 fact_contract_load_failed 与
   unknown_system。ok=False 的 fail-closed 判定不变，且当前没有消费方按
   unknown_system 分支处理；不为此实现缓存兜底（避免过度设计）。
6. **required-key hook 返回值必须先归一**：第三次独立验收发现
   `required_output_ids` / `required_calendar_keys` 若返回字符串或不可哈希项，
   可分别绕过 required 检查或让 facade 抛出 `TypeError`。facade 现只接受
   `tuple[str, ...]` 且每个 key 必须非空；非法返回统一生成
   `fact_contract_invalid_return`，不迭代、不回显 hostile 内容、不向上抛。
