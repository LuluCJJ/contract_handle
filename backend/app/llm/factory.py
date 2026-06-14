from backend.app.core.config import get_settings
from backend.app.llm.mock_client import MockLLMClient
from backend.app.llm.openai_compatible_client import OpenAICompatibleClient


def create_llm_client(use_mock: bool = False):
    settings = get_settings()
    if use_mock or settings.llm_provider == "mock":
        return MockLLMClient()
    return OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )

