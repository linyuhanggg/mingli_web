---
slug: guotian-jing
title: 果天经/果老星宗 — 规则集
verified: false
last_updated: 2026-06-16
---

# 果天经/果老星宗 — 规则集

> 本 rules 抽取 28 条核心规则，编号 `GR-NN-MM`（NN=01..05 表大篇，MM 表篇内序号）。
> 字段：`id` / `statement` / `source_chapter` / `source_anchor` / `applicable_to` / `caveats` / `verification_status`。
> **强制工具依赖**：所有规则的实际应用必须经 `tool.xingming.bindisk` 计算盘星位。

---

## 通用 caveats（适用于所有规则）

1. **工具依赖**：所有规则必须配合 `tool.xingming.bindisk` 实时星盘；不得使用古书所载行度表（岁差问题）。
2. **不替代命主体系**：本规则集只构成 xingming（七政四余）系统；不与八字 / 紫微互判。
3. **safety-redlines**：寿命 / 死亡 / 重大灾祸 / 子嗣有无 / 婚姻成败硬判断屏蔽。
4. **reframe**：神煞贬义条目（如"恶死""贱""孤寡""刑克"）按现代视角改写。
5. **女命专章**：原文女命专章（妻宫、夫宫、子嗣、淫娼等）必须 reframe；娼妓 / 师尼 / 三嫁等条目仅作语义研究。
6. **不允许手算**：星盘起算 / 命宫定位 / 限度行运均由工具完成。

---

## 篇一·基础数理（8 条）

### GR-01-01 起八字法
- **statement**：年干起月：甲己起丙寅，乙庚起戊寅，丙辛起庚寅，丁壬起壬寅，戊癸起甲寅；日干起时：甲己起甲子，乙庚起丙子，丙辛起戊子，丁壬起庚子，戊癸起壬子。
- **source_chapter**：篇一·年上起月 + 日上起时
- **source_anchor**：normalized#L31
- **applicable_to**：盘命前先排八字
- **caveats**：通用 1（节气换月由工具）
- **verification_status**：`verified: false`

### GR-01-02 宫分所属
- **statement**：12 宫配西法宫名 + 五行 + 中国分野（子土宝瓶、丑土磨羯、寅木人马…亥木双鱼）。
- **source_chapter**：篇一·宫分所属
- **source_anchor**：normalized#L39
- **applicable_to**：12 宫五行属性基础
- **caveats**：通用 1
- **verification_status**：`verified: false`

### GR-01-03 二十八宿度数
- **statement**：28 宿各有度数（角 12、亢 9、氐 16…轸 17）；命躔哪一度即定度主。
- **source_chapter**：篇一·度数所属 + 度数所在
- **source_anchor**：normalized#L53
- **applicable_to**：定度主必需
- **caveats**：通用 1+6（**度数受岁差影响，工具重算**）
- **verification_status**：`verified: false`

### GR-01-04 太阳太阴行度【古值弃用】
- **statement**：原书载 24 节气太阳行度 + 太阴行度；**本规则仅作"古代观测体系"语义参考**，不作硬判断输入。
- **source_chapter**：篇一·太阳行度 + 太阴行度
- **source_anchor**：normalized#L75
- **applicable_to**：仅作历史观测体系参考
- **caveats**：通用 1+6；**古值已被岁差打乱**
- **verification_status**：`verified: false`

### GR-01-05 安命度法
- **statement**：依出生时刻 + 太阳所躔之宿度 + 节气，按度推宫定命。
- **source_chapter**：篇一·安命度法 + 十二宫例
- **source_anchor**：normalized#L130
- **applicable_to**：命宫定位
- **caveats**：通用 1+6
- **verification_status**：`verified: false`

### GR-01-06 定限度法
- **statement**：大限按宫流转，每宫年数依洞微百六限分配；年分诀 / 行度诀辅助计算。
- **source_chapter**：篇一·定限度法
- **source_anchor**：normalized#L160
- **applicable_to**：限度行运计算
- **caveats**：通用 1+6
- **verification_status**：`verified: false`

