import json
from backend.models.schemas import ExtractedData, CompanyInfo, PersonInfo, AccountInfo, PermissionInfo
from backend.services.comparator import run_comparisons

def test_semantic_logic():
    print("=== 开始语义比对逻辑测试 ===")
    
    # 模拟数据
    eflow = ExtractedData(
        source="eflow",
        activity="测试开户申请",
        permissions=PermissionInfo(level="Admin", single_limit=10000, daily_limit=50000)
    )
    word = ExtractedData(
        source="word",
        activity="开立单位银行结算账户",
        permissions=PermissionInfo(level="管理员", daily_limit=50000)
    )
    ocr = ExtractedData(source="ocr")
    
    print("[1] 正在模拟 OCR 后的比对环节...")
    try:
        results = run_comparisons(eflow, word, ocr)
        print(f"[成功] 获取到 {len(results)} 条检查结果")
        for i, res in enumerate(results):
            print(f"  {i+1}. {res.check_name}: {res.result} ({res.severity})")
    except Exception as e:
        print(f"[失败] 比对逻辑中途崩溃!")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_semantic_logic()
