# 三命通会 — Rules

> 本文件抽取《三命通会》全书的可路由判断规则。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `applicable_to` / `caveats` / `verification_status`。
> 单条规则正文 ≤ 200 字。
> `verification_status` 现阶段全部 `pending_verification`（CTP 文本未对四库本影印复核）。

---

## R-01-01 五行生成数

- **rule_statement**：五行各有生数与成数（水一六、火二七、木三八、金四九、土五十）；命理依此分阴阳与配数。
- **source_chapter**：vol-01/wuxing-shengcheng
- **applicable_to**：基础理论；纳音取象、河图配数
- **caveats**：本规则属理论铺垫，不直接用于具体断命；不可作为吉凶硬判依据。
- **verification_status**：pending_verification

## R-01-02 五行生克次序

- **rule_statement**：相生：木→火→土→金→水→木；相克：木克土、土克水、水克火、火克金、金克木。
- **source_chapter**：vol-01/wuxing-shengke
- **applicable_to**：所有命局生克判断
- **caveats**：单纯生克不等于吉凶；需结合旺衰与喜忌。
- **verification_status**：pending_verification

## R-01-03 纳音取象

- **rule_statement**：六十甲子各配纳音五行取象（海中金、炉中火、大林木、路旁土、剑锋金、山头火、涧下水、城头土、白腊金、杨柳木、泉中水、屋上土、霹雳火、松柏木、流下水、砂石金、山下火、平地木、壁上土、金箔金、灯头火、天河水、大驿土、钗钏金、桑柘木、柘榴木、大海水、石榴木、大海水），30组纳音以象喻命。
- **source_chapter**：vol-01/nayin-quxiang
- **applicable_to**：古法年命论、纳音取象参考
- **caveats**：纳音在现代子平中已很少使用；仅作古法源流参考，不参与格局判断。
- **verification_status**：pending_verification

## R-01-04 六十甲子性质吉凶

- **rule_statement**：六十甲子各有五行性质与吉凶倾向，如甲子乙丑海中金（藏而不露）、丙寅丁卯炉中火（炎上）等；可为年命/日柱论命提供甲子级判词。
- **source_chapter**：vol-01/liushi-jiazi-jixiong
- **applicable_to**：年柱/日柱特性参考
- **caveats**：六十甲子判词属古法年命体系；现代子平以日干旺衰格局为主，甲子级判词仅作点缀。
- **verification_status**：pending_verification

## R-02-01 天干阴阳生死

- **rule_statement**：阳干顺行十二宫，阴干逆行十二宫；如甲长生在亥，乙长生在午（与寄生十二宫相配）。
- **source_chapter**：vol-02/tiangan-yinyang-shengsi
- **applicable_to**：日干旺衰判断、长生诀
- **caveats**：阴干逆行说后世有争议；与《滴天髓阐微》"阴阳同生同死"说冲突，需在 conflict-policy 中按问题类型选派。
- **verification_status**：pending_verification

## R-02-02 月令藏干本中余气

- **rule_statement**：月令所藏天干分本气、中气、余气，按节气分日数分配司令；取格优先看本气透干，本气不透看中气、余气。
- **source_chapter**：vol-02/renyuan-sishi
- **applicable_to**：取格、用神判断
- **caveats**：本气分配日数古今略有差异；与《子平真诠》R2 互证，但日数细节以专精派 pack 为准。
- **verification_status**：pending_verification

## R-02-03 节气换月

- **rule_statement**：八字月柱以节气分界（立春、惊蛰…），不以朔望分界；节气前后须严格区分。
- **source_chapter**：vol-02/sishi-jieqi
- **applicable_to**：排盘、月令判断
- **caveats**：节气分界事实层；必须由 `tool.bazi.paipan` 计算，不让 LLM 手算。
- **verification_status**：pending_verification

## R-02-04 五行旺相休囚死

- **rule_statement**：当令者旺、所生者相、生我者休、克我者囚、我克者死；命局以日干在月令的状态定基本旺衰。
- **source_chapter**：vol-02/wuxing-wangxiang
- **applicable_to**：日主旺衰、扶抑用神
- **caveats**：旺衰只是粗框架；细致判断须追加 `bazi/ditiansui-chanwei`。
- **verification_status**：pending_verification

## R-02-05 大运起运法

- **rule_statement**：大运从月柱起；男阳女阴顺行，男阴女阳逆行；起运岁数按生时距前/后节气日数除三。
- **source_chapter**：vol-02/dayun
- **applicable_to**：所有大运排算
- **caveats**：起运岁数为事实层；必须由 `tool.bazi.paipan` 计算。
- **verification_status**：pending_verification

## R-02-06 太岁与犯太岁

- **rule_statement**：流年为太岁；命局与太岁冲、刑、合者皆有应；不限于值太岁、冲太岁。
- **source_chapter**：vol-02/taisui
- **applicable_to**：流年判断
- **caveats**：现代流派"犯太岁"包装多有夸大；本书强调辨明冲、刑、合的具体类型，不一概而论。
- **verification_status**：pending_verification

## R-02-07 岁运合参

- **rule_statement**：大运与流年合参，看与命局喜忌的生克冲合；岁运并临往往应大事。
- **source_chapter**：vol-02/zonglun-suiyun
- **applicable_to**：流年具体事项判断
- **caveats**：具体事件应期需配合神煞与十神；具体事件层可叠加六爻 `divination/*`。
- **verification_status**：pending_verification

## R-02-08 十干五合

- **rule_statement**：甲己合土、乙庚合金、丙辛合水、丁壬合木、戊癸合火。
- **source_chapter**：vol-02/shigan-he
- **applicable_to**：合化判断、男女合婚参考
- **caveats**：合不一定化；化需化神当令且不被破。
- **verification_status**：pending_verification

## R-02-09 化气成立条件

- **rule_statement**：天干五合化气需化神当令、四柱有化神之根、不被冲克破合者方真化。
- **source_chapter**：vol-02/shigan-huaqi
- **applicable_to**：化气格判断
- **caveats**：化气真伪是命理大变量；不真化时仍按原五行论。
- **verification_status**：pending_verification

## R-02-10 地支六合

- **rule_statement**：子丑合土、寅亥合木、卯戌合火、辰酉合金、巳申合水、午未合（土火）。
- **source_chapter**：vol-02/zhiyuan-liuhe
- **applicable_to**：合化判断
- **caveats**：六合是否化亦受月令、四柱影响。
- **verification_status**：pending_verification

