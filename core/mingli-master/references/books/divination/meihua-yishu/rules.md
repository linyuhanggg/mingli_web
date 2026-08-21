# 梅花易数 — Rules

> 本文件抽取《梅花易数》全书的可路由判断规则。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `applicable_to` / `caveats` / `verification_status`。
> 全部 `pending_verification`（维基文库本未对古本逐篇复核）。
> rule_id 前缀 `MR` = Meihua Rule。

---

## 一、基础规则（先天数与五行）

### MR-01-01 八卦先天数

- **rule_statement**：八卦先天数序为乾一、兑二、离三、震四、巽五、坎六、艮七、坤八；起卦取数皆以此为本。
- **source_chapter**：xsly-1/zhouyi-guashu
- **applicable_to**：所有起卦
- **caveats**：与文王后天八卦数次序不同，勿与京房纳甲混。
- **verification_status**：pending_verification

### MR-01-02 五行生克

- **rule_statement**：金生水、水生木、木生火、火生土、土生金；金克木、木克土、土克水、水克火、火克金。
- **source_chapter**：xsly-1/wuxing-shengke
- **applicable_to**：体用生克判断的底层规则
- **caveats**：基础铺垫。
- **verification_status**：pending_verification

### MR-01-03 八宫所属五行

- **rule_statement**：乾兑属金、坤艮属土、震巽属木、坎属水、离属火。
- **source_chapter**：xsly-1/bagong-wuxing
- **applicable_to**：体用生克的卦 → 五行映射
- **caveats**：与京房八宫纳甲分宫不同。
- **verification_status**：pending_verification

### MR-01-04 卦气旺

- **rule_statement**：震巽木旺于春；离火旺于夏；乾兑金旺于秋；坎水旺于冬；坤艮土旺于辰戌丑未月。
- **source_chapter**：xsly-1/guaqi-wang
- **applicable_to**：体用衰旺判断
- **caveats**：与"卦气衰"对照使用（MR-01-05）。
- **verification_status**：pending_verification

### MR-01-05 卦气衰

- **rule_statement**：春坤艮衰、夏乾兑衰、秋震巽衰、冬离衰、辰戌丑未坎衰。
- **source_chapter**：xsly-1/guaqi-shuai
- **applicable_to**：体用衰旺判断
- **caveats**：用以衡量克我者之力（克体若克者衰，凶力减；体若衰，更怕克）。
- **verification_status**：pending_verification

## 二、起卦规则

### MR-02-01 卦以八除

- **rule_statement**：起上下卦时以总数除以 8，取余数对应八卦先天数（恰得 8 取坤）；不足 8 直接取数。
- **source_chapter**：xsly-1/gua-yibachu
- **applicable_to**：所有数字起卦法
- **caveats**：必须由 `tool.divination.qiguagua` 计算，禁止 LLM 手算。
- **verification_status**：pending_verification

### MR-02-02 爻以六除

- **rule_statement**：起动爻时以重卦总数（年 + 月 + 日 + 时）除以 6，取余数为动爻位（恰得 6 取上爻）。
- **source_chapter**：xsly-1/yao-yiliuchu
- **applicable_to**：所有先天起卦
- **caveats**：动爻一爻为常；多爻动需另解（古法不出本书规范）。
- **verification_status**：pending_verification

### MR-02-03 互卦取法

- **rule_statement**：互卦只用八卦不取六十四卦名；以重卦的二三四爻为下互、三四五爻为上互；乾坤无互，互其变卦。
- **source_chapter**：xsly-1/hugua-qili
- **applicable_to**：体用占断中"事之中"分析
- **caveats**：本书互卦法与京房六爻不同，不可混用。
- **verification_status**：pending_verification

### MR-02-04 起卦时机原则

- **rule_statement**：可数之物 / 已成器物 / 已栽树木 / 已建屋宅可起卦；江河山石及未成之物不可起卦；牛马犬豕初生 / 初置时方可起卦。
- **source_chapter**：xsly-1/zhan-jingwu
- **applicable_to**：所有占断时机选择
- **caveats**：起卦机不应强占，"无故不占"为本书心法。
- **verification_status**：pending_verification

## 三、当日动静占（外应）

### MR-03-01 当日动静占

- **rule_statement**：求占者报数起卦，以体用生克及卦象类比断当日动静吉凶；用克体凶、体克用顺、比和平、用生体得、体生用失。
- **source_chapter**：xsly-3/jinwei-laozhan
- **applicable_to**：日常吉凶占断
- **caveats**：仅供参考，非命理结论。
- **verification_status**：pending_verification

