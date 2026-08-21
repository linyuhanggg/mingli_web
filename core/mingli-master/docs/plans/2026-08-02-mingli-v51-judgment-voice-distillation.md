# 命理大师 V5.1 主断与人话表达蒸馏实施与验收记录

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 在不改变便携核心 Interface、不增加第二模型或生产 Gate 的前提下，用匿名、无术语的短小 drafting discipline 提升主断选择、普通中文表达和确定性校准。

**Architecture:** 离线材料只用于提取通用判断操作；运行时只在现有 `Prepared.brief → 同一宿主模型成稿 → complete` 之间应用短胶囊。Interface、Provider 算法、Adapter、Gateway 和 Accepted 交付不变；另修正 common Provider projection 将“缺反证”误报成“无支持出处”的既有语义错误。

**Tech Stack:** Markdown、Python 标准库、现有 JSONL replay、unittest；不增加模型 SDK、服务、依赖或运行进程。

---

## 0. 基线、脏树保护与运行时事实

### 施工基线

| 项目 | 值 |
| --- | --- |
| 基线 commit | `8e4fa505dc5a1d42ccfb0295b59ec2ba17598e4f` |
| 基线 worktree | `<codex-root>/2026-07-31/mingli-master-model-selection-fallback`（clean） |
| 施工 worktree | `<codex-root>/2026-08-02/mingli-master-judgment-voice` |
| 施工分支 | `claude/mingli-judgment-voice-20260802` |

`<codex-root>` 是本机 Codex 工作区根目录，不写入仓库：绝对路径属于
私有环境资料，仓库隐私测试禁止提交本机路径。

### 旧权威树保护

旧审计树 `<codex-root>/2026-06-16/skill/work/mingli-master-release-fix`
停在 `c8cf4ca`，带用户未提交资产（`SKILL.md`、
`references/v2-reading-transaction.md`、`scripts/reading_transaction.py`、
`scripts/test_v4_skill_minimalism.py` 的修改，以及三个未跟踪文件）。
本计划只读取它用于理解历史：不修改、不覆盖、不 reset、不 clean、
不 checkout、不格式化、不提交其中任何内容。本计划的任何提交都不吸
收该树的资产。

### 已核对的运行时基线缺陷（本计划不修复）

已安装的固定运行时（`MINGLI_PYTHON` 解析到的 venv 解释器）的
`runtime_python.validate_runtime_tree` 拒绝已安装 site-packages 中
未校验的字节码，当前该 venv 的 `yaml/__pycache__/*.pyc`
触发 `RuntimeError: unchecked runtime bytecode is forbidden`。因此
`scripts.test_v4_skill_minimalism` 的
`test_prepare_with_complete_facts_returns_prepared` 在基线
`8e4fa505` 与本分支同样失败（1 failure）。

这属于已安装运行时的环境状态，不是本次改动引入的代码缺陷。修复它
需要改写已安装目录，本计划明确禁止该操作，因此：

- 不安装依赖、不清理 venv、不重建 runtime；
- 不把该失败伪称通过；
- 在交付证据中标注基线对照，说明失败数量在改动前后一致。

## 1. 一句话架构结论

主断与人话表达是**成稿纪律**，不是新模块：核心继续只提供 `brief`，
宿主模型继续一次成稿，改动只是在 `SKILL.md` 的成稿章节加入一段匿
名、无术语、无模板的行为约束；表达质量在**离线盲审**中度量，永不
进入 `complete` 或 Gateway。

## 2. 离线研究与运行时隔离图

```text
┌──────────── 离线（不进运行时）────────────┐
│ 公共人物母本：只记录来源、定位、材料类型   │
│ 用户真实好坏回答对：只用于校准"说人话"     │
│        │                                   │
│        ▼ 提取通用判断操作（HOW，不是 WHAT） │
│ 匿名 drafting discipline（无人名/无原话）  │
└────────────────┬──────────────────────────┘
                 │ 一次性匿名行为提炼，不打包语料
                 ▼
        SKILL.md「成稿」章节的短胶囊
                 │
─────────────────┼──────── 运行时 ────────────────────
                 ▼
describe 缓存 → prepare → Prepared.brief
                 │
                 ▼ 同一个宿主模型，一次成稿（无第二模型）
              complete → Accepted.public_copy → 宿主原样展示

┌──────────── 离线（不阻断运行时）────────────┐
│ tests/replay/mingli-answer-cases.jsonl      │
│ scripts/run_model_replay.py（独立盲审 scorer）│
│ 生产文件不 import 它；它不能否决 complete    │
└─────────────────────────────────────────────┘
```

隔离不变量：