## R-02-11 地支三合局

- **rule_statement**：申子辰合水局、亥卯未合木局、寅午戌合火局、巳酉丑合金局；三合局成时五行势力大增。
- **source_chapter**：vol-02/zhiyuan-sanhe
- **applicable_to**：合局判断、专局格
- **caveats**：三合需三支齐；缺一为半合，效力打折。
- **verification_status**：pending_verification

## R-02-12 六害

- **rule_statement**：子未、丑午、寅巳、卯辰、申亥、酉戌相害；多主无情、不和。
- **source_chapter**：vol-02/liuhai
- **applicable_to**：六亲、家庭、合作判断
- **caveats**：六害较冲、刑为轻；不可独断凶。
- **verification_status**：pending_verification

## R-02-13 三刑

- **rule_statement**：寅巳申无恩之刑、丑戌未持势之刑、子卯无礼之刑；辰午酉亥自刑。
- **source_chapter**：vol-02/sanxing
- **applicable_to**：六亲、刑伤判断
- **caveats**：刑入命未必凶，需结合用神喜忌；自刑较弱。
- **verification_status**：pending_verification

## R-02-14 六冲

- **rule_statement**：子午、丑未、寅申、卯酉、辰戌、巳亥相冲；冲动、移动、变化之象。
- **source_chapter**：vol-02/chongji
- **applicable_to**：日柱冲、月柱冲、流年冲
- **caveats**：冲不一定凶；冲喜用为凶，冲忌神为吉；月柱冲影响最大。
- **verification_status**：pending_verification

## R-02-15 十干天文十二支地理

- **rule_statement**：十干分配天文（甲雷、乙风、丙日、丁星、戊霞、己云、庚月、辛霜、壬雨、癸露）；十二支分配地理（子齐青州、丑吴越扬州等）。古法以天文地理取象配命。
- **source_chapter**：vol-02/shigan-tianwen；vol-02/shierzhi-dili
- **applicable_to**：古法取象参考
- **caveats**：天文地理配干支属古法取象，现代仅作背景知识；分野说已不符合当代地理区划。
- **verification_status**：pending_verification

## R-02-16 胎元

- **rule_statement**：胎元取法：月干进一位、月支进三位（如甲子月→乙卯为胎元）；胎元代表先天根基，看命时可作辅助参考。
- **source_chapter**：vol-02/taiyuan
- **applicable_to**：古法命理辅助
- **caveats**：现代八字排盘通常不排胎元柱；胎元仅为古法辅助概念，不是必看项。
- **verification_status**：pending_verification

## R-02-17 坐命官

- **rule_statement**：坐命宫取法以月将加时辰推算得地支，再配天干；命宫辅助看命主根基与运势。
- **source_chapter**：vol-02/zuomingguan
- **applicable_to**：古法命宫查询
- **caveats**：本书"坐命宫"与紫微斗数"命宫"取法不同，不可混用；现代子平通常不排命宫。
- **verification_status**：pending_verification

## R-02-18 小运

- **rule_statement**：小运以时辰为起点，男阳女阴顺行、男阴女阳逆行，逐年推排；每一年一柱，用于辅助大运看年内细节。
- **source_chapter**：vol-02/xiaoyun
- **applicable_to**：古法小运查询
- **caveats**：子平后世较少用小运，现代八字以大运+流年为标准配置；小运仅在古法研究或特定流派中使用。
- **verification_status**：pending_verification

## R-02-19 进交退伏

- **rule_statement**：五行在节气转换中有四阶段：进气（将旺未旺）、交气（正旺）、退气（旺极将衰）、伏气（衰极潜伏）。判断五行力量需考虑节气深浅。
- **source_chapter**：vol-02/jinjiao-tuifu
- **applicable_to**：五行旺衰精细判断
- **caveats**：现代多简化为旺衰二分；进交退伏属精细古法概念，在实务中可作参考但不强制。
- **verification_status**：pending_verification

## R-03-01 禄马同乡

- **rule_statement**：日干之禄与驿马同支或邻支为禄马同乡；古以为吉象。
- **source_chapter**：vol-03/zonglun-luma
- **applicable_to**：神煞辅助
- **caveats**：神煞作辅；不主主线；与格局冲突时以格局为主。
- **verification_status**：pending_verification

## R-03-02 天乙贵人取法

- **rule_statement**：甲戊庚日见牛（丑）羊（未）；乙己日见鼠（子）猴（申）；丙丁日见猪（亥）鸡（酉）；壬癸日见兔（卯）蛇（巳）；辛日见马（午）虎（寅）。
- **source_chapter**：vol-03/tianyi-guiren
- **applicable_to**：神煞辅证
- **caveats**：贵人入命主有解厄之力；但不可单凭贵人作富贵硬断。
- **verification_status**：pending_verification

## R-03-03 阳刃 / 羊刃

- **rule_statement**：阳干见刃位（甲见卯、丙见午、戊见午、庚见酉、壬见子）为阳刃；阴干一般不取刃。
- **source_chapter**：vol-03/yangren；vol-06/yangren
- **applicable_to**：日主旺衰、性情判断、阳刃格
- **caveats**：阳刃过旺需食伤、官煞制；阴干刃后世有不同观点。
- **verification_status**：pending_verification

## R-03-04 空亡

- **rule_statement**：以日柱所属旬定旬空（甲子旬空戌亥…）；空亡入命主无依、有变。
- **source_chapter**：vol-03/kongwang
- **applicable_to**：六亲、十神所在柱判断
- **caveats**：空亡不必凶；逢冲、合、填实可解。
- **verification_status**：pending_verification

## R-03-05 神煞总则

- **rule_statement**：神煞作事项点缀与应期辅证，不作主格主用；神煞与格局/用神冲突时以格局/用神为主。
- **source_chapter**：vol-03/zonglun-shensha
- **applicable_to**：所有神煞判断
- **caveats**：本书神煞条目多达数十种；多神煞同现并不构成必然结论。
- **verification_status**：pending_verification

## R-03-06 金舆

