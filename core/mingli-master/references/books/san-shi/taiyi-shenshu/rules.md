---
slug: taiyi-shenshu
file: rules
---

# 太乙神数 规则集

> 本文件区分确定性盘面事实、古籍关系谓词和历史占例。盘面事实只由 V5.1
> `taiyi-jinjing-annual-yang-board-v1` provider 计算；模型不得手算，也不得把关系谓词直接改写成现代事件结论。
> verified: true；完整公式、版本、哈希与 72 局立成见 `references/matrices/taiyi-source-tables-v1.yaml`。

---

## 第一组：起例（TR-01 ~ TR-08）

### TR-01 推上元积年

- **rule_id**: TR-01
- **scope**: 太乙·起例·积年
- **condition**: 共享历法给出的公元农历年；本发布只支持公元年
- **conclusion**: 采用卷一上元甲子年计；大唐甲子（724）为 1,937,281 算，一算起例，公元换算偏移为 1,936,557
- **source_anchor**: fulltext.md L67-L69
- **verified**: true
- **caveats**: 不与卷二周厉王近元、卷五上元甲寅或后世演纪积年混用

### TR-02 推太岁所在

- **rule_id**: TR-02
- **scope**: 太乙·起例·太岁
- **condition**: 当年干支
- **conclusion**: 太岁在地支所主之宫；占国家事件之"年神"位
- **source_anchor**: 卷一·推太岁所在
- **verified**: true

### TR-03 推入六纪三元

- **rule_id**: TR-03
- **scope**: 太乙·起例·六纪三元
- **condition**: 卷一年计积年
- **conclusion**: 360 年为六纪，每纪 60 年；另以连续五个 72 年段标记五子元（甲子、丙子、戊子、庚子、壬子），72 局内每三年依次理天、理地、理人
- **source_anchor**: fulltext.md L75-L81；L493-L505
- **verified**: true

### TR-04 推太乙所在

- **rule_id**: TR-04
- **scope**: 太乙·起例·所在
- **condition**: 一算起例的积年在 24 年小周中的位置
- **conclusion**: 每三年移一宫，按一、二、三、四、六、七、八、九顺行，不游中五
- **source_anchor**: fulltext.md L79-L81；L310-L321
- **verified**: true

### TR-05 推五将所主

- **rule_id**: TR-05
- **scope**: 太乙·五将
- **condition**: 文昌、始击、太乙三者位置与主客算已经确定
- **conclusion**: 主客大将取算数个位；整十取十位；参将取大将乘三的十进制余数，余零留中五
- **source_anchor**: fulltext.md L314-L316；L348-L351；L493-L505
- **verified**: true
- **caveats**: 只输出将位事实，不自动输出胜负

### TR-06 推九宫所主

- **rule_id**: TR-06
- **scope**: 太乙·九宫
- **condition**: 太乙所在 + 分野
- **conclusion**: 九宫各主一州（一兾 / 二荆 / 三青 / 四徐 / 五豫 / 六雍 / 七梁 / 八兖 / 九雝）
- **source_anchor**: 卷二·推九宫所主法 / 卷八·九宫分野
- **verified**: true
- **caveats**: 古代分野；现代地理无直接对应；仅作文化参考

### TR-07 推八门所主

- **rule_id**: TR-07
- **scope**: 太乙·八门
- **condition**: 太乙所在
- **conclusion**: 开 / 休 / 生为吉；伤 / 死 / 惊为凶；杜门闭、景门半吉
- **source_anchor**: 卷二·推八门所主法
- **verified**: true

### TR-08 推三门具不具

- **rule_id**: TR-08
- **scope**: 太乙·三门
- **condition**: 已计算的太乙、天目与直门位置满足卷四的精确关系
- **conclusion**: 只产生“三门具/不具”的结构化关系谓词和来源，不把古代兵占结论写入事实层
- **source_anchor**: 卷四·推三门具不具
- **verified**: true

---

## 第二组：11 大法 + 太乙诸神（TR-09 ~ TR-12）

### TR-09 11 大法

