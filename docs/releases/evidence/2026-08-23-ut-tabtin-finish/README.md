# T-0821-UT-3 用户测试证据

入口：`http://106.14.10.235:18080/`（预览 `ui-20260823-fivearts-t0821rel4`）
身份：游客；排盘资料 林宇航 / 男 / 2000-10-18 05:10 / 福建省莆田市涵江区
视口：1440×900、360×800（系统 Chrome）
结论：**PASS**

验收的是纸墨完成度，不是暗色皮肤。不因「不够像 TabTin 官网」判 FAIL。

## 首页 `/`

| 项 | 1440 | 360 |
| --- | --- | --- |
| 01–07 章节 | 可见 01 开卷、02 先做这一件、03 机制、04 命盘、05 问事、06 合参、07 先拿到一张可核对的盘 | 同左，可滚动数出 |
| 标题 vs 正文 | 主标题 56px/700，章题 40px/700，正文 18px/400 | 主标题仍明显大于正文 |
| 册页框 + 空盘 | 03 节右侧册页框（352×232）年/月/日/时柱空槽，文案「无示例干支」，未出现假干支 | `display:none`，无桌面框，符合「360 可以没有」 |
| 动效 | 入场/墨气/符箓 sway 均为 1 次迭代后结束，未见无限乱飞 | 同左 |
| 减弱动态 | `prefers-reduced-motion: reduce` 下 `getAnimations()` 为空，符箓不再摆 | 同左 |

截图：`1440/00-home-hero.png`、`1440/01-home-ch-01.png`–`07.png`、`1440/01b-home-reduced-motion.png`；`360/00-home-hero.png`、`360/01-home-ch-01.png`–`07.png`。

## 八字 `/bazi`

游客填表出盘。四柱为矩阵表（年庚辰、月丙戌、日己酉、时丁卯），在盘面卡片里，不是散开的定义列表。时间层芯片：本命 / 流年 / 流月 / 流日。点流年只发一层：`POST /api/v1/readings/preview` 仅 `target_year: 2026`（1440 与 360 各一次）。未做 UT-1 全套失败网测。

截图：`1440/05c-bazi-natal.png`、`1440/06c-bazi-year.png`；`360/05d-bazi-natal.png`、`360/06d-bazi-year.png`。

## 梅花 `/meihua` 游客起卦

提交后 URL 仍是 `/meihua`，未进 `/account/history/:id`。本页出三卦一组：本卦天山遁、互卦天风姤、变卦天火同人；体乾金、用艮土。可见正文无内部键（`calculated_strength_not_verdict`、`facts_only`、英文 polarity 工序句等）。顶栏仍是「登录」。

截图：`1440/08d-meihua-filled.png`、`1440/10d-meihua-s3.png`；`360/08d-meihua-filled.png`、`360/10d-meihua-s3.png`。正文：各视口 `meihua-result-text.txt`。
