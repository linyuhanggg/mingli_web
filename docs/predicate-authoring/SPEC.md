# 谓词施工规范

给承接「把古籍规则条文翻译成可执行谓词」这项工作的执行者。逐条照做，不要推断规范之外的做法。

---

## 0. 这项工作是什么

发行包里有 1328 条从 55 部古籍抠出来的规则，每条带原文、行号锚点和 SHA-256。其中 747 条**还没有触发条件**——机器不知道这条古文在什么情况下适用，所以永远不会被用上。

你的工作：给这些规则写触发条件（谓词）。

一条规则长这样：

```
《三命通会》R-03-03 阳刃
  原文：「阳干见刃位（甲见卯、丙见午、戊见午、庚见酉、壬见子）为阳刃；阴干一般不取刃。」
  触发条件：？？？   ← 你要写的
```

翻译后（取其中「甲见卯」一支，实测 360 张基准盘成立 3 次 = 0.83%）：

```yaml
predicates:
  - {operator: eq, path_suffix: /output/day_master/stem, value: 甲}
  - {operator: descendant_eq, path_suffix: /output/hidden_stems, value: 卯}
```

第一条限定日干为甲，第二条要求卯出现在某一柱的地支上
（`/output/hidden_stems/{年月日时}/branch` 是逐柱地支，天干里不会出现卯，所以
`descendant_eq` 在这里等价于「某柱地支为卯」）。

**你只写触发条件。不写断语、不改原文、不判断吉凶。**

---

## 1. 唯一可编辑的文件

```
core/mingli-master/references/matrices/evidence-scope-bindings-v1.yaml
```

**只改这一个文件。**编译器会从它重算所有摘要和索引。

### 绝对不要碰

| 文件 | 为什么 |
|---|---|
| `references/index/evidence-rules.jsonl` | 编译产物。手改会破坏 5 处耦合摘要，Runtime 直接拒绝启动 |
| `references/matrices/classical-evidence-bindings-v1.json` | 独立审计产物。它决定规则能否激活，不是施工范围 |
| `.mingli-release-manifest.json` | 签名清单 |
| `references/books/**`、`references/fulltext/**` | 原文。改一个字就破坏 `quote_hash` 和原文锚点 |
| `scripts/**` | 引擎代码 |

---

## 2. YAML 格式

```yaml
schema_version: mingli-evidence-scope-bindings-v1
bindings:
  <规则完整 ID>:
    route: <见下表>
    rationale: <一句话说明这个条件依据原文哪一句>   # 必填，缺了编译器直接报错
    predicates:
      - operator: <见 §3>
        path_suffix: <见 §4>
        value: <单值>        # 或 values: [多值]，二者只能用一个
    excluded_predicates:      # 可选：满足则不适用（用于「忌」「不见」类）
      - {...}
    evidence_role: <可选，见 §6>
```

### route 白名单

只有这 10 个 route 被编译器接受：

```
bazi   ziwei   luming-nayin   xingming   liuyao
meihua   liuren   selection   fengshui   physiognomy
```

**没有 qimen，没有 taiyi。**这两门不在本次范围内，遇到就跳过。

`rationale` 是**强制字段**，不是注释。缺了编译器报
`evidence scope rationale missing: <规则 ID>`。

route 必须与规则 ID 的书目前缀相符，例如 `bazi/sanming-tonghui#R-03-03` 的 route 必须是 `bazi`；`divination/zengshan-buyi#...` 的 route 是 `liuyao`，`divination/meihua-yishu#...` 的 route 是 `meihua`。写错编译器会报错。

---

## 3. 算子白名单

**只有这 7 个。**用别的编译器直接拒绝。

