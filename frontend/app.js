/**
 * Nyaya AI — Frontend Application Logic
 * Handles tab switching, mode selection, query submission, contract upload.
 */

// ── State ──────────────────────────────────────────────────
let currentMode = 'citizen';
let isLoading = false;
let riskGaugeChart = null;
let categoryBarChart = null;
let clauseDonutChart = null;
let standardDonutChart = null;

// ── Helpers ────────────────────────────────────────────────
function getMode() { return currentMode; }

function setMode(mode) {
    if (isLoading) return;
    currentMode = mode;
    document.getElementById('btn-citizen').classList.toggle('active', mode === 'citizen');
    document.getElementById('btn-counsel').classList.toggle('active', mode === 'counsel');
    const badge = document.getElementById('mode-label');
    if (mode === 'citizen') {
        badge.textContent = 'Plain English Mode';
        badge.style.color = 'var(--blue)';
        badge.style.background = 'var(--blue-dim)';
        badge.style.borderColor = 'rgba(59,130,246,0.25)';
    } else {
        badge.textContent = 'Legal Counsel Mode';
        badge.style.color = 'var(--gold)';
        badge.style.background = 'var(--gold-dim)';
        badge.style.borderColor = 'rgba(212,168,67,0.25)';
    }
}

function setLoadingLock(locked) {
    isLoading = locked;
    document.getElementById('mode-pill').classList.toggle('disabled', locked);
}

function switchTab(tab) {
    document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('section-' + tab).classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
}

// ── Animated agent steps ────────────────────────────────────
const steps = ['step-rag', 'step-router', 'step-expert', 'step-synth'];
let stepInterval = null;

function startAgentAnimation() {
    let i = 0;
    steps.forEach(id => {
        const dot = document.querySelector('#' + id + ' .step-dot');
        if (dot) { dot.className = 'step-dot'; }
    });
    document.querySelector('#' + steps[0] + ' .step-dot').classList.add('active-step');
    stepInterval = setInterval(() => {
        const prev = document.querySelector('#' + steps[i] + ' .step-dot');
        if (prev) prev.classList.replace('active-step', 'done-step');
        i++;
        if (i < steps.length) {
            const curr = document.querySelector('#' + steps[i] + ' .step-dot');
            if (curr) curr.classList.add('active-step');
        } else {
            clearInterval(stepInterval);
        }
    }, 8000);
}

function stopAgentAnimation() {
    clearInterval(stepInterval);
    steps.forEach(id => {
        const dot = document.querySelector('#' + id + ' .step-dot');
        if (dot) dot.className = 'step-dot done-step';
    });
}

// ── Document Attachment Helpers ─────────────────────────────
let _queryAttachedFile = null;

function handleQueryDocAttach(event) {
    const file = event.target.files[0];
    if (!file) return;
    _queryAttachedFile = file;
    document.getElementById('query-doc-name').textContent = file.name;
    document.getElementById('query-doc-indicator').classList.remove('hidden');
}

function removeQueryDoc() {
    _queryAttachedFile = null;
    document.getElementById('query-doc-input').value = '';
    document.getElementById('query-doc-indicator').classList.add('hidden');
}

// ── TAB 1: Chat Session Management ────────────────────────────
let _currentSessionId = null;
let _chatHistory = [];

function generateId() { return Math.random().toString(36).substr(2, 9); }

function loadChatSessions() {
    const sessions = JSON.parse(localStorage.getItem('nyaya_sessions') || '[]');
    const listEl = document.getElementById('chat-history-list');
    listEl.innerHTML = '';
    
    sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = `chat-session-item ${session.id === _currentSessionId ? 'active' : ''}`;
        item.textContent = session.title;
        item.onclick = () => loadChat(session.id);
        listEl.appendChild(item);
    });
}

function saveSession(title) {
    let sessions = JSON.parse(localStorage.getItem('nyaya_sessions') || '[]');
    if (!sessions.find(s => s.id === _currentSessionId)) {
        sessions.unshift({ id: _currentSessionId, title: title || 'New Legal Case' });
        localStorage.setItem('nyaya_sessions', JSON.stringify(sessions));
        loadChatSessions();
    }
}

