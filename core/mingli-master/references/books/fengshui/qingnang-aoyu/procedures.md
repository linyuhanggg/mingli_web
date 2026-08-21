# procedures: 青囊奥语

## QNA-P001 理气问题加载流程

**source_anchor**: fulltext.md L11-L38

1. 用户问玄空、青囊、二十四山、水口、城门、金龙、雌雄、天心十道时，加载本 pack。
2. 同时检查是否应加载 `qingnang-xu`、`tianyu-jing`、`dutian-baozhao-jing` 或 `dili-bianzheng`。
3. 若用户只是问阳宅门主灶，优先 `yangzhai-shishu` / `yangzhai-sanyao`；若问形峦寻龙，优先 `zangshu` / `hanlong-jing` / `yilong-jing` / `rudi-yan-quanshu`。

## QNA-P002 玄空/水法事实层

**source_anchor**: fulltext.md L13-L34

1. 收集坐山、朝向、水来水去、明堂、城门、水口、元运/流派口径。
2. 调用 `tool.fengshui.luopan.degrees_to_24_mountains`，输出二十四山。
3. 调用 `tool.fengshui.water_flow_profile`，输出来水、去水、出入、屈曲、克入、生旺休囚。
4. 调用或要求 `xuan_kong_school_profile`，明确三元/玄空/青囊/蒋大鸿注解口径。
5. 事实层缺任一关键字段时，停止解释，只列缺失项。

## QNA-P003 与下游理气书对读

**source_anchor**: fulltext.md L17-L38

1. 先用本 pack 定位词源：玄空、金龙、城门、天心十道、向放水、进退旺。
2. 查 `qingnang-xu` 对雌雄、金龙、血脉、山水两路的展开。
3. 查 `tianyu-jing` / `dutian-baozhao-jing` 对卦、零正、城门、水法的后续体系。
4. 查 `dili-bianzheng` 时必须标注蒋大鸿注释层，不让注解覆盖原文。
5. 输出时保留“奥语原文层 / 后出注解层 / 工具事实层”三层。