1. 运行时每轮不加载研究语料、不加载 few-shot、不加载评测文件。
2. 评测分数不写回 Provider、证据准入、路由契约或生产默认值。
3. 完整书籍、字幕、长转录不进入 active release archive。

## 3. Module 职责与禁止职责

| Module | 负责 | 禁止 |
| --- | --- | --- |
| Portable Core（`interface.py` / `turns.py` / `interface_contracts.py` / storage / token / lineage） | 计算、证据、claim scope、limits、lineage、状态、原子提交 | 理解或验证文风；读取表达评分；因文风拒绝提交 |
| `ReadingBrief`（`brief.py`） | 仍是本轮唯一成稿依据 | 新增人物、语气、模板、`voice_id`、`persona_id`、`style_id` 或 ambient memory 字段 |
| 主断表达胶囊（`SKILL.md`「成稿」） | 选择先说什么；把依据翻成现实含义；在边界内明确判断；集中说明限制；按用户问题控制详略 | 选术；修改事实；增加具体事件；修改 certainty ceiling；改变 claim scope；调用模型；返回评分 |
| 离线 Replay（`run_model_replay.py` + fixtures + `docs/model-evaluation.md`） | 独立盲审的数据结构与统计；明确区分人工与 Agent | 被任何生产文件 import；阻断 `complete` 或 `Accepted` |
| Host Adapter（`scripts/adapters/`） | 完全不变：JSON 转换、token 透传、`public_copy` 展示 | 任何命理判断、文风判断 |

核心 Interface 保持：

```text
execute(Describe | Prepare | Complete)
    -> Described | Prepared | Accepted | Stopped
```

不新增 Command、Result、Gate、Provider、模型、依赖或常驻进程。

## 4. 蒸馏对象、语料选择与诚实边界

### 4.1 为什么只选一个公共母本

第一版只用**梁湘润**作为公共母本，用途单一：研究"在多条互相牵制
的材料中，怎样先抓住一个主断"。他的教材系列长期以"实务判例 + 细
则心法"的形式出版，正面处理"同八字而命不同""身强身弱之争""怕算
不准"等**判断取舍**问题，这正是"主断优先"这一操作的可核对来源。

第一版不混入倪海厦、李居明、老子、张雪峰或其他人物：多母本会把
"抓主断"稀释成风格拼贴，且无法归因。

### 4.2 实际核对的一手来源

以下为本次可直接访问并核对的出版物元数据（出版社、ISBN、版次、
定位）：

| 来源 | 类型 | 定位 | 派生行为 |
| --- | --- | --- | --- |
| 《实务论命》（行卯出版社，教材系列，何重建序、郭伟辑补） | 出版书籍元数据与出版方简介 | 遗作教材，正面处理早晚子时、大运分管、同八字异命等争议，并给"怕算不准"的从业者建议 | 遇到材料互相牵制时，若公开材料足以分主次就说明主导方与改变条件；否则只下共同支持的有界结论，不猜私有裁决 |
| 《子平秘要》（行卯出版社，ISBN 9789869080972，1983 初版 / 2019 第 7 版） | 出版书籍元数据与出版方简介 | 面向已有基础的读者，比较四家取用神路径，"由同中求异，进而异中求同" | 先收敛到一个主结论，再用少量决定性材料解释；不把所有成立的分支并列 |
| 《八字实务精选》（行卯出版社，教材系列） | 出版书籍元数据与出版方简介 | 五年间精批实录的判例集 | 判断要落到具体处境与选择，而不是继续堆形容词 |
| 《子平母法大流年判例》（行卯出版社，教材系列，第 11 版） | 出版书籍元数据与出版方简介 | 修订全部原始判例，为"身强身弱"之争建立系统判准，力求吉凶更精确 | 在允许的确定性内作出明确判断，同时把失效条件说清；直接不等于绝对 |

### 4.3 明确不可访问 / 未取得的材料

- **未取得任何书籍正文、判例原文、课堂转录或字幕。** 上述四项只
  核对了出版元数据与出版方公开简介。
- 计划撰写期间 `WebSearch` 对相关中文查询持续返回 `API Error: 400`，
  无法用检索补充二手材料；提供的视频 URL 未返回任何标题、描述或
  转录，`xingmao.co` 的合集页返回 404。
- 因此**没有**进行逐句风格测量、没有统计句长/问句比/比喻密度，也
  没有做门派规则或术理的蒸馏。

### 4.4 诚实边界声明

> 本版本是由可核对材料与用户反馈提炼出的匿名行为规范，不声称模拟
> 或复现任何真人。

具体约束：

