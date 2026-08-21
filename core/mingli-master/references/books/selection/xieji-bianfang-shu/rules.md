# 钦定协纪辨方书 — Rules

> 本文件抽取《协纪辨方书》全书的可路由判断规则。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `applicable_to` / `caveats` / `verified`。
> rule_id 前缀 `XR` = Xieji Rule。
> `verified=false`（维基文库文本未对四库本影印复核）。

---

## XR-01 基础原理（河图洛书 / 八卦 / 五行 / 干支）

- **rule_statement**：择日基础以河图洛书、先后天八卦、十二月辟卦（泰、大壮、夬、乾、姤、遯、否、观、剥、坤、复、临）、二十八宿配日、五行用事、干支六合、五虎遁、纳音为根本框架。
- **source_chapter**：vol-01-benyuan-shang
- **applicable_to**：择日基础知识
- **caveats**：本卷为术数共同基础；不涉及具体宜忌判断。
- **verified**：false

## XR-02 方位（二十四方位 / 洪范 / 纳甲 / 大小游年）

- **rule_statement**：二十四方位以八卦（壬子、癸丑、艮寅…）布全周天 360°；坐山方位避忌按"年月克山家"裁判；阳宅方位用八宅大小游年变卦。
- **source_chapter**：vol-02-benyuan-zhong；vol-27/li-yong-si；vol-28/li-yong-wu
- **applicable_to**：方位择吉、修方
- **caveats**：方位避忌涉及年家三煞、大将军、太岁等，必须由 mingli-master.selection.v1 起盘。文化参考，非事实判断。
- **verified**：false

## XR-03 年神（岁德 / 三煞 / 大将军等）

- **rule_statement**：每年依年支推年家神煞：太岁、岁破、大将军、博士、蚕室、太阴、白虎、豹尾、死符、劫煞、灾煞、岁煞、大煞、金神、破败五鬼、日游神等。岁德、岁德合、岁枝德为吉，余者多凶。
- **source_chapter**：vol-03-nianshen-shang
- **applicable_to**：年家方位、年家用事
- **caveats**：本规则为元规则；具体某年某神煞所在方位必须由 mingli-master.selection.v1 计算。
- **verified**：false

## XR-04 月神 / 建除十二神

- **rule_statement**：建除十二神依月支起例：寅月起建于寅，卯月起建于卯，依次类推；建/除/满/平/定/执/破/危/成/收/开/闭十二位轮排，配合月支推每日"建除"。建/除/定/执/成/开六位为吉，其余六位多凶。月厌与月支相冲。
- **source_chapter**：vol-04-yueshen-shang
- **applicable_to**：月家用事、逐日吉凶
- **caveats**：建除十二神必须由 mingli-master.selection.v1 计算；某日为何"客"决定通用宜忌。
- **verified**：false

## XR-05 嫁娶择日（卷九 / 卷十四 / 卷三十一 综合）

- **rule_statement**：嫁娶宜：天德、月德、月恩、四相、时德、生气、母仓、不将日、要安、定日、成日、开日、收日；忌：月破、月厌、月刑、月害、四废、五墓、孤辰、寡宿、十恶大败、重丧、三丧、复日、伏断、嫁娶周堂"翁姑/夫妇/父母"忌位。
- **source_chapter**：vol-09-lijing；vol-14/yiji-yi；vol-31/yili-xia
- **applicable_to**：嫁娶 / 纳采 / 问名 / 订盟 / 亲迎
- **caveats**：嫁娶吉凶必须由 mingli-master.selection.v1 起盘 + 考查男女双方四柱。文化参考，非事实判断；现代婚姻不以此作决策依据。
- **verified**：false

## XR-06 起造修建择日（卷十 / 卷十五 / 卷十六 综合）

