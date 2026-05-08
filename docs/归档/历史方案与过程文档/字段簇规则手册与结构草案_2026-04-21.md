# 网银权限预审：字段簇级规则清单与输出 Schema 草案

**文档定位**：在“检查逻辑重构”“Prompt 重构草案”“场景化规则矩阵”基础上，进一步形成可直接指导后续实现的字段簇级规则清单与检查输出结构草案。  
**目标**：

- 把业务规则压缩成可落地的字段簇级规则单元
- 明确每条规则的输入、检查方式、场景差异和输出形式
- 为后续 `schemas.py`、规则引擎、Prompt 输出契约改造提供基线

---

## 1. 总体设计原则

后续系统不应继续停留在：

- 一份宽泛抽取结果
- 一组宽泛 semantic checks
- 一段宽泛总结

而应逐步演进为：

1. 字段簇事实层
2. 场景动作层
3. 规则检查层
4. 报告汇总层

其中，“规则检查层”是这份文档的重点。

---

## 2. 建议的四层输出结构

### 2.1 文档事实层 `DocumentFacts`

作用：

- 表示从单份文档中抽取出的原始业务事实
- 包含原始值、标准化候选值、证据和置信度

### 2.2 场景动作层 `ScenarioContext`

作用：

- 表示这次申请到底在做什么
- 决定后续检查逻辑走哪条策略

### 2.3 规则检查层 `AuditChecks`

作用：

- 表示具体检查项
- 是最终风控判断的核心载体

### 2.4 汇总报告层 `AuditDecision`

作用：

- 面向申请人、审核人、审批人输出可用结论

---

## 3. 场景动作层 Schema 草案

建议新增统一场景对象：

```json
{
  "scenario_type": "OPEN|CANCEL|MODIFY|ATTACH",
  "action_type": "OPEN_PERMISSION|CANCEL_PERMISSION|OPEN_MEDIA|CANCEL_MEDIA|ATTACH_PERMISSION|UNKNOWN",
  "action_target": [
    {
      "target_type": "permission|media|account|user",
      "target_identifier": "Payment (Authorize) User / Token(OTP) / 76147XXXXXX8001",
      "confidence": 0.92
    }
  ],
  "action_scope": {
    "scope_mode": "full|partial|unknown",
    "details": ["authorize", "payment"]
  },
  "business_reason": "注销原有支付权限"
}
```

### 为什么要单独建这个对象

因为后续很多检查项不是只看“字段值对不对”，而是看：

- 这次是新增还是注销
- 动作作用到哪个对象
- 范围是全量还是部分

这部分如果不单独建模，开通与注销场景会长期混在一起。

---

## 4. 文档事实层 Schema 草案

建议单份文档的事实输出至少包含以下结构：

```json
{
  "source_file": "bank_app.docx",
  "source_type": "word",
  "scenario_context": {},
  "field_clusters": {
    "business_scenario": {},
    "platform": {},
    "subject": {},
    "permission": {},
    "media": {},
    "account": {}
  },
  "raw_risk_clues": [
    {
      "clue_type": "non_standard_note",
      "text": "备注：仅保留查询权限",
      "evidence_section": "表格3-备注",
      "confidence": 0.81
    }
  ]
}
```

每个字段建议都尽量支持：

- `raw_value`
- `normalized_value`
- `evidence_text`
- `evidence_section`
- `confidence`

例如：

```json
{
  "permission_scope": {
    "raw_value": "经办/复核/查询",
    "normalized_value": {
      "authorize": true,
      "payment": true,
      "query": true,
      "upload": false
    },
    "evidence_text": "操作权限：经办、复核、查询",
    "evidence_section": "表3-客户证书信息",
    "confidence": 0.94
  }
}
```

---

## 5. 检查输出 Schema 草案

这是后续最值得稳定下来的对象。

```json
{
  "check_id": "CHK-PERM-001",
  "field_group": "permission",
  "field_name": "permission_scope",
  "scenario_type": "OPEN",
  "check_mode": "compliance_review",
  "rule_code": "PERM_SCOPE_EXCESSIVE_OPEN",
  "source_a_label": "EFlow",
  "source_a_value": {
    "authorize": true,
    "payment": false,
    "query": true,
    "upload": false
  },
  "source_b_label": "Document",
  "source_b_value": {
    "authorize": true,
    "payment": true,
    "query": true,
    "upload": false
  },
  "result": "MISMATCH",
  "severity": "CRITICAL",
  "manual_confirmation_required": false,
  "reason_code": "DOC_SCOPE_EXCEEDS_EFLOW",
  "detail": "申请文档中包含支付权限，但电子流未批准支付权限，属于超配申请。",
  "evidence": [
    {
      "source": "document",
      "text": "操作权限：经办、复核、查询",
      "section": "表3-客户证书信息"
    }
  ]
}
```

---

## 6. 字段簇级规则清单

以下规则清单不是最终全量版本，而是当前最关键、最值得优先落地的核心规则。

