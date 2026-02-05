// ============================================================================
// DOM REFERENCES
// ============================================================================

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

// ============================================================================
// FRAUD RING VISUALIZER CLASS
// ============================================================================

class FraudRingVisualizer {
    constructor() {
        this.fraudRingsData = null;
    }

    displayFraudRings(fraudRingsReport) {
        this.fraudRingsData = fraudRingsReport;

        if (!fraudRingsReport || fraudRingsReport.total_rings_detected === 0) {
            this.hideAllFraudRingSections();
            return;
        }

        // Calculate risk scores for all rings
        fraudRingsReport.rings.forEach(ring => {
            const riskScore = this.calculateRiskScore(ring, fraudRingsReport.rings);
            ring.calculated_risk_score = riskScore;
            ring.calculated_severity = this.getRiskLevel(riskScore);
        });

        this.updateExecutiveAlert(fraudRingsReport);
        this.renderNetworkGraph(fraudRingsReport);
        this.renderRingCards(fraudRingsReport);
        this.generateAIRecommendations(fraudRingsReport);
    }

    hideAllFraudRingSections() {
        ['fraudRingAlertBanner', 'networkVisualizationSection', 'fraudRingDetailsSection', 'aiRecommendationsSection'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    }

    updateExecutiveAlert(report) {
        const banner = document.getElementById('fraudRingAlertBanner');
        if (!banner) return;

        const totalRingsSpan = document.getElementById('totalFraudRings');
        const totalMembersSpan = document.getElementById('totalFraudMembers');
        const pluralSpan = document.getElementById('ringsPlural');

        if (totalRingsSpan) totalRingsSpan.textContent = report.total_rings_detected;
        if (pluralSpan) pluralSpan.textContent = report.total_rings_detected === 1 ? '' : 's';

        let totalMembers = 0;
        if (report.rings && report.rings.length > 0) {
            const uniqueMembers = new Set();
            report.rings.forEach(ring => {
                if (ring.members && Array.isArray(ring.members)) {
                    ring.members.forEach(m => uniqueMembers.add(m));
                } else if (ring.member_count) {
                    totalMembers += ring.member_count;
                }
            });
            if (uniqueMembers.size > 0) totalMembers = uniqueMembers.size;
        }

        if (totalMembersSpan) totalMembersSpan.textContent = totalMembers;
        banner.style.display = 'flex';
    }

    renderNetworkGraph(report) {
        const section = document.getElementById('networkVisualizationSection');
        const container = document.getElementById('networkGraph');
        if (!section || !container) return;

        if (typeof vis === 'undefined') {
            container.innerHTML = '<p style="text-align:center;color:#64748B;padding:2rem;">Network visualization library not available</p>';
            section.style.display = 'block';
            return;
        }

        container.innerHTML = '';

        const nodes = new vis.DataSet();
        const edges = new vis.DataSet();

        report.rings.forEach((ring, index) => {
            const nodeSize = Math.sqrt(ring.member_count || 1) * 3 + 15;
            const label = ring.fake_name_pattern || ring.ring_name || ring.ring_type || `Ring ${index + 1}`;
            const amount = ring.total_fraud_amount || ring.total_amount || 0;
            const amountFormatted = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'EUR' }).format(amount);
            const severity = ring.calculated_severity || ring.severity || 'MEDIUM';
            const riskScore = ring.calculated_risk_score !== undefined ? ring.calculated_risk_score.toFixed(1) : '0';
            const nodeColor = this.getRiskColor(severity);

            const highlightColors = {
                '#DC2626': '#EF4444',
                '#EA580C': '#F97316',
                '#CA8A04': '#EAB308',
                '#16A34A': '#22C55E'
            };

            nodes.add({
                id: index,
                label: label,
                title: `${severity} (${riskScore}%)\n${ring.member_count || 0} members | ${amountFormatted}`,
                value: nodeSize,
                color: {
                    background: nodeColor,
                    border: nodeColor,
                    highlight: {
                        background: highlightColors[nodeColor] || nodeColor,
                        border: highlightColors[nodeColor] || nodeColor
                    }
                },
                font: {
                    color: '#FFFFFF',
                    size: 16,
                    face: 'Arial',
                    strokeWidth: 3,
                    strokeColor: '#1B263B'
                }
            });
        });

        report.rings.forEach((ring1, i) => {
            report.rings.slice(i + 1).forEach((ring2, j) => {
                if (Math.random() > 0.65) {
                    edges.add({
                        from: i,
                        to: i + j + 1,
                        color: { color: 'rgba(99, 102, 241, 0.2)' },
                        width: 1,
                        smooth: { type: 'continuous' }
                    });
                }
            });
        });

        const options = {
            physics: {
                barnesHut: {
                    gravitationalConstant: -5000,
                    centralGravity: 0.2,
                    springLength: 300,
                    springConstant: 0.02,
                    damping: 0.15
                },
                stabilization: { iterations: 250 }
            },
            nodes: {
                shape: 'dot',
                scaling: { min: 25, max: 70, label: { enabled: true, min: 16, max: 24 } },
                font: { color: '#FFFFFF', size: 18, strokeWidth: 3 },
                borderWidth: 3,
                borderWidthSelected: 4
            },
            edges: {
                width: 1,
                color: { inherit: false },
                smooth: { type: 'continuous' }
            },
            interaction: { hover: true, tooltipDelay: 100, zoomView: true, dragView: true },
            layout: { improvedLayout: true, hierarchical: false }
        };

        const network = new vis.Network(container, { nodes, edges }, options);
        network.once('stabilizationIterationsDone', () => {
            network.fit({ animation: { duration: 1000, easingFunction: 'easeInOutQuad' } });
        });

