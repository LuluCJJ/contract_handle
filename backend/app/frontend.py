FRONTEND_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>银行文档预审 Demo 原型</title>
  <script src="https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
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
    .stage-nav {
      margin-bottom: 10px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .stage-nav button {
      min-height: 46px;
      color: var(--ink);
      background: #e2e8f0;
      text-align: left;
    }
    .stage-nav button.active {
      color: #fff;
      background: var(--primary);
    }
    .stage-nav span {
      display: block;
      margin-top: 3px;
      font-size: 11px;
      font-weight: 500;
      opacity: .78;
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
    .native-preview {
      max-width: 820px;
      margin: 0 auto 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }
    .native-preview iframe {
      width: 100%;
      height: 520px;
      border: 0;
      display: block;
    }
    .native-preview img {
      display: block;
      max-width: 100%;
      max-height: 520px;
      margin: 0 auto;
      object-fit: contain;
    }
    .office-preview {
      max-width: 920px;
      min-height: 620px;
      margin: 0 auto 14px;
      padding: 28px 34px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 10px 22px rgba(15, 23, 42, .08);
      overflow: auto;
      line-height: 1.65;
    }
    .office-preview table {
      min-width: 0;
      width: auto;
      max-width: 100%;
      border-collapse: collapse;
    }
    .office-preview td,
    .office-preview th {
      border: 1px solid #cbd5e1;
      padding: 6px 8px;
      font-size: 13px;
    }
    .office-preview-message {
      max-width: 820px;
      margin: 0 auto 14px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--muted);
      font-size: 13px;
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
      grid-template-columns: 120px 1fr 160px 118px 95px 130px;
      gap: 8px;
      align-items: start;
      padding: 10px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .config-row.header { background: #f8fafc; color: #475569; font-size: 12px; font-weight: 800; }
    .template-config-layout {
      display: grid;
      grid-template-columns: 240px minmax(0, 1fr) 560px;
      gap: 12px;
      align-items: start;
    }
    .template-preview {
      height: calc(100vh - 250px);
      min-height: 520px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 16px;
    }
    .template-line {
      display: grid;
      grid-template-columns: 64px minmax(0, 1fr);
      gap: 10px;
      min-height: 30px;
      padding: 6px 8px;
      border-bottom: 1px solid #eef2f7;
      font-size: 13px;
      cursor: pointer;
    }
    .template-line:hover { background: #f8fafc; }
    .template-line.focused {
      background: #eff6ff;
      outline: 2px solid var(--focus);
      outline-offset: -2px;
    }
    .template-line .line-no { color: var(--muted); font-size: 12px; }
    .upload-layout { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 12px; }
    .route-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 12px;
      display: grid;
      gap: 8px;
    }
    .route-card strong { font-size: 14px; }
    .prep-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }
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
      .template-config-layout { grid-template-columns: 1fr; }
      .stage-nav { grid-template-columns: 1fr; }
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
      <select id="routeMode" aria-label="预审方案" onchange="switchRouteMode()">
        <option value="A">方案 A：有模板 Plus</option>
        <option value="B">方案 B：无模板 Plus</option>
        <option value="compare">A/B 对比</option>
      </select>
      <select id="modelMode" aria-label="模型模式">
        <option value="mock">Mock 模型，稳定演示</option>
        <option value="real">真实 API，调用 Kimi/公司接口</option>
      </select>
      <button class="cyan" type="button" onclick="runCurrentComparison()">运行当前案例</button>
      <button class="secondary" type="button" onclick="runSuite()">刷新案例状态</button>
    </div>
  </header>

  <main>
    <nav class="stage-nav" aria-label="用户旅程">
      <button class="active" type="button" data-stage="setup" onclick="showStage('setup')">配置环节<span>模板库、Template Plus、填写规范、原文定位</span></button>
      <button type="button" data-stage="execution" onclick="showStage('execution')">上传实施触发<span>材料准备、上传、匹配解析、路线执行</span></button>
      <button type="button" data-stage="reporting" onclick="showStage('reporting')">最终结果和报告<span>统一报告、多路径对比、人工确认</span></button>
    </nav>
    <nav class="nav" aria-label="页面导航">
      <button class="active" type="button" data-stage="setup" data-screen="config">模板配置中心</button>
      <button type="button" data-stage="execution" data-screen="review">材料准备</button>
      <button type="button" data-stage="execution" data-screen="upload">上传材料</button>
      <button type="button" data-stage="execution" data-screen="match">模板匹配与解析</button>
      <button type="button" data-stage="execution" data-screen="diff">路线 A：模板 Plus</button>
      <button type="button" data-stage="execution" data-screen="fields">路线 B：填写规范</button>
      <button type="button" data-stage="reporting" data-screen="overview">统一预审报告</button>
      <button type="button" data-stage="reporting" data-screen="compare">多路径对比</button>
    </nav>

    <section id="overview" class="screen">
      <div class="summary-strip">
        <div class="metric"><span>全部案例</span><strong id="mTotal">0</strong></div>
        <div class="metric"><span>通过</span><strong id="mPass">0</strong></div>
        <div class="metric"><span>失败</span><strong id="mFail">0</strong></div>
        <div class="metric"><span>需确认</span><strong id="mConfirm">0</strong></div>
        <div class="metric"><span>高风险</span><strong id="mHigh">0</strong></div>
      </div>
      <div class="panel">
        <div class="panel-title">
          <h2>统一预审报告</h2>
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
                  <th>报告摘要</th>
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
      <div class="prep-grid" id="prepSummary"></div>
      <div class="review-grid">
        <aside class="panel">
          <div class="panel-title"><h2>本次应准备文档</h2></div>
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
              <div class="top-actions">
                <a id="openSourceLink" class="badge" href="#" target="_blank" rel="noreferrer">打开原文件</a>
                <button class="neutral" type="button" onclick="clearFocus()">清除定位</button>
              </div>
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

    <section id="match" class="screen">
      <div class="panel">
        <div class="panel-title">
          <h2>模板匹配与文档解析</h2>
          <span class="badge">进入预审前确认</span>
        </div>
        <div class="panel-body stack">
          <p class="muted">这一页说明每份材料为什么匹配当前模板、为什么进入路线 A 或路线 B，以及系统是否已经抽取出可检查内容。</p>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>上传文档</th>
                  <th>预期模板</th>
                  <th>匹配状态</th>
                  <th>解析状态</th>
                  <th>默认路线</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody id="matchRows"></tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <section id="fields" class="screen">
      <div class="panel">
        <div class="panel-title">
          <h2>路线 B：填写规范逐项预审</h2>
          <span class="badge">申请材料 vs 填写规范 vs 检查结论</span>
        </div>
        <div class="panel-body stack">
          <p class="muted">适用于没有 Template Plus 或关键检查项明确的材料。系统逐项展示文档提取内容、参考值/规范、结论、证据和建议动作。</p>
          <div id="fieldGrid" class="field-grid"></div>
        </div>
      </div>
    </section>

    <section id="diff" class="screen">
      <div class="panel">
        <div class="panel-title">
          <h2>路线 A：模板 Plus 差异预审</h2>
          <span class="badge">申请书 vs Template Plus 基准</span>
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

    <section id="config" class="screen active">
      <div class="panel">
          <div class="panel-title">
          <h2>模板配置中心</h2>
          <div class="top-actions">
            <select id="templateSelect" onchange="renderConfig()"></select>
            <button class="neutral" type="button" onclick="addConfigBlock()">新增区块</button>
            <button type="button" onclick="savePrototypeConfig()">保存当前配置</button>
          </div>
        </div>
        <div class="panel-body">
          <div class="template-config-layout">
            <aside class="stack">
              <div class="route-card">
                <strong>模板资产</strong>
                <span class="muted">围绕模板版本配置区块、锚点、Template Plus 和填写规范。</span>
                <span id="routeModeBadge"><span class="badge low">方案 A：有模板 Plus</span></span>
              </div>
              <div id="templateAssetList" class="material-list"></div>
            </aside>
            <section>
              <div class="doc-toolbar">
                <p class="muted">点击模板原文行，再在右侧配置区块；点击区块的“定位原文”可回到对应锚点。</p>
                <span class="badge" id="selectedAnchorLabel">未选择原文行</span>
              </div>
              <div id="configTemplatePreview" class="template-preview"></div>
            </section>
            <section>
              <div class="config-row header">
                <div>操作</div><div>区块/说明</div><div>锚点原文</div><div>eFlow 路径</div><div>AI</div><div>检查类型</div>
              </div>
              <div id="configRows"></div>
            </section>
          </div>
        </div>
      </div>
    </section>

    <section id="compare" class="screen">
      <div class="panel">
        <div class="panel-title">
          <h2>多路径对比</h2>
          <span class="badge">POC 方案比较</span>
        </div>
        <div class="panel-body stack">
          <p class="muted">同一材料包同时运行路线 A 和路线 B，对比发现问题、解释方式、模型调用和配置成本，方便 Demo 阶段讨论方案取舍。</p>
          <div id="compareRows" class="grid-3"></div>
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
      selectedPackageId: "PKG-CASE-001-PASS",
      selectedDocId: null,
      selectedRiskId: null,
      templates: null,
      prototypeConfig: {},
      deletedConfigKeys: new Set(),
      selectedTemplateAnchor: "",
      currentStage: "setup"
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
      const navButton = document.querySelector(`.nav button[data-screen="${id}"]`);
      if (navButton?.dataset.stage) {
        state.currentStage = navButton.dataset.stage;
      }
      renderStageNav();
      document.querySelectorAll(".nav button").forEach(item => item.classList.toggle("active", item.dataset.screen === id));
      document.querySelectorAll(".screen").forEach(item => item.classList.toggle("active", item.id === id));
    }

    function showStage(stage) {
      state.currentStage = stage;
      renderStageNav();
      const first = document.querySelector(`.nav button[data-stage="${stage}"]`);
      if (first) showScreen(first.dataset.screen);
    }

    function renderStageNav() {
      document.querySelectorAll(".stage-nav button").forEach(item => item.classList.toggle("active", item.dataset.stage === state.currentStage));
      document.querySelectorAll(".nav button").forEach(item => item.classList.toggle("hidden", item.dataset.stage !== state.currentStage));
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

    function routeMode() {
      return qs("routeMode").value;
    }

    function routeModeLabel() {
      const mode = routeMode();
      if (mode === "A") return "方案 A：有模板 Plus";
      if (mode === "B") return "方案 B：无模板 Plus";
      return "A/B 对比";
    }

    function switchRouteMode() {
      renderAll();
      const mode = routeMode();
      if (mode === "A") showScreen("diff");
      else if (mode === "B") showScreen("fields");
      else showScreen("compare");
      toast(`已切换为${routeModeLabel()}`);
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
      renderStageNav();
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
      const mode = routeMode();
      const strategies = mode === "A"
        ? ["template_plus_diff"]
        : mode === "B"
          ? ["block_rule_check"]
          : ["block_rule_check", "template_plus_diff", "full_agent_review"];
      const data = await api(`/api/packages/${state.selectedPackageId}/run-comparison`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategies,
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
      renderPrepSummary();
      renderMaterials();
      renderDocument();
      renderRisks();
      renderFields();
      renderDiff();
      renderConfig();
      renderMatch();
      renderCompare();
    }

    function renderPrepSummary() {
      const pkg = currentPackage();
      if (!pkg) return;
      const docs = [...pkg.submitted_documents, ...pkg.identity_documents];
      const ready = docs.filter(item => item.text || item.preview_text || item.preview_url).length;
      const routeA = pkg.expected_template_set?.length ? "可进入" : "待确认";
      const routeB = docs.length ? "可进入" : "待补充";
      qs("prepSummary").innerHTML = `
        <div class="metric"><span>申请场景</span><strong>${pkg.eflow.bank}</strong><div class="tiny">${pkg.eflow.platform}</div></div>
        <div class="metric"><span>应准备文档</span><strong>${docs.length}</strong><div class="tiny">申请表 + 身份证明</div></div>
        <div class="metric"><span>已上传/已挂载</span><strong>${ready}/${docs.length}</strong><div class="tiny">真实 Word/PDF/图片或上传文本</div></div>
        <div class="metric"><span>可进入预审</span><strong>${ready === docs.length ? "是" : "否"}</strong><div class="tiny">路线 A：${routeA} / 路线 B：${routeB}</div></div>
      `;
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
          <div class="tiny">${doc.group} / ${doc.file_type}${doc.preview_url ? " / 真实文件" : ""}</div>
          <div style="margin-top:6px">${badge(doc.match_status || "matched")} ${doc.text || doc.preview_text ? badge("已解析") : badge("待解析")}</div>
        </div>
      `).join("");
    }

    function renderMatch() {
      const pkg = currentPackage();
      if (!pkg) return;
      const docs = [...pkg.submitted_documents, ...pkg.identity_documents];
      qs("matchRows").innerHTML = docs.map(doc => {
        const mode = routeMode();
        const canUsePlus = pkg.expected_template_set?.length > 0 && !["jpg", "jpeg", "png"].includes(doc.file_type);
        const hasPlus = mode === "A" ? canUsePlus : mode === "B" ? false : canUsePlus;
        const route = hasPlus ? "路线 A：模板 Plus 差异预审" : "路线 B：填写规范逐项预审";
        const explanation = hasPlus
          ? "当前选择方案 A。该申请表已匹配模板版本，系统将以“申请书 vs Template Plus 基准”为核心检查差异。"
          : "当前选择方案 B 或该材料不适用 Template Plus。系统将按已配置的填写规范、证件或附件规则逐项检查。";
        return `<tr>
          <td><strong>${doc.file_name}</strong><div class="tiny">${doc.file_type}${doc.preview_url ? " / 原文件可打开" : ""}</div></td>
          <td>${doc.matched_template_version_id || "证件/附件规则"}</td>
          <td>${badge(doc.match_status || "suspected")}<div class="tiny">置信度：${Math.round((doc.match_confidence || 0) * 100)}%</div></td>
          <td>${doc.text || doc.preview_text ? badge("文本已解析") : badge("待解析")}</td>
          <td>${route}</td>
          <td class="muted">${explanation}</td>
        </tr>`;
      }).join("") || `<tr><td colspan="6" class="muted">暂无材料。</td></tr>`;
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
      const sourceLink = qs("openSourceLink");
      if (doc.preview_url) {
        sourceLink.href = doc.preview_url;
        sourceLink.classList.remove("hidden");
      } else {
        sourceLink.href = "#";
        sourceLink.classList.add("hidden");
      }
      const marks = evidenceTexts();
      const previewText = doc.preview_text || doc.text || "暂无正文";
      const lines = String(previewText).split(/\r?\n/);
      const nativePreview = nativePreviewHtml(doc);
      qs("docPage").innerHTML = `
        ${nativePreview}
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
      renderRichOfficePreview(doc);
    }

    function nativePreviewHtml(doc) {
      if (!doc.preview_url) return "";
      const type = String(doc.file_type || "").toLowerCase();
      if (type === "pdf") {
        return `<div class="native-preview"><iframe src="${escapeAttr(doc.preview_url)}" title="${escapeAttr(doc.file_name)}"></iframe></div>`;
      }
      if (["jpg", "jpeg", "png"].includes(type)) {
        return `<div class="native-preview"><img src="${escapeAttr(doc.preview_url)}" alt="${escapeAttr(doc.file_name)}" /></div>`;
      }
      if (["docx", "xlsx", "xlsm", "xls"].includes(type)) {
        return `<div id="richOfficePreview" class="office-preview-message">
          正在渲染 ${escapeHtml(doc.file_name)}。如果浏览器无法加载预览插件，将显示系统抽取文本。
        </div>`;
      }
      return `<div class="native-preview" style="padding:12px">
        <strong>原始文件：</strong>${escapeHtml(doc.file_name)}
        <div class="tiny">该类型暂不支持内嵌预览，这里展示系统抽取文本，并保留原文件打开入口。</div>
      </div>`;
    }

    async function renderRichOfficePreview(doc) {
      const holder = document.getElementById("richOfficePreview");
      if (!holder || !doc.preview_url) return;
      const type = String(doc.file_type || "").toLowerCase();
      try {
        const response = await fetch(doc.preview_url);
        const buffer = await response.arrayBuffer();
        if (type === "docx") {
          if (!window.mammoth) {
            holder.textContent = "Word 预览插件未加载，已显示系统抽取文本。";
            return;
          }
          const result = await window.mammoth.convertToHtml({ arrayBuffer: buffer });
          holder.className = "office-preview";
          holder.innerHTML = result.value || "<p>Word 文件未解析出可展示内容。</p>";
          return;
        }
        if (["xlsx", "xlsm", "xls"].includes(type)) {
          if (!window.XLSX) {
            holder.textContent = "Excel 预览插件未加载，已显示系统抽取文本。";
            return;
          }
          const workbook = window.XLSX.read(buffer, { type: "array" });
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
          holder.className = "office-preview";
          holder.innerHTML = window.XLSX.utils.sheet_to_html(firstSheet);
        }
      } catch (error) {
        holder.textContent = `原文件预览失败，已保留抽取文本。${error.message || ""}`;
      }
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

    function renderCompare() {
      const reports = state.reports || [];
      const byStrategy = new Map(reports.map(report => [report.strategy, report]));
      const routeA = byStrategy.get("template_plus_diff");
      const routeB = byStrategy.get("block_rule_check");
      const agent = byStrategy.get("full_agent_review");
      const cards = [
        {
          title: "路线 A：模板 Plus",
          mode: "看最终申请书相对标准预填模板变了什么",
          report: routeA,
          cost: "配置成本：中；需要维护模板基准和差异分类"
        },
        {
          title: "路线 B：填写规范",
          mode: "看文档内容是否逐项符合 eFlow、证件和规则",
          report: routeB,
          cost: "配置成本：高；需要维护区块、字段和规则"
        },
        {
          title: "全文 Agent 兜底",
          mode: "在规则和模板之外提示非结构化风险",
          report: agent,
          cost: "配置成本：低；但需要约束输出和人工确认"
        }
      ];
      qs("compareRows").innerHTML = cards.map(card => {
        const report = card.report;
        const issueCount = report?.metrics?.detected_issues_count ?? "-";
        const llmCalls = report?.metrics?.llm_calls ?? "-";
        const manual = report?.results?.filter(item => item.manual_confirm_required).length ?? "-";
        return `<div class="route-card">
          <strong>${card.title}</strong>
          <span class="muted">${card.mode}</span>
          <div>${badge(report ? "已运行" : "未运行")}</div>
          <div class="tiny">发现问题：${issueCount} / 人工确认：${manual} / 模型调用：${llmCalls}</div>
          <div class="tiny">${card.cost}</div>
          <div class="tiny">${report?.summary || "运行当前案例后显示摘要。"}</div>
        </div>`;
      }).join("");
    }

    function renderConfig() {
      if (!state.templates) return;
      const routeBadge = qs("routeModeBadge");
      if (routeBadge) {
        const mode = routeMode();
        routeBadge.innerHTML = mode === "A"
          ? `<span class="badge low">当前：方案 A，有模板 Plus</span>`
          : mode === "B"
            ? `<span class="badge medium">当前：方案 B，无模板 Plus</span>`
            : `<span class="badge">当前：A/B 对比</span>`;
      }
      const templateVersionId = qs("templateSelect").value || state.templates.template_versions?.[0]?.template_version_id;
      const templateVersion = state.templates.template_versions?.find(item => item.template_version_id === templateVersionId);
      const templatePlus = state.templates.template_plus?.find(item => item.template_version_id === templateVersionId);
      qs("templateAssetList").innerHTML = `
        <div class="material-item active">
          <strong>${templateVersion?.template_version_id || templateVersionId}</strong>
          <div class="tiny">模板版本：${templateVersion?.version || "-"}</div>
          <div style="margin-top:6px">${templatePlus ? badge("Template Plus") : badge("填写规范")}</div>
        </div>
        <div class="material-item">
          <strong>固定内容与变量槽</strong>
          <div class="tiny">${templatePlus ? templatePlus.variable_slots.join(", ") : "未配置 Template Plus 变量槽"}</div>
        </div>
      `;
      renderConfigTemplatePreview(templateVersionId);
      renderConfigRows(templateVersionId);
    }

    function renderConfigTemplatePreview(templateVersionId) {
      const text = templateBaselineText(templateVersionId);
      const lines = text.split(/\r?\n/).filter(line => line.trim());
      qs("configTemplatePreview").innerHTML = lines.map((line, index) => `
        <div id="tpl-line-${index}" class="template-line ${line === state.selectedTemplateAnchor ? "focused" : ""}" onclick="selectTemplateAnchor(${index})">
          <div class="line-no">L${index + 1}</div>
          <div>${escapeHtml(line)}</div>
        </div>
      `).join("") || `<p class="muted">当前模板没有可展示的基准原文。</p>`;
      qs("selectedAnchorLabel").textContent = state.selectedTemplateAnchor ? `已选择：${state.selectedTemplateAnchor}` : "未选择原文行";
    }

    function renderConfigRows(templateVersionId) {
      const baseBlocks = state.templates.template_blocks?.[templateVersionId] || [];
      const baseRows = baseBlocks.map(block => {
        const key = configKey(templateVersionId, block.block_id);
        return { key, value: { ...block, ...(state.prototypeConfig[key] || {}) } };
      });
      const addedRows = Object.entries(state.prototypeConfig)
        .filter(([key]) => key.startsWith(`${templateVersionId}-NEW-`) && !state.deletedConfigKeys.has(key))
        .map(([key, value]) => ({ key, value }));
      const rows = [...baseRows, ...addedRows].filter(row => !state.deletedConfigKeys.has(row.key));
      qs("configRows").innerHTML = rows.map(row => {
        const saved = row.value;
        return `<div class="config-row">
          <div class="stack">
            <button class="neutral" type="button" onclick="focusTemplateAnchor(${jsString(saved.anchor_text || "")})">定位原文</button>
            <button class="neutral" type="button" onclick="duplicateConfigBlock('${row.key}')">复制</button>
            <button class="secondary" type="button" onclick="deleteConfigBlock('${row.key}')">删除</button>
          </div>
          <div>
            <input value="${escapeAttr(saved.block_name || "")}" onchange="setConfig('${row.key}','block_name',this.value)" />
            <textarea onchange="setConfig('${row.key}','fill_instruction',this.value)">${escapeHtml(saved.fill_instruction || saved.business_meaning || "")}</textarea>
          </div>
          <textarea onchange="setConfig('${row.key}','anchor_text',this.value)">${escapeHtml(saved.anchor_text || "")}</textarea>
          <input value="${escapeAttr(saved.expected_eflow_path || "")}" onchange="setConfig('${row.key}','expected_eflow_path',this.value)" />
          <select onchange="setConfig('${row.key}','ai_required',this.value === 'true')">
            <option value="false" ${!saved.ai_required ? "selected" : ""}>否</option>
            <option value="true" ${saved.ai_required ? "selected" : ""}>是</option>
          </select>
          <select onchange="setConfig('${row.key}','check_type',this.value)">
            ${["normalized_match","contains_all","activity_match","count_match","max_limit_review"].map(type => `<option value="${type}" ${saved.check_type === type ? "selected" : ""}>${type}</option>`).join("")}
          </select>
        </div>`;
      }).join("") || `<p class="muted">当前模板没有配置区块。</p>`;
    }

    function templateBaselineText(templateVersionId) {
      const templatePlus = state.templates.template_plus?.find(item => item.template_version_id === templateVersionId);
      if (templatePlus?.baseline_text) return templatePlus.baseline_text;
      const blocks = state.templates.template_blocks?.[templateVersionId] || [];
      return blocks.map(block => `${block.anchor_text}: <${block.expected_eflow_path || block.block_name}>`).join("\n");
    }

    function configKey(templateVersionId, blockId) {
      return `${templateVersionId}-${blockId}`;
    }

    function selectTemplateAnchor(index) {
      const line = document.querySelector(`#tpl-line-${index}`);
      state.selectedTemplateAnchor = line?.innerText.replace(/^L\d+\s*/, "").trim() || "";
      renderConfig();
    }

    function focusTemplateAnchor(anchor) {
      state.selectedTemplateAnchor = anchor;
      renderConfig();
      const lines = [...document.querySelectorAll(".template-line")];
      const target = lines.find(line => line.textContent.includes(anchor));
      if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function addConfigBlock() {
      const templateVersionId = qs("templateSelect").value || state.templates.template_versions?.[0]?.template_version_id;
      const key = `${templateVersionId}-NEW-${Date.now()}`;
      state.prototypeConfig[key] = {
        block_id: key,
        block_name: "新检查区块",
        fill_instruction: "请维护该区块的业务含义、填写规范和检查依据。",
        anchor_text: state.selectedTemplateAnchor || "请先选择模板原文行",
        expected_eflow_path: "",
        check_type: "normalized_match",
        ai_required: false,
      };
      renderConfig();
      toast("已新增区块，请绑定原文锚点和 eFlow 路径。");
    }

    function duplicateConfigBlock(key) {
      const source = state.prototypeConfig[key] || findConfigBlockByKey(key);
      if (!source) return;
      const templateVersionId = qs("templateSelect").value || state.templates.template_versions?.[0]?.template_version_id;
      const newKey = `${templateVersionId}-NEW-${Date.now()}`;
      state.prototypeConfig[newKey] = { ...source, block_id: newKey, block_name: `${source.block_name || "区块"} 副本` };
      renderConfig();
    }

    function deleteConfigBlock(key) {
      state.deletedConfigKeys.add(key);
      renderConfig();
    }

    function findConfigBlockByKey(key) {
      const templateVersionId = qs("templateSelect").value || state.templates.template_versions?.[0]?.template_version_id;
      const blockId = key.replace(`${templateVersionId}-`, "");
      return state.templates.template_blocks?.[templateVersionId]?.find(block => block.block_id === blockId);
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

    function jsString(value) {
      return JSON.stringify(String(value ?? ""));
    }

    init().catch(error => toast(error.message, true));
  </script>
</body>
</html>
"""
