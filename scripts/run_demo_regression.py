from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.enums import CheckStatus, StrategyName
from backend.app.data_store import store
from backend.app.services.strategy_runner_service import StrategyRunnerService


EXPECTED_ATTENTION = {
    "PKG-CASE-001-PASS": False,
    "PKG-CASE-003-ID-MISMATCH": True,
    "PKG-CASE-004-NAME-MISMATCH": True,
    "PKG-CASE-005-ACTIVITY-RISK": True,
    "PKG-CASE-006-ACCOUNT-RISK": True,
    "PKG-CASE-007-IDTYPE-RISK": True,
    "PKG-CASE-015-MULTI-PASS": False,
    "PKG-CASE-014-PDF-PASS": False,
    "PKG-CASE-021-HIGH-LIMIT": True,
    "PKG-DEMO-001": True,
}


def needs_attention(report) -> bool:
    return any(
        result.status in {CheckStatus.FAIL, CheckStatus.WARNING, CheckStatus.NEED_CONFIRM}
        for result in report.results
    )


def main() -> None:
    runner = StrategyRunnerService()
    failures = []
    print("Demo regression suite")
    print("=====================")
    for package_id, expected_attention in EXPECTED_ATTENTION.items():
        case = store.demo_cases[package_id]
        block_report = runner.run(package_id, StrategyName.BLOCK_RULE_CHECK, use_mock_llm=True)
        diff_report = runner.run(package_id, StrategyName.TEMPLATE_PLUS_DIFF, use_mock_llm=True)
        actual_attention = needs_attention(block_report) or needs_attention(diff_report)
        ok = actual_attention == expected_attention
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures.append(package_id)
        print(
            f"{status} {package_id} | {case.source_case} | "
            f"attention={actual_attention} expected={expected_attention} | "
            f"block={block_report.metrics.detected_issues_count} "
            f"diff={diff_report.metrics.detected_issues_count}"
        )

    if failures:
        raise SystemExit(f"Regression failed: {', '.join(failures)}")
    print("All demo regression cases passed.")


if __name__ == "__main__":
    main()
