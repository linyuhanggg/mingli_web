# 皇极经世书 — Rules

> 本文件抽取《皇极经世书》数理 + 易理之可路由判断规则。
> 字段：`rule_id` / `rule_statement` / `source_chapter` / `applicable_to` / `caveats` / `verification_status`。
> 全部 `pending_verification`。
> rule_id 前缀 `HR` = Huangji Rule。

---

## 一、元会运世数理（核心）

### HR-01-01 元会运世总数

- **rule_statement**：一元 = 12 会 = 360 运 = 4320 世 = 129600 年；为天地一开辟之大周期。
- **source_chapter**：vol-01-up（觀物篇一）+ vol-13
- **applicable_to**：宇宙时间最大尺度
- **caveats**：本数为术数史观符号，不等于现代地质 / 天文学时间尺度。
- **verification_status**：pending_verification

### HR-01-02 子会开物

- **rule_statement**：邵雍以"子会"开物（万物始）、"丑会"立地、"寅会"生人；亥会闭物（万物归）。
- **source_chapter**：vol-01 ~ vol-02
- **applicable_to**：元会运世史观
- **caveats**：属术数史观，非自然演化论。
- **verification_status**：pending_verification

### HR-01-03 三才相经规则

- **rule_statement**：以元经会主天之运（卷一至二）、以会经运主地之化（卷三至四）、以运经世主人物之事（卷五至六）；以世经世落具体年甲子（卷七至十）。
- **source_chapter**：vol-01 ~ vol-10 框架
- **applicable_to**：经世数表的层级路由
- **caveats**：—
- **verification_status**：pending_verification

### HR-01-04 一会主管

- **rule_statement**：一元 12 会以 12 地支配；子开寅生午盛申退戌闭亥归；现今天地正处于"午会"中后期。
- **source_chapter**：vol-13
- **applicable_to**：当下纪元定位
- **caveats**：邵雍立场视点为北宋，"午会"判断含历史时代背景。
- **verification_status**：pending_verification

## 二、卦气配年规则

### HR-02-01 六十四卦配年

- **rule_statement**：以六十四卦配岁；卦气消息按月配中孚 / 复 / 临 / 泰……剥 / 坤；亦按经世配元会运世。
- **source_chapter**：vol-05 ~ vol-10
- **applicable_to**：年甲子卦气配置
- **caveats**：与汉孟喜卦气、京房八宫卦气取义不同；查具体年用 `tool.divination.huangji`。
- **verification_status**：pending_verification

### HR-02-02 经世卦序

- **rule_statement**：经世卦序以乾坤为始、咸恒为人事之序；与《周易》上下经卦序有结构相通。
- **source_chapter**：vol-05 ~ vol-10
- **applicable_to**：经世表卦序排列
- **caveats**：—
- **verification_status**：pending_verification

### HR-02-03 用神不在本书

- **rule_statement**：本书不涉个人卜筮取用神；元会运世为时间数理框架，非占断系统。
- **source_chapter**：全书
- **applicable_to**：路由判断
- **caveats**：用户问占断 → 转 `meihua-yishu` 或 `zengshan-buyi`。
- **verification_status**：pending_verification

## 三、先天易学规则

### HR-04-01 先天数

- **rule_statement**：八卦先天数：乾 1、兑 2、离 3、震 4、巽 5、坎 6、艮 7、坤 8。
- **source_chapter**：vol-13（觀物外篇上）
- **applicable_to**：所有先天起卦法（梅花易数主用此）
- **caveats**：起具体卦应由 `tool.divination.qiguagua`（梅花体系）处理；本书仅提供数理来源。
- **verification_status**：pending_verification

### HR-04-02 加一倍法

- **rule_statement**：每加一爻卦数倍增；太极生两仪→四象→八卦→十六→三十二→六十四。
- **source_chapter**：vol-13
- **applicable_to**：先天易理推演
- **caveats**：—
- **verification_status**：pending_verification

### HR-04-03 先天 vs 后天方位

- **rule_statement**：先天八卦方位（伏羲）— 乾南坤北、离东坎西；后天八卦方位（文王）— 离南坎北、震东兑西。
- **source_chapter**：vol-13
- **applicable_to**：先后天方位之辨
- **caveats**：梅花易数兼用先后天，本书仅辨先天。
- **verification_status**：pending_verification

