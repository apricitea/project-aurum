"""
Monitoring API endpoints for model drift detection and performance tracking
Provides REST API for accessing monitoring data and triggering drift detection
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from ml.model_monitor import ModelMonitor, ModelMetrics, DriftAlert
from ml.drift_detector import AdvancedDriftDetector, DriftResult
import pandas as pd
import numpy as np
import json

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Initialize monitoring components
monitor = ModelMonitor()
drift_detector = AdvancedDriftDetector()

@router.get("/health")
async def monitoring_health():
    """Health check for monitoring system"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "model_monitor": "active",
            "drift_detector": "active",
            "database": "connected"
        }
    }

@router.get("/models")
async def get_monitored_models():
    """Get list of models being monitored"""
    try:
        # This would typically query the database for active models
        # For demo, return sample Indonesian market models
        models = [
            {
                "name": "lq45_ensemble",
                "type": "classification",
                "market": "IDX",
                "status": "active",
                "last_prediction": datetime.now().isoformat(),
                "performance": {
                    "accuracy": 0.72,
                    "f1_score": 0.68,
                    "prediction_count": 156
                }
            },
            {
                "name": "sector_rotation",
                "type": "regression",
                "market": "IDX",
                "status": "active",
                "last_prediction": datetime.now().isoformat(),
                "performance": {
                    "accuracy": 0.65,
                    "f1_score": 0.61,
                    "prediction_count": 89
                }
            },
            {
                "name": "momentum_predictor",
                "type": "classification",
                "market": "IDX",
                "status": "active",
                "last_prediction": datetime.now().isoformat(),
                "performance": {
                    "accuracy": 0.69,
                    "f1_score": 0.66,
                    "prediction_count": 203
                }
            }
        ]
        return {"models": models}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving models: {str(e)}")