1. 最终产物不是"梁湘润人格"，而是匿名的 drafting discipline。
2. `SKILL.md`、生产 Python 和 Interface 中不出现任何人物名字。
3. 不复制人物原话、固定句式、古风、口头禅或身份卡。
4. 不蒸馏人物的门派规则、术理、选术逻辑或确定性等级。
5. 本文档不提交长引用、整段转录或完整书籍内容；只保留来源、定位、
   材料类型与派生行为四列。
6. 用户自己的真实好坏回答对只用于校准"什么叫说人话"；其原句不写
   入 Skill，也不作为固定答案。

### 4.5 从用户反馈提取的行为（不复制句子）

已知反馈只用于理解目标：

- 正确但像"脑子快、表达力强、容易想多"这类通用总结 → 用户反馈
  "说人话"。派生行为：**把专业依据翻成现实含义，而不是换同义形容词。**
- 更受认可的表达直接落到现实（指出真正问题是频繁换方向、做不深）。
  派生行为：**落到真实行为、处境或选择，同时不编造事件。**
- "指点太笼统太官方"的反馈；更受认可的表达会选一个主矛盾。派生
  行为：**先收敛到一个主结论，再解释。**

这些句子不写入 Skill，只提取行为。

## 5. 五类目标行为

| 编号 | 行为 | 运行时含义 | 明确不做 |
| --- | --- | --- | --- |
| B1 主断 | 内部先确定本轮最值得先说的结论：与当前问题最相关、支持最充分、最能解释其余材料，且不越过允许范围 | 先说结论，再用少量决定性材料解释 | 不按 `brief` 字段顺序复述；不为显得全面把所有成立内容并列 |
| B2 翻译 | 像当面交谈，把必要的专门表达落到可观察的行为、处境或选择 | 读者一次阅读能说出核心判断及现实取舍 | 不写成分析报告；不用另一串抽象名词替代解释；不扮演人物或模仿口头禅 |
| B3 直接性 | 在允许的确定性内作出明确判断 | 直接服从 claim scope 与 certainty ceiling；有条件的判断至少明说一次条件性 | 不用连续含糊词冲淡每句；也不放松 claim scope 换取"更直接" |
| B4 边界 | 把未知、牵制和失效条件集中说清 | brief 给出主次时说明主导方与改变条件；未给主次时只下双方共同支持的有界结论 | 不把限制撒进每句；连共同结论也不成立时，明说不能再硬断 |
| B5 续问 | 按用户问题控制详略 | 宽泛问题先给整体主线再展开；单点问题直接回答；续问先回答最新问题 | 不复述整份解读；不加入 `brief` 之外的人、事、领域或具体事件 |

## 6. 完整 SKILL 胶囊

以下文本加入 `SKILL.md` 现有「成稿」章节。允许为衔接现有段落做轻
微编辑，但不改变含义、不加例句、人物名字、术语列表或新 Interface。

```markdown
只依据 `brief` 成稿。先在内部选出本轮最值得说的判断：它应与当前问题
最相关、支持最充分、最能解释其余材料，并且不越过允许范围。

正文像当面把话讲清，不写成分析报告，也不解释自己的写作步骤。答案长短
由用户问题决定，不由 `brief` 的材料量决定；用户没有要完整报告，就不把
内容扩成资料清单或建议清单，同一结论只说一次。直接说出本轮判断，只保
留会改变主判断、成立条件或现实取舍的少量材料；其余即使成立也省略。将
必要的专门表达随即落到可观察的行为、处境或选择，不要用另一串抽象名词
代替解释；不扮演人物，不模仿口头禅，不写古风或固定套话。

直接不等于绝对：在允许的确定性内作出明确判断，把未知、牵制和失效条件
集中说清，不用连续含糊词冲淡每句话。如果允许范围只支持有条件的判断，
至少用一句话明说这种条件性，不把它写成无条件的“会”；一句即可，不要
句句重复。

宽泛问题先给整体主线，再按用户真正关心的范围展开；单点问题直接回答；
续问先回答最新问题，不复述整份解读。材料能收敛到同一判断时给主断；
相互牵制时只说它们共同能确定的部分；连共同部分也不成立时，清楚说明
不能再硬断。
不得加入 `brief` 之外的人、事、领域或具体事件。
```

胶囊约束：

- 不拆成新的外部 reference 并要求每轮加载。
- 不增加完整 few-shot。
- 不写人物名字、具体体系名、维度名、资料字段或古籍包。
- 不加入"我直说""贫道""师傅告诉你"等固定开头。
- 不加入输出标题、段落数量或句数模板。
- 不修改 frontmatter trigger。
- 不新增 Command、Result 或 token 规则。
- 不修改 `Accepted` 交付规则、选术与降级行为。

## 7. 文件清单

允许修改或新增：

