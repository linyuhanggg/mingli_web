# 命理大师 V5.1 模型选术与无资料降级 — 返工实施计划

本计划对 Codex 独立验收指出的 V5.1 模型选术与无资料降级的确定性
缺口做返工。所有改动只服务于 P1 真实根因：不接受文档/测试名称/
release evidence 的等价重写，必须以代码与行为测试为准。

## 一、修复目标与不变量

下列契约在本返工后必须恒成立，并被测试明确断言：

1. 多候选 + 无显式 capability：核心不按资料数量、cost、priority
   选术；返回 `Stopped.need_input` + `choose_capability` 模板，由宿
   主模型依据 `describe` 重新提交。
2. 显式 capability 缺资料：核心只针对该 capability 返回
   `Stopped.need_input` 与可恢复 token；不试探其他 capability。
3. pending token 不得被改写 capability：显式 capability 与 pending
   capability 不一致时返回 `Stopped.conflict`；核心不重写 token。
4. fallback 必须丢弃 pending token 并以无 token 方式发起新根；
   每个用户请求最多一次，核心不循环试 Provider。
5. 新受试者、新对象、显式不同 capability 必为真正独立新根：
   - 新根不继承旧 `parent_reading_id`、`root_reading_id`、
     `action`；
   - 新根不 claim 旧 token 的 lineage 槽位；
   - 旧 token 仍可用于原 scope 续问；
   - 新根不继承旧 comparisons。
6. `correct` / `restart` 只用于同一受试者、同一对象、同一能力；
   scope 不一致或同时显式切换 capability 时返回
   `Stopped.conflict`，不会偷偷改写。
7. Interface 不读取 pending 文件、不依赖 `isinstance(TurnEngine)`、
   不调用 engine 私有方法；透明 engine proxy 与直接 `TurnEngine`
   行为一致。
8. 零证据 + 非空 claim scope：返回 `Prepared` 且 brief 必须包含
   `limit.source_gap` 或等价结构化 limit；不得伪造证据。
9. 空 claim scope：返回非空 `Stopped.unsupported`，public_copy
   非空；不返回看似成功但无成稿依据的 `Prepared`。
10. 部分维度：只交付被支持的 claim scope；未覆盖维度进入
    `limit.unsupported_dimension`，不整轮丢弃。
11. required comparison 不可用/缺资料/与 primary 同 lineage：
    返回 `Stopped.need_input` / `Stopped.unsupported`，不静默删
    除；optional comparison 不可用时降级为 limit，不阻断 primary。
12. Provider `display.zh-CN.description` 足够让宿主模型依据
    `describe` 自主选术；SKILL.md / 通用 core 不写真实术数名称或
    分工表，不写"看到某词即选某能力"。
13. 无 token 的相同内容是两个独立用户轮次，必须创建不同新根；
    幂等只由 opaque token 保证，不用请求内容摘要充当新根身份。
14. publishability 不只检查“非空”：fact、evidence、scope、finding
    之间的引用必须闭合；断链返回非空 `Stopped.error`。

## 二、P1 修复与提交切分

为便于独立 revert，将改动切成小提交；不重写既有 7 个提交的历史。

1. `test: expose detached root and pending engine seam`
   - 新增 `scripts/test_v51_p1_rework.py`：
     - A. 新根 lineage：scope 变化 / 显式 capability 变化 / 同一
       scope 显式 capability 变化 / 新根不继承旧 comparisons /
       correct/restart + scope 不一致。
     - B. Pending engine seam：interface 不读 pending 路径、不
       isinstance、不调私有方法；透明 proxy 与直接 engine 行为
       一致。
   - 同时更新 `scripts/test_v51_model_selection_fallback.py` 的
     fixture `_build_preparation`，让现有 `test_prepared_with_zero_
     evidence_has_source_gap_limit` 在新的“claim scope 必须非空”
     边界下继续通过。
2. `fix: detach new scopes from prior reading lineage`
   - `scripts/reading_engine/interface.py`：`_prepare` 重写 lineage
     决策。scope 变化或显式 capability 变化时，engine 必须以
     `state_token=None, transition=None` 收到请求；不传旧 token。
   - `scripts/reading_engine/turns.py`：`_reading_identity` 给出
     “new”根路径；`_stage` 在无 lineage 时显式写入
     `action="new"`、`root_reading_id == reading_id`。
3. `refactor: move pending capability binding behind engine seam`
   - `scripts/reading_engine/turns.py`：新增
     `TurnEngine.pending_intake_capability(state_token)`，封装
     pending 文件的读取与 capability 解析。
   - `scripts/reading_engine/interface.py`：删除
     `_pending_intake_capability` 私有读取与 `isinstance(TurnEngine)`
     分支，改为调用 engine seam。
4. `test: require publishable claims and comparison provenance`
   - 三个独立测试在 `test_v51_p1_rework.py`：
     - `EmptyClaimScopeUnsupportedTests`：facts 非空 + claim scope
       为空 → `Stopped.unsupported` 且 public_copy 非空；
     - `ZeroEvidenceSourceGapLimitTests`：facts+scope 非空 + 零
       证据 → `Prepared` 且 brief 含 `limit.source_gap`；
     - `PartialDimensionsLimitTests`：请求多维度时仅保留被支持
       维度，未覆盖维度进入 `limit.unsupported_dimension`；
     - `ComparisonProvenanceTests`：required 缺资料→`need_input`/
       `unsupported`、optional 缺资料→降级 limit、required 重
       复→`unsupported`、optional 重复→显式
       `limit.comparison_skipped`。
