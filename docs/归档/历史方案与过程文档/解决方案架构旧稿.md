# 协议类智能化文档预审方案架构

## 1. 业务全景图 (Mermaid Flowchart)

```mermaid
graph TD
    subgraph Input_Layer [输入层: 多源异构数据]
        A1[E-Flow JSON<br/>(办理意图/审批代码)]
        A2[护照/ID 图片<br/>(身份客观事实)]
        A3[银行申请书 .docx<br/>(对外报送文档)]
    end

    subgraph Extraction_Layer [提取与还原层: 结构化解析]
        B1[护照 OCR 识别]
        B2[Word 全文表格还原<br/>(保留布局坐标)]
        B3[LLM 语义提取<br/>(基于 32B/72B 针对性 Prompt)]
    end

    subgraph Validation_Layer [对齐与校验层: 一致性预审]
        C1{身份一致性校验<br/>Word vs OCR}
        C2{业务逻辑校验<br/>限额/权限/代码}
        C3{语义 Mapping<br/>代码 vs 自然语言}
    end

    subgraph Output_Layer [输出层: 自动化报告]
        D1[业务办理概览]
        D2[合规风险预审报告<br/>(红黑榜/风险提示)]
    end

    A1 --> B3
    A2 --> B1
    A3 --> B2
    B2 --> B3
    B1 --> C1
    B3 --> C1
    B3 --> C2
    B3 --> C3
    A1 --> C3
    C1 --> D2
    C2 --> D2
    C3 --> D1
```

## 2. 针对 32B/72B 模型的 Harness Engineering 策略

由于模型能力上限（32B/72B），方案采用**“分治提取”**与**“显性化校验”**策略：

| 策略维度 | 具体实施方案 |
| :--- | :--- |
| **分步提取 (Chained)** | 将“身份、限额、功能、操作员”拆分为 4 个独立的 LLM 任务，降低单次推理负荷。 |
| **结构还原 (Recon)** | 预先通过 Python-docx 还原表格，将 `Cell[1,2]` 这种空间关系显性化后再输入模型。 |
| **CoT 验证 (Logic)** | 强制模型先“复述” Word 中的原文，再与 E-Flow 的标准值进行“逐项对比”。 |

## 3. 系统输出示例

*   **业务概览**：清晰呈现该笔业务办理的是哪个银行、哪个层级的权限。
*   **一致性红黑榜**：
    *   ✅ 姓名对齐 (Word ↔ OCR ↔ E-Flow)
    *   ❌ 限额冲突 (Word: 500W > E-Flow: 100W)
    *   ⚠️ 语义待确认 (代码 Level_A 已对齐为“全功能操作员”)
