from time import perf_counter

from backend.app.core.enums import CheckStatus, EvidenceSourceType, RiskLevel, StrategyName
from backend.app.data_store import store
from backend.app.rules.rule_engine import RuleEngine
from backend.app.schemas import CheckResult, Evidence, MaterialPackage, ReviewReport, Scenario
from backend.app.services.report_service import ReportService


class BlockRuleCheckStrategy:
    strategy_name = StrategyName.BLOCK_RULE_CHECK

    def __init__(self, llm_client) -> None:
        self.llm_client = llm_client
        self.rule_engine = RuleEngine()
        self.report_service = ReportService()

    def run(self, package: MaterialPackage, scenario: Scenario) -> ReviewReport:
        started = perf_counter()
        results: list[CheckResult] = []
        evidences: list[Evidence] = []

        for template_version_id in package.expected_template_set:
            document = next(
                (doc for doc in package.submitted_documents if doc.matched_template_version_id == template_version_id),
                None,
            )
            if document is None:
                results.append(
                    CheckResult(
                        result_id=f"MISS-{template_version_id}",
                        package_id=package.package_id,
                        strategy=self.strategy_name,
                        check_item="模板完整性",
                        status=CheckStatus.FAIL,
                        risk_level=RiskLevel.HIGH,
                        summary=f"缺少预期模板 {template_version_id}",
                        manual_confirm_required=True,
                        suggested_action="请补充对应申请材料。",
                    )
                )
                continue

            for block in store.template_blocks.get(template_version_id, []):
                extracted = self.rule_engine.extract_block_text(document.text, block)
                evidence = Evidence(
                    evidence_id=f"EVD-{block.block_id}",
                    document_id=document.document_id,
                    text=extracted,
                    source_type=EvidenceSourceType.SUBMITTED_DOCUMENT,
                )
                evidences.append(evidence)
                result = self.rule_engine.run_block_rule(package, self.strategy_name, block, extracted, evidence)
                results.append(result)

                if block.ai_required or result.status == CheckStatus.NEED_CONFIRM:
                    agent_output = self.llm_client.judge_json(
                        "block_check",
                        {
                            "scenario": scenario.model_dump(),
                            "block": block.model_dump(),
                            "extracted_content": extracted,
                            "eflow": package.eflow.model_dump(),
                            "system_result": result.model_dump(mode="json"),
                        },
                    )
                    if agent_output.get("manual_confirm_required"):
                        results.append(
                            CheckResult(
                                result_id=f"AGENT-{block.block_id}",
                                package_id=package.package_id,
                                strategy=self.strategy_name,
                                check_item=f"{block.block_name} Agent 复核",
                                status=CheckStatus(agent_output["status"]),
                                risk_level=RiskLevel(agent_output["risk_level"]),
                                summary=agent_output["summary"],
                                evidence_ids=[evidence.evidence_id],
                                owner="agent",
                                manual_confirm_required=True,
                                suggested_action=agent_output.get("suggested_action", ""),
                                details=agent_output,
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
            manual_config_cost="high",
            notes="区块级检查适合沉淀明确审核关注点，但需要维护区块和规则。",
        )

