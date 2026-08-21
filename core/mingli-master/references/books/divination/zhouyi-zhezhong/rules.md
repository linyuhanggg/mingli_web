# 御纂周易折中 — Rules

> 本文件抽取《御纂周易折中》义理 + 象数判断原则。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `applicable_to` / `caveats` / `verification_status`。
> 全部 `pending_verification`。
> rule_id 前缀 `ZZR` = ZheZhong Rule。
> 重点：解卦义理之普遍原则；非卜筮装卦操作（操作转 `zengshan-buyi`）。

---

### ZZR-M001 八卦重为六十四卦

- **rule_statement**：八卦相重，每一重卦具六爻，由此形成六十四卦体系。
- **source_chapter**：卷首/卦爻总论
- **applicable_to**：provider 已确定本卦的梅花盘
- **caveats**：仅作重卦结构方法，不授权卦意吉凶。
- **verification_status**：verified

## 一、爻位判断（义例核心）

### ZZR-01-01 当位为正

- **rule_statement**：阳爻居阳位（初三五）、阴爻居阴位（二四上）为"当位"；当位则正，多吉。
- **source_chapter**：vol-00/yi-li
- **applicable_to**：所有解卦
- **caveats**：当位非必然吉；尚需看爻之时位与应。
- **verification_status**：pending_verification

### ZZR-01-02 中位为贵

- **rule_statement**：二爻居下卦中、五爻居上卦中；得中位者多吉，所谓"刚中"（阳爻居中）或"柔中"（阴爻居中）。
- **source_chapter**：vol-00/yi-li
- **applicable_to**：解卦
- **caveats**：中位虽贵，仍需看爻才与时。
- **verification_status**：pending_verification

### ZZR-01-03 中正为大吉

- **rule_statement**：得中又当位（如九五、六二）为"中正"，最贵之爻；多主大吉、君子之道。
- **source_chapter**：vol-00/yi-li
- **applicable_to**：解卦
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-01-04 应

- **rule_statement**：初与四、二与五、三与上相应；阴阳相应为有应（吉象）、同性相应为无应（孤立）。
- **source_chapter**：vol-00/yi-li
- **applicable_to**：解卦时论爻之援助
- **caveats**：与卜筮"世应"概念不同；此处专属义理解卦。
- **verification_status**：pending_verification

### ZZR-01-05 比

- **rule_statement**：相邻两爻为比；阴阳相比为亲、同性为敌。比关系次于应。
- **source_chapter**：vol-00/yi-li
- **applicable_to**：解卦
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-01-06 卦主

- **rule_statement**：一卦之主爻多为五爻（君位）；或以"成卦之主"（一阴一阳独成卦义者）；或以"主卦之主"（位最尊德最大者）。
- **source_chapter**：vol-00/yi-li
- **applicable_to**：解卦义之归
- **caveats**：朱熹与程颐对卦主认定有差异，本书取折中。
- **verification_status**：pending_verification

### ZZR-01-07 时位

- **rule_statement**：易爻随卦时而变义；同一爻位在不同卦中义不同（如九三在乾为君子终日乾乾、在坤无）。
- **source_chapter**：vol-00/yi-li
- **applicable_to**：所有解卦
- **caveats**：不可执位以释爻。
- **verification_status**：pending_verification

## 二、卦义判断

### ZZR-02-01 卦时

- **rule_statement**：每卦象征一时；解卦先识卦时（屯之难、需之待、否之闭、泰之通）。
- **source_chapter**：vol-00/yi-li 总论 + 各卦
- **applicable_to**：所有解卦
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-02-02 卦德

- **rule_statement**：上下两卦之德合为一卦德（如乾下乾上为健中健、坎下离上为水火既济）。
- **source_chapter**：vol-00 + vol-16
- **applicable_to**：解卦
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-02-03 反对相成

- **rule_statement**：64 卦两两为反对（综卦）；反对之卦义相反相成（如屯蒙、需讼、师比）。
- **source_chapter**：vol-17/xugua-zagua + vol-00/yi-li
- **applicable_to**：解卦序与卦义
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-02-04 错卦相通

- **rule_statement**：64 卦皆有错卦（六爻全反）；错卦之义为本卦之背面（乾错坤、屯错鼎）。
- **source_chapter**：vol-17
- **applicable_to**：深度解卦
- **caveats**：—
- **verification_status**：pending_verification

## 三、八卦象义（卷十六说卦）

### ZZR-03-01 八卦德性

- **rule_statement**：乾健、坤顺、震动、巽入、坎陷、离丽、艮止、兑悦；为八卦本德。
- **source_chapter**：vol-16/shuogua
- **applicable_to**：解卦取象
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-03-02 八卦类象

- **rule_statement**：八卦各有动物 / 身体 / 家人 / 方位 / 季节等多重类象（详卷十六）。
- **source_chapter**：vol-16
- **applicable_to**：取象解卦
- **caveats**：类象有传统差异；与梅花易数取象互参。
- **verification_status**：pending_verification

## 四、繫辭义理（卷十三 ~ 卷十五）

### ZZR-04-01 太极生两仪

- **rule_statement**：易有太极，是生两仪、两仪生四象、四象生八卦；为易理生成之总框架。
- **source_chapter**：vol-13（系辞上）
- **applicable_to**：易学根本论
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-04-02 道器同体

- **rule_statement**：形而上者谓之道、形而下者谓之器；易兼道器，不可偏执。
- **source_chapter**：vol-13
- **applicable_to**：易学方法论
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-04-03 知幾

- **rule_statement**：君子见几而作；知微之始者，可应万变。
- **source_chapter**：vol-15（系辞下）
- **applicable_to**：易学修身论
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-04-04 三才

