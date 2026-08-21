# 紫微斗数全书 — 流程库（procedures）

> 全书覆盖型流程梳理。**所有需要排盘的步骤一律依赖 `tool.ziwei.bindisk`，禁止 LLM 手算紫微斗数盘**。本流程库供文化研究与教学辅助参考，不替代任何专业咨询。

---

## P-ZW-01 紫微斗数排盘起例

- **purpose**: 给定阳历/阴历生辰，排出完整的紫微斗数盘（命身宫 + 12 宫主星 + 辅煞 + 四化）。
- **steps**:
  1. 依赖 `tool.ziwei.bindisk` 起命宫与身宫，不得手算。
  2. 依赖 `tool.ziwei.bindisk` 定五行局（水二局 / 木三局 / 金四局 / 土五局 / 火六局）。
  3. 依赖 `tool.ziwei.bindisk` 安紫微等 14 主星。
  4. 依赖 `tool.ziwei.bindisk` 安文昌文曲左辅右弼天魁天钺禄存天马 8 辅星。
  5. 依赖 `tool.ziwei.bindisk` 安擎羊陀罗火星铃星 4 煞。
  6. 依赖 `tool.ziwei.bindisk` 安天空地劫天伤天使天刑天姚天哭天虚等辅煞。
  7. 依赖 `tool.ziwei.bindisk` 安四化（化禄/化权/化科/化忌，按生年天干飞）。
  8. 依赖 `tool.ziwei.bindisk` 起大限（按五行局起运岁，男阳/女阳顺、男阴/女阴逆）。
  9. 依赖 `tool.ziwei.bindisk` 起小限与流年。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: 卷二·安身命例
- **caveats**: **禁止 LLM 手算紫微斗数盘**；不得使用八字 `tool.bazi.paipan`（系统不同）；命主出生时辰必须确证（参 juan-03/lun-rensheng-shi-yao-shen-dique）。
- **verified**: false

## P-ZW-02 命宫主星与三方四正判读

- **purpose**: 排出命宫后，按"命宫主星 + 三方四正会照"判读命主气象。
- **steps**:
  1. 完成 P-ZW-01 排盘。
  2. 命宫主星：本宫主星 + 庙旺利平闲陷亮度（参 juan-01/shiergong-zhuxing-dedi-hege-jue）。
  3. 三方四正：本宫 + 对宫（迁移）+ 左三合（财帛）+ 右三合（官禄）四宫会照星煞。
  4. 四化加临：生年四化与大限/小限/流年四化飞入命三方者。
  5. 综合判读：参照诸星问答论（ZW-01-01~14）+ 富/贵/贫贱/杂格局（ZW-05-01~05）。
  6. 输出：命宫气象 + 主要格局命中 + 文化象义参考。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: 卷一·诸星问答论 + 卷一·定富贵贫贱十等论 + 卷二·一命宫
- **caveats**: 仅作命书文化研究参考；不作铁口断富贵；不作具体职业/学业/婚姻预测；不替代现代专业咨询。
- **verified**: false

## P-ZW-03 十二宫综合判读

- **purpose**: 系统判读十二宫各宫主题（兄弟/夫妻/子女/财帛/疾厄/迁移/交友/事业/田宅/福德/父母）。
- **steps**:
  1. 完成 P-ZW-01 排盘。
  2. 各宫按以下顺序判读：本宫主星 → 庙旺亮度 → 对宫会照 → 三合会照 → 四化加临 → 煞星会照。
  3. 参照卷二·一命宫至十二父母（juan-02/01-mingong ~ 12-fumu）各宫断法。
  4. **强 reframe 宫位**：
     - 妻妾宫（juan-02/03-qiqie）→ 现代义改为"夫妻宫"；不作铁口断离合。
     - 疾厄宫（juan-02/06-jie）→ **严禁**作医疗诊断。
     - 奴仆宫（juan-02/08-nupu）→ 现代义改为"交友宫"。
     - 官禄宫（juan-02/09-guanlu）→ 现代义改为"事业宫"。
  5. 输出：十二宫各宫文化象义 + 强 reframe 标注。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: 卷二·12 宫详断
- **caveats**: ⚠️ 妻妾宫/疾厄宫/奴仆宫/官禄宫古代用语须 reframe；不作铁口断婚姻/健康/朋友/职业；仅作文化研究参考。
- **verified**: false

## P-ZW-04 大限/小限/流年运程推断

- **purpose**: 推断命主当前大限、小限、流年三层运程。
- **steps**:
  1. 完成 P-ZW-01 排盘。
  2. 依赖 `tool.ziwei.bindisk` 计算命主当前所在大限（10 年）、小限（1 年）、流年（1 年太岁）。
  3. 大限断：参照卷三·论大限十年祸福（juan-03/lun-daxian-shinian-huofu）+ 论行限分南北斗（juan-03/lun-xingxian-fen-nanbei-dou）。
  4. 二限断：参照卷三·论二限太岁吉凶（juan-03/lun-erxian-taisui-jixiong）。
  5. 流年断：参照卷三·论流年太岁吉凶星杀（juan-03/lun-liunian-taisui-jixiong-xingsha）。
  6. 凶限合参：羊陀迭并（ZW-06-05）+ 七杀重逢（ZW-06-05）+ 化忌叠并。
  7. 输出：大限/小限/流年三层运程文化象义参考。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: 卷三·论大限十年祸福 + 论二限太岁 + 论流年太岁吉凶星煞