| 文件 | 改动 |
| --- | --- |
| `docs/plans/2026-08-02-mingli-v51-judgment-voice-distillation.md` | 本文（新增） |
| `docs/model-evaluation.md` | 新 review 字段说明、v2 报告字段、只用于独立盲审的声明 |
| `scripts/run_model_replay.py` | 校验 6 个新 review 字段；输出 6 个新指标；`schema_version` 升 v2 |
| `scripts/test_v51_model_replay.py` | 新字段的 RED 测试、fixture coverage 断言 |
| `scripts/export_v51_answer_cases.py` | 用真实 `ReadingInterface.execute(Prepare)` 可重复导出 8 个行为正交 brief，并物化隔离 generation packets/Skill hashes |
| `tests/replay/mingli-answer-cases.jsonl` | 8 个由生产入口导出的 answer case，不再手写 brief、私有 artifacts 或重复维护 Provider 清单 |
| `scripts/reading_engine/providers.py` | 仅修正一处公开边界：有支持证据、只是没有反证时不再误报“无可引用出处” |
| `scripts/test_v51_provider_finding_contract.py` | 上述 source-gap 矛盾的 RED/GREEN 回归 |
| `SKILL.md` | 「成稿」章节加入主断表达胶囊 |

明确不修改：

- `scripts/reading_engine/interface_contracts.py`、`brief.py`、
  `interface.py`、`transaction.py`、`provider_protocol.py`、
  `provider_registry.py`；除上表单点公开 limit 修正外不改核心事务
- `resources/runtime/providers/`、`resources/runtime/catalog-v1.json`
- storage、`state_token`、lineage
- `scripts/adapters/`、13 个 Provider
- Hermes 源码或测试；三处已安装 Skill

## 8. 实际小提交

每个提交独立可 `git revert`，只 stage 明确文件；不使用 `git add -A`。

| 序号 | commit | 目的 |
| --- | --- | --- |
| 1 | `90b801d docs: define judgment-first drafting plan` | 冻结目标、减法边界与禁止项 |
| 2 | `c77741f test: extend human review for answer delivery` | 扩展离线评审字段与指标 |
| 3 | `eb79da3 test: add judgment voice replay coverage` | 增加第一版表达 case |
| 4 | `8b776c5 feat: add judgment-first natural drafting discipline` | 加入最小成稿纪律 |
| 5 | `7ff96ea docs: specify blind A/B packets and drop local paths` | 明确隔离协议并删除本机路径 |
| 6 | `164da82 test: bind answer fixtures to the real drafting boundary` | 将 fixture 绑定到 `ReadingBrief` |
| 7 | `d3cef3d fix: reject empty replay runs and document the A/B protocol` | 空运行 fail closed，补 A/B 协议 |
| 8 | `b593e46 test: align blind replay with production briefs` | 去除私有 artifact identity |
| 9 | `482bff4 fix: distinguish missing support from missing counterevidence` | 修正 source-gap 公开语义 |
| 10 | `6531492 test: export replay briefs through production seam` | 从真实 `execute(Prepare)` 导出 |
| 11 | `7a81b22 feat: refine conditional judgment drafting discipline` | 明确直接性不越过确定性上限 |
| 12 | `eccdfe3 feat: make drafting conversational and concrete` | 改为当面说话、落到处境与选择 |
| 13 | `789c666 feat: make answer length follow the question` | 长度跟随问题而非材料量 |
| 14 | `dfbda31 feat: resolve conflicting material without hidden priority` | 删除不存在的通用“主次字段”假设 |
| 15 | `b6f4e6c test: reduce answer replay to behavior seams` | 从 18 例减到 8 个正交行为 seam，并增加 packet materializer |
| 16 | `docs: record independent blind acceptance` | 写回冻结哈希、盲评结果与诚实边界 |

docs、evaluator、fixtures 与生产行为分别独立提交，保持独立回滚能力。

## 9. Replay 盲审 schema

### 9.1 保留字段

`direct_answer`、`evidence_relevant`、`naturalness`（1..5 口语自然
度）、`main_answer_claims_complete`、`claim_reviews`。

### 9.2 新增必填字段

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `main_point_clear` | boolean | 普通读者一次阅读后能否说出回答的核心判断 |
| `plain_language` | number 1..5 | 是否真正翻译成普通中文，而非术语换同义词 |
| `useful_specificity` | number 1..5 | 是否落到真实行为、处境或选择，又没有编造事件 |
| `certainty_calibrated` | boolean | 直接性是否服从 claim scope 与 certainty ceiling |
| `ambient_context_clean` | boolean | 是否没有把 brief 之外的宿主环境主题、事件或细节带入答案 |
| `template_smell` | boolean | 是否明显像固定报告、固定话术或人物模仿 |

