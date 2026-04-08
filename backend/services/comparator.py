"""
Comparator Service - Compares extracted data against rules and identifies risks
V20.3 - Supporting Configurable Prompts
"""
import json
from backend.services.llm_client import chat_json
from backend.config import get_config

def run_comparisons(extracted_data: dict, rules: str) -> dict:
    """
    Compare extracted information against business rules using 'comparative_risk_report'.
    """
    cfg = get_config()
    system_prompt = cfg.get_prompt("comparative_risk_report")
    
    if not system_prompt:
        print("[Comparator] Warning: No comparative_risk_report prompt found in config.")
        return {"items": []}

    user_prompt = {
        "extracted_data": extracted_data,
        "business_rules": rules
    }
    
    try:
        return chat_json(system_prompt, user_prompt)
    except Exception as e:
        print(f"[Comparator] Error during comparison: {e}")
        return {"items": []}
