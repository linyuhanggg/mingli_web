# 滴天髓阐微 — Rules

> 本文件抽取《滴天髓阐微》全书的可路由判断规则。
> **抽取层级约束**：仅从 [原]（京图原文+原注）与 [任注]（任铁樵注）抽取；[案例] 仅作 quote-index 引用，不上升为规则。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `source_layer` / `applicable_to` / `caveats` / `verification_status`。
> `source_layer` 取值：`原` / `任注` / `原+任注`。
> 全部 `pending_verification`（normalized 文本与权威影印未逐章复核）。
> rule_id 前缀 `DR` = Ditiansui Rule。

---

## DR-01-01 三元一统

- **rule_statement**：干为天元，支为地元，支中所藏为人元；论命三元一统，以日干为我，旁参支藏。
- **source_chapter**：tongshen/01-tiandao
- **source_layer**：原+任注
- **applicable_to**：基础理论
- **caveats**：理论铺垫；具体到取用必转入第十七章衰旺。
- **verification_status**：pending_verification

## DR-01-02 五气偏全

- **rule_statement**：五气偏全决定命之吉凶；偏者凶、全者吉，此为根本判断框架。
- **source_chapter**：tongshen/02-didao
- **source_layer**：原
- **applicable_to**：吉凶大体判断
- **caveats**："偏全"非简单的五行皆见，须看流通；与中和章互参。
- **verification_status**：pending_verification

## DR-01-03 顺悖之辨

- **rule_statement**：八字干支顺接相生（天干气弱地支生之、地支气衰天干辅之）为吉；反克为害则凶；命贵中和，偏枯终于有损。
- **source_chapter**：tongshen/03-rendao
- **source_layer**：原+任注
- **applicable_to**：全局吉凶
- **caveats**：本派核心立场；"奇异"（如四戊午、四癸亥）一律按偏枯论，不得作奇格高论。
- **verification_status**：pending_verification

## DR-01-04 知命平心

- **rule_statement**：知命之人当平心定气，不取奇偏怪格；以中和为贵。
- **source_chapter**：tongshen/04-zhiming
- **source_layer**：任注
- **applicable_to**：方法论
- **caveats**：方法论层面；任氏多次警告勿信"奇格"。
- **verification_status**：pending_verification

## DR-01-05 理气分体用

- **rule_statement**：理为体，气为用；理气不可偏废。
- **source_chapter**：tongshen/05-liqi
- **source_layer**：原+任注
- **applicable_to**：方法论
- **caveats**：与第十三章体用互参。
- **verification_status**：pending_verification

## DR-01-06 配合得宜

- **rule_statement**：干支配合得宜（生克化制各得其用）为命之大纲。
- **source_chapter**：tongshen/06-peihe
- **source_layer**：原+任注
- **applicable_to**：全局判断
- **caveats**："配合得宜"为旺衰派的最高判语。
- **verification_status**：pending_verification

## DR-01-07 十干性情

- **rule_statement**：十干各有性情：甲为参天之木、乙为花卉之木、丙为太阳之火、丁为灯烛之火、戊为城墙之土、己为田园之土、庚为顽铁之金、辛为珠玉之金、壬为江湖之水、癸为雨露之水；用法各异。
- **source_chapter**：tongshen/07-tiangan
- **source_layer**：原+任注
- **applicable_to**：日干特性判断
- **caveats**：本书十干特性是后世旺衰派教学的根基；切忌与《穷通宝鉴》调候视角混用。
- **verification_status**：pending_verification

## DR-01-08 地支精修

- **rule_statement**：十二支各有所藏（本气/中气/余气）与季节属性；刑冲合害需结合所藏与位置精判。
- **source_chapter**：tongshen/08-dizhi
- **source_layer**：原+任注
- **applicable_to**：地支判断
- **caveats**：藏干司令、深浅与位置（年/月/日/时）皆影响实际作用。
- **verification_status**：pending_verification

## DR-01-09 干支总论

- **rule_statement**：天干为外、地支为内；天干之用须根于地支，地支之力须透于天干。
- **source_chapter**：tongshen/09-ganzhi-zonglun
- **source_layer**：原+任注
- **applicable_to**：干支配合
- **caveats**：与配合章互参。
- **verification_status**：pending_verification

## DR-02-01 形象之辨

- **rule_statement**：两气合而成象（如水木相涵），五气聚而成形（金木水火土齐备）；形象成则气势顺，宜顺其势；形象破则需通关或制伏。
- **source_chapter**：tongshen/10-xingxiang
- **source_layer**：原+任注
- **applicable_to**：气势判断
- **caveats**：形象为高阶视角；与从象、化象互参。
- **verification_status**：pending_verification

