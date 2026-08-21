# 增删卜易 — Rules

> 本文件抽取《增删卜易》全书的可路由判断规则。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `applicable_to` / `caveats` / `verification_status`。
> 全部 `pending_verification`（维基文库本未对古本逐篇复核）。
> rule_id 前缀 `ZR` = Zengshan Rule。

---

### ZR-F01 兑化讼成卦实例

- **rule_statement**：原文保存兑为泽初、上爻动而变天水讼的完整成卦实例，只用于核对 provider 的起卦结果。
- **source_chapter**：实例/官占
- **applicable_to**：本卦、变卦与动爻均已确定的六爻盘
- **caveats**：仅证明成卦实例，不授权官运吉凶判断。
- **verification_status**：verified

## 一、装卦基础

### ZR-02-01 浑天甲子纳甲

- **rule_statement**：八宫卦各纳天干（乾纳甲壬、坤纳乙癸、震纳庚、巽纳辛、坎纳戊、离纳己、艮纳丙、兑纳丁）；六爻配地支按纳甲歌取。
- **source_chapter**：vol-01/ch-04-huntian-jiazi
- **applicable_to**：所有装卦
- **caveats**：必须由 `tool.divination.liuyao_bindisk` 处理；禁止 LLM 手算。
- **verification_status**：pending_verification

## 二、六亲取法

### ZR-03-01 六亲口诀

- **rule_statement**：以世爻五行为我，生我者父母、克我者官鬼、我生者子孙、我克者妻财、与我同者兄弟。
- **source_chapter**：vol-01/ch-05-liuqin-ge
- **applicable_to**：所有占断的六亲映射
- **caveats**：六亲是占断主轴；女命问夫看官鬼、男命问妻看妻财（含现代性别考量）。
- **verification_status**：pending_verification

## 三、用神取法（核心）

### ZR-04-01 用神

- **rule_statement**：所占之事在卦中之代表爻为用神；问占类型决定用神（详见 ZP-04 取用神流程）。
- **source_chapter**：vol-01/ch-08-yongshen
- **applicable_to**：所有占断
- **caveats**：用神为占断之根本；用神有伤则事不成。
- **verification_status**：pending_verification

### ZR-04-02 元神 / 忌神 / 仇神

- **rule_statement**：生用神者元神（喜其旺动）；克用神者忌神（怕其旺动）；克元神 / 生忌神者仇神（不可旺）。
- **source_chapter**：vol-01/ch-09-yongyuanjichou
- **applicable_to**：用神动静吉凶
- **caveats**：四神协参，单看用神不全。
- **verification_status**：pending_verification

### ZR-04-03 飞伏神

- **rule_statement**：用神不上卦时取本宫伏神；伏神受日月生扶可用、被压制则不可用。
- **source_chapter**：vol-02/ch-28-feifu-shen
- **applicable_to**：用神不上卦的占断
- **caveats**：伏神之力远不及上卦之爻。
- **verification_status**：pending_verification

### ZR-04-04 用神两现

- **rule_statement**：用神两现时，若仅一爻发动则取动爻；若两爻俱动或俱静，须再择其旺者。旬空、月破等取舍不可脱离实际占验机械套用。
- **source_chapter**：vol-02/ch-32-liangxian
- **applicable_to**：用神恰有两个可见候选；Runtime 当前只执行其中“仅一爻发动”的分支。
- **caveats**：两爻同动或同静时仍须完成月日、旺相休囚、空破冲合与受伤等综合裁决，不得按单一条件硬选。
- **verification_status**：verified

## 四、旺衰生克

### ZR-05-01 元神忌神衰旺

- **rule_statement**：元神旺动而无伤——用神得力；忌神旺动而无制——用神受伤。
- **source_chapter**：vol-01/ch-10-yuanji-shuaiwang
- **applicable_to**：吉凶程度判断
- **caveats**：动静与旺衰并参。
- **verification_status**：pending_verification

### ZR-05-02 五行相生

- **rule_statement**：金生水、水生木、木生火、火生土、土生金；元神之力本于此。
- **source_chapter**：vol-01/ch-11-wuxing-shengsheng
- **applicable_to**：六爻生扶判断
- **caveats**：—
- **verification_status**：pending_verification

### ZR-05-03 五行相克

- **rule_statement**：金克木、木克土、土克水、水克火、火克金；忌神之力本于此。
- **source_chapter**：vol-01/ch-12-wuxing-xiangke
- **applicable_to**：六爻克伤判断
- **caveats**：—
- **verification_status**：pending_verification

### ZR-05-04 克处逢生

