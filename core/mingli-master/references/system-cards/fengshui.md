# 风水 (fengshui)

## Executable provider boundary

The runtime route is `observation_driven_ready` and uses `scripts/reading_engine/fengshui.py`; the generic validated-user-chart path is forbidden. It normalizes caller-supplied compass measurements with the versioned north-centred, half-open 24-mountain engineering convention and keeps raw measurement, explicit correction, wrap history and uncertainty. It does not look up declination or silently normalize invalid raw degrees.

`form` and `liqi` are separate. Form rules activate only from eligible supplied observations and only inside the declared residential/site/burial source layer. Layout provenance is kind-scoped: room/zone nodes and partition-door boundaries require an accepted `layout` observation, while an unrelated road/water/terrain observation cannot be reused as layout proof. An unmeasured partition door remains non-blocking for a form-only request and becomes critical only when the selected Liqi calculation needs its direction. The only calculated Liqi school in this release is residential Bazhai, using an explicitly measured entrance/door trigram as the source-bound游年 origin; the sitting trigram is never substituted for that door measurement. Building period data is retained but cannot activate Xuankong; Xuankong, Sanhe and mixed-school requests fail closed. Image facts must be caller transcriptions with a hash-pinned asset id, normalized region anchor, enumerated quality and uncertainty; the provider performs no vision and emits no吉凶/outcome verdict.

When a declared sitting/facing pair conflicts with a usable measurement, the conflict remains blocking until the user explicitly confirms one measurement id. That confirmation makes the selected measurement authoritative for calculation while retaining the overridden declaration as a non-blocking audit record; it never silently erases the discrepancy.

