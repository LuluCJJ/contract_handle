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


class DemoStore:
    def __init__(self) -> None:
        self.scenarios: dict[str, Scenario] = {}
        self.templates: dict[str, Template] = {}
        self.template_versions: dict[str, TemplateVersion] = {}
        self.template_blocks: dict[str, list[TemplateBlock]] = {}
        self.template_plus: dict[str, TemplatePlus] = {}
        self.packages: dict[str, MaterialPackage] = {}
        self._seed()

    def _seed(self) -> None:
        scenario = Scenario(
            scenario_id="SCN-UBA-NG-USER-PERM",
            country="Nigeria",
            bank="UBA",
            channel="UBA Business Direct",
            activity_type="change",
            activity_subtype="user_permission_change",
            special_modes=["admin_mode"],
            description="尼日利亚 UBA 网银用户权限/介质变更",
        )
        self.scenarios[scenario.scenario_id] = scenario

        template = Template(
            template_id="TPL-UBA-TOKEN-REQUEST",
            template_name="UBA Token Request Form",
            country="Nigeria",
            bank="UBA",
            channel="UBA Business Direct",
            document_type="application_form",
        )
        self.templates[template.template_id] = template

        version = TemplateVersion(
            template_version_id="TPLV-UBA-TOKEN-V1",
            template_id=template.template_id,
            version="v1.0",
            fingerprint="demo-layout-text-hash",
            published_by="business_coe",
            published_at="2026-06-13",
        )
        self.template_versions[version.template_version_id] = version

        self.template_blocks[version.template_version_id] = [
            TemplateBlock(
                block_id="BLK-OPERATOR",
                template_version_id=version.template_version_id,
                block_name="操作员信息区",
                block_type="variable_field",
                business_meaning="记录本次申请的网银操作员",
                anchor_text="Operator Name",
                expected_eflow_path="users.0.name",
                fill_instruction="应填写电子流中的操作员姓名，与证件姓名保持一致。",
                check_type="normalized_match",
            ),
            TemplateBlock(
                block_id="BLK-PERMISSION",
                template_version_id=version.template_version_id,
                block_name="权限区",
                block_type="variable_field",
                business_meaning="记录本次申请开通或变更的网银权限",
                anchor_text="Permissions",
                expected_eflow_path="users.0.permissions",
                fill_instruction="权限应与电子流变化项一致，不应出现额外付款或审批权限。",
                check_type="contains_all",
                ai_required=True,
            ),
            TemplateBlock(
                block_id="BLK-MEDIA",
                template_version_id=version.template_version_id,
                block_name="介质区",
                block_type="variable_field",
                business_meaning="记录 Token、OTP 等安全介质",
                anchor_text="Media",
                expected_eflow_path="users.0.media",
                fill_instruction="介质类型应与电子流一致。",
                check_type="contains_all",
            ),
        ]

        baseline_text = "\n".join(
            [
                "Company Name: Huawei Technologies Company (Nigeria) Limited",
                "Account Number: 102XXXX804",
                "Platform: UBA Business Direct",
                "Operator Name: <operator_name>",
                "Permissions: query, payment",
                "Media: Token, OTP",
                "Declaration: The company confirms the above request follows approved internal authorization.",
            ]
        )
        self.template_plus["TPLP-UBA-TOKEN-V1"] = TemplatePlus(
            template_plus_id="TPLP-UBA-TOKEN-V1",
            template_version_id=version.template_version_id,
            plus_version="v1.0",
            description="已预填固定公司信息、固定声明、标准权限逻辑的 UBA Token 申请模板",
            fixed_content_policy="固定公司信息、平台、账号和声明不应异常删改。",
            variable_slots=["operator_name", "application_date"],
            baseline_text=baseline_text,
            expected_contents=[
                ExpectedContent(
                    expected_content_id="EXP-COMPANY",
                    content_type="fixed",
                    business_meaning="公司名称",
                    expected_value="Huawei Technologies Company (Nigeria) Limited",
                    source="template_fixed",
                    check_policy="must_not_change",
                ),
                ExpectedContent(
                    expected_content_id="EXP-ACCOUNT",
                    content_type="fixed",
                    business_meaning="账号",
                    expected_value="102XXXX804",
                    source="template_fixed",
                    check_policy="must_not_change",
                ),
                ExpectedContent(
                    expected_content_id="EXP-OPERATOR",
                    content_type="variable",
                    business_meaning="操作员姓名",
                    expected_value="<operator_name>",
                    source="eflow.users.0.name",
                    check_policy="must_match_eflow",
                ),
            ],
        )

        eflow = EFlow(
            eflow_id="EF-UBA-001",
            applicant="Yingqi Guo",
            company="Huawei Technologies Company (Nigeria) Limited",
            bank="UBA",
            platform="UBA Business Direct",
            account_name="Huawei Technologies Company (Nigeria) Limited",
            account_number="102XXXX804",
            users=[
                EFlowUser(
                    name="Yingqi Guo",
                    role="Payment User",
                    permissions=["payment", "query"],
                    media=["Token", "OTP"],
                    identity_doc_no="PXXXXXX",
                )
            ],
            change_items=["user", "permission", "media"],
        )
        submitted_text = "\n".join(
            [
                "Company Name: Huawei Technologies Nigeria Ltd.",
                "Account Number: 102XXXX804",
                "Platform: UBA Business Direct",
                "Operator Name: Yingqi Guo",
                "Permissions: query, payment, admin approval",
                "Media: Token",
                "Declaration: The company confirms the above request follows approved internal authorization.",
                "Additional Clause: User may approve transactions above standard workflow threshold.",
            ]
        )
        package = MaterialPackage(
            package_id="PKG-DEMO-001",
            scenario_id=scenario.scenario_id,
            eflow=eflow,
            submitted_documents=[
                SubmittedDocument(
                    document_id="DOC-UBA-TOKEN-FILLED",
                    package_id="PKG-DEMO-001",
                    file_name="filled_uba_token_request.txt",
                    file_type="txt",
                    matched_template_version_id=version.template_version_id,
                    match_confidence=0.92,
                    match_status="matched",
                    text=submitted_text,
                )
            ],
            expected_template_set=[version.template_version_id],
        )
        self.packages[package.package_id] = package


store = DemoStore()

