---
slug: liuren-miben
file: rules
rule_count: 20
source_status: complete_text
---

# 《大六壬秘本》Evidence-Linked Rule Cards

> 本书是类象、歌赋、五要权衡与专项占法的补充层，不是确定性起课实现。每张卡只消费已经验证的 adapter 字段；任何月将、天地盘、四课、三传、天将、旬空或课名都不得由语言模型自由手算。

## LM-R00 确定性课盘输入门

- **system**: `san-shi / daliuren`
- **source_location**: fulltext.md L2968-L2982, L3886-L3900
- **source_layer**: `transmitted_body` + `mixed_body_commentary`; 本卡的停止条件是 reference-pack 执行政策
- **quote_id**: LM-Q035, LM-Q052, LM-Q053
- **preconditions**: 用户要求具体起课、断某一件事或把本书规则套入实际盘。
- **required_fields**: `query_time`, `timezone`, `calendar_policy`, `day_pillar`, `hour_pillar`, `month_general`, `earth_plate`, `heaven_plate`, `four_lessons`, `three_transmissions`, `heavenly_generals`, `xunkong`, `rule_profile`, `guiren_profile`, `validation_status`
- **execution**:
  1. 校验 adapter 名称、版本、输入和 `validation_status=pass`。
  2. 核对日时干支、月将与盘式字段来自同一次计算。
  3. 只读取 adapter 输出，不从本书课名描述反推四课三传。
  4. 字段完整后才进入其余规则卡。
- **decision_effect**: 建立唯一、可复算的事实层；本卡本身不输出吉凶。
- **stop_conditions**: 任一必需字段缺失；历法边界未声明；盘面内部不一致；adapter 仅给自然语言结论而无结构化事实。
- **exceptions**: 纯粹询问书中术语、版本或类象时，可不要求实际课盘，但必须标 `textual_lookup_only`。
- **conflicts**: 卷十三、卷十五的课名异文不得覆盖 adapter profile。
- **adapter_fields**: 上述全部字段。
- **confidence**: high for source workflow; chart correctness depends on adapter validation.

## LM-R01 类象采用“神/将 + 所临 + 状态”组合

- **system**: `san-shi / daliuren / imagery`
- **source_location**: fulltext.md L82-L359, L600-L771
- **source_layer**: `transmitted_body`
- **quote_id**: LM-Q003, LM-Q007, LM-Q013, LM-Q014
- **preconditions**: 查询本书某月将、天将、地支或八卦的传统类象；若用于实际盘，LM-R00 已通过。
- **required_fields**: 文本查询需 `symbol_type` 与 `symbol`；实际盘另需 `landing_branch`, `heavenly_general`, `strength_state`, `question_domain`。
- **execution**:
  1. 先确定类象层：卷一月将、卷二天将、卷五天官加辰、卷六八卦将神。
  2. 只检索与输入层完全匹配的条目。
  3. 实际盘至少组合“神/将、所临、旺衰/空陷、所问事项”四项。
  4. 多个条目冲突时并列，不以单一词条压过课传主结构。
- **decision_effect**: 输出 `imagery_candidates[]` 及每项来源，不直接生成事实结论。
- **stop_conditions**: 不知道符号属于哪一层；实际盘缺所临或旺衰；试图把一个地支的所有类象同时套用。
- **exceptions**: 纯词义检索可只返回原书条目。
- **conflicts**: 同一支在不同卷、不同天将下有多重类象，这是条件差异，不自动合并为同义。
- **adapter_fields**: `heaven_plate`, `heavenly_generals`, `strength_state`。
- **confidence**: high for lookup; low for any uncorroborated real-world identification.

## LM-R02 卷三神煞只作同书查表证据

- **system**: `san-shi / daliuren / shensha`
- **source_location**: fulltext.md L360-L376
- **source_layer**: `transmitted_body`
- **quote_id**: LM-Q008
- **preconditions**: 用户明确查询本书卷三六旬表，或 adapter 已按同一来源 profile 输出对应神煞。
- **required_fields**: `day_xun`, `day_pillar`, `shensha_profile`, `computed_shensha[]`。
- **execution**:
  1. 仅在六旬对应行内核对仪神、丁神、天中、奇神、闭口、五亡等。
  2. 标记 `source_book=liuren-miben` 与行号。
  3. 只作为课传解释的辅证或冲突提示。
