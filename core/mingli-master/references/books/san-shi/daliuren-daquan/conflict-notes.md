# 《大六壬大全》版本与规则冲突

> 冲突项不是待模型“凭常识裁判”的空白。每项都给当前处理策略：`adopt_with_evidence`、`parallel_profiles`、`stop_pending_collation` 或 `historical_only`。

## C-001 normalized 与文渊阁卷次异构

- **evidence**: `chapter-map.md` A-C；`source-manifest.yaml`。
- **conflict**: normalized 把兵占列为卷五、宿度分野列为卷六、课经列卷七至十、毕法列卷十一至十二；Kanripo WYG 则课经为卷五至八、毕法为卷九至十、分野为卷十一至十二，并无同卷的独立兵占。
- **risk**: 只写“卷五”会把兵占和课经一混为一卷；声称 normalized 是逐卷文渊阁本不成立。
- **policy**: `parallel_profiles`。所有卷号加 `normalized` 或 `WYG/Kanripo` 前缀；最终版本学裁定等待影印页图。

## C-002 元首与重审在兵占容器反置

- **evidence for core definition**: DLQ-006、DLQ-026、DLQ-027；WYG K01、K05。
- **conflicting evidence**: DLQ-023、DLQ-024（normalized N05 兵占）。
- **conflict**: 起例与课经重复说“上克下=元首，下贼上=重审”，兵占两行反写。
- **policy**: `adopt_with_evidence`。算法和术语采用起例+课经+WYG 重复证据；N05 两行只保留为异文/编排问题，不参与默认定名。
- **test implication**: 任何引擎把下贼上标元首或上克下标重审均失败。

## C-003 昴星操作与“虎视”别名不稳定

- **evidence for operation**: DLQ-011、DLQ-034、DLQ-035。
- **conflicting wording**: normalized L13344 称“虎视课者，乃柔日也，昴昨课者，乃刚日也”。
- **conflict**: 课经主段把刚日分支称“虎视转蓬”、柔日称“冬蛇掩目”；毕法层又把“虎视”指柔日。
- **policy**: `adopt_with_evidence` for operation, `parallel_aliases` for names。算法只使用阳日酉上、阴日酉下及中末字段，不由“虎视”名称反推阴阳。

## C-004 柔日别责取支本身还是取其上神

- **evidence**: DLQ-012、DLQ-037、DLQ-038。
- **conflict**: 起例说“皆以天上作初传”；课经主文以柔日支三合前一辰的支字为初传；后文又明确问“独不用三合上之神，何也”并标“存疑”。
- **policy**: `stop_pending_collation`。阳日别责可按干合寄宫上神；柔日必须显式选择有来源的 `biezhe_profile`，否则停止，不设隐藏默认。

## C-005 八专不是“八个日柱”

- **evidence**: DLQ-039、DLQ-040。
- **conflict**: 旧 pack 曾列甲寅、乙辰、丁未、己未、戊巳、丙午、庚申、辛戌八日；本书课经明确列癸丑、甲寅、丁未、己未、庚申五日。
- **policy**: `adopt_with_evidence`。术语表使用五日集合；癸丑有克时先按贼克，另外四日的无克盘才常进入顺逆数三。

## C-006 天乙贵人正文俗例与四库订正冲突

- **body evidence**: DLQ-017、DLQ-021；normalized L2880 还说所载图“近不用”。
- **editorial evidence**: DLQ-003；提要称《星历考原》《协纪辨方书》订正曹震圭昼丑夜未之讹。
- **conflict**: 正文保留流传口诀，四库馆臣明确认为其口径有误。提要本身没有在本包中展开完整、可直接编码的逐日干订正表。
- **policy**: `parallel_profiles`。`book_conventional` 与 `siku_corrected_external` 分开；实际布将必须选择 profile 并记录完整 mapping/source。不得把订正口径简化为对所有日干都相同的一对地支，也不得静默默认。

## C-007 分野内容被四库提要直接批评

- **evidence**: DLQ-004、DLQ-025。
- **conflict**: 正文保存旧宿度和地域分野，馆臣称“多拘牵旧说，未能订正”。
- **policy**: `historical_only`。可用于文本史研究，不直接映射现代行政区、经纬度或现实事件；没有专门历史地理 adapter 时不执行。

