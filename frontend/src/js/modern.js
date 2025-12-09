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

// ============================================================================
// FRAUD RING VISUALIZER CLASS
// ============================================================================

class FraudRingVisualizer {
    constructor() {
        this.fraudRingsData = null;
    }

    displayFraudRings(fraudRingsReport) {
        console.log('[FraudRingVisualizer] displayFraudRings called with:', fraudRingsReport);
        this.fraudRingsData = fraudRingsReport;

        // Only display if rings were actually detected
        if (!fraudRingsReport || fraudRingsReport.total_rings_detected === 0) {
            console.log('[FraudRingVisualizer] No rings to display, hiding sections');
            this.hideAllFraudRingSections();
            return;
        }

        console.log('[FraudRingVisualizer] Displaying', fraudRingsReport.total_rings_detected, 'fraud rings');

        // Calculate risk scores for all rings (used by network graph and cards)
        console.log('[FraudRingVisualizer] Calculating weighted risk scores...');
        fraudRingsReport.rings.forEach(ring => {
            const riskScore = this.calculateRiskScore(ring, fraudRingsReport.rings);
            ring.calculated_risk_score = riskScore;
            ring.calculated_severity = this.getRiskLevel(riskScore);
        });

        // Update executive alert banner
        console.log('[FraudRingVisualizer] Updating alert banner...');
        this.updateExecutiveAlert(fraudRingsReport);

        // Update summary cards (5 ring types)
        console.log('[FraudRingVisualizer] Updating summary cards...');
        this.updateSummaryCards(fraudRingsReport);

        // Render network graph
        console.log('[FraudRingVisualizer] Rendering network graph...');
        this.renderNetworkGraph(fraudRingsReport);

        // Render fraud ring detail cards
        console.log('[FraudRingVisualizer] Rendering ring cards...');
        this.renderRingCards(fraudRingsReport);

        // Generate AI recommendations
        console.log('[FraudRingVisualizer] Generating AI recommendations...');
        this.generateAIRecommendations(fraudRingsReport);

        console.log('[FraudRingVisualizer] Display complete!');
    }

