# 穷通宝鉴 — Rules

> 全书规则按"五行总论 / 五行行论 / 十干 × 四季"分组。
> 规则编号：`QR-NN-MM`（NN：行号 00=总论，01-05=木火土金水；MM：00=行论；01-08=该行下两干 × 四季）。
> 每条规则带 `source_chapter` `source_anchor` `applicable_to` `caveats` `verification_status`。
> 所有规则 `verification_status: unverified`（待对清刊本影印）。
> **重要**：本书是 **调候派** 文献，所有规则在使用时必须遵守 `qiongtong/rule-of-use`：
> 1. 调候用神 ≠ 唯一用神。必须与旺衰、格局合参。
> 2. 月令以 **节气** 分界，必须由 `tool.bazi.paipan` 给出。
> 3. 所示用神组合是"典型"，盘中无相应天干透出时按"取其同类"或"虚用"处理，不能强配。

---

### QTB-M01 四时乘气方法

- **rule_statement**：五行之土无固定一季之性，须结合四时所乘之气审视调济。
- **source_chapter**：五行总论
- **applicable_to**：已计算日主天干与月令地支的四柱盘
- **caveats**：仅说明四时方法，不据此自动判断旺衰吉凶。
- **verification_status**：verified

## QR-00 五行总论

### QR-00-01 — 五行性情与生克总纲

- **rule_id**: QR-00-01
- **source_chapter**: 五行总论
- **source_anchor**: fulltext.md L3
- **statement**: 木主仁、性直；火主礼、性急；土主信、性重；金主义、性刚；水主智、性聪。生克之理：木生火、火生土、土生金、金生水、水生木；木克土、土克水、水克火、火克金、金克木。
- **applicable_to**: 所有日主气质判断的语义底层。
- **caveats**: 仅作日主性情参考；不可用于断职业、伴侣等社会层面。
- **verification_status**: unverified

---

## QR-01 论木（行论 + 甲乙木 × 四季）

### QR-01-00 — 论木总性

- **rule_id**: QR-01-00
- **source_chapter**: 论木
- **source_anchor**: fulltext.md L23
- **statement**: 木性腾上而无所止；春木阳气方盛，宜火以宣其华；夏木根干叶燥，宜水以润之；秋木气衰枝叶凋零，宜金以斩削；冬木枝叶归根，宜火以暖之。
- **applicable_to**: 甲乙日主总论；用于判定四季宜忌的语义底层。
- **caveats**: 仅是宜忌总纲，具体用神组合需查 QR-01-01 ～ QR-01-08。
- **verification_status**: unverified

### QR-01-01 — 三春甲木（寅卯辰月）

- **rule_id**: QR-01-01
- **source_chapter**: 三春甲木
- **source_anchor**: fulltext.md L41-L69
- **statement**: 正月甲木余寒，原文取丙癸；二月以庚金得所为要；三月先取庚金、次用壬水。三个月令次序不同，不得合并成同一用神组合。
- **applicable_to**: 甲日生于寅卯辰月。
- **caveats**: 寅月调候忌庚金过早伤甲；具体宜忌取决于盘中庚丁透与不透；调候必须与旺衰、格局合参。
- **verification_status**: unverified

### QR-01-02 — 三夏甲木（巳午未月）

- **rule_id**: QR-01-02
- **source_chapter**: 三夏甲木
- **source_anchor**: fulltext.md L73-L101
- **statement**: 四月甲木先癸后丁；五月先癸后丁，庚金次之；六月先丁后庚，原文并明言无癸亦可。三夏须按实际月支分别取用。
- **applicable_to**: 甲日生于巳午未月。
- **caveats**: 巳月病火不可全废；癸水必须有源（庚辛申子辰之类）；炎上格、伤官生财格另判。
- **verification_status**: unverified

### QR-01-03 — 三秋甲木（申酉戌月）

- **rule_id**: QR-01-03
- **source_chapter**: 三秋甲木
- **source_anchor**: fulltext.md L105-L149
- **statement**: 七月甲木以丁火为尊、庚金次之；八月先丁、次丙、再次庚；九月独爱丁火，并以壬癸滋扶。三秋各月不可互换次序。
- **applicable_to**: 甲日生于申酉戌月。
- **caveats**: 戌月燥土反需癸水润；纯杀格、从杀格另判。
- **verification_status**: unverified

### QR-01-04 — 三冬甲木（亥子丑月）

