# 命理大师 V5.1 会话核心收敛实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** 将已部署的 `mingli-master` 收敛为可被任意宿主直接调用的深模块；修复结构化补资料、闭集成稿、发行面污染和会话连续性，同时不把命理路由、验签或交付否决重新放回 Hermes Gateway。

**Architecture:** 保留一个小而稳定的 `execute(Command) -> Result` Interface。`describe` 提供可缓存的能力描述，`prepare` 是唯一的计算、状态推进和补资料入口，`complete` 只做核心内原子提交。Provider 和其 manifest 是术语、输入、计算、证据、解释素材的唯一所有者；宿主 Adapter 只转换协议；Gateway 只发送普通消息。

**Tech Stack:** Python 3.10+（项目固定运行时）、dataclass、JSON codec、文件锁与原子文件存储、现有 13 个确定性 Provider、既有古籍/证据资源。不得新增模型 API、常驻服务、依赖或 Gateway 进程。

## 实施状态（2026-07-30）

- 已完成结构化补资料（`050292b`）、周运公开视图压缩（`94b268d`）和 request scope 持久化（`46b0456`）；后续提交继续只改隔离工作树。
- 本轮将 Provider-owned findings、起法选项、有效时间范围、发行 closure 和 fresh-install 验证作为同一条主链收口；不部署、不修改运行中的 Gateway。
- 当前基线的部分“全文本审计”测试期待仓库不存在的 `references/fulltext/**` 资料。该问题不能靠复制未知语料掩盖：本计划保留原有算法和索引，只将它记录为独立的资料恢复任务，不把它变成 portable core 的运行前置条件。

---

## 0. 实施基线、事实与非目标

### 已核对的事实

- 实际已安装/运行的 portable core 是提交 `a5c33e79`；用户指定的旧工作树停在其祖先 `c8cf4ca`，并有未提交用户资产。
- 因此所有本计划的代码修改只发生在基于 `a5c33e79` 的隔离工作树；旧树、其计划和未提交文件一律不覆盖、不 reset、不清理。
- 当前活动 Hermes release 为 `0b7aab32a3`，其 Gateway 已删除命理 observer、guard、二次摘要验证和命理 Turn Ledger；用户最初列出的 `9692659130` 是仍保留旧代码的非活动归档，既不作为验收对象，也不在本计划中删除。
- 当前运行代码仍有四个缺口：`Stopped.need_input` 没有机器可读字段；`Prepared.brief` 的解释素材过于原始；`complete` 前的宿主可阅读面混入了旧协议；发行器把几乎整个仓库（含旧说明和测试）装进 Skill。

### 本计划明确不做的事

- 不修改、重启、停止或探测生产 Gateway 与端口 8642/8645。
- 不恢复或改名保留 observer、guard、Gateway 命理正则、摘要重建、命理 delivery veto 或兼容分支。
- 不重写已完成的 13 个 Provider、古籍语料或底层计算体系。
- 不在核心放入模型选择、模型调用、供应商 SDK、Hermes 私有接口、shell 命令形状、临时文件路径或固定中文回答模板。
- 不为首问传输中断引入默认的跨模块 exactly-once ledger。

### 对“技能里不能硬编码术语”的可执行解释

字面禁止所有术语不可执行：算法与古籍语料本身必然含领域词。最终约束是：

- `SKILL.md`、generic core、Interface、通用 Adapter 不得维护体系清单、触发词、别名、关键词、正则或固定回答话术；
- 可见的领域名称、输入字段、能力、解释素材和限制只由相应 Provider manifest/资源拥有；
- Provider 算法内部所必需的领域词保留在该 Provider 的局部实现，不能泄漏为通用路由规则。

## 1. 一句话架构结论

以 `mingli-master` 为唯一命理权威：它把 Provider 的确定性事实、证据、边界、会话状态和原子提交藏在一个深模块内；任意宿主只调用三种 Command，依据 `Prepared.brief` 的闭集自然成稿，得到 `Accepted` 即直接展示，后面没有第二层命理判断或拦截。

## 2. 当前问题图与根因

```text
用户自然语言
       │
       ▼
宿主模型 ──错误的旧文档/错误运行时──► 自行挑选脚本、Provider 或补造输入
       │                                      │
       │ prepare                              ▼
       ▼                           原始 facts / 空 conclusion
mingli-master core ───────────────────────────┘
       │
       ├─ Stopped.need_input 只有一句文字，宿主无法可靠续接
       ├─ Prepared.brief 缺少足够的 Provider-owned 解释素材
       └─ complete 接受自然中文，正确但不能纠正上游自由发挥
```