        section.style.display = 'block';
    }

    calculateRiskScore(ring, allRings) {
        const maxMembers = Math.max(...allRings.map(r => r.member_count || 0));
        const maxAmount = Math.max(...allRings.map(r => r.total_fraud_amount || 0));
        const maxTxns = Math.max(...allRings.map(r => r.fraudulent_orders || r.member_count || 0));

        const normMembers = maxMembers > 0 ? (ring.member_count || 0) / maxMembers * 100 : 0;
        const normAmount = maxAmount > 0 ? (ring.total_fraud_amount || 0) / maxAmount * 100 : 0;
        const normTxns = maxTxns > 0 ? (ring.fraudulent_orders || ring.member_count || 0) / maxTxns * 100 : 0;

        return (normMembers * 0.3) + (normAmount * 0.4) + (normTxns * 0.3);
    }

    getRiskLevel(score) {
        if (score >= 80) return 'CRITICAL';
        if (score >= 60) return 'HIGH';
        if (score >= 40) return 'MEDIUM';
        return 'LOW';
    }

    getRiskColor(severity) {
        const colors = { 'CRITICAL': '#DC2626', 'HIGH': '#EA580C', 'MEDIUM': '#CA8A04', 'LOW': '#16A34A' };
        return colors[severity] || '#6B7280';
    }

    renderRingCards(report) {
        const section = document.getElementById('fraudRingDetailsSection');
        const container = document.getElementById('fraudRingCardsList');
        if (!section || !container) return;

        container.innerHTML = '';
        const sortedRings = [...report.rings].sort((a, b) =>
            (b.calculated_risk_score || 0) - (a.calculated_risk_score || 0)
        );

        sortedRings.forEach((ring, index) => {
            container.appendChild(this.createFraudRingCard(ring, index));
        });

        section.style.display = 'block';
    }

    createFraudRingCard(ring, index) {
        const severity = ring.calculated_severity || ring.severity;
        const riskScore = ring.calculated_risk_score !== undefined ? ring.calculated_risk_score : (ring.risk_score * 100);
        const card = document.createElement('div');
        card.className = `fraud-ring-card severity-${severity.toLowerCase()}`;
        card.style.animation = `fadeIn 0.5s ease-out ${index * 0.1}s both`;

        const severityEmoji = { 'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢' };
        const evidence = ring.evidence || ring.key_indicators || {};
        const sampleTransactions = ring.sample_transactions || ring.sample_orders || [];
        const members = ring.members || [];

        // Build signal metrics bars from evidence_metrics
        const evidenceMetrics = ring.evidence_metrics || evidence;
        const signalLabels = {
            device_reuse: 'Device Reuse',
            device_family: 'Device Family',
            subnet_reuse: 'Subnet Reuse',
            shared_device: 'Shared Device',
            shared_ip: 'Shared IP',
            geo_mismatch_rate: 'Geo Mismatch',
            micro_amount_ratio: 'Micro Amounts',
            threshold_cluster_score: 'Threshold Cluster',
            merchant_concentration: 'Merchant Conc.',
            bin_concentration: 'BIN Conc.',
            disposable_email: 'Disposable Email',
            burst_score: 'Burstiness',
            ring_burst_score: 'Ring Burst',
            night_txn: 'Night Txns',
        };

        let signalBarsHtml = '';
        if (evidenceMetrics && typeof evidenceMetrics === 'object') {
            const entries = Object.entries(evidenceMetrics)
                .filter(([k, v]) => typeof v === 'number' && signalLabels[k])
                .sort((a, b) => b[1] - a[1]);

            if (entries.length > 0) {
                signalBarsHtml = `
                    <div class="dark-card" style="padding: 1rem;">
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">Signal Metrics</h4>
                        <div class="signal-metrics">
                            ${entries.map(([key, val]) => {
                                const pct = Math.min(val * 100, 100);
                                const barClass = pct >= 80 ? 'critical' : pct >= 60 ? 'high' : pct >= 30 ? 'medium' : 'low';
                                return `<div class="signal-row">
                                    <span class="signal-name">${signalLabels[key] || key}</span>
                                    <div class="signal-bar-bg"><div class="signal-bar-fill ${barClass}" style="width:${pct}%"></div></div>
                                    <span class="signal-value">${(val * 100).toFixed(0)}%</span>
                                </div>`;
                            }).join('')}
                        </div>
                    </div>
                `;
            }
        }

        // Fallback if no signal metrics — show raw evidence
        if (!signalBarsHtml) {
            signalBarsHtml = `
                <div class="dark-card" style="padding: 1rem;">
                    <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">Evidence</h4>
                    <div class="text-sm text-gray-400 space-y-1">
                        ${Array.isArray(evidence) ?
                            evidence.slice(0, 5).map(item => `<div>• ${item}</div>`).join('') :
                            Object.entries(evidence).slice(0, 5).map(([key, value]) => `
                                <div><span class="font-semibold">${key}:</span> ${JSON.stringify(value).substring(0, 50)}</div>
                            `).join('')}
                    </div>
                </div>
            `;
        }

        // Build infrastructure tags
        const topDevices = ring.top_devices || [];
        const topIPs = ring.top_ip_prefixes_24 || [];
        const topBINs = ring.top_bins || [];
        const topEmails = ring.top_email_domains || [];
        const hasInfra = topDevices.length + topIPs.length + topBINs.length + topEmails.length > 0;

        let infraHtml = '';
        if (hasInfra) {
            infraHtml = `<div class="infra-section">
                <h5>Shared Infrastructure</h5>
                <div class="infra-tags">
                    ${topDevices.map(d => `<span class="infra-tag device">${d}</span>`).join('')}
                    ${topIPs.map(ip => `<span class="infra-tag ip">${ip}.*</span>`).join('')}
                    ${topBINs.map(b => `<span class="infra-tag bin">BIN ${b}</span>`).join('')}
                    ${topEmails.map(e => `<span class="infra-tag email">@${e}</span>`).join('')}
                </div>
            </div>`;
        }

        card.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center gap-3 mb-3">
                        <div class="text-3xl">${severityEmoji[severity]}</div>
                        <div>
                            <h3 class="text-xl font-bold text-white mb-1">${ring.ring_name}</h3>
                            <div class="flex items-center gap-3 text-sm">
                                <span class="badge badge-${severity.toLowerCase()}">${severity}</span>
                                <span class="text-gray-400">${ring.member_count} members</span>
                                <span class="text-gray-400">Confidence: ${(ring.confidence * 100).toFixed(0)}%</span>
                                <span class="text-gray-400">Exposure: $${(ring.exposure || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                            </div>
                        </div>
                    </div>
                    <p class="text-gray-300 text-sm mb-3">${ring.explanation}</p>
                    <div class="text-sm text-gray-400">
                        <span class="font-semibold">Detection:</span> ${ring.detection_method}
                        <span style="margin-left:0.75rem;" class="font-semibold">Type:</span> ${ring.suspected_type || ring.ring_type || 'Unknown'}
                    </div>
                    ${infraHtml}
                </div>
                <svg class="expand-icon w-6 h-6 ml-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
            </div>
            <div class="fraud-ring-details">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    ${signalBarsHtml}
                    <div class="dark-card" style="padding: 1rem;">
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">Recommendations</h4>
                        <ul class="text-sm text-gray-400 space-y-1 list-disc list-inside">
                            ${(ring.recommendations || []).slice(0, 5).map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                ${members.length > 0 ? `
                    <div class="mb-4">
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">Ring Members (${members.length})</h4>
                        <div class="flex flex-wrap gap-2">
                            ${members.slice(0, 20).map(m => `<span class="member-chip">${m}</span>`).join('')}
                            ${members.length > 20 ? `<span class="member-chip" style="background: rgba(239, 68, 68, 0.2); border-color: #EF4444;">+${members.length - 20} more</span>` : ''}
                        </div>
                    </div>
                ` : ''}
                ${sampleTransactions.length > 0 ? `
                    <div>
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">Sample Transactions</h4>
                        <div class="dark-card" style="padding: 0; overflow: hidden;">
                            <table class="w-full text-sm dark-table">
                                <thead><tr>
                                    <th class="px-3 py-2 text-left">Transaction ID</th>
                                    <th class="px-3 py-2 text-left">User</th>
                                    <th class="px-3 py-2 text-right">Amount</th>
                                    <th class="px-3 py-2 text-left">Details</th>
                                </tr></thead>
                                <tbody>
                                    ${sampleTransactions.slice(0, 8).map(txn => `
                                        <tr>
                                            <td class="px-3 py-2 font-mono text-xs text-gray-400">${txn.transaction_id || txn.order_id || 'N/A'}</td>
                                            <td class="px-3 py-2 text-gray-300">${txn.user_id || txn.billing_first_name || 'N/A'}</td>
                                            <td class="px-3 py-2 text-right text-gray-300">$${(txn.amount || txn.total_amount || 0).toFixed(2)}</td>
                                            <td class="px-3 py-2 text-gray-400 text-xs">
                                                ${txn.merchant_id ? `Merchant: ${txn.merchant_id}` : ''}
                                                ${txn.country || txn.bin_country_code ? ` | ${txn.country || txn.bin_country_code}` : ''}
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        card.addEventListener('click', (e) => {
            if (window.getSelection().toString()) return;
            document.querySelectorAll('.fraud-ring-card.expanded').forEach(c => {
                if (c !== card) c.classList.remove('expanded');
            });
            card.classList.toggle('expanded');
            if (card.classList.contains('expanded')) {
                setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 100);
            }
        });

        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
        });

        return card;
    }

    generateAIRecommendations(report) {
        const section = document.getElementById('aiRecommendationsSection');
        const preventionList = document.getElementById('preventionTipsList');
        const detectionList = document.getElementById('detectionTipsList');
        if (!section || !preventionList || !detectionList) return;

        // Collect evidence-driven signals across all rings
        const allDevices = new Set();
        const allIPs = new Set();
        const allBINs = new Set();
        const allEmails = new Set();
        let hasGeoMismatch = false;
        let hasMicroAmounts = false;
        let hasDeviceReuse = false;
        let hasSubnetReuse = false;
        let hasBurstiness = false;
        let hasDisposableEmail = false;
        let hasNightTxn = false;
        let hasMerchantConc = false;
        let totalMembers = 0;

        report.rings.forEach(ring => {
            if (ring.member_count) totalMembers += ring.member_count;
            (ring.top_devices || []).forEach(d => allDevices.add(d));
            (ring.top_ip_prefixes_24 || []).forEach(ip => allIPs.add(ip));
            (ring.top_bins || []).forEach(b => allBINs.add(b));
            (ring.top_email_domains || []).forEach(e => allEmails.add(e));

            const em = ring.evidence_metrics || ring.evidence || {};
            if ((em.geo_mismatch_rate || 0) > 0.3) hasGeoMismatch = true;
            if ((em.micro_amount_ratio || 0) > 0.2) hasMicroAmounts = true;
            if ((em.device_reuse || 0) > 0.3) hasDeviceReuse = true;
            if ((em.subnet_reuse || 0) > 0.3) hasSubnetReuse = true;
            if ((em.burst_score || em.ring_burst_score || 0) > 0.3) hasBurstiness = true;
            if ((em.disposable_email || 0) > 0.3) hasDisposableEmail = true;
            if ((em.night_txn || 0) > 0.3) hasNightTxn = true;
            if ((em.merchant_concentration || 0) > 0.3) hasMerchantConc = true;
        });

        const tip = (color, text) =>
            `<li class="flex items-start gap-2"><span class="text-${color}-400 font-bold">&bull;</span><span>${text}</span></li>`;

        const preventionTips = [];
        if (allDevices.size > 0) {
            preventionTips.push(tip('blue', `Block compromised device fingerprints: <strong class="text-blue-400">${[...allDevices].slice(0, 3).join(', ')}</strong>`));
        }
        if (allIPs.size > 0) {
            preventionTips.push(tip('blue', `Rate-limit or block IP subnets: <strong class="text-blue-400">${[...allIPs].slice(0, 4).map(ip => ip + '.*').join(', ')}</strong>`));
        }
        if (allBINs.size > 0) {
            preventionTips.push(tip('blue', `Apply enhanced verification for card BINs: <strong class="text-blue-400">${[...allBINs].join(', ')}</strong>`));
        }
        if (hasDisposableEmail && allEmails.size > 0) {
            preventionTips.push(tip('blue', `Block disposable email domains: <strong class="text-blue-400">${[...allEmails].join(', ')}</strong>`));
        }
        if (hasMicroAmounts) {
            preventionTips.push(tip('blue', 'Implement micro-transaction velocity limits (card testing pattern detected)'));
        }
        if (hasGeoMismatch) {
            preventionTips.push(tip('blue', 'Enforce card-country / IP-country match validation'));
        }
        if (hasNightTxn) {
            preventionTips.push(tip('blue', 'Apply time-based risk scoring — elevated night transaction ratio detected'));
        }

        const detectionTips = [];
        if (hasDeviceReuse) {
            detectionTips.push(tip('purple', `Device reuse detected across ${totalMembers} accounts — implement device fingerprint clustering`));
        }
        if (hasSubnetReuse) {
            detectionTips.push(tip('purple', 'Subnet sharing pattern found — monitor /24 and /16 prefix reuse across accounts'));
        }
        if (hasBurstiness) {
            detectionTips.push(tip('purple', 'Temporal burst pattern detected — add velocity-based ring detection triggers'));
        }
        if (hasMerchantConc) {
            detectionTips.push(tip('purple', 'Merchant concentration anomaly — investigate merchant onboarding and transaction patterns'));
        }
        if (hasGeoMismatch) {
            detectionTips.push(tip('purple', 'Geo-mismatch rate elevated — cross-reference IP geolocation with card issuing country'));
        }
        detectionTips.push(tip('purple', `${report.total_rings_detected} ring(s) confirmed — review all ${totalMembers} flagged accounts for coordinated activity`));

        preventionList.innerHTML = preventionTips.slice(0, 7).join('');
        detectionList.innerHTML = detectionTips.slice(0, 6).join('');
        section.style.display = 'block';
    }
}

