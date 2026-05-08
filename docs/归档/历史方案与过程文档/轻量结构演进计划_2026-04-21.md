# 网银权限预审：轻量版 Schema 演进实施稿

**适用阶段**：下周领导对标前的 demo 阶段  
**模型约束**：内部部署 Qwen 32B / 72B 量级  
**目标**：在不把系统复杂度拉得过高的前提下，补齐最关键的数据契约，使当前 Demo 能更稳定地承载“多场景、可解释、可审视”的预审逻辑。

---

## 1. 这份实施稿解决什么问题

前面几份文档已经推导出一个更完整的能力模型，但如果现在直接按完整框架重构：

- 模型输出结构会大幅变复杂
- 现有路由、前端、比对器都要跟着大改
- Qwen 32B / 72B 虽然能做复杂抽取，但过长、过细、层层嵌套的输出格式会增加不稳定性
- 对 demo 阶段来说，投入产出比不高

因此，这份文档的立场是：

> 不做“大而全 Schema 重构”，只做“对当前架构最有价值的轻量增强”。

---

## 2. 轻量版演进原则

### 原则 1

保留当前主干对象不变：

- `EFlowData`
- `DocExtractedData`
- `CheckResult`
- `DocAnalysisReport`
- `AuditReport`

### 原则 2

只补最关键的缺口，不一口气引入完整对象树。

### 原则 3

优先让模型输出变得“更可控、更可解释”，而不是“更全面”。

### 原则 4

把“场景感知”先作为最小扩展打进现有结构，而不是重起一套全新结构。

---

## 3. 轻量版最小 Schema 增强建议

## 3.1 对 `DocExtractedData` 的增强

当前 `DocExtractedData` 已有：

- `source_file`
- `source_type`
- `business_activity`
- `company`
- `persons`
- `users`
- `raw_text`

建议只新增以下字段：

```python
scenario_type: str = ""      # OPEN / CANCEL / MODIFY / ATTACH / UNKNOWN
action_type: str = ""        # OPEN_PERMISSION / CANCEL_PERMISSION / OPEN_MEDIA / CANCEL_MEDIA / UNKNOWN
action_summary: str = ""     # 对本次办理动作的简要归纳
evidence_summary: str = ""   # 文档中支持该结论的关键信息摘要
```

### 为什么只加这 4 个

因为它们足以承载：

- 当前是什么场景
- 这次在做什么动作
- 模型是如何理解本次文档的

而不会把当前数据结构改得太重。

---

## 3.2 对 `UserPermission` 的轻量增强

当前 `UserPermission` 已经基本可用，但为了兼容开通/注销场景，建议只补两个字段：

```python
action_on_permission: str = ""   # OPEN / CANCEL / KEEP / UNKNOWN
action_on_media: str = ""        # OPEN / CANCEL / KEEP / UNKNOWN
```

### 为什么不引入复杂 action object

因为 demo 阶段最重要的是：

- 看得出这是在开还是销
- 看得出动作落在哪个用户/权限/介质上

没必要马上做完整 `target_scope[]` 模型。

---

## 3.3 对 `MediaInfo` 的轻量增强

建议新增：

```python
is_physical: bool = False
needs_cancellation: bool = False
```

### 作用

- `is_physical`
  - 承接业务上“是否实体介质”的信息
- `needs_cancellation`
  - 承接注销表中“是否注销介质”的关键信息

这两个字段对 demo 的解释力很强，但实现成本不高。

---

## 3.4 对 `CheckResult` 的轻量增强

这是最值得先补的一层。

建议新增：

```python
field_group: str = ""                  # business_scenario / platform / subject / permission / media / account
scenario_type: str = ""               # OPEN / CANCEL / ...
check_mode: str = ""                  # consistency / completeness / reverse_review / cross_doc / compliance_review / manual_confirmation
manual_confirmation_required: bool = False
reason_code: str = ""
```

### 为什么这几个值最重要

因为它们能显著提升：

- 风险解释能力
- 前端分组呈现能力
- 汇总器可控性
- 后续产品化接续能力

但又不会强迫我们重写整个报告结构。

---

## 3.5 对 `AuditReport` 的轻量增强

建议只补两个字段：

```python
manual_confirmation_items: list[dict] = Field(default_factory=list)
scenario_summary: str = ""
```

### 作用

- `manual_confirmation_items`
  - 让 demo 能清楚告诉领导：哪些点系统不敢判死，需要人工把关
- `scenario_summary`
  - 用一句话说明本次是开通还是注销、核心对象是什么

---

## 4. Demo 阶段不建议现在引入的重型结构

以下内容是对的，但不建议现在就上：

- 完整 `ScenarioContext` 嵌套对象
- 全量 `field_clusters` 对象树
- 独立 `action_target[]`
- 每个字段的逐项 evidence 节点数组
- 过细的多层 JSON 输出

原因很简单：

- 增加 Qwen 输出负担
- 增加解析失败概率
- 增加现有代码改造量
- 对下周 demo 的边际价值不高

---

## 5. 对当前代码最友好的改造方式

如果后续要真正改代码，建议顺序如下：

### 第一步

只改 `schemas.py`，加上上文这些轻量字段。

### 第二步

只改 `global_document_extraction` 的输出格式，让它产出：

- `scenario_type`
- `action_type`
- `action_summary`
- `evidence_summary`

### 第三步

只改 `semantic_risk_analyzer` 的输出格式，让它产出：

- `field_group`
- `scenario_type`
- `check_mode`
- `manual_confirmation_required`
- `reason_code`

### 第四步

前端先不大改，只利用：

- `field_group`
- `manual_confirmation_required`

做更清晰的分组与提示。

---

## 6. 一句话版本

对当前 Demo 来说，最合理的 Schema 路线不是：

> 一步做成未来最终版

而是：

> 在保留现有主结构的前提下，最小化补齐“场景、动作、检查模式、人工确认”四类关键语义。

---

*文档生成日期：2026-04-21*  
*文档性质：轻量版 Schema 演进实施稿*