历史的 Gateway 双权威已经删除；本次问题不是“少一个 Gateway gate”。真实根因是：

1. **宿主表面污染：** `release_deploy.py` 默认发布几乎所有 tracked file。实际会话先读取了旧 `references/tool-adapters.md`，于是绕开 portable Interface、尝试错误的 Python/旧入口，并自行挑算法。
2. **补资料不是协议对象：** core 知道缺什么，却只把它拼成一句公开文字；宿主无法稳定保存 token、显示字段、合并用户补充。
3. **成稿前信息过薄：** `turns.py` 把多项 judgment 固定为 `caller_review_required` 且 `conclusion=""`。宿主拿到的主要是原始事实，容易写成泛化、混入环境记忆或把“按时间起卦”错映射为随机投币。
4. **错误的修复方向会再造空回复：** 要求 `complete` 携带逐句 span、摘要、claim 签名或强制引用集合，会把自然中文变成第二个必过 gate；任一字段错配即可再次发生“核心已经成功、最终却无输出”。

`既济` 与当前输出风格差异主要来自后者“本地规则/解释卡片先形成可用材料，再成稿”，而不是 Gateway。当前应在 `Prepared` 前丰富 Provider-owned 素材，不应在 `Accepted` 后再裁决。

## 3. 推荐目标架构图

```text
Codex / Hermes Agent / Claude Code / 其他宿主
    │
    │ 缓存 describe；把用户明确资料转为 manifest 字段；仅用 brief 成稿
    ▼
薄 Adapter（进程内 / CLI / MCP）
    │  JSON 或类型转换；保存 opaque state_token；没有命理判断
    ▼
┌────────────────── mingli-master 深模块 ──────────────────┐
│ ReadingInterface.execute(Command) -> Result               │
│   Catalog + Provider manifests  ─── 输入/术语/能力所有权   │
│   Provider seam                 ─── 计算/证据/解释素材     │
│   Brief compiler                ─── 闭集 caller_view      │
│   Turn engine + state token     ─── 续问/纠正/重起/提交     │
│   Atomic storage                ─── 版本、lineage、恢复    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Accepted.public_copy ─────────────────────────► 宿主原样展示

Gateway（图外）：只承担任何普通最终消息的收发与通用投递可靠性。
```

### 深模块检查

| 原则 | 落点 |
| --- | --- |
| Deep module | Interface 只有三个 Command；Provider、存储、lineage 和证据复杂度都藏在 core 内。 |
| Interface | 对外只暴露可序列化的 Command/Result，不暴露文件、digest、internal id、shell 或模型。 |
| Seam | Provider manifest + `ProviderPreparation` 是唯一可扩展 seam；Adapter 是纯传输 seam。 |
| Locality | 领域术语、起卦方法、限制和解释素材与 Provider 同处；generic core 不扫描术语。 |
| Deletion test | 删除 Gateway 命理代码后 core 仍能完成一轮；删除 core 后 Gateway 仍能发送普通消息。 |

## 4. 模块职责与禁止职责

| Module | 负责 | 禁止 |
| --- | --- | --- |
| `interface_contracts.py` | 三 Command、四 Result、`InputRequest`、闭集公开对象的 JSON contract | Provider import、领域词、宿主类型、路径、digest 协议 |
| `interface.py` | 执行调度、错误归一化、把缺资料映射为结构化请求 | 解析自然语言、读取宿主记忆、语义审稿、Gateway 兼容 |
| `catalog.py` + manifests | capability、字段 schema、展示词、可用起法、限制的唯一数据权威 | 关键词路由、别名/正则、会话判断 |
| Provider seam / Provider | 既有算法、输入校验、确定性计算、古籍证据、解释素材与 source gap | 在 Gateway 或 generic core 复制体系规则 |
| `brief.py` | 从公开 Provider projection 构造唯一的 `caller_view` | 读取私有 calculation、环境记忆、未选 Provider 资源 |
| `turns.py` | pending/prepared/accepted、lineage、幂等、原子 commit、恢复 | 把自然中文当作另一份待验签业务对象 |
| `state_token.py` / storage | opaque token、版本、并发锁、内部 hash/一致性；每个安装实例的私有状态命名空间 | 向宿主暴露 reading 文件、跨 profile 解析 token，或变成第二套业务账本 |
| CLI/MCP/进程内 Adapter | Command/Result 的序列化、通用 transport failure 到非空 Result 的归一化 | 任何命理路由、资料推断、续问判断、摘要验证 |
| 宿主模型 | 选择 Skill、从 describe 的数据作结构化选择、只用 brief 写自然中文、直接展示 Accepted | 补造用户事实、读 store、混入环境记忆、Accepted 后改写文本 |
| Hermes Gateway | 普通收发和与内容无关的投递 obligation | 命理 import、observer、guard、意图正则、reading ledger、内容 veto |

