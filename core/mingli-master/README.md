<div align="center">

# 命理大师 · Mingli Master

### 面向 AI Agent 的确定性命理计算、古籍证据与连续解读引擎

![版本](https://img.shields.io/badge/版本-V5.1-7c3aed)
![体系](https://img.shields.io/badge/体系-13%2F13-0f766e)
![测试](https://img.shields.io/badge/测试-1584%20通过-2563eb)
![仓库](https://img.shields.io/badge/仓库-Private-374151)

不是固定话术库，也不是关键词触发器。它把排盘计算、古籍证据、上下文延续和公开回答校验收拢为一条可审计事务链。

</div>

---

## 项目简介

命理大师是一套供 Codex、Hermes 等 AI Agent 使用的私有 Skill。它负责生成确定性命理事实、匹配有出处的古籍证据、维持多轮解读的谱系关系，并在回答发布前验证事实与证据引用。

模型负责理解用户意图和组织自然语言；事务引擎负责请求结构、计算结果、证据身份、版本谱系和原子持久化。两者边界清晰，使回答既保持自然，也能追溯“依据什么盘、哪条事实、哪份证据”。

## 当前状态

| 项目 | 状态 |
| --- | --- |
| 当前版本 | V5.1 Provider Contract Hardened Core |
| 运行路线 | 13/13 ready |
| 古籍参考包 | 55 个 ready packs |
| 自动化测试 | 1584 tests / 0 failed / one zero-exit run |
| 生产入口 | `scripts/adapters/json_cli.py`（或 `scripts/run_reading_transaction.sh` 引导） |
| 部署目标 | Mac mini 的 Codex、Agents、Hermes 默认与 liujing profile，以及 MacBook Codex |
| 外部质量验收 | 等待 host-model predictions 与独立盲审，不以自动门禁替代 |

> 自动技术候选已经通过，但经验预测准确率仍属于实验性指标。系统不会把自动化测试包装成真实世界预测有效性的证明。

## 支持体系

| 类别 | 路线 | 能力形态 |
| --- | --- | --- |
| 命理 | 八字 | 确定性排盘与事实层 |
| 运势 | 日运 / 近时运势 | 参考周期绑定与确定性事实 |
| 星命 | 紫微斗数 | 固定版本星盘事实 |
| 古法 | 早期禄命 / 纳音 | 专用计算与来源约束 |
| 星命 | 七政四余 | 星历计算与古籍证据 |
| 占筮 | 六爻 | 起卦、纳甲与断验事实 |
| 占筮 | 梅花易数 | 起卦与体用事实 |
| 三式 | 大六壬 | 确定性起课与审计 |
| 三式 | 奇门遁甲 | 盘局计算与独立复核 |
| 三式 | 太乙神数 | 盘局计算与独立复核 |
| 应用 | 择日 | 候选计算、硬冲突淘汰 |
| 环境 | 风水 | 形势观察输入与理气计算 |
| 观察 | 相法 | 隐私受限的可见事实规范化 |

权威能力卡位于 `references/routing.md`，可执行注册表由 `resources/runtime/providers/` 的能力清单驱动。语料覆盖不能替代真实计算能力。

## 核心设计

```mermaid
flowchart LR
    A["Agent 明确选择动作与体系"] --> B["prepare：校验输入"]
    B --> C["确定性计算 / 观察事实"]
    C --> D["古籍证据与反证编译"]
    D --> E["Agent 生成自然中文回答"]
    E --> F["complete：事实与证据校验"]
    F --> G["原子提交与连续谱系"]
```

V5.1 遵循以下原则：

- 不使用自然语言正则、关键词表或同义词表代替体系选择。
- 不用固定回答脚本冒充模型推理。
- 不制造超出事实粒度的具体时间、金额、地点或事件。
- 证据零命中时保持零命中，不伪造古籍出处。
- 追问继承已接受的基础盘，但会针对最新问题重新编译意图、证据和判断。
- 缺少必要资料时进入可恢复 intake，不强行输出断语。

## 快速开始

### 1. 准备独立运行环境

```bash
python3 scripts/provision_runtime.py
```

启动器优先使用显式配置的 `MINGLI_PYTHON`，否则使用：

```text
~/.local/share/mingli-master/venv/bin/python
```

它不会静默回退到系统 Python。

### 2. 查看可用能力

```bash
echo '{"kind":"describe"}' | scripts/run_reading_transaction.sh
```

### 3. 执行事务

生产交互只有三种 Command：

- `describe`：查看所有已就绪能力的结构化信息（缓存后不重复调用）
- `prepare`：携带结构化选择和确认事实，获得 `brief` 与 `state_token`
- `complete`：携带 `state_token` 与自然中文正文，原子提交

状态延续使用 opaque `state_token`：无 token 即新问题；pending token 补资料后重试 prepare；accepted token 加 `transition` 控制续问/修正/重起。

完整协议见 `SKILL.md` 和 `references/v2-reading-transaction.md`。

## 部署

只能从干净的私有 Git worktree 部署：

```bash
python3 scripts/release_deploy.py \
  --source /path/to/clean/mingli-master \
  --destination /path/to/installed/mingli-master \
  --apply --protect
```

部署器只选择允许发布的跟踪文件，排除运行记录、草稿、个人资料、密钥和本地完整语料，并写入带哈希与权限信息的发布 manifest。

Hermes 的 profile 拥有独立 Skill 目录，因此必须分别部署，例如：

```text
~/.hermes/skills/research/mingli-master
~/.hermes/profiles/<profile>/skills/research/mingli-master
```

更新 Skill 后无需重启 Hermes Gateway。新会话会读取最新内容；已有长会话可执行 `/reload-skills` 重新扫描。

## 验证

```bash
MINGLI_PYTHON="$HOME/.local/share/mingli-master/venv/bin/python"
MINGLI_RESEARCH_ROOT="/path/to/external-research-tree"

# 默认按 CPU 使用最多 10 个进程预算格；已审查的长审计会按真实子进程
# 数量占用 3/6 格，避免嵌套并发超卖。Provider completeness 的矩阵快照
# 在一个测试进程内只构建一次 canonical；它预留 6 格，内部并行 6 个
# 子进程审计 13 个 Provider，其余契约断言在普通格上并行运行。
# 同一轮中重复需要的 live audit report 只通过临时、运行级目录复用，运行
# 结束即删除；独立运行单个测试时会自动执行真实审计。状态、存储、原子性
# 和发布测试在自己的单进程顺序队列中执行，并与主并行区重叠。
PYTHONPATH=scripts "$MINGLI_PYTHON" -B \
  scripts/run_test_suite.py --research-root "$MINGLI_RESEARCH_ROOT"

# 可按机器内存调低两层并发；两者都设为 1 可复现严格串行行为。
PYTHONPATH=scripts MINGLI_MATRIX_JOBS=2 "$MINGLI_PYTHON" -B \
  scripts/run_test_suite.py --jobs 4 \
  --research-root "$MINGLI_RESEARCH_ROOT"

# 开发时只运行一组文件。
PYTHONPATH=scripts "$MINGLI_PYTHON" -B \
  scripts/run_test_suite.py --pattern 'test_v51_*contract.py'

PYTHONPATH=scripts "$MINGLI_PYTHON" -B \
  scripts/audit_provider_completeness.py --check

PYTHONPATH=scripts "$MINGLI_PYTHON" -B \
  scripts/audit_v51_vocabulary_locality.py --check

python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

验收覆盖陌生措辞、连续追问、资料修正、重新起盘、缺字段恢复、重启连续性、普通聊天隔离、制品身份和公开回答原样保留。

## 目录结构

```text
SKILL.md                              Agent 操作说明
scripts/adapters/json_cli.py           JSON Adapter（唯一生产 CLI 面）
scripts/run_reading_transaction.sh     可选 POSIX 启动引导
scripts/reading_engine/                计算、证据、谱系、校验与存储
resources/runtime/providers/          能力清单与公开词表
references/routing.md                 体系能力卡与输入要求
references/system-cards/              各体系的受限来源指导
references/books/                     已验证古籍参考包
references/inference/                 来源谱系与证据规则
docs/                                 架构、验收与发布记录
```

`references/fulltext/` 是本地研究语料，不进入发布包，也不上传仓库。

## 隐私与边界

- 出生资料、观察资料、真实会话和推演结果不进入 Git。
- 近时运势所需个人资料必须由 Gateway 在仓库外提供，并保持 `0600` 权限。
- 风水与相法只接受完成当前任务所需的最小观察事实。
- 本项目用于传统术数研究与 Agent 工程，不替代医疗、法律、投资等专业意见。

## 版本与证据

- 发布记录：`CHANGELOG.md`
- 当前发布状态与自动验收回执：`CHANGELOG.md`
- V5.1 实施账本：`docs/plans/2026-07-24-mingli-v51-progress.json`
- Provider 完整性矩阵：`references/matrices/provider-completeness.yaml`
- 参考目录：`references/catalog/D2_READY_REFERENCE_PACKS.md`

---

<div align="center">

**Private repository · Internal research and deployment only**

</div>
