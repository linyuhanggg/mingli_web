# procedures: 阳宅十书

## YZS-P001 Pack loading route

**source_anchor**: fulltext.md L25-L3015

1. 用户问阳宅、门向、宅内布局、放水、修门、择日或宅形时，先确认是否属于 `fengshui/yangzhai-shishu`。
2. 若是早期宅法/二十四路源流，先读 `huangdi-zhaijing`；若是门主灶三要，读 `yangzhai-sanyao`；若要阳宅外形、福元、大游年、穿宫、放水或修门择日，加载本 pack。
3. 只加载需要层：术语查 `terms.md`，判断查 `rules.md`，流程查本文件，引证查 `quote-index.md`。
4. 若涉及真实住宅，先取得现实测量与布局事实层；没有事实层时只说明“书中要求什么信息”，不做吉凶判定。

## YZS-P002 阳宅外形初筛

**source_anchor**: fulltext.md L25-L126

1. 收集地块/建筑事实：周边山水道路、明堂开阔度、前后左右高低、门前水塘/井/桥/路冲/树木/屋角/神庙等。
2. 用 `tool.fengshui.site_profile` 或等价人工勘测输出结构化事实。
3. 按 `YZS-R001` 到 `YZS-R003` 把外形风险分为：大局形势、门前冲射、水路桥井、近邻环境。
4. 只把古籍断语作为“传统风险指示”，另列现代安全/法务/建筑现实因素。

## YZS-P003 福元、东四西四与大游年

**source_anchor**: fulltext.md L767-L1303

1. 输入出生年/性别或书中所需的三元甲子事实；若缺失，停止在“需要福元事实层”。
2. 调用 `tool.fengshui.fuyuan_or_eight_mansion` 输出福元、东四位/西四位、八宅九星。
3. 调用罗盘/布局 adapter 输出门向、房位、路、灶、水、碾磨、牛马栏等位置到八卦/二十四山的映射。
4. 套用本 pack 的星名和吉凶分组：生气/延年/天乙优先，五鬼/六煞/祸害/绝命避重。
5. 若与《阳宅三要》门主灶口径冲突，保留书名差异，不平均。

## YZS-P004 穿宫九星与截路分房

**source_anchor**: fulltext.md L1577-L1680

1. 取得院落、墙体、门洞、进深层数、房屋高低和实际使用功能。
2. 先以大门起盘；遇到墙隔断并开门，按本书“截路分房”从该门重起。
3. 由 adapter 给出每个院/门后的九星层位，不由语言模型数层。
4. 吉星层高大、凶星层低小只是基础规则；若星与方位五行冲突，保留冲突并降低断定性。

## YZS-P005 开门修造与择日

**source_anchor**: fulltext.md L1766-L1860

1. 取得修门/安门/开门基的具体用途、地点、门向、施工范围。
2. 调用 `tool.fengshui.door_profile` 输出八山/二十四山门向。
3. 经 `scripts/run_reading_transaction.sh` 唯一生产入口调用 `mingli-master.selection.v1`，输出天德月德、满成开日、黑道、三煞、胎神、门光星等确定性字段。
4. 只有字段完整时才可按本书判断宜忌；字段缺失时列缺失项，不挑日子。
5. 门尺/门光星图涉及图表，未结构化前只作“需 adapter 输出”的字段。

## YZS-P006 放水与水法

**source_anchor**: fulltext.md L1881-L2014

1. 取得来水、去水、天井排水、外部沟渠/道路水势、坐向和二十四山。
2. 调用 `tool.fengshui.water_flow_profile` 和 `tool.fengshui.luopan.degrees_to_24_mountains`。
3. 分九星水法、阴阳山水、四路黄泉和二十四山放水四层读取。
4. 不把阴宅水法、阳宅排水、现代管线工程混成一层；现代排水安全优先独立说明。

## YZS-P007 选择第九

**source_anchor**: fulltext.md L2197-L2601

1. 输入宅主出生年、施工事项、候选日期、地点时区。
2. 要求 selection adapter 输出命前五神、九宫建宅、游年变宅、行年建宅、起工动土、上梁盖屋、太阴太阳过宫等字段。
3. 没有完整历法事实层时，只能说“本书要求先起命前五神并查诸局”，不能推荐具体日期。

## YZS-P008 符镇章节处理

**source_anchor**: fulltext.md L2616-L3015

1. 符镇章节只作为传统文献存在记录。
2. 保留符名、图像 URL、章节线索；不让语言模型抄绘、变造或推荐执行符法。
3. 若用户问符镇来源，可引用 `quote-index.md` 的短引并指向 fulltext 图像锚点。
4. 若用户问现实问题，回到外形/福元/放水/择日的 fact-layer 流程。
