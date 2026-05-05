const API_BASE = '/api/audit';
const CFG_KEY = 'audit_llm_config_v2';
const DEFAULT_PRIORITY_ISSUES = 8;
let CURRENT_REPORT = null;
let CURRENT_ISSUE_ITEMS = [];
let CURRENT_BOARD_ITEMS = [];
let ISSUE_BOARD_EXPANDED = false;

document.addEventListener('DOMContentLoaded', () => {
    initSettings();
    initUploadHandlers();
    loadTestCases();
    initReportInteractions();
});

// === 1. 基础 UI 交互 ===

function showLoading(show) {
    const el = document.getElementById('loading-overlay');
    if (el) el.classList.toggle('show', show);
}

function initUploadHandlers() {
    ['eflow', 'bank', 'id'].forEach(type => {
        const zone     = document.getElementById(`zone-${type}`);
        const input    = document.getElementById(`file-${type}`);
        const nameNode = document.getElementById(`name-${type}`);
        if(!zone || !input) return;
        zone.onclick = () => input.click();
        input.onchange = () => {
            if (input.files.length > 0) {
                nameNode.innerText = input.files.length === 1
                    ? input.files[0].name
                    : `已选择 ${input.files.length} 个文件`;
                zone.style.borderColor = 'var(--audit-blue)';
                zone.style.background  = '#f0f7ff';
            }
        };
    });

    document.getElementById('upload-form').onsubmit = async (e) => {
        e.preventDefault();
        runAudit('/run', new FormData(e.target));
    };

    const runBtn = document.getElementById('btn-run-case');
    if (runBtn) {
        runBtn.onclick = () => {
            const caseId = document.getElementById('case-select').value;
            if (!caseId) return alert('请先选择一个用例');
            runBtn.disabled = true;
            runBtn.innerHTML = "<i class='ri-loader-4-line'></i> 正在提交...";
            const descEl = document.getElementById('status-desc');
            if (descEl) descEl.innerText = `[${new Date().toLocaleTimeString()}] 已提交用例: ${caseId}，正在全量审计研判，请耐心等待...`;
            const fd = new FormData();
            fd.append('case_id', caseId);
            runAudit('/run-from-testcase', fd, () => {
                runBtn.disabled = false;
                runBtn.innerHTML = "<i class='ri-play-fill'></i> 运行用例";
            });
        };
    }

    const closeBtn = document.getElementById('close-modal');
    if (closeBtn) {
        closeBtn.onclick = () => {
            document.getElementById('full-text-modal').style.display = 'none';
        };
    }
}

// === 2. 核心审计执行 ===

async function runAudit(endpoint, formData, callback) {
    showLoading(true);
    try {
        console.log(`[Audit] Sending request to ${endpoint}...`);
        const resp = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', body: formData });
        if (!resp.ok) {
            const errBody = await resp.text();
            throw new Error(`HTTP ${resp.status}: ${errBody}`);
        }
        const result = await resp.json();
        console.log('[Audit] Response received:', result);
        if (result.status === 'error') throw new Error(result.error);
        renderV15Report(result.report || result);
    } catch (err) {
        console.error('[Audit] Execution Error:', err);
        alert('审计任务失败: ' + err.message);
    } finally {
        showLoading(false);
        if (callback) callback();
    }
}

// === 3. 渲染引擎 V15.25 ===