---

## 6.1 业务场景簇规则

### 规则 BS-001：业务场景一致性

- 字段簇：`business_scenario`
- 适用场景：`OPEN` / `CANCEL`
- 检查类型：`consistency`

输入：

- E-Flow 的场景类型
- 文档中的业务动作、办理目的、操作类型

判定逻辑：

- 若系统为 `OPEN`，文档应明显表现为开通/新增/加挂
- 若系统为 `CANCEL`，文档应明显表现为注销/取消/撤销/停用

输出方向：

- `MATCH`
- `MISMATCH`
- `manual_confirmation`

推荐实现：

- Prompt 识别场景语义
- 规则层判定是否与 E-Flow 场景冲突

### 规则 BS-002：业务场景多文档交叉一致性

- 字段簇：`business_scenario`
- 适用场景：全场景
- 检查类型：`cross_doc`

输入：

- 多份申请材料中的场景描述

判定逻辑：

- 多文档对于办理目的、业务动作、对象范围的描述不得冲突

人工确认触发：

- 一份文档写“注销”
- 一份文档写“保留/变更”

---

## 6.2 平台识别簇规则

### 规则 PF-001：平台对象识别充分性

- 字段簇：`platform`
- 检查类型：`manual_confirmation`

输入：

- 银行名称
- 银行简称
- 国家/地区
- 分支银行

判定逻辑：

- 如果无法稳定归一到唯一平台对象，则不得继续给出高置信结论

推荐实现：

- Prompt 归一
- 规则层做置信度门槛

### 规则 PF-002：平台对象一致性

- 字段簇：`platform`
- 检查类型：`consistency`

判定逻辑：

- 文档识别到的平台对象应与系统 E-Flow 平台对象一致

---

## 6.3 申请人与主体簇规则

### 规则 SB-001：申请人映射一致性

- 字段簇：`subject`
- 检查类型：`consistency`

输入：

- 系统申请人
- 文档中的申请人/联系人候选

判定逻辑：

- 文档中的联系人若被识别为申请人，应与系统申请人一致

人工确认触发：

- 同时存在多个联系人/申请人候选
- 联系人与申请人角色边界不清

### 规则 SB-002：名义用户一致性

- 字段簇：`subject`
- 检查类型：`consistency`

适用场景：

- `OPEN`
- `CANCEL`

判定逻辑：

- 名义用户 / 持有人 / 当前持有人应与系统中的目标用户一致

`CANCEL` 特别关注：

- 被注销对象是否真的属于该名义用户

### 规则 SB-003：主体信息多文档交叉一致性

- 字段簇：`subject`
- 检查类型：`cross_doc`

检查对象：

- 姓名
- 工号
- 部门
- 证件信息

---

## 6.4 权限定义簇规则

### 规则 PM-001：权限四分类归一

- 字段簇：`permission`
- 检查类型：`mapping`

输入：

- 文档原始权限词句

输出：

- 标准四分类：
  - `authorize`
  - `payment`
  - `query`
  - `upload`

推荐实现：

- Prompt

### 规则 PM-002：权限范围一致性

- 字段簇：`permission`
- 适用场景：全场景
- 检查类型：`consistency`

判定逻辑：

- 将 E-Flow 和文档都归一到四大类后逐项比对

输出：

- 一致项
- 差异项
- 缺失项
- 冗余项

### 规则 PM-003：开通场景超配检查

- 字段簇：`permission`
- 适用场景：`OPEN`
- 检查类型：`compliance_review`

判定逻辑：

- 文档申请范围不得大于系统批准范围

主要风险：

- `excessive`
- `redundant`

### 规则 PM-004：注销场景少销/误销检查

- 字段簇：`permission`
- 适用场景：`CANCEL`
- 检查类型：`compliance_review`

判定逻辑：

- 文档声明注销的权限应与系统现有权限精准匹配
- 注销范围不得大于或小于系统登记范围

主要风险：

- `insufficient`
- `wrong_target`
- `conflict`

### 规则 PM-005：权限与业务场景匹配性

- 字段簇：`permission`
- 适用场景：全场景
- 检查类型：`compliance_review`

判定逻辑：

- 权限动作应与当前业务场景自洽

人工确认触发：

- 文档既像全量注销，又像部分保留
- 权限子类和权限范围存在歧义

---

## 6.5 介质簇规则

### 规则 MD-001：当前平台已有介质条件矩阵

- 字段簇：`media`
- 适用场景：`OPEN`
- 检查类型：`consistency` + `manual_confirmation`

判定矩阵：

1. 文档有介质，系统有介质，且一致 -> 通过
2. 文档有介质，系统有介质，但不一致 -> 需确认
3. 文档有介质，系统无介质 -> 需确认
4. 文档无介质，系统有介质 -> 介质遗漏风险，需确认
5. 文档无介质，系统无介质 -> 风险较低

推荐实现：

- 文档事实提取：Prompt
- 条件矩阵：规则

