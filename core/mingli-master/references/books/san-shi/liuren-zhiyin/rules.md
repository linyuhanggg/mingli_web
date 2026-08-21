# 《六壬指南 / 六壬指南注解》Executable Rule Cards

> 本文件只把可定位、可设前置字段和停止条件的内容做成规则。排盘、节气、月将、天地盘、四课、三传、天将及神煞位置必须由确定性 adapter 给出。规则文本只解释分支，不自由手算。

## LR-00 起盘输入门

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q007`, `LZ-Q008`, `LZ-Q009`, `LZ-Q010`
- **normalized_lines**: L57-L61
- **required_fields**: `query_time`, `timezone`, `calendar_policy`, `month_general`, `heaven_plate`, `day_stem`, `day_branch`, `four_lessons`
- **preconditions**: 用户给出可校验的占时，或给出已由同一算法生成的完整课盘。
- **execution**:
  1. 用历算 adapter 按约定节气边界求月将，不从农历月份猜月将。
  2. 由 adapter 执行月将加占时、顺布天盘。
  3. 由 adapter 生成干支各阴阳课，输出四课及每课上下神。
  4. 字段完整后才进入 `LR-01`。
- **decision_effect**: 建立唯一、可复算的取用输入；本卡本身不下吉凶结论。
- **exceptions**: 已有完整课盘时可跳过历算，但必须记录排盘来源、算法版本和占时口径。
- **conflicts**: L59 对正时、报时、报数有注本偏好；若用户采用其他起时法，必须显式记录，不得静默替换。
- **adapter_requirements**: `calendar.month_general`, `liuren.heaven_plate`, `liuren.four_lessons`。
- **confidence**: high for textual sequence; chart correctness depends on adapter and input quality.

## LR-01 直接贼克优先

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q011`, `LZ-Q012`, `LZ-Q013`
- **normalized_lines**: L63-L64
- **required_fields**: `four_lessons[].lower`, `four_lessons[].upper`, `five_phase_relations`, `heaven_plate`
- **preconditions**: `LR-00` 已通过，四课上下关系可确定。
- **execution**:
  1. 收集所有“下克上”的候选，记为 `lower_overcomes_upper`。
  2. 只要该集合非空，就忽略所有“上克下”候选。
  3. 若该集合恰有一个，以其上神为初传，课名记 `重审`。
  4. 若该集合多于一个，转 `LR-02`。
  5. 只有在没有下克上时才检查“上克下”；恰有一个则以上神为初传，课名记 `元首`，多于一个转 `LR-02`。
  6. 初传确定后，由天盘追取中传、末传；不得凭文字猜支序。
- **decision_effect**: 输出直接克分支的初传候选或唯一初传。
- **exceptions**: 伏吟、反吟、八专若存在直接克，仍先走本卡；其“无克”情形才走各自专卡。
- **conflicts**: 不得在已有下贼时因上克数量更多而改选上克。
- **adapter_requirements**: 五行克关系、四课候选去重、天盘逐传函数。
- **confidence**: high.

## LR-02 多克的比用与《指南》涉害层次

- **source_layer**: `original_text` + `chen_gongxian_content`; L68 modifier is `zhang_hong_modern_annotation`
- **quote_id**: `LZ-Q014`, `LZ-Q015`, `LZ-Q016`
- **normalized_lines**: L66-L68
- **required_fields**: `day_stem_yinyang`, `candidate_upper_branch_yinyang`, `candidate_ground_branch`, `candidate_count`
- **preconditions**: `LR-01` 留下两个或更多同类直接克候选。
- **execution**:
  1. 以候选上神的阴阳与日干阴阳相同者为比用候选。
  2. 若仅余一个，取该候选为初传，记录 `比用/知一`。
  3. 若仍多于一个，按本注本的孟、仲、季层次筛选：先看地盘孟位 `寅申巳亥`，无则仲位 `子午卯酉`，再无则季位 `辰戌丑未`。
  4. 同一优先层仍有多个候选时，返回 `unresolved_by_this_pack`，不得自行加入涉害深浅或他派 tie-break。
