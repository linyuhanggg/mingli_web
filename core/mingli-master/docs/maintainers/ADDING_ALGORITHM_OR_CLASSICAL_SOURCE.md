# 为命理大师 V5.1 增加算法或古籍的标准路径

本文档面向维护者。目标：新增一个算法或一本古籍时，改动尽量局部、可测试、
可独立回滚，且不触碰 Gateway、通用 transaction、complete 事务、最终中文模板
或宿主 Adapter。

两条路径都依赖既有管线，不引入新的插件系统或 source registry：

- 算法来源与审计：`references/matrices/algorithm-source-dependencies.yaml`
  + `scripts/audit_algorithm_sources.py`
- 古籍证据管线：`references/matrices/classical-evidence-bindings-v1.json`
  （由 `scripts/generate_classical_evidence_bindings.py` 生成）、
  `references/matrices/evidence-scope-bindings-v1.yaml`、
  `scripts/build_evidence_index.py`、
  `references/catalog/SOURCE_PROVENANCE_POLICY.md`
- 事实校验迁移（可选）：Provider manifest 的 `fact_contract` entrypoint
  + `scripts/fact_contracts/`（见
  `docs/plans/2026-08-07-mingli-v51-provider-maintainability-refactor.md`）

## 一、给现有 Provider 增加一个算法

只改以下位置：

1. **该 Provider 自己的 adapter / 算法代码**。例如八字改
   `scripts/bazi_fact_adapter.py`。通用层（`adapter_validate.py` facade、
   reading transaction、Gateway、宿主 Adapter）不加任何 system-specific
   if/elif。
2. **算法来源声明**：在
   `references/matrices/algorithm-source-dependencies.yaml` 对应 provider 的
   `dependencies` 下新增一条记录。必填字段：
   `id`、`category`、`version`、`status`、`convention`、
   `primary_sources`（引用 `source_registry` 锚点或外部工程参考）、
   `independent_test_sample`。
   - `status` 必须是已完成验证的状态；占位词（TODO/placeholder/待定等）
     会被 `audit_algorithm_sources.py` 的 `PLACEHOLDER_RE` 与
     `DEFERRED_VERIFICATION_RE` 直接判失败。
3. **独立验证**：为该算法增加独立 oracle、冻结 fixture 或 replay。
   独立 oracle 不得复用被测生成器的计算函数（禁止"自己证明自己"）。
   八字的样板是 `scripts/fact_contracts/bazi.py` 中的
   `_BAZI_ORACLE_*` 常量表 + `_bazi_partial_luck_oracle`。
4. **Provider manifest 仅在对外能力真的变化时才改**
   （`resources/runtime/providers/<id>.json`）。纯内部算法不修改 manifest。
   manifest 永远不写关键词、别名、同义词或 regex。
5. （可选）若该算法的事实形状需要结构化校验，把它放进该 Provider 的
   FactContract（`fact_contract` entrypoint），而不是 facade。

验证命令（环境契约见仓库 README；`MINGLI_RESEARCH_ROOT` 必须指向权威语料根）：

```
python -m unittest test_algorithm_source_dependencies test_v51_fact_contracts
python scripts/audit_algorithm_sources.py
python scripts/run_test_suite.py -j 3 --research-root ~/.codex/skills/mingli-master
```

机器证明：`scripts/test_v51_fact_contracts.py` 的
`AlgorithmAndClassicalSourceLocalityTests` 在临时目录里合成一条新的算法声明，
证明 `audit_algorithm_sources.audit_matrix` 能发现并验证它（包括 SHA 篡改与
未验证状态两种失败），全程不改通用核心。不要为了演示添加假的生产算法。

## 二、新增一本古籍

严格区分两类材料：

- **本地 research fulltext**：完整转录本保存在本地研究语料根
  （`MINGLI_RESEARCH_ROOT`，生产安装为 `~/.codex/skills/mingli-master`）之下，
  只读使用，不随 Skill 发布。
- **可发布的 distilled rules / reference pack**：发布物只保留精确 anchor、
  短摘录、底本/版本说明与 SHA-256（见 `algorithm-source-dependencies.yaml`
  顶部 `audit_policy` 与 `references/catalog/SOURCE_PROVENANCE_POLICY.md`）。

步骤：

