import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.routers.audit import _run_pipeline

def test_complex_case():
    # 选择 case_012_boc_hk_pass 作为深度验证对象
    case_id = "case_012_boc_hk_pass"
    case_dir = Path("test_data") / case_id
    
    if not case_dir.exists():
        print(f"Error: {case_id} not found.")
        return

    eflow_path = str(case_dir / "eflow.json")
    doc_paths = []
    img_paths = []

    for f in case_dir.iterdir():
        if f.suffix in (".doc", ".docx", ".pdf") and f.stem != "eflow":
            doc_paths.append(str(f))
        elif f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            img_paths.append(str(f))

    print(f"--- STARTING END-TO-END VALIDATION: {case_id} ---")
    print(f"Docs: {doc_paths}")
    print(f"Imgs: {img_paths}\n")
    
    try:
        result = _run_pipeline(case_id, eflow_path, doc_paths, img_paths)
        report = result.get("report", {})
        
        print("\n[✔] PIPELINE EXECUTION COMPLETED")
        print(f"Overall Status: {report.get('overall_status')}")
        print(f"Summary: {report.get('summary')}")
        
        # 详细检查第一个文档的提取和比对情况
        if report.get("document_reports"):
            first_rep = report["document_reports"][0]
            print(f"\n[REPORT SAMPLE: {first_rep['doc_name']}]")
            print(f"- Extracted Business Activity: {first_rep['extracted_data'].get('business_activity')}")
            
            # 打印硬比对
            print(f"- Hard Checks Count: {len(first_rep.get('hard_checks', []))}")
            for hc in first_rep.get('hard_checks', []):
                print(f"  [{hc['result']}] {hc['check_name']}: {hc['detail']}")
                
            # 打印语义比对
            print(f"- Semantic Checks Count: {len(first_rep.get('semantic_checks', []))}")
            for sc in first_rep.get('semantic_checks', []):
                print(f"  [{sc['result']}] {sc['check_name']}: {sc['detail']}")

        # 检查总结
        llm_sum = report.get("llm_summary", {})
        print(f"\n[LLM GLOBAL SUMMARY]")
        print(f"Risk Insights: {llm_sum.get('risk_insights', [])}")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complex_case()
