"""Shared taxonomy for the two-layer/four-block checking framework."""

from backend.models.schemas import CheckResult


class CheckLayer:
    EFLOW_BASED = "EFLOW_BASED"
    DOCUMENT_ONLY = "DOCUMENT_ONLY"


class CheckBlock:
    A1_EXACT = "A1_EXACT"
    A2_SEMANTIC = "A2_SEMANTIC"
    B1_SOP = "B1_SOP"
    B2_RISK_CLAUSE = "B2_RISK_CLAUSE"


def tag_check(
    check: CheckResult,
    *,
    layer: str,
    block: str,
    confidence: float | None = None,
    requires_config_review: bool | None = None,
    requires_engineering_change: bool | None = None,
) -> CheckResult:
    """Attach taxonomy metadata without changing the existing check semantics."""
    check.check_layer = layer
    check.check_block = block
    if confidence is not None:
        check.confidence = confidence
    if requires_config_review is not None:
        check.requires_config_review = requires_config_review
    if requires_engineering_change is not None:
        check.requires_engineering_change = requires_engineering_change
    return check