1. **source manifest**：在
   `references/matrices/algorithm-source-dependencies.yaml` 的
   `source_registry` 中新增条目：`title`、`edition_or_recension`（版本/底本）、
   `normalized_path`、`sha256`、`anchor`、`exact_excerpt`、`material`、
   `license_status`。冲突版本或 counter-evidence 通过追加独立条目并在相关
   dependency/binding 的 rationale 中显式说明，而不是覆盖原条目。
2. **classical evidence binding**：在 binding 源记录中声明该古籍规则
   （rule_id、scope、applicability 条件、fact_refs），然后运行
   `python scripts/generate_classical_evidence_bindings.py` 重新生成
   `references/matrices/classical-evidence-bindings-v1.json`。生成器是
   确定性的：同样输入必须得到同样输出。
3. **evidence scope binding**：若规则需要限定在某条 route / 某类事实层状态
   下才允许引用，在 `references/matrices/evidence-scope-bindings-v1.yaml`
   的 `bindings` 下新增条目（`route`、`rationale`、`evidence_role`、
   `predicates`）。该文件 policy 是 `unlisted_rules: disabled`：未登记的
   规则默认禁用。
4. **applicability 条件**：binding 的适用条件写在 binding 记录本身，
   由证据引擎在运行时求值；不修改 Python 路由代码。
5. **索引与矩阵**：binding 清单是被 SHA-256 pin 钉住的审计产物。重新生成
   binding 后，必须先把新的清单哈希同步到两处 pin——
   `scripts/build_evidence_index.py` 与
   `scripts/reading_engine/evidence_rules.py` 的
   `CLASSICAL_EVIDENCE_BINDINGS_SHA256`——否则索引构建会以
   `classical evidence binding manifest hash mismatch` 失败封闭（这是刻意
   的审计闸门：未审计的新古籍不能悄悄进入运行时索引）。pin 更新后运行
   `python scripts/build_evidence_index.py` 重建证据索引；若 scripts 指纹
   变化，运行 `python scripts/audit_provider_completeness.py --write` 刷新
   `references/matrices/provider-completeness.yaml`。
6. **测试**：为新古籍增加绑定/范围/审计测试（可参考
   `scripts/test_v51_classical_evidence_bindings.py`、
   `scripts/test_v51_evidence_source_integrity.py`）。

硬约束：

- 不修改 Gateway、通用 transaction、最终中文模板；原则上不修改 Python
  路由代码——新增古籍的落点是资料、manifest、binding、索引与测试。
- **古籍零命中仍保持零命中**：不得为了"有引用"硬塞无关资料；证据引擎
  找不到匹配时必须维持空结果。
- 不把完整研究转录本复制进发布目录。
- 不把 SHA-256 变成 Skill 与宿主之间的信任协议；它只服务于本地语料的
  逐字节审计。

机器证明（两层）：

- `AlgorithmAndClassicalSourceLocalityTests` 用临时目录合成一条新的古籍声明
  （fulltext + source 记录），证明 `audit_matrix(verify_research_sources=
  True, research_root=<临时根>)` 能发现并验证它，篡改 SHA 或状态未验证都会
  被抓住，全程不改通用核心。
- `ClassicalExtensionFullChainLocalityTests`（独立验收返工补充）复制整棵
  发布树后合成一本新书，走完 source pack → classical binding → scope
  binding → 生成器 → evidence index → 运行时匹配的完整链路：生成器以
  纯数据方式发现新书（inactive_unverified，生产 binding 零漂移）、pin 拒绝
  未审计新书进入索引（零命中保持零命中，失败封闭）、inactive 规则对满足
  谓词的事实仍然零命中，且全程没有任何 `*.py` 被修改。

测试只用合成 fixture，不添加假的生产古籍。

## 三、新增或迁移 Provider FactContract（参考）

- manifest 加一个可选顶层键 `"fact_contract": "module:Class"`，与
  `entrypoint` 平级，机制相同；不新增用户可见能力、不写关键词。
- 契约模块必须位于 Skill 根目录内；registry 拒绝路径逃逸、相对导入、
  非法 entrypoint，所有失败都变成明确 finding，不产生空回复。
- 契约设置 `replaces_legacy_validation = True` 后即完全接管该系统的
  事实校验，facade 的遗留 required 表与遗留校验器自动让位，通用
  dispatch 无需任何修改。八字（`fact_contracts/bazi.py`）是唯一完整样板；
  其余 Provider 未迁移前继续走原实现。