Evidence is eligible only when both the fact-layer status and the exact pack-qualified rule id match `output.active_source_rule_ids`. A local id such as `YZS-R003` never matches a rule from another pack.

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `fengshui/dili-bianzheng` | 地理辨正 | 玄空理气、雌雄、金龙、血脉、三叉、天元/人元/地元等概念索引; 与《青囊经》《青囊序》《天玉经》对读，辨蒋大鸿注解层; 风水理气派与形势派冲突时的理气侧证据 | 直接替代罗盘坐向计算; 对具体阴宅阳宅作吉凶承诺; 不拆经注层时回答精确版本校勘问题 | CTP 行表 301 行已抽取；quote-index 短引 exact-ish 命中。 |
| `fengshui/dutian-baozhao-jing` | 都天宝照经 | 玄空理气源流中的山水、龙穴、坐向与水法术语索引; 都天大卦、天元/地元/人元、五吉星、城门、零正神相关文献锚点; 与《青囊序》《天玉经》《地理辨正》的依赖关系与冲突标注 | 实地阴宅/阳宅吉凶判断; 罗盘度数、坐向、来龙去水、挨星或城门诀的 LLM 手算; 把古代富贵贫贱、伤亡、官禄等断语用于现代个案 | 本 pack 以 NCC「陽宅堪輿古文 - 都天寶照經」单页 HTML 为临时全文底本，页面题署含 「都天寶照經 地理辨正疏 - 蔣大鴻」。原文分上篇、中篇、下篇。网页授权与底本系统未完全核实， 后续必须与《地理辨正》刊本/影印本校勘。题杨筠松口授、黄妙应笔录之归属按传统题名处理，不作史实断定。 |
| `fengshui/hanlong-jing` | 撼龙经 | 形势派九星龙脉体系（贪巨禄文廉武破辅弼）; 峦头形势核心范式（高山落脉、平洋寻龙、星峰辨认）; 九星形态学与穴形对应 | 排盘/起卦/择日事实计算（不替代工具）; 风水坐向实际测量（不替代 tool.fengshui.luopan）; 罗盘度数手算（严格禁止 LLM 手算坐向） | 题唐·杨筠松（救贫先生）撰，《钦定四库全书》子部·术数类·相宅相墓收录， 与《疑龙经》《葬法倒杖》合刊。本 pack 取四库本（维基文库整理）为底本， 专论山陇落脉形势，分贪狼、巨门、禄存、文曲、廉贞、武曲、破军、左辅、右弼 九星各为之说。 作者归属与版本流传仍有争议；李国本旧注庸陋已删；source_status 维持 partial 待四库影印逐段复核。 |
| `fengshui/huangdi-zhaijing` | 黄帝宅经 | 早期相宅/阳宅源流、二十四路阴阳宅法、修宅次第与生气死气方 | 替代罗盘坐向/建筑测量; 与八宅游年、玄空飞星、形峦派混为同一体系 | 维基文库《宅经（四库全书本）》完整文本；旧题黄帝，四库提要认为依托。 |
| `fengshui/qingnang-aoyu` | 青囊奥语 | 青囊系玄空/理气术语溯源; 二十四山、雌雄、金龙、城门、天心十道、向放水、进退旺等短句定位; 与《青囊序》《天玉经》《都天宝照经》《地理辨正》对读 | 替代罗盘坐向、元运、挨星或水法计算; 直接为现实住宅/墓地断吉凶; 把短篇口诀当作可手算流程 | 维基文库单篇完整文本；旧题杨筠松按传统题名记录，作者归属与版本系统保守标注。 |
| `fengshui/qingnang-jing` | 青囊经 | See index.md | See safety-and-versioning.md | 短篇经文但版本众多、注本繁杂（蒋大鸿注、张心言疏等），白文文字差异较小但段落分章不一；必须明确底本与是否含注疏。 |
| `fengshui/qingnang-xu` | 青囊序 | 理气派"看雌雄""认金龙""察血脉"水法源头; 二十四山阴阳顺逆与四十八局体系; 山龙水龙各管一路（"山管山兮水管水"） | 排盘/起卦/择日事实计算（不替代工具）; 风水坐向实际测量（不替代 tool.fengshui.luopan）; 罗盘度数手算（严格禁止 LLM 手算坐向） | 题唐·曾文迪（曾求己）作，紧承《青囊经》而立。本 pack 取维基文库通行本为底本， 并以蒋大鸿《地理辨正》所收本与各家校本为对校系统。全书为通篇韵文，无显式 分章；本 pack 按文意分为 8 个 stanza 作为 chapter-map 条目。 作者归属、与《青囊奥语》《天玉经》《都天宝照经》合刊关系待考；source_status 维持 par... |
| `fengshui/rudi-yan-quanshu` | 入地眼全书 | 龙砂水向全流程、形峦与理气合参、入首/祖宗/父母山、水法形象优先、阳宅门路灶宫星 | 替代实地踏勘、罗盘测量或地形数据; 单凭文字为现实墓宅定吉凶; 把龙砂水向阳宅跨层混用 | 维基文库完整单页整理本；龙、砂、水、向、阳宅多层混排，须按层读取。 |
| `fengshui/shenshi-xuankong-xue` | 沈氏玄空学 | 玄空飞星、九运挨星、下卦起星、到山到向、上山下水等术语解释; 阴宅/阳宅案例中的山向、运星、旺衰、反吟伏吟等文本证据定位; 与《地理辨正》《天玉经》《青囊》系文献对读 | 现实住宅/墓地吉凶硬断; 投资、迁居、医疗、寿夭、灾祸等现实决策; 把 image_only 图表页当成已结构化规则 | 158 个章节页已缓存原始 HTML；147 个有正文，11 个 image_only/section-title 章节以 skipped 计入覆盖。 短引均取自 normalized source。 |
| `fengshui/tianyu-jing` | 天玉经 | 玄空理气的三卦、父母卦、东西南北卦框架; 天卦/地卦/玄空卦/挨星的术语溯源; 二十四山、零正神、双山三合、四龙折水的文献锚点 | 实地风水勘测或住宅建议; 罗盘度数、坐向、水口、挨星飞排的 LLM 手算; 把富贵贫贱等古代评价语作现代决定论陈述 | 本 pack 取维基文库《天玉經內傳》与《天玉經外編》raw 导出为 canonical fulltext；文本含经文与吴公等注释性文字， 使用时必须区分“经文口诀层”“外编层”和“注解阐释层”。四库/CTP/Internet Archive 影印仅作对校锚点。 题唐杨筠松撰之归属有争议；本 pack 仅按传统题名入库。 |
| `fengshui/xuexin-fu` | 雪心赋 | 風水形勢/巒頭法的入門原典參考; 水口、明堂、來龍、分合、向背、五星、水法、龍穴真假等術語解釋; 與《葬書》《撼龍經》《疑龍經》對讀，作形勢法旁證 | 現代住宅/墓地的即時吉凶判定; 替代實地勘察、測量、法規與安全評估; 理氣羅盤計算 | normalized 為白文轉錄，仍待與書格/Commons 影印逐字校。 |
| `fengshui/yangzhai-sanyao` | 阳宅三要 | See index.md | See safety-and-versioning.md | normalized 为翻印文字页，含后人补充；清光绪 PDF 仅作影印锚点且尚未 OCR，不可称为逐字清刊校本。 |
| `fengshui/yangzhai-shishu` | 阳宅十书 | 阳宅外形/宅内形、福元、东四西四、大游年、穿宫分房、开门修造、放水、选择与符镇的原典证据; 与《黄帝宅经》《阳宅三要》对读 | 替代罗盘坐向/户型测量/排水测量/择日历算; 让语言模型手算福元、游年、门光星、太阴太阳过宫; 执行或转写符镇符形 | 《钦定古今图书集成》所收《阳宅十书一至四》；第十《论符镇》与多处宅图含图像资产，fulltext 只保留 IMAGE 锚点，不转写符形。 |
| `fengshui/yilong-jing` | 疑龙经 | 形势派寻龙辨穴疑难判别（干枝辨、背面辨、真假辨、形穴辨）; 撼龙经九星理论的辨证应用与穴法补充; 公位、阳宅阴宅、嗣续等专题疑问之文化研究 | 风水坐向实际测量（不替代 tool.fengshui.luopan）; 阴宅选址实务决策（不替代 tool.fengshui.terrain 与现场踏勘）; 现代殡葬与公共政策依据 | 题唐·杨筠松（传）撰，《钦定四库全书》子部术数类收录。 本 pack 取维基文库整理本（CC BY-SA 4.0；古籍原文公有领域）。 全书结构：上篇 / 中篇 / 下篇 / 附《疑龙十问》/ 附《卫龙篇》/ 附《变星篇》。 与《撼龙经》合刊版本居多，本 pack 仅处理疑龙经部分。 《疑龙十问》部分通行本作正文附录，本 pack 单独切分为 10 章... |
| `fengshui/zangfa-daozhang` | 葬法倒杖 | 阴宅穴法、圆晕/金鱼水界、两仪四象、盖粘倚撞、倒杖十二法、二十四砂葬法的原典证据; 与《葬书》《撼龙经》《疑龙经》《入地眼全书》对读 | 阳宅风水、择日、玄空理气、罗盘坐向计算; 缺现场来龙、砂水、明堂、四兽、地形事实层时直接断吉凶; 现代墓地处置/施工/法律建议 | 维基文库《撼龍經/葬法倒杖》6 个章节页完整入库；旧题唐·杨筠松。第 34 行 `高$山陰龍`、第 67 行 `浮□`、第 110 行 `登□□望龍` 保留为校勘风险，不作模型补字。 |
| `fengshui/zangshu` | 葬书 | 形势派阴宅葬法源流与"乘生气"核心命题; 形—势—气—理一体框架（藏风得水、外气内气、形止气蓄）; 山形吉凶判断（童、断、石、过、独五不可葬） | 排盘/起卦/择日事实计算（不替代工具）; 风水坐向实际测量（不替代 tool.fengshui.luopan）; 罗盘度数手算（严格禁止 LLM 手算坐向） | 托名晋·郭璞，今传本主要由宋元以后整理。本 pack 取《地理眞詮》一集所收《葬书》本（吴澄删定本，分内篇、外篇、雜篇共 8+2 篇约 1246 字）为底本， 并以《钦定四库全书》子部·术数类·相宅相墓本为对校系统。 作者归属、篇章删定、版本流派均存在争议；蔡季通去十二存其八，吴澄草庐先生再删定为今本。 四库本影印逐段复核尚未完成，source_sta... |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.
