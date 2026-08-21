# 渊海子平 — Procedures

> 本文件抽取《渊海子平》中可被主 skill 调用的可操作流程。
> 字段：`procedure_id` / `name` / `inputs` / `steps` / `outputs` / `tool_dependencies` / `source_chapter` / `verification_status`。
> 所有涉及排盘的步骤一律以 `tool.bazi.paipan` 标注，**不让 LLM 手算**。
> procedure_id 前缀 `YP` = Yuanhai Procedure。

---

## YP-01 四柱排法

- **name**：四柱排法
- **inputs**：公历生年月日时 / 出生地 / 性别
- **steps**：
  1. 调用 `tool.bazi.paipan` 取得年月日时四柱干支。
  2. 校验节气换月（以节气分界，不以朔望分界）。
  3. 校验真太阳时（如未做，加"待真太阳时复核"标注）。
  4. 输出四柱八字。
- **outputs**：四柱干支
- **tool_dependencies**：`tool.bazi.paipan`（必需）
- **source_chapter**：vol-01/lun-sizhu
- **verification_status**：pending_verification

## YP-02 看命入式

- **name**：看命入式（看命次序）
- **inputs**：YP-01 的四柱
- **steps**：
  1. 以日干定"我"（YR-01-03）。
  2. 取月令定提纲（YR-01-04）。
  3. 看十神透干与藏干（terms.md §3 十神）。
  4. 看合冲刑害（YR-01-06~13）。
  5. 判旺衰（YR-01-05 / YR-02-20）。
  6. 取用神（YR-02-21）；格局精修转 `bazi/ziping-zhenquan`。
  7. 看大运流年（YR-03-01~03）。
  8. 查神煞（YR-04-01 作辅证）。
- **outputs**：命局粗框架 + 用神倾向
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-02/kanming-rushi
- **verification_status**：pending_verification

## YP-03 大运流年合参

- **name**：大运流年合参
- **inputs**：YP-01 的四柱 + 大运表 + 待问年份
- **steps**：
  1. 由 `tool.bazi.paipan` 取大运表。
  2. 锁定待问年份的大运柱与流年柱。
  3. 看大运、流年与命局的生克冲合。
  4. 看触发的神煞。
  5. 输出大运流年关系图谱（不下铁口）。
- **outputs**：大运流年关系图 / 触发的神煞
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-03/lun-dayun；vol-03/lun-taisui；vol-03/lun-liunian
- **verification_status**：pending_verification

## YP-04 看命总节

- **name**：看命总节（总结要诀）
- **inputs**：YP-02 的命局粗框架
- **steps**：
  1. 按卷五"看命总节"的次序复核。
  2. 对照继善篇、喜忌篇的总纲。
  3. 如有格局精修需求 → 转 `bazi/ziping-zhenquan`。
  4. 如有旺衰精修需求 → 转 `bazi/ditiansui-chanwei`。
  5. 如有调候需求 → 转 `bazi/qiongtong-baojian`。
- **outputs**：命局总结 + 分流建议
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-05/kanming-zongjie
- **verification_status**：pending_verification

## YP-05 神煞查表

- **name**：神煞查表
- **inputs**：YP-01 的四柱
- **steps**：
  1. 以日干为主查天乙贵人、禄、羊刃、空亡。
  2. 以年支/日支为主查驿马、华盖、桃花、劫煞亡神、孤辰寡宿。
  3. 标注每个神煞所在柱位。
  4. 按 YR-04-01 神煞作辅证不主主线。
- **outputs**：神煞清单
- **tool_dependencies**：`tool.bazi.paipan`（取四柱信息）
- **source_chapter**：vol-04/lun-shensha-zonglun
- **verification_status**：pending_verification

## YP-06 女命模块

- **name**：女命模块
- **inputs**：YP-01 的四柱（性别=女）
- **steps**：
  1. 取夫星（正官）、子星（食伤）。
  2. 看夫宫（日支）稳定性。
  3. 看伤官见官影响。
  4. 现代输出 reframe，不照搬古文贬义判语。
- **outputs**：女命结构分析
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-03/lun-numing；vol-05/lun-furen-zonglun
- **verification_status**：pending_verification

## YP-07 六亲推断

- **name**：六亲推断
- **inputs**：YP-01 的四柱
- **steps**：
  1. 按 YR-03-04 配属六亲十神。
  2. 看对应十神的所在柱、强弱、是否被冲合。
  3. 输出六亲倾向。
- **outputs**：六亲倾向
- **tool_dependencies**：`tool.bazi.paipan`
- **source_chapter**：vol-03/lun-liuqin
- **verification_status**：pending_verification

---

## 流程总图

```text
[用户问题] ─► YP-01 四柱排法 (tool.bazi.paipan)
                 │
                 ├─► YP-02 看命入式
                 │     ├─ 取月令 → 取格雏形 → (精修转 bazi/ziping-zhenquan)
                 │     ├─ 看十神
                 │     ├─ 看合冲刑害
                 │     └─ 判旺衰 → (精修转 bazi/ditiansui-chanwei)
                 ├─► YP-03 大运流年合参
                 ├─► YP-04 看命总节
                 ├─► YP-05 神煞查表
                 ├─► YP-06 女命模块（性别=女）
                 └─► YP-07 六亲推断
```

---

**说明**：所有事实层步骤均由 `tool.bazi.paipan` 完成。本 pack 作为子平法骨架源，详细格局/旺衰/调候精修需转下游 pack。Batch 1A-1 框架抽取，7 条流程。