- **rule_id**: TR-09
- **scope**: 太乙·占断·11 大法
- **condition**: 太乙、文昌、始击、主客四将和门位满足卷三逐条定义的精确位置关系
- **conclusion**: 本 profile 只输出下表中可由年计主盘逐字段验证的掩、囚、格、对子谓词；不得把未具备门位或先后方向数据的击、迫、关、四郭固、四郭杜、执提、提挟伪报为已计算
- **source_anchor**: fulltext.md L428-L470
- **verified**: true
- **caveats**: 谓词不等于现代事件结论；证据仅在相同谓词事实存在时激活

## 年计盘精确关系谓词

以下每条只在 provider 输出同名 `TY-Pxx` 事实时适用。参与字段必须来自同一个
`board_digest`；关系名不构成胜负、灾异或现代事件判断。

### TY-P01 掩

- **rule**: 始击／客目与太乙同位
- **source_chapter**: 卷三·推掩法
- **source_anchor**: fulltext.md L430
- **applicable_to**: 盘面命中 TY-P01

### TY-P02 文昌囚

- **rule**: 天目／文昌与太乙同位
- **source_chapter**: 卷三·推囚法
- **source_anchor**: fulltext.md L442
- **applicable_to**: 盘面命中 TY-P02

### TY-P03 始击格

- **rule**: 始击／客目在太乙对宫
- **source_chapter**: 卷三·推格法
- **source_anchor**: fulltext.md L450
- **applicable_to**: 盘面命中 TY-P03

### TY-P04 文昌对

- **rule**: 天目／文昌在太乙对宫
- **source_chapter**: 卷三·推对法
- **source_anchor**: fulltext.md L454
- **applicable_to**: 盘面命中 TY-P04

### TY-P05 主大将囚

- **rule**: 主大将与太乙同宫
- **source_chapter**: 卷三·推囚法
- **source_anchor**: fulltext.md L442
- **applicable_to**: 盘面命中 TY-P05

### TY-P06 主参将囚

- **rule**: 主参将与太乙同宫
- **source_chapter**: 卷三·推囚法
- **source_anchor**: fulltext.md L442
- **applicable_to**: 盘面命中 TY-P06

### TY-P07 客大将囚

- **rule**: 客大将与太乙同宫
- **source_chapter**: 卷三·推囚法
- **source_anchor**: fulltext.md L442
- **applicable_to**: 盘面命中 TY-P07

### TY-P08 客参将囚

- **rule**: 客参将与太乙同宫
- **source_chapter**: 卷三·推囚法
- **source_anchor**: fulltext.md L442
- **applicable_to**: 盘面命中 TY-P08

### TY-P09 客大将格

- **rule**: 客大将在太乙对宫
- **source_chapter**: 卷三·推格法
- **source_anchor**: fulltext.md L450
- **applicable_to**: 盘面命中 TY-P09

### TY-P10 客参将格

- **rule**: 客参将在太乙对宫
- **source_chapter**: 卷三·推格法
- **source_anchor**: fulltext.md L450
- **applicable_to**: 盘面命中 TY-P10

### TR-10 太乙诸神（君臣民基 + 五福 + 大小游 + 四神 + 天乙地乙直符）

- **rule_id**: TR-10
- **scope**: 太乙·诸神
- **condition**: 各神使用自身声明的卷五积年，不与年计主盘积年混合
- **conclusion**: 计算君基、臣基、民基、五福、大游、小游、四神、天乙、地乙、直符的确定位置与独立 epoch_profile
- **source_anchor**: fulltext.md L595-L759
- **verified**: true
- **caveats**: 古代所主仅作出处标签；位置事实不自动生成国家事件判断

### TR-11 高阶太乙（天皇 / 帝符 / 天时 / 太尊 / 飞鸟 / 五行 / 八风）

- **rule_id**: TR-11
- **scope**: 太乙·高阶诸神
- **condition**: 各神之独立推法
- **conclusion**: 天皇占至尊 / 帝符占符瑞 / 天时占时气 / 太尊占至上 / 飞鸟以鸟象占 / 五行以五行配 / 八风以八方风占
- **source_anchor**: 卷七
- **verified**: false
- **caveats**: 古代国家级占法；现代不构成事实判断

