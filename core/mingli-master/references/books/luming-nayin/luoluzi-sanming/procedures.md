# 珞琭子三命消息赋 — 流程

约定：禁止 LLM 手算排盘；所有需要排盘起运的步骤须依赖 `tool.bazi.paipan`。
所有 verified=false。

---

## P-01：识别"以干为禄、向背定贫富"判读流程

- purpose: 用珞琭子赋"以干为禄"取用法判断命局向背贫富
- steps:
  1. 调用 `tool.bazi.paipan` 排出年/月/日/时四柱及天元（十干）/支元（十二支）
  2. 以日干为天元主体，扫描其他三柱支位之人元（藏干）
  3. 标记日干向其禄马（建禄/帝旺）/财帛/官印/寿限/旺相位的支位为"向"
  4. 标记日干见七煞、克泄、休囚、败地的支位为"背"
  5. 综合"向"位与"背"位的多寡与轻重，判读贫富向背趋向
- tool_dependency: tool.bazi.paipan
- source_chapter: gan-zhi/yi-gan-wei-lu / caiming-youqi/beilu-bupin
- caveats: 仅作命书向背取用法研究输出；具体贫富不作铁口断语
- verified: false

---

## P-02：识别"背禄"格局流程

- purpose: 识别六甲~六癸日干的背禄格局并辨析有救无救
- steps:
  1. 调用 `tool.bazi.paipan` 取得日干及四柱
  2. 按"十干背禄表"：甲乙见丙丁、丙丁见戊己、戊己见庚辛、庚辛见壬癸、壬癸见甲乙者，标记为背禄候选
  3. 检视背禄之干所居支位是否为生旺（巳午、寅卯之类）；旺则背禄确立，衰则减半
  4. 扫描三合（巳酉丑、申子辰、亥卯未、寅午戌）是否能"飞祿走馬"救其官印
  5. 评估"财命有气"（克我之神得地为财则不贫）vs "财绝命衰"（财鬼俱衰则建禄不富）
- tool_dependency: tool.bazi.paipan
- source_chapter: caiming-youqi/beilu-bupin / wuhe-youhe/yi-fenwei-san
- caveats: 命书取用法研究；不作贫富铁口断语
- verified: false

---

## P-03：识别"祿馬同鄉"上贵格局流程

- purpose: 识别"不三台而八座"的上贵祿馬同鄉格
- steps:
  1. 调用 `tool.bazi.paipan` 排出四柱
  2. 检视日柱是否为壬午、丙午、庚子等"祿馬同乡"日（日干本祿与马星共聚一支）
  3. 验证生时不居休败、岁月支无衝刑克破本祿
  4. 验证三奇（如丙、辛、癸或甲、戊、庚）是否齐备且无内外争夺
  5. 验证太岁与日时不形成"二壬刑卯"等"合而不合"
  6. 综合输出"祿馬同乡贵命"的强度判定
- tool_dependency: tool.bazi.paipan
- source_chapter: beilu-zhuma/lumatongxiang
- caveats: 仅作贵格识别文化研究；不作仕宦/官位预测
- verified: false

---

## P-04：识别"夾祿"真假流程

- purpose: 区分真夹祿与"夹禄不实"虚名命
- steps:
  1. 调用 `tool.bazi.paipan` 排出四柱
  2. 检视是否符合戊辰戊午（夹巳）、丁巳丁未（夹午）、己未己巳（夹午）、壬戌壬子（夹亥）、癸丑癸亥（夹子）等夾祿候选
  3. 检视所夹之支（巳/午/亥/子）在四柱中是否被岁/月/时实占
  4. 若被实占则为"夹禄不稳"虚名命；若空位则为真夹禄
  5. 验证日干两侧之干无被剋（如甲日逢庚剋则坏夹）
  6. 综合输出夹禄等级
- tool_dependency: tool.bazi.paipan
- source_chapter: guan-chong/jia-lu-jie-cai
- caveats: 命书格局识别研究；不作具体仕途预测
- verified: false

---

## P-05：大运吉凶判读流程（节气浅深+伏吟反吟+元辰之歲）

- purpose: 综合节气深浅、运向背、伏吟反吟、元辰煞断大运吉凶
- steps:
  1. 调用 `tool.bazi.paipan` 起大运、小运、流年序列（一辰十岁、三日为年）
  2. 测量出生节气浅深（起运岁数）；标记"男迎女送"前后五年发福之分
  3. 检视当前大运支位与本命日支：相对者为伏吟、相衝者为反吟
  4. 检视当前大运/流年是否触发四煞（辰戌丑未叠临）、五鬼（克财官印）、六害、七煞
  5. 检视太岁是否为"出入之年"（顺运换运之年）或"元辰之歲"（命中元有害神之太岁）
  6. 综合输出当前大运/流年阶段的吉凶倾向（迎福/退灾/凶会/吉会/伏吟反吟）
- tool_dependency: tool.bazi.paipan
- source_chapter: yun-cheng/yi-chen-shi-sui / yin-yang-nan-nv/churu-yuanchen / sheng-di/tuishen-bi-wei / huoxun-shuaixiang/nan-ying-nv-song
- caveats: ⚠️ 涉及大运吉凶判读；仅作命书运程理论文化研究参考，不得铁口断祸福；不替代医学/法律/财务咨询；现代严格 reframe，不作绝对断语
- verified: false