## DR-02-02 方局取用

- **rule_statement**：三合局（亥卯未木局等）成局者气势全；方局（寅卯辰东方等）齐全者气势纯；局成宜顺、局破宜疏。
- **source_chapter**：tongshen/11-fangju
- **source_layer**：原+任注
- **applicable_to**：合局判断
- **caveats**：方与局不混；方为同方位三支齐、局为三合三支齐。
- **verification_status**：pending_verification

## DR-02-03 八格的旺衰视角

- **rule_statement**：八格（正官/七杀/正印/偏印/正财/偏财/食神/伤官）的取用以"扶抑"为主线，不同于格局派以"成败救应"为主线。
- **source_chapter**：tongshen/12-bage
- **source_layer**：原+任注
- **applicable_to**：八格判断
- **caveats**：与《子平真诠》视角不同；遇到月令格局精修需求时转 `bazi/ziping-zhenquan`。
- **verification_status**：pending_verification

## DR-02-04 体用分立

- **rule_statement**：以日主为体，以用神为用；体强者用宜泄、体弱者用宜扶。
- **source_chapter**：tongshen/13-tiyong
- **source_layer**：原+任注
- **applicable_to**：用神取法
- **caveats**：本派"用神"为旺衰扶抑视角；与格局派的"相神"不同。
- **verification_status**：pending_verification

## DR-02-05 精神饱满

- **rule_statement**：命局之精（资源充足）、气（流通无阻）、神（光彩外显）三者饱满者为贵。
- **source_chapter**：tongshen/14-jingshen
- **source_layer**：原+任注
- **applicable_to**：贵贱判断
- **caveats**：抽象判语；不能单独成断。
- **verification_status**：pending_verification

## DR-02-06 月令为重

- **rule_statement**：月令为提纲，决定旺衰、决定喜忌；用神取法以月令为最重要参考。
- **source_chapter**：tongshen/15-yueling
- **source_layer**：原+任注
- **applicable_to**：旺衰、用神
- **caveats**：与《子平真诠》"月令本气透干取格"不同：本书月令为旺衰之主，格局派月令为格局之主。
- **verification_status**：pending_verification

## DR-02-07 生时归宿

- **rule_statement**：生时为命之归宿；时干时支与日主的关系决定晚年归宿。
- **source_chapter**：tongshen/16-shengshi
- **source_layer**：原+任注
- **applicable_to**：晚年判断
- **caveats**：抽象判语；具体到事件需结合大运。
- **verification_status**：pending_verification

## DR-03-01 衰旺主线

- **rule_statement**：日主衰旺判断需综合月令得令失令、四柱根气、十干性情、合冲解化；强中有弱、弱中有强；不可以"得令"或"失令"一项独断。
- **source_chapter**：tongshen/17-shuaiwang
- **source_layer**：原+任注
- **applicable_to**：旺衰判断（核心）
- **caveats**：本派核心规则；任氏多次强调"得令未必旺、失令未必衰"。
- **verification_status**：pending_verification

## DR-03-02 中和为贵

- **rule_statement**：命贵中和；五行流通、刚柔得宜者富贵；偏枯至极者贫贱。
- **source_chapter**：tongshen/18-zhonghe
- **source_layer**：原+任注
- **applicable_to**：贵贱判断
- **caveats**："中和"不是五行皆有；是五行配合得宜、流通无阻。
- **verification_status**：pending_verification

## DR-03-03 源流流通

- **rule_statement**：五行有源（生发之神）有流（归宿之神）；流通无阻为贵，停滞为滞，反克为凶。
- **source_chapter**：tongshen/19-yuanliu
- **source_layer**：原+任注
- **applicable_to**：流通判断
- **caveats**：与中和章互参；流通为本派的主线判语之一。
- **verification_status**：pending_verification

## DR-03-04 通关化战

- **rule_statement**：当二五行相战（如金木相战）时，介入第三方（如水）使战局化为生生（金生水、水生木）即为通关；通关之神得令为吉。
- **source_chapter**：tongshen/20-tongguan
- **source_layer**：原+任注
- **applicable_to**：相战处理（核心）
- **caveats**：通关之神必须得令或有根；否则徒劳。
- **verification_status**：pending_verification

## DR-03-05 官杀精修

- **rule_statement**：官杀混杂者去留得宜（去官留杀、去杀留官）；官杀有制（食神制杀、伤官驾杀）者贵；官杀两清者吉；官杀无制者凶。
- **source_chapter**：tongshen/21-guansha
- **source_layer**：原+任注
- **applicable_to**：官杀判断
- **caveats**：本书官杀视角与格局派略有不同：本派以"制化平衡"为主，格局派以"成败救应"为主。
- **verification_status**：pending_verification

