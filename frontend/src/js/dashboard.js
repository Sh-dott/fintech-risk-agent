const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

// Initialize charts
let decisionChart, riskDistributionChart;

async function initDashboard() {
    await updateMetrics();
    await updateHistory();
    updateChartsOnInterval();
    setInterval(updateMetrics, 5000);
    setInterval(updateHistory, 10000);
}

async function updateMetrics() {
    try {
        const response = await fetch(`${API_BASE}/analytics`);
        const data = await response.json();

        document.getElementById('totalTransactions').textContent = data.summary.total_transactions;
        document.getElementById('approvalRate').textContent = data.summary.approval_rate_percent;
        document.getElementById('blockRate').textContent = data.summary.block_rate_percent;
        document.getElementById('p95Latency').textContent = data.performance.p95_latency_ms;
        document.getElementById('avgRiskScore').textContent = data.performance.avg_risk_score;

        const uptime = Math.floor(data.performance.uptime_seconds);
        const minutes = Math.floor(uptime / 60);
        const seconds = uptime % 60;
        document.getElementById('uptimeInfo').textContent = `Uptime: ${minutes}m ${seconds}s`;

        updateDecisionChart(data.summary);
    } catch (error) {
        console.error('Error updating metrics:', error);
    }
}

function updateDecisionChart(data) {
    const ctx = document.getElementById('decisionChart').getContext('2d');
    if (decisionChart) {
        decisionChart.destroy();
    }
    decisionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Allowed', 'Blocked', 'Review'],
            datasets: [{
                data: [data.total_allowed, data.total_blocked, data.total_review],
                backgroundColor: ['#28a745', '#dc3545', '#ffc107'],
                borderColor: ['#fff', '#fff', '#fff'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: 'Decision Distribution'
                }
            }
        }
    });
}

function updateChartsOnInterval() {
    const ctx2 = document.getElementById('riskDistributionChart').getContext('2d');
    if (riskDistributionChart) {
        riskDistributionChart.destroy();
    }
    riskDistributionChart = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: ['Low Risk', 'Medium Risk', 'High Risk'],
            datasets: [{
                label: 'Transaction Count',
                data: [45, 28, 12],
                backgroundColor: ['#d4edda', '#fff3cd', '#f8d7da'],
                borderColor: ['#28a745', '#ffc107', '#dc3545'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true
                },
                title: {
                    display: true,
                    text: 'Risk Distribution'
                }
            }
        }
    });
}

async function updateHistory() {
    try {
        const response = await fetch(`${API_BASE}/history?limit=10`);
        const data = await response.json();

        const tbody = document.getElementById('historyBody');
        tbody.innerHTML = '';

        if (data.transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #999;">No transactions yet</td></tr>';
            return;
        }

        data.transactions.reverse().forEach(txn => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td><strong>${txn.transaction_id}</strong></td>
                <td><span class="reason-tag">${txn.decision.toUpperCase()}</span></td>
                <td>${txn.risk_score.toFixed(3)}</td>
                <td>${txn.user_id}</td>
                <td>${txn.merchant_id}</td>
                <td>${new Date(txn.timestamp).toLocaleTimeString()}</td>
            `;
        });
    } catch (error) {
        console.error('Error updating history:', error);
    }
}

document.getElementById('scoreForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
        transaction_id: document.getElementById('txnId').value,
        amount: parseFloat(document.getElementById('amount').value),
        currency: 'USD',
        merchant_id: document.getElementById('merchantId').value,
        user_id: document.getElementById('userId').value,
        device_id: document.getElementById('deviceId').value,
        ip_address: document.getElementById('ipAddress').value,
        user_country: 'US'
    };

    try {
        document.getElementById('errorMessage').classList.remove('show');
        const response = await fetch(`${API_BASE}/score`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        displayResult(result);
        await updateMetrics();
        await updateHistory();
    } catch (error) {
        document.getElementById('errorMessage').textContent = `Error: ${error.message}`;
        document.getElementById('errorMessage').classList.add('show');
        console.error('Error scoring transaction:', error);
    }
});

function displayResult(result) {
    const decisionClass = `decision-${result.decision}`;
    const resultContent = `
        <div class="decision-badge ${decisionClass}">
            ${result.decision.toUpperCase()}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
            <div>
                <strong>Risk Score:</strong> ${result.risk_score.toFixed(3)}
            </div>
            <div>
                <strong>Risk Level:</strong> ${result.risk_level.toUpperCase()}
            </div>
        </div>
        <div class="reason-codes">
            <h4>Reason Codes</h4>
            ${result.reason_codes.map(code => `<span class="reason-tag">${code}</span>`).join('')}
        </div>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px;">
            <strong>Explanation:</strong>
            <p style="margin-top: 8px; color: #666;">${result.explanation}</p>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; font-size: 0.9em; color: #666;">
            <div>Latency: ${result.latency_ms.toFixed(2)}ms</div>
            <div>Compliance ID: ${result.compliance_log_id}</div>
        </div>
    `;
    document.getElementById('resultContent').innerHTML = resultContent;
    document.getElementById('resultContainer').classList.add('show');
}

// Initialize on load
window.addEventListener('load', initDashboard);
