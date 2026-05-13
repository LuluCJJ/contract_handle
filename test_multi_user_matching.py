from backend.models.schemas import (
    DocExtractedData,
    EFlowData,
    PermissionScope,
    PlatformInfo,
    UserPermission,
)
from backend.services import hard_comparator


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
        account_status="In Use",
    )


def test_multi_user_object_matching():
    eflow = EFlowData(
        business_type="开通",
        business_scenario="开通企业网上银行并设置多级操作权限",
        platform=PlatformInfo(bank_name="中国银行"),
        users=[
            _user("Liu Yang", "454676800100123456", payment=True),
            _user("Wang Fang", "454676800100789012", authorize=True),
        ],
    )
    doc = DocExtractedData(
        source_type="word",
        scenario_type="OPEN",
        users=[
            _user("Liu Yang", "454676800100123456,454676800100789012", payment=True),
            _user("Wang Fang", "454676800100123456,454676800100789012", authorize=True),
        ],
    )

    checks = hard_comparator.run_hard_comparisons(eflow, doc)
    reason_codes = [check.reason_code for check in checks]

    assert reason_codes.count("USER_OBJECT_MATCH") == 2
    assert reason_codes.count("USER_PERMISSION_PAYMENT_MATCH") == 1
    assert reason_codes.count("USER_PERMISSION_AUTHORIZE_MATCH") == 1
    assert "EFLOW_USER_NOT_FOUND_IN_DOC" not in reason_codes
    assert "DOC_USER_NOT_IN_EFLOW" not in reason_codes


def test_extra_doc_user_requires_review():
    eflow = EFlowData(users=[_user("Liu Yang", "454676800100123456", query=True)])
    doc = DocExtractedData(
        source_type="word",
        scenario_type="OPEN",
        users=[
            _user("Liu Yang", "454676800100123456", query=True),
            _user("Extra User", "999999999999", payment=True),
        ],
    )

    checks = hard_comparator.run_hard_comparisons(eflow, doc)
    reason_codes = [check.reason_code for check in checks]

    assert "DOC_USER_NOT_IN_EFLOW" in reason_codes


if __name__ == "__main__":
    test_multi_user_object_matching()
    test_extra_doc_user_requires_review()
    print("multi-user matching smoke tests passed")
