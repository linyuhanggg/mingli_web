# 增删卜易 — Procedures

> 本文件抽取《增删卜易》六爻金钱卦的可路由操作流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verification_status`。
> 全部 `pending_verification`。
> **核心约束**：所有装卦 / 排纳甲 / 安世应 / 旬空 / 月破等事实层运算，一律调用 `tool.divination.liuyao_bindisk`；**禁止 LLM 手算**。
> procedure_id 前缀 `ZP` = Zengshan Procedure。

---

## ZP-01 三钱起卦法（金钱卦摇卦）

- **inputs**：
  - 占问主题（一事一占）
  - 占问时间（年 / 月 / 日 / 时，含真太阳时）
  - 三枚铜钱（或硬币）
- **steps**：
  1. 心诚意专，默念所占之事。
  2. 摇钱六次，每次记录三钱正反：
     - 三背为老阳（重，动爻 ⚊○）
     - 三面为老阴（交，动爻 ⚋×）
     - 二背一面为少阴（拆 ⚋）
     - 二面一背为少阳（单 ⚊）
  3. 自下而上记爻，初爻先摇、上爻后摇。
  4. 得本卦六爻 + 老阴老阳变成本变两卦。
- **outputs**：本卦 + 变卦的爻象表
- **tool_dependencies**：`tool.divination.liuyao_bindisk`（标准化记爻 / 验证摇卦合规）
- **source_chapter**：vol-01/ch-01-bagua（八卦）+ ch-23-fubai-yaoxiang
- **verification_status**：pending_verification

## ZP-02 装卦（纳甲 + 世应 + 六亲 + 六神）

- **inputs**：本卦 + 变卦六爻
- **steps**：
  1. **定卦宫**：根据本卦上下卦判定属八宫之何宫（乾、坎、艮、震、巽、离、坤、兑）。
  2. **配纳甲**（浑天甲子）：按八宫卦纳甲表配六爻地支。
  3. **安世应**：按八宫"一世二世……归魂"位置定世应（世应隔三爻相对）。
  4. **配六亲**：以本宫五行为我，按生克定父母 / 兄弟 / 子孙 / 妻财 / 官鬼。
  5. **配六神**：按占日天干起六神（甲乙日起青龙、丙丁起朱雀、戊起勾陈、己起腾蛇、庚辛起白虎、壬癸起玄武），自初爻向上排。
  6. **标动爻 / 变爻**：老阴老阳之爻为动，变出之爻为变。
- **outputs**：完整装好的卦盘（六爻、纳甲、世应、六亲、六神、动变）
- **tool_dependencies**：`tool.divination.liuyao_bindisk`（**强制**：装卦事实层禁止 LLM 手算）
- **source_chapter**：vol-01/ch-03-bagong + ch-04-huntian-jiazi + ch-05-liuqin + ch-06-shiying + ch-19-liushen
- **verification_status**：pending_verification

## ZP-03 标月建 / 日辰 / 旬空

- **inputs**：装好的卦盘 + 占问年月日时
- **steps**：
  1. **月建**：占月之地支为月将，主管全卦旺衰一月。
  2. **日辰**：占日之地支为日辰，主管全卦旺衰一日（事之主宰）。
  3. **旬空**：以占日所在旬定旬空（甲子旬空戌亥、甲戌旬空申酉、甲申旬空午未、甲午旬空辰巳、甲辰旬空寅卯、甲寅旬空子丑）。
  4. **月破**：与月建相冲之爻为月破。
  5. **暗动**：日辰冲卦中静爻而该爻得令旺相，为暗动（动而不显）。
- **outputs**：标记完整的旺衰 / 旬空 / 月破 / 暗动状态
- **tool_dependencies**：`tool.divination.liuyao_bindisk`（旬空 / 月破 / 暗动判定由工具完成）
- **source_chapter**：vol-01/ch-17-yueli + ch-18-rilun + ch-25-xunkong + vol-02/ch-27-yuepo
- **verification_status**：pending_verification

## ZP-04 取用神（按问占类型）

- **inputs**：装好的卦盘 + 问占主题
- **steps**：
  1. **识别问占类型**（按下表对应六亲）：
     - 父母用神：父母、长辈、师长、文书、契约、舟车、城池、屋宅、衣服、雨具
     - 官鬼用神：官职、功名、夫君（女命）、官讼、疾病（病象）、鬼神
     - 妻财用神：妻妾（男命）、财物、金钱、奴婢、用物、晴天
     - 子孙用神：子孙、晚辈、医药、僧道、六畜、解忧、福神
     - 兄弟用神：兄弟、姐妹、朋友、同僚、劫财
  2. **检查用神是否上卦**：
     - 上卦 → 用之
     - 不上卦 → 取本宫伏神
     - 用神两现 → 取旺者 / 临世应者 / 临日月者；详见 vol-02/ch-32-liangxian
  3. **取元神 / 忌神 / 仇神**：生用神者元神、克用神者忌神、克元神生忌神者仇神。
- **outputs**：用神 + 元神 + 忌神 + 仇神 4 爻定位
- **tool_dependencies**：—（取用神规则可由 LLM 推理，但用神所在位置由 ZP-02 已定）
- **source_chapter**：vol-01/ch-08-yongshen + ch-09-yuanjichou + vol-02/ch-29-feifushen + ch-32-liangxian
- **verification_status**：pending_verification

## ZP-05 旺衰判断（用神主导）

- **inputs**：用神所在爻 + 月建 + 日辰
- **steps**：
  1. **看月建对用神**：生扶 / 比和 → 旺；克泄 → 衰；冲 → 月破；同 → 临月建（极旺）。
  2. **看日辰对用神**：生扶 → 有气；克 → 受伤；冲 → 暗动 / 日破（视用神原静原动）；合 → 日合（绊住）。
  3. **看动爻对用神**：动来生 → 大吉；动来克 → 凶；动而合 → 牵制；动而冲 → 散。
  4. **综合判定**：旺者事可成；衰且无救者事难成；旺而被合 → 应期延；衰而逢生 → 应期至生扶之日。
- **outputs**：用神旺衰等级 + 是否成事
- **tool_dependencies**：—（理论判断由 LLM；事实层旺衰由 ZP-03 工具输出）
- **source_chapter**：vol-01/ch-10-wangshuai ~ ch-13-dongjingshengke
- **verification_status**：pending_verification

## ZP-06 动爻 / 变爻 / 反伏吟判断

- **inputs**：标动 / 变爻的卦盘
- **steps**：
  1. **动爻主事**：卦中动爻为事之变化主线；静爻为不变之事。
  2. **化进 / 化退**：动爻变出之爻地支较本爻进一步（如寅化卯）为化进、退一步（卯化寅）为化退。
  3. **化回头生 / 克**：变爻生本爻 → 化回头生（吉）；变爻克本爻 → 化回头克（凶）。
  4. **化绝 / 化墓 / 化空**：变爻使本爻入绝 / 入墓 / 旬空，皆主事中止或失败。
  5. **反吟 / 伏吟**：本卦变卦内外卦相冲为反吟（事反复）；本卦变卦相同地支为伏吟（事呻吟难进）。
- **outputs**：动爻吉凶 + 反伏吟状态
- **tool_dependencies**：`tool.divination.liuyao_bindisk`（化进退 / 反伏吟由工具识别）
- **source_chapter**：vol-01/ch-22-guabian + ch-24-fanfu + vol-02/ch-30-jintui
- **verification_status**：pending_verification

## ZP-07 应期判断

- **inputs**：用神状态 + 旬空 / 月破 / 合冲 / 旺衰
- **steps**：
  1. **用神旺而静** → 应期为冲应（被冲之日 / 月）。
  2. **用神旺而动** → 应期为合应（合住之日）。
  3. **用神入墓** → 应期为冲墓库 / 出墓之日。
  4. **用神逢空** → 应期为出空 / 填实之日。
  5. **用神被合** → 应期为冲开之日。
  6. **用神被克** → 应期为克力解除日（克者被合 / 被冲 / 入墓）。
  7. **应远应近**：动应近（爻动之日月）；静应远（候令之冲）。
- **outputs**：应事发生的具体日期范围
- **tool_dependencies**：`tool.divination.liuyao_bindisk`（应期天干地支推算由工具）
- **source_chapter**：vol-01/ch-15-liuhe-liuchong-sanxing + ch-16-andong-dongsan + ch-26-guihun-youhun
- **verification_status**：pending_verification

## ZP-08 综合占断流程（顶层）

- **inputs**：占问主题 + 时间
- **steps**：
  1. ZP-01 起卦
  2. ZP-02 装卦（含纳甲 / 世应 / 六亲 / 六神）
  3. ZP-03 标月建 / 日辰 / 旬空 / 月破 / 暗动
  4. ZP-04 取用神 + 元神 + 忌神 + 仇神
  5. ZP-05 判旺衰
  6. ZP-06 看动变 / 反伏
  7. ZP-07 定应期
  8. **门类断诀**：按问占类型查 ZP-09 路由相应章节
  9. 综合给出吉凶 + 应期 + 变化建议
- **outputs**：完整占断报告
- **tool_dependencies**：`tool.divination.liuyao_bindisk`（前 ZP-01~ZP-03、ZP-06 由工具）
- **source_chapter**：全书框架
- **verification_status**：pending_verification

## ZP-09 按问占类型路由章节

- **inputs**：用户问题主题
- **steps**：
  1. **身命 / 终身** → vol-03/ch-36-shenming + ch-37-zhongshen
  2. **求名 / 功名 / 科举** → vol-03/ch-46~58（童试 / 乡试 / 会试 / 殿试 / 武试）
  3. **求财** → vol-03/ch-59-qiucai + vol-04/ch-69~74（求财细分）
  4. **婚姻** → vol-04/ch-75~80
  5. **胎孕 / 产育** → vol-04/ch-81~84
  6. **出行 / 行人** → vol-04/ch-85~91
  7. **官讼** → vol-04/ch-92~98
  8. **疾病 / 痘疹** → vol-04/ch-99~108
  9. **家宅 / 蓋造** → vol-04/ch-109~118
  10. **风水 / 阴宅 / 茔葬** → vol-04/ch-119~130
  11. **天时 / 农时** → vol-02/ch-35-tianshi
- **outputs**：路由到的具体章节 + 该门类下用神 / 应期口诀
- **tool_dependencies**：—
- **source_chapter**：全书章节索引
- **verification_status**：pending_verification

---

## 现代使用边界

- **ZP-01 起卦**：本流程为传统三钱摇卦，现代亦有数字 / 时间起卦法（属梅花体系，应转 `meihua-yishu`）。
- **ZP-02 装卦**：装卦是事实层运算，**严禁 LLM 手算**；必须 `tool.divination.liuyao_bindisk`。
- **ZP-04 取用神**：女命问夫取官鬼（书中默认观念），现代取用应基于咨询者具体身份与意图，不应教条套用。
- **ZP-09 疾病占**：本书第 99-108 章详述疾病占断；占断仅为参考，**不能替代医学诊断**；急重症必须就医。
- **ZP-09 寿元 / 终身占**：仅供文化参考；不应用于现代医保 / 保险 / 雇佣等决策。
- **ZP-09 官讼占**：不应用于法律实务决策；遇法律事务必请律师。
