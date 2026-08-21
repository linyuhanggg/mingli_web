# 《大六壬大全》Executable Rule Cards

> 这些卡片是选择性规则库，不是全书逐条穷尽。`execution` 只消费本地确定性 adapter 的结构化字段；任何历法、月将、天地盘、四课、三传、天将、空亡或神煞计算都不得由语言模型自由手算。

## DLR-00 实际起课事实门

- **source_layer**: `compendium_body` + `modern_synthesis`
- **quote_id**: `DLQ-007`, `DLQ-020`
- **normalized_lines**: L38, L4518
- **required_adapter_fields**: `adapter_name`, `adapter_version`, `input_datetime`, `timezone`, `location`, `calendar_policy`, `solar_term`, `day_ganzhi`, `hour_ganzhi`, `month_general`, `earth_plate`, `heaven_plate`, `four_lessons`, `rule_trace`, `three_transmissions`, `guiren_profile`, `heavenly_generals`, `xunkong`, `source_trace`
- **preconditions**: 用户要求实际占事或给出的既有课盘需要被当成事实使用。
- **execution**:
  1. 标准化时间、时区、地点和历法边界。
  2. 调用本地确定性大六壬 adapter；若用户给盘，则调用同一 adapter 的 `validate_existing_chart` 模式。
  3. 校验字段完整、干支时相容、月将来源可追踪、四课与三传决策链可复算。
  4. 只有通过后才进入 DLR-01 至 DLR-18。
- **decision_effect**: 产出可复算的事实层，不直接下断语。
- **stop_or_exception**: adapter 不存在、报错、字段缺失或决策链不可复算时，返回 `formal_liuren_cast_unavailable`；只可做文本解释。
- **conflicts**: 不接受未定义的外部接口名充当事实；不把第三方模型的自然语言盘面当 adapter 输出。
- **confidence**: high as a safety and reproducibility gate.

## DLR-01 十干寄宫输入校验

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-005`
- **normalized_lines**: L34
- **required_adapter_fields**: `day_stem`, `stem_lodge`, `stem_lodge_table_id`, `stem_lodge_source`
- **preconditions**: DLR-00 通过，adapter 已给日干和寄宫。
- **execution**:
  1. 以本书表核对甲寅、乙辰、丙戊巳、丁己未、庚申、辛戌、壬亥、癸丑。
  2. 记录表版本与原文证据，不从 Kanripo 的己/巳转写异字自动覆盖。
  3. 寄宫与表不一致时标记 `stem_lodge_mismatch`。
- **decision_effect**: 验证干课的落宫基础。
- **stop_or_exception**: 出现不一致时停止四课解释，先回到 adapter 修正；不得在下游补猜。
- **conflicts**: Kanripo K01 首叶有明显己/巳转写混淆，见 `conflict-notes.md` C-010。
- **confidence**: high for the normalized rule; scan collation still pending.

## DLR-02 贼克优先、元首重审定名与递传

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-006`, `DLQ-007`, `DLQ-026`, `DLQ-027`
- **normalized_lines**: L36-L38, L6832, L6926
- **required_adapter_fields**: `four_lessons[].lower`, `four_lessons[].upper`, `five_phase_relation`, `lower_overcomes_upper_candidates`, `upper_overcomes_lower_candidates`, `heaven_plate`, `decision_trace`
- **preconditions**: 四课已确定且不是无效盘。
- **execution**:
  1. 先检查全部 `lower_overcomes_upper_candidates`。
  2. 只有该集合为空时才检查 `upper_overcomes_lower_candidates`。
  3. 唯一下克上：以上神发用，课名 `重审`。
  4. 唯一上克下：以上神发用，课名 `元首`。
  5. 同类候选多于一项则转 DLR-03；初传唯一后，以初传所临天盘上神取中传，再取中传上神为末传，专式例外另走专卡。
- **decision_effect**: 输出唯一发用与课名，或输出待筛选候选。
- **stop_or_exception**: 不能区分上下、候选去重不明或盘式专分支未标记时停止。
- **conflicts**: normalized 兵占 L5470/L5472 把名称反置；重复正文与 WYG 两处均支持本卡，冲突行只作异文证据。
- **confidence**: high; cross-witness confirmed at WYG K01 and K05.