    hideAllFraudRingSections() {
        const sections = [
            'fraudRingAlertBanner',
            'fraudRingSummarySection',
            'networkVisualizationSection',
            'fraudRingDetailsSection'
        ];
        sections.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });
    }

    updateExecutiveAlert(report) {
        const banner = document.getElementById('fraudRingAlertBanner');
        if (!banner) return;

        const totalRingsSpan = document.getElementById('totalFraudRings');
        const totalMembersSpan = document.getElementById('totalFraudMembers');

        if (totalRingsSpan) totalRingsSpan.textContent = report.total_rings_detected;

        // Calculate total unique members across all rings
        // Handle both formats: ring.members (fraud_rings) or ring.member_count (organized_fraud)
        let totalMembers = 0;
        if (report.rings && report.rings.length > 0) {
            if (report.rings[0].members) {
                // fraud_rings format: has members array
                const uniqueMembers = new Set();
                report.rings.forEach(ring => {
                    if (ring.members) {
                        ring.members.forEach(member => uniqueMembers.add(member));
                    }
                });
                totalMembers = uniqueMembers.size;
            } else {
                // organized_fraud format: use member_count
                totalMembers = report.rings.reduce((sum, ring) => sum + (ring.member_count || 0), 0);
            }
        }

        if (totalMembersSpan) totalMembersSpan.textContent = totalMembers;

        banner.style.display = 'block';
    }

    updateSummaryCards(report) {
        const section = document.getElementById('fraudRingSummarySection');
        if (!section) return;

        // Count rings by type (only for fraud_rings with ring_type, not for organized_fraud)
        const ringCounts = {
            'HIGH_VELOCITY': 0,
            'CROSS_BORDER': 0,
            'MERCHANT_CYCLING': 0,
            'TEMPORAL_CLUSTERING': 0,
            'HIGH_VALUE': 0
        };

        report.rings.forEach(ring => {
            const ringType = ring.ring_type;
            if (ringType && ringCounts.hasOwnProperty(ringType)) {
                ringCounts[ringType]++;
            }
        });

        // Update each card count
        const countElements = {
            'velocityRingCount': ringCounts.HIGH_VELOCITY,
            'crossBorderRingCount': ringCounts.CROSS_BORDER,
            'merchantCyclingRingCount': ringCounts.MERCHANT_CYCLING,
            'temporalRingCount': ringCounts.TEMPORAL_CLUSTERING,
            'highValueRingCount': ringCounts.HIGH_VALUE
        };

        Object.entries(countElements).forEach(([elementId, count]) => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = count;
                // Highlight if count > 0
                if (count > 0) {
                    element.style.color = 'var(--severity-critical)';
                    element.style.textShadow = '0 0 20px rgba(239, 68, 68, 0.5)';
                }
            }
        });

        // Only show summary section if we have ring_type data (fraud_rings, not organized_fraud)
        const hasRingTypes = report.rings.some(ring => ring.ring_type);
        if (hasRingTypes) {
            section.style.display = 'block';
        }
    }

    renderNetworkGraph(report) {
        const section = document.getElementById('networkVisualizationSection');
        const container = document.getElementById('networkGraph');
        if (!section || !container) return;

        // Check if vis.js is available
        if (typeof vis === 'undefined') {
            console.error('[Network Graph] vis.js library not loaded');
            container.innerHTML = '<p class="text-center text-gray-500">Network visualization library not available</p>';
            section.style.display = 'block';
            return;
        }

        // Clear container
        container.innerHTML = '';

        // Create nodes from rings
        const nodes = new vis.DataSet();
        const edges = new vis.DataSet();

        report.rings.forEach((ring, index) => {
            // Calculate node size based on member count
            const nodeSize = Math.sqrt(ring.member_count || 1) * 3 + 15;

            // Get ring label
            const label = ring.fake_name_pattern || ring.ring_name || ring.ring_type || `Ring ${index + 1}`;

            // Get ring amount (handle different field names)
            const amount = ring.total_fraud_amount || ring.total_amount || 0;
            const amountFormatted = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'EUR'
            }).format(amount);

            // Get calculated severity and color
            const severity = ring.calculated_severity || ring.severity || 'MEDIUM';
            const riskScore = ring.calculated_risk_score !== undefined ? ring.calculated_risk_score.toFixed(1) : '0';
            const nodeColor = this.getRiskColor(severity);

            // Lighter version for highlight
            const highlightColors = {
                '#DC2626': '#EF4444',  // CRITICAL: brighter red
                '#EA580C': '#F97316',  // HIGH: brighter orange
                '#CA8A04': '#EAB308',  // MEDIUM: brighter yellow
                '#16A34A': '#22C55E'   // LOW: brighter green
            };
            const highlightColor = highlightColors[nodeColor] || nodeColor;

            nodes.add({
                id: index,
                label: label,
                title: `${severity} (${riskScore}%)\n${ring.member_count || 0} members | ${amountFormatted}`,
                value: nodeSize,
                color: {
                    background: nodeColor,
                    border: nodeColor,
                    highlight: {
                        background: highlightColor,
                        border: highlightColor
                    }
                },
                font: {
                    color: '#FFFFFF',  // White text for visibility
                    size: 16,
                    face: 'Arial',
                    bold: { color: '#FFFFFF' },
                    strokeWidth: 3,
                    strokeColor: '#1B263B'  // Dark outline for visibility
                }
            });
        });

        // Create some edges between rings (for visualization)
        report.rings.forEach((ring1, i) => {
            report.rings.slice(i + 1).forEach((ring2, j) => {
                // Connect rings if they share similar patterns (simplified logic)
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

        // Network configuration (improved spacing and visibility)
        const options = {
            physics: {
                barnesHut: {
                    gravitationalConstant: -5000,  // More spread (was -3000)
                    centralGravity: 0.2,           // Less pull to center
                    springLength: 300,             // More distance (was 200)
                    springConstant: 0.02,          // Less rigid (was 0.04)
                    damping: 0.15                  // More damping for stability
                },
                stabilization: {
                    iterations: 250                 // More iterations for better layout
                }
            },
            nodes: {
                shape: 'dot',
                scaling: {
                    min: 25,                       // Larger minimum size
                    max: 70,                       // Larger maximum size
                    label: { enabled: true, min: 16, max: 24 }
                },
                font: {
                    color: '#FFFFFF',              // White text (overridden per node)
                    size: 18,                      // Larger font (was 14)
                    strokeWidth: 3                 // Outline for visibility
                },
                borderWidth: 3,                    // Thicker border
                borderWidthSelected: 4
            },
            edges: {
                width: 1,
                color: { inherit: false },
                smooth: {
                    type: 'continuous'
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                zoomView: true,
                dragView: true
            },
            layout: {
                improvedLayout: true,
                hierarchical: false
            }
        };

        // Create network
        const network = new vis.Network(container, { nodes, edges }, options);

        // Fit network to view after stabilization
        network.once('stabilizationIterationsDone', () => {
            network.fit({
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
        });

        section.style.display = 'block';
    }

    /**
     * Calculate weighted risk score for a fraud ring
     * Formula: (members × 0.3) + (amount × 0.4) + (transactions × 0.3)
     * Each factor is normalized to 0-100 scale
     * Returns score 0-100
     */
    calculateRiskScore(ring, allRings) {
        // Find maximum values across all rings for normalization
        const maxMembers = Math.max(...allRings.map(r => r.member_count || 0));
        const maxAmount = Math.max(...allRings.map(r => r.total_fraud_amount || 0));
        const maxTxns = Math.max(...allRings.map(r => r.fraudulent_orders || r.member_count || 0));

        // Normalize each factor to 0-100 scale
        const normMembers = maxMembers > 0 ? (ring.member_count || 0) / maxMembers * 100 : 0;
        const normAmount = maxAmount > 0 ? (ring.total_fraud_amount || 0) / maxAmount * 100 : 0;
        const normTxns = maxTxns > 0 ? (ring.fraudulent_orders || ring.member_count || 0) / maxTxns * 100 : 0;

        // Apply weighted formula
        const score = (normMembers * 0.3) + (normAmount * 0.4) + (normTxns * 0.3);

        console.log(`[Risk Score] ${ring.ring_name}: members=${normMembers.toFixed(1)}, amount=${normAmount.toFixed(1)}, txns=${normTxns.toFixed(1)} => ${score.toFixed(1)}`);

        return score;
    }

    /**
     * Convert risk score to severity level
     * 80-100: CRITICAL
     * 60-79: HIGH
     * 40-59: MEDIUM
     * 0-39: LOW
     */
    getRiskLevel(score) {
        if (score >= 80) return 'CRITICAL';
        if (score >= 60) return 'HIGH';
        if (score >= 40) return 'MEDIUM';
        return 'LOW';
    }

    /**
     * Get color for risk level
     */
    getRiskColor(severity) {
        const colors = {
            'CRITICAL': '#DC2626',  // Red
            'HIGH': '#EA580C',      // Orange
            'MEDIUM': '#CA8A04',    // Yellow
            'LOW': '#16A34A'        // Green
        };
        return colors[severity] || '#6B7280';
    }

    renderRingCards(report) {
        const section = document.getElementById('fraudRingDetailsSection');
        const container = document.getElementById('fraudRingCardsList');
        if (!section || !container) return;

        container.innerHTML = '';

        // Risk scores already calculated in displayFraudRings()
        // Sort rings by calculated risk score - highest first
        const sortedRings = [...report.rings].sort((a, b) =>
            (b.calculated_risk_score || 0) - (a.calculated_risk_score || 0)
        );

        sortedRings.forEach((ring, index) => {
            const card = this.createFraudRingCard(ring, index);
            container.appendChild(card);
        });

        section.style.display = 'block';
    }

    createFraudRingCard(ring, index) {
        // Use calculated severity if available, fallback to backend severity
        const severity = ring.calculated_severity || ring.severity;
        const riskScore = ring.calculated_risk_score !== undefined ? ring.calculated_risk_score : (ring.risk_score * 100);

        const card = document.createElement('div');
        card.className = `fraud-ring-card severity-${severity.toLowerCase()}`;
        card.id = `fraud-ring-${index}`;

        // Add entrance animation
        card.style.animation = `fadeIn 0.5s ease-out ${index * 0.1}s both`;

        // Severity emojis
        const severityEmoji = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        };

        // Format risk score as percentage
        const riskPercent = riskScore.toFixed(1);

        // Handle different field names (evidence vs key_indicators, sample_transactions vs sample_orders)
        const evidence = ring.evidence || ring.key_indicators || [];
        const sampleTransactions = ring.sample_transactions || ring.sample_orders || [];
        const members = ring.members || [];

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
                                <span class="text-gray-400">Risk: ${riskPercent}%</span>
                            </div>
                        </div>
                    </div>
                    <p class="text-gray-300 text-sm mb-3">${ring.explanation}</p>
                    <div class="text-sm text-gray-400">
                        <span class="font-semibold">Detection Method:</span> ${ring.detection_method}
                    </div>
                </div>
                <svg class="expand-icon w-6 h-6 ml-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
            </div>

            <!-- Expandable Details -->
            <div class="fraud-ring-details">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div class="dark-card" style="padding: 1rem;">
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">📊 Evidence</h4>
                        <div class="text-sm text-gray-400 space-y-1">
                            ${Array.isArray(evidence) ?
                                evidence.slice(0, 5).map(item => `<div>• ${item}</div>`).join('') :
                                Object.entries(evidence).slice(0, 5).map(([key, value]) => `
                                    <div><span class="font-semibold">${key}:</span> ${JSON.stringify(value).substring(0, 50)}</div>
                                `).join('')
                            }
                        </div>
                    </div>

                    <div class="dark-card" style="padding: 1rem;">
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">💡 Recommendations</h4>
                        <ul class="text-sm text-gray-400 space-y-1 list-disc list-inside">
                            ${ring.recommendations.slice(0, 3).map(rec => `
                                <li>${rec}</li>
                            `).join('')}
                        </ul>
                    </div>
                </div>

                ${members.length > 0 ? `
                    <div class="mb-4">
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">👥 Ring Members (${members.length})</h4>
                        <div class="flex flex-wrap gap-2">
                            ${members.slice(0, 20).map(member => `
                                <span class="member-chip">${member}</span>
                            `).join('')}
                            ${members.length > 20 ? `
                                <span class="member-chip" style="background: rgba(239, 68, 68, 0.2); border-color: var(--severity-critical);">
                                    +${members.length - 20} more
                                </span>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}

                ${sampleTransactions.length > 0 ? `
                    <div>
                        <h4 class="text-sm font-bold text-gray-300 mb-2 uppercase tracking-wide">🔍 Sample Transactions</h4>
                        <div class="dark-card" style="padding: 0; overflow: hidden;">
                            <table class="w-full text-sm dark-table">
                                <thead>
                                    <tr>
                                        <th class="px-3 py-2 text-left">Transaction ID</th>
                                        <th class="px-3 py-2 text-left">User</th>
                                        <th class="px-3 py-2 text-right">Amount</th>
                                        <th class="px-3 py-2 text-left">Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${sampleTransactions.slice(0, 5).map(txn => `
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

        // Add click to expand/collapse
        card.addEventListener('click', (e) => {
            if (window.getSelection().toString()) return;

            const wasExpanded = card.classList.contains('expanded');

            // Close other cards
            document.querySelectorAll('.fraud-ring-card.expanded').forEach(otherCard => {
                if (otherCard !== card) {
                    otherCard.classList.remove('expanded');
                }
            });

            card.classList.toggle('expanded');

            // Scroll to card if expanding
            if (!wasExpanded) {
                setTimeout(() => {
                    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            }
        });

        // Keyboard accessibility
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.click();
            }
        });

        return card;
    }

    generateAIRecommendations(report) {
        const section = document.getElementById('aiRecommendationsSection');
        const preventionList = document.getElementById('preventionTipsList');
        const detectionList = document.getElementById('detectionTipsList');

        if (!section || !preventionList || !detectionList) return;

        // Extract unique patterns from rings
        const fakeNamePatterns = new Set();
        const emailDomains = new Set();
        const countryCodes = new Set();
        let totalExposure = 0;
        let totalMembers = 0;

        report.rings.forEach(ring => {
            if (ring.fake_name_pattern) fakeNamePatterns.add(ring.fake_name_pattern);
            if (ring.total_fraud_amount) totalExposure += ring.total_fraud_amount;
            if (ring.member_count) totalMembers += ring.member_count;

            // Extract patterns from evidence/key_indicators
            const evidence = ring.evidence || ring.key_indicators || [];
            if (Array.isArray(evidence)) {
                evidence.forEach(item => {
                    if (typeof item === 'string') {
                        if (item.includes('@')) {
                            const domain = item.split('@')[1]?.split(' ')[0];
                            if (domain) emailDomains.add(domain);
                        }
                        if (item.includes('country') || item.includes('BIN_COUNTRY')) {
                            const match = item.match(/[A-Z]{2}/);
                            if (match) countryCodes.add(match[0]);
                        }
                    }
                });
            }
        });

        // Generate prevention tips
        const preventionTips = [];

        if (fakeNamePatterns.size > 0) {
            preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Block orders with gibberish billing names like: <strong class="text-indigo-600">${Array.from(fakeNamePatterns).slice(0, 3).join(', ')}</strong></span></li>`);
            preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Implement name validation rules to flag suspicious patterns (repeated characters, keyboard sequences)</span></li>`);
        }

        if (countryCodes.size > 0) {
            preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Cross-reference card country with IP country to detect mismatches</span></li>`);
            preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Flag high-risk country codes: <strong class="text-indigo-600">${Array.from(countryCodes).slice(0, 3).join(', ')}</strong></span></li>`);
        }

        if (totalMembers > 50) {
            preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Implement velocity checks: limit orders per user/card/IP per hour</span></li>`);
            preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Use device fingerprinting to detect multiple accounts from same device</span></li>`);
        }

        if (emailDomains.size > 0) {
            preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Monitor suspicious email domains for disposable/temporary email services</span></li>`);
        }

        preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Enable 3D Secure (3DS) authentication for high-risk transactions</span></li>`);
        preventionTips.push(`<li class="flex items-start gap-2"><span class="text-indigo-500 font-bold">•</span><span>Set up real-time alerts for suspicious order patterns</span></li>`);

        // Generate detection tips
        const detectionTips = [];

        detectionTips.push(`<li class="flex items-start gap-2"><span class="text-purple-500 font-bold">•</span><span>Look for patterns in <strong class="text-purple-600">BILLING_FIRST_NAME</strong> field - fraudsters often use gibberish</span></li>`);
        detectionTips.push(`<li class="flex items-start gap-2"><span class="text-purple-500 font-bold">•</span><span>Check <strong class="text-purple-600">BIN_COUNTRY_CODE</strong> vs <strong class="text-purple-600">IP country</strong> mismatches</span></li>`);
        detectionTips.push(`<li class="flex items-start gap-2"><span class="text-purple-500 font-bold">•</span><span>Monitor for multiple failed transactions followed by successful ones (card testing)</span></li>`);
        detectionTips.push(`<li class="flex items-start gap-2"><span class="text-purple-500 font-bold">•</span><span>Track unusual <strong class="text-purple-600">carrier/route patterns</strong> and shipping addresses</span></li>`);
        detectionTips.push(`<li class="flex items-start gap-2"><span class="text-purple-500 font-bold">•</span><span>Identify accounts created in rapid succession with similar details</span></li>`);
        detectionTips.push(`<li class="flex items-start gap-2"><span class="text-purple-500 font-bold">•</span><span>Flag orders with round amounts (e.g., $100.00, $50.00) - common in fraud</span></li>`);

        if (totalMembers > 100) {
            detectionTips.push(`<li class="flex items-start gap-2"><span class="text-purple-500 font-bold">•</span><span><strong class="text-red-600">⚠️ Large-scale attack detected!</strong> ${totalMembers} compromised accounts - escalate immediately</span></li>`);
        }

        // Update the DOM
        preventionList.innerHTML = preventionTips.slice(0, 6).join('');
        detectionList.innerHTML = detectionTips.slice(0, 6).join('');

        section.style.display = 'block';
    }
}

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

// File guidelines toggle
const guidelinesHeader = document.getElementById('guidelinesHeader');
const guidelinesContent = document.getElementById('guidelinesContent');
const guidelinesChevron = document.getElementById('guidelinesChevron');

if (guidelinesHeader && guidelinesContent && guidelinesChevron) {
    guidelinesHeader.addEventListener('click', () => {
        const isHidden = guidelinesContent.style.display === 'none';
        guidelinesContent.style.display = isHidden ? 'block' : 'none';
        guidelinesChevron.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    });
}

async function handleFile() {
    const file = fileInput.files[0];
    if (!file) return;

    errorMsg.style.display = 'none';
    uploadContent.style.display = 'none';
    uploadingContent.style.display = 'block';

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
        uploadContent.style.display = 'block';
        uploadingContent.style.display = 'none';
    }
}