- **rule_statement**：金舆贵人取法以日干查地支（甲日见辰、乙日见巳等）；金舆主车驾出行之吉、迁动之利。
- **source_chapter**：vol-03/jinyu
- **applicable_to**：神煞辅证
- **caveats**：金舆为吉神，但力量较轻，不作主线判断。
- **verification_status**：pending_verification

## R-03-07 三奇贵人

- **rule_statement**：天上三奇甲戊庚、地下三奇乙丙丁、人中三奇壬癸辛；三奇入命需顺排不杂（天干连续）方为真，主特异才能。
- **source_chapter**：vol-03/sanqi
- **applicable_to**：神煞辅证
- **caveats**：三奇贵人条件苛刻（需顺排+不杂+不逢冲破）；八字三奇≠奇门三奇（乙丙丁）；现代以格局为主，三奇为点缀。
- **verification_status**：pending_verification

## R-03-08 太极贵人

- **rule_statement**：太极贵人取法以日干年干查地支（甲乙见子午、丙丁见卯酉等）；主智慧、玄学、学术天赋。
- **source_chapter**：vol-03/taiji-gui
- **applicable_to**：神煞辅证
- **caveats**：太极贵人主聪明好学，但不可单凭此断学历高低。
- **verification_status**：pending_verification

## R-03-09 学堂词馆

- **rule_statement**：学堂、词馆贵人取法以日干查地支（甲见亥、乙见午等）；主文章学业功名，命带学堂词馆者多有文才。
- **source_chapter**：vol-03/xuetang-ciguan
- **applicable_to**：学业功名辅助
- **caveats**：学堂词馆为文章类神煞，现代可作学业参考但非决定性因素。
- **verification_status**：pending_verification

## R-03-10 正印（神煞）

- **rule_statement**：神煞篇"正印"取法以日干查地支（甲见子、乙见亥等）；主印信文书之吉。
- **source_chapter**：vol-03/zhengyin
- **applicable_to**：古法神煞参考
- **caveats**：与十神"正印"（生日干且异阴阳者）为完全不同的概念，不可混用。
- **verification_status**：pending_verification

## R-03-11 德秀

- **rule_statement**：德秀贵人取法以月支查天干（寅午戌月见丙丁等）；主容貌秀美、品性端正。
- **source_chapter**：vol-03/dexiu
- **applicable_to**：神煞辅证
- **caveats**：容貌品性类神煞，现代仅作趣味参考。
- **verification_status**：pending_verification

## R-03-12 元辰（大耗）

- **rule_statement**：元辰（大耗）取法以年支查（子年见未、丑年见申等）；主损耗、失脱、变动。
- **source_chapter**：vol-03/yuanchen
- **applicable_to**：神煞辅证
- **caveats**：元辰为凶煞但非必应；需结合十神与格局判断。
- **verification_status**：pending_verification

## R-03-13 暗金的煞

- **rule_statement**：暗金的煞取法以年支日支查（子午年日见巳、丑未年日见酉等）；为五行金之煞气，主刑伤意外。
- **source_chapter**：vol-03/anjin-desha
- **applicable_to**：神煞辅证
- **caveats**：煞名虽凶，需有刑冲引动方验；不可一见即断凶。
- **verification_status**：pending_verification

## R-03-14 灾煞

- **rule_statement**：灾煞取法为三合局之沐浴位（申子辰见午、亥卯未见酉等）；主突发灾祸、意外变动。
- **source_chapter**：vol-03/zaisha
- **applicable_to**：神煞辅证
- **caveats**：灾煞需有冲克引动方验；流年遇之需结合全局判断。
- **verification_status**：pending_verification

## R-03-15 六厄

- **rule_statement**：六厄煞取法以日干查地支（甲见卯、乙见辰等）；主困厄阻滞。
- **source_chapter**：vol-03/lui-e
- **applicable_to**：神煞辅证
- **caveats**：六厄为凶煞但力量较轻；不可独断厄运。
- **verification_status**：pending_verification

## R-03-16 勾绞

- **rule_statement**：勾煞、绞煞取法以年支日支查（子见卯、丑见辰等）；主口舌是非、牵连纠缠。
- **source_chapter**：vol-03/goujiao
- **applicable_to**：神煞辅证
- **caveats**：勾绞主口舌但非决定性因素；需结合官非类十神综合判断。
- **verification_status**：pending_verification

## R-03-17 十恶大败

- **rule_statement**：十恶大败日以年柱干支查日柱，特定日柱（甲辰、乙巳、丙申等十日）为十恶大败；主破败不顺、仓库空乏。
- **source_chapter**：vol-03/shi-e-dabai
- **applicable_to**：古法日柱禁忌
- **caveats**：古法日柱禁忌，现代仅作参考；十恶大败日有贵人解救者可减凶。
- **verification_status**：pending_verification

## R-05-01 印食官财之名义

- **rule_statement**：印为护身、食为养命、官为约束、财为资助；十神四类之本义。
- **source_chapter**：vol-05/lishou-yinmingyi
- **applicable_to**：十神判读
- **caveats**：本义之外尚有偏正之分；偏者多变。
- **verification_status**：pending_verification

## R-05-02 正官清纯

- **rule_statement**：正官一位清纯而有印护或财生为佳；多见正官则反成混杂。
- **source_chapter**：vol-05/zhengguan
- **applicable_to**：官星判断、功名事业
- **caveats**：精细成败救应需 `bazi/ziping-zhenquan`。
- **verification_status**：pending_verification

## R-05-03 偏官（七煞）需制化

- **rule_statement**：七煞为忌神，需食神制、印化、合留三法之一；制化得宜则煞为权星。
- **source_chapter**：vol-05/pianguan
- **applicable_to**：煞星判断
- **caveats**：制化不当则反伤身；与《子平真诠》"逆用"思想互证。
- **verification_status**：pending_verification

## R-05-04 官煞混杂

- **rule_statement**：正官与七煞同现谓之官煞混杂；杂则不清，需去留得宜。
- **source_chapter**：vol-05/guansha-hunza
- **applicable_to**：官星判断
- **caveats**：去留之法见 R-05-06。
- **verification_status**：pending_verification

## R-05-05 弃命从煞成立条件

- **rule_statement**：日主无根极弱、煞极旺无制、行运扶煞者，弃命从煞为格成；从而反贵。
- **source_chapter**：vol-05/qiming-congsha
- **applicable_to**：从格判断
- **caveats**：从格判定严格；运逢扶身则破格。
- **verification_status**：pending_verification