## DLR-03 多克先比用

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-008`, `DLQ-029`
- **normalized_lines**: L42, L6996
- **required_adapter_fields**: `day_stem_yinyang`, `same_direction_candidates[].upper_branch_yinyang`, `comparison_trace`
- **preconditions**: DLR-02 留下两个或更多同方向直接克候选。
- **execution**:
  1. 仅在 DLR-02 已保留的同方向集合内筛选。
  2. 阳日保留阳神，阴日保留阴神。
  3. 若仅余一项，以其为发用并标 `比用/知一`。
  4. 若仍多项或一项不余，转 DLR-04 涉害并保留原始候选。
- **decision_effect**: 缩小或确定发用候选。
- **stop_or_exception**: adapter 未输出候选阴阳、把支阴阳与天干阴阳混为一表时停止。
- **conflicts**: 不得跳过比用直接按涉害深度，也不得把上下两种克混在一起比。
- **confidence**: high.

## DLR-04 涉害、察微与缀瑕的可审计分支

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-009`, `DLQ-030`, `DLQ-031`, `DLQ-032`
- **normalized_lines**: L46, L7078, L7136, L7162
- **required_adapter_fields**: `remaining_candidates`, `candidate_harm_paths`, `candidate_harm_depths`, `candidate_ground_classes`, `day_stem_yinyang`, `lesson_order`, `shehai_trace`
- **preconditions**: 多个同方向候选经比用后仍俱比或俱不比。
- **execution**:
  1. adapter 为每个候选生成从所临地盘归本家的完整受克路径和深度。
  2. 深度唯一最大者发用，标 `涉害/见机`。
  3. 深度并列时检查孟仲季层；无孟而取仲季者标 `察微`。
  4. 深度和层级仍相等时，按四课先见规则处理并标 `缀瑕/复等`；阳日取干课先见，阴日取支课先见。
  5. 输出逐候选路径、每步克关系和 tie-break，不只输出最终支。
- **decision_effect**: 以可复核 trace 确定涉害发用。
- **stop_or_exception**: 任何路径、土寄宫、孟仲季或先见顺序缺字段即返回 `unresolved_shehai`，禁止语言模型手数。
- **conflicts**: 同书还有多段涉害解释与比用回退；若 adapter profile 不等于 `daliuren-daquan-wyg`，必须显式报告。
- **confidence**: high for decision stages; implementation requires golden-case validation.

## DLR-05 无直接克时的遥克优先次序

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-010`, `DLQ-033`
- **normalized_lines**: L50, L7268
- **required_adapter_fields**: `has_direct_overcome`, `lesson_upper_to_day_relations`, `day_to_lesson_upper_relations`, `remote_candidates`, `comparison_trace`
- **preconditions**: 四课上下无直接克；未进入伏吟、返吟、八专等专式无克分支。
- **execution**:
  1. 先找四课上神克日干，命名 `蒿矢` 候选。
  2. 仅在没有蒿矢候选时，找日干克四课上神，命名 `弹射` 候选。
  3. 多候选按 DLR-03、DLR-04 的比用/涉害逻辑筛选。
  4. 仍无遥克才进入 DLR-06 或其他专卡。
- **decision_effect**: 输出蒿矢或弹射发用，或确认无遥克。
- **stop_or_exception**: 上下关系或第二至第四课候选范围不明确时停止。
- **conflicts**: 不能把日克神叫蒿矢，也不能在神克日存在时优先弹射。
- **confidence**: high.

## DLR-06 昴星按阳仰阴俯，不按别名猜

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-011`, `DLQ-034`, `DLQ-035`
- **normalized_lines**: L54, L7410, L7436
- **required_adapter_fields**: `distinct_lesson_count`, `has_direct_overcome`, `has_remote_overcome`, `day_stem_yinyang`, `earth_you_above`, `heaven_you_below`, `day_upper`, `branch_upper`
- **preconditions**: 四课完整、无直接克、无遥克，且不属于伏吟、返吟、八专或三课别责。
- **execution**:
  1. 阳日取地盘酉上神为初传，中传取支上神，末传取干上神。
  2. 阴日取天盘酉所临地盘之神为初传，中传取干上神，末传取支上神。
  3. decision trace 写明 `yang_up` 或 `yin_down`，名称仅作附注。