- **rule_statement**：起造宜：成日、开日、收日、天德、月德、月恩、四相、时德、生气、母仓；忌：土王用事日、月破、三煞、大耗、月家三煞方、大将军方、太岁方。动土、上梁、立柱另有专用吉凶神煞。
- **source_chapter**：vol-10-yiji-shang；vol-15-nianbiao-si；vol-16-nianbiao-wu
- **applicable_to**：起造 / 修建 / 动土 / 上梁 / 立柱 / 入宅 / 安门 / 安床
- **caveats**：方位避忌（三煞、大将军、太岁）必须由 mingli-master.selection.v1 起盘。文化参考，非事实判断。
- **verified**：false

## XR-07 丧葬择日（卷十一 / 卷三十一 综合）

- **rule_statement**：丧葬宜：鸣吠日、鸣吠对日、不将日、成日、开日；忌：重丧日、三丧日、复日、伏断日、月破、月厌、地火、土禁、土王用事。
- **source_chapter**：vol-11-yiji-xia；vol-31/yili-xia
- **applicable_to**：丧葬 / 入殓 / 移柩 / 安葬 / 启攒 / 除服
- **caveats**：现代殡葬不以此作时间决策。文化参考，非事实判断。
- **verified**：false

## XR-08 通用宜忌（卷十二 / 卷二十六 / 卷二十九 / 卷三十二 综合）

- **rule_statement**：通用宜忌总则：每日吉凶以建除 + 黄黑道 + 当日神煞综合判断。十恶大败为大凶；四废、五墓为通用凶日；天德、月德、天恩为通用吉日。
- **source_chapter**：vol-12-nianbiao-yi；vol-26/yongshi-ba；vol-29/li-yong-liu；vol-32/yongshi-jiu
- **applicable_to**：通用择日
- **caveats**：必须由 mingli-master.selection.v1 综合起盘。
- **verified**：false

## XR-09 出行 / 上任 / 受官（卷十三 / 卷二十）

- **rule_statement**：出行宜：驿马日、天马日、天德、月德、黄道吉时；忌：往亡日、归忌日、四离四绝、杨公忌。上任 / 受官宜：成日、开日、临政日、天恩日；忌：破日、死日、闭日。
- **source_chapter**：vol-13-nianbiao-er；vol-20-yuebiao-si
- **applicable_to**：出行 / 远行 / 上任 / 受官 / 上册 / 上表
- **caveats**：现代仅作礼仪文化参考，不构成事实判断。
- **verified**：false

## XR-10 小型用事（卷十七 / 卷二十五）

- **rule_statement**：安碓、修井、作灶、开渠、穿井、装饰、修补、葺墙等小型用事，多以通用吉日为准；特殊忌日（如井泉龙日忌穿井）需对照神煞表。
- **source_chapter**：vol-17/li-yong-er；vol-25/yongshi-qi
- **applicable_to**：小型修缮 / 居家用事
- **caveats**：文化参考，非事实判断。
- **verified**：false

## XR-11 农事（卷十八）

- **rule_statement**：牧养、纳畜、捕捉、田猎、取鱼等农事用事，多以"母仓""收日""成日"为吉，"破日""闭日""复日"为忌。
- **source_chapter**：vol-18/li-yong-san
- **applicable_to**：农事 / 牧养 / 田猎
- **caveats**：现代农业不以此作时间决策。文化参考，非事实判断。
- **verified**：false

## XR-12 祭祀 / 祈福（卷十九）

- **rule_statement**：祭祀宜：天恩、天赦、母仓、四相、月德、鸣吠对日；祈福求嗣宜：天医、月恩、生气。
- **source_chapter**：vol-19-yuebiao-san
- **applicable_to**：祭祀 / 祈福 / 求嗣
- **caveats**：文化参考，非事实判断。
- **verified**：false

## XR-13 学礼（卷二十一 / 卷三十）

- **rule_statement**：入学宜：成日、开日、定日；冠笄宜：天德、月德、生气；习艺宜：成日、开日、四相。
- **source_chapter**：vol-21-yuebiao-wu；vol-30/yili-shang
- **applicable_to**：入学 / 冠笄 / 习艺
- **caveats**：文化参考，非事实判断。
- **verified**：false

