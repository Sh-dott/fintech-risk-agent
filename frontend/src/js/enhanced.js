let analysisResults = null;
let charts = {};

const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const uploadContent = uploadArea.querySelector('.upload-content');
const loadingSpinner = document.getElementById('loadingSpinner');
const errorMsg = document.getElementById('errorMsg');
const tabsContainer = document.getElementById('tabsContainer');
const actionButtons = document.getElementById('actionButtons');

// File upload handlers
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.background = 'linear-gradient(135deg, #e8eef7 0%, #b8d4f1 100%)';
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)';
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)';
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleFile();
    }
});

fileInput.addEventListener('change', handleFile);

async function handleFile() {
    const file = fileInput.files[0];
    if (!file) return;

    errorMsg.style.display = 'none';
    uploadContent.style.display = 'none';
    loadingSpinner.style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post('/upload-and-analyze', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        analysisResults = response.data;
        displayResults();
        uploadArea.style.display = 'none';
        tabsContainer.style.display = 'flex';
        actionButtons.style.display = 'flex';
    } catch (error) {
        showError(error.response?.data?.detail || 'Error analyzing file');
        loadingSpinner.style.display = 'none';
        uploadContent.style.display = 'block';
    }
}

function displayResults() {
    // Overview Tab
    displayMetrics();
    displayCharts();
    displayInsights();

    // Denial Analysis Tab
    displayDenials();

    // Customer Analytics Tab
    displayCustomers();

    // Detailed Reports Tab
    displayDetailedReports();
}

function displayMetrics() {
    const data = analysisResults;
    const metricsGrid = document.getElementById('metricsGrid');

    const metrics = [
        {
            label: 'Total Transactions',
            value: data.records_processed,
            icon: '📊'
        },
        {
            label: 'High Risk (>0.7)',
            value: data.summary?.high_risk_count || 0,
            icon: '⚠️'
        },
        {
            label: 'Detected Anomalies',
            value: data.anomalies?.length || 0,
            icon: '🔍'
        },
        {
            label: 'Fraud Networks',
            value: data.fraud_networks?.suspicious_clusters || 0,
            icon: '🕸️'
        },
        {
            label: 'ML Patterns',
            value: data.money_laundering_patterns?.length || 0,
            icon: '🎯'
        },
        {
            label: 'Unique Entities',
            value: data.risk_profiles?.length || 0,
            icon: '👥'
        }
    ];

    metricsGrid.innerHTML = metrics.map((m, i) => `
        <div class="metric-card" onclick="showMetricDetails('${m.label}')">
            <div style="font-size: 2em; margin-bottom: 10px;">${m.icon}</div>
            <div class="metric-label">${m.label}</div>
            <div class="metric-value">${m.value}</div>
        </div>
    `).join('');
}