function displayResults() {
    const data = analysisResults;

    // DEBUG: Log all fraud detection data
    console.log("=== FRAUD DETECTION DATA ===");
    console.log("Fraud Rings:", data.fraud_rings);
    console.log("Organized Fraud:", data.organized_fraud);
    console.log("Data-Driven Fraud Rings:", data.data_driven_fraud_rings);
    console.log("===========================");

    // Show results section
    document.getElementById('resultsSection').style.display = 'block';

    // FRAUD INTELLIGENCE DISPLAY (NEW!)
    try {
        displayFraudInsights(data.fraud_insights);
    } catch (error) {
        console.error('[ERROR] displayFraudInsights failed:', error);
    }

    // FRAUD RING VISUALIZATION (NEWEST!)
    if (data.fraud_rings && data.fraud_rings.total_rings_detected > 0) {
        const fraudRingVisualizer = new FraudRingVisualizer();
        fraudRingVisualizer.displayFraudRings(data.fraud_rings);
    }

    // DATA-DRIVEN FRAUD RINGS (NIGHT-TIME, VELOCITY, SHOPPING)
    if (data.data_driven_fraud_rings && data.data_driven_fraud_rings.total_rings_detected > 0) {
        const fraudRingVisualizer = new FraudRingVisualizer();
        fraudRingVisualizer.displayFraudRings(data.data_driven_fraud_rings);
    }

    // ORGANIZED FRAUD RINGS (FAKE IDENTITY, EMAIL, GEOGRAPHIC MISMATCH)
    console.log('[DEBUG] Checking organized_fraud:', data.organized_fraud);
    if (data.organized_fraud && data.organized_fraud.total_rings_detected > 0) {
        console.log('[DEBUG] Creating FraudRingVisualizer for organized_fraud with', data.organized_fraud.total_rings_detected, 'rings');
        const fraudRingVisualizer = new FraudRingVisualizer();
        console.log('[DEBUG] Calling displayFraudRings...');
        fraudRingVisualizer.displayFraudRings(data.organized_fraud);
        console.log('[DEBUG] displayFraudRings completed');
    } else {
        console.log('[DEBUG] NOT displaying organized_fraud - condition failed');
    }

    // LIVE INSIGHTS DASHBOARD (animated counters, gauges, progress rings)
    // IMPORTANT: Must be called AFTER fraud ring visualizers calculate risk scores!
    try {
        initLiveInsightsDashboard(data);
    } catch (error) {
        console.error('[ERROR] initLiveInsightsDashboard failed:', error);
    }
}