- **decision_effect**: 输出 `corroborating | conflicting | unresolved`，不改变初传或课名。
- **stop_conditions**: 旬首不明、profile 不明、试图把卷三神煞跨移到八字/择日或让神煞单独下断。
- **exceptions**: 文献比较可直接列六旬表异文。
- **conflicts**: 其他六壬书神煞表不一致时保留双来源，不自动覆盖。
- **adapter_fields**: `day_xun`, `xunkong`, `computed_shensha`。
- **confidence**: high for transcription lookup; effectiveness not validated.

## LM-R03 射覆先看日辰层与发用，再评旺衰

- **system**: `san-shi / daliuren / shefu`
- **source_location**: fulltext.md L377-L425
- **source_layer**: `transmitted_body`
- **quote_id**: LM-Q009, LM-Q010, LM-Q011
- **preconditions**: 问题明确为射覆/传统物类推演，且 LM-R00 已通过。
- **required_fields**: `day_stem_yinyang`, `day_upper`, `branch_upper`, `initial_transmission`, `initial_landing`, `five_phase`, `strength_state`, `void_status`, `question_time`。
- **execution**:
  1. 刚日读取日上神，柔日读取支上神，并记录发用。
  2. 以初传为主要射覆入口；中末不用于卷四“用传”这一特定步骤。
  3. 结合初传所临日辰、旺相休囚与五行类，生成候选物类。
  4. 再进入形色、新旧、生死、表里等次级字段。
- **decision_effect**: 生成有来源的 `object_class_candidates[]`，并按字段支持度排序。
- **stop_conditions**: 无正式课盘；发用不明；旺衰 profile 不明；用户把结果要求为视觉识别的确定答案。
- **exceptions**: 研究卷四文义时可不执行，只解释先后顺序。
- **conflicts**: “中末总弃”只限定卷四射覆用传，不得扩展成所有大六壬断法都忽略中末。
- **adapter_fields**: 日干阴阳、日/支上神、初传、所临、旺衰、空亡。
- **confidence**: high for textual procedure; outcome confidence is inherently low.

## LM-R04 射覆遇空须先判断“有无”，再谈物类

- **system**: `san-shi / daliuren / shefu`
- **source_location**: fulltext.md L427-L437
- **source_layer**: `transmitted_body`
- **quote_id**: LM-Q012
- **preconditions**: LM-R03 已进入射覆解释，adapter 已给发用和空亡状态。
- **required_fields**: `initial_transmission`, `initial_void`, `landing_void`, `tiankong_present`, `source_direction_void`。
- **execution**:
  1. 先判断发用、所临和来方是否落空。
  2. 若多重空象成立，返回 `absence_or_deception_candidate`。
  3. 只有未触发停止条件时才继续物类、形色和味道匹配。
- **decision_effect**: 阻止在“有无尚未成立”时强行猜物。
- **stop_conditions**: 空亡字段缺失；来方不明却硬套“空方来”；试图把空亡等同绝对不存在。
- **exceptions**: 本书自身也在卷十五对不同事项给出空亡例外，跨卷使用时须加载 LM-R10。
- **conflicts**: 卷四的射覆空象与卷十五的事项空亡不是同一粒度。
- **adapter_fields**: 旬空、天盘落空、天空、方向。
- **confidence**: medium-high for source rule, low for empirical object inference.

## LM-R05 旺衰 profile 必须显式，不得混算

- **system**: `san-shi / daliuren / strength`
- **source_location**: fulltext.md L772-L830, L2864-L2890, L4994-L5000
- **source_layer**: multiple `transmitted_body` layers
- **quote_id**: LM-Q017, LM-Q029, LM-Q061
- **preconditions**: 任何规则使用旺、相、死、休、囚。
- **required_fields**: `strength_profile`, `seasonal_qi`, `day_stem`, `target_phase`。
- **execution**:
  1. 记录所用口径：四时旺衰、两干/两日圆机，或其他已验证 profile。
  2. 同一判断只用一个主 profile；其他口径作为 conflict/variant 旁证。
  3. 输出 profile 名称和来源行。