// ============================================================================
// FILE UPLOAD
// ============================================================================

uploadArea.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFile);

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
    uploadingContent.style.display = 'flex';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post('/api/v1/upload-and-analyze', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        analysisResults = response.data;
        displayResults();
        resultsSection.style.display = 'block';
    } catch (error) {
        showError(error.response?.data?.detail || error.message);
    } finally {
        uploadContent.style.display = 'flex';
        uploadingContent.style.display = 'none';
    }
}

// ============================================================================
// DISPLAY RESULTS
// ============================================================================

function displayResults() {
    const data = analysisResults;
    console.log('[FRS] Analysis results:', data.consolidated_fraud);

    resultsSection.style.display = 'block';

    // Ring visualization using consolidated_fraud as single source of truth
    const consolidated = data.consolidated_fraud;
    if (consolidated && consolidated.total_rings > 0) {
        const report = {
            total_rings_detected: consolidated.total_rings,
            rings: consolidated.rings.map(ring => ({
                ...ring,
                total_fraud_amount: ring.exposure || 0,
            })),
        };
        new FraudRingVisualizer().displayFraudRings(report);
    } else {
        new FraudRingVisualizer().hideAllFraudRingSections();
    }

    // Executive summary metrics
    renderExecutiveSummary(data);

    // Data audit section from audit_appendix
    renderDataAudit(data);

    // Ring type tags
    if (consolidated && consolidated.rings) {
        renderRingTypeTags(consolidated.rings);
    }

    // Financial exposure breakdown from audit_appendix
    renderFinancialExposure(data);
}

// ============================================================================
// DATA AUDIT
// ============================================================================

function renderDataAudit(data) {
    const section = document.getElementById('dataAuditSection');
    const grid = document.getElementById('auditGrid');
    if (!section || !grid) return;

    const consolidated = data.consolidated_fraud;
    const audit = consolidated?.audit_appendix?.data_proof;
    const dataValidation = data.data_validation;

    // Use audit_appendix if available, fall back to data_validation
    const source = audit || dataValidation;
    if (!source) return;

    grid.innerHTML = '';

    const items = [
        { label: 'Rows Processed', value: (source.row_count || 0).toLocaleString() },
        { label: 'Unique Users', value: (source.unique_user_count || source.unique_user_ids || 0).toLocaleString() },
        { label: 'Unique Transactions', value: (source.unique_tx_count || source.unique_transaction_ids || 0).toLocaleString() },
        { label: 'Amount Range', value: `$${(source.amount_min || 0).toFixed(2)} - $${(source.amount_max || 0).toFixed(2)}` },
        { label: 'Mean Amount', value: `$${(source.amount_mean || 0).toFixed(2)}` },
        { label: 'Time Window', value: `${source.timestamp_min || 'N/A'} to ${source.timestamp_max || 'N/A'}` },
    ];

    items.forEach(item => {
        const el = document.createElement('div');
        el.className = 'audit-item';
        el.innerHTML = `
            <div class="audit-item-label">${item.label}</div>
            <div class="audit-item-value">${item.value}</div>
        `;
        grid.appendChild(el);
    });

    // SHA256 hash (full width)
    const sha = source.sha256_input_file;
    if (sha) {
        const hashEl = document.createElement('div');
        hashEl.className = 'audit-item full-width';
        hashEl.innerHTML = `
            <div class="audit-item-label">SHA-256 Input File Hash</div>
            <div class="audit-item-value hash">${sha}</div>
        `;
        grid.appendChild(hashEl);
    }

    section.style.display = 'block';
}

// ============================================================================
// FINANCIAL EXPOSURE
// ============================================================================

function renderFinancialExposure(data) {
    const section = document.getElementById('financialExposureSection');
    const grid = document.getElementById('exposureGrid');
    if (!section || !grid) return;

    const consolidated = data.consolidated_fraud;
    const metrics = consolidated?.audit_appendix?.export_artifacts?.metrics_json;
    if (!metrics) return;

    grid.innerHTML = '';

    const cards = [
        {
            label: 'Expected Loss',
            value: metrics.expected_loss || 0,
            cls: 'expected',
            desc: 'Probability-weighted loss estimate',
        },
        {
            label: 'Potential Loss',
            value: metrics.potential_loss || 0,
            cls: 'potential',
            desc: 'Maximum exposure if all flagged txns are fraudulent',
        },
        {
            label: 'Actual Loss Estimate',
            value: metrics.actual_loss || 0,
            cls: 'actual',
            desc: 'Estimated realized loss based on confidence',
        },
    ];

    cards.forEach(card => {
        const el = document.createElement('div');
        el.className = 'exposure-card';
        el.innerHTML = `
            <div class="exposure-card-label">${card.label}</div>
            <div class="exposure-card-value ${card.cls}">$${card.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <div class="exposure-card-desc">${card.desc}</div>
        `;
        grid.appendChild(el);
    });

    // Additional stats row
    const statsEl = document.createElement('div');
    statsEl.className = 'exposure-card';
    statsEl.style.gridColumn = '1 / -1';
    const fr = metrics.flagged_transactions || 0;
    const fa = metrics.flagged_accounts || 0;
    const cr = metrics.confirmed_rings || 0;
    const sc = metrics.suspicious_clusters || 0;
    statsEl.innerHTML = `
        <div style="display:flex; justify-content:center; gap:2rem; flex-wrap:wrap;">
            <div><span style="font-size:1.1rem;font-weight:800;color:var(--critical);font-family:monospace;">${fr}</span> <span style="font-size:0.7rem;color:var(--text-muted);">Flagged Txns</span></div>
            <div><span style="font-size:1.1rem;font-weight:800;color:var(--high);font-family:monospace;">${fa}</span> <span style="font-size:0.7rem;color:var(--text-muted);">Flagged Accounts</span></div>
            <div><span style="font-size:1.1rem;font-weight:800;color:var(--accent);font-family:monospace;">${cr}</span> <span style="font-size:0.7rem;color:var(--text-muted);">Confirmed Rings</span></div>
            <div><span style="font-size:1.1rem;font-weight:800;color:var(--medium);font-family:monospace;">${sc}</span> <span style="font-size:0.7rem;color:var(--text-muted);">Suspicious Clusters</span></div>
        </div>
    `;
    grid.appendChild(statsEl);

    section.style.display = 'block';
}

