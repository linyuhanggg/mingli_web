# 疑龙经 — Procedures

> 严格禁令：本流程仅声明工具依赖，不允许 LLM 手算坐向、罗盘度数、地势距离。
> 所有现场判别须由具资质的勘舆师傅与现代地质/规划工具配合完成。

## P-01: 干枝辨识与立穴位置粗筛
- **purpose**: 据《疑龙经》上篇辨干龙枝龙之关系，初筛立穴位置
- **steps**:
  1. 借助现代地形图与卫星影像识别区域主脉走向（需要工具：tool.fengshui.terrain / 现代 GIS）
  2. 沿干龙路径标注护托旗枪位置（需要工具：tool.fengshui.terrain）
  3. 识别枝龙护纒疊数（≥三疊为可取）（需要工具：tool.fengshui.terrain）
  4. 据 R-01 / R-02 给出"干上""枝上"标注，不作最终选址
  5. 将候选位置与现代水文图、地质图叠加复核（需要工具：现代 GIS / 地质勘察）
- **tool_dependency**: [tool.fengshui.terrain, 现代 GIS, 地质勘察]
- **source_chapter**: shangpian
- **verified**: false

## P-02: 朝山真假与明堂格局复核
- **purpose**: 据上篇朝山法与明堂横直辨明堂格局
- **steps**:
  1. 现场踏勘候选穴位前方山形（需要工具：tool.fengshui.terrain / 现场踏勘）
  2. 据 R-04 判别朝山特来与否，标记"墜朝山"风险
  3. 用罗盘测量明堂方向（需要工具：tool.fengshui.luopan）
  4. 据 R-05 检查明堂避风惜水之具体形态
  5. 编写形势记录文档，不替代选址决策
- **tool_dependency**: [tool.fengshui.terrain, tool.fengshui.luopan, 现场踏勘]
- **source_chapter**: shangpian
- **verified**: false

## P-03: 干龙尽处鬼官辨识
- **purpose**: 据中篇辨识干龙行尽处之鬼山官山，为大地候选给出文化研究意义上的标注
- **steps**:
  1. 借助 GIS 工具识别干龙路径之"水穷山尽"区域（需要工具：tool.fengshui.terrain / 现代 GIS）
  2. 现场踏勘穴后逆转之鬼山形态（需要工具：tool.fengshui.terrain）
  3. 现场踏勘隔水来顾之官山（需要工具：tool.fengshui.terrain）
  4. 据 R-07 给出大地候选标注，仅作文化研究参考
  5. 任何阴宅选址决策应交由具资质机构与现代法规审核
- **tool_dependency**: [tool.fengshui.terrain, 现代 GIS, 现场踏勘]
- **source_chapter**: zhongpian
- **verified**: false

## P-04: 形穴真假之文化研究判别
- **purpose**: 据下篇与第七问辨蛇虎人禽等形穴真假
- **steps**:
  1. 现场识别龙脉外形归类（蛇 / 虎 / 蜈蚣 / 龙等）（需要工具：tool.fengshui.terrain）
  2. 据 R-17 寻找相配之真案（鼠蛤 / 肉堆狮子 / 蚰蜒 / 雲雷等）
  3. 现场用罗盘记录穴位与案之相对方位（需要工具：tool.fengshui.luopan）
  4. 输出形穴对应表，明确标注"仅作文化研究参考"
  5. 不据此作阴宅选址决策
- **tool_dependency**: [tool.fengshui.terrain, tool.fengshui.luopan]
- **source_chapter**: xiapian
- **verified**: false

## P-05: 九星博换辨识与穴形对应
- **purpose**: 据十问·博换与变星篇，识别龙脉九星博换节数与对应穴形
- **steps**:
  1. 沿干龙路径以现代等高线分段（需要工具：tool.fengshui.terrain / 现代 GIS）
  2. 据 R-20 标注每段九星本相（贪巨禄文廉武破辅弼）
  3. 据 R-21 给出本相对应穴形（乳突 / 窝中 / 釵頭 / 燕窠仰等）
  4. 现场踏勘验证（需要工具：tool.fengshui.terrain / 现场踏勘）
  5. 输出博换分段图，仅作风水文献研究使用
- **tool_dependency**: [tool.fengshui.terrain, 现代 GIS, 现场踏勘]
- **source_chapter**: wen-10-bohuan
- **verified**: false

## P-06: 主客与花穴之鉴别核查
- **purpose**: 据第六问、第九问辨主客山与花假穴
- **steps**:
  1. 现场踏勘候选穴前后山水（需要工具：tool.fengshui.terrain）
  2. 据 R-16 以水抱方向辨主客
  3. 据 R-19 检查案山是否向裏、外點檢山醜走
  4. 数重龙虎外抱之穴据 R-19 末段加倍审慎
  5. 任何鉴别结论仅作文化研究参考
- **tool_dependency**: [tool.fengshui.terrain, tool.fengshui.luopan]
- **source_chapter**: wen-6-zhuke
- **verified**: false

## P-07: 阳宅与阴宅穴形差异之文化对照
- **purpose**: 据第四问、第五问对照阳宅阴宅穴形要求
- **steps**:
  1. 区分研究对象为阳宅或阴宅（需要工具：tool.fengshui.terrain）
  2. 阳宅候选据 R-15 检查穴大寬阔连绵平伏
  3. 阴宅候选据 R-15 检查穴小、势抱水朝
  4. 阳宅决策须以现代规划法、建筑规范为准
  5. 阴宅决策须以现代殡葬法规与公共卫生规范为准
- **tool_dependency**: [tool.fengshui.terrain]
- **source_chapter**: wen-4-yangzhai
- **verified**: false