### TR-12 三元五纪立成鉴

- **rule_id**: TR-12
- **scope**: 太乙·速查表
- **condition**: 已知积年
- **conclusion**: 卷五三元五纪立成钤作为四神、天乙、地乙、直符 180 年周期的独立验算表
- **source_anchor**: 卷五
- **verified**: true

---

## 第三组：七术 + 16 推占（TR-13）

### TR-13 太乙七术 + 16 推占法

- **rule_id**: TR-13
- **scope**: 太乙·占法纲领
- **condition**: 已起局
- **conclusion**: 七术（临津问道 / 狮子反掷 / 白云卷空 / 猛虎相拒 / 雷公入水 / 白龙得云 / 回军无言）+ 16 推占（含三才 / 长短缓急 / 五音灾变 / 孤单成败 / 内外攻击 / 多少胜负 / 阴阳厄会 / 所主吉凶 等）
- **source_anchor**: 卷六·太乙七术序
- **verified**: false
- **caveats**: 不在本发布的 annual_macro_historical_board_facts 计算范围；不得借盘面字段伪装已计算

---

## 第四组：兵占与国家占法（TR-14 ~ TR-15，仅文化警示）

### TR-14 古代兵占（卷四 + 卷九）

- **rule_id**: TR-14
- **scope**: 太乙·兵占
- **condition**: 古代军事 / 国家事件
- **conclusion**: 卷四（出师 / 障向 / 置阵 / 风云飞鸟助战 / 奇兵伏兵 / 对阵雲气）+ 卷九（敌国动静 / 敌使虚实 / 间谍 / 敌来方面 / 始击将临二十八舍）皆古代兵占；本 pack 仅作纲领，不展开具体应用
- **source_anchor**: 卷四 / 卷九
- **verified**: false
- **caveats**: ⚠️ 严格仅作文化遗产参考；不可用于现代决策；现代不构成事实判断

### TR-15 古代国家占法（卷十）

- **rule_id**: TR-15
- **scope**: 太乙·国家占法
- **condition**: 古代帝王专用占法（巡狩 / 举贤良 / 太乙择日 / 太乙择时 / 岁中灾发 / 域名厄会 / 飞行四杀 / 九州域名 / 见闻虚实 / 望行人 / 执囚 / 求索）
- **conclusion**: 本 pack 仅作纲领；不展开具体应用
- **source_anchor**: 卷十
- **verified**: false
- **caveats**: ⚠️ 严格仅作文化遗产参考；古代帝王专用；现代不构成事实判断

---

## 第五组：分野（TR-16）

### TR-16 九宫分野

- **rule_id**: TR-16
- **scope**: 太乙·分野
- **condition**: 古代天文地理对应
- **conclusion**: 一兾 / 二荆 / 三青 / 四徐 / 五豫 / 六雍 / 七梁 / 八兖 / 九雝；附绛宫交州 / 明堂益州 / 玉堂幽州
- **source_anchor**: 卷八·九宫分野
- **verified**: false
- **caveats**: ⚠️ 古代分野与现代地理无直接对应；不构成事实判断

---

## 文化警示（全文档级）

- 太乙神数原为古代帝王之占；属古代国家级占法。
- 现代**绝不构成事实判断**。
- 输出涉及"国家事件预测""兵占胜败""灾异预测""帝王占断"时，必须 caveat："文化参考，非事实判断"；古代国家占法仅作文化遗产参考。
- 涉及医疗 / 法律 / 重大决策的占断，须额外提示寻求专业意见。
- 所有年计盘面、主客算和卷五诸神位置由 V5.1 deterministic provider 计算；LLM 不手算。
- 本发布声明范围为 `annual_macro_historical_board_facts`。个人命法、个人事件、现代军事决策、医疗与法律判断不属于该 provider 的能力。
- 关系谓词只能由已验证盘面激活；历史占例不得用作现代结果保证。