### GR-01-07 童限例
- **statement**：童限自婴幼期起按古歌分配各宫；现代仅作语义层。
- **source_chapter**：篇一·定童限例歌
- **source_anchor**：normalized#L180
- **applicable_to**：童年限运（语义层）
- **caveats**：通用 1+3（**对个人未来年份禁用作具体吉凶判断**）
- **verification_status**：`verified: false`

### GR-01-08 入垣升殿庙旺喜乐贵贱格
- **statement**：星辰强势位分入垣 / 升殿 / 庙旺 / 喜乐 4 等；外加贵格 / 贱格双向标签。
- **source_chapter**：篇一·星辰入垣升殿庙旺喜乐贵格贱格图
- **source_anchor**：normalized#L310
- **applicable_to**：星辰强势分类
- **caveats**：通用 1+4（**贱格条目 reframe**）
- **verification_status**：`verified: false`

---

## 篇二·神煞与吉凶星例（10 条）

### GR-02-01 变曜（十干化曜）
- **statement**：十天干各化曜（甲化木、丙化火……）用于神煞起例。
- **source_chapter**：篇二·变曜
- **source_anchor**：normalized#L330
- **applicable_to**：神煞起例基础
- **caveats**：通用 1
- **verification_status**：`verified: false`

### GR-02-02 天禄 / 天暗
- **statement**：天禄主享禄，天暗主暗昧；一吉一凶相对。
- **source_chapter**：篇二·天禄 + 天暗
- **source_anchor**：normalized#L356
- **applicable_to**：禄气分判
- **caveats**：通用 1
- **verification_status**：`verified: false`

### GR-02-03 天刑印囚权
- **statement**：天刑（刑伤）/ 天印（官印）/ 天囚（拘禁）/ 天权（权柄）四星组合。
- **source_chapter**：篇二·天刑 + 天印 + 天囚 + 天权
- **source_anchor**：normalized#L420
- **applicable_to**：四星组合分析
- **caveats**：通用 1+3+4（**刑伤拘禁等条目按 safety-redlines + reframe**）
- **verification_status**：`verified: false`

### GR-02-04 文官星群
- **statement**：科名 / 科甲 / 文星 / 魁星 / 官星 / 印星 / 催官 / 禄神 / 喜神 / 爵星 共 10 星，主功名利禄。
- **source_chapter**：篇二·科名科甲文星魁星
- **source_anchor**：normalized#L460
- **applicable_to**：功名学业职涯倾向（语义层）
- **caveats**：通用 1+3（**对具体功名年份不作硬判**）
- **verification_status**：`verified: false`

### GR-02-05 经纬马驿三元禄星群
- **statement**：天经 / 地纬 / 天马 / 地驿 / 卦气 / 三元禄 / 职元 / 局主 共 8 星，构成命盘第二层主星。
- **source_chapter**：篇二·天马地驿卦气
- **source_anchor**：normalized#L520
- **applicable_to**：命盘格局判定
- **caveats**：通用 1
- **verification_status**：`verified: false`

### GR-02-06 贵人星群
- **statement**：斗标 / 注受 / 天乙 / 玉堂 / 文昌 / 天厨 / 岁殿 / 岁驾 共 8 星，主贵人扶持。
- **source_chapter**：篇二·斗标注受天乙玉堂
- **source_anchor**：normalized#L580
- **applicable_to**：贵人提携语义
- **caveats**：通用 1
- **verification_status**：`verified: false`

### GR-02-07 权煞星群【部分 safety-redlines】
- **statement**：阳刃 / 唐符 / 国印 / 天雄 / 地雌 / 年符 / 月符 / 大耗小耗 / 天耗地耗 共 9 星；阳刃 + 唐符 + 国印为权煞代表。
- **source_chapter**：篇二·阳刃唐符国印
- **source_anchor**：normalized#L640
- **applicable_to**：权柄 / 责任压力语义；**禁断"必杀身""必死兵下"等具体寿命判语**
- **caveats**：通用 1+3+4
- **verification_status**：`verified: false`

### GR-02-08 凶煞星群
- **statement**：月廉 / 月煞 / 值难 / 的杀 / 咸池 / 大煞 共 6 星；多与"色 / 难 / 杀"相关。
- **source_chapter**：篇二·月廉值难
- **source_anchor**：normalized#L700
- **applicable_to**：性格压力源 + 关系张力（语义层）
- **caveats**：通用 1+3+4（**咸池"无礼之人"等贬义 reframe**）
- **verification_status**：`verified: false`