## C-008 返吟井栏电子文本损坏

- **evidence**: DLQ-015；normalized L70 后半；Kanripo `KR3g0031_WYG_001-3a` 与 K05 井栏段。
- **conflict**: normalized 将口诀、夹注与字词粘连，无法仅靠该行安全还原全部无克井栏规则。
- **policy**: `stop_pending_adapter_validation`。只接受经过 WYG 页叶校对和 golden tests 的本地实现；本包不从损坏行补全算法。

## C-009 毕法目录编号 51-53 异常

- **evidence**: DLQ-051、DLQ-052。
- **conflict**: L12722 把“罡塞鬼户”标第五十三，下一行又把“两蛇夹墓”标第五十三，导致第五十二缺位。
- **policy**: `stop_on_number_only`。法条定位同时使用标题和正文锚点，不能按纯数字顺延；最终编号等影印核定。

## C-010 normalized 与 Kanripo 都不是无误校本

- **evidence**: DLQ-005 及 Kanripo K01 首叶。
- **conflict**: Kanripo 十干寄宫出现“丙戊课己”“丁巳课未”等己/巳疑误；normalized 又有返吟粘连、表格扁平和小注边界问题。
- **policy**: `triangulate`。关键规则至少用 normalized 重复正文、Kanripo 页叶和影印三层校勘；当前未完成影印校勘的地方明确降级。

## C-011 normalized N04/N05 的版本身份未决

- **evidence**: `chapter-map.md` C。
- **conflict**: N04 篇幅显著长于 Kanripo K04；N05 兵占无直接 WYG 同卷，并出现元首重审反置。
- **policy**: `separate_layer_pending_bibliography`。两容器仍属于完整电子来源的一部分，但不能无保留称为文渊阁原卷；其中规则需额外见证才能进入核心算法。

## C-012 课体、类神、神煞的权重冲突

- **evidence**: DLQ-002、DLQ-018、DLQ-028。
- **conflict**: 汇编收多层断法，若单取课体、单取类神或单取神煞，会产生相互矛盾的硬断。
- **policy**: `layered_interpretation`。四课三传为骨架，旺衰空墓与天将为修正，神煞后置；输出同时列支持与反向因素。

## C-013 兄弟书不是强制依赖或权威覆盖

- **evidence**: 本书自成完整总集；`source-manifest.yaml`。
- **conflict**: 旧 pack 曾把《六壬指南》写成下游简化，并以外部 `matrices/conflict-policy` 静默裁判。
- **policy**: `independent_books`。《六壬指南》《大六壬秘本》等只能在明确的跨书比较任务中并列，不自动覆盖本书，也不承担本书缺失证据。

## C-014 历史规则不等于统计准确率

- **evidence**: 全书提供传统规则与历史占验，但本地 corpus 没有现代盲测标签集。
- **conflict**: “权威古籍”“整本来源”容易被误读为已证实预测准确。
- **policy**: `no_empirical_claim_without_dataset`。可以审计文本忠实度、排盘一致性和规则复现率；预测准确率必须另建有时间戳、预注册、结果标签和基线比较的数据集。

## 冲突处理摘要

| conflict | current state | actual-cast behavior |
|---|---|---|
| C-001 卷次 | parallel | 卷号必须带体系 |
| C-002 元首/重审 | evidence-adopted | 上克下元首、下贼上重审 |
| C-003 昴星别名 | operation adopted, alias unresolved | 用阳仰阴俯字段，不用别名算 |
| C-004 柔日别责 | unresolved | 未选 profile 停止 |
| C-005 八专日集合 | evidence-adopted | 仅五日集合 |
| C-006 天乙贵人 | parallel profiles | 未选 profile 停止布将 |
| C-007 分野 | historical only | 不映射现代地理 |
| C-008 井栏 | guarded | 未验证 adapter 停止 |
| C-009 毕法编号 | unresolved | 标题+正文定位，不按数字猜 |
| C-010 转写质量 | pending scan collation | 疑字不进入硬编码 |
