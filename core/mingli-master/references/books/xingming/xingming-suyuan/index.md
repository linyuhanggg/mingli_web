---
slug: xingming-suyuan
title: 星命溯源
system: xingming
school:
  - 七政四余
  - 五星推命
  - 化气派
  - 正气派
source_layer: primary
verified: false
distillation_status: ready_candidate
---

# 星命溯源 · 蒸馏首页

## 一、典籍定位

《星命溯源》四库提要称五卷，不著编辑者名氏；本地合法缓存为维基文库四库本卷一至卷四。四库提要明言："世所传五星之书以此为鼻祖，别有所谓《果老星宗》者，盖因此本而广之。"

- **托名**：第一卷《通玄遗书》托名唐张果（"通玄先生"），第二卷《果憕问答》称明李憕遇张果口授，第三卷《通玄妙经解》称张果撰、元郑希诚注。
- **断代**：内容杂入唐宋元明，实为元明间术士累代汇编，托名上推至张果以神其说。
- **学派关系**：与《果老星宗》同源；四库提要："化气当从天官，正气当从果老。"本书与 guotian-jing 互为表里，是七政四余推命体系最早系统传本。

## 二、版本与来源

- **底本**：清《钦定四库全书》子部七 术数类五；本地 normalized source 收卷一至卷四，source manifest 记为 4/4 acquired。
- **章名规范**：保留繁体字段名，但术语统一使用《果老星宗》通行写法（如"五曜连珠"、"二星合璧"、"朝拱辅夹"）。
- **校勘说明**：卷四《观星要诀》混入大量"一……"开头实战口诀（约 100 余条），来源驳杂，部分含具体寿夭断语；卷五《观星心传口诀补遗》仅见提要著录，未进入本地 normalized source；本 pack 标为 skipped/unavailable，不作规则蒸馏。
- **本地路径**：`references/fulltext/xingming/xingming-suyuan/fulltext.md`（460 行）

## 三、school_lineage 演化谱

```
张果（托名，唐）→ 通玄遗书 + 玉衡经
        ↓
李憕（托名，盛唐）果憕问答 → 至宝论 / 五星先天后天口诀
        ↓
郑希诚（元，瑞安主簿）通玄妙经解 + 观星要诀
        ↓
《星命溯源》（明清间汇编 → 四库本）
        ↓
《果老星宗》（广之而成）
```

## 四、本书在体系中的定位

- 与 [guotian-jing](../guotian-jing/index.md) 共同构成七政四余推命体系的核心双典。
- 本书偏"理论原型"（论断纲领、心法口诀），果老偏"实操扩展"（神煞起例、十干化曜、行限格局）。
- 与子平体系（[ditiansui-chanwei](../../bazi/ditiansui-chanwei/index.md) / [qiongtong-baojian](../../bazi/qiongtong-baojian/index.md)）属并行体系，**不可混用术语与起例**。
- 与相术（[shenxiang-quanbian](../../physiognomy/shenxiang-quanbian/index.md)）互参时本书占主，相术为旁证。

## 五、核心心法

1. **五曜连珠 / 二星合璧 / 朝拱辅夹**：星曜分布格局取贵之纲。
2. **三主取用**：宫主（命宫所主）、度主（命度所主）、身主（夜生身度主）。先生曰"专用宫主为非，度主为是"。
3. **强弱败旺 / 登殿入庙 / 失时得令**：星曜得位失位之衡量。
4. **化气当从天官，正气当从果老**：本书定调，二家术法可互参。
5. **生克制化**：星曜得令、相、休、囚、死按四时流转。

## 六、强制工具依赖

- **`tool.xingming.bindisk`** — 起七政四余命盘、定行度、神煞排布、十一曜垣度。
- 本蒸馏不允许任何手工排盘、行限推演、神煞起例。古书行度数据因岁差错位，必须通过现代天文历算工具校正。

## 七、蒸馏边界

- `verified=false`：所有规则为术数典籍内部一致性提取，不代表客观事实。
- 短引 ≤80 字；不复制大段原文（>200 字）。
- **safety-redlines**：卷四含大量具体寿夭、死法、产亡、孤寡、瞽聋断语，所有此类条目仅作"古文修辞"留存；输出层屏蔽，不允许对真人作硬判。
- **女命 reframe**：卷一玉衡经、卷四观星要诀含"妇人""产亡""三嫁""娼妓""师尼"等强贬义女命断语，必须 reframe 为"古代礼教叙事，仅作典籍内部上下文留存"。
- **天文历算 caveats**：古书行度数据受岁差累积已偏离今天约 24°，必须通过 `tool.xingming.bindisk` 重算；行限推演不可直接套用古书度数。

## 八、文件清单

- [chapter-map.md](./chapter-map.md)
- [terms.md](./terms.md)
- [rules.md](./rules.md)
- [procedures.md](./procedures.md)
- [quote-index.md](./quote-index.md)
- [validation.md](./validation.md)