- **rule_statement**：用神被克处又逢生扶（日月或动爻）则危而不死；俗谓"贪生忘克"。
- **source_chapter**：vol-01/ch-13-kechu-fengsheng
- **applicable_to**：化解凶兆
- **caveats**：必须有真生扶之爻，非空虚之论。
- **verification_status**：pending_verification

### ZR-05-05 四时旺相

- **rule_statement**：月令当令的本气五行为旺，月令所生五行为相，其余先记作休囚候选；四时标签须与日辰、空破、动变和生克合参。
- **source_chapter**：vol-01/ch-15you-sishi-wangxiang
- **applicable_to**：已计算月令与爻支五行的六爻候选季节状态。
- **caveats**：只裁定月令季节带，不单独形成候选综合旺衰、成败、吉凶或应期结论。
- **verification_status**：verified

### ZR-05-06 月将（月建）

- **rule_statement**：月建生扶用神则旺、克伤用神则衰；月建之力贯穿一月。
- **source_chapter**：vol-01/ch-16-yuejiang
- **applicable_to**：月内吉凶
- **caveats**：月建之力大于动爻、小于日辰。
- **verification_status**：pending_verification

### ZR-05-07 日辰

- **rule_statement**：日辰为占断之最大旺衰主宰；可生扶可克破，可冲实空爻、合住动爻。
- **source_chapter**：vol-01/ch-17-richen
- **applicable_to**：所有占断
- **caveats**：日辰之权最大。
- **verification_status**：pending_verification

## 五、动静与变爻

### ZR-06-01 动变之分

- **rule_statement**：摇卦得三背或三面为动爻，老阳老阴变化；动爻变出之爻为变爻。
- **source_chapter**：vol-01/ch-07-dongbian
- **applicable_to**：装卦
- **caveats**：必须由 `tool.divination.liuyao_bindisk` 完成；禁止 LLM 手算。
- **verification_status**：pending_verification

### ZR-06-02 动静生克

- **rule_statement**：动爻能生克他爻、亦能受他爻克生；静爻不能生克他爻，唯受日月生克。
- **source_chapter**：vol-01/ch-14-dongjing-shengke
- **applicable_to**：爻间生克判断
- **caveats**：暗动除外（ZR-06-04）。
- **verification_status**：pending_verification

### ZR-06-03 动变冲合

- **rule_statement**：动爻与变爻间可成回头生、回头克、回头冲、回头合；变爻反作用于本动爻。
- **source_chapter**：vol-01/ch-15-dongbian-chonghe
- **applicable_to**：动爻吉凶
- **caveats**：变克本为大忌；变生本为大吉。
- **verification_status**：pending_verification

### ZR-06-04 暗动

- **rule_statement**：静爻得日辰冲为暗动；暗动如同动，能生克他爻。
- **source_chapter**：vol-01/ch-22-andong
- **applicable_to**：日辰冲爻判断
- **caveats**：暗动力虽显但不及真动。
- **verification_status**：pending_verification

### ZR-06-05 动散

- **rule_statement**：动爻被日辰冲为动散，力减不能为大用。
- **source_chapter**：vol-01/ch-23-dongsan
- **applicable_to**：动爻力量评估
- **caveats**：—
- **verification_status**：pending_verification

### ZR-06-06 进退神

- **rule_statement**：化进神（如寅化卯）力增、化退神（如卯化寅）力减；进神逢冲不进、退神逢冲不退。
- **source_chapter**：vol-02/ch-29-jintui
- **applicable_to**：动爻力量
- **caveats**：—
- **verification_status**：pending_verification

### ZR-06-07 独发

- **rule_statement**：一卦六爻独一爻动，此动爻为占断之主；详细参其生克墓绝。
- **source_chapter**：vol-02/ch-31-dufa
- **applicable_to**：单动卦
- **caveats**：—
- **verification_status**：pending_verification

## 六、合冲刑害

### ZR-07-01 六合

- **rule_statement**：子丑、寅亥、卯戌、辰酉、巳申、午未六合；合则成事、合则停、合住忌神则解凶。
- **source_chapter**：vol-01/ch-19-liuhe
- **applicable_to**：合化判断
- **caveats**：合住用神有时反不利（事不动）。
- **verification_status**：pending_verification

### ZR-07-02 六冲

- **rule_statement**：子午、丑未、寅申、卯酉、辰戌、巳亥六冲；冲散事、冲实空、冲开合。
- **source_chapter**：vol-01/ch-20-liuchong
- **applicable_to**：冲克判断
- **caveats**：六冲卦不一定凶，看用神状态。
- **verification_status**：pending_verification

