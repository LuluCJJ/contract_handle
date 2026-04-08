"""
Information Extractor - Uses LLM to parse application forms
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

def extract_information(document_text: str) -> dict:
    cfg = get_config()
    system_prompt = cfg.get_prompt("main_document_parsing")
    if not system_prompt: return {}
    user_prompt = f"请从以下银行申请文档内容中提取信息：\n\n{document_text}"
    try:
        return chat_json(system_prompt, user_prompt)
    except Exception as e:
        print(f"[Extractor] Error: {e}")
        return {}
