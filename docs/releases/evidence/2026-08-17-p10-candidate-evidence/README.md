# P10 八字、紫微与梅花候选证据层

日期：2026-08-17（Asia/Shanghai）  
范围：本机 V53 one-shot Runtime、合成资料、无个人资料落盘

## 本次完成

- 八字增加 `conflict_arbitration` 工具：保留强弱、格局、调候之间的分歧；只有问题明确指定侧重点时才选择对应 primary view；没有问题侧重时返回 `requires_question_specific_adjudication`。工具始终输出 `hard_verdict=null`，不把冲突压成吉凶、用神或人生结论。
- 紫微增加命宫三方四正候选层：从 Runtime 已计算的命宫、迁移、财帛、官禄、四化和星曜亮度事实生成十条《太微赋》谓词候选。每条保留规则编号、source ref、依赖和匹配状态，状态为 `predicate_matched_not_verdict` 或 `predicate_not_matched`；规则未形成硬断。
- 紫微候选穿过 Provider manifest、后端 `ZiweiCoreFacts`、`ziwei-chart/v1` schema、Web registry 和结果页，页面明确标记“古籍候选（非最终结论）”。
- 梅花增加体用关系候选层：主卦、互卦、变卦的五行关系均保留盘层、位置、体用角色、月令状态、规则编号和 source ref；主卦使用稳定关系 key，互/变卦使用施动者与体的规范关系 key，未知关系不会静默吞掉。
- 梅花候选穿过 Provider manifest、`MeihuaCoreFacts`、`meihua-chart/v1` schema、Web registry、结果页和真实 Worker；候选层保持 `hard_verdict=null`，明确需要古典裁决，不生成吉凶、成败或应期。
- V53 寻时定盘同步到 v2 release：子时按跨午夜区间处理，代表时刻为 `00:00…22:00`，时间范围按传统时辰区间交集计算；这修复了真实 release 中把 `01:30` 标成子时的漂移。
- 真实 Runtime 子进程固定 `PYTHONPYCACHEPREFIX=/dev/null`，避免运行过程中重新生成被启动守卫拒绝的虚拟环境字节码缓存。

## 验证

- 真实 V53 `14` 个能力的 `Prepare → calculated facts → Guard → Complete → Accepted → typed ReadingDocument` 矩阵：`1 passed`；其中新增梅花候选层后的真实矩阵仍通过。
- 梅花真实 Runtime 五种起法（时间、报数、声音、观测、报卦）：`2 passed`，覆盖时间起卦和四种显式起法。
- 后端图表投影、公共核心流程和真实矩阵回归：`28 passed`。
- Web `runtime-chart` 回归：`7 passed`。
- 本轮完整本地门禁：Backend `937 passed / 114 skipped`，Web `454 passed`，Admin `122 passed`；两端 lint、typecheck 和 production build 通过，mypy `142` 个源文件无问题。
- V53 startup gate：`219` 个签名文件、`14` 个 Provider、`55` 个 reference packs、`1328` 条 evidence、`219` 个 closure 文件；正式 release 与工作区镜像逐文件一致且无 pyc。
- 紫微直接候选探针和八字冲突仲裁探针均通过；本轮 release 变更后的全仓门禁已通过：Backend `937 passed / 114 skipped`、Web `454 passed`、Admin `122 passed`、mypy `142` 个源文件无问题，两端 lint/typecheck/build 均通过。
- 显式切换到 V53 release 后，启动门禁再次通过 `14 capabilities / 14 providers / 219 release files / 55 reference packs / 1328 evidence / 219 closure files`；一次性个人真太阳时回归只在进程内使用用户授权资料，八字、紫微、七政均返回 `Prepared`，未写入仓库、服务器、证据正文或记忆。

## 边界

这份证据只证明候选事实和链路接线，不证明完整古法断法、深读、三术合参互证/分歧、解梦/姓名正式 Provider、用户逐页批准或生产准入。梅花现有来源明确把体用/旺衰限定为事实层，因此本次没有凭空增加吉凶判断。奇门现有 named patterns 与太乙 board predicates 同样只属于来源绑定的结构谓词，不等于事件吉凶结论。测试服务器尚未同步本轮 Runtime release，待本地门禁和证据收口后再上传供用户浏览。
