/**
 * Nyaya AI — Frontend Application Logic
 * Handles tab switching, mode selection, query submission, contract upload.
 */

// ── State ──────────────────────────────────────────────────
let currentMode = 'citizen';
let isLoading = false;

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

// ── TAB 1: Legal Engine ─────────────────────────────────────
async function submitQuery() {
    const query = document.getElementById('legal-query').value.trim();
    if (!query) { alert('Please describe your legal situation.'); return; }

    setLoadingLock(true);
    document.getElementById('query-result').classList.add('hidden');
    document.getElementById('query-loading').classList.remove('hidden');
    startAgentAnimation();

    try {
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, mode: getMode() })
        });
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        // Tags
        const tagsEl = document.getElementById('routed-domains');
        tagsEl.innerHTML = '';
        (data.routed_domains || []).forEach(d => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.textContent = d.toUpperCase();
            tagsEl.appendChild(tag);
        });

        // Stats
        document.getElementById('stat-verified').textContent = data.pipeline_summary?.verified_cases ?? 0;
        document.getElementById('stat-cautioned').textContent = data.pipeline_summary?.cautioned_cases ?? 0;
        document.getElementById('stat-rejected').textContent = data.pipeline_summary?.rejected_cases ?? 0;
        document.getElementById('stat-revisions').textContent = data.revisions_made ?? 0;

        // Memo
        document.getElementById('final-draft').innerHTML = marked.parse(data.final_draft || '');

        stopAgentAnimation();
        document.getElementById('query-loading').classList.add('hidden');
        document.getElementById('query-result').classList.remove('hidden');
        document.getElementById('query-result').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
        stopAgentAnimation();
        document.getElementById('query-loading').classList.add('hidden');
        alert('Error connecting to AI: ' + err.message);
    } finally {
        setLoadingLock(false);
    }
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
    // Store reference for later upload
    window._selectedFile = file;
}

async function handleFileUpload() {
    const file = window._selectedFile;
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', getMode());

    setLoadingLock(true);
    document.getElementById('contract-result').classList.add('hidden');
    document.getElementById('contract-loading').classList.remove('hidden');

    try {
        const res = await fetch('/api/analyze-contract', { method: 'POST', body: formData });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned ${res.status}`);
        }
        const data = await res.json();

        // Contract type & summary
        const contractTypeEl = document.getElementById('contract-type');
        if (contractTypeEl) contractTypeEl.textContent = data.contract_type || '';
        document.getElementById('contract-summary').textContent = data.summary || '';

        // Industry standard assessment banner
        const industryAssessEl = document.getElementById('industry-assessment');
        if (industryAssessEl) industryAssessEl.textContent = data.industry_standard_assessment || '';

        // Safe/Unsafe verdict
        const verdict = document.getElementById('contract-verdict');
        if (data.is_safe_to_sign) {
            verdict.textContent = '✓ Broadly Acceptable — Safe to Sign';
            verdict.className = 'verdict-chip safe';
        } else {
            verdict.textContent = '✗ High Risk — Renegotiate Before Signing';
            verdict.className = 'verdict-chip unsafe';
        }

        document.getElementById('contract-recommendation').textContent = data.overall_recommendation || '';

        const container = document.getElementById('pitfalls-container');
        container.innerHTML = '';
        (data.pitfalls || []).forEach(p => {
            const isStandard = p.is_industry_standard;
            const riskClass = (p.risk_level || 'medium').toLowerCase();
            const standardBadge = isStandard
                ? `<div class="standard-badge"><i class="fa-solid fa-industry"></i> Industry Standard</div>`
                : `<div class="non-standard-badge"><i class="fa-solid fa-triangle-exclamation"></i> Non-Standard</div>`;
            const card = document.createElement('div');
            card.className = `pitfall-card risk-${riskClass}`;
            card.innerHTML = `
                <div class="clause-card-header">
                    <div class="risk-badge">${p.risk_level || 'Medium'} Risk</div>
                    ${standardBadge}
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