- **decision_effect**: 形成昴星三传。
- **stop_or_exception**: adapter 只给“虎视”名称而不给酉上/酉下事实字段时停止；三课、两课不得进入本卡。
- **conflicts**: 毕法层 L13344 对“虎视”别名的刚柔用法与课经段不一致，故不以别名驱动算法。
- **confidence**: high for explicit operation; alias mapping unresolved.

## DLR-07 别责分阳日确定支与阴日歧义支

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-012`, `DLQ-036`, `DLQ-037`, `DLQ-038`
- **normalized_lines**: L58, L7514, L7550
- **required_adapter_fields**: `distinct_lesson_count`, `has_direct_overcome`, `has_remote_overcome`, `day_stem_yinyang`, `stem_combination`, `combined_stem_lodge`, `upper_over_combined_lodge`, `branch_trine_forward`, `upper_over_branch_trine_forward`, `day_upper`, `biezhe_profile`
- **preconditions**: 去重后恰为三课，且无直接克、无遥克。
- **execution**:
  1. 阳日取日干五合之干的寄宫上神为初传；中末并干上神。
  2. 阴日先同时计算 `branch_trine_forward` 与其上神，不静默丢弃任一候选。
  3. 若 `biezhe_profile` 明确选择校定口径，按该口径取初传，中末并干上神。
  4. 输出必须写明 profile、两个候选和采用理由。
- **decision_effect**: 阳日可确定；阴日仅在口径明示时确定。
- **stop_or_exception**: 阴日未提供经过校定的 `biezhe_profile` 时返回 `unresolved_biezhe_yin`。
- **conflicts**: L58 的“皆以天上作初传”、L7514 的支前三合本字和 L7550 的“存疑”不能被压成一个无争议规则。
- **confidence**: high for阳日; unresolved for阴日取支本身还是上神.

## DLR-08 八专先论克，无克才顺逆数三

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-013`, `DLQ-039`, `DLQ-040`
- **normalized_lines**: L62, L7556, L7652
- **required_adapter_fields**: `day_pillar`, `is_bazhuan_day`, `stem_branch_same_lodge`, `distinct_lesson_count`, `direct_overcomes`, `day_stem_yinyang`, `day_yang_upper`, `branch_yin_upper`, `count_three_trace`, `day_upper`
- **preconditions**: 日柱属于癸丑、甲寅、丁未、己未、庚申，且干支同位形成两课结构。
- **execution**:
  1. 有直接克时仍走 DLR-02 至 DLR-04，不用无克专法。
  2. 无克时不再找遥克。
  3. 阳日从干课阳神连本位顺数三位取初传；阴日从支课阴神连本位逆数三位取初传。
  4. 中传、末传均并干上神，并输出计数路径。
- **decision_effect**: 形成八专无克三传。
- **stop_or_exception**: 不在五日集合、课数不是两课或计数是否含本位不明时停止。
- **conflicts**: 旧 pack 列八个日柱错误；本书明确“五日”，且癸丑通常有克。
- **confidence**: high.