| 算子 | 语义 | 用法 |
|---|---|---|
| `eq` | 该路径的值等于 value | `{operator: eq, path_suffix: /output/day_master/stem, value: 甲}` |
| `in` | 该路径的值属于 values 之一 | `{operator: in, path_suffix: /output/month_command/branch, values: [亥,子,丑]}` |
| `contains` | 该路径的值（字符串/数组）包含 value | `{operator: contains, path_suffix: /output/named_patterns, value: 三奇入墓}` |
| `descendant_eq` | 该路径**子树内任一叶子**等于 value | `{operator: descendant_eq, path_suffix: /output/palaces, value: 命宫}` |
| `same_record_fields` | 子树内**同一条记录**同时满足多个字段 | `{operator: same_record_fields, path_suffix: /output/star_facts, value: {name: 紫微, palace: 命宫}}` |
| `present` | 该路径存在 | 慎用，见 §5 |
| `nonempty` | 该路径存在且非空 | 慎用，见 §5 |

### 三条重要限制

**没有 OR。**`predicates` 列表内所有条目是 **AND**。遇到「A 或 B 则 C」，拆成两条规则，ID 加后缀区分（`R-06-29a` / `R-06-29b`），两条的 `rationale` 都注明是同一原文的分支。

**没有计数。**「庚丁戊三者俱透」这类需要计数的，**跳过不写**，在交付清单里列为「需计数算子，当前不支持」。不要用三个 `eq` 硬凑——那表达的是「三者都在盘中某处」，不等于「三者俱透（出现在天干）」，语义不同。

**没有程度比较。**「过多」「太旺」「不及」这类没有可判定阈值的，**跳过不写**，列为「原文无可操作阈值」。

### `same_record_fields` 是最有用的那个

古籍条件大量是「同一位置上两个特征同时成立」。这种情况**必须**用
`same_record_fields`；用两个独立的 `descendant_eq` 是错的——那只表示
「盘里有太阳」和「盘里有官禄宫」，它们可能毫不相干。

它的分组语义：`path_suffix` 下**再下一段路径**即一条记录，`value` 里的
字段必须是那条记录的**直接子字段**。所以：

- ✅ `path_suffix: /output/star_facts`，字段 `name` / `palace` / `brightness` / `mutagen`
  （`star_facts` 是扁平星曜表，每条记录直接带宫位归属）
- ❌ `path_suffix: /output/palace_facts`，字段 `name` + 星名
  （星曜在 `palace_facts/N/majorStars/M/name`，隔了两层，不是直接子字段）

### 紫微：`star_facts` 是主力路径

紫微盘里几乎所有「某星在某宫」「某星带某四化」「某星在某地支」都走这一条路径。
一条记录的字段实测如下：

```
/output/star_facts/N/name           = '太阴'
/output/star_facts/N/palace         = '命宫'        十二宫名，见下
/output/star_facts/N/palace_branch  = '寅'          宫位地支
/output/star_facts/N/brightness     = '旺'          庙旺得利平陷不
/output/star_facts/N/mutagen        = '忌'          禄权科忌，无四化时为空串 ''
/output/star_facts/N/type           = 'major'       major/soft/tough/flower/lucun/tianma/helper/adjective
```

**十二宫名的准确字符串**（写错就恒不成立）：

```
命宫  兄弟  夫妻  子女  财帛  疾厄  迁移  仆役  官禄  田宅  福德  父母
```

注意是 `官禄` 不是「事业」，是 `仆役` 不是「奴仆」。

---

## 4. path_suffix 只能从白名单里选

```
docs/predicate-authoring/fact-paths/bazi.txt          733 条
docs/predicate-authoring/fact-paths/ziwei.txt         346 条
docs/predicate-authoring/fact-paths/xingming.txt      311 条
docs/predicate-authoring/fact-paths/luming-nayin.txt   89 条
```

**不许自己编路径。**这是最严重的错误类型：编一个 `/output/lu_cun/palace` 出来，编译能过、校验能过，但它在任何盘上都不成立——**静默失效**，只有跑判别力检查才会暴露。

白名单里的数组下标已归一为 `/N`。写谓词时：

- 要匹配任意一条记录 → 用 `/N` 之前的父路径 + `descendant_eq` 或 `same_record_fields`
- 要匹配特定位置 → 写具体下标，如 `/output/four_pillars/day/stem`

如果你需要的信息白名单里没有，**不要绕过**。记录到交付清单的「缺路径」一节，说明需要哪个事实，交给算法侧决定是否补 Runtime 输出。