- **rule_statement**：六爻分三才；初二为地、三四为人、五上为天。
- **source_chapter**：vol-15
- **applicable_to**：解卦层级论
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-04-05 易有四象（吉凶悔吝）

- **rule_statement**：吉凶生大业；悔吝者言乎其小疵；动爻之吉凶悔吝皆由象生。
- **source_chapter**：vol-13
- **applicable_to**：解卦判吉凶
- **caveats**：—
- **verification_status**：pending_verification

## 五、序卦与杂卦理路

### ZZR-05-01 序卦相次

- **rule_statement**：64 卦相次有理；后卦由前卦之必然演化（屯生于乾坤、蒙次于屯）。
- **source_chapter**：vol-17/xugua
- **applicable_to**：卦序解读
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-05-02 杂卦反对

- **rule_statement**：杂卦传以两两反对论卦义之异同（乾刚坤柔、比乐师忧）。
- **source_chapter**：vol-17/zagua
- **applicable_to**：卦义比较
- **caveats**：—
- **verification_status**：pending_verification

## 六、啟蒙规则（卷十八 ~ 卷二十二）

### ZZR-06-01 河图洛书数

- **rule_statement**：河图天数 1+3+5+7+9 = 25、地数 2+4+6+8+10 = 30、合 55；洛书纵横皆 15。
- **source_chapter**：vol-18/qimeng-1-bentu
- **applicable_to**：象数解卦根本
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-06-02 加一倍生卦

- **rule_statement**：太极一、两仪二、四象四、八卦八、十六、三十二、六十四；每加一爻倍增。
- **source_chapter**：vol-19/qimeng-2-yuangua
- **applicable_to**：先天易理
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-06-03 大衍揲蓍

- **rule_statement**：50 根蓍草、去 1 不用、余 49 根、分二挂一揲四归奇，共 18 变成一卦。
- **source_chapter**：vol-20/qimeng-3-mingshi
- **applicable_to**：揲蓍成卦
- **caveats**：实操**严禁** LLM 手算；必须 `tool.divination.qiguagua`。
- **verification_status**：pending_verification

### ZZR-06-04 老阴老阳为动

- **rule_statement**：揲蓍得 9（老阳 / 重）、6（老阴 / 交）为动爻；7（少阳 / 单）、8（少阴 / 拆）为静爻。
- **source_chapter**：vol-20
- **applicable_to**：动静爻判定
- **caveats**：与三钱金钱卦动静爻一致，但概率分布不同。
- **verification_status**：pending_verification

### ZZR-06-05 变占法（朱熹折中）

- **rule_statement**：六爻全静占本卦彖辞 / 卦辞；一爻变占本卦变爻爻辞；二爻变占本卦二变爻、上爻为主；三爻变占本卦及变卦彖辞、本卦为主；四爻变占变卦二不变爻、下爻为主；五爻变占变卦不变爻；六爻全变占之卦彖辞（乾用九 / 坤用六例外）。
- **source_chapter**：vol-21/qimeng-4-kaobianzhan
- **applicable_to**：变占判断
- **caveats**：朱熹折中诸家说之总结；其他派别变占法（如京房 6 亲法）不同。
- **verification_status**：pending_verification

### ZZR-06-06 占断不替代修身

- **rule_statement**：易者寡过之书；占断为辅，修身为本；君子知幾不待占而后行。
- **source_chapter**：vol-15 + vol-22
- **applicable_to**：易学伦理立场
- **caveats**：本书反对依赖占卜决疑而废修身。
- **verification_status**：pending_verification

## 七、解卦综合规则

### ZZR-07-01 折中四层

- **rule_statement**：本书解卦四层：先程传（义理）、次本义（义理 + 象数兼）、次集说（诸家）、终案语（折中）；学者依此层次研读。
- **source_chapter**：凡例 + vol-01 ~ vol-12
- **applicable_to**：本书解卦使用方法
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-07-02 程朱异同

- **rule_statement**：程颐重义理（伊川易传）、朱熹兼象数与卜筮（本义）；本书以朱为正、程为佐。
- **source_chapter**：凡例
- **applicable_to**：辨程朱
- **caveats**：—
- **verification_status**：pending_verification

### ZZR-07-03 不偏汉学

- **rule_statement**：本书重宋学义理而旁取汉学象数；不取魏伯阳 / 京房等纳甲飞伏之纯象数。
- **source_chapter**：凡例 + 綱領
- **applicable_to**：易学派别立场
- **caveats**：清代后期惠栋汉学派对此有反动，应注明。
- **verification_status**：pending_verification

### ZZR-07-04 解卦不可一执

- **rule_statement**：解卦兼综时位 / 才德 / 应比 / 中正 / 卦主等多角度；不可执一以蔽义。
- **source_chapter**：vol-00/yi-li 总论
- **applicable_to**：所有解卦
- **caveats**：—
- **verification_status**：pending_verification

---

## 现代使用边界（caveats 总）

- **ZZR-06-03 蓍法**：揲蓍实操须 `tool.divination.qiguagua`，**严禁** LLM 手算。
- **ZZR-06-06 占断不替代修身**：本书核心立场——易非以预测吉凶为本，而以反观修身为旨。
- **义理解卦**：本 pack 是义理框架的索引，具体卦义需阅读原书 + 现代学术注疏。
- **64 卦每卦细节**：本 pack 不展开；具体应回归原典。
- **不涉占断实务**：金钱卦 / 体用占法应转 `zengshan-buyi` / `meihua-yishu`。

**全部 28 条规则 `verification_status: pending_verification`，待与四库本逐章复核后升级。**