`naturalness` 继续表示口语自然度，不新增重复的 `spoken_naturalness`。

### 9.3 review 行示例

```json
{"case_id":"answer-bazi-career","prediction_sha256":"...","reviewer":{"reviewer_id":"reviewer-anonymous-1","reviewer_kind":"independent_agent","independent":true,"blinded_run_label":"run-a"},"direct_answer":true,"evidence_relevant":true,"naturalness":4,"main_point_clear":true,"plain_language":4,"useful_specificity":4,"certainty_calibrated":true,"ambient_context_clean":true,"template_smell":false,"main_answer_claims_complete":true,"claim_reviews":[{"claim_index":0,"claim_text":"...","trace_indexes":[0],"unsupported":false}]}
```

### 9.4 新增报告指标

`main_point_clear_rate`、`plain_language_mean`、
`useful_specificity_mean`、`certainty_calibrated_rate`、
`ambient_memory_contamination_rate`、`template_smell_rate`。

报告 `schema_version` 升为 `mingli-model-replay-report-v2`。不增加
v1/v2 双路径兼容层：当前仓库没有已提交的正式 review artifact 需要
兼容。

### 9.5 fail-closed 规则

缺任一新增字段、boolean 传字符串、评分越界（< 1 或 > 5）、review
内嵌进 prediction row、digest 过期、盲标签不一致，一律失败，不降级
为低分。空 case/prediction 集合同样是协议错误而非满分。`brief_sha256`
不一致、reference violation、unsupported claim 与 blind binding 继续
fail closed。usage 是可选遥测：有值就必须完整可信；宿主拿不到时报告
coverage 0 与 `null` 均值，禁止伪造 0。

`unsupported` 不要求答案逐字复述 `brief`：在公开 claim scope 内，由
所引事实或证据合理支撑、并服从确定性上限的普通中文翻译仍是 supported。
只有没有合理公开依据、与 brief 冲突，或加入未授权领域、具体事件、日期、
金额和保证时才标为 unsupported。评审按完整意思簇枚举，不按每个从句
机械拆分；这一判准必须在评审冻结前给出，但不得把发布门槛告诉评审。

### 9.6 fixture coverage

`tests/replay/mingli-answer-cases.jsonl` 固定为 8 个行为正交 case，而不是
第二份 Provider 清单：

- 分别覆盖说人话的单点主断、required cross-system 的两个独立 scope、
  `one_sentence`、`zero_evidence`、真实续问、真实纠正和
  `horizon_boundary`；
- 周运宽问同时承载 `broad_overview` 与 `ambient_context_noise`，以一例
  覆盖“材料多但正文要收敛”和“宿主记忆不能污染”两个相关风险；
- 13 个 Provider 的计算正确性与准入完整性继续由已有 Provider/catalog
  合约测试负责，表达评测不再硬编码或重复维护这份权威清单；
- ambient context 对抗样本出现与当前解读无关的订单、回款、项目或对账
  背景，rubric 禁止把它写进答案；
- 全部使用合成输入：可以保留生产实际会公开的合成出生／事件／资产元
  数据，但没有真实用户记录、姓名、附件路径、凭据、token 或生产
  `reading_id`；
- 不写固定 expected public prose；每个 case 只定义用户问题、固定
  `brief`、必须回答的意义、禁止越界的内容；
- 不引用或模仿任何公共人物原话。

### 9.7 每个 case 必须携带真实 `brief`

盲审要判断 `certainty_calibrated`，就必须看到生产成稿真正依赖的边界。
因此每个 answer case 携带真实 `brief` 与 canonical `brief_sha256`，且
必须能经 `ReadingBrief.from_dict()` 校验并 `to_dict()` 往返一致：

- `claim_scopes` 含 `certainty_ceiling_id`（`certainty.tendency`）与
  `allowed_kind_ids`（`kind.fact` / `kind.tendency`）；
- `limits` 只使用生产可达的真实语义：仅 `brief.evidence` 为空时公开
  `limit.source_gap`；内部没有反证不再伪装成“无可引用出处”；
- `request_view` 使用真实 manifest 的 object / dimension / horizon id；
- 续问 case 携带非空 `prior_answer`；纠正与生产一致，不公开旧答案，
  只检查是否按更正后的事实重新作答；
- claim scope 只能授权 `request_view` 实际请求的维度；生产不可达的
  partial-scope case 已删除，Unsupported 继续由 Interface 合约测试覆盖；
- `brief.evidence` 只投影支持证据；不把私有 counter-evidence 交给成稿方
  或评审方制造不可完成的隐藏要求；
- 成稿 trace 只使用 `brief` 发布的 public ref；任何私有或不存在的 ref
  都是协议违规；
