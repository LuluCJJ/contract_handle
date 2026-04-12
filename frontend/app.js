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
        if(e.target.files.length > 0) {
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

// Dropdown change listener for "smooth" switching
document.getElementById('cfg-type').addEventListener('change', (e) => {
    const newType = e.target.value;
    // Before switching, optionally we could temp save current inputs, 
    // but the main requirement is to record what was PREVIOUSLY saved.
    fillSettings(newType);
});

function fillSettings(type) {
    const cfg = llmConfigs[type] || { api_base: '', model_name: '', api_key_masked: '' };
    document.getElementById('cfg-base').value = cfg.api_base || '';
    document.getElementById('cfg-model').value = cfg.model_name || '';
    // Key is always masked from backend, clear it to invite fresh entry or keep sk-placeholder
    document.getElementById('cfg-key').value = ""; 
    document.getElementById('cfg-key').placeholder = cfg.api_key_masked || "sk-...";
}

btnClose.addEventListener('click', () => modal.classList.remove('show'));

// Save Settings Logic
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
        
        // Sync to local state
        llmConfigs.active_type = data.api_type;
        llmConfigs.openai = data.openai;
        llmConfigs.requests = data.requests;
        
        if (!silent) {
            toast.textContent = '配置已保存';
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
            fillSettings(activeType); // Re-sync UI with masked keys
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
    // 1. Ensure current inputs are saved first (blocking)
    btnTest.textContent = "正在保存并测试...";
    btnTest.disabled = true;

    try {
        const saved = await saveSettings(true);
        if (!saved) throw new Error("保存配置失败，无法测试");

        // 2. Now test
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
    const bankF = document.getElementById('file-bank').files[0];
    const idF = document.getElementById('file-id').files[0];
    
    if(!eflowF || !bankF || !idF) return alert('必须上传所有文件');
    
    showLoading();
    const fd = new FormData();
    fd.append('eflow_json', eflowF);
    fd.append('bank_doc', bankF);
    fd.append('id_document', idF);
    
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

// Render
function renderResult(data) {
    if(data.status !== 'completed' || !data.report) {
        return alert("后端返回状态不是 completed。可能是未配置正确的大模型。");
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
    desc.textContent = rp.summary;
    
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
                li.textContent = item;
                insightsList.appendChild(li);
            });
        } else {
            insightsList.innerHTML = '<li>无特别风险提示</li>';
        }
    } else {
        llmCard.style.display = 'none';
    }

    // Extracted Data Grid
    renderColumn('ext-eflow', rp.eflow_data);
    renderColumn('ext-word', rp.word_data);
    renderColumn('ext-ocr', rp.ocr_data);
    
    // Checks
    const list = document.getElementById('check-list');
    list.innerHTML = '';
    rp.checks.forEach(chk => {
        const li = document.createElement('li');
        li.className = `check-item severity-${chk.severity}`;
        
        let diffHtml = '';
        if(chk.source_a_label || chk.source_b_label || chk.source_c_label) {
            diffHtml = '<div class="check-diffs">';
            if(chk.source_a_value) diffHtml += `<div class="diff-item"><span class="diff-label">${chk.source_a_label}</span><span class="diff-value">${chk.source_a_value}</span></div>`;
            if(chk.source_b_value) diffHtml += `<div class="diff-item"><span class="diff-label">${chk.source_b_label}</span><span class="diff-value">${chk.source_b_value}</span></div>`;
            if(chk.source_c_value) diffHtml += `<div class="diff-item"><span class="diff-label">${chk.source_c_label}</span><span class="diff-value">${chk.source_c_value}</span></div>`;
            diffHtml += '</div>';
        }

        li.innerHTML = `
            <div class="check-header">
                <span class="check-title">${chk.check_name}</span>
                <span class="check-badge">${chk.severity}</span>
            </div>
            <div class="check-desc">${chk.detail || (chk.result ==='MATCH'?'一致':'异常')}</div>
            ${diffHtml}
        `;
        list.appendChild(li);
    });
}

function renderColumn(id, extData) {
    if(!extData) return;
    const col = document.getElementById(id);
    let html = '';
    
    const addkv = (label, val) => {
        if(val) html += `<div class="ext-group"><div class="ext-label">${label}</div><div class="ext-value">${val}</div></div>`;
    };
    
    if(extData.company.name) addkv('单位名称', extData.company.name);
    if(extData.company.cert_number) addkv('单位统一码', extData.company.cert_number);
    if(extData.operator.name) addkv('操作员姓名', extData.operator.name);
    if(extData.operator.id_number) addkv('操作员证件', `${extData.operator.id_type || ''} ${extData.operator.id_number}`);
    if(extData.account.account_number) addkv('业务账号', extData.account.account_number);
    if(extData.activity) addkv('办理业务', extData.activity);
    
    col.innerHTML = html || '<div class="ext-group"><div class="ext-label">无提取数据</div></div>';
}
