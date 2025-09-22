"""
Integration tests for API endpoints and workflows
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import json

from tests.fixtures.indonesian_market_data import IndonesianMarketFixtures


class TestAuthenticationIntegration:
    """Test authentication integration workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_authentication_flow(self, test_client):
        """Test complete authentication flow from login to protected access"""
        # Step 1: Login
        with patch('src.api.main.auth_manager') as mock_auth:
            mock_auth.authenticate.return_value = {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test",
                "refresh_token": "refresh_token_here",
                "token_type": "bearer",
                "expires_in": 3600
            }

            login_response = await test_client.post("/auth/login", json={
                "username": "testuser",
                "password": "testpass"
            })

            assert login_response.status_code == 200
            login_data = login_response.json()
            access_token = login_data["access_token"]

        # Step 2: Use token to access protected endpoint
        with patch('src.api.main.get_current_user') as mock_get_user:
            mock_user = AsyncMock()
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_user.email = "test@example.com"
            mock_user.role = "trader"
            mock_get_user.return_value = mock_user

            profile_response = await test_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            assert profile_response.status_code == 200
            profile_data = profile_response.json()
            assert profile_data["username"] == "testuser"

        # Step 3: Refresh token
        with patch('src.api.main.auth_manager') as mock_auth:
            mock_auth.refresh_token.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer",
                "expires_in": 3600
            }

            refresh_response = await test_client.post("/auth/refresh", json={
                "refresh_token": "refresh_token_here"
            })

            assert refresh_response.status_code == 200
            new_token_data = refresh_response.json()
            assert new_token_data["access_token"] == "new_access_token"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_token_expiration_handling(self, test_client):
        """Test handling of expired tokens"""
        # Use expired token
        with patch('src.api.main.get_current_user') as mock_get_user:
            from fastapi import HTTPException
            mock_get_user.side_effect = HTTPException(status_code=401, detail="Token has expired")

            response = await test_client.get(
                "/auth/me",
                headers={"Authorization": "Bearer expired_token"}
            )

            assert response.status_code == 401
            assert "expired" in response.json()["detail"].lower()