- **decision_effect**: 产生可审计的 `strength_state`，避免同一元素被同时判旺与囚。
- **stop_conditions**: adapter 未声明 profile；语言模型自行按季节/日干混合推算；把卷七“两日轮转”当全体系唯一口径。
- **exceptions**: 版本研究可并列三处说法而不执行。
- **conflicts**: 本书内部至少并存四时定理和逐日圆机，见 conflict-notes。
- **adapter_fields**: `strength_profile`, `strength_state_by_symbol`。
- **confidence**: high for detecting source conflict; no claim that one profile is empirically superior.

## LM-R06 类神须经空旺、生克与课传共同复核

- **system**: `san-shi / daliuren / specialty`
- **source_location**: fulltext.md L1474, L5182-L5188
- **source_layer**: `transmitted_body` + `mixed_body_commentary`
- **quote_id**: LM-Q019, LM-Q063
- **preconditions**: 已按问题域确定类神，LM-R00 已通过。
- **required_fields**: `question_domain`, `class_deity`, `class_deity_location`, `void_status`, `strength_state`, `three_transmissions`, `relations`, `combinations`, `harms`。
- **execution**:
  1. 先确认类神与问题对象匹配。
  2. 检查类神是否空、旺相或为日鬼，以及三传上下生克、三合六合、刑害。
  3. 只有结构同向时才提高该类象权重。
  4. 条件相反时输出冲突，不用类神单句压过课传。
- **decision_effect**: 形成 `class_deity_weight` 和支持/反对证据表。
- **stop_conditions**: 类神选择无出处；只有类神名称而无落宫/状态；把歌诀“须成/不遂”改写成事实保证。
- **exceptions**: 纯文本查询可列本书类神表而不加权。
- **conflicts**: 不同卷可能为同一事项列不同类神，按问题细分并保留来源。
- **adapter_fields**: 类神落宫、空旺、生克、合害、三传。
- **confidence**: medium; the combination rule is textually supported, predictive validity untested.

## LM-R07 “全吉/全凶”标签后仍须检查鬼、救与空

- **system**: `san-shi / daliuren / weighting`
- **source_location**: fulltext.md L1811-L1835
- **source_layer**: `transmitted_body` + `mixed_body_commentary`
- **quote_id**: LM-Q022, LM-Q023, LM-Q024
- **preconditions**: adapter 或上游解释给出“多吉/多凶”的初步标签。
- **required_fields**: `three_transmissions`, `day_relation`, `ghost_strength`, `rescue_deity`, `rescue_reachability`, `void_status`。
- **execution**:
  1. 即便三传多吉，仍检查是否有旺鬼克日。
  2. 有救神时检查其距离、旺衰、空陷和是否能实际制化。
  3. 吉凶遇空时降低“已经落实”的置信度。
  4. 输出“主象 + 反证 + 是否被制”的三栏结果。
- **decision_effect**: 防止把多个吉词或凶词简单计票。
- **stop_conditions**: 救神字段不存在却宣称“有救”；只凭神将名称判断强弱。
- **exceptions**: 无实际盘的古文解释只说明这一权衡原则。
- **conflicts**: 其他卷若给出特定事项例外，按原来源并列。
- **adapter_fields**: 三传关系、鬼/救、旺衰、空亡。
- **confidence**: high as an internal anti-simplification rule.

## LM-R08 吉将受伤与凶神受制会改变作用

- **system**: `san-shi / daliuren / generals`
- **source_location**: fulltext.md L2150-L2162
- **source_layer**: `transmitted_body` + `mixed_body_commentary`
- **quote_id**: LM-Q027
- **preconditions**: 已有天将、所乘神、旺衰与生克事实。
- **required_fields**: `heavenly_general`, `general_valence_in_book`, `general_strength`, `general_is_damaged`, `general_is_controlled`。
- **execution**:
  1. 不以“吉将/凶将”名称直接计分。
  2. 吉将受克、休败或落空时降低其支持度。
  3. 凶将被制且无同向凶结构时降低其阻碍度。
