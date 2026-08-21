# 太微赋 — Procedures

> 紫微斗数早期赋文流程抽取。每条流程字段：`purpose` / `steps` / `tool_dependency` / `source_chapter` / `verified`。
> 全部 `verified: false`。
> ⚠️ 严禁 LLM 手算排盘。紫微排盘统一依赖 `tool.ziwei.bindisk`。

---

## TP-01 应用太微赋判断格局的总流程

- **purpose**: 给定一张已排好的紫微盘，使用本赋判断是否成立赋中所列重要格局。
- **steps**:
  1. 调用 `tool.ziwei.bindisk` 完成排盘（得到 12 宫位、14 主星、6 吉星、6 煞星、四化、长生十二宫、空亡等）。
  2. 在排盘结果上识别命宫主星与三方四正星曜组合。
  3. 对照 [terms.md](./terms.md) 格局组（TT-P01 ~ TT-P18）逐一检测：
     - 君臣庆会（紫微+辅弼+吉星）
     - 辅弼夹帝（紫微 ±1 宫见左右）
     - 日丽中天（太阳坐午）
     - 水澄桂萼（太阴坐子）
     - 禄文拱命（禄存+文星拱命）
     - 日月夹财（太阳/太阴夹财帛）
     - 马头带剑（天马+擎羊同宫）
     - 刑囚夹印（擎羊+廉贞夹印星）
     - 蟾宫折桂（太阴+文曲在妻宫）
     - 皇殿朝班（太阳+文昌在官禄）
  4. 对照 [rules.md](./rules.md) 检测凶象格局（路上埋尸/水中作冢/犯水桃花/风流彩杖）。
  5. 凡涉及寿夭/疾病/死亡断语的格局（TR-16/17/18/19/20），必须 reframe 为倾向性参考，严禁铁口。
  6. 输出格局清单与 caveats 提示。
- **tool_dependency**: `tool.ziwei.bindisk`（必需）
- **source_chapter**: zonglun/zhi-xuan-zhi-wei + 全部 liyue/* 段
- **verified**: false

## TP-02 入庙失度判断流程

- **purpose**: 判断指定主星在所坐之垣是否入庙、平、闲、陷。
- **steps**:
  1. 调用 `tool.ziwei.bindisk` 取得主星所在宫位。
  2. 查《紫微斗数全书》卷二的庙旺利陷表（本赋未列具体配位，仅有"入庙为奇/失度为虚"总纲）。
  3. 标记主星状态为：庙 / 旺 / 平 / 闲 / 陷 / 失度。
  4. 反背状态特别标注（日不入南、月不照北）。
- **tool_dependency**: `tool.ziwei.bindisk` + 庙旺利陷查表（参考 ziwei-doushu-quanshu pack）
- **source_chapter**: zonglun/rumiao-shidu + liyue/riyue-fanbei
- **verified**: false

## TP-03 流年限运的童子/老人限提醒

- **purpose**: 判断当前所处大限/流年是否触发童子限或老人限的特殊告诫。
- **steps**:
  1. 调用 `tool.ziwei.bindisk` 取得大限十年及流年宫位。
  2. 若年龄 ≤ 15 标记为童子限（如水上泡沤）；若 ≥ 65 标记为老人限（如风中燃烛）。
  3. 检查童子/老人限宫位是否遇杀（七杀/破军/羊陀火铃/化忌）。
  4. 若遇杀无制，仅作风险提示，⚠️ 严禁断寿断祸，必须 reframe 为"需注意健康/安全"。
- **tool_dependency**: `tool.ziwei.bindisk`（流年模块）
- **source_chapter**: liyue/tongzi-laoren-xian
- **verified**: false

## TP-04 引用本赋短句的查询流程

- **purpose**: 给定一句疑似出自《太微赋》的短引，验证其归属。
- **steps**:
  1. 在 [quote-index.md](./quote-index.md) 表格中按关键词检索。
  2. 比对 chapter 字段定位赋文段落。
  3. 比对 source_url（CTP / Wikisource）原文。
  4. 若与《增补太微赋》文本相近，须区分本赋与增补版（增补版在《紫微斗数全书》卷一另列）。
- **tool_dependency**: 无（纯文本检索）
- **source_chapter**: 全文
- **verified**: false

---

## 流程统计

- **总计**：4 个流程（TP-01 ~ TP-04）。
- 全部依赖 `tool.ziwei.bindisk`（涉及排盘的 3 个流程）。
- 全部 `verified: false`。