5. `fix: enforce honest partial and comparison results`
   - `scripts/reading_engine/turns.py`：新增
     `_enforce_publishability` 在 `_run_prepare` 之后统一校验
     facts/claim_scopes/evidence/findings/limits/dimensions 的引用闭包。
     `ResolvedComparison` 是逐轮冻结值，不修改共享 catalog
     descriptor；其 `requirement` 在 engine 一侧驱动
     required/optional 行为：
     optional 失败时丢弃并加 `limit.comparison_skipped`，不阻断
     primary；多主体 optional comparison 按整个比较原子成功或失败，
     不泄漏部分主体结果；新根不继承旧 comparisons。
   - `scripts/reading_engine/interface_contracts.py`：新增
     `ComparisonSelection(capability_id, requirement)`，`Intent
     Selection.comparisons` 取代旧 `comparison_capability_ids`
     列表。
   - `scripts/reading_engine/provider_protocol.py`：`ProviderRequest.
     comparisons` 升级为带 requirement 字段的列表。
   - `scripts/reading_engine/turns.py`：`_turn_digest` 与
     `_save_pending` / `_merge_pending` 切换到新字段。
     `_merge_pending` 仅为已落盘旧状态兼容读取
     `comparison_capability_ids`，新写入只使用 `comparisons`。
   - `scripts/reading_engine/interface.py`：`_resolve_comparisons`
     显式 required/optional 处理，required 失败→`Stopped`，
     optional 失败→丢弃。
6. `docs: make provider capability descriptions self-contained`
   - 13 个 `resources/runtime/providers/*.json` 的
     `display.zh-CN.description` 全面扩展到包含：适用请求范围、
     真实输入前提、不支持的边界、相对结构上重叠能力的选择依据。
7. `refactor: localize structural capability selection`
   - `scripts/reading_engine/interface.py`：`_choose_descriptor`
     改为仅映射 `RuntimeCatalog.select(...)` 的返回；删除直接调
     用 `RuntimeCatalog._matches` / `_effective_dimensions` 的重
     复实现；删除无生产调用的 `_provided_field_ids`。
   - `scripts/reading_engine/catalog.py`：`assumption_cost` /
     `default_priority` 标注为 deprecated audit-only metadata，
     注明不得进入选术逻辑；当前 release schema 暂保留以避免制品
     兼容破坏。
8. `docs: certify model-selected capability fallback corrections`
   - 更新 SKILL.md：移除“必要时用 correct/restart”误导；明确新
     subject/object 默认独立新根；明确 pending fallback 必须丢
     弃 token；明确比较的 required/optional 语义；明确零命中但
     有可发布范围时必须带 source gap；明确无 claim scope 返回
     unsupported。

## 三、SKILL.md 措辞要点

- 显式 capability 缺资料 → 唯一对应的 `Stopped.need_input` +
  pending token；不静默循环试其他 capability。
- fallback 必须丢弃 pending token 并以无 token 方式发起新根；
  每个用户请求最多一次。
- 同一受试者同一对象类型的续问可继续使用原 `capability_id`；新
  受试者或新对象默认独立新根。
- `correct` / `restart` 只用于同一受试者同一对象和同一 capability；
  scope 不一致或同时切换 capability 返回 `Stopped.conflict`。
- pending token 显式 capability 与 pending capability 不一致时
  返回 `Stopped.conflict`；丢弃 token、以无 token 方式重起新根。
- `comparisons` 的 required 不可静默删除；optional 不可用时记录
  limit，不阻断 primary；新根不继承旧 comparisons。
- 零命中但有可发布范围：`brief.limits` 必须带 `limit.source_gap`
  或等价结构化 limit；无 claim scope 时返回 `Stopped.unsupported`。

## 四、测试矩阵

固定 runtime：
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts $HOME/.local/share/mingli-master/venv/bin/python -B`

下列命令在返工后必须以 exit code 0 通过（不计 provider_completeness
的基线失败）：

- `python -m unittest scripts.test_v51_p1_rework`（新增 32 个 P1
  验证）
- `python -m unittest scripts.test_v51_model_selection_fallback`
- `python -m unittest scripts.test_v51_catalog_driven_registry`
- `python -m unittest scripts.test_v51_portable_interface`
- `python -m unittest scripts.test_v4_followup_state`
- `python -m unittest scripts.test_v51_closed_world_brief`
- `python -m unittest scripts.test_v51_cross_host_contract`
- `python -m unittest scripts.test_v4_skill_minimalism`

下列 audit 必须以 exit code 0 通过：

- `python scripts/audit_v51_vocabulary_locality.py --check`
- `python scripts/audit_release_archive.py --source .`

`scripts/audit_provider_completeness.py --check` 在固定 base
`2e9c8a4` 上已经返回 exit code 1（"provider matrix differs from the
canonical live snapshot" 与各 provider 的 “not ready” 提示），属
于基线既有问题，本返工不处理；release evidence 中需明确记录对照。

## 五、最终验收对照

完成返工后，最终验收条件（与本计划 §一 不变量一一对应）应全部
满足；worktree 必须保持 clean；release evidence 文档
`docs/releases/2026-07-31-mingli-model-selection-and-graceful-
fallback.md` 必须包含真实命令、真实 exit code、真实测试数量与耗
时、明确未部署/未安装/未触碰 Gateway/8642/8645 的声明。
