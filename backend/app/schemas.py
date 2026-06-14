from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.app.core.enums import CheckStatus, DiffClassification, EvidenceSourceType, RiskLevel, StrategyName


class Scenario(BaseModel):
    scenario_id: str
    country: str
    bank: str
    channel: str
    activity_type: str
    activity_subtype: str
    special_modes: list[str] = Field(default_factory=list)
    description: str


class EFlowUser(BaseModel):
    name: str
    role: str
    permissions: list[str]
    media: list[str]
    identity_doc_no: str
    identity_doc_type: str = "Passport"
    identity_expiry_date: str | None = None
    account_number: str | None = None
    single_limit: float | None = None
    daily_limit: float | None = None


class EFlow(BaseModel):
    eflow_id: str
    applicant: str
    company: str
    bank: str
    platform: str
    account_name: str
    account_number: str
    users: list[EFlowUser]
    change_items: list[str]
    activity: str = "open"


class Template(BaseModel):
    template_id: str
    template_name: str
    country: str
    bank: str
    channel: str
    document_type: str
    status: Literal["active", "inactive"] = "active"


class TemplateVersion(BaseModel):
    template_version_id: str
    template_id: str
    version: str
    fingerprint: str
    published_by: str
    published_at: str


class TemplateBlock(BaseModel):
    block_id: str
    template_version_id: str
    block_name: str
    block_type: str
    business_meaning: str
    anchor_text: str
    expected_eflow_path: str | None = None
    fill_instruction: str
    check_type: str
    ai_required: bool = False


class ExpectedContent(BaseModel):
    expected_content_id: str
    content_type: Literal["fixed", "variable", "optional", "instruction_only"]
    business_meaning: str
    expected_value: str
    source: str
    check_policy: str


class TemplatePlus(BaseModel):
    template_plus_id: str
    template_version_id: str
    plus_version: str
    description: str
    fixed_content_policy: str
    variable_slots: list[str]
    baseline_text: str
    expected_contents: list[ExpectedContent]


class SubmittedDocument(BaseModel):
    document_id: str
    package_id: str
    file_name: str
    file_type: str
    matched_template_version_id: str
    match_confidence: float
    match_status: Literal["matched", "suspected", "unmatched"]
    text: str


class Evidence(BaseModel):
    evidence_id: str
    document_id: str
    page: int = 1
    bbox: list[float] | None = None
    text: str
    source_type: EvidenceSourceType


class CheckResult(BaseModel):
    result_id: str
    package_id: str
    strategy: StrategyName
    check_item: str
    status: CheckStatus
    risk_level: RiskLevel
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    owner: Literal["code", "config", "agent", "human", "hybrid"] = "code"
    manual_confirm_required: bool = False
    suggested_action: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class DocumentDiff(BaseModel):
    diff_id: str
    diff_type: Literal["added", "deleted", "modified"]
    baseline_text: str
    submitted_text: str
    classification: DiffClassification = DiffClassification.UNKNOWN
    evidence_ids: list[str] = Field(default_factory=list)


class StrategyMetrics(BaseModel):
    strategy: StrategyName
    runtime_seconds: float
    llm_calls: int
    manual_config_cost: Literal["low", "medium", "high"]
    detected_issues_count: int
    reviewer_rating: int | None = None
    notes: str = ""


class ReviewReport(BaseModel):
    report_id: str
    package_id: str
    strategy: StrategyName
    status: Literal["completed", "failed"] = "completed"
    scenario: Scenario
    summary: str
    results: list[CheckResult]
    evidences: list[Evidence]
    metrics: StrategyMetrics


class MaterialPackage(BaseModel):
    package_id: str
    scenario_id: str
    eflow: EFlow
    submitted_documents: list[SubmittedDocument]
    identity_documents: list[SubmittedDocument] = Field(default_factory=list)
    expected_template_set: list[str]
    selected_strategy: StrategyName = StrategyName.BLOCK_RULE_CHECK


class RunPreauditRequest(BaseModel):
    strategy: StrategyName
    options: dict[str, Any] = Field(default_factory=dict)


class RunComparisonRequest(BaseModel):
    strategies: list[StrategyName]
    options: dict[str, Any] = Field(default_factory=dict)


class ComparisonResponse(BaseModel):
    package_id: str
    reports: list[ReviewReport]


class UploadedTextFile(BaseModel):
    file_name: str
    file_type: str = "txt"
    text: str = ""


class CreateUploadPackageRequest(BaseModel):
    package_id: str | None = None
    scenario_id: str = "SCN-GENERIC-ONLINE-BANKING"
    company: str
    bank: str = "Demo Bank"
    platform: str = "Corporate Online Banking"
    activity: str = "open"
    account_number: str
    user_name: str
    user_role: str = "Payment User"
    identity_doc_type: str = "Passport"
    identity_doc_no: str
    permissions: list[str] = Field(default_factory=lambda: ["query", "payment"])
    media: list[str] = Field(default_factory=lambda: ["Token"])
    single_limit: float | None = 500000
    daily_limit: float | None = None
    submitted_files: list[UploadedTextFile] = Field(default_factory=list)
    identity_files: list[UploadedTextFile] = Field(default_factory=list)
    template_file: UploadedTextFile | None = None


class CreateUploadPackageResponse(BaseModel):
    package_id: str
    package: MaterialPackage
    template_version_id: str
    notes: list[str] = Field(default_factory=list)
