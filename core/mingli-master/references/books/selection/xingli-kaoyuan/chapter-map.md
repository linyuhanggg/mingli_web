# 御定星历考原 — Chapter Map

> D2 全书章节地图。`digest_status=done` 表示本 reference pack 已覆盖该单元到可蒸馏层；`verified=false` 表示尚未对四库影印逐页校勘。
> 底本为维基文库《御定星历考原（四库全书本）》本地规范化文本。

## Source Root

- 维基文库：https://zh.wikisource.org/zh-hans/御定星歷考原_(四庫全書本)
- CTP 锚点：https://ctext.org/wiki.pl?if=gb&res=403679
- 本地规范化文本：`references/fulltext/selection/xingli-kaoyuan/fulltext.md`

## Front Matter

| slug | title | digest_status | function | source_anchor | verified | notes |
|---|---|---|---|---|---|---|
| front/tiyao | 四库提要 | done | 说明本书奉敕重定、六目结构、神煞说源流与删汰诸家的编纂宗旨。 | fulltext.md L3-L16 | false | quote-index.md XK-Q001~XK-Q006 |

## Six Volumes

| slug | title | digest_status | function | source_anchor | verified | notes |
|---|---|---|---|---|---|---|
| vol-01-xiangshu | 卷一·象数考原 | done | 天地、五纪、八卦、五行、干支、月建、方位、节气、闰月、纳音、二十八宿、五虎遁、五鼠遁、三合五合六合等基础原理。 | fulltext.md L20-L295 | false | quote-index.md；rules.md |
| vol-02-nianshen | 卷二·年神方位 | done | 三元年九星、岁干合、岁德合、太岁、博士、力士、蚕室、太阴、大将军、岁刑岁破、金神等年神方位。 | fulltext.md L296-L471 | false | quote-index.md；rules.md |
| vol-03-yueji | 卷三·月事吉神 | done | 天道、天德、月德、天德合、月空、天赦、母仓、月恩、生气、驿马、六合、三合、解神、六仪等月事吉神。 | fulltext.md L472-L681 | false | quote-index.md；rules.md |
| vol-04-yuexiong | 卷四·月事凶神 | done | 月建、月破、月杀、月害、独火、月虚、大耗、小耗、四废、四离、四绝、官符、天贼等月事凶神。 | fulltext.md L682-L911 | false | quote-index.md；rules.md |
| vol-05-rishi | 卷五·日时总类 | done | 月建十二神、黄黑二道、喜神、二十八宿配日、空亡、三伏、二社、得辛、人神、太白游方、阴阳大会小会等日时总类。 | fulltext.md L912-L1193 | false | quote-index.md；rules.md |
| vol-06-yongshi | 卷六·用事宜忌 | done | 选择总论及祭祀、祈福、修造、移徙、安床、纳采、嫁娶、求嗣、出行、开市、安葬等用事宜忌。 | fulltext.md L1194-L1404 | false | quote-index.md；rules.md |

## Counts

- **chapter_count_total**：7（提要 1 + 正文 6 卷）
- **chapter_count_done**：7
- **chapter_count_partial**：0
- **chapter_count_pending**：0
- **chapter_count_skipped**：0
- **chapter_count_unavailable**：0

## Notes

- 卷六正确末行是 `fulltext.md L1404`，不得引用 line 1405。
- 本书是官方“考原”层，后续择日 skill 中优先级高于民间通书层。
- 具体日期、时辰、神煞落点必须由 `mingli-master.selection.v1` 计算，本 pack 只提供考源与规则证据。