## 四、体用生克核心规则

### MR-04-01 体用之分

- **rule_statement**：起卦后含动爻一卦为用，不含动爻一卦为体；体卦为问占者本身 / 主体，用卦为所问之事 / 客体；体用乃占断主轴。
- **source_chapter**：tyk-1/tiyong-zonglun
- **applicable_to**：所有梅花占断
- **caveats**：若两卦皆有动爻或两卦皆无动爻，按本书"用卦取动多者"约定（具体看正文细则）。
- **verification_status**：pending_verification

### MR-04-02 体用生克吉凶（核心）

- **rule_statement**：用卦生体卦——大吉，主有外财外喜；体卦生用卦——主耗、退财；用卦克体卦——大凶；体卦克用卦——主顺、克他人；体用比和（同五行）——吉，事顺。
- **source_chapter**：tyk-1/tiyong-shengke-jixiong
- **applicable_to**：所有体用占断
- **caveats**：吉凶轻重还须看体用之衰旺；体衰受克尤凶，体旺受克较缓。
- **verification_status**：pending_verification

### MR-04-03 比和

- **rule_statement**：体用同五行（如皆木皆金）为比和，事顺利、平稳；不主大吉大凶。
- **source_chapter**：tyk-1/biheli-shi
- **applicable_to**：体用比和场合
- **caveats**：比和虽吉，仍须看互变。
- **verification_status**：pending_verification

### MR-04-04 互变之用

- **rule_statement**：互卦看事之中（过程曲折），变卦看事之终（结果归宿）；互变之卦与体用之生克须合参。
- **source_chapter**：tyk-1/hubian-zhi-yong
- **applicable_to**：占断过程与结果
- **caveats**：变卦克体凶；变卦生体吉。
- **verification_status**：pending_verification

### MR-04-05 体用之变

- **rule_statement**：体用并非固定，因时因事而变；体之力借助于互变之中之比和、生扶、克泄综合判断。
- **source_chapter**：tyk-2/tiyong-bian
- **applicable_to**：复杂占例
- **caveats**：体用之变需经验；不可机械套用。
- **verification_status**：pending_verification

### MR-04-06 变卦并体

- **rule_statement**：变卦旺则减体之力，变卦克体则祸；变卦生体则福。
- **source_chapter**：tyk-2/biangua-bingti
- **applicable_to**：占断结果导向
- **caveats**：变卦之力小于本卦体用，但决定事之终向。
- **verification_status**：pending_verification

## 五、克应期与衰旺

### MR-05-01 克应之期

- **rule_statement**：应期取八卦数（如乾应戌亥年月日时）+ 时令旺衰 + 卦气强弱综合断；不可单凭一项。
- **source_chapter**：tyk-3/keying-zhi-qi
- **applicable_to**：占断应期判断
- **caveats**：应期判断属经验性，本书仅给框架；不应作为现代精准时间预测。
- **verification_status**：pending_verification

### MR-05-02 卦气衰旺合参

- **rule_statement**：体卦旺则吉力大、凶力减；体卦衰则吉力减、凶力大；判生克须先衡量旺衰。
- **source_chapter**：tyk-4/guaqi-shuaiwang
- **applicable_to**：所有体用判断
- **caveats**：旺衰参 MR-01-04 / MR-01-05。
- **verification_status**：pending_verification

## 六、十类问占断诀

### MR-07-01 天时占

- **rule_statement**：体克用、用克体晴；用生体雨；坎多雨；离多晴；震多雷；巽多风；坤多阴；艮多雾。
- **source_chapter**：dz-1/tianshi-zhan
- **applicable_to**：天气占断
- **caveats**：现代气象预报应优先于占断。
- **verification_status**：pending_verification

### MR-07-02 人事占

- **rule_statement**：用克体凶、体克用顺、用生体得益、体生用耗损、比和顺利；卦象再合参。
- **source_chapter**：dz-1/renshi-zhan
- **applicable_to**：泛泛事吉凶
- **caveats**：仅作参考。
- **verification_status**：pending_verification

### MR-07-03 家宅占

- **rule_statement**：体为家宅、用为外事；体克用宅吉、用克体宅有外祟；用生体得外援、体生用宅气泄；比和家宅安。
- **source_chapter**：dz-1/jiazhai-zhan
- **applicable_to**：家宅吉凶
- **caveats**：现代住宅安全应以工程检测为主。
- **verification_status**：pending_verification

### MR-07-04 屋舍占

