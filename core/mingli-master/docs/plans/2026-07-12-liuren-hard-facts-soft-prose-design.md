# 大六壬“硬事实、软表达”设计

## 背景

2026-07-12 的真实 Hermes BlueBubbles 会话 `20260712_071646_c9eb203d` 暴露出两个不同层级的问题：

- 事实层有价值：首稿把第一课写成“丁未上戌”，当前 gate 正确地拒绝了错课。
- 表现层过严：同一首稿还因“未将小吉”、紧凑三传、“结论”措辞、未公开列全三本书名而被拒绝。
- 执行链过重：补充城市后的正式占事产生 14 个工具调用，`read_file` 注入 97,431 字符，超过既定 8 次调用和 20k context 预算。
- 公开稿报告化：为满足固定解析格式，最终回复被迫展开完整四课、三传六亲天将、旬空和三书依据。

问题不是 gate 本身，而是事实校验、证据校验和公开文风被绑成了一个合同。

## 目标

1. 继续 fail-closed 校验起课时间、月将、取传法、四课三传、旬空、候期和明确事实声明。
2. 将起课、校验、brief、古籍检索收敛为一个 hash-bound pipeline。
3. 默认公开一行紧凑课象，再给直接判断和一个决定性机制。
4. 不强制固定标题、完整四课、三传全部六亲天将、三本书名或行动建议。
5. 同一课的解释性追问复用当前课，不重复起课和读取古籍。
6. 将正常回合控制在 4 个 skill-specific tool calls，允许一次修稿时不超过 6 个。

## 非目标

- 不放松错课、错候期、错月将和无依据确定性结论的拦截。
- 不取消古籍证据，也不让模型从记忆选择熟悉断语。
- 不把古籍文本直接拼进公开回复。
- 不改变大六壬 adapter 的算法口径。

## 架构

### 单一 Pipeline

新增 Hermes 入口 `~/.hermes/scripts/liuren_calc.py`：

```text
question + datetime + timezone + location
  -> liuren_fact_adapter cast
  -> adapter_validate liuren
  -> liuren_public_brief
  -> reading_source_plan(system=liuren)
  -> reading_evidence_bundle
  -> private artifacts + compact synthesis_context
  -> mingli-liuren-pipeline-v1 manifest
```

完整 facts、brief、source plan 和 evidence 存在权限为 `0700/0600` 的唯一运行目录。模型只得到紧凑 synthesis context、公开稿路径和 gate command。

### 公开课象

默认公开课象只要求这些可核对事实：

- 日柱、时柱；
- 月将；
- 课体/取传法；
- 三传地支；
- 旬空。

四课、三传六亲和天将仍留在事实层。模型若主动声明这些字段，gate 必须逐项核对；未声明时不强迫展开。

### 自然判断

课象必须在判断之前，但判断不依赖固定标题。以下均可表达 direct verdict：

- “判断：候期在……”
- “我直说，偏慢……”
- “传统候期落在……”
- “这件事更偏向……”

gate 只检查是否实际回答了问题、是否有决定性课理，以及声明是否匹配事实。来源名称、条件句和行动建议为可选内容。

### 古籍证据

三套 D2-ready pack 继续由 source plan 和 evidence bundle 在当前起课后检索。gateway 校验 bundle 的路径、hash、plan digest 和 facts digest。公开回复不再被要求列出全部来源；只有模型主动提书名时，才检查书名是否在当前 bundle 中。

### Gateway

gateway 同时支持：

- 新 `mingli-liuren-pipeline-v1`；
- 旧 adapter + 六文件读取链，作为兼容路径。

新路径只有在 manifest、runtime identity、私有 artifact、source/evidence digest 和最终 public gate 全部有效时才放行。最终仍只交付 gate 返回的 hash-bound `public_copy`。

## 默认公开效果

```text
【玄枢｜MINGLI】
课象：丁亥日甲辰时，未将，昴星课；三传午空→戌→寅，旬空午未。
判断：下次工资的传统候期在 7 月 23 日前后，偏慢，不像立即到账。
初传空、末传实，是先悬后落的结构；这个日期是候期，不是保证当天发薪。
```

完整四课和来源清单只在用户要求“展开课盘”或追问依据时显示。

## 验收

- 错四课仍失败。
- 错月将、错三传、错旬空、错候期仍失败。
- “未将”“月将为未”均可通过。
- “结论”“判断”“我直说”“传统候期落在”均可表达直接判断。
- 紧凑课象不因省略四课、六亲、天将和书名而失败。
- pipeline manifest 小于 12,000 bytes。
- 正常回合不超过 4 个 tool calls，修稿回合不超过 6 个。
- 真实工资候期回复同时通过 gate 与人工复核。
