from backend.routers.audit import _parse_eflow_v3
from backend.models.schemas import CheckResult, DocAnalysisReport, DocExtractedData, EFlowData, Severity
from backend.services.check_point_builder import build_check_points
from backend.services.check_taxonomy import CheckBlock, CheckLayer, tag_check
from backend.services.comparator import _should_skip_llm_check
from backend.services.sop_checker import run_sop_checks


def _company_payload():
    return {
        "flow_id": "EF2026051101",
        "business_type": "开通",
        "business_scenario": "权限开通",
        "platform": {
            "platform_code": "EB_DEMO",
            "platform_name": "Demo Online Banking",
            "platform_url": "xxxx",
            "bank_name": "Demo Bank Limited",
            "bank_short_name": "DBL",
            "branch_name": "Demo Tower Branch",
        },
        "users": [{
            "user_name": "sampleuser 00000001",
            "permission_sub_type": "Group D Authorized Signatory",
            "permission_scope": {"authorize": True, "payment": False, "query": True, "upload": False},
            "media": {"new_media_type": "Token(OTP)", "is_blank_media": "/"},
            "accounts": [
                {
                    "account_number": "7575XXXXX933",
                    "account_name_en": "ACME GLOBAL FINANCE CO., LIMITED",
                    "account_status": "In Use",
                    "permission_scope": {"authorize": True, "payment": False, "query": True, "upload": False},
                },
                {
                    "account_number": "20210XXXXXX902",
                    "account_name_en": "ACME GLOBAL FINANCE CO., LIMITED",
                    "account_status": "In Use",
                    "permission_scope": {"authorize": True, "payment": False, "query": True, "upload": False},
                },
            ],
        }],
    }


def test_company_payload_flattens_accounts_and_media():
    eflow = _parse_eflow_v3(_company_payload())

    assert eflow.platform.bank_short == "DBL"
    assert eflow.platform.login_url == "xxxx"
    assert eflow.users[0].account_number == "7575XXXXX933,20210XXXXXX902"
    assert eflow.users[0].account_status == "In Use"
    assert eflow.users[0].media.media_type == "Token(OTP)"
    assert eflow.users[0].permission_scope.authorize is True
    assert eflow.users[0].permission_scope.query is True


def test_open_doc_with_cancel_option_does_not_raise_b1_conflict():
    eflow = EFlowData(business_type="开通", business_scenario="权限开通")
    doc = DocExtractedData(
        source_type="word",
        scenario_type="OPEN",
        action_type="OPEN_PERMISSION",
        action_summary="表格中明确选择现有企业网上银行委托使用者，属于新增使用者的场景。",
        evidence_summary="文档命中新增，模板选项中也出现 Cancel 字样。",
    )

    checks = run_sop_checks(eflow, doc, "Cancel")
    assert "BUSINESS_SUBSTANCE_CONFLICT" not in [check.reason_code for check in checks]


def test_llm_noise_checks_are_skipped():
    eflow = _parse_eflow_v3(_company_payload())
    doc = DocExtractedData(source_type="word", scenario_type="OPEN")

    assert _should_skip_llm_check(eflow, doc, {
        "field_group": "platform",
        "field_name": "platform_code",
        "check_name": "平台编码缺失",
        "detail": "系统中平台编码为 EB_DEMO，但文档中平台编码为空",
    })
    assert _should_skip_llm_check(eflow, doc, {
        "field_group": "account",
        "field_name": "account_status",
        "check_name": "账户状态核对",
        "detail": "系统与文档中均未填写账户状态字段",
    })
    assert _should_skip_llm_check(eflow, doc, {
        "field_group": "media",
        "field_name": "needs_cancellation",
        "check_name": "介质注销状态核对",
        "detail": "系统与文档均未标记介质需要注销，且当前为开通场景",
    })


def test_check_point_uses_active_evidence_only_when_mixed():
    red = tag_check(CheckResult(
        check_name="办理事项实质冲突复核",
        field_group="business_scenario",
        field_name="scenario_conflict",
        source_a_label="业务SOP",
        source_a_value="EFlow登记场景：开通",
        source_b_label="材料扫描结果",
        source_b_value="Cancel",
        result="MISMATCH",
        severity=Severity.CRITICAL,
        reason_code="BUSINESS_SUBSTANCE_CONFLICT",
        detail="全文扫描发现与电子流办理方向相反的表述",
        evidence="Cancel",
    ), layer=CheckLayer.DOCUMENT_ONLY, block=CheckBlock.B1_SOP, traffic_light="RED")
    green = tag_check(CheckResult(
        check_name="办理事项一致",
        field_group="business_scenario",
        field_name="scenario_type",
        source_a_label="EFlow",
        source_a_value="开通",
        source_b_label="文档",
        source_b_value="开通",
        result="MATCH",
        severity=Severity.PASS,
        reason_code="SCENARIO_MATCH",
        detail="一致",
        evidence="OPEN",
    ), layer=CheckLayer.EFLOW_BASED, block=CheckBlock.A2_SEMANTIC, traffic_light="GREEN")
    points = build_check_points([DocAnalysisReport(doc_name="a.pdf", doc_type="word", semantic_checks=[red, green])])
    scenario = [point for point in points if point.key == "business_type"][0]

    assert scenario.traffic_light == "RED"
    assert len(scenario.evidence_items) == 1
    assert scenario.source_b_value == "材料扫描结果：Cancel"


if __name__ == "__main__":
    test_company_payload_flattens_accounts_and_media()
    test_open_doc_with_cancel_option_does_not_raise_b1_conflict()
    test_llm_noise_checks_are_skipped()
    test_check_point_uses_active_evidence_only_when_mixed()
    print("company payload regression tests passed")