// ============================================================================
// EXECUTIVE SUMMARY
// ============================================================================

function renderExecutiveSummary(data) {
    const consolidated = data.consolidated_fraud;
    const hasRings = consolidated && consolidated.total_rings > 0;

    // Metadata line
    const metaEl = document.getElementById('execMeta');
    if (metaEl) {
        const now = new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
        metaEl.textContent = `${data.records_processed || 0} records analyzed at ${now}`;
    }

    const ringsEl = document.getElementById('metricRings');
    const exposureEl = document.getElementById('metricExposure');
    const accountsEl = document.getElementById('metricAccounts');
    const riskEl = document.getElementById('metricRisk');
    const confEl = document.getElementById('metricConfidence');

    if (hasRings) {
        if (ringsEl) animateValue(ringsEl, 0, consolidated.total_rings, 1200);
        if (exposureEl) animateValue(exposureEl, 0, consolidated.total_exposure, 1500, '$');
        if (accountsEl) animateValue(accountsEl, 0, consolidated.total_flagged_accounts, 1200);

        const riskLevel = consolidated.overall_risk_level || 'LOW';
        if (riskEl) {
            riskEl.textContent = riskLevel;
            riskEl.className = 'exec-risk risk-' + riskLevel.toLowerCase();
        }

        const avgConf = consolidated.rings.reduce((s, r) => s + (r.confidence || 0), 0) / consolidated.rings.length;
        if (confEl) confEl.textContent = (avgConf * 100).toFixed(0) + '%';
    } else {
        if (ringsEl) ringsEl.textContent = '0';
        if (exposureEl) exposureEl.textContent = '$0';
        if (accountsEl) accountsEl.textContent = '0';
        if (riskEl) {
            riskEl.textContent = 'CLEAN';
            riskEl.className = 'exec-risk risk-clean';
        }
        if (confEl) confEl.textContent = '--';
    }
}