## 5. 唯一外部 Interface（最终推荐）

```text
execute(Command) -> Result
```

`describe` 是可缓存的数据加载，不应每轮调用。缓存键为 `protocol_version + manifest_digest`；安装、Skill 重载或 digest 改变后刷新。`publish-question`、`probe`、`run` 及任何 shell 子命令全部退出生产 Interface。

### Command

```text
Describe { kind: "describe" }

Prepare {
  kind: "prepare"
  query: string
  intent: {
    subject_refs: string[]
    object_id: string
    dimension_ids: string[]
    horizon: { kind_id: string, start?: string, end?: string }
    capability_id?: string
    comparison_capability_ids: string[]
  }
  facts: { [subject_ref]: { [manifest_input_field_id]: JSON value } }
  state_token?: opaque string
  transition?: "correct" | "restart"
}

Complete {
  kind: "complete"
  state_token: opaque string
  public_copy: non-empty string
}
```

`Complete` **不增加** `draft_token`、摘要、签名、span、逐句 claim 或 Gateway envelope。现有 `state_token` 同时承担 intake、prepared 和 accepted 状态引用，已足以隐藏 reading store、路径、digest 和内部 ID。

### Result

```text
Described {
  kind: "described"
  protocol_version: string
  manifest_digest: string
  capabilities: CapabilityView[]
}

Prepared {
  kind: "prepared"
  state_token: opaque string
  brief: CallerView
}

Accepted {
  kind: "accepted"
  state_token: opaque string
  public_copy: non-empty string
}

Stopped {
  kind: "stopped"
  reason: "need_input" | "unsupported" | "conflict" | "error"
  public_copy: non-empty string
  state_token?: opaque string
  input_request?: InputRequest
}
```

`InputRequest` 是减法：它只把 core 已知的最小缺失输入公开为数据，不另开 `resume` 协议，也不让宿主猜中文。建议字段为：

```text
InputRequest {
  requirements: [{
    any_of: [{ id, label, type_id, description?, choices? }, ...]
  }, ...]
}
```

`CallerView` 保留现有 `ReadingBrief` 的闭集，并显式分组为：

- `request`: 本轮 query、subject refs、requested dimensions、horizon/capability；
- `facts` 和 `evidence`: 本轮公开、可引用的确定性资料；
- `findings`: Provider-owned、数据化的解释素材（可选、可递增）；精确依据可标为 `support_mode=exact`，未声明精确依据时明确标为 `shared_turn`，不假装逐项证据归属；
- `claim_scopes`: allowed subjects/domains、specific-event policy、maximum certainty 和可支持关系；
- `limits`: unresolved boundaries、source gaps、不能作出的结论。

其中 `claim_scopes` 是给成稿上下文的边界数据，**不是** `complete` 的阻断性验签输入。核心内部仍校验 token、版本、lineage、provider projection、引用关系、文件完整性与原子存储。

## 6. 端到端流程

### 首问

1. 宿主使用缓存的 `describe` 选择 manifest 声明的 capability/字段；只放用户明确提供或可信系统时钟等声明来源的 facts。
2. 调用 `prepare`。
3. `Prepared`：宿主隔离成稿上下文，只给模型 `brief`，自然组织答案；调用 `complete`。
4. `Accepted`：原样展示；没有后置命理检查。

“算一下这周运势”会得到某个 Provider 的本周结构化事实、证据、解释素材、受请求维度限制的边界和资料缺口，再由宿主组织为自然中文总览、分段与提醒。它不是固定句式，也不能把订单、回款等环境记忆带入，因为成稿上下文不含这些资料。

“看一下这个八字”会先要求或使用 manifest 所声明的出生/四柱等资料；资料齐全则返回排盘事实、证据、解释素材和限制。核心不凭空生成用户的职业、婚史、资金等生活事实。

