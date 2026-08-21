# 董公择日 — Terms

> D2 术语索引。术语按《董公选择日要览》本地规范化文本与 `monthly-day-table.md` 归纳；`verified=false` 表示尚未对国图影印逐页校勘。
> 本文件只给 skill 路由和检索使用，具体神煞起例仍需以 `mingli-master.selection.v1` 与官方书交叉。

## 1. 月日索引类

| term | definition | source_chapter | evidence | verified |
|---|---|---|---|---|
| 月建 | 正月寅、二月卯至十二月丑的月支框架，是本书 12 月日课表的上层索引。 | month/* | chapter-map.md month/01-yin~month/12-chou | false |
| 建除十二日 | 建、除、满、平、定、执、破、危、成、收、开、闭十二值，本书每月各列一轮。 | month/* | monthly-day-table.md DG-D001~DG-D144 | false |
| 月日条目 | 由“月建 + 建除值 + 日支”构成的原文条目，例如正月寅月建寅日。 | month/* | monthly-day-table.md 全表 | false |
| 四离四绝 | 节气交接前后的避忌类术语，见各月节令提示。 | month/* | fulltext.md L51, L110 等 | false |
| 三煞方 | 节气后提示某方忌修造动土，如“立春后三煞在北”。 | month/* | fulltext.md L52, L109 等 | false |

## 2. 吉日类

| term | definition | source_chapter | evidence | verified |
|---|---|---|---|---|
| 煞贡日 | 本书附录列出的民间吉日类之一，常与直星、人专并列。 | appendix/sha-gong-zhi-xing-ren-zhuan | quote-index.md DG-Q152~DG-Q153 | false |
| 直星日 | 本书附录列出的民间吉日类之一，不与紫微等体系同名词混用。 | appendix/sha-gong-zhi-xing-ren-zhuan | quote-index.md DG-Q152~DG-Q153 | false |
| 人专吉日 | 本书附录列出的“人事”通用吉日类。 | appendix/sha-gong-zhi-xing-ren-zhuan | quote-index.md DG-Q152~DG-Q153 | false |
| 天德 / 月德 | 月日表中常见吉神名；本 pack 仅记录原文出现，不负责起例。 | month/* | monthly-day-table.md `summary` 字段 | false |
| 黄罗紫檀 / 天皇地皇 | 本书吉曜套语，常与财库、金银库楼等并列作为吉象描述。 | month/* | monthly-day-table.md `summary` 字段 | false |

## 3. 凶日 / 神煞类

| term | definition | source_chapter | evidence | verified |
|---|---|---|---|---|
| 金神七煞 | 附录歌诀所列避忌，技能中作民间通书避忌项。 | appendix/jinshen-qisha-ge | quote-index.md DG-Q151 | false |
| 煞入中宫 / 煞集中宫 | 月日表和论略中反复出现的重避忌项，输出时只能表述为“原书列为避忌”。 | front/lunlue-shisanze；month/* | quote-index.md DG-Q005；monthly-day-table.md `risk_terms` | false |
| 白虎入中宫 | 论略中特别提示不宜中庭钉钉、鼓乐喧哗的凶煞类说法。 | front/lunlue-shisanze；month/* | quote-index.md DG-Q005 | false |
| 红沙 / 小红沙 | 月日表常见民间避忌名。 | month/* | monthly-day-table.md `summary` 字段 | false |
| 四废 | 月日表常见避忌名，需由历算工具确认。 | month/* | monthly-day-table.md `risk_terms` | false |
| 重丧 | 丧葬相关凶煞/凶验语之一，必须重写为文化文本描述。 | month/* | monthly-day-table.md `risk_terms` | false |

## 4. 用事分类

| term | definition | source_chapter | evidence | verified |
|---|---|---|---|---|
| 嫁娶 | 婚姻嫁娶之事；本书常与起造、入宅、开张同列宜忌。 | front/lue-ji；month/* | quote-index.md DG-Q002；monthly-day-table.md | false |
| 起造 / 修造 / 动土 | 建筑、修方、动土类事项，需同时检查方位煞和金神七煞。 | front/lue-ji；month/* | rules.md DR-05；monthly-day-table.md | false |
| 移居 / 入宅 | 搬迁入宅事项，论略强调需兼看主人入宅、敬神时辰。 | front/lunlue-shisanze；month/* | quote-index.md DG-Q003~DG-Q004 | false |
| 出行 | 远行、出门事项；本书只作民间通书口径。 | front/lue-ji；month/* | monthly-day-table.md | false |
| 安葬 / 丧葬祭祀 | 殡葬、祭祀类事项；输出必须避免事实性凶断。 | front/lue-ji；month/* | monthly-day-table.md | false |
| 上官 / 赴任 / 入学 | 附录煞贡、直星、人专吉日明确列入的用事类。 | appendix/sha-gong-zhi-xing-ren-zhuan | quote-index.md DG-Q153 | false |

## 5. 跨体系同名词警示

| term | 本书含义 | 其它体系含义 | 处理 |
|---|---|---|---|
| 直星 | 民间通书吉日类 | 紫微、星命语境可能另有所指 | 不互通，按 source_chapter 路由 |
| 黄道 | 择日/选时中的黄黑道语境 | 天文学黄道或星命黄道十二宫 | 不互通，必须区分体系 |
| 吉凶 | 原书文化文本的宜忌/凶验话语 | 现实预测或事实断言 | 必须改写为“原书认为/列为” |

---

## D2 使用说明

- 本文件术语已与 `monthly-day-table.md` 和 `quote-index.md` 对齐。
- 同名神煞起例不由本 pack 计算，必须调用 `mingli-master.selection.v1` 并交叉官方《协纪辨方书》《星历考原》。
- 所有现实输出必须附“文化参考，非事实判断”。
