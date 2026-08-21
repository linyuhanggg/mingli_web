# 《六壬指南 / 六壬指南注解》Chapter Map

> 行号一律指 `references/fulltext/san-shi/liuren-zhiyin/fulltext.md`。`mapped` 只表示结构已定位，不表示已与 NLC 影印逐页校勘。L1-L29、L44-L49、L598-L603、L852-L857、L2444-L2449 是 normalized 包装层，不能当作书中引文。

## Source-layer codes

| code | meaning |
|---|---|
| `annotated_edition_heading` | 注本卷题、章题和目录标题，只作结构证据 |
| `old_preface_attribution` | 旧序对陈公献、庄公远内容归属的书目证言 |
| `original_text` | 先贤《心印赋》《指掌赋》的赋文短句，作者不强定 |
| `chen_gongxian_content` | 陈公献旧注、《会纂》分门占法与旧占验 |
| `zhuang_gongyuan_content` | 旧序归庄公远的《神煞图位》及卷末辨讹层 |
| `zhang_hong_modern_annotation` | 张洪自序、简注、史注和编辑说明 |
| `modern_case` | 注本所收现代增补课例 |
| `modern_weifang_case` | 明示潍坊或现代机关语境的课例 |
| `annotated_comment_unattributed` | 电子注本题下注，现阶段不能稳归作者 |

## Front matter

| id | normalized lines | semantic unit | source layer | status | notes |
|---|---|---|---|---|---|
| `F-01` | L30-L31 | 注本题名、卷首语 | `zhang_hong_modern_annotation` | mapped | 不是陈公献原序；L31含现代师承叙述 |
| `F-02` | L32-L37 | 注本目录 | `zhang_hong_modern_annotation` | mapped | 目录只能作注本结构证据 |
| `F-03` | L38-L39 | 张洪自序及署名 | `zhang_hong_modern_annotation` | mapped | 明示“简注”“参己意”“少许实例” |
| `F-04` | L40 | 周元曙原序 | `old_preface_attribution` | mapped | 叙述陈公献增注两赋、成《会纂》 |
| `F-05` | L41 | 程起鸾原序 | `old_preface_attribution` | mapped | 明示陈公献两赋旧注、会纂及庄公远神煞图位 |
| `F-06` | L42 | 地名、月名现代释语 | `zhang_hong_modern_annotation` | mapped | 不作古序正文 |

## 卷一：心印赋语义段

| id | normalized lines | semantic unit | source layers | status | notes |
|---|---|---|---|---|---|
| `J1-00` | L50-L51 | 卷题与同名《心印赋》辨别 | `zhang_hong_modern_annotation` | mapped | L51 是注本辨名，不是赋文 |
| `J1-01` | L52-L83 | 入式、月将加时、四课、九宗门取用 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 核心取用决策树证据区 |
| `J1-02` | L84-L368 | 天乙贵人及十二天将临十二宫象 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 赋句与旧注、现代经验交错，不可整段称原文 |
| `J1-03` | L369-L462 | 课体、卦名、格局与附义 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 元首至五行局等格局层 |
| `J1-04` | L463-L517 | 十二支类神、事类与分占纲要 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 类象须回到占类和课传，不独断 |
| `J1-05` | L518-L554 | 旺相休囚、孟仲季、五行乘临与神将顺逆 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 解释层，不替代取用层 |
| `J1-06` | L555-L565 | 日辰彼我、初末传与先后吉凶 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 主客与过程层 |
| `J1-07` | L566-L596 | 占时先锋、克生多寡与通变收束 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 需确定性排盘字段 |

## 卷二：指掌赋语义段

| id | normalized lines | semantic unit | source layers | status | notes |
|---|---|---|---|---|---|
| `J2-00` | L604-L605 | 卷题与题名释义 | `zhang_hong_modern_annotation` | mapped | L605 为注本释题 |
| `J2-01` | L606-L651 | 四课、九宗门、内外战、事在日前后 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 与卷一取用互证，不另造算法 |
| `J2-02` | L652-L700 | 日辰互临、乱首赘婿、交生交克、度厄等附卦 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 课体解释层 |
| `J2-03` | L701-L751 | 玄胎、三交、游子、天网天狱、三光三阳、八迍五福 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 多为课名组合条件 |
| `J2-04` | L752-L769 | 四季、四仲顺逆传的时令名义 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 不等同日历计算 |
| `J2-05` | L770-L777 | 初中末三传的发端、移易、归计与生克 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 过程判断核心 |
| `J2-06` | L778-L788 | 三间、顺逆连茹十二局 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 须由 adapter 给出连茹结构 |
| `J2-07` | L789-L816 | 进退气、空亡、交车、合害与主客关系 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 不可凭单一空亡机械下断 |
| `J2-08` | L817-L829 | 既定课传后再观十二天将与支神组合 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 明确解释次序 |
| `J2-09` | L830-L836 | 天时、宅人、病狱、婚胎、财官等分类入口 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 仅作问题路由，不作现实保证 |
| `J2-10` | L837-L839 | 州野、宅舍、人物、身体类象 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 医病内容只作历史文本研究 |
| `J2-11` | L840-L850 | 占时来情与全赋总断 | `original_text` + `chen_gongxian_content` + 张洪增注 | mapped | 最终仍以课传结构为主 |

## 卷三：会纂占验章节

