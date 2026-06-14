# 银行协议/申请文档预审 POC 框架说明书：业务底座与多方案验证架构

> 建议文件名：`POC_FRAMEWORK_SPEC.md`  
> 项目代号：`bank-doc-preaudit-poc-framework`  
> 版本：v0.2  
> 目标：为 Codex / AI Coding Agent 提供一份可直接执行的项目设计说明  
> 核心原则：**业务原始逻辑稳定，解决方案路径可插拔；先抽象业务底座，再实现 Demo1 / Demo2 / Demo3 多路径验证。**

---

## 0. 给 Codex 的最高优先级指令

请先完整阅读本文档，再开始写代码。

本项目不是只实现某一个单点方案，而是要搭建一个支持多种 POC 路线的验证框架。

请严格区分两类内容：

```text
A. 业务原始逻辑 / 原始作业环节 / 原始需求
   这些是稳定的，不应被某一种技术方案绑定。

B. 解决方案路径 / 技术实现路线 / Demo 形态
   这些是可变的，需要支持并行验证、切换和扩展。
```

请不要把“区块级填写规范检查”写死为唯一方案。它只是 Demo1。

当前至少需要预留以下两条路线：

```text
Demo1：区块级填写规范检查路线
业务在模板上框选关键区块，配置填写规范、数据来源、检查规则。
系统提取最终文档中的对应区块，基于单块内容进行规则/AI 检查。

Demo2：模板 Plus 预填基准差异检查路线
业务先维护一个带固定预填内容和标准填写逻辑的模板 Plus。
系统将最终提交申请书与模板 Plus 进行比对，识别差异。
差异再被分类为：电子流变化项、合理填写项、模板偏离项、潜在风险项。
```

未来还可能有：

```text
Demo3：全文 Agent 辅助审查路线 / 混合路线 / 在线填写路线
```

因此代码架构必须是：

```text
稳定业务底座
  + 方案策略 Strategy
  + 多 Demo 可插拔执行
  + 统一报告输出
  + 统一样本与反馈闭环
```

---

## 1. 第一性原理：这个业务到底要解决什么问题

### 1.1 业务本质

银行协议/申请材料预审的本质不是“让 AI 读懂一份文档”，而是：

> 在银行申请材料正式提交或审批前，确认本次申请材料是否符合业务场景、银行模板、电子流信息、证件信息和审核关注点的要求，提前发现错填、漏填、模板偏离、关键信息不一致和潜在风险。

### 1.2 人工作业为什么能完成这件事

一线人员和审核审批人不是每次从零理解整份文档。他们通常依赖：

```text
1. 业务场景
   这次是哪个国家、哪家银行、哪个平台、办理什么事项。

2. 模板经验
   这类业务通常用哪几份模板，每份模板大概长什么样。

3. 历史样例
   上一次相似场景是怎么填的。

4. 固定规范
   哪些内容基本固定，哪些字段每次会变。

5. 审核重点
   审核人知道重点看用户、账号、权限、介质、签字、证件、关键条款等。

6. 判断边界
   哪些差异可以接受，哪些差异要退回，哪些差异需要人工确认。
```

因此系统要模仿的不是“人全文阅读”这个表象，而是人背后的工作机制：

```text
场景识别
  → 模板选择
  → 规范引用
  → 变化项核对
  → 偏离项识别
  → 风险项判断
  → 证据化输出
```

### 1.3 稳定不变的业务问题

不管采用 Demo1、Demo2 还是未来 Demo3，以下业务问题都不会变：

```text
1. 本次申请是什么业务场景？
2. 这个业务场景应该使用哪些材料/模板？
3. 电子流中本次真正变化的信息是什么？
4. 文档里哪些内容应与电子流、证件或模板规范一致？
5. 文档里哪些内容是固定规范，不应随意变化？
6. 文档里哪些新增/删除/修改可能带来风险？
7. 审核审批人需要看到哪些关注点和证据？
8. 如果系统无法判断，应该如何提示人工确认？
9. 业务如何将经验沉淀为可复用的模板、规则和样本？
```

### 1.4 可变的是解决方案路径

不同 Demo 只是解决上述问题的不同路径：

```text
Demo1 通过“区块配置”收敛检查范围。
Demo2 通过“模板 Plus 基准差异”收敛检查范围。
Demo3 可能通过“全文 Agent + 规则约束”补充复杂风险识别。
```

所以系统设计必须做到：

> **业务对象统一，检查策略可插拔，报告结构统一，验证结果可对比。**

---

## 2. 项目总目标

### 2.1 业务目标

建设一个支持银行协议/申请文档预审 POC 的验证平台，用于验证不同方案路径在真实业务场景中的可行性、稳定性、配置成本、AI 效果和审核人价值。

### 2.2 技术目标

搭建一个可扩展的 POC 框架，支持：

