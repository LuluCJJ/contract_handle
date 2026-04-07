"""
LLM 客户端 — OpenAI 兼容格式的统一调用层
"""
import re
import json
from openai import OpenAI
from backend.config import get_config


def get_llm_client() -> OpenAI:
    """获取配置好的 OpenAI 客户端"""
    cfg = get_config()
    return OpenAI(
        base_url=cfg.llm.api_base,
        api_key=cfg.llm.api_key,
    )


def chat(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
    """
    发送一轮对话，返回模型回复文本。
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
    发送对话并期望 JSON 格式回复。
    """
    json_instruction = "\n\n请严格以 JSON 格式输出，不要包含任何额外的解释文字或 markdown 代码块标记。"
    return chat(system_prompt + json_instruction, user_prompt, temperature=0.0)


def safe_parse_json(text: str) -> dict:
    """
    安全地解析 LLM 返回的 JSON 字符串。
    1. 处理 Markdown 代码块标记。
    2. 使用正则提取第一个 '{' 到最后一个 '}'。
    3. 支持解析失败时的降级处理。
    """
    if not text:
        return {}
    
    # 移除 markdown 标记
    clean_text = text.strip()
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
        # 正则提取兜底
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            try:
                content = match.group()
                # 尝试修复一些常见的错误，比如单引号和尾部逗号
                fixed_content = content.replace("'", '"')
                # 移除 JSON 对象中最后一个属性后的逗号 (常见 LLM 错误)
                fixed_content = re.sub(r',\s*\}', '}', fixed_content)
                fixed_content = re.sub(r',\s*\]', ']', fixed_content)
                return json.loads(fixed_content)
            except Exception:
                print(f"[LLM] 解析 JSON 极度失败，原文预览: {clean_text[:100]}...")
                return {}
        return {}


def test_connection() -> dict:
    """测试 LLM 连接是否正常"""
    cfg = get_config()
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=cfg.llm.model_name,
            messages=[{"role": "user", "content": "请回复OK"}],
            max_tokens=10,
        )
        reply = response.choices[0].message.content or ""
        return {"status": "ok", "reply": reply, "model": cfg.llm.model_name}
    except Exception as e:
        return {"status": "error", "error": str(e)}