- **rule_id**: QR-01-04
- **source_chapter**: 三冬甲木
- **source_anchor**: fulltext.md L151
- **statement**: 冬木寒凝，专用庚金为先（破癸去寒），丁火暖局，戊土堤水。庚丁戊三者俱透者大贵。
- **applicable_to**: 甲日生于亥子丑月。
- **caveats**: 子月切忌癸水透干无制；冬甲见己土泥木为忌；正官格遇冬子另判格局。
- **verification_status**: unverified

### QR-01-05 — 三春乙木

- **rule_id**: QR-01-05
- **source_chapter**: 三春乙木
- **source_anchor**: fulltext.md L179-L207
- **statement**: 正月乙木丙先癸次；二月以丙为君、癸为臣；三月转为先癸后丙。应用时必须保留寅卯辰的逐月差异。
- **applicable_to**: 乙日生于寅卯辰月。
- **caveats**: 辰月乙弱不可见戊厚埋根；调候用神与旺衰用神冲突时按 §冲突优先级裁判。
- **verification_status**: unverified

### QR-01-06 — 三夏乙木

- **rule_id**: QR-01-06
- **source_chapter**: 三夏乙木
- **source_anchor**: fulltext.md L209
- **statement**: 夏乙焦枯，专用癸水润；丙火透出反喜，能催英华；忌干旱无水，亦忌庚金生水反复。
- **applicable_to**: 乙日生于巳午未月。
- **caveats**: 未月燥土须癸水透天；夏乙见伤官生财格另判。
- **verification_status**: unverified

### QR-01-07 — 三秋乙木

- **rule_id**: QR-01-07
- **source_chapter**: 三秋乙木
- **source_anchor**: fulltext.md L247-L275
- **statement**: 三秋乙木总纲先丙后癸，但九月专用癸水；七月、八月还须依各月段所列条件分别判断，不得把三秋写成统一组合。
- **applicable_to**: 乙日生于申酉戌月。
- **caveats**: 酉月切忌庚辛合乙乱命；纯七杀格另议。
- **verification_status**: unverified

### QR-01-08 — 三冬乙木

- **rule_id**: QR-01-08
- **source_chapter**: 三冬乙木
- **source_anchor**: fulltext.md L277
- **statement**: 冬乙阴寒，专用丙火暖局；最忌癸水冻木；戊土制癸为佐。丙戊两透者贵。
- **applicable_to**: 乙日生于亥子丑月。
- **caveats**: 冬乙若日干弱极而四柱无丙，已成寒木无用之造，须警示判语；从财、从杀格另议。
- **verification_status**: unverified

---

## QR-02 论火（行论 + 丙丁火 × 四季）

### QR-02-00 — 论火总性

- **rule_id**: QR-02-00
- **source_chapter**: 论火
- **source_anchor**: fulltext.md L299
- **statement**: 火性炎上，宜其得地见水以济之；春火炎而未烈，秋火退气，冬火气衰，夏火炎烈。喜壬水克之、忌癸水熄之，丙喜见甲乙发其光。
- **applicable_to**: 丙丁日主总论。
- **caveats**: 仅总纲。具体宜忌见 QR-02-01 ～ QR-02-08。
- **verification_status**: unverified

### QR-02-01 — 三春丙火

- **rule_id**: QR-02-01
- **source_chapter**: 三春丙火
- **source_anchor**: fulltext.md L317-L382
- **statement**: 正月丙火用壬、庚辛为助；二月专用壬水；三月仍用壬水，土重时取甲为辅。三春依据实际月支保留不同佐用。
- **applicable_to**: 丙日生于寅卯辰月。
- **caveats**: 寅月丙生时尚有余寒，忌见过早水多寒身；正官格、印格另议。
- **verification_status**: unverified

### QR-02-02 — 三夏丙火

- **rule_id**: QR-02-02
- **source_chapter**: 三夏丙火
- **source_anchor**: fulltext.md L386-L448
- **statement**: 四月丙火专用壬水、金为佐；五月亦专用壬水；六月用壬并借庚金为佐。此为三夏逐月原文次序，不外推固定吉凶。
- **applicable_to**: 丙日生于巳午未月。
- **caveats**: 午月阳刃格须配七杀；不可滥用壬水致水多反克身；炎上格另判。
- **verification_status**: unverified

### QR-02-03 — 三秋丙火