## R-05-06 官煞去留

- **rule_statement**：官煞混杂时，凭月令、合冲、制化决定去官留煞或去煞留官；保留者为格之主。
- **source_chapter**：vol-05/guansha-quliu
- **applicable_to**：官煞混杂处理
- **caveats**：去留判断细节较多；与《子平真诠》救应章互参。
- **verification_status**：pending_verification

## R-05-07 正官细目

- **rule_statement**：正官诸子格：天福贵人（官星得福神护）、天元作禄（日坐禄，身强官得用）、岁德正官（年柱正官，祖上官贵）、时上正官（时柱正官，晚来得贵）。共性为官星在特定柱位得用，忌伤官克破。
- **source_chapter**：vol-05/tianfu-guiren；vol-05/tianyuan-zuolu；vol-05/suide-zhengguan；vol-05/shishang-zhengguan
- **applicable_to**：官星细化判断
- **caveats**：正官子格以月令正官格为基础，柱位不同仅影响应期和来源，不改变官格本质。
- **verification_status**：pending_verification

## R-05-08 官星配合

- **rule_statement**：官印禄库（官印禄库俱全为贵）、相刑遇贵（刑中有贵人解）、三合遇贵（三合局又遇贵人）——三者均为官星得辅助或救应的吉祥组合。
- **source_chapter**：vol-05/guan-yin-luku；vol-05/xiangxing-yugui；vol-05/sanhe-yugui
- **applicable_to**：官格辅助判断
- **caveats**：配合条件需同时满足；单一条件不构成必然结论。
- **verification_status**：pending_verification

## R-05-09 五行配合细目

- **rule_statement**：金木间隔（金木有制为佳）、水火既济（丙壬相配智慧通达）、金火相成（火炼金成器）——三者均为五行搭配的特殊吉象。
- **source_chapter**：vol-05/jinmu-jiange；vol-05/shuihuo-jiji；vol-05/jinhuo-xiangcheng
- **applicable_to**：五行配合参考
- **caveats**：古法五行配合细目，现代仅作搭配参考，不单独构成格局。
- **verification_status**：pending_verification

## R-05-10 偏官细目

- **rule_statement**：偏官（七煞）诸子格：天元坐煞（日坐七煞需制化）、时上一位贵（时上一位七煞有制为权星）、年上七煞（年柱七煞需制化）。共性为七煞在特定柱位，制化得宜方吉。
- **source_chapter**：vol-05/tianyuan-zuosha；vol-05/shishang-yiweigui；vol-05/nianshang-qisha
- **applicable_to**：七煞细化判断
- **caveats**：七煞无论在哪柱均需制化（食制、印化、合留）；无制之煞为忌。
- **verification_status**：pending_verification

## R-05-11 专禄要制

- **rule_statement**：专禄格（日坐临官禄位）禄旺，需财官食伤为用以平衡；禄旺无制则过刚易折。
- **source_chapter**：vol-05/zhuanlu-yaozhi
- **applicable_to**：建禄/专禄格判断
- **caveats**：专禄与建禄同类（皆日干临官），不取月令格局而转扶抑论法。
- **verification_status**：pending_verification

## R-06-01 魁罡格

- **rule_statement**：庚辰、庚戌、壬辰、戊戌为魁罡日；性烈刚强、聪明果决；忌见财官。
- **source_chapter**：vol-06/kuigang
- **applicable_to**：杂格判断
- **caveats**：魁罡多则贵；财官杂之则破格。
- **verification_status**：pending_verification

## R-06-02 五行专局格

- **rule_statement**：木局曲直（亥卯未或寅卯辰全）、火局炎上（寅午戌或巳午未全）、金局从革（巳酉丑或申酉戌全）、水局润下（申子辰或亥子丑全）、土局稼穑（辰戌丑未全）；专局成时以化神为用。
- **source_chapter**：vol-06/quzhi；vol-06/yanshang；vol-06/congge；vol-06/runxia；vol-06/jiase
- **applicable_to**：外格判断
- **caveats**：专局忌克化神之神；运行克神则破格。
- **verification_status**：pending_verification

## R-06-03 正财论

- **rule_statement**：正财主妻、主守财；身财两停为佳；身弱财多为富屋穷人。
- **source_chapter**：vol-06/zhengcai
- **applicable_to**：财星判断、婚姻
- **caveats**：身弱者扶身比逐财更重要。
- **verification_status**：pending_verification

## R-06-04 财旺生官

- **rule_statement**：财星旺而生官者，官星稳固；身、财、官三停为格高。
- **source_chapter**：vol-06/caiwang-shengguan
- **applicable_to**：官星判断、事业财运
- **caveats**：身弱时财旺生官反害身；需印护。
- **verification_status**：pending_verification

## R-06-05 偏财论

- **rule_statement**：偏财主父、主众人之财；多情而慷慨；不忌比劫则可发偏财。
- **source_chapter**：vol-06/piancai
- **applicable_to**：财星、父星、人际
- **caveats**：偏财怕比劫夺；时上偏财尤忌劫。
- **verification_status**：pending_verification

## R-06-06 弃命从财

- **rule_statement**：日主无根极弱、财星极旺无克、行运扶财者，弃命从财为格成。
- **source_chapter**：vol-06/qiming-congcai
- **applicable_to**：从格判断
- **caveats**：从财格行比劫运则破。
- **verification_status**：pending_verification

## R-06-07 偏正财合论

- **rule_statement**：偏正财同看为吉者重在身强能任；身弱者偏正财皆为忌。
- **source_chapter**：vol-06/pianzhengcai-helun
- **applicable_to**：财星判断
- **caveats**：忌混财杂；需以月令所透为主。
- **verification_status**：pending_verification

## R-06-08 印绶论

- **rule_statement**：印绶生身、护身；身弱喜印；身强忌印过重。
- **source_chapter**：vol-06/yinshou
- **applicable_to**：印星判断、母星
- **caveats**：印多则懒；偏印（枭）夺食为忌。
- **verification_status**：pending_verification

## R-06-09 弃印就财

- **rule_statement**：印多为病、又有财能破印，行运扶财者，弃印就财为格。
- **source_chapter**：vol-06/qiyin-jiucai
- **applicable_to**：印多取财
- **caveats**：身弱印为用神时不可弃。
- **verification_status**：pending_verification

