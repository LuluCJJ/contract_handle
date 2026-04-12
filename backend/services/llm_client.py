"""
LLM Client - OpenAI-compatible unified calling layer
V21.0 - Robust Type Handling & Internal Proxy Preservation
"""
import os
import re
import json
import httpx
import requests
from typing import Union, Any
from openai import OpenAI
from backend.config import get_config

# === COMPANY INTERNAL PROXY CONFIG - REMAIN FIXED ===
os.environ["NO_PROXY"] = "oneapi.rnd.huawei.com"
httpx_client = httpx.Client(verify=False, timeout=300)

def get_llm_client() -> OpenAI:
    cfg = get_config()
    # Always use the current active configuration for the SDK client
    active_cfg = getattr(cfg.llm, cfg.llm.api_type)
    return OpenAI(
        base_url=active_cfg.api_base,
        api_key=active_cfg.api_key,
        http_client=httpx_client
    )

def _chat_openai(cfg, system_prompt: str, user_prompt: str, temperature: float) -> str:
    """Standard OpenAI SDK call"""
    client = get_llm_client()
    # Use config from the openai slot
    response = client.chat.completions.create(
        model=cfg.llm.openai.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""

def _chat_requests(cfg, system_prompt: str, user_prompt: str) -> str:
    """Internal requests-based call for Huawei custom LLM endpoints"""
    # Use config from the requests slot
    target = cfg.llm.requests
    headers = {
        "Content-Type": "application/json",
        "Authorization": target.api_key,
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    data = {
        "model": target.model_name if target.model_name else "auto",
        "messages": messages
    }
    
    # Note: Using verify=False as per Demo code requirement (verbify=False)
    response = requests.post(
        target.api_base, 
        headers=headers, 
        json=data, 
        verify=False,
        timeout=300
    )
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def chat(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """
    Send a round of conversation. Routes based on cfg.llm.api_type.
    """
    if not isinstance(user_prompt, str):
        user_prompt = str(user_prompt)

    cfg = get_config()
    try:
        if cfg.llm.api_type == "requests":
            return _chat_requests(cfg, system_prompt, user_prompt)
        else:
            return _chat_openai(cfg, system_prompt, user_prompt, temperature)
    except Exception as e:
        print(f"[LLM] Call Error ({cfg.llm.api_type}): {e}")
        return ""

def chat_json(system_prompt: str, user_prompt: Any) -> dict:
    """
    Expect a JSON format response. Automatically stringifies dict input.
    """
    # Force string conversion to prevent unhashable type errors in SDK/Network layers
    if isinstance(user_prompt, (dict, list)):
        u_prompt_str = json.dumps(user_prompt, ensure_ascii=False)
    else:
        u_prompt_str = str(user_prompt)
        
    json_instruction = "\n\nReturn ONLY raw JSON. No markdown."
    raw_resp = chat(system_prompt + json_instruction, u_prompt_str, temperature=0.0)
    return safe_parse_json(raw_resp)

def safe_parse_json(text: str) -> dict:
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
    """测试当前 LLM 配置是否连通"""
    cfg = get_config()
    print(f"[LLM] Testing connection via {cfg.llm.api_type}...")
    
    try:
        reply = chat(
            system_prompt="You are a connection tester. Reply with 'OK'.",
            user_prompt="ping",
            temperature=0.0
        )
        
        if reply and "OK" in reply.upper():
            active_cfg = getattr(cfg.llm, cfg.llm.api_type)
            return {
                "status": "ok",
                "model": active_cfg.model_name,
                "reply": reply
            }
        elif reply:
            active_cfg = getattr(cfg.llm, cfg.llm.api_type)
            return {
                "status": "ok",
                "model": active_cfg.model_name,
                "reply": reply,
                "warning": "Received unexpected reply but connection seems open."
            }
        else:
            return {
                "status": "error",
                "error": "Received empty response from LLM."
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