### 补资料

`prepare` 缺字段时返回 `Stopped.need_input + InputRequest + state_token`。Adapter 显示 `public_copy`、保存 token 和字段 schema。用户补充后，同一 token 调用 `prepare`，core 合并已保存 facts；没有 `publish-question`、没有 store path、没有旁路 resume。

### 续问、纠正、重起

- 续问：以 `Accepted` token 调 `prepare`，无 transition；同一 `reading_id`，版本加一，`brief.prior_answer` 可作为闭集上下文。
- 纠正：`transition="correct"`；同一 reading，版本加一，旧事实被明确替换，不按关键词重路由。
- 重起：`transition="restart"`；新 reading/version，保留 parent/root lineage，旧结果不覆盖。

### 起法、零证据和故障

- 用户明确要求某一起法时，宿主只能提交 manifest 声明且用户资料支持的方法。当前某 Provider 未声明时间起法，就返回 `Stopped.unsupported` 或 `need_input`；不得把“时间起”静默改为随机 `digital_coin`。
- 古籍零命中不是失败：有确定性事实则仍 `Prepared`，`limits` 标记 source gap；禁止虚构出处。
- 资料不足、体系不支持、并发冲突、空草稿、未知 token、内部故障分别得到对应的非空 `Stopped`。只要 Adapter/bootstrap 已启动，绝不输出空字符串。
- 进程未启动或 stdout 物理损坏属于宿主通用工具故障，不能为此恢复命理 Gateway guard。

## 7. 内部状态机、幂等、并发与崩溃恢复

```text
new ── prepare(缺资料) ──► pending_input
 │                              │ same token + facts
 │ prepare(资料齐)              ▼
 └──────────────────────────► prepared ── complete ──► accepted
                                                       │
                   ┌───────────────┬──────────────────┴──────────────┐
                   ▼               ▼                                 ▼
               continue        correct                            restart
             same id/v+1     same id/v+1                       new id/v1
```

- 有 token 的 `prepare` 与 `complete` 强幂等：同一 canonical 输入返回已存在状态；不同输入竞争时返回 `conflict`。
- `complete` first-commit-wins：首次非空 `public_copy` 原子落盘；重试返回同一 `Accepted`。不存在任何跨模块 digest 或交付 veto。
- 无 token 首问在传输中断时只保证不产生两个 `Accepted`；允许留下可回收的未提交 stage，避免新增 operation ledger。
- 使用既有 token log/index、reading 目录锁和不可变版本。`current` 是 commit point，索引/事件可重建；内部 SHA-256 仅发现损坏、状态错配或引用不一致。

## 8. 文件级保留／修改／删除清单

### 保留（不大改）

- `scripts/reading_engine/providers.py` 及其 13 个 Provider/算法入口；
- `references/books/**`、Provider 运行时真实需要的资料和证据索引；
- `scripts/reading_engine/state_token.py`、storage、lineage、原子写入机制；
- Hermes 的通用普通消息投递机制（与命理无关的部分）。

### 修改或新增

| 文件 | 改动 |
| --- | --- |
| `docs/plans/2026-07-30-mingli-v51-conversational-core-recovery.md` | 本文，取代 2026-07-29 计划中“plain brief 足够、全仓发布”的缺口。 |
| `scripts/reading_engine/interface_contracts.py` | 加 `InputRequest`，使 `Stopped` 可携带机器可读缺字段；保持 Complete 极简。 |
| `scripts/reading_engine/interface.py` | 从 manifest field view 构造最小 `InputRequest`；所有失败仍非空。 |
| `scripts/reading_engine/brief.py` / `provider_protocol.py` | 增加可选 Provider-owned `findings`，并将 request/scope/limits 编译为 caller_view；finding 只允许取公开 calculation projection。 |
| 受影响 Provider 的 manifest/局部实现 | 仅在本地声明可用起法、解释素材、精确支持事实、有效范围和 source gaps；先覆盖实际误用路径，不重写其余计算。 |
| `SKILL.md` | 唯一宿主说明：三 Command、四 Result、缓存、闭集、不得造事实；不列物理命令和领域词。 |
| `agents/openai.yaml` | 从源码删除。任何宿主私有 metadata 必须在宿主侧覆盖层维护，不能进入 portable core。 |
| `scripts/release_deploy.py` + release audit | 从 deny-list 改为可验证的 runtime closure allow-list；制品只发布运行需要文件和唯一宿主说明。 |
| `scripts/test_v51_conversation_contract.py` | 新增结构化补资料、token 连续性、非空失败与闭集成稿测试。 |
| `scripts/test_v51_release_surface.py` | 新增构建制品级测试，阻止旧协议再次进入安装包。 |