function startNewChat() {
    _currentSessionId = generateId();
    _chatHistory = [];
    document.getElementById('chat-welcome').classList.remove('hidden');
    document.getElementById('legal-query').value = '';
    document.querySelectorAll('.message').forEach(e => e.remove());
    removeQueryDoc();
    loadChatSessions();
}

function loadChat(sessionId) {
    _currentSessionId = sessionId;
    _chatHistory = JSON.parse(localStorage.getItem(`nyaya_chat_${sessionId}`) || '[]');
    
    document.getElementById('chat-welcome').classList.add('hidden');
    document.querySelectorAll('.message').forEach(e => e.remove());
    
    _chatHistory.forEach(msg => appendMessage(msg.role, msg.content, msg.metadata));
    loadChatSessions();
}

function appendMessage(role, content, metadata = null) {
    const chatMessages = document.getElementById('chat-messages');
    document.getElementById('chat-welcome').classList.add('hidden');
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    let avatarHTML = role === 'user' 
        ? `<div class="msg-avatar"><i class="fa-solid fa-user"></i></div>`
        : `<div class="msg-avatar"><img src="/static/hero_scales.png" /></div>`;
        
    let bubbleContent = role === 'ai' ? marked.parse(content) : content.replace(/\n/g, '<br>');
    
    // Inject stats if AI message has metadata
    if (role === 'ai' && metadata) {
        let tagsHTML = (metadata.routed_domains || []).map(d => `<span class="tag">${d.toUpperCase()}</span>`).join('');
        if (metadata.document_attached) {
            tagsHTML += `<span class="tag tag-doc"><i class="fa-solid fa-paperclip"></i> Document Analyzed</span>`;
        }
        
        let statsHTML = `
            <div class="result-tags" style="margin-bottom:12px">${tagsHTML}</div>
            <div class="stats-row" style="margin-bottom:16px; font-size:0.8rem">
                <div class="stat-chip interactive-chip" onclick="showCasesModal('verified', '${metadata.id}')"><i class="fa-solid fa-circle-check text-green"></i> <span>${metadata.verified_cases}</span> Verified</div>
                <div class="stat-chip interactive-chip" onclick="showCasesModal('cautioned', '${metadata.id}')"><i class="fa-solid fa-triangle-exclamation text-amber"></i> <span>${metadata.cautioned_cases}</span> Cautioned</div>
                <div class="stat-chip interactive-chip" onclick="showCasesModal('rejected', '${metadata.id}')"><i class="fa-solid fa-circle-xmark text-red"></i> <span>${metadata.rejected_cases}</span> Rejected</div>
            </div>
        `;
        bubbleContent = statsHTML + bubbleContent;
        
        // Save case data to window so modal works for history
        if (!window._chatCases) window._chatCases = {};
        window._chatCases[metadata.id] = metadata.cases_data;
    }

    msgDiv.innerHTML = `${avatarHTML}<div class="msg-bubble">${bubbleContent}</div>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── TAB 1: Legal Engine ─────────────────────────────────────
async function submitQuery() {
    const queryEl = document.getElementById('legal-query');
    const query = queryEl.value.trim();
    if (!query) { alert('Please describe your legal situation.'); return; }
    
    if (!_currentSessionId) startNewChat();

    // 1. Show User Message
    appendMessage('user', query);
    _chatHistory.push({ role: 'user', content: query });
    localStorage.setItem(`nyaya_chat_${_currentSessionId}`, JSON.stringify(_chatHistory));
    
    if (_chatHistory.length === 1) saveSession(query.substring(0, 30) + '...');
    
    queryEl.value = '';
    queryEl.style.height = 'auto'; // reset resize

    setLoadingLock(true);
    document.getElementById('query-loading').classList.remove('hidden');

    try {
        let res;
        const historyPayload = JSON.stringify(_chatHistory.slice(0, -1)); // all but the current query

        if (_queryAttachedFile) {
            const formData = new FormData();
            formData.append('query', query);
            formData.append('mode', getMode());
            formData.append('chat_history', historyPayload);
            formData.append('file', _queryAttachedFile);

            res = await fetch('/api/analyze-with-doc', { method: 'POST', body: formData });
        } else {
            res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, mode: getMode(), chat_history: JSON.parse(historyPayload) })
            });
        }

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned ${res.status}`);
        }
        const data = await res.json();
        
        const msgId = generateId();
        const metadata = {
            id: msgId,
            routed_domains: data.routed_domains,
            document_attached: data.document_attached,
            verified_cases: data.pipeline_summary?.verified_cases || 0,
            cautioned_cases: data.pipeline_summary?.cautioned_cases || 0,
            rejected_cases: data.pipeline_summary?.rejected_cases || 0,
            cases_data: data.cases_data || {}
        };

        appendMessage('ai', data.final_draft || "Error: No draft generated.", metadata);
        _chatHistory.push({ role: 'ai', content: data.final_draft, metadata: metadata });
        localStorage.setItem(`nyaya_chat_${_currentSessionId}`, JSON.stringify(_chatHistory));

        removeQueryDoc();

    } catch (err) {
        appendMessage('ai', `**System Error:** ${err.message}`);
    } finally {
        setLoadingLock(false);
        document.getElementById('query-loading').classList.add('hidden');
    }
}

