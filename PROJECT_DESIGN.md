# 银行协议/申请文档预审 POC 设计理解

## 1. 这个项目真正要证明什么

这个 POC 要证明的不是“AI 能不能读懂一份银行文档”，而是：

> 能否把银行协议/申请材料预审拆成稳定业务底座 + 可插拔方案策略，并用同一材料包比较不同路线的业务价值、配置成本和稳定性。

结合你的工作背景，这个项目应服务于“财经 AI 场景落地”和“协议场景辅助”两件事：一方面要让审核审批人直观看到 AI 的价值，另一方面必须在企业受限环境下保持可控、可解释、可审计。

## 2. POC 的产品定位

第一版建议定位为“审核关注点生成器 + 方案验证台”，而不是生产审批系统。

它应该帮助业务方回答：

- 这份材料属于什么业务场景？
- 应该匹配哪些模板？
- 相比电子流、模板 Plus 或配置区块，哪里变了？
- 哪些变化合理，哪些疑似模板偏离或风险？
- 哪些地方系统证据不足，需要人工确认？
- Demo1 和 Demo2 哪个更适合继续投入？

## 3. 核心架构判断

稳定层：

- MaterialPackage
- Scenario
- EFlow
- Template / TemplateVersion
- TemplatePlus
- SubmittedDocument
- Evidence
- CheckResult
- ReviewReport

策略层：

- BlockRuleCheckStrategy
- TemplatePlusDiffStrategy
- FullAgentReviewStrategy
- HybridReviewStrategy

公共层：

- RuleEngine
- DiffClassifier
- DocumentParser
- LLMClient
- ReportBuilder

这能避免把“区块检查”或“模板差异”任何一个方案过早写死。

## 4. Demo 优先级建议

第一优先级是 Demo2：模板 Plus 差异检查。

原因是它更贴近领导提出的“先维护标准基准，最终只看差异”的管理思路，也更容易向审核人解释：“这些是本次文档相对基准发生的变化。”

第二优先级是 Demo1：区块级检查。

它适合沉淀审核关注点，尤其适合固定模板中的高风险区域，例如操作员、权限、账号、介质、签字、证件号等。

全文 Agent 只做补充，不作为主路线。它可以用于发现漏网风险，但不能替代规则和证据链。

## 5. 模型接入设计

模型层必须保持可替换：

- 本地演示默认使用 MockLLMClient，保证无 key 也能演示。
- 公司内 API 使用 OpenAICompatibleClient，适配 `/chat/completions` 风格接口。
- 模型输出必须是 JSON，转换为统一 CheckResult。
- 模型只做局部判断：区块解释、差异解释、风险提示。
- 不让模型直接给最终审批结论。

## 6. 演示叙事

推荐演示脚本：

1. 选择样例材料包：Nigeria / UBA / User Permission Change。
2. 先跑 Demo1，展示系统能检查关键区块：操作员、权限、介质。
3. 再跑 Demo2，展示系统能识别最终文档相对模板 Plus 的差异。
4. 打开多策略对比，看两条路线命中的风险、需人工确认项、模型调用次数和配置成本。
5. 说明未来接公司 API 后，只替换 LLM Client，不改变业务架构。

## 7. 第一版取舍

第一版不做复杂 PDF 视觉级 diff，不做生产权限，不做多用户。

第一版先跑通：

- 内置样例数据；
- 两条策略；
- 统一报告；
- 可配置 LLM Client；
- 简单前端演示；
- API 文档可试。

等业务认可路线后，再补文档上传、PDF 解析、区块框选、数据库和反馈闭环。