## DR-03-06 伤官真假

- **rule_statement**：伤官真者（当令而透）泄秀为贵；伤官假者（不当令）反主刑伤；伤官见官，需结合身强身弱、合冲化解综合判断，非铁定为祸。
- **source_chapter**：tongshen/22-shangguan
- **source_layer**：原+任注
- **applicable_to**：伤官判断
- **caveats**：本书纠正《渊海子平》"伤官见官为祸百端"的简化说，强调"伤官见官，要看格局"。
- **verification_status**：pending_verification

## DR-03-07~08 清浊之辨

- **rule_statement**：命局清者（十神不杂、生克得宜）为贵；浊者（十神混杂、生克失宜）为贱；清中有浊、浊中有清者另议。
- **source_chapter**：tongshen/23-qingqi；tongshen/24-zhuoqi
- **source_layer**：原+任注
- **applicable_to**：清浊判断
- **caveats**："清浊"不能简单看十神种类多寡，要看是否各得其位。
- **verification_status**：pending_verification

## DR-03-09~10 真假神

- **rule_statement**：当令而透干、得用之神为真神；不当令、被合冲制伏的为假神；真神得用为贵、假神乱真为凶。
- **source_chapter**：tongshen/25-zhenshen；tongshen/26-jiashen
- **source_layer**：原+任注
- **applicable_to**：用神判断
- **caveats**：真假之辨须结合月令与透干位置。
- **verification_status**：pending_verification

## DR-03-11 刚柔相济

- **rule_statement**：干性刚（甲丙戊庚壬）柔（乙丁己辛癸）须相济；过刚则折、过柔则靡。
- **source_chapter**：tongshen/27-gangrou
- **source_layer**：原+任注
- **applicable_to**：日干配合
- **caveats**：与配合章互参。
- **verification_status**：pending_verification

## DR-03-12 顺逆结合气势

- **rule_statement**：顺者吉、逆者凶为大纲；但顺逆需结合气势：从势顺生为顺、反克成势为反，皆可为格。
- **source_chapter**：tongshen/28-shunni
- **source_layer**：原+任注
- **applicable_to**：顺逆判断
- **caveats**：与第十六/十七章顺局/反局互参。
- **verification_status**：pending_verification

## DR-04-01 寒暖调节（调候旁证）

- **rule_statement**：冬令日主不可无火（暖调）；夏令日主不可无水（寒调）；寒暖得宜者贵。
- **source_chapter**：tongshen/29-hannuan
- **source_layer**：原+任注
- **applicable_to**：寒暖调节
- **caveats**：本章为旺衰派对调候的旁证视角；调候十干配合精修需转 `bazi/qiongtong-baojian`。
- **verification_status**：pending_verification

## DR-04-02 燥湿调节（调候旁证）

- **rule_statement**：火土过盛则燥（不长万物）；水土过盛则湿（成淤泥）；燥湿调节为贵。
- **source_chapter**：tongshen/30-zaoshi
- **source_layer**：原+任注
- **applicable_to**：燥湿调节
- **caveats**：与寒暖章互参；调候精修转 `bazi/qiongtong-baojian`。
- **verification_status**：pending_verification

## DR-04-03 隐显之辨

- **rule_statement**：吉神宜隐藏蓄势（不被冲克）、凶神宜显露受制；隐者贵显、显者贵隐。
- **source_chapter**：tongshen/31-yinxian
- **source_layer**：原+任注
- **applicable_to**：吉凶神位置
- **caveats**：经验判语；具体看位置与合冲。
- **verification_status**：pending_verification

## DR-04-04 众寡处理

- **rule_statement**：五行众者（如比劫遍野）宜散（食伤泄）、寡者（如孤立一根）宜聚（印星生）。
- **source_chapter**：tongshen/32-zhongguagua
- **source_layer**：原+任注
- **applicable_to**：偏枯处理
- **caveats**：与中和章互参。
- **verification_status**：pending_verification

## DR-04-05 震兑相对

- **rule_statement**：震（卯）兑（酉）相对；卯酉冲为震兑战；处理须看月令支援。
- **source_chapter**：tongshen/33-zhendui
- **source_layer**：原+任注
- **applicable_to**：卯酉冲判断
- **caveats**：本派对卯酉冲不一律凶论，要看气势。
- **verification_status**：pending_verification

## DR-04-06 坎离相对

