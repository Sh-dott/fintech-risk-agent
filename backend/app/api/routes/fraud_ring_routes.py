"""
Fraud Ring Detection API Routes
=================================

Advanced fraud ring detection endpoints using:
- Graph-based community detection (Louvain)
- HDBSCAN density clustering
- Behavioral pattern analysis
- Velocity checks
- Entity resolution

Provides comprehensive fraud ring intelligence for fintech risk management.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from datetime import datetime

from backend.app.services.analytics.fraud_ring_detector import AdvancedFraudRingDetector
from backend.app.services.analytics.clustering_detector import HDBSCANFraudDetector
from backend.app.services.analytics.advanced_fraud_detection import AdvancedFraudDetectionEngine


router = APIRouter(prefix="/fraud-rings", tags=["Fraud Ring Detection"])


@router.post("/detect")
async def detect_fraud_rings(transactions: List[Dict[str, Any]]):
    """
    Comprehensive fraud ring detection using multiple advanced techniques.

    Analyzes transaction data to identify:
    - Organized fraud rings (shared devices, IPs, behavioral patterns)
    - Money mule networks
    - Card testing rings
    - Account takeover rings
    - Coordinated synthetic identity fraud

    Args:
        transactions: List of transaction dictionaries with fields:
            - transaction_id, user_id, amount, timestamp
            - device_id, ip_address, merchant_id (optional but recommended)
            - country, currency (optional)

    Returns:
        Comprehensive fraud ring detection report with:
        - Detected fraud rings with members and risk scores
        - Detection methods and evidence
        - Velocity violations
        - Behavioral anomalies
        - Actionable recommendations
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        # Initialize detectors
        graph_detector = AdvancedFraudRingDetector()
        cluster_detector = HDBSCANFraudDetector(min_cluster_size=2, min_samples=2)

        # Load data
        graph_detector.load_transactions(transactions)
        cluster_detector.load_transactions(transactions)

        # Run detection
        graph_report = graph_detector.detect_all()
        cluster_report = cluster_detector.get_report()

        # Run clustering
        cluster_detector.detect_clusters()
        cluster_report = cluster_detector.get_report()

        # Combine results
        combined_report = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "total_transactions_analyzed": len(transactions),
            "detection_methods": [
                "Graph-based Community Detection (Louvain)",
                "HDBSCAN Density Clustering",
                "Shared Resource Analysis",
                "Velocity Pattern Detection",
                "Behavioral Analytics"
            ],

            # Graph-based detection results
            "graph_detection": {
                "total_rings_detected": graph_report['total_fraud_rings_detected'],
                "fraud_rings": graph_report['fraud_rings'],
                "velocity_violations": graph_report['velocity_violations'],
                "suspicious_patterns": graph_report['suspicious_patterns'],
                "summary": graph_report['summary']
            },

            # Clustering-based detection results
            "cluster_detection": {
                "total_clusters_detected": cluster_report['total_clusters_detected'],
                "clusters": cluster_report['clusters'],
                "summary": cluster_report['summary']
            },

            # Overall summary
            "overall_summary": {
                "total_fraud_rings_detected": (
                    graph_report['total_fraud_rings_detected'] +
                    cluster_report['total_clusters_detected']
                ),
                "critical_threats": (
                    graph_report['summary']['critical_rings'] +
                    cluster_report['summary']['high_risk_clusters']
                ),
                "high_risk_threats": (
                    graph_report['summary']['high_risk_rings'] +
                    cluster_report['summary']['medium_risk_clusters']
                ),
                "velocity_violations": len(graph_report['velocity_violations']),
                "temporal_anomalies": len(graph_report['suspicious_patterns']),
                "unique_users_in_rings": graph_report['summary']['total_users_in_rings']
            },

            # Actionable recommendations
            "recommendations": graph_report['recommendations'],

            # Alert level
            "alert_level": _determine_alert_level(graph_report, cluster_report)
        }

        return combined_report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fraud ring detection failed: {str(e)}")


