from time import perf_counter

from backend.app.core.enums import CheckStatus, EvidenceSourceType, RiskLevel, StrategyName
from backend.app.schemas import CheckResult, Evidence, MaterialPackage, ReviewReport, Scenario
from backend.app.services.report_service import ReportService


class FullAgentReviewStrategy:
    strategy_name = StrategyName.FULL_AGENT_REVIEW

    def __init__(self, llm_client) -> None:
        self.llm_client = llm_client
        self.report_service = ReportService()

    def run(self, package: MaterialPackage, scenario: Scenario) -> ReviewReport:
        started = perf_counter()
        document = package.submitted_documents[0]
        evidence = Evidence(
            evidence_id="EVD-FULL-SUMMARY",
            document_id=document.document_id,
            text=document.text[:800],
            source_type=EvidenceSourceType.SUBMITTED_DOCUMENT,
        )
        agent_output = self.llm_client.judge_json(
            "full_agent_risk_scan",
            {
                "scenario": scenario.model_dump(),
                "document_summary": document.text,
                "eflow": package.eflow.model_dump(),
                "constraint": "Only produce risk hints and manual confirmation items.",
            },
        )
        result = CheckResult(
            result_id="CHK-FULL-AGENT",
            package_id=package.package_id,
            strategy=self.strategy_name,
            check_item="全文 Agent 风险扫描",
            status=CheckStatus(agent_output["status"]),
            risk_level=RiskLevel(agent_output["risk_level"]),
            summary=agent_output["summary"],
            evidence_ids=[evidence.evidence_id],
            owner="agent",
            manual_confirm_required=bool(agent_output.get("manual_confirm_required")),
            suggested_action=agent_output.get("suggested_action", ""),
            details=agent_output,
        )
        return self.report_service.build_report(
            package=package,
            scenario=scenario,
            strategy=self.strategy_name,
            results=[result],
            evidences=[evidence],
            runtime_seconds=perf_counter() - started,
            llm_calls=self.llm_client.calls,
            manual_config_cost="low",
            notes="全文 Agent 仅用于补充风险扫描，不作为默认审批路线。",
        )

