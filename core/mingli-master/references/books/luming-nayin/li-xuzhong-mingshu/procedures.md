# 李虚中命书 — Procedures

> 字段：`purpose` / `steps` / `tool_dependency` / `source_chapter` / `verified`。
> 全部 `verified: false`。排盘步骤一律 `依赖 tool.bazi.paipan`，禁止 LLM 手算。

---

## P-01 三元九命定位流程

- **purpose**: 按"干禄（天元）/支命（地元）/纳音身（人元）"三元分层，建立李虚中命书的核心命局结构。
- **steps**:
  1. 输入用户阳历生辰（年月日时）→ `依赖 tool.bazi.paipan` 起四柱+胎元（月干进一、月支前三位）。
  2. 标定每柱纳音五行（60甲子海中金/炉中火等表）。
  3. 干层（天元）：抽取四柱天干，按 [LX-T12](terms.md) 论"名禄贵权"。
  4. 支层（地元）：抽取四柱地支，按 [LX-T13](terms.md) 论"金珠积富"。
  5. 纳音层（人元）：以年柱纳音为身命主，按 [LX-T14](terms.md) 论"才能器识"。
  6. 三元各分生/旺/库三地，构成"九命"判别。
- **tool_dependency**: `tool.bazi.paipan`（起四柱+胎元）；纳音表内置；长生十二宫表内置。
- **source_chapter**: juan-zhong/sanyuan-jiu-ming、juan-zhong/sizhu-xiu-bei
- **verified**: false

## P-02 六十甲子单元判读流程

- **purpose**: 按 [chapter-map.md `juan-shang/jiazi`~`guihai`](chapter-map.md) 60条对照命主年柱/日柱的纳音性质。
- **steps**:
  1. 调用 P-01 取得四柱。
  2. 以年柱（命主）为基准，对照 60 甲子条目检索相应"五行性质 + 喜忌 + 命格"三段式。
  3. 同步对照日柱、月柱、时柱纳音，记录"喜忌冲突/和合"。
  4. 输出年柱主性 + 日柱副性 + 月时辅性的命局轮廓。
- **tool_dependency**: `tool.bazi.paipan`；60甲子条目表（chapter-map.md+rules.md）。
- **source_chapter**: juan-shang/jiazi ~ juan-shang/guihai
- **verified**: false

## P-03 天乙贵神/贵合贵食/紫虚局识别流程

- **purpose**: 扫描命局是否触发 [LX-02-03~06](rules.md) 系列吉格。
- **steps**:
  1. 调用 P-01 取得四柱+胎元。
  2. 按 [LX-T21~T31](terms.md) 检查天乙贵神是否落于月日时三柱。
  3. 若命中天乙，进一步对照 [`juan-shang/guishen-youlie`](chapter-map.md) 判文星/华盖/截路空亡/进神/交神/伏神/羊刃之具体优劣。
  4. 检查贵合（甲戊庚得己丑己未等）、贵食（甲食丙乙食丁等）。
  5. 若命局月日时互换见贵且太岁不带→ 触发紫虚局判定。
  6. 输出格局列表 + caveats（古代官禄话语，不作现代预测）。
- **tool_dependency**: `tool.bazi.paipan`；天乙贵神对照表（terms.md）。
- **source_chapter**: juan-shang/tianyi-guishen ~ juan-shang/zixu-ju
- **verified**: false

## P-04 三元九限运程推算流程

- **purpose**: 按李虚中"三元九限"体系（异于子平的大运/流年）推算运程波段。
- **steps**:
  1. 调用 P-01 取得四柱。
  2. 大运起法：阳男阴女顺、阴男阳女逆；十干分月、三日成年（[LX-T44](terms.md)）→ `依赖 tool.bazi.paipan` 计算大运起始岁。
  3. 小运起法：男一岁起寅、女一岁起申，逐年循环（[LX-T45](terms.md)）。
  4. 限位判别（[LX-T46~T52](terms.md)）：
     - 三元到中庸地见贵 → 天官限（君子荣）；
     - 三元到旺相+四柱相资 → 得势限；
     - 禄/命/身入土下 → 藏限（不利君子）；
     - 金人到亥子 → 波浪限；
     - 三元衰绝+禄鬼 → 风雨限；
     - 行运身旺支干死绝 → 布素限；
     - 三元值鬼+二运三刑 → 失所限（⚠️）；
     - 运至伏吟逢丧吊白衣飞廉 → 灾位限（⚠️）。
  5. 输出大运表 + 小运表 + 限位标识 + 严格 caveats。
- **tool_dependency**: `tool.bazi.paipan`（大小运）；三元九限识别表。
- **source_chapter**: juan-xia/sanyuan-jiu-xian ~ juan-xia/po-sui-zai-wei-xian
- **verified**: false

## P-05 神头禄六合之德识别流程

- **purpose**: 扫描命局是否符合 [LX-08-01](rules.md) 的"神头禄+六合之德"组合。
- **steps**:
  1. 调用 P-01 取得四柱。
  2. 对四柱中任两柱，检查是否同属"五合"（甲己/乙庚/丙辛/丁壬/戊癸）。
  3. 命中即匹配三十组六合之德（如"甲子己丑—换贵德"、"甲寅己亥—三元承天德"等，详见 [chapter-map.md `juan-xia/liu-he-jia-zi-mu`~`liu-he-ren-ding`](chapter-map.md)）。
  4. 同步检查 12 位神头禄（戊辰/戊戌/己丑/己未/丙午/丁巳/壬子/癸亥/甲寅/乙卯/庚申/辛酉）是否成立。
  5. 输出"六合之德"+"神头禄"组合表，附 caveats。
- **tool_dependency**: `tool.bazi.paipan`；六合之德三十组对照表；神头禄12位表。
- **source_chapter**: juan-xia/liu-he-de-zonglun ~ juan-xia/shi-jiazi-shou-zhi-shen
- **verified**: false

---

## 通用约束

- **禁止 LLM 手算**：四柱、胎元、纳音、神煞起例、大小运、限位一律 `依赖 tool.bazi.paipan`，否则视为流程不合规。
- **禁止铁口断**：所有涉及寿夭/疾病/死亡/婚配/职业/贫贱的断语必须 reframe，参考 [rules.md ⚠️ 敏感断语集中提示](rules.md)。
- **正文/注文分层**：原书"正文+小字双行注"混排，**本 pack 仅抽取正文层**作为流程依据。
- **跨系统隔离**：本 pack 为禄命纳音体系，**不混用**子平用神/紫微星曜术语；如需子平判读，跳转 [`references/bazi/`](../../bazi/)；紫微跳转 [`references/ziwei/`](../../ziwei/)。

---

**流程统计**：5 个核心流程（三元九命定位 / 六十甲子判读 / 天乙贵神识别 / 三元九限运程 / 神头禄六合之德）。