```text
1. 管理业务场景。
2. 管理模板和模板版本。
3. 管理材料包。
4. 接入电子流信息。
5. 上传最终申请文档和证件文档。
6. 支持多种预审策略：
   - 区块级规则检查；
   - 模板 Plus 基准差异检查；
   - 未来扩展全文 Agent / 在线填写 / 混合策略。
7. 统一输出预审报告。
8. 统一沉淀反馈、样本和评估结果。
```

### 2.3 POC 目标

POC 不是为了第一版就做生产系统，而是为了回答：

```text
1. 哪条路线业务价值最高？
2. 哪条路线配置成本最低？
3. 哪条路线技术落地难度最可控？
4. 哪条路线对 AI 依赖最合理？
5. 哪条路线更贴近申请人和审核审批人的实际作业？
6. 哪条路线适合先试点，再扩展 Top 10 银行？
```

---

## 3. 稳定业务底座：不随方案变化的对象模型

### 3.1 Material Package，材料包

一次预审任务的总对象。

```json
{
  "package_id": "PKG-20260613-0001",
  "scenario_id": "SCN-001",
  "eflow": {},
  "submitted_documents": [],
  "identity_documents": [],
  "expected_template_set": [],
  "selected_strategy": "block_rule_check | template_plus_diff | full_agent_review"
}
```

材料包是所有 Demo 的共同输入。

### 3.2 Scenario，业务场景

描述本次申请的业务上下文。

```json
{
  "scenario_id": "SCN-001",
  "country": "Nigeria",
  "bank": "UBA",
  "channel": "UBA Business Direct",
  "activity_type": "change",
  "activity_subtype": "user_permission_change",
  "special_modes": ["admin_mode"],
  "description": "尼日利亚 UBA 网银用户权限/介质变更"
}
```

业务场景用于回答：

```text
这次办什么事？
应该使用哪些模板？
应该加载哪些规则？
哪些检查项适用？
```

### 3.3 EFlow，电子流

电子流代表系统内的本次申请基准信息。

```json
{
  "eflow_id": "EF-001",
  "applicant": "Yingqi Guo",
  "company": "Huawei Technologies Company (Nigeria) Limited",
  "bank": "UBA",
  "platform": "UBA Business Direct",
  "account_name": "Huawei Technologies Company (Nigeria) Limited",
  "account_number": "102XXXX804",
  "users": [
    {
      "name": "Yingqi Guo",
      "role": "Payment User",
      "permissions": ["payment", "query"],
      "media": ["Token", "OTP"],
      "identity_doc_no": "PXXXXXX"
    }
  ],
  "change_items": ["user", "permission", "media"]
}
```

注意：电子流里真正变化的信息通常有限，主要是用户、权限、介质，以及账户、账号、平台等字段。  
这决定了系统不需要全文审查所有内容，而应重点关注变化项和偏离项。

### 3.4 Template，标准模板

银行原始制式模板或业务维护的标准模板。

```json
{
  "template_id": "TPL-UBA-TOKEN-REQUEST",
  "template_name": "UBA Token Request Form",
  "country": "Nigeria",
  "bank": "UBA",
  "channel": "UBA Business Direct",
  "document_type": "application_form",
  "status": "active"
}
```

### 3.5 Template Version，模板版本

某个模板的具体版本。

```json
{
  "template_version_id": "TPLV-001",
  "template_id": "TPL-UBA-TOKEN-REQUEST",
  "version": "v1.0",
  "file_path": "/storage/templates/uba_token_v1.pdf",
  "fingerprint": "layout-or-text-hash",
  "published_by": "business_coe",
  "published_at": "2026-06-13"
}
```

### 3.6 Template Set，模板组合

某个业务场景下应使用的一组模板。

```json
{
  "template_set_id": "TSET-001",
  "scenario_id": "SCN-001",
  "required_templates": [
    {
      "template_id": "TPL-UBA-TOKEN-REQUEST",
      "required": true,
      "role": "main_application"
    },
    {
      "template_id": "TPL-BOARD-RESOLUTION",
      "required": true,
      "role": "authorization_document"
    },
    {
      "template_id": "TPL-IDENTITY-DOC",
      "required": true,
      "role": "identity_document"
    }
  ]
}
```

### 3.7 Submitted Document，最终提交文档

申请人最终上传的文档。

```json
{
  "document_id": "DOC-001",
  "package_id": "PKG-001",
  "file_name": "filled_uba_token_request.pdf",
  "file_type": "pdf",
  "matched_template_version_id": "TPLV-001",
  "match_confidence": 0.91,
  "match_status": "matched | suspected | unmatched"
}
```

### 3.8 Evidence，证据

所有检查结论必须能追溯到证据。

```json
{
  "evidence_id": "EVD-001",
  "document_id": "DOC-001",
  "page": 1,
  "bbox": [100, 200, 400, 260],
  "text": "Payment User / Token Request",
  "source_type": "submitted_document | template | eflow | identity_doc"
}
```

### 3.9 Check Result，检查结果

统一结构，供所有 Demo 路线复用。