- **decision_effect**: 输出修饰后的 `general_effect`，而不是固定吉凶标签。
- **stop_conditions**: 无所乘/所临关系；把“凶神受制”扩大成必然成功。
- **exceptions**: 特定分门另有明确例外时必须带该分门来源。
- **conflicts**: 各书对某将吉凶角色可能不同，保留 book profile。
- **adapter_fields**: 天将、旺衰、生克、空陷。
- **confidence**: high for textual principle, medium for any applied weighting.

## LM-R09 五要权衡先分类，再判断

- **system**: `san-shi / daliuren / five-essentials`
- **source_location**: fulltext.md L3105-L3185
- **source_layer**: `transmitted_body`，L3183-L3185 含金氏增录提示
- **quote_id**: LM-Q039-LM-Q043
- **preconditions**: 需要用卷十四解释具体问题，LM-R00 已通过。
- **required_fields**: `question_domain`, `actor_roles`, `day_branch_roles`, `inner_outer`, `host_guest`, `strength_state`, `void_status`, `relations`。
- **execution**:
  1. 从三十类中只选择与问题有关的维度，不全量堆叠。
  2. 先定彼此/主客/内外/尊卑，再定天时、地利。
  3. 再看喜忌、虚实及后续动静始终。
  4. 每一维只引用能被 adapter 字段支持的原文。
- **decision_effect**: 生成 `selected_dimensions[]` 和有序解释计划。
- **stop_conditions**: 主客角色不明；把“三十类”当三十个必须同时命中的神煞；缺事实字段仍强行解释。
- **exceptions**: 只查术语时可返回维度定义。
- **conflicts**: 同一干支角色会随“我去见人/人来见我”变化，不能复用静态映射。
- **adapter_fields**: 日辰、四课、三传、旺衰、空亡、关系矩阵。
- **confidence**: high as the book's organizing framework.

## LM-R10 课传既定后先审虚实，且空亡分阶段

- **system**: `san-shi / daliuren / void`
- **source_location**: fulltext.md L3187-L3195, L3564-L3638
- **source_layer**: `transmitted_body` + `mixed_body_commentary` + some Jin notes
- **quote_id**: LM-Q044, LM-Q051
- **preconditions**: adapter 已给旬空、落空/陷空和三传位置。
- **required_fields**: `xunkong`, `initial_void`, `middle_void`, `final_void`, `filled_by`, `question_domain`, `beneficial_or_harmful_relation`。
- **execution**:
  1. 区分旬空、天盘落空/陷空与填实。
  2. 分别记录初空、中空、末空，禁止压成单一布尔值。
  3. 对生我、救我和克我、害我的作用分别评估空亡影响。
  4. 卷十五事项例外只在对应问题域内使用。
- **decision_effect**: 输出 `void_effect_by_stage` 与例外来源。
- **stop_conditions**: 旬空算法/profile 不明；只凭“空亡”两个字断成或不成；混用其他术数的空亡。
- **exceptions**: 太岁、月将、月建、日时年命等是否填实按所用 adapter/source profile 明示。
- **conflicts**: 卷十三、十四、十五对空亡表述粒度不同，不能互相抹平。
- **adapter_fields**: 旬空、落空、填实、三传阶段、事项域。
- **confidence**: medium-high; many item-specific exceptions remain uncarded.

## LM-R11 先用干、三传生克和正时建立基础解释，再考虑变法

- **system**: `san-shi / daliuren / weighting`
- **source_location**: fulltext.md L3197-L3205, L3884-L3900
- **source_layer**: quoted lineage + `mixed_body_commentary`
- **quote_id**: LM-Q045, LM-Q052, LM-Q053
- **preconditions**: 盘面事实完整，准备加入聚散、初建复建或奇格。
- **required_fields**: `day_stem`, `day_upper`, `branch_upper`, `three_transmissions`, `query_hour`, `relations`。
- **execution**:
  1. 先以干为主，检查干支上神和三传生克。
  2. 写出基础路径后，才允许加载聚散、初建复建等变法。
  3. 若变法与基础结构冲突，标记冲突，不为追求“奇”而改写基础事实。
