"""
Configuration Management - Manage runtime configs for LLM endpoints, OCR paths, and Prompts.
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
PROMPT_FILE = BASE_DIR / "backend" / "prompts" / "prompts.json"


@dataclass
class LLMConfig:
    api_base: str = "http://localhost:8080/v1"
    api_key: str = "sk-placeholder"
    model_name: str = "qwen2.5-72b-instruct"
    api_type: str = "openai"  # "openai" or "requests"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    ocr_model_dir: str = ""  
    upload_dir: str = "uploads"
    prompts: dict = field(default_factory=dict)

    def save(self):
        CONFIG_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> "AppConfig":
        cfg = cls()
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                llm_data = data.get("llm", {})
                cfg.llm = LLMConfig(**llm_data)
                cfg.ocr_model_dir = data.get("ocr_model_dir", "")
                cfg.upload_dir = data.get("upload_dir", "uploads")
            except: pass
        
        # Load external prompts
        if PROMPT_FILE.exists():
            try:
                cfg.prompts = json.loads(PROMPT_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[Config] Error loading prompts.json: {e}")
        
        return cfg

    def get_prompt(self, key: str) -> str:
        """Get system_prompt from the library by key"""
        return self.prompts.get(key, {}).get("system_prompt", "")


# Singleton
_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def update_config(**kwargs) -> AppConfig:
    global _config
    cfg = get_config()
    # Simple updates
    if "api_base" in kwargs: cfg.llm.api_base = kwargs["api_base"]
    if "api_key" in kwargs: cfg.llm.api_key = kwargs["api_key"]
    if "model_name" in kwargs: cfg.llm.model_name = kwargs["model_name"]
    if "api_type" in kwargs: cfg.llm.api_type = kwargs["api_type"]
    if "ocr_model_dir" in kwargs: cfg.ocr_model_dir = kwargs["ocr_model_dir"]
    
    cfg.save()
    _config = cfg
    return cfg
