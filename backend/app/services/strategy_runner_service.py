from backend.app.core.enums import StrategyName
from backend.app.data_store import store
from backend.app.llm.factory import create_llm_client
from backend.app.schemas import ReviewReport
from backend.app.strategies.block_rule_check_strategy import BlockRuleCheckStrategy
from backend.app.strategies.full_agent_review_strategy import FullAgentReviewStrategy
from backend.app.strategies.template_plus_diff_strategy import TemplatePlusDiffStrategy


class StrategyRunnerService:
    def run(self, package_id: str, strategy_name: StrategyName, use_mock_llm: bool = False) -> ReviewReport:
        package = store.packages[package_id]
        scenario = store.scenarios[package.scenario_id]
        llm_client = create_llm_client(use_mock=use_mock_llm)
        strategy = self._create_strategy(strategy_name, llm_client)
        return strategy.run(package, scenario)

    def run_many(self, package_id: str, strategy_names: list[StrategyName], use_mock_llm: bool = False) -> list[ReviewReport]:
        return [self.run(package_id, strategy_name, use_mock_llm) for strategy_name in strategy_names]

    def _create_strategy(self, strategy_name: StrategyName, llm_client):
        if strategy_name == StrategyName.BLOCK_RULE_CHECK:
            return BlockRuleCheckStrategy(llm_client)
        if strategy_name == StrategyName.TEMPLATE_PLUS_DIFF:
            return TemplatePlusDiffStrategy(llm_client)
        if strategy_name == StrategyName.FULL_AGENT_REVIEW:
            return FullAgentReviewStrategy(llm_client)
        if strategy_name == StrategyName.HYBRID_REVIEW:
            return TemplatePlusDiffStrategy(llm_client)
        raise ValueError(f"Unsupported strategy: {strategy_name}")