- **rule_id**: QR-02-03
- **source_chapter**: 三秋丙火
- **source_anchor**: fulltext.md L450
- **statement**: 秋丙退气，专用甲木生身，壬水显威；甲壬两透者贵；忌癸水熄丙。
- **applicable_to**: 丙日生于申酉戌月。
- **caveats**: 戌月燥土须配癸水反润；财格、官杀格另议。
- **verification_status**: unverified

### QR-02-04 — 三冬丙火

- **rule_id**: QR-02-04
- **source_chapter**: 三冬丙火
- **source_anchor**: fulltext.md L503-L557
- **statement**: 十月丙火按木旺、水旺、火旺分别酌用庚、戊、壬；十一月壬水为最、戊土佐之；十二月喜壬，土多时不可少甲。三冬不存在统一的壬甲戊三透规则。
- **applicable_to**: 丙日生于亥子丑月。
- **caveats**: 冬丙忌壬水无制泛滥；从杀格、化气格另议。
- **verification_status**: unverified

### QR-02-05 — 三春丁火

- **rule_id**: QR-02-05
- **source_chapter**: 三春丁火
- **source_anchor**: fulltext.md L561
- **statement**: 春丁柔弱，专用庚金劈甲、引甲生丁；甲庚不悖者贵。
- **applicable_to**: 丁日生于寅卯辰月。
- **caveats**: 庚金须有制（壬水或丁火本身），不可孤庚伤丁。
- **verification_status**: unverified

### QR-02-06 — 三夏丁火

- **rule_id**: QR-02-06
- **source_chapter**: 三夏丁火
- **source_anchor**: fulltext.md L609
- **statement**: 夏丁炎旺，用庚金、壬水（"金白水清"），庚壬两透者贵；忌甲木助火、戊土晦光。
- **applicable_to**: 丁日生于巳午未月。
- **caveats**: 未月燥土仍以壬水为先；炎上格另议。
- **verification_status**: unverified

### QR-02-07 — 三秋丁火

- **rule_id**: QR-02-07
- **source_chapter**: 三秋丁火
- **source_anchor**: fulltext.md L669
- **statement**: 秋丁退气，专用甲木生身为主、庚金劈甲为辅；甲庚两透者贵。
- **applicable_to**: 丁日生于申酉戌月。
- **caveats**: 酉月忌庚旺无丁；财格、杀格另议。
- **verification_status**: unverified

### QR-02-08 — 三冬丁火

- **rule_id**: QR-02-08
- **source_chapter**: 三冬丁火
- **source_anchor**: fulltext.md L707
- **statement**: 冬丁寒弱，专用甲木生身、庚金劈甲、戊土制水；甲庚戊三透不悖者贵。
- **applicable_to**: 丁日生于亥子丑月。
- **caveats**: 子月忌癸水透干熄丁；从杀格、化气格另议。
- **verification_status**: unverified

---

## QR-03 论土（行论 + 戊己土 × 四季）

### QR-03-00 — 论土总性

- **rule_id**: QR-03-00
- **source_chapter**: 论土
- **source_anchor**: fulltext.md L743
- **statement**: 土主信、性重，散在四维，不立一方；春土气虚而薄，宜火生之；夏土性燥，宜水润之；秋土子旺母衰，宜火助之；冬土外寒内温，宜火暖之。
- **applicable_to**: 戊己日主总论。
- **caveats**: 仅总纲。具体宜忌见 QR-03-01 ～ QR-03-08。
- **verification_status**: unverified

### QR-03-01 — 三春戊土

- **rule_id**: QR-03-01
- **source_chapter**: 三春戊土
- **source_anchor**: fulltext.md L769-L798
- **statement**: 正二月戊土先丙后甲、癸又次之；三月先甲后丙、癸又次之。春季共同涉及甲丙癸，但先后随月令改变。
- **applicable_to**: 戊日生于寅卯辰月。
- **caveats**: 寅月忌甲多无丙；正官格、七杀格另议。
- **verification_status**: unverified

### QR-03-02 — 三夏戊土

- **rule_id**: QR-03-02
- **source_chapter**: 三夏戊土
- **source_anchor**: fulltext.md L800
- **statement**: 夏戊燥裂，专用癸水润；丙火合癸化雨为辅。癸丙不悖（不直接相合即"既济"）者富贵。
- **applicable_to**: 戊日生于巳午未月。
- **caveats**: 午月忌火多焦土；从强格另议。
- **verification_status**: unverified