function animateValue(el, start, end, duration, prefix) {
    const startTime = performance.now();
    const isAmount = prefix === '$';

    function update(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * ease;

        if (isAmount) {
            el.textContent = '$' + current.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        } else {
            el.textContent = Math.round(current).toLocaleString();
        }

        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// ============================================================================
// RING TYPE TAGS
// ============================================================================

function renderRingTypeTags(rings) {
    const container = document.getElementById('ringTags');
    if (!container) return;

    container.innerHTML = '';

    // Count by type
    const typeCounts = {};
    rings.forEach(ring => {
        const t = ring.ring_type || 'unknown';
        typeCounts[t] = (typeCounts[t] || 0) + 1;
    });

    const typeConfig = {
        'IDENTITY_FRAUD': { icon: '🎭', label: 'Identity Fraud', color: '#EF4444' },
        'CARD_TESTING': { icon: '💳', label: 'Card Testing', color: '#F97316' },
        'HIGH_VELOCITY': { icon: '⚡', label: 'High Velocity', color: '#8B5CF6' },
        'DEVICE_SHARING': { icon: '📱', label: 'Device Sharing', color: '#3B82F6' },
        'MERCHANT_CYCLING': { icon: '🔄', label: 'Merchant Cycling', color: '#EC4899' },
        'MULE_MERCHANT_CLUSTER': { icon: '🏪', label: 'Mule/Merchant Cluster', color: '#D946EF' },
        'UnknownSuspicious': { icon: '🔍', label: 'Suspicious', color: '#9CA3AF' },
        'TEMPORAL_CLUSTERING': { icon: '⏰', label: 'Temporal Cluster', color: '#14B8A6' },
        'HIGH_VALUE': { icon: '💰', label: 'High Value', color: '#F59E0B' },
        'CROSS_BORDER': { icon: '✈️', label: 'Cross-Border', color: '#6366F1' },
        'unknown': { icon: '❓', label: 'Unclassified', color: '#6B7280' },
    };

    Object.entries(typeCounts).forEach(([type, count]) => {
        const config = typeConfig[type] || typeConfig['unknown'];
        const chip = document.createElement('div');
        chip.className = 'ring-type-chip';
        chip.style.borderColor = config.color;
        chip.innerHTML = `
            <span class="ring-type-icon">${config.icon}</span>
            <span class="ring-type-count" style="color: ${config.color}">${count}</span>
            <span class="ring-type-label">${config.label}</span>
        `;
        container.appendChild(chip);
    });

    // Severity summary chips
    const sevCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    rings.forEach(r => { sevCounts[r.severity || 'MEDIUM']++; });

    Object.entries(sevCounts).forEach(([sev, count]) => {
        if (count === 0) return;
        const colors = { CRITICAL: '#EF4444', HIGH: '#F97316', MEDIUM: '#EAB308', LOW: '#10B981' };
        const chip = document.createElement('div');
        chip.className = 'ring-type-chip severity-chip';
        chip.style.borderColor = colors[sev];
        chip.innerHTML = `
            <span class="ring-type-count" style="color: ${colors[sev]}">${count}</span>
            <span class="ring-type-label">${sev}</span>
        `;
        container.appendChild(chip);
    });
}

// ============================================================================
// CLEAR & DOWNLOAD BUTTONS
// ============================================================================

clearBtn.addEventListener('click', () => {
    fileInput.value = '';
    resultsSection.style.display = 'none';
    uploadContent.style.display = 'flex';
    uploadingContent.style.display = 'none';
    errorMsg.style.display = 'none';
    analysisResults = null;

    [
        'fraudRingAlertBanner', 'networkVisualizationSection', 'fraudRingDetailsSection',
        'aiRecommendationsSection', 'dataAuditSection', 'financialExposureSection'
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // Reset exec summary
    const ringsEl = document.getElementById('metricRings');
    const exposureEl = document.getElementById('metricExposure');
    const accountsEl = document.getElementById('metricAccounts');
    const riskEl = document.getElementById('metricRisk');
    const confEl = document.getElementById('metricConfidence');
    if (ringsEl) ringsEl.textContent = '0';
    if (exposureEl) exposureEl.textContent = '$0';
    if (accountsEl) accountsEl.textContent = '0';
    if (riskEl) { riskEl.textContent = 'LOW'; riskEl.className = 'exec-risk risk-low'; }
    if (confEl) confEl.textContent = '--';

    // Clear ring tags
    const ringTags = document.getElementById('ringTags');
    if (ringTags) ringTags.innerHTML = '';
});

downloadBtn.addEventListener('click', async () => {
    if (!analysisResults) return;

    downloadBtn.classList.add('downloading');
    setTimeout(() => downloadBtn.classList.remove('downloading'), 600);

    try {
        await generateWordReport(analysisResults);
        const origHTML = downloadBtn.innerHTML;
        downloadBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Downloaded';
        setTimeout(() => { downloadBtn.innerHTML = origHTML; }, 2000);
    } catch (err) {
        console.error('[FRS] Report generation failed:', err);
        showError('Failed to generate report. Please try again.');
    }
});

// ============================================================================
// ERROR DISPLAY
// ============================================================================

function showError(message) {
    errorMsg.style.display = 'flex';
    errorText.textContent = message;
    errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ============================================================================
// UTILITY
// ============================================================================

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ============================================================================
// WORD REPORT GENERATION
// ============================================================================

async function generateWordReport(data) {
    const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
            Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
            TableLayoutType, PageBreak } = docx;

    const consolidated = data.consolidated_fraud;
    const rings = consolidated?.rings || [];
    const totalRings = consolidated?.total_rings || 0;
    const totalAmount = consolidated?.total_exposure || 0;
    const totalMembers = consolidated?.total_flagged_accounts || 0;
    const overallRiskLevel = consolidated?.overall_risk_level || 'LOW';
    const overallRiskScore = consolidated?.overall_risk_score || 0;
    const audit = consolidated?.audit_appendix || {};
    const dataProof = audit.data_proof || data.data_validation || {};
    const metrics = audit.export_artifacts?.metrics_json || {};

    const currentDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const riskColor = s => s === 'CRITICAL' ? 'DC2626' : s === 'HIGH' ? 'EA580C' : s === 'MEDIUM' ? 'CA8A04' : '16A34A';
    const fmt$ = n => '$' + (n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const pct = n => ((n || 0) * 100).toFixed(0) + '%';
    const thinBorder = { top: { style: BorderStyle.SINGLE, size: 1, color: 'D0D0D0' }, bottom: { style: BorderStyle.SINGLE, size: 1, color: 'D0D0D0' }, left: { style: BorderStyle.SINGLE, size: 1, color: 'D0D0D0' }, right: { style: BorderStyle.SINGLE, size: 1, color: 'D0D0D0' } };
    const hCell = (text, w) => new TableCell({ children: [new Paragraph({ children: [new TextRun({ text, bold: true, size: 18, color: 'FFFFFF' })], spacing: { before: 40, after: 40 } })], shading: { type: ShadingType.SOLID, color: '1B263B' }, width: w ? { size: w, type: WidthType.PERCENTAGE } : undefined, borders: thinBorder });
    const dCell = (text, o = {}) => new TableCell({ children: [new Paragraph({ children: [new TextRun({ text: String(text), size: 18, color: o.color || '333333', bold: o.bold || false })], spacing: { before: 30, after: 30 }, alignment: o.align || AlignmentType.LEFT })], shading: o.bg ? { type: ShadingType.SOLID, color: o.bg } : undefined, borders: thinBorder });

    // Prose helpers
    const prose = (text, opts = {}) => new Paragraph({
        children: [new TextRun({ text, size: opts.size || 22, color: opts.color || '333333', italics: opts.italic || false, bold: opts.bold || false })],
        spacing: { before: opts.before || 80, after: opts.after || 80 },
        indent: opts.indent ? { left: opts.indent } : undefined,
    });
    const callout = (text) => new Paragraph({
        children: [new TextRun({ text: `"${text}"`, size: 24, color: '1B263B', bold: true, italics: true })],
        spacing: { before: 150, after: 150 },
        indent: { left: 400, right: 400 },
        alignment: AlignmentType.CENTER,
    });
    const bullet = (text, color = '333333') => new Paragraph({
        children: [new TextRun({ text: `    ▸  ${text}`, size: 20, color })],
        spacing: { before: 30, after: 30 },
    });
    const divider = () => new Paragraph({
        children: [new TextRun({ text: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', color: 'D0D0D0', size: 16 })],
        alignment: AlignmentType.CENTER, spacing: { before: 200, after: 200 },
    });
    const bar = (val) => { const f = Math.round((val || 0) * 10); return '█'.repeat(f) + '░'.repeat(10 - f); };

    // Narrative builders that analyze ring data
    const describeRingType = (type) => {
        const d = {
            'CARD_TESTING': 'Card testing is a technique where fraudsters validate stolen card numbers by making many small transactions in rapid succession. They probe merchants with micro-amounts to find cards that will authorize, then escalate to larger purchases. This pattern is one of the clearest indicators of organized fraud.',
            'IDENTITY_FRAUD': 'Identity fraud rings operate by creating multiple synthetic or stolen identities, often using disposable email addresses and mismatched geographic signals. Members share devices and infrastructure while posing as different people, a pattern that graph analysis can reliably detect.',
            'DEVICE_SHARING': 'Device sharing rings involve multiple accounts operating from the same physical devices. While some device sharing is legitimate (family devices, shared computers), the combination with other fraud signals — subnet reuse, unusual transaction patterns — indicates coordinated fraudulent activity.',
            'MULE_MERCHANT_CLUSTER': 'Mule/merchant clusters involve a network of accounts funneling transactions through specific merchants. This pattern often indicates money laundering or merchant collusion, where the merchant is complicit or compromised. High merchant concentration combined with threshold-amount clustering is the signature.',
            'HIGH_VELOCITY': 'High-velocity rings generate transactions at rates far exceeding normal user behavior. The temporal clustering and burst patterns suggest automated or coordinated activity designed to extract value before detection systems can respond.',
        };
        return d[type] || 'This ring exhibits a combination of fraud signals that, taken together, indicate coordinated fraudulent activity across multiple accounts sharing common infrastructure.';
    };

    const narrateSignals = (em, ring) => {
        const insights = [];
        const dr = em.device_reuse || 0;
        const sr = em.subnet_reuse || 0;
        const geo = em.geo_mismatch_rate || 0;
        const micro = em.micro_amount_ratio || 0;
        const mc = em.merchant_concentration || 0;
        const rb = em.ring_burst_score || em.burst_score || 0;
        const de = em.disposable_email || 0;
        const nt = em.night_txn || 0;
        const sd = em.shared_device || 0;

        if (dr >= 0.8) insights.push(`Device reuse is extremely high at ${pct(dr)} — the same devices are appearing across the vast majority of ring members, a hallmark of a single operator controlling multiple accounts.`);
        else if (dr >= 0.5) insights.push(`Device reuse at ${pct(dr)} shows significant overlap. Multiple ring members are transacting from identical or very similar devices.`);

        if (geo >= 0.8) insights.push(`Geographic mismatch is alarming at ${pct(geo)} — nearly all transactions show a disconnect between the card's issuing country and the IP address location. This is a strong indicator that stolen card data is being used remotely.`);
        else if (geo >= 0.3) insights.push(`A ${pct(geo)} geo-mismatch rate suggests some members are using cards from different countries than where they're transacting — worth investigating further.`);

        if (micro >= 0.5) insights.push(`${pct(micro)} of transactions are micro-amounts (under $10), which is the classic card-testing signature. Fraudsters start small to validate cards before attempting larger charges.`);
        else if (micro >= 0.2) insights.push(`Micro-transactions make up ${pct(micro)} of this ring's activity — not conclusive alone, but combined with other signals, it supports the card-testing hypothesis.`);

        if (rb >= 0.7) insights.push(`The ring burst score of ${pct(rb)} indicates highly synchronized timing across members. These accounts are transacting in tight temporal windows, suggesting automated or coordinated operation.`);
        else if (rb >= 0.3) insights.push(`Moderate temporal clustering (${pct(rb)} burst score) shows some coordination in transaction timing.`);

        if (de >= 0.5) insights.push(`Disposable email usage at ${pct(de)} means many of these accounts were created with throwaway email addresses — a clear sign the accounts were set up specifically for fraud.`);

        if (mc >= 0.6) insights.push(`Merchant concentration at ${pct(mc)} reveals that transactions are funneled through a very small set of merchants. This points to either merchant collusion or deliberate targeting.`);
        else if (mc >= 0.3) insights.push(`A ${pct(mc)} merchant concentration is above normal — this ring is showing preference for specific merchants.`);

        if (sr >= 0.5) insights.push(`Subnet reuse at ${pct(sr)} shows ring members connecting from the same network segments. They're likely operating from the same location or using the same VPN/proxy infrastructure.`);

        if (nt >= 0.5) insights.push(`${pct(nt)} of transactions occur during nighttime hours, which is unusual for legitimate commerce and suggests automated activity or operations in different time zones.`);

        if (sd >= 0.3 && dr >= 0.3) insights.push(`The combination of shared devices (${pct(sd)}) and device reuse (${pct(dr)}) paints a picture of a small number of physical devices being used to operate many accounts simultaneously.`);

        return insights;
    };

    const narrateImpact = (ring) => {
        const exp = ring.exposure || 0;
        const members = ring.member_count || 0;
        const conf = ring.confidence || 0;
        const parts = [];
        if (exp > 10000) parts.push(`With ${fmt$(exp)} in exposure, this ring represents a significant financial threat that warrants immediate intervention.`);
        else if (exp > 1000) parts.push(`The ${fmt$(exp)} exposure, while not the largest, is meaningful — and the operational pattern suggests it would grow if unchecked.`);
        else parts.push(`Although the current exposure of ${fmt$(exp)} is relatively modest, the infrastructure and coordination suggest this ring is in an early or testing phase.`);

        if (members > 20) parts.push(`The ${members} member accounts represent a large-scale operation. Blocking individual accounts won't be sufficient — the shared infrastructure (devices, IPs) must be addressed.`);
        else if (members > 5) parts.push(`With ${members} members, this is a moderately sized ring where targeted account actions combined with infrastructure blocks should be effective.`);

        if (conf >= 0.7) parts.push(`At ${pct(conf)} confidence, this is a high-certainty detection. The evidence strongly supports immediate action.`);
        else if (conf >= 0.55) parts.push(`The ${pct(conf)} confidence level meets the confirmation threshold, though enhanced monitoring should continue to gather additional evidence.`);

        return parts.join(' ');
    };

    const children = [];

    // ═══════════════════════════════════════════════════════════════
    // COVER PAGE
    // ═══════════════════════════════════════════════════════════════
    children.push(
        new Paragraph({ text: '', spacing: { before: 1200 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: 'FRAUD RING', size: 56, bold: true, color: '1B263B' }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: 'INVESTIGATION REPORT', size: 56, bold: true, color: '1B263B' }),
        ], spacing: { after: 200 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: `${totalRings} Confirmed Ring${totalRings !== 1 ? 's' : ''}  ·  ${totalMembers} Flagged Accounts  ·  `, size: 24, color: '666666' }),
            new TextRun({ text: overallRiskLevel + ' RISK', size: 24, bold: true, color: riskColor(overallRiskLevel) }),
        ], spacing: { after: 100 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: `${fmt$(metrics.expected_loss || totalAmount)} Expected Loss`, size: 28, bold: true, color: 'DC2626' }),
        ], spacing: { after: 300 } }),
        divider(),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: currentDate, size: 22, color: '888888' }),
        ], spacing: { after: 40 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: `Analysis of ${(dataProof.row_count || data.records_processed || 0).toLocaleString()} transactions  ·  ${(dataProof.unique_user_count || dataProof.unique_user_ids || 0).toLocaleString()} users  ·  ${dataProof.timestamp_min || ''} to ${dataProof.timestamp_max || ''}`, size: 18, color: '999999' }),
        ], spacing: { after: 40 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: 'FRS — FraudRingsSeeker  ·  Calibrated Pipeline v2  ·  Louvain Constrained Detection', size: 18, color: 'AAAAAA' }),
        ]}),
        new Paragraph({ children: [new PageBreak()] }),
    );

    // ═══════════════════════════════════════════════════════════════
    // 1. EXECUTIVE NARRATIVE
    // ═══════════════════════════════════════════════════════════════
    children.push(
        new Paragraph({ text: '1. What We Found', heading: HeadingLevel.HEADING_1, spacing: { before: 200, after: 200 } }),
    );

    // Build a dynamic opening paragraph
    const ringTypes = rings.map(r => (r.suspected_type || r.ring_type || '').replace(/_/g, ' ').toLowerCase());
    const uniqueTypes = [...new Set(ringTypes)].filter(Boolean);
    const openingNarrative = `Our analysis of ${(dataProof.row_count || data.records_processed || 0).toLocaleString()} transactions across ${(dataProof.unique_user_count || dataProof.unique_user_ids || 0).toLocaleString()} accounts uncovered ${totalRings} confirmed fraud ring${totalRings !== 1 ? 's' : ''} involving ${totalMembers} accounts. The rings operate using ${uniqueTypes.join(' and ')} techniques, with a combined expected loss of ${fmt$(metrics.expected_loss || totalAmount)}.`;

    children.push(prose(openingNarrative, { size: 24 }));

    // Severity narrative
    const highRings = rings.filter(r => r.severity === 'HIGH' || r.severity === 'CRITICAL');
    if (highRings.length > 0) {
        children.push(prose(
            `${highRings.length} of ${totalRings} ring${totalRings !== 1 ? 's' : ''} are classified as ${highRings.map(r => r.severity).join('/')} severity. These require immediate attention — the fraud infrastructure is active and growing.`,
            { size: 22, color: 'DC2626', bold: true }
        ));
    }

    // Key insight callout
    const topSignals = [];
    rings.forEach(r => {
        const em = r.evidence_metrics || r.evidence || {};
        if ((em.device_reuse || 0) > 0.7) topSignals.push('device reuse');
        if ((em.geo_mismatch_rate || 0) > 0.7) topSignals.push('geographic mismatch');
        if ((em.micro_amount_ratio || 0) > 0.5) topSignals.push('micro-transaction testing');
        if ((em.ring_burst_score || 0) > 0.7) topSignals.push('synchronized timing');
        if ((em.disposable_email || 0) > 0.5) topSignals.push('disposable emails');
    });
    const uniqueSignals = [...new Set(topSignals)];
    if (uniqueSignals.length > 0) {
        callout(`The strongest fraud indicators are: ${uniqueSignals.join(', ')}. These signals, appearing together across multiple accounts, form the evidentiary basis for each confirmed ring.`);
        children.push(callout(`The strongest fraud indicators are: ${uniqueSignals.join(', ')}.`));
    }

    // Exposure breakdown
    children.push(
        prose('Financial Impact at a Glance:', { bold: true, size: 24, before: 200 }),
    );
    children.push(new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
            new TableRow({ children: [hCell('Measure'), hCell('Amount'), hCell('What It Means')] }),
            new TableRow({ children: [dCell('Expected Loss'), dCell(fmt$(metrics.expected_loss || totalAmount), { bold: true, color: 'DC2626' }), dCell('The probability-weighted loss — our best single estimate')] }),
            new TableRow({ children: [dCell('Potential Loss'), dCell(fmt$(metrics.potential_loss), { bold: true, color: 'EA580C' }), dCell('Worst case if every flagged transaction is fraudulent')] }),
            new TableRow({ children: [dCell('Actual Loss Est.'), dCell(fmt$(metrics.actual_loss), { bold: true, color: 'CA8A04' }), dCell('Realized losses based on historical patterns')] }),
        ],
    }));

    children.push(new Paragraph({ children: [new PageBreak()] }));

    // ═══════════════════════════════════════════════════════════════
    // 2. THE INVESTIGATION — PER RING STORIES
    // ═══════════════════════════════════════════════════════════════
    children.push(
        new Paragraph({ text: '2. The Investigation', heading: HeadingLevel.HEADING_1, spacing: { before: 200, after: 100 } }),
        prose('Each confirmed ring is analyzed below with its full evidence profile, what makes it tick, and what to do about it.', { italic: true, color: '666666' }),
    );

    const sortedRings = [...rings].sort((a, b) => (b.confidence || 0) - (a.confidence || 0));

    sortedRings.forEach((ring, idx) => {
        const severity = ring.severity || 'MEDIUM';
        const ringType = ring.suspected_type || ring.ring_type || 'Unknown';
        const em = ring.evidence_metrics || ring.evidence || {};
        const topDevices = ring.top_devices || [];
        const topIPs = ring.top_ip_prefixes_24 || [];
        const topBINs = ring.top_bins || [];
        const topEmails = ring.top_email_domains || [];
        const members = ring.members || [];

        // Ring title
        children.push(divider());
        children.push(new Paragraph({
            spacing: { before: 200, after: 60 },
            children: [
                new TextRun({ text: `RING ${idx + 1}:  `, size: 28, bold: true, color: '1B263B' }),
                new TextRun({ text: ring.ring_name || ring.ring_id, size: 28, bold: true, color: '1B263B' }),
            ],
        }));
        children.push(new Paragraph({
            spacing: { after: 60 },
            children: [
                new TextRun({ text: `${severity} SEVERITY`, size: 22, bold: true, color: riskColor(severity) }),
                new TextRun({ text: `   ·   ${ring.member_count} members   ·   ${pct(ring.confidence)} confidence   ·   ${fmt$(ring.exposure)} exposure`, size: 20, color: '777777' }),
            ],
        }));

        // What is this type?
        children.push(
            prose('What This Is', { bold: true, size: 24, before: 200 }),
            prose(describeRingType(ringType)),
        );

        // Evidence narrative
        const insights = narrateSignals(em, ring);
        if (insights.length > 0) {
            children.push(prose('What the Evidence Shows', { bold: true, size: 24, before: 200 }));
            insights.forEach(insight => children.push(prose(insight, { indent: 200 })));
        }

        // Signal strength visual table
        const signalLabels = {
            device_reuse: 'Device Reuse', device_family: 'Device Family', subnet_reuse: 'Subnet Reuse',
            shared_device: 'Shared Device', shared_ip: 'Shared IP', geo_mismatch_rate: 'Geo Mismatch',
            micro_amount_ratio: 'Micro Amounts', threshold_cluster_score: 'Threshold Cluster',
            merchant_concentration: 'Merchant Conc.', bin_concentration: 'BIN Conc.',
            disposable_email: 'Disposable Email', burst_score: 'Burstiness',
            ring_burst_score: 'Ring Burst', night_txn: 'Night Activity',
        };
        const signalEntries = Object.entries(em)
            .filter(([k, v]) => typeof v === 'number' && signalLabels[k])
            .sort((a, b) => b[1] - a[1]);

        if (signalEntries.length > 0) {
            children.push(prose('Signal Strength Profile', { bold: true, size: 22, before: 200, after: 100 }));
            const rows = [new TableRow({ children: [hCell('Signal', 30), hCell('Strength', 45), hCell('Score', 12), hCell('Level', 13)] })];
            signalEntries.forEach(([key, val]) => {
                const bg = val >= 0.8 ? 'FDECEC' : val >= 0.6 ? 'FEF3E2' : val >= 0.3 ? 'FEF9E7' : 'ECFDF5';
                const level = val >= 0.8 ? 'CRITICAL' : val >= 0.6 ? 'HIGH' : val >= 0.3 ? 'MEDIUM' : 'LOW';
                rows.push(new TableRow({ children: [
                    dCell(signalLabels[key] || key, { bold: true }),
                    dCell(bar(val), { bg }),
                    dCell(pct(val), { bold: true, align: AlignmentType.CENTER, color: riskColor(level) }),
                    dCell(level, { color: riskColor(level), bold: true }),
                ]}));
            });
            children.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows }));
        }

        // Infrastructure — narrative style
        const infraParts = [];
        if (topDevices.length > 0) infraParts.push(`device fingerprint${topDevices.length > 1 ? 's' : ''} ${topDevices.map(d => `"${d}"`).join(', ')}`);
        if (topIPs.length > 0) infraParts.push(`IP subnet${topIPs.length > 1 ? 's' : ''} ${topIPs.map(ip => ip + '.*').join(', ')}`);
        if (topBINs.length > 0) infraParts.push(`card BIN${topBINs.length > 1 ? 's' : ''} ${topBINs.join(', ')}`);
        if (topEmails.length > 0) infraParts.push(`email domain${topEmails.length > 1 ? 's' : ''} @${topEmails.join(', @')}`);

        if (infraParts.length > 0) {
            children.push(
                prose('Shared Infrastructure', { bold: true, size: 22, before: 200 }),
                prose(`Ring members are connected through shared ${infraParts.join('; and ')}. This infrastructure overlap is what links otherwise separate accounts into a single coordinated operation.`),
            );
        }

        // Business impact narrative
        children.push(
            prose('Business Impact', { bold: true, size: 22, before: 200 }),
            prose(narrateImpact(ring)),
        );

        // What to do — ring-specific
        const recs = ring.recommendations || [];
        if (recs.length > 0) {
            children.push(prose('Recommended Response', { bold: true, size: 22, before: 200 }));
            recs.forEach(rec => children.push(bullet(rec)));
        }

        // Members (collapsed)
        if (members.length > 0) {
            children.push(
                prose(`Affected Accounts (${members.length}):`, { bold: true, size: 20, before: 200, color: '777777' }),
                prose(members.slice(0, 40).join(', ') + (members.length > 40 ? ` ... and ${members.length - 40} more` : ''), { size: 18, color: '999999' }),
            );
        }
    });

    children.push(new Paragraph({ children: [new PageBreak()] }));

    // ═══════════════════════════════════════════════════════════════
    // 3. THE BIG PICTURE — CROSS-RING INSIGHTS
    // ═══════════════════════════════════════════════════════════════
    children.push(
        new Paragraph({ text: '3. The Big Picture', heading: HeadingLevel.HEADING_1, spacing: { before: 200, after: 200 } }),
    );

    // Cross-ring comparison table
    if (rings.length > 1) {
        children.push(prose('How do the confirmed rings compare? This side-by-side view reveals whether they share tactics or represent independent threats.', { italic: true, color: '666666' }));

        const compSignals = ['device_reuse', 'geo_mismatch_rate', 'micro_amount_ratio', 'merchant_concentration', 'ring_burst_score', 'disposable_email', 'subnet_reuse', 'night_txn'];
        const compLabels = { device_reuse: 'Device Reuse', geo_mismatch_rate: 'Geo Mismatch', micro_amount_ratio: 'Micro Amounts', merchant_concentration: 'Merchant Conc.', ring_burst_score: 'Ring Burst', disposable_email: 'Disp. Email', subnet_reuse: 'Subnet Reuse', night_txn: 'Night Activity' };

        const header = [hCell('Signal', 25)];
        sortedRings.forEach(r => header.push(hCell((r.ring_name || r.ring_id).substring(0, 20), Math.floor(75 / sortedRings.length))));
        const compRows = [new TableRow({ children: header })];

        compSignals.forEach(sig => {
            const cells = [dCell(compLabels[sig] || sig, { bold: true })];
            sortedRings.forEach(r => {
                const em = r.evidence_metrics || r.evidence || {};
                const val = em[sig] || 0;
                const bg = val >= 0.8 ? 'FDECEC' : val >= 0.6 ? 'FEF3E2' : val >= 0.3 ? 'FEF9E7' : 'ECFDF5';
                const level = val >= 0.8 ? 'CRITICAL' : val >= 0.6 ? 'HIGH' : val >= 0.3 ? 'MEDIUM' : 'LOW';
                cells.push(dCell(`${bar(val)} ${pct(val)}`, { bg, color: riskColor(level) }));
            });
            compRows.push(new TableRow({ children: cells }));
        });

        children.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: compRows }));
    }

    // Cross-ring narrative insights
    const allDevices = new Set(), allIPs = new Set(), allBINs = new Set(), allEmails = new Set();
    let maxGeo = 0, maxDevice = 0, maxBurst = 0, maxMicro = 0;
    rings.forEach(r => {
        (r.top_devices || []).forEach(d => allDevices.add(d));
        (r.top_ip_prefixes_24 || []).forEach(ip => allIPs.add(ip));
        (r.top_bins || []).forEach(b => allBINs.add(b));
        (r.top_email_domains || []).forEach(e => allEmails.add(e));
        const em = r.evidence_metrics || r.evidence || {};
        maxGeo = Math.max(maxGeo, em.geo_mismatch_rate || 0);
        maxDevice = Math.max(maxDevice, em.device_reuse || 0);
        maxBurst = Math.max(maxBurst, em.ring_burst_score || em.burst_score || 0);
        maxMicro = Math.max(maxMicro, em.micro_amount_ratio || 0);
    });

    children.push(prose('Key Patterns Across All Rings:', { bold: true, size: 24, before: 300 }));

    if (allDevices.size > 0) children.push(prose(
        `Across all rings, ${allDevices.size} unique device fingerprint${allDevices.size > 1 ? 's were' : ' was'} flagged. Device reuse peaks at ${pct(maxDevice)}, meaning the same physical devices are being used to operate accounts across ring boundaries. This is the single most reliable indicator of coordinated fraud.`
    ));
    if (maxGeo > 0.3) children.push(prose(
        `Geographic inconsistency is a recurring theme, reaching ${pct(maxGeo)} in the worst case. Fraudsters are using cards issued in one country while connecting from IP addresses in another — a pattern that legitimate users rarely exhibit at this scale.`
    ));
    if (maxBurst > 0.3) children.push(prose(
        `Temporal analysis reveals coordinated timing with burst scores up to ${pct(maxBurst)}. Ring members are not transacting independently — they're operating in synchronized windows, which strongly suggests a central operator or automated tooling.`
    ));
    if (allEmails.size > 0) children.push(prose(
        `Disposable email domains (${[...allEmails].join(', ')}) appear across ring accounts. These throwaway addresses are created solely for fraud operations and should be blocklisted.`
    ));

    // Suspicious clusters note
    const sc = metrics.suspicious_clusters || 0;
    if (sc > 0) {
        children.push(prose('Beyond the Confirmed Rings:', { bold: true, size: 24, before: 300 }));
        children.push(prose(
            `In addition to the ${totalRings} confirmed ring${totalRings !== 1 ? 's' : ''}, our analysis identified ${sc} suspicious cluster${sc !== 1 ? 's' : ''} that fell below the confirmation threshold. These clusters share some fraud indicators but lack sufficient evidence for conclusive classification. They should be monitored — some may graduate to confirmed rings as more data becomes available.`
        ));
    }

    children.push(new Paragraph({ children: [new PageBreak()] }));

    // ═══════════════════════════════════════════════════════════════
    // 4. WHAT TO DO NOW — PRIORITIZED ACTIONS
    // ═══════════════════════════════════════════════════════════════
    children.push(
        new Paragraph({ text: '4. What To Do Now', heading: HeadingLevel.HEADING_1, spacing: { before: 200, after: 200 } }),
        prose('Actions are prioritized by urgency and tied directly to the evidence uncovered in this investigation.', { italic: true, color: '666666' }),
    );

    // Immediate
    children.push(prose('Immediate (within 24 hours)', { bold: true, size: 24, color: 'DC2626', before: 200 }));
    if (allDevices.size > 0) children.push(bullet(`Block device fingerprints: ${[...allDevices].slice(0, 5).join(', ')}. These are the connective tissue between ring accounts.`, 'DC2626'));
    if (allIPs.size > 0) children.push(bullet(`Rate-limit or block IP subnets: ${[...allIPs].slice(0, 5).map(ip => ip + '.*').join(', ')}. Ring members route through these networks.`, 'DC2626'));
    children.push(bullet(`Freeze the ${totalMembers} flagged accounts pending manual review. Focus first on accounts in HIGH-severity rings.`, 'DC2626'));

    // Short-term
    children.push(prose('Short-Term (within 1 week)', { bold: true, size: 24, color: 'EA580C', before: 200 }));
    if (allEmails.size > 0) children.push(bullet(`Add ${[...allEmails].join(', ')} to the email domain blocklist.`));
    if (allBINs.size > 0) children.push(bullet(`Apply enhanced verification (3DS, step-up auth) for card BINs: ${[...allBINs].join(', ')}.`));
    if (maxGeo > 0.3) children.push(bullet(`Deploy card-country vs. IP-country validation rules. Current mismatch rate: ${pct(maxGeo)}.`));
    if (maxMicro > 0.2) children.push(bullet(`Implement micro-transaction velocity limits to catch card-testing patterns early.`));

    // Long-term
    children.push(prose('Long-Term (ongoing)', { bold: true, size: 24, color: '3B82F6', before: 200 }));
    children.push(bullet('Integrate real-time graph analysis into the transaction pipeline for continuous ring detection.'));
    children.push(bullet('Build feedback loops — confirmed fraud cases should retrain the model to improve future detection.'));
    children.push(bullet(`Monitor the ${sc} suspicious clusters for escalation. Set alerts if their confidence scores rise.`));
    children.push(bullet('Implement cross-merchant fraud intelligence sharing to detect rings operating across platforms.'));

    children.push(new Paragraph({ children: [new PageBreak()] }));

    // ═══════════════════════════════════════════════════════════════
    // 5. DATA PROVENANCE & METHODOLOGY
    // ═══════════════════════════════════════════════════════════════
    children.push(
        new Paragraph({ text: '5. Data Provenance & Methodology', heading: HeadingLevel.HEADING_1, spacing: { before: 200, after: 200 } }),
        prose('This section documents the input data and detection parameters for audit and reproducibility purposes.', { italic: true, color: '666666' }),
    );

    children.push(new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        rows: [
            new TableRow({ children: [hCell('Property', 35), hCell('Value', 65)] }),
            new TableRow({ children: [dCell('Records Analyzed'), dCell((dataProof.row_count || data.records_processed || 0).toLocaleString())] }),
            new TableRow({ children: [dCell('Unique Users'), dCell((dataProof.unique_user_count || dataProof.unique_user_ids || 0).toLocaleString())] }),
            new TableRow({ children: [dCell('Unique Transactions'), dCell((dataProof.unique_tx_count || dataProof.unique_transaction_ids || 0).toLocaleString())] }),
            new TableRow({ children: [dCell('Amount Range'), dCell(`${fmt$(dataProof.amount_min)} — ${fmt$(dataProof.amount_max)} (mean: ${fmt$(dataProof.amount_mean)})`)] }),
            new TableRow({ children: [dCell('Time Window'), dCell(`${dataProof.timestamp_min || 'N/A'} to ${dataProof.timestamp_max || 'N/A'}`)] }),
            new TableRow({ children: [dCell('SHA-256 Input Hash'), dCell(dataProof.sha256_input_file || 'N/A', { color: '3B82F6' })] }),
            new TableRow({ children: [dCell('Model'), dCell('Calibrated Pipeline v2 (calibrated_v2)')] }),
            new TableRow({ children: [dCell('Detection Algorithm'), dCell('Louvain Community Detection (constrained)')] }),
            new TableRow({ children: [dCell('Ring Confidence Floor'), dCell('55%')] }),
            new TableRow({ children: [dCell('Tx Risk Threshold'), dCell('60 / 100')] }),
            new TableRow({ children: [dCell('Account Risk Threshold'), dCell('50 / 100')] }),
            new TableRow({ children: [dCell('Exposure Method'), dCell(metrics.exposure_method || 'expected_loss')] }),
        ],
    }));

    // ═══════════════════════════════════════════════════════════════
    // FOOTER
    // ═══════════════════════════════════════════════════════════════
    children.push(
        new Paragraph({ text: '', spacing: { before: 600 } }),
        divider(),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: 'CONFIDENTIAL', size: 20, bold: true, color: 'AAAAAA' }),
        ], spacing: { after: 60 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: 'This report contains sensitive fraud intelligence and is intended for authorized personnel only.', size: 18, color: '999999', italics: true }),
        ], spacing: { after: 40 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
            new TextRun({ text: 'Automated analysis by FRS — FraudRingsSeeker v2.0', size: 18, color: 'AAAAAA' }),
        ]}),
    );

    const doc = new Document({ sections: [{ properties: { page: { margin: { top: 1000, bottom: 1000, left: 1200, right: 1200 } } }, children }] });
    const blob = await Packer.toBlob(doc);
    saveAs(blob, `fraud-investigation-${new Date().toISOString().slice(0, 10)}.docx`);
}

