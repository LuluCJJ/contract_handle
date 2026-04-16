import os
import sys
from pathlib import Path
import time
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.routers.audit import _run_pipeline

def run_batch_tests():
    data_dir = Path("test_data")
    
    total_cases = 0
    success_cases = 0
    failed_cases = []
    
    print("=" * 60)
    print("V3.0 BATCH PIPELINE VALIDATOR")
    print("=" * 60)
    
    start_time = time.time()
    
    for case_dir in sorted(data_dir.iterdir()):
        if not case_dir.is_dir():
            continue
            
        case_id = case_dir.name
        eflow_path = str(case_dir / "eflow.json")
        
        if not os.path.exists(eflow_path):
            continue
            
        doc_paths = []
        img_paths = []

        for f in case_dir.iterdir():
            if f.suffix in (".doc", ".docx", ".pdf") and f.stem != "eflow":
                if "bank_app" in f.name or "form" in f.name or "表" in f.name or "app" in f.name:
                    doc_paths.append(str(f))
                else:
                    img_paths.append(str(f))
            elif f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                img_paths.append(str(f))
                
        print(f"\n[{case_id}]")
        print(f"  Docs: {len(doc_paths)} | Imgs: {len(img_paths)}")
        
        total_cases += 1
        
        try:
            # Execute Pipeline
            result = _run_pipeline(case_id, eflow_path, doc_paths, img_paths)
            status = result.get("overall_status")
            
            if result.get("status") == "completed":
                print(f"  [PASS] Pipeline Executed. Audit Status: {result.get('report', {}).get('overall_status')}")
                success_cases += 1
            else:
                print(f"  [FAIL] Pipeline returned anomalous payload.")
                failed_cases.append(case_id)
                
        except Exception as e:
            print(f"  [ERROR] Pipeline Crash: {e}")
            failed_cases.append(case_id)
            
    print("\n" + "=" * 60)
    print("BATCH RUN SUMMARY")
    print("=" * 60)
    print(f"Total valid cases  : {total_cases}")
    print(f"Execution Success  : {success_cases}")
    print(f"Execution Failures : {len(failed_cases)}")
    
    if failed_cases:
        print("\nFailed Cases List:")
        for fc in failed_cases:
            print(f" - {fc}")
            
    exec_time = time.time() - start_time
    print(f"\nTotal Time: {exec_time:.2f} seconds")

if __name__ == "__main__":
    run_batch_tests()