- `ambient_context` 条目绝不出现在 `brief` 内。

四类不完整 case 的修正：

| Case | 问题 | 修正 |
| --- | --- | --- |
| weekly | 手写“前段／后段”不是 Provider 输出 | 真实执行周运，保留 7 日、7 个默认 scope 与完整起止范围；胶囊负责收敛主线 |
| continuation | 只有 tag，无前文 | 真实执行 `Prepare → Complete → Prepare`，由核心产生 `prior_answer` |
| correction | 人工写入旧结论 | 真实执行 `transition=correct`，按生产规则保持 `prior_answer=null` |
| cross-system | 手工合并 scope 并预设主次／冲突 | 真实执行 required comparison，保留两个独立 scope；rubric 不要求猜私有裁决 |

## 10. 验收标准

### 10.1 本地确定性验收（本计划范围内）

- 聚焦测试全部 PASS：`scripts.test_v51_model_replay`、
  `scripts.test_v51_provider_finding_contract`、
  `scripts.test_v4_skill_minimalism`、`scripts.test_skill_metadata`、
  `scripts.test_v51_portable_interface`、
  `scripts.test_v51_cross_host_contract`、
  `scripts.test_v51_active_artifact_minimalism`
  （§0 记录的运行时基线失败按基线对照说明，不计为本次回归）。
- 使用可用的固定运行时执行 `scripts/export_v51_answer_cases.py --check`，
  必须报告 8 个 production-exported case 全部最新；
- `scripts/audit_v51_vocabulary_locality.py --check` 的 JSON `ok: true`。
- `scripts/audit_release_archive.py --source .` exit code 0。
- `git diff --check` 无输出。
- `SKILL.md` 仍只有三种 Command、四种 Result；不出现具体 Provider
  名称、人物名字、模型厂商、路径、Gateway 或命令形状。

### 10.2 离线表达质量门槛（Codex 独立执行）

硬性：

| 指标 | 门槛 |
| --- | --- |
| `brief_invariance_rate` | = 1.0 |
| `reference_violation_rate` | = 0 |
| `unsupported_claim_rate` | = 0 |
| `untraced_claim_rate` | = 0 |
| `evidence_relevance_rate` | = 1.0 |
| `direct_answer_rate` | = 1.0 |
| ambient memory contamination | = 0 |
| `Accepted` 交付 | 仍原样交付 |
| 所有 terminal Result | 非空 |

表达：

| 指标 | 门槛 |
| --- | --- |
| `main_point_clear_rate` | ≥ 0.90 |
| `plain_language_mean` | ≥ 4.0 |
| `useful_specificity_mean` | ≥ 4.0 |
| `naturalness_mean` | ≥ 4.0 |
| `certainty_calibrated_rate` | ≥ 0.95 |
| `template_smell_rate` | ≤ 0.10 |

以上门槛只用于离线 release evidence，**绝不进入生产 `complete` 或
Gateway**。

## 11. 独立语义盲验（生成方不自证）

```text
quality_blind_review_pending_codex = false
quality_blind_review_status = passed_independent_agent
```

同一执行者不得既生成某条答案又评审该条答案。评审必须显式声明
`reviewer_kind=human|independent_agent`；Agent 评审不得在报告中冒充人工
盲审。独立性字段只是程序性声明，不是身份认证。

### 11.1 三个 packet（关键隔离）

仓库内 scorer 只给 prediction/review JSONL 打分，不调用或选择模型；
fixture exporter 只负责从生产入口冻结 `brief`。外部生成方每个 case
构造三个 packet；这个切分本身就是盲验的有效性来源——**成稿模型绝不
能看到自己将被如何评分**。

| Packet | 交给谁 | 内容 | 绝不包含 |
| --- | --- | --- | --- |
| Generation packet | 成稿模型 | canonical JSON 的 `brief` + 对应 arm 的完整 `SKILL.md`；输出固定为 `main_answer` + `claim_traces` | `review_rubric`、`coverage_tags`、带标签的 `ambient_context`、其他 case 的 brief、本文任何门槛 |
| Ambient 注入 | 宿主环境（不进 brief） | 按列表顺序把每个字符串作为更早的 `user` 消息逐字注入；两 arm 完全相同 | 不标成噪声，不写入 `brief` |
| Review packet | 只给评审（predictions 冻结之后） | 冻结的 `brief`、有序 `ambient_context`、prediction 行、case 的 `review_rubric` | Skill 版本和 arm 对应关系 |

`brief` 是真实 `ReadingBrief` payload：`question`、`vocabulary`、
`facts`、`evidence`、`findings`、`claim_scopes`（含
`certainty_ceiling_id` 与 `allowed_kind_ids`）、`limits`、
`prior_answer`、`request_view`，与生产 `Prepared.brief` 同构。

