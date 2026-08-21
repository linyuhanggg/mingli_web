# 玉照神应真经 — Procedures

> 字段：`purpose` / `steps` / `tool_dependency` / `source_chapter` / `verified`。
> 全部 `verified: false`。
> 排盘步骤一律 `依赖 tool.bazi.paipan`，禁止 LLM 手算干支/纳音。

---

## P-01 五主参看流程

- **purpose**: 按"年/胎/月/日/时五主"分尊卑判生尅，识别命局主导力。
- **steps**:
  1. 输入用户阳历生辰（年月日时）→ `依赖 tool.bazi.paipan` 起四柱（年柱/月柱/日柱/时柱），并由月柱推得**胎元**（月干进一、月支前三位）。
  2. 标定五主纳音五行（甲子海中金等60甲子纳音表）。
  3. 两两判定干尅、音尅、干合、支合、支冲、支刑。
  4. 对所有"上尅下/下尅上"按 [YZ-02-02](rules.md) 标定部位（头面尊老 / 身体陰人）。
  5. 输出五主关系图（建议表格化）。
- **tool_dependency**: `tool.bazi.paipan`（起四柱+胎元）；纳音表内置。
- **source_chapter**: theme-01/sanchu-cankan、theme-01/shang-ke-xia
- **verified**: false

## P-02 干神/支神映射神煞流程

- **purpose**: 将四柱十干十二支映射到玉照体系神将（青龙/六合/朱雀/螣蛇/勾陈/太常/白虎/太陰/天后/玄武）+ 十二支神（功曹/太冲/天罡/...大吉）。
- **steps**:
  1. 调用 P-01 取得四柱。
  2. 按 [terms.md](terms.md) YZ-T09~YZ-T30 直接映射：天干→十干神将；地支→十二支神。
  3. 检查神将与支神组合是否触发主题二/三的常用断语（如"魁罡上见往来"、"乙辛丁巳亥酉官事"）。
  4. 命中即输出对应规则 + 严格 caveats reframe（参考 [rules.md](rules.md) YZ-03-xx）。
- **tool_dependency**: `tool.bazi.paipan`；神将映射表（terms.md）。
- **source_chapter**: theme-03/jia-qinglong ~ theme-03/shier-zhi-shen
- **verified**: false

## P-03 入墓/刑冲扫描流程

- **purpose**: 扫描四柱中"干墓在辰戌丑未"、自刑、三刑、玄武折足等敏感结构。
- **steps**:
  1. 调用 P-01 取得四柱+纳音。
  2. 对每柱天干，按 [YZ-T31~T33](terms.md) 检查是否落在辰戌丑未（库/墓）。
  3. 扫描三刑组合：子卯、丑戌未、寅巳申、辰午酉亥自刑。
  4. 命中"丑戌未"→ 触发 [YZ-05-06](rules.md)（⚠️ 疾病断语 reframe）。
  5. 命中"卯+辰"→ 触发 [YZ-05-07](rules.md)（⚠️ 刑讼/疾病 reframe）。
  6. 输出结构清单 + 文化研究层 caveats，**不输出医学/司法预测**。
- **tool_dependency**: `tool.bazi.paipan`。
- **source_chapter**: theme-04/gan-shen-zhi-mu ~ theme-04/zi-xing-zhongjian
- **verified**: false

## P-04 月德/三限/十二宫定位流程

- **purpose**: 以年支为基础推月德/月德合，叠加三限段(25/50/50+)合十二宫定位。
- **steps**:
  1. 调用 P-01 取得四柱。
  2. 按月支推月德/月德合（古法表）。
  3. 按用户年龄分配三限段：
     - 年龄 ≤ 25 → 用月柱合十二宫；
     - 25 < 年龄 ≤ 50 → 用日柱；
     - 年龄 > 50 → 用时柱。
  4. 将月德/月德合落点对应至十二宫（命/兄弟/妻妾/...父母）。
  5. 输出"当限主宫+月德落宫"二维定位。
- **tool_dependency**: `tool.bazi.paipan`；月德/月德合查表；十二宫推定法（玉照体系，不同于紫微斗数）。
- **source_chapter**: theme-06/yue-de-shuang-jia、theme-06/shi-er-gong、theme-06/san-xian-jian-xiang
- **verified**: false

## P-05 真五行（合化）正道判流程

- **purpose**: 区分纳音五行与"甲己真土/乙庚真金/丙辛真水/丁壬真木/戊癸真火"合化五行。
- **steps**:
  1. 调用 P-01 取得四柱天干。
  2. 检查月干与日干、年干与日干是否满足"五合"（甲己/乙庚/丙辛/丁壬/戊癸）。
  3. 命中合且地支不破（无相冲、相刑），按 [YZ-08-04](rules.md) 标记"真五行"。
  4. 与纳音五行**并列对照**（不替代），输出"真五行 vs 纳音五行"二元结构。
  5. 五行升降按 [YZ-08-02](rules.md) 判断进退气势。
- **tool_dependency**: `tool.bazi.paipan`；纳音表；五合判别。
- **source_chapter**: theme-08/zhengdao-ge、theme-08/gan-zhi-jin-tui、theme-08/wai-nei-he
- **verified**: false

---

## 通用约束

- **禁止 LLM 手算**：四柱、胎元、纳音、神煞起例、月德、十二宫一律 `依赖 tool.bazi.paipan`，否则视为流程不合规。
- **禁止铁口断**：所有涉及寿夭/疾病/死亡/婚配/职业的断语必须 reframe，参考 [rules.md ⚠️ 敏感断语集中提示](rules.md)。
- **禁止跨系统术语污染**：本 pack 为禄命纳音体系，**不使用**紫微星曜/宫位/四化术语；如需用户同步紫微判读，应跳转至 [`references/ziwei/`](../../ziwei/) 套件。
- **可信度声明**：本套件 7 文件全部 `verified: false`，待四库本影印逐条对校。

---

**流程统计**：5 个核心流程（五主参看 / 神将映射 / 入墓刑冲 / 月德三限 / 真五行合化）。
