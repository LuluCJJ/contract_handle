import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.routers.audit import _run_pipeline

def test_v3_pipeline():
    task_id = "test_v3_case_013"
    case_dir = Path("test_data/case_013_icbc_cert_pass")
    
    eflow_path = str(case_dir / "eflow.json")
    doc_paths = []
    img_paths = []

    # Get all files mapped correctly as per run_from_testcase logic
    for f in case_dir.iterdir():
        if f.suffix in (".doc", ".docx", ".pdf") and f.stem != "eflow":
            doc_paths.append(str(f))
        elif f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            img_paths.append(str(f))

    print(f"Running V3 Pipeline with:\n  Docs: {doc_paths}\n  Imgs: {img_paths}\n")
    
    try:
        result = _run_pipeline(task_id, eflow_path, doc_paths, img_paths)
        print("Pipeline Status:", result["status"])
        report = result["report"]
        print("\n--- OVERALL STATUS ---")
        print(report.get("overall_status"))
        print("\n--- SUMMARY ---")
        print(report.get("summary"))
        print("\n--- LLM RISK INSIGHTS ---")
        print(report.get("llm_summary", {}).get("risk_insights", []))
        
        print("\n--- HARD CHECKS SAMPLE ---")
        for dr in report.get("document_reports", []):
            print(f"Doc: {dr['doc_name']}")
            for hc in dr.get("hard_checks", []):
                print(f"  [HARD] {hc['check_name']} : {hc['result']} ({hc['severity']}) - {hc['detail']}")
            for sc in dr.get("semantic_checks", []):
                print(f"  [SEMANTIC] {sc['check_name']} : {sc['result']} ({sc['severity']}) - {sc['detail']}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_v3_pipeline()
