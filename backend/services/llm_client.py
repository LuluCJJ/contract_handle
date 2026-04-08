"""
LLM Client - OpenAI-compatible unified calling layer
V20.3 - Supporting Dynamic Prompts & Preserving Internal Proxy Settings
"""
import os
import re
import json
import httpx
from openai import OpenAI
from backend.config import get_config

# === COMPANY INTERNAL PROXY CONFIG - REMAIN FIXED ===
os.environ["NO_PROXY"] = "oneapi.rnd.huawei.com"
httpx_client = httpx.Client(verify=False, timeout=300)

def get_llm_client() -> OpenAI:
    """Get the configured OpenAI client with internal proxy settings"""
    cfg = get_config()
    return OpenAI(
        base_url=cfg.llm.api_base,
        api_key=cfg.llm.api_key,
        http_client=httpx_client
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


def chat_json(system_prompt: str, user_prompt: str or dict) -> dict:
    """
    Send conversation and expect a JSON format response.
    Returns a parsed dict using safe_parse_json.
    """
    if isinstance(user_prompt, dict):
        user_prompt = json.dumps(user_prompt, ensure_ascii=False)
        
    json_instruction = "\n\nReturn ONLY raw JSON. No markdown."
    raw_resp = chat(system_prompt + json_instruction, user_prompt, temperature=0.0)
    return safe_parse_json(raw_resp)


def safe_parse_json(text: str) -> dict:
    """
    Safely parse JSON from LLM response.
    """
    if not text: return {}
    clean_text = text.strip()
    if clean_text.startswith("```json"): clean_text = clean_text[7:]
    elif clean_text.startswith("```"): clean_text = clean_text[3:]
    if clean_text.endswith("```"): clean_text = clean_text[:-3]
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


def test_connection() -> dict:
    """Test LLM connection"""
    try:
        client = get_llm_client()
        cfg = get_config()
        response = client.chat.completions.create(
            model=cfg.llm.model_name,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=10,
        )
        reply = response.choices[0].message.content or ""
        return {"status": "ok", "reply": reply}
    except Exception as e:
        return {"status": "error", "error": str(e)}