@router.post("/detect-advanced")
async def detect_fraud_rings_advanced(
    transactions: List[Dict[str, Any]],
    include_ml_detection: bool = True,
    include_network_analysis: bool = True,
    include_behavioral_analysis: bool = True
):
    """
    Advanced fraud ring detection with configurable analysis modules.

    Allows selective enabling of detection techniques based on requirements.

    Args:
        transactions: Transaction data
        include_ml_detection: Enable ML-based anomaly detection
        include_network_analysis: Enable graph network analysis
        include_behavioral_analysis: Enable behavioral pattern detection

    Returns:
        Detailed fraud ring detection report
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        results = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_modules": []
        }

        # Graph/Network Analysis
        if include_network_analysis:
            detector = AdvancedFraudRingDetector()
            detector.load_transactions(transactions)
            network_results = detector.detect_all()
            results["network_analysis"] = network_results
            results["analysis_modules"].append("Network Graph Analysis")

        # ML-Based Detection
        if include_ml_detection:
            ml_detector = AdvancedFraudDetectionEngine()
            ml_detector.load_transactions(transactions)

            # Run ML detections
            ml_detector.detect_anomalies()
            ml_detector.detect_fraud_networks()
            ml_detector.detect_money_laundering_patterns()
            ml_detector.calculate_comprehensive_risk_scores()

            ml_report = ml_detector.generate_comprehensive_report()
            results["ml_analysis"] = ml_report
            results["analysis_modules"].append("ML Anomaly Detection")

        # Behavioral/Clustering Analysis
        if include_behavioral_analysis:
            cluster_detector = HDBSCANFraudDetector()
            cluster_detector.load_transactions(transactions)
            cluster_detector.detect_clusters()
            cluster_results = cluster_detector.get_report()
            results["behavioral_clustering"] = cluster_results
            results["analysis_modules"].append("Behavioral Clustering")

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advanced detection failed: {str(e)}")


@router.post("/quick-scan")
async def quick_fraud_scan(transactions: List[Dict[str, Any]]):
    """
    Quick fraud ring scan for real-time applications.

    Performs lightweight detection focusing on:
    - Shared devices/IPs
    - Velocity violations
    - High-risk behavioral signals

    Returns:
        Quick scan results with immediate actionable insights
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        import pandas as pd

        df = pd.DataFrame(transactions)

        quick_results = {
            "status": "success",
            "scan_type": "quick_scan",
            "timestamp": datetime.utcnow().isoformat(),
            "transactions_scanned": len(transactions),
            "alerts": []
        }

        # Quick device sharing check
        if 'device_id' in df.columns and 'user_id' in df.columns:
            device_sharing = df.groupby('device_id')['user_id'].nunique()
            shared_devices = device_sharing[device_sharing > 1]

            if len(shared_devices) > 0:
                quick_results["alerts"].append({
                    "type": "DEVICE_SHARING",
                    "severity": "HIGH",
                    "message": f"{len(shared_devices)} shared devices detected",
                    "details": {
                        "device_count": len(shared_devices),
                        "max_users_per_device": int(shared_devices.max())
                    }
                })

        # Quick IP sharing check
        if 'ip_address' in df.columns and 'user_id' in df.columns:
            ip_sharing = df.groupby('ip_address')['user_id'].nunique()
            shared_ips = ip_sharing[ip_sharing > 2]  # More lenient for IPs

            if len(shared_ips) > 0:
                quick_results["alerts"].append({
                    "type": "IP_SHARING",
                    "severity": "MEDIUM",
                    "message": f"{len(shared_ips)} shared IPs detected",
                    "details": {
                        "ip_count": len(shared_ips),
                        "max_users_per_ip": int(shared_ips.max())
                    }
                })

        # Quick velocity check
        if 'user_id' in df.columns:
            user_counts = df['user_id'].value_counts()
            high_velocity = user_counts[user_counts >= 4]

            if len(high_velocity) > 0:
                quick_results["alerts"].append({
                    "type": "HIGH_VELOCITY",
                    "severity": "HIGH",
                    "message": f"{len(high_velocity)} high-velocity users detected",
                    "details": {
                        "user_count": len(high_velocity),
                        "max_transactions": int(high_velocity.max())
                    }
                })

        # Temporal clustering check
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            if df['timestamp'].notna().any():
                hours = df['timestamp'].dt.hour
                hour_dist = hours.value_counts()
                max_hour_pct = (hour_dist.max() / len(df)) * 100

                if max_hour_pct > 70:
                    quick_results["alerts"].append({
                        "type": "TEMPORAL_CLUSTERING",
                        "severity": "MEDIUM",
                        "message": f"{max_hour_pct:.0f}% of transactions at same hour",
                        "details": {
                            "dominant_hour": int(hour_dist.idxmax()),
                            "concentration_pct": float(max_hour_pct)
                        }
                    })

        # Overall risk assessment
        alert_count = len(quick_results["alerts"])
        high_severity = len([a for a in quick_results["alerts"] if a["severity"] == "HIGH"])

        quick_results["risk_assessment"] = {
            "total_alerts": alert_count,
            "high_severity_alerts": high_severity,
            "risk_level": "CRITICAL" if high_severity >= 2 else "HIGH" if high_severity == 1 or alert_count >= 3 else "MEDIUM" if alert_count > 0 else "LOW",
            "recommendation": _get_quick_recommendation(alert_count, high_severity)
        }

        return quick_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick scan failed: {str(e)}")


@router.get("/health")
async def fraud_ring_detection_health():
    """Health check for fraud ring detection service."""
    return {
        "status": "healthy",
        "service": "Fraud Ring Detection",
        "available_detectors": [
            "Graph-based Community Detection",
            "HDBSCAN Clustering",
            "Velocity Analysis",
            "Behavioral Analytics"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


def _determine_alert_level(graph_report: Dict, cluster_report: Dict) -> str:
    """Determine overall alert level based on detection results."""
    critical_count = graph_report['summary']['critical_rings'] + cluster_report['summary']['high_risk_clusters']
    high_count = graph_report['summary']['high_risk_rings'] + cluster_report['summary']['medium_risk_clusters']
    total_rings = graph_report['total_fraud_rings_detected'] + cluster_report['total_clusters_detected']

    if critical_count > 0:
        return "CRITICAL"
    elif high_count >= 2 or total_rings >= 5:
        return "HIGH"
    elif total_rings > 0:
        return "MEDIUM"
    else:
        return "LOW"


def _get_quick_recommendation(alert_count: int, high_severity: int) -> str:
    """Generate quick recommendation based on alerts."""
    if high_severity >= 2:
        return "URGENT: Multiple critical fraud indicators detected. Immediate investigation required."
    elif high_severity == 1:
        return "High-risk fraud patterns detected. Review and block suspicious accounts."
    elif alert_count >= 3:
        return "Multiple fraud indicators present. Enhanced monitoring recommended."
    elif alert_count > 0:
        return "Some suspicious activity detected. Continue monitoring."
    else:
        return "No immediate fraud rings detected. Maintain normal vigilance."