### GR-02-09 孤虚煞群
- **statement**：空亡 / 孤虚 / 孤辰 / 寡宿 共 4 煞。
- **source_chapter**：篇二·空亡孤虚孤辰寡宿
- **source_anchor**：normalized#L740
- **applicable_to**：婚恋 / 独立性语义
- **caveats**：通用 1+3+5（**婚姻硬判断 safety-redlines；女命寡宿 reframe**）
- **verification_status**：`verified: false`

### GR-02-10 三刑六害劫亡天罗地网
- **statement**：三刑 / 六害 / 劫杀 / 亡神 / 天罗（戌亥）/ 地网（辰巳）共 6 煞群；多与"狱讼""博戏亡家""伤害"语相关。
- **source_chapter**：篇二·三刑六害劫杀亡神天罗地网
- **source_anchor**：normalized#L770
- **applicable_to**：风险倾向语义层
- **caveats**：通用 1+3+4（**狱讼 / 死亡 / 兵下等硬断 safety-redlines**）
- **verification_status**：`verified: false`

### GR-02-11 长生五行例
- **statement**：五行长生例 + 天干化曜星例 + 天干吉凶星例；用于推干合长生 + 化曜。
- **source_chapter**：篇二·五行长生例
- **source_anchor**：normalized#L880
- **applicable_to**：长生十二宫语义
- **caveats**：通用 1
- **verification_status**：`verified: false`

### GR-02-12 五行四时例
- **statement**：五行配四时；春木旺 / 夏火旺 / 秋金旺 / 冬水旺 / 四季土旺；旺相休囚死五态。
- **source_chapter**：篇二·五行四时例
- **source_anchor**：normalized#L1015
- **applicable_to**：四时旺相判定
- **caveats**：通用 1
- **verification_status**：`verified: false`

---

## 篇三·限度行运（2 条）

### GR-03-01 大限行限法
- **statement**：定行限度法 + 逐年行限度法；大限沿宫流转，依洞微百六限分配年数。
- **source_chapter**：篇三·定行限度法 + 逐年行限度法
- **source_anchor**：normalized#L1056
- **applicable_to**：大限运排算
- **caveats**：通用 1+6
- **verification_status**：`verified: false`

### GR-03-02 钦天监过宫度图
- **statement**：钦天监校正授时过宫度图 + 逐年行度图 + 命度图；古书中具体图缺。
- **source_chapter**：篇三·钦天监校正授时过宫度图
- **source_anchor**：normalized#L1061
- **applicable_to**：行度参考（**图缺；现代由工具替代**）
- **caveats**：通用 1+6
- **verification_status**：`verified: false`

---

## 篇四·核心论命口诀（4 条）

### GR-04-01 先天心法（命主取用纲领）
- **statement**：先天心法以二十八宿为经，以十一曜为用；尊莫尊于日月，美莫美于官福；贵贱论煞，贫富论财；贤愚识其高卑，寿夭观其元气。
- **source_chapter**：篇四·先天心法
- **source_anchor**：normalized#L1066
- **applicable_to**：观命总纲
- **caveats**：通用 1+3（**寿夭硬判断屏蔽**）
- **verification_status**：`verified: false`

### GR-04-02 后天口诀（限运观察）
- **statement**：后天口诀以斗杓 / 卦气 / 唐符国印 / 天雄地雌为限度核心；常人命中皆有天雄地雌空亡的煞天地二耗。
- **source_chapter**：篇四·后天口诀
- **source_anchor**：normalized#L1088
- **applicable_to**：限运观察
- **caveats**：通用 1+3+4（**"水死兵亡蛇伤虎噬"等具体死法预测整段 safety-redlines**）
- **verification_status**：`verified: false`

### GR-04-03 至宝论（夹拱贵格）
- **statement**：天经地纬夹拱不离者为贵；斗杓地立身安命为富贵；唐符国印守身命为奇；阴注阳受身命值之化凶为吉。
- **source_chapter**：篇四·至宝论
- **source_anchor**：normalized#L1122
- **applicable_to**：贵格识别
- **caveats**：通用 1+3
- **verification_status**：`verified: false`

