---
title: 大六壬大全
slug: daliuren-daquan
system: san-shi
pack_type: evidence_reference_pack
source_status: complete_chapter_set
rule_coverage: selective
scan_collation: pending
adapter_required_for_casting: true
last_rebuilt: 2026-07-10
---

# 《大六壬大全》Reference Pack

本包是 `mingli-master` 的大六壬证据层，不是独立排盘器。它提供整书来源清单、两套十二卷结构、可追溯规则卡、冲突与停止条件。任何现实起课都必须先取得本地确定性 adapter 的结构化结果；缺少 adapter 输出时只能做古籍检索，不能由语言模型手排天地盘、四课、三传或天将。

## 当前结论

- **完整性**：normalized 十二容器齐全；Kanripo 文渊阁十二卷齐全；文渊阁第 0808 册影印已取得。
- **版本风险**：normalized 的卷次与 Kanripo 文渊阁本不一致，并多出独立“兵占”容器；两者不是可直接互换的卷号体系。
- **规则覆盖**：本包精选起例、九宗分支、天将、课体解释和毕法使用门，不声称穷尽全书全部规则。
- **校勘状态**：关键文本可检索并有独立转写见证；影印尚未建立本书页码图，也未逐图逐行校定。
- **测试状态**：静态来源、格式、行号与短引校验见 `validation.md`；模型盲测未执行。

## 来源层

| layer | 内容 | 可承担的证据 |
|---|---|---|
| `siku_editorial_preface` | 四库提要及馆臣批评 | 书目、归属、版本冲突；不等于汇编正文 |
| `compendium_body` | normalized 中的起例、神将、歌赋、课经、毕法等 | 行号可核的古籍规则和案例 |
| `kanripo_wyg_witness` | KR3g0031 文渊阁十二卷转写 | 独立文本见证、文渊阁卷次与叶码 |
| `scan_witness` | 文渊阁第 0808 册影印 | 最终字形、图表与页码校勘；当前未页映射 |
| `modern_synthesis` | 本包的术语、规则卡和流程 | 现代结构化转述，不得伪称原文 |

## 书内骨架

全书电子主文本的功能层可以概括为：

1. `起例层`：十干寄宫、贼克、比用、涉害、遥克、昴星、别责、八专、伏吟、返吟及神煞表。
2. `盘面语义层`：十二支神、月将、十二天将、日辰、发用、三传和歌赋。
3. `专题与课经层`：兵占、宿度分野、课经分类与大量课式。
4. `毕法层`：一百法索引及逐法说明，但电子文本存在编号与卷次异常。

两套具体卷次不得混称，详见 `chapter-map.md`。

## 依赖关系

```text
用户问题与占时
  -> 历法标准化（时区、节气、日时干支、月将）
  -> 本地确定性大六壬 adapter
  -> 天地盘、四课、取传轨迹、三传、天将、空亡等事实字段
  -> 本包 rules/procedures 的证据解释
  -> mingli-master 组织自然语言回答
```

- 本包**不依赖**《六壬指南》才能成立；兄弟书只可用于明示的异文或流派比较。
- Kanripo 是版本见证，不是另一套现代算法。
- 当前正式接口只有本地 `mingli-master.liuren_fact_adapter`；其他未定义工具名不能充当事实层。
- adapter 必须输出算法版本、历法口径、贵人 profile、规则决策轨迹和 source trace；字段不足即停止。

## 加载指南

| 需求 | 加载文件 |
|---|---|
| 确认来源、版本和校勘状态 | `source-manifest.yaml`, `validation.md` |
| 查询 normalized 与文渊阁卷次 | `chapter-map.md` |
| 查询术语和正确边界 | `terms.md` |
| 查询可执行规则卡 | `rules.md` |
| 组织起课与解释流程 | `procedures.md` |
| 引用短原文 | `quote-index.md` |
| 处理卷次、元首重审、昴星、别责、八专、天乙冲突 | `conflict-notes.md` |
| 运行或扩展压力测试 | `test-prompts.json` |

## 强制守门

1. **先 facts，后解释**：实际占事没有 adapter 结构化输出，不进入规则断法。
2. **卷号带体系**：写 `normalized 卷七` 或 `WYG/Kanripo 卷五`，不能只写“卷五”。
3. **引用带层级**：每个古籍结论必须带 `quote_id` 与 normalized 精确行号；需要文渊阁页叶时再带 Kanripo locator。
4. **贵人口径不静默**：正文沿俗例与四库提要订正意见并存；未给 `guiren_profile` 时不得布天将。
5. **不裸断课名**：元首、重审、官爵、游子、殃咎等名称只是一层结构，仍须核旺衰、神将、空亡、救制和问题域。
6. **不伪造完整率**：十二卷结构已建图不等于 13800 行逐条蒸馏，也不等于全部课式已适配。

## 文件清单

| 文件 | 状态 | 职责 |
|---|---|---|
| `source-manifest.yaml` | authoritative metadata | 来源、checksum、完整度、层级 |
| `chapter-map.md` | rebuilt | 两套十二卷与交叉映射 |
| `terms.md` | rebuilt | 术语、异名、操作边界 |
| `rules.md` | rebuilt | 精选可追溯规则卡 |
| `procedures.md` | rebuilt | adapter-first 执行流程 |
| `quote-index.md` | rebuilt | exact quote registry |
| `conflict-notes.md` | new | 同书、版本和实现冲突 |
| `validation.md` | rebuilt | 已执行静态校验与未执行项 |
| `test-prompts.json` | new | Darwin/mingli 压力测试定义 |
| `section-map.md` | compatibility only | 指向 `chapter-map.md`，不再保存虚假 done 切片 |

## 不应声称

- 不声称“100% 规则蒸馏”或“千课全部实现”。
- 不声称 normalized 就是逐页无差的文渊阁校本。
- 不声称四库提要已给出一张可直接编码的完整订正贵人表。
- 不声称历史占验已经过现代统计验证。
- 不在没有本地确定性 adapter 结果时给出正式大六壬课盘。