// Auto-init chat on load
document.addEventListener('DOMContentLoaded', () => {
    loadChatSessions();
    const sessions = JSON.parse(localStorage.getItem('nyaya_sessions') || '[]');
    if (sessions.length > 0) loadChat(sessions[0].id);
    else startNewChat();
});

function showCasesModal(type, msgId) {
    let casesData = window._currentCasesData;
    if (msgId && window._chatCases && window._chatCases[msgId]) {
        casesData = window._chatCases[msgId];
    }
    
    if (!casesData) return;
    const cases = casesData[type] || [];
    
    let title = 'Cases';
    if (type === 'verified') title = 'Verified Cases (Safe to Cite)';
    if (type === 'cautioned') title = 'Cautioned Cases (Dissenting Opinions)';
    if (type === 'rejected') title = 'Rejected Cases (Overruled / Bad Law)';
    
    document.getElementById('modal-title').textContent = title;
    const listEl = document.getElementById('modal-cases-list');
    listEl.innerHTML = '';
    
    if (cases.length === 0) {
        listEl.innerHTML = '<p style="color: var(--text-2);">No cases found in this category.</p>';
    } else {
        cases.forEach(c => {
            const card = document.createElement('div');
            card.className = 'case-card';
            
            const linkHtml = c.url ? `<a href="${c.url}" target="_blank" class="case-link-btn"><i class="fa-solid fa-arrow-up-right-from-square"></i> Read Full Judgment</a>` :
                             `<a href="https://indiankanoon.org/search/?formInput=${encodeURIComponent(c.name || c.case_name)}" target="_blank" class="case-link-btn"><i class="fa-solid fa-magnifying-glass"></i> Search on Indian Kanoon</a>`;
            
            card.innerHTML = `
                <div class="case-card-header">
                    <div>
                        <div class="case-card-title">${c.name || c.case_name || 'Unknown Case'}</div>
                        <div class="case-card-meta">${c.court || 'Court'} · ${c.year || 'Year'} · Hierarchy Score: ${c.hierarchy_score || 'N/A'}</div>
                    </div>
                </div>
                <div class="case-card-summary">
                    <strong>Verdict/Holding:</strong> ${c.verdict || c.summary || 'No summary available.'}<br/>
                    <strong>Issue:</strong> ${c.legal_issue || 'N/A'}
                </div>
                ${linkHtml}
            `;
            listEl.appendChild(card);
        });
    }
    
    document.getElementById('cases-modal').classList.remove('hidden');
}

function closeCasesModal() {
    document.getElementById('cases-modal').classList.add('hidden');
}

// ── TAB 2: Contract Analyzer ───────────────────────────────
function handleDrop(event) {
    event.preventDefault();
    document.getElementById('drop-area').classList.remove('drag-over');
    const file = event.dataTransfer.files[0];
    if (file) showFileSelected(file);
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) showFileSelected(file);
}

function showFileSelected(file) {
    document.getElementById('file-name-display').textContent = file.name;
    document.getElementById('file-selected').classList.remove('hidden');
    window._selectedFile = file;
}

// ── Chart helpers ───────────────────────────────────────────
function destroyCharts() {
    [riskGaugeChart, categoryBarChart, clauseDonutChart, standardDonutChart].forEach(c => {
        if (c) { c.destroy(); }
    });
    riskGaugeChart = categoryBarChart = clauseDonutChart = standardDonutChart = null;
}