function renderV15Report(rp) {
    CURRENT_REPORT = rp;
    const panel = document.getElementById('result-panel');
    if (panel) panel.style.display = 'block';

    // 1. 状态画像卡片
    const status = rp.overall_status || 'ZERO_RISK';
    const card   = document.getElementById('summary-card');
    if (card) {
        card.className = `card result-summary risk-${status}`;
        const statusMap = {
            'HIGH_RISK': { title: '高风险关注：建议人工重点复核', icon: 'ri-alarm-warning-fill' },
            'MED_RISK':  { title: '建议人工核议：存在逻辑偏离',   icon: 'ri-error-warning-line' },
            'LOW_RISK':  { title: '轻微偏离提醒：要素基本一致',   icon: 'ri-information-line' },
            'ZERO_RISK': { title: '全量预审通过：要素高度一致',   icon: 'ri-checkbox-circle-line' }
        };
        const info = statusMap[status] || statusMap['ZERO_RISK'];
        document.getElementById('status-icon').innerHTML  = `<i class='${info.icon}'></i>`;
        document.getElementById('status-title').innerText = info.title;
        const docCount = (rp.document_reports || []).length;
        const scenarioText = rp.scenario_summary ? ` | ${rp.scenario_summary}` : '';
        document.getElementById('status-desc').innerText  = `任务ID: ${rp.task_id} | ${docCount} 份文档${scenarioText}`;
    }

    // 2. AI 风险洞察
    renderRiskInsights(rp.llm_summary, rp);

    // 3. 建议优先复核事项：从结论进入证据与明细
    renderPriorityIssueBoard(rp);

    // 4. 两级折叠审计明细
    renderClusteredChecks(rp);

    window.scrollTo({ top: 300, behavior: 'smooth' });
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function normalizeSeverity(sev) {
    return String(sev || 'PASS').toUpperCase();
}

function severityRank(sev) {
    const s = normalizeSeverity(sev);
    if (s === 'CRITICAL') return 0;
    if (s === 'WARNING') return 1;
    if (s === 'INFO') return 2;
    return 3;
}

function coreFieldRank(check) {
    const group = String(check.field_group || '').toLowerCase();
    const name = String(check.field_name || '').toLowerCase();
    const reason = String(check.reason_code || '').toLowerCase();
    if (['business_scenario', 'account', 'permission', 'media', 'subject', 'platform'].includes(group)) return 0;
    if (['account', 'permission', 'media', 'scenario', 'person', 'cert', 'id', 'platform'].some(k => name.includes(k) || reason.includes(k))) return 1;
    return 2;
}

function priorityScore(item) {
    const c = item.check || {};
    return severityRank(c.severity) * 100
        + coreFieldRank(c) * 10
        + (c.manual_confirmation_required ? 0 : 4);
}

function severityLabel(sev) {
    const s = normalizeSeverity(sev);
    return {
        CRITICAL: '重点风险',
        WARNING: '风险提示',
        INFO: '优化建议',
        PASS: '已通过'
    }[s] || s;
}

function issueActionText(check) {
    if (check.manual_confirmation_required) return '建议人工确认后再按原流程办理';
    const sev = normalizeSeverity(check.severity);
    if (sev === 'CRITICAL') return '建议优先核实并补充/修正';
    if (sev === 'WARNING') return '建议审核人重点复核';
    return '可作为材料优化参考';
}

function collectIssueItems(report) {
    const items = [];
    (report.document_reports || []).forEach(doc => {
        const checks = [...(doc.hard_checks || []), ...(doc.semantic_checks || [])];
        checks.forEach(check => {
            if (normalizeSeverity(check.severity) === 'PASS') return;
            items.push({
                doc_name: doc.doc_name || '未知文档',
                doc_type: doc.doc_type || '',
                extracted_data: doc.extracted_data || {},
                check,
                priority: severityRank(check.severity)
            });
        });
    });

    (report.cross_validation_checks || []).forEach(check => {
        if (normalizeSeverity(check.severity) === 'PASS') return;
        items.push({
            doc_name: '跨文档检查',
            doc_type: 'cross_validation',
            extracted_data: {},
            check,
            priority: severityRank(check.severity)
        });
    });

    const seen = new Set();
    const deduped = [];
    items.sort((a, b) => a.priority - b.priority).forEach(item => {
        const c = item.check || {};
        const key = [
            item.doc_name,
            c.reason_code || c.check_name || '',
            c.field_group || '',
            c.field_name || '',
            String(c.detail || '').slice(0, 80)
        ].join('|');
        if (seen.has(key)) return;
        seen.add(key);
        deduped.push(item);
    });
    return deduped;
}

function pickBoardIssues(items) {
    const sorted = [...items].sort((a, b) => priorityScore(a) - priorityScore(b));
    return ISSUE_BOARD_EXPANDED ? sorted : sorted.slice(0, DEFAULT_PRIORITY_ISSUES);
}

function toggleIssueBoardExpanded() {
    ISSUE_BOARD_EXPANDED = !ISSUE_BOARD_EXPANDED;
    if (CURRENT_REPORT) renderPriorityIssueBoard(CURRENT_REPORT);
}

function renderPriorityIssueBoard(report) {
    const container = document.getElementById('priority-issue-board');
    if (!container) return;
    CURRENT_REPORT = report;

    CURRENT_ISSUE_ITEMS = collectIssueItems(report);
    CURRENT_BOARD_ITEMS = pickBoardIssues(CURRENT_ISSUE_ITEMS);
    closeEvidenceDrawer();

    if (CURRENT_BOARD_ITEMS.length === 0) {
        container.innerHTML = `
            <div class="issue-empty-state">
                <i class="ri-checkbox-circle-line"></i>
                <div>
                    <strong>未发现需要优先复核的事项</strong>
                    <p>系统没有识别到重点风险、风险提示或人工确认项，可按需展开完整审计明细复核每份文件的抽取事实和规则命中。</p>
                </div>
            </div>`;
        return;
    }

    const total = CURRENT_ISSUE_ITEMS.length;
    const shown = CURRENT_BOARD_ITEMS.length;
    const hidden = Math.max(CURRENT_ISSUE_ITEMS.length - CURRENT_BOARD_ITEMS.length, 0);
    const expandButton = hidden > 0 || ISSUE_BOARD_EXPANDED
        ? `<button type="button" class="issue-expand-btn" onclick="toggleIssueBoardExpanded()">${ISSUE_BOARD_EXPANDED ? '收起为优先事项' : `展开其余 ${hidden} 项`}</button>`
        : '';

    const cards = CURRENT_BOARD_ITEMS.map((item) => {
        const c = item.check;
        const sev = normalizeSeverity(c.severity).toLowerCase();
        const evidenceIndex = CURRENT_ISSUE_ITEMS.indexOf(item);
        return `
            <div class="issue-card sev-${sev}">
                <div class="issue-card-topline">
                    <span class="issue-severity-pill">${severityLabel(c.severity)}</span>
                    ${c.manual_confirmation_required ? '<span class="issue-manual-pill">需人工确认</span>' : ''}
                    <span class="issue-doc-name" title="${escapeHtml(item.doc_name)}">${escapeHtml(item.doc_name)}</span>
                </div>
                <div class="issue-title">${escapeHtml(c.check_name || '未命名检查项')}</div>
                <div class="issue-detail">${escapeHtml(c.detail || '暂无详细说明')}</div>
                <div class="issue-meta-row">
                    ${c.field_group ? `<span>字段簇：${escapeHtml(c.field_group)}</span>` : ''}
                    ${c.check_mode ? `<span>方式：${escapeHtml(c.check_mode)}</span>` : ''}
                    ${c.reason_code ? `<span>规则码：${escapeHtml(c.reason_code)}</span>` : ''}
                </div>
                <div class="issue-action">${escapeHtml(issueActionText(c))}</div>
                <div class="issue-actions">
                    <button type="button" onclick="showEvidence(${evidenceIndex})"><i class="ri-search-eye-line"></i> 查看依据</button>
                </div>
            </div>`;
    }).join('');

    container.innerHTML = `
        <div class="issue-board-summary issue-board-summary-simple">
            <span><strong>${total}</strong> 全部需关注事项</span>
            <span><strong>${shown}</strong> 当前优先展示</span>
        </div>
        <div class="issue-board-hint">
            <strong>排序依据：</strong>风险影响程度、是否需要人工确认、是否涉及核心字段（业务场景、主体、账号、权限、介质、平台、证件有效期）。
            ${hidden > 0 ? `默认收起 ${hidden} 项低优先级事项。` : '当前已展示全部需关注事项。'}
            这里是辅助排序，不改变原有业务办理链路；完整底稿仍以下方审计明细为准。
            ${expandButton}
        </div>
        <div class="issue-card-grid">${cards}</div>`;
}

function buildEvidenceSnippet(item) {
    const c = item.check || {};
    const ed = item.extracted_data || {};
    const raw = ed.evidence_summary || ed.action_summary || ed.raw_text || '';
    if (!raw) return '暂无可展示的解析依据。';
    return String(raw).slice(0, 2200);
}

function showEvidence(index) {
    const item = CURRENT_ISSUE_ITEMS[index];
    if (!item) return;

    const drawer = document.getElementById('evidence-drawer');
    const title = document.getElementById('evidence-title');
    const content = document.getElementById('evidence-content');
    if (!drawer || !title || !content) return;

    const c = item.check || {};
    title.innerText = c.check_name || '查看依据';
    content.innerHTML = `
        <div class="evidence-section evidence-risk">
            <div class="evidence-risk-title">${escapeHtml(severityLabel(c.severity))}</div>
            <div class="evidence-risk-detail">${escapeHtml(c.detail || '暂无检查说明')}</div>
        </div>
        <div class="evidence-grid">
            <div class="evidence-field">
                <label>${escapeHtml(c.source_a_label || 'EFlow 基准')}</label>
                <div>${escapeHtml(c.source_a_value || '/')}</div>
            </div>
            <div class="evidence-field">
                <label>${escapeHtml(c.source_b_label || item.doc_name || '文档抽取')}</label>
                <div>${escapeHtml(c.source_b_value || '/')}</div>
            </div>
        </div>
        <div class="evidence-meta">
            <span>来源文档：${escapeHtml(item.doc_name)}</span>
            ${c.field_group ? `<span>字段簇：${escapeHtml(c.field_group)}</span>` : ''}
            ${c.field_name ? `<span>字段：${escapeHtml(c.field_name)}</span>` : ''}
            ${c.check_mode ? `<span>检查方式：${escapeHtml(c.check_mode)}</span>` : ''}
            ${c.scenario_type ? `<span>场景：${escapeHtml(c.scenario_type)}</span>` : ''}
            ${c.reason_code ? `<span>规则码：${escapeHtml(c.reason_code)}</span>` : ''}
        </div>
        ${c.manual_confirmation_required ? '<div class="evidence-manual"><i class="ri-user-search-line"></i> 该事项需要人工确认，系统仅作辅助提示。</div>' : ''}
        <div class="evidence-section">
            <h4>解析依据 / 原文片段</h4>
            <pre>${escapeHtml(buildEvidenceSnippet(item))}</pre>
        </div>`;

    drawer.style.display = 'block';
}

function closeEvidenceDrawer() {
    const drawer = document.getElementById('evidence-drawer');
    if (drawer) drawer.style.display = 'none';
}

function getEvidenceIndexForCheck(check, docName) {
    return CURRENT_ISSUE_ITEMS.findIndex(item =>
        item.check === check || (
            item.doc_name === docName &&
            item.check.check_name === check.check_name &&
            item.check.reason_code === check.reason_code &&
            item.check.field_name === check.field_name
        )
    );
}

function initReportInteractions() {
    const closeEvidence = document.getElementById('btn-close-evidence');
    if (closeEvidence) closeEvidence.onclick = closeEvidenceDrawer;
}

// --- 2.1 AI 风险洞察卡片 ---
function compactList(values, fallback = '未识别') {
    const cleaned = values.filter(Boolean).map(v => String(v).trim()).filter(Boolean);
    const unique = [...new Set(cleaned)];
    if (unique.length === 0) return fallback;
    if (unique.length <= 3) return unique.join('、');
    return `${unique.slice(0, 3).join('、')} 等 ${unique.length} 项`;
}

function describeEflowBusiness(ef) {
    if (!ef) return '电子流基准事实未返回。';
    const users = ef.users || [];
    const userNames = compactList(users.map(u => u.user_name), '未识别名义用户');
    const accounts = compactList(users.map(u => u.account_number), '未识别账户');
    const permissions = compactList(users.flatMap(u => {
        const sc = u.permission_scope || {};
        return [
            sc.authorize ? '授权' : '',
            sc.payment ? '支付' : '',
            sc.query ? '查询' : '',
            sc.upload ? '上传' : ''
        ];
    }), '未识别权限');
    const media = compactList(users.map(u => u.media?.media_type), '未识别介质');
    const scenario = compactList([ef.business_type, ef.business_scenario], '未识别业务场景');
    const platform = compactList([ef.platform?.bank_name, ef.platform?.platform_name], '未识别平台');
    return `电子流基准显示：本次拟办理 ${scenario}，涉及 ${platform}，名义用户 ${userNames}，账户 ${accounts}，权限 ${permissions}，介质 ${media}。`;
}

function describeDocsBusiness(reports) {
    const docs = reports || [];
    if (docs.length === 0) return '未返回申请材料解析结果。';
    const scenarios = compactList(docs.map(d => d.extracted_data?.scenario_type), '未识别文档场景');
    const actions = compactList(docs.map(d => d.extracted_data?.action_type), '未识别文档动作');
    const summaries = docs
        .map(d => d.extracted_data?.action_summary || d.extracted_data?.business_activity)
        .filter(Boolean);
    const summaryText = compactList(summaries, '文档未形成明确业务摘要');
    return `材料解析显示：上传材料共 ${docs.length} 份，文档侧主要识别为 ${scenarios} / ${actions}，业务表述为：${summaryText}。`;
}

function renderBusinessContextSummary(report) {
    const node = document.getElementById('business-context-summary');
    if (!node) return;
    node.style.display = 'grid';
    node.innerHTML = `
        <div class="business-context-item">
            <label>电子流应办理</label>
            <p>${escapeHtml(describeEflowBusiness(report.eflow_data))}</p>
        </div>
        <div class="business-context-item">
            <label>材料实际说明</label>
            <p>${escapeHtml(describeDocsBusiness(report.document_reports))}</p>
        </div>`;
}

function renderRiskInsights(llmSummary, report) {
    const card = document.getElementById('llm-summary-card');
    if (!card) return;
    if (!llmSummary || !llmSummary.aggregator_summary) {
        card.style.display = 'none';
        return;
    }
    card.style.display = 'block';
    renderBusinessContextSummary(report || CURRENT_REPORT || {});

    const scenarioNode = document.getElementById('scenario-summary');
    if (scenarioNode) {
        if (llmSummary.scenario_summary) {
            scenarioNode.style.display = 'block';
            scenarioNode.innerHTML = `<strong>场景摘要：</strong>${escapeHtml(llmSummary.scenario_summary)}`;
        } else {
            scenarioNode.style.display = 'none';
        }
    }

    const aggNode = document.getElementById('aggregator-text');
    if (aggNode) aggNode.innerText = llmSummary.aggregator_summary;

    const riskList = document.getElementById('llm-risk-insights');
    if (riskList) {
        const insights = (llmSummary.risk_insights || []).slice(0, 3);
        riskList.innerHTML = insights.map(r =>
            `<div class="insight-card"><i class="ri-error-warning-fill insight-icon"></i><span>${escapeHtml(r)}</span></div>`
        ).join('');
    }

    const manualList = document.getElementById('manual-confirmation-list');
    if (manualList) {
        const items = llmSummary.manual_confirmation_items || [];
        if (items.length > 0) {
            manualList.style.display = 'block';
            manualList.innerHTML = `
                <div class="manual-summary-card">
                    <i class="ri-user-search-line manual-confirm-icon"></i>
                    <span>共 ${items.length} 项建议人工确认，具体事项已进入下方“建议优先复核事项”和“完整审计明细”。</span>
                </div>
            `;
        } else {
            manualList.style.display = 'none';
            manualList.innerHTML = '';
        }
    }
}

// --- 2.2 EFlow 手风琴（复用文档组件 + 摘要副标题）---
function renderEFlowAccordion(ef) {
    const container = document.getElementById('ext-eflow');
    if (!container || !ef) return;
    container.innerHTML = '';

    // 生成 KV 行（grid 两列）；值为 null/空 跳过
    function kvRow(k, v) {
        if (v === null || v === undefined || v === '' || v === 0.0) return '';
        const display = v === true ? '✓ 是' : v === false ? '✗ 否' : String(v);
        return `<div class="doc-kv-key">${k}</div><div class="doc-kv-val">${display}</div>`;
    }

    // 创建折叠条：复用已验证的 doc-accordion-item 类
    function makeSection(icon, title, summary, kvHtml, defaultOpen) {
        if (!kvHtml.trim()) return;
        const item = document.createElement('div');
        item.className = `doc-accordion-item${defaultOpen ? ' open' : ''}`;
        item.innerHTML = `
            <div class="doc-acc-header" onclick="this.parentElement.classList.toggle('open')">
                <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">
                    <i class="${icon}" style="color:#64748b;flex-shrink:0;font-size:15px;"></i>
                    <div style="min-width:0;">
                        <div class="doc-filename" style="max-width:none;">${title}</div>
                        ${summary ? `<div style="font-size:11px;color:#94a3b8;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${summary}</div>` : ''}
                    </div>
                </div>
                <i class="ri-arrow-down-s-line doc-arrow"></i>
            </div>
            <div class="doc-acc-content">
                <div style="display:grid;grid-template-columns:auto 1fr;gap:5px 12px;align-items:start;">
                    ${kvHtml}
                </div>
            </div>`;
        container.appendChild(item);
    }

    // 业务信息
    const bizSummary = [ef.business_type, ef.business_scenario].filter(Boolean).join(' · ');
    let kv = kvRow('业务类型', ef.business_type)
           + kvRow('业务场景', ef.business_scenario)
           + kvRow('流程 ID',  ef.flow_id);
    makeSection('ri-briefcase-line', '业务信息', bizSummary, kv, true);

    // 网银平台
    const p = ef.platform || {};
    const platSummary = [p.bank_name, p.platform_name].filter(Boolean).join(' · ');
    kv = kvRow('银行名称', p.bank_name)
       + kvRow('平台名称', p.platform_name)
       + kvRow('国家/地区', p.country)
       + kvRow('分行', p.branch_name)
       + kvRow('登录入口', p.login_url)
       + kvRow('平台代码', p.platform_code);
    makeSection('ri-global-line', '网银平台', platSummary, kv, false);

    // 申请公司
    const co = ef.company || {};
    const coSummary = [co.name, co.cert_type].filter(Boolean).join(' · ');
    kv = kvRow('公司名称', co.name)
       + kvRow('英文名称', co.name_en)
       + kvRow('证件类型', co.cert_type)
       + kvRow('证件号码', co.cert_number)
       + kvRow('法定代表人', co.legal_representative)
       + kvRow('联系电话', co.phone)
       + kvRow('所属行业', co.industry);
    makeSection('ri-building-line', '申请公司', coSummary, kv, false);

    // 申请人
    const a = ef.applicant || {};
    const appSummary = [a.name, a.department].filter(Boolean).join(' · ');
    kv = kvRow('姓名', a.name)
       + kvRow('部门', a.department)
       + kvRow('证件号', a.id_number)
       + kvRow('角色', a.role)
       + kvRow('联系电话', a.phone);
    makeSection('ri-user-received-line', '申请人信息', appSummary, kv, false);

    // 每个操作员独立一个折叠条
    (ef.users || []).forEach((u, i) => {
        const sc = u.permission_scope || {};
        const perms = ['authorize','payment','query','upload']
            .filter(k => sc[k] === true)
            .map(k => ({ authorize:'授权', payment:'支付', query:'查询', upload:'上传' }[k]))
            .join('/');
        const userSummary = [u.media?.media_type ? `介质:${u.media.media_type}` : '', perms ? `权限:${perms}` : ''].filter(Boolean).join(' · ');
        kv = kvRow('用户名', u.user_name)
           + kvRow('权限类型', u.permission_sub_type)
           + kvRow('账号', u.account_number)
           + kvRow('授权权限', sc.authorize !== undefined ? sc.authorize : null)
           + kvRow('支付权限', sc.payment  !== undefined ? sc.payment  : null)
           + kvRow('查询权限', sc.query    !== undefined ? sc.query    : null)
           + kvRow('介质类型', u.media?.media_type)
           + kvRow('介质号',   u.media?.media_number)
           + kvRow('单笔限额', u.single_limit > 0 ? u.single_limit.toLocaleString() + ' 元' : null)
           + kvRow('日累计限额', u.daily_limit > 0 ? u.daily_limit.toLocaleString() + ' 元' : null);
        makeSection('ri-user-settings-line', `操作员 ${i + 1}：${u.user_name || '未命名'}`, userSummary, kv, i === 0);
    });
}

// --- 2.3 文档解析手风琴（升级版）---
function _docRiskLevel(doc) {
    const all = [...(doc.hard_checks || []), ...(doc.semantic_checks || [])];
    if (all.some(c => c.severity === 'CRITICAL')) return 0;
    if (all.some(c => c.severity === 'WARNING'))  return 1;
    return 2;
}

function renderDocAccordion(reports) {
    const wordList = document.getElementById('ext-word');
    const ocrList  = document.getElementById('ext-ocr');
    if (!wordList) return;
    wordList.innerHTML = ''; ocrList.innerHTML = '';
    if (!reports || reports.length === 0) return;

    [...reports].sort((a, b) => _docRiskLevel(a) - _docRiskLevel(b)).forEach((r, idx) => {
        const allChecks = [...(r.hard_checks || []), ...(r.semantic_checks || [])];
        const critical  = allChecks.filter(c => c.severity === 'CRITICAL').length;
        const warning   = allChecks.filter(c => c.severity === 'WARNING').length;
        const infoN     = allChecks.filter(c => c.severity === 'INFO').length;
        const autoOpen  = idx === 0 && (critical > 0 || warning > 0);

        const ed = r.extracted_data || {};
        // OCR 文档只展示姓名和证件号；Word/PDF 展示业务要素
        let keyFields;
        if (r.doc_type === 'ocr') {
            const persons = ed.persons || [];
            if (persons.length > 0) {
                keyFields = persons.flatMap(p => [
                    ['持证人姓名', p.name || '/'],
                    ['证件号码',   p.id_number || '/'],
                ]);
            } else {
                keyFields = [['持证人姓名', '/'], ['证件号码', '/']];
            }
        } else {
            keyFields = [
                ['场景识别', ed.scenario_type || '/'],
                ['动作识别', ed.action_type || '/'],
                ['业务动作', ed.business_activity || '/'],
                ['公司名称', ed.company?.name || '/'],
                ['操作员',   (ed.users || []).map(u => u.user_name).filter(Boolean).join(', ') || '/'],
                ['介质类型', (ed.users || []).map(u => u.media?.media_type).filter(Boolean).join(', ') || '/'],
            ];
        }

        const badges = [
            critical > 0 ? `<span class="badge-critical">${critical} 重点风险</span>` : '',
            warning  > 0 ? `<span class="badge-warning">${warning} 警告</span>` : '',
            infoN    > 0 ? `<span class="badge-info">${infoN} 提示</span>` : '',
            (critical === 0 && warning === 0 && infoN === 0) ? `<span class="badge-pass">通过</span>` : ''
        ].join('');

        const kvHtml  = keyFields.map(([k, v]) => `<div><div class="doc-kv-key">${k}</div><div class="doc-kv-val">${v}</div></div>`).join('');
        const rawText = ed.raw_text || '未获取到解析原文';
        const safeRaw = JSON.stringify(rawText);

        const item = document.createElement('div');
        item.className = `doc-accordion-item${autoOpen ? ' open' : ''}`;
        item.innerHTML = `
            <div class="doc-acc-header" onclick="this.parentElement.classList.toggle('open')">
                <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">
                    <i class="ri-file-text-line" style="color:#64748b;flex-shrink:0;"></i>
                    <span class="doc-filename">${r.doc_name}</span>
                    <span class="doc-type-tag">${r.doc_type === 'ocr' ? 'OCR' : 'Word/PDF'}</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px;">${badges}<i class="ri-arrow-down-s-line doc-arrow"></i></div>
            </div>
            <div class="doc-acc-content">
                <div class="doc-kv-grid">${kvHtml}</div>
                <button class="btn-view-raw" onclick="showRawText(event,${safeRaw})">
                    <i class="ri-file-search-line"></i> 查看全文解析
                </button>
            </div>`;
        if (r.doc_type === 'ocr') ocrList.appendChild(item);
        else wordList.appendChild(item);
    });
}

function showRawText(event, text) {
    event.stopPropagation();
    const modal   = document.getElementById('full-text-modal');
    const content = document.getElementById('modal-body-content');
    if (modal && content) { content.innerText = text; modal.style.display = 'flex'; }
}

// --- 2.4 两级折叠审计明细 ---
function renderClusteredChecks(rp) {
    const container = document.getElementById('check-list-container');
    if (!container) return;
    container.innerHTML = '';
    const docs = rp.document_reports || [];
    if (docs.length === 0) {
        container.innerHTML = '<p style="padding:20px;color:#94a3b8;text-align:center;">暂无审计明细</p>';
        return;
    }

    [...docs].sort((a, b) => _docRiskLevel(a) - _docRiskLevel(b)).forEach(doc => {
        const allChecks = [...(doc.hard_checks || []), ...(doc.semantic_checks || [])];
        const critical  = allChecks.filter(c => c.severity === 'CRITICAL').length;
        const warning   = allChecks.filter(c => c.severity === 'WARNING').length;
        const autoOpen  = critical > 0;

        // 按 category 分组
        const cats = {};
        allChecks.forEach(c => {
            const cat = c.category || '业务要素核对';
            if (!cats[cat]) cats[cat] = [];
            cats[cat].push(c);
        });

        const docBadges = [
            critical > 0 ? `<span class="badge-critical">${critical} 重点风险</span>` : '',
            warning  > 0 ? `<span class="badge-warning">${warning} 警告</span>` : '',
            (critical === 0 && warning === 0) ? `<span class="badge-pass">暂无重点风险</span>` : ''
        ].join('');

        const factsHtml = renderDocFactSnapshot(doc);

        let catHtml = '';
        for (const [cat, checks] of Object.entries(cats)) {
            const catCritical = checks.filter(c => c.severity === 'CRITICAL').length;
            const catWarning  = checks.filter(c => c.severity === 'WARNING').length;
            const passChecks  = checks.filter(c => c.severity === 'PASS');
            const riskChecks  = checks.filter(c => c.severity !== 'PASS');

            const catBadge = catCritical > 0
                ? `<span class="badge-critical">${catCritical}</span>`
                : catWarning > 0
                    ? `<span class="badge-warning">${catWarning}</span>`
                    : `<span class="badge-pass">✓</span>`;

            const n = passChecks.length;
            const passSection = n > 0 ? `
                <div style="margin-top:4px;">
                    <button class="pass-toggle" onclick="
                        var el=this.nextElementSibling;
                        el.classList.toggle('hidden');
                        this.innerText=el.classList.contains('hidden')?'显示 ${n} 项通过':'隐藏 ${n} 项通过';
                    ">显示 ${n} 项通过</button>
                    <div class="pass-items hidden">${passChecks.map(c => renderCheckItem(c)).join('')}</div>
                </div>` : '';

            catHtml += `
                <div class="cat-accordion-item${catCritical > 0 ? ' open' : ''}">
                    <div class="cat-acc-header" onclick="this.parentElement.classList.toggle('open')">
                        <span>${cat}</span>
                        <div style="display:flex;align-items:center;gap:6px;">${catBadge}<i class="ri-arrow-down-s-line" style="color:#64748b;"></i></div>
                    </div>
                    <div class="cat-acc-content">
                        ${riskChecks.map(c => renderCheckItem(c, doc.doc_name)).join('')}
                        ${passSection}
                    </div>
                </div>`;
        }

        const panel = document.createElement('div');
        panel.className = `doc-check-panel${autoOpen ? ' open' : ''}`;
        panel.innerHTML = `
            <div class="doc-check-header" onclick="this.parentElement.classList.toggle('open')">
                <div style="display:flex;align-items:center;gap:8px;">
                    <i class="ri-file-list-3-line" style="color:#64748b;"></i>
                    <span style="font-weight:600;font-size:13px;">${doc.doc_name}</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px;">${docBadges}<i class="ri-arrow-down-s-line" style="color:#94a3b8;"></i></div>
            </div>
            <div class="doc-check-content">
                ${factsHtml}
                ${catHtml}
            </div>`;
        container.appendChild(panel);
    });
}

function renderDocFactSnapshot(doc) {
    const ed = doc.extracted_data || {};
    const isOcr = doc.doc_type === 'ocr';
    let facts = [];
    if (isOcr) {
        const persons = ed.persons || [];
        facts = persons.length > 0
            ? persons.flatMap(p => [
                ['持证人', p.name || '/'],
                ['证件号', p.id_number || '/'],
                ['有效期', p.expiry_date || '/']
            ])
            : [['持证人', '/'], ['证件号', '/']];
    } else {
        const users = ed.users || [];
        facts = [
            ['场景识别', ed.scenario_type || '/'],
            ['动作识别', ed.action_type || '/'],
            ['业务动作', ed.business_activity || '/'],
            ['公司名称', ed.company?.name || '/'],
            ['操作员', compactList(users.map(u => u.user_name), '/')],
            ['账户', compactList(users.map(u => u.account_number), '/')],
            ['介质', compactList(users.map(u => u.media?.media_type), '/')]
        ];
    }

    return `
        <div class="doc-fact-snapshot">
            <div class="doc-fact-title"><i class="ri-file-search-line"></i> 文件抽取事实</div>
            <div class="doc-fact-grid">
                ${facts.map(([k, v]) => `
                    <div class="doc-fact-item">
                        <label>${escapeHtml(k)}</label>
                        <span>${escapeHtml(v)}</span>
                    </div>`).join('')}
            </div>
        </div>`;
}

function renderCheckItem(c, docName) {
    const sev = (c.severity || 'PASS').toLowerCase();
    // 来源文档标注：优先用 source_b_label，如为通用描述则用传入的文件名
    const genericLabels = ['文档解析', '目标文档', '提取-word', '提取-ocr', '文档发现'];
    const srcLabel = (c.source_b_label && !genericLabels.includes(c.source_b_label))
        ? c.source_b_label
        : (docName ? docName : '文档发现');
    const diffHtml = c.result === 'MISMATCH' ? `
        <div class="check-diff-grid">
            <div><span class="diff-label">${c.source_a_label || 'EFlow 基准'}</span><div class="diff-val">${c.source_a_value || '/'}</div></div>
            <div><span class="diff-label" title="${srcLabel}" style="max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block;">📄 ${srcLabel}</span><div class="diff-val diff-mismatch">${c.source_b_value || '/'}</div></div>
        </div>` : '';
    const metaBits = [
        c.field_group ? `字段簇: ${c.field_group}` : '',
        c.check_mode ? `检查方式: ${c.check_mode}` : '',
        c.scenario_type ? `场景: ${c.scenario_type}` : '',
        c.reason_code ? `规则码: ${c.reason_code}` : ''
    ].filter(Boolean);
    const metaHtml = metaBits.length > 0
        ? `<div class="check-meta-row">${metaBits.map(t => `<span class="check-meta-badge">${t}</span>`).join('')}</div>`
        : '';
    const manualHtml = c.manual_confirmation_required
        ? `<div class="manual-confirm-inline"><i class="ri-user-search-line"></i><span>需人工确认</span></div>`
        : '';
    const evidenceIndex = getEvidenceIndexForCheck(c, docName);
    const evidenceActionHtml = evidenceIndex >= 0
        ? `<button type="button" class="check-evidence-btn" onclick="showEvidence(${evidenceIndex})"><i class="ri-search-eye-line"></i> 查看依据</button>`
        : '';
    return `
        <div class="check-item sev-${sev}">
            <div class="check-item-header">
                <span class="check-item-name">${c.check_name}</span>
                <span class="sev-badge sev-badge-${sev}">${c.severity}</span>
            </div>
            ${metaHtml}
            ${manualHtml}
            ${c.detail ? `<div class="check-item-detail">${c.detail}</div>` : ''}
            ${diffHtml}
            ${evidenceActionHtml}
        </div>`;
}

// === 4. 配置与辅助功能 ===

function initSettings() {
    const saved = localStorage.getItem(CFG_KEY);
    if (saved) {
        try {
            const cfg = JSON.parse(saved);
            const typeNode  = document.getElementById('cfg-type');  if (typeNode)  typeNode.value  = cfg.api_type   || 'openai';
            const baseNode  = document.getElementById('cfg-base');  if (baseNode)  baseNode.value  = cfg.api_base   || '';
            const modelNode = document.getElementById('cfg-model'); if (modelNode) modelNode.value = cfg.model_name || '';
        } catch(e) {}
    }

    const setsBtn = document.getElementById('btn-settings');
    if (setsBtn) setsBtn.onclick = () => document.getElementById('settings-modal').classList.add('show');

    const closeSets  = document.getElementById('btn-close-settings');
    if (closeSets)  closeSets.onclick  = () => document.getElementById('settings-modal').classList.remove('show');
    const closeSets2 = document.getElementById('btn-close-settings-2');
    if (closeSets2) closeSets2.onclick = () => document.getElementById('settings-modal').classList.remove('show');

    const saveSets = document.getElementById('btn-save-settings');
    if (saveSets) {
        saveSets.onclick = async () => {
            const cfg = {
                api_type:   document.getElementById('cfg-type').value,
                api_base:   document.getElementById('cfg-base').value,
                api_key:    document.getElementById('cfg-key').value,
                model_name: document.getElementById('cfg-model').value
            };
            const resp = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cfg)
            });
            if (resp.ok) {
                localStorage.setItem(CFG_KEY, JSON.stringify(cfg));
                alert('配置已持久化到后端');
                document.getElementById('settings-modal').classList.remove('show');
            }
        };
    }
}

async function loadTestCases() {
    try {
        const resp = await fetch(`${API_BASE}/testcases`);
        const data = await resp.json();
        const cases  = Array.isArray(data) ? data : (data.cases || []);
        const select = document.getElementById('case-select');
        if (!select) return;
        cases.forEach(c => {
            const opt = document.createElement('option');
            opt.value    = c.case_id || c.id || '';
            opt.innerText = `${c.case_id || c.id}: ${c.description || '标准测试用例'}`;
            select.appendChild(opt);
        });
        console.log(`[TestCases] Loaded ${cases.length} cases`);
    } catch (e) {
        console.error('[TestCases] Failed to load:', e);
    }
}
