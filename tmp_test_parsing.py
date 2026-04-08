
import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent)
sys.path.insert(0, project_root)

# Import schemas and the logic to test
from backend.models.schemas import ExtractedData
from backend.routers.audit import _parse_eflow

def test_robust_parsing():
    print("Running Robust Parsing Tests (V22.7)...")
    
    # 模拟数据 1：混合格式（部分是字典，部分是字符串）
    raw_1 = {
        "company": "测试有限公司",  # 字符串输入
        "account": {"account_number": "123456"}, # 正常字典
        "operator": None, # 空
        "permissions": "高权限" # 字符串
    }
    
    data_1 = _parse_eflow(raw_1)
    assert data_1.company.name == "测试有限公司"
    assert data_1.account.account_number == "123456"
    assert data_1.permissions.level == "高权限"
    print(" - Test 1 (Mixed Formats): PASS")

    # 模拟数据 2：包含非标 Key 的字典
    raw_2 = {
        "company": {"name_cn": "中文公司名"},
        "operator": {"name": "张三"}
    }
    data_2 = _parse_eflow(raw_2)
    assert data_2.company.name == "中文公司名"
    assert data_2.operator.name == "张三"
    print(" - Test 2 (Non-standard keys): PASS")

    # 模拟数据 3：完全畸形（非字典）
    try:
        data_3 = _parse_eflow("这不是字典")
        assert data_3.source == "eflow"
        print(" - Test 3 (Non-dict input): PASS")
    except Exception as e:
        print(f" - Test 3 (Non-dict input): FAILED ({e})")
        sys.exit(1)

    print("\n[SUCCESS] All robust parsing tests passed!")

if __name__ == "__main__":
    test_robust_parsing()
