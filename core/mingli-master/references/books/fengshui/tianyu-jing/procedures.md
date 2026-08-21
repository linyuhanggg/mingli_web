---
slug: tianyu-jing
file: procedures
---

# 天玉经 流程声明

> 本书包含大量罗盘、水口、挨星、零正神推演语汇。reference pack 只定义“如何调用资料”，不让 LLM 手算。

## TYP-01: 三卦语义定位

- **purpose**: 将用户问题中的江东/江西/南北、三般卦、父母卦定位到本书对应章节。
- **steps**:
  1. 检索 `terms.md` 中“三卦 / 父母”组。
  2. 优先读取 `chapter-map.md` 的 `shang-sanban`。
  3. 输出时区分经文口诀与注解阐释。
- **tool_dependency**: none
- **source_chapter**: shang-sanban
- **verified**: false

## TYP-02: 玄空/挨星源流查询

- **purpose**: 回答“天玉经如何谈玄空、挨星、天卦地卦”的文献层问题。
- **steps**:
  1. 检索 `TYR-04 / TYR-08 / TYR-09`。
  2. 引用 `quote-index.md` 中 TQ-006、TQ-012、TQ-013 等短引。
  3. 若涉及后世飞星操作，路由到玄空专项 skill 或工具，不在本 pack 内手算。
- **tool_dependency**:
  - tool.fengshui.luopan（仅当有实测坐向时）
  - tool.fengshui.xuankong（待定）
- **source_chapter**: shang-sanban, zhong-aixing
- **verified**: false

## TYP-03: 零正神/水法术语查询

- **purpose**: 将零神、正神、水口、四墓、借库、自库等术语归入文本证据链。
- **steps**:
  1. 检索 `terms.md` 的“山水 / 二十四山”组。
  2. 读取 `TYR-06 / TYR-11 / TYR-12`。
  3. 输出古文释义和版本争议，不做个案断语。
- **tool_dependency**:
  - tool.fengshui.luopan
  - tool.fengshui.watermouth（待定）
- **source_chapter**: shang-sanban, xia-lingshen
- **verified**: false

## TYP-04: 与青囊系互证

- **purpose**: 把《天玉经》与《青囊经》《青囊序》《青囊奥语》合参。
- **steps**:
  1. 先读取 `qingnang-xu` 的雌雄、金龙、山水二路。
  2. 再读取本 pack 的三卦、父母、玄空、挨星条目。
  3. 冲突时标注“源流互证未裁判”，留给 xhigh/专家团处理。
- **tool_dependency**: none
- **source_chapter**: all
- **verified**: false

## TYP-05: 安全输出边界

- **purpose**: 避免把古代富贵贫贱断语误用为现实建议。
- **steps**:
  1. 若用户问文献解释：可解释术语和句读。
  2. 若用户问现实房宅/阴宅吉凶：必须拒绝确定性断语，转为文化研究或要求专业测绘资料。
  3. 若用户提供坐向和水口：只允许结构化工具计算，LLM 不手算。
- **tool_dependency**:
  - tool.fengshui.luopan
- **source_chapter**: all
- **verified**: false

## TYP-06: 外编九星形势互证

- **purpose**: 当用户问贪狼、巨门、武曲、祿存、文曲、廉贞、破军、辅弼等形势名目时，路由到外编并与形势派古籍互证。
- **steps**:
  1. 先读 `chapter-map.md` 的 `waibian-jiuxing`。
  2. 从 `terms.md` 的“外编 / 形势九星”定位术语。
  3. 需要形势派细断时，交叉读取 `hanlong-jing`、`yilong-jing`、`zangshu`。
  4. 输出仅限文献释义和流派差异，不做实地结论。
- **tool_dependency**:
  - tool.fengshui.terrain（仅在有地形数据时）
- **source_chapter**: waibian-jiuxing
- **verified**: false
