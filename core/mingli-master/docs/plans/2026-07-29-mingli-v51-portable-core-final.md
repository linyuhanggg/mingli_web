# 命理大师 V5.1 可脱离 Hermes 独立运行：最终架构与迁移方案

状态：最终推荐，且主体代码已经按本方案落地。本文以当前运行代码为事实，取代历史计划里关于 Gateway 二次验签、跨体系复核账本、`Repair` 循环和旧事务入口的设计。

## 1. 一句话架构结论

把 `mingli-master` 收敛为一个拥有 Provider、证据、状态和提交语义的深模块，对所有宿主只暴露 `execute(Command) -> Result`；Hermes 退化为普通消息通道，模型只依据核心返回的闭集 `brief` 成稿，`Accepted.public_copy` 一经核心原子提交即为最终可展示结果，之后没有第二道命理拦截。

## 2. 当前架构问题图

历史架构把同一事务拆成了多个互相猜测的权威：

```text
用户消息
   │
   ▼
Hermes 命理意图/续问正则 ──► Gateway Turn/Delivery Ledger
   │                              │
   ▼                              ▼
Skill prepare/complete       Observer + Guard
   │                              │
   ├── Provider/证据/存储          ├── 重建摘要
   └── Accepted                  ├── 按另一版本重算 digest
                                  └── 再决定是否交付
                                         │
                         任一规则漂移 ────┴──► 0 字符或拒绝
```

这不是“校验不够”，而是权威重复：

- Skill 和 Gateway 分别解释意图、续问、结果与摘要，版本必然漂移。
- `accepted` 后仍可能被外部 guard 推翻，事务提交不再具有含义。
- observer 只能证明命令被执行，不能证明自然中文没有越出事实范围。
- Gateway 看不到完整的 requested dimensions、subject scope、certainty ceiling 和 source gap，只能用正则猜测语义。
- 核心已有确定性 Provider、证据绑定、lineage、原子存储，Gateway 的第二账本没有增加真相，只增加失败组合。

历史计划与当前代码的关键冲突如下，均以当前代码为准：

- 历史 `scripts/reading_engine/transaction.py` 已删除，事务编排权威是 `scripts/reading_engine/turns.py`。
- 历史 `scripts/reading_engine/answer_contract.py` 与 `Repair` 循环已删除；`complete` 只负责非空文本、token 状态和原子提交，不做自然语言二次验签。
- 历史 `scripts/reading_engine/capability_resolver.py` 已删除；能力由 `resources/runtime/providers/*.json` 声明，generic catalog 只做结构匹配。
- 历史 cross-check review ledger 已删除；多 Provider 只能作为同一次 prepare 的独立 artifact 组合，不能再建立第二套交付裁决。
- `scripts/reading_engine/fortune.py` 的旧能力权威已删除；实际计算继续复用既有 Provider/算法文件。

## 3. 推荐目标架构图

```text
Codex / Hermes Agent / Claude Code / 其他宿主模型
   │
   │ ① 首次加载或 manifest_digest 变化时 describe
   │ ② 把自然语言映射为 manifest 中的结构化 ID
   │ ③ 仅依据 Prepared.brief 写自然中文
   ▼
薄 Adapter：JSON CLI / 未来 MCP / 进程内调用
   │  只做 Command/Result 序列化；无命理规则、无验签、无摘要重建
   ▼
┌──────────────── mingli-master 深模块 ────────────────┐
│ ReadingInterface.execute(Command) -> Result          │
│   ├── Catalog：加载 Provider manifests 与公开术语     │
│   ├── Provider Registry：发现并绑定 13 个既有 Provider │
│   ├── Provider Adapter：输入映射、计算、证据与公开投影   │
│   ├── Brief Compiler：闭集 facts/evidence/scope/limits │
│   └── Turn Engine：token、lineage、stage、complete      │
│          ├── AtomicReadingStore                         │
│          └── StateTokenStore                            │
└───────────────────────────────────────────────────────┘
   │
   ▼
Accepted.public_copy ──► 宿主原样展示
```

