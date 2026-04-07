"""
信息提取层
"""
import json
from backend.services.llm_client import chat_json
from backend.prompts.extraction import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from backend.models.schemas import ExtractedData, CompanyInfo, PersonInfo, AccountInfo, PermissionInfo

def extract_from_document(document_text: str) -> ExtractedData:
    """
    调用 LLM 从文档解析文本中提取结构化字段
    """
    user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(document_text=document_text)
    
    response_text = chat_json(EXTRACTION_SYSTEM_PROMPT, user_prompt)
    
    # 尝试解析 JSON
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # 兜底：如果 LLM 返回不是合法 JSON（尽管我们努力约束了）
        import re
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                data = {}
        else:
            data = {}
            
    # 转为 Pydantic 模型
    extracted = ExtractedData(
        source="word",
        raw_text=document_text[:2000] # 保留部分原文供调试
    )
    
    if "company" in data:
        c = data["company"]
        extracted.company = CompanyInfo(
            name=c.get("name", ""),
            name_en=c.get("name_en", ""),
            cert_type=c.get("cert_type", ""),
            cert_number=c.get("cert_number", "")
        )
        
    if "operator" in data:
        o = data["operator"]
        extracted.operator = PersonInfo(
            name=o.get("name", ""),
            id_type=o.get("id_type", ""),
            id_number=o.get("id_number", "")
        )
        
    if "account" in data:
        a = data["account"]
        extracted.account = AccountInfo(
            bank_name=a.get("bank_name", ""),
            branch=a.get("branch", ""),
            account_number=a.get("account_number", "")
        )
        
    if "permissions" in data:
        p = data["permissions"]
        try:
            extracted.permissions = PermissionInfo(
                level=p.get("level", ""),
                single_limit=float(p.get("single_limit", 0)),
                daily_limit=float(p.get("daily_limit", 0))
            )
        except ValueError:
            pass # 不能转数字就算了
            
    extracted.activity = data.get("activity", "")
    
    return extracted