```json
{
  "result_id": "R-001",
  "package_id": "PKG-001",
  "strategy": "block_rule_check",
  "check_item": "operator_name_consistency",
  "status": "pass | warning | need_confirm | fail | not_applicable | not_checked",
  "risk_level": "low | medium | high",
  "summary": "用户姓名与电子流一致",
  "evidence_ids": ["EVD-001"],
  "owner": "code | config | agent | human | hybrid",
  "manual_confirm_required": false,
  "suggested_action": "无需处理"
}
```

---

## 4. 稳定业务流程：不随方案变化的作业链路

### 4.1 原始业务链路

```text
申请人发起电子流
  → 判断本次办理事项
  → 准备银行申请材料
  → 填写申请表/协议/附件
  → 上传证件或授权材料
  → 提交审核审批
  → 审核审批人核对材料
  → 发现问题则退回修正
  → 无问题则继续审批/提交银行
```

### 4.2 系统介入后的通用链路

```text
材料包创建
  → 场景识别/选择
  → 模板组合匹配
  → 文档上传
  → 模板匹配
  → 选择预审策略
  → 执行预审
  → 输出统一报告
  → 人工确认/反馈
  → 样本与规则沉淀
```

### 4.3 预审系统需要回答的通用问题

```text
1. 本次场景是否识别清楚？
2. 该场景所需模板是否齐全？
3. 上传文档是否匹配预期模板？
4. 上传文档是否疑似使用旧模板或错误模板？
5. 电子流变化字段是否正确体现在文档中？
6. 固定模板内容是否被异常修改？
7. 是否存在模板外新增内容？
8. 是否存在额外用户、额外账号、额外权限？
9. 是否存在需要审核审批人关注的风险条款？
10. 是否存在系统无法判断、需要人工确认的内容？
```

---

## 5. 多方案策略设计：Strategy Pattern

### 5.1 为什么要用策略模式

当前还处于 POC 和 Demo 验证阶段，不应提前假设唯一正确路线。

因此系统应支持：

```text
同一个材料包
  → 选择不同预审策略
  → 输出统一报告
  → 对比不同策略的效果、成本和稳定性
```

### 5.2 策略接口

建议后端定义统一策略接口：

```python
class PreauditStrategy(Protocol):
    strategy_name: str

    def run(self, package_id: str) -> ReviewReport:
        ...
```

每个 Demo 都实现这个接口。

### 5.3 当前策略清单

```text
Strategy 1：BlockRuleCheckStrategy
对应 Demo1：区块级填写规范检查。

Strategy 2：TemplatePlusDiffStrategy
对应 Demo2：模板 Plus 预填基准差异检查。

Strategy 3：FullAgentReviewStrategy
可选 Demo3：全文 Agent 辅助审查，仅用于对比，不作为主推生产路线。

Strategy 4：HybridReviewStrategy
未来方案：综合区块检查 + 模板差异 + Agent 风险扫描。
```

### 5.4 策略对比指标

每次 Demo 运行后，应记录：

```json
{
  "strategy": "template_plus_diff",
  "runtime_seconds": 12.3,
  "llm_calls": 4,
  "manual_config_cost": "medium",
  "detected_issues_count": 6,
  "false_positive_count": 1,
  "false_negative_count": 0,
  "reviewer_rating": 4,
  "notes": "差异项解释较清晰，但模板版本匹配仍需人工确认"
}
```

---

## 6. Demo1：区块级填写规范检查路线

### 6.1 方案定义

Demo1 的核心是：

> 业务在模板上框选关键区块，并为每个区块配置业务含义、填写规范、数据来源、检查规则和风险提示。系统从最终提交文档中定位这些区块，提取内容后进行规则检查和局部 AI 判断。

### 6.2 适用场景

适合：

```text
1. 模板结构相对稳定。
2. 关键检查区域明确。
3. 审核关注点可以被业务框选和描述。
4. 不需要整篇全文理解。
5. 业务愿意维护模板区块规则。
```

### 6.3 核心对象

#### Template Block，模板区块

```json
{
  "block_id": "BLK-001",
  "template_version_id": "TPLV-001",
  "block_name": "操作员信息区",
  "block_type": "variable_field",
  "business_meaning": "记录本次申请的网银操作员",
  "location": {
    "page": 1,
    "bbox": [100, 200, 400, 280],
    "anchor_text": "Operator Name"
  }
}
```

#### Block Rule，区块规则

```json
{
  "rule_id": "RULE-001",
  "block_id": "BLK-001",
  "data_source": ["eflow.users.name", "identity_doc.name"],
  "fill_instruction": "应填写电子流中的操作员姓名，与证件姓名保持一致。",
  "check_type": "normalized_match",
  "ai_required": false,
  "manual_confirm_condition": "存在英文名顺序差异或缩写时需人工确认"
}
```

### 6.4 处理流程

```text
选择材料包
  → 确认业务场景
  → 匹配模板版本
  → 加载模板区块配置
  → 在最终文档中定位区块
  → 提取区块内容
  → 执行确定性规则检查
  → 必要时调用 Agent 做局部语义判断
  → 汇总区块结果
  → 输出预审报告
```