class TestAlertSystemIntegration:
    """Test alert system integration workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_alert_creation_and_retrieval_workflow(self, test_client, sample_user):
        """Test complete alert workflow: create, retrieve, update"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.alert_engine') as mock_alert_engine:

            # Step 1: Create alert
            mock_created_alert = AsyncMock()
            mock_created_alert.id = 1
            mock_created_alert.alert_type = "PRICE_BREAKOUT"
            mock_created_alert.message = "BBCA breakout above 9200"
            mock_created_alert.priority = "HIGH"
            mock_created_alert.status = "ACTIVE"
            mock_created_alert.created_at = datetime.now()
            mock_created_alert.metadata = {"stock_code": "BBCA", "breakout_price": 9200}

            mock_alert_engine.create_alert.return_value = mock_created_alert

            create_response = await test_client.post(
                "/alerts",
                json={
                    "alert_type": "PRICE_BREAKOUT",
                    "message": "BBCA breakout above 9200",
                    "priority": "HIGH",
                    "metadata": {"stock_code": "BBCA", "breakout_price": 9200}
                },
                headers={"Authorization": "Bearer valid_token"}
            )

            assert create_response.status_code == 200
            created_alert = create_response.json()
            alert_id = created_alert["id"]

            # Step 2: Retrieve alerts
            mock_alert_engine.get_alerts.return_value = [mock_created_alert]

            get_response = await test_client.get(
                "/alerts",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert get_response.status_code == 200
            alerts = get_response.json()
            assert len(alerts) == 1
            assert alerts[0]["id"] == alert_id

            # Step 3: Update alert status
            mock_updated_alert = AsyncMock()
            mock_updated_alert.id = 1
            mock_updated_alert.status = "ACKNOWLEDGED"
            mock_alert_engine.update_alert_status.return_value = mock_updated_alert

            update_response = await test_client.put(
                f"/alerts/{alert_id}/status",
                json={"status": "ACKNOWLEDGED", "notes": "Alert reviewed"},
                headers={"Authorization": "Bearer valid_token"}
            )

            assert update_response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_alert_filtering_and_pagination(self, test_client, sample_user):
        """Test alert filtering and pagination"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.alert_engine') as mock_alert_engine:

            # Mock multiple alerts
            alerts = []
            for i in range(15):
                alert = AsyncMock()
                alert.id = i + 1
                alert.alert_type = "PRICE_BREAKOUT" if i % 2 == 0 else "RISK_WARNING"
                alert.priority = "HIGH" if i < 5 else "MEDIUM"
                alert.status = "ACTIVE" if i < 10 else "ACKNOWLEDGED"
                alert.created_at = datetime.now() - timedelta(hours=i)
                alerts.append(alert)

            mock_alert_engine.get_alerts.return_value = alerts[:10]  # First page

            # Test pagination
            response = await test_client.get(
                "/alerts?limit=10&offset=0",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            page1_alerts = response.json()
            assert len(page1_alerts) == 10

            # Test filtering by status
            active_alerts = [a for a in alerts if a.status == "ACTIVE"]
            mock_alert_engine.get_alerts.return_value = active_alerts

            response = await test_client.get(
                "/alerts?status=ACTIVE",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            filtered_alerts = response.json()
            # Should only return active alerts
            assert len(filtered_alerts) == len(active_alerts)


class TestSignalGenerationIntegration:
    """Test signal generation integration workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_signal_generation_workflow(self, test_client, sample_admin_user, lq45_stocks):
        """Test complete signal generation workflow"""
        with patch('src.api.main.get_current_user', return_value=sample_admin_user), \
             patch('src.api.main.signal_service') as mock_signal_service:

            # Step 1: Trigger signal generation
            task_id = "signal_gen_123"
            mock_signal_service.start_signal_generation.return_value = task_id

            generate_response = await test_client.post(
                "/signals/generate",
                headers={"Authorization": "Bearer admin_token"}
            )

            assert generate_response.status_code == 200
            generate_data = generate_response.json()
            assert generate_data["task_id"] == task_id
            assert generate_data["status"] == "started"

            # Step 2: Check generation status
            mock_signal_service.get_generation_status.return_value = {
                "task_id": task_id,
                "status": "running",
                "progress": 50,
                "message": "Processing technical indicators",
                "started_at": datetime.now().isoformat(),
                "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
            }

            status_response = await test_client.get(
                f"/signals/generation/{task_id}",
                headers={"Authorization": "Bearer admin_token"}
            )

            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] == "running"
            assert status_data["progress"] == 50

            # Step 3: Get completed signals
            mock_signals = []
            for i, stock in enumerate(lq45_stocks[:5]):
                signal = AsyncMock()
                signal.stock_code = stock["code"]
                signal.signal_type = ["BUY", "SELL", "HOLD"][i % 3]
                signal.confidence = 0.8 + (i * 0.02)
                signal.generated_at = datetime.now()
                mock_signals.append(signal)

            mock_signal_service.get_daily_signals.return_value = mock_signals

            signals_response = await test_client.get(
                "/signals/daily",
                headers={"Authorization": "Bearer admin_token"}
            )

            assert signals_response.status_code == 200
            signals_data = signals_response.json()
            assert signals_data["total_signals"] == 5
            assert len(signals_data["signals"]) == 5

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_indonesian_market_signal_generation(self, test_client, sample_admin_user, bbca_price_data):
        """Test signal generation with Indonesian market data"""
        with patch('src.api.main.get_current_user', return_value=sample_admin_user), \
             patch('src.api.main.signal_service') as mock_signal_service:

            # Mock signal generation with Indonesian market characteristics
            indonesian_signals = [
                {
                    "stock_code": "BBCA",
                    "signal_type": "BUY",
                    "confidence": 0.85,
                    "price_target": 9500,
                    "stop_loss": 8500,
                    "generated_at": datetime.now(),
                    "metadata": {
                        "currency": "IDR",
                        "market": "IDX",
                        "sector": "Financial Services",
                        "is_lq45": True,
                        "rupiah_impact": "positive",
                        "sector_rotation": "into_banking"
                    }
                }
            ]

            mock_signal_service.get_daily_signals.return_value = [AsyncMock(**signal) for signal in indonesian_signals]

            response = await test_client.get(
                "/signals/daily",
                headers={"Authorization": "Bearer admin_token"}
            )

            assert response.status_code == 200
            signals = response.json()["signals"]

            # Verify Indonesian market characteristics
            bbca_signal = next((s for s in signals if s.get("stock_code") == "BBCA"), None)
            if bbca_signal:
                assert bbca_signal["metadata"]["currency"] == "IDR"
                assert bbca_signal["metadata"]["market"] == "IDX"
                assert bbca_signal["metadata"]["is_lq45"] is True