- **caveats**: 运程古书断语含吉凶铁口断，**仅作命书文化研究参考**；不作具体年份的祸福铁口断；不得用于股市/投资/医疗/法律决策。
- **verified**: false

## P-ZW-05 富贵贫贱格局扫描

- **purpose**: 系统扫描命盘中的富格、贵格、贫贱格、杂格命中情况。
- **steps**:
  1. 完成 P-ZW-01 排盘。
  2. 富局扫描：日月并明 / 月朗天门 / 武贪格 / 火贪格 / 铃贪格 / 双禄交流（参 juan-01/dingfuju）。
  3. 贵局扫描：紫府同宫 / 紫府朝垣 / 君臣庆会 / 府相朝垣 / 日月夹命 / 机月同梁 / 杀破狼 / 阳梁昌禄 / 巨日同宫 / 石中隐玉 / 三奇加会 / 紫微在午无杀凑 / 马头带剑（参 juan-01/dingguiju）。
  4. 贫贱局扫描：日月反背 / 命无正曜 / 命坐空亡 / 羊陀夹忌 / 火铃夹命（参 juan-01/dingpinjianju）→ **强 reframe**。
  5. 杂局扫描：桃花犯主 / 贪武同行 / 廉贞会贪狼（参 juan-01/dingzaju）。
  6. 输出：命中格局清单 + 文化象义 + 现代 reframe 提示（贫贱格特别 reframe）。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: 卷一·定富贵贫贱十等论 + 定富局/定贵局/定贫贱局/定杂局
- **caveats**: ⚠️ 贫贱格断语含宿命色彩，**严禁**用于现代社会经济地位判读；富贵格不作铁口断；仅作文化研究参考。
- **verified**: false

## P-ZW-06 女命与男女命同异判读（强 reframe）

- **purpose**: 古书男女命差异条目展示，**严格强 reframe**。
- **steps**:
  1. 完成 P-ZW-01 排盘。
  2. 男命：参照卷一·斗数骨髓赋 + 卷三·论男女命同异（juan-03/lun-nannv-ming-tongyi）。
  3. 女命：参照卷一·女命骨髓赋（juan-01/nvming-gusui-fu）→ **特殊强 reframe**。
  4. **强制 reframe 输出**：在所有女命断语前加 caveats 模板："⚠️ 女命骨髓赋为古代父权时代产物，含明显时代偏见（如刑夫克子煞、伤夫煞），仅作命书历史研究参考，**严禁**用于现代女性命运判读；现代社会男女平权，须批判性阅读。"
  5. 输出：男女命古书条目 + 强 reframe 标注。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: 卷一·女命骨髓赋 + 卷三·论男女命同异
- **caveats**: ⚠️ **特别强 reframe**：女命骨髓赋含父权时代偏见，**严禁**用于现代女性命运判读；不替代婚姻/职业咨询；现代须批判性阅读。
- **verified**: false

## P-ZW-07 小儿命与疾厄判读（强 reframe）

- **purpose**: 古书小儿命与疾厄宫条目展示，**严格强 reframe**。
- **steps**:
  1. 完成 P-ZW-01 排盘。
  2. 小儿命：参照卷三·论小儿命（juan-03/lun-xiaoer-ming）+ 定小儿生时诀（juan-03/dingxiaoer-shengshi-jue）+ 论小儿克亲（juan-03/lun-xiaoer-keqin）。
  3. 疾厄宫：参照卷二·六疾厄（juan-02/06-jie）。
  4. **强制 reframe 输出**：所有小儿/疾厄断语前加 caveats 模板："⚠️ 古代命学小儿关煞/疾病说与现代医学无对应关系，**仅作文化研究参考**，**严禁**作健康/医疗决策依据；如有健康疑虑请就医。"
  5. 输出：古书条目 + 强 reframe 标注。
- **tool_dependency**: `tool.ziwei.bindisk`
- **source_chapter**: 卷二·六疾厄 + 卷三·论小儿命 + 论小儿克亲
- **caveats**: ⚠️ **严禁**作铁口断病/断小儿命运；**严禁**替代医学诊断；仅作命书历史/文化研究层；现代须严格 reframe，宜批判性阅读。
- **verified**: false

## P-ZW-08 时辰确证（命学合规起点）

- **purpose**: 紫微斗数对生时极敏感，必须先确证生时。
- **steps**:
  1. 询问命主出生时辰（精确到时辰）。
  2. 若不确定，参照卷三·定小儿生时诀（juan-03/dingxiaoer-shengshi-jue）+ 论人生时要审的确（juan-03/lun-rensheng-shi-yao-shen-dique）的传统口诀（如发旋、坐立、面相对照）作为参考。
  3. 时辰交界（如 23 点为子时还是次日子时）须特别确证。
  4. 输出：确证生时 + 进入 P-ZW-01 排盘。
- **tool_dependency**: `tool.ziwei.bindisk`（部分功能验证）
- **source_chapter**: 卷三·定小儿生时诀 + 论人生时要审的确
- **caveats**: 时辰不确则命局误，全盘失真；不作铁口断；仅作文化研究参考。
- **verified**: false