function displayFraudInsights(fraudInsights) {
    if (!fraudInsights || !fraudInsights.patterns) {
        return;
    }

    const fraudSection = document.getElementById('fraudInsightsSection');
    const alertBanner = document.getElementById('fraudAlertBanner');
    const fraudSummary = document.getElementById('fraudSummary');
    const fraudPatternsContainer = document.getElementById('fraudPatternsContainer');
    const fraudPatternsList = document.getElementById('fraudPatternsList');

    if (!fraudSection) return; // Exit if section doesn't exist

    // Show fraud insights section
    fraudSection.style.display = 'block';

    const totalPatterns = fraudInsights.total_patterns || 0;
    const highCount = fraudInsights.high_severity_count || 0;
    const mediumCount = fraudInsights.medium_severity_count || 0;
    const lowCount = fraudInsights.low_severity_count || 0;

    if (totalPatterns === 0) {
        // No fraud detected - hide all fraud insight elements
        if (alertBanner) alertBanner.style.display = 'none';
        if (fraudSummary) fraudSummary.style.display = 'none';
        if (fraudPatternsContainer) fraudPatternsContainer.style.display = 'none';
        return;
    }

    // Fraud patterns detected
    // Show alert banner if high severity patterns exist
    if (highCount > 0 && alertBanner) {
        alertBanner.style.display = 'block';
        const highSevCount = document.getElementById('highSeverityCount');
        if (highSevCount) highSevCount.textContent = highCount;
    } else if (alertBanner) {
        alertBanner.style.display = 'none';
    }

    // Show summary
    if (fraudSummary) {
        fraudSummary.style.display = 'block';
        const highEl = document.getElementById('fraudHighCount');
        const mediumEl = document.getElementById('fraudMediumCount');
        const lowEl = document.getElementById('fraudLowCount');
        const totalEl = document.getElementById('fraudTotalCount');
        if (highEl) highEl.textContent = highCount;
        if (mediumEl) mediumEl.textContent = mediumCount;
        if (lowEl) lowEl.textContent = lowCount;
        if (totalEl) totalEl.textContent = totalPatterns;
    }

    // Display pattern cards
    if (fraudPatternsContainer) fraudPatternsContainer.style.display = 'block';
    if (fraudPatternsList) fraudPatternsList.innerHTML = '';

    // Sort patterns by severity (HIGH -> MEDIUM -> LOW)
    if (fraudPatternsList) {
        const severityOrder = { 'HIGH': 0, 'MEDIUM': 1, 'LOW': 2 };
        const sortedPatterns = [...fraudInsights.patterns].sort((a, b) =>
            severityOrder[a.severity] - severityOrder[b.severity]
        );

        sortedPatterns.forEach((pattern, index) => {
            const card = createFraudPatternCard(pattern, index);
            fraudPatternsList.appendChild(card);
        });
    }
}

