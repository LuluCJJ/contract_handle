"""
LLM 客户端 — OpenAI 兼容格式的统一调用层
"""
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
    temperature 默认低值以获得更确定性的输出。
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
    会在 system prompt 中追加 JSON 输出要求。
    """
    json_instruction = "\n\n请严格以 JSON 格式输出，不要包含任何额外的解释文字或 markdown 代码块标记。"
    return chat(system_prompt + json_instruction, user_prompt, temperature=0.0)


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
