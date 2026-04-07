---
name: gen_test_cases
description: 基于银行模板文档自动生成测试用例（填写模板空格、构造 E-Flow JSON、生成测试数据集）
---

# 银行网银权限预审 — 测试用例生成 Skill

## 概述

本技能用于基于 `inputs/bank_template/` 目录下的真实银行申请表模板，自动往模板的空表格字段中填入数据，生成可用于三方比对演示的测试用例。

## 前置条件

- Python 3.10+
- 已安装 `python-docx`（`pip install python-docx`）
- 已安装 `pywin32`（`pip install pywin32`）— 仅处理 `.doc` 文件时需要
- Windows 环境 + Microsoft Word（仅处理 `.doc` 文件时需要，用于 COM 自动化转换）

## 工作流程

### Step 1: 将 `.doc` 模板转为 `.docx`

如果模板是 `.doc` 格式，需要先通过 Word COM 自动化转换：

```python
import win32com.client as win32
import os

def convert_doc_to_docx(doc_path: str, output_dir: str) -> str:
    """将 .doc 转为 .docx，返回输出路径"""
    word = win32.gencache.EnsureDispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    fname = os.path.basename(doc_path).replace('.doc', '.docx')
    dst = os.path.join(output_dir, fname)
    
    doc = word.Documents.Open(os.path.abspath(doc_path), ReadOnly=True)
    doc.SaveAs2(os.path.abspath(dst), FileFormat=12)  # wdFormatXMLDocument = 12
    doc.Close(False)
    word.Quit()
    
    return dst
```

### Step 2: 分析模板结构

用 `python-docx` 读取模板，打印表格的行列结构，确定字段位置映射：

```python
from docx import Document

def analyze_template(docx_path: str):
    """分析模板的表格结构，输出每行每列的标签"""
    doc = Document(docx_path)
    print(f"段落数: {len(doc.paragraphs)}, 表格数: {len(doc.tables)}")
    
    for ti, table in enumerate(doc.tables):
        print(f"\n=== 表格 {ti}: {len(table.rows)} 行 x {len(table.columns)} 列 ===")
        for ri, row in enumerate(table.rows):
            cells = [c.text.strip().replace('\n', ' | ')[:50] for c in row.cells]
            print(f"  R{ri}: {cells}")
```

**关键产出**：确定一个 `field_map` 字典，映射 `(row_index, col_index) → 字段名`。

### Step 3: 定义数据填充函数

基于 Step 2 分析出的字段映射，定义填充函数：

```python
def fill_template(template_path: str, data: dict, output_path: str):
    """向模板的空格中填写数据"""
    doc = Document(template_path)
    table = doc.tables[TARGET_TABLE_INDEX]  # 根据分析结果确定
    
    field_map = {
        (0, 1): data.get("company_name", ""),
        (1, 1): data.get("cert_type", ""),
        (1, 4): data.get("cert_number", ""),
        # ... 根据模板结构补充
    }
    
    for (row_idx, col_idx), value in field_map.items():
        if value:
            cell = table.cell(row_idx, col_idx)
            for p in cell.paragraphs:
                p.text = ""
            cell.paragraphs[0].text = value
    
    doc.save(output_path)
```

### Step 4: 定义测试场景并生成

为每个测试场景准备一组数据，调用 `fill_template` 生成对应的 Word 文件，同时生成配套的 E-Flow JSON：

```python
import json

def gen_test_case(case_id, template_path, word_data, eflow_data, output_dir):
    """生成一组完整的测试用例"""
    case_dir = os.path.join(output_dir, case_id)
    os.makedirs(case_dir, exist_ok=True)
    
    # 1. 填充 Word 模板
    fill_template(template_path, word_data, os.path.join(case_dir, "bank_app.docx"))
    
    # 2. 生成 E-Flow JSON
    with open(os.path.join(case_dir, "eflow.json"), "w", encoding="utf-8") as f:
        json.dump(eflow_data, f, ensure_ascii=False, indent=2)
    
    # 3. 证件图片（待补充，可放 placeholder 或用 generate_image 生成）
    print(f"Case {case_id} generated in {case_dir}")
```

## 已验证的模板字段映射

### 建行模板 `[perfect]ccb_corp_app`

单表(17行×6列)，字段映射：

| (行,列) | 字段名 | 说明 |
|---------|--------|------|
| (0, 1) | company_name | 单位名称 |
| (1, 1) | cert_type | 证件类型 |
| (1, 4) | cert_number | 证件号码 |
| (2, 1) | address | 地址 |
| (3, 1) | postal_code | 邮政编码 |
| (3, 4) | legal_rep | 法定代表人 |
| (4, 1) | contact_name | 联系人姓名 |
| (4, 4) | contact_phone | 联系电话 |
| (5, 1) | email | E-Mail地址 |
| (5, 4) | fax | 传真号 |
| (8, 1) | account_name | 账户名称 |
| (8, 4) | bank_branch | 开户行 |
| (9, 1) | new_account | 新账号 |

### 中行模板 `[1]boc_corp_app`

10个表格，核心表格：

**表格2 (公司信息, 5行×4列)**：

| (行,列) | 字段名 | 说明 |
|---------|--------|------|
| (0, 1) | company_name | Company Name 申请单位名称 |
| (1, 1) | account_prefix | Account Number (前6位客户号) |
| (2, 1) | address | Company Address 公司地址 |
| (3, 1) | email | Email Address |
| (4, 1) | phone | Phone 电话 |
| (4, 3) | fax | Fax 传真 |

**表格8 (操作员信息, 21行×5列)**：

| (行,列) | 字段名 | 说明 |
|---------|--------|------|
| (1, 1) | operator_name | Name 操作员姓名 |
| (2, 1) | company_name | Company Name 公司名称 |
| (3, 1) | id_type | ID Type 证件类型 |
| (3, 3) | id_number | ID Number 证件号码 |
| (4, 1) | email | Email address 操作员电邮 |
| (5, 1) | fax | Fax No. 传真 |
| (5, 3) | phone | Phone No. 电话 |
| (6, 1) | mobile | Mobile 手机 |

## 注意事项

1. **合并单元格**：`python-docx` 中写入合并单元格的一个子单元格，值会自动扩散到所有合并的部分。这在 Word 里打开看是正确的，只是 python 读回时每个子单元格都会显示相同值。
2. **勾选框**：模板中的 `□` 符号需要手动替换为 `☑` 来表示选中状态。这种替换是纯文本替换。
3. **新模板适配**：遇到新的银行模板时，先运行 `analyze_template()` 打印结构，然后手动建立字段映射。
4. **`.doc` 转换依赖**：需要 Windows + MS Word 环境。如果在无 Word 的环境，需要预先批量转换好。
