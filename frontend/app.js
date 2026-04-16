const API_BASE = '/api/audit';
const CFG_KEY = 'audit_llm_config_v2';

document.addEventListener('DOMContentLoaded', () => {
    initSettings();
    initUploadHandlers();
    loadTestCases();
});

// === 1. 基础 UI 交互 ===

function showLoading(show) {
    document.getElementById('loading-overlay').classList.toggle('show', show);
}

function initUploadHandlers() {
    ['eflow', 'bank', 'id'].forEach(type => {
        const zone = document.getElementById(`zone-${type}`);
        const input = document.getElementById(`file-${type}`);
        const nameNode = document.getElementById(`name-${type}`);
        
        if(!zone || !input) return;

        zone.onclick = () => input.click();
        input.onchange = () => {
            if (input.files.length > 0) {
                nameNode.innerText = input.files.length === 1 ? input.files[0].name : `已选择 ${input.files.length} 个文件`;
                zone.style.borderColor = 'var(--audit-blue)';
                zone.style.background = '#f0f7ff';
            }
        };
    });

    document.getElementById('upload-form').onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        runAudit('/run', fd);
    };

    document.getElementById('btn-run-case').onclick = () => {
        const caseId = document.getElementById('case-select').value;
        if (!caseId) return alert('请先选择一个用例');
        const fd = new FormData();
        fd.append('case_id', caseId);
        runAudit('/run-from-testcase', fd);
    };

    const closeBtn = document.getElementById('close-modal');
    if(closeBtn) {
        closeBtn.onclick = () => {
            document.getElementById('full-text-modal').style.display = 'none';
        }
    }
}

// === 2. 核心审计执行与 V15.0 渲染分流 ===

async function runAudit(endpoint, formData) {
    showLoading(true);
    try {
        const resp = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', body: formData });
        const result = await resp.json();
        if (result.status === 'error') throw new Error(result.error);
        renderV15Report(result);
    } catch (err) {
        alert('审计任务失败: ' + err.message);
    } finally {
        showLoading(false);
    }
}

function renderV15Report(rp) {
    const panel = document.getElementById('result-panel');
    if(panel) panel.style.display = 'block';
    
    // 1. 画像层：总体结论
    const status = rp.overall_status || 'ZERO_RISK';
    const card = document.getElementById('summary-card');
    if(card) {
        card.className = `card result-summary risk-${status}`;
        const statusMap = {
            'HIGH_RISK': { title: '高风险关注：预审建议核核', icon: 'ri-alarm-warning-fill' },
            'MED_RISK': { title: '建议人工核议：存在逻辑偏离', icon: 'ri-error-warning-line' },
            'LOW_RISK': { title: '轻微偏离提醒：要素基本一致', icon: 'ri-information-line' },
            'ZERO_RISK': { title: '全量预审通过：要素高度一致', icon: 'ri-checkbox-circle-line' }
        };
        const info = statusMap[status] || statusMap['ZERO_RISK'];
        document.getElementById('status-icon').innerHTML = `<i class='${info.icon}'></i>`;
        document.getElementById('status-title').innerText = info.title;
        document.getElementById('status-desc').innerText = `任务ID: ${rp.task_id} | 智感分析已完成`;
    }

    // 2. 综述层：全景画像
    const summaryCard = document.getElementById('llm-summary-card');
    if (rp.llm_summary && summaryCard) {
        summaryCard.style.display = 'block';
        const aggNode = document.getElementById('aggregator-text');
        if(aggNode) aggNode.innerText = rp.llm_summary.aggregator_summary || '正在整合多路审计结论...';
        
        const riskList = document.getElementById('llm-risk-insights');
        if(riskList) {
            riskList.innerHTML = (rp.llm_summary.risk_insights || []).map(r => `<li>${r}</li>`).join('');
        }
    }

    // 3. 穿透层：EFlow 折叠渲染
    renderEFlowAccordion(rp.eflow_data);

    // 4. 文档展示渲染
    renderDocCards(rp.document_reports);

    // 5. 明细层：三层聚类渲染
    renderClusteredChecks(rp);

    window.scrollTo({ top: 300, behavior: 'smooth' });
}

function renderEFlowAccordion(ef) {
    const container = document.getElementById('ext-eflow');
    if(!container) return;
    container.innerHTML = '';
    
    const sections = [
        { title: '业务场景', data: { '需求大类': ef.business_type, '具体场景': ef.business_scenario } },
        { title: '网银平台', data: { '名称': ef.platform.platform_name, '银行': ef.platform.bank_name, 'URL': ef.platform.login_url } },
        { title: '基础信息', data: { '申请人': ef.applicant.name, '工号': ef.applicant.id_number, '部门': ef.applicant.department } },
        { title: '用户信息', data: { '操作员名单': ef.users.map(u => u.user_name).join(', ') } }
    ];

    sections.forEach(s => {
        const item = document.createElement('div');
        item.className = 'accordion-item';
        let kvHtml = '';
        for(let k in s.data) {
            kvHtml += `<div style='display:flex; justify-content:space-between; margin-bottom:4px;'><span style='color:#64748b'>${k}</span><span style='font-weight:500'>${s.data[k] || '/'}</span></div>`;
        }
        item.innerHTML = `
            <div class='acc-header' onclick='this.parentElement.classList.toggle("open")'>
                <span>${s.title}</span><i class='ri-arrow-down-s-line'></i>
            </div>
            <div class='acc-content'>${kvHtml}</div>
        `;
        container.appendChild(item);
    });
}