### QR-03-03 — 三秋戊土

- **rule_id**: QR-03-03
- **source_chapter**: 三秋戊土
- **source_anchor**: fulltext.md L848
- **statement**: 秋戊金多泄气，用丙火助身、癸水润、甲木疏。丙癸甲三者俱备者贵。
- **applicable_to**: 戊日生于申酉戌月。
- **caveats**: 戌月燥金燥土须癸水透干；伤官生财格另议。
- **verification_status**: unverified

### QR-03-04 — 三冬戊土

- **rule_id**: QR-03-04
- **source_chapter**: 三冬戊土
- **source_anchor**: fulltext.md L897-L929
- **statement**: 十月戊土先用甲木、次取丙火；十一、十二月严寒冰冻，丙火为专、甲木为佐。亥月与子丑月的先后次序不可混同。
- **applicable_to**: 戊日生于亥子丑月。
- **caveats**: 子月切忌癸水透干无丙；从财格另议。
- **verification_status**: unverified

### QR-03-05 — 三春己土

- **rule_id**: QR-03-05
- **source_chapter**: 三春己土
- **source_anchor**: fulltext.md L933
- **statement**: 春己阴湿，专用丙火暖、癸水润、甲木疏（合不化）。丙癸甲三者俱备者贵。
- **applicable_to**: 己日生于寅卯辰月。
- **caveats**: 己甲合化土须时柱配合，详见 sanming-tonghui 五合化气；正官格另议。
- **verification_status**: unverified

### QR-03-06 — 三夏己土

- **rule_id**: QR-03-06
- **source_chapter**: 三夏己土
- **source_anchor**: fulltext.md L981-L1002
- **statement**: 三夏己土取癸为要、次用丙火；原文以甘沛与太阳并论。此章不授权把辛金泄秀或癸辛两透写成三夏统一结论。
- **applicable_to**: 己日生于巳午未月。
- **caveats**: 未月忌火多燥土；伤官生财格另议。
- **verification_status**: unverified

### QR-03-07 — 三秋己土

- **rule_id**: QR-03-07
- **source_chapter**: 三秋己土
- **source_anchor**: fulltext.md L1006-L1029
- **statement**: 三秋己土以丙火温、癸水润，癸先丙后；九月土盛时另宜甲木疏之。不得据此虚构丙癸辛三透的统一规则。
- **applicable_to**: 己日生于申酉戌月。
- **caveats**: 戌月燥土须癸水透干。
- **verification_status**: unverified

### QR-03-08 — 三冬己土

- **rule_id**: QR-03-08
- **source_chapter**: 三冬己土
- **source_anchor**: fulltext.md L1031
- **statement**: 冬己寒湿，专用丙火暖、戊土帮身；不忌甲木合身（合而无化）。丙戊两透者贵。
- **applicable_to**: 己日生于亥子丑月。
- **caveats**: 子月忌水多无丙；从财格另议。
- **verification_status**: unverified

---

## QR-04 论金（行论 + 庚辛金 × 四季）

### QR-04-00 — 论金总性

- **rule_id**: QR-04-00
- **source_chapter**: 论金
- **source_anchor**: fulltext.md L1068
- **statement**: 金性沉重、主义、性刚；春金犹寒，宜火气以舒之；夏金尤柔，宜土厚以扶之；秋金当权，喜火炼以成器；冬金寒甚，喜火暖以解冻。
- **applicable_to**: 庚辛日主总论。
- **caveats**: 仅总纲。具体宜忌见 QR-04-01 ～ QR-04-08。
- **verification_status**: unverified

### QR-04-01 — 三春庚金

- **rule_id**: QR-04-01
- **source_chapter**: 三春庚金
- **source_anchor**: fulltext.md L1072-L1133
- **statement**: 正月庚金以丙甲为上、丁火次之；二月专用丁火并借甲引丁、借庚劈甲；三月先甲后丁。三春须逐月读取。
- **applicable_to**: 庚日生于寅卯辰月。
- **caveats**: 寅月仍寒，丁火不可无；正财格另议。
- **verification_status**: unverified

### QR-04-02 — 三夏庚金