### 6.5 Agent 输入

```json
{
  "scenario": {},
  "block": {},
  "fill_instruction": "",
  "extracted_content": "",
  "eflow_context": {},
  "rule_context": {},
  "system_check_results": []
}
```

### 6.6 优势

```text
1. 检查范围收敛，AI 上下文小。
2. 业务可以明确告诉系统“这里要看什么”。
3. 结果容易解释。
4. 适合做审核关注点提示。
5. 适合沉淀业务知识。
```

### 6.7 挑战

```text
1. 初始配置成本较高。
2. 区块定位稳定性是技术难点。
3. 模板变更后区块配置可能失效。
4. 业务规则配置质量直接影响检查效果。
```

### 6.8 MVP 实现建议

```text
第一版只支持：
- 人工选择模板；
- PDF 预览框选；
- 保存区块坐标和锚点；
- 提取区块文本；
- 配置 3-5 类基础规则；
- 调用 Mock Agent 做语义判断；
- 输出报告。
```

---

## 7. Demo2：模板 Plus 预填基准差异检查路线

### 7.1 方案定义

Demo2 的核心是：

> 业务先维护一个“模板 Plus”，即在空白银行模板基础上预置固定内容、标准填写内容和规范逻辑。系统将最终提交的申请书与模板 Plus 进行比对，识别所有差异，再将差异分类为电子流变化项、合理填写项、模板偏离项、潜在风险项，并进行进一步预审。

这是领导提出的关键思路：

```text
不要让 AI 从头审全文。
先由业务把应该固定的内容、应该预填的内容、标准填写逻辑沉淀到模板 Plus。
最终文档只需要跟这个基准模板比差异。
差异才是检查重点。
```

### 7.2 适用场景

适合：

```text
1. 固定填写内容较多。
2. 业务实际常参考上一单或标准样例填写。
3. 每次变化字段相对有限。
4. 需要判断最终文档相对标准模板发生了哪些变化。
5. 领导关注“初始化复杂，但后续一劳永逸”的方案。
```

### 7.3 核心对象

#### Template Plus，模板 Plus

模板 Plus 不是空白模板，而是带有预填内容和标准规范的基准模板。

```json
{
  "template_plus_id": "TPLP-001",
  "template_version_id": "TPLV-001",
  "plus_version": "v1.0",
  "file_path": "/storage/template_plus/uba_token_plus_v1.pdf",
  "description": "已预填固定公司信息、固定声明、标准勾选逻辑的 UBA Token 申请模板",
  "fixed_content_policy": "最终文档不应删除或异常修改固定内容",
  "variable_slots": [
    "operator_name",
    "operator_id",
    "media_type",
    "application_date"
  ]
}
```

#### Expected Content，预期内容

模板 Plus 中的内容可以分类：

```json
{
  "expected_content_id": "EXP-001",
  "template_plus_id": "TPLP-001",
  "content_type": "fixed | variable | optional | instruction_only",
  "business_meaning": "公司名称",
  "expected_value": "Huawei Technologies Company (Nigeria) Limited",
  "source": "template_fixed",
  "check_policy": "must_not_change"
}
```

#### Document Diff，文档差异

```json
{
  "diff_id": "DIFF-001",
  "package_id": "PKG-001",
  "template_plus_id": "TPLP-001",
  "diff_type": "added | deleted | modified",
  "location": {},
  "baseline_text": "Huawei Technologies Company (Nigeria) Limited",
  "submitted_text": "Huawei Technologies Nigeria Ltd.",
  "classification": "eflow_change | acceptable_fill | template_deviation | potential_risk | unknown",
  "evidence_ids": []
}
```

### 7.4 差异分类逻辑

模板 Plus 与最终文档比对后，差异不能直接判错，需要分类。

| 差异类型 | 含义 | 处理方式 |
|---|---|---|
| eflow_change | 由电子流变化字段导致的合理差异 | 与电子流比对 |
| acceptable_fill | 申请人根据规范填写的合理内容 | 通过或提示 |
| template_deviation | 固定内容被删改、模板结构偏离 | 风险提示 |
| potential_risk | 新增条款、额外权限、额外用户等 | Agent 解释 + 人工确认 |
| unknown | 系统无法判断 | 人工确认 |

### 7.5 处理流程

```text
选择材料包
  → 确认业务场景
  → 匹配模板 Plus
  → 解析模板 Plus 与最终文档
  → 执行文档级差异比对
  → 生成差异清单
  → 对差异进行分类
  → 对电子流变化项做一致性检查
  → 对模板偏离项做风险提示
  → 对潜在风险项调用 Agent 解释
  → 输出预审报告
```

### 7.6 Demo2 与 Demo1 的区别

