"""
LLM Client - OpenAI-compatible unified calling layer
V18.0 - ASCII-safe comments & Robust JSON Parsing
"""
import re
import json
from openai import OpenAI
from backend.config import get_config


def get_llm_client() -> OpenAI:
    """Get the configured OpenAI client"""
    cfg = get_config()
    return OpenAI(
        base_url=cfg.llm.api_base,
        api_key=cfg.llm.api_key,
    )


def chat(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """
    Send a round of conversation and return the model's reply text.
    """
    cfg = get_config()
    client = get_llm_client()

    response = client.chat.completions.create(
        model=cfg.llm.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def chat_json(system_prompt: str, user_prompt: str) -> str:
    """
    Send conversation and expect a JSON format response.
    """
    json_instruction = "\n\nReturn ONLY raw JSON. No markdown, no explanations."
    return chat(system_prompt + json_instruction, user_prompt, temperature=0.0)


def safe_parse_json(text: str) -> dict:
    """
    Safely parse JSON from LLM response.
    1. Strip markdown blocks.
    2. Extract content between first '{' and last '}'.
    3. Fix trailing commas.
    """
    if not text:
        return {}
    
    # Pre-clean
    clean_text = text.strip()
    
    # Strip common markdown prefixes
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
        # Regex fallback: find the largest JSON block
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                content = match.group()
                # Fix trailing commas in objects and arrays
                content = re.sub(r',\s*\}', '}', content)
                content = re.sub(r',\s*\]', ']', content)
                return json.loads(content)
            except Exception:
                # Last resort: try to fix common quote issues if possible
                try:
                    # Only replace if it strictly looks like a key/value issue
                    # But for safety in V18.0, we just log and return empty
                    print(f"[LLM] JSON Parsing failed. Raw: {clean_text[:50]}...")
                    return {}
                except: return {}
        return {}


def test_connection() -> dict:
    """Test LLM connection"""
    cfg = get_config()
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=cfg.llm.model_name,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=10,
        )
        reply = response.choices[0].message.content or ""
        return {"status": "ok", "reply": reply}
    except Exception as e:
        return {"status": "error", "error": str(e)}