## DLR-09 伏吟有克优先，无克按刚柔刑冲

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-014`, `DLQ-041`, `DLQ-042`
- **normalized_lines**: L66, L7696, L7818
- **required_adapter_fields**: `is_fuyin`, `direct_overcomes`, `day_stem_yinyang`, `day_upper`, `branch_upper`, `punishment_map`, `clash_map`, `transmission_trace`
- **preconditions**: 月将支与占时支相同，十二神各居本宫，adapter 标记 `is_fuyin=true`。
- **execution**:
  1. 有克先走 DLR-02 至 DLR-04。
  2. 无克时，阳日取干上神为初传，阴日取支上神为初传。
  3. 通常依刑递取中末。
  4. 初传自刑时，阳日次传取支、阴日次传取干；次传非自刑，末仍取刑；次传复自刑，末取冲。
  5. 输出 `自任`、`自信` 或 `杜传` 分支与每步原因。
- **decision_effect**: 形成伏吟三传并保留自刑回退轨迹。
- **stop_or_exception**: 刑表、冲表或日干寄宫不统一时停止。
- **conflicts**: “伏吟”是盘式结构，不自动等于所有问题都静止或不成。
- **confidence**: high.

## DLR-10 返吟有克取克，无克井栏必须校定

- **source_layer**: `compendium_body` + `kanripo_wyg_witness`
- **quote_id**: `DLQ-015`, `DLQ-043`
- **normalized_lines**: L70, L7874
- **required_adapter_fields**: `is_fanyin`, `all_spirits_on_opposites`, `direct_overcomes`, `day_pillar`, `well_rail_trace`, `three_transmissions`, `rule_profile`
- **preconditions**: 十二神各居冲位，adapter 标记 `is_fanyin=true`。
- **execution**:
  1. 有直接克时走 DLR-02 至 DLR-04。
  2. 无克时只接受经过 WYG 页叶和测试固定的井栏实现；输出日柱适用集、斜射对象和中末取法。
  3. rule trace 必须引用 profile 和校定来源，不读取 normalized L70 损坏后半句来手算。
- **decision_effect**: 有克分支可确定；无克分支由校定 adapter 决定。
- **stop_or_exception**: adapter 没有 `well_rail_trace` 或 profile 未经过 golden tests 时返回 `unresolved_fanyin_well_rail`。
- **conflicts**: normalized L70 后半粘连，Kanripo K01 与 K05 虽保留更多文字，也不能免除实现测试。
- **confidence**: high for返吟识别与有克优先; guarded for井栏.

## DLR-11 天乙贵人 profile 必须显式

- **source_layer**: `siku_editorial_preface` + `compendium_body`
- **quote_id**: `DLQ-003`, `DLQ-017`, `DLQ-021`
- **normalized_lines**: L3, L3260, L4566
- **required_adapter_fields**: `day_stem`, `day_or_night_policy`, `guiren_profile`, `guiren_mapping`, `guiren_direction`, `heavenly_generals`, `profile_source_ids`
- **preconditions**: 要布十二天将或解释贵人顺逆。
- **execution**:
  1. adapter 必须声明 `guiren_profile`，至少区分“本书正文沿俗例”和“据《星历考原》《协纪辨方书》订正的官方口径”。
  2. 输出所选日干的昼贵、夜贵、昼夜判定规则、顺逆起点与来源表。
  3. 本包只验证“profile 已明确且 mapping 可追踪”，不凭提要一句话补造完整订正表。
  4. 比较两 profile 时并列输出差异，不把一个结果冒充另一个。
- **decision_effect**: 形成可复算天将盘或明确停止。
- **stop_or_exception**: `guiren_profile` 缺失、只给一个全局“昼某夜某”常量或来源表不可追踪时停止布将。
- **conflicts**: 四库提要明确批评正文沿俗例；默认不得静默裁判。
- **confidence**: high for the existence of conflict; corrected full mapping requires its own source pack.

## DLR-12 课体不可裸断，先课传后神将

- **source_layer**: `siku_editorial_preface` + `compendium_body`
- **quote_id**: `DLQ-002`, `DLQ-018`, `DLQ-028`
- **normalized_lines**: L3, L4064, L6910
- **required_adapter_fields**: `question_domain`, `four_lessons`, `three_transmissions`, `lesson_strengths`, `transmission_strengths`, `heavenly_generals`, `general_relations`, `xunkong`, `deities`, `rescues`, `contradictions`
- **preconditions**: 课体与三传已由 adapter 唯一确定。
- **execution**:
  1. 先解释四课、三传、干支与问题对象的结构。
  2. 再以旺相休囚死、空墓刑冲合、神将内外战和救制限定。
  3. 神煞只作后置辅证，不允许单项推翻已核课传。
  4. 输出“支持因素、反向因素、未决因素”，不因课名生成固定套话。
- **decision_effect**: 形成证据链而非标签断语。
- **stop_or_exception**: 关键修正字段缺失时只说明课体定义，不给具体事件推断。
- **conflicts**: 元首在原文中也明确“未可执一”；课体、类神、神煞任何一层都不能独占结论。
- **confidence**: high as an interpretive gate.

## DLR-13 复合课体必须逐条件命中

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-044`, `DLQ-045`, `DLQ-046`
- **normalized_lines**: L8404, L9416, L11402
- **required_adapter_fields**: `pattern_candidates`, `matched_conditions`, `unmatched_conditions`, `year_month_life_horses`, `transmission_elements`, `xunding`, `tianma`, `transmission_overcomes`, `general_overcomes`, `stem_branch_tombs`
- **preconditions**: 用户或下游想标记官爵、游子、殃咎等课经复合课体。
- **execution**:
  1. 为每个课体读取原文列出的全部必要条件。
  2. 只有必要条件全部命中才设 `pattern_confirmed=true`。
  3. 条件部分命中只能输出 `pattern_candidate`，列出缺项。
  4. 课名确认后仍进入 DLR-12，不直接映射具体事件。
