# 冰鉴 — Chapter Map

> 全书 9 节（7 篇正文 + 序 + 跋），按 normalized 行号锚定。D2 状态口径：digest_status=done 表示该单元已进入 chapter-map，并已完成原文证据覆盖或序跋版本标注；verified=false 表示尚未完成清刊本影印逐字复核。
> 字段：`slug` / `title` / `digest_status` / `function` / `source_anchor` / `verified` / `notes`。
> `digest_status` 取值：`done` / `partial` / `pending` / `skipped` / `unavailable`。
> `verified` 现阶段全部 `false`（清刊本影印未对校）。

## 来源根

- 维基文库：https://zh.wikisource.org/wiki/冰鑑
- 本地 normalized：`references/fulltext/physiognomy/bingjian/fulltext.md`

---

## 章节地图（9 条）

| slug | title | digest_status | function | source_anchor | verified | notes |
|---|---|---|---|---|---|---|
| `xu/jianshalvxu` | 民國簡沙侶抄簡熙堯校本序 | done | 整理者序，记述抄录缘起；与本书内容无关，但用于版本溯源。 | normalized#L13 | false | 不抽规则；只在 quote-index 给版本溯源短引 |
| `01-shengu` | 神骨章第一 | done | 全书纲领：开门见山，文人观人先看神与骨；论清浊邪正、骨九起、骨色骨质。 | normalized#L17 | false | rules.md BR-01-xx；术语：神、骨、清浊、九起 |
| `02-gangrou` | 剛柔章第二 | done | 五行生克为外刚柔；喜怒伏跳深浅为内刚柔。论顺合逆合与"金形带火"等。 | normalized#L29 | false | rules.md BR-02-xx；术语：内外刚柔、顺合逆合 |
| `03-rongmao` | 容貌章第三 | done | 容貴整、貌合两仪；论身形整齐五短两大；科名星 / 阴骘纹之类隐显气象。 | normalized#L35 | false | rules.md BR-03-xx；含贬义"舌脱无官、橘面不显"需 reframe |
| `04-qingtai` | 情態章第四 | done | 情态四分（弱 / 狂 / 疏懒 / 周旋），论恒态与时态、人物气质画像。 | normalized#L45 | false | rules.md BR-04-xx；本章在现代相术教学最常被引 |
| `05-xumei` | 鬚眉章第五 | done | 论须眉为男子标志；眉之"彩"层、须之多寡清健；如剑如帚之高下。 | normalized#L53 | false | rules.md BR-05-xx；女命相术不在本书范围 |
| `06-shengyin` | 聲音章第六 | done | 声主张、音主敛；声雄声雌、远近起止、上品与下品的辨听。 | normalized#L59 | false | rules.md BR-06-xx；含贬义"市井之夫"需 reframe |
| `07-qise` | 氣色章第七 | done | 面部如命、气色如运；论终身年月日四级气色与色之忌（白青）。 | normalized#L67 | false | rules.md BR-07-xx；不抽寿命相关判断 |
| `ba/wurongguangba` | 清吳榮光中丞跋 | done | 中丞跋，赞本书"非同泛书"；用于版本与流传线索。 | normalized#L77 | false | 不抽规则；只在 quote-index 给版本溯源短引 |

---

## 章节统计

- 正文 7 篇：神骨 / 刚柔 / 容貌 / 情态 / 须眉 / 声音 / 气色
- 序跋 2 节：简沙侣序 / 吴荣光跋
- **总计**：**9 节**

详细覆盖率统计见 [validation.md](./validation.md)。
