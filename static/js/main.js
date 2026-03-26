let uploadedFile = null;
let sessionId = null;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function openZoom(imageSrc, title) {
    document.getElementById('zoomImage').src = imageSrc;
    document.getElementById('zoomTitle').textContent = title;
    document.getElementById('zoomModal').style.display = 'block';
}

function closeZoom() {
    document.getElementById('zoomModal').style.display = 'none';
}

// Close zoom on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeZoom();
    }
});

// Open animation in new window
function openAnimationWindow() {
    if (sessionId) {
        const width = 1600;
        const height = 900;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;
        
        window.open(
            `/animation/${sessionId}`, 
            'Animation', 
            `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
        );
    } else {
        alert('Please analyze a dataset first to generate the animation!');
    }
}

// ============================================================================
// FILE UPLOAD HANDLER
// ============================================================================

document.getElementById('fileInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        uploadedFile = file;
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('analyzeBtn').disabled = false;
    }
});

// Drag and drop support
const uploadArea = document.querySelector('.upload-area');

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'white';
    uploadArea.style.background = 'rgba(255,255,255,0.1)';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = 'rgba(255,255,255,0.5)';
    uploadArea.style.background = 'transparent';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'rgba(255,255,255,0.5)';
    uploadArea.style.background = 'transparent';
    
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) {
        uploadedFile = file;
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('analyzeBtn').disabled = false;
    } else {
        alert('Please upload a CSV file!');
    }
});

// ============================================================================
// CONFLICT RULES MANAGEMENT
// ============================================================================

function addRule() {
    const rulesContainer = document.getElementById('conflictRules');
    const ruleCount = rulesContainer.children.length + 1;
    
    const ruleHtml = `
        <div class="conflict-rule">
            <div class="row align-items-center">
                <div class="col-md-3">
                    <select class="form-select" id="ruleType${ruleCount}">
                        <option value="same_value">Same Value</option>
                        <option value="time_overlap">Time Overlap</option>
                        <option value="resource_exceed">Resource Exceed</option>
                    </select>
                </div>
                <div class="col-md-7">
                    <input type="text" class="form-control" id="ruleColumn${ruleCount}" placeholder="Enter column name(s)">
                </div>
                <div class="col-md-2">
                    <button class="btn btn-sm btn-outline-danger" onclick="removeRule(this)">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    rulesContainer.insertAdjacentHTML('beforeend', ruleHtml);
}

function removeRule(button) {
    const rule = button.closest('.conflict-rule');
    if (document.querySelectorAll('.conflict-rule').length > 1) {
        rule.remove();
    } else {
        alert('At least one rule is required!');
    }
}

function getConflictRules() {
    const rules = [];
    document.querySelectorAll('.conflict-rule').forEach((rule, index) => {
        const ruleNum = index + 1;
        const type = document.getElementById(`ruleType${ruleNum}`).value;
        const column = document.getElementById(`ruleColumn${ruleNum}`).value;
        
        if (column) {
            rules.push({
                type: type,
                column: column
            });
        }
    });
    return rules;
}

// ============================================================================
// DATASET ANALYSIS
// ============================================================================

async function analyzeDataset() {
    if (!uploadedFile) {
        alert('Please upload a dataset first!');
        return;
    }
    
    const rules = getConflictRules();
    if (rules.length === 0) {
        alert('Please configure at least one conflict rule!');
        return;
    }
    
    // Show loading
    document.getElementById('loadingOverlay').style.display = 'flex';
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('conflict_rules', JSON.stringify(rules));
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            sessionId = data.session_id;
            displayResults(data);
        } else {
            alert('Analysis failed: ' + data.error);
        }
        
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

// ============================================================================
// DISPLAY RESULTS
// ============================================================================

function displayResults(data) {
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    
    // Update summary
    document.getElementById('summaryNodes').textContent = data.summary.nodes;
    document.getElementById('summaryEdges').textContent = data.summary.edges;
    document.getElementById('summaryDegree').textContent = data.summary.max_degree;
    
    // Display visualizations
    const vizGrid = document.getElementById('vizGrid');
    vizGrid.innerHTML = '';
    
    const vizTitles = {
        'viz1_scenarios.png':   'Runtime Comparison — 3 Deployment Scenarios',
        'viz2_scalability.png': 'Scalability Analysis',
        'viz3_bottleneck.png':  'Coordinator Bottleneck Delay',
        'viz4_latency.png':     'Network Latency Impact',
        'viz5_architecture.png':'Algorithm Architecture Summary',
        'viz6_winners.png':     'Winners Matrix — Quality & Speed'
    };
    
    data.visualizations.forEach((viz, index) => {
        const vizTitle = vizTitles[viz] || `Visualization ${index + 1}`;
        const imageUrl = `/api/image/${sessionId}/${viz}`;
        
        const vizCard = `
            <div class="viz-card">
                <img src="${imageUrl}" 
                     alt="${vizTitle}" 
                     onclick="openZoom('${imageUrl}', '${vizTitle}')">
                <div class="viz-card-body">
                    <h6 class="viz-card-title">${vizTitle}</h6>
                    <a href="/api/download/${sessionId}/${viz}" class="download-btn">
                        <i class="fas fa-download"></i> Download
                    </a>
                </div>
            </div>
        `;
        vizGrid.insertAdjacentHTML('beforeend', vizCard);
    });
    
    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}