// ============================================================================
// HEALTH CHECK & SYSTEM STATUS
// ============================================================================

async function checkHealth() {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const footerDot = document.getElementById('footerDot');
    const footerStatus = document.getElementById('footerStatus');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
        const resp = await fetch('/health', { signal: controller.signal });
        clearTimeout(timeoutId);
        const online = resp.ok;

        if (statusDot) statusDot.className = 'status-dot ' + (online ? 'online' : 'offline');
        if (statusText) statusText.textContent = online ? 'System Online' : 'API Error ' + resp.status;
        if (footerDot) footerDot.className = 'footer-dot ' + (online ? 'online' : 'offline');
        if (footerStatus) footerStatus.textContent = online ? 'API: Connected' : 'API: Error ' + resp.status;
    } catch (e) {
        clearTimeout(timeoutId);
        if (statusDot) statusDot.className = 'status-dot offline';
        if (statusText) statusText.textContent = 'System Offline';
        if (footerDot) footerDot.className = 'footer-dot offline';
        if (footerStatus) footerStatus.textContent = 'API: Offline';
    }
}

function updateFooterTime() {
    const el = document.getElementById('footerTime');
    if (el) {
        el.textContent = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    setInterval(checkHealth, 60000);

    updateFooterTime();
    setInterval(updateFooterTime, 30000);
});
