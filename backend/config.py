"""
配置管理 — 管理 LLM 端点、OCR 模型路径等运行时配置
"""
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


@dataclass
class LLMConfig:
    api_base: str = "http://localhost:8080/v1"
    api_key: str = "sk-placeholder"
    model_name: str = "qwen2.5-72b-instruct"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    ocr_model_dir: str = ""  # 留空则用默认位置
    upload_dir: str = "uploads"

    def save(self):
        CONFIG_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            llm_data = data.get("llm", {})
            return cls(
                llm=LLMConfig(**llm_data),
                ocr_model_dir=data.get("ocr_model_dir", ""),
                upload_dir=data.get("upload_dir", "uploads"),
            )
        return cls()


# 全局单例
_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def update_config(**kwargs) -> AppConfig:
    global _config
    cfg = get_config()
    if "api_base" in kwargs or "api_key" in kwargs or "model_name" in kwargs:
        if "api_base" in kwargs:
            cfg.llm.api_base = kwargs["api_base"]
        if "api_key" in kwargs:
            cfg.llm.api_key = kwargs["api_key"]
        if "model_name" in kwargs:
            cfg.llm.model_name = kwargs["model_name"]
    if "ocr_model_dir" in kwargs:
        cfg.ocr_model_dir = kwargs["ocr_model_dir"]
    cfg.save()
    _config = cfg
    return cfg