### ZR-07-03 三刑

- **rule_statement**：寅巳申、丑戌未、子卯三刑；刑则有损伤纠葛。
- **source_chapter**：vol-01/ch-21-sanxing
- **applicable_to**：刑伤判断
- **caveats**：本书重视六冲六合，三刑作辅。
- **verification_status**：pending_verification

### ZR-07-04 反伏吟

- **rule_statement**：反吟主反复颠倒、伏吟主呻吟忧虑；皆非吉象。
- **source_chapter**：vol-01/ch-25-fanfu
- **applicable_to**：卦象总判
- **caveats**：—
- **verification_status**：pending_verification

## 七、应期与墓绝

### ZR-08-01 卦变生克墓绝

- **rule_statement**：动爻变出之爻有回头生 / 克 / 比合 / 墓 / 绝；其中入墓主收藏停滞、入绝主断绝。
- **source_chapter**：vol-01/ch-24-guabian-shengkemujue
- **applicable_to**：动爻吉凶细判
- **caveats**：—
- **verification_status**：pending_verification

### ZR-08-02 旬空

- **rule_statement**：用神旬空——空而不空（动 / 旺 / 临日月）则不空；真空——出旬即应；旬空亦可冲实。
- **source_chapter**：vol-01/ch-26-xunkong
- **applicable_to**：用神旬空判断
- **caveats**：必须由 `tool.divination.liuyao_bindisk` 计算旬空；禁止 LLM 手算。
- **verification_status**：pending_verification

### ZR-08-03 生旺墓绝（应期）

- **rule_statement**：用神长生之地、帝旺之地、墓绝之地皆为应期取义点。
- **source_chapter**：vol-01/ch-26you1-shengwangmuabsolute
- **applicable_to**：应期判断
- **caveats**：与 ZR-08-04 合参。
- **verification_status**：pending_verification

### ZR-08-04 应期总注

- **rule_statement**：用神动则于值日 / 冲日 / 合日应；用神静则于冲日 / 临日应；用神空则出空 / 冲空之日实。
- **source_chapter**：vol-01/ch-26you3-yingqi-zongzhu
- **applicable_to**：所有应期判断
- **caveats**：本书核心规则之一；现代精准时间预测仍受多重不确定性限制。
- **verification_status**：pending_verification

### ZR-08-05 月破（核心）

- **rule_statement**：月建冲爻为月破；月破之爻——静则到底破、动则能伤本变、变则能伤本动、出月或合日不破。
- **source_chapter**：vol-02/ch-27-yuepo
- **applicable_to**：月破爻判断
- **caveats**：本书对月破有"动则能伤"重大补充，与他书有差异；以本书为准。
- **verification_status**：pending_verification

### ZR-08-06 随鬼入墓

- **rule_statement**：用神动随官鬼入墓——大凶；用神入日辰之墓亦凶。
- **source_chapter**：vol-02/ch-30-suigui-rumu
- **applicable_to**：凶象判断
- **caveats**：占病、占讼、占行人尤忌。
- **verification_status**：pending_verification

## 八、卦象总判

### ZR-09-01 归魂游魂

- **rule_statement**：归魂卦——主回归、还原；游魂卦——主漂泊、不定；问行人、问出行尤宜参看。
- **source_chapter**：vol-01/ch-26you4-guihun-youhun
- **applicable_to**：卦象总参
- **caveats**：仅作辅参，不主主线。
- **verification_status**：pending_verification

## 九、各门类问占

### ZR-10-00 题头总注

- **rule_statement**：所有问占先取用神 → 看用神旺衰 → 看元忌动静 → 看应期；此为通则。
- **source_chapter**：vol-01/ch-26you2-tito-zongzhu
- **applicable_to**：所有问占
- **caveats**：—
- **verification_status**：pending_verification

### ZR-10-01 天时

- **rule_statement**：占天时——父母为雨、子孙为晴、官鬼为云雷、妻财为风、兄弟为风云；旺动则现。
- **source_chapter**：vol-02/ch-35-tianshi
- **applicable_to**：天气占
- **caveats**：现代以气象预报为主。
- **verification_status**：pending_verification

## 十、人事问占

### ZR-11-01 身命

- **rule_statement**：占身命——以世爻为身、子孙为福德、官鬼为忧；世旺无伤为佳。
- **source_chapter**：vol-03/ch-36-shenming
- **applicable_to**：身命占
- **caveats**：仅作综合参考，不替代命理分析。
- **verification_status**：pending_verification

### ZR-11-02 终身财福

