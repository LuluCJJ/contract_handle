from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.enums import StrategyName
from backend.app.data_store import LEGACY_TEST_DATA_ROOT, store
from backend.app.frontend import FRONTEND_HTML
from backend.app.schemas import (
    ComparisonResponse,
    CreateUploadPackageRequest,
    CreateUploadPackageResponse,
    EFlow,
    EFlowUser,
    ExpectedContent,
    MaterialPackage,
    RunComparisonRequest,
    RunPreauditRequest,
    SubmittedDocument,
    TemplatePlus,
    TemplateVersion,
    UploadedTextFile,
)
from backend.app.services.strategy_runner_service import StrategyRunnerService


DEFAULT_TEMPLATE_VERSION_ID = "TPLV-CORP-ONLINE-BANKING-V1"

app = FastAPI(title="Bank Document Preaudit POC", version="0.2.0")
runner = StrategyRunnerService()

if LEGACY_TEST_DATA_ROOT.exists():
    app.mount("/case-files", StaticFiles(directory=str(LEGACY_TEST_DATA_ROOT)), name="case-files")


@app.get("/", response_class=HTMLResponse)
def demo_page() -> str:
    return FRONTEND_HTML


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/scenarios")
def list_scenarios():
    return list(store.scenarios.values())


@app.get("/api/templates")
def list_templates():
    return {
        "templates": list(store.templates.values()),
        "template_versions": list(store.template_versions.values()),
        "template_blocks": store.template_blocks,
        "template_plus": list(store.template_plus.values()),
    }


@app.get("/api/packages")
def list_packages():
    return list(store.packages.values())


@app.get("/api/demo-cases")
def list_demo_cases():
    return [
        {
            "package_id": case.package_id,
            "source_case": case.source_case,
            "title": case.title,
            "expected_focus": case.expected_focus,
            "expected_risk": case.expected_risk,
            "demo_story": case.demo_story,
        }
        for case in store.demo_cases.values()
    ]


