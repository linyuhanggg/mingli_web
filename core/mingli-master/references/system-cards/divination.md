# 六爻 / 梅花 / 易占 (divination)

## Packs

| pack | title | best for | do not use for | caveat |
|---|---|---|---|---|
| `divination/bushi-zhengzong` | 卜筮正宗 | 六爻纳甲断卦实务的用神、世应、原神忌神、飞伏神、旬空月破等基础规则; 黄金策总断/天时/年时/国朝/婚姻/疾病/求财/家宅等分类占断; 与《增删卜易》对读，处理六爻实务分歧 | 不经起卦/装卦工具手算六爻; 对现实疾病、寿命、诉讼、失踪作确定结论; 将神煞旧断语直接输出给用户 | 4 个 CTP 页全部抽取；chapter-map 行级覆盖 3472 单元，quote-index 跨页短引 303 条。 |
| `divination/huangji-jingshi` | 皇极经世书 | 元会运世数理框架（一元 12 会、一会 30 运、一运 12 世、一世 30 年；总 129600 年）; 先天易学（伏羲六十四卦方圆图）原始文献; 邵雍象数易学源头（观物内 / 外篇之义理） | LLM 手算元会运世年表（必须 `tool.divination.huangji`）; 个人命局推算（本书是宇宙史观，非个人命术）; 严格历史预测 / 现代决策（属术数史观，非现代实证） | - 文渊阁本与黄畿《皇极经世书传》、张行成《皇极经世索隐》之文本细节差异未在本 pack 复核。 - 觀物篇 1-50 为大量数表（年甲子表），本 pack 不展开数表细目，仅给框架性概览。 - 觀物外篇上下系门人辑录，与内篇文体不同，故 chapter-map 标注分离。 - 全部章节 `verified: false`。 |
| `divination/huangjin-ce` | 黄金策 | 火珠林法/纳甲六爻总断纲领、分门占断、求财/婚姻/家宅/词讼/出行等章节路由；神煞降权为生克制化旁证 | 不经六爻 adapter 手算本卦、变卦、动爻、纳甲、世应、六亲、旬空、六神；不把病症、兵灾、逃亡、讼狱等旧断当现代事实 | Wikisource 完整文本，页头题刘基并说明按《卜筮正宗》本全文载录；正文夹注释层，须与原典断语分开。 |
| `divination/huozhu-lin` | 火珠林 | 纳甲六爻源流、飞伏神早期法、财官公私用事、世应与出现伏藏规则 | 不经六爻/装卦工具手算纳甲、世应、六亲、旬空; 不替代《增删卜易》《卜筮正宗》的后世实务主裁 | 维基文库完整单页整理本；作者归属与版本系统待考，作为源流层使用。 |
| `divination/meihua-yishu` | 梅花易数 | 先天数起卦（年月日时、字数、声音、物数、字数等）; 后天起卦（端法：以物为上卦、方位为下卦）; 体用生克吉凶判断 | LLM 手算起卦（必须调用 tool.divination.qiguagua）; 六爻纳甲世应用神（应转 zengshan-buyi / bushi-zhengzong）; 易学义理解经（应转 zhouyi-zhezhong） | - 作者归属待考：传邵雍，实为后人托名编纂。 - 通行本与古本差异较大，民间增删较多；本 pack 章节命名依维基文库整理本。 - 占例（观梅、牡丹、牛鸣等）原文叙述较长，本 pack 仅做摘要 + 短引，不复制大段原文。 - status：本 batch 完成框架，章节级 digest_status 全部 partial；待与古本对校升级 done。 |
| `divination/zengshan-buyi` | 增删卜易 | 六爻金钱卦装卦（纳甲、世应、六亲、动变）; 用神取法（按问占类型取用神）; 元神 / 忌神 / 仇神判断 | LLM 手算装卦 / 排纳甲 / 安世应（必须调用 tool.divination.liuyao_bindisk）; 象数体用占法（应转 meihua-yishu）; 易学义理 / 经传解读（应转 zhouyi-zhezhong） | - 作者归属待考（野鹤老人 / 李我平 / 李文辉）。 - 卷篇划分各本不同（12 卷或 14 篇之说），本 pack 采用维基文库整理本之 4 卷 130+ 章版本。 - 含大量占例（每章往往附 5-20 个），本 pack 仅做摘要 + 短引，不复制占例原文。 - status：本 batch 完成框架，章节级 digest_status 全部 p... |
| `divination/zhouyi-zhezhong` | 御纂周易折中 | 周易经传义理 + 象数注疏汇编（程朱二派为主，旁采诸家）; 64 卦卦爻辞解读（程传 + 本义 + 集说 + 案语 4 层结构）; 易学义例（位 / 徳 / 應 / 比 / 中 / 才 / 卦主 等概念框架） | 卜筮装卦操作（应转 `zengshan-buyi` 或 `meihua-yishu`）; LLM 手算占筮蓍法（蓍法虽收入啟蒙，但实操应由 `tool.divination.qiguagua` 处理）; 个人命术 / 八字推算（应转 `bazi/*`） | - 本书 22 卷涉及 64 卦 + 系传 + 启蒙，文本量极大（约 1.4 MB）；   本 pack 采用粗粒度策略：按卷次列条目，64 卦不逐卦展开。 - 程傳 / 本義 / 集說 / 案語 四层文献结构，本 pack 仅给框架性概览，不复制注疏原文。 - 與《周易本義》《伊川易傳》單行本之文本差異未在本 pack 復核。 - 全部章节 `ver... |

## Runtime use

This card is capability and source metadata for selecting the transaction
system before `prepare`. During a live reading, use only the bounded evidence
returned by the transaction; do not load packs or run a separate corpus search.