## R-06-10 倒食（偏印夺食）

- **rule_statement**：偏印逢食神为倒食；食神被夺则身弱无养。
- **source_chapter**：vol-06/daoshi
- **applicable_to**：食神格、寿元
- **caveats**：有偏财通关或七煞食制者可解。
- **verification_status**：pending_verification

## R-06-11 杂气格

- **rule_statement**：月令辰戌丑未为杂气；取格须看透干本气、中气、余气；杂气需冲透为用。
- **source_chapter**：vol-06/zaqi
- **applicable_to**：辰戌丑未月令格局
- **caveats**：杂气取用复杂；与《子平真诠》互证。
- **verification_status**：pending_verification

## R-06-12 伤官见官

- **rule_statement**：伤官见官为祸百端；除非伤官配印或伤官生财者可解。
- **source_chapter**：vol-06/shangguan
- **applicable_to**：伤官格判断
- **caveats**：伤官伤尽却又喜见官的特例存在；需精细辨。
- **verification_status**：pending_verification

## R-06-13 食神制煞

- **rule_statement**：身强、食神有力、七煞当令时，食神制煞为佳，反成权贵。
- **source_chapter**：vol-06/shishen
- **applicable_to**：食神格、煞格
- **caveats**：食神被合、被夺则制煞失力。
- **verification_status**：pending_verification

## R-06-14 阳刃格

- **rule_statement**：阳干见月刃为阳刃格；以官、煞、食、伤制刃为用；不取格而以扶抑论。
- **source_chapter**：vol-06/yangren
- **applicable_to**：阳刃格判断
- **caveats**：刃重无制则凶；与卷三神煞"羊刃"互证。
- **verification_status**：pending_verification

## R-06-15 建禄格

- **rule_statement**：日干临官在月支为建禄；不取格而以扶抑论；常以月外财、官、食、伤为用。
- **source_chapter**：vol-06/jianlu
- **applicable_to**：建禄格判断
- **caveats**：与《子平真诠》"建禄不取格"主张一致。
- **verification_status**：pending_verification

## R-07-01 性情形貌

- **rule_statement**：日干、十神、五行偏枯决定性情与形貌；木主仁、火主礼、土主信、金主义、水主智。
- **source_chapter**：vol-07/xingqing-xiangmao
- **applicable_to**：性格、外貌倾向判断
- **caveats**：性情判断与命主自我描述对照；不可作绝对判定。
- **verification_status**：pending_verification

## R-07-02 五脏六腑配干支

- **rule_statement**：甲乙肝胆、丙丁心小肠、戊己脾胃、庚辛肺大肠、壬癸肾膀胱；五行偏枯有相应脏腑病。
- **source_chapter**：vol-07/jibing
- **applicable_to**：体质倾向判断
- **caveats**：本书属理论倾向；现代医学事实不能由此替代；遇用户问诊一律建议就医。
- **verification_status**：pending_verification

## R-07-03 女命总纲

- **rule_statement**：女命以正官为夫、食伤为子；夫宫稳定为佳；夫星与子星均不可缺。
- **source_chapter**：vol-07/numing
- **applicable_to**：女命判断
- **caveats**：本书部分女命断语具时代局限（如"濁滥娼淫"等条目）；现代输出须 reframe，不照搬贬义判语。
- **verification_status**：pending_verification

## R-07-04 小儿关煞

- **rule_statement**：小儿命须看关煞与刑冲破害；关煞重者主夭折或多病。
- **source_chapter**：vol-07/xiaoer
- **applicable_to**：小儿命判断
- **caveats**：关煞名目繁多，多神煞同现不必然成应；现代医学事实优先。
- **verification_status**：pending_verification

## R-07-05 六亲十神配属

- **rule_statement**：父—偏印；母—正印；兄弟姐妹—比劫；妻—正财；子—食伤（男）；夫—正官（女）。
- **source_chapter**：vol-07/liuqin
- **applicable_to**：六亲判断
- **caveats**：本书古制；现代有"父—偏财"等异说；需明标流派出处。
- **verification_status**：pending_verification

## R-07-06 女命纯和清贵

- **rule_statement**：女命纯和清贵者，五行平和、夫星（正官）清贵有力、子星（食伤）得所、无冲无破。
- **source_chapter**：vol-07/numing/chunhe-qinggui
- **applicable_to**：女命判断
- **caveats**：古文"纯和清贵"含时代价值观；现代以"夫星清纯+子星得用+命局平和"中性表述。
- **verification_status**：pending_verification

## R-07-07 女命浊滥（reframe）

- **rule_statement**：古文"浊滥娼淫"的命理成因：伤官过重无制、官煞混杂无去留、五行偏枯、桃花咸池泛滥。
- **source_chapter**：vol-07/numing/zhuolan-changyin
- **applicable_to**：⚠️ 古文判语不可照搬；现代仅作命理成因分析
- **caveats**：极度敏感内容。现代输出必须reframe：以"伤官无制/官煞混杂/五行偏枯/桃花过重"等中性命理语言替代贬义判词；禁止使用古文贬义标签。
- **verification_status**：pending_verification

## R-07-08 女命旺夫克子类

- **rule_statement**：旺夫克子（夫星旺、子星弱→正官得用+食伤被制）；旺子伤夫（子星旺、夫星弱→食伤有力+正官被克）；伤夫克子（夫星子星皆损→官被伤、食被夺）。三者以十神生克为判断核心。
- **source_chapter**：vol-07/numing/wangfu-kezi；vol-07/numing/wangzi-shangfu；vol-07/numing/shangfu-kezi
- **applicable_to**：女命夫星/子星关系判断
- **caveats**：古文以夫为纲的价值观；现代中性化为"正官与食伤的强弱关系"，不照搬"克/伤"等带有价值判断的古文判语。
- **verification_status**：pending_verification

## R-07-09 女命安静守分与福寿两备

- **rule_statement**：安静守分（命局平和无冲战）；福寿两备（五行流通、夫星子星皆得用、无冲无破）。二者均为女命理想化标准。
- **source_chapter**：vol-07/numing/anjing-shoufen；vol-07/numing/fushou-liangbei
- **applicable_to**：女命综合判断
- **caveats**：理想化标准，现实少有完全符合；现代以"命局平和/五行流通"中性表述，不以古文价值标签定性。
- **verification_status**：pending_verification

