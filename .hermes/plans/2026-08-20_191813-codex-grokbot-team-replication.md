# Codex Grok Bot 团队复刻实施计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
>
> **For Codex:** 主任务固定充当“项目经理”，通过项目级自定义 Agent 派单；本计划只定义配置和验收，不在本轮启动任何开发 Agent。

**Goal:** 在 `mingli_web` 内复刻现有 Grok Bot 的固定岗位、项目经理派单、执行制作收口、专业成员实施、测试与用户验收链路，并保留 Codex App 中可查看的独立 Agent 任务。

**Architecture:** 使用项目级 `.codex/agents/*.toml` 固化岗位身份，根目录 `AGENTS.md` 让 Codex 主任务承担项目经理职责，`execution_producer` 作为第二级进度统筹。所有专业 Agent 按任务临时启动，身份配置长期保留；成员完成后先给执行制作发三行以内结论，项目经理只依据执行制作的整批结论进行下一步派单。

**Tech Stack:** Codex CLI `0.147.0`、Codex Subagents、项目级 TOML Agent 配置、`AGENTS.md` 指令层级、Codex App Agent 任务视图、现有 `docs/CHECKLIST.md` / `DESIGN.md` / `CONTEXT.md` / Runtime 合同。

---

## 1. 已核实的现状

### 1.1 Grok Bot 的真实团队，不是按名称猜测

本机 Grok Bot 持久化数据中有 10 条 Agent 记录。与 `mingli_web` 直接相关的可见团队为：

1. 项目经理
2. 执行制作
3. 前端开发
4. 后端开发
5. 核心算法开发
6. UI设计师
7. 测试工程师
8. 用户测试
9. 小助理

另有一个隐藏 Bot“彼阁迪克”，其职责偏 GitHub/Figma 连接器建议，不属于这套研发流水线，本次不复刻。

Grok Bot 的各岗位会话中存在大量 `send-message` 事件，证明它们确实在互相派单和回报。真实回报链是：

```text
用户
  ↓
项目经理：定目标、拆任务、分配唯一负责人、拦越界
  ↓
专业成员：前端 / 后端 / 核心算法 / UI / 测试 / 用户测试
  ↓
执行制作：收成员结论、追落后、整批结束或真卡住时上报
  ↓
项目经理：决定验收、返工、下一刀或停止
```

### 1.2 Codex 能复刻的部分

OpenAI 官方文档确认：

- Codex 当前版本默认支持 Subagents。
- App 会显示每个 Subagent 的独立任务，可打开查看过程和结果。
- 主 Agent 可派发、追问、等待、停止和关闭 Subagent。
- 个人 Agent 放在 `~/.codex/agents/`；项目 Agent 放在 `.codex/agents/`。
- 每个 Agent TOML 至少包含 `name`、`description`、`developer_instructions`。
- `[agents].max_concurrent_threads_per_session` 控制主任务之外同时打开的 Agent 数量。

### 1.3 不能假装完全相同的部分

- Grok Bot 是长期存在的 Bot 会话；Codex 自定义 Agent 的“岗位定义”长期存在，但每次执行的 Agent 任务是按需启动的。
- Codex App 能显示 Agent 任务，但没有 Grok Bot 那种固定九人侧边栏和统一群聊时间线。
- Subagent 的最终结果仍会自动回到主任务，无法真正做到“成员只让执行制作看、项目经理完全看不到”。流程上可规定项目经理不据此派下一刀，必须等待执行制作的批次结论。
- 当前会话只有 4 个并发槽位（含主任务），所以可靠起步值是“项目经理 + 执行制作 + 两名专业成员”。九个岗位可以全部定义，但不能承诺九个同时运行。

## 2. 最终方案选择

采用“一个项目经理主任务 + 八个项目级自定义 Agent”的原生方案，不建立额外调度服务，不用数据库模拟群聊，也不把 Grok CLI 套在 Codex 外面。

初始并发设为 3 个 Subagent，加上主任务共 4 个活跃任务。任务按波次执行：

```text
波次 A：执行制作 + 1~2 个实施成员
波次 B：执行制作保持 + 测试工程师/用户测试
波次 C：项目经理收口，必要时把原成员重新唤醒返工
```

以后若 Codex 新会话实际提供更多槽位，再把 `max_concurrent_threads_per_session` 从 3 调高；岗位数量和并发数量不绑定。

## 3. 角色映射与权限