// ============================================================================
// LIVE INSIGHTS DASHBOARD FUNCTIONS
// ============================================================================

function initLiveInsightsDashboard(data) {
    console.log('[DEBUG] initLiveInsightsDashboard called');
    const dashboard = document.getElementById('liveInsightsDashboard');
    if (!dashboard || !data.organized_fraud) {
        console.log('[DEBUG] Dashboard element or organized_fraud not found');
        return;
    }

    const organizedFraud = data.organized_fraud;
    if (!organizedFraud.rings || organizedFraud.total_rings_detected === 0) {
        console.log('[DEBUG] No rings detected');
        return;
    }

    // Show dashboard
    dashboard.style.display = 'block';

    // Calculate metrics
    const totalRings = organizedFraud.total_rings_detected || 0;
    const totalAmount = organizedFraud.total_fraud_amount || 0;
    const totalMembers = organizedFraud.total_fraudulent_orders || 0;

    console.log('[DEBUG] Dashboard metrics:', { totalRings, totalAmount, totalMembers });

    // Count severity distribution
    const severityCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    organizedFraud.rings.forEach((ring, index) => {
        const severity = ring.calculated_severity || ring.severity || 'MEDIUM';
        const riskScore = ring.calculated_risk_score || 0;
        console.log(`[DEBUG] Ring ${index + 1}: severity=${severity}, risk_score=${riskScore.toFixed(1)}%, name=${ring.ring_name || ring.shared_value}`);
        severityCounts[severity] = (severityCounts[severity] || 0) + 1;
    });

    console.log('[DEBUG] Severity distribution:', severityCounts);

    // Calculate overall risk (average of all ring risk scores)
    let totalRiskScore = 0;
    organizedFraud.rings.forEach(ring => {
        totalRiskScore += ring.calculated_risk_score || 0;
    });
    const averageRiskScore = totalRings > 0 ? totalRiskScore / totalRings : 0;
    console.log('[DEBUG] Average risk score:', averageRiskScore.toFixed(1) + '%');

    // Animate counters
    setTimeout(() => animateCounter('counterFraudRings', totalRings, 0, ''), 300);
    setTimeout(() => animateCounter('counterFraudAmount', totalAmount, 0, '€'), 500);
    setTimeout(() => animateCounter('counterFraudMembers', totalMembers, 0, ''), 700);

    // Animate gauge
    setTimeout(() => animateGauge(averageRiskScore), 900);

    // Animate progress rings
    setTimeout(() => animateProgressRing('ringCritical', 'ringCriticalValue', severityCounts.CRITICAL, totalRings), 1100);
    setTimeout(() => animateProgressRing('ringHigh', 'ringHighValue', severityCounts.HIGH, totalRings), 1200);
    setTimeout(() => animateProgressRing('ringMedium', 'ringMediumValue', severityCounts.MEDIUM, totalRings), 1300);
    setTimeout(() => animateProgressRing('ringLow', 'ringLowValue', severityCounts.LOW, totalRings), 1400);
}

function animateCounter(elementId, targetValue, startValue, prefix) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const duration = 2000; // 2 seconds
    const startTime = performance.now();
    const isAmount = prefix === '€';

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function (easeOutCubic)
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const currentValue = startValue + (targetValue - startValue) * easeProgress;

        if (isAmount) {
            element.textContent = prefix + currentValue.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        } else {
            element.textContent = Math.floor(currentValue).toLocaleString();
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            // Final value
            if (isAmount) {
                element.textContent = prefix + targetValue.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            } else {
                element.textContent = targetValue.toLocaleString();
            }
        }
    }

    requestAnimationFrame(update);
}

function animateGauge(riskScore) {
    const gaugeForeground = document.getElementById('gaugeForeground');
    const gaugeValue = document.getElementById('gaugeValue');
    const gaugeLabel = document.getElementById('gaugeLabel');

    if (!gaugeForeground || !gaugeValue || !gaugeLabel) return;

    // Normalize risk score to 0-100
    const normalizedScore = Math.min(Math.max(riskScore, 0), 100);

    // Calculate arc length (semicircle circumference = π * radius = π * 100 ≈ 314)
    const totalLength = 314;
    const offset = totalLength - (normalizedScore / 100) * totalLength;

    // Determine color and label based on score
    let color, label;
    if (normalizedScore >= 80) {
        color = '#DC2626'; // CRITICAL - Red
        label = 'CRITICAL';
    } else if (normalizedScore >= 60) {
        color = '#EA580C'; // HIGH - Orange
        label = 'HIGH';
    } else if (normalizedScore >= 40) {
        color = '#CA8A04'; // MEDIUM - Yellow
        label = 'MEDIUM';
    } else {
        color = '#16A34A'; // LOW - Green
        label = 'LOW';
    }

    // Animate gauge
    gaugeForeground.style.strokeDashoffset = offset;
    gaugeForeground.style.stroke = color;
    gaugeValue.textContent = normalizedScore.toFixed(1) + '%';
    gaugeLabel.textContent = label;
}