- **decision_effect**: 形成 `base_reading` 与可选 `variant_reading` 两层。
- **stop_conditions**: 基础字段尚未解释便直接堆叠奇格；变法无 adapter 支持。
- **exceptions**: 用户明确做版本/变法研究时可只解释变法，但不得称默认算法。
- **conflicts**: 卷十四同收复杂变法与“求奇反不奇”的自我约束，应同时保留。
- **adapter_fields**: 日辰、正时、三传关系。
- **confidence**: high as an internal anti-overfitting rule.

## LM-R12 动静与始终必须按多字段、三阶段表达

- **system**: `san-shi / daliuren / process`
- **source_location**: fulltext.md L3207-L3217
- **source_layer**: `transmitted_body`
- **quote_id**: LM-Q046, LM-Q047
- **preconditions**: 已有日辰和三传，问题包含进退、过程或结果。
- **required_fields**: `day_branch_state`, `three_transmissions`, `relations_by_stage`, `movement_markers`, `static_markers`。
- **execution**:
  1. 以日辰为静态基础，以三传为动态过程。
  2. 同时检查相生/克陷和动静标记，不能单取一项。
  3. 将初传写成发端，中传写成移易，末传写成归计。
  4. 每段列神将、生克、空墓和支持/阻碍，不把末传一句替代全过程。
- **decision_effect**: 输出三段式 `process_timeline`。
- **stop_conditions**: 缺中末传；只凭伏吟/马星断动静；把三段直接换算具体日期。
- **exceptions**: 纯术语解释可只返回三段定义。
- **conflicts**: 特殊课体会改变过程感，但不取消三传事实。
- **adapter_fields**: 三传、动静标记、生克、空墓。
- **confidence**: high for interpretive structure.

## LM-R13 迟速只作相对尺度，应期日期另行计算

- **system**: `san-shi / daliuren / timing`
- **source_location**: fulltext.md L3233-L3261, L4994-L5000
- **source_layer**: `transmitted_body` + examples
- **quote_id**: LM-Q048, LM-Q061
- **preconditions**: 用户询问快慢或应期，LM-R00 已通过。
- **required_fields**: `lesson_type`, `guiren_direction`, `initial_position_relative_to_day_branch`, `time_scale_markers`, `strength_profile`, `calendar_policy`。
- **execution**:
  1. 先输出相对尺度 `fast | slow | delayed | unresolved` 及支持项。
  2. 岁、月、旬、候、日、时等标记只定义候选窗口。
  3. 需要公历日期时调用历法 adapter 解析，不按文本自行换算。
  4. 多个尺度冲突时返回区间或未决，不选最戏剧性的一个。
- **decision_effect**: 生成相对时间判断和可复算候选窗口。
- **stop_conditions**: 缺占时或历法边界；课名来自未验证文本异文；要求凭一条歌诀精确到某日某时。
- **exceptions**: 文献研究可列原书应期例而不转为现代日期。
- **conflicts**: 卷十四和卷十七的时间口径用途不同，须标 source rule。
- **adapter_fields**: 课名、贵人顺逆、相对位置、历法窗口。
- **confidence**: medium; no empirical accuracy claim.

## LM-R14 合、鬼、墓等名称必须经过制化关系再解释

- **system**: `san-shi / daliuren / relations`
- **source_location**: fulltext.md L2994-L3048, L3139-L3185
- **source_layer**: `mixed_body_commentary` + `transmitted_body`
- **quote_id**: LM-Q036-LM-Q038, LM-Q043
- **preconditions**: adapter 已输出合、鬼、墓、刑冲破害及旺衰。
- **required_fields**: `relations`, `strength_state`, `rescue_relations`, `heavenly_generals`, `question_domain`。
- **execution**:
  1. 合先查是否带鬼、刑、破、克和吉助。
  2. 鬼先查日是否旺、是否有子孙/德合/制化、是否空陷。
  3. 墓先查日夜、入墓/覆生/墓求生及所问事项。
  4. 结果写为条件链，不写“见 X 必 Y”。
