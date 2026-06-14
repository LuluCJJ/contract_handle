from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from backend.app.core.enums import StrategyName
from backend.app.data_store import store
from backend.app.schemas import ComparisonResponse, RunComparisonRequest, RunPreauditRequest
from backend.app.services.strategy_runner_service import StrategyRunnerService


app = FastAPI(title="Bank Document Preaudit POC", version="0.1.0")
runner = StrategyRunnerService()


@app.get("/", response_class=HTMLResponse)
def demo_page() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>银行文档预审 POC</title>
  <style>
    body { margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #172033; }
    header { padding: 28px 36px; background: #10243f; color: white; }
    main { padding: 24px 36px; display: grid; gap: 18px; grid-template-columns: 360px 1fr; }
    section { background: white; border: 1px solid #d9e0ea; border-radius: 8px; padding: 18px; }
    button { width: 100%; margin: 8px 0; padding: 11px 12px; border: 0; border-radius: 6px; background: #2463eb; color: white; cursor: pointer; font-size: 14px; }
    button.secondary { background: #2f4858; }
    pre { white-space: pre-wrap; word-break: break-word; background: #0b1020; color: #d8e2ff; padding: 16px; border-radius: 6px; min-height: 420px; overflow: auto; }
    .muted { color: #607086; line-height: 1.6; }
    @media (max-width: 900px) { main { grid-template-columns: 1fr; padding: 16px; } header { padding: 22px 16px; } }
  </style>
</head>
<body>
  <header>
    <h1>银行协议/申请文档预审 POC</h1>
    <p>稳定业务底座 + 可插拔策略 + 统一报告 + 模型接口预留</p>
  </header>
  <main>
    <section>
      <h2>样例材料包</h2>
      <p class="muted">案例矩阵来自旧方案 test_data，已转成新方案材料包。可按场景演示通过、硬失败、风险提示和多策略对比。</p>
      <select id="caseSelect" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;margin:8px 0;"></select>
      <button onclick="loadPackage()">查看材料包</button>
      <button onclick="runStrategy('block_rule_check')">运行 Demo1 区块检查</button>
      <button onclick="runStrategy('template_plus_diff')">运行 Demo2 模板 Plus 差异</button>
      <button class="secondary" onclick="runComparison()">多策略对比</button>
      <button class="secondary" onclick="runSuite()">运行全量 Demo Suite</button>
      <p class="muted">完整接口可在 <a href="/docs">/docs</a> 中试用。</p>
    </section>
    <section>
      <h2>输出</h2>
      <pre id="output">点击左侧按钮开始演示。</pre>
    </section>
  </main>
  <script>
    const out = document.getElementById('output');
    async function show(url, options) {
      out.textContent = '运行中...';
      const res = await fetch(url, options);
      out.textContent = JSON.stringify(await res.json(), null, 2);
    }
    let selectedPackage = 'PKG-DEMO-001';
    async function initCases() {
      const res = await fetch('/api/demo-cases');
      const cases = await res.json();
      const select = document.getElementById('caseSelect');
      select.innerHTML = cases.map(item => `<option value="${item.package_id}">${item.package_id}｜${item.title}</option>`).join('');
      select.value = selectedPackage;
      select.addEventListener('change', () => { selectedPackage = select.value; });
    }
    function loadPackage() { show(`/api/packages/${selectedPackage}`); }
    function runStrategy(strategy) {
      show(`/api/packages/${selectedPackage}/run-preaudit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy, options: { use_mock_llm: true } })
      });
    }
    function runComparison() {
      show(`/api/packages/${selectedPackage}/run-comparison`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategies: ['block_rule_check', 'template_plus_diff', 'full_agent_review'] })
      });
    }
    function runSuite() {
      show('/api/demo-suite/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategies: ['block_rule_check', 'template_plus_diff'], options: { use_mock_llm: true } })
      });
    }
    initCases();
  </script>
</body>
</html>
"""


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
            "description": "区块级填写规范检查",
        },
        {
            "strategy": StrategyName.TEMPLATE_PLUS_DIFF,
            "demo": "Demo2",
            "description": "模板 Plus 预填基准差异检查",
        },
        {
            "strategy": StrategyName.FULL_AGENT_REVIEW,
            "demo": "Demo3",
            "description": "受约束的全文 Agent 风险提示",
        },
        {
            "strategy": StrategyName.HYBRID_REVIEW,
            "demo": "Future",
            "description": "混合策略预留",
        },
    ]


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