`review_rubric` 是评审专用：若成稿侧看过 rubric，该轮作废。

不能把成稿方指向完整 answer-case JSONL，再只靠提示词要求它忽略其他
字段。生成前必须为每个 case 物化一份只含 `case_id`、`brief_sha256`、
`brief` 三个键的只读 packet；单次成稿任务只把一个 packet 与一个冻结的
Skill snapshot 作为具名输入，并禁止其他读取。任务只要直接指向含 rubric、
tags 或其他 case 的文件，本轮即作废。两个 Skill snapshot 在首轮前统一
冻结并记录 SHA-256；禁止逐 case 重读可能变化的工作树。若评测宿主无法
提供 OS 级文件系统隔离，必须把这项限制记为程序性隔离，不能声称输入面
经过密码学强制。

### 11.2 冻结与匿名化

predictions 写入不含 arm 身份的 stem（`run-a.jsonl`，不是
`candidate-skill.jsonl`），再对每行计算 `prediction_sha256`。评审不
得知道哪个 stem 是基线、哪个是候选，也不得看到 Skill 版本或 commit。
predictions 一经哈希即不可变：任何编辑都会破坏绑定并被 scorer 拒绝。

### 11.3 A/B 执行

两侧使用同一 fixture 版本、同一宿主设置、同一重试策略、同一 rubric；
**只有 `SKILL.md` 的成稿指令不同**。基线 Skill commit `8e4fa505`，
候选 Skill commit 见交接。各生成一个 prediction 文件与一个 review
文件，然后一次性打分以便并列对照：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -B \
  scripts/run_model_replay.py \
  --kind answer \
  --cases tests/replay/mingli-answer-cases.jsonl \
  --predictions /path/to/run-a.jsonl /path/to/run-b.jsonl \
  --reviews /path/to/review-a.jsonl /path/to/review-b.jsonl
