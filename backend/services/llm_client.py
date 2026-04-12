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
# Ensure internal domains bypass the proxy to avoid handshake/routing issues
os.environ["NO_PROXY"] = "localhost,127.0.0.1,.huawei.com,.rnd.huawei.com,oneapi.rnd.huawei.com"
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

def _chat_vision_openai(cfg, system_prompt: str, base64_image: str, temperature: float) -> str:
    """OpenAI SDK Call with Vision capabilities"""
    client = get_llm_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Please extract the requested information from this image."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }
    ]
    response = client.chat.completions.create(
        model=cfg.llm.openai.model_name,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""

def _chat_requests(cfg, system_prompt: str, user_prompt: str) -> str:
    """Internal requests-based call for local/custom LLM endpoints"""
    target = cfg.llm.requests
    # Adaptive Auth: If it's a standard sk- key or it already has 'Bearer ', keep it. 
    # If it's a raw internal token like 'c008...', send as is.
    auth_header = target.api_key
    if auth_header.startswith("sk-") and not auth_header.startswith("Bearer "):
        auth_header = f"Bearer {auth_header}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
    }
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    data = {
        "model": target.model_name if target.model_name else "auto",
        "messages": messages
    }
    
    try:
        print(f"[LLM] Sending Request (Requests-mode) to: {target.api_base}")
        print(f"[LLM] Auth Prefix: {auth_header[:10]}...")
        
        response = requests.post(
            target.api_base, 
            headers=headers, 
            json=data, 
            verify=False, # Mandatory for internal SSL/Internal endpoints
            timeout=300,
            proxies={"http": None, "https": None} # Double safety to ensure no proxy for internal nodes
        )
        
        if response.status_code != 200:
            print(f"[LLM] HTTP ERROR {response.status_code}: {response.text[:500]}")
            return f"Error: Backend returned {response.status_code} - {response.text[:100]}"

        resp_json = response.json()
        if 'choices' in resp_json and len(resp_json['choices']) > 0:
            return resp_json['choices'][0]['message']['content']
        else:
            print(f"[LLM] Unexpected JSON structure: {resp_json}")
            return f"Error: Unexpected JSON structure from LLM. Keys: {list(resp_json.keys())}"

    except Exception as e:
        print(f"[LLM] CRITICAL ERROR in _chat_requests: {str(e)}")
        return f"Exception: {str(e)}"

def _chat_vision_requests(cfg, system_prompt: str, base64_image: str) -> str:
    """Internal requests-based call with Vision for local/custom LLM API"""
    target = cfg.llm.requests
    auth_header = target.api_key
    if auth_header.startswith("sk-") and not auth_header.startswith("Bearer "):
        auth_header = f"Bearer {auth_header}"

    headers = {"Content-Type": "application/json", "Authorization": auth_header}
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Please extract the requested information from this image."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }
    ]
    data = {"model": target.model_name if target.model_name else "auto", "messages": messages}
    
    try:
        response = requests.post(target.api_base, headers=headers, json=data, verify=False, timeout=300, proxies={"http": None, "https": None})
        if response.status_code != 200:
            print(f"[LLM] Vision HTTP ERROR {response.status_code}: {response.text[:500]}")
            return ""
        return response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        print(f"[LLM] Vision CRITICAL ERROR: {str(e)}")
        return ""

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

def chat_vision_json(system_prompt: str, base64_image: str) -> dict:
    """
    Send a vision request and parse response as JSON.
    """
    cfg = get_config()
    json_instruction = "\n\nReturn ONLY raw JSON. No markdown."
    full_prompt = system_prompt + json_instruction
    try:
        if cfg.llm.api_type == "requests":
            raw_resp = _chat_vision_requests(cfg, full_prompt, base64_image)
        else:
            raw_resp = _chat_vision_openai(cfg, full_prompt, base64_image, temperature=0.0)
    except Exception as e:
        print(f"[LLM Vision] Call Error ({cfg.llm.api_type}): {e}")
        return {}
    return safe_parse_json(raw_resp)

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