- **rule_statement**：坎（子）离（午）相对；子午冲为坎离战；处理须看月令支援与寒暖。
- **source_chapter**：tongshen/34-kanli
- **source_layer**：原+任注
- **applicable_to**：子午冲判断
- **caveats**：与寒暖章互参。
- **verification_status**：pending_verification

---

## DR-05-01 妻星妻宫

- **rule_statement**：男以正财（偏财）为妻、日支为妻宫；妻星与妻宫俱旺者得贤妻；妻星弱、妻宫被冲克者婚不利。
- **source_chapter**：liuqin/01-fuqi
- **source_layer**：原+任注
- **applicable_to**：婚姻判断
- **caveats**：经验判语；现代不作婚姻铁口断。
- **verification_status**：pending_verification

## DR-05-02 子星子宫

- **rule_statement**：男以官杀为子、女以食伤为子；时柱为子宫；子星生旺、子宫稳定者子嗣顺利。
- **source_chapter**：liuqin/02-zinv
- **source_layer**：原+任注
- **applicable_to**：子嗣判断
- **caveats**：现代不作生育铁口断；遇咨询建议医学优先。
- **verification_status**：pending_verification

## DR-05-03 父母星

- **rule_statement**：偏财为父、正印为母；父星母星得地者父母康健；被冲克者主父母不利。
- **source_chapter**：liuqin/03-fumu
- **source_layer**：原+任注
- **applicable_to**：父母判断
- **caveats**：现代有"父正财母偏印"之异说；不能铁口断。
- **verification_status**：pending_verification

## DR-05-04 兄弟星

- **rule_statement**：比劫为兄弟；身弱用比劫者得兄弟之助；身强忌比劫者主兄弟分夺。
- **source_chapter**：liuqin/04-xiongdi
- **source_layer**：原+任注
- **applicable_to**：兄弟判断
- **caveats**：经验判语；需结合喜忌。
- **verification_status**：pending_verification

## DR-05-05 何知章

- **rule_statement**：何知其人富——财气通门户；何知其人贵——官星有理会；何知其人贫——财神反不真；何知其人贱——官星还不见；何知其人吉——喜神为辅弼；何知其人凶——忌神得权位；何知其人寿——五行流通；何知其人夭——五行偏枯至极。
- **source_chapter**：liuqin/05-hezhi-zhang
- **source_layer**：原+任注
- **applicable_to**：经验断语
- **caveats**：⚠️ 经验断语，不可铁口；尤其"夭"不得作寿命铁断；现代结合医学事实。
- **verification_status**：pending_verification

## DR-05-06 女命专章

- **rule_statement**：女命以夫星（正官）、子星（食伤）为重；夫星纯正、子星生旺者吉；古文有"贞淫"等贬义判语，现代不沿用。
- **source_chapter**：liuqin/06-numing-zhang
- **source_layer**：原+任注
- **applicable_to**：女命判断
- **caveats**：⚠️ 古文价值观需 reframe；不照搬贞淫等贬义判语；女命与男命使用同一旺衰框架，仅夫子星位置不同。
- **verification_status**：pending_verification

## DR-05-07 小儿命

- **rule_statement**：小儿命主要看关煞、五行偏枯、冲战过重；任氏多次强调"小儿命断夭折须极审慎"。
- **source_chapter**：liuqin/07-xiaoer
- **source_layer**：原+任注
- **applicable_to**：⚠️ 仅作记录
- **caveats**：⚠️ 绝对禁止铁口断小儿夭折；现代医学事实优先；只分析五行倾向，不作寿夭结论。
- **verification_status**：pending_verification

## DR-05-08 才德

- **rule_statement**：才（用神得用）与德（喜神有情）的命局表征；才德兼备者贵。
- **source_chapter**：liuqin/08-caide
- **source_layer**：原+任注
- **applicable_to**：才德判断
- **caveats**：抽象判语。
- **verification_status**：pending_verification

## DR-05-09 奋郁

- **rule_statement**：命局气势顺而清者主奋发；气势逆而浊者主抑郁。
- **source_chapter**：liuqin/09-fenyu
- **source_layer**：原+任注
- **applicable_to**：性情倾向
- **caveats**：性情倾向，非心理诊断。
- **verification_status**：pending_verification

## DR-05-10 恩怨

- **rule_statement**：十神相生为恩、相克为怨；命局中恩怨配合决定际遇。
- **source_chapter**：liuqin/10-enyuan
- **source_layer**：原+任注
- **applicable_to**：人际际遇
- **caveats**：抽象判语。
- **verification_status**：pending_verification

## DR-06-01 闲神处理

