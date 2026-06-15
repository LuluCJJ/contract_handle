# 明日 Demo 实施路径与测试用例

## 演示目标

这次 Demo 要证明四件事：

1. 前后端已经打通：同事可以在页面上选择场景、预览文档、上传材料、运行策略、查看结果。
2. 业务底座稳定：电子流、Word/PDF 申请书、身份证明图片、模板、证据、风险结果都被组织成统一材料包。
3. 方案路线可比较：规则检查、Template Plus 差异、全文 Agent 可以对同一材料包并行输出。
4. AI 受控使用：Kimi 或公司内 OpenAI-compatible API 只做局部风险解释，结果归一化为结构化 `CheckResult`。

## 演示顺序

1. 打开 Demo 工作台：http://127.0.0.1:8001/
2. 从“配置中心”开始，讲清楚场景树、模板与知识资产、Template Plus、填写规范和默认预审路线。
3. 进入“材料准备”，展示当前申请应准备哪些文档，哪些已挂载，真实 Word/PDF/图片材料在哪里。
4. 进入“模板匹配与解析”，说明每份文档匹配哪个模板、解析是否完成、为什么进入路线 A 或路线 B。
5. 用右上角“预审方案”一键切换方案 A/方案 B：方案 A 代表有 Template Plus，方案 B 代表无 Template Plus。
6. 进入“路线 A：模板 Plus”，展示申请书与 Template Plus 基准差异，以及差异分类。
7. 进入“路线 B：填写规范”，展示文档提取内容、参考值/规范、检查结论和证据。
8. 进入“统一预审报告”，展示 10 个场景都可批量验证，其中包含 Word、PDF 和图片材料。
9. 进入“多路径对比”，比较路线 A、路线 B 和全文 Agent 的发现问题、模型调用和配置成本。
10. 选择 `PKG-CASE-003-ID-MISMATCH` 或 `PKG-CASE-004-NAME-MISMATCH`，展示证件号/姓名硬错误。
11. 选择 `PKG-CASE-005-ACTIVITY-RISK`，展示电子流与材料业务方向不一致。
12. 选择 `PKG-DEMO-001`，先用 Mock 展示稳定结果，再切真实 API 展示 Kimi 对新增高风险条款的解释。
13. 切到“上传材料”，粘贴或选择申请书文本，再粘贴模板基准，点击“生成材料包并进入审阅”，展示自定义材料也能进入同一流程。

## 测试用例矩阵

| package_id | 来源旧案例 | 目标 | 预期 |
|---|---|---|---|
| PKG-CASE-001-PASS | case_001_pass | 基础字段一致 | 低风险通过 |
| PKG-CASE-003-ID-MISMATCH | case_003_fail_id | 证件号不一致 | fail/需确认 |
| PKG-CASE-004-NAME-MISMATCH | case_004_fail_name | 操作员姓名不一致 | fail/需确认 |
| PKG-CASE-005-ACTIVITY-RISK | case_005_risk_activity | 开通 vs 注销 | need_confirm |
| PKG-CASE-006-ACCOUNT-RISK | case_006_risk_account | 账号不一致 | fail/需确认 |
| PKG-CASE-007-IDTYPE-RISK | case_007_risk_idtype | 证件类型不一致 | fail/需确认 |
| PKG-CASE-015-MULTI-PASS | case_015_boc_multi_pass | 多操作员数量 | 低风险通过 |
| PKG-CASE-014-PDF-PASS | case_014_boc_domestic_pass | PDF 申请表真实预览 | 低风险通过 |
| PKG-CASE-021-HIGH-LIMIT | case_021_ccb_high_limit | 高限额/敏感行业 | warning/需确认 |
| PKG-DEMO-001 | UBA 手工模板 Plus | admin approval 与超标准审批条款 | high risk/需确认 |
| PKG-UPLOAD-* | 页面手动上传 | 用户自定义材料包 | 能生成包并完成三策略对比 |

## 必测功能点

- 首页能打开，内置场景列表能加载。
- 案例总览能显示每个 case 的通过、失败、需确认和高风险状态。
- 文档审阅页能显示材料树、文档预览和风险证据。
- 内置旧案例材料树能显示真实 `docx/pdf/jpg` 文件，而不是 txt 替身。
- Word 能通过前端 Mammoth 插件渲染为 HTML；PDF 能内嵌预览；Excel 预留 SheetJS 表格预览。
- 右上角“预审方案”能一键切换方案 A、方案 B、A/B 对比，并跳转到对应页面。
- 点击风险项能定位到文档预览里的证据行。
- 字段核对页能展示 eFlow 预期值、文档提取值和结论。
- 模板差异页能展示 baseline、submitted 和差异分类。
- 配置中心能展示区块规则配置原型。
- 模板匹配与解析页能说明文档匹配状态、解析状态和默认预审路线。
- 多路径对比页能展示路线 A、路线 B、全文 Agent 的差异。
- 每个内置材料包能查看详情。
- `block_rule_check` 能识别字段、账号、证件、权限、介质、限额问题。
- `template_plus_diff` 能识别模板基准差异。
- `full_agent_review` 能输出受控 Agent 风险提示。
- Mock 模式可稳定运行，不依赖外部 API。
- 真实 API 模式可调用 Kimi/OpenAI-compatible 接口。
- 手动上传能生成临时材料包。
- 上传模板基准能生成临时 Template Plus 版本。
- 全量 Demo Suite 能跑完 9 个内置场景。

## 已验证

- `python -m compileall backend scripts tests`
- `python scripts\run_demo_regression.py`
- `GET /`
- `GET /api/demo-cases`
- `POST /api/upload-package`
- `POST /api/packages/{package_id}/run-comparison`

## 后续工程路线

1. 文档解析：把 Word/PDF/OCR 接入 `DocumentParser`，替换当前 key-value 文本模拟。
2. 模板管理：做模板版本、固定内容、变量槽位、业务规则的配置页面。
3. 区块配置：支持 PDF 预览框选区块、保存坐标和锚点。
4. 审核反馈：审核人标注误报/漏报，沉淀到规则和模板版本。
5. 生产化：数据库、文件存储、权限、审计日志、脱敏和环境隔离。