function renderDocCards(reports) {
    const wordList = document.getElementById('ext-word');
    const ocrList = document.getElementById('ext-ocr');
    if(!wordList) return;
    wordList.innerHTML = ''; ocrList.innerHTML = '';

    reports.forEach(r => {
        const card = document.createElement('div');
        card.className = 'ext-card';
        const checkCount = (r.hard_checks || []).length + (r.semantic_checks || []).length;
        card.innerHTML = `
            <div style='font-weight:600; font-size:13px;'>${r.doc_name}</div>
            <div class='ext-card-tag'>${r.doc_type}</div>
            <div style='font-size:11px; color:#64748b; margin-top:4px;'>已关联 ${checkCount} 项核验</div>
        `;
        card.onclick = () => {
            const modal = document.getElementById('full-text-modal');
            const content = document.getElementById('modal-body-content');
            if(modal && content) {
                content.innerText = r.extracted_data.raw_text || '未获取到解析原文';
                modal.style.display = 'flex';
            }
        };
        if(r.doc_type === 'ocr') ocrList.appendChild(card);
        else wordList.appendChild(card);
    });
}

function renderClusteredChecks(rp) {
    const container = document.getElementById('check-list-container');
    if(!container) return;
    container.innerHTML = '';
    
    // 聚合所有项
    let allChecks = [];
    (rp.document_reports || []).forEach(r => {
        if(r.hard_checks) allChecks = allChecks.concat(r.hard_checks);
        if(r.semantic_checks) allChecks = allChecks.concat(r.semantic_checks);
    });
    if(rp.cross_validation_checks) {
        allChecks = allChecks.concat(rp.cross_validation_checks);
    }

    // 分类 Map
    const clusters = {};
    allChecks.forEach(c => {
        const cat = c.category || '业务要素核对';
        if(!clusters[cat]) clusters[cat] = [];
        clusters[cat].push(c);
    });

    for(let cat in clusters) {
        const group = document.createElement('div');
        group.className = 'check-cluster';
        group.innerHTML = `<div class='cluster-title'><i class='ri-focus-3-line'></i> ${cat} (${clusters[cat].length})</div>`;
        
        clusters[cat].forEach(c => {
            const item = document.createElement('div');
            item.className = `check-item severity-${c.severity}`;
            item.style.padding = '12px';
            item.style.marginBottom = '10px';
            item.style.borderBottom = '1px solid #f0f0f0';
            
            item.innerHTML = `
                <div class='check-header' style='display:flex; justify-content:space-between;'>
                    <span class='check-title' style='font-weight:600; font-size:14px;'>${c.check_name}</span>
                    <span class='check-badge'>${c.severity}</span>
                </div>
                <div style='font-size:12px; color:#475569; margin:6px 0;'>${c.detail || ''}</div>
                ${c.result === 'MISMATCH' ? `
                    <div class='check-diffs' style='display:grid; grid-template-columns:1fr 1fr; background:#f8fafc; padding:8px; border-radius:4px;'>
                        <div><span style='font-size:10px; color:#94a3b8;'>EFlow 基准</span><div class='diff-value' style='font-size:12px; font-weight:600;'>${c.source_a_value || '/'}</div></div>
                        <div><span style='font-size:10px; color:#94a3b8;'>文档发现</span><div class='diff-value' style='font-size:12px; font-weight:600; color:var(--audit-blue);'>${c.source_b_value || '/'}</div></div>
                    </div>
                ` : ''}
            `;
            group.appendChild(item);
        });
        container.appendChild(group);
    }
}

// === 3. 配置与辅助功能 ===

function initSettings() {
    const saved = localStorage.getItem(CFG_KEY);
    if (saved) {
        const cfg = JSON.parse(saved);
        const typeNode = document.getElementById('cfg-type');
        if(typeNode) typeNode.value = cfg.api_type || 'openai';
        const baseNode = document.getElementById('cfg-base');
        if(baseNode) baseNode.value = cfg.api_base || '';
        const modelNode = document.getElementById('cfg-model');
        if(modelNode) modelNode.value = cfg.model_name || '';
    }
    
    const setsBtn = document.getElementById('btn-settings');
    if(setsBtn) {
        setsBtn.onclick = () => document.getElementById('settings-modal').classList.add('show');
    }
    const closeSets = document.getElementById('btn-close-settings');
    if(closeSets) {
        closeSets.onclick = () => document.getElementById('settings-modal').classList.remove('show');
    }
    
    const saveSets = document.getElementById('btn-save-settings');
    if(saveSets) {
        saveSets.onclick = async () => {
            const cfg = {
                api_type: document.getElementById('cfg-type').value,
                api_base: document.getElementById('cfg-base').value,
                api_key: document.getElementById('cfg-key').value,
                model_name: document.getElementById('cfg-model').value
            };
            const resp = await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(cfg)
            });
            if(resp.ok) {
                localStorage.setItem(CFG_KEY, JSON.stringify(cfg));
                alert('配置已持久化到后端');
                document.getElementById('settings-modal').classList.remove('show');
            }
        };
    }
}

async function loadTestCases() {
    try {
        const resp = await fetch('/api/test-cases');
        const cases = await resp.json();
        const select = document.getElementById('case-select');
        if(!select) return;
        cases.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.innerText = `${c.id}: ${c.description || '无描述'}`;
            select.appendChild(opt);
        });
    } catch (e) {}
}