## R-07-10 横夭少年

- **rule_statement**：小儿/少年命局冲战过重、关煞重、五行偏枯至极，古法断为横夭。
- **source_chapter**：vol-07/numing/hengyao-shaonian
- **applicable_to**：⚠️ 涉及寿夭判断需极度谨慎
- **caveats**：绝对禁止铁口断寿！遇小儿/少年命局只分析五行偏枯和冲战，必须注明"不作寿夭结论"；现代医学事实优先。
- **verification_status**：pending_verification

## R-07-11 女命正偏自处与招嫁不定

- **rule_statement**：正偏自处（正官与七煞同现，需去留得宜）；招嫁不定（夫宫被冲合或官煞混杂无定主→感情不稳）。
- **source_chapter**：vol-07/numing/zhengpian-zichu；vol-07/numing/zhaojia-buding
- **applicable_to**：女命感情判断
- **caveats**：古文婚姻观；现代解读为"夫宫不稳定/官煞混杂导致感情选择困难"，与 R-05-04 官煞混杂互参。
- **verification_status**：pending_verification

## R-07-12 孕生男女（古法）

- **rule_statement**：古法由八字推孕中男女，以年柱时柱或特定干支组合（如阳年阳月阳日阳时生男等）推断。
- **source_chapter**：vol-07/yunsheng-nannv
- **applicable_to**：⚠️ 仅作古法记录
- **caveats**：现代绝对不作事实结论；古法推测不可替代医学检查；遇此问均回复"建议以医学手段为准"。
- **verification_status**：pending_verification

---

## R-08-01~05 卷八日时断总则（甲—戊）

- **rule_statement**：卷八载六甲/六乙/六丙/六丁/六戊各12时辰共60条日时断语。核心原则：时柱为归宿，时辰与日干配合决定晚年格局倾向；日时断为古法断语索引，每条以日干+时支的组合给出一句话吉凶判断。
- **source_chapter**：vol-08/liujia；vol-08/liuyi；vol-08/liubing；vol-08/liuding；vol-08/liuwu
- **applicable_to**：日时配合古法参考
- **caveats**：日时断为古法枚举型断语，每条仅作对应日时的"古法判词索引"；不可直接当作现代八字主线结论。逐时细断语需对四库本影印复核后方可进入 quote-index.md。
- **verification_status**：pending_verification

## R-09-01~05 卷九日时断总则（己—癸）

- **rule_statement**：卷九载六己/六庚/六辛/六壬/六癸各12时辰共60条日时断语。原则与卷八相同：时柱为归宿，日时配合得宜则晚年有靠。
- **source_chapter**：vol-09/liuji；vol-09/liugeng；vol-09/liuxin；vol-09/liuren；vol-09/liugui
- **applicable_to**：日时配合古法参考
- **caveats**：同卷八日时断：古法枚举型断语索引，不可作现代八字主线结论。逐时细断语需对四库本影印复核后方可补入。
- **verification_status**：pending_verification

- **rule_statement**：十干各有喜忌支位：甲喜寅卯、忌申酉；乙喜寅卯辰、忌酉戌；丙喜巳午、忌亥子；丁喜巳午未、忌子丑；戊喜巳午辰戌、忌寅卯；己喜巳午未、忌卯辰；庚喜申酉、忌巳午；辛喜申酉戌、忌午未；壬喜亥子、忌辰戌丑未；癸喜亥子丑、忌未戌。
- **source_chapter**：vol-04/shigan-zuozhi
- **applicable_to**：日主旺衰、用神选取
- **caveats**：喜忌为一般趋势；需结合月令与全局生克；得月得时则增力，失时失地则减力。
- **verification_status**：pending_verification

## R-04-02 月时配合原则

- **rule_statement**：日干得月令之气者为得时，得时支生扶者为得地；月时俱得则日主强旺；月时一得一失则中和；月时俱失则身弱。
- **source_chapter**：vol-04/shigan-zuozhi
- **applicable_to**：旺衰判断、扶抑用神
- **caveats**：月时配合为粗框架；精细旺衰需看全局生克制化。
- **verification_status**：pending_verification

## R-04-03 行运扶抑变格

- **rule_statement**：大运可改变格局喜忌重心；原局身弱逢印比运则转强；原局身强逢财官运则得用；运过则复原局。
- **source_chapter**：vol-04/shigan-zuozhi
- **applicable_to**：大运流年判断
- **caveats**：行运扶抑为暂态；十年一运，不可将行运之变误作原局之变。
- **verification_status**：pending_verification

## R-04-04 十二月支得日干吉凶

- **rule_statement**：以月支为纲论日干吉凶：月支当令则日干得气而旺，月支失令则日干不得气而衰；月支与日干生克关系决定基本旺衰倾向。
- **source_chapter**：vol-04/shier-yuezhi-derigan
- **applicable_to**：月令旺衰判断
- **caveats**：月支得日干仅为粗判；需结合节气深浅与藏干司令。
- **verification_status**：pending_verification

## R-04-05 五行时地分野

- **rule_statement**：五行在十二时辰各有旺衰变化（如木旺于寅卯辰时、火旺于巳午未时等）；五行与地理方位（东南西北中）亦有分野吉凶。时辰定五行当前气数，地域分野作辅证。
- **source_chapter**：vol-04/wuxing-shidi-fenye
- **applicable_to**：时辰旺衰、地理辅助
- **caveats**：分野之说属古法理论框架，现代不作硬性结论；时辰旺衰可作参考但不应遮盖全局判断。
- **verification_status**：pending_verification

---

## R-06-16 壬骑龙背

- **rule_statement**：壬辰日柱多见（尤以月日时三见壬辰为佳）为壬骑龙背格；辰为水库，壬水坐库得势；忌见财官透干破格。
- **source_chapter**：vol-06/ren-qi-longbei
- **applicable_to**：杂格判断（古法）
- **caveats**：古法杂格，现代不作八字主线结论；见正官七煞透干则破格。
- **verification_status**：pending_verification

## R-06-17 遥合禄马类