---

## 5. 判别力：最容易踩的坑

**一条谓词必须能区分不同的盘。**

反面例子——现有 125 条绑定里的真实写法：

```yaml
ziwei/ziwei-doushu-quanshu#ZW-06-01:
  predicates:
    - {operator: nonempty, path_suffix: /major_limits}
```

「盘里有大限」——每张紫微盘都有。这条在 **100%** 的盘上成立，等于没有条件。这种写法会被验收直接打回。

正面例子：

```yaml
bazi/qiongtong-baojian#QR-01-04:      # 三冬甲木
  predicates:
    - {operator: eq, path_suffix: /output/day_master/stem, value: 甲}
    - {operator: in, path_suffix: /output/month_command/branch, values: [亥,子,丑]}
```

实测 12/360 = **3.33%**。这是真条件。

### 硬指标

验收在 360 张基准盘（30 个日期 × 12 时辰的交叉积）上测每条谓词的成立率：

- **成立率 > 60%** → 存在性检查，打回
- **成立率 0%** → 打回。三种可能，交付前自己先分清：
  1. 条件组合在术数上根本不存在（例：「紫府同宫在丑」——实测紫府只在**寅、申**同宫）
  2. 路径对但取值字符串错（例：宫位写成「事业」而不是 `官禄`）
  3. 基准盘样本没覆盖到 → 用 `--count 1080` 复测。真实例子：
     `eq(/output/four_pillars/day, 甲子)` 在 360 张盘上 0 次，因为默认 30 个日期
     只覆盖 60 个日柱中的 30 个，甲子不在其中；放大样本即可命中
- **成立率 ≥ 1 次命中且 ≤ 60%** → 通过

不设百分比下限。实测合法的罕见格局可以低到 **0.83%**（「太阳会文昌于官禄」在
360 张盘上命中 3 次），用百分比下限会误杀真规则。

`present` / `nonempty` 几乎必然导致 100%。**除非原文本身就是「只要有这类盘面就适用」
这种方法论陈述**（这种要标 `evidence_role: methodology_rule`，验收会豁免判别力上限），
否则不要用这两个算子。

### 不要凭术数常识推测，一律实测

写这份规范时我推测「紫府同宫在丑或未」，实测是**寅和申**，丑未两个变体成立率 0%。
凭推测写出来的谓词能通过编译和路径检查，只有判别力检查会抓到——**所以每条都要跑
一遍再交**，不要成批写完才验。

---

## 6. `series`：批量模板

编译器支持这个结构，专门用于「同一谓词形状 × 不同取值」。现有 125 条绑定一条都没用它，但很多规则适合。

```yaml
series:
  - route: bazi
    source_pack: bazi/sanming-tonghui
    rationale: 十恶大败以年柱查日柱，原文逐项列举特定日柱干支。
    predicate: {operator: eq, path_suffix: /output/four_pillars/day}
    values:
      R-03-17a: 甲辰
      R-03-17b: 乙巳
      R-03-17c: 丙申
```

**注意**：`predicate` 里**不能**预先写 `value` 或 `values`，值由 `values` 映射注入。
规则 ID 由 `source_pack` + `#` + 映射键拼成。

**`series` 只能注入单值。**它把 `values` 里的每个值塞进**同一个**谓词的 `value` 字段，
所以只适用于「一个谓词、换一个取值」的形状。像阳刃「甲见卯」这种需要**两个谓词联合**
（限定日干 + 限定地支）的，`series` 表达不了，必须在 `bindings` 里逐条写。

适合 `series` 的：十恶大败（查日柱干支）、纳音查表、单字段枚举。
不适合的：任何需要两个及以上谓词的条件。

---

## 6.5 已实测的范例（照这个写）

下面每条都在 360 张基准盘上跑过，括号里是实测成立率。**照这些形状写，不要自创。**

### A · 星 + 宫位地支：一条 `same_record_fields`

