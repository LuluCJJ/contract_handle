"""
Pydantic 数据模型 — 定义 API 请求/响应和内部数据结构
V3.0 - 支持四大类权限系统、多介质关联与多文档审计管线
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict, Any

# === 配置相关 ===

class LLMInstanceSettings(BaseModel):
    api_base: str
    api_key_masked: str
    model_name: str


class LLMSettingsRequest(BaseModel):
    api_type: str = "openai"
    api_base: str = Field(..., description="API 端点")
    api_key: str = Field(..., description="API Key")
    model_name: str = Field(..., description="模型名称")


class LLMSettingsResponse(BaseModel):
    api_type: str
    openai: LLMInstanceSettings
    requests: LLMInstanceSettings


# === 基础信息 ===

class PersonInfo(BaseModel):
    name: str = ""
    id_type: str = ""
    id_number: str = ""
    issue_date: str = ""
    expiry_date: str = ""
    role: str = ""
    phone: str = ""
    department: str = ""

class CompanyInfo(BaseModel):
    name: str = ""
    name_en: str = ""
    cert_type: str = ""
    cert_number: str = ""
    legal_representative: str = ""
    phone: str = ""
    industry: str = ""


class PlatformInfo(BaseModel):
    platform_code: str = ""
    platform_name: str = ""
    bank_name: str = ""
    bank_name_en: str = ""
    bank_short: str = ""
    country: str = ""
    branch_name: str = ""
    login_url: str = ""
    supported_languages: List[str] = Field(default_factory=list)


# === 权限 & 介质 (核心业务逻辑) ===

class PermissionScope(BaseModel):
    authorize: bool = False
    payment: bool = False
    query: bool = False
    upload: bool = False
    raw_text: str = ""

class MediaInfo(BaseModel):
    media_type: str = ""       # Token(OTP), 证书等
    media_number: str = ""
    is_blank: bool = False
    existing_media: str = ""   # 已有介质详情
    is_physical: bool = False
    needs_cancellation: bool = False

class UserPermission(BaseModel):
    """单用户、单账号维度的完整权限包"""
    user_name: str = ""
    permission_sub_type: str = ""
    permission_scope: PermissionScope = Field(default_factory=PermissionScope)
    account_number: str = ""
    account_name: str = ""
    account_name_en: str = ""
    account_status: str = ""
    account_type: str = ""          # 账户性质
    pay_receive_type: str = ""      # 收付款类型
    payment_id: str = ""            # 支付号
    query_id: str = ""              # 查询号
    company_code: str = ""          # 公司编码
    media: MediaInfo = Field(default_factory=MediaInfo)
    single_limit: float = 0.0
    daily_limit: float = 0.0
    action_on_permission: str = ""
    action_on_media: str = ""


# === EFlow & 文档数据标准 ===

class EFlowData(BaseModel):
    """标准的 EFlow 系统数据电子流"""
    flow_id: str = ""
    business_type: str = ""      # 开通/变更/销户等
    business_scenario: str = ""  # 具体业务场景
    platform: PlatformInfo = Field(default_factory=PlatformInfo)
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    applicant: PersonInfo = Field(default_factory=PersonInfo)
    users: List[UserPermission] = Field(default_factory=list)
    raw_text: str = ""

class DocExtractedData(BaseModel):
    """从单一文件(申请表词法/图片证件)中泛化提取的数据片段"""
    source_file: str = ""        # 来源文件名
    source_type: str = ""        # "word" or "ocr"
    business_activity: str = ""  # 识别出的整体业务动作
    scenario_type: str = ""      # OPEN / CANCEL / MODIFY / ATTACH / UNKNOWN
    action_type: str = ""        # OPEN_PERMISSION / CANCEL_PERMISSION / OPEN_MEDIA / CANCEL_MEDIA / UNKNOWN
    action_summary: str = ""
    evidence_summary: str = ""
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    # OCR主要提取这个
    persons: List[PersonInfo] = Field(default_factory=list)
    # 文档主要提取这个
    users: List[UserPermission] = Field(default_factory=list)
    raw_text: str = ""


# === 比对 & 报告结构 ===

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    PASS = "PASS"

class CheckResult(BaseModel):
    check_name: str
    category: str = "基本要素核对" # 默认为基本要素，支持：身份一致性、合规完整性、业务要素核对
    field_group: str = ""
    field_name: str = ""
    scenario_type: str = ""
    check_mode: str = ""
    source_a_label: str = "EFlow基准"
    source_a_value: str = ""
    source_b_label: str = "目标文档"
    source_b_value: str = ""
    result: str = ""  # "MATCH" / "MISMATCH"
    severity: Severity = Severity.PASS
    manual_confirmation_required: bool = False
    reason_code: str = ""
    detail: str = ""
    evidence: str = ""

class DocAnalysisReport(BaseModel):
    """单文档审查结果"""
    doc_name: str = ""
    doc_type: str = ""
    extracted_data: DocExtractedData = Field(default_factory=DocExtractedData)
    hard_checks: List[CheckResult] = Field(default_factory=list)
    semantic_checks: List[CheckResult] = Field(default_factory=list)

class OverallStatus(str, Enum):
    HIGH_RISK = "HIGH_RISK"
    MED_RISK = "MED_RISK"
    LOW_RISK = "LOW_RISK"
    ZERO_RISK = "ZERO_RISK"

class AuditReport(BaseModel):
    """贯穿全局的完整审查报告"""
    task_id: str = ""
    overall_status: OverallStatus = OverallStatus.ZERO_RISK
    eflow_data: EFlowData = Field(default_factory=EFlowData)
    document_reports: List[DocAnalysisReport] = Field(default_factory=list)
    cross_validation_checks: List[CheckResult] = Field(default_factory=list)
    summary: str = ""
    llm_summary: dict = Field(default_factory=dict)
    manual_confirmation_items: List[Dict[str, Any]] = Field(default_factory=list)
    scenario_summary: str = ""