Hermes Gateway 位于图外，只负责收消息、把 agent 最终文本发出去及通用投递恢复。Gateway 源码不 import 核心，也不识别命理、Provider、reading、digest 或 state token。

## 4. 各 Module 的职责和禁止职责

| Module | 必须负责 | 明确禁止 |
|---|---|---|
| `interface_contracts.py` | 三种 Command、四种 Result 及 JSON 可表达的公开值对象 | Provider import、领域术语表、宿主或模型厂商类型、文件路径 |
| `interface.py` | `execute`、结构化 capability 选择、结果归一化、所有失败非空 | 解析自然语言、Gateway 兼容、按回答正文重新验签 |
| `catalog.py` + Provider manifests | 能力、输入字段、结构 ID、展示名、claim policy、缓存摘要 | 关键词、别名、正则、会话判断；generic catalog 不得出现 Provider 名单常量 |
| `provider_registry.py` | 从 manifest entrypoint 发现 Adapter | 手写第二份 Provider 分发表 |
| `provider_protocol.py` | 一个深的 Provider seam：`descriptor + prepare` | 向外暴露算法文件、临时路径、shell 命令或内部摘要 |
| `providers.py` 与各算法模块 | 复用 13 个确定性 Provider，拥有本体系输入映射、计算、证据路由和隐私投影 | 把体系规则复制到 Gateway 或 generic interface |
| `brief.py` | 从 Provider 的公开投影生成唯一成稿闭集 | 读取私有 calculation、宿主记忆或全局领域常量 |
| `turns.py` | prepare/resume/continue/correct/restart/complete 编排 | 自然语言审稿、模型调用、投递决策 |
| `state_token.py` | 不透明 token、阶段、父子推进互斥、可重建索引 | 向宿主暴露 reading 路径、digest 或内部 ID |
| `storage.py` | 私有目录、不可变版本、原子 stage/commit、崩溃修复 | 成为宿主可查询 API、建立第二份业务账本 |
| `json_cli.py`、未来 MCP Adapter | 一次解码、一次调用、一次编码；传输错误归一化 | 路由规则、缺资料判断、续问判断、摘要验证 |
| 宿主模型 | 理解用户话语、从 `describe` 选择结构 ID、只依据 `brief` 写自然中文 | 读取 store、补造事实、把环境记忆混入闭集、提交后改写 `public_copy` |
| Hermes Gateway | 普通收发与通用投递可靠性 | 命理 import、observer、guard、命理正则、reading ledger、命理失败文案 |

“技能里不硬编码术语”的可执行定义是：`SKILL.md` 和 generic core 不维护任何体系清单、触发词、别名、正则或固定答案话术；公开领域词只存在于对应 Provider manifest/资源中，算法所必需的术语仍属于该 Provider 的私有实现。若把“任何术语”解释成算法和语料里也不能出现领域词，13 个 Provider 将无法存在，该解释不可执行。

## 5. 唯一外部 Interface 及完整输入/结果类型

唯一逻辑入口：

```text
execute(Command) -> Result
```

JSON CLI 只是该入口的一种 codec：stdin 读一个对象，stdout 写一个对象。`describe`、`prepare`、`complete` 是 payload 的 `kind`，不是 shell 子命令。

### Command

```text
Describe {
  kind: "describe"
}

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
  facts: {
    [subject_ref]: { [input_field_id]: JSON value }
  }
  state_token?: opaque string
  transition?: "correct" | "restart"
}

Complete {
  kind: "complete"
  state_token: opaque string
  public_copy: non-empty string
}
```

