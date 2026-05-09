// Tab Switching Logic
function switchTab(tabId, event) {
    if(event) event.preventDefault();
    
    // Update nav links
    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
    event.target.classList.add('active');

    // Update sections
    document.querySelectorAll('.tab-content').forEach(sec => sec.classList.add('hidden'));
    document.getElementById(tabId + '-section').classList.remove('hidden');
}

// ==========================================
// TAB 1: LEGAL ENGINE QUERY
// ==========================================
async function submitQuery() {
    const queryInput = document.getElementById('legal-query').value.trim();
    if (!queryInput) {
        alert("Please enter a legal query.");
        return;
    }

    // UI State: Loading
    document.getElementById('query-result').classList.add('hidden');
    document.getElementById('query-loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: queryInput })
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        
        // Render Tags
        const tagsContainer = document.getElementById('routed-domains');
        tagsContainer.innerHTML = '';
        data.routed_domains.forEach(domain => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.textContent = domain.toUpperCase();
            tagsContainer.appendChild(tag);
        });

        // Render Stats
        document.getElementById('stat-verified').textContent = data.pipeline_summary?.verified_cases || 0;
        document.getElementById('stat-cautioned').textContent = data.pipeline_summary?.cautioned_cases || 0;
        document.getElementById('stat-rejected').textContent = data.pipeline_summary?.rejected_cases || 0;
        document.getElementById('stat-revisions').textContent = data.revisions_made || 0;

        // Render Markdown
        document.getElementById('final-draft').innerHTML = marked.parse(data.final_draft);

        // UI State: Done
        document.getElementById('query-loading').classList.add('hidden');
        document.getElementById('query-result').classList.remove('hidden');

    } catch (error) {
        alert("Error connecting to AI: " + error.message);
        document.getElementById('query-loading').classList.add('hidden');
    }
}

// ==========================================
// TAB 2: CONTRACT ANALYZER
// ==========================================
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

// Drag events
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleFileUpload();
    }
});

// Click event
fileInput.addEventListener('change', handleFileUpload);

async function handleFileUpload() {
    if (!fileInput.files.length) return;
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    // UI State: Loading
    document.getElementById('contract-result').classList.add('hidden');
    document.getElementById('contract-loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/analyze-contract', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || `Server returned ${response.status}`);
        }

        const data = await response.json();

        // Render Header
        document.getElementById('contract-summary').textContent = data.summary;
        
        const verdictEl = document.getElementById('contract-verdict');
        if (data.is_safe_to_sign) {
            verdictEl.textContent = "SAFE TO SIGN";
            verdictEl.className = "verdict-badge verdict-safe";
        } else {
            verdictEl.textContent = "DO NOT SIGN";
            verdictEl.className = "verdict-badge verdict-danger";
        }

        document.getElementById('contract-recommendation').textContent = data.overall_recommendation;

        // Render Pitfalls
        const pitfallsContainer = document.getElementById('pitfalls-container');
        pitfallsContainer.innerHTML = '';

        if (data.pitfalls && data.pitfalls.length > 0) {
            data.pitfalls.forEach(p => {
                const card = document.createElement('div');
                card.className = 'pitfall-card';
                
                let badgeClass = 'risk-low';
                if (p.risk_level.toLowerCase() === 'high') badgeClass = 'risk-high';
                if (p.risk_level.toLowerCase() === 'medium') badgeClass = 'risk-medium';

                card.innerHTML = `
                    <div class="pitfall-card-header">
                        <span class="pitfall-clause">"${p.clause}"</span>
                        <span class="risk-badge ${badgeClass}">${p.risk_level} RISK</span>
                    </div>
                    <p class="pitfall-explanation">${p.explanation}</p>
                    <div class="pitfall-mitigation">
                        <strong>Mitigation:</strong> ${p.mitigation}
                    </div>
                `;
                pitfallsContainer.appendChild(card);
            });
        } else {
            pitfallsContainer.innerHTML = '<p style="color: #10b981;">No critical pitfalls found. The contract appears standard.</p>';
        }

        // UI State: Done
        document.getElementById('contract-loading').classList.add('hidden');
        document.getElementById('contract-result').classList.remove('hidden');

    } catch (error) {
        alert("Error analyzing contract: " + error.message);
        document.getElementById('contract-loading').classList.add('hidden');
    }
}