| chapter | normalized lines | title | primary layer | embedded modern layers |
|---:|---|---|---|---|
| 1 | L859-L861 | 总论 | `zhang_hong_modern_annotation` | 合卷、二十九章、史注说明均属现代编辑层 |
| 2 | L862-L928 | 天时 | `chen_gongxian_content` | 张洪注释与史注；L876 明署“张注” |
| 3 | L929-L948 | 阳宅 | `chen_gongxian_content` | 张洪注释 |
| 4 | L949-L964 | 阴地 | `chen_gongxian_content` | 张洪注释 |
| 5 | L965-L972 | 迁移 | `chen_gongxian_content` | 张洪注释 |
| 6 | L973-L974 | 香火 | `chen_gongxian_content` | 张洪注释 |
| 7 | L975-L1016 | 婚姻 | `chen_gongxian_content` | L997-L1016 为现代增补课例 |
| 8 | L1017-L1078 | 孕产 | `chen_gongxian_content` | 张洪注释 |
| 9 | L1079-L1168 | 疾病 | `chen_gongxian_content` | L1159-L1168 为现代增补课例 |
| 10 | L1169-L1213 | 出行 | `chen_gongxian_content` | L1194-L1213 为现代增补课例；L1212 明示潍坊 |
| 11 | L1214-L1297 | 行人 | `chen_gongxian_content` | L1280-L1297 为现代增补课例 |
| 12 | L1298-L1303 | 趋谒 | `chen_gongxian_content` | 张洪注释 |
| 13 | L1304-L1403 | 选举 | `chen_gongxian_content` | 张洪史注 |
| 14 | L1404-L1419 | 武举 | `chen_gongxian_content` | 张洪注释 |
| 15 | L1420-L1813 | 仕宦 | `chen_gongxian_content` | 大量张洪史注和复盘，不得整章称陈公献原断 |
| 16 | L1814-L1839 | 求财 | `chen_gongxian_content` | L1821-L1839 为现代增补课例；L1831 明示潍坊工商局 |
| 17 | L1840-L1884 | 买卖 | `chen_gongxian_content` | 张洪注释 |
| 18 | L1885-L2014 | 占讼 | `chen_gongxian_content` | 张洪注释与史注 |
| 19 | L2015-L2038 | 隐遁 | `chen_gongxian_content` | 张洪注释 |
| 20 | L2039-L2050 | 逃亡 | `chen_gongxian_content` | 张洪注释 |
| 21 | L2051-L2079 | 贼盗 | `chen_gongxian_content` | 张洪注释 |
| 22 | L2080-L2083 | 田蚕 | `chen_gongxian_content` | 张洪注释 |
| 23 | L2084-L2094 | 六畜 | `chen_gongxian_content` | 张洪注释 |
| 24 | L2095-L2136 | 应候 | `chen_gongxian_content` | 张洪注释 |
| 25 | L2137-L2161 | 岁占 | `chen_gongxian_content` | 张洪史注 |
| 26 | L2162-L2196 | 射覆 | `chen_gongxian_content` | L2179-L2196 为现代增补课例 |
| 27 | L2197-L2213 | 钦差 | `chen_gongxian_content` | 张洪史注 |
| 28 | L2214-L2300 | 章奏 | `chen_gongxian_content` | 张洪史注 |
| 29 | L2301-L2430 | 兵斗 | `chen_gongxian_content` | 张洪史注；此处结束其自称的二十九章 |
| 30 | L2431-L2442 | 三合 | `zhang_hong_modern_annotation` | L2434-L2442 是 `modern_weifang_case`；与 L860“列为二十九章”冲突，按现代附录异常处理 |

## 卷之四：神煞层

| id | normalized lines | semantic unit | source layers | use gate |
|---|---|---|---|---|
| `J4-00` | L2450 | 卷题 | `annotated_edition_heading` | 不作规则 |
| `J4-01` | L2451-L2532 | 神煞全图说明及月、年、日、支表 | `zhuang_gongyuan_content` 候选 + `annotated_comment_unattributed` | 必须先有完整课盘；表格字形待影印复核 |
| `J4-02` | L2533-L2561 | 岁煞 | 庄氏图歌层 + 张洪注释 | 盘后辅证 |
| `J4-03` | L2562-L2753 | 月煞、季煞及月例歌 | 庄氏图歌层 + 张洪注释 + `modern_case` | L2580-L2592、L2627-L2638 为 1998 年现代课例 |
| `J4-04` | L2754-L2757 | 旬煞 | 庄氏图歌层 + 注本解释 | 盘后辅证 |
| `J4-05` | L2758-L2779 | 干煞 | 庄氏图歌层 + 注本解释 | 盘后辅证；L2767 明署“庄按” |
| `J4-06` | L2780-L2796 | 支煞、刑冲合害及天时支煞 | 庄氏图歌层 + 注本解释 | 盘后辅证 |
| `J4-07` | L2797-L2798 | 神煞辨讹与旋图用法 | `zhuang_gongyuan_content` + 题下注 | 版本辨异，不作为无条件事实 |

## 卷次与章数异常

- L860 说张洪把“原书卷三、卷四合而为一，列为二十九章”；L2431 却出现“三合章第三十”。本包把 1-29 章作为张洪声明的合卷主体，把第 30 章作为现代附录异常。
- L910 的注语仍称“卷五神煞指南”，而 CTP 容器题为“卷之四”。这支持“旧卷三、四合并后旧卷五改列当前卷四”的解释，但在 NLC 全本逐页校勘前只记为版本映射假说。
- `chapter-map.md` 的 line range 是检索锚点，不是 NLC 页码；不得伪造页码互换。