- **decision_effect**: 唯一时输出初传；不唯一时输出停止状态和剩余候选。
- **exceptions**: L68 是张洪对《指南》法的现代说明，不代表所有大六壬流派。
- **conflicts**: 与按涉害深浅取用的算法冲突时，必须通过 `lineage=liuren-zhinan-annotated` 参数隔离。
- **adapter_requirements**: 阴阳过滤、孟仲季地盘分类、冲突状态输出。
- **confidence**: high for 比用 and 孟/仲 wording; medium for the no-depth modifier because it is modern annotation.

## LR-03 无直接克时先取遥克

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q017`, `LZ-Q018`, `LZ-Q019`
- **normalized_lines**: L70-L71
- **required_fields**: `day_stem`, `lesson_2_upper`, `lesson_3_upper`, `lesson_4_upper`, `five_phase_relations`, `day_stem_yinyang`
- **preconditions**: 四课上下全无直接克；不是八专无克分支。
- **execution**:
  1. 先检查第二、三、四课上神是否克日干。
  2. 有候选则以其为 `蒿矢` 候选；多候选只做比用阴阳过滤。
  3. 若没有上神克日干，再检查日干是否克第二、三、四课上神。
  4. 有候选则以其为 `弹射` 候选；多候选只做比用阴阳过滤。
  5. 过滤后仍并列则返回 `unresolved_by_this_pack`；完全无遥克则转 `LR-04` 或 `LR-05`。
- **decision_effect**: 输出蒿矢或弹射初传，或确认“无遥克”。
- **exceptions**: 八专无克明确“不复取遥”；伏吟、反吟无克先走专卡。
- **conflicts**: 不得颠倒蒿矢与弹射的检查次序，也不得把遥克当直接贼克。
- **adapter_requirements**: 上神对日干、日干对上神的定向克关系和比用过滤。
- **confidence**: high; residual tie handling intentionally conservative.

## LR-04 四课无克无遥取昴星

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q020`, `LZ-Q021`, `LZ-Q022`, `LZ-Q024`
- **normalized_lines**: L73-L74, L77
- **required_fields**: `distinct_lesson_count`, `day_stem_yinyang`, `heaven_plate.you_above`, `heaven_plate.you_below`, `day_upper`, `branch_upper`
- **preconditions**: 恰为四课，既无直接克又无遥克，且不是伏吟或反吟专式。
- **execution**:
  1. 阳日调用 adapter 的 `you_above` 取初传；中传取 `branch_upper`，末传取 `day_upper`。
  2. 阴日调用 adapter 的 `you_below` 取初传；中传取 `day_upper`，末传取 `branch_upper`。
  3. 输出课名 `昴星` 和三传生成路径。
- **decision_effect**: 形成昴星三传。
- **exceptions**: 三课不备用别责；两课八专不用昴星。
- **conflicts**: “酉上/酉下”的实现必须由 adapter 的《指南》口径定义，语言模型不得凭图形直觉手算。
- **adapter_requirements**: 昴星俯仰函数、干上/支上取神。
- **confidence**: high for branch conditions; implementation confidence depends on adapter convention.

## LR-05 三课无克无遥取别责

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q023`, `LZ-Q024`
- **normalized_lines**: L76-L77
- **required_fields**: `distinct_lesson_count`, `day_stem_yinyang`, `day_stem_combination`, `day_branch_trine`, `day_upper`
- **preconditions**: 四课去重后恰为三课，且无直接克、无遥克。
- **execution**:
  1. 阳日以日干五合之干所寄宫的上神为初传。
  2. 阴日以日支三合局的前一位为初传，按本书说明“不用乘神”。
  3. 阴阳日的中传、末传均取 `day_upper`。
  4. 输出课名 `别责` 和三传来源。
- **decision_effect**: 形成别责三传。
- **exceptions**: 四课用昴星，两课用八专；课数不明时停止。
- **conflicts**: 三合“前一位”的方向和天干寄宫须由 adapter 明确定义，不能靠模型默算。
- **adapter_requirements**: 天干五合寄宫、日支三合前位、课数去重。
- **confidence**: high for textual branch; adapter mapping required.

## LR-06 伏吟无克取传

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q025`, `LZ-Q026`
- **normalized_lines**: L78-L79
- **required_fields**: `is_fuyin`, `direct_overcomes`, `day_stem_yinyang`, `day_upper`, `branch_upper`, `branch_punishments`, `branch_clashes`
- **preconditions**: 天地盘同位，adapter 标记 `is_fuyin=true`。
- **execution**:
  1. 有直接克时返回 `LR-01` / `LR-02`。
  2. 无克时，阳日以 `day_upper` 发初传，阴日以 `branch_upper` 发初传。
  3. 正常按刑关系递取中末传。
  4. 初传自刑时，阳日改以 `branch_upper` 为中传，阴日改以 `day_upper` 为中传，再取刑为末传。
  5. 中传自刑时，末传改取其冲神。