`facts` 只接受 manifest 声明的 `input_field_id`。未知字段不会成为计算事实；宿主原始对话、图片二进制、记忆片段、订单或回款上下文不得塞入 `facts`。

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
  brief: {
    question: string
    vocabulary: PublicTerm[]
    facts: PublicFact[]
    evidence: PublicEvidence[]
    claim_scopes: ClaimScope[]
    limits: PublicLimit[]
    prior_answer?: string
  }
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
}
```

为做减法，`NeedInput`、`Unsupported`、`Error` 不再是各自一套带分支协议，而统一为 `Stopped.reason`；`Repair` 被删除，因为它会重新制造“差一个条件就不交付”的循环。`Prepared.brief` 内的 policy 映射为：

- requested dimensions：`claim_scopes[].dimension_id`
- allowed subjects：`claim_scopes[].subject_ref`
- allowed domains：选中的 object/dimension 以及对应 scope
- specific-event policy：`allowed_kind_ids + certainty_ceiling_id`
- maximum certainty：`certainty_ceiling_id`
- supported claims：允许引用的 `fact_refs + evidence_refs`
- unresolved boundaries：`limits[]`
- source gaps：`limit.source_gap`

`describe` 不应每轮调用。宿主按 `protocol_version + manifest_digest` 缓存，安装、Skill 重载或 digest 变化时刷新；普通轮次直接使用缓存。`publish-question`、`probe` 和业务 `run` 全部退出生产 Interface。仓库仍可有名为 `run()` 的 codec 内部函数，但它不是外部 Command，也不承载业务语义。

## 6. 首问、补资料、续问、纠正、重起、零证据和故障流程

### 普通消息

Hermes 按普通 agent 消息运行；未调用 Skill 时不经过任何命理代码。Gateway 不做命理意图识别。

### 命理首问

1. 宿主模型依据缓存的 `describe` 把用户请求转成结构化 intent 和显式 facts。
2. 调用 `prepare`。
3. 得到 `Prepared` 时，模型只看 `brief` 写自然中文，再调用 `complete`。
4. 得到 `Accepted` 后原样展示。

例如“算一下这周运势”：宿主选择近时个人对象、周 horizon、用户要求的维度和对应 capability；若出生资料、时区、地点和参考时间齐全，`brief` 会含本周确定性层、可适用证据、倾向性上限及 source gap。最终回答是模型按这些事实自然组织的本周总览、分段变化、各请求维度与边界，不是核心内置模板。若资料缺失，用户得到类似“还需要：出生时间、时区……”的非空 `Stopped`，而不是空回复。

例如“看一下这个八字”：宿主选择 natal 对象，把用户明确给出的出生时间或四柱放入 manifest 字段。`Prepared.brief` 提供确定性排盘事实、适用出处、维度 scope 与倾向性上限；模型可以自然说明结构、关系和时间层，但不能从宿主记忆补入用户没提供的订单、婚史或资金事实。资料不足时明确追问；体系不支持时明确说明不支持。

### 补资料

首次 `prepare` 缺字段时返回 `Stopped(reason=need_input, state_token=...)`。宿主原样显示 `public_copy` 并保存 token。用户补资料后，用同一 token 再 `prepare`；核心合并之前已保存的结构化 facts，不要求宿主重建 store 路径或 intake ID。

### 续问

对 `Accepted` token 调用 `prepare`，不带 transition。核心继承已绑定 capability 和独立 lineage，沿用同一 `reading_id`，版本加一，并把上次公开回答作为 `brief.prior_answer`。宿主不能重新按关键词改路由。

### 纠正

对最新 `Accepted` token 调用 `prepare(transition="correct")`。纠正沿用同一 `reading_id`，版本加一，记录 `supersedes_version`，重新计算被纠正的事实；它不是新问题，也不保留已被撤回的旧事实。

### 重起

调用 `prepare(transition="restart")`。核心创建新的 `reading_id` 和版本 1，同时保留 `parent_reading_id/root_reading_id` 以说明谱系；旧 reading 不被覆盖。

### 古籍零命中

零证据不是事务失败。只要确定性事实可用，仍返回 `Prepared`，在 `brief.limits` 放入 source gap；模型可基于事实层回答并明确没有适用出处，禁止虚构引用。

### 资料不足、范围不支持、空草稿和内部故障

- 资料不足：`Stopped.need_input`，附 token，可继续补资料。
- 体系或维度不支持：`Stopped.unsupported`。
- 并发使用旧 token：`Stopped.conflict`。
- 空白 `public_copy`、未知 token、状态错配、存储异常：`Stopped.error`。
- malformed JSON 或 core import 失败：JSON Adapter 仍写一个合法、非空的 `Stopped.error`。
- 运行时缺失但 launcher 已启动：shell bootstrap 仍写一个非空 `Stopped.error`。

物理上“进程完全没有启动”或 stdout 本身损坏不可能由核心保证输出；这属于宿主的通用工具调用失败，不得为此在 Gateway 增加命理 guard。

## 7. 核心内部状态机、幂等、并发和崩溃恢复设计

```text
                 缺资料