- **decision_effect**: 防止凭一个驿马、三传皆土或一处克战误报复合课体。
- **stop_or_exception**: 原文条件表尚未建立的课体不得从名称猜测，应回到卷段检索。
- **conflicts**: 课经各卷不是一个可随意关键词匹配的断语库。
- **confidence**: high for the gate; only three example patterns are carded here.

## DLR-14 毕法目录必须回查正文

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-047`, `DLQ-048`, `DLQ-049`, `DLQ-050`, `DLQ-053`
- **normalized_lines**: L12702, L12756, L12764, L12768, L13328
- **required_adapter_fields**: `bifa_rule_number`, `bifa_heading`, `bifa_body_anchor`, `matched_conditions`, `counter_conditions`, `question_domain`, `chart_facts`
- **preconditions**: 想调用毕法赋中的某一法。
- **execution**:
  1. 目录短句只用来定位法号，不直接执行。
  2. 必须加载对应逐法正文，抽取前置条件、例外和反例。
  3. 将 adapter facts 与正文条件逐项匹配，再输出是否适用。
  4. “非占现类勿言之”要求结论与当前问题域相关，不把盘上所有象全说一遍。
- **decision_effect**: 使毕法从口号索引变成有正文证据的条件判断。
- **stop_or_exception**: 找不到正文锚点、法号落在 51/53 编号异常附近或条件未全时停止，不猜法号。
- **conflicts**: 目录连续出现两个“第五十三法”，见 DLQ-051/DLQ-052。
- **confidence**: high as a lookup gate; individual hundred rules are not exhaustively carded.

## DLR-15 来源层与卷号守门

- **source_layer**: `siku_editorial_preface` + `modern_synthesis`
- **quote_id**: `DLQ-001`, `DLQ-004`, `DLQ-023`, `DLQ-024`, `DLQ-051`, `DLQ-052`
- **normalized_lines**: L3, L5470, L5472, L12722, L12724
- **required_adapter_fields**: `evidence_quote_ids`, `normalized_anchors`, `source_layers`, `edition_id`, `volume_numbering_system`, `witness_locators`, `unresolved_conflicts`
- **preconditions**: 准备引用本书、声称某卷内容或把规则写入用户答案。
- **execution**:
  1. 每个主张绑定 quote ID、normalized 行号和 source layer。
  2. 卷号必须标 `normalized` 或 `WYG/Kanripo`。
  3. 命中冲突项时并列展示证据和当前处理状态。
  4. 未完成影印页映射时只给电子行号或 Kanripo 页叶，不伪造扫描页。
- **decision_effect**: 输出可审计引用和版本边界。
- **stop_or_exception**: 无证据锚点的候选只能进 `validation.md`，不得成为 authoritative rule。
- **conflicts**: normalized 与 WYG 卷序、兵占容器、毕法编号和分野卷次均存在未决问题。
- **confidence**: high.

## DLR-16 旺衰分别约束数量与迟速

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-054`, `DLQ-055`, `DLQ-056`, `DLQ-060`, `DLQ-061`, `DLQ-062`, `DLQ-063`, `DLQ-064`, `DLQ-066`
- **normalized_lines**: L4098, L4102, L6914
- **required_adapter_fields**: `question_domain`, `month_branch`, `initial_transmission`, `initial_strength`, `target_relative`, `target_branch`, `target_strength`, `strength_profile`
- **preconditions**: 已确定发用、月令旺相休囚死口径；若判断多少，还必须先按问题确定类神或六亲。
- **execution**:
  1. 应期只以发用旺相为相对较速、休囚死为相对较迟；没有另一个应期锚点时不得擅定“几天内”或具体日期。
  2. 数量只看当前问题类神的旺衰：旺相倾向较多，休囚死倾向较少；不得拿发用旺衰代替财爻旺衰。
  3. 干支进入三传时增加一个相对催速信号；它与发用休囚的迟信号并存时输出 `mixed`，不得静默择一。
  4. 同时输出所用月支、五行季节表、发用和类神各自旺衰，避免把“迟”误写成“少”。