- **rule_statement**：占财福——以妻财为用、子孙为元神；财旺有源为佳。
- **source_chapter**：vol-03/ch-37-zhongshen-caifu
- **applicable_to**：终身财福
- **caveats**：—
- **verification_status**：pending_verification

### ZR-11-03 终身功名

- **rule_statement**：占功名——以官鬼为用、父母为元神（印绶）；官旺得印为佳。
- **source_chapter**：vol-03/ch-38-zhongshen-gongming
- **applicable_to**：科举 / 仕途
- **caveats**：现代职业发展应以多因素评估为主。
- **verification_status**：pending_verification

### ZR-11-04 求名

- **rule_statement**：占求名——同 ZR-11-03；考试以父母为文书、子孙为忌神（克官）。
- **source_chapter**：vol-03/ch-48-qiuming
- **applicable_to**：科举 / 现代考试
- **caveats**：现代考试以备考为主。
- **verification_status**：pending_verification

### ZR-11-05 求财

- **rule_statement**：占求财——以妻财为用；财旺有元神（子孙）则得；忌兄弟（劫财）旺动。
- **source_chapter**：vol-03/ch-68-qiucai
- **applicable_to**：求财
- **caveats**：仅参考；不应作为投机指引。
- **verification_status**：pending_verification

### ZR-12-01 婚姻

- **rule_statement**：占婚——男以妻财为用、女以官鬼为用；用神旺动有元神则成。
- **source_chapter**：vol-04/ch-82you-hunyin
- **applicable_to**：婚姻成败
- **caveats**：婚姻属现代私事，占断不替代当事人意愿。
- **verification_status**：pending_verification

### ZR-12-02 胎孕

- **rule_statement**：占胎孕——以子孙为用；阳卦阳爻男、阴卦阴爻女；忌官鬼旺动克子孙。
- **source_chapter**：vol-04/ch-87-taiyun
- **applicable_to**：胎孕占
- **caveats**：**严禁替代现代产前检查**；男女鉴定属医学伦理范畴，本书不作为现代用途。
- **verification_status**：pending_verification

### ZR-13-01 出行

- **rule_statement**：占出行——以世爻为身；忌世动入墓 / 入空 / 受冲克；游魂卦不宜远行。
- **source_chapter**:vol-04/ch-91-chuxing
- **applicable_to**：出行吉凶
- **caveats**：现代出行以天气交通为主。
- **verification_status**：pending_verification

### ZR-13-02 行人

- **rule_statement**：占行人归否——以应爻 / 远人之爻为用；用动来生世 / 临归魂——速归；用入墓入空——未归。
- **source_chapter**：vol-04/ch-94-xingren
- **applicable_to**：行人归否
- **caveats**：—
- **verification_status**：pending_verification

### ZR-14-01 防讼

- **rule_statement**：占防非避讼——以官鬼为用；官鬼空 / 安静 / 受制——无讼；官鬼旺动克世——讼来。
- **source_chapter**：vol-04/ch-95-fangsong
- **applicable_to**：预防官非
- **caveats**：—
- **verification_status**：pending_verification

### ZR-14-02 兴讼

- **rule_statement**：占兴讼胜负——世应相战看哪边得日月生扶；世旺应衰胜、世衰应旺败。
- **source_chapter**：vol-04/ch-97-xingci-juesong
- **applicable_to**：诉讼胜负
- **caveats**：现代诉讼以法律证据为准；占断不替代律师意见。
- **verification_status**：pending_verification

### ZR-15-01 疾病

- **rule_statement**：占疾病——以官鬼为病、子孙为药；官鬼旺动且无子孙——病重；子孙旺动 / 临日月——可愈。
- **source_chapter**：vol-04/ch-99-jibing
- **applicable_to**：疾病占
- **caveats**：**严禁替代现代医学诊断**；占断仅做心理参考；危及生命须立即就医。
- **verification_status**：pending_verification

### ZR-16-01 家宅

- **rule_statement**：占家宅——以世爻为人、二爻为宅、五爻为路、六爻为屋顶 / 远；世爻旺无伤、宅爻不被冲克为佳。
- **source_chapter**：vol-04/ch-105-jiazhai
- **applicable_to**：家宅吉凶
- **caveats**：现代住宅安全应以工程检测为主。
- **verification_status**：pending_verification

### ZR-17-01 茔葬

- **rule_statement**：占茔葬——以二爻为穴、世爻为后人；穴旺生世——吉地；穴受冲克——凶地。
- **source_chapter**：vol-04/ch-118-yingzang
- **applicable_to**：茔葬选址
- **caveats**：现代殡葬以法规为主；本书内容属传统民俗。
- **verification_status**：pending_verification
