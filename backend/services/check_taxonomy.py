"""Shared taxonomy for the two-layer/four-block checking framework."""

from backend.models.schemas import CheckResult


class TrafficLight:
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class BusinessStatus:
    PASS = "PASS"
    REVIEW = "REVIEW"
    NEED_FIX = "NEED_FIX"


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
    traffic_light: str | None = None,
    business_status: str | None = None,
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
    if traffic_light is not None:
        check.traffic_light = traffic_light
    if business_status is not None:
        check.business_status = business_status
    if not check.traffic_light:
        severity = str(check.severity)
        if severity.endswith("PASS"):
            check.traffic_light = TrafficLight.GREEN
        elif check.manual_confirmation_required:
            check.traffic_light = TrafficLight.YELLOW
        else:
            check.traffic_light = TrafficLight.RED
    if not check.business_status:
        if check.traffic_light == TrafficLight.GREEN:
            check.business_status = BusinessStatus.PASS
        elif check.traffic_light == TrafficLight.YELLOW:
            check.business_status = BusinessStatus.REVIEW
        else:
            check.business_status = BusinessStatus.NEED_FIX
    return check
