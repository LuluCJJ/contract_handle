from dataclasses import dataclass

from backend.app.schemas import (
    EFlow,
    EFlowUser,
    ExpectedContent,
    MaterialPackage,
    Scenario,
    SubmittedDocument,
    Template,
    TemplateBlock,
    TemplatePlus,
    TemplateVersion,
)


@dataclass(frozen=True)
class DemoCase:
    package_id: str
    source_case: str
    title: str
    expected_focus: str
    expected_risk: str
    demo_story: str


class DemoStore:
    def __init__(self) -> None:
        self.scenarios: dict[str, Scenario] = {}
        self.templates: dict[str, Template] = {}
        self.template_versions: dict[str, TemplateVersion] = {}
        self.template_blocks: dict[str, list[TemplateBlock]] = {}
        self.template_plus: dict[str, TemplatePlus] = {}
        self.packages: dict[str, MaterialPackage] = {}
        self.demo_cases: dict[str, DemoCase] = {}
        self._seed()

    def _seed(self) -> None:
        self._seed_common_objects()
        self._seed_demo_cases()

    def _seed_common_objects(self) -> None:
        scenarios = [
            Scenario(
                scenario_id="SCN-GENERIC-ONLINE-BANKING",
                country="Multi-country",
                bank="Multi-bank",
                channel="Corporate Online Banking",
                activity_type="open_or_change",
                activity_subtype="user_permission_media_account",
                description="企业网银用户、权限、介质、账号与证件预审通用场景",
            ),
            Scenario(
                scenario_id="SCN-UBA-NG-USER-PERM",
                country="Nigeria",
                bank="UBA",
                channel="UBA Business Direct",
                activity_type="change",
                activity_subtype="user_permission_change",
                special_modes=["admin_mode"],
                description="尼日利亚 UBA 网银用户权限/介质变更",
            ),
        ]
        self.scenarios.update({item.scenario_id: item for item in scenarios})

        template = Template(
            template_id="TPL-CORP-ONLINE-BANKING",
            template_name="Corporate Online Banking Application",
            country="Multi-country",
            bank="Multi-bank",
            channel="Corporate Online Banking",
            document_type="application_form",
        )
        self.templates[template.template_id] = template

        version = TemplateVersion(
            template_version_id="TPLV-CORP-ONLINE-BANKING-V1",
            template_id=template.template_id,
            version="v1.0",
            fingerprint="demo-key-value-text-hash",
            published_by="business_coe",
            published_at="2026-06-15",
        )
        self.template_versions[version.template_version_id] = version

        self.template_blocks[version.template_version_id] = [
            TemplateBlock(
                block_id="BLK-ACTIVITY",
                template_version_id=version.template_version_id,
                block_name="办理事项",
                block_type="variable_field",
                business_meaning="判断本次材料是开通、变更还是注销",
                anchor_text="Activity",
                expected_eflow_path="activity",
                fill_instruction="办理事项应与电子流场景一致，不能把开通材料填成注销。",
                check_type="activity_match",
                ai_required=True,
            ),
            TemplateBlock(
                block_id="BLK-USER-COUNT",
                template_version_id=version.template_version_id,
                block_name="操作员数量",
                block_type="variable_field",
                business_meaning="确认材料中的操作员数量与电子流一致",
                anchor_text="User Count",
                expected_eflow_path="users_count",
                fill_instruction="多操作员场景不得漏填或多填操作员。",
                check_type="count_match",
            ),
            TemplateBlock(
                block_id="BLK-OPERATOR",
                template_version_id=version.template_version_id,
                block_name="操作员姓名",
                block_type="variable_field",
                business_meaning="记录本次申请的网银操作员",
                anchor_text="Operator Name",
                expected_eflow_path="users.0.name",
                fill_instruction="应填写电子流中的操作员姓名，与证件姓名保持一致。",
                check_type="normalized_match",
            ),
            TemplateBlock(
                block_id="BLK-ID-NO",
                template_version_id=version.template_version_id,
                block_name="证件号码",
                block_type="variable_field",
                business_meaning="核对操作员证件号",
                anchor_text="Identity Doc No",
                expected_eflow_path="users.0.identity_doc_no",
                fill_instruction="证件号码应与电子流和证件材料一致。",
                check_type="normalized_match",
            ),
            TemplateBlock(
                block_id="BLK-ID-TYPE",
                template_version_id=version.template_version_id,
                block_name="证件类型",
                block_type="variable_field",
                business_meaning="核对身份证、护照等证件类型",
                anchor_text="Identity Doc Type",
                expected_eflow_path="users.0.identity_doc_type",
                fill_instruction="证件类型应与电子流要求一致。",
                check_type="normalized_match",
            ),
            TemplateBlock(
                block_id="BLK-ACCOUNT",
                template_version_id=version.template_version_id,
                block_name="账号",
                block_type="variable_field",
                business_meaning="核对申请材料中的账号",
                anchor_text="Account Number",
                expected_eflow_path="account_number",
                fill_instruction="账号应与电子流账户一致，不应错填账号前缀或尾号。",
                check_type="normalized_match",
            ),
            TemplateBlock(
                block_id="BLK-PERMISSION",
                template_version_id=version.template_version_id,
                block_name="权限范围",
                block_type="variable_field",
                business_meaning="记录本次申请开通或变更的网银权限",
                anchor_text="Permissions",
                expected_eflow_path="users.0.permissions",
                fill_instruction="权限应与电子流变化项一致，不应出现额外付款、审批或管理权限。",
                check_type="contains_all",
                ai_required=True,
            ),
            TemplateBlock(
                block_id="BLK-MEDIA",
                template_version_id=version.template_version_id,
                block_name="介质",
                block_type="variable_field",
                business_meaning="记录 Token、U盾、OTP 等安全介质",
                anchor_text="Media",
                expected_eflow_path="users.0.media",
                fill_instruction="介质类型应与电子流一致。",
                check_type="contains_all",
            ),
            TemplateBlock(
                block_id="BLK-SINGLE-LIMIT",
                template_version_id=version.template_version_id,
                block_name="单笔限额",
                block_type="risk_field",
                business_meaning="识别高限额申请是否需要人工关注",
                anchor_text="Single Limit",
                expected_eflow_path="users.0.single_limit",
                fill_instruction="高于 500 万的单笔限额需要额外授权或人工确认。",
                check_type="max_limit_review",
                ai_required=True,
            ),
        ]

        baseline_text = "\n".join(
            [
                "Activity: open",
                "User Count: 1",
                "Company Name: <company>",
                "Account Number: <account_number>",
                "Operator Name: <operator_name>",
                "Identity Doc Type: <identity_doc_type>",
                "Identity Doc No: <identity_doc_no>",
                "Permissions: query, payment",
                "Media: Token",
                "Single Limit: <single_limit>",
                "Declaration: Standard corporate online banking application terms remain unchanged.",
            ]
        )
        self.template_plus["TPLP-CORP-ONLINE-BANKING-V1"] = TemplatePlus(
            template_plus_id="TPLP-CORP-ONLINE-BANKING-V1",
            template_version_id=version.template_version_id,
            plus_version="v1.0",
            description="通用模板 Plus：预置固定声明、标准字段和高风险差异政策",
            fixed_content_policy="固定声明、公司名称、账号、标准权限与业务场景不应异常删改。",
            variable_slots=[
                "company",
                "account_number",
                "operator_name",
                "identity_doc_type",
                "identity_doc_no",
                "single_limit",
            ],
            baseline_text=baseline_text,
            expected_contents=[
                ExpectedContent(
                    expected_content_id="EXP-DECLARATION",
                    content_type="fixed",
                    business_meaning="固定声明",
                    expected_value="Standard corporate online banking application terms remain unchanged.",
                    source="template_fixed",
                    check_policy="must_not_change",
                ),
                ExpectedContent(
                    expected_content_id="EXP-ACTIVITY",
                    content_type="variable",
                    business_meaning="办理事项",
                    expected_value="<activity>",
                    source="eflow.activity",
                    check_policy="must_match_eflow",
                ),
                ExpectedContent(
                    expected_content_id="EXP-ACCOUNT",
                    content_type="variable",
                    business_meaning="账号",
                    expected_value="<account_number>",
                    source="eflow.account_number",
                    check_policy="must_match_eflow",
                ),
            ],
        )

    def _seed_demo_cases(self) -> None:
        cases = [
            self._case(
                package_id="PKG-CASE-001-PASS",
                source_case="case_001_pass",
                title="[正例] CCB 建行：字段完全一致",
                expected_focus="基础字段一致性",
                expected_risk="low",
                user_name="张光",
                doc_no="ID442015",
                doc_type="ID Card",
                account="4420156430005200",
                permissions=["authorize", "payment", "query"],
                media=["U盾/Token"],
                single_limit=500000,
            ),
            self._case(
                package_id="PKG-CASE-003-ID-MISMATCH",
                source_case="case_003_fail_id",
                title="[负例] CCB 建行：证件号不一致",
                expected_focus="证件号码",
                expected_risk="high",
                user_name="张光",
                doc_no="ID442015",
                doc_type="ID Card",
                account="4420156430005200",
                submitted_overrides={"Identity Doc No": "ID999999"},
            ),
            self._case(
                package_id="PKG-CASE-004-NAME-MISMATCH",
                source_case="case_004_fail_name",
                title="[负例] BOC 中行：操作员姓名不一致",
                expected_focus="操作员身份",
                expected_risk="high",
                user_name="SANTA CLAUS",
                doc_no="P12345678",
                doc_type="Passport",
                account="C12345XXXXXXX",
                submitted_overrides={"Operator Name": "CLAIRE BENNETT"},
            ),
            self._case(
                package_id="PKG-CASE-005-ACTIVITY-RISK",
                source_case="case_005_risk_activity",
                title="[风险] CCB 建行：电子流开通，材料勾选注销",
                expected_focus="办理事项",
                expected_risk="medium",
                user_name="张光",
                doc_no="ID442015",
                doc_type="ID Card",
                account="4420156430005200",
                submitted_overrides={"Activity": "Cancellation"},
            ),
            self._case(
                package_id="PKG-CASE-006-ACCOUNT-RISK",
                source_case="case_006_risk_account",
                title="[风险] BOC 中行：账号前缀/尾号不一致",
                expected_focus="账号",
                expected_risk="medium",
                user_name="SANTA CLAUS",
                doc_no="P12345678",
                doc_type="Passport",
                account="C12345XXXXXXX",
                submitted_overrides={"Account Number": "C54321XXXXXXX"},
            ),
            self._case(
                package_id="PKG-CASE-007-IDTYPE-RISK",
                source_case="case_007_risk_idtype",
                title="[风险] BOC 中行：电子流身份证，材料使用护照",
                expected_focus="证件类型",
                expected_risk="medium",
                user_name="SANTA CLAUS",
                doc_no="ID884422",
                doc_type="ID Card",
                account="C12345XXXXXXX",
                submitted_overrides={"Identity Doc Type": "Passport"},
            ),
            self._case(
                package_id="PKG-CASE-015-MULTI-PASS",
                source_case="case_015_boc_multi_pass",
                title="[正例] BOC 国内：多操作员场景",
                expected_focus="多操作员数量与首位操作员核对",
                expected_risk="low",
                user_name="Liu Yang",
                doc_no="P-LIU-001",
                doc_type="Passport",
                account="454676800100123456,454676800100789012",
                permissions=["payment"],
                media=["Token"],
                single_limit=500000,
                extra_users=[
                    EFlowUser(
                        name="Wang Fang",
                        role="Reviewer",
                        permissions=["authorize", "query"],
                        media=["Token"],
                        identity_doc_no="P-WANG-002",
                        identity_doc_type="Passport",
                        account_number="454676800100123456,454676800100789012",
                        single_limit=500000,
                    )
                ],
                submitted_overrides={"User Count": "2"},
            ),
            self._case(
                package_id="PKG-CASE-021-HIGH-LIMIT",
                source_case="case_021_ccb_high_limit",
                title="[风险] CCB 建行：珠宝贸易高限额",
                expected_focus="高限额与敏感行业",
                expected_risk="high",
                user_name="赵强",
                doc_no="ID-ZQ-001",
                doc_type="ID Card",
                account="4420123456780001",
                permissions=["payment", "query"],
                media=["U盾/Token"],
                single_limit=10000000,
                submitted_overrides={
                    "Industry": "Jewelry and gold trading",
                    "Additional Clause": "High limit requested for sensitive industry treasury payments.",
                },
            ),
            self._case(
                package_id="PKG-DEMO-001",
                source_case="manual_uba_template_plus",
                title="[风险] UBA：新增 admin approval 与超标准审批条款",
                expected_focus="模板 Plus 差异与职责分离",
                expected_risk="high",
                user_name="Yingqi Guo",
                doc_no="PXXXXXX",
                doc_type="Passport",
                account="102XXXX804",
                company="Huawei Technologies Company (Nigeria) Limited",
                scenario_id="SCN-UBA-NG-USER-PERM",
                bank="UBA",
                platform="UBA Business Direct",
                permissions=["payment", "query"],
                media=["Token", "OTP"],
                submitted_overrides={
                    "Company Name": "Huawei Technologies Nigeria Ltd.",
                    "Permissions": "query, payment, admin approval",
                    "Media": "Token",
                    "Additional Clause": "User may approve transactions above standard workflow threshold.",
                },
            ),
        ]
        for package, case in cases:
            self.packages[package.package_id] = package
            self.demo_cases[package.package_id] = case

    def _case(
        self,
        package_id: str,
        source_case: str,
        title: str,
        expected_focus: str,
        expected_risk: str,
        user_name: str,
        doc_no: str,
        doc_type: str,
        account: str,
        permissions: list[str] | None = None,
        media: list[str] | None = None,
        single_limit: float = 500000,
        company: str = "Demo Corporate Customer Limited",
        scenario_id: str = "SCN-GENERIC-ONLINE-BANKING",
        bank: str = "Demo Bank",
        platform: str = "Corporate Online Banking",
        activity: str = "open",
        extra_users: list[EFlowUser] | None = None,
        submitted_overrides: dict[str, str] | None = None,
    ) -> tuple[MaterialPackage, DemoCase]:
        permissions = permissions or ["authorize", "payment", "query"]
        media = media or ["Token"]
        user = EFlowUser(
            name=user_name,
            role="Payment User",
            permissions=permissions,
            media=media,
            identity_doc_no=doc_no,
            identity_doc_type=doc_type,
            account_number=account,
            single_limit=single_limit,
        )
        users = [user] + (extra_users or [])
        eflow = EFlow(
            eflow_id=f"EF-{package_id}",
            applicant=user_name,
            company=company,
            bank=bank,
            platform=platform,
            account_name=company,
            account_number=account,
            users=users,
            change_items=["activity", "user", "permission", "media", "account", "identity"],
            activity=activity,
        )
        submitted = {
            "Activity": activity,
            "User Count": str(len(users)),
            "Company Name": company,
            "Account Number": account,
            "Operator Name": user_name,
            "Identity Doc Type": doc_type,
            "Identity Doc No": doc_no,
            "Permissions": ", ".join(permissions),
            "Media": ", ".join(media),
            "Single Limit": str(int(single_limit)),
            "Declaration": "Standard corporate online banking application terms remain unchanged.",
        }
        submitted.update(submitted_overrides or {})
        submitted_text = "\n".join(f"{key}: {value}" for key, value in submitted.items())
        package = MaterialPackage(
            package_id=package_id,
            scenario_id=scenario_id,
            eflow=eflow,
            submitted_documents=[
                SubmittedDocument(
                    document_id=f"DOC-{package_id}",
                    package_id=package_id,
                    file_name=f"{source_case}.txt",
                    file_type="txt",
                    matched_template_version_id="TPLV-CORP-ONLINE-BANKING-V1",
                    match_confidence=0.95,
                    match_status="matched",
                    text=submitted_text,
                )
            ],
            expected_template_set=["TPLV-CORP-ONLINE-BANKING-V1"],
        )
        case = DemoCase(
            package_id=package_id,
            source_case=source_case,
            title=title,
            expected_focus=expected_focus,
            expected_risk=expected_risk,
            demo_story=f"源自旧方案测试数据 {source_case}，用于验证新方案中的 {expected_focus}。",
        )
        return package, case


store = DemoStore()
