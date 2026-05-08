# 网银权限申请预审：Prompt 重构草案

**定位**：基于 `网银权限申请信息对照表.xlsx` 的业务逻辑，重构当前系统的 Prompt 体系。  
**原则**：不再用一个“泛化 semantic check”去承担所有任务，而是把抽取、归一、检查、交叉、汇总拆开。

---

## 1. 当前 Prompt 体系的问题

当前系统主要使用：

- `global_document_extraction`
- `semantic_risk_analyzer`
- `multi_doc_summary`
- `id_extraction_fallback`

这些 Prompt 的问题不是不能用，而是职责过宽：

- 抽取和检查混在一起
- 字段映射与规则判定混在一起
- 单文档检查和多文档交叉混在一起
- 风险识别与风险表达混在一起

因此，继续在现有 Prompt 上叠加规则，最终会变得越来越难控。

---

## 2. 建议的新 Prompt 体系

### 2.1 Prompt A：`document_fact_extraction`

**职责**：

- 从单份申请文档中抽取尽可能完整的业务事实
- 输出结构化字段
- 同时输出原文证据
- 不做最终风险判断

**重点输出**：

- 业务场景
- 平台信息
- 申请人/联系人
- 名义用户/持有人
- 权限子类
- 权限范围原文
- 权限范围标准化候选
- 介质信息
- 账号与账户名称
- 账户状态
- 其他非标备注

**新增要求**：

- 每个关键字段尽量带 `evidence_text`
- 尽量带 `evidence_section`
- 对不确定字段给出 `confidence`

**为什么必须单列**：

因为后续很多规则判断都依赖“抽取得够全、证据够清楚”。

---

### 2.2 Prompt B：`field_mapping_normalization`

**职责**：

- 将文档原始表述映射到系统统一语义
- 建立“文档字段 -> 标准字段”的中间层

**重点处理对象**：

- 联系人 -> 申请人
- 持有人姓名 -> 名义用户
- 银行/平台表述 -> 平台对象
- 原始权限表述 -> 四大权限分类
- 介质表述 -> 标准介质类型

**建议输出结构**：

```json
{
  "normalized_fields": [
    {
      "field_group": "权限定义簇",
      "source_field": "操作权限",
      "raw_value": "经办/复核/付款/查询",
      "normalized_value": {
        "authorize": true,
        "payment": true,
        "query": true,
        "upload": false
      },
      "mapping_reason": "复核映射到授权，付款映射到支付",
      "confidence": 0.93
    }
  ]
}
```

**为什么必须单列**：

因为很多银行文档不是直接同名字段，必须先做归一，后续规则才能稳定。

---

### 2.3 Prompt C：`field_level_audit_checker`

**职责**：

- 基于 E-Flow 标准与单份文档归一化结果
- 逐字段簇执行检查
- 输出结构化检查项

**检查类型必须显式区分**：

- `consistency`
- `completeness`
- `reverse_review`
- `compliance_review`
- `manual_confirmation`

**重点检查字段簇**：

- 业务场景簇
- 申请人与主体簇
- 权限定义簇
- 介质簇
- 账户簇

**建议输出结构**：

```json
{
  "audit_checks": [
    {
      "field_group": "介质簇",
      "field_name": "当前平台已有介质",
      "check_mode": "manual_confirmation",
      "source_a_value": "Token-123",
      "source_b_value": "",
      "result": "MISMATCH",
      "severity": "WARNING",
      "manual_confirmation_required": true,
      "reason_code": "DOC_MISSING_SYSTEM_MEDIA_PRESENT",
      "detail": "系统存在已有介质，但申请文档未体现，存在介质信息遗漏风险。"
    }
  ]
}
```

**为什么必须单列**：

因为现在的 `semantic_risk_analyzer` 太宽泛，没有把“检查类型”和“字段簇”结构化输出。

---

### 2.4 Prompt D：`cross_document_audit_checker`

**职责**：

- 专门检查多份申请材料之间的冲突与矛盾
- 不再让全局总结器兼任交叉校验器

**重点校验对象**：

- 姓名 / 工号 / 部门
- 证件信息
- 账号
- 账户状态
- 空白介质
- 介质类型

**建议输出结构**：

```json
{
  "cross_doc_checks": [
    {
      "field_group": "申请人与主体簇",
      "field_name": "名义用户",
      "documents": ["申请表A", "授权书B"],
      "result": "MISMATCH",
      "severity": "CRITICAL",
      "detail": "两份申请材料中的名义用户填写不一致。"
    }
  ]
}
```

**为什么必须单列**：