- **decision_effect**: 形成伏吟三传并记录每次自刑回退。
- **exceptions**: 伏吟的动静解释仍须看课传神将，不能只凭“伏”字断静。
- **conflicts**: 刑、冲表必须来自同一 adapter 版本。
- **adapter_requirements**: 伏吟识别、三刑、自刑、冲神函数。
- **confidence**: high.

## LR-07 反吟有克与无依井栏

- **source_layer**: `chen_gongxian_content`
- **quote_id**: `LZ-Q027`, `LZ-Q028`
- **normalized_lines**: L79
- **required_fields**: `is_fanyin`, `direct_overcomes`, `day_pillar`, `well_rail_opposite_upper`, `branch_upper`, `day_upper`
- **preconditions**: adapter 标记十二神各临冲位，`is_fanyin=true`。
- **execution**:
  1. 有直接克时，少克走 `LR-01`，多克走 `LR-02`。
  2. 无克时只接受丁未、己未、辛未、丁丑、己丑、辛丑六日的 `无依/井栏` 分支。
  3. 初传取 adapter 计算的 `well_rail_opposite_upper`，中传取 `branch_upper`，末传取 `day_upper`。
  4. 若 adapter 报反吟无克但日柱不在六日集合，返回 `inconsistent_chart_or_lineage`。
- **decision_effect**: 输出反吟直接克或井栏三传。
- **exceptions**: 反吟并不自动等于所有事情都会移动；后续仍按神将、空亡和问题字段解释。
- **conflicts**: 不得在无依分支中改套遥克、昴星或别责。
- **adapter_requirements**: 反吟识别、六日校验、井栏冲射上神。
- **confidence**: high.

