// Elements
const modal = document.getElementById('settings-modal');
const btnSettings = document.getElementById('btn-settings');
const btnClose = document.getElementById('btn-close-settings');
const btnSave = document.getElementById('btn-save-settings');
const btnTest = document.getElementById('btn-test-llm');
const toast = document.getElementById('settings-toast');

// Upload Elements
const form = document.getElementById('upload-form');
const fields = ['eflow', 'bank', 'id'];
fields.forEach(f => {
    const input = document.getElementById(`file-${f}`);
    const zone = document.getElementById(`zone-${f}`);
    const name = document.getElementById(`name-${f}`);
    
    zone.addEventListener('click', () => input.click());
    input.addEventListener('change', (e) => {
        if(e.target.files.length > 1) {
            name.textContent = `已选择 ${e.target.files.length} 个文件`;
            zone.classList.add('has-file');
        } else if(e.target.files.length === 1) {
            name.textContent = e.target.files[0].name;
            zone.classList.add('has-file');
        } else {
            name.textContent = '未选择文件';
            zone.classList.remove('has-file');
        }
    });
});

// LLM Configuration State
let llmConfigs = {
    openai: { api_base: '', model_name: '' },
    requests: { api_base: '', model_name: '' },
    active_type: 'openai'
};

// Setup Modal Toggle
btnSettings.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/settings/llm');
        const data = await res.json();
        
        // Sync to local state
        llmConfigs.active_type = data.api_type;
        llmConfigs.openai = data.openai;
        llmConfigs.requests = data.requests;

        // Render Active Type
        document.getElementById('cfg-type').value = data.api_type;
        fillSettings(data.api_type);

    } catch(e) { console.error("Failed to load settings", e); }
    modal.classList.add('show');
});

// Dropdown change listener
document.getElementById('cfg-type').addEventListener('change', (e) => {
    const newType = e.target.value;
    fillSettings(newType);
});

function fillSettings(type) {
    const cfg = llmConfigs[type] || { api_base: '', model_name: '', api_key_masked: '' };
    document.getElementById('cfg-base').value = cfg.api_base || '';
    document.getElementById('cfg-model').value = cfg.model_name || '';
    document.getElementById('cfg-key').value = ""; 
    document.getElementById('cfg-key').placeholder = cfg.api_key_masked || "sk-...";
}

btnClose.addEventListener('click', () => modal.classList.remove('show'));

async function saveSettings(silent = false) {
    const activeType = document.getElementById('cfg-type').value;
    const keyInput = document.getElementById('cfg-key').value;
    
    const body = {
        api_type: activeType,
        api_base: document.getElementById('cfg-base').value,
        api_key: keyInput || "sk-placeholder",
        model_name: document.getElementById('cfg-model').value
    };
    
    try {
        const res = await fetch('/api/settings/llm', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        llmConfigs.active_type = data.api_type;
        llmConfigs.openai = data.openai;
        llmConfigs.requests = data.requests;
        
        if (!silent) {
            toast.textContent = '配置已保存';
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
            fillSettings(activeType);
        }
        return true;
    } catch(e) {
        console.error("Save failed:", e);
        if (!silent) alert("保存失败: " + e.message);
        return false;
    }
}

btnSave.addEventListener('click', () => saveSettings());

btnTest.addEventListener('click', async () => {
    btnTest.textContent = "正在保存并测试...";
    btnTest.disabled = true;

    try {
        const saved = await saveSettings(true);
        if (!saved) throw new Error("保存配置失败，无法测试");

        const res = await fetch('/api/settings/llm/test', { method: 'POST' });
        const data = await res.json();
        
        if(data.status === 'ok') {
            const model = data.model || '未定义模型';
            const reply = data.reply || '(无响应内容)';
            const warning = data.warning ? `\n警告: ${data.warning}` : '';
            alert(`✅ 连通成功！\n模型: ${model}\n响应: ${reply}${warning}`);
        } else {
            alert(`❌ 连通失败！\n错误详情: ${data.error || '未知错误'}`);
        }
    } catch(e) {
        alert("请求异常: " + e.message);
    } finally {
        btnTest.textContent = "连通性测试";
        btnTest.disabled = false;
    }
});

// Testcases
async function loadTestcases() {
    try {
        const res = await fetch('/api/audit/testcases');
        const data = await res.json();
        const sel = document.getElementById('case-select');
        sel.innerHTML = '<option value="">载入标准测试集...</option>';
        data.cases.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.case_id;
            opt.textContent = `${c.case_id} — ${c.description || ''}`;
            sel.appendChild(opt);
        });
    } catch(e) { console.error(e); }
}
loadTestcases();