- **rule_statement**：遥合取贵类杂格（子遥巳禄、丑遥巳禄、冲合禄马、虎午奔巳、羊击猪蛇）的共同原则：日柱通过遥合、冲合等方式获取远在它支的禄（临官）或马（驿马）或财官；成立条件为遥合不破、禄马不被克冲。
- **source_chapter**：vol-06/zi-yao-si-lu；vol-06/chou-yao-si-lu；vol-06/chonghe-luma；vol-06/huwu-bensi；vol-06/yangji-zhushe
- **applicable_to**：古法杂格判断
- **caveats**：全部属古法杂格，现代子平格局体系已基本不取此类；如用于趣味参考，需明确标注"非主流八字结论"。
- **verification_status**：pending_verification

## R-06-18 日时禄贵类

- **rule_statement**：日时禄贵类杂格（六阴朝阳=辛日子时、六乙鼠贵=乙日子时、日禄归时=时支为日干临官）的共同原则：时柱为归宿，时得禄贵则晚年有靠有贵；忌见官星或冲克破格。
- **source_chapter**：vol-06/liuyin-chaoyang；vol-06/liuyi-shugui；vol-06/rilu-guishi
- **applicable_to**：日时配合判断
- **caveats**：日禄归时较其余两格更接近子平主线（时支禄位属身强论），但其"不取它格"的主张与后世格局取用法有冲突；需以月令格局为主，时禄为辅。
- **verification_status**：pending_verification

## R-06-19 拱夹禄贵

- **rule_statement**：拱禄拱贵格：两柱之间虚夹一位为禄（临官）或贵人（天乙贵人），虚而实应为贵；冲禄格：禄位被冲则动，动而有得（喜冲忌神得禄）。忌填实则拱破，忌冲喜用。
- **source_chapter**：vol-06/gonglu-gonggui；vol-06/chonglu
- **applicable_to**：古法杂格判断
- **caveats**：拱夹之说属古法取象；现代八字以实柱论，虚拱不取。
- **verification_status**：pending_verification

## R-06-20 趋乾趋艮

- **rule_statement**：六壬趋艮（壬日寅时）：壬水趋艮（寅属艮）得止为贵；六甲趋乾（甲日亥时）：甲木趋乾（亥属乾）得生为贵。忌冲：申冲寅破六壬趋艮，巳冲亥破六甲趋乾。
- **source_chapter**：vol-06/liuren-quken；vol-06/liujia-quqian
- **applicable_to**：古法杂格判断
- **caveats**：以八卦方位配日时的古法，现代基本不取。
- **verification_status**：pending_verification

## R-06-21 日柱特格类

- **rule_statement**：特定日柱自成贵格：财官双美（壬午、癸巳，日坐财官）；日贵（丁酉、丁亥、癸卯、癸巳，日带天乙贵人）；日德（甲寅、丙辰、戊辰、庚辰、壬戌，日坐德神）。共性为日柱本身带贵气，忌刑冲破害。
- **source_chapter**：vol-06/caiguan-shuangmei；vol-06/rigui；vol-06/ride
- **applicable_to**：日柱特性判断
- **caveats**：日柱特格在子平体系中属参考（非主格）；月令格局为主，日柱特格为辅；刑冲则贵气散。
- **verification_status**：pending_verification

## R-06-22 破格取用类

- **rule_statement**：破官/飞财/破财三格的共同原则：原有格局（官格/财格）被破之后，另有替代之格可成；破而后立，有救应方可取格；破而无救则原格毁。
- **source_chapter**：vol-06/poguan；vol-06/feicai；vol-06/pocai
- **applicable_to**：格局成败判断
- **caveats**：破格取用的替代条件严苛；不可因破官/破财之名而轻断格局。
- **verification_status**：pending_verification

## R-06-23 飞天禄马

- **rule_statement**：庚子、壬子、癸亥等日柱多见子水者，以子多冲出午中财官（丁火正官、己土正财）为飞天禄马格；忌午支填实则冲力失效破格。
- **source_chapter**：vol-06/feitian-luma
- **applicable_to**：古法杂格判断
- **caveats**：古法杂格，以"冲出"为取格方式；现代子平不取此格；见午填实即破。
- **verification_status**：pending_verification

## R-06-24 福德秀气与禄元互换

- **rule_statement**：福德秀气格：合福德（天月德等）与秀气（学堂词馆等）为一体，主身份清贵；禄元互换格：年禄在日、日禄在年，互换为有情之象。
- **source_chapter**：vol-06/fude-xiuqi；vol-06/luyuan-huhuan
- **applicable_to**：古法杂格、年日关系
- **caveats**：古法杂格，细则需对原文逐条核；禄元互换尤需年日皆有禄位。
- **verification_status**：pending_verification

## R-06-25 子午双包

- **rule_statement**：子午双包格：命局子午对冲而各有包裹得宜（如子被丑合包裹、午被未合包裹）；冲中有合、动中有制则为贵。
- **source_chapter**：vol-06/ziwu-shuangbao
- **applicable_to**：古法杂格判断
- **caveats**：子午冲为最强之地支冲；有制化方可取贵，冲而无制仍为凶。
- **verification_status**：pending_verification

## R-06-26 六神兽格

- **rule_statement**：六神兽格（青龙=木、白虎=金、朱雀=火、玄武=水、勾陈=土）为五行配六神的取象法；各神兽对应五行须在命局成形（三合或方局）且格局清纯不破方为贵。
- **source_chapter**：vol-06/qinglong-fuxing；vol-06/baihu-chishi；vol-06/zhuque-chengfeng；vol-06/xuanwu-dangquan；vol-06/gouchen-dewei
- **applicable_to**：古法取象参考
- **caveats**：六神兽格属古法取象，不作现代八字主线结论；本质上可归入五行专局格（曲直/从革/炎上/润下/稼穑）的变体。
- **verification_status**：pending_verification

## R-06-27 还魂借气

- **rule_statement**：还魂借气格：命局借他柱之气为己用（如枯木逢水得生），日主衰弱而有情生扶者可借气还魂；借气来源须有情不破。
- **source_chapter**：vol-06/huanhun-jieqi
- **applicable_to**：身弱取扶判断
- **caveats**：借气非原气，行运变则格局随之而变；最忌借气来源被冲合。
- **verification_status**：pending_verification

## R-06-28 八专禄旺

- **rule_statement**：八专日（甲寅、乙卯、丁未、己未、庚申、辛酉、壬子、癸丑）日坐禄旺之地，身强为论；以月令它格为用。
- **source_chapter**：vol-06/bazhuan-luwang
- **applicable_to**：日柱旺衰判断
- **caveats**：八专日身强需看是否过旺无制；过旺需食伤、财、官为用。
- **verification_status**：pending_verification

