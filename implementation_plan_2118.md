# 网银通道/权限预审系统深度重构计划 (V3.0)

## 一、业务理解与核心设计理念

### 1.1 "无模板化"的大模型泛化提取 (Global Generalization)
鉴于全球银行众多且表单格式千变万化，我们**放弃为每家银行制定固定映射规则**。
**策略**：赋予大模型“概念映射”能力。在 Prompt 中我们只定义核心业务概念（如：授权类权限、介质申请、开户行名称），让 LLM 作为“智能阅读者”，去自主识别不同语言（中英繁体等）、不同排版下的对应信息。它不需要确切知道这是 ICBC 的“表3-客户证书信息”，它只需要找寻文档中实质上的“权限勾选项”。

### 1.2 "单点拆解 + 全局汇总"的多文档审计流 (Multi-Doc Pipeline)
因为申请材料可能不仅包含一份申请表，还可能包含授权书、印鉴卡、多份证件。
**策略**：
1. **基准确立**：解析唯一的 E-Flow JSON，确定业务终态。
2. **逐件核对 (Item-by-Item)**：针对每一份上传的申请文档（或图片），单独与 E-Flow 基准进行比对，产出 `Doc_A_Result`, `Doc_B_Result`。
3. **全域交叉 (Cross-Validation)**：比对 Doc_A 和 Doc_B 之间的关键信息（如介质是否冲突、账号是否统一）。
4. **全局定调 (Global Summary)**：汇总所有的逐件结果和交叉结果，由大模型出具最终的《综合风险审查报告》。

### 1.3 "混合动力"的规则检查引擎 (Hybrid Engine)
**代码硬比对（绝对死线）**：
- 姓名（含中英文字符串容错清洗）。
- 证件号码、银行账号等。
**大模型语义比对（业务逻辑脑）**：
- 业务大类（开通/变更/注销）的语义一致性。
- **四大权限（授权/支付/查询/上载）的映射评估**。
- 文档中的额外/附加风险条款识别。

---

## 二、全新 E-Flow 结构定义 (JSON Schema V3)

为了承载 44 字段的核心要素，定义标准化的系统侧电子流结构：

```json
{
  "flow_id": "EF-2026-001",
  "business_info": {
    "requirement_type": "开通",          // 开通/变更/销户 (对应需求大类)
    "scenario": "权限开通",              // 业务场景
    "apply_reason": "新增业务需求"
  },
  "platform_info": {
    "platform_code": "ICBC_WEB_01",
    "platform_name": "工商银行企网平台",
    "bank_name": "中国工商银行",         // 应由大模型泛化匹配
    "bank_name_en": "ICBC",
    "country": "中国",
    "branch_name": ""
  },
  "company_info": {
    "name": "公司名称",
    "cert_number": "信用代码..."
  },
  "applicant_info": {
    "name": "申请人名",
    "department": "支付中心"
  },
  "users": [                           // ============ 核心权限户 ============
    {
      "sequence": 1,
      "user_name": "操作员A",
      "permission_sub_type": "Payment (Authorize) User",
      "permission_scopes": ["授权", "支付", "查询", "上载"],  // 关键映射词
      "media_info": {
        "existing_media": "",
        "apply_new_media": "Token(OTP)",
        "use_blank_media": false
      },
      "account_list": [
        {
          "account_number": "1234567890",
          "account_status": "In Use"
        }
      ]
    }
  ]
}
```

---

## 三、代码级实施蓝图 (M1 - M4)

### M1: 底层模型重组 (Data Models)
- **文件**: `schemas.py`
- **动作**: 根据上述 E-Flow 结构重写 `Pydantic` 模型。创建支持多文档结构的 `AuditSession` 和 `DocumentResult`。

### M2: 提示词泛化改造 (Prompts)
- **文件**: `prompts.json`
- **动作**: 
  - **泛化提取篇 (`global_document_extraction`)**: 教导 LLM 如何在一份未知银行表单中，准确锁定“四大类权限”、“介质申请类型”、“目标账号”、“操作人列表”。
  - **语义比对篇 (`semantic_risk_analyzer`)**: 传入 E-Flow 定义与单个文档提取结果，让 LLM 做语义和四大权限类型的专项校验与超限检查。
  - **总控报告篇 (`multi_doc_summary`)**: 根据多份文档的解析比对结果数组，输出含“一致性”、“交叉冲突”、“完整性”的终审报告。

### M3: 核心审核管线改写 (Pipeline Router)
- **文件**: `audit.py`
- **动作**: 重构 `_run_pipeline` 循环支持多附件。
  ```python
  def _run_pipeline(eflow: EFlowData, docs: list[File], id_imgs: list[Image]):
      1. reports = []
      2. for doc in docs:
            extracted = llm_extract(doc)
            hard_result = hard_compare(eflow, extracted)
            semantic_result = llm_compare(eflow, extracted)
            reports.append({doc: har_result + semantic_result})
      3. for img in id_imgs:
            ocr_res = ocr_extract(img)
            reports.append({img: check_id(eflow, ocr_res)})
      4. final_report = generate_global_summary(eflow, reports)
  ```

### M4: “硬比对”模块独立 (Hard Comparator)
- **文件**: 新建 `services/hard_comparator.py`
- **动作**: 承接精确比对工作，如账号去空去分隔符对比、身份证号正则匹配、统一信用代码核验。这确保不会因为 LLM 幻觉产生将明显的 1 退 1 对错问题漏判。

### M5: 测试用例全面重构 
- **动作**: 清理目前的 `test_data`，基于新版 `eflow.json` 制作至少包含以下场景的多文档用例：
  - `001_multi_doc_pass`: 一份申请表+两份证件 (完全一致)
  - `002_permission_mismatch`: 文档上勾了"资金划转"，但 EFlow 只批了"查询"。
  - `003_media_conflict`: EFlow有介质，但文档又要求新发一个 Token。

---

## 结论请求
**架构对齐完成**。该重构涉及核心路由的大规模调整和 Prompt 的全新升维。一旦确认，我将从 **M1 数据模型重构**及 **M2 Prompt 泛化** 开始动刀写代码。

请确认是否可以立即开工？
