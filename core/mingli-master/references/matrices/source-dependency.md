# 典籍出处与依赖关系矩阵 (source-dependency)

> 本矩阵把总计划 §2.1.2 的文字描述转写为可执行的依赖图，供主 skill 决定 reference pack 的加载顺序与组合方式。
> `depends_on` 表示文本/术语/方法论的上游典籍；`informs` 表示该典籍会支持哪些下游典籍或判断模块。
> 源流依赖不等于实务优先级：早期禄命是八字源流，但现代八字解读以子平主线为核心。
> 机器置信度只读取 `references/inference/source-lineages-v1.json`；本图不能因为列出多本同源书就自动增加票数。

## 1. 总览：体系层级

| 架构层 | 体系 | 说明 |
|---|---|---|
| 命盘主线 | 八字子平 / 早期禄命纳音 / 紫微斗数 / 七政四余 | 长期人生结构、十年大运、年度主题 |
| 短事决策 | 六爻 / 梅花 / 大六壬 / 奇门遁甲 / 太乙 | 单事件成败、应期、临场策略 |
| 环境择时旁证 | 择日 / 风水（形峦+理气）/ 相法 | 行动时机、环境调整、外相旁证 |

## 2. 体系内部依赖

### 2.1 八字子平

```text
li-xuzhong-mingshu (李虚中命书)  ─┐
luoluzi-sanming    (珞琭子三命)  ─┼─► yuanhai-ziping (渊海子平)
wuxing-jingji      (五行精纪)    ─┘            │
                                                ▼
                                      sanming-tonghui (三命通会)
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          ▼                     ▼                     ▼
                  ziping-zhenquan       ditiansui-chanwei      qiongtong-baojian
                   (子平真诠)            (滴天髓阐微)           (穷通宝鉴)
                          │
                          ▼
                  shenfeng-tongkao / mingli-yueyan
```

**关键说明**：
- 《三命通会》是总汇编型源头（万历，万民英编），偏综合分类；可作子平体系入口索引。
- 《渊海子平》是子平法骨架与术语枢纽；后世四派精修版都需先回到本书看雏形。
- 《子平真诠》偏格局月令成败救应；沈孝瞻原典与徐乐吾评注在 pack 内必须分层。
- 《滴天髓阐微》偏气势生克；《穷通宝鉴》偏调候。三者主张不同，主 skill 必须按问题类型加权。
- 《神峰通考》《命理约言》作为后出整理、辨证或实务对照层，不应覆盖子平主线入口。
- 早期禄命诸书作源流层，**不能直接替代现代子平用神/格局结论**。

#### 当前 ready 八字内部依赖明细

| pack | path | status | full_book_coverage | depends_on | informs | Batch |
|---|---|---|---|---|---|---|
| sanming-tonghui | references/books/bazi/sanming-tonghui/index.md | ready | see validation.md | yuanhai-ziping, wuxing-jingji, li-xuzhong-mingshu, luoluzi-sanming | ziping-zhenquan, ditiansui-chanwei, qiongtong-baojian, shenfeng-tongkao, mingli-yueyan | D2 ready |
| yuanhai-ziping | references/books/bazi/yuanhai-ziping/index.md | ready | see validation.md | li-xuzhong-mingshu, luoluzi-sanming | sanming-tonghui, ziping-zhenquan, shenfeng-tongkao | D2 ready |
| ziping-zhenquan | references/books/bazi/ziping-zhenquan/index.md | ready | see validation.md | yuanhai-ziping, sanming-tonghui | ditiansui-chanwei, qiongtong-baojian, shenfeng-tongkao | D2 ready |
| ditiansui-chanwei | references/books/bazi/ditiansui-chanwei/index.md | ready | see validation.md | sanming-tonghui, ziping-zhenquan | qiongtong-baojian, mingli-yueyan | D2 ready |
| qiongtong-baojian | references/books/bazi/qiongtong-baojian/index.md | ready | see validation.md | ziping-zhenquan, ditiansui-chanwei | bazi.调候判断 | D2 ready |
| shenfeng-tongkao | references/books/bazi/shenfeng-tongkao/index.md | ready | see validation.md | yuanhai-ziping, sanming-tonghui | bazi.实务对照 | D2 ready |
| mingli-yueyan | references/books/bazi/mingli-yueyan/index.md | ready | see validation.md | sanming-tonghui, ditiansui-chanwei | bazi.后出辨证/清代实务 | D2 ready |

