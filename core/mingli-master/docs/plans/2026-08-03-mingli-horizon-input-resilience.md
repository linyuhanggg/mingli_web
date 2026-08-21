# 命理大师 V5.1 近时范围输入韧性 — 返工实施计划

日期：2026-08-03
分支：`claude/mingli-horizon-resilience-rework-20260803`
工作树：`~/Documents/Codex/2026-08-02/mingli-master-horizon-resilience-rework`
基线：`2ed239f86ea774b326ee8ebd9dbe034192833a4d`
上一版（被拒收）：`claude/mingli-horizon-resilience-20260803`
（`~/Documents/Codex/2026-08-02/mingli-master-judgment-voice`，HEAD
`3965762`，只读保留，本次不修改、不删除、不重写。）

## 1. 真实问题

Hermes 对话记录显示，用户请求"算一下这周运势"时，宿主模型已经**正确**
选出了近时个人运势能力——选术没有问题。但第一次 `prepare` 把范围写成一个
完整民用日的首尾时刻：

```
start = 2026-08-03T00:00:00+08:00
end   = 2026-08-03T23:59:59+08:00
```

`scripts/reading_engine/providers.py` 的 `_target_date` / `_target_dates`
用 `date.fromisoformat` 解析两个边界，而它只接受 `YYYY-MM-DD`：

```
>>> date.fromisoformat('2026-08-03T00:00:00+08:00')
ValueError: Invalid isoformat string
```

于是在真正排盘之前就抛错，统一收敛成 `Stopped.error`。宿主随后清空
horizon 又调用了一次 `prepare` 才成功——即两次调用才拿到一个结果。

复现结果（修改前，参考时刻 `2026-08-03T10:00:00+08:00`）：

| 调用形状 | 修改前 |
| --- | --- |
| 周 + 空边界 | Prepared |
| 周 + `YYYY-MM-DD` 七日 | Prepared |
| 周 + 同一民用日首尾时刻（截图形状） | **Stopped.error** |
| 周 + 单个 ISO datetime 锚点 | **Stopped.error** |
| 日 + 同一民用日 datetime | **Stopped.error** |
| 日 + `Z`/UTC datetime | **Stopped.error** |
| 日 + naive datetime | **Stopped.error** |
| 周 + 显式三日 / 倒序 | Stopped（本应如此） |

这不是 Gateway 故障：范围语义属于 Provider，必须由 Skill 自己消化。

## 2. 上一版被拒收的两个阻塞问题

上一版（`3965762`）已实现单锚点归一化，但验收发现：

1. **P1：end-only 单锚点被忽略。** 上一版 `_near_time_period_days` 用
   `anchor = start if start is not None else fallback_anchor`，且
   `_target_date` 的入口条件是 `horizon.kind == "day" and horizon.start`。
   对 `day + start=null + end=2026-08-05T14:00:00+08:00`，真正计算的是
   reference 民用日 `2026-08-03`，而 `request_view` 仍保留 8 月 5 日边界，
   属于静默错算；相同形状用于 week 会返回 `Stopped.error`。

2. **P2：日期格式闭集被意外放宽。** 上一版 `_civil_day` 直接尝试
   `date.fromisoformat` 再 `datetime.fromisoformat`，后者还接受
   `20260803`、`2026-W32-1`、`20260803T100000` 等未声明格式，静默扩大了
   公开契约。

本返工只修这两个问题，并在新分支按正确提交边界重新提交；旧分支只读保留。

## 2b. 验收后的极小返工（2026-08-03 晚）

第二次验收确认主问题已修复，但严格输入闭集仍有一处遗漏：

1. **P2（阻断）**：`_civil_day` 先执行 `text.strip()` 再做正则校验，
   导致 `" 2026-08-05 "` 被静默修正并进入 `Prepared`。正确行为是带非空
   `public_copy` 的 `Stopped`——必须对原始完整字符串严格检查，不预先
   `strip()`。
2. **P3（非阻断）**：datetime 正则使用 `[T ]`，`2026-08-05 14:00:00+08:00`
   会进入 `Prepared`。将公开闭集明确为只接受 `T` 分隔符。

修复方式：`_civil_day` 不再 `strip()`，直接校验原始字符串；datetime 分隔符
固定为 `T`；`_near_time_period_days` 中只有 `None`/空字符串 `""` 才视为
"未提供边界"，空白内容一律拒绝。新增两侧首尾空白、纯空白、空格分隔
datetime 的公开接口拒绝测试（新套件 49 → 52 项）。

