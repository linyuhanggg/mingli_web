---
title: 李虚中命书 — Reference Pack
slug: li-xuzhong-mingshu
system: luming-nayin
school: 唐宋禄命纳音体系（鬼谷子撰、李虚中注，传本）
source_layer: primary
source_status: normalized_ready
depends_on: []
informs:
  - references/luming-nayin/luoluzi-sanming
  - references/luming-nayin/yuzhao-shenying
  - references/luming-nayin/wuxing-jingji
core_use_cases:
  - 六十甲子纳音五行性质判别（金溺水下、火出水上等十二音五行轻重）
  - 天乙贵神、贵合贵食、紫虚局之识别
  - 三元九命（天元干禄/地元支命/人元纳音身）总纲
  - 五行性情、清浊、升降、真假之文化研究
not_for:
  - 现代职业、寿命、疾病、婚配的预测断语
  - 紫微星曜/宫位/四化系统（属于 references/ziwei/）
  - 子平日主格局之"用神/喜忌"系统（属于 references/bazi/）
extraction_targets:
  - 60 甲子单位的纳音格局描述（卷上主体）
  - 天乙贵神 / 贵合贵食 / 紫虚局
  - 三元九命系统（卷中"三元入墓"、"九命论"等）
  - 三元九限的运程理论
  - 天承地禄六合之德三十组、神头祿格局
batch: D2
verified: false
---

# 李虚中命书 — Reference Pack

## 一、典籍简介

《李虚中命书》三卷，题"鬼谷子撰，唐李虚中注"，实为唐宋之间禄命纳音学派集成。其文为韩愈《昌黎先生集·殿中侍御史李君墓志铭》所记"以人之始生年月日所值日辰支干相生胜衰死王相斟酌推人寿夭贵贱"的具体方法源头，**世传星命之学者皆以虚中为祖**。

四库馆臣详勘文本，指出：
- 前半"六十甲子"详释合于韩愈墓志所言"始生年月日"之三柱法；
- 后半多称"四柱"系宋以后术语，疑唐人原文为宋星家所添入；
- 故"真伪杂出"，**本 pack 不论作者真伪**，按现存传本（永乐大典所收+晁公武读书志三卷本）原文层做提取。

## 二、与外部典籍的关系

```
李虚中命书（祖论）
  ├─→ 珞琭子三命消息赋（相生相成的赋文体）
  ├─→ 玉照神应真经（神将十二支神断语化）
  └─→ 五行精纪（廖中南宋集成 34 卷大全）
```

李虚中命书是禄命纳音体系**最早的系统化文献之一**，其六十甲子纳音性质表（"甲子天官藏"、"乙丑禄官承"...）在后世被广泛引用。本套件作为禄命书的**理论祖本参考**，应优先于其他三本被加载。

## 三、与紫微/八字系统的边界

| 维度 | 李虚中体系 | 子平八字 | 紫微斗数 |
|---|---|---|---|
| 命主 | 年柱 / 纳音身 | 日干 | 命宫主星 |
| 五行 | **纳音五行**（甲子海中金等） | 天干本五行 | 星曜五行 |
| 关键术语 | 三元九命 / 三限 / 神头禄 / 贵神 | 用神 / 喜忌 / 格局 | 星曜 / 宫位 / 四化 |
| 排盘 | 年/胎/月/日/时五主 | 四柱（年月日时） | 十二宫位 |

**严禁混用**。本 pack 全部术语限于"纳音/五行/干支/禄命/神煞/格局"六类。

## 四、文件组织（File Map）

| 文件 | 作用 | 关键字段 |
|---|---|---|
| [chapter-map.md](chapter-map.md) | 三卷分节地图 | slug / source_anchor / verified |
| [terms.md](terms.md) | 术语表（约 60 条） | id / term / definition / category |
| [rules.md](rules.md) | 抽取规则（含 caveats） | rule / applicable_to / caveats |
| [procedures.md](procedures.md) | 排盘/判读流程（依赖 tool.bazi.paipan） | steps / tool_dependency |
| [quote-index.md](quote-index.md) | 短引索引（≤80字×120 条） | quote / chapter / source_anchor |
| [validation.md](validation.md) | 覆盖率与状态 | D2 ready_candidate / evidence gate |

## 五、Loading Guide（建议加载顺序）

1. **首次加载**：index.md（本文件）→ chapter-map.md
2. **理解六十甲子**：terms.md → quote-index.md（卷上 60 条原文）
3. **应用层判读**：rules.md → procedures.md
4. **可信度核查**：validation.md（注意 verified: false）

## 六、声明

- **底本说明**：以四库本永乐大典所收为底，CTP 入口 https://ctext.org/wiki.pl?if=gb&res=812498 。
- **verified 状态**：全部 false（本地 normalized source 已完整取得；四库本影印逐条对校仍待补）。
- **正文/注文分层**：原书"正文+小字双行注"混排，**本 pack 仅抽取正文层**。带〔...〕的小字注暂不入 terms/rules，作为参考记入 chapter-map 的 notes。
- **敏感断语 reframe**：寿夭/疾病/职业/婚配/贫贱断语，一律带 caveats（参见 rules.md）。