- **decision_effect**: 形成相对数量与相对迟速两个独立信号。
- **stop_or_exception**: 类神缺失、月令季节表不明或没有具体问题对象时，数量层返回 `relative_quantity_unresolved`；无应期锚点时具体日历窗口返回 `calendar_window_unresolved`。
- **conflicts**: 原文另有发用占时、太岁、月建、候气等具体应期法；本卡不能越过那些条件，把旺衰一项当完整应期算法。
- **confidence**: high for relative quantity/speed; guarded for calendar timing.

## DLR-17 三传递生必须检查最终与日干关系

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-057`, `DLQ-058`
- **normalized_lines**: L8756, L8758
- **required_adapter_fields**: `three_transmissions`, `transmission_relations`, `day_stem`, `final_to_day_relation`, `xunkong`, `punishments`, `clashes`, `harms`, `strengths`
- **preconditions**: 三传及日干五行均由已验证事实层给出。
- **execution**:
  1. 逐项核对初传到中传、中传到末传的生克关系。
  2. 若初生中、中生末，再检查末传与日干；末生日干才可进入亨通候选。
  3. 若初生中、中生末而末克日干，标记 `generation_chain_ends_in_day_overcome`，解释为过程向前传递但最终压力落到问课人，不得只凭递生断顺遂。
  4. 再以后续空破刑害和旺衰作限制，不把本结构机械映射成某个现实事件。
- **decision_effect**: 区分“递生终于扶日”与“递生终于克日”，形成过程及收尾方向。
- **stop_or_exception**: 任一传支、日干或关系字段缺失时停止本卡，不由语言模型补算。
- **conflicts**: “恩多怨深”是原文象义标签；公开回答应翻译到当前问题，不照抄为人际怨恨。
- **confidence**: high.

## DLR-18 传统数目只能先给数目族

- **source_layer**: `compendium_body`
- **quote_id**: `DLQ-055`, `DLQ-059`, `DLQ-065`
- **normalized_lines**: L4102, L5348, L12164
- **required_adapter_fields**: `question_domain`, `initial_source_lesson`, `upper_number`, `lower_number`, `operation`, `base_number`, `initial_strength`, `real_world_scale`
- **preconditions**: 初传能唯一回指发用课，且上下神传统数值和运算可追踪。
- **execution**:
  1. 依据发用课上下神形成传统基数，并记录乘除过程和旺衰增减方向。
  2. 《杂状课》的“旺相倍数、休囚减之”与兵数段“旺则进、相则倍、休言本数、死减半”语境不一；未完成跨段裁定前只记录冲突，不实际套乘数。
  3. 基数只定义候选数目族；回答货币时，`30`、`300`、`3000`、`30000` 等量级不能由同一古法基数自行选择。
  4. 若用户没有提供已知款项级别、合同金额、工资档位或同类历史样本，公开回答只可给相对多少和传统数目族，并明确量级未定。
  5. 只有具备现实尺度或经留出样本校准的映射，才可给货币区间；校准数据必须与本次个案分离。
- **decision_effect**: 保留古籍数目法，同时阻止伪精确金额。
- **stop_or_exception**: 发用不能唯一回课或传统数值表缺失时返回 `number_family_unresolved`；现实尺度缺失时返回 `currency_magnitude_unresolved`。
- **conflicts**: 数值表在本书部分段落用于兵数，跨占类使用须保留来源语境；DLQ-059 支持一般数目/日期例，却不自动证明现代货币量级。
- **confidence**: medium for cross-domain number family; low until calibrated for currency magnitude.

## 规则覆盖声明

- 已卡片化：起课事实门、寄宫、贼克、比用、涉害、遥克、昴星、别责、八专、伏吟、返吟、天乙 profile、解释次序、复合课体门、毕法检索门、来源层门、数量迟速、三传递生终局、传统数目族边界。
- 未卡片化：卷一全部神煞表、卷二每个类神、卷五全部兵占、卷六全部分野、课经全部课体、毕法全部一百法正文。
- 未卡片化不等于来源缺失；只表示尚未满足逐条来源、前置条件、执行、停止和 adapter 字段要求。
