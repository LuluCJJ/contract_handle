from functools import lru_cache
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[3]


def _load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


class Settings:
    def __init__(self) -> None:
        _load_env_file()
        self.app_name = "bank-doc-preaudit-poc"
        self.llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
        self.llm_base_url = os.getenv("LLM_BASE_URL", "")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_model = os.getenv("LLM_MODEL", "mock-risk-reviewer")
        self.llm_timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