- **decision_effect**: 输出 `relation_effects[]`，每项附制化路径。
- **stop_conditions**: 只有关系名称无上下神；忽略旺衰和救制；将古文极端断语直接外推。
- **exceptions**: 纯术语或异文查询可展示原句。
- **conflicts**: 本书同一关系在不同事项可变义；跨书定义必须分 profile。
- **adapter_fields**: 关系矩阵、旺衰、天将、救神、问题域。
- **confidence**: high for conditionalization, medium for applied semantics.

## LM-R15 专项占法先路由到卷，不把相邻歌诀拼接

- **system**: `san-shi / daliuren / specialty-routing`
- **source_location**: fulltext.md L2407-L2863, L4495-L4981, L4982-L5332
- **source_layer**: `transmitted_body` + `mixed_body_commentary`
- **quote_id**: LM-Q028, LM-Q057-LM-Q059, LM-Q063-LM-Q064
- **preconditions**: 用户问题属于婚姻、疾病、出行、行人、谒人、诉讼、田产、宅舍、商贾、盗失、逃亡、假借等具体门类。
- **required_fields**: `question_domain`, `actor_roles`, `adapter_output`, `requested_source_book`。
- **execution**:
  1. 用 `chapter-map.md` 选唯一主卷/主节。
  2. 先应用通用权衡卡 LM-R09 至 LM-R14。
  3. 只加载该门类相邻完整段，不跨标题把歌诀拼成新规则。
  4. 记录未卡片化条目为 `text_lookup`，不伪装成已验证规则。
- **decision_effect**: 形成最小、可追踪的专项证据集。
- **stop_conditions**: 问题域不明；同时加载所有专项；把疾病/盗贼等古代断辞当现实证据。
- **exceptions**: 用户明确比较两个门类时可并列，但不得合成一个来源。
- **conflicts**: 卷十二、十六、十七可能重复同一事项，须分别保留卷次和条件。
- **adapter_fields**: 由所选门类决定；最低仍须满足 LM-R00。
- **confidence**: high for routing, variable for individual uncarded sayings.

## LM-R16 三才应事只能消费罡、魁、贵落处

- **system**: `san-shi / daliuren / sancai`
- **source_location**: fulltext.md L4982-L5000
- **source_layer**: `transmitted_body` + `mixed_body_commentary`
- **quote_id**: LM-Q060, LM-Q061
- **preconditions**: 用户明确采用卷十七三才应事，且 LM-R00 已通过。
- **required_fields**: `target=tian|ren|di`, `tiangang_landing`, `hekui_landing`, `guiren_landing`, `meng_zhong_ji_class`, `heaven_plate`, `heavenly_generals`。
- **execution**:
  1. 占天读取天罡落处，占地读取河魁落处，占人读取贵人落处。
  2. 仲取本位；孟、季按本书前/后五辰规则调用 adapter 函数。
  3. 从所得位置读取盘面和天将，再按本书例法解释。
- **decision_effect**: 输出 `sancai_target`, `response_position`, `evidence_path`。
- **stop_conditions**: 罡魁贵落处由模型心算；孟仲季方向函数未验证；把示例结论复制到不同盘。
- **exceptions**: 只解释三才文本时可展示流程而不执行。
- **conflicts**: 这是一项卷十七专法，不覆盖常规四课三传解释。
- **adapter_fields**: 天盘、天罡、河魁、贵人、孟仲季、天将。
- **confidence**: medium; textual steps clear, adapter implementation still required.

## LM-R17 课名段只作盘后释义，不参与起课

- **system**: `san-shi / daliuren / lesson-types`
- **source_location**: fulltext.md L2892-L2910, L4410-L4468
- **source_layer**: `mixed_body_commentary`
- **quote_id**: LM-Q030, LM-Q031, LM-Q055, LM-Q056
- **preconditions**: 确定性 adapter 已给 `lesson_type` 和生成路径，用户要查本书如何解释该课名。
- **required_fields**: `lesson_type`, `derivation_trace`, `rule_profile`, `source_comparison_requested`。
- **execution**:
  1. 先验证课名来自 adapter，不从本书文字反向生成。
  2. 展示卷十三与卷十五相关原句及其不一致。
  3. 只抽取盘后语义候选；算法定义以 adapter profile 为准。
- **decision_effect**: 生成 `post_chart_interpretation` 与 `textual_conflict`。
- **stop_conditions**: adapter 未给生成路径；要求按卷十三“始入/比邻/知一”直接重排三传；文本内部矛盾未显示。
- **exceptions**: 版本研究可不需要实际盘。
- **conflicts**: 卷十三 L2894-L2896 与卷十五 L4414-L4422及通行课名定义不一致；L4414 对返吟/伏吟“自克/不自克”也同句冲突。
- **adapter_fields**: 课名、生成分支、候选克、profile。
- **confidence**: high for identifying conflict; disabled for calculation.

## LM-R18 “两事之象”只生成复核标志

- **system**: `san-shi / daliuren / multiplicity`
- **source_location**: fulltext.md L3910-L3912
- **source_layer**: `mixed_body_commentary` + `scan_collated_junction`
- **quote_id**: LM-Q054
- **preconditions**: adapter 显示巳/亥、干支同出、或生干合支/生支合干的明确结构。
- **required_fields**: `branches_present`, `stem_branch_origins`, `generation_relations`, `combination_relations`。
- **execution**:
  1. 精确匹配书中列出的结构。
  2. 命中时只标 `dual_issue_candidate=true`。
  3. 回到用户问题检查是否确有两个对象、两条路径或两个阶段；没有现实对应则保持未决。
- **decision_effect**: 提醒模型主动检查“双对象/双过程”，不直接断定必有两件事。
- **stop_conditions**: 仅因出现巳或亥就断两事；忽略生合方向；未说明该句为影印补齐。
- **exceptions**: 版本校勘时可直接引用 NCL 第 179 页补字记录。
- **conflicts**: 其他书对“两事”条件不同则并列，不自动合并。
- **adapter_fields**: 支、干支来源、生合关系。
- **confidence**: medium; exact restored text, interpretive scope deliberately narrow.

## LM-R19 引文必须标来源层与校勘状态

- **system**: `corpus / evidence`
- **source_location**: fulltext.md L1-L3, L154-L160, L5335-L5354
- **source_layer**: pack evidence policy derived from explicit normalization and collation records
- **quote_id**: LM-Q001, LM-Q004, LM-Q066-LM-Q069
- **preconditions**: 输出任何本书引文、作者归属、影印页码或“古籍原文”判断。
- **required_fields**: `quote_id`, `normalized_line`, `source_layer`, `scan_page_if_verified`, `attribution_confidence`。
- **execution**:
  1. 在 `quote-index.md` 取 exact quote 和行号。
  2. 判断是传承正文、混排注层、金氏层、署名批注、抄录款还是现代校勘记录。
  3. 只有三处章界允许给已核影印页；其余页码返回 `not_page_collated`。
  4. 引文字符串命中与作者归属、术数有效性分开报告。
- **decision_effect**: 产生可审计的 `source_evidence[]`。
- **stop_conditions**: 用 normalized 行号按比例猜扫描页；把校勘记录当古籍原文；把未署名注语强归金正音。
- **exceptions**: 无。
- **conflicts**: 目录十七卷与馆藏二十卷元数据必须同时保留。
- **adapter_fields**: none; this is an evidence gate.
- **confidence**: high.

## LM-R20 求财必须先见财，再看旺空与凶将损耗

- **system**: `san-shi / daliuren / money`
- **source_location**: fulltext.md L4917-L4919
- **source_layer**: `transmitted_body` + `mixed_body_commentary`
- **quote_id**: LM-Q072, LM-Q073
- **preconditions**: 用户问具体求财/入账，LM-R00 已通过。
- **required_fields**: `three_transmissions`, `six_relatives`, `strength_profile`, `xunkong`, `heavenly_generals`, `question_domain`。
- **execution**:
  1. 先确认三传是否见妻财，以及财爻所在阶段、旺衰与空亡。
  2. 财爻出现且旺相不空，才形成较实的求财信号；仍不等于精确金额。
  3. 三传见玄武、白虎或天空时增加损耗/落空风险，但必须说明其所在阶段，不把将名写成具体故事。
  4. 与《指南》求财章及《大全》旺衰规则交叉后输出支持、损耗和未决项。