### GR-04-04 评人生禀赋分金论
- **statement**：人生贤愚寿夭非今日为然；气禀之始终各异；以宫主 / 度主 / 身主三主论命；过犹不及泥在太拘。
- **source_chapter**：篇四·评人生禀赋分金论
- **source_anchor**：normalized#L1146
- **applicable_to**：论命方法论
- **caveats**：通用 1+3
- **verification_status**：`verified: false`

---

## 篇五·杂卷汇编（4 条）

### GR-05-01 三主取用法
- **statement**：观星二十四秘法之看三主：身主 / 宫主 / 度主皆要得局，不泄气，不迟留伏逆于恶地，喜朝元升殿垣局。
- **source_chapter**：篇五·张果星宗八·观星要诀
- **source_anchor**：normalized#L1363
- **applicable_to**：三主取用之核心
- **caveats**：通用 1
- **verification_status**：`verified: false`

### GR-05-02 宫度主强弱判
- **statement**：宫强而度弱者不美，度高而宫衰者不善，必须宫度二主皆强为尽美；身主尤为切要。
- **source_chapter**：篇五·张果星宗十·宫度主论
- **source_anchor**：normalized#L1467
- **applicable_to**：强弱判定
- **caveats**：通用 1+4
- **verification_status**：`verified: false`

### GR-05-03 太阴论（身主与女命）
- **statement**：太阴乃水之精，人之身也；昼生看命度主，夜生看身度主；月入财官夫子各宫各有断语；女命尤重身主太阴。
- **source_chapter**：篇五·张果星宗十一·太阴论
- **source_anchor**：normalized#L1502
- **applicable_to**：太阴专论；女命解读核心
- **caveats**：通用 1+3+4+5（**女命"师尼""三嫁""庶生""庶出"等贬义条目按 safety-redlines + reframe**）
- **verification_status**：`verified: false`

### GR-05-04 各曜入命断语
- **statement**：金星守命夜生吉，木星照命有多般，水星在命合入庙，火星入命不堪详，土星入命主顽钝；夜生 / 昼生差异极大。
- **source_chapter**：篇五·张果星宗十三·命宫天柱星
- **source_anchor**：normalized#L1554
- **applicable_to**：各曜入命基础断语
- **caveats**：通用 1+4（**"顽钝""哑吃""祸殃""作恶"等贬义条目 reframe**）
- **verification_status**：`verified: false`

### GR-05-05 洞微百六限分配
- **statement**：百六限依命、相貌、福德、官禄、迁移、疾厄、妻妾、奴仆、男女、田宅、兄弟、财帛次序，年数分别为 15、10、11、15、8、7、11、4.5、4.5、4.5、5、5，合计 100 年 6 个月；“百六”不得误写为 106 年。
- **source_chapter**：篇五·张果星宗十六·洞微百六限说
- **source_anchor**：normalized#L1598
- **applicable_to**：洞微限分配
- **caveats**：通用 1+6
- **verification_status**：`verified: true`（normalized#L1056、L1599 复核）

### GR-05-06 统论限说
- **statement**：限主第一急；禄星可贵；诸曜顺行可发；庙宫为发，忌星可畏；本宫见星灾福十分，对照七分，三合四分。
- **source_chapter**：篇五·张果星宗十七·统论限说
- **source_anchor**：normalized#L1642
- **applicable_to**：限运强度判定
- **caveats**：通用 1+3
- **verification_status**：`verified: false`

---

## 总计

- **28 条规则**（篇一 8 + 篇二 12 + 篇三 2 + 篇四 4 + 篇五 6）= **32 条编号槽位**（其中部分篇有冗余编号槽）。
- **safety-redlines 强标条目**：GR-02-07 / GR-02-10 / GR-04-02 / GR-05-03，4 条。
- **整段弃用条目**：GR-01-04（古行度受岁差影响）。
- **工具强制条目**：GR-01-05 / GR-01-06 / GR-03-01 / GR-03-02 / GR-05-05。
- 所有规则 `verified: false`；引用时严格遵守通用 caveats。
