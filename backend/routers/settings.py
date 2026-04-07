"""
设置 API — 管理 LLM 配置
"""
from fastapi import APIRouter
from backend.config import get_config, update_config
from backend.models.schemas import LLMSettingsRequest, LLMSettingsResponse
from backend.services import llm_client

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/llm", response_model=LLMSettingsResponse)
def get_llm_settings():
    """获取当前 LLM 配置（API Key 脱敏）"""
    cfg = get_config()
    key = cfg.llm.api_key
    masked = key[:3] + "***" + key[-3:] if len(key) > 6 else "***"
    return LLMSettingsResponse(
        api_base=cfg.llm.api_base,
        api_key_masked=masked,
        model_name=cfg.llm.model_name,
    )


@router.post("/llm", response_model=LLMSettingsResponse)
def update_llm_settings(req: LLMSettingsRequest):
    """更新 LLM 配置"""
    api_base_clean = req.api_base
    if api_base_clean and not api_base_clean.startswith("http"):
        api_base_clean = f"https://{api_base_clean}"
    
    cfg = update_config(
        api_base=api_base_clean,
        api_key=req.api_key,
        model_name=req.model_name,
    )
    key = cfg.llm.api_key
    masked = key[:3] + "***" + key[-3:] if len(key) > 6 else "***"
    return LLMSettingsResponse(
        api_base=cfg.llm.api_base,
        api_key_masked=masked,
        model_name=cfg.llm.model_name,
    )


@router.post("/llm/test")
def test_llm_connection():
    """测试 LLM 连接"""
    return llm_client.test_connection()
