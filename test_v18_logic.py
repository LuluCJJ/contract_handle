import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

from backend.services.llm_client import safe_parse_json

def test_parsing():
    print("--- V18.0 JSON Parsing Logic Test ---")
    
    cases = [
        {
            "name": "Markdown Block",
            "input": '```json\n{"status": "success", "data": [1, 2, 3]}\n```',
            "expected": "success"
        },
        {
            "name": "Trailing Comma (Object)",
            "input": '{"detail": "It\'s a match",}',
            "expected": "It's a match"
        },
        {
            "name": "Trailing Comma (Array)",
            "input": '{"items": [1, 2, 3, ]}',
            "expected": 3
        },
        {
            "name": "Leading/Trailing Noise",
            "input": 'Here is the result: {"check": "passed"} Hope it helps!',
            "expected": "passed"
        }
    ]
    
    all_passed = True
    for case in cases:
        try:
            result = safe_parse_json(case["input"])
            # Verification
            val = ""
            if "status" in result: val = result["status"]
            elif "detail" in result: val = result["detail"]
            elif "check" in result: val = result["check"]
            elif "items" in result: val = result["items"][-1]
            
            if val == case["expected"]:
                print(f"[PASS] {case['name']}")
            else:
                print(f"[FAIL] {case['name']} - Got: {val}")
                all_passed = False
        except Exception as e:
            print(f"[ERROR] {case['name']}: {e}")
            all_passed = False
            
    if all_passed:
        print("\n[RESULT] Logic test passed! safe_parse_json is robust.")
        sys.exit(0)
    else:
        print("\n[RESULT] Logic test failed.")
        sys.exit(1)

if __name__ == "__main__":
    test_parsing()