## 3. 归一化规则

单个边界如何解析为民用日：

- `YYYY-MM-DD` 本身就是民用日期，按字面取用。但必须先对**原始完整字符串**
  做严格格式检查（`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`），再交给
  `date.fromisoformat` 验证真实年月日，不得只依赖 `fromisoformat`。
- 其他必须是**完整 ISO-8601 datetime**：严格扩展日期前缀
  `YYYY-MM-DD` + `T` 分隔符 + 明确时间部分（不接受空格分隔日期与时间）。
  支持 naive datetime（按业务时区解释）、带偏移 datetime、大写 `Z`。
  时刻只有落到时区才能确定民用日：
  - 带时区（偏移或 `Z`）：先换算到该 Provider 已解析出的业务时区，
    再取日期。`2026-08-03T20:00:00Z` 在 `Asia/Shanghai` 是 08-04；
    截断字符串会答错一天。
  - 不带时区：按该业务时区解释。
- **不接受**：`20260803`、`2026-W32-1`、`20260803T100000`、`2026-08`、
  自然语言（"这周"）、**带首尾空白的日期/时刻**（如 `" 2026-08-05 "`）、
  纯空白边界、以及"只有日期却偷偷当作午夜"的其他形状。这些一律
  返回非空 `Stopped`，不猜测周期、不静默修正输入。
- 只有 `None` 或空字符串 `""` 才视为"未提供该边界"（与 null 等价），
  进入单锚点 / 双空规则；空白内容不是"未提供"。

范围如何成立：

- **一个锚点**——边界全空、只有一个边界（start **或 end** 皆可）、或两个
  边界归一化后落在同一个民用日——表示"包含该锚点的那个周期"。同一天的
  `00:00:00`/`23:59:59` 本来描述的就是这一天，不是一个"只有一天的周"。
- **两个不同民用日**按字面取用，且必须已经正好构成该周期（周 = 连续
  七日）。三日、八日、倒序都抛错，**不扩大也不截断**。
- 只有 start/end 都为空时，才允许使用 `reference_datetime` 的民用日；
  `reference_datetime` 本身仍是完整参考时刻，不被截断成日期。
- 真太阳时 / 民用时 / 出生时间的既有职责分工不变：本次只涉及"目标周期
  边界"这一件事。

## 4. Locality

归一化放在近时 Provider 的私有函数 `_near_time_period_days` 内，
`calculate()` 与 `extend()` **共用同一个**函数——所以对外公布的有效范围
必然等于真正排过盘的范围，不会出现"说的是一周、算的是一天"。

generic Interface 不按领域 ID 分支；`SKILL.md` 只增加对所有 Provider
通用的调用纪律，不出现任何真实术数名称、`object_id` 或 `capability_id`。
格式说明写进 `resources/runtime/providers/fortune.json` 对应 horizon term
的 `description`（嵌套 `{name, description}` 形式），经既有
`PublicTerm.description` 投影给宿主，不扩大 Interface schema。

## 5. 施工顺序（提交切分）

1. `test:` 先用 public `ReadingInterface.execute` 写失败测试
   （`scripts/test_v51_horizon_input_resilience.py`），覆盖全部形状加
   非法范围、`complete` → `Accepted`、token replay、缺资料仍
   `need_input`、环境记忆封闭、无新增关键词路由。
2. `fix:` 实现 Provider 私有归一化（严格格式 + 单锚点），`calculate` 与
   `extend` 共用。
3. `feat:` 发布 Provider 拥有的边界方向说明（`SKILL.md` +
   `fortune.json`）。
4. `fix:` 保持富显示术语的词汇局部性（`audit_v51_vocabulary_locality.py`
   读取嵌套 `name`）。
5. `docs:` 记录返工计划与真实 evidence（本文件 + release evidence）。

## 6. 不做的事

不改 Gateway、不碰 8642/8645、不动已安装副本、不装依赖、不部署、不 push；
不重写 13 个 Provider 算法、古籍语料或既有确定性体系；不引入"资料最少
优先"或按关键词选术；不改测试或删断言掩盖失败；不在旧分支上 reset、
rebase、amend、stash 或强推。