### 删除（仅从发行物/宿主可见面删除；历史源可保留）

- 源码中的 `agents/openai.yaml` 及其旧 Gateway/摘要/内部 ID 指令；
- 制品中的 `docs/**`、历史计划、`CHANGELOG.md`、`test-prompts.json`、测试、回归样本、旧运行手册与未被 runtime closure 引用的 scripts；
- 特别是旧 `references/tool-adapters.md`、`production-pipelines.md`、`fortune-cron-reminders.md`、旧 v2 transaction 名称和含 probe/gate/check 的宿主操作说明。

不删除 Provider 运行时真实读取的资源；由 release closure audit 证明，而不是靠人工猜目录。

## 9. 分阶段实施与可回滚提交

每一步都是独立、可测试、可 `git revert` 的小提交；直到所有验证通过前不部署、不改安装目录、不重启 Gateway。

1. **基线与契约回归（提交 A）**：记录 `a5c33e79` 为实施基线；新增会失败的 Interface 测试，固定 `need_input` 的结构化字段和 `complete` 的无二次 gate 语义。
2. **结构化补资料（提交 B）**：实现 `InputRequest`、JSON round trip、同 token 补资料和错误归一化；不变更 Provider 算法。
3. **闭集成稿视图（提交 C）**：在 brief 中加入 request/scope/limits/finding 的稳定投影；先让现有 Provider 的公开投影完全闭集化，任何 ambient context 不得进入。
4. **解释素材与起法收敛（提交 D）**：仅修改真实问题路径中的 Provider manifest/局部适配器：有数据则给 finding，无数据给明确 limit；每个 finding 可以声明精确公开事实，未声明则标记为共享本轮依据；将未声明的时间起法稳定返回 unsupported/need_input，禁止隐式随机替代。其余 Provider 不重写。
5. **宿主表面减法（提交 E）**：重写 `SKILL.md` 和 metadata 为唯一协议指令；移除旧手册在发行物中的可见性，不加入兼容命令。
6. **发行 closure（提交 F）**：实现白名单/真实依赖 closure、制品审计和 fresh-install 跨 Adapter 测试；确保古籍与 Provider resource 仍在制品中。
7. **全量回归与发布候选（提交 G）**：固定运行时运行完整 suite、Provider matrix、archive audit、跨宿主 JSON test；只生成可检查的 release candidate，不触碰生产安装。
8. **部署（单独授权后）**：由用户确认后才更新 Codex/Hermes Skill 安装位置、核对 manifest/hash；Gateway 保持运行且不修改。

### Profile 状态隔离切换规则（2026-07-30 补充）

- 默认状态根按安装实例隔离；宿主如显式提供状态基目录，核心仍附加安装实例命名空间，不能把两个 profile 合并到同一状态库。
- 旧的共享状态根不是 Skill 制品文件：切换后它不会被新实例读取，也不自动迁移或删除。先让旧 token 自然结束或单独归档，再按隐私保留策略清理；不得为了“清旧版本”把历史解读数据与旧代码混为一谈。

## 10. 测试、跨宿主测试与验收标准

### 新增/更新测试

- `Stopped.need_input` 含准确的 `InputRequest.fields`、非空 `public_copy` 和可恢复 token；同 token 补资料能完成而无需解析中文。
- 任意 malformed Command、unknown token、空 `public_copy`、unsupported capability、存储异常均返回一个合法、非空 `Stopped`。
- `Complete` 对同 token 重试返回同一 Accepted；它不要求摘要、span、claim 列表或 Gateway 数据。
- 任何 `Prepared.brief` 只由本次公开 provider projection 构成；塞入宿主环境记忆不会改变它。
- 起法声明测试：未声明 `time` 的 Provider 不能被静默替换为 `digital_coin`；声明 `time` 的 Provider 正常走其自身逻辑。
- release archive 测试：安装制品中只有一个宿主 instruction surface，旧 Gateway/guard/observer/reading-id/命令说明和测试文件均不存在；runtime import closure、Provider manifests 与必要证据资料仍完整。物化制品必须在 `-I` 隔离环境下经 JSON Adapter 完成 describe、补资料、普通 prepare 和择日 prepare，并经正式 runner 完成 describe，不能从源码 `PYTHONPATH` 回退。

