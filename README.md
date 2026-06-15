# 银行协议/申请文档预审 POC

这是一个本地可运行的前后端 Demo/POC。它用“材料包”为核心，把电子流、申请书、身份证明、模板基准和预审策略串起来，方便演示银行文档预审从材料进入到风险输出的完整链路。

## 当前能力

- 前端工作台：内置场景矩阵、手动上传材料、上传模板基准、策略运行、结果展示、全量回归表。
- 文档审阅原型：材料树、伪文档预览、风险行高亮、点击风险定位证据、字段核对、模板差异视图。
- 真实案例文件：已挂载旧项目 `test_data` 中的 Word、PDF、身份证明图片，页面展示真实文件名、类型和预览链接。
- 配置中心原型：展示模板区块、eFlow 路径、检查类型、AI 复核开关，当前为前端原型态配置。
- 材料包管理：每个包包含 eFlow、提交文件、身份文件、预期模板版本。
- 策略引擎：
  - `block_rule_check`：区块级字段、账号、证件、权限、介质、限额检查。
  - `template_plus_diff`：提交材料与 Template Plus 基准差异检查。
  - `full_agent_review`：受约束的全文 Agent 风险提示。
  - `hybrid_review`：混合路线预留。
- 模型接口：支持 Mock LLM 和 OpenAI-compatible API，当前本地可接 Kimi。
- Demo Suite：覆盖旧方案 `test_data` 中沉淀的主要场景。

## 快速启动

```powershell
cd D:\AI\project\contract_verify
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8001
```

打开：

- Demo 工作台：http://127.0.0.1:8001/
- API 文档：http://127.0.0.1:8001/docs

## 明日演示入口

建议先打开 Demo 工作台，不要从接口文档开始讲。

1. 在“内置场景”里选择 `PKG-CASE-001-PASS`，运行“区块规则检查”和“模板 Plus 差异检查”，展示正例通过。
2. 切换到 `PKG-CASE-003-ID-MISMATCH` 或 `PKG-CASE-004-NAME-MISMATCH`，展示硬性字段错误。
3. 切换到 `PKG-CASE-005-ACTIVITY-RISK`，展示电子流开通但材料注销的业务方向风险。
4. 切换到 `PKG-DEMO-001`，把模型模式切到真实 API，展示 Kimi 对 `admin approval` 和超审批阈值条款的解释。
5. 进入“文档审阅”，点击右侧风险项，展示文档预览中的证据行定位和高亮。
6. 进入“字段核对”和“模板差异”，分别展示规则判断和 Template Plus 差异分类。
7. 进入“配置中心”，展示区块规则、eFlow 路径、检查类型和 AI 复核开关。
8. 点击“刷新案例状态”，展示 10 个场景的批量验证结果，其中包含 Word、PDF 和图片材料。
9. 切到“上传材料”，上传或粘贴申请书文本和模板基准，生成临时材料包并运行三策略对比。

## 关键接口

- `GET /api/demo-cases`：查看内置演示矩阵。
- `GET /api/packages/{package_id}`：查看材料包。
- `POST /api/upload-package`：创建手动上传材料包。
- `POST /api/packages/{package_id}/run-preaudit`：运行单一策略。
- `POST /api/packages/{package_id}/run-comparison`：运行多策略对比。
- `POST /api/demo-suite/run`：运行全量演示回归。

## 本地验证

```powershell
.\.venv\Scripts\python.exe -m compileall backend scripts tests
.\.venv\Scripts\python.exe scripts\run_demo_regression.py
```

也可以运行完整测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

## 模型接口

默认可用 Mock 模式，适合演示时保证稳定。如果要接公司内部或 Kimi 这类 OpenAI-compatible API，在 `.env` 中配置：

```text
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://your-company-api/v1
LLM_API_KEY=...
LLM_MODEL=...
```

所有策略只通过统一 LLM Client 调用模型，后续切换公司内 API 不需要改策略代码。

## 当前边界

- 文本类文件可以在前端读取正文并进入材料包。
- 内置旧案例会从真实 Word/PDF/图片文件生成预览；Word/PDF/Excel 文本抽取由 `DocumentParser` 负责。
- 图片当前展示原文件，文字识别后续应接 OCR。
- 上传模板基准当前按 key-value 文本做 Template Plus 差异比较，后续可扩展为模板版本管理 UI 和区块框选。
