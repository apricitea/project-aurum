"""
Unit tests for main FastAPI application endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from httpx import AsyncClient
import json

from src.api.main import app


class TestHealthEndpoints:
    """Test health check endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_basic_health_check(self, test_client):
        """Test basic health check endpoint"""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "alert-system"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_detailed_health_check_all_healthy(self, test_client):
        """Test detailed health check with all services healthy"""
        with patch('src.api.main.db_manager') as mock_db, \
             patch('src.api.main.alert_engine') as mock_alert, \
             patch('src.api.main.risk_monitor') as mock_risk:

            # Mock healthy services
            mock_db.health_check = AsyncMock()
            mock_alert.is_running = True
            mock_risk.is_monitoring = True

            response = await test_client.get("/health/detailed")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["alert_engine"] == "healthy"
            assert data["services"]["risk_monitor"] == "healthy"

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_detailed_health_check_database_unhealthy(self, test_client):
        """Test detailed health check with database unhealthy"""
        with patch('src.api.main.db_manager') as mock_db, \
             patch('src.api.main.alert_engine') as mock_alert, \
             patch('src.api.main.risk_monitor') as mock_risk:

            # Mock database failure
            mock_db.health_check = AsyncMock(side_effect=Exception("Connection failed"))
            mock_alert.is_running = True
            mock_risk.is_monitoring = True

            response = await test_client.get("/health/detailed")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert "unhealthy: Connection failed" in data["services"]["database"]