function animateProgressRing(ringId, valueId, count, total) {
    const ring = document.getElementById(ringId);
    const valueElement = document.getElementById(valueId);

    if (!ring || !valueElement) return;

    const percentage = total > 0 ? (count / total) * 100 : 0;
    const circumference = 2 * Math.PI * 50; // r=50
    const offset = circumference - (percentage / 100) * circumference;

    ring.style.strokeDashoffset = offset;
    valueElement.textContent = count;
}

function createFraudPatternCard(pattern, index) {
    const card = document.createElement('div');
    card.className = `fraud-pattern-card severity-${pattern.severity.toLowerCase()}`;
    card.id = `pattern-${index}`;

    // Add entrance animation with stagger
    card.style.animation = `fadeIn 0.5s ease-out ${index * 0.1}s both`;

    // Severity icon
    const severityEmoji = {
        'HIGH': '🚨',
        'MEDIUM': '⚠️',
        'LOW': 'ℹ️'
    };

    // Truncate explanation for preview
    const shortExplanation = pattern.explanation.length > 200
        ? pattern.explanation.substring(0, 200) + '...'
        : pattern.explanation;

    card.innerHTML = `
        <div class="flex items-start gap-4">
            <div class="severity-icon ${pattern.severity.toLowerCase()}">
                ${severityEmoji[pattern.severity]}
            </div>
            <div class="flex-1">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-lg font-bold text-gray-800">${pattern.title}</h3>
                    <div class="flex items-center gap-2">
                        <span class="badge badge-${pattern.severity.toLowerCase()}">${pattern.severity}</span>
                        <svg class="expand-icon w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                    </div>
                </div>
                <p class="text-gray-700 text-sm mb-2">${shortExplanation}</p>
                <div class="text-sm text-gray-600">
                    <span class="font-semibold">Affected:</span> ${pattern.affected_count} ${pattern.affected_count === 1 ? 'entity' : 'entities'}
                </div>

                <!-- Expandable Details -->
                <div class="fraud-pattern-details">
                    <div class="bg-gray-50 p-4 rounded-lg mb-3">
                        <h4 class="font-semibold text-gray-800 mb-2">📋 Full Explanation</h4>
                        <p class="text-gray-700 text-sm">${pattern.explanation}</p>
                    </div>

                    <div class="mb-3">
                        <h4 class="font-semibold text-gray-800 mb-2">🎯 Affected Entities</h4>
                        <div class="flex flex-wrap gap-1">
                            ${pattern.affected_entities.slice(0, 10).map(entity =>
                                `<span class="entity-chip">${entity}</span>`
                            ).join('')}
                            ${pattern.affected_entities.length > 10 ?
                                `<span class="entity-chip">+${pattern.affected_entities.length - 10} more</span>` : ''}
                        </div>
                    </div>

                    ${pattern.sample_transactions && pattern.sample_transactions.length > 0 ? `
                        <div>
                            <h4 class="font-semibold text-gray-800 mb-2">🔍 Sample Transactions</h4>
                            <div class="bg-white border border-gray-200 rounded-lg overflow-hidden">
                                <table class="w-full text-sm">
                                    <thead class="bg-gray-50">
                                        <tr>
                                            <th class="px-3 py-2 text-left text-gray-600">ID</th>
                                            <th class="px-3 py-2 text-left text-gray-600">Amount</th>
                                            <th class="px-3 py-2 text-left text-gray-600">Details</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${pattern.sample_transactions.slice(0, 3).map(txn => `
                                            <tr class="border-t">
                                                <td class="px-3 py-2 font-mono text-xs">${txn.transaction_id || 'N/A'}</td>
                                                <td class="px-3 py-2">$${(txn.amount || 0).toFixed(2)}</td>
                                                <td class="px-3 py-2 text-gray-600">
                                                    ${txn.user_id ? `User: ${txn.user_id}` : ''}
                                                    ${txn.merchant_id ? ` | Merchant: ${txn.merchant_id}` : ''}
                                                    ${txn.country ? ` | ${txn.country}` : ''}
                                                </td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ` : ''}

                    ${pattern.metadata && Object.keys(pattern.metadata).length > 0 ? `
                        <div class="mt-3 text-xs text-gray-500">
                            <strong>Metadata:</strong> ${JSON.stringify(pattern.metadata, null, 2).substring(0, 100)}...
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;

    // Add click to expand/collapse with smooth animation
    card.addEventListener('click', (e) => {
        // Prevent text selection from toggling
        if (window.getSelection().toString()) return;

        const wasExpanded = card.classList.contains('expanded');

        // Close all other cards for cleaner UX
        document.querySelectorAll('.fraud-pattern-card.expanded').forEach(otherCard => {
            if (otherCard !== card) {
                otherCard.classList.remove('expanded');
            }
        });

        // Toggle this card
        card.classList.toggle('expanded');

        // Smooth scroll to card if expanding
        if (!wasExpanded) {
            setTimeout(() => {
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        }
    });

    // Add keyboard accessibility
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.setAttribute('aria-expanded', 'false');

    card.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            card.click();
        }
    });

    // Update aria-expanded when card state changes
    const observer = new MutationObserver(() => {
        card.setAttribute('aria-expanded', card.classList.contains('expanded'));
    });
    observer.observe(card, { attributes: true, attributeFilter: ['class'] });

    return card;
}

clearBtn.addEventListener('click', () => {
    fileInput.value = '';
    resultsSection.style.display = 'none';
    uploadContent.style.display = 'block';
    uploadingContent.style.display = 'none';
    errorMsg.style.display = 'none';
    analysisResults = null;
    if (riskChart) riskChart.destroy();

    // Clear fraud insights
    document.getElementById('fraudInsightsSection').style.display = 'none';
    document.getElementById('fraudAlertBanner').style.display = 'none';
    document.getElementById('noFraudBanner').style.display = 'none';
    document.getElementById('fraudSummary').style.display = 'none';
    document.getElementById('fraudPatternsContainer').style.display = 'none';
});

downloadBtn.addEventListener('click', async () => {
    if (!analysisResults) return;

    // Add download animation
    downloadBtn.classList.add('downloading');
    setTimeout(() => downloadBtn.classList.remove('downloading'), 600);

    try {
        await generateWordReport(analysisResults);

        // Show success feedback
        const originalText = downloadBtn.textContent;
        downloadBtn.textContent = '✓ Report Downloaded';
        setTimeout(() => {
            downloadBtn.textContent = originalText;
        }, 2000);
    } catch (error) {
        console.error('[ERROR] Failed to generate Word report:', error);
        alert('Failed to generate report. Please try again.');
    }
});

function showError(message) {
    errorMsg.style.display = 'block';
    errorMsg.style.animation = 'fadeIn 0.3s ease-out';
    errorText.textContent = message;

    // Smooth scroll to error
    errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ============================================================================
// ANIMATED NETWORK BACKGROUND
// ============================================================================

function initNetworkBackground() {
    const canvas = document.getElementById('networkBackground');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Network nodes
    const nodes = [];
    const nodeCount = 20;
    const connectionDistance = 150;

    // Create nodes
    for (let i = 0; i < nodeCount; i++) {
        nodes.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            radius: Math.random() * 2 + 1
        });
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Update and draw nodes
        nodes.forEach((node, i) => {
            // Move nodes
            node.x += node.vx;
            node.y += node.vy;

            // Bounce off edges
            if (node.x < 0 || node.x > canvas.width) node.vx *= -1;
            if (node.y < 0 || node.y > canvas.height) node.vy *= -1;

            // Draw node
            ctx.fillStyle = 'rgba(147, 197, 253, 0.6)'; // Light blue
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
            ctx.fill();

            // Draw connections
            nodes.forEach((otherNode, j) => {
                if (i === j) return;

                const dx = node.x - otherNode.x;
                const dy = node.y - otherNode.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < connectionDistance) {
                    const opacity = (1 - distance / connectionDistance) * 0.3;
                    ctx.strokeStyle = `rgba(147, 197, 253, ${opacity})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(node.x, node.y);
                    ctx.lineTo(otherNode.x, otherNode.y);
                    ctx.stroke();
                }
            });
        });

        requestAnimationFrame(animate);
    }

    animate();

    // Handle window resize
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

