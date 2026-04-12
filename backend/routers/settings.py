"""
设置 API — 管理 LLM 配置
"""
from fastapi import APIRouter
from backend.config import get_config, update_config
from backend.models.schemas import LLMSettingsRequest, LLMSettingsResponse, LLMInstanceSettings
from backend.services import llm_client

router = APIRouter(prefix="/api/settings", tags=["settings"])


def mask_key(key: str) -> str:
    if not key or key == "sk-placeholder": return "sk-..."
    return key[:3] + "***" + key[-3:] if len(key) > 6 else "***"

@router.get("/llm", response_model=LLMSettingsResponse)
def get_llm_settings():
    """获取当前全量 LLM 配置（API Key 脱敏）"""
    cfg = get_config()
    return LLMSettingsResponse(
        api_type=cfg.llm.api_type,
        openai=LLMInstanceSettings(
            api_base=cfg.llm.openai.api_base,
            api_key_masked=mask_key(cfg.llm.openai.api_key),
            model_name=cfg.llm.openai.model_name
        ),
        requests=LLMInstanceSettings(
            api_base=cfg.llm.requests.api_base,
            api_key_masked=mask_key(cfg.llm.requests.api_key),
            model_name=cfg.llm.requests.model_name
        )
    )


@router.post("/llm", response_model=LLMSettingsResponse)
def update_llm_settings(req: LLMSettingsRequest):
    """更新 LLM 配置"""
    api_base_clean = req.api_base
    if api_base_clean and not api_base_clean.startswith("http"):
        # Auto-fix protocol if missing
        api_base_clean = f"https://{api_base_clean}"
    
    # Configuration will be updated into the slot matching req.api_type
    cfg = update_config(
        api_type=req.api_type,
        api_base=api_base_clean,
        api_key=req.api_key,
        model_name=req.model_name,
    )
    
    return get_llm_settings()


@router.post("/llm/test")
def test_llm_connection():
    """测试 LLM 连接"""
    return llm_client.test_connection()