```yaml
ziwei/taiwei-fu#TR-11:
  route: ziwei
  rationale: 依《太微赋》「太阳居午，谓之日丽中天」，条件即太阳落午宫。
  predicates:
    - operator: same_record_fields
      path_suffix: /output/star_facts
      value: {name: 太阳, palace_branch: 午}
```

实测 24/360 = **6.67%**。同型：`{name: 太阴, palace_branch: 子}`（TR-12，9.44%）。

### B · 两星同宫，且宫位是常量：两条 `same_record_fields` 相 AND

```yaml
ziwei/taiwei-fu#TR-13:
  route: ziwei
  rationale: 依《太微赋》「太阳会文昌于官禄」，条件为太阳与文昌同落官禄宫。
  predicates:
    - operator: same_record_fields
      path_suffix: /output/star_facts
      value: {name: 太阳, palace: 官禄}
    - operator: same_record_fields
      path_suffix: /output/star_facts
      value: {name: 文昌, palace: 官禄}
```

实测 3/360 = **0.83%**。

**为什么这样 AND 是对的**：两条谓词都把 `palace` 钉死成同一个常量 `官禄`，
所以「太阳在官禄」且「文昌在官禄」必然意味着二者同宫。

**什么时候这样 AND 是错的**：如果宫位不是常量（「某两星同宫，不限哪一宫」），
两条独立谓词只表示「盘里有 A」「盘里有 B」，**不表示同宫**。那种情况见 C。

### C · 两星同宫但宫位不固定：必须按可能的宫位拆成多条

「紫府同宫」原文没指定宫位。不能写成两条不带宫位的谓词——那不表达同宫。
正确做法是穷举它实际可能出现的宫位，拆成独立规则：

```yaml
ziwei/ziwei-doushu-quanshu#ZW-01-07a:
  route: ziwei
  rationale: 《紫微斗数全书》紫府同宫格；本条为落寅宫的分支（同格另有申宫分支 ZW-01-07b）。
  predicates:
    - operator: same_record_fields
      path_suffix: /output/star_facts
      value: {name: 紫微, palace_branch: 寅}
    - operator: same_record_fields
      path_suffix: /output/star_facts
      value: {name: 天府, palace_branch: 寅}
```

实测：寅 44/360 = **12.22%**，申 26/300 = **8.67%**。
丑、未两个分支实测 **0%**——紫府不在那两宫同宫，写了就是错的。

### D · 四化

```yaml
predicates:
  - operator: same_record_fields
    path_suffix: /output/star_facts
    value: {name: 武曲, mutagen: 忌}
```

实测 72/360 = **20.00%**。`mutagen` 取值：`禄` `权` `科` `忌`，无四化时是空串 `''`。

### E · 反例：不要这样写

```yaml
# ✗ 错误：这两条毫不相干，表达的是「盘里有太阳」且「盘里有官禄宫」
predicates:
  - {operator: descendant_eq, path_suffix: /output/star_facts, value: 太阳}
  - {operator: descendant_eq, path_suffix: /output/star_facts, value: 官禄}
```

实测 360/360 = **100%**。每张盘都有太阳、都有官禄宫，这条等于没有条件。
`descendant_eq` 只看「子树里有没有这个值」，不管它落在哪条记录上。
**需要「同一条记录同时满足多个字段」时，永远用 `same_record_fields`。**

---

## 7. 禁止项

| 禁止 | 原因 |
|---|---|
| 修改任何 `quote` 字段 | 破坏 `quote_hash` 与原文锚点，整条规则失效 |
| 设置 `runtime_active: true` | 激活状态由古籍绑定的核对结果决定，不是施工内容 |
| 填写 `semantic_verification_status` | 同上，这是审计产物 |
| 写入任何 `verdict` 字段 | 谓词只表达「此条适用」，绝不表达「所以结论是 X」。出现即打回 |
| 使用白名单外的算子或 route | 编译器拒绝 |
| 为了让成立率好看而放宽条件 | 条件必须来自原文，不是来自指标 |

**核心红线**：谓词回答的是「这句古文适不适用于这张盘」，不是「这张盘吉不吉」。

---

## 8. 交付前自检