## XR-14 商业（卷二十二）

- **rule_statement**：立券、交易、开市、纳财宜：天恩、天德、月德、成日、开日、满日；忌：破日、闭日、月破、四废、五墓。经络、酝酿另有专用吉日。
- **source_chapter**：vol-22-yuebiao-liu
- **applicable_to**：立券 / 交易 / 开市 / 纳财 / 经络 / 酝酿
- **caveats**：现代商业不以此作时间决策。文化参考，非事实判断。
- **verified**：false

## XR-15 小事（卷二十三）

- **rule_statement**：沐浴、整容、剃头、整手足甲等小事，按"沐浴日""剃头日"等专用吉凶神煞查询。
- **source_chapter**：vol-23/yongshi-wu
- **applicable_to**：沐浴 / 整容 / 剃头 / 整手足甲
- **caveats**：文化参考，非事实判断。
- **verified**：false

## XR-16 医事（卷二十四）

- **rule_statement**：求医疗病、针灸、服药宜：天医、月恩、四相、生气；忌：复日、四废、十恶大败。
- **source_chapter**：vol-24-ribiao-er
- **applicable_to**：求医 / 针灸 / 服药
- **caveats**：现代医疗绝对不以此作时间决策。**文化参考，非事实判断；不替代任何医疗决策**。
- **verified**：false

## XR-17 辨讹（卷三十三~三十六，本书最大特色）

- **rule_statement**：本书"辨讹"卷订正《选择通书》及民间通书之讹，主要包括：
  - 罗天大进、走天罗地网、上吉七圣、太极贵人等"无据虚名"神煞应予废除。
  - 起例口诀错谬（如某神煞起例算法错）应订正。
  - "诸事不宜""百事大吉"等绝对化判语应回归"具体宜忌"。
  - 所有择日不可"以吉避吉、以凶避凶"，应按事择日。
- **source_chapter**：vol-33/bian-e-yi；vol-34/bian-e-er；vol-35/bian-e-san；vol-36/bian-e-si
- **applicable_to**：择日讹谬辨正、与民间通书冲突时的官方裁判
- **caveats**：本规则为本书最大特色；与民间通书（董公择日、玉匣记）冲突时以本书为权威裁判。
- **verified**：false

## XR-18 巡山罗睺的动作范围与制化边界

- **rule_statement**：巡山羅㬋按年支配二十四山；原文明确“止忌立向，开山、修方不忌”，且一白到向为吉、吉星到山到向可择用，与太岁同宫则勿犯。当前事实层未计算同宫与制化，因此仅作方位信息，不作硬淘汰。
- **source_chapter**：vol-08-rishi-xia；vol-33-bianer-yi；vol-34-bianer-er；vol-35-bianer-san
- **source_anchor**：fulltext.md#L1699-L1700；fulltext.md#L10778；fulltext.md#L10969-L10970；fulltext.md#L11305
- **applicable_to**：起造修建的二十四山方位事实
- **caveats**：只在巡山罗睺方位由确定性 provider 实际命中时适用；不得据此直接淘汰候选日。
- **verified**：source-hash-bound

---

## 路由说明

- 本 pack 是清代官方择日的"集大成"权威；与民间通书（董公、玉匣记）冲突时以本 pack 为准。
- 涉及具体某日吉凶 / 某方位避忌，**一律由 mingli-master.selection.v1 起盘**，本规则集只提供"应当查哪些神煞、哪些吉凶日类型"的元规则。
- 涉及"嫁娶/丧葬/出行/起造"事实层判断，**必须加 caveat："文化参考，非事实判断"**。
- 涉及医事（XR-16），**必须额外强调"不替代任何医疗决策"**。
- 共 18 条规则；XR-18 由 Task 7K 的原文哈希见证与运行时事实谓词共同约束。
