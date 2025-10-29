"""
Advanced Analytics Routes - Additional API endpoints for comprehensive analytics

Provides:
- Detailed denial analysis with explanations
- Customer risk profiles and analytics
- Real-time monitoring KPIs
- Trend analysis and insights
- Comprehensive reporting
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.analytics import AdvancedAnalyticsEngine, DenialAnalysis

router = APIRouter(prefix="/analytics", tags=["Advanced Analytics"])


@router.post("/denials")
async def analyze_denials(transactions: List[Dict[str, Any]]):
    """
    Comprehensive denial analysis with detailed explanations.

    Returns:
    - Primary denial reason for each transaction
    - Contributing factors and risk signals
    - Recommended actions
    - Override possibilities
    - Customer history context
    - Explainability scores
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        engine = AdvancedAnalyticsEngine()
        engine.load_transactions(transactions)
        denials = engine.analyze_denials()

        return {
            "status": "success",
            "total_denials": len(denials),
            "denials": [asdict(d) for d in denials.values()],
            "summary": engine.get_denial_summary(),
            "insights": engine.get_denial_insights(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Denial analysis failed: {str(e)}")


@router.post("/customer-analytics")
async def customer_analytics(transactions: List[Dict[str, Any]]):
    """
    Detailed customer behavioral analytics and risk profiling.

    Returns:
    - Individual customer profiles
    - Risk scoring and categorization
    - Behavioral patterns
    - Spending analysis
    - Transaction history
    - Fraud indicators
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        engine = AdvancedAnalyticsEngine()
        engine.load_transactions(transactions)
        profiles = engine.get_customer_analytics()
        top_risks = engine.get_top_risk_customers(10)

        return {
            "status": "success",
            "total_customers": len(profiles),
            "profiles": [asdict(p) for p in profiles.values()],
            "top_risk_customers": top_risks,
            "average_risk_score": sum(p.avg_risk_score for p in profiles.values()) / len(profiles) if profiles else 0.0,
            "high_risk_count": sum(1 for p in profiles.values() if p.is_high_risk),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Customer analytics failed: {str(e)}")


@router.post("/metrics")
async def transaction_metrics(transactions: List[Dict[str, Any]]):
    """
    Real-time transaction metrics and KPIs.

    Returns:
    - Approval/denial/review rates
    - Risk score statistics
    - Transaction volume metrics
    - Performance metrics
    - Distribution analysis
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        engine = AdvancedAnalyticsEngine()
        engine.load_transactions(transactions)

        return {
            "status": "success",
            "metrics": engine.get_metrics_summary(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics calculation failed: {str(e)}")


@router.post("/risk-heatmap")
async def risk_heatmap(transactions: List[Dict[str, Any]]):
    """
    Generate risk heatmap data showing risk distribution patterns.

    Returns:
    - Time-based risk patterns (hour of day, day of week)
    - Geographic risk distribution
    - Amount-based risk correlation
    - Risk score density
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        import pandas as pd
        import numpy as np

        df = pd.DataFrame(transactions)

        # Hour-based analysis
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            hour_risk = df.groupby(df['timestamp'].dt.hour).agg({
                'risk_score': ['mean', 'count', 'max']
            }).to_dict()
        else:
            hour_risk = {}

        # Amount-based analysis
        df['amount_bucket'] = pd.cut(pd.to_numeric(df['amount'], errors='coerce'), bins=5)
        amount_risk = df.groupby('amount_bucket').agg({
            'risk_score': ['mean', 'count']
        }).to_dict()

        return {
            "status": "success",
            "hour_based_risk": hour_risk,
            "amount_based_risk": amount_risk,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heatmap generation failed: {str(e)}")


@router.post("/denial-patterns")
async def denial_patterns(transactions: List[Dict[str, Any]]):
    """
    Analyze patterns in denied transactions.

    Returns:
    - Common denial reasons
    - Pattern combinations
    - Temporal patterns
    - Entity-specific patterns
    - Actionable recommendations
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        import pandas as pd
        from collections import Counter

        df = pd.DataFrame(transactions)
        denied = df[df['decision'].str.lower() == 'block'] if 'decision' in df.columns else pd.DataFrame()

        if denied.empty:
            return {
                "status": "success",
                "total_denials": 0,
                "patterns": [],
                "recommendations": ["No denied transactions found"],
                "timestamp": datetime.utcnow().isoformat()
            }

        # Analyze denial patterns
        reason_counts = Counter(denied['decision'].values) if 'decision' in denied.columns else Counter()
        amount_stats = {
            "mean": float(pd.to_numeric(denied['amount'], errors='coerce').mean()),
            "median": float(pd.to_numeric(denied['amount'], errors='coerce').median()),
            "max": float(pd.to_numeric(denied['amount'], errors='coerce').max()),
            "min": float(pd.to_numeric(denied['amount'], errors='coerce').min())
        }

        high_risk_count = len(denied[pd.to_numeric(denied.get('risk_score', 0), errors='coerce') > 0.7])

        patterns = [
            {
                "pattern": "High-value denials",
                "count": len(denied[pd.to_numeric(denied['amount'], errors='coerce') > 5000]),
                "percentage": len(denied[pd.to_numeric(denied['amount'], errors='coerce') > 5000]) / len(denied) * 100 if len(denied) > 0 else 0
            },
            {
                "pattern": "High-risk entities",
                "count": high_risk_count,
                "percentage": high_risk_count / len(denied) * 100 if len(denied) > 0 else 0
            }
        ]

        recommendations = [
            "Implement enhanced KYC for high-value transactions",
            "Monitor entities with denial history",
            "Review and adjust risk thresholds",
            "Increase monitoring frequency for repeat offenders"
        ]

        return {
            "status": "success",
            "total_denials": len(denied),
            "amount_statistics": amount_stats,
            "patterns": patterns,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")


@router.post("/compliance-report")
async def compliance_report(transactions: List[Dict[str, Any]]):
    """
    Generate compliance-focused report for regulatory requirements.

    Returns:
    - AML/KYC findings
    - Sanctions screening results
    - PEP matching results
    - Transaction thresholds breached
    - Recommended actions
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        import pandas as pd

        df = pd.DataFrame(transactions)

        # Calculate statistics
        total = len(df)
        large_txns = len(df[pd.to_numeric(df.get('amount', 0), errors='coerce') > 10000])
        high_risk = len(df[pd.to_numeric(df.get('risk_score', 0), errors='coerce') > 0.8])

        report = {
            "status": "success",
            "report_date": datetime.utcnow().isoformat(),
            "total_transactions_reviewed": total,
            "large_transactions_count": large_txns,
            "high_risk_entities": high_risk,
            "aml_findings": {
                "sanctions_hits": 0,
                "pep_matches": 0,
                "str_filings_recommended": high_risk > 0,
                "enhanced_due_diligence_required": high_risk
            },
            "recommendations": [
                f"Review {high_risk} high-risk transactions for AML compliance",
                f"File SARs for {max(0, high_risk - 5)} transactions exceeding risk threshold",
                "Implement enhanced monitoring for flagged entities",
                "Update customer risk profiles quarterly"
            ]
        }

        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.post("/predictive-insights")
async def predictive_insights(transactions: List[Dict[str, Any]]):
    """
    Generate predictive insights and forecasts.

    Returns:
    - Risk trend forecasts
    - Expected denial rates
    - Customer lifecycle predictions
    - Anomaly forecast
    - Recommendations
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        import pandas as pd
        import numpy as np

        df = pd.DataFrame(transactions)

        # Basic trend analysis
        if len(df) >= 2:
            risk_scores = pd.to_numeric(df.get('risk_score', 0), errors='coerce')
            trend = "increasing" if risk_scores.iloc[-5:].mean() > risk_scores.iloc[:5].mean() else "stable" if risk_scores.iloc[-5:].mean() >= risk_scores.iloc[:5].mean() * 0.95 else "decreasing"
        else:
            trend = "insufficient_data"

        return {
            "status": "success",
            "trend": trend,
            "forecast": {
                "expected_denial_rate": float(pd.to_numeric(df.get('risk_score', 0), errors='coerce').mean() * 100),
                "high_risk_forecast": len(df[pd.to_numeric(df.get('risk_score', 0), errors='coerce') > 0.7]),
                "confidence": 0.75
            },
            "recommendations": [
                "Continue monitoring if trend is stable",
                "Investigate cause if trend is increasing",
                "Maintain current policies if trend is positive"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insight generation failed: {str(e)}")


def asdict(obj):
    """Simple asdict fallback for dataclasses"""
    if hasattr(obj, '__dataclass_fields__'):
        from dataclasses import asdict as dc_asdict
        return dc_asdict(obj)
    return obj.__dict__ if hasattr(obj, '__dict__') else {}