| Grok Bot | Codex 载体 | 模型/强度 | 默认权限 | 唯一职责 |
|---|---|---|---|---|
| 项目经理 | 主 Codex 任务 + 根 `AGENTS.md` | 当前主模型 | 随主任务 | 拆单、选择唯一 owner、派单、裁决、验收；不直接写代码 |
| 执行制作 | `execution_producer` | `gpt-5.6-luna` / low | read-only | 收口、追落后、上报阻塞；不查代码、不定优先级 |
| 前端开发 | `frontend_developer` | `gpt-5.6-sol` / medium | workspace-write | `web/**`、`admin/**`、`ui/**`，遵守嵌套 `AGENTS.md` |
| 后端开发 | `backend_developer` | `gpt-5.6-sol` / medium | workspace-write | `backend/**`、后端合同与服务层；不改算法内核 |
| 核心算法开发 | `core_algorithm_developer` | `gpt-5.6-sol` / high | workspace-write | `core/mingli-master/**` 与明确授权的算法接入文件；把独立 Git 工作树当源码权威 |
| UI设计师 | `ui_designer` | `gpt-5.6-terra` / medium | read-only | 对照 `DESIGN.md` 做视觉/交互审查和交接；不写代码 |
| 测试工程师 | `test_engineer` | `gpt-5.6-terra` / high | workspace-write | 写或运行测试、报缺陷、做回归；只改测试/证据文件，除非重新派单 |
| 用户测试 | `user_tester` | `gpt-5.6-luna` / medium | read-only | 真实浏览器旅程、可用性验收、截图证据；不写产品代码 |
| 小助理 | `project_assistant` | `gpt-5.6-luna` / low | read-only | 只做没有专业 owner 的小型查询、摘要和资料定位 |

模型名选择以本机已经存在并可用的 `gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna` 为准。原 Grok 配置中的“必须调用 `/Users/yuhanglin/.grok/bin/grok`”不迁移；那是 Grok Bot 节省自身额度的二级执行策略，在 Codex 中应直接用岗位自己的 Codex 模型。`ocx-gpt-*` 同样不引入，保持当前原生 Codex 路径。

## 4. 路由和交接协议

### 4.1 项目经理派单包

每次派单必须同时给出：

```text
目标：这一刀完成后用户能看到什么结果
Owner：唯一负责岗位
路径：允许读取和修改的目录/文件
禁止：不得触碰的产品合同、算法边界或其他人改动
验收：可执行命令或可观察行为
回报对象：execution_producer 的任务名
停止条件：完成、真实阻塞或需要项目经理裁决
```

缺少 Owner 或验收条件时不派单。跨前后端任务仍只有一个主 Owner；另一个岗位先做只读接口审查，等主 Owner 冻结合同后再接手。

### 4.2 成员回报

成员完成后先向执行制作发送最多三行：

```text
结果：DONE / BLOCKED / NEEDS_REVIEW
证据：改动文件或测试命令 + 结果
下一步：需要哪个岗位做什么；没有则写“无”
```

不回复“收到”，不群发，不自行开下一刀，不和其他成员闲聊。Codex 自动返回给主任务的 final 只作为原始证据；项目经理等待执行制作的整批结论后再行动。

### 4.3 执行制作回报

执行制作只维护三种结论：

- `BATCH_DONE`：本批所有 Owner 已完成，列出证据。
- `BLOCKED`：明确谁被什么阻塞、需要项目经理作什么决定。
- `WAITING`：仍有人工作，暂不催下一刀。

执行制作不得打开源码判断对错，不得修改仓库，不得改变优先级。一次只催一个真正落后的成员，整批结束或真实阻塞才回项目经理。

### 4.4 验收顺序

```text
实施成员完成
  → 测试工程师做技术验收
  → UI 变更再由 UI设计师只读复核
  → 用户可见流程再由用户测试走真实浏览器
  → 执行制作汇总
  → 项目经理决定 DONE 或退回原 Owner
```

测试失败必须退回原 Owner，测试工程师不顺手修产品代码。只有项目经理重新把缺陷派给测试工程师时，它才成为新 Owner。

## 5. 文件设计

