# 明日演示实施路径与测试用例

## 演示目标

这次 Demo 要证明三件事：

1. 业务底座稳定：同一材料包能进入统一模型、统一报告、统一证据体系。
2. 方案路线可比较：Demo1 区块规则检查和 Demo2 模板 Plus 差异检查可以并行验证。
3. AI 受控使用：Kimi/公司内 API 只做局部风险解释，输出会被归一化为结构化 CheckResult。

## 明日演示顺序

1. 打开 `GET /api/demo-cases`，说明样例矩阵来自旧方案 `test_data`。
2. 打开一个正例：`PKG-CASE-001-PASS`，运行 Demo1 和 Demo2，展示低风险。
3. 打开一个硬失败：`PKG-CASE-003-ID-MISMATCH` 或 `PKG-CASE-004-NAME-MISMATCH`，展示证件/姓名不一致。
4. 打开一个业务方向风险：`PKG-CASE-005-ACTIVITY-RISK`，展示电子流开通但材料注销。
5. 打开一个高价值风险：`PKG-DEMO-001`，用真实 Kimi 展示模板 Plus 差异解释。
6. 运行 `POST /api/demo-suite/run`，展示整套案例可回归。

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

## 已覆盖功能点

- 场景与材料包管理。
- 电子流字段核对。
- 区块级规则检查。
- 模板 Plus 文本差异检查。
- 差异分类。
- Mock LLM 和真实 Kimi/OpenAI-compatible LLM。
- 模型输出 JSON 归一化。
- 外部 API 瞬断重试。
- 多策略对比。
- Demo Suite 回归。

## 后续工程路线

1. 文档上传与解析：把旧 `test_data` 的 docx/pdf 接入 `DocumentParser`，替换当前 key-value 文本模拟。
2. 模板 Plus 管理：支持业务上传基准模板、配置固定内容和变量槽位。
3. 区块配置 UI：支持 PDF 预览框选区块、保存坐标和锚点。
4. 反馈闭环：审核人标注误报/漏报，沉淀到规则和模板版本。
5. 生产化：SQLite/PostgreSQL、文件存储、权限、审计日志和脱敏。

