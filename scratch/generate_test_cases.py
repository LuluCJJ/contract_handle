# -*- coding: utf-8 -*-
"""
批量生成测试用例：基于银行模板填充数据 + 生成配套 eflow.json
"""
import os
import sys
import json
import shutil
from pathlib import Path

sys.path.append(os.getcwd())

from docx import Document

PROJECT_ROOT = Path(r"d:\AI\project\contract_handle")
TEMPLATE_DIR = PROJECT_ROOT / "inputs" / "bank_template"
CONVERTED_DIR = PROJECT_ROOT / "_converted_docx"
TEST_DATA_DIR = PROJECT_ROOT / "test_data"

# ---- 找到可用的证件图片 ----
EXISTING_ID_IMGS = []
for case_dir in sorted(TEST_DATA_DIR.iterdir()):
    if case_dir.is_dir():
        for f in case_dir.iterdir():
            if f.suffix in (".jpg", ".jpeg", ".png"):
                EXISTING_ID_IMGS.append(str(f))
                break

print(f"Found {len(EXISTING_ID_IMGS)} existing ID images")
ID_IMG_1 = EXISTING_ID_IMGS[0] if EXISTING_ID_IMGS else None
ID_IMG_2 = EXISTING_ID_IMGS[1] if len(EXISTING_ID_IMGS) > 1 else ID_IMG_1


def fill_docx_cells(template_path, field_map, output_path):
    """
    Fill cells in a docx template using (table_idx, row_idx, col_idx) -> value mapping.
    """
    doc = Document(template_path)
    for (ti, ri, ci), value in field_map.items():
        if value and ti < len(doc.tables):
            table = doc.tables[ti]
            if ri < len(table.rows):
                row = table.rows[ri]
                if ci < len(row.cells):
                    cell = row.cells[ci]
                    for p in cell.paragraphs:
                        p.text = ""
                    cell.paragraphs[0].text = str(value)
    doc.save(output_path)
    print(f"  Saved filled doc: {output_path}")