### 5.1 创建 `.codex/config.toml`

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
interrupt_message = true
```

不修改 `~/.codex/config.toml`，避免影响其他项目。每个岗位自己声明模型和 reasoning，因此不设置全局 `default_subagent_model`。

### 5.2 创建根 `AGENTS.md`

根文件负责项目经理规则、路由表、单一写 Owner、回报链和脏工作树保护。必须明确：

- 主任务默认是项目经理，不直接实现专业代码。
- 非琐碎开发必须派给对应自定义 Agent。
- 任务可以并行，但同一文件集同一时刻只能有一个写 Owner。
- 现有用户/Grok Bot 未提交改动不得回滚、覆盖、重置或混入提交。
- `docs/CHECKLIST.md` 是范围/进度权威，`DESIGN.md` 是视觉权威，`CONTEXT.md` 是术语权威。
- `core/mingli-master` 是独立 Git 工作树；`.runtime/**` 是制品，不是算法源码编辑入口。
- 临时任务状态不写入 Nowledge Mem；已确认的长期决策才写入 `default` 空间，禁止回退 Hindsight。
- `web/AGENTS.md` 和 `admin/AGENTS.md` 保持不变并继续作为更具体的目录规则。

### 5.3 创建八个 Agent TOML

创建：

```text
.codex/agents/execution-producer.toml
.codex/agents/frontend-developer.toml
.codex/agents/backend-developer.toml
.codex/agents/core-algorithm-developer.toml
.codex/agents/ui-designer.toml
.codex/agents/test-engineer.toml
.codex/agents/user-tester.toml
.codex/agents/project-assistant.toml
```

命名字段使用英文稳定标识，`description` 同时写中文岗位名，便于项目经理准确选择。每个 TOML 都包含：

```toml
name = "<stable_agent_name>"
description = "<何时调用、中文岗位名、明确不负责什么>"
model = "<role model>"
model_reasoning_effort = "<low|medium|high>"
sandbox_mode = "<read-only|workspace-write>"
developer_instructions = """
<岗位边界、权威文档、允许路径、回报对象、停止条件>
"""
```

其中 `execution_producer` 的完整基线应为：

```toml
name = "execution_producer"
description = "执行制作：收取 mingli_web 各专业 Agent 的交付，追踪阻塞并向项目经理汇总；不检查或修改代码。"
model = "gpt-5.6-luna"
model_reasoning_effort = "low"
sandbox_mode = "read-only"
developer_instructions = """
你是 mingli_web 的执行制作，不是项目经理，也不是开发者。
只接收项目经理给出的批次名单和成员任务名；成员只向你报告结果。
你不打开源码判断实现，不运行测试，不修改仓库，不决定优先级，不派下一刀。
一次只追一个真正落后的成员；已交付成员不再催；不要发送“收到”。
只有整批完成或出现真实阻塞时才向项目经理报告一次。
报告必须是 BATCH_DONE、BLOCKED 或 WAITING，并附成员给出的原始证据。
"""
```

其余岗位必须把上述第 3 节的目录和职责原样写入 `developer_instructions`，并统一追加：保留他人改动、只处理派发任务、完成后先给 `execution_producer` 发三行以内结论、不得自行派新任务。

### 5.4 创建 `docs/CODEX_AGENT_TEAM.md`

该文档给用户操作，不放系统提示词细节，包含：

- 角色列表和职责。
- 在 Codex App 中启动一个“项目经理任务”的推荐提示词。
- 如何打开各 Agent 任务查看实时进度。
- 如何要求项目经理催办、暂停、返工或停止某个 Agent。
- 当前并发上限和波次规则。
- 一份前端问题、后端问题、跨域问题的派单例子。
- Grok Bot 与 Codex 的差异，尤其是“岗位持久、执行任务临时”。

推荐启动提示词：

```text
你是 mingli_web 项目经理。先读根 AGENTS.md、docs/CHECKLIST.md、CONTEXT.md；不要自己改代码。
按问题归属派给项目自定义 Agent，启动 execution_producer 收口。每个任务只设一个写 Owner，
成员完成后先回执行制作；你等待执行制作的批次结论，再决定测试、返工或下一刀。
本轮目标：<用户目标>。
```

## 6. 隐私与测试数据处理

Grok Bot 的“用户测试”描述里嵌入了真实姓名、出生时间和地区。不能把这些个人资料提交进项目级 `.codex/agents/user-tester.toml`。

Codex 版 `user_tester` 使用仓库已有的虚构 E2E 档案：`web/e2e/product-journeys.spec.ts` 中的 1990-05-06 08:30、江苏省常州市金坛区，或 `backend/tests/test_email_user_journey.py` 明确标注为 fictional 的测试档案。需要真实个人 dogfood 时，只能由用户在当前任务临时提供或引用本机受控数据，不写进 Agent 配置、Git、日志或长期记忆。

## 7. 实施任务

### Task 1: 冻结配置改动边界

**Objective:** 确保复刻配置不碰当前 Grok Bot 正在开发的大片未提交代码。

**Files:** 只读检查整个仓库。

**Steps:**

1. 运行 `git status --short` 和 `git diff --name-only`。
2. 运行 `git -C core/mingli-master status --short`，单独记录核心工作树状态。
3. 把允许新增范围冻结为 `AGENTS.md`、`.codex/**`、`docs/CODEX_AGENT_TEAM.md`。
4. 若这些目标文件在实施前已经存在或被他人修改，停止并先与用户确认；不得覆盖。

**Acceptance:** 原有脏文件列表前后完全不因本工作发生内容变化。

### Task 2: 建立项目级并发配置

**Objective:** 开启并限制项目 Subagents。

**Files:** Create `.codex/config.toml`。

**Steps:**

1. 写入第 5.1 节的 `[agents]` 配置。
2. 运行 `codex doctor --summary`。
3. 在仓库目录运行 `codex exec --strict-config --ephemeral --sandbox read-only "不要使用工具，只回复 CONFIG_OK"`。

**Acceptance:** 配置无 unknown key；一次只允许 3 个 Subagent 并发。

### Task 3: 固化项目经理协议

**Objective:** 让每个新的 Codex 主任务默认按项目经理方式工作。

**Files:** Create `AGENTS.md`；保留 `web/AGENTS.md`、`admin/AGENTS.md` 不变。

**Steps:**

1. 写入第 4、5.2 节规则。
2. 明确目录 owner 与跨域任务的单一主 Owner。
3. 明确执行制作收口和成员三行回报格式。
4. 明确不回滚现有脏改动、不自行提交、不自行发布。

**Acceptance:** 新建只读 Codex 任务询问“一个八字结果页接口字段错位交给谁”，它应选择一个主 Owner，并把另一岗位设为只读审查/后续接手，而不是让两人同时改同一合同。

### Task 4: 创建管理与辅助 Agent

**Objective:** 建立执行制作和小助理。

**Files:** Create `.codex/agents/execution-producer.toml`、`.codex/agents/project-assistant.toml`。

**Steps:**

1. 使用第 5.3 节完整基线写执行制作。
2. 小助理限定为只读、小型、无明确专业 owner 的查询和摘要。
3. 两者都禁止修改代码、派新任务和递归委派。

**Acceptance:** 执行制作收到“帮我修接口”时应拒绝接管实现，并要求项目经理把任务派给后端开发；小助理遇到前端实现应返回给项目经理路由。

### Task 5: 创建三个实施 Agent

**Objective:** 建立前端、后端、核心算法的明确写边界。

**Files:** Create `.codex/agents/frontend-developer.toml`、`.codex/agents/backend-developer.toml`、`.codex/agents/core-algorithm-developer.toml`。

**Steps:**

1. 前端 Agent 强制读取 `DESIGN.md`、`docs/CHECKLIST.md` 和命中目录的嵌套 `AGENTS.md`。
2. 后端 Agent 强制先核对现有 API/合同，不擅自改产品地图或 `mingli-master` 内核。
3. 核心算法 Agent 强制先运行 `make mingli-core-status`，只在 `core/mingli-master` 独立工作树改源码，不手改 `.runtime/**`。
4. 全部 Agent 只处理派发范围，不自行开下一刀，向执行制作回报三行结论。

**Acceptance:** 三个 Agent 对同一个示例任务能给出不同且正确的 owner 判断，不会跨目录抢活。

### Task 6: 创建审查与验收 Agent

**Objective:** 建立 UI、技术测试、用户测试三段验收。

**Files:** Create `.codex/agents/ui-designer.toml`、`.codex/agents/test-engineer.toml`、`.codex/agents/user-tester.toml`。

**Steps:**

1. UI设计师设为 read-only，只出具体界面问题和设计交接，不写实现。
2. 测试工程师允许写测试与证据文件，但不得顺手修产品实现。
3. 用户测试设为 read-only，必须使用真实浏览器和虚构测试档案；不得把 DOM 存在、正则或单测当成用户验收。
4. 三者都把结论发给执行制作。

**Acceptance:** UI设计师不产生代码 diff；测试工程师失败时指出原 Owner；用户测试生成真实步骤与截图路径且不包含真实个人资料。

### Task 7: 编写用户操作手册

**Objective:** 让用户无需记住工具名即可启动和监工。

**Files:** Create `docs/CODEX_AGENT_TEAM.md`。

**Steps:**

1. 写入角色和启动提示词。
2. 写入“查看、催办、暂停、返工、停止”的自然语言示例。
3. 写入并发波次和 Codex/Grok 差异。
4. 写入三个真实路由示例。

**Acceptance:** 用户只复制一段启动提示词，就能让新 Codex 任务按项目经理模式派单。

### Task 8: 做只读团队演练

**Objective:** 验证角色发现、通信和收口，不改任何产品文件。

**Files:** 无产品文件修改。

**Steps:**

1. 新开 Codex App 任务，使用第 5.4 节启动提示词，并明确“只读演练”。
2. 让项目经理同时启动 `execution_producer`、`frontend_developer`、`backend_developer`，正好占满当前 3 个 Subagent 槽位。
3. 给前端和后端各一个只读定位任务，要求结论先发给执行制作。
4. 检查 App 是否出现三个独立 Agent 任务、专业成员是否没有越界修改、执行制作是否只回一份批次总结。
5. 让项目经理停止一个 Agent、重新唤醒一个已完成 Agent，验证 steer/stop/follow-up。

**Acceptance:** `git status --short` 与演练前一致；项目经理最终输出只依据执行制作的 `BATCH_DONE` 或 `BLOCKED`。

### Task 9: 做一刀真实试运行

**Objective:** 用一个小而真实的问题验证实施—测试—收口链路。

**Files:** 由试点任务决定，但只能有一个写 Owner。

**Steps:**

1. 从 `docs/CHECKLIST.md` 选一条未完成且范围小的任务。
2. 项目经理派给唯一实施 Agent；另一个相关岗位只能只读审查。
3. 实施完成后由测试工程师跑聚焦测试。
4. 若用户可见，再由用户测试走一个浏览器旅程。
5. 执行制作汇总，项目经理决定完成或退回原 Owner。

**Acceptance:** 一条完整链路走通；没有双重 owner、没有擅自开下一刀、没有覆盖当前未提交改动。

## 8. 总体验收标准

- `.codex/config.toml` 能被 Codex `--strict-config` 接受。
- 八个自定义 Agent 都能被项目经理按名称选中。
- 主任务保持项目经理角色，不直接写专业代码。
- 执行制作不查代码、不跑测试、不决定优先级。
- 专业成员只处理各自路径，跨域任务只有一个写 Owner。
- 技术测试、UI 复核、用户测试按顺序执行，失败退回原 Owner。
- Codex App 能打开每个 Agent 任务查看实时过程。
- 当前并发稳定在 3 个 Subagent；超出的岗位排队，不丢任务。
- 用户真实资料不进入 `.codex/**`、Git、日志或长期记忆。
- 当前工作树里的既有改动全部保留，没有被复刻配置覆盖或顺手提交。

## 9. 风险与取舍

1. **并发不是岗位数。** 当前只能可靠运行 3 个 Subagent；先保证路由正确，再根据新会话实际容量调高。
2. **Codex 的 final 会回主任务。** 无法完全隐藏成员回报，只能在流程上要求项目经理等待执行制作收口。
3. **共享工作区仍需单一写 Owner。** 你的岗位设计没有职责冲突，但跨域合同和公共文件仍必须指定一个实际修改者。
4. **核心算法是独立 Git 工作树。** 核心 Agent 若同时修改父仓库接入层，项目经理必须把它拆成两个连续任务，不能一刀横跨两个 Git 历史。
5. **长期 Bot UI 不完全一致。** 若以后必须要九个永久侧边栏任务，可在 Codex App 另建并固定九个顶层任务；第一版不采用，因为跨任务自动收口和并发容量不如原生 Subagents 稳定。

## 10. 本轮不做

- 不修改任何 `.codex` 或 `AGENTS.md` 实际配置。
- 不启动 Subagent，不打断正在运行的 Grok Bot。
- 不修改当前大批未提交产品代码。
- 不把隐藏 Bot“彼阁迪克”并入研发团队。
- 不复制 Grok 配置中的真实个人资料。
- 不提交、不发布、不上传。