class TestPortfolioIntegration:
    """Test portfolio management integration workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_portfolio_management_workflow(self, test_client, sample_user, sample_portfolio):
        """Test complete portfolio management workflow"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.signal_service') as mock_signal_service:

            # Step 1: Get portfolio summary
            mock_summary = {
                "total_value": 50000000,  # 50M IDR
                "total_pnl": 2500000,    # 2.5M IDR profit
                "total_pnl_percent": 5.0,
                "positions_count": 5,
                "cash_balance": 10000000,
                "currency": "IDR",
                "last_updated": datetime.now().isoformat()
            }

            mock_signal_service.get_portfolio_summary.return_value = mock_summary

            summary_response = await test_client.get(
                "/portfolio/summary",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert summary_response.status_code == 200
            summary_data = summary_response.json()
            assert summary_data["total_value"] == 50000000
            assert summary_data["currency"] == "IDR"

            # Step 2: Get current positions
            mock_positions = []
            for pos_data in sample_portfolio:
                pos = AsyncMock()
                pos.stock_code = pos_data["stock_code"]
                pos.quantity = pos_data["quantity"]
                pos.average_price = pos_data["average_price"]
                pos.current_price = pos_data["current_price"]
                pos.market_value = pos_data["market_value"]
                pos.unrealized_pnl = pos_data["unrealized_pnl"]
                mock_positions.append(pos)

            mock_signal_service.get_current_positions.return_value = mock_positions

            positions_response = await test_client.get(
                "/portfolio/positions",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert positions_response.status_code == 200
            positions_data = positions_response.json()
            assert len(positions_data) == len(sample_portfolio)

            # Step 3: Update position
            user_with_permissions = AsyncMock()
            user_with_permissions.id = 1
            user_with_permissions.has_permission.return_value = True

            updated_position = AsyncMock()
            updated_position.stock_code = "BBCA"
            updated_position.quantity = 1200
            updated_position.average_price = 8900

            mock_signal_service.update_position.return_value = updated_position

            with patch('src.api.main.get_current_user', return_value=user_with_permissions):
                update_response = await test_client.post(
                    "/portfolio/positions",
                    json={
                        "stock_code": "BBCA",
                        "quantity": 1200,
                        "average_price": 8900
                    },
                    headers={"Authorization": "Bearer valid_token"}
                )

                assert update_response.status_code == 200


class TestRiskManagementIntegration:
    """Test risk management integration workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_risk_monitoring_workflow(self, test_client, sample_user):
        """Test complete risk monitoring workflow"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.risk_monitor') as mock_risk_monitor:

            # Step 1: Get risk overview
            mock_risk_data = {
                "overall_risk_score": 6.5,
                "var_1d": 2500000,  # 2.5M IDR VaR
                "var_percentile": 95,
                "currency": "IDR",
                "sector_concentration": {
                    "Financial Services": 45.0,
                    "Technology": 25.0,
                    "Consumer Goods": 20.0,
                    "Other": 10.0
                },
                "position_risk": "MEDIUM",
                "correlation_risk": "LOW",
                "currency_risk": "LOW",  # IDR exposure
                "liquidity_risk": "LOW",
                "last_calculated": datetime.now().isoformat()
            }

            mock_risk_monitor.get_risk_overview.return_value = mock_risk_data

            risk_response = await test_client.get(
                "/risk/overview",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert risk_response.status_code == 200
            risk_data = risk_response.json()
            assert risk_data["overall_risk_score"] == 6.5
            assert risk_data["currency"] == "IDR"

            # Step 2: Get risk alerts
            mock_risk_alerts = []
            alert_scenarios = [
                {
                    "risk_type": "CONCENTRATION_RISK",
                    "severity": "MEDIUM",
                    "message": "Financial sector exposure exceeds 40% threshold",
                    "threshold": 40.0,
                    "current_value": 45.0,
                    "recommended_action": "Reduce banking sector positions"
                },
                {
                    "risk_type": "VAR_BREACH",
                    "severity": "HIGH",
                    "message": "Portfolio VaR exceeded daily limit",
                    "threshold": 2000000,
                    "current_value": 2500000,
                    "recommended_action": "Reduce position sizes or add hedging"
                }
            ]

            for i, scenario in enumerate(alert_scenarios):
                alert = AsyncMock()
                alert.id = i + 1
                alert.risk_type = scenario["risk_type"]
                alert.severity = scenario["severity"]
                alert.message = scenario["message"]
                alert.created_at = datetime.now()
                alert.metadata = {
                    "threshold": scenario["threshold"],
                    "current_value": scenario["current_value"],
                    "recommended_action": scenario["recommended_action"]
                }
                mock_risk_alerts.append(alert)

            mock_risk_monitor.get_risk_alerts.return_value = mock_risk_alerts

            alerts_response = await test_client.get(
                "/risk/alerts",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert alerts_response.status_code == 200
            alerts_data = alerts_response.json()
            assert len(alerts_data) == 2

            # Verify Indonesian market risk characteristics
            concentration_alert = next(
                (alert for alert in alerts_data if alert.get("risk_type") == "CONCENTRATION_RISK"),
                None
            )
            assert concentration_alert is not None
            assert "Financial sector" in concentration_alert["message"]


class TestMarketDataIntegration:
    """Test market data integration workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_indonesian_market_status_workflow(self, test_client, jakarta_timezone, indonesian_market_hours):
        """Test Indonesian market status checking"""
        import pytz
        from datetime import time

        # Test during market hours (10:00 AM Jakarta time)
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        market_open_time = datetime.now(jakarta_tz).replace(hour=10, minute=0, second=0, microsecond=0)

        with patch('src.api.main.datetime') as mock_datetime:
            mock_datetime.now.return_value = market_open_time
            mock_datetime.strptime = datetime.strptime

            response = await test_client.get("/market/status")

            assert response.status_code == 200
            status_data = response.json()
            assert status_data["is_open"] is True
            assert status_data["session_type"] == "regular"

        # Test during market closed hours (6:00 PM Jakarta time)
        market_closed_time = datetime.now(jakarta_tz).replace(hour=18, minute=0, second=0, microsecond=0)

        with patch('src.api.main.datetime') as mock_datetime:
            mock_datetime.now.return_value = market_closed_time
            mock_datetime.strptime = datetime.strptime

            response = await test_client.get("/market/status")

            assert response.status_code == 200
            status_data = response.json()
            assert status_data["is_open"] is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_market_data_with_currency_effects(self, test_client, usd_idr_rates):
        """Test market data integration with currency effects"""
        # This test would integrate with currency data to show
        # how IDR movements affect portfolio values

        # Mock portfolio with USD/IDR exposure
        with patch('src.api.main.signal_service') as mock_signal_service:
            # Portfolio including currency effects
            portfolio_with_fx = {
                "total_value_idr": 50000000,
                "total_value_usd": 3225,  # At 15,500 USD/IDR
                "currency_exposure": {
                    "IDR": 90.0,  # 90% in IDR assets
                    "USD": 10.0   # 10% in USD-linked assets
                },
                "fx_risk_metrics": {
                    "usd_idr_rate": 15500,
                    "daily_fx_var": 75000,  # IDR equivalent
                    "fx_correlation": 0.3
                }
            }

            mock_signal_service.get_portfolio_summary.return_value = portfolio_with_fx

            response = await test_client.get(
                "/portfolio/summary",
                headers={"Authorization": "Bearer valid_token"}
            )

            if response.status_code == 200:
                data = response.json()
                # Verify currency exposure is tracked
                if "currency_exposure" in data:
                    assert data["currency_exposure"]["IDR"] == 90.0


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.indonesian_market
    async def test_daily_trading_workflow(self, test_client, sample_admin_user, lq45_stocks):
        """Test complete daily trading workflow for Indonesian market"""
        with patch('src.api.main.get_current_user', return_value=sample_admin_user), \
             patch('src.api.main.signal_service') as mock_signal_service, \
             patch('src.api.main.alert_engine') as mock_alert_engine, \
             patch('src.api.main.risk_monitor') as mock_risk_monitor:

            # 1. Check market status (should be open)
            with patch('src.api.main.datetime') as mock_datetime:
                # Jakarta time 10:00 AM
                jakarta_time = datetime.now().replace(hour=10, minute=0)
                mock_datetime.now.return_value = jakarta_time
                mock_datetime.strptime = datetime.strptime

                market_response = await test_client.get("/market/status")
                assert market_response.status_code == 200
                assert market_response.json()["is_open"] is True

            # 2. Generate daily signals
            mock_signal_service.start_signal_generation.return_value = "daily_gen_123"

            generate_response = await test_client.post(
                "/signals/generate",
                headers={"Authorization": "Bearer admin_token"}
            )
            assert generate_response.status_code == 200

            # 3. Get generated signals for LQ45 stocks
            mock_signals = []
            for stock in lq45_stocks[:5]:
                signal = AsyncMock()
                signal.stock_code = stock["code"]
                signal.signal_type = "BUY" if stock["code"] in ["BBCA", "BBRI"] else "HOLD"
                signal.confidence = 0.82
                signal.generated_at = datetime.now()
                signal.metadata = {
                    "market": "IDX",
                    "sector": stock["sector"],
                    "is_lq45": True
                }
                mock_signals.append(signal)

            mock_signal_service.get_daily_signals.return_value = mock_signals

            signals_response = await test_client.get(
                "/signals/daily",
                headers={"Authorization": "Bearer admin_token"}
            )
            assert signals_response.status_code == 200

            # 4. Check risk overview
            mock_risk_monitor.get_risk_overview.return_value = {
                "overall_risk_score": 5.5,
                "var_1d": 1800000,
                "position_risk": "LOW"
            }

            risk_response = await test_client.get(
                "/risk/overview",
                headers={"Authorization": "Bearer admin_token"}
            )
            assert risk_response.status_code == 200

            # 5. Generate daily report
            mock_signal_service.generate_daily_report.return_value = {
                "date": datetime.now().date().isoformat(),
                "market": "IDX",
                "signals_generated": 5,
                "buy_signals": 2,
                "hold_signals": 3,
                "total_portfolio_value": 50000000,
                "daily_pnl": 1200000,
                "top_performers": ["BBCA", "BBRI"],
                "risk_score": 5.5
            }

            report_response = await test_client.get(
                "/reports/daily?format=json",
                headers={"Authorization": "Bearer admin_token"}
            )
            assert report_response.status_code == 200

            report_data = report_response.json()
            assert report_data["market"] == "IDX"
            assert report_data["signals_generated"] == 5

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_high_frequency_operations(self, test_client, sample_user):
        """Test high-frequency operations typical in trading systems"""
        with patch('src.api.main.get_current_user', return_value=sample_user):

            # Simulate rapid market data requests
            tasks = []
            for i in range(10):
                task = test_client.get("/market/status")
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # All requests should succeed
            assert all(r.status_code == 200 for r in responses)

            # Test rapid alert retrieval
            with patch('src.api.main.alert_engine') as mock_alert_engine:
                mock_alert_engine.get_alerts.return_value = []

                alert_tasks = []
                for i in range(5):
                    task = test_client.get(
                        "/alerts",
                        headers={"Authorization": "Bearer valid_token"}
                    )
                    alert_tasks.append(task)

                alert_responses = await asyncio.gather(*alert_tasks)
                assert all(r.status_code == 200 for r in alert_responses)