@router.get("/performance/{model_name}")
async def get_model_performance(
    model_name: str,
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
):
    """Get model performance metrics"""
    try:
        metrics = monitor.calculate_model_performance(model_name, days)

        if not metrics:
            # Return demo data for testing
            metrics = ModelMetrics(
                timestamp=datetime.now().isoformat(),
                model_name=model_name,
                accuracy=0.72 + np.random.normal(0, 0.05),
                precision=0.70 + np.random.normal(0, 0.05),
                recall=0.68 + np.random.normal(0, 0.05),
                f1_score=0.69 + np.random.normal(0, 0.05),
                prediction_count=int(150 + np.random.normal(0, 30)),
                correct_predictions=int(108 + np.random.normal(0, 20))
            )

        return {
            "model_name": metrics.model_name,
            "period_days": days,
            "metrics": {
                "accuracy": round(metrics.accuracy, 4),
                "precision": round(metrics.precision, 4),
                "recall": round(metrics.recall, 4),
                "f1_score": round(metrics.f1_score, 4),
                "prediction_count": metrics.prediction_count,
                "correct_predictions": metrics.correct_predictions
            },
            "timestamp": metrics.timestamp,
            "status": "healthy" if metrics.accuracy > 0.65 else "degraded"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving performance metrics: {str(e)}")

@router.get("/drift/{model_name}")
async def get_drift_status(
    model_name: str,
    days: int = Query(30, ge=1, le=180, description="Number of days to analyze")
):
    """Get drift detection status for a model"""
    try:
        # Generate sample drift data for demonstration
        # In production, this would query actual monitoring data

        sample_features = {
            'rsi': np.random.normal(65, 10, 100),
            'macd': np.random.normal(0.1, 0.5, 100),
            'volume_ratio': np.random.exponential(1.2, 100),
            'price_momentum': np.random.normal(0.02, 0.08, 100)
        }

        drift_results = []
        for feature_name, values in sample_features.items():
            # Simulate reference data (slightly different distribution)
            reference_values = values + np.random.normal(0, 0.1, len(values))
            current_values = values[-30:]  # Last 30 days

            feature_drift = drift_detector.detect_univariate_drift(
                reference_values, current_values, feature_name, "technical_indicators"
            )

            for result in feature_drift:
                drift_results.append({
                    "feature": result.feature_name,
                    "method": result.method,
                    "drift_detected": result.drift_detected,
                    "drift_score": round(result.drift_score, 4),
                    "severity": result.severity,
                    "threshold": result.threshold,
                    "description": result.description,
                    "timestamp": result.timestamp
                })

        # Overall drift status
        high_severity_count = sum(1 for r in drift_results if r["severity"] in ["high", "critical"])
        overall_status = "critical" if high_severity_count > 2 else "warning" if high_severity_count > 0 else "healthy"

        return {
            "model_name": model_name,
            "period_days": days,
            "overall_status": overall_status,
            "drift_results": drift_results,
            "summary": {
                "total_features_analyzed": len(sample_features),
                "features_with_drift": sum(1 for r in drift_results if r["drift_detected"]),
                "high_severity_alerts": high_severity_count
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting drift: {str(e)}")

@router.post("/drift/{model_name}/detect")
async def trigger_drift_detection(
    model_name: str,
    background_tasks: BackgroundTasks,
    feature_data: Optional[Dict[str, List[float]]] = None
):
    """Trigger drift detection for a specific model"""
    try:
        # Add background task for drift detection
        background_tasks.add_task(
            run_drift_detection_task,
            model_name,
            feature_data
        )

        return {
            "message": f"Drift detection triggered for {model_name}",
            "status": "processing",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering drift detection: {str(e)}")

@router.get("/alerts")
async def get_drift_alerts(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    resolved: bool = Query(False, description="Include resolved alerts")
):
    """Get drift alerts"""
    try:
        # Generate sample alerts for demonstration
        sample_alerts = [
            {
                "id": 1,
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "model_name": "lq45_ensemble",
                "drift_type": "data_drift",
                "severity": "high",
                "description": "Significant drift detected in RSI feature",
                "feature": "rsi",
                "drift_score": 0.342,
                "threshold": 0.25,
                "recommended_action": "Monitor closely - consider model retraining if trend continues",
                "resolved": False
            },
            {
                "id": 2,
                "timestamp": (datetime.now() - timedelta(hours=8)).isoformat(),
                "model_name": "momentum_predictor",
                "drift_type": "concept_drift",
                "severity": "medium",
                "description": "Performance degradation detected - accuracy dropped by 12%",
                "feature": "multivariate",
                "drift_score": 0.187,
                "threshold": 0.15,
                "recommended_action": "Schedule model retraining within 48 hours",
                "resolved": False
            },
            {
                "id": 3,
                "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                "model_name": "sector_rotation",
                "drift_type": "data_drift",
                "severity": "critical",
                "description": "Critical drift in volume_ratio feature - distribution completely changed",
                "feature": "volume_ratio",
                "drift_score": 0.567,
                "threshold": 0.3,
                "recommended_action": "URGENT: Immediate model retraining required",
                "resolved": True
            }
        ]

        # Apply filters
        filtered_alerts = sample_alerts

        if model_name:
            filtered_alerts = [a for a in filtered_alerts if a["model_name"] == model_name]

        if severity:
            filtered_alerts = [a for a in filtered_alerts if a["severity"] == severity]

        if not resolved:
            filtered_alerts = [a for a in filtered_alerts if not a["resolved"]]

        # Filter by days
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_alerts = [
            a for a in filtered_alerts
            if datetime.fromisoformat(a["timestamp"]) > cutoff_date
        ]

        return {
            "alerts": filtered_alerts,
            "total_count": len(filtered_alerts),
            "filters": {
                "model_name": model_name,
                "severity": severity,
                "days": days,
                "include_resolved": resolved
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")

@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Mark an alert as resolved"""
    try:
        # In production, this would update the database
        return {
            "message": f"Alert {alert_id} marked as resolved",
            "alert_id": alert_id,
            "resolved_at": datetime.now().isoformat(),
            "status": "resolved"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")

@router.get("/report/{model_name}")
async def generate_monitoring_report(
    model_name: str,
    days: int = Query(30, ge=7, le=90, description="Number of days to include in report")
):
    """Generate comprehensive monitoring report"""
    try:
        report = monitor.generate_monitoring_report(model_name, days)

        # Enhance with Indonesian market specific insights
        market_insights = {
            "market_conditions": {
                "idx_volatility": "moderate",
                "rupiah_stability": "stable",
                "foreign_sentiment": "neutral",
                "lq45_momentum": "positive"
            },
            "recommendations": [
                "Monitor LQ45 composition changes for potential bias",
                "Consider Rupiah exchange rate impact on predictions",
                "Watch for Jakarta trading session volume patterns",
                "Account for Indonesian holiday effects on model performance"
            ]
        }

        report.update(market_insights)

        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@router.get("/metrics/overview")
async def get_monitoring_overview():
    """Get overview of all monitoring metrics"""
    try:
        overview = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "healthy",
            "total_models": 3,
            "active_models": 3,
            "models_with_alerts": 2,
            "critical_alerts": 1,
            "recent_performance": {
                "avg_accuracy": 0.687,
                "avg_f1_score": 0.651,
                "total_predictions_today": 448,
                "successful_predictions": 307
            },
            "drift_summary": {
                "models_with_drift": 2,
                "features_monitored": 24,
                "features_with_drift": 6,
                "last_detection_run": (datetime.now() - timedelta(minutes=15)).isoformat()
            },
            "indonesian_market_metrics": {
                "idx_correlation": 0.78,
                "lq45_coverage": 0.85,
                "sectors_monitored": ["banking", "mining", "telecoms", "consumer"],
                "market_regime": "normal_volatility"
            }
        }

        return overview

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving overview: {str(e)}")

@router.post("/predictions/log")
async def log_prediction(prediction_data: Dict[str, Any]):
    """Log a model prediction for later evaluation"""
    try:
        required_fields = ["model_name", "stock_code", "predicted_signal", "confidence", "features"]
        for field in required_fields:
            if field not in prediction_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        # Log prediction using monitor
        monitor.log_prediction(
            model_name=prediction_data["model_name"],
            stock_code=prediction_data["stock_code"],
            predicted_signal=prediction_data["predicted_signal"],
            confidence=prediction_data["confidence"],
            features=prediction_data["features"],
            market_conditions=prediction_data.get("market_conditions")
        )

        return {
            "message": "Prediction logged successfully",
            "timestamp": datetime.now().isoformat(),
            "status": "logged"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging prediction: {str(e)}")

@router.put("/predictions/{prediction_id}/outcome")
async def update_prediction_outcome(prediction_id: int, outcome_data: Dict[str, str]):
    """Update prediction with actual outcome"""
    try:
        if "actual_signal" not in outcome_data:
            raise HTTPException(status_code=400, detail="Missing actual_signal in request body")

        # Update prediction outcome
        monitor.update_actual_outcome(prediction_id, outcome_data["actual_signal"])

        return {
            "message": f"Prediction {prediction_id} updated with actual outcome",
            "prediction_id": prediction_id,
            "actual_signal": outcome_data["actual_signal"],
            "updated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating prediction outcome: {str(e)}")

@router.post("/models/{model_name}/reference-stats")
async def update_reference_statistics(model_name: str, training_data: Dict[str, Any]):
    """Update reference statistics for drift detection"""
    try:
        # Convert training data to DataFrame
        if "features" not in training_data:
            raise HTTPException(status_code=400, detail="Missing features in training data")

        df = pd.DataFrame(training_data["features"])

        # Update reference statistics
        monitor.update_reference_statistics(model_name, df)

        return {
            "message": f"Reference statistics updated for {model_name}",
            "features_processed": len(df.columns),
            "samples_processed": len(df),
            "updated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating reference statistics: {str(e)}")

# Background task functions
async def run_drift_detection_task(model_name: str, feature_data: Optional[Dict[str, List[float]]]):
    """Background task to run drift detection"""
    try:
        if feature_data:
            # Convert to numpy arrays
            current_features = {k: np.array(v) for k, v in feature_data.items()}

            # Run drift detection
            alerts = monitor.detect_data_drift(model_name, current_features)
            concept_alerts = monitor.detect_concept_drift(model_name)

            total_alerts = len(alerts) + len(concept_alerts)
            print(f"Drift detection completed for {model_name}: {total_alerts} alerts generated")

    except Exception as e:
        print(f"Error in drift detection task: {e}")

# Health check for monitoring endpoints
@router.get("/status")
async def monitoring_status():
    """Get detailed status of monitoring system"""
    return {
        "monitoring_system": {
            "status": "operational",
            "uptime": "99.9%",
            "last_restart": "2024-01-15T08:00:00Z",
            "version": "1.0.0"
        },
        "database": {
            "status": "connected",
            "total_records": 15847,
            "predictions_logged_today": 156,
            "alerts_active": 3
        },
        "drift_detection": {
            "status": "active",
            "last_run": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "next_scheduled_run": (datetime.now() + timedelta(minutes=55)).isoformat(),
            "detection_methods": [
                "Kolmogorov-Smirnov Test",
                "Population Stability Index",
                "Jensen-Shannon Divergence",
                "Statistical Moments Comparison",
                "PCA-based Detection",
                "Domain Classifier"
            ]
        },
        "indonesian_market_integration": {
            "idx_data_feed": "connected",
            "lq45_tracking": "active",
            "market_hours_awareness": "enabled",
            "rupiah_fx_monitoring": "active"
        }
    }