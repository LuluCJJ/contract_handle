from enum import Enum


class CheckStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    NEED_CONFIRM = "need_confirm"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    NOT_CHECKED = "not_checked"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrategyName(str, Enum):
    BLOCK_RULE_CHECK = "block_rule_check"
    TEMPLATE_PLUS_DIFF = "template_plus_diff"
    FULL_AGENT_REVIEW = "full_agent_review"
    HYBRID_REVIEW = "hybrid_review"


class DiffClassification(str, Enum):
    EFLOW_CHANGE = "eflow_change"
    ACCEPTABLE_FILL = "acceptable_fill"
    TEMPLATE_DEVIATION = "template_deviation"
    POTENTIAL_RISK = "potential_risk"
    UNKNOWN = "unknown"


class EvidenceSourceType(str, Enum):
    SUBMITTED_DOCUMENT = "submitted_document"
    TEMPLATE = "template"
    EFLOW = "eflow"
    IDENTITY_DOC = "identity_doc"
    TEMPLATE_PLUS = "template_plus"