document.getElementById('btn-run-case').addEventListener('click', async () => {
    const caseId = document.getElementById('case-select').value;
    if(!caseId) return alert('请先选择一个用例');
    
    showLoading();
    try {
        const fd = new FormData();
        fd.append('case_id', caseId);
        const res = await fetch('/api/audit/run-from-testcase', { method: 'POST', body: fd });
        const data = await res.json();
        renderResult(data);
    } catch(e) {
        alert("执行失败: " + e.message);
    } finally {
        hideLoading();
    }
});

// Submit Form
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const eflowF = document.getElementById('file-eflow').files[0];
    const bankFiles = document.getElementById('file-bank').files;
    const idFiles = document.getElementById('file-id').files;
    
    if(!eflowF || bankFiles.length === 0 || idFiles.length === 0) return alert('必须上传所有文件');
    
    showLoading();
    const fd = new FormData();
    fd.append('eflow_json', eflowF);
    
    // 多文档支持: bank_doc
    for(let i=0; i<bankFiles.length; i++) {
        fd.append('bank_doc', bankFiles[i]);
    }
    
    // 多文档支持: id_documents
    for(let i=0; i<idFiles.length; i++) {
        fd.append('id_documents', idFiles[i]);
    }
    
    try {
        const res = await fetch('/api/audit/run', { method: 'POST', body: fd });
        const data = await res.json();
        renderResult(data);
    } catch(e) {
        alert("执行失败: " + e.message);
    } finally {
        hideLoading();
    }
});

function showLoading() { document.getElementById('loading-overlay').classList.add('show'); }
function hideLoading() { document.getElementById('loading-overlay').classList.remove('show'); }

// V3 Render Logic
function renderResult(data) {
    // 兼容判定：V3 必须有 document_reports
    if(!data.report || !data.report.document_reports) {
        console.error("V3 Protocol Mismatch", data);
        return alert("后端返回数据结构与 V3 协议不匹配，请检查服务版本。");
    }
    
    const rp = data.report;
    const panel = document.getElementById('result-panel');
    panel.style.display = 'block';
    
    // Status Card
    const sc = document.getElementById('summary-card');
    sc.className = 'card glass-card result-summary';
    const icon = document.getElementById('status-icon');
    const title = document.getElementById('status-title');
    const desc = document.getElementById('status-desc');
    
    if(rp.overall_status === 'PASSED') {
        sc.classList.add('pass');
        icon.innerHTML = '<i class="ri-shield-check-line"></i>';
        title.textContent = '审核通过';
    } else if(rp.overall_status === 'RISK_FOUND') {
        sc.classList.add('risk');
        icon.innerHTML = '<i class="ri-error-warning-line"></i>';
        title.textContent = '检测到一般风险';
    } else {
        sc.classList.add('failed');
        icon.innerHTML = '<i class="ri-close-circle-line"></i>';
        title.textContent = '预审阻断 (存在严重冲突)';
    }
    desc.textContent = rp.summary || '审计管线执行结束。';
    
    // LLM Overall Summary
    const llmCard = document.getElementById('llm-summary-card');
    if(rp.llm_summary && Object.keys(rp.llm_summary).length > 0) {
        llmCard.style.display = 'block';
        document.getElementById('llm-overall-summary').textContent = rp.llm_summary.summary || '无整体结论';
        
        const insightsList = document.getElementById('llm-risk-insights');
        insightsList.innerHTML = '';
        const insights = rp.llm_summary.risk_insights || [];
        if(insights.length > 0) {
            insights.forEach(item => {
                const li = document.createElement('li');
                li.style.marginBottom = '6px';
                li.innerHTML = `<i class="ri-alert-line" style="color:#f59e0b"></i> ${item}`;
                insightsList.appendChild(li);
            });
        }
    } else {
        llmCard.style.display = 'none';
    }

    // Extracted Data Grid (V3 Adaption)
    // 基准列
    renderV3Column('ext-eflow', 'EFlow 系统基准', rp.eflow_data);
    
    // 提取结果分片展示
    if(rp.document_reports && rp.document_reports.length > 0) {
        // 1. 合同附件列 (展示所有 Word/PDF)
        const bankCol = document.getElementById('ext-word');
        bankCol.innerHTML = '';
        const allBankDocs = rp.document_reports.filter(d => d.doc_type === 'word' || d.doc_type === 'pdf');
        
        if(allBankDocs.length > 0) {
            allBankDocs.forEach((doc, idx) => {
                const subDiv = document.createElement('div');
                subDiv.id = `ext-word-sub-${idx}`;
                subDiv.className = 'ext-multi-item';
                bankCol.appendChild(subDiv);
                renderV3Column(subDiv.id, doc.doc_name, doc.extracted_data);
            });
        } else {
             bankCol.innerHTML = '<div class="ext-label">无合同附件</div>';
        }

        // 2. 证件列 (展示所有 OCR)
        const ocrCol = document.getElementById('ext-ocr');
        ocrCol.innerHTML = ''; 
        const allOcrDocs = rp.document_reports.filter(d => d.doc_type === 'ocr');
        
        if(allOcrDocs.length > 0) {
            allOcrDocs.forEach((doc, idx) => {
                const subDiv = document.createElement('div');
                subDiv.id = `ext-ocr-sub-${idx}`;
                subDiv.className = 'ext-multi-item';
                ocrCol.appendChild(subDiv);
                renderV3Column(subDiv.id, doc.doc_name, doc.extracted_data);
            });
        } else {
            ocrCol.innerHTML = '<div class="ext-label">无证件附件</div>';
        }
    }
    
    // Checks (合并展示所有文档的检查项)
    const list = document.getElementById('check-list');
    list.innerHTML = '';
    
    // 渲染普通检查项
    rp.document_reports.forEach(dr => {
        const allChecks = [...dr.hard_checks, ...dr.semantic_checks];
        allChecks.forEach(chk => {
            if(chk.severity === 'PASS') return; // 隐藏通过项
            addCheckItem(list, dr.doc_name, chk);
        });
    });
    
    // 渲染交叉检查项
    if(rp.cross_validation_checks) {
        rp.cross_validation_checks.forEach(chk => {
            addCheckItem(list, '交叉验证', chk);
        });
    }
}

