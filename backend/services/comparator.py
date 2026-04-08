"""
Comparator Service - Compares extracted data against rules and identifies risks
V21.2 - Supporting Configurable Prompts & VSCode Direct Run
"""
import sys
from pathlib import Path

# VSCode Path Fix
script_dir = Path(__file__).resolve().parent
project_root = str(script_dir.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.llm_client import chat_json
from backend.config import get_config

def run_comparisons(extracted_data: dict, rules: str) -> dict:
    cfg = get_config()
    system_prompt = cfg.get_prompt("comparative_risk_report")
    if not system_prompt: return {"items": []}
    user_prompt = {"extracted_data": extracted_data, "business_rules": rules}
    try:
        return chat_json(system_prompt, user_prompt)
    except Exception as e:
        print(f"[Comparator] Error: {e}")
        return {"items": []}