每批改动交付前，自己按顺序跑完这三步，全绿再交。

```bash
# 1 编译必须 pass
cd core/mingli-master && PYTHONDONTWRITEBYTECODE=1 \
  ~/.local/share/mingli-master/venv/bin/python scripts/build_evidence_index.py --check
```

```bash
# 2 施工前先存基线快照（只需在开工时做一次）
python3 scripts/verify_predicates.py --route ziwei --snapshot snapshots/ziwei-before.json
```

```bash
# 3 验收本批改动：路径真实性 + 判别力 + 越界扫描（默认 360 张基准盘，约 50 秒）
python3 scripts/verify_predicates.py --route ziwei --since snapshots/ziwei-before.json
```

```bash
# 4 若某条成立率为 0 且你确信条件正确，放大样本复测
python3 scripts/verify_predicates.py --route ziwei --since snapshots/ziwei-before.json --count 1080
```

退出码 0 才算通过。任何 `✗` 都要修掉，不要提交带 `✗` 的批次。

### 交付清单

每批附一份清单，逐条写：

- 规则 ID
- 依据原文的哪一句（引用那一句）
- 谓词的自然语言解释（一句话）
- 实测成立率
- 跳过的规则及原因（需计数 / 无可操作阈值 / 缺路径 / route 不支持）

---

## 9. 操作陷阱

**所有调用 Runtime venv 的 Python 命令必须带 `PYTHONDONTWRITEBYTECODE=1`。**

漏了会往 venv 里写 `__pycache__`，触发运行时完整性校验，之后八字之类的 Provider 会以一个完全看不懂的错误失败：

```
"The V4 transaction did not produce a complete result."
```

补救：

```bash
find ~/.local/share/mingli-master/venv -type d -name __pycache__ -exec rm -rf {} +
```

同理不要在 `core/mingli-master/` 里留下 `__pycache__`。

---

## 10. 本次范围与优先级

| 顺序 | 典籍 | 空谓词条数 | route | 说明 |
|---|---|---|---|---|
| 1 | 紫微斗数全书 | 47 | `ziwei` | 紫微入口目前判断规则为 0，优先级最高 |
| 2 | 增删卜易 | 44 | `liuyao` | 六爻入口目前为 0 |
| 3 | 三命通会 | 105 | `bazi` | 存量最大，大量查表型规则，适合 `series` |
| 4 | 滴天髓阐微 | 51 | `bazi` | 纲领性条文较多，预计跳过比例高 |

一次交付一本书，不要跨书混批——验收要按 route 分开跑。

不在范围内：qimen、taiyi（route 不支持）；风水、相法（需要现场资料/影像输入，Provider 探测尚未跑通）。

---

## 附：语义忠实由人工复核

前面所有检查都是机器判定的。有一项机器判不了：**这个谓词是否真的表达了原文那句话的条件**。

这一项由算法侧人工逐条复核。所以 `rationale` 字段必须写清楚依据原文哪一句——复核时会拿它跟原文比对。写「Recovered from the checked contract」这种样板话等于没写，会被打回。


---

## 附二：运行环境（两个路径，不要混）

```
core/mingli-master/          可编辑源码。scope YAML、编译器、规则索引在这里。
                             **没有签名清单，跑不了 Provider。**
.runtime/v53-time-check-release/   已签名 Runtime，220 文件 / 14 capability。
                             跑盘面事实用它。它的 YAML 是上次发布的快照，不要改。
```

验收工具已按这个布局拆开：

```bash
python3 scripts/verify_predicates.py --route ziwei --since snapshots/ziwei-before.json
# 默认 --tree core/mingli-master  --runtime .runtime/v53-time-check-release
```

判别力测量不需要你的新谓词进入 release——tracer 直接对 fact index 评估目标谓词，
绕过 `runtime_active` 门禁。所以**改完源码树的 YAML 就能立刻验收，不用重新签名发布**。

项目在 exFAT 卷上，编辑器的原子写会报 `ENOTSUP`。写文件先落 `/tmp` 再 `cp` 到目标；
原地改用 `sed -i`。