def create_case(case_id, description, template_src, field_map, eflow_data, id_img_src):
    """Create a complete test case directory."""
    case_dir = TEST_DATA_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    
    # README
    readme = case_dir / "README.md"
    readme.write_text(f"# {case_id}\n\n**场景**: {description}\n", encoding="utf-8")
    
    # Bank app document
    src_ext = Path(template_src).suffix.lower()
    if src_ext == ".pdf":
        # PDF: copy as-is (we can't easily fill PDFs programmatically)
        dst = case_dir / f"bank_app.pdf"
        shutil.copy2(template_src, dst)
        print(f"  Copied PDF: {dst}")
    else:
        # DOCX: fill template
        dst = case_dir / "bank_app.docx"
        fill_docx_cells(template_src, field_map, str(dst))
    
    # E-Flow JSON
    eflow_path = case_dir / "eflow.json"
    eflow_path.write_text(json.dumps(eflow_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved eflow: {eflow_path}")
    
    # ID image
    if id_img_src and Path(id_img_src).exists():
        dst_img = case_dir / f"id_document{Path(id_img_src).suffix}"
        shutil.copy2(id_img_src, dst_img)
        print(f"  Copied ID image: {dst_img}")
    
    print(f"[OK] Case {case_id} created.")


# ======================================================================
# CASE DEFINITIONS
# ======================================================================

# --- Paths to converted templates ---
boc_france = str(CONVERTED_DIR / "[1]boc_corp_app.docx")
boc_hk1 = str(TEMPLATE_DIR / "中国银行香港表1.docx")
icbc_cert = str(CONVERTED_DIR / "ICBC企业客户证书及分支机构信息表.docx")
boc_domestic = str(CONVERTED_DIR / "中国银行股份有限公司网上银行服务申请变更表(表1.企业客户基本信息表).docx")
ccb_template = str(CONVERTED_DIR / "[perfect]ccb_corp_app.docx")
boc_hk2 = str(CONVERTED_DIR / "中国银行香港表2.docx")

# ======================================================================
# Case 010: BOC France e-Corp - PASS
# Template: [1]boc_corp_app.docx (Table 2=company 5x4, Table 8=operator 21x5)
# ======================================================================
print("\n--- Generating case_010 ---")
create_case(
    case_id="case_010_boc_france_pass",
    description="[正例] BOC法国 e-Corp 企业网银 - 中英双语表单，信息完全一致",
    template_src=boc_france,
    field_map={
        # Table 2: Company Info (5x4)
        (2, 0, 1): "Global Trading Solutions SARL",
        (2, 1, 1): "880012",
        (2, 2, 1): "15 Rue de la Paix, 75002 Paris, France",
        (2, 3, 1): "contact@globaltrading.fr",
        (2, 4, 1): "+33 1 42 00 1234",
        (2, 4, 3): "+33 1 42 00 1235",
        # Table 8: Operator Info (21x5)
        (8, 1, 1): "Li Wei",
        (8, 2, 1): "Global Trading Solutions SARL",
        (8, 3, 1): "Passport",
        (8, 3, 3): "E12345678",
        (8, 4, 1): "liwei@globaltrading.fr",
        (8, 6, 1): "+33 6 12 34 56 78",
    },
    eflow_data={
        "flow_id": "EF2026041001",
        "company": {
            "name": "Global Trading Solutions SARL",
            "name_en": "Global Trading Solutions SARL",
            "cert_type": "Business Registration",
            "cert_number": "RCS Paris B 880 012 345"
        },
        "account": {
            "bank_name": "Bank of China Paris Branch",
            "branch": "Paris Main",
            "account_number": "FR7630004000031234567890143"
        },
        "operator": {
            "name": "Li Wei",
            "id_type": "Passport",
            "id_number": "E12345678"
        },
        "handler": {
            "name": "Li Wei",
            "id_type": "Passport",
            "id_number": "E12345678"
        },
        "activity": "Apply for e-Corp Internet Banking Service",
        "permissions": {"level": "Level_A", "single_limit": 100000, "daily_limit": 500000},
        "apply_date": "2026-04-10"
    },
    id_img_src=ID_IMG_1
)

# ======================================================================
# Case 011: BOC France - MISMATCH (ID number different)
# ======================================================================
print("\n--- Generating case_011 ---")
create_case(
    case_id="case_011_boc_france_mismatch",
    description="[负例] BOC法国 - 操作员证件号在Word(E12345678)与eflow(E99999999)中不一致 (CRITICAL)",
    template_src=boc_france,
    field_map={
        (2, 0, 1): "Global Trading Solutions SARL",
        (2, 1, 1): "880012",
        (2, 2, 1): "15 Rue de la Paix, 75002 Paris, France",
        (8, 1, 1): "Li Wei",
        (8, 2, 1): "Global Trading Solutions SARL",
        (8, 3, 1): "Passport",
        (8, 3, 3): "E12345678",  # Word says E12345678
    },
    eflow_data={
        "flow_id": "EF2026041101",
        "company": {
            "name": "Global Trading Solutions SARL",
            "cert_type": "Business Registration",
            "cert_number": "RCS Paris B 880 012 345"
        },
        "account": {
            "bank_name": "Bank of China Paris Branch",
            "branch": "Paris Main",
            "account_number": "FR7630004000031234567890143"
        },
        "operator": {
            "name": "Li Wei",
            "id_type": "Passport",
            "id_number": "E99999999"  # eflow says E99999999 -> MISMATCH
        },
        "handler": {"name": "Li Wei", "id_type": "Passport", "id_number": "E99999999"},
        "activity": "Apply for e-Corp Internet Banking Service",
        "permissions": {"level": "Level_A", "single_limit": 100000, "daily_limit": 500000},
        "apply_date": "2026-04-11"
    },
    id_img_src=ID_IMG_2
)

# ======================================================================
# Case 012: BOC HK - PASS (Complex merged cells)
# Template: 中国银行香港表1.docx (38x24, heavy merged cells)
# Key rows based on analysis: R3=申请单位名称, R4=证件, R5=法定代表人, R20-26=操作员信息
# ======================================================================
print("\n--- Generating case_012 ---")
create_case(
    case_id="case_012_boc_hk_pass",
    description="[正例] 香港中行企业网银 - 复杂合并单元格(38x24表格)，信息一致",
    template_src=boc_hk1,
    field_map={
        # Table 0 (the big 38x24 table)
        # R3: *申请单位名称 -> cols 4-23 are the value area
        (0, 3, 7): "Hong Kong Bright Future Trading Ltd",
        # R4: 证件号码 -> around col 12
        (0, 4, 12): "91110000MA0EXAMPLE",
        # R5: 法定代表人 -> around col 4
        (0, 5, 4): "Chen Ming",
        # R5: 单位电话 -> around col 14
        (0, 5, 14): "+852 2888 1234",
        # R6: 通信地址 -> around col 4
        (0, 6, 4): "Unit 2301, Tower 1, Lippo Centre, Admiralty, HK",
        # R10: 客户账户信息 *账号 -> col 1
        (0, 10, 1): "012-676-0-012345-6",
        # R20: 操作员信息 *姓名
        (0, 20, 1): "Chen Ming",
        # R20: *证件类型
        (0, 20, 6): "Passport",
        # R20: *证件号码
        (0, 20, 9): "K12345678",
    },
    eflow_data={
        "flow_id": "EF2026041201",
        "company": {
            "name": "Hong Kong Bright Future Trading Ltd",
            "cert_type": "Business Registration Certificate",
            "cert_number": "91110000MA0EXAMPLE"
        },
        "account": {
            "bank_name": "Bank of China (Hong Kong)",
            "branch": "Admiralty Branch",
            "account_number": "012-676-0-012345-6"
        },
        "operator": {
            "name": "Chen Ming",
            "id_type": "Passport",
            "id_number": "K12345678"
        },
        "handler": {"name": "Chen Ming", "id_type": "Passport", "id_number": "K12345678"},
        "activity": "网银新开户",
        "permissions": {"level": "Level_A", "single_limit": 500000, "daily_limit": 2000000},
        "apply_date": "2026-04-12"
    },
    id_img_src=ID_IMG_1
)

# ======================================================================
# Case 013: ICBC Certificate - PASS
# Template: ICBC企业客户证书及分支机构信息表.docx (Table0: 23x13, Table1: 25x13)
# ======================================================================
print("\n--- Generating case_013 ---")
create_case(
    case_id="case_013_icbc_cert_pass",
    description="[正例] ICBC工行证书及分支机构信息表 - 信息完全一致",
    template_src=icbc_cert,
    field_map={
        # Table 0 (23x13) - 企业信息
        (0, 1, 2): "北京中远国际物流有限公司",
        (0, 2, 2): "91110000351234567X",
        (0, 3, 2): "北京市朝阳区建国门外大街甲6号",
        (0, 4, 2): "010-65001234",
        # Table 0 - rows with operator info  
        (0, 7, 2): "Wang Jun",
        (0, 8, 2): "身份证",
        (0, 8, 6): "110101198501012345",
        (0, 9, 2): "13912345678",
    },
    eflow_data={
        "flow_id": "EF2026041301",
        "company": {
            "name": "北京中远国际物流有限公司",
            "cert_type": "统一社会信用代码",
            "cert_number": "91110000351234567X"
        },
        "account": {
            "bank_name": "中国工商银行",
            "branch": "北京朝阳支行",
            "account_number": "0200004509201234567"
        },
        "operator": {
            "name": "Wang Jun",
            "id_type": "身份证",
            "id_number": "110101198501012345"
        },
        "handler": {"name": "Wang Jun", "id_type": "身份证", "id_number": "110101198501012345"},
        "activity": "企业网银证书申请",
        "permissions": {"level": "Level_B", "single_limit": 1000000, "daily_limit": 5000000},
        "apply_date": "2026-04-13"
    },
    id_img_src=ID_IMG_2
)

# ======================================================================
# Case 014: BOC Domestic - PASS (Super large table 43x42)
# ======================================================================
print("\n--- Generating case_014 ---")
create_case(
    case_id="case_014_boc_domestic_pass",
    description="[正例] 国内中行企业网银申请变更表(43x42超大表格) - 信息一致",
    template_src=boc_domestic,
    field_map={
        # The single massive table (43x42)
        # Based on HK analysis pattern, similar field positioning
        (0, 1, 5): "上海星辰贸易有限公司",  # 申请单位名称
        (0, 2, 5): "91310000567890ABCD",       # 证件号码
        (0, 3, 5): "Liu Yang",                  # 法定代表人
        (0, 4, 5): "021-62345678",              # 电话
        (0, 5, 5): "上海市浦东新区陆家嘴环路1000号",  # 地址
    },
    eflow_data={
        "flow_id": "EF2026041401",
        "company": {
            "name": "上海星辰贸易有限公司",
            "cert_type": "统一社会信用代码",
            "cert_number": "91310000567890ABCD"
        },
        "account": {
            "bank_name": "中国银行",
            "branch": "上海浦东支行",
            "account_number": "454676800100123456"
        },
        "operator": {
            "name": "Liu Yang",
            "id_type": "身份证",
            "id_number": "310101199001011234"
        },
        "handler": {"name": "Liu Yang", "id_type": "身份证", "id_number": "310101199001011234"},
        "activity": "开通企业网上银行",
        "permissions": {"level": "Level_A", "single_limit": 500000, "daily_limit": 2000000},
        "apply_date": "2026-04-14"
    },
    id_img_src=ID_IMG_1
)

# ======================================================================
# Case 020: BOC HK - Operator name different (WARNING)
# ======================================================================
print("\n--- Generating case_020 ---")
create_case(
    case_id="case_020_boc_hk_operator_diff",
    description="[负例] 香港中行 - eflow经办人(Chen Ming)与文档操作员(Zhang Fang)姓名不同 (WARNING)",
    template_src=boc_hk1,
    field_map={
        (0, 3, 7): "Hong Kong Bright Future Trading Ltd",
        (0, 4, 12): "91110000MA0EXAMPLE",
        (0, 5, 4): "Chen Ming",
        (0, 10, 1): "012-676-0-012345-6",
        (0, 20, 1): "Zhang Fang",  # Different from eflow!
        (0, 20, 6): "ID Card",
        (0, 20, 9): "K88888888",
    },
    eflow_data={
        "flow_id": "EF2026042001",
        "company": {
            "name": "Hong Kong Bright Future Trading Ltd",
            "cert_type": "Business Registration Certificate",
            "cert_number": "91110000MA0EXAMPLE"
        },
        "account": {
            "bank_name": "Bank of China (Hong Kong)",
            "branch": "Admiralty Branch",
            "account_number": "012-676-0-012345-6"
        },
        "operator": {
            "name": "Chen Ming",  # Different from Word's "Zhang Fang"
            "id_type": "Passport",
            "id_number": "K12345678"
        },
        "handler": {"name": "Chen Ming", "id_type": "Passport", "id_number": "K12345678"},
        "activity": "网银新开户",
        "permissions": {"level": "Level_A", "single_limit": 500000, "daily_limit": 2000000},
        "apply_date": "2026-04-20"
    },
    id_img_src=ID_IMG_2
)

# ======================================================================
# Case 021: CCB High Limit + Sensitive Industry
# Template: [perfect]ccb_corp_app.docx (Table 0: 17x6)
# Field map from SKILL.md
# ======================================================================
print("\n--- Generating case_021 ---")
create_case(
    case_id="case_021_ccb_high_limit",
    description="[风险] CCB建行 - 单笔限额超500万 + 珠宝贸易敏感行业 (INFO)",
    template_src=ccb_template,
    field_map={
        # Table 0 (17x6) - CCB standard form
        (0, 0, 1): "深圳市鑫达珠宝贸易有限公司",
        (0, 1, 1): "统一社会信用代码",
        (0, 1, 4): "91440300MA5F123456",
        (0, 2, 1): "深圳市罗湖区翠竹路水贝珠宝大厦12层",
        (0, 3, 1): "518000",
        (0, 3, 4): "Zhao Qiang",
        (0, 4, 1): "Zhao Qiang",
        (0, 4, 4): "0755-22001234",
        (0, 5, 1): "zhao@xindajewelry.com",
        (0, 8, 1): "深圳市鑫达珠宝贸易有限公司",
        (0, 8, 4): "建设银行深圳罗湖支行",
        (0, 9, 1): "4420 1234 5678 0001",
    },
    eflow_data={
        "flow_id": "EF2026042101",
        "company": {
            "name": "深圳市鑫达珠宝贸易有限公司",
            "cert_type": "统一社会信用代码",
            "cert_number": "91440300MA5F123456"
        },
        "account": {
            "bank_name": "中国建设银行",
            "branch": "深圳罗湖支行",
            "account_number": "4420123456780001"
        },
        "operator": {
            "name": "Zhao Qiang",
            "id_type": "身份证",
            "id_number": "440301198806061234"
        },
        "handler": {"name": "Zhao Qiang", "id_type": "身份证", "id_number": "440301198806061234"},
        "activity": "珠宝黄金贸易网银开通",
        "permissions": {
            "level": "Level_S",
            "single_limit": 10000000,  # 1000万 - 超高额度
            "daily_limit": 50000000    # 5000万
        },
        "apply_date": "2026-04-21"
    },
    id_img_src=ID_IMG_1
)

# ======================================================================
# Case 022: BOC France - Expired ID (CRITICAL)
# ======================================================================
print("\n--- Generating case_022 ---")
create_case(
    case_id="case_022_boc_france_expired_id",
    description="[负例] BOC法国 - 经办人证件已过期(expiry_date=2024-01-15) (CRITICAL)",
    template_src=boc_france,
    field_map={
        (2, 0, 1): "Europe Tech Innovation SAS",
        (2, 1, 1): "990088",
        (2, 2, 1): "8 Avenue des Champs-Elysees, 75008 Paris",
        (8, 1, 1): "Zhang San",
        (8, 2, 1): "Europe Tech Innovation SAS",
        (8, 3, 1): "Passport",
        (8, 3, 3): "G55667788",
    },
    eflow_data={
        "flow_id": "EF2026042201",
        "company": {
            "name": "Europe Tech Innovation SAS",
            "cert_type": "Business Registration",
            "cert_number": "RCS Paris B 990 088 777"
        },
        "account": {
            "bank_name": "Bank of China Paris Branch",
            "branch": "Paris Main",
            "account_number": "FR7630004000039876543210187"
        },
        "operator": {
            "name": "Zhang San",
            "id_type": "Passport",
            "id_number": "G55667788",
            "expiry_date": "2024-01-15"  # EXPIRED!
        },
        "handler": {"name": "Zhang San", "id_type": "Passport", "id_number": "G55667788"},
        "activity": "Apply for e-Corp Internet Banking",
        "permissions": {"level": "Level_A", "single_limit": 200000, "daily_limit": 1000000},
        "apply_date": "2026-04-22"
    },
    id_img_src=ID_IMG_2
)


# ======================================================================
# Summary
# ======================================================================
print("\n" + "="*60)
print("ALL CASES GENERATED SUCCESSFULLY!")
print("="*60)
new_cases = [d.name for d in sorted(TEST_DATA_DIR.iterdir()) if d.is_dir() and d.name.startswith("case_0")]
print(f"Total test cases: {len(new_cases)}")
for c in new_cases:
    print(f"  - {c}")