@app.get("/api/packages/{package_id}")
def get_package(package_id: str):
    package = store.packages.get(package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return package


@app.get("/api/strategies")
def list_strategies():
    return [
        {
            "strategy": StrategyName.BLOCK_RULE_CHECK,
            "demo": "Demo1",
            "description": "区块级字段、权限、介质、限额等确定性规则检查。",
        },
        {
            "strategy": StrategyName.TEMPLATE_PLUS_DIFF,
            "demo": "Demo2",
            "description": "把提交材料与 Template Plus 基准做差异识别，并交给模型解释高风险变化。",
        },
        {
            "strategy": StrategyName.FULL_AGENT_REVIEW,
            "demo": "Demo3",
            "description": "受约束的全文 Agent 复核，用于兜底发现非结构化风险。",
        },
        {
            "strategy": StrategyName.HYBRID_REVIEW,
            "demo": "Future",
            "description": "混合策略预留入口。",
        },
    ]


@app.post("/api/upload-package", response_model=CreateUploadPackageResponse)
def create_upload_package(request: CreateUploadPackageRequest):
    if request.scenario_id not in store.scenarios:
        raise HTTPException(status_code=400, detail="Unknown scenario_id")

    package_id = request.package_id or f"PKG-UPLOAD-{uuid4().hex[:8].upper()}"
    if package_id in store.packages:
        raise HTTPException(status_code=409, detail="Package already exists")

    template_version_id, notes = _prepare_template_version(package_id, request)
    eflow = _build_eflow(package_id, request)
    submitted_documents = _build_submitted_documents(package_id, template_version_id, request)
    identity_documents = [
        SubmittedDocument(
            document_id=f"ID-{package_id}-{index + 1}",
            package_id=package_id,
            file_name=file.file_name,
            file_type=file.file_type,
            matched_template_version_id=template_version_id,
            match_confidence=0.3,
            match_status="suspected",
            text=file.text,
        )
        for index, file in enumerate(request.identity_files)
    ]

    package = MaterialPackage(
        package_id=package_id,
        scenario_id=request.scenario_id,
        eflow=eflow,
        submitted_documents=submitted_documents,
        identity_documents=identity_documents,
        expected_template_set=[template_version_id],
    )
    store.packages[package_id] = package
    return CreateUploadPackageResponse(
        package_id=package_id,
        package=package,
        template_version_id=template_version_id,
        notes=notes,
    )


@app.post("/api/packages/{package_id}/run-preaudit")
def run_preaudit(package_id: str, request: RunPreauditRequest):
    if package_id not in store.packages:
        raise HTTPException(status_code=404, detail="Package not found")
    use_mock = bool(request.options.get("use_mock_llm", False))
    return runner.run(package_id, request.strategy, use_mock_llm=use_mock)


@app.post("/api/packages/{package_id}/run-comparison", response_model=ComparisonResponse)
def run_comparison(package_id: str, request: RunComparisonRequest):
    if package_id not in store.packages:
        raise HTTPException(status_code=404, detail="Package not found")
    use_mock = bool(request.options.get("use_mock_llm", False))
    reports = runner.run_many(package_id, request.strategies, use_mock_llm=use_mock)
    return ComparisonResponse(package_id=package_id, reports=reports)


@app.post("/api/demo-suite/run")
def run_demo_suite(request: RunComparisonRequest):
    use_mock = bool(request.options.get("use_mock_llm", True))
    rows = []
    for case in store.demo_cases.values():
        reports = runner.run_many(case.package_id, request.strategies, use_mock_llm=use_mock)
        rows.append(
            {
                "case": {
                    "package_id": case.package_id,
                    "source_case": case.source_case,
                    "title": case.title,
                    "expected_focus": case.expected_focus,
                    "expected_risk": case.expected_risk,
                },
                "reports": [
                    {
                        "strategy": report.strategy,
                        "summary": report.summary,
                        "result_count": len(report.results),
                        "issue_count": report.metrics.detected_issues_count,
                        "llm_calls": report.metrics.llm_calls,
                        "risk_levels": [result.risk_level for result in report.results],
                        "manual_confirm_count": sum(1 for result in report.results if result.manual_confirm_required),
                    }
                    for report in reports
                ],
            }
        )
    return {"case_count": len(rows), "strategies": request.strategies, "rows": rows}


def _prepare_template_version(package_id: str, request: CreateUploadPackageRequest) -> tuple[str, list[str]]:
    notes: list[str] = []
    if request.template_file is None or not request.template_file.text.strip():
        notes.append("未上传模板基准，使用系统内置 Template Plus。")
        return DEFAULT_TEMPLATE_VERSION_ID, notes

    template_version_id = f"TPLV-UPLOAD-{package_id}"
    store.template_versions[template_version_id] = TemplateVersion(
        template_version_id=template_version_id,
        template_id="TPL-CORP-ONLINE-BANKING",
        version=f"upload-{package_id}",
        fingerprint=f"manual-upload-{uuid4().hex[:10]}",
        published_by="demo_user",
        published_at="2026-06-15",
    )
    store.template_blocks[template_version_id] = [
        block.model_copy(update={"template_version_id": template_version_id})
        for block in store.template_blocks[DEFAULT_TEMPLATE_VERSION_ID]
    ]
    store.template_plus[f"TPLP-UPLOAD-{package_id}"] = TemplatePlus(
        template_plus_id=f"TPLP-UPLOAD-{package_id}",
        template_version_id=template_version_id,
        plus_version="upload",
        description=f"用户上传模板基准：{request.template_file.file_name}",
        fixed_content_policy="上传模板作为本次 Demo 的临时基准；提交材料中新增、删除或修改内容均进入差异识别。",
        variable_slots=[
            "company",
            "account_number",
            "operator_name",
            "identity_doc_type",
            "identity_doc_no",
            "single_limit",
        ],
        baseline_text=request.template_file.text,
        expected_contents=[
            ExpectedContent(
                expected_content_id=f"EXP-UPLOAD-{package_id}",
                content_type="fixed",
                business_meaning="上传模板基准",
                expected_value=request.template_file.text[:200],
                source="uploaded_template",
                check_policy="compare_against_uploaded_baseline",
            )
        ],
    )
    notes.append("已为上传模板生成临时 Template Plus 基准。")
    return template_version_id, notes


def _build_eflow(package_id: str, request: CreateUploadPackageRequest) -> EFlow:
    user = EFlowUser(
        name=request.user_name,
        role=request.user_role,
        permissions=request.permissions,
        media=request.media,
        identity_doc_no=request.identity_doc_no,
        identity_doc_type=request.identity_doc_type,
        account_number=request.account_number,
        single_limit=request.single_limit,
        daily_limit=request.daily_limit,
    )
    return EFlow(
        eflow_id=f"EF-{package_id}",
        applicant=request.user_name,
        company=request.company,
        bank=request.bank,
        platform=request.platform,
        account_name=request.company,
        account_number=request.account_number,
        users=[user],
        change_items=["activity", "user", "permission", "media", "account", "identity"],
        activity=request.activity,
    )


def _build_submitted_documents(
    package_id: str,
    template_version_id: str,
    request: CreateUploadPackageRequest,
) -> list[SubmittedDocument]:
    files = request.submitted_files or []
    if not files:
        files = [
            _generated_application_file(request),
        ]
    return [
        SubmittedDocument(
            document_id=f"DOC-{package_id}-{index + 1}",
            package_id=package_id,
            file_name=file.file_name,
            file_type=file.file_type,
            matched_template_version_id=template_version_id,
            match_confidence=0.86 if file.text.strip() else 0.2,
            match_status="matched" if file.text.strip() else "suspected",
            text=file.text,
        )
        for index, file in enumerate(files)
    ]


def _generated_application_file(request: CreateUploadPackageRequest) -> UploadedTextFile:
    text = "\n".join(
        [
            f"Activity: {request.activity}",
            "User Count: 1",
            f"Company Name: {request.company}",
            f"Account Number: {request.account_number}",
            f"Operator Name: {request.user_name}",
            f"Identity Doc Type: {request.identity_doc_type}",
            f"Identity Doc No: {request.identity_doc_no}",
            f"Permissions: {', '.join(request.permissions)}",
            f"Media: {', '.join(request.media)}",
            f"Single Limit: {int(request.single_limit or 0)}",
            "Declaration: Standard corporate online banking application terms remain unchanged.",
        ]
    )
    return UploadedTextFile(
        file_name="generated-application.txt",
        file_type="txt",
        text=text,
    )