function displayCharts() {
    // Decision Distribution
    const decisions = {
        'Approved': analysisResults.summary?.approved_count || 0,
        'Denied': analysisResults.summary?.denied_count || 0,
        'Review': analysisResults.summary?.review_count || 0
    };

    new Chart(document.getElementById('decisionChart'), {
        type: 'doughnut',
        data: {
            labels: Object.keys(decisions),
            datasets: [{
                data: Object.values(decisions),
                backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
                borderColor: 'white',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });

    // Risk Distribution
    const risks = analysisResults.risk_profiles || [];
    const riskBins = {
        'Very Low (0-0.2)': 0,
        'Low (0.2-0.4)': 0,
        'Medium (0.4-0.6)': 0,
        'High (0.6-0.8)': 0,
        'Very High (0.8-1.0)': 0
    };

    risks.forEach(r => {
        const score = r.final_risk_score || 0;
        if (score < 0.2) riskBins['Very Low (0-0.2)']++;
        else if (score < 0.4) riskBins['Low (0.2-0.4)']++;
        else if (score < 0.6) riskBins['Medium (0.4-0.6)']++;
        else if (score < 0.8) riskBins['High (0.6-0.8)']++;
        else riskBins['Very High (0.8-1.0)']++;
    });

    new Chart(document.getElementById('riskChart'), {
        type: 'bar',
        data: {
            labels: Object.keys(riskBins),
            datasets: [{
                label: 'Count',
                data: Object.values(riskBins),
                backgroundColor: ['#10b981', '#84cc16', '#f59e0b', '#ef4444', '#991b1b'],
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    // Denial Reasons
    const denialReasons = analysisResults.summary?.denial_reasons || {};
    new Chart(document.getElementById('denialReasonsChart'), {
        type: 'bar',
        data: {
            labels: Object.keys(denialReasons).slice(0, 5),
            datasets: [{
                label: 'Count',
                data: Object.values(denialReasons).slice(0, 5),
                backgroundColor: '#ef4444',
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { beginAtZero: true }
            }
        }
    });

    // Amount Distribution
    const amounts = analysisResults.risk_profiles?.map(r => r.amount) || [];
    new Chart(document.getElementById('amountChart'), {
        type: 'line',
        data: {
            labels: amounts.map((_, i) => i + 1),
            datasets: [{
                label: 'Transaction Amount',
                data: amounts,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.3,
                fill: true,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom' }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function displayInsights() {
    const summary = analysisResults.summary || {};
    const insights = [
        `${summary.high_risk_count || 0} high-risk entities detected (>0.7 score)`,
        `${analysisResults.anomalies?.length || 0} statistical anomalies identified`,
        `${analysisResults.fraud_networks?.suspicious_clusters || 0} suspicious fraud networks detected`,
        `${analysisResults.money_laundering_patterns?.length || 0} potential ML patterns found`
    ].join(' | ');

    document.getElementById('insightsText').textContent = insights;
}

function displayDenials() {
    const risks = analysisResults.risk_profiles || [];
    const denied = risks.filter(r => r.risk_level === 'HIGH');

    const html = denied.map(d => `
        <div class="denial-card" onclick="showDenialDetails('${d.entity_id}')">
            <div class="denial-header">
                <div class="denial-id">Entity: ${d.entity_id}</div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <div class="denial-reason">Risk: ${(d.final_risk_score * 100).toFixed(1)}%</div>
                    <div class="denial-risk severity-${d.risk_level.toLowerCase()}">${d.risk_level}</div>
                </div>
            </div>
            <div class="contributing-factors">
                <strong>Risk Factors:</strong>
                ${d.risk_factors?.map(f => `<div class="factor-tag">${f}</div>`).join('') || '<div class="factor-tag">No factors</div>'}
            </div>
        </div>
    `).join('');

    document.getElementById('denialsList').innerHTML = html || '<p style="color: #999;">No high-risk entities found</p>';
}

function displayCustomers() {
    const risks = analysisResults.risk_profiles || [];
    const groupedByCustomer = {};

    risks.forEach(r => {
        const cid = r.entity_id || 'unknown';
        if (!groupedByCustomer[cid]) {
            groupedByCustomer[cid] = {
                total: 0,
                riskScores: [],
                ...r
            };
        }
        groupedByCustomer[cid].total++;
        groupedByCustomer[cid].riskScores.push(r.final_risk_score);
    });

    const tbody = document.getElementById('customersTableBody');
    tbody.innerHTML = Object.entries(groupedByCustomer).map(([id, data]) => {
        const avgRisk = data.riskScores.reduce((a, b) => a + b, 0) / data.riskScores.length;
        const riskLevel = avgRisk > 0.7 ? 'HIGH' : avgRisk > 0.4 ? 'MEDIUM' : 'LOW';
        const badgeClass = riskLevel === 'HIGH' ? 'badge-high' : riskLevel === 'MEDIUM' ? 'badge-medium' : 'badge-low';

        return `
            <tr onclick="showCustomerDetails('${id}')">
                <td><strong>${id}</strong></td>
                <td>${data.total}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>${(avgRisk * 100).toFixed(1)}%</td>
                <td><span class="badge ${badgeClass}">${riskLevel}</span></td>
                <td>-</td>
            </tr>
        `;
    }).join('');
}

function displayDetailedReports() {
    const container = document.getElementById('detailedReportsContainer');
    container.innerHTML = `
        <div class="insights-box">
            <h3>Platform Statistics</h3>
            <p><strong>Records Processed:</strong> ${analysisResults.records_processed}</p>
            <p><strong>Analysis Timestamp:</strong> ${new Date(analysisResults.timestamp).toLocaleString()}</p>
            <p><strong>File Name:</strong> ${analysisResults.file_name}</p>
        </div>
    `;
}

function showDenialDetails(entityId) {
    const entity = analysisResults.risk_profiles?.find(r => r.entity_id === entityId);
    if (!entity) return;

    const modal = document.getElementById('detailModal');
    const body = document.getElementById('modalBody');

    body.innerHTML = `
        <div class="insights-box">
            <h3>Entity: ${entity.entity_id}</h3>
            <p><strong>Risk Score:</strong> ${(entity.final_risk_score * 100).toFixed(1)}%</p>
            <p><strong>Risk Level:</strong> ${entity.risk_level}</p>
            <p><strong>Risk Factors:</strong> ${entity.risk_factors?.join(', ') || 'None'}</p>
            <p><strong>Red Flags:</strong> ${entity.red_flags?.join(', ') || 'None'}</p>
        </div>
    `;

    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('detailModal').classList.remove('active');
}

function showError(msg) {
    errorMsg.style.display = 'block';
    errorMsg.textContent = msg;
}

function downloadReport() {
    const dataStr = JSON.stringify(analysisResults, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `fraud-analysis-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
}

function exportCSV() {
    alert('CSV export coming soon');
}

function clearResults() {
    location.reload();
}

function printResults() {
    window.print();
}

function showMetricDetails(label) {
    alert('Details for: ' + label);
}

function showCustomerDetails(id) {
    alert('Details for customer: ' + id);
}

// Tab switching
document.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});