// ============================================================================
// WORD REPORT GENERATION (Executive Summary)
// ============================================================================

async function generateWordReport(data) {
    const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle } = docx;

    // Extract fraud data
    const organizedFraud = data.organized_fraud || {};
    const rings = organizedFraud.rings || [];
    const totalRings = organizedFraud.total_rings_detected || 0;
    const totalAmount = organizedFraud.total_fraud_amount || 0;
    const totalMembers = organizedFraud.total_fraudulent_orders || 0;

    // Calculate overall risk level
    let totalRiskScore = 0;
    rings.forEach(ring => {
        totalRiskScore += ring.calculated_risk_score || 0;
    });
    const averageRiskScore = totalRings > 0 ? totalRiskScore / totalRings : 0;

    let overallRiskLevel = 'LOW';
    if (averageRiskScore >= 80) overallRiskLevel = 'CRITICAL';
    else if (averageRiskScore >= 60) overallRiskLevel = 'HIGH';
    else if (averageRiskScore >= 40) overallRiskLevel = 'MEDIUM';

    // Current date
    const currentDate = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Build document sections
    const sections = [];

    // ========================================================================
    // TITLE PAGE
    // ========================================================================
    sections.push(
        new Paragraph({
            text: "FRAUD RING DETECTION REPORT",
            heading: HeadingLevel.TITLE,
            alignment: AlignmentType.CENTER,
            spacing: { before: 400, after: 200 }
        }),
        new Paragraph({
            text: "Executive Summary",
            heading: HeadingLevel.HEADING_1,
            alignment: AlignmentType.CENTER,
            spacing: { after: 100 }
        }),
        new Paragraph({
            text: `Generated: ${currentDate}`,
            alignment: AlignmentType.CENTER,
            spacing: { after: 400 }
        }),
        new Paragraph({ text: "" }) // Spacer
    );

    // ========================================================================
    // EXECUTIVE OVERVIEW
    // ========================================================================
    sections.push(
        new Paragraph({
            text: "EXECUTIVE OVERVIEW",
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 400, after: 200 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "• ", bold: true }),
                new TextRun({ text: `${totalRings} fraud rings detected`, bold: true })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "• ", bold: true }),
                new TextRun({ text: `Total fraud exposure: `, bold: true }),
                new TextRun({
                    text: `€${totalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    bold: true,
                    color: "DC2626"
                })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "• ", bold: true }),
                new TextRun({ text: `${totalMembers} fraudulent transactions identified`, bold: true })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "• ", bold: true }),
                new TextRun({ text: "Risk Level: ", bold: true }),
                new TextRun({
                    text: overallRiskLevel,
                    bold: true,
                    color: overallRiskLevel === 'CRITICAL' ? "DC2626" :
                           overallRiskLevel === 'HIGH' ? "EA580C" :
                           overallRiskLevel === 'MEDIUM' ? "CA8A04" : "16A34A"
                })
            ],
            spacing: { after: 300 }
        }),
        new Paragraph({ text: "" }) // Spacer
    );

    // ========================================================================
    // KEY FINDINGS
    // ========================================================================
    sections.push(
        new Paragraph({
            text: "KEY FINDINGS",
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 400, after: 200 }
        })
    );

    // Sort rings by risk score (highest first)
    const sortedRings = [...rings].sort((a, b) =>
        (b.calculated_risk_score || 0) - (a.calculated_risk_score || 0)
    );

    sortedRings.forEach((ring, index) => {
        const ringName = ring.ring_name || ring.shared_value || `Ring ${index + 1}`;
        const severity = ring.calculated_severity || ring.severity || 'MEDIUM';
        const memberCount = ring.member_count || 0;
        const fraudAmount = ring.total_fraud_amount || 0;
        const pattern = ring.detection_pattern || ring.pattern_type || 'Unknown pattern';
        const riskScore = ring.calculated_risk_score || 0;

        // Ring heading
        sections.push(
            new Paragraph({
                children: [
                    new TextRun({ text: `${index + 1}. "${ringName}" Ring - `, bold: true, size: 24 }),
                    new TextRun({
                        text: `${severity} RISK`,
                        bold: true,
                        size: 24,
                        color: severity === 'CRITICAL' ? "DC2626" :
                               severity === 'HIGH' ? "EA580C" :
                               severity === 'MEDIUM' ? "CA8A04" : "16A34A"
                    })
                ],
                spacing: { before: 300, after: 100 }
            })
        );

        // Ring details
        sections.push(
            new Paragraph({
                children: [
                    new TextRun({ text: "   • ", bold: true }),
                    new TextRun({ text: `${memberCount} members, ` }),
                    new TextRun({
                        text: `€${fraudAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} exposure`,
                        color: "DC2626"
                    })
                ],
                spacing: { after: 50 }
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "   • ", bold: true }),
                    new TextRun({ text: "Pattern: " }),
                    new TextRun({ text: pattern, italics: true })
                ],
                spacing: { after: 50 }
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "   • ", bold: true }),
                    new TextRun({ text: "Risk Score: " }),
                    new TextRun({
                        text: `${riskScore.toFixed(1)}%`,
                        bold: true,
                        color: severity === 'CRITICAL' ? "DC2626" :
                               severity === 'HIGH' ? "EA580C" : "CA8A04"
                    })
                ],
                spacing: { after: 50 }
            })
        );

        // Recommendation
        let recommendation = "Monitor closely";
        if (severity === 'CRITICAL') {
            recommendation = "Block immediately and investigate all related accounts";
        } else if (severity === 'HIGH') {
            recommendation = "Flag for manual review and restrict high-value transactions";
        } else if (severity === 'MEDIUM') {
            recommendation = "Monitor and apply additional verification";
        }

        sections.push(
            new Paragraph({
                children: [
                    new TextRun({ text: "   • ", bold: true }),
                    new TextRun({ text: "Recommendation: ", bold: true }),
                    new TextRun({ text: recommendation })
                ],
                spacing: { after: 200 }
            })
        );
    });

    // ========================================================================
    // RECOMMENDED ACTIONS
    // ========================================================================
    sections.push(
        new Paragraph({ text: "" }), // Spacer
        new Paragraph({
            text: "RECOMMENDED ACTIONS",
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 400, after: 200 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "1. ", bold: true }),
                new TextRun({ text: "Immediate Actions", bold: true })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            text: "   • Block all accounts identified in CRITICAL risk rings",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Freeze pending transactions from HIGH risk ring members",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Initiate manual review for all flagged patterns",
            spacing: { after: 200 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "2. ", bold: true }),
                new TextRun({ text: "Short-Term Improvements (1-2 weeks)", bold: true })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            text: "   • Implement velocity monitoring for rapid transaction sequences",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Add validation for gibberish or fake billing names",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Deploy card country vs IP country mismatch detection",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Enhance email domain validation rules",
            spacing: { after: 200 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "3. ", bold: true }),
                new TextRun({ text: "Long-Term Strategy (1-3 months)", bold: true })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            text: "   • Implement device fingerprinting for better user identification",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Deploy machine learning models for real-time fraud scoring",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Establish automated fraud ring detection pipeline",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Build merchant risk profiling system",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Create cross-border transaction monitoring dashboard",
            spacing: { after: 200 }
        })
    );

    // ========================================================================
    // TECHNICAL DETAILS
    // ========================================================================
    sections.push(
        new Paragraph({ text: "" }), // Spacer
        new Paragraph({
            text: "TECHNICAL DETAILS",
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 400, after: 200 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "Detection Methods:", bold: true })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            text: "   • Advanced fraud detection engine with multi-dimensional analysis",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Network graph analysis for fraud ring identification",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Pattern recognition for fake identities and geographic mismatches",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • Weighted risk scoring algorithm (members×0.3 + amount×0.4 + transactions×0.3)",
            spacing: { after: 200 }
        }),
        new Paragraph({
            children: [
                new TextRun({ text: "Risk Level Classification:", bold: true })
            ],
            spacing: { after: 100 }
        }),
        new Paragraph({
            text: "   • CRITICAL: Risk score 80-100% - Immediate action required",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • HIGH: Risk score 60-79% - Priority investigation needed",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • MEDIUM: Risk score 40-59% - Enhanced monitoring recommended",
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "   • LOW: Risk score 0-39% - Standard monitoring sufficient",
            spacing: { after: 200 }
        })
    );

    // ========================================================================
    // FOOTER
    // ========================================================================
    sections.push(
        new Paragraph({ text: "" }), // Spacer
        new Paragraph({ text: "" }), // Spacer
        new Paragraph({
            text: "─────────────────────────────────────────────────────────────────",
            alignment: AlignmentType.CENTER,
            spacing: { before: 400, after: 100 }
        }),
        new Paragraph({
            text: "This report is confidential and intended for authorized personnel only.",
            alignment: AlignmentType.CENTER,
            italics: true,
            spacing: { after: 50 }
        }),
        new Paragraph({
            text: "Generated by Advanced Fraud Ring Detection System",
            alignment: AlignmentType.CENTER,
            italics: true
        })
    );

    // ========================================================================
    // CREATE DOCUMENT
    // ========================================================================
    const doc = new Document({
        sections: [{
            properties: {},
            children: sections
        }]
    });

    // Generate and download
    const blob = await Packer.toBlob(doc);
    const fileName = `fraud-detection-report-${new Date().toISOString().slice(0, 10)}.docx`;
    saveAs(blob, fileName);
}

// Page load animation
document.addEventListener('DOMContentLoaded', () => {
    // Initialize network background
    initNetworkBackground();

    // Add fade-in animation to main sections
    const sections = document.querySelectorAll('nav, .max-w-7xl > div');
    sections.forEach((section, index) => {
        section.style.opacity = '0';
        section.style.animation = `fadeIn 0.6s ease-out ${index * 0.1}s forwards`;
    });

    // Add hover effect sound feedback (visual only, no actual sound)
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', () => {
            button.style.transition = 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)';
        });
    });
});