| 项目 | Demo1：区块级规则 | Demo2：模板 Plus 差异 |
|---|---|---|
| 业务配置对象 | 区块和规则 | 预填基准模板和差异政策 |
| 检查入口 | 每个配置区块 | 最终文档相对模板 Plus 的差异 |
| AI 上下文 | 单个区块 | 单个差异项/差异片段 |
| 适合场景 | 审核关注点明确 | 固定内容多、变化项少 |
| 技术难点 | 区块定位 | 文档差异比对和差异分类 |
| 业务价值 | 告诉审核人看哪里 | 告诉审核人哪里变了 |

### 7.7 优势

```text
1. 更符合“业务预填固定模板，一次配置长期复用”的管理思路。
2. 检查重点天然收敛到“差异”。
3. 能更好识别模板被改动、固定内容被删除、新增异常内容。
4. 对审核审批人直观：只看变化和异常。
```

### 7.8 挑战

```text
1. 需要业务先维护高质量模板 Plus。
2. 不同格式文档的差异比对难度较高。
3. 文档版式变化可能导致 diff 噪音。
4. 差异分类需要规则和 AI 协同。
```

### 7.9 MVP 实现建议

第一版不要做复杂视觉级 diff。先做文本结构化 diff：

```text
1. 解析模板 Plus 文本和最终文档文本。
2. 按段落/表格单元格/关键锚点做对齐。
3. 生成 added/deleted/modified 差异。
4. 用规则分类：
   - 与电子流字段匹配 → eflow_change；
   - 固定内容变化 → template_deviation；
   - 新增非预期内容 → potential_risk；
   - 无法判断 → unknown。
5. 对 potential_risk 和 unknown 调用 Agent 解释。
```

---

## 8. Demo3：全文 Agent / 混合路线预留

### 8.1 为什么还要保留 Demo3

虽然主推不应是全文 Agent，但 POC 阶段可以保留它用于：

```text
1. 和 Demo1/Demo2 做效果对比。
2. 发现模板/区块/差异路线覆盖不到的风险。
3. 为未来混合策略提供补充能力。
```

### 8.2 Demo3 不应作为默认路线

全文 Agent 的问题：

```text
1. 上下文大。
2. 稳定性不如局部检查。
3. 证据定位难。
4. 成本较高。
5. 输出容易自由发挥。
```

### 8.3 Demo3 应受约束

如果实现 Demo3，必须：

```text
1. 输入结构化文档摘要，而不是原始全文。
2. 输出统一 CheckResult。
3. 必须绑定证据。
4. 只能输出风险提示和人工确认项，不能输出最终审批结论。
```

---

## 9. 公共能力模块

无论 Demo1、Demo2、Demo3，以下能力都应复用。

### 9.1 场景管理

```text
国家
银行
通道
平台
业务活动
活动细类
特殊模式
模板组合
```

### 9.2 模板库

```text
模板上传
模板版本管理
模板适用范围
模板启停用
模板变更记录
```

### 9.3 材料包管理

```text
电子流录入
申请文档上传
证件文档上传
模板选择
策略选择
预审执行
```

### 9.4 文档解析

```text
PDF 解析
Word 解析
Excel 解析
文本抽取
表格抽取
坐标/页码提取
段落结构化
```

### 9.5 证据体系

所有报告项必须可追溯：

```text
来自哪份文档
第几页
哪个区块
哪段原文
对应哪条规则
```

### 9.6 规则引擎

支持：

```text
not_empty
exact_match
normalized_match
date_valid
mask_account_match
fixed_content_unchanged
expected_checkbox
diff_classification
semantic_check_required
```

### 9.7 Agent 调用层

统一封装：

```text
MockLLMClient
OpenAICompatibleClient
LocalModelClient(optional)
```

Agent 输出必须统一 JSON Schema。

### 9.8 统一报告

不同 Demo 输出统一报告结构：

```text
材料包摘要
场景信息
模板匹配结果
策略执行结果
变化项
偏离项
风险项
人工确认项
证据索引
反馈入口
```

---

## 10. 推荐系统架构

### 10.1 总体架构

```text
前端
  - 场景管理
  - 模板管理
  - 区块配置
  - 模板 Plus 管理
  - 材料包上传
  - 策略选择
  - 报告查看

后端 API
  - 场景服务
  - 模板服务
  - 材料包服务
  - 文档解析服务
  - 策略执行服务
  - 规则引擎服务
  - Agent 服务
  - 报告服务
  - 反馈服务

策略层
  - BlockRuleCheckStrategy
  - TemplatePlusDiffStrategy
  - FullAgentReviewStrategy
  - HybridReviewStrategy

基础设施
  - 数据库
  - 文件存储
  - LLM Client
  - 日志与运行记录
```

### 10.2 推荐 MVP 技术栈

```text
后端：Python + FastAPI + Pydantic
数据库：SQLite，后续可替换 PostgreSQL
前端：React / Next.js + TypeScript
PDF 解析：PyMuPDF
PDF 预览：PDF.js
Word 解析：python-docx
Excel 解析：openpyxl
AI 调用：MockLLMClient + OpenAICompatibleClient
```