- **rule_id**: QR-04-02
- **source_chapter**: 三夏庚金
- **source_anchor**: fulltext.md L1137-L1166
- **statement**: 四月庚金参用壬丙戊；五月专用壬水、癸又次之；六月先用丁火、次取甲木。三夏没有统一的壬戊组合。
- **applicable_to**: 庚日生于巳午未月。
- **caveats**: 午月忌丁多熔金；从杀格另议。
- **verification_status**: unverified

### QR-04-03 — 三秋庚金

- **rule_id**: QR-04-03
- **source_chapter**: 三秋庚金
- **source_anchor**: fulltext.md L1168
- **statement**: 秋庚得令，专用丁火炼成器、甲木引丁。丁甲两透不悖者大贵。
- **applicable_to**: 庚日生于申酉戌月。
- **caveats**: 戌月燥土反晦丁，须癸水或壬水调；从革格另议。
- **verification_status**: unverified

### QR-04-04 — 三冬庚金

- **rule_id**: QR-04-04
- **source_chapter**: 三冬庚金
- **source_anchor**: fulltext.md L1214
- **statement**: 冬庚寒，专用丁火炼、丙火暖、戊土制水。丁丙戊俱透者贵。
- **applicable_to**: 庚日生于亥子丑月。
- **caveats**: 子月忌伤官无制；从儿格另议。
- **verification_status**: unverified

### QR-04-05 — 三春辛金

- **rule_id**: QR-04-05
- **source_chapter**: 三春辛金
- **source_anchor**: fulltext.md L1260
- **statement**: 春辛弱嫩，专用己土生身、壬水洗辛。己壬两透者贵；忌丙火合辛化水误用。
- **applicable_to**: 辛日生于寅卯辰月。
- **caveats**: 春辛见戊土反埋；正官格另议。
- **verification_status**: unverified

### QR-04-06 — 三夏辛金

- **rule_id**: QR-04-06
- **source_chapter**: 三夏辛金
- **source_anchor**: fulltext.md L1311
- **statement**: 夏辛被火炼，专用壬水洗辛、己土护身、癸水润。壬己癸三透者贵。
- **applicable_to**: 辛日生于巳午未月。
- **caveats**: 未月燥土须癸水透干；从杀格另议。
- **verification_status**: unverified

### QR-04-07 — 三秋辛金

- **rule_id**: QR-04-07
- **source_chapter**: 三秋辛金
- **source_anchor**: fulltext.md L1348-L1405
- **statement**: 七月辛金以壬水为尊、甲戊酌用；八月专用壬水，见戊己时才以甲制土；九月先壬后甲。不得把甲戊无条件并入所有秋月。
- **applicable_to**: 辛日生于申酉戌月。
- **caveats**: 酉月忌伤官见官。
- **verification_status**: unverified

### QR-04-08 — 三冬辛金

- **rule_id**: QR-04-08
- **source_chapter**: 三冬辛金
- **source_anchor**: fulltext.md L1407
- **statement**: 冬辛寒甚，专用丙火暖（合而不化于本月），壬水洗辛（不寒）。丙壬两透清纯者贵。
- **applicable_to**: 辛日生于亥子丑月。
- **caveats**: 子月忌癸水寒辛无丙；化气格另议。
- **verification_status**: unverified

---

## QR-05 论水（行论 + 壬癸水 × 四季）

### QR-05-00 — 论水总性

- **rule_id**: QR-05-00
- **source_chapter**: 论水
- **source_anchor**: fulltext.md L1440
- **statement**: 水主智、性聪，至清而柔；春水泛滥，宜土堤之；夏水涸竭，宜金生之；秋水通源，喜水之归；冬水冻凝，喜火之暖。
- **applicable_to**: 壬癸日主总论。
- **caveats**: 仅总纲。具体宜忌见 QR-05-01 ～ QR-05-08。
- **verification_status**: unverified

### QR-05-01 — 三春壬水

- **rule_id**: QR-05-01
- **source_chapter**: 三春壬水
- **source_anchor**: fulltext.md L1456
- **statement**: 春壬泄气于木，用辛金生身；如盘中水势已盛，配戊土堤防。辛戊适配者贵。
- **applicable_to**: 壬日生于寅卯辰月。
- **caveats**: 辰月水库须看戊土透不透；伤官生财格另议。
- **verification_status**: unverified

### QR-05-02 — 三夏壬水