## LR-08 八专两课分支

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q029`, `LZ-Q030`
- **normalized_lines**: L81-L82
- **required_fields**: `is_bazhuan`, `distinct_lesson_count`, `direct_overcomes`, `day_stem_yinyang`, `day_upper`, `branch_yin_upper`
- **preconditions**: 干支同位，四课去重后为两课，adapter 标记 `is_bazhuan=true`。
- **execution**:
  1. 有直接克时走 `LR-01` / `LR-02`。
  2. 无克时跳过遥克。
  3. 阳日从干上阳神连根顺数三神取初传。
  4. 阴日从支上阴神连根逆数三神取初传。
  5. 中传、末传均取 `day_upper`。
- **decision_effect**: 形成八专三传。
- **exceptions**: “得三而止”按本书连根计数；计数函数不得与别派实现混用。
- **conflicts**: 两课无克不能进入遥克、昴星或别责。
- **adapter_requirements**: 八专识别、顺逆连根计数。
- **confidence**: high.

## LR-09 初中末过程角色

- **source_layer**: `original_text`
- **quote_id**: `LZ-Q031`
- **normalized_lines**: L770
- **required_fields**: `initial_transmission`, `middle_transmission`, `final_transmission`, `transmission_relations`
- **preconditions**: 三传已由前述规则或 adapter 唯一生成。
- **execution**:
  1. 初传只标记发端和最先显现的条件。
  2. 中传标记过程中的移易、转折或承接。
  3. 末传标记归计和最终落点。
  4. 同时检查三传相生、相克、空墓、进退；不得只取初传一句定全局。
- **decision_effect**: 生成按时间/过程分层的解释结构。
- **exceptions**: 伏吟、反吟、回环等结构会改变过程感，但不取消三层记录。
- **conflicts**: 历史占验的事后叙述不能反推为通用应期公式。
- **adapter_requirements**: 三传关系矩阵与空墓进退字段。
- **confidence**: high as interpretive order, not empirical guarantee.

## LR-10 课传先于神将

- **source_layer**: `original_text`
- **quote_id**: `LZ-Q032`
- **normalized_lines**: L817
- **required_fields**: `resolved_lessons`, `resolved_transmissions`, `heavenly_generals`, `general_strength`, `general_conflicts`
- **preconditions**: 取用和三传已定。
- **execution**:
  1. 先保存课体、初中末和干支主客形成的主结构。
  2. 再读取各传所乘天将及旺衰、内外战等字段。
  3. 天将用于限定、修饰或揭示作用方式，不反向重选初传。
  4. 神煞须再后置到 `LR-12`。
- **decision_effect**: 形成“核心课传 -> 神将”的两层解释，不发生顺序倒置。
- **exceptions**: 若 adapter 发现盘式不一致，回到 `LR-00`，而不是让神将替错误课盘兜底。
- **conflicts**: 不得从单一白虎、玄武、贵人等名称直接生成现实断言。
- **adapter_requirements**: 天将布置及旺衰、克战字段。
- **confidence**: high.

## LR-11 分占章节只负责问题路由

- **source_layer**: `original_text` + `chen_gongxian_content`
- **quote_id**: `LZ-Q033`
- **normalized_lines**: L830
- **required_fields**: `question_domain`, `resolved_chart`, `chapter_map_id`, `risk_domain`
- **preconditions**: 用户问题已分类，且不是要求把文化文本当现实保证。
- **execution**:
  1. 按 `chapter-map.md` 选择卷二分类纲要或卷三相应章节。
  2. 先抽取该占类要求观察的字段，再与已定课传交叉。
  3. 卷三占验只作历史案例比较，不能以单例生成新规则。
  4. 医疗、法律、投资、灾祸、婚育等高风险问题只作文本解释，不给事实预测或替代专业意见。
- **decision_effect**: 输出检索范围和所需字段，不直接输出事件必然发生。
- **exceptions**: 问题跨多个占类时可加载多个章节，但必须分别说明证据。
- **conflicts**: 现代增补课例不得冒充陈公献占验。
- **adapter_requirements**: 问题分类器、章节路由、风险门控。
- **confidence**: high for routing; no claim of predictive validity.

## LR-12 神煞仅作盘后辅证

- **source_layer**: `annotated_comment_unattributed`
- **quote_id**: `LZ-Q042`, `LZ-Q048`
- **normalized_lines**: L2451, L2798
- **required_fields**: `resolved_chart`, `primary_reading`, `shensha_positions`, `shensha_source_system`, `corroborating_core_factors`
- **preconditions**: `LR-00` 至 `LR-10` 所需主盘字段齐全，且已有不含神煞的主判断。
- **execution**:
  1. 由六壬专用 adapter 计算岁、月、旬、干、支煞，不从压平表格手抄位置。
  2. 对每个神煞检查是否同时得到干支、课传、神将、刑克或旺衰的同向支持。
  3. 有同向核心因素时只增加“辅证”标签；无同向因素时标 `unconfirmed_shensha`。
  4. 神煞冲突时保留冲突，不投票，不推翻课传，不重选发用。
- **decision_effect**: 只调整解释置信度或提供复核线索；不得单独生成结论。
- **exceptions**: 若用户专门研究《神煞图位》的文本，可直接检索卷四，但仍须标来源层和未页校状态。
- **conflicts**: 六壬神煞不得移植到八字、择日、紫微、星命或其他系统；百家异同见 L2798。
- **adapter_requirements**: `liuren.shensha` with source profile `liuren-zhinan`; provenance per shensha.
- **confidence**: high for post-chart gate; medium for individual table values pending scan collation.

## LR-13 三合只能是三传的一项特征

- **source_layer**: `zhang_hong_modern_annotation`
- **quote_id**: `LZ-Q039`, `LZ-Q040`, `LZ-Q041`
- **normalized_lines**: L2431-L2434
- **required_fields**: `three_transmissions`, `trine_type`, `initial_use`, `transmission_relations`, `chapter_30_flag`
- **preconditions**: 三传形成三合局，且明确调用的是张洪注本第三十章现代附录。
- **execution**:
  1. 记录三合局的五行类别与顺逆、旺衰。
  2. 仍按初中末、课体、干支和神将逐层解释。
  3. 把三合只作为 `pattern_feature`，不得压缩成一个固定事件断语。
  4. 输出中标明该卡来自现代附录，并与陈公献 1-29 章隔离。
- **decision_effect**: 为既有主判断添加一个现代注本模式特征。
- **exceptions**: 不调用第三十章时，本卡不参与古籍原文规则集。
- **conflicts**: 不得用潍坊单例证明三合局普遍应验。
- **adapter_requirements**: 三传三合识别和 chapter-layer flag。
- **confidence**: medium as modern interpretive note; low as empirical generalization.

## LR-14 输出前执行来源层守门

- **source_layer**: `old_preface_attribution` + `zhang_hong_modern_annotation`
- **quote_id**: `LZ-Q001`, `LZ-Q003`, `LZ-Q004`, `LZ-Q005`, `LZ-Q036`
- **normalized_lines**: L38, L40-L41, L1194
- **required_fields**: `evidence_quote_id`, `evidence_line`, `source_layer`, `attribution_status`, `claim_text`
- **preconditions**: 准备引用、转述或生成规则。
- **execution**:
  1. 先从 `quote-index.md` 取 `quote_id` 和层级。
  2. 若为两赋短句，写“赋文”；若为旧注或《会纂》，写陈公献内容。
  3. 若为庄氏神煞层，写传统归属并保留庄公远/庄广之待考。
  4. 若为张洪增注、史注、现代课例或潍坊课例，明确写“现代注本层”。
  5. 归属不明的题下注写 `annotated_comment_unattributed`，不强归古人。
- **decision_effect**: 每个输出片段都附来源层；层级缺失则阻止引用。
- **exceptions**: 纯目录导航可只给行号，但不得称其为原文证据。
- **conflicts**: normalized 包装层永远不能升级为书中引文。
- **adapter_requirements**: quote registry lookup and source-layer validator.
- **confidence**: high.

## LR-15 求财先验妻财旺空，再用玄武限定实得

- **source_layer**: `original_text`
- **quote_id**: `LZ-Q050`, `LZ-Q051`, `LZ-Q052`
- **normalized_lines**: L777, L1817, L1819
- **required_fields**: `question_domain`, `three_transmissions`, `wealth_relative`, `wealth_stage`, `wealth_strength`, `wealth_void_or_tomb`, `heavenly_generals`, `final_stage`
- **preconditions**: 用户问收款、入账或求财，三传、六亲、旺衰、空墓与天将已由确定性事实层给出。
- **execution**:
  1. 先确认妻财是否进入三传、位于初中末哪一阶段以及旺相休囚死。
  2. 财爻空、墓时列为实质阻碍；财旺相且不空墓只支持“财信号实”，不自动推出精确金额。
  3. 玄武进入财事的后段时只增加失、耗、扣减或实得不足的风险标签；不得单凭玄武编造被骗、拖欠或具体支出。
  4. 把课传过程与财爻信号合并，分别输出名义金额倾向与最终可支配倾向。
- **decision_effect**: 形成 `wealth_presence`, `relative_quantity`, `net_receipt_modifier` 三层求财信号。
- **exceptions**: 纯问财运而非一笔具体收款时，不套用具体到账阶段。
- **conflicts**: 青龙、玄武是后置限定；不得覆盖课传、旺衰、空墓或问题类神。
- **adapter_requirements**: 三传六亲、旺衰、空墓、天将、阶段。
- **confidence**: high for the textual decision order; uncalibrated for currency magnitude.

## LR-16 应期先合并课体迟速，求财再看末传六合

- **source_layer**: `chen_gongxian_content` + `original_text`
- **quote_id**: `LZ-Q049`, `LZ-Q053`
- **normalized_lines**: L65, L1820
- **required_fields**: `lesson_method`, `initial_strength`, `final_branch`, `final_combination_branch`, `calendar_normalization`, `other_timing_candidates`
- **preconditions**: 用户问具体事件应期，事实层日期、课体和三传完整；只有求财问题才启用末传六合分支。
- **execution**:
  1. 元首增加相对速信号，重审增加相对迟信号；同时保留发用旺衰等反向信号。
  2. 求财成期以末传六合支生成一个候选支，不直接当唯一日期；非求财问题跳过本步。
  3. 用已验证日干支和民用日期换算下一候选支日；与其他原典候期候选并列。
  4. 多个候选相邻时可输出候选窗口；相距明显或规则冲突时并列说明，不强行平均。
- **decision_effect**: 产出相对迟速证据和求财完成候选日。
- **exceptions**: 缺民用日期时只给候选支；泛财运不生成某笔到账日。
- **conflicts**: 传统候期未经真实案例留出集校准，不得写成保证到账日。
- **adapter_requirements**: 课体、三传、六合表、干支日期换算。
- **confidence**: medium; deterministic rule application, empirical accuracy uncalibrated.

## LR-17 日辰主客只在定向相克时给出方向

- **source_layer**: `original_text`
- **quote_id**: `LZ-Q054`
- **normalized_lines**: L557-L558
- **required_fields**: `day_stem`, `day_branch`, `five_phase_relation(day_stem, day_branch)`
- **preconditions**: 日干、日支及其五行均由同一确定性课盘给出；问题属于可判成否的具体事件。
- **execution**:
  1. 日支五行克日干时，记为主客关系对所问不利。
  2. 日干五行克日支时，记为主客关系对所问有利。
  3. 相生、被生、同类或关系不明时，本卡不产生方向。
  4. 与类神、三传、空旺所得方向相反时保留反证，不以本卡独断。
- **decision_effect**: 产生一个 `subject_object_relation` 支持或阻力证据组。
- **exceptions**: 当前状态、精确地点、已发生事实识别等问题不使用本卡伪装观察事实。
- **conflicts**: 不把“辰来克日”改读成任意一课上神克日；本实现严格采用原注“支辰来克干 / 日干去克支辰”的日干日支口径。
- **adapter_requirements**: 已验证日柱、五行定向关系。
- **confidence**: medium for textual application; empirical predictive accuracy uncalibrated.

## LR-18 三传整体与初末克向必须完整命中

- **source_layer**: `original_text`
- **quote_id**: `LZ-Q055`
- **normalized_lines**: L777
- **required_fields**: `day_stem`, `initial_transmission`, `middle_transmission`, `final_transmission`, `five_phase_relations`
- **preconditions**: 三传完整有序，五行关系由确定性事实层给出。
- **execution**:
  1. 三传三支全部生日干时形成支持；全部克日干时形成阻力。
  2. 初传克末传形成阻力；末传克初传形成支持。
  3. 只有一传或两传命中“生/克日”时，不冒充“三传生日/克日”。
  4. 多项条件同时命中而方向相反时分别保留，不用条数投票。
- **decision_effect**: 分别产生 `transmissions_to_day` 与 `initial_final_relation` 证据组。
- **exceptions**: 求财的“日克三传”仍须与妻财类神规则合用，不能泛化为任何金额保证。
- **conflicts**: 本卡不覆盖空亡、旺衰和专项类神；这些条件可作为反证改变总判断。
- **adapter_requirements**: 三传支、日干、五行定向关系。
- **confidence**: medium; exact textual conditions, empirical predictive accuracy uncalibrated.

## LR-19 六亲入传先证明事项有落点

- **source_layer**: `original_text`
- **quote_id**: `LZ-Q056`, `LZ-Q057`
- **normalized_lines**: L777, L817
- **required_fields**: `question_domain`, `target_relative`, `three_transmissions`, `target_stage`, `void_status`, `strength_state`, `heavenly_general`
- **preconditions**: 问题类神已由有出处的专项映射确定，三传六亲、旺衰和空亡完整。
- **execution**:
  1. 对应六亲进入三传，只形成“事项进入课传、有落点”的支持证据。
  2. 再检查所在传位、空亡与旺衰；空或囚死可形成独立阻力。
  3. 天将后置为作用方式或成色修饰，只生成中性辅证。
  4. 类神不入传时只标此卡未命中，不反推出事项必不发生。
- **decision_effect**: 产生 `target_presence`, `target_strength` 和中性的 `target_general_modifier`。
- **exceptions**: 六亲名称不是现实动作；父母、妻财等不得脱离用户所问直接编造事件。
- **conflicts**: 类神存在与类神衰空可以同时成立，必须分别作为主证和反证保留。
- **adapter_requirements**: 问题类神映射、三传六亲、传位、旺衰、空亡、天将。
- **confidence**: medium; interpretation is source-bound but not empirically calibrated.
