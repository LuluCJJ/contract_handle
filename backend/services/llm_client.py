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
    return OpenAI(
        base_url=cfg.llm.api_base,
        api_key=cfg.llm.api_key,
        http_client=httpx_client
    )

def _chat_openai(cfg, system_prompt: str, user_prompt: str, temperature: float) -> str:
    """Standard OpenAI SDK call"""
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

def _chat_requests(cfg, system_prompt: str, user_prompt: str) -> str:
    """Internal requests-based call for Huawei custom LLM endpoints"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": cfg.llm.api_key,
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    data = {
        "model": cfg.llm.model_name if cfg.llm.model_name != "qwen2.5-72b-instruct" else "auto",
        "messages": messages
    }
    
    # Note: Using verify=False as per Demo code requirement (verbify=False)
    response = requests.post(
        cfg.llm.api_base, 
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