### 跨宿主

- 同一 JSON Command 在进程内、JSON CLI、未来 MCP Adapter 得到同构 Result；Adapter 不得拥有 Provider 特例。
- Codex、Hermes、Claude Code 各只需保存 `manifest_digest` 和 `state_token`，不需要本地读取 reading store；token 只在签发它的安装实例/显式宿主状态根内有效，不能跨 profile 传递。
- Hermes 没有 Skill 调用时仍是普通消息；有 `Accepted` 时仍走普通发送路径。Gateway 源码对命理 import/路由的搜索为零。

### 最终验收

- 一份制品能直接给 Codex、Hermes 或任意 Adapter 使用；升级 Skill 不需要同步升级或重启 Gateway。
- Gateway 源码中无命理 import；core 返回 `Accepted` 后没有第二层命理拦截。
- “这周运势”“看这个八字”“补资料”“续问”“纠正”“重起”“零证据”“不支持起法”“内部故障”都有明确、非空路径。
- 所有 13 个既有 Provider、古籍和计算体系保留；变更只发生在 seam、公开投影、受影响 manifest 与发行面。

## 11. 风险、代价与明确不解决的内容

- **不能机械证明自然中文完全正确。** core 不调用模型也不做中文语义 gate；通过闭集 caller_view 和 Provider-owned finding 缩小错误面。高对抗审计只能是未来可选、事后、非阻断 Adapter。
- **宿主仍可能选错 capability。** `describe`/manifest 会让选择有数据可依，但工具选择质量仍属于宿主；不得把修复放回 Gateway 正则。
- **解释素材需要渐进补强。** 不应以“重写 13 Provider”为前置条件；先修真实误用路径，同时在 matrix 中量化 coverage。
- **发行 closure 需要严谨验证。** 过度裁剪可能漏掉古籍资料；因此先用构建测试和每个 Provider 的 prepare smoke test，再发布。
- **历史全文本资料缺失不在本次伪造。** 基线的 audit-only Liuren/Meihua/Liuyao fulltext 测试会因源树缺少 `references/fulltext/**` 失败；必须从可追溯原始归档恢复，再单独验收，不能把未知文本塞进运行制品或用假引用掩盖。
- **不解决多租户、跨机器一致性、监管级不可抵赖签名。** 这些若将来需要，做成可选 Adapter 的审计导出，不能成为默认 `Accepted` 的前置条件。

## 12. 最终 deletion test 与修正后的最终版本

### 删除后真正消失的复杂度

- Skill/Gateway 双版本 digest、摘要重建和交付 veto；
- Gateway 命理意图/续问正则、observer、guard、命理 Turn Ledger、命理失败文案；
- 终端命令次数、临时路径、chmod、旧 launcher 形状作为业务协议；
- 旧 `publish-question`/`probe`/`run` 分支和“成功却 0 字符”的后置条件；
- 宿主可浏览的数百份相互矛盾的旧说明。

### 必要复杂度回归核心的位置

- Provider manifest 的输入/能力/术语所有权；
- state token、reading lineage、版本、原子 stage/commit、并发和崩溃恢复；
- 确定性计算、证据适用性、source gap 和 caller_view；
- 机器可读补资料 schema；
- release closure 的完整性校验。

### 对上一版方案的关键修正

1. 不以 mandatory claim/span/digest 提交替代 Gateway guard；它会把“避免越界”错做成“阻止输出”。
2. `complete(token, public_copy)` 保持极简且无二次中文校验；质量改在 `Prepared` 的 Provider-owned 解释素材和闭集 caller_view 中解决。
3. `Stopped.need_input` 增加结构化 schema，消除宿主从文案猜字段的复杂度。
4. 发行包从“全仓可见”收敛为 runtime closure，消除宿主误读旧流程的根因。
5. 时间起法由 Provider manifest 明确声明；不支持就有非空 `Unsupported`，绝不静默换算法。

这就是最终推荐：更少 Interface、更少外部条件、更少可见旧流程；必要的状态和证据复杂度只在核心内存在。任何已启动调用都返回枚举 Result；需要停下时必定是可展示、可行动的非空 `Stopped`，而 `Accepted` 永远不再经过第二层业务拦截。