```

prediction 与 review 按位置配对：`review-a.jsonl` 必须评审
`run-a.jsonl`，且其行内 `reviewer.blinded_run_label` 必须等于
**prediction 文件的 stem**（如 `run-a`）。review 文件自身的文件名不
受约束。arm 与 stem 的对应关系只在打分之后揭盲。

### 11.4 2026-08-02 正式盲验结果

本轮冻结 8 个真实生产 `ReadingBrief`，两个 arm 各生成 8 条答案；每个
case 由未参与该 case 生成的独立 Agent 在不知道 Skill 版本和映射的条件
下评审。打分成功后才揭盲：`run-cedar` 是基线 `8e4fa505`，
`run-river` 是本分支候选。

| 指标 | 基线 `run-cedar` | 候选 `run-river` | 候选门槛 |
| --- | ---: | ---: | ---: |
| brief invariance | 1.000 | 1.000 | 1.000 |
| reference violation | 0.000 | 0.000 | 0.000 |
| unsupported claim | 0.000 | 0.000 | 0.000 |
| untraced claim | 0.000 | 0.000 | 0.000 |
| evidence relevance | 1.000 | 1.000 | 1.000 |
| direct answer | 1.000 | 1.000 | 1.000 |
| naturalness | 4.500 | **4.875** | ≥ 4.000 |
| main point clear | 1.000 | 1.000 | ≥ 0.900 |
| plain language | 4.125 | **4.500** | ≥ 4.000 |
| useful specificity | **4.750** | 4.375 | ≥ 4.000 |
| certainty calibrated | 1.000 | 1.000 | ≥ 0.950 |
| ambient contamination | 0.000 | 0.000 | 0.000 |
| template smell | 0.125 | **0.000** | ≤ 0.100 |

候选全部达到 §10.2 门槛；基线在 `template_smell_rate` 上未达门槛。
候选不是所有单项都高于基线：`useful_specificity` 低 0.375，但仍高于
发布目标；这说明结果不是把候选机械评成全胜。候选被枚举的实质主张为
69 条，基线为 95 条，和“材料不等于正文长度”的减法方向一致，但该计数
受评审粒度影响，只作旁证。

| 冻结 artifact | SHA-256 |
| --- | --- |
| generation manifest | `c67ac9bc8ed5929888d8627089486af4e503ffa431b811bd235f3fba4218d811` |
| baseline Skill | `4c077ef9872dc02c8e846dda1a8206e0cdb57591642a730efa4ff822656138f6` |
| candidate Skill | `750bae12f39019556b86de53afff3e8493c2921e528f1a150aeec02d1edc37da` |
| `run-cedar.jsonl` | `0c0799f573a8918a391a842ae07302720313e35e34c5d11b8f599742f0122ba0` |
| `run-river.jsonl` | `067428a7ea5ccd077e5c0360ea65ab45b7cca625d4d4aa51a235c72fc0deff80` |
| review packet manifest | `562c5ee5a0869824f6d26936f431b1f903962771d60daf69c420705d251f092b` |
| baseline reviews | `50ad99ea91fe13df1920c7df86fb0790a802bf4817402e4aceff8223fad9cf32` |
| candidate reviews | `9698c315fce4a0c365c8ccff8e40de399909d41479b53a4877d3e2a5ec895952` |
| scorer report | `3aa91cb3eddd83dbf938d40873921a7c39e91cee1576a04698049116e6b350fb` |

诚实边界：评审者是 `independent_agent`，不是人类；宿主是 Codex
subagent，不能取得精确底层模型版本或 token/费用遥测，因此 usage
coverage 为 0，均值为 `null`。文件读取隔离是程序性约束，不是 OS 级
密码学隔离。一次 generation worker 在读取输入前中止并由全新 worker
替换，没有产生候选答案；weekly 的第一份 review 因 `unsupported` 判准
未定义而作废，补写上述定义后由全新盲审者重评。语义评审的分数和 claim
enumeration 未改；其中 8 行 reviewer 元数据曾使用简写键，协调器只按
已冻结 prediction hash 机械规范化为 scorer schema，未改评分。


## 12. 风险与明确不解决的内容

| 风险 | 处理 |
| --- | --- |
| 胶囊可能被模型读成"要更绝对" | B3 明确"直接不等于绝对"，并由 `certainty_calibrated_rate` 在离线度量；不放松 claim scope |
| 表达质量无法机械证明 | 只做离线独立盲审并标明评审类型；不加关键词、正则或词频检测；不建生产评分器 |
| 蒸馏保真度无法验证 | 明确不声称模拟真人；只保留可核对元数据派生的通用操作 |
| 未取得一手正文 | §4.3 如实记录；不编造样本数量，不声称高保真人物蒸馏 |
| 宿主仍可能选错 capability | 不在本计划范围；不把修复放回关键词路由 |

明确不解决：

- 不做人物身份模仿、口头禅、身份卡或时间线。
- 不做多母本混合、门派规则蒸馏或术理蒸馏。
- 不做 `Accepted` 后置检查、Gateway 自然语言检查。
- 不解决固定运行时 venv 字节码校验缺陷（§0）。
- 不做多租户、跨机器一致性或监管级签名。

## 13. Deletion test

| 删除对象 | 结果 |
| --- | --- |
| 删除 `SKILL.md` 的胶囊段落 | 核心、Provider、Adapter、Gateway 与全部聚焦测试行为不变；仅表达纪律消失，运行链仍完整 |
| 删除 `scripts/run_model_replay.py` 与 fixtures | 生产运行完全不受影响：没有生产文件 import 它；`prepare`/`complete`/`Accepted` 行为不变 |
| 删除本计划文档 | 运行时零影响 |
| 删除整个 Portable Core | 宿主失去命理权威，但 Gateway 仍能发送普通消息 |

反向证明：本次改动**没有**在生产路径上增加任何新的必过条件——胶囊
是 Markdown 指令，evaluator 是离线脚本，两者都可删除而不产生空回复
或新的失败组合。

## 14. 交接约定

完成后不部署、不 push、不重启任何服务、不触碰 8642/8645、不安装依
赖、不修改任何已安装 Skill 目录。只有在 §11 的独立盲验冻结并达到
§10.2 门槛后，才能声明“本地独立 Agent 验收通过”；该表述不等于人工
偏好验证或生产发布完成。

## 15. 本地确定性验收记录

- 固定运行时下候选聚焦套件：`Ran 85 tests`，84 PASS，1 项为基线已有
  的已安装运行时字节码失败；同环境基线 `Ran 57 tests`，也是同一项
  failure，因此新增 28 项聚焦测试全部通过。
- `scripts.test_v51_provider_finding_contract`：3 PASS。
- production exporter `--check`：8 个 case 全部最新。
- vocabulary locality：`ok: true`，findings 为空；`SKILL.md` 新增胶囊
  不含具体体系名、人物名、厂商名、Gateway 或路径。
- release archive：`ok: true`，212 files；`git diff --check` 无输出。
- repository privacy：候选与基线都是同两条早期文档路径 finding，本分支
  新增 0 条。

全套测试曾在最终冻结前执行：候选 1314 项、基线 1286 项；两侧都被
缺失的外部古籍全文／来源校验和既有运行时环境问题主导。候选那次运行与
最后的 fixture 减法编辑重叠，故只作为广覆盖旁证，不把它伪称最终零回归
证明；本次改动的最终结论以前述精确聚焦对照为准。
