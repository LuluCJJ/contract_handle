from time import perf_counter

from backend.app.core.enums import CheckStatus, DiffClassification, EvidenceSourceType, RiskLevel, StrategyName
from backend.app.data_store import store
from backend.app.rules.diff_classifier import DiffClassifier
from backend.app.schemas import CheckResult, Evidence, MaterialPackage, ReviewReport, Scenario
from backend.app.services.document_diff_service import DocumentDiffService
from backend.app.services.report_service import ReportService


class TemplatePlusDiffStrategy:
    strategy_name = StrategyName.TEMPLATE_PLUS_DIFF

    def __init__(self, llm_client) -> None:
        self.llm_client = llm_client
        self.diff_service = DocumentDiffService()
        self.classifier = DiffClassifier()
        self.report_service = ReportService()

    def run(self, package: MaterialPackage, scenario: Scenario) -> ReviewReport:
        started = perf_counter()
        results: list[CheckResult] = []
        evidences: list[Evidence] = []

        for template_plus in store.template_plus.values():
            document = next(
                (
                    doc
                    for doc in package.submitted_documents
                    if doc.matched_template_version_id == template_plus.template_version_id
                ),
                None,
            )
            if document is None:
                continue

            diffs = self.diff_service.diff_text(template_plus.baseline_text, document.text)
            for diff in diffs:
                classification = self.classifier.classify(diff, package, template_plus)
                diff.classification = classification
                evidence = Evidence(
                    evidence_id=f"EVD-{diff.diff_id}",
                    document_id=document.document_id,
                    text=diff.submitted_text or diff.baseline_text,
                    source_type=EvidenceSourceType.SUBMITTED_DOCUMENT,
                )
                evidences.append(evidence)

                status, risk, manual, action = self._map_classification(classification)
                details = diff.model_dump(mode="json")
                owner = "code"
                summary = f"{classification.value}: {diff.submitted_text or diff.baseline_text}"

                if classification in {DiffClassification.POTENTIAL_RISK, DiffClassification.UNKNOWN}:
                    agent_output = self.llm_client.judge_json(
                        "diff_explanation",
                        {
                            "scenario": scenario.model_dump(),
                            "diff": diff.model_dump(mode="json"),
                            "template_plus_policy": template_plus.fixed_content_policy,
                            "eflow": package.eflow.model_dump(),
                        },
                    )
                    status = CheckStatus(agent_output["status"])
                    risk = RiskLevel(agent_output["risk_level"])
                    manual = bool(agent_output.get("manual_confirm_required", True))
                    action = agent_output.get("suggested_action", action)
                    summary = agent_output.get("summary", summary)
                    details["agent"] = agent_output
                    owner = "agent"

                results.append(
                    CheckResult(
                        result_id=f"CHK-{diff.diff_id}",
                        package_id=package.package_id,
                        strategy=self.strategy_name,
                        check_item=f"模板 Plus 差异：{diff.diff_type}",
                        status=status,
                        risk_level=risk,
                        summary=summary,
                        evidence_ids=[evidence.evidence_id],
                        owner=owner,  # type: ignore[arg-type]
                        manual_confirm_required=manual,
                        suggested_action=action,
                        details=details,
                    )
                )

        return self.report_service.build_report(
            package=package,
            scenario=scenario,
            strategy=self.strategy_name,
            results=results,
            evidences=evidences,
            runtime_seconds=perf_counter() - started,
            llm_calls=self.llm_client.calls,
            manual_config_cost="medium",
            notes="模板 Plus 差异路线适合展示“哪里变了、哪里偏离基准”。",
        )

    def _map_classification(self, classification: DiffClassification):
        if classification == DiffClassification.EFLOW_CHANGE:
            return CheckStatus.PASS, RiskLevel.LOW, False, "与电子流变化项核对通过。"
        if classification == DiffClassification.ACCEPTABLE_FILL:
            return CheckStatus.PASS, RiskLevel.LOW, False, "合理填写，可通过。"
        if classification == DiffClassification.TEMPLATE_DEVIATION:
            return CheckStatus.WARNING, RiskLevel.MEDIUM, True, "请确认固定模板内容是否允许修改。"
        if classification == DiffClassification.POTENTIAL_RISK:
            return CheckStatus.NEED_CONFIRM, RiskLevel.HIGH, True, "请审核人确认该差异是否有授权依据。"
        return CheckStatus.NEED_CONFIRM, RiskLevel.MEDIUM, True, "系统无法判断，请人工确认。"

