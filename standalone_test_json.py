import sys
import re
import json

# Standalone copy of the function for testing without dependencies
def safe_parse_json(text: str) -> dict:
    if not text:
        return {}
    
    clean_text = text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
        
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    
    clean_text = clean_text.strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                content = match.group()
                content = re.sub(r',\s*\}', '}', content)
                content = re.sub(r',\s*\]', ']', content)
                return json.loads(content)
            except Exception:
                return {}
        return {}

def test_parsing():
    print("--- V18.0 STANDALONE JSON Logic Test ---")
    
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
        print("\n[RESULT] Standalone Logic test passed!")
        sys.exit(0)
    else:
        print("\n[RESULT] Standalone Logic test failed.")
        sys.exit(1)

if __name__ == "__main__":
    test_parsing()