- **decision_effect**: 形成可追踪的求财支持与损耗修正。
- **stop_conditions**: 三传六亲、旺衰、空亡或天将缺失；只想凭青龙/玄武定金额。
- **exceptions**: 研究原文时可单列异文“無才/無財”，不能静默校改。
- **conflicts**: 凶将不能推翻旺相财爻，只能限定实得和风险。
- **adapter_fields**: 三传六亲、旺衰、空亡、天将。
- **confidence**: medium-high for textual synthesis; empirical outcome uncalibrated.

## LM-R21 发用分组取季支上神为候期支

- **system**: `san-shi / daliuren / timing`
- **source_location**: fulltext.md L3070-L3076
- **source_layer**: `mixed_body_commentary`
- **quote_id**: LM-Q070, LM-Q071
- **preconditions**: 用户问应期，发用、天地盘和民用日期均已验证。
- **required_fields**: `initial_transmission`, `heaven_plate`, `civil_datetime`, `day_ganzhi`。
- **execution**:
  1. 寅卯发用取辰上神，巳午取未上神，申酉取戌上神，亥子取丑上神；四季发用按原文各取下一季支上神。
  2. “上神”必须从本课已验证天地盘读取，不由语言模型心算。
  3. 以上神之支生成下一候选支日，并记录干支与公历换算。
  4. 该日只作为传统候期候选，与课体迟速、旺衰和专项末传合期并列。
- **decision_effect**: 产出一个可复算候期支和候选公历日。
- **stop_conditions**: 天地盘或公历日期缺失；上神读取失败；候选日期未通过干支序列校验。
- **exceptions**: 无民用日期时只返回候选支，不伪造公历日。
- **conflicts**: 与其他候期法不一致时并列，不静默择一。
- **adapter_fields**: 发用、天地盘、日干支、公历日期。
- **confidence**: medium; deterministic textual rule, empirical accuracy uncalibrated.

## LM-R22 文书消息以父母为类神并检查空旺

- **system**: `san-shi / daliuren / message-document`
- **source_location**: fulltext.md L1474, L1835, L2926
- **source_layer**: `transmitted_body` + `mixed_body_commentary`
- **quote_id**: LM-Q019, LM-Q024, LM-Q074
- **preconditions**: 用户明确问消息、回复、确认、批复、合同、协议、签字、盖章或其他文书结果，LM-R00 已通过。
- **required_fields**: `question_domain`, `three_transmissions`, `six_relatives`, `target_stage`, `strength_state`, `xunkong`, `relations`, `heavenly_general`。
- **execution**:
  1. 将父母六亲设为本问题的文书/消息类神，而不是把所有工作问题都固定成父母。
  2. 父母入三传且不空，形成事项有回应或落点的支持证据。
  3. 父母旺相形成较实支持；囚死或空亡形成明确反证；休气只作中性偏弱，不强定方向。
  4. 所乘天将只能说明呈现方式或成色，不能单独建立或翻转方向。
- **decision_effect**: 形成 `message_target_presence`, `message_target_strength` 和中性的天将修饰。
- **stop_conditions**: 问题不涉及消息/文书；父母六亲未由事实层计算；仅凭玄武、朱雀等单将编造具体回复内容。
- **exceptions**: 用户只问口头闲聊且没有确认、答复或文书含义时，不自动套用本卡。
- **conflicts**: 类神入传与类神囚死可同时成立，前者为主证，后者为反证，不相互删除。
- **adapter_fields**: 三传六亲、传位、旺衰、空亡、天将、五行关系。
- **confidence**: medium; source mapping is explicit, real-world accuracy remains uncalibrated.

## Rule Selection Order

1. 具体课先过 LM-R00。
2. 选问题域：类象/射覆用 LM-R01-LM-R05；专项先用 LM-R15，再按门类加载；求财加 LM-R20，应期加 LM-R21，文书消息加 LM-R22。
3. 通用权衡依次用 LM-R06-LM-R14。
4. 课名只在盘后使用 LM-R17。
5. 命中“两事”时加 LM-R18 复核，不直接扩写结论。
6. 所有输出最后过 LM-R19 引文门。
