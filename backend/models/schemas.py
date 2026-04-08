"""
Pydantic 数据模型 — 定义 API 请求/响应和内部数据结构
"""
from pydantic import BaseModel, Field
from enum import Enum


# === 配置相关 ===

class LLMSettingsRequest(BaseModel):
    api_base: str = Field(..., description="OpenAI 兼容 API 端点")
    api_key: str = Field(..., description="API Key")
    model_name: str = Field(..., description="模型名称")


class LLMSettingsResponse(BaseModel):
    api_base: str
    api_key_masked: str  # 脱敏显示
    model_name: str


# === 提取结果 ===

class PersonInfo(BaseModel):
    name: str = ""
    id_type: str = ""
    id_number: str = ""
    issue_date: str = ""
    expiry_date: str = ""


class CompanyInfo(BaseModel):
    name: str = ""
    name_en: str = ""
    cert_type: str = ""
    cert_number: str = ""


class AccountInfo(BaseModel):
    bank_name: str = ""
    branch: str = ""
    account_number: str = ""


class PermissionInfo(BaseModel):
    level: str = ""
    single_limit: float = 0
    daily_limit: float = 0


class ExtractedData(BaseModel):
    """从某个数据源提取的统一结构"""
    source: str = ""  # "eflow" / "word" / "ocr"
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    operator: PersonInfo = Field(default_factory=PersonInfo)
    handler: PersonInfo = Field(default_factory=PersonInfo)
    account: AccountInfo = Field(default_factory=AccountInfo)
    permissions: PermissionInfo = Field(default_factory=PermissionInfo)
    activity: str = ""
    raw_text: str = ""


# === 比对结果 ===

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    PASS = "PASS"


class CheckResult(BaseModel):
    check_name: str
    field_name: str = ""
    source_a_label: str = ""
    source_a_value: str = ""
    source_b_label: str = ""
    source_b_value: str = ""
    source_c_label: str = ""
    source_c_value: str = ""
    result: str = ""  # "MATCH" / "MISMATCH"
    severity: Severity = Severity.PASS
    detail: str = ""


class OverallStatus(str, Enum):
    PASSED = "PASSED"
    RISK_FOUND = "RISK_FOUND"
    FAILED = "FAILED"


class AuditReport(BaseModel):
    overall_status: OverallStatus = OverallStatus.PASSED
    eflow_data: ExtractedData = Field(default_factory=ExtractedData)
    word_data: ExtractedData = Field(default_factory=ExtractedData)
    ocr_data: ExtractedData = Field(default_factory=ExtractedData)
    checks: list[CheckResult] = Field(default_factory=list)
    summary: str = ""
    llm_summary: dict = Field(default_factory=dict)  # LLM 生成的总结性字典