function addCheckItem(container, scopeName, chk) {
    const li = document.createElement('li');
    li.className = `check-item severity-${chk.severity}`;
    
    const diffHtml = `
        <div class="check-diffs">
            <div class="diff-item"><span class="diff-label">EFlow</span><span class="diff-value">${chk.source_a_value || '-'}</span></div>
            <div class="diff-item"><span class="diff-label">${scopeName}</span><span class="diff-value">${chk.source_b_value || '-'}</span></div>
        </div>
    `;

    li.innerHTML = `
        <div class="check-header">
            <span class="check-title">${chk.check_name}</span>
            <span class="check-badge">${chk.severity}</span>
        </div>
        <div class="check-desc">${chk.detail}</div>
        ${diffHtml}
    `;
    container.appendChild(li);
}

function renderV3Column(id, title, data) {
    const col = document.getElementById(id);
    if(!col || !data) return;
    
    let html = `<div style="font-size:12px; opacity:0.6; margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.1)">${title}</div>`;
    
    const addkv = (label, val) => {
        if(val) html += `<div class="ext-group"><div class="ext-label">${label}</div><div class="ext-value">${val}</div></div>`;
    };

    // 公司信息
    if(data.company && data.company.name) addkv('单位', data.company.name);
    
    // 人员/账号/权限 (如果是 EFlowData)
    if(data.users && Array.isArray(data.users)) {
        data.users.forEach(u => {
            if(!u) return;
            const scope = u.permission_scope || {};
            const scopeStr = [
               scope.authorize ? '审' : '',
               scope.payment ? '支' : '',
               scope.query ? '查' : '',
               scope.upload ? '传' : ''
            ].filter(x => x).join('|');
            
            const acc = u.account_number || '-';
            const limitStr = (u.single_limit || u.daily_limit) ? `<br/>单笔:${u.single_limit || 0} / 日累:${u.daily_limit || 0}` : '';
            addkv(u.user_name || '操作员', `账号:${acc}<br/>权限:[${scopeStr || '无'}]${limitStr}`);
        });
    }
    
    // 补充：展示公司证件号与情景
    if(data.company && data.company.cert_number) addkv('主证件号', data.company.cert_number);
    if(data.business_scenario) addkv('业务情景', data.business_scenario);
    
    // 如果是 OCR/人员模型
    if(data.persons && Array.isArray(data.persons)) {
        data.persons.forEach(p => {
            addkv('持证人', `${p.name}<br/>${p.id_number || ''}`);
        });
    }

    if(data.business_activity) addkv('意图', data.business_activity);
    
    col.innerHTML = html;
}