new prepare ─────────────► pending_input
     │                         │ 同 token + 补充 facts
     │ 资料齐                  ▼
     └────────────────────► prepared
                               │ complete(non-empty)
                               ▼
                            accepted
                               │
             ┌─────────────────┼──────────────────┐
             ▼                 ▼                  ▼
          continue           correct            restart
        同 ID / v+1        同 ID / v+1         新 ID / v1
```

### 身份与连续性

- 新问：随机 32 位 `reading_id`，version 1。
- 补资料：未形成 accepted reading 前使用同一不透明 token 继续 intake。
- 续问：同一 `reading_id`，version +1，action=`continue`。
- 纠正：同一 `reading_id`，version +1，action=`correct`，绑定被替代版本。
- 重起：新 `reading_id`，version 1，action=`recast`，保留 parent/root。

### 幂等

- `describe`：进程内缓存；同一 manifest 恒定返回相同内容。
- pending token + 相同补资料：由 intake/token 状态恢复，不要求宿主知道内部 ID。
- prepared token + 相同请求：直接返回已 stage 的 preparation；不同请求返回 conflict。
- accepted parent token：父 token 加推进锁；相同 canonical turn 重放返回同一 child reading，不同 turn 只能有一个获胜。
- `complete`：first-commit-wins。同 token 重试返回第一次已提交的字节，即使进程在 commit 后、token 标记前崩溃也能从 committed record 恢复。

首问在尚未拿到 token 前发生物理传输中断时不承诺分布式 exactly-once；重复首问最多产生未提交的 orphan preparation，不会产生两个 Accepted。这里有意不增加 `operation_id`、外部幂等账本或 Gateway 协议，因为它会为极小的传输窗口重新引入一套前置条件。未来若宿主确有跨进程 exactly-once 要求，可在通用 Adapter 增加可选操作键，但不能进入命理规则或成为普通调用的必填条件。

### 并发

- reading 目录、intake 和 parent advance 分别使用文件锁。
- 同一 accepted parent 只允许一个不同的 child turn 落位；竞争者得到 conflict。
- version 必须严格为当前版本 +1；不可跳号或覆盖不可变历史。
- comparison Provider 保留独立 lineage，不能把同源 Provider 当作相互验证。

### 崩溃恢复

- state token 的 append-only log 是权威；按 token hash 的 index 是可重建派生物。
- store 先写不可变 prepared/version artifact，再原子替换 pending/current。
- `current.json` 是 commit point；events/public 副本缺失可从 current 修复。
- commit 成功但 pending 未清除时，重试通过 `prepared_digest` 找回已提交结果并清理派生残留。
- SHA-256 只用于核心内部的损坏、版本和引用一致性检查，不是 Skill 与 Gateway 之间的信任协议。

## 8. 按文件列出的“保留／修改／删除”清单

### 保留，不重写

- `scripts/reading_engine/providers.py` 中 13 个 Provider 的计算入口，以及其调用的既有算法模块。
- `references/books/**`、`references/matrices/**`、`references/fixtures/**` 中的古籍、规则表、来源依赖与回放样本。
- `scripts/reading_evidence_bundle.py`、`scripts/reading_source_plan.py`、`scripts/build_evidence_index.py` 的证据编译能力，但调用权归 Provider seam。
- `scripts/reading_engine/outcome_store.py` 作为核心内部可选校准记录；它不参与回答交付。
- Hermes 的通用 `gateway/delivery_ledger.py`：只记录任何普通最终消息的投递义务，不含命理特殊分支，也不是 reading/turn ledger。

### 已修改或新增，作为目标架构

- `SKILL.md`：只保留三命令、四结果、state token 和闭集成稿规则；不列体系术语或触发词。
- `resources/runtime/catalog-v1.json`
- `resources/runtime/providers/*.json`：唯一 capability/输入/公开术语/claim policy 数据权威。
- `resources/runtime/messages/zh-CN.json`：协议级非空失败文案和通用 policy 词汇。
- `scripts/reading_engine/interface_contracts.py`
- `scripts/reading_engine/interface.py`
- `scripts/reading_engine/catalog.py`
- `scripts/reading_engine/provider_protocol.py`
- `scripts/reading_engine/provider_registry.py`
- `scripts/reading_engine/brief.py`
- `scripts/reading_engine/turns.py`
- `scripts/reading_engine/state_token.py`
- `scripts/reading_engine/storage.py`
- `scripts/reading_engine/factory.py`
- `scripts/reading_engine/runtime_context.py`
- `scripts/adapters/json_cli.py`
- `scripts/reading_transaction.py`：仅保留为 JSON Adapter 门面。
- `scripts/runtime_launcher.py`、`scripts/run_reading_transaction.sh`：仅做固定运行时 bootstrap，不暴露业务子命令。
- `scripts/audit_v51_vocabulary_locality.py`：防止领域词重新进入 SKILL/generic core。
- `scripts/test_v51_portable_interface.py`、`test_v51_state_token.py`、`test_v51_closed_world_brief.py`、`test_v51_cross_host_contract.py` 等目标契约测试。

### 已从 Skill 制品删除

- `scripts/reading_engine/transaction.py`
- `scripts/reading_engine/answer_contract.py`
- `scripts/reading_engine/capability_resolver.py`
- `scripts/reading_engine/cross_check.py`
- `scripts/reading_engine/drafting.py`
- `scripts/reading_engine/routing.py`
- `scripts/reading_engine/legacy.py`
- `scripts/reading_engine/fortune.py`
- `scripts/reading_engine/ziwei.py`
- `scripts/gate_check.py`、`public_answer_*`、`reading_public_brief.py`、`reading_followup.py`
- `scripts/legacy_v3/**` 及对应旧测试。

### 已从 Hermes 删除

- `gateway/mingli_transaction_observer.py`
- `gateway/mingli_transaction_guard.py`
- `gateway/mingli_guard_runtime.py`
- `tests/gateway/test_mingli_transaction_guard.py`
- `tests/gateway/test_mingli_v4_tool_activation.py`
- `gateway/run.py` 和 `gateway/platforms/api_server.py` 中的命理分支。
- `tools/environments/local.py` 中的命理 profile 注入与摘要协议。
- `gateway/delivery_ledger.py` 中的命理失败文案识别和特殊丢弃规则。

## 9. 分阶段迁移计划，拆成可独立回滚的小提交

以下顺序已经在隔离分支执行；每步只依赖前一步，均可按逆序 `git revert`，不需要部署或重启 Gateway 才能验证。

1. **先定义端口**：用测试固定三 Command/四 Result 和非空 terminal result。
2. **数据化能力与术语**：引入 catalog/manifests，generic loader 禁止 keywords/aliases/synonyms/regex。
3. **建立深 Provider seam**：registry 从 entrypoint 发现 Provider，输入字段按 manifest 映射。
4. **建立唯一 Interface**：实现 `ReadingInterface.execute`，`describe` 可缓存。
5. **隐藏状态**：合并 intake/draft token 为一种不透明 `state_token`。
6. **闭集成稿**：`Prepared.brief` 只含公开 facts/evidence/scope/limits/vocabulary。
7. **收敛 complete**：删除 answer validator/Repair；complete 成为唯一原子提交方法。
8. **Adapter 变薄**：JSON CLI、旧文件名门面和 shell bootstrap 只做 codec/启动。
9. **删除旧 Skill 管线**：删除 capability resolver、cross-check ledger、legacy calculators、旧公共 brief/gates 及测试。
10. **修复 Provider locality**：能力只从 manifest 派生；Provider 专有可选输入也必须在对应 manifest 声明。
11. **稳定证据回放**：修复时间戳非确定性和来源 hash 链，重建 13 Provider 矩阵。
12. **Hermes 去命理化**：先删除 API 路径，再删除消息循环路径，再删除 observer/guard/tests，最后新增普通消息与 profile 隔离回归。
13. **最终文档与 release gates**：全量 Skill suite、Hermes suite、archive audit、零 import grep、跨宿主实跑；不部署。

关键已落地提交包括：

- `714d85b`：组合 portable reading transaction。
- `2017eda`：capability 从 manifests 派生。
- `232ca0e`：删除 cross-check review ledger。
- `9a49932`：删除退役计算/交付管线。
- `947ed05`：删除 legacy capability authority。
- `6057427`：稳定 Provider release evidence。
- `2b1beab`：对齐 manifest seam 与 portable contract。
- Hermes `e39a121ab7`、`6cbd0d997a`、`965bc8b4c8`、`0b7aab32a3`：依次删除 API、消息循环、领域模块并补普通投递回归。

## 10. Interface 层测试、跨宿主测试和验收标准

### Interface 层

- `describe` 不启动 engine，不访问 reading store，可缓存且 manifest 变化会改变 digest。
- 三种 Command 均能 JSON round-trip；未知 kind/malformed JSON 返回非空 `Stopped.error`。
- `Prepared.brief` 不暴露 reading 路径、私有 calculation、seed、digest 或 fact index。
- 零证据仍 `Prepared`，并有 source-gap limit。
- complete 空字符串失败且返回非空；Accepted 重放返回第一次文本。
- pending/prepared/accepted token 状态与 correction/restart lineage 全覆盖。

### 跨宿主

- 对同一 Command JSON，进程内 Python、JSON CLI、Codex/Hermes/Claude Code 的 Adapter 得到同构 Result。
- Adapter 测试只可比较序列化结果，不允许为某个宿主加入 Provider 特例。
- Hermes 普通消息在没有 Skill 调用时照常发送；Skill 的 `Accepted.public_copy` 走相同普通发送路径。
- Gateway 源码和测试中对命理标识的搜索为零，且 AST/import graph 中没有命理 import。

### 最终验收

- 同一份 `mingli-master` 制品可由多个宿主直接调用，无 Hermes 私有 import。
- Gateway 源码无命理 import；Skill 更新只改变 Skill 制品和 manifest digest。
- 核心返回 `Accepted` 后不存在第二层校验、摘要重建或交付拦截。
- 所有可达失败都产生合法、非空的 `Stopped.public_copy`。
- 13 个 Provider 权威矩阵、来源完整性、archive audit、术语 locality 和全量测试通过。
- 不启动/停止 Gateway，不访问生产端口，不安装依赖，不部署。

## 11. 风险、代价以及明确不解决的内容

- **自然语言语义不是机械可证明的**：核心不内置 LLM，也不做关键词审稿；closed-world brief 能缩小输入面，但不能数学保证模型绝不越界。重新增加 semantic gate 只会恢复双重权威。
- **首问物理重试不是分布式 exactly-once**：在 token 返回前的极窄崩溃窗口可能留下未提交 preparation；它不会生成 Accepted，也不值得引入 Gateway 幂等账本。
- **本地文件存储不是多租户数据库**：当前设计面向单机私有 Skill，依靠目录权限和文件锁；不解决跨机器共识、租户隔离或监管审计。
- **术语缓存需要失效**：宿主若错误地永久缓存 describe，会看不到新 manifest；正确缓存键必须包括 manifest digest。
- **旧宿主命令不兼容**：`publish-question/probe/run`、草稿路径、digest 参数和 store 路径不再接受。迁移目标是删除，不提供 Gateway 临时兼容层。
- **不重写算法**：13 个 Provider 的算法质量、古籍解释争议和语料版权边界继续由各 Provider 的既有审计处理。
- **不负责模型选择**：核心不知道 OpenAI、Anthropic 或其他厂商；模型能力、温度、上下文窗口属于宿主配置。
- **不把高对抗验签设为默认**：未来监管场景可用独立 Adapter 导出签名审计包，但它不能拦截默认 Accepted，也不能进入 Gateway。

## 12. 最终 deletion test

删除 observer 和外部验签后，真正消失的复杂度：

- Skill/Gateway 双版本 evidence digest 协议。
- Accepted 后再次验签和“成功却 0 字符”的状态。
- Gateway 命理意图正则、续问判定、摘要重建和命理失败文案。
- Observer 命令白名单、终端调用次数、shell 形状、临时路径和 chmod 规则。
- 两套 Turn/Review ledger 以及跨模块同步升级、同步部署、重启 Gateway 的要求。
- Gateway 为某个 Skill 版本维护的测试矩阵和兼容分支。

回到核心、且确有必要的复杂度：

- 输入 schema 与 Provider capability 的单一 manifest 权威。
- reading lineage、版本、pending/prepared/accepted 状态机。
- Provider 内部的确定性计算、证据适用性和公开隐私投影。
- 原子 stage/commit、并发冲突、崩溃修复和内部 SHA-256 完整性检查。
- `brief` 中的 subject/dimension/claim/certainty/source-gap 边界。
- 所有失败归一化为非空 Result。

删除完成的判据不是“代码换了名字”，而是 Gateway 在删除整个 Skill 后仍可独立完成普通消息收发，Skill 在删除整个 Gateway 源码后仍可通过 JSON CLI 或进程内 Interface 完成 describe → prepare → complete → accepted。

## 当前需求中仍存在的架构漏洞，以及修正后的最终版本

1. **“任何术语都不能硬编码”字面上不可实现。** Provider 算法和古籍语料必然包含领域术语。修正为：SKILL、generic core 和宿主 Adapter 不得硬编码领域术语；术语只由 Provider manifest/资源拥有。
2. **“任何失败都一定有输出”忽略了进程未启动和 stdout 损坏。** 修正为：只要 Adapter 或 bootstrap 进程已启动，所有业务/校验/运行时失败都返回非空 Result；启动与物理传输失败走宿主通用工具错误，不能为此恢复命理 Gateway guard。
3. **“删除验签”容易被误解成删除内部一致性。** 修正为：删除跨模块信任协议和交付 veto；保留核心内部版本、引用、lineage、prepared digest 和文件完整性检查。
4. **“防止语义越界”与“核心不调用模型、也不做语义 gate”之间存在能力缺口。** 修正为：核心输出闭集 brief，宿主隔离成稿上下文；不声称机械证明自然语言正确。高对抗语义审计只能是可选、事后、非拦截 Adapter。
5. **“Hermes 不理解命理”不等于 agent 不选择 Skill。** 修正为：Gateway 完全无业务路由；宿主模型根据 Skill 描述和缓存 describe 做选择。误触发/漏触发是 agent 工具选择质量问题，不得用 Gateway 正则补洞。
6. **“幂等 prepare”若要求首问 exactly-once，会迫使新增操作账本。** 修正为：所有有 token 的流程和 complete 强幂等；无 token 首问在传输中断时只保证没有重复 Accepted，不引入默认 operation ledger。
7. **“删除 Turn Ledger”不能误删通用投递可靠性。** 修正为：删除命理 reading/validation ledger；保留与内容无关的 Gateway delivery obligation ledger，因为它只解决任何消息的崩溃投递，与命理权威无关。

修正后的最终版本就是本文给出的三 Command、四 Result、单 state token、manifest-owned vocabulary、closed-world brief、core-only commit 和 zero-Mingli Gateway。它满足必要能力，同时把每轮成功所需的外部前置条件降到最少。