**当前状态**：八字系统 7 个 pack 均在 `references/catalog/catalog.json` 中列为 `d2_status: ready`。加载顺序仍以《三命通会》《渊海子平》为入口；专题判断再追加格局、气势、调候或后出对照包。

### 2.2 紫微斗数

```text
ziwei-doushu-quanshu (紫微斗数全书)  ─►  taiwei-fu (太微赋)
        └────────────────────────────►  feixing-ziwei-doushu-yuanzhi (斗数观测录/飞星紫微观测层)
```

**关键说明**：当前 ready pack 有 `ziwei-doushu-quanshu`、`taiwei-fu` 与 `feixing-ziwei-doushu-yuanzhi`。其中 `feixing-ziwei-doushu-yuanzhi` 是 NLC/Commons 116 页影印本 OCR 校阅完成的民国《斗数观测录》/飞星紫微观测层，只能在完整紫微事实层之后用于十二宫活用假借、阴阳宅/相法/邻里方位旁证、红鸾大耗/天刑巨门案例，不得替代《紫微斗数全书》《太微赋》。现代钦天 / 中州 / 河洛流派仍只能作 `modern_notes`，不能写入原典规则区；排盘必须来自工具适配层。

### 2.3 七政四余 / 星命

`guotian-jing`、`xingming-suyuan` 与 `xingxue-dacheng` 互为旁证。《星学大成》为大全式汇编，适合补图例、行度、变曜、观星节要与诸家限例；7 政 4 余必须依赖现代天文工具，不能让 LLM 自行换算坐标。

### 2.4 六爻 / 梅花

```text
zhouyi-zhezhong (御纂周易折中) / huangji-jingshi (皇极经世书)
       │
       ├─► huozhu-lin (火珠林，纳甲源流)
       │        └─► zengshan-buyi (增删卜易)  ─► bushi-zhengzong (卜筮正宗)
       │
meihua-yishu (梅花易数) — 独立分支
```

**关键说明**：当前 ready pack 以《增删卜易》《卜筮正宗》为六爻实务入口，《火珠林》补纳甲源流与飞伏早期法，《梅花易数》为独立分支，《御纂周易折中》《皇极经世书》作易学与象数背景。《断易天机》仍需另行 source-acquisition，不可假装已入库。

### 2.5 三式

| 体系 | 入口典籍 | 关键依赖 |
|---|---|---|
| 大六壬 | `daliuren-daquan` + `liuren-zhiyin` + `liuren-miben` | 起课工具（必需）+ 神将体系 |
| 奇门 | `qimen-dunjia-tongzhi` | 飞盘/转盘/时家口径必须由工具或用户盘面声明 |
| 太乙 | `taiyi-shenshu` | 默认不参与个人短问；触发条件：用户明确要求太乙或宏观时势 |

### 2.6 择日

```text
xingli-kaoyuan (御定星历考原)  ─►  xieji-bianfang-shu (钦定协纪辨方书)
                                              │
                                              ├─► yuqia-ji (玉匣记)（注：通书系，谨慎）
                                              └─► donggong-zeri (董公择日)（通书系，谨慎）
```

**关键说明**：
- 《御定星历考原》是官方校正框架；《钦定协纪辨方书》是官方综合大成。两者优先。
- 《玉匣记》《董公择日》归通书系，宜忌繁杂、相互冲突；主 skill 不应做机械堆叠。
- 董公系当前以《董公选择日要览》文本入库，已通过 D2；但仍属通书系，须声明版本差异，不作官方框架主轴。

### 2.7 风水

```text
[形峦阴宅线]
zangshu (葬书)  ─►  hanlong-jing (撼龙经) / yilong-jing (疑龙经)
                         └─► zangfa-daozhang (葬法倒杖，穴法/倒杖/二十四砂葬法)
                                  └─► rudi-yan-quanshu (入地眼全书，龙砂水向全流程)

[阳宅线]
huangdi-zhaijing (黄帝宅经，二十四路早期宅法)
       └─► yangzhai-shishu (阳宅十书，外形/福元/大游年/穿宫/放水/选择)
              └─► yangzhai-sanyao (阳宅三要)  ─►  shenshi-xuankong-xue (沈氏玄空学，玄空注释层)

[理气线]
qingnang-jing / qingnang-xu / qingnang-aoyu (青囊经/序/奥语)
                                         ├─►  tianyu-jing (天玉经)         ─┐
                                         └─►  dutian-baozhao-jing (都天宝照经) ─┴─► dili-bianzheng (地理辨正，注释层)

[形理旁证]
xuexin-fu (雪心赋)
```

