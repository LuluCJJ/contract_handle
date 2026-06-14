# 明日 Demo 实施路径与测试用例

## 演示目标

这次 Demo 要证明四件事：

1. 前后端已经打通：同事可以在页面上选择场景、上传材料、运行策略、查看结果。
2. 业务底座稳定：电子流、申请书、模板、证据、风险结果都被组织成统一材料包。
3. 方案路线可比较：规则检查、Template Plus 差异、全文 Agent 可以对同一材料包并行输出。
4. AI 受控使用：Kimi 或公司内 OpenAI-compatible API 只做局部风险解释，结果归一化为结构化 `CheckResult`。

## 演示顺序

1. 打开 Demo 工作台：http://127.0.0.1:8001/
2. 先讲左侧“演示场景矩阵”：这些场景来自旧方案 `test_data`，现在已转成新材料包。
3. 选择 `PKG-CASE-001-PASS`，运行区块规则检查和模板 Plus 差异检查，展示低风险通过。
4. 选择 `PKG-CASE-003-ID-MISMATCH` 或 `PKG-CASE-004-NAME-MISMATCH`，展示证件号/姓名硬错误。
5. 选择 `PKG-CASE-005-ACTIVITY-RISK`，展示电子流与材料业务方向不一致。
6. 选择 `PKG-DEMO-001`，先用 Mock 展示稳定结果，再切真实 API 展示 Kimi 对新增高风险条款的解释。
7. 点击“全量回归”，展示 9 个场景都可批量验证。
8. 切到“手动上传”，粘贴或选择申请书文本，再粘贴模板基准，点击“生成材料包并预审”，展示自定义材料也能进入同一流程。

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
| PKG-CASE-021-HIGH-LIMIT | case_021_ccb_high_limit | 高限额/敏感行业 | warning/需确认 |
| PKG-DEMO-001 | UBA 手工模板 Plus | admin approval 与超标准审批条款 | high risk/需确认 |
| PKG-UPLOAD-* | 页面手动上传 | 用户自定义材料包 | 能生成包并完成三策略对比 |

## 必测功能点

- 首页能打开，内置场景列表能加载。
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
