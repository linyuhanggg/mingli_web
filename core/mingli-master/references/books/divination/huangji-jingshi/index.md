---
title: 皇极经世书
slug: huangji-jingshi
system: divination
school:
  - 象数
  - 元会运世
  - 邵雍
source_layer: primary
source_status: partial
source_links:
  - https://zh.wikisource.org/wiki/%E7%9A%87%E6%A5%B5%E7%B6%93%E4%B8%96%E6%9B%B8
version_notes: |
  宋·邵雍（康节，1011-1077）撰。元会运世、先天易学、象数推演的总集，宋代象数易学之巅峰。
  通行本系统：四库全书文渊阁本，14 卷（卷十三、十四为《观物外篇》上下）。
  本 pack 以维基文库整理本（CC BY-SA 4.0）为参考底本。
  全书结构：
    - 卷一至卷六：觀物篇 1-34，元会运世数表（以元经会、以会经运、以运经世）
    - 卷七至卷十：觀物篇 35-50，运经世（以世经世数）
    - 卷十一至卷十二：觀物篇 51-62（声音律吕图、声音唱和图等地物之数）
    - 卷十三至卷十四：觀物外篇 上 / 下（邵子门人辑录之口义、易学要旨）
depends_on: []
informs:
  - meihua-yishu
  - zhouyi-zhezhong
core_use_cases:
  - 元会运世数理框架（一元 12 会、一会 30 运、一运 12 世、一世 30 年；总 129600 年）
  - 先天易学（伏羲六十四卦方圆图）原始文献
  - 邵雍象数易学源头（观物内 / 外篇之义理）
  - 历史史观（以元经会主天、以会经运主地、以运经世主人）
not_for:
  - LLM 手算元会运世年表（必须 `tool.divination.huangji`）
  - 个人命局推算（本书是宇宙史观，非个人命术）
  - 严格历史预测 / 现代决策（属术数史观，非现代实证）
  - 卜筮断卦操作（应转 `meihua-yishu` 或 `zengshan-buyi`）
extraction_targets:
  - concepts
  - terms
  - rules
  - procedures
  - cautions
  - quote_index
conflict_policy: |
  - 与朱熹《周易本义》冲突 → 本书属象数易学源头（北宋），朱熹义理易学（南宋）属另一系；冲突视语境分流。
  - 与京房纳甲冲突 → 本书不涉占法纳甲，元会运世为时间数理框架；不混用。
  - 与梅花易数冲突 → 梅花传为邵雍后学伪托，与本书原典不一定一致；本 pack 仅以本书为邵雍原典之据。
validation_notes: |
  - 文渊阁本与黄畿《皇极经世书传》、张行成《皇极经世索隐》之文本细节差异未在本 pack 复核。
  - 觀物篇 1-50 为大量数表（年甲子表），本 pack 不展开数表细目，仅给框架性概览。
  - 觀物外篇上下系门人辑录，与内篇文体不同，故 chapter-map 标注分离。
  - 全部章节 `verified: false`。
modern_notes: |
  现代邵雍研究（高怀民、唐明邦、张其成等）对元会运世数有诸多重新阐释；本 pack 仅收原典框架。
  现代用本书做"历史预测"或"国运推算"属过度演绎，应注明文化参考性质。
---

## D2 Source Scope

- **source_lines**: 37276
- **structural_units**: 8132
- **scope**: 四库本维基文库整理源；含大量元会运世数表与观物篇标题。
- **version_note**: 当前 D2 ready 表示本地 Wikisource 四库本 normalized source 已全标题建图；数表 HTML 还原风险保留，后续可做表格专门结构化。
- **evidence_files**: `section-map.md`, `chapter-map.md`, `quote-index.md`


# 皇极经世书 Reference Pack（index）

> 本文件是《皇极经世书》参考包的**入口索引**。详细内容分布在 `chapter-map.md / terms.md / rules.md / procedures.md / quote-index.md / validation.md`。