**关键说明**：
- 阳宅与阴宅不可混用；`zangfa-daozhang` 只作阴宅穴法/倒杖/二十四砂葬法证据层，不能外推为阳宅、择日或玄空理气；`huangdi-zhaijing` 只作早期宅经/二十四路入口，`yangzhai-shishu` 作阳宅外形、福元、大游年、穿宫、放水、开门修造与选择的原典入口，`rudi-yan-quanshu` 按龙砂水向分层读取；理气流派（三元/三合/玄空/八宅）必须单独标明坐向、元运、流派。
- 《地理辨正》是注释/汇校性质，归 `commentary` 层。

### 2.8 相法

`shenxiang-quanbian`（神相全编，集大成）↔ `mayi-shenxiang`（麻衣，源流）↔ `liuzhuang-xiangfa`（柳庄，实务）↔ `renxiang-shuijing`（水镜，整理）。
四者互为旁证，无强依赖；只允许做旁证层，不参与命盘硬判断。

## 3. 跨体系：典籍 → 下游主 skill 模块

| 上游典籍 | 主 skill 下游模块 | 用途 |
|---|---|---|
| 三命通会 / 渊海子平 | bazi.格局 / bazi.大运流年 | 八字综合检索与分类入口 |
| 子平真诠 | bazi.格局.成败救应 | 月令格局、相神 |
| 滴天髓阐微 | bazi.旺衰.通关病药 | 气势生克 |
| 穷通宝鉴 | bazi.调候 | 月令调候 |
| 紫微斗数全书 | ziwei.宫位 / ziwei.限运 | 紫微基础宫职 |
| 飞星紫微斗数原旨 / 斗数观测录 | ziwei.观测旁证 / ziwei.十二宫假借 | 民国紫微观测法、方位/阴阳宅/相法互证、事件案例旁证 |
| 火珠林 / 增删卜易 / 卜筮正宗 | divination.六爻.断卦 | 短事问卦；火珠林作源流层 |
| 梅花易数 | divination.梅花.体用 | 临场短问、外应 |
| 六壬大全 | san-shi.六壬 | 课式断人事（需起课工具）|
| 奇门遁甲统宗 / 奇门法窍 | san-shi.奇门 | 择时方位（需排盘工具）|
| 协纪辨方 / 御定星历考原 / 董公选择 / 玉匣记 | selection.择日 | 行动时机（需历算工具）|
| 葬书 / 撼龙经 / 疑龙经 / 葬法倒杖 / 入地眼全书 | fengshui.形峦 | 阴宅 / 形势 / 穴法 / 倒杖 / 龙砂水向 |
| 黄帝宅经 / 阳宅十书 / 阳宅三要 | fengshui.阳宅 | 住宅布局、福元游年、门路灶水、开门修造 |
| 青囊经 / 青囊序 / 青囊奥语 / 天玉经 / 都天宝照 | fengshui.理气 | 理气坐向、水法、城门、玄空术语（需明确流派与坐向输入）|
| 神相全编 / 柳庄 | physiognomy | 旁证（不硬断）|

## 4. 加载策略

1. 主 skill 命中某体系时，先尝试加载该体系的 **入口 pack**（见上图根节点）。
2. 若问题需要特定模块（格局/调候/旺衰/理气流派等），按 `informs` 链向下追加加载下游 pack。
3. 若上游 pack `status != ready`，则降级加载已 ready 的同体系替代 pack，并在输出中标注降级原因。
4. 跨体系加载（例如八字 + 卜筮）由 `routing-matrix.md` 决定，本矩阵只决定单体系内部顺序。

## 5. TODO

- 八宅的坐向、实测门卦起游年、观察、户型和来源绑定已由 `fengshui-source-tables-v1.yaml` 与专用 provider 实现；坐卦不会被当作门卦代入。三元、三合、玄空仍须各自取得完整来源表和独立 fixtures 后才能启用，不能由元运字段自动激活。
- 后续取得《断易天机》完整可核验文本后，再补六爻工具书/索引层 ready pack。
- 为 Bazi/Ziwei/Qimen/Selection 增加实际 adapter command 示例，并在 license review 后决定是否 vendor。
- 累积真实 case log 后，将 `references/accuracy-and-statistical-validation.md` 的校准指标写入版本化报告。