class TestAuthenticationEndpoints:
    """Test authentication endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_login_success(self, test_client, mock_auth_manager):
        """Test successful login"""
        with patch('src.api.main.auth_manager', mock_auth_manager):
            mock_auth_manager.authenticate.return_value = {
                "access_token": "test_token",
                "refresh_token": "refresh_token",
                "token_type": "bearer",
                "expires_in": 3600
            }

            response = await test_client.post("/auth/login", json={
                "username": "testuser",
                "password": "testpass"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test_token"
            assert data["token_type"] == "bearer"
            mock_auth_manager.authenticate.assert_called_once_with("testuser", "testpass")

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_login_invalid_credentials(self, test_client, mock_auth_manager):
        """Test login with invalid credentials"""
        with patch('src.api.main.auth_manager', mock_auth_manager):
            mock_auth_manager.authenticate.side_effect = Exception("Invalid credentials")

            response = await test_client.post("/auth/login", json={
                "username": "testuser",
                "password": "wrongpass"
            })

            assert response.status_code == 401
            data = response.json()
            assert data["detail"] == "Invalid credentials"

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_refresh_token_success(self, test_client, mock_auth_manager):
        """Test successful token refresh"""
        with patch('src.api.main.auth_manager', mock_auth_manager):
            mock_auth_manager.refresh_token.return_value = {
                "access_token": "new_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer",
                "expires_in": 3600
            }

            response = await test_client.post("/auth/refresh", json={
                "refresh_token": "valid_refresh_token"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_token"

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_get_current_user_profile(self, test_client, sample_user):
        """Test getting current user profile"""
        with patch('src.api.main.get_current_user', return_value=sample_user):
            response = await test_client.get(
                "/auth/me",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert data["role"] == "trader"


class TestAlertEndpoints:
    """Test alert management endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.alerts
    async def test_get_alerts_success(self, test_client, sample_user, sample_alerts):
        """Test successful retrieval of alerts"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.alert_engine') as mock_engine:

            # Mock alert engine response
            mock_alerts = [MagicMock() for _ in sample_alerts]
            for mock_alert, sample_alert in zip(mock_alerts, sample_alerts):
                mock_alert.id = sample_alert["id"]
                mock_alert.alert_type = sample_alert["alert_type"]
                mock_alert.message = sample_alert["message"]
                mock_alert.priority = sample_alert["priority"]
                mock_alert.status = sample_alert["status"]
                mock_alert.created_at = sample_alert["created_at"]
                mock_alert.metadata = sample_alert["metadata"]

            mock_engine.get_alerts.return_value = mock_alerts

            response = await test_client.get(
                "/alerts?limit=10&status=ACTIVE",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == len(sample_alerts)
            mock_engine.get_alerts.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.alerts
    async def test_create_alert_success(self, test_client, sample_user):
        """Test successful alert creation"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.alert_engine') as mock_engine:

            # Mock created alert
            mock_alert = MagicMock()
            mock_alert.id = 1
            mock_alert.alert_type = "PRICE_BREAKOUT"
            mock_alert.message = "Test alert"
            mock_alert.priority = "HIGH"
            mock_alert.status = "ACTIVE"
            mock_alert.created_at = datetime.now()
            mock_alert.metadata = {}

            mock_engine.create_alert.return_value = mock_alert

            alert_data = {
                "alert_type": "PRICE_BREAKOUT",
                "message": "Test alert",
                "priority": "HIGH",
                "metadata": {}
            }

            response = await test_client.post(
                "/alerts",
                json=alert_data,
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["alert_type"] == "PRICE_BREAKOUT"
            assert data["message"] == "Test alert"

    @pytest.mark.asyncio
    @pytest.mark.alerts
    async def test_update_alert_status_success(self, test_client, sample_user):
        """Test successful alert status update"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.alert_engine') as mock_engine:

            # Mock updated alert
            mock_alert = MagicMock()
            mock_alert.id = 1
            mock_alert.status = "ACKNOWLEDGED"

            mock_engine.update_alert_status.return_value = mock_alert

            response = await test_client.put(
                "/alerts/1/status",
                json={"status": "ACKNOWLEDGED", "notes": "Reviewed"},
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            mock_engine.update_alert_status.assert_called_once_with(
                alert_id=1,
                status="ACKNOWLEDGED",
                notes="Reviewed",
                user_id=sample_user.id
            )


class TestSignalEndpoints:
    """Test signal management endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.signals
    async def test_get_daily_signals_success(self, test_client, sample_user, sample_signals):
        """Test successful retrieval of daily signals"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.signal_service') as mock_service:

            # Mock signal service response
            mock_signals = []
            for signal_data in sample_signals:
                mock_signal = MagicMock()
                mock_signal.stock_code = signal_data["stock_code"]
                mock_signal.signal_type = signal_data["signal_type"]
                mock_signal.confidence = signal_data["confidence"]
                mock_signal.generated_at = signal_data["generated_at"]
                mock_signals.append(mock_signal)

            mock_service.get_daily_signals.return_value = mock_signals

            response = await test_client.get(
                "/signals/daily",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "signals" in data
            assert "total_signals" in data
            assert data["total_signals"] == len(sample_signals)

    @pytest.mark.asyncio
    @pytest.mark.signals
    async def test_generate_signals_success(self, test_client, sample_admin_user):
        """Test manual signal generation"""
        with patch('src.api.main.get_current_user', return_value=sample_admin_user), \
             patch('src.api.main.signal_service') as mock_service:

            mock_service.start_signal_generation.return_value = "task_123"

            response = await test_client.post(
                "/signals/generate",
                headers={"Authorization": "Bearer admin_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task_123"
            assert data["status"] == "started"

    @pytest.mark.asyncio
    @pytest.mark.signals
    async def test_generate_signals_insufficient_permissions(self, test_client, sample_user):
        """Test signal generation with insufficient permissions"""
        with patch('src.api.main.get_current_user', return_value=sample_user):

            response = await test_client.post(
                "/signals/generate",
                headers={"Authorization": "Bearer user_token"}
            )

            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"


class TestPortfolioEndpoints:
    """Test portfolio management endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.portfolio
    async def test_get_portfolio_summary_success(self, test_client, sample_user):
        """Test successful portfolio summary retrieval"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.signal_service') as mock_service:

            mock_summary = {
                "total_value": 50000000,  # 50M IDR
                "total_pnl": 2500000,    # 2.5M IDR
                "total_pnl_percent": 5.0,
                "positions_count": 5,
                "cash_balance": 10000000
            }

            mock_service.get_portfolio_summary.return_value = mock_summary

            response = await test_client.get(
                "/portfolio/summary",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_value"] == 50000000
            assert data["total_pnl_percent"] == 5.0

    @pytest.mark.asyncio
    @pytest.mark.portfolio
    async def test_get_current_positions_success(self, test_client, sample_user, sample_portfolio):
        """Test successful retrieval of current positions"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.signal_service') as mock_service:

            # Mock portfolio positions
            mock_positions = []
            for pos_data in sample_portfolio:
                mock_pos = MagicMock()
                mock_pos.stock_code = pos_data["stock_code"]
                mock_pos.quantity = pos_data["quantity"]
                mock_pos.average_price = pos_data["average_price"]
                mock_pos.current_price = pos_data["current_price"]
                mock_positions.append(mock_pos)

            mock_service.get_current_positions.return_value = mock_positions

            response = await test_client.get(
                "/portfolio/positions",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == len(sample_portfolio)


class TestMarketDataEndpoints:
    """Test market data endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.indonesian_market
    async def test_get_market_status_open(self, test_client):
        """Test market status during open hours"""
        # Mock time during market hours (10:00 AM)
        mock_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

        with patch('src.api.main.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.strptime = datetime.strptime

            response = await test_client.get("/market/status")

            assert response.status_code == 200
            data = response.json()
            assert data["is_open"] is True
            assert data["session_type"] == "regular"

    @pytest.mark.asyncio
    @pytest.mark.indonesian_market
    async def test_get_market_status_closed(self, test_client):
        """Test market status during closed hours"""
        # Mock time outside market hours (18:00 PM)
        mock_time = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)

        with patch('src.api.main.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.strptime = datetime.strptime

            response = await test_client.get("/market/status")

            assert response.status_code == 200
            data = response.json()
            assert data["is_open"] is False


class TestRiskManagementEndpoints:
    """Test risk management endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.risk
    async def test_get_risk_overview_success(self, test_client, sample_user):
        """Test successful risk overview retrieval"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.risk_monitor') as mock_monitor:

            mock_risk_data = {
                "overall_risk_score": 6.5,
                "var_1d": 2500000,  # 2.5M IDR
                "sector_concentration": {
                    "Financial Services": 45.0,
                    "Technology": 25.0,
                    "Consumer Goods": 20.0,
                    "Other": 10.0
                },
                "position_risk": "MEDIUM",
                "correlation_risk": "LOW"
            }

            mock_monitor.get_risk_overview.return_value = mock_risk_data

            response = await test_client.get(
                "/risk/overview",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["overall_risk_score"] == 6.5
            assert data["position_risk"] == "MEDIUM"

    @pytest.mark.asyncio
    @pytest.mark.risk
    async def test_get_risk_alerts_success(self, test_client, sample_user):
        """Test successful risk alerts retrieval"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.risk_monitor') as mock_monitor:

            # Mock risk alerts
            mock_alerts = []
            for i in range(2):
                mock_alert = MagicMock()
                mock_alert.id = i + 1
                mock_alert.risk_type = "CONCENTRATION_RISK"
                mock_alert.severity = "MEDIUM"
                mock_alert.message = f"Risk alert {i + 1}"
                mock_alerts.append(mock_alert)

            mock_monitor.get_risk_alerts.return_value = mock_alerts

            response = await test_client.get(
                "/risk/alerts",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2


class TestAnalyticsEndpoints:
    """Test analytics and reporting endpoints"""

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_get_performance_analytics_success(self, test_client, sample_user):
        """Test successful performance analytics retrieval"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.signal_service') as mock_service:

            mock_analytics = {
                "total_return": 12.5,
                "sharpe_ratio": 1.8,
                "max_drawdown": -8.2,
                "win_rate": 68.5,
                "avg_return_per_trade": 2.3,
                "volatility": 15.6
            }

            mock_service.get_performance_analytics.return_value = mock_analytics

            response = await test_client.get(
                "/analytics/performance?days=30",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_return"] == 12.5
            assert data["sharpe_ratio"] == 1.8

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_generate_daily_report_json(self, test_client, sample_user):
        """Test daily report generation in JSON format"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.signal_service') as mock_service:

            mock_report = {
                "date": "2024-01-30",
                "signals_generated": 5,
                "trades_executed": 3,
                "total_pnl": 1500000,
                "portfolio_value": 52500000
            }

            mock_service.generate_daily_report.return_value = mock_report

            response = await test_client.get(
                "/reports/daily?format=json",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["signals_generated"] == 5
            assert data["total_pnl"] == 1500000


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_internal_server_error_handling(self, test_client, sample_user):
        """Test handling of internal server errors"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.alert_engine') as mock_engine:

            mock_engine.get_alerts.side_effect = Exception("Database connection failed")

            response = await test_client.get(
                "/alerts",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Failed to retrieve alerts"

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_unauthenticated_request(self, test_client):
        """Test handling of unauthenticated requests"""
        response = await test_client.get("/alerts")

        # Should return 401 or 403 depending on authentication middleware
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_invalid_request_data(self, test_client, sample_user):
        """Test handling of invalid request data"""
        with patch('src.api.main.get_current_user', return_value=sample_user):

            # Send invalid JSON data
            response = await test_client.post(
                "/alerts",
                json={"invalid": "data"},  # Missing required fields
                headers={"Authorization": "Bearer valid_token"}
            )

            # Should return 422 for validation error
            assert response.status_code in [422, 500]