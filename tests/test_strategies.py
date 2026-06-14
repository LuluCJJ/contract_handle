from backend.app.core.enums import CheckStatus, StrategyName
from backend.app.services.strategy_runner_service import StrategyRunnerService


def test_block_rule_strategy_runs():
    report = StrategyRunnerService().run("PKG-DEMO-001", StrategyName.BLOCK_RULE_CHECK, use_mock_llm=True)
    assert report.strategy == StrategyName.BLOCK_RULE_CHECK
    assert report.results
    assert any(result.status in {CheckStatus.PASS, CheckStatus.NEED_CONFIRM, CheckStatus.FAIL} for result in report.results)


def test_template_plus_diff_strategy_finds_risk():
    report = StrategyRunnerService().run("PKG-DEMO-001", StrategyName.TEMPLATE_PLUS_DIFF, use_mock_llm=True)
    assert report.strategy == StrategyName.TEMPLATE_PLUS_DIFF
    assert any(result.manual_confirm_required for result in report.results)

