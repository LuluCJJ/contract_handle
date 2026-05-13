from backend.models.schemas import DocExtractedData, EFlowData, PermissionScope, PlatformInfo, UserPermission
from backend.services.hard_comparator import run_hard_comparisons
from backend.services.sop_checker import run_sop_checks


def _user(name, account, *, authorize=False, payment=False, query=False, upload=False):
    return UserPermission(
        user_name=name,
        account_number=account,
        permission_scope=PermissionScope(
            authorize=authorize,
            payment=payment,
            query=query,
            upload=upload,
        ),
    )


def test_open_maintenance_text_is_not_cancel_conflict():
    eflow = EFlowData(business_type="开通", business_scenario="新增网银操作员")
    doc = DocExtractedData(
        source_type="word",
        scenario_type="OPEN",
        action_type="OPEN_MEDIA",
        action_summary="文档勾选申请证书 2 张，并申请新增操作员网银盾。",
        evidence_summary="已有电子渠道码、已开通企业网银为背景信息；本次填写新增用户及权限配置。",
    )

    checks = run_sop_checks(
        eflow,
        doc,
        document_text="表格中出现更改服务、已有、已开通、申请证书、操作员网银盾新增、Cancel 说明项。",
    )

    assert "BUSINESS_SUBSTANCE_CONFLICT" not in [check.reason_code for check in checks]


def test_platform_check_uses_platform_group_and_ignores_code():
    eflow = EFlowData(
        platform=PlatformInfo(platform_code="SYS_001", bank_name="中国银行", branch_name="上海分行")
    )
    doc = DocExtractedData(
        source_type="word",
        platform=PlatformInfo(bank_name="中国银行", branch_name="上海分行"),
    )

    checks = run_hard_comparisons(eflow, doc)
    platform_checks = [check for check in checks if check.field_group == "platform"]

    assert [check.reason_code for check in platform_checks] == ["BANK_PLATFORM_MATCH", "BANK_BRANCH_MATCH"]
    assert all(check.field_name != "platform_code" for check in platform_checks)


def test_permission_scope_is_split_by_four_permissions():
    eflow = EFlowData(users=[_user("Liu Yang", "1001", query=True)])
    doc = DocExtractedData(
        source_type="word",
        users=[_user("Liu Yang", "1001", query=True, payment=True)],
    )

    checks = run_hard_comparisons(eflow, doc)
    reason_codes = [check.reason_code for check in checks]

    assert "USER_PERMISSION_QUERY_MATCH" in reason_codes
    assert "USER_PERMISSION_PAYMENT_EXCEEDS_EFLOW" in reason_codes
    assert "USER_PERMISSION_SCOPE_EXCEEDS_EFLOW" not in reason_codes


def test_maker_role_is_treated_as_payment_permission():
    eflow = EFlowData(users=[_user("Liu Yang", "1001", payment=True, query=True)])
    doc = DocExtractedData(
        source_type="word",
        users=[
            UserPermission(
                user_name="Liu Yang",
                account_number="1001",
                permission_sub_type="制单员",
                permission_scope=PermissionScope(query=True, raw_text="制单员"),
            )
        ],
    )

    checks = run_hard_comparisons(eflow, doc)
    reason_codes = [check.reason_code for check in checks]

    assert "USER_PERMISSION_PAYMENT_MATCH" in reason_codes
    assert "USER_PERMISSION_PAYMENT_MISSING" not in reason_codes
    assert "USER_PERMISSION_QUERY_EXCEEDS_EFLOW" not in reason_codes


if __name__ == "__main__":
    test_open_maintenance_text_is_not_cancel_conflict()
    test_platform_check_uses_platform_group_and_ignores_code()
    test_permission_scope_is_split_by_four_permissions()
    test_maker_role_is_treated_as_payment_permission()
    print("check-point regression tests passed")
