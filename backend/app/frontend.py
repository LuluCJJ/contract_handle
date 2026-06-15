FRONTEND_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>银行文档预审 Demo 原型</title>
  <style>
    :root {
      --bg: #f7f9fc;
      --surface: #ffffff;
      --surface-2: #eef3f8;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #d8e2ee;
      --primary: #1e293b;
      --accent: #2563eb;
      --cyan: #0e7490;
      --ok: #047857;
      --warn: #b45309;
      --bad: #b91c1c;
      --focus: rgba(37, 99, 235, .24);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    header {
      min-height: 72px;
      padding: 14px 22px;
      color: #fff;
      background: var(--primary);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }
    h1, h2, h3, p { margin-top: 0; }
    h1 { font-size: 20px; margin-bottom: 4px; letter-spacing: 0; }
    header p { margin: 0; color: #cbd5e1; font-size: 13px; }
    main { padding: 16px 22px 24px; }
    button, input, select, textarea {
      font: inherit;
    }
    button {
      min-height: 38px;
      border: 0;
      border-radius: 6px;
      padding: 8px 12px;
      color: #fff;
      background: var(--accent);
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary { background: #334155; }
    button.neutral { color: var(--ink); background: #e2e8f0; }
    button.cyan { background: var(--cyan); }
    button:disabled { opacity: .52; cursor: not-allowed; }
    button:focus, input:focus, select:focus, textarea:focus {
      outline: 3px solid var(--focus);
      outline-offset: 1px;
    }
    input, select, textarea {
      width: 100%;
      min-height: 38px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 8px 10px;
      color: var(--ink);
      background: #fff;
      font-size: 13px;
    }
    textarea { min-height: 92px; line-height: 1.5; resize: vertical; }
    label { display: grid; gap: 6px; color: var(--muted); font-size: 12px; font-weight: 700; }
    .top-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .nav {
      margin-bottom: 14px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .nav button {
      color: var(--ink);
      background: #e2e8f0;
      min-height: 36px;
    }
    .nav button.active { color: #fff; background: var(--primary); }
    .screen { display: none; }
    .screen.active { display: block; }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .panel-title {
      min-height: 46px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      background: #fff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .panel-title h2 { margin: 0; font-size: 15px; }
    .panel-body { padding: 14px; }
    .stack { display: grid; gap: 12px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .review-grid {
      display: grid;
      grid-template-columns: 240px minmax(0, 1fr) 360px;
      gap: 12px;
      align-items: start;
    }
    .muted { color: var(--muted); font-size: 13px; line-height: 1.55; }
    .tiny { color: var(--muted); font-size: 12px; line-height: 1.45; }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 22px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #e2e8f0;
      color: #334155;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .badge.pass, .badge.low { background: #dcfce7; color: #166534; }
    .badge.warning, .badge.medium, .badge.need_confirm { background: #fef3c7; color: #92400e; }
    .badge.fail, .badge.high { background: #fee2e2; color: #991b1b; }
    .summary-strip {
      margin-bottom: 14px;
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 6px; font-size: 22px; }
    .table-wrap { overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    table { width: 100%; min-width: 860px; border-collapse: collapse; background: #fff; }
    th, td { padding: 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; }
    th { background: #f8fafc; color: #475569; font-size: 12px; }
    tr.clickable { cursor: pointer; }
    tr.clickable:hover { background: #f8fafc; }
    .material-list { display: grid; gap: 8px; }
    .material-item {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      cursor: pointer;
    }
    .material-item.active { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
    .doc-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }
    .doc-preview {
      height: calc(100vh - 230px);
      min-height: 520px;
      overflow: auto;
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    .doc-page {
      max-width: 820px;
      min-height: 900px;
      margin: 0 auto;
      padding: 38px 44px;
      background: #fff;
      border: 1px solid #d7dee9;
      box-shadow: 0 12px 24px rgba(15, 23, 42, .08);
    }
    .doc-title {
      margin-bottom: 22px;
      padding-bottom: 12px;
      border-bottom: 2px solid #0f172a;
      font-size: 18px;
      font-weight: 800;
    }
    .doc-line {
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 12px;
      min-height: 34px;
      padding: 7px 8px;
      border-bottom: 1px solid #eef2f7;
      font-size: 14px;
      line-height: 1.4;
    }
    .doc-line .key { color: #475569; font-weight: 700; }
    .doc-line.issue { background: #fff7ed; box-shadow: inset 4px 0 0 #f59e0b; }
    .doc-line.high { background: #fef2f2; box-shadow: inset 4px 0 0 #dc2626; }
    .doc-line.focused { outline: 3px solid var(--focus); outline-offset: 2px; }
    .risk-list { display: grid; gap: 9px; max-height: calc(100vh - 230px); overflow: auto; }
    .risk-item {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 11px;
      cursor: pointer;
    }
    .risk-item.active { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
    .risk-head { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 8px; }
    .risk-head strong { font-size: 13px; }
    .field-grid {
      display: grid;
      grid-template-columns: 1.2fr 1fr 1fr 110px;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }
    .field-cell {
      min-height: 44px;
      padding: 10px;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      font-size: 13px;
      word-break: break-word;
    }
    .field-head { background: #f8fafc; color: #475569; font-size: 12px; font-weight: 800; }
    .diff-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 280px;
      gap: 12px;
    }
    .diff-box {
      min-height: 420px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 12px;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12px;
      line-height: 1.55;
    }
    .config-row {
      display: grid;
      grid-template-columns: 160px 1fr 190px 120px 130px;
      gap: 8px;
      align-items: start;
      padding: 10px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .config-row.header { background: #f8fafc; color: #475569; font-size: 12px; font-weight: 800; }
    .upload-layout { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 12px; }
    .dropzone {
      border: 1px dashed #94a3b8;
      background: #f8fafc;
      border-radius: 8px;
      padding: 12px;
      display: grid;
      gap: 8px;
    }
    .toast {
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 30;
      max-width: 390px;
      padding: 12px 14px;
      color: #fff;
      background: var(--primary);
      border-radius: 8px;
      box-shadow: 0 18px 34px rgba(15, 23, 42, .16);
      font-size: 14px;
    }
    .hidden { display: none !important; }
    @media (max-width: 1180px) {
      .review-grid, .diff-grid, .upload-layout { grid-template-columns: 1fr; }
      .doc-preview, .risk-list { height: auto; max-height: none; }
      .summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 720px) {
      header { align-items: flex-start; flex-direction: column; padding: 14px; }
      main { padding: 12px; }
      .grid-2, .grid-3 { grid-template-columns: 1fr; }
      .field-grid { grid-template-columns: 1fr; }
      .field-cell { border-right: 0; }
      .config-row { grid-template-columns: 1fr; }
      .summary-strip { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>银行文档预审 Demo 原型</h1>
      <p>案例状态、文档预览、证据高亮、字段核对、模板差异和规则配置</p>
    </div>
    <div class="top-actions">
      <select id="modelMode" aria-label="模型模式">
        <option value="mock">Mock 模型，稳定演示</option>
        <option value="real">真实 API，调用 Kimi/公司接口</option>
      </select>
      <button class="cyan" type="button" onclick="runCurrentComparison()">运行当前案例</button>
      <button class="secondary" type="button" onclick="runSuite()">刷新案例状态</button>
    </div>
  </header>

  <main>
    <nav class="nav" aria-label="页面导航">
      <button class="active" type="button" data-screen="overview">案例总览</button>
      <button type="button" data-screen="review">文档审阅</button>
      <button type="button" data-screen="fields">字段核对</button>
      <button type="button" data-screen="diff">模板差异</button>
      <button type="button" data-screen="config">配置中心</button>
      <button type="button" data-screen="upload">上传材料</button>
    </nav>

    <section id="overview" class="screen active">
      <div class="summary-strip">
        <div class="metric"><span>全部案例</span><strong id="mTotal">0</strong></div>
        <div class="metric"><span>通过</span><strong id="mPass">0</strong></div>
        <div class="metric"><span>失败</span><strong id="mFail">0</strong></div>
        <div class="metric"><span>需确认</span><strong id="mConfirm">0</strong></div>
        <div class="metric"><span>高风险</span><strong id="mHigh">0</strong></div>
      </div>
      <div class="panel">
        <div class="panel-title">
          <h2>案例总览</h2>
          <div class="top-actions">
            <select id="caseFilter" onchange="renderOverview()">
              <option value="all">全部</option>
              <option value="pass">通过</option>
              <option value="fail">失败</option>
              <option value="need_confirm">需确认</option>
              <option value="high">高风险</option>
            </select>
          </div>
        </div>
        <div class="panel-body">
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>案例</th>
                  <th>来源</th>
                  <th>状态</th>
                  <th>风险</th>
                  <th>关注点</th>
                  <th>策略命中</th>
                </tr>
              </thead>
              <tbody id="overviewRows">
                <tr><td colspan="6" class="muted">正在加载案例状态...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <section id="review" class="screen">
      <div class="review-grid">
        <aside class="panel">
          <div class="panel-title"><h2>材料树</h2></div>
          <div class="panel-body stack">
            <div class="metric"><span>当前案例</span><strong id="currentCaseShort">-</strong></div>
            <div id="materialList" class="material-list"></div>
          </div>
        </aside>

        <section class="panel">
          <div class="panel-title">
            <h2 id="docName">文档预览</h2>
            <span class="badge" id="docMatchStatus">-</span>
          </div>
          <div class="panel-body">
            <div class="doc-toolbar">
              <p class="muted" id="docHint">点击右侧风险项，可定位到对应证据行。</p>
              <button class="neutral" type="button" onclick="clearFocus()">清除定位</button>
            </div>
            <div class="doc-preview">
              <div class="doc-page" id="docPage"></div>
            </div>
          </div>
        </section>

        <aside class="panel">
          <div class="panel-title">
            <h2>风险与证据</h2>
            <span class="badge" id="riskCount">0 条</span>
          </div>
          <div class="panel-body">
            <div id="riskList" class="risk-list"></div>
          </div>
        </aside>
      </div>
    </section>

    <section id="fields" class="screen">
      <div class="panel">
        <div class="panel-title">
          <h2>字段核对视图</h2>
          <span class="badge">eFlow vs 申请材料</span>
        </div>
        <div class="panel-body stack">
          <p class="muted">这一页用于演示确定性规则如何判断“通过/失败/需确认”。字段行来自区块规则检查报告。</p>
          <div id="fieldGrid" class="field-grid"></div>
        </div>
      </div>
    </section>

    <section id="diff" class="screen">
      <div class="panel">
        <div class="panel-title">
          <h2>模板 Plus 差异视图</h2>
          <span class="badge">baseline vs submitted</span>
        </div>
        <div class="panel-body">
          <div class="diff-grid">
            <div>
              <h3>模板基准</h3>
              <div class="diff-box" id="baselineBox"></div>
            </div>
            <div>
              <h3>提交材料</h3>
              <div class="diff-box" id="submittedBox"></div>
            </div>
            <div>
              <h3>差异分类</h3>
              <div id="diffList" class="risk-list"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="config" class="screen">
      <div class="panel">
        <div class="panel-title">
          <h2>配置中心原型</h2>
          <div class="top-actions">
            <select id="templateSelect" onchange="renderConfig()"></select>
            <button type="button" onclick="savePrototypeConfig()">保存当前配置</button>
          </div>
        </div>
        <div class="panel-body stack">
          <p class="muted">这里展示未来业务人员可配置的模板区块、eFlow 路径、检查类型和是否需要 AI。当前版本保存为前端原型态，不写入数据库。</p>
          <div class="config-row header">
            <div>区块名称</div><div>业务含义/填报说明</div><div>eFlow 路径</div><div>检查类型</div><div>AI 复核</div>
          </div>
          <div id="configRows"></div>
        </div>
      </div>
    </section>

    <section id="upload" class="screen">
      <div class="upload-layout">
        <section class="panel">
          <div class="panel-title"><h2>上传材料包</h2></div>
          <div class="panel-body stack">
            <div class="grid-2">
              <label>公司名称<input id="upCompany" value="Demo Corporate Customer Limited" /></label>
              <label>银行<input id="upBank" value="Demo Bank" /></label>
              <label>账号<input id="upAccount" value="4420156430005200" /></label>
              <label>办理事项
                <select id="upActivity">
                  <option value="open">开通</option>
                  <option value="change">变更</option>
                  <option value="cancel">注销</option>
                </select>
              </label>
              <label>操作员姓名<input id="upUser" value="Zhang Guang" /></label>
              <label>证件类型<input id="upDocType" value="ID Card" /></label>
              <label>证件号码<input id="upDocNo" value="ID442015" /></label>
              <label>单笔限额<input id="upSingleLimit" type="number" value="500000" /></label>
            </div>
            <label>权限，逗号分隔<input id="upPermissions" value="query, payment" /></label>
            <label>介质，逗号分隔<input id="upMedia" value="Token" /></label>
            <button class="cyan" type="button" onclick="createUploadPackage()">生成材料包并进入审阅</button>
          </div>
        </section>

        <section class="panel">
          <div class="panel-title"><h2>申请书与模板基准</h2></div>
          <div class="panel-body stack">
            <div class="dropzone">
              <label>申请书/银行表单文件
                <input id="upSubmitted" type="file" multiple />
              </label>
              <textarea id="upSubmittedText">Activity: open
User Count: 1
Company Name: Demo Corporate Customer Limited
Account Number: 4420156430005200
Operator Name: Zhang Guang
Identity Doc Type: ID Card
Identity Doc No: ID442015
Permissions: query, payment
Media: Token
Single Limit: 500000
Declaration: Standard corporate online banking application terms remain unchanged.</textarea>
            </div>
            <div class="dropzone">
              <label>模板/基准文件，可选
                <input id="upTemplate" type="file" />
              </label>
              <textarea id="upTemplateText" placeholder="不上传则使用系统内置 Template Plus 基准。"></textarea>
            </div>
            <p class="muted">文本类文件会读取正文；PDF、Word 等二进制文件当前作为附件占位进入材料包，后续可接 OCR、Word 解析或 PDF.js 预览。</p>
          </div>
        </section>
      </div>
    </section>
  </main>

  <div id="toast" class="toast hidden" role="status" aria-live="polite"></div>

  <script>
    const state = {
      cases: [],
      suite: null,
      packages: new Map(),
      reports: [],
      selectedPackageId: "PKG-DEMO-001",
      selectedDocId: null,
      selectedRiskId: null,
      templates: null,
      prototypeConfig: {}
    };

    const qs = (id) => document.getElementById(id);
    const labels = {
      block_rule_check: "区块规则",
      template_plus_diff: "模板差异",
      full_agent_review: "全文 Agent",
      pass: "通过",
      fail: "失败",
      warning: "警告",
      need_confirm: "需确认",
      low: "低",
      medium: "中",
      high: "高"
    };

    document.querySelectorAll(".nav button").forEach(button => {
      button.addEventListener("click", () => showScreen(button.dataset.screen));
    });

    function showScreen(id) {
      document.querySelectorAll(".nav button").forEach(item => item.classList.toggle("active", item.dataset.screen === id));
      document.querySelectorAll(".screen").forEach(item => item.classList.toggle("active", item.id === id));
    }

    function toast(message, isError = false) {
      const el = qs("toast");
      el.textContent = message;
      el.style.background = isError ? "var(--bad)" : "var(--primary)";
      el.classList.remove("hidden");
      setTimeout(() => el.classList.add("hidden"), 3200);
    }

    function badge(value) {
      return `<span class="badge ${value}">${labels[value] || value}</span>`;
    }

    function useMock() {
      return qs("modelMode").value !== "real";
    }

    async function api(url, options = {}) {
      const res = await fetch(url, options);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "请求失败");
      return data;
    }

    async function init() {
      state.cases = await api("/api/demo-cases");
      await Promise.all([loadTemplates(), runSuite(false)]);
      await selectCase(state.selectedPackageId, false);
      renderAll();
    }

    async function loadTemplates() {
      state.templates = await api("/api/templates");
      const versions = state.templates.template_versions || [];
      qs("templateSelect").innerHTML = versions.map(item => `<option value="${item.template_version_id}">${item.version} / ${item.template_version_id}</option>`).join("");
    }

    async function runSuite(showMessage = true) {
      state.suite = await api("/api/demo-suite/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategies: ["block_rule_check", "template_plus_diff"],
          options: { use_mock_llm: true }
        })
      });
      renderOverview();
      if (showMessage) toast("案例状态已刷新");
    }

    async function selectCase(packageId, switchToReview = true) {
      state.selectedPackageId = packageId;
      const pkg = await api(`/api/packages/${packageId}`);
      state.packages.set(packageId, pkg);
      state.selectedDocId = pkg.submitted_documents[0]?.document_id || null;
      await runCurrentComparison(false);
      renderAll();
      if (switchToReview) showScreen("review");
    }

    async function runCurrentComparison(showMessage = true) {
      const data = await api(`/api/packages/${state.selectedPackageId}/run-comparison`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategies: ["block_rule_check", "template_plus_diff", "full_agent_review"],
          options: { use_mock_llm: useMock() }
        })
      });
      state.reports = data.reports || [];
      renderAll();
      if (showMessage) toast("当前案例预审完成");
    }

    function caseOutcome(packageId) {
      const row = state.suite?.rows?.find(item => item.case.package_id === packageId);
      if (!row) return { status: "not_checked", risk: "low", issues: 0, manual: 0, strategies: "" };
      const reports = row.reports || [];
      const issues = reports.reduce((sum, report) => sum + report.issue_count, 0);
      const manual = reports.reduce((sum, report) => sum + report.manual_confirm_count, 0);
      const risks = reports.flatMap(report => report.risk_levels || []);
      const risk = risks.includes("high") ? "high" : risks.includes("medium") ? "medium" : "low";
      let status = "pass";
      if (reports.some(report => report.risk_levels?.includes("high")) || row.case.expected_risk === "high") status = "fail";
      else if (manual > 0 || issues > 0) status = "need_confirm";
      return {
        status,
        risk,
        issues,
        manual,
        strategies: reports.map(report => `${labels[report.strategy] || report.strategy}: ${report.issue_count}`).join(" / ")
      };
    }

    function renderOverview() {
      const rows = state.cases.map(item => ({ ...item, outcome: caseOutcome(item.package_id) }));
      qs("mTotal").textContent = rows.length;
      qs("mPass").textContent = rows.filter(item => item.outcome.status === "pass").length;
      qs("mFail").textContent = rows.filter(item => item.outcome.status === "fail").length;
      qs("mConfirm").textContent = rows.filter(item => item.outcome.status === "need_confirm").length;
      qs("mHigh").textContent = rows.filter(item => item.outcome.risk === "high").length;

      const filter = qs("caseFilter").value;
      const filtered = rows.filter(item => {
        if (filter === "all") return true;
        if (filter === "high") return item.outcome.risk === "high";
        return item.outcome.status === filter;
      });
      qs("overviewRows").innerHTML = filtered.map(item => `
        <tr class="clickable" onclick="selectCase('${item.package_id}')">
          <td><strong>${item.title}</strong><div class="tiny">${item.package_id}</div></td>
          <td>${item.source_case}</td>
          <td>${badge(item.outcome.status)}</td>
          <td>${badge(item.outcome.risk)}</td>
          <td>${item.expected_focus}</td>
          <td>${item.outcome.strategies || "未运行"}</td>
        </tr>
      `).join("") || `<tr><td colspan="6" class="muted">没有匹配的案例。</td></tr>`;
    }

    function currentPackage() {
      return state.packages.get(state.selectedPackageId);
    }

    function allResults() {
      return state.reports.flatMap(report => {
        const evidenceById = new Map((report.evidences || []).map(item => [item.evidence_id, item]));
        return report.results.map(result => ({
          ...result,
          strategy: report.strategy,
          evidence_texts: (result.evidence_ids || [])
            .map(id => evidenceById.get(id)?.text)
            .filter(Boolean)
        }));
      });
    }

    function actionableResults() {
      return allResults().filter(item => item.status !== "pass" || item.manual_confirm_required);
    }

    function renderAll() {
      renderOverview();
      renderMaterials();
      renderDocument();
      renderRisks();
      renderFields();
      renderDiff();
      renderConfig();
    }

    function renderMaterials() {
      const pkg = currentPackage();
      if (!pkg) return;
      qs("currentCaseShort").textContent = pkg.package_id.replace("PKG-", "");
      const docs = [
        ...pkg.submitted_documents.map(item => ({ ...item, group: "申请材料" })),
        ...pkg.identity_documents.map(item => ({ ...item, group: "身份证明" })),
        {
          document_id: `EFLOW-${pkg.package_id}`,
          file_name: "eFlow 电子流",
          file_type: "eflow",
          match_status: "matched",
          text: JSON.stringify(pkg.eflow, null, 2),
          group: "电子流"
        }
      ];
      if (!state.selectedDocId && docs[0]) state.selectedDocId = docs[0].document_id;
      qs("materialList").innerHTML = docs.map(doc => `
        <div class="material-item ${doc.document_id === state.selectedDocId ? "active" : ""}" onclick="selectDoc('${doc.document_id}')">
          <strong>${doc.file_name}</strong>
          <div class="tiny">${doc.group} / ${doc.file_type}</div>
          <div style="margin-top:6px">${badge(doc.match_status || "matched")}</div>
        </div>
      `).join("");
    }

    function selectDoc(docId) {
      state.selectedDocId = docId;
      renderMaterials();
      renderDocument();
    }

    function selectedDocument() {
      const pkg = currentPackage();
      if (!pkg) return null;
      const docs = [
        ...pkg.submitted_documents,
        ...pkg.identity_documents,
        {
          document_id: `EFLOW-${pkg.package_id}`,
          file_name: "eFlow 电子流",
          file_type: "eflow",
          match_status: "matched",
          text: JSON.stringify(pkg.eflow, null, 2)
        }
      ];
      return docs.find(item => item.document_id === state.selectedDocId) || docs[0];
    }

    function evidenceTexts() {
      return actionableResults()
        .map(item => ({
          id: item.result_id,
          risk: item.risk_level,
          text: String(item.evidence_texts?.[0] || item.details?.extracted || item.details?.submitted_text || item.summary || "").trim()
        }))
        .filter(item => item.text);
    }

    function parseLine(line) {
      if (line.includes(":")) {
        const [key, ...rest] = line.split(":");
        return { key: key.trim(), value: rest.join(":").trim() };
      }
      return { key: "", value: line };
    }

    function renderDocument() {
      const doc = selectedDocument();
      if (!doc) return;
      qs("docName").textContent = doc.file_name;
      qs("docMatchStatus").innerHTML = labels[doc.match_status] || doc.match_status || "matched";
      const marks = evidenceTexts();
      const lines = String(doc.text || "暂无正文").split(/\r?\n/);
      qs("docPage").innerHTML = `
        <div class="doc-title">${doc.file_name}</div>
        ${lines.map((line, index) => {
          const parsed = parseLine(line);
          const hit = marks.find(mark => mark.text && line.includes(mark.text));
          const cls = hit ? `issue ${hit.risk === "high" ? "high" : ""}` : "";
          return `<div id="line-${index}" class="doc-line ${cls}" data-line="${index}">
            <div class="key">${escapeHtml(parsed.key || `Line ${index + 1}`)}</div>
            <div>${escapeHtml(parsed.value)}</div>
          </div>`;
        }).join("")}
      `;
    }

    function renderRisks() {
      const risks = actionableResults();
      qs("riskCount").textContent = `${risks.length} 条`;
      qs("riskList").innerHTML = risks.map(item => `
        <article class="risk-item ${item.result_id === state.selectedRiskId ? "active" : ""}" onclick="focusRisk('${item.result_id}')">
          <div class="risk-head">
            <strong>${item.check_item}</strong>
            <span>${badge(item.status)} ${badge(item.risk_level)}</span>
          </div>
          <p class="muted">${item.summary}</p>
          <div class="tiny">策略：${labels[item.strategy] || item.strategy}</div>
          ${item.suggested_action ? `<div class="tiny">建议：${item.suggested_action}</div>` : ""}
        </article>
      `).join("") || `<p class="muted">当前文档未发现需要关注的问题。</p>`;
    }

    function focusRisk(resultId) {
      state.selectedRiskId = resultId;
      renderRisks();
      clearFocus();
      const result = actionableResults().find(item => item.result_id === resultId);
      const needle = String(result?.evidence_texts?.[0] || result?.details?.extracted || result?.details?.submitted_text || "").trim();
      if (!needle) return;
      const lines = [...document.querySelectorAll(".doc-line")];
      const target = lines.find(line => line.textContent.includes(needle));
      if (target) {
        target.classList.add("focused");
        target.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }

    function clearFocus() {
      document.querySelectorAll(".doc-line.focused").forEach(item => item.classList.remove("focused"));
    }

    function renderFields() {
      const blockReport = state.reports.find(report => report.strategy === "block_rule_check");
      const rows = blockReport?.results || [];
      qs("fieldGrid").innerHTML = `
        <div class="field-cell field-head">检查项</div>
        <div class="field-cell field-head">eFlow 预期值</div>
        <div class="field-cell field-head">文档提取值</div>
        <div class="field-cell field-head">结论</div>
        ${rows.map(item => `
          <div class="field-cell"><strong>${item.check_item}</strong><div class="tiny">${item.details?.instruction || ""}</div></div>
          <div class="field-cell">${escapeHtml(formatValue(item.details?.expected))}</div>
          <div class="field-cell">${escapeHtml(formatValue(item.details?.extracted))}</div>
          <div class="field-cell">${badge(item.status)} ${badge(item.risk_level)}</div>
        `).join("")}
      `;
    }

    function renderDiff() {
      const pkg = currentPackage();
      const report = state.reports.find(item => item.strategy === "template_plus_diff");
      const diffs = report?.results || [];
      qs("baselineBox").textContent = diffs.map(item => item.details?.baseline_text).filter(Boolean).join("\n") || "当前案例暂无模板差异，或提交内容与模板基准一致。";
      qs("submittedBox").textContent = diffs.map(item => item.details?.submitted_text).filter(Boolean).join("\n") || pkg?.submitted_documents?.[0]?.text || "";
      qs("diffList").innerHTML = diffs.map(item => `
        <article class="risk-item">
          <div class="risk-head">
            <strong>${item.details?.classification || item.check_item}</strong>
            <span>${badge(item.status)} ${badge(item.risk_level)}</span>
          </div>
          <p class="muted">${item.summary}</p>
          <div class="tiny">类型：${item.details?.diff_type || "-"}</div>
        </article>
      `).join("") || `<p class="muted">没有发现模板差异。</p>`;
    }

    function renderConfig() {
      if (!state.templates) return;
      const templateVersionId = qs("templateSelect").value || state.templates.template_versions?.[0]?.template_version_id;
      const blocks = state.templates.template_blocks?.[templateVersionId] || [];
      qs("configRows").innerHTML = blocks.map((block, index) => {
        const key = `${templateVersionId}-${block.block_id}`;
        const saved = state.prototypeConfig[key] || block;
        return `<div class="config-row">
          <input value="${escapeAttr(saved.block_name)}" onchange="setConfig('${key}','block_name',this.value)" />
          <textarea onchange="setConfig('${key}','fill_instruction',this.value)">${escapeHtml(saved.fill_instruction || saved.business_meaning || "")}</textarea>
          <input value="${escapeAttr(saved.expected_eflow_path || "")}" onchange="setConfig('${key}','expected_eflow_path',this.value)" />
          <select onchange="setConfig('${key}','check_type',this.value)">
            ${["normalized_match","contains_all","activity_match","count_match","max_limit_review"].map(type => `<option value="${type}" ${saved.check_type === type ? "selected" : ""}>${type}</option>`).join("")}
          </select>
          <select onchange="setConfig('${key}','ai_required',this.value === 'true')">
            <option value="false" ${!saved.ai_required ? "selected" : ""}>否</option>
            <option value="true" ${saved.ai_required ? "selected" : ""}>是</option>
          </select>
        </div>`;
      }).join("") || `<p class="muted">当前模板没有配置区块。</p>`;
    }

    function setConfig(key, field, value) {
      state.prototypeConfig[key] = { ...(state.prototypeConfig[key] || {}), [field]: value };
    }

    function savePrototypeConfig() {
      toast("配置已保存在当前页面原型中，后续可接后端配置表。");
    }

    function splitCsv(value) {
      return value.split(",").map(item => item.trim()).filter(Boolean);
    }

    async function readFiles(input, fallbackText) {
      const files = Array.from(input.files || []);
      if (files.length === 0) {
        return fallbackText.trim() ? [{ file_name: "manual-input.txt", file_type: "txt", text: fallbackText }] : [];
      }
      return Promise.all(files.map(file => new Promise(resolve => {
        const reader = new FileReader();
        reader.onload = () => resolve({
          file_name: file.name,
          file_type: file.name.split(".").pop() || "txt",
          text: typeof reader.result === "string" ? reader.result : `[binary attachment] ${file.name}`
        });
        reader.onerror = () => resolve({ file_name: file.name, file_type: "bin", text: `[unreadable attachment] ${file.name}` });
        if (file.type.startsWith("text/") || /\.(txt|csv|json|md)$/i.test(file.name)) reader.readAsText(file, "utf-8");
        else reader.readAsArrayBuffer(file);
      })));
    }

    async function createUploadPackage() {
      const submittedFiles = await readFiles(qs("upSubmitted"), qs("upSubmittedText").value);
      const templateFiles = await readFiles(qs("upTemplate"), qs("upTemplateText").value);
      const created = await api("/api/upload-package", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company: qs("upCompany").value,
          bank: qs("upBank").value,
          platform: "Corporate Online Banking",
          activity: qs("upActivity").value,
          account_number: qs("upAccount").value,
          user_name: qs("upUser").value,
          identity_doc_type: qs("upDocType").value,
          identity_doc_no: qs("upDocNo").value,
          permissions: splitCsv(qs("upPermissions").value),
          media: splitCsv(qs("upMedia").value),
          single_limit: Number(qs("upSingleLimit").value || 0),
          submitted_files: submittedFiles,
          template_file: templateFiles[0] || null
        })
      });
      state.selectedPackageId = created.package_id;
      state.packages.set(created.package_id, created.package);
      state.selectedDocId = created.package.submitted_documents[0]?.document_id || null;
      await runCurrentComparison(false);
      renderAll();
      showScreen("review");
      toast(`材料包 ${created.package_id} 已生成`);
    }

    function formatValue(value) {
      if (Array.isArray(value)) return value.join(", ");
      if (value === null || value === undefined) return "";
      return String(value);
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function escapeAttr(value) {
      return escapeHtml(value).replaceAll("\n", " ");
    }

    init().catch(error => toast(error.message, true));
  </script>
</body>
</html>
"""
