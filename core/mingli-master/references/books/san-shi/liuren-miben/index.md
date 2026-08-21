---
title: 大六壬秘本
slug: liuren-miben
system: san-shi
school:
  - 大六壬
  - 鬼撮脚系
  - 秘本抄本
source_layer: specialty_and_correlative_reference
source_status: complete_text
reference_pack_status: usable_with_source_and_adapter_qualifications
depends_on: []
related_packs:
  - daliuren-daquan
  - liuren-zhiyin
source_links:
  - https://ctext.org/wiki.pl?if=gb&res=348173
  - https://commons.wikimedia.org/wiki/File:NCL-06572_%E5%A4%A7%E5%85%AD%E5%A3%AC%E7%A7%98%E6%9C%AC.pdf
---

# 《大六壬秘本》Reference Pack

> 十七卷完整可检索转写已经入库，三处 CTP 章界乱码已据 NCL-06572 影印补齐。本包完成的是全书结构索引、来源分层和选择性规则蒸馏，不是逐句规则化，也不是全本影印定本。

## 定位

本书汇集月将、天将、旬中神煞、射覆、百章歌、赋歌、五要权衡及多类专项占法。它在主 skill 中承担三类任务：

1. **类象检索**：卷一至卷七的人物、物类、形色、旺衰和射覆表。
2. **权衡补充**：卷十三、卷十四关于日辰、发用、三传、虚实、动静、始终、迟速的解释框架。
3. **专项分门**：卷八至卷十二、卷十五至卷十七的婚姻、行人、盗失、宅舍、求财、诉讼等传统分类材料。

本包不承担月将、天地盘、四课、三传、天将或旬空的计算，也不把本书的课名异文写入起课算法。

## Source State

- **辑录题署**：清·金正音辑。
- **检索底本**：CTP `ctp:wb348173` 五个 wiki chapter 的完整转写。
- **影印锚点**：NCL-06572，243 页，二册。
- **normalized/reference checksum**：`44ea31ef43f874ffc9da03c6ed6c01eee62081db6c2faf11593ec9bbe47847e0`。
- **结构**：书题/目录、卷一至卷十七、两处抄录款、影印补字记录。
- **校勘程度**：仅三处 CTP 章界完成影印逐字复核；其余尚未逐页对校。
- **层次风险**：正文、金氏辑注/朱批、其他署名批注和双行小字在电子文本中局部混排。

详见 [source-manifest.yaml](./source-manifest.yaml) 与 [conflict-notes.md](./conflict-notes.md)。

## Adapter Gate

### 可直接读取本包的情况

- 查询某一卷的结构、术语、异文或传统类象。
- 比较本书与其他六壬文献的说法。
- 已有确定性大六壬 adapter 的完整、校验通过输出，需要按本书做专项解释。

### 必须停止实际课断的情况

出现以下任一情形时，只能解释文献，不能声称已按本书完成具体起课：

- 没有可复算的占时、时区和历法口径。
- `calendar_normalization.validated` 不是 `true`。
- 缺少 `month_general`、天地盘、四课、三传、天将、旬空或日时干支。
- adapter 没有输出版本、规则 profile、贵人 profile 或输入校验结果。
- adapter 输出内部不一致，或把本书卷十三/卷十五的课名异文直接当计算规则。

### 最小输入契约

```yaml
adapter:
  name: "deterministic liuren adapter"
  version: "required"
  validation_status: "pass"
calendar_normalization:
  query_time: "ISO-8601"
  timezone: "IANA timezone"
  location: "required when calendar policy needs it"
  day_pillar: "required"
  hour_pillar: "required"
  month_general: "required"
  boundary_policy: "required"
output:
  earth_plate: {}
  heaven_plate: {}
  four_lessons: []
  three_transmissions: []
  heavenly_generals: {}
  xunkong: []
  lesson_type: "adapter-derived"
  rule_profile: "required"
  guiren_profile: "required"
```

## Loading Guide

| 需求 | 加载文件 |
|---|---|
| 先判断能否使用 | `index.md`、`source-manifest.yaml` |
| 查全书卷次和行界 | `chapter-map.md` |
| 查术语、异名、层次 | `terms.md` |
| 查可执行解释卡 | `rules.md` |
| 查调用顺序和停止条件 | `procedures.md` |
| 查原文短引 | `quote-index.md` |
| 查版本、异文和跨书冲突 | `conflict-notes.md` |
| 查静态校验与剩余风险 | `validation.md` |
| 做路由压力测试 | `test-prompts.json` |

## Interpretation Order

在 adapter 已通过的前提下，按此顺序读取，不得用单一神煞或单句歌诀跳步：

1. 明确问题域和主客/彼此。
2. 读取日辰、四课、发用与三传的结构事实。
3. 先看虚实、旺衰、生克、刑冲破害，再看神将。
4. 将初、中、末分作发端、移易、归计。
5. 按具体问题加载对应卷的类神和专项断法。
6. 神煞、歌诀和射覆表只作同源补充或冲突证据。
7. 输出所用规则、quote id、行号、来源层和未决冲突。

## Cross-Book Policy

- 《大六壬秘本》《大六壬大全》《六壬指南》互为**独立来源**，没有自动的上位覆盖关系。
- 跨书一致时可写“互证”，但要分别保留书名和证据锚点。
- 跨书冲突时并列展示来源、规则 profile 与实际选择，不以“大全更权威”自动抹掉本书异文。
- 本包不依赖《指南》才能加载，也不要求先用《大全》裁判。
- 排盘算法的选择由独立、经过测试的 adapter profile 决定，不由 reference pack 的名望决定。

## Claim Boundary

本包能证明“该版本在某行这样记载”，不能凭字符串命中证明术数效果、历史作者归属或现代事实必然如此。使用时应把文本解释、adapter 事实和现实证据分层记录。