Excel 中明确存在大量“多文档交叉比对”要求，而当前 `multi_doc_summary` 并不是真正的校验器。

---

### 2.5 Prompt E：`audit_report_aggregator`

**职责**：

- 汇总单文档检查结果与多文档交叉结果
- 形成最终预审结论
- 输出面向业务角色可读的总述

**应输入**：

- 字段级检查结果
- 多文档交叉结果
- 系统总体状态草案
- 需人工确认清单

**应输出**：

- 总体结论
- 总体风险级别
- 关键风险点
- 需人工确认点
- 建议优先处理事项

---

## 3. 哪些逻辑不应继续只靠 Prompt

这次重构中，需要特别避免“把所有业务规则都塞进大模型”。

### 3.1 更适合下沉成代码矩阵的逻辑

- 介质有/无四象限判断
- 空白介质条件判定
- 账号精确一致性
- 字段是否缺失
- 权限四分类结果对照
- 多文档同一字段是否冲突

### 3.2 更适合模型处理的逻辑

- 联系人是否可视为申请人
- 权限原文如何映射到四大权限
- 平台信息如何综合识别
- 账户名称与业务主体是否匹配
- 是否存在非标风险备注

---

## 4. 对当前 `prompts.json` 的最小改造策略

如果暂时不想一次性把系统改得太大，可以采用“两步走”。

### 第一步：保守增强

保留现有四个 key，但增强职责边界：

- `global_document_extraction`
  - 增加字段簇覆盖与证据输出要求
- `semantic_risk_analyzer`
  - 增加 `check_mode` / `field_group` / `manual_confirmation_required`
- `multi_doc_summary`
  - 只做总结，不再承载校验逻辑

然后新增：

- `cross_document_audit_checker`

### 第二步：正式重构

将现有 prompt 体系拆成：

- `document_fact_extraction`
- `field_mapping_normalization`
- `field_level_audit_checker`
- `cross_document_audit_checker`
- `audit_report_aggregator`

---

## 5. 推荐优先顺序

### 优先级 1

- 重写 `global_document_extraction`
- 让它输出更完整的字段簇与证据

### 优先级 2

- 重写 `semantic_risk_analyzer`
- 让它从“泛化语义检查”升级为“字段簇级审查器”

### 优先级 3

- 新增 `cross_document_audit_checker`

### 优先级 4

- 再决定是否把 `field_mapping_normalization` 独立出来

---

## 6. 当前最值得马上补进 Prompt 的业务要求

根据 Excel，当前最值得先补进 Prompt 的不是所有字段，而是这几类高价值规则：

1. 权限范围四大类归一与逐项比对
2. 当前平台已有介质的条件矩阵判断
3. 空白介质使用的条件矩阵判断
4. 名义用户/持有人/申请人之间的映射与一致性检查
5. 账号 / 账户名称 / 账户状态的单文档与多文档检查
6. 明确输出“需人工确认”而不是只给 MATCH / MISMATCH

---

## 7. 最终建议

当前阶段最合适的做法不是直接“改几个 prompt 文案”，而是：

1. 以 Excel 为基础形成统一检查逻辑模型
2. 先增强抽取与检查 Prompt 的结构化输出
3. 同时把最稳定的规则下沉成硬规则矩阵
4. 最后再让汇总报告器负责表达，而不是负责发现规则

---

## 8. 多场景兼容补充要求

在补充“权限注销”对照表后，Prompt 体系还需要满足一个新约束：

> 所有核心 Prompt 都必须具备场景感知能力，不能默认只有“权限开通”一个场景。

最小要求如下：

### 8.1 抽取 Prompt 需要增加动作对象

除了抽取字段值，还要尽量抽出：

- `scenario_type`
- `action_type`
- `action_target`
- `action_scope`

否则后续无法稳定区分：

- 开通权限
- 注销权限
- 开通介质
- 注销介质
- 仅保留权限
- 仅处理介质

### 8.2 检查 Prompt 需要显式输入场景

建议后续检查类 Prompt 至少感知：

- `OPEN`
- `CANCEL`
- `MODIFY`
- `ATTACH`

同一字段在不同场景下的审查方向不同。

### 8.3 报告 Prompt 需要输出场景化风险

报告不能只写“存在差异”，而应能表达：

- 开通场景下的超配风险
- 注销场景下的对象错配风险
- 介质保留/注销冲突风险

因此，未来 Prompt 设计应从“通用抽取器 + 通用审查器”升级为：

> 统一 Prompt 骨架 + 场景参数化输入 + 场景策略化输出。

---

*文档生成日期：2026-04-21*  
*文档性质：Prompt 重构草案，不代表最终实现版本*
