# 银行协议/申请文档预审 POC

这是一个本地可运行的银行协议/申请材料预审 Demo/POC 骨架。它的重点不是让 AI 从头审全文，而是验证多条可插拔预审路线：

- `block_rule_check`：区块级填写规范检查
- `template_plus_diff`：模板 Plus 基准差异检查
- `full_agent_review`：受约束的全文风险提示预留
- `hybrid_review`：混合路线预留

## 快速启动

```powershell
cd D:\AI\project\contract_verify
python -m uvicorn backend.app.main:app --reload --port 8000
```

打开：

- API 文档：http://127.0.0.1:8000/docs
- Demo 页面：http://127.0.0.1:8000/

## 明日演示入口

- 案例矩阵：`GET /api/demo-cases`
- 单材料包运行：`POST /api/packages/{package_id}/run-preaudit`
- 多策略对比：`POST /api/packages/{package_id}/run-comparison`
- 全量演示回归：`POST /api/demo-suite/run`

本地一键回归：

```powershell
python scripts\run_demo_regression.py
```

## 模型接口

默认使用 `MockLLMClient`，不需要 key。后续接公司内 OpenAI-compatible API 时，复制 `.env.example` 为 `.env`，配置：

```text
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://your-company-api/v1
LLM_API_KEY=...
LLM_MODEL=...
```

所有策略只通过统一 LLM Client 调用模型，方便以后接入公司内 API 或其他本地模型。
