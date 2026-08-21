# 御定星历考原 — Rules

> 全书判断规则。前缀 `KR-` = Kaoyuan Rule（星历考原规则）。
> 所有规则 `verified: false`；具体日期吉凶必须转 mingli-master.selection.v1。
> 规则定位：本书是"神煞起例的官方考源"，规则多为起例 / 起源 / 配位 / 通则，不直接判断"某日吉凶"。

---

## KR-01 总纲：考源蓝本

- **rule_id**: KR-01
- **rule_statement**: 本书为康熙朝官方择日典籍考源；其规则定位是"神煞出处与起例口诀的官方源头"，不直接定具体某日吉凶。
- **source_chapter**: front/yu-zhi-xu
- **applicable_to**: 主 skill 在引用神煞时确认起例来源
- **caveats**: 文化参考，非事实判断
- **verified**: false

## KR-02 五纪与甲历

- **rule_id**: KR-02
- **rule_statement**: 五纪（岁、月、日、星辰、历数）与甲历（六十甲子）共同构成择日体系的时间坐标。
- **source_chapter**: vol-01-xiangshu
- **applicable_to**: 任何择日规则的时间表述前提
- **verified**: false

## KR-03 十二月辟卦配月

- **rule_id**: KR-03
- **rule_statement**: 十二月配十二消息卦：复（子）、临（丑）、泰（寅）、大壮（卯）、夬（辰）、乾（巳）、姤（午）、遯（未）、否（申）、观（酉）、剥（戌）、坤（亥）。
- **source_chapter**: vol-01-xiangshu
- **applicable_to**: 月令配卦的官方依据
- **verified**: false

## KR-04 二十四方位与二十四节气对应

- **rule_id**: KR-04
- **rule_statement**: 二十四方位（十二支 + 八天干 + 四维）对应二十四节气；方位与节气共构空间-时间矩阵。
- **source_chapter**: vol-01-xiangshu
- **applicable_to**: 方位 / 节气交叉的择日推算
- **verified**: false

## KR-05 五虎遁与五鼠遁

- **rule_id**: KR-05
- **rule_statement**: 五虎遁（年起月）：甲己起丙寅、乙庚起戊寅、丙辛起庚寅、丁壬起壬寅、戊癸起甲寅；五鼠遁（日起时）：甲己起甲子、乙庚起丙子、丙辛起戊子、丁壬起庚子、戊癸起壬子。
- **source_chapter**: vol-01-xiangshu
- **applicable_to**: 月柱 / 时柱起例（亦为八字四柱之依据）
- **verified**: false

## KR-06 三合 / 五合 / 六合

- **rule_id**: KR-06
- **rule_statement**: 三合：申子辰水、亥卯未木、寅午戌火、巳酉丑金；五合（天干）：甲己土、乙庚金、丙辛水、丁壬木、戊癸火；六合（地支）：子丑、寅亥、卯戌、辰酉、巳申、午未。
- **source_chapter**: vol-01-xiangshu
- **applicable_to**: 神煞配合 / 择日选时 / 课体合化基础
- **verified**: false

## KR-07 三元年九星

- **rule_id**: KR-07
- **rule_statement**: 上中下三元各 60 年，每元起九星入中宫；上元起一白、中元起四绿、下元起七赤；逐年逆转。
- **source_chapter**: vol-02-nianshen
- **applicable_to**: 年神方位推算（亦为玄空风水基础）
- **verified**: false

## KR-08 太岁与年神

- **rule_id**: KR-08
- **rule_statement**: 太岁为年神之首，居当年地支位；年神有岁德合 / 岁枝德等吉神，与大将军 / 太阴 / 白虎 / 豹尾 / 金神七煞 / 力士等凶神。
- **source_chapter**: vol-02-nianshen
- **applicable_to**: 年方位的择日 / 风水通用基础
- **caveats**: 文化参考，非事实判断
- **verified**: false

## KR-09 金神七煞起例

- **rule_id**: KR-09
- **rule_statement**: 金神七煞由年干推算，每年所占方位不同；为方位之大凶神，忌动土 / 修造。
- **source_chapter**: vol-02-nianshen
- **applicable_to**: 起造 / 修造动土择年
- **caveats**: 文化参考，非事实判断；具体方位由 mingli-master.selection.v1 输出。
- **verified**: false

## KR-10 大将军方

- **rule_id**: KR-10
- **rule_statement**: 大将军居太岁三方之冲（一说三方对宫），主战伐之神；忌兴造、动土、伐木。
- **source_chapter**: vol-02-nianshen
- **applicable_to**: 起造方位通则
- **caveats**: 文化参考，非事实判断
- **verified**: false

