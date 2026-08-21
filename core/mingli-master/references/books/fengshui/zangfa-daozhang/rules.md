# rules: 葬法倒杖

> 规则均来自完整章节集；`confidence` 是文本定位可信度，不是现实准确率。

## ZFD-R001: 真穴先看圆晕与小明堂

- **source_location**: fulltext.md L12
- **quote**: 有此圓暈則生氣內聚
- **plain_language_rule**: 本书把穴场中隐微圆晕、金鱼水界与小明堂作为“真穴”先验标志。
- **preconditions**: 已有现场形峦观察；能描述水分、水合、圆晕、小明堂。
- **decision_effect**: 无圆晕者不得直接按本书后续葬法展开。
- **adapter_requirements**: `tool.fengshui.site_survey`, `tool.fengshui.terrain_profile`
- **confidence**: high

## ZFD-R002: 凹凸分阴阳，阴阳交会处优先

- **source_location**: fulltext.md L19
- **quote**: 取阴阳交媾之中
- **plain_language_rule**: 晕间凹为阴穴，凸为阳穴；凹凸相兼时，重在取阴阳升降聚会处。
- **preconditions**: 有穴晕凹凸、龙体阴阳、饶减事实。
- **decision_effect**: 不可只看单一凹凸，必须合龙体与交会处。
- **adapter_requirements**: `tool.fengshui.terrain_profile`
- **confidence**: high

## ZFD-R003: 四象决定基础定基方向

- **source_location**: fulltext.md L26
- **quote**: 四象者，脈息窟突也
- **plain_language_rule**: 脉、息、窟、突分别对应取中、剖开、培高、凿平四类定基倾向。
- **preconditions**: 已辨明穴晕内微脊、微形、微窝、微泡。
- **decision_effect**: 四象未明时，不进入盖粘倚撞等细法。
- **adapter_requirements**: `tool.fengshui.site_survey`
- **confidence**: high

## ZFD-R004: 倍八卦把四象细分为十六法

- **source_location**: fulltext.md L33-L36
- **quote**: 脈緩者，用蓋法
- **plain_language_rule**: 本书按高山阳龙、高山阴龙、平地阳龙、平地阴龙四组，把脉/息/窟/突细分为盖、粘、倚、撞、斩、截、吊/坠、正、求、架、折、挨、并、斜、插等作法。
- **preconditions**: 已确认高山/平地、阴龙/阳龙、脉势急缓直横等。
- **decision_effect**: 只允许在同一组事实条件内取法，不跨组套用。
- **adapter_requirements**: `tool.fengshui.terrain_profile`, `tool.fengshui.site_survey`
- **confidence**: medium-high

## ZFD-R005: 葬法细节差错会破坏本书内部逻辑

- **source_location**: fulltext.md L39-L43
- **quote**: 理法少差，天淵懸隔
- **plain_language_rule**: 文中多次强调上下左右、深浅高低、大小厚薄的差错会使取法失效。
- **preconditions**: 使用任何细法前必须有足够现场尺度与位置资料。
- **decision_effect**: 若事实层只给“山形大概像某类”，不得输出具体下杖判断。
- **adapter_requirements**: `tool.fengshui.terrain_profile`, `tool.fengshui.luopan`
- **confidence**: high

## ZFD-R006: 十二杖以脉势急缓和山形状态触发

- **source_location**: fulltext.md L60-L81
- **quote**: 脈急中沖用逆杖
- **plain_language_rule**: 顺、逆、缩、离、没、穿、斗、截、对、缀、犯等法分别以脉缓、脉急、形俯、形仰、山体长横/长直、刚柔交接等条件触发。
- **preconditions**: 已描述脉势、穴形、四兽、明堂、水势。
- **decision_effect**: 十二杖不是一组可自由选择的“吉法”，而是按条件触发的形势分类。
- **adapter_requirements**: `tool.fengshui.site_survey`
- **confidence**: medium-high

## ZFD-R007: 二十四砂葬法以起止、生死、生气为总纲

- **source_location**: fulltext.md L88
- **quote**: 夫觀龍觀其起，明穴明其止
- **plain_language_rule**: 二十四砂法开始先要求观察来龙起处与穴情止处，在“死处又寻生”的框架下分合、浅深、饶减。
- **preconditions**: 已有来龙、止聚、砂水、穴情事实层。
- **decision_effect**: 不可把二十四砂条目当作单独象形比附；先看起止与生气。
- **adapter_requirements**: `tool.fengshui.terrain_profile`
- **confidence**: high

## ZFD-R008: 条目法必须绑定具体形类

- **source_location**: fulltext.md L89-L136
- **quote**: 來龍急氣，脈直沖中
- **plain_language_rule**: 担伞、正葬、打开、悬棺、马鬣封、回龙顾祖等都绑定特定来龙、穴势、砂水条件。
- **preconditions**: 已判明具体形类，且能定位条目中的关键条件。
- **decision_effect**: 条目名不能脱离文本条件单独引用。
- **adapter_requirements**: `tool.fengshui.site_survey`
- **confidence**: medium-high

## ZFD-R009: 本 pack 不提供现代实地处置结论

- **source_location**: fulltext.md L48-L49, L96-L102
- **quote**: 天地玄機，由人幹運
- **plain_language_rule**: 文中有棺、井、壙、墳等古代葬法操作语汇；在现代只能作为文本证据与术语研究。
- **preconditions**: 用户问题涉及现实墓地、工程、安全、法律时。
- **decision_effect**: 停在文献解释与事实需求，不给实际施工/安葬建议。
- **adapter_requirements**: legal/site/professional consultation outside this skill
- **confidence**: high

## ZFD-R010: 缺字异文不得补成规则

- **source_location**: fulltext.md L67, L110
- **quote**: 浮□
- **plain_language_rule**: 底文存在缺字或异常字符时，只保留为校勘风险，不把模型猜补内容放入规则。
- **preconditions**: 规则依赖缺字附近文本。
- **decision_effect**: 需要别本校勘；未校前只作低置信提示。
- **adapter_requirements**: edition_diff / OCR collation
- **confidence**: high
