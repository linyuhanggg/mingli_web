---
slug: liuren-miben
file: terms
source_status: complete_text
---

# 《大六壬秘本》术语与异名

> 术语定义只说明本书中的操作含义。凡涉及月将、天地盘、四课、三传、天将、旬空、干支阴阳或旺衰计算，必须读取确定性 adapter 输出。

| term_id | term / aliases | 本书中的操作含义 | source | source layer | 边界 / 歧义 |
|---|---|---|---|---|---|
| LM-T01 | 月将 / 神后、大吉、功曹等十二将 | 卷一按十二支建立数、味、宿度、人物和物类；卷四又以“月将加时”作为射覆盘面前提。 | LM-Q003, LM-Q010 | transmitted_body | 月将值与节气边界不由本包计算。 |
| LM-T02 | 十二天将 / 天官 | 贵人、蛇、雀、合、勾、龙、空、虎、常、玄、阴、后及其所主；卷五又与十二辰组合为物类表。 | LM-Q007, LM-Q013 | transmitted_body | 天将布列和昼夜贵人 profile 由 adapter 决定。 |
| LM-T03 | 旬中神煞 | 卷三所列仪神、丁神、天中、奇神、闭口、五亡等六旬表。 | LM-Q008 | transmitted_body | 仅为本书表法；不得跨系统移植或单独下断。 |
| LM-T04 | 射覆 | 卷四至卷七以发用、日辰、旺衰、五行、形色、天官和八卦推物类的传统方法。 | LM-Q009-LM-Q017 | transmitted_body + mixed variants | 可用于文本研究或已知盘面解释，不是通用视觉识别。 |
| LM-T05 | 发用 / 用神 / 初传 | 事情的发端；卷四射覆“专视初”，卷十四称发端门，卷十五称心之所主、事之所向。 | LM-Q010, LM-Q047, LM-Q053 | transmitted_body + mixed_body_commentary | 初传必须由 adapter 产生；本包只消费结果。 |
| LM-T06 | 初传、中传、末传 / 发端、移易、归计 | 本书把三传分为事初、事中、事末，并用作过程分段。 | LM-Q047 | transmitted_body | 这是解释顺序，不是自动应验时间表。 |
| LM-T07 | 日辰 / 干支 / 人宅 | 日干常被设为我、人、外；支辰常被设为他、宅、内。卷十四会随问法改变主客身份。 | LM-Q040, LM-Q052, LM-Q057 | transmitted_body + mixed_body_commentary | 不得机械固定“干永远是自己、支永远是对方”；先看问题角色。 |
| LM-T08 | 四课 / 直事门 | 卷十三称月将加正时后分四课阴阳、别三传生克。 | LM-Q035 | transmitted_body | 这句话是输入关系说明，不授权 LLM 手排四课三传。 |
| LM-T09 | 彼此 / 体用 | 卷十四以日、三传和天地盘位置区分我/他、体/用。 | LM-Q039, LM-Q040 | transmitted_body | 必须记录问法和角色映射；不同分门可能重定义主客。 |
| LM-T10 | 天时 | 四时旺、相、休、死、囚的时令强弱。 | LM-Q041 | transmitted_body | 与卷七“两日轮转”异说并存；计算 profile 必须显式。 |
| LM-T11 | 地利 | 天干所对应之神得临、不空、不受克，并得照得党。 | LM-Q042 | transmitted_body | 属本书权衡维度，不是地理风水概念。 |
| LM-T12 | 喜忌 | 印、财、禄、德、官、救及鬼、劫、窃、枭等关系，再叠加马墓刑冲破害合、空陷旺衰。 | LM-Q043 | transmitted_body + Jin-added passage nearby | 不能把单个名称直接固定成吉凶；须看旺衰、亲疏、关隔。 |
| LM-T13 | 虚实 / 空亡 / 落空 / 陷空 | 卷十四先以空、陷及生克比和分虚实；卷十五进一步按初中末与事项区分空亡效果。 | LM-Q044, LM-Q051 | transmitted_body + mixed_body_commentary | 不能用“见空一律无”代替分层判断。 |
| LM-T14 | 聚散 / 初建、复建 | 卷十四引《中黄经》用日干、时干五子元遁后的建干多寡观察来情聚散。 | LM-Q045 | quoted_lineage + mixed commentary | 属本书收录的变法，不作为默认 adapter 必需字段。 |
| LM-T15 | 动静 | 日辰被用作静，三传被用作动，再看相生、克陷及斩关、墓合等。 | LM-Q046 | transmitted_body | 不能只凭伏吟/马星一个标签决定动静。 |
| LM-T16 | 始终 | 初中末三段及其与日干的生克、神将变化。 | LM-Q047 | transmitted_body | 输出应保留过程转折，不能只截一句终局。 |
| LM-T17 | 迟速 | 卷十四用伏吟、涉害、贵人顺逆、用在日辰前后、岁月日时等多项区分快慢。 | LM-Q048 | transmitted_body + examples | 具体日期仍需历法 adapter；本规则只描述相对快慢。 |
| LM-T18 | 类神 | 按所问人物或事项选择代表神；卷十七行人篇列奴、婢、僧、道、妇女、六亲等类神。 | LM-Q019, LM-Q063 | transmitted_body + mixed_body_commentary | 类神是问题域入口，不能越过主课结构单独定结论。 |
| LM-T19 | 日阴 / 辰阴 | 日、辰上神的再传上神；书中用于外内、发用阴神和事项细分。 | LM-Q032, LM-Q053 | mixed_body_commentary | 必须由天地盘 adapter 给出，不凭名称猜。 |
| LM-T20 | 鬼 / 救 / 子孙制鬼 | 克日之关系及其制化；本书反复强调鬼可被生旺、子孙、德合或其他结构缓解。 | LM-Q023, LM-Q038, LM-Q043 | transmitted_body + mixed_body_commentary | “鬼”不是固定灾祸词；需验证是否受制、空陷、旺衰。 |
| LM-T21 | 墓 | 四季墓神及入墓、覆生、墓求生等结构。 | LM-Q038 | mixed_body_commentary | 卷十三自列日墓/夜墓等口径；不得跨 profile 默用。 |
| LM-T22 | 交车格 | 干与支上神相合、支与干上神相合的互合结构，书中又分财、脱、害、空、刑、冲、克等。 | LM-Q037 | mixed_body_commentary | 只在 adapter 已提供干支上下神与合关系后解释。 |
| LM-T23 | 五要权衡 | 卷十四先分彼此、内外、主客、尊卑、虚实、动静、始终等三十类，再做综合判断。 | LM-Q039 | transmitted_body | 不是五个固定指标；“五要”篇实际展开为三十类框架。 |
| LM-T24 | 三才应事 | 卷十七以天课、人课、地课，分别查看天罡、河魁、贵人落处，并按孟仲季取应。 | LM-Q060 | transmitted_body + mixed_body_commentary | 若无 adapter 的落宫和孟仲季字段，只能解释文字。 |
| LM-T25 | 旺相死休囚 | 五行强弱状态；卷七、卷十三、卷十七并存四时与两日口径。 | LM-Q017, LM-Q029, LM-Q061 | multiple transmitted layers | 本书内部口径不唯一；必须标 `strength_profile`。 |
| LM-T26 | 始入 / 元首 / 重审 / 比邻 / 知一 | 卷十三与卷十五出现不一致的课名、释名和“入/不入”表述。 | LM-Q030, LM-Q031, LM-Q055-LM-Q056 | mixed_body_commentary | 只作异文研究；不得用本包这些行生成课名或三传。 |
| LM-T27 | 课名 | 元首、重审、比用、涉害、遥克、昴星、伏吟、返吟、别责、八专等盘式标签。 | LM-Q055-LM-Q056 | mixed_body_commentary | 课名由独立验证的 adapter profile 输出；本书只作盘后释义候选。 |
| LM-T28 | 金氏层 | 明标“金氏注、旁注、朱笔改、又录”的改字和补充。 | LM-Q004, LM-Q043, LM-Q054 | jin_editorial_note | 与无署名正文/注解分开；不可统称古法原文。 |
| LM-T29 | 影印补字层 | 三处 CTP 章界乱码据 NCL 第 72、179、234 页恢复的正文。 | LM-Q020, LM-Q054, LM-Q062, LM-Q067-LM-Q069 | scan_collated_junction | 仅证明三处局部复核，不代表全书已逐页校定。 |

## Use Rule

术语命中只决定“应加载哪个卷和哪张规则卡”，不直接产出吉凶。至少要同时记录：

- `term_id`
- adapter 字段及版本
- 问题角色映射
- `quote_id` 与 normalized 行号
- source layer
- 与其他书或本书异文的冲突状态