### HR-04-04 反对相参

- **rule_statement**：六十四卦两两为偶（反对）；非反即对；卦序之理本于此。
- **source_chapter**：vol-13
- **applicable_to**：卦序与变卦解读
- **caveats**：—
- **verification_status**：pending_verification

## 四、观物义理规则

### HR-05-01 反观

- **rule_statement**：以物观物则得理通，以我观物则有情累；圣人之观物在反观。
- **source_chapter**：vol-13 ~ vol-14
- **applicable_to**：易学方法论
- **caveats**：属哲学义理，非具体占断规则。
- **verification_status**：pending_verification

### HR-05-02 心为太极

- **rule_statement**：天地之心可知，万化从心起；心为太极，万象皆心之发。
- **source_chapter**：vol-13
- **applicable_to**：邵雍心学立场
- **caveats**：—
- **verification_status**：pending_verification

### HR-05-03 体用相须

- **rule_statement**：乾坤为体、坎离为用；体不立则用不行，用不行则体不显。
- **source_chapter**：vol-13
- **applicable_to**：邵雍体用论
- **caveats**：与梅花易数"体用生克"占法不同；梅花是占断方法。
- **verification_status**：pending_verification

## 五、声音律吕规则

### HR-06-01 声音配数

- **rule_statement**：天声 10 类配地音 12 类、平上去入 4 调 × 开发收闭 4 等；声音之数皆受元会运世数管摄。
- **source_chapter**：vol-11
- **applicable_to**：邵雍音韵学
- **caveats**：与现代音韵学需对照；具体音类查 `tool.divination.huangji`。
- **verification_status**：pending_verification

### HR-06-02 唱和

- **rule_statement**：天声唱、地音和；唱和成则音律备。
- **source_chapter**：vol-11
- **applicable_to**：声音律吕图解读
- **caveats**：—
- **verification_status**：pending_verification

## 六、动植物数

### HR-07-01 动植飞走

- **rule_statement**：万物分动 / 植 / 飞 / 走；总数受元会运世数管摄；动植之数 12 万 8 千有奇。
- **source_chapter**：vol-12
- **applicable_to**：物数总论
- **caveats**：术数符号意义，非生物学分类。
- **verification_status**：pending_verification

## 七、推演操作约束

### HR-09-01 数表必须用工具

- **rule_statement**：元会运世年甲子表 / 卦气配年表 / 声音律吕表，凡查询事实层运算，必须 `tool.divination.huangji`，**严禁 LLM 手算**。
- **source_chapter**：—（架构性约束）
- **applicable_to**：所有数表查询
- **caveats**：手算极易出错；表项数百万级。
- **verification_status**：pending_verification

### HR-09-02 元始甲辰

- **rule_statement**：邵雍以唐尧元年甲辰（公元前 2357 年）为经世表元始首甲；后续年甲子均依此推。
- **source_chapter**：vol-05
- **applicable_to**：年表推算起点
- **caveats**：与《竹书纪年》《史记·三代世表》等他源元始有出入；以本书表为准。
- **verification_status**：pending_verification

### HR-09-03 不预测国运

- **rule_statement**：本书数理框架虽含史观，但邵雍未明言"国运"预测；后世以此预言朝代兴衰多属附会。
- **source_chapter**：全书立场
- **applicable_to**：现代使用边界
- **caveats**：避免据本书推断现代国运 / 政治；纯文化参考。
- **verification_status**：pending_verification

### HR-09-04 不可个人命术化

- **rule_statement**：本书是宇宙史观数理，非个人命术；不可用本书直接推个人吉凶。
- **source_chapter**：—
- **applicable_to**：使用边界
- **caveats**：个人命术应转 `bazi/*` 或 `divination/{meihua-yishu, zengshan-buyi}`。
- **verification_status**：pending_verification

---

## 现代使用边界（caveats 总）

- **元会运世数**仅为术数符号，不等同于现代天文学 / 地质学时间尺度。
- **当下午会判定**含邵雍北宋视角；现代套用应说明时代局限。
- **国运推算**为后世附会，本书无明文；不应据以做现代政治 / 经济决策。
- **个人命术**不在本书范围。
- **数表查询**严禁手算，必须用 `tool.divination.huangji`。

**全部 21 条 `verification_status: pending_verification`，待与四库本逐章复核后升级。**