## KR-11 月吉神（天德 / 月德 / 月空 / 母仓）

- **rule_id**: KR-11
- **rule_statement**: 天德（按月轮转吉方）、月德（与天德并列）、月空（虚位之吉）、母仓（主孳息）共为月吉神核心；月德合 / 天德合为其合神。
- **source_chapter**: vol-03-yueji
- **applicable_to**: 月择日的吉日 / 吉方筛选
- **verified**: false

## KR-12 月凶神（月建 / 月破 / 月厌 / 月害）

- **rule_id**: KR-12
- **rule_statement**: 月建（该月建除之首）；月破（月建对冲日）；月厌（按月逆轮）；月害（六害关系）；为月凶神核心。
- **source_chapter**: vol-04-yuexiong
- **applicable_to**: 月择日的避忌
- **caveats**: 文化参考，非事实判断
- **verified**: false

## KR-13 四废 / 四离 / 四绝

- **rule_id**: KR-13
- **rule_statement**: 四废：春庚辛日、夏壬癸日、秋甲乙日、冬丙丁日；四离：二分二至前一日；四绝：四立前一日。共为节气交替之大忌。
- **source_chapter**: vol-04-yuexiong
- **applicable_to**: 用事日的硬避忌
- **caveats**: 文化参考，非事实判断
- **verified**: false

## KR-14 黄道黑道（六黄六黑）

- **rule_id**: KR-14
- **rule_statement**: 黄道六神：青龙、明堂、金匮、天德、玉堂、司命（吉）；黑道六神：天刑、朱雀、白虎、天牢、玄武、勾陈（凶）；按月建逐日轮配。
- **source_chapter**: vol-05-rishi
- **applicable_to**: 日吉凶的官方通则
- **verified**: false

## KR-15 二十八宿配日

- **rule_id**: KR-15
- **rule_statement**: 二十八宿（角亢氐房心尾箕…）按七曜（日月火水木金土）周而复始配日；每宿主吉凶不同。
- **source_chapter**: vol-05-rishi
- **applicable_to**: 日吉凶的星宿层判定
- **verified**: false

## KR-16 贵登天门 / 四大吉时

- **rule_id**: KR-16
- **rule_statement**: 时神之首为贵登天门（贵人乘天乙之时）；其次为四大吉时；按日干起十二贵人时辰。
- **source_chapter**: vol-05-rishi
- **applicable_to**: 选时的官方通则
- **verified**: false

## KR-17 用事六十事项分类

- **rule_id**: KR-17
- **rule_statement**: 卷六将"用事"系统化为六十事项（祭祀 / 嫁娶 / 起造 / 商事 / 安葬 / 出行 / 农事 / 医疗 / 沐浴 / 修缮 等）；每事项有官方"宜 / 忌"通例。
- **source_chapter**: vol-06-yongshi
- **applicable_to**: 用事分类的官方依据
- **caveats**: 文化参考，非事实判断；具体某事某日的吉凶由 mingli-master.selection.v1 输出。
- **verified**: false

## KR-18 嫁娶择日通则

- **rule_id**: KR-18
- **rule_statement**: 嫁娶择日宜天德 / 月德 / 天德合 / 月德合 / 三合 / 六合等吉神；忌月厌 / 月破 / 受死 / 八专 / 四废等。
- **source_chapter**: vol-06-yongshi
- **applicable_to**: 嫁娶择日
- **caveats**: 文化参考，非事实判断
- **verified**: false

## KR-19 安葬启攒通则

- **rule_id**: KR-19
- **rule_statement**: 安葬宜鸣吠 / 鸣吠对 / 月恩 / 三合等；忌重丧 / 复日 / 重日 / 月破 / 月厌等。
- **source_chapter**: vol-06-yongshi
- **applicable_to**: 安葬择日
- **caveats**: 文化参考，非事实判断
- **verified**: false

## KR-20 起造修造动土通则

- **rule_id**: KR-20
- **rule_statement**: 起造 / 修造动土宜成日 / 开日 / 月恩 / 母仓；忌土王用事 / 月破 / 月厌 / 大将军 / 金神七煞方。
- **source_chapter**: vol-06-yongshi
- **applicable_to**: 起造修造择日 + 择方位
- **caveats**: 文化参考，非事实判断；方位避忌由 mingli-master.selection.v1 与 fengshui pack 联合输出。
- **verified**: false

---

**说明**：共 20 条规则。本书规则的核心特色是"神煞起例考源"；具体某日某事的吉凶判断必须转 `mingli-master.selection.v1`。