function getRiskColor(score) {
    if (score >= 67) return '#EF4444';
    if (score >= 34) return '#F59E0B';
    return '#22C55E';
}

function buildGaugeChart(score) {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    const color = getRiskColor(score);
    riskGaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [color, 'rgba(255,255,255,0.06)'],
                borderWidth: 0,
                circumference: 180,
                rotation: 270,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
        }
    });
    document.getElementById('gaugeScore').textContent = score;
    document.getElementById('gaugeScore').style.color = color;
    const label = score >= 67 ? 'HIGH RISK' : score >= 34 ? 'MODERATE RISK' : 'LOW RISK';
    document.getElementById('gaugeLabel').textContent = label;
    document.getElementById('gaugeLabel').style.color = color;
}

function buildCategoryChart(scores) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    const labels = Object.keys(scores);
    const values = Object.values(scores);
    const colors = values.map(v => getRiskColor(v) + 'CC');
    categoryBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderRadius: 6,
                borderSkipped: false,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: {
                callbacks: { label: ctx => ` Risk Score: ${ctx.raw}/100` }
            }},
            scales: {
                x: {
                    min: 0, max: 100,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94A3B8', font: { size: 11 } }
                },
                y: { grid: { display: false }, ticks: { color: '#CBD5E1', font: { size: 11 } } }
            }
        }
    });
}

function buildClauseDonut(breakdown) {
    const ctx = document.getElementById('clauseDonut').getContext('2d');
    clauseDonutChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Risk', 'Medium Risk', 'Low Risk'],
            datasets: [{
                data: [breakdown.high, breakdown.medium, breakdown.low],
                backgroundColor: ['rgba(239,68,68,0.8)', 'rgba(245,158,11,0.8)', 'rgba(34,197,94,0.8)'],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '65%',
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94A3B8', padding: 12, font: { size: 11 } } }
            }
        }
    });
}

function buildStandardDonut(breakdown) {
    const ctx = document.getElementById('standardDonut').getContext('2d');
    standardDonutChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Industry Standard', 'Non-Standard'],
            datasets: [{
                data: [breakdown.standard, breakdown.non_standard],
                backgroundColor: ['rgba(34,197,94,0.8)', 'rgba(239,68,68,0.8)'],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '65%',
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94A3B8', padding: 12, font: { size: 11 } } }
            }
        }
    });
}

