from backend.models.schemas import CheckResult, DocAnalysisReport, Severity
from backend.services.check_point_builder import build_check_points
from backend.services.check_taxonomy import CheckBlock, CheckLayer, tag_check


def _check(name, group, field, reason, light, a, b, detail=""):
    severity = Severity.PASS if light == "GREEN" else Severity.WARNING
    return tag_check(
        CheckResult(
            check_name=name,
            field_group=group,
            field_name=field,
            reason_code=reason,
            source_a_label="EFlow",
            source_a_value=a,
            source_b_label="材料",
            source_b_value=b,
            result="MATCH" if light == "GREEN" else "REVIEW",
            severity=severity,
            manual_confirmation_required=light == "YELLOW",
            detail=detail or name,
        ),
        layer=CheckLayer.EFLOW_BASED,
        block=CheckBlock.A1_EXACT,
        traffic_light=light,
    )


def test_identity_checks_are_merged_into_one_business_point():
    report = DocAnalysisReport(
        doc_name="bank_app.docx",
        doc_type="word",
        hard_checks=[
            _check("操作员对象匹配", "subject", "user_object", "USER_OBJECT_MATCH", "GREEN", "Liu Yang", "Liu Yang"),
            _check("申请人一致性检查", "subject", "applicant_name", "APPLICANT_INFO_MISSING", "YELLOW", "Liu Yang", ""),
            _check("证件实体收录核查", "subject", "person_whitelist", "PERSON_NOT_IN_EFLOW_WHITELIST", "YELLOW", "姓名池:Liu Yang", "Wang Jun"),
        ],
    )

    points = build_check_points([report])
    identity_points = [point for point in points if point.key == "identity_name"]

    assert len(identity_points) == 1
    assert identity_points[0].title == "操作员身份"
    assert identity_points[0].traffic_light == "YELLOW"
    assert len(identity_points[0].evidence_items) == 3
    assert "Liu Yang" in identity_points[0].source_a_value
    assert "Wang Jun" in identity_points[0].source_b_value


def test_permission_checks_are_one_business_point_with_evidence_rows():
    report = DocAnalysisReport(
        doc_name="bank_app.docx",
        doc_type="word",
        hard_checks=[
            _check("授权权限核对", "permission", "permission_authorize", "USER_PERMISSION_AUTHORIZE_MATCH", "GREEN", "需要", "出现"),
            _check("支付权限核对", "permission", "permission_payment", "USER_PERMISSION_PAYMENT_MISSING", "YELLOW", "需要", "未稳定识别"),
        ],
    )

    points = build_check_points([report])
    permission_points = [point for point in points if point.key == "permission_scope"]

    assert len(permission_points) == 1
    assert permission_points[0].title == "权限范围"
    assert permission_points[0].traffic_light == "YELLOW"
    assert "支付/转账" in permission_points[0].summary
    assert len(permission_points[0].evidence_items) == 2


if __name__ == "__main__":
    test_identity_checks_are_merged_into_one_business_point()
    test_permission_checks_are_one_business_point_with_evidence_rows()
    print("check point builder tests passed")
