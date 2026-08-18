# 2026-08-19 八字用户反馈修正版发布证据

## 结论

用户反馈的四类问题已修正并上传既有测试服务器：出生时间选择后控件不再被拉高；结果页不再展示原始 JSON、英文键名和服务端枚举；报告移除无意义的对象、主题与目标日期元数据；PNG/PDF 改为八字专用中文内容并消除不受字体支持的符号。

- 验收入口：`http://106.14.10.235:18080/bazi`
- 当前应用 release：`/opt/fateradar/releases/ui-preview-20260819-bazi-acceptance-fix5`
- 回滚应用 release：`/opt/fateradar/releases/ui-preview-20260819-bazi-acceptance-fix4`
- Runtime：沿用既有已签名 V53 one-shot release，未在本次修改算法制品
- 回滚记录：`/opt/fateradar/shared/cache/bazi-acceptance-fix5-20260819-previous-release.txt`

## 用户可见改动

- 年、月、日、时、分选择框使用同一固定高度；日期与时间区域顶部对齐。
- 免费结果只展示八字盘面和确定性事实，不再把 `branch_relations`、`interpretive_candidates`、`luck_cycles` 等结构原样打印。
- `metal`、`calculated`、`civil`、`midnight`、`exact Jie instant`、`policy`、`Runtime` 等内部文字均不再出现在八字公开可见页面；五行、状态、时间口径、换日与换月口径改为中文。
- 结果正文采用单列全宽布局，实测页面高度由修复前约 `17156 px` 收敛到 `5301 px`。
- 报告侧栏只保留版本、状态和说明，删除“对象 / 命理档案、主题 / 事业、服务端目标日期 / 长期范围”。
- PNG/PDF 使用八字专用内容：四柱、日主/月令/时令、五行计数、地支关系、大运、古籍定位和免费预览边界；不再输出通用事实面板或内部结构。

## 构建与验证

- Web 全量：`80 files / 505 passed`。
- 最后文案补丁定向：`24 passed`；TypeScript 与 ESLint 通过。
- 本地和服务器 Next production build 均通过，服务器重新执行 standalone prepare。
- Backend 导出、交付和 API 定向回归：`7 passed`；服务器 release 不安装 `pytest` 开发依赖，因此未伪称远端 pytest 已执行。
- 公网真实 Playwright 从填写出生资料到排盘、下载 PNG/PDF：`1 passed`；同时断言无 page error、无 5xx、结果内容宽度比例大于 0.75、页面高度小于 9000 px，并对整页执行内部英文禁词检查。
- PNG 文件头与尺寸有效；PDF 为 A4、2 页、PDF 1.4。PDF 两页均已渲染为图片人工复核，中文无方框乱码；`pdftotext` 未命中旧元数据、原始结构名或问题符号。
- 切换后 `fateradar-test-api`、`fateradar-test-worker`、`fateradar-test-web`、`fateradar-test-admin` 均为 `active`，`NRestarts=0`；公网 `/bazi`、API live、ready 均为 `200`。

## 浏览器与导出证据

- [时间填写后的表单](../../../../artifacts/browser-evidence/2026-08-19-bazi-acceptance-fix5/1440/bazi-form-after-time.png)
- [真实结果整页](../../../../artifacts/browser-evidence/2026-08-19-bazi-acceptance-fix5/1440/bazi-result-clean.png)
- [下载的 PNG 报告](../../../../artifacts/browser-evidence/2026-08-19-bazi-acceptance-fix5/1440/bazi-report.png)
- [下载的 PDF 报告](../../../../artifacts/browser-evidence/2026-08-19-bazi-acceptance-fix5/1440/bazi-report.pdf)
- [PDF 第 1 页渲染](../../../../artifacts/browser-evidence/2026-08-19-bazi-acceptance-fix5/1440/bazi-report-pdf-page-1.png)
- [PDF 第 2 页渲染](../../../../artifacts/browser-evidence/2026-08-19-bazi-acceptance-fix5/1440/bazi-report-pdf-page-2.png)

## 发布过程说明

fix4 首次切换时发现 rsync 继承了本机目录的 `0700` 权限，服务账号无法进入候选目录。自动回滚当场恢复到 fix3，四服务与公网健康均恢复；随后只修正候选目录的组可进入权限，并以真实 `fateradar` 服务账号在独立端口预检成功后重新切换。最终 fix5 继承已验证权限并再次完成候选预检、原子切换和公网纵链。

## 边界

本次交付的是免费确定性八字排盘预览，不是完整深度解读。测试环境仍为 local + 已签名 one-shot Runtime；Model、OTP 与支付仍是 Fake/不可用。页面与导出明确写明“尚未生成完整深度解读”，不得把本次排盘验收描述成真实付费模型解读已经上线。未修改生产域名，未 push Git，也未把用户验收状态自动标为通过。