- **rule_id**: QR-05-02
- **source_chapter**: 三夏壬水
- **source_anchor**: fulltext.md L1496-L1530
- **statement**: 四月壬水取壬比肩为助、辛金发源、庚金为佐；五月取癸为用、庚为佐；六月先辛后甲、次取癸水。三夏用法逐月不同。
- **applicable_to**: 壬日生于巳午未月。
- **caveats**: 午月忌火多无金；从财格另议。
- **verification_status**: unverified

### QR-05-03 — 三秋壬水

- **rule_id**: QR-05-03
- **source_chapter**: 三秋壬水
- **source_anchor**: fulltext.md L1532
- **statement**: 秋壬通源旺极，用戊土堤防、丁火财星为佐。戊丁两透者贵。
- **applicable_to**: 壬日生于申酉戌月。
- **caveats**: 戌月燥土过重反塞水源；从儿格另议。
- **verification_status**: unverified

### QR-05-04 — 三冬壬水

- **rule_id**: QR-05-04
- **source_chapter**: 三冬壬水
- **source_anchor**: fulltext.md L1587-L1625
- **statement**: 十月壬水专用戊丙、次取庚金；十一月先戊后丙；十二月专用丙火、甲木为佐。戊丙不是三冬不分月令的统一结论。
- **applicable_to**: 壬日生于亥子丑月。
- **caveats**: 子月忌癸水透干争夫；化气格另议。
- **verification_status**: unverified

### QR-05-05 — 三春癸水

- **rule_id**: QR-05-05
- **source_chapter**: 三春癸水
- **source_anchor**: fulltext.md L1629
- **statement**: 春癸泄于木，用辛金生身、丙火配（不可同透相合）。辛丙间透者贵。
- **applicable_to**: 癸日生于寅卯辰月。
- **caveats**: 戊癸合化火须看时柱与化神是否得令；正官格另议。
- **verification_status**: unverified

### QR-05-06 — 三夏癸水

- **rule_id**: QR-05-06
- **source_chapter**: 三夏癸水
- **source_anchor**: fulltext.md L1671
- **statement**: 夏癸枯竭，专用辛金生身、庚金为辅。辛庚两透者贵；忌火多无金。
- **applicable_to**: 癸日生于巳午未月。
- **caveats**: 未月燥土塞水源，须癸水透干自助。
- **verification_status**: unverified

### QR-05-07 — 三秋癸水

- **rule_id**: QR-05-07
- **source_chapter**: 三秋癸水
- **source_anchor**: fulltext.md L1692
- **statement**: 秋癸通源，用辛金生身、丁火制辛（不忌庚金）。辛丁不悖者贵。
- **applicable_to**: 癸日生于申酉戌月。
- **caveats**: 戌月燥土须辛金护癸；伤官生财格另议。
- **verification_status**: unverified

### QR-05-08 — 三冬癸水

- **rule_id**: QR-05-08
- **source_chapter**: 三冬癸水
- **source_anchor**: fulltext.md L1731-L1764
- **statement**: 十月癸水宜用庚辛；十一月专用丙火解冻并要辛金滋扶；十二月宜丙火解冻。亥子丑三月不得合并为统一丙辛规则。
- **applicable_to**: 癸日生于亥子丑月。
- **caveats**: 子月忌水多无丙；从强格另议。
- **verification_status**: unverified

---

## 通用 caveats（适用于全部 QR-NN-MM 调候规则）

- 调候用神 ≠ 唯一用神：必须与旺衰、格局合参。
- 月令分界以 **节气** 为准，必须由 `tool.bazi.paipan` 取得。
- "用某干"是指该天干在盘中**透出**（年/月/时三干，最有效是月时透）；不透时按"取其同类（地支藏干）或虚用"处理。
- 调候规则不可单独用于断富贵贫贱；富贵贫贱属于复合判断，详见 `bazi/sanming-tonghui` 与冲突裁判。
- 涉及"贵格"等判语，仅作子平派传统判断标记，不作现代社会身份的对应。
- 涉及健康、寿命、子嗣、女命的判语，不在本 pack 提供；详见 `matrices/conflict-policy.md` 与 `matrices/safety-redlines.md`。

---

## 全书规则统计

- 总论规则：1 条（QR-00-01）
- 行论规则：5 条（QR-NN-00）
- 月令子目规则：40 条（QR-NN-MM, NN ∈ {01..05}, MM ∈ {01..08}）
- **总计**：**46 条规则**

详细覆盖率与对校状态见 [validation.md](./validation.md)。
