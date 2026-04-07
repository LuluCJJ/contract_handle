# 银行网银权限预审系统 (Bank Permission Pre-audit System)
## 需求规格说明书 (PRD) v1.0

### 1. 项目愿景 (Vision)
在企业内部环境下，通过大模型（32B/72B级别）实现银行权限申请文档的自动化预审。通过交叉比对“业务办理意图”、“申请人真实身份”与“银行对外报送文档”，在文档递交柜台前发现一致性偏差与潜在合规风险。

### 2. 核心业务流程 (Core Pipeline)
系统采用多源异构数据比对逻辑，流程如下：

1.  **输入模块 (Input Layer)**:
    *   **E-Flow JSON**: 承载已预审通过的办理行为、账户、权限、限额等结构化信息。
    *   **Passport Image (OCR)**: 原始护照扫描件，用于验证经办人身份信息的客观性。
    *   **Bank Application (Word)**: 填好的银行网银权限申请书（docx格式）。

2.  **提取模块 (Extraction Layer)**:
    *   **Passport OCR**: 提取姓名、证件号，输出为标准标识。
    *   **Word Form Reconstruction**: 全文表格还原。要求最大限度保留原始文档布局，识别单元格对应关系。
    *   **LLM Info Extraction**: 使用 32B/72B 针对性 Prompt，从 Word 全文及还原表格中提取权限代码、限额数值、岗位角色等语义信息。

3.  **对齐与校验模块 (Matching & Alignment Layer)**:
    *   **Semantic Mapping**: 解决 E-Flow 业务代码与银行文档表述的不一致。如：E-Flow 的 `LVL_FULL` -> Word 里的 `权限代号 A`。
    *   **Identity Consistency Check**: 检查 (Word vs OCR vs E-Flow) 三方姓名、证件号是否一致。
    *   **Permission/Limit Validation**: 检查 (Word vs E-Flow) 申请权限是否在获批范围内、限额逻辑是否正确。

4.  **最终产出 (Output Layer)**:
    *   **Overview Report**: 包括办理活动概述、业务逻辑概览。
    *   **Risk Audit Report**: 明确标出一致性冲突、合规风险点。

### 3. 技术约束 (Technical Constraints)
*   **模型选型**: 针对 32B/72B 开源模型（如 Qwen-2.5-72B 或 DeepSeek-V2）。
*   **核心方案**: 采用 Harness Engineering，通过模块化 Prompt 降级策略实现高置信度。
*   **数据格式**: E-Flow 模拟接口获取，文档支持 docx，附件支持原始图片。

---
*Created by OpenClaw Assistant*