### 10.3 为什么 MVP 这样选

```text
1. Codex 容易快速生成。
2. Python 适合文档解析和 AI 编排。
3. FastAPI 适合定义清晰 API 和 Schema。
4. SQLite 便于本地演示。
5. MockLLMClient 能保证无模型 Key 时也能跑通。
```

---

## 11. 推荐代码目录结构

```text
bank-doc-preaudit-poc/
  README.md
  POC_FRAMEWORK_SPEC.md
  .env.example

  backend/
    app/
      main.py

      core/
        config.py
        logging.py
        enums.py

      models/
        scenario.py
        template.py
        template_plus.py
        material_package.py
        document.py
        evidence.py
        check_result.py
        report.py
        feedback.py

      schemas/
        scenario.py
        template.py
        template_plus.py
        material_package.py
        strategy.py
        report.py

      api/
        routes_scenarios.py
        routes_templates.py
        routes_template_blocks.py
        routes_template_plus.py
        routes_packages.py
        routes_strategies.py
        routes_reports.py
        routes_feedback.py

      services/
        scenario_service.py
        template_service.py
        template_block_service.py
        template_plus_service.py
        material_package_service.py
        document_parser_service.py
        template_match_service.py
        block_locator_service.py
        document_diff_service.py
        rule_engine_service.py
        strategy_runner_service.py
        report_service.py
        feedback_service.py

      strategies/
        base.py
        block_rule_check_strategy.py
        template_plus_diff_strategy.py
        full_agent_review_strategy.py
        hybrid_review_strategy.py

      llm/
        base.py
        mock_client.py
        openai_compatible_client.py
        prompts.py
        schemas.py

      rules/
        builtin_rules.py
        normalization.py
        diff_classifier.py

      storage/
        file_store.py

      db/
        session.py
        init_db.py

    tests/
      test_block_rule_strategy.py
      test_template_plus_diff_strategy.py
      test_rule_engine.py
      test_report_service.py

  frontend/
    src/
      app/
      components/
        ScenarioManager.tsx
        TemplateManager.tsx
        TemplateViewer.tsx
        BlockAnnotator.tsx
        TemplatePlusManager.tsx
        PackageUploader.tsx
        StrategySelector.tsx
        ReportViewer.tsx
      api/
        client.ts
      types/
        scenario.ts
        template.ts
        templatePlus.ts
        materialPackage.ts
        report.ts
```

---

## 12. 开发规范

### 12.1 架构规范

1. 不允许把某个 Demo 路线写死到核心业务模型里。
2. 所有预审逻辑必须通过 Strategy 执行。
3. 所有策略必须输出统一 ReviewReport。
4. 所有检查项必须输出统一 CheckResult。
5. 所有证据必须通过 Evidence 对象记录。
6. Agent 调用必须通过 LLMClient 抽象。
7. 不允许 Agent 输出自由 Markdown 作为最终结果。
8. 不允许没有证据的风险结论进入报告。

### 12.2 代码职责边界

#### API 层

只负责：

```text
接收请求
校验参数
调用 service
返回 response
```

不写业务逻辑。

#### Service 层

负责：

```text
数据处理
业务编排
状态管理
调用策略
```

#### Strategy 层

负责：

```text
具体预审路线执行
```

#### Rule Engine

负责：

```text
确定性检查
规则检查
差异分类初筛
```

#### Agent Service

负责：

```text
构造局部上下文
调用 LLM
校验 JSON 输出
转换为 CheckResult
```

### 12.3 状态枚举

```python
class CheckStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    NEED_CONFIRM = "need_confirm"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    NOT_CHECKED = "not_checked"
```

```python
class StrategyName(str, Enum):
    BLOCK_RULE_CHECK = "block_rule_check"
    TEMPLATE_PLUS_DIFF = "template_plus_diff"
    FULL_AGENT_REVIEW = "full_agent_review"
    HYBRID_REVIEW = "hybrid_review"
```

```python
class DiffClassification(str, Enum):
    EFLOW_CHANGE = "eflow_change"
    ACCEPTABLE_FILL = "acceptable_fill"
    TEMPLATE_DEVIATION = "template_deviation"
    POTENTIAL_RISK = "potential_risk"
    UNKNOWN = "unknown"
```

---

## 13. API 草案

### 13.1 策略执行 API

```http
POST /api/packages/{package_id}/run-preaudit
```

请求：

```json
{
  "strategy": "block_rule_check",
  "options": {
    "use_mock_llm": true
  }
}
```

响应：

```json
{
  "report_id": "RPT-001",
  "strategy": "block_rule_check",
  "status": "completed"
}
```

### 13.2 同一材料包多策略对比 API

```http
POST /api/packages/{package_id}/run-comparison
```

请求：

```json
{
  "strategies": [
    "block_rule_check",
    "template_plus_diff",
    "full_agent_review"
  ]
}
```

响应：

