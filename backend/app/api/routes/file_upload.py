"""
File upload and analysis endpoints for Risk Decision Engine API
"""

from fastapi import APIRouter, HTTPException, File, UploadFile
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
import tempfile
import os

from app.models.schemas import AdvancedAnalysisResponse, RiskProfileResponse
from app.core.fraud_insights import FraudInsightsEngine
import numpy as np
import pandas as pd

# Import analytics modules - with error handling for missing modules
try:
    from app.services.analytics.file_processor import FileProcessor
    from app.services.analytics.advanced_fraud_detection import AdvancedFraudDetectionEngine
    from app.services.analytics.targeted_ring_detector import TargetedFraudRingDetector
    from app.services.analytics.organized_fraud_detector import OrganizedFraudDetector
    from app.services.analytics.data_driven_fraud_detector import DataDrivenFraudDetector
    FILE_PROCESSOR_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Analytics modules not fully available: {e}")
    FILE_PROCESSOR_AVAILABLE = False
    FileProcessor = None
    AdvancedFraudDetectionEngine = None
    TargetedFraudRingDetector = None
    OrganizedFraudDetector = None

router = APIRouter(tags=["File Upload"])


def convert_numpy_types(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj


@router.post("/upload-and-analyze", response_model=AdvancedAnalysisResponse)
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Upload a transaction data file (CSV/JSON/Excel) and get world-class fraud detection analysis.

    Supported formats:
    - CSV (comma-separated values)
    - JSON (array of transactions)
    - JSONL (JSON Lines format)
    - Excel (XLSX/XLS)

    Returns comprehensive fraud detection including:
    - Multi-dimensional risk profiling
    - Anomaly detection (Isolation Forest + Local Outlier Factor)
    - Fraud network detection (graph analysis)
    - Money laundering pattern detection
    - Entity risk scoring (base + ML + behavioral + network + anomaly)
    - Detailed risk factors and red flags
    - Suspicious network clusters
    """
    if not FILE_PROCESSOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="File processing service not available. Analytics modules missing."
        )

    temp_file_path = None

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            temp_file_path = tmp.name
            content = await file.read()
            tmp.write(content)

        # Process file
        transactions = FileProcessor.process_file(temp_file_path)

        # Keep original transactions for OrganizedFraudDetector (it does its own normalization)
        original_transactions = transactions.copy()

        # Normalize column names (intelligent mapping)
        transactions = FileProcessor.normalize_columns(transactions)

        # Validate data quality (now flexible - accepts any format)
        validation = FileProcessor.validate_transactions(transactions)

        # Note: Removed strict quality check - system now works with any data!

        # Initialize advanced fraud detection engine
        print("[DEBUG] Running AdvancedFraudDetectionEngine...")
        try:
            fraud_engine = AdvancedFraudDetectionEngine()
            fraud_engine.load_transactions(transactions)

            # Run all detection analyses
            anomalies = fraud_engine.detect_anomalies()
            fraud_networks = fraud_engine.detect_fraud_networks()
            ml_patterns = fraud_engine.detect_money_laundering_patterns()
            risk_profiles = fraud_engine.calculate_comprehensive_risk_scores()

            # Generate comprehensive report
            report = fraud_engine.generate_comprehensive_report()
            print(f"[DEBUG] AdvancedFraudDetectionEngine completed successfully")
        except Exception as e:
            print(f"[ERROR] AdvancedFraudDetectionEngine failed: {e}")
            raise

        # Run Fraud Intelligence Analysis (NEW!)
        print("[DEBUG] Running FraudInsightsEngine...")
        try:
            fraud_insights_engine = FraudInsightsEngine(transactions)
            fraud_insights = fraud_insights_engine.analyze()
            print(f"[DEBUG] FraudInsightsEngine completed successfully")
        except Exception as e:
            print(f"[ERROR] FraudInsightsEngine failed: {e}")
            raise

        # Run Targeted Fraud Ring Detection (5 specific fraud ring types)
        print("[DEBUG] Running TargetedFraudRingDetector...")
        try:
            from dataclasses import asdict
            ring_detector = TargetedFraudRingDetector()
            ring_detector.load_transactions(transactions)
            fraud_rings_obj = ring_detector.detect_all_targeted_rings()
            # Convert dataclass to dict for JSON serialization
            fraud_rings_report = asdict(fraud_rings_obj) if fraud_rings_obj else None
            print(f"[DEBUG] TargetedFraudRingDetector completed successfully")
        except Exception as e:
            print(f"[ERROR] TargetedFraudRingDetector failed: {e}")
            raise

        # Run Organized Fraud Detection (Fake Identity + Geographic Mismatch patterns)
        # Use ORIGINAL transactions (before normalization) as it does its own normalization
        print("[DEBUG] Running OrganizedFraudDetector...")
        try:
            organized_fraud_detector = OrganizedFraudDetector()
            organized_fraud_detector.load_transactions(original_transactions)
            organized_fraud_detector.detect_organized_fraud_rings()
            organized_fraud_report = organized_fraud_detector.generate_report()
            print(f"[DEBUG] Organized fraud report: {organized_fraud_report.get('total_rings_detected', 0)} rings")
        except Exception as e:
            print(f"[ERROR] OrganizedFraudDetector failed: {e}")
            raise

        # Run Data-Driven Fraud Detection (Based on discovered patterns from actual fraud data)
        print("[DEBUG] Running DataDrivenFraudDetector...")
        try:
            data_driven_detector = DataDrivenFraudDetector()
            data_driven_detector.load_transactions(transactions)
            data_driven_report = data_driven_detector.generate_comprehensive_report()
            print(f"[DEBUG] Data-driven report: {data_driven_report.get('total_rings_detected', 0)} rings")
        except Exception as e:
            print(f"[ERROR] DataDrivenFraudDetector failed: {e}")
            raise

        # Convert risk profiles to response format (with numpy type conversion)
        risk_profile_responses = [
            RiskProfileResponse(
                entity_id=str(profile.entity_id),
                entity_type=str(profile.entity_type),
                base_risk_score=float(profile.base_risk_score) if profile.base_risk_score is not None else 0.0,
                ml_risk_score=float(profile.ml_risk_score) if profile.ml_risk_score is not None else 0.0,
                behavioral_risk_score=float(profile.behavioral_risk_score) if profile.behavioral_risk_score is not None else 0.0,
                network_risk_score=float(profile.network_risk_score) if profile.network_risk_score is not None else 0.0,
                anomaly_score=float(profile.anomaly_score) if profile.anomaly_score is not None else 0.0,
                final_risk_score=float(profile.final_risk_score) if profile.final_risk_score is not None else 0.0,
                risk_level=str(profile.risk_level),
                risk_factors=convert_numpy_types(profile.risk_factors),
                red_flags=convert_numpy_types(profile.red_flags),
                confidence_score=float(profile.confidence_score) if profile.confidence_score is not None else 0.0
            )
            for profile in risk_profiles.values()
        ]

        # Convert all numpy types to native Python types for JSON serialization
        response_data = {
            "status": "success",
            "file_name": file.filename,
            "records_processed": validation["valid_records"],
            "timestamp": datetime.utcnow().isoformat(),
            "summary": convert_numpy_types(report["summary"]),
            "anomalies": convert_numpy_types(anomalies),
            "fraud_networks": convert_numpy_types(fraud_networks),
            "money_laundering_patterns": convert_numpy_types(ml_patterns),
            "risk_profiles": risk_profile_responses,
            "fraud_insights": convert_numpy_types(fraud_insights),
            "fraud_rings": convert_numpy_types(fraud_rings_report),  # Targeted fraud ring detection
            "organized_fraud": convert_numpy_types(organized_fraud_report),  # Organized fraud (fake ID, email mismatch)
            "data_driven_fraud_rings": convert_numpy_types(data_driven_report)  # Data-driven fraud rings (NIGHT-TIME, VELOCITY, SHOPPING)
        }

        return AdvancedAnalysisResponse(**response_data)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post("/analyze-transactions", response_model=AdvancedAnalysisResponse)
async def analyze_transactions(transactions: List[Dict[str, Any]]):
    """
    Analyze a list of transactions (JSON) with world-class fraud detection.

    Provides:
    - Multi-dimensional risk profiling
    - Anomaly detection (Isolation Forest + Local Outlier Factor)
    - Fraud network detection (graph analysis)
    - Money laundering pattern detection
    - Entity risk scoring (base + ML + behavioral + network + anomaly)
    - Detailed risk factors and red flags
    - Comprehensive fraud intelligence
    """
    if not FILE_PROCESSOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Analytics service not available. Analytics modules missing."
        )

    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided")

    try:
        # Normalize column names (intelligent mapping)
        transactions = FileProcessor.normalize_columns(transactions)

        # Initialize advanced fraud detection engine
        fraud_engine = AdvancedFraudDetectionEngine()
        fraud_engine.load_transactions(transactions)

        # Run all detection analyses
        anomalies = fraud_engine.detect_anomalies()
        fraud_networks = fraud_engine.detect_fraud_networks()
        ml_patterns = fraud_engine.detect_money_laundering_patterns()
        risk_profiles = fraud_engine.calculate_comprehensive_risk_scores()

        # Generate comprehensive report
        report = fraud_engine.generate_comprehensive_report()

        # Run Fraud Intelligence Analysis (NEW!)
        fraud_insights_engine = FraudInsightsEngine(transactions)
        fraud_insights = fraud_insights_engine.analyze()

        # Run Targeted Fraud Ring Detection (5 specific fraud ring types)
        from dataclasses import asdict
        ring_detector = TargetedFraudRingDetector()
        ring_detector.load_transactions(transactions)
        fraud_rings_obj = ring_detector.detect_all_targeted_rings()
        # Convert dataclass to dict for JSON serialization
        fraud_rings_report = asdict(fraud_rings_obj) if fraud_rings_obj else None

        # Run Organized Fraud Detection (Fake Identity + Geographic Mismatch patterns)
        print("[DEBUG] Running OrganizedFraudDetector...")
        organized_fraud_detector = OrganizedFraudDetector()
        organized_fraud_detector.load_transactions(transactions)
        organized_fraud_detector.detect_organized_fraud_rings()
        organized_fraud_report = organized_fraud_detector.generate_report()
        print(f"[DEBUG] Organized fraud report: {organized_fraud_report.get('total_rings_detected', 0)} rings")

        # Run Data-Driven Fraud Detection (Based on discovered patterns from actual fraud data)
        print("[DEBUG] Running DataDrivenFraudDetector...")
        data_driven_detector = DataDrivenFraudDetector()
        data_driven_detector.load_transactions(transactions)
        data_driven_report = data_driven_detector.generate_comprehensive_report()
        print(f"[DEBUG] Data-driven report: {data_driven_report.get('total_rings_detected', 0)} rings")

        # Convert risk profiles to response format (with numpy type conversion)
        risk_profile_responses = [
            RiskProfileResponse(
                entity_id=str(profile.entity_id),
                entity_type=str(profile.entity_type),
                base_risk_score=float(profile.base_risk_score) if profile.base_risk_score is not None else 0.0,
                ml_risk_score=float(profile.ml_risk_score) if profile.ml_risk_score is not None else 0.0,
                behavioral_risk_score=float(profile.behavioral_risk_score) if profile.behavioral_risk_score is not None else 0.0,
                network_risk_score=float(profile.network_risk_score) if profile.network_risk_score is not None else 0.0,
                anomaly_score=float(profile.anomaly_score) if profile.anomaly_score is not None else 0.0,
                final_risk_score=float(profile.final_risk_score) if profile.final_risk_score is not None else 0.0,
                risk_level=str(profile.risk_level),
                risk_factors=convert_numpy_types(profile.risk_factors),
                red_flags=convert_numpy_types(profile.red_flags),
                confidence_score=float(profile.confidence_score) if profile.confidence_score is not None else 0.0
            )
            for profile in risk_profiles.values()
        ]

        return AdvancedAnalysisResponse(
            status="success",
            file_name="json_input",
            records_processed=len(transactions),
            timestamp=datetime.utcnow().isoformat(),
            summary=report["summary"],
            anomalies=anomalies,
            fraud_networks=fraud_networks,
            money_laundering_patterns=ml_patterns,
            risk_profiles=risk_profile_responses,
            fraud_insights=fraud_insights,
            fraud_rings=fraud_rings_report  # NEW: Targeted fraud ring detection!
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing transactions: {str(e)}")