## R-06-29 五行专格补

- **rule_statement**：土局润下（土遇水局，克中有生）；金白水清（金水相生，主聪明）；木火交辉（木火通明，主文采）；火金铸印（火炼金成器，主权威）；火土夹杂（火土过燥需水润）。五者皆属两五行配合的特殊格局。
- **source_chapter**：vol-06/tuju-runxia；vol-06/jinbai-shuiqing；vol-06/muhuo-jiaohui；vol-06/huojin-zhuyin；vol-06/huotu-jiaza
- **applicable_to**：外格/特殊格局判断
- **caveats**：此五格为五行搭配而成的特殊取象，不属标准八格；金白水清、木火交辉在实务中可作搭配参考但不宜独断格局。
- **verification_status**：pending_verification

## R-06-30 墓煞

- **rule_statement**：辰戌丑未墓库遇七煞为墓煞；墓煞凶中藏变，有制化（食神制煞或印化煞）则可转凶为吉。
- **source_chapter**：vol-06/musha
- **applicable_to**：煞星+墓库判断
- **caveats**：墓煞非必凶；墓库本身为收藏转化之地，与煞相遇只是凶象增重，制化得力则可解。
- **verification_status**：pending_verification

## R-06-31 四位纯全与一气生成

- **rule_statement**：四位纯全（四柱干支同气纯一）与一气生成（四柱地支顺连如寅卯辰巳）皆为专一格局；纯全太过则偏枯，一气顺连为美、逆乱则破。
- **source_chapter**：vol-06/siwei-chunquan；vol-06/yiqi-shengcheng
- **applicable_to**：特殊格局判断
- **caveats**：纯全格在现代较少见；一气生成顺连者更接近五行专局（如寅卯辰=曲直），可直接归入对应专局格。
- **verification_status**：pending_verification

## R-06-32 背禄逐马与大贵人例

- **rule_statement**：背禄逐马（禄被背不得、马被逐失势）为古法凶断；十干十二年生大贵人例为十干各年大贵人的枚举配合。
- **source_chapter**：vol-06/beilu-zhuma；vol-06/dagiren-li
- **applicable_to**：古法参考
- **caveats**：背禄逐马为古法凶断，需结合整体格局复核不可独断；大贵人例属枚举型古法，现代作趣味参考。
- **verification_status**：pending_verification

## R-06-33 财类细目补

- **rule_statement**：岁带正马（年柱正财，祖上有财，需身强能任）；时带正马（时柱正财，晚年财运，忌比劫夺）；天元坐财（日干自坐财，主自身得财，忌坐下被冲）；时上偏财（时上偏财一位为贵，忌劫财夺）；日坐天财（特定日柱坐财得贵）。
- **source_chapter**：vol-06/suidai-zhengma；vol-06/shidai-zhengma；vol-06/tianyuan-zuocai；vol-06/shishang-piancai；vol-06/rizuo-tiancai
- **applicable_to**：财星在不同柱位的判断
- **caveats**：财在何柱何位只是参考信息；最终财星成败需看全局扶抑与格局配合。
- **verification_status**：pending_verification

## R-06-34 印类细目补

- **rule_statement**：时逢生印（时上印绶，晚年得印护身，需区分正印/偏印，偏印夺食为忌）；胞胎逢印绶（胎元得印，根基深厚，现代多用月柱替代胎元）。
- **source_chapter**：vol-06/shifeng-shengyin；vol-06/baotai-fengyin
- **applicable_to**：印星在不同柱位的判断
- **caveats**：胞胎（胎元）为古法概念，现代八字排盘通常不含胎元柱；时印需看是否构成倒食（偏印夺食）。
- **verification_status**：pending_verification

## R-06-35 附论墓运

- **rule_statement**：大运入墓为收藏、转变之期，非必凶；身强入墓伏藏（收敛），身弱入墓得藏（安稳）；墓运过后复出则有新局。
- **source_chapter**：vol-06/fulun-muyun
- **applicable_to**：大运判断
- **caveats**：墓运因人而异；不可一遇墓运即断凶；墓为土，土重者入墓尤需关注。
- **verification_status**：pending_verification

## R-06-36 食伤类补

- **rule_statement**：倒冲禄（日时冲合求禄，与飞天禄马同理）；福星贵人（特定日柱带的福神，主福禄，神煞辅证）；食神同窠（食神与日干同柱，主子旺食丰，需不逢偏印夺食）；食神带合（食神被合则制煞不力或食力转变）；红鸾天印（红鸾桃花+天印，主婚喜或文印之喜，神煞辅证）；墨池涌泉（水局涌动文思如泉，主文贵）。
- **source_chapter**：vol-06/daochonglu；vol-06/fuxing-guiren；vol-06/shishen-tongke；vol-06/shishen-daihe；vol-06/hongluan-tianyin；vol-06/mochi-yongquan
- **applicable_to**：食伤/神煞辅助判断
- **caveats**：全部属古法杂格或神煞辅证；食神同窠/食神带合在实务中有参考价值（食神为子星、才华星），其余为古法或神煞参考。
- **verification_status**：pending_verification

## R-06-37 杂格总则

- **rule_statement**：本书卷六所载杂格（壬骑龙背、遥合禄马、飞天禄马、六神兽格、趋乾趋艮等 30+ 项）多数属古法、唐宋朝禄命法或取象法，不属后世子平格局体系的主流结论；杂格可作趣味参考或历史源流追踪，但不得替代正格（八格+建禄阳刃+外格）的判断。
- **source_chapter**：vol-06/*（杂格全章）
- **applicable_to**：所有杂格判断
- **caveats**：主 skill 在遇到杂格相关提问时，默认先以正格（月令格局）为第一判断路径；杂格仅作"可提及但非主线"信息。
- **verification_status**：pending_verification

---

**说明**：本表 Batch 0.5 完成卷一至卷七主线 33 条规则框架；Batch 0.6 新增卷四 5 条 + 卷六 22 条（R-06-16~R-06-37），总计 60 条；Batch 0.7 新增卷一~卷九剩余全部规则（R-01-03~R-09-05），总计 102 条规则。全部 verification_status = pending_verification（CTP 文本未对四库本影印复核）。