// ── Main upload handler ─────────────────────────────────────
async function handleFileUpload() {
    const file = window._selectedFile;
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', getMode());

    setLoadingLock(true);
    document.getElementById('contract-result').classList.add('hidden');
    document.getElementById('contract-loading').classList.remove('hidden');
    destroyCharts();

    try {
        const res = await fetch('/api/analyze-contract', { method: 'POST', body: formData });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned ${res.status}`);
        }
        const data = await res.json();

        // ── Decision Card ───────────────────────────────────
        const decisionEl = document.getElementById('decision-badge');
        const decisionReasonEl = document.getElementById('decision-reason');
        const dec = (data.decision || 'NEGOTIATE').toUpperCase();
        decisionEl.textContent = dec === 'SIGN' ? '✅ SIGN THIS CONTRACT'
                               : dec === 'REJECT' ? '🚫 DO NOT SIGN — REJECT'
                               : '⚠️ NEGOTIATE BEFORE SIGNING';
        decisionEl.className = 'decision-badge decision-' + dec.toLowerCase();
        decisionReasonEl.textContent = data.decision_reason || '';

        // ── Meta info ───────────────────────────────────────
        document.getElementById('contract-type').textContent = data.contract_type || '';
        document.getElementById('contract-parties').textContent = data.parties || '';
        document.getElementById('contract-summary').textContent = data.summary || '';
        document.getElementById('industry-assessment').textContent = data.industry_standard_assessment || '';
        document.getElementById('contract-recommendation').textContent = data.overall_recommendation || '';

        // ── Charts ──────────────────────────────────────────
        buildGaugeChart(data.overall_risk_score || 0);
        buildCategoryChart(data.category_scores || {});
        buildClauseDonut(data.risk_breakdown || { high: 0, medium: 0, low: 0 });
        buildStandardDonut(data.standard_breakdown || { standard: 0, non_standard: 0 });

        // ── Red / Green Flags ───────────────────────────────
        const redContainer = document.getElementById('red-flags-list');
        const greenContainer = document.getElementById('green-flags-list');
        redContainer.innerHTML = '';
        greenContainer.innerHTML = '';

        (data.red_flags || []).forEach(f => {
            const li = document.createElement('li');
            li.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${f}`;
            redContainer.appendChild(li);
        });
        (data.green_flags || []).forEach(f => {
            const li = document.createElement('li');
            li.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${f}`;
            greenContainer.appendChild(li);
        });

        document.getElementById('flags-section').classList.toggle('hidden',
            !data.red_flags?.length && !data.green_flags?.length);

        // ── Negotiation Priorities ──────────────────────────
        const negContainer = document.getElementById('negotiation-container');
        negContainer.innerHTML = '';
        (data.negotiation_priorities || []).forEach((n, i) => {
            const prioClass = n.priority === 'Critical' ? 'prio-critical'
                            : n.priority === 'Important' ? 'prio-important' : 'prio-nice';
            const card = document.createElement('div');
            card.className = 'neg-card';
            card.innerHTML = `
                <div class="neg-header">
                    <span class="neg-number">${i + 1}</span>
                    <span class="prio-badge ${prioClass}">${n.priority}</span>
                    <strong class="neg-clause">${n.clause}</strong>
                </div>
                <div class="neg-ask"><i class="fa-solid fa-pen-to-square"></i><span><strong>Ask for:</strong> ${n.ask}</span></div>
                <div class="neg-leverage"><i class="fa-solid fa-handshake"></i><span><strong>Leverage:</strong> ${n.leverage}</span></div>
            `;
            negContainer.appendChild(card);
        });
        document.getElementById('negotiation-section').classList.toggle('hidden', !data.negotiation_priorities?.length);

        // ── Clause Cards ────────────────────────────────────
        const container = document.getElementById('pitfalls-container');
        container.innerHTML = '';
        (data.pitfalls || []).forEach(p => {
            const isStandard = p.is_industry_standard;
            const riskClass = (p.risk_level || 'medium').toLowerCase();
            const standardBadge = isStandard
                ? `<div class="standard-badge"><i class="fa-solid fa-industry"></i> Industry Standard</div>`
                : `<div class="non-standard-badge"><i class="fa-solid fa-triangle-exclamation"></i> Non-Standard</div>`;
            const scoreColor = getRiskColor(p.risk_score || 50);
            const card = document.createElement('div');
            card.className = `pitfall-card risk-${riskClass}`;
            card.innerHTML = `
                <div class="clause-card-header">
                    <div class="risk-badge">${p.risk_level || 'Medium'} Risk</div>
                    ${standardBadge}
                    <span class="clause-category-tag">${p.clause_category || ''}</span>
                    <span class="clause-score" style="color:${scoreColor}">${p.risk_score || '—'}/100</span>
                </div>
                <h4>"${p.clause || ''}"</h4>
                <div class="industry-context"><i class="fa-solid fa-scale-balanced"></i><span><strong>Industry Context:</strong> ${p.industry_context || ''}</span></div>
                <p>${p.explanation || ''}</p>
                <div class="mitigation"><i class="fa-solid fa-lightbulb"></i><span><strong>${isStandard ? 'Tip' : 'Fix'}:</strong> ${p.mitigation || ''}</span></div>
            `;
            container.appendChild(card);
        });

        document.getElementById('contract-loading').classList.add('hidden');
        document.getElementById('contract-result').classList.remove('hidden');
        document.getElementById('contract-result').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
        document.getElementById('contract-loading').classList.add('hidden');
        alert('Error analyzing contract: ' + err.message);
    } finally {
        setLoadingLock(false);
        document.getElementById('file-selected').classList.add('hidden');
        window._selectedFile = null;
        document.getElementById('contract-file-input').value = '';
    }
}

// ── Navbar shadow on scroll ─────────────────────────────────
window.addEventListener('scroll', () => {
    const nav = document.getElementById('navbar');
    if (window.scrollY > 20) {
        nav.style.boxShadow = '0 4px 40px rgba(0,0,0,0.5)';
    } else {
        nav.style.boxShadow = 'none';
    }
});
