"""
Information Extractor - Uses LLM to parse application forms
V20.3 - Supporting Configurable Prompts
"""
import json
from backend.services.llm_client import chat_json
from backend.config import get_config

def extract_information(document_text: str) -> dict:
    """
    Extract structured data from OCR text using the dynamic 'main_document_parsing' prompt.
    """
    cfg = get_config()
    system_prompt = cfg.get_prompt("main_document_parsing")
    
    if not system_prompt:
        print("[Extractor] Warning: No main_document_parsing prompt found in config.")
        return {}

    user_prompt = f"请从以下银行申请文档内容中提取信息：\n\n{document_text}"
    
    try:
        return chat_json(system_prompt, user_prompt)
    except Exception as e:
        print(f"[Extractor] Error during extraction: {e}")
        return {}