- **rule_statement**：屋舍新旧、坐向、构件依卦象分别取；体克用屋无大碍。
- **source_chapter**：dz-1/wujie-zhan
- **applicable_to**：屋舍占断
- **caveats**：仅供参考。
- **verification_status**：pending_verification

### MR-08-01 婚姻占

- **rule_statement**：体为求婚者、用为对方；用生体或体克用婚成；用克体或体生用难成；比和顺成。
- **source_chapter**：dz-2/hunyin-zhan
- **applicable_to**：婚姻成败占
- **caveats**：婚姻属现代私事，占断不替代当事人意愿。
- **verification_status**：pending_verification

### MR-08-02 生产占

- **rule_statement**：体为母、用为子；阳卦为男、阴卦为女；体克用 / 用克体产难；体生用 / 用生体顺产；比和顺。
- **source_chapter**：dz-2/shengchan-zhan
- **applicable_to**：母子安否、男女
- **caveats**：现代产前必须以医学超声 / 产检为主，占断不作医学结论。
- **verification_status**：pending_verification

### MR-09-01 求财占

- **rule_statement**：体为我、用为财；用生体得财、体克用得财；体生用耗财、用克体破财；比和守成。
- **source_chapter**：dz-2/qiucai-zhan
- **applicable_to**：求财占断
- **caveats**：仅参考；不应作为投机指引。
- **verification_status**：pending_verification

### MR-09-02 交易占

- **rule_statement**：体用生克同求财；用克体交易凶；体克用交易顺。
- **source_chapter**：dz-2/jiaoyi-zhan
- **applicable_to**：交易成败
- **caveats**：仅参考。
- **verification_status**：pending_verification

### MR-10-01 出行占

- **rule_statement**：体为出行者、用为去处；体克用顺、用生体得益；用克体凶忌；体生用劳形耗资。
- **source_chapter**：dz-3/chuxing-zhan
- **applicable_to**：出行吉凶
- **caveats**：现代出行须以天气、交通为主。
- **verification_status**：pending_verification

### MR-10-02 行人占

- **rule_statement**：体为占者、用为行人；用生体行人速归；体生用未归；用克体行人遇险；体克用行人受制。
- **source_chapter**：dz-3/xingren-zhan
- **applicable_to**：行人归否占
- **caveats**：仅参考。
- **verification_status**：pending_verification

### MR-10-03 谒见占

- **rule_statement**：体为求见者、用为所见；用生体可见、有益；体克用可见而不悦；用克体不见或有阻。
- **source_chapter**：dz-3/yejian-zhan
- **applicable_to**：谒见有无
- **caveats**：—
- **verification_status**：pending_verification

### MR-10-04 失物占

- **rule_statement**：体为失主、用为物 / 拿者；用方位即物之方；体克用易得、用克体难得；卦象类比物形与去向。
- **source_chapter**：dz-3/shisuwu-zhan
- **applicable_to**：失物寻找
- **caveats**：仅供方向参考；现代寻物应报警。
- **verification_status**：pending_verification

### MR-11-01 疾病占

- **rule_statement**：体为病人、用为病；用克体病重；体克用病可制；用生体反耗体；体生用病退；比和病稳。卦象类病象（坎肾、离心、震肝、艮脾）。
- **source_chapter**：dz-4/jibing-zhan
- **applicable_to**：疾病轻重占
- **caveats**：**严禁替代现代医学诊断**；占断仅做心理参考；危及性命须立即就医。
- **verification_status**：pending_verification

### MR-12-01 官讼占

- **rule_statement**：体为告者、用为对方；体克用胜、用克体败；用生体有人助、体生用己耗。
- **source_chapter**：dz-4/guansong-zhan
- **applicable_to**：官讼胜负
- **caveats**：现代诉讼以法律证据为准；占断不替代律师意见。
- **verification_status**：pending_verification

### MR-12-02 坟墓占

- **rule_statement**：体为后人、用为坟；体生用耗、用生体福；用克体凶；体克用安。
- **source_chapter**：dz-4/fenmu-zhan
- **applicable_to**：坟茔吉凶
- **caveats**：现代殡葬以法规为主。
- **verification_status**：pending_verification

## 七、总诀

### MR-13-01 占断总诀

- **rule_statement**：占断本于体用生克 + 卦气衰旺 + 互变补充 + 类象取义；不拘一格，须临占灵动。
- **source_chapter**：dz-4/zhanduan-zonggui
- **applicable_to**：占断总则
- **caveats**：本书重心法多于死法。
- **verification_status**：pending_verification
