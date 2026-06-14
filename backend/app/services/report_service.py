from collections import Counter
from backend.app.core.enums import CheckStatus, StrategyName
from backend.app.schemas import CheckResult, Evidence, MaterialPackage, ReviewReport, Scenario, StrategyMetrics


class ReportService:
    def build_report(
        self,
        package: MaterialPackage,
        scenario: Scenario,
        strategy: StrategyName,
        results: list[CheckResult],
        evidences: list[Evidence],
        runtime_seconds: float,
        llm_calls: int,
        manual_config_cost: str,
        notes: str,
    ) -> ReviewReport:
        counts = Counter(result.status for result in results)
        issue_count = sum(
            1
            for result in results
            if result.status in {CheckStatus.FAIL, CheckStatus.WARNING, CheckStatus.NEED_CONFIRM}
        )
        summary = (
            f"共生成 {len(results)} 个检查项；"
            f"通过 {counts[CheckStatus.PASS]} 项，"
            f"需确认 {counts[CheckStatus.NEED_CONFIRM]} 项，"
            f"失败 {counts[CheckStatus.FAIL]} 项。"
        )
        return ReviewReport(
            report_id=f"RPT-{package.package_id}-{strategy.value}",
            package_id=package.package_id,
            strategy=strategy,
            scenario=scenario,
            summary=summary,
            results=results,
            evidences=evidences,
            metrics=StrategyMetrics(
                strategy=strategy,
                runtime_seconds=round(runtime_seconds, 4),
                llm_calls=llm_calls,
                manual_config_cost=manual_config_cost,  # type: ignore[arg-type]
                detected_issues_count=issue_count,
                notes=notes,
            ),
        )

