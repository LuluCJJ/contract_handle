FRONTEND_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>银行文档预审 Demo 工作台</title>
  <style>
    :root {
      --bg: #f8fafc;
      --surface: #ffffff;
      --surface-2: #f1f5f9;
      --text: #0f172a;
      --muted: #64748b;
      --line: #dbe4ef;
      --primary: #1e293b;
      --accent: #2563eb;
      --accent-2: #0891b2;
      --danger: #dc2626;
      --warn: #b45309;
      --ok: #047857;
      --shadow: 0 12px 30px rgba(15, 23, 42, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, "Microsoft YaHei", sans-serif;
      color: var(--text);
      background: var(--bg);
    }
    header {
      background: var(--primary);
      color: #fff;
      padding: 20px 28px;
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: center;
    }
    h1, h2, h3, p { margin-top: 0; }
    h1 { font-size: 22px; margin-bottom: 6px; letter-spacing: 0; }
    header p { margin: 0; color: #cbd5e1; font-size: 14px; }
    main { padding: 20px 28px 28px; }
    .layout {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .panel-body { padding: 16px; }
    .panel-title {
      padding: 13px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    .panel-title h2 { font-size: 15px; margin: 0; }
    .stack { display: grid; gap: 12px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    label { display: grid; gap: 6px; font-size: 12px; color: var(--muted); font-weight: 600; }
    input, select, textarea {
      width: 100%;
      min-height: 40px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 9px 10px;
      font-size: 14px;
      color: var(--text);
      background: #fff;
    }
    textarea { min-height: 92px; resize: vertical; line-height: 1.5; }
    input:focus, select:focus, textarea:focus, button:focus {
      outline: 3px solid rgba(37, 99, 235, .22);
      outline-offset: 1px;
    }
    button {
      min-height: 40px;
      border: 0;
      border-radius: 6px;
      padding: 9px 12px;
      font-size: 14px;
      font-weight: 700;
      color: #fff;
      background: var(--accent);
      cursor: pointer;
      transition: transform .15s ease, opacity .15s ease, background .15s ease;
    }
    button:hover { opacity: .93; }
    button:active { transform: translateY(1px); }
    button.secondary { background: #334155; }
    button.ghost { background: #e2e8f0; color: var(--text); }
    button.cyan { background: var(--accent-2); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .button-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .tabs { display: flex; gap: 8px; flex-wrap: wrap; }
    .tab {
      width: auto;
      min-height: 34px;
      padding: 7px 10px;
      background: #e2e8f0;
      color: var(--text);
    }
    .tab.active { background: var(--primary); color: #fff; }
    .muted { color: var(--muted); font-size: 13px; line-height: 1.6; }
    .tiny { font-size: 12px; color: var(--muted); }
    .case-list { display: grid; gap: 8px; max-height: 360px; overflow: auto; padding-right: 4px; }
    .case-card {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 8px;
      padding: 10px;
      cursor: pointer;
    }
    .case-card.active { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
    .case-card strong { display: block; font-size: 13px; margin-bottom: 4px; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      background: #e2e8f0;
      color: #334155;
    }
    .badge.high, .badge.fail, .badge.need_confirm { background: #fee2e2; color: #991b1b; }
    .badge.medium, .badge.warning { background: #fef3c7; color: #92400e; }
    .badge.low, .badge.pass { background: #dcfce7; color: #166534; }
    .kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .kpi { border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }
    .kpi span { color: var(--muted); font-size: 12px; }
    .kpi strong { display: block; margin-top: 5px; font-size: 22px; }
    .result-list { display: grid; gap: 10px; }
    .result-card { border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }
    .result-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
    .result-head strong { font-size: 14px; }
    .evidence {
      margin-top: 8px;
      padding: 9px 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      color: #334155;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .table-wrap { overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; background: #fff; min-width: 760px; }
    th, td { padding: 10px; border-bottom: 1px solid var(--line); text-align: left; font-size: 13px; vertical-align: top; }
    th { background: #f8fafc; color: #475569; font-size: 12px; }
    .dropzone {
      border: 1px dashed #94a3b8;
      background: #f8fafc;
      border-radius: 8px;
      padding: 12px;
      display: grid;
      gap: 8px;
    }
    .dropzone input { background: #fff; padding: 8px; }
    .source-switch { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .hidden { display: none !important; }
    .toast {
      position: fixed;
      right: 18px;
      bottom: 18px;
      max-width: 360px;
      padding: 12px 14px;
      border-radius: 8px;
      color: #fff;
      background: var(--primary);
      box-shadow: var(--shadow);
      font-size: 14px;
      z-index: 20;
    }
    @media (max-width: 1040px) {
      header { align-items: flex-start; flex-direction: column; }
      .layout { grid-template-columns: 1fr; }
      .kpis, .grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 640px) {
      header, main { padding-left: 14px; padding-right: 14px; }
      .grid-2, .grid-3, .kpis, .button-row, .source-switch { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>银行文档预审 Demo 工作台</h1>
      <p>内置测试场景 + 手动上传材料包 + 规则/模板 Plus/Agent 策略对比</p>
    </div>
    <div class="tabs" aria-label="数据来源">
      <button class="tab active" id="tabScenario" type="button">内置场景</button>
      <button class="tab" id="tabUpload" type="button">手动上传</button>
    </div>
  </header>

  <main>
    <div class="layout">
      <aside class="stack">
        <section class="panel" id="scenarioPanel">
          <div class="panel-title">
            <h2>演示场景矩阵</h2>
            <span class="badge" id="caseCount">0 个</span>
          </div>
          <div class="panel-body stack">
            <div class="case-list" id="caseList"></div>
            <div class="button-row">
              <button type="button" onclick="loadPackage()">查看材料包</button>
              <button class="secondary" type="button" onclick="runSuite()">全量回归</button>
            </div>
          </div>
        </section>

        <section class="panel hidden" id="uploadPanel">
          <div class="panel-title">
            <h2>上传材料包</h2>
            <span class="badge">本地文件</span>
          </div>
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
            <button class="cyan" type="button" onclick="createUploadPackage()">生成材料包并预审</button>
            <p class="muted">文本类文件会读取正文；PDF、Word 等二进制文件在此版本中先作为附件名进入材料包，后续可接 OCR 和文档解析器。</p>
          </div>
        </section>

        <section class="panel">
          <div class="panel-title"><h2>预审动作</h2></div>
          <div class="panel-body stack">
            <button type="button" onclick="runStrategy('block_rule_check')">区块规则检查</button>
            <button type="button" onclick="runStrategy('template_plus_diff')">模板 Plus 差异检查</button>
            <button class="secondary" type="button" onclick="runComparison()">三策略对比</button>
            <label>
              模型模式
              <select id="modelMode">
                <option value="mock">Mock，稳定演示</option>
                <option value="real">真实 Kimi/API</option>
              </select>
            </label>
            <p class="muted">明天正式演示建议先用 Mock 保证节奏，再选一个高风险场景切真实 Kimi 展示智能解释。</p>
          </div>
        </section>
      </aside>

      <section class="stack">
        <section class="panel">
          <div class="panel-title">
            <h2>当前材料包</h2>
            <span class="badge" id="currentPackage">未选择</span>
          </div>
          <div class="panel-body">
            <div class="kpis">
              <div class="kpi"><span>材料包</span><strong id="kpiPackage">-</strong></div>
              <div class="kpi"><span>公司</span><strong id="kpiCompany">-</strong></div>
              <div class="kpi"><span>银行</span><strong id="kpiBank">-</strong></div>
              <div class="kpi"><span>文件数</span><strong id="kpiDocs">-</strong></div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-title">
            <h2>预审结果</h2>
            <span class="badge" id="runStatus">待运行</span>
          </div>
          <div class="panel-body stack">
            <div class="grid-3">
              <div class="kpi"><span>问题数</span><strong id="metricIssues">0</strong></div>
              <div class="kpi"><span>需人工确认</span><strong id="metricManual">0</strong></div>
              <div class="kpi"><span>模型调用</span><strong id="metricLlm">0</strong></div>
            </div>
            <div id="results" class="result-list">
              <p class="muted">请选择场景或上传材料，然后运行预审。</p>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-title">
            <h2>全量测试矩阵</h2>
            <span class="badge">Demo Suite</span>
          </div>
          <div class="panel-body">
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>场景</th>
                    <th>来源</th>
                    <th>关注点</th>
                    <th>预期风险</th>
                    <th>结果摘要</th>
                  </tr>
                </thead>
                <tbody id="suiteRows">
                  <tr><td colspan="5" class="muted">点击左侧“全量回归”后显示。</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </section>
    </div>
  </main>
  <div id="toast" class="toast hidden" role="status" aria-live="polite"></div>

  <script>
    let demoCases = [];
    let selectedPackage = "PKG-DEMO-001";
    let lastPackage = null;

    const qs = (id) => document.getElementById(id);
    const strategyLabel = {
      block_rule_check: "区块规则检查",
      template_plus_diff: "模板 Plus 差异",
      full_agent_review: "全文 Agent 复核",
      hybrid_review: "混合策略"
    };

    function toast(message, isError = false) {
      const el = qs("toast");
      el.textContent = message;
      el.style.background = isError ? "var(--danger)" : "var(--primary)";
      el.classList.remove("hidden");
      setTimeout(() => el.classList.add("hidden"), 3200);
    }

    function useMock() {
      return qs("modelMode").value !== "real";
    }

    async function api(url, options = {}) {
      qs("runStatus").textContent = "运行中";
      const res = await fetch(url, options);
      const data = await res.json();
      if (!res.ok) {
        qs("runStatus").textContent = "失败";
        throw new Error(data.detail || "请求失败");
      }
      qs("runStatus").textContent = "完成";
      return data;
    }

    function splitCsv(value) {
      return value.split(",").map(item => item.trim()).filter(Boolean);
    }

    async function readFiles(input, fallbackText) {
      const files = Array.from(input.files || []);
      if (files.length === 0) {
        return fallbackText.trim()
          ? [{ file_name: "manual-input.txt", file_type: "txt", text: fallbackText }]
          : [];
      }
      const readers = files.map(file => new Promise(resolve => {
        const reader = new FileReader();
        reader.onload = () => resolve({
          file_name: file.name,
          file_type: file.name.split(".").pop() || "txt",
          text: typeof reader.result === "string" ? reader.result : `[binary attachment] ${file.name}`
        });
        reader.onerror = () => resolve({
          file_name: file.name,
          file_type: file.name.split(".").pop() || "bin",
          text: `[unreadable attachment] ${file.name}`
        });
        if (file.type.startsWith("text/") || /\.(txt|csv|json|md)$/i.test(file.name)) {
          reader.readAsText(file, "utf-8");
        } else {
          reader.readAsArrayBuffer(file);
        }
      }));
      return Promise.all(readers);
    }

    async function readTemplateFile() {
      const files = await readFiles(qs("upTemplate"), qs("upTemplateText").value);
      return files[0] || null;
    }

    function renderCases() {
      qs("caseCount").textContent = `${demoCases.length} 个`;
      qs("caseList").innerHTML = demoCases.map(item => `
        <div class="case-card ${item.package_id === selectedPackage ? "active" : ""}" onclick="selectCase('${item.package_id}')">
          <strong>${item.title}</strong>
          <div class="tiny">${item.source_case}</div>
          <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
            <span class="badge ${item.expected_risk}">${item.expected_risk}</span>
            <span class="badge">${item.expected_focus}</span>
          </div>
        </div>
      `).join("");
    }

    function selectCase(packageId) {
      selectedPackage = packageId;
      renderCases();
      loadPackage();
    }

    function showPackage(packageData) {
      lastPackage = packageData;
      selectedPackage = packageData.package_id;
      qs("currentPackage").textContent = packageData.package_id;
      qs("kpiPackage").textContent = packageData.package_id.replace("PKG-", "");
      qs("kpiCompany").textContent = packageData.eflow.company;
      qs("kpiBank").textContent = packageData.eflow.bank;
      qs("kpiDocs").textContent = packageData.submitted_documents.length + packageData.identity_documents.length;
    }

    async function loadPackage() {
      try {
        const data = await api(`/api/packages/${selectedPackage}`);
        showPackage(data);
        qs("results").innerHTML = `<div class="evidence">${JSON.stringify(data, null, 2)}</div>`;
      } catch (err) {
        toast(err.message, true);
      }
    }

    function resultBadge(value) {
      return `<span class="badge ${value}">${value}</span>`;
    }

    function renderReport(report) {
      const manual = report.results.filter(item => item.manual_confirm_required).length;
      qs("metricIssues").textContent = report.metrics.detected_issues_count;
      qs("metricManual").textContent = manual;
      qs("metricLlm").textContent = report.metrics.llm_calls;
      qs("results").innerHTML = `
        <p class="muted">${strategyLabel[report.strategy] || report.strategy}：${report.summary}</p>
        ${report.results.map(item => `
          <article class="result-card">
            <div class="result-head">
              <strong>${item.check_item}</strong>
              <div>${resultBadge(item.status)} ${resultBadge(item.risk_level)}</div>
            </div>
            <p class="muted">${item.summary}</p>
            ${item.suggested_action ? `<p><strong>建议：</strong>${item.suggested_action}</p>` : ""}
            <div class="evidence">${JSON.stringify(item.details || {}, null, 2)}</div>
          </article>
        `).join("") || `<p class="muted">未发现需要关注的问题。</p>`}
      `;
    }

    function renderComparison(data) {
      const reports = data.reports || [];
      qs("metricIssues").textContent = reports.reduce((sum, report) => sum + report.metrics.detected_issues_count, 0);
      qs("metricManual").textContent = reports.reduce((sum, report) => sum + report.results.filter(item => item.manual_confirm_required).length, 0);
      qs("metricLlm").textContent = reports.reduce((sum, report) => sum + report.metrics.llm_calls, 0);
      qs("results").innerHTML = reports.map(report => `
        <article class="result-card">
          <div class="result-head">
            <strong>${strategyLabel[report.strategy] || report.strategy}</strong>
            <span class="badge">${report.results.length} 条结果</span>
          </div>
          <p class="muted">${report.summary}</p>
          <div class="evidence">${report.results.map(item => `${item.status} / ${item.risk_level} / ${item.check_item}: ${item.summary}`).join("\n") || "无问题"}</div>
        </article>
      `).join("");
    }

    async function runStrategy(strategy) {
      try {
        const data = await api(`/api/packages/${selectedPackage}/run-preaudit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ strategy, options: { use_mock_llm: useMock() } })
        });
        renderReport(data);
      } catch (err) {
        toast(err.message, true);
      }
    }

    async function runComparison() {
      try {
        const data = await api(`/api/packages/${selectedPackage}/run-comparison`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            strategies: ["block_rule_check", "template_plus_diff", "full_agent_review"],
            options: { use_mock_llm: useMock() }
          })
        });
        renderComparison(data);
      } catch (err) {
        toast(err.message, true);
      }
    }

    async function runSuite() {
      try {
        const data = await api("/api/demo-suite/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            strategies: ["block_rule_check", "template_plus_diff"],
            options: { use_mock_llm: true }
          })
        });
        qs("suiteRows").innerHTML = data.rows.map(row => {
          const summary = row.reports.map(report => `${strategyLabel[report.strategy] || report.strategy}: 问题 ${report.issue_count}, 模型 ${report.llm_calls}`).join("<br>");
          return `<tr>
            <td>${row.case.title}</td>
            <td>${row.case.source_case}</td>
            <td>${row.case.expected_focus}</td>
            <td>${resultBadge(row.case.expected_risk)}</td>
            <td>${summary}</td>
          </tr>`;
        }).join("");
        toast("全量 Demo Suite 已完成");
      } catch (err) {
        toast(err.message, true);
      }
    }

    async function createUploadPackage() {
      try {
        const submittedFiles = await readFiles(qs("upSubmitted"), qs("upSubmittedText").value);
        const templateFile = await readTemplateFile();
        const payload = {
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
          template_file: templateFile
        };
        const data = await api("/api/upload-package", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        showPackage(data.package);
        toast(`材料包 ${data.package_id} 已生成`);
        await runComparison();
      } catch (err) {
        toast(err.message, true);
      }
    }

    function switchSource(source) {
      const upload = source === "upload";
      qs("uploadPanel").classList.toggle("hidden", !upload);
      qs("scenarioPanel").classList.toggle("hidden", upload);
      qs("tabUpload").classList.toggle("active", upload);
      qs("tabScenario").classList.toggle("active", !upload);
    }

    async function init() {
      qs("tabScenario").addEventListener("click", () => switchSource("scenario"));
      qs("tabUpload").addEventListener("click", () => switchSource("upload"));
      const res = await fetch("/api/demo-cases");
      demoCases = await res.json();
      renderCases();
      await loadPackage();
    }

    init();
  </script>
</body>
</html>
"""
