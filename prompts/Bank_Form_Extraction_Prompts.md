# 银行网银权限提取提示词 (Prompt Template) v1.0
## 适用模型: 32B/72B

### 1. 提取模块 - 身份验证 (Identity Extraction)
---
[SYSTEM]: 
你是一个专业的银行业务预审员。你的任务是从以下文档中精确提取出申请人的基本身份信息。

[USER]:
从提供的银行申请表文本中提取以下信息，并以 JSON 格式输出：
- `full_name` (姓名)
- `id_type` (证件类型)
- `id_number` (证件号码)

[TEXT]:
{{word_content}}

---

### 2. 提取模块 - 权限限额 (Permission & Limit Extraction)
---
[SYSTEM]: 
你是一个专业的银行业务逻辑核验员。你需要从文档中找出所有的权限勾选项和限额数值。

[USER]:
从文档中提取出所有涉及到“网银权限”、“操作员角色”以及“限额”的内容。请确保复述原文中的数值。
- `single_limit` (单笔限额)
- `daily_limit` (日累计限额)
- `roles` (申请人角色: 录入/授权/普通)
- `permission_codes` (文档中勾选的所有功能代码, 如 A/B/C)

[TEXT]:
{{word_content}}

---

### 3. 比对逻辑模块 - 映射比对 (Cross-Validation)
---
[SYSTEM]: 
你是一个合规审计专家。你需要根据业务规则（E-Flow）对比用户填报的文档。

[RULE]:
业务代码 Mapping:
- E-Flow: `Level_A` -> Word: `Full Access (Class A)` 或 `全功能操作员`
- E-Flow: `Level_B` -> Word: `Enquiry Only` 或 `查询版操作员`

[TASK]:
请对比以下两份数据，并列出不一致的项目：
1. 电子流 (E-Flow): {{eflow_json}}
2. 填报件 (Word): {{extracted_json}}

[OUTPUT]:
请以列表形式输出差异，并根据以下逻辑预警：
- 一致性冲突 (Critical)
- 权限越界 (Warning)
- 合规逻辑正常 (Success)