```json
{
  "package_id": "PKG-001",
  "reports": [
    {
      "strategy": "block_rule_check",
      "report_id": "RPT-001"
    },
    {
      "strategy": "template_plus_diff",
      "report_id": "RPT-002"
    }
  ]
}
```

### 13.3 模板 Plus API

```http
POST   /api/template-plus
GET    /api/template-plus
GET    /api/template-plus/{template_plus_id}
POST   /api/template-plus/{template_plus_id}/expected-contents
POST   /api/template-plus/{template_plus_id}/diff-with-document
```

---

## 14. 核心伪代码

### 14.1 Strategy Runner

```python
def run_preaudit(package_id: str, strategy_name: StrategyName) -> ReviewReport:
    package = package_service.get_package(package_id)

    strategy = strategy_registry.get(strategy_name)

    report = strategy.run(package)

    report_service.save(report)

    return report
```

### 14.2 Demo1 Strategy

```python
class BlockRuleCheckStrategy:
    strategy_name = "block_rule_check"

    def run(self, package: MaterialPackage) -> ReviewReport:
        scenario = scenario_service.get(package.scenario_id)
        template_versions = template_service.get_expected_templates(scenario)

        results = []

        for template_version in template_versions:
            submitted_doc = template_match_service.get_matched_doc(package, template_version)

            if not submitted_doc:
                results.append(CheckResult.template_missing(template_version))
                continue

            blocks = template_block_service.get_blocks(template_version.id)

            for block in blocks:
                extracted = block_locator_service.extract(submitted_doc, block)

                rule_results = rule_engine_service.run_block_rules(
                    package=package,
                    block=block,
                    extracted=extracted,
                )
                results.extend(rule_results)

                if block.requires_agent or any(r.requires_agent for r in rule_results):
                    agent_result = agent_service.check_block(
                        package=package,
                        scenario=scenario,
                        block=block,
                        extracted=extracted,
                        rule_results=rule_results,
                    )
                    results.append(agent_result)

        return report_service.build_report(package, results, self.strategy_name)
```

### 14.3 Demo2 Strategy

```python
class TemplatePlusDiffStrategy:
    strategy_name = "template_plus_diff"

    def run(self, package: MaterialPackage) -> ReviewReport:
        scenario = scenario_service.get(package.scenario_id)
        template_plus_list = template_plus_service.get_expected_template_plus(scenario)

        results = []

        for template_plus in template_plus_list:
            submitted_doc = template_match_service.get_matched_doc(
                package, template_plus.template_version_id
            )

            if not submitted_doc:
                results.append(CheckResult.template_missing(template_plus))
                continue

            diffs = document_diff_service.diff(
                baseline_template_plus=template_plus,
                submitted_document=submitted_doc,
            )

            for diff in diffs:
                classification = diff_classifier.classify(
                    diff=diff,
                    package=package,
                    template_plus=template_plus,
                )

                if classification in ["potential_risk", "unknown"]:
                    agent_result = agent_service.explain_diff(
                        package=package,
                        diff=diff,
                        classification=classification,
                    )
                    results.append(agent_result)
                else:
                    results.append(
                        check_result_service.from_diff(diff, classification)
                    )

        return report_service.build_report(package, results, self.strategy_name)
```

---

## 15. Agent 设计

### 15.1 Agent 角色

Agent 不是审批人，也不是全文审核人。  
Agent 是局部上下文下的业务判断助手。

### 15.2 Demo1 Agent：区块检查 Prompt

```text
你是银行申请材料预审助手。
你只检查当前输入的模板区块，不要扩大到全文。
请根据业务场景、区块含义、填写规范、电子流字段、区块提取内容和系统检查结果，判断当前区块是否符合要求。
如果证据不足，请输出 need_confirm。
输出必须是 JSON。
```

### 15.3 Demo2 Agent：差异解释 Prompt

```text
你是银行申请材料差异解释助手。
系统已经将最终提交文档与模板 Plus 进行比对，并识别出一个差异项。
请判断该差异更可能属于：
1. 电子流变化项；
2. 合理填写项；
3. 模板偏离项；
4. 潜在风险项；
5. 无法判断，需人工确认。

你只能基于输入的差异片段、模板 Plus 规范、电子流字段和证据判断。
不要输出最终审批结论。
输出必须是 JSON。
```

### 15.4 Agent 统一输出 Schema

```json
{
  "status": "pass|warning|need_confirm|fail|not_applicable",
  "risk_level": "low|medium|high",
  "classification": "optional",
  "summary": "简短结论",
  "reasoning_brief": "业务可读理由，不要写模型思考过程",
  "evidence_refs": [],
  "manual_confirm_required": false,
  "manual_confirm_question": "",
  "suggested_action": ""
}
```

---

## 16. 验证样例设计

### 16.1 同一个材料包跑多个 Demo

POC 需要支持同一个材料包分别跑 Demo1 和 Demo2。

例如：

```text
材料包：Nigeria / UBA / User Permission Change
文档：Token Request Form + Board Resolution + Identity Document
电子流：用户 Yingqi Guo，权限 payment/query，介质 Token
```