## Source

- **作者**：宋·邵雍（康节，1011-1077），北宋洛阳象数易学宗师。
- **版本系统**：四库全书文渊阁本（清乾隆，14 卷）。
- **本 pack 底本**：维基文库整理本（CC BY-SA 4.0）。
- **复核状态**：`partial`。文渊阁本与黄畿、张行成传索本之异未复核。

## Position In Lineage

- **在象数易学中的位置**：宋代象数易学的总集与原典；与周敦颐、邵雍、张载并列为"北宋四子"之一。
- **上游**：《周易》经传、汉魏象数易学（孟喜、京房、扬雄太玄）、唐《李虚中命书》。
- **下游**：朱熹《易学启蒙》（折中本义）、梅花易数（民间伪托）、《周易折中》（清官方）、明清诸子注疏。

## Core Use Cases

- 元会运世数理框架（一元 = 12 会 = 360 运 = 4320 世 = 129600 年）
- 三才数理（以元经会主天、以会经运主地、以运经世主人物）
- 先天易学（伏羲六十四卦方圆图、八卦次序图）
- 观物内篇（义理：观物之道）
- 观物外篇（声音律吕图、动植飞走数）
- 邵雍象数史观源头文献

## Not For

- 个人命术 / 八字推算（本书是宇宙史观，非命术）
- LLM 手算元会运世年表（必须 `tool.divination.huangji`）
- 卜筮起卦 / 断卦（应转 `meihua-yishu` 或 `zengshan-buyi`）
- 现代严格历史预测（属术数史观，仅供文化参考）

## Loading Guide

1. **默认只加载** `index.md`：拿 frontmatter / 卷次概览 / 路由。
2. **查具体章节** → `chapter-map.md`。
3. **查术语** → `terms.md`。
4. **查判断规则** → `rules.md`。
5. **查推演流程** → `procedures.md`。
6. **查短引 + 出处** → `quote-index.md`。
7. **查覆盖率 / 版本状态** → `validation.md`。

## File Map

| 文件 | 职责 | 何时加载 |
|---|---|---|
| [index.md](./index.md) | 入口索引 + frontmatter + 卷次概览 + 路由 | 默认加载 |
| [chapter-map.md](./chapter-map.md) | 14 卷地图 + 觀物篇 1-62 + 觀物外篇 | 需要查具体章节 |
| [terms.md](./terms.md) | 元会运世 + 先天 + 声音律吕等核心术语 | 需要查术语 |
| [rules.md](./rules.md) | 数理 + 易理判断规则 | 需要查判断规则 |
| [procedures.md](./procedures.md) | 元会运世推演 / 先天起卦框架 | 需要查操作流程 |
| [quote-index.md](./quote-index.md) | 短引索引（觀物篇 + 外篇要言） | 需要引用原文 |
| [validation.md](./validation.md) | 覆盖率 + 版本状态 | 需要校验覆盖率 |

## Routing

主 skill 收到象数易学 / 元会运世相关问题后：

1. **元会运世数理框架** → 本 pack `terms.md` + `rules.md` HR-01-* + procedures.md HP-01
2. **先天易学（方圆图）** → 本 pack `terms.md` + `rules.md` HR-04-*
3. **观物义理（观物之道）** → 本 pack `quote-index.md` 觀物篇要言
4. **声音律吕** → 本 pack `chapter-map.md` 卷十一 / 十二
5. **观物外篇（口义辑录）** → 本 pack `chapter-map.md` 卷十三 / 十四
6. **个人占断 / 命术** → 转 `bazi/*` 或 `divination/{meihua-yishu, zengshan-buyi}`
7. **易学义理** → 转 `divination/zhouyi-zhezhong`
8. **元会运世数理推演**（具体年代换算）→ 必须 `tool.divination.huangji`，**禁止 LLM 手算**。

## 冲突裁判

详见 frontmatter `conflict_policy`。
