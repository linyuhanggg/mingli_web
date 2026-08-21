# 董公择日 — Chapter Map

> D2 全书章节地图。底本为本地规范化文本 `references/fulltext/selection/donggong-zeri/fulltext.md`，来源记录见 `sources/manifests/donggong-zeri.yaml`。
> 字段：`slug` / `title` / `digest_status` / `function` / `source_anchor` / `verified` / `notes`。
> `digest_status=done` 表示该章节已被本 reference pack 覆盖到可蒸馏层；`verified=false` 表示尚未对国图影印逐页校勘。

## 来源根

- 规范化文本：`references/fulltext/selection/donggong-zeri/fulltext.md`
- 维基文库整理文本：https://zh.wikisource.org/wiki/%E8%91%A3%E5%85%AC%E9%81%B8%E8%A6%81%E8%A6%BD
- 国图藏本 Wikimedia Commons 镜像：https://upload.wikimedia.org/wikipedia/commons/8/87/NLC416-12jh005366-44510

---

## 序跋（2 小目）

| slug | title | digest_status | function | source_anchor | verified | notes |
|---|---|---|---|---|---|---|
| `front/lue-ji` | 董公选择要览略记 | done | 蒋奇峰所录唐大师正一书略记；介绍董德彰其人与本书来历。 | fulltext.md L19 | false | quote-index.md DG-Q001~DG-Q002 |
| `front/lunlue-shisanze` | 蒋奇峰董书论略十三则摘要 | done | 蒋奇峰摘要十三则论略，阐述本书来历、择日选时总纲与中宫煞避忌。 | fulltext.md L26 | false | quote-index.md DG-Q003~DG-Q006；rules.md DR-01 |

## 月份吉凶日（12 小目）

| slug | title | digest_status | function | source_anchor | verified | notes |
|---|---|---|---|---|---|---|
| `month/01-yin` | 正月 寅月 | done | 正月（寅月）12 建除日宜忌。 | fulltext.md L49 | false | monthly-day-table.md DG-D001~DG-D012 |
| `month/02-mao` | 二月 卯月 | done | 二月（卯月）12 建除日宜忌。 | fulltext.md L107 | false | monthly-day-table.md DG-D013~DG-D024 |
| `month/03-chen` | 三月 辰月 | done | 三月（辰月）12 建除日宜忌。 | fulltext.md L166 | false | monthly-day-table.md DG-D025~DG-D036 |
| `month/04-si` | 四月 巳月 | done | 四月（巳月）12 建除日宜忌。 | fulltext.md L231 | false | monthly-day-table.md DG-D037~DG-D048 |
| `month/05-wu` | 五月 午月 | done | 五月（午月）12 建除日宜忌。 | fulltext.md L289 | false | monthly-day-table.md DG-D049~DG-D060 |
| `month/06-wei` | 六月 未月 | done | 六月（未月）12 建除日宜忌。 | fulltext.md L348 | false | monthly-day-table.md DG-D061~DG-D072 |
| `month/07-shen` | 七月 申月 | done | 七月（申月）12 建除日宜忌。 | fulltext.md L409 | false | monthly-day-table.md DG-D073~DG-D084 |
| `month/08-you` | 八月 酉月 | done | 八月（酉月）12 建除日宜忌。 | fulltext.md L474 | false | monthly-day-table.md DG-D085~DG-D096 |
| `month/09-xu` | 九月 戌月 | done | 九月（戌月）12 建除日宜忌。 | fulltext.md L542 | false | monthly-day-table.md DG-D097~DG-D108 |
| `month/10-hai` | 十月 亥月 | done | 十月（亥月）12 建除日宜忌。 | fulltext.md L612 | false | monthly-day-table.md DG-D109~DG-D120 |
| `month/11-zi` | 十一月 子月 | done | 十一月（子月）12 建除日宜忌。 | fulltext.md L671 | false | monthly-day-table.md DG-D121~DG-D132 |
| `month/12-chou` | 十二月 丑月 | done | 十二月（丑月）12 建除日宜忌。 | fulltext.md L733 | false | monthly-day-table.md DG-D133~DG-D144 |

## 神煞与吉日歌诀（3 小目）

| slug | title | digest_status | function | source_anchor | verified | notes |
|---|---|---|---|---|---|---|
| `appendix/jinshen-qisha-ge` | 金神七煞歌 | done | 金神七煞日的口诀与避忌。 | fulltext.md L794 | false | quote-index.md DG-Q151 |
| `appendix/sha-gong-zhi-xing-ren-zhuan` | 煞贡、直星、人专吉日 | done | 煞贡日、直星日、人专吉日三类吉日的取法与使用。 | fulltext.md L798 | false | quote-index.md DG-Q152~DG-Q153 |
| `appendix/zeri-xuanshi-gejue` | 董公择日选时歌诀 | done | 选时择时口诀、遁时法、偷修吉日、喜神财神与诸忌日汇总。 | fulltext.md L817 | false | quote-index.md DG-Q154~DG-Q156；procedures.md DP-02 |

---

## 说明

- 本书无官方卷次结构；按“序跋 / 月份 / 神煞歌诀”三大块归类，共 17 个章节条目。
- 12 个月 144 个建除日条目已完整抽入 `monthly-day-table.md`；短引均以本地 `fulltext.md` exact-match 为准。
- `done` 是蒸馏覆盖状态，不代表版本学定本。因民间通书传本异文多，所有章节 `verified=false`，后续仍需国图影印逐页校勘。
- 涉及具体公历/农历日期的吉凶查询，必须由 `mingli-master.selection.v1` 换算干支；本 pack 只提供历史文本证据与民间口径对照。