- **rule_statement**：闲神（不为用、不为忌）虽不主吉凶，但能起转化作用；闲神被合化为忌神时为凶变。
- **source_chapter**：liuqin/11-xianshen
- **source_layer**：原+任注
- **applicable_to**：用神精修
- **caveats**：闲神判断为本派精修概念。
- **verification_status**：pending_verification

## DR-06-02 从象（从财从煞从儿从势）

- **rule_statement**：日主无根极弱时，从最旺之神：从财、从煞、从儿（食伤）、从势（多势并旺）；运忌扶身。
- **source_chapter**：liuqin/12-congxiang
- **source_layer**：原+任注
- **applicable_to**：从格判断
- **caveats**：从格判定严格，必须无根；运逢扶身则破。
- **verification_status**：pending_verification

## DR-06-03 化象（真化）

- **rule_statement**：天干五合化气为真化的条件：化神当令、有根、不被冲克。
- **source_chapter**：liuqin/13-huaxiang
- **source_layer**：原+任注
- **applicable_to**：化气格判断
- **caveats**：与《渊海子平》YR-02-19 互证。
- **verification_status**：pending_verification

## DR-06-04~05 假从假化

- **rule_statement**：日主有微根而大势从之者为假从；化神不真但合而似化者为假化；假从假化者，运行从化之乡反吉、运逢扶身反凶。
- **source_chapter**：liuqin/14-jiacong；liuqin/15-jiahua
- **source_layer**：任注
- **applicable_to**：从化精修
- **caveats**：本派精修概念；与真从真化对照。
- **verification_status**：pending_verification

## DR-06-06~09 顺反战合四局

- **rule_statement**：顺局（从势顺生）、反局（反克成势）、战局（五行相战需通关）、合局（合化成势）；皆为气势格局。
- **source_chapter**：liuqin/16-shunju；liuqin/17-fanju；liuqin/18-zhanju；liuqin/19-heju
- **source_layer**：原+任注
- **applicable_to**：气势格局
- **caveats**：与《子平真诠》月令格局派分立两条体系。
- **verification_status**：pending_verification

## DR-06-10~13 君臣母子象

- **rule_statement**：君象（日主为主、众星拱卫）、臣象（日主为臣、君星显达）、母象（印星养身）、子象（食伤泄秀）；皆为气势比拟。
- **source_chapter**：liuqin/20-junxiang；liuqin/21-chenxiang；liuqin/22-muxiang；liuqin/23-zixiang
- **source_layer**：原+任注
- **applicable_to**：气势比拟
- **caveats**：四象为本派的高阶比拟，须结合具体喜忌使用。
- **verification_status**：pending_verification

## DR-07-01 性情

- **rule_statement**：木仁、火礼、土信、金义、水智；性情判断以日主五行为主，并结合用神调节。
- **source_chapter**：liuqin/24-xingqing
- **source_layer**：原+任注
- **applicable_to**：性情倾向
- **caveats**：性情倾向参考；不作心理诊断。
- **verification_status**：pending_verification

## DR-07-02 疾病体质

- **rule_statement**：五行偏枯对应脏腑（甲乙肝胆、丙丁心小肠、戊己脾胃、庚辛肺大肠、壬癸肾膀胱）；偏枯之气主体质倾向。
- **source_chapter**：liuqin/25-jibing
- **source_layer**：原+任注
- **applicable_to**：体质倾向参考
- **caveats**：⚠️ 不作医学诊断；遇用户问诊一律建议就医；只作命理体质倾向参考。
- **verification_status**：pending_verification

## DR-07-03 岁运合参

- **rule_statement**：大运为方向、流年为发动；岁运与命局合参，看用神得力、忌神得权。
- **source_chapter**：liuqin/28-suiyun
- **source_layer**：原+任注
- **applicable_to**：流年判断
- **caveats**：必须由 tool.bazi.paipan 起大运表。
- **verification_status**：pending_verification

## DR-07-04 贞元寿元

- **rule_statement**：贞元之运为命之终始；五行流通无阻者主寿，偏枯至极、运行绝地者为危。
- **source_chapter**：liuqin/29-zhenyuan
- **source_layer**：原+任注
- **applicable_to**：⚠️ 仅作记录
- **caveats**：⚠️ 绝对禁止铁口断寿命；现代不作死亡时间结论；古法判断仅作历史记录。
- **verification_status**：pending_verification

---

**说明**：Batch D1 框架抽取，共 38 条规则（DR-01-01 ~ DR-07-04）。全部 pending_verification。所有规则均从 [原] 与 [任注] 提取，[案例] 仅在 quote-index.md 中作引用。