### 规则 MD-002：空白介质使用检查

- 字段簇：`media`
- 适用场景：`OPEN`
- 检查类型：`consistency` + `cross_doc`

判定逻辑：

- 若系统有空白介质字段值，文档应明确表述使用空白介质
- 若系统无值但文档提及空白介质，应判为异常

### 规则 MD-003：注销场景介质存在性与动作一致性

- 字段簇：`media`
- 适用场景：`CANCEL`
- 检查类型：`consistency` + `manual_confirmation`

判定逻辑：

1. 系统无介质，文档有介质 -> 需确认
2. 系统无介质，文档无介质 -> 风险较低
3. 系统有介质，文档要求注销介质 -> 核验介质对象一致性
4. 系统有介质，文档明确“不注销介质” -> 需进一步确认
5. 系统有介质，文档无介质表述 -> 介质遗漏风险

### 规则 MD-004：介质对象精准匹配

- 字段簇：`media`
- 适用场景：全场景
- 检查类型：`consistency`

检查对象：

- 介质类型
- 介质编号
- 是否实体介质

---

## 6.6 账户簇规则

### 规则 AC-001：账号精确一致性

- 字段簇：`account`
- 适用场景：全场景
- 检查类型：`consistency`

推荐实现：

- 硬规则

### 规则 AC-002：账户名称主体匹配

- 字段簇：`account`
- 适用场景：全场景
- 检查类型：`compliance_review`

判定逻辑：

- 账户中文/外文名称应与业务主体合理对应

推荐实现：

- Prompt + 规则

### 规则 AC-003：账户状态正向一致性

- 字段簇：`account`
- 适用场景：全场景
- 检查类型：`consistency`

判定逻辑：

- 文档中账户状态应与系统备案一致

### 规则 AC-004：账户状态反向风险审视

- 字段簇：`account`
- 适用场景：全场景
- 检查类型：`reverse_review`

判定逻辑：

- 若系统状态不支持当前业务动作，则即使字段看起来一致，也要提示风险

例子：

- 失效账户仍被用于开通/加挂
- 注销材料指向的账户与系统状态不匹配

### 规则 AC-005：账户多文档交叉一致性

- 字段簇：`account`
- 适用场景：全场景
- 检查类型：`cross_doc`

检查对象：

- 账号
- 账户名称
- 账户状态

---

## 7. 推荐的检查输出枚举

为了支撑比现在更精细的报告，建议保留以下结果/原因维度。

### 7.1 结果值

- `MATCH`
- `MISMATCH`
- `MISSING`
- `CONFLICT`
- `LOW_EVIDENCE`

### 7.2 严重程度

- `CRITICAL`
- `WARNING`
- `INFO`
- `PASS`

### 7.3 原因代码示例

- `DOC_SCOPE_EXCEEDS_EFLOW`
- `DOC_SCOPE_BELOW_SYSTEM_FOR_CANCEL`
- `MEDIA_PRESENT_IN_DOC_NOT_IN_SYSTEM`
- `SYSTEM_MEDIA_PRESENT_DOC_MISSING`
- `ACCOUNT_STATUS_UNSUPPORTED_FOR_ACTION`
- `CROSS_DOC_SUBJECT_CONFLICT`
- `PLATFORM_NOT_CONFIDENT`

---

## 8. 推荐的 Prompt 输出契约改造

如果后续先做小步改造，而不是一步重构全系统，建议至少让现有 Prompt 输出增加这些字段：

### 8.1 对抽取 Prompt

新增：

- `scenario_context`
- `field_clusters`
- `evidence_text`
- `evidence_section`
- `confidence`

### 8.2 对语义检查 Prompt

新增：

- `field_group`
- `field_name`
- `scenario_type`
- `check_mode`
- `manual_confirmation_required`
- `reason_code`

### 8.3 对汇总 Prompt

新增：

- `manual_confirmation_items`
- `high_priority_actions`
- `scenario_summary`

---

## 9. 后续直接可做的实现任务

如果后面要正式进入重构，这份文档可以直接转成下面这些任务：

1. 重构 `schemas.py`
   - 增加 `ScenarioContext`
   - 增加字段簇对象
   - 扩展 `CheckResult`

2. 重构 `global_document_extraction`
   - 输出字段簇和证据

3. 重构 `semantic_risk_analyzer`
   - 从宽泛语义检查改为字段簇级检查输出

4. 新增交叉校验器
   - 专门处理 `cross_doc`

5. 将稳定规则下沉
   - 介质条件矩阵
   - 空白介质条件矩阵
   - 权限四分类对照
   - 账户状态反向风险检查

---

## 10. 一句话总结

从这一层开始，后续系统应该逐步从：

> “抽一个 JSON，然后做一些松散对比”

升级成：

> “围绕字段簇、场景、对象、动作输出结构化事实，并基于规则单元产生可追溯的检查结果”

---

*文档生成日期：2026-04-21*  
*文档性质：字段簇级规则清单与输出 Schema 草案*