运行：

```text
Run Strategy A: block_rule_check
Run Strategy B: template_plus_diff
Compare Reports
```

### 16.2 需要比较的问题

```text
1. Demo1 是否能准确检查配置区块？
2. Demo2 是否能准确识别模板差异？
3. 哪个方案配置成本更低？
4. 哪个方案对文档格式更敏感？
5. 哪个方案更容易给审核审批人解释？
6. 哪个方案更适合扩展到 Top 10 银行？
```

---

## 17. 方案选择评估框架

每个方案都按以下维度评估。

| 维度 | 说明 |
|---|---|
| 业务贴合度 | 是否贴近申请人和审核人的真实作业 |
| 初始配置成本 | 业务需要配置多少模板、区块、规则 |
| 维护成本 | 模板变化后维护是否方便 |
| 技术可行性 | 文档解析、定位、差异比对是否可控 |
| AI 依赖度 | 是否过度依赖 AI 自由理解 |
| 稳定性 | 同样输入是否能稳定输出相似结果 |
| 可解释性 | 报告是否能绑定证据和规则 |
| 扩展性 | 是否能扩展到 Top 10 银行 |
| 用户价值 | 是否能减少返工、聚焦审核重点 |
| 工程复杂度 | MVP 是否能较快做出来 |

---

## 18. 开发任务拆解

### Task 1：创建项目骨架

创建前后端项目，完成基础启动。

### Task 2：实现稳定业务底座模型

实现：

```text
Scenario
Template
TemplateVersion
TemplatePlus
MaterialPackage
UploadedDocument
Evidence
CheckResult
ReviewReport
Feedback
```

### Task 3：实现 Strategy 框架

实现：

```text
PreauditStrategy
StrategyRegistry
StrategyRunnerService
BlockRuleCheckStrategy stub
TemplatePlusDiffStrategy stub
FullAgentReviewStrategy stub
```

### Task 4：实现模板库与材料包上传

支持上传模板、上传最终文档、创建材料包。

### Task 5：实现 Demo1 基础闭环

支持：

```text
模板区块配置
区块内容提取
基础规则检查
Mock Agent 区块检查
报告输出
```

### Task 6：实现 Demo2 基础闭环

支持：

```text
模板 Plus 上传
最终文档与模板 Plus 文本 diff
差异分类
Mock Agent 差异解释
报告输出
```

### Task 7：实现多策略对比

同一个材料包可运行多个策略并对比报告。

### Task 8：实现反馈与评估

支持用户对每个报告项标记：

```text
正确
误报
漏报
需规则更新
需模板更新
```

---

## 19. MVP 成功标准

MVP 成功不是“AI 全部审对”，而是：

```text
1. 能清晰分离业务底座和方案策略。
2. 同一个材料包能跑 Demo1 和 Demo2。
3. Demo1 能展示区块级规则检查价值。
4. Demo2 能展示模板 Plus 差异检查价值。
5. 两个 Demo 都输出统一报告结构。
6. 报告能告诉审核人：哪里变化、哪里偏离、哪里需确认。
7. 用户能反馈哪些结果有用、哪些误报、哪些漏报。
8. 后续可以继续新增 Demo3，而不推翻架构。
```

---

## 20. Codex 第一条启动提示词

```text
请阅读 `POC_FRAMEWORK_SPEC.md`，实现一个“银行协议/申请文档预审 POC 框架”。

最高优先级要求：
1. 请先搭建稳定业务底座，不要把任一方案写死为唯一实现。
2. 预审能力必须通过 Strategy Pattern 实现。
3. 当前至少预留两个策略：
   - block_rule_check：区块级填写规范检查；
   - template_plus_diff：模板 Plus 预填基准差异检查。
4. 同一个材料包必须能够选择不同策略运行，并输出统一 ReviewReport。
5. 所有检查结果必须结构化为 CheckResult，且必须支持 Evidence。
6. Agent 调用必须通过 LLMClient 抽象，并默认支持 MockLLMClient。
7. 不要实现 AI 全文自由审查作为主路线。
8. 第一版先实现本地可运行 MVP，不追求生产级权限、并发和全格式兼容。
```

---

## 21. 最终总结

本项目的设计重点是：

> **先把稳定的业务原始逻辑抽象出来，再把不同解决方案作为可插拔策略进行验证。**

业务问题不变：

```text
识别场景、匹配模板、检查电子流变化项、发现模板偏离项、提示风险项、输出审核关注点。
```

方案路径可变：

```text
Demo1：通过区块级配置来检查。
Demo2：通过模板 Plus 差异来检查。
Demo3：未来通过全文 Agent 或混合策略补充。
```

这样做的价值是：

```text
1. 不把 POC 锁死在单一路线。
2. 能支持领导提出的不同思路。
3. 能用真实样本比较不同方案优劣。
4. 能逐步收敛出最适合生产落地的路径。
5. 能让 Codex 在清晰边界下快速开发 Demo。
```
