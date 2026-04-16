"""
Information Extractor - Uses LLM to parse application forms
V3.0 - Template-free Global Extraction
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
from backend.models.schemas import DocExtractedData

def extract_information(document_text: str, filename: str, doc_type: str) -> DocExtractedData:
    """提取单文档的数据，并强转为 DocExtractedData 结构"""
    cfg = get_config()
    system_prompt = cfg.get_prompt("global_document_extraction")
    if not system_prompt: 
        return DocExtractedData(source_file=filename, source_type=doc_type)
        
    user_prompt = f"请从以下提取出的文本表单或信件中提取信息：\n\n{document_text}"
    try:
        raw_dict = chat_json(system_prompt, user_prompt)
        res = DocExtractedData(**raw_dict)
        res.source_file = filename
        res.source_type = doc_type
        # 保存原始 LLM dict 到 raw_text
        import json
        res.raw_text = json.dumps(raw_dict, ensure_ascii=False)
        return res
    except Exception as e:
        print(f"[Extractor] Error extracting from {filename}: {e}")
        return DocExtractedData(source_file=filename, source_type=doc_type, raw_text=str(e))
