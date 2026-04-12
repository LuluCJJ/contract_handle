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
class LLMInstanceConfig:
    api_base: str = ""
    api_key: str = ""
    model_name: str = ""


@dataclass
class LLMConfig:
    api_type: str = "openai"  # "openai" or "requests"
    openai: LLMInstanceConfig = field(default_factory=lambda: LLMInstanceConfig(
        api_base="https://api.openai.com/v1",
        api_key="sk-placeholder",
        model_name="gpt-4o"
    ))
    requests: LLMInstanceConfig = field(default_factory=lambda: LLMInstanceConfig(
        api_base="http://xiaoluban.rnd.huawei.com:80/y/llm/v1/chat/completions",
        api_key="sk-placeholder",
        model_name="auto"
    ))


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    ocr_model_dir: str = ""  
    upload_dir: str = "uploads"
    prompts: dict = field(default_factory=dict)

    def save(self):
        # We EXCLUDE prompts from config.json to prevent syncing logic-heavy 
        # prompts into environment-specific config files.
        data = asdict(self)
        if "prompts" in data:
            del data["prompts"]
            
        CONFIG_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> "AppConfig":
        cfg = cls()
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                llm_data = data.get("llm", {})
                
                # Load API Type
                cfg.llm.api_type = llm_data.get("api_type", "openai")
                
                # Load Sub-configs safely
                for key in ["openai", "requests"]:
                    if key in llm_data:
                        setattr(cfg.llm, key, LLMInstanceConfig(**llm_data[key]))
                
                cfg.ocr_model_dir = data.get("ocr_model_dir", "")
                cfg.upload_dir = data.get("upload_dir", "uploads")
                # cfg.prompts is deliberately NOT loaded from config.json here
            except Exception as e:
                print(f"[Config] Warning: Failed to parse {CONFIG_FILE}: {e}")
                # Fallback to default which is already in cfg
        
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
    
    # Update API Type
    if "api_type" in kwargs: 
        cfg.llm.api_type = kwargs["api_type"]

    # Update active instance config
    active_type = cfg.llm.api_type
    target = getattr(cfg.llm, active_type)
    
    if "api_base" in kwargs: target.api_base = kwargs["api_base"]
    if "api_key" in kwargs and kwargs["api_key"] != "sk-placeholder": 
        target.api_key = kwargs["api_key"]
    if "model_name" in kwargs: target.model_name = kwargs["model_name"]
    
    # Global settings
    if "ocr_model_dir" in kwargs: cfg.ocr_model_dir = kwargs["ocr_model_dir"]
    
    cfg.save()
    _config = cfg
    return cfg
