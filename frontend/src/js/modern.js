const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadContent = document.getElementById('uploadContent');
const uploadingContent = document.getElementById('uploadingContent');
const resultsSection = document.getElementById('resultsSection');
const clearBtn = document.getElementById('clearBtn');
const downloadBtn = document.getElementById('downloadBtn');
const errorMsg = document.getElementById('errorMsg');
const errorText = document.getElementById('errorText');

let analysisResults = null;
let riskChart = null;

// File upload handling
uploadArea.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFile);

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleFile();
    }
});

async function handleFile() {
    const file = fileInput.files[0];
    if (!file) return;

    errorMsg.style.display = 'none';
    uploadContent.style.display = 'none';
    uploadingContent.style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post('/upload-and-analyze', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        analysisResults = response.data;
        displayResults();
        resultsSection.style.display = 'block';
    } catch (error) {
        showError(error.response?.data?.detail || error.message);
    } finally {
        uploadContent.style.display = 'block';
        uploadingContent.style.display = 'none';
    }
}

function displayResults() {
    const data = analysisResults;

    // Update summary cards
    document.getElementById('totalTxns').textContent = data.records_processed;
    document.getElementById('highRisk').textContent = data.summary.high_risk_entities;
    document.getElementById('anomaliesCount').textContent = data.anomalies.length;
    document.getElementById('patternsCount').textContent = data.money_laundering_patterns.length;

    // Risk distribution chart
    const ctx = document.getElementById('riskChart').getContext('2d');
    if (riskChart) riskChart.destroy();
    riskChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Risk', 'Medium Risk', 'Low Risk'],
            datasets: [{
                data: [
                    data.summary.high_risk_entities,
                    data.summary.medium_risk_entities,
                    data.summary.low_risk_entities
                ],
                backgroundColor: ['#ef4444', '#f97316', '#22c55e'],
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Risk profiles table
    const profilesTable = document.getElementById('profilesTable');
    profilesTable.innerHTML = data.risk_profiles.map(profile => `
        <tr class="border-b hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-sm">${profile.entity_id}</td>
            <td class="px-4 py-3">
                <span class="font-semibold">${profile.final_risk_score.toFixed(4)}</span>
            </td>
            <td class="px-4 py-3">
                <span class="badge badge-${profile.risk_level.toLowerCase()}">${profile.risk_level}</span>
            </td>
            <td class="px-4 py-3 text-sm">
                ${profile.risk_factors.length > 0 ? profile.risk_factors.join(', ') : 'None'}
            </td>
            <td class="px-4 py-3 text-sm">
                ${profile.red_flags.length > 0 ? `<span class="text-red-600 font-semibold">${profile.red_flags.join(', ')}</span>` : 'None'}
            </td>
        </tr>
    `).join('');

    // Patterns info
    const patternsInfo = document.getElementById('patternsInfo');
    if (data.money_laundering_patterns.length > 0) {
        patternsInfo.innerHTML = data.money_laundering_patterns.map(pattern => `
            <div class="p-3 bg-orange-50 border border-orange-200 rounded">
                <div class="font-semibold text-orange-900">${pattern.type}</div>
                <div class="text-sm text-orange-700 mt-1">${pattern.description}</div>
                <div class="text-xs text-orange-600 mt-2">Risk Score: ${pattern.risk_score.toFixed(4)}</div>
            </div>
        `).join('');
    } else {
        patternsInfo.innerHTML = '<p class="text-gray-500">No suspicious patterns detected</p>';
    }

    // Anomalies
    if (data.anomalies.length > 0) {
        document.getElementById('anomaliesSection').style.display = 'block';
        const anomaliesList = document.getElementById('anomaliesList');
        anomaliesList.innerHTML = data.anomalies.slice(0, 5).map(anomaly => `
            <div class="p-3 bg-red-50 border border-red-200 rounded">
                <div class="font-semibold text-red-900">${anomaly.method}</div>
                <div class="text-sm text-red-700">${anomaly.reason}</div>
                <div class="text-xs text-red-600 mt-1">Txn: ${anomaly.transaction_id} | Score: ${anomaly.anomaly_score.toFixed(4)}</div>
            </div>
        `).join('');
    }

    // Networks
    if (data.fraud_networks.networks && data.fraud_networks.networks.length > 0) {
        document.getElementById('networkSection').style.display = 'block';
        const networkInfo = document.getElementById('networkInfo');
        networkInfo.innerHTML = `
            <div class="mb-3"><strong>Suspicious Clusters:</strong> ${data.fraud_networks.networks.length}</div>
            <div class="mb-3"><strong>Total Graph Nodes:</strong> ${data.fraud_networks.total_nodes || 'N/A'}</div>
            <div><strong>Graph Density:</strong> ${(data.fraud_networks.graph_density * 100).toFixed(2)}%</div>
        `;
    }
}

clearBtn.addEventListener('click', () => {
    fileInput.value = '';
    resultsSection.style.display = 'none';
    uploadContent.style.display = 'block';
    uploadingContent.style.display = 'none';
    errorMsg.style.display = 'none';
    analysisResults = null;
    if (riskChart) riskChart.destroy();
});

downloadBtn.addEventListener('click', () => {
    if (!analysisResults) return;
    const report = JSON.stringify(analysisResults, null, 2);
    const blob = new Blob([report], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fraud-analysis-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
});

function showError(message) {
    errorMsg.style.display = 'block';
    errorText.textContent = message;
}
