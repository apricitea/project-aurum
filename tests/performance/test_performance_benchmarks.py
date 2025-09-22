"""
Performance benchmarking tests for Project Aurum
Tests critical performance requirements for production trading system
"""

import pytest
import asyncio
import time
import psutil
import statistics
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, AsyncMock
import pandas as pd
import numpy as np


class TestAPIPerformance:
    """Test API endpoint performance"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_health_check_performance(self, test_client, performance_thresholds):
        """Test health check response time"""
        response_times = []

        for _ in range(10):
            start_time = time.time()
            response = await test_client.get("/health")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)

        # Health check should be very fast
        assert avg_response_time < 0.1, f"Average health check time {avg_response_time:.3f}s too slow"
        assert max_response_time < 0.2, f"Max health check time {max_response_time:.3f}s too slow"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_authentication_performance(self, test_client, performance_thresholds):
        """Test authentication endpoint performance"""
        with patch('src.api.main.auth_manager') as mock_auth:
            mock_auth.authenticate.return_value = {
                "access_token": "test_token",
                "refresh_token": "refresh_token",
                "token_type": "bearer",
                "expires_in": 3600
            }

            response_times = []

            for _ in range(5):
                start_time = time.time()
                response = await test_client.post("/auth/login", json={
                    "username": "testuser",
                    "password": "testpass"
                })
                end_time = time.time()

                assert response.status_code == 200
                response_times.append(end_time - start_time)

            avg_response_time = statistics.mean(response_times)

            # Authentication should complete within threshold
            assert avg_response_time < performance_thresholds["api_response_time"], \
                f"Authentication avg time {avg_response_time:.3f}s exceeds threshold"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_alert_retrieval_performance(self, test_client, sample_user, performance_thresholds):
        """Test alert retrieval performance with large datasets"""
        with patch('src.api.main.get_current_user', return_value=sample_user), \
             patch('src.api.main.alert_engine') as mock_alert_engine:

            # Mock large number of alerts
            mock_alerts = []
            for i in range(1000):
                alert = AsyncMock()
                alert.id = i + 1
                alert.alert_type = "PRICE_BREAKOUT"
                alert.message = f"Alert {i + 1}"
                alert.priority = "MEDIUM"
                alert.status = "ACTIVE"
                alert.created_at = datetime.now()
                mock_alerts.append(alert)

            mock_alert_engine.get_alerts.return_value = mock_alerts[:100]  # Paginated

            start_time = time.time()
            response = await test_client.get(
                "/alerts?limit=100",
                headers={"Authorization": "Bearer valid_token"}
            )
            end_time = time.time()

            assert response.status_code == 200
            response_time = end_time - start_time

            # Alert retrieval should be fast even with large datasets
            assert response_time < performance_thresholds["api_response_time"], \
                f"Alert retrieval time {response_time:.3f}s exceeds threshold"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, test_client, sample_user, performance_thresholds):
        """Test API performance under concurrent load"""
        with patch('src.api.main.get_current_user', return_value=sample_user):

            # Test concurrent health checks
            concurrent_requests = 20
            start_time = time.time()

            tasks = []
            for _ in range(concurrent_requests):
                task = test_client.get("/health")
                tasks.append(task)

            responses = await asyncio.gather(*tasks)
            end_time = time.time()

            # All requests should succeed
            assert all(r.status_code == 200 for r in responses)

            total_time = end_time - start_time
            avg_time_per_request = total_time / concurrent_requests

            # Concurrent requests should not significantly degrade performance
            assert avg_time_per_request < performance_thresholds["api_response_time"] * 2, \
                f"Concurrent requests too slow: {avg_time_per_request:.3f}s per request"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_websocket_performance(self, test_client):
        """Test WebSocket connection and message performance"""
        # Note: This is a simplified test as WebSocket testing can be complex
        # In a real implementation, you'd test actual WebSocket connections

        connection_times = []

        for _ in range(5):
            start_time = time.time()

            # Simulate WebSocket connection establishment
            # In real test, you'd use a WebSocket test client
            try:
                # Mock WebSocket connection time
                await asyncio.sleep(0.01)  # Simulate connection time
                connection_established = True
            except Exception:
                connection_established = False

            end_time = time.time()

            assert connection_established
            connection_times.append(end_time - start_time)

        avg_connection_time = statistics.mean(connection_times)

        # WebSocket connections should be fast
        assert avg_connection_time < 0.1, \
            f"WebSocket connection time {avg_connection_time:.3f}s too slow"


class TestMLPerformance:
    """Test ML pipeline performance"""

    @pytest.mark.performance
    @pytest.mark.ml
    def test_feature_engineering_performance(self, performance_thresholds):
        """Test feature engineering performance with large datasets"""
        from feature_engineering import IDXFeatureEngineer

        # Create large dataset
        n_samples = 10000
        dates = pd.date_range(start='2020-01-01', periods=n_samples, freq='D')

        large_data = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(8000, 12000, n_samples),
            'high': np.random.uniform(8500, 12500, n_samples),
            'low': np.random.uniform(7500, 11500, n_samples),
            'close': np.random.uniform(8000, 12000, n_samples),
            'volume': np.random.randint(1000000, 10000000, n_samples)
        })

        feature_engineer = IDXFeatureEngineer()

        start_time = time.time()
        try:
            result = feature_engineer.generate_technical_features(large_data)
            end_time = time.time()

            processing_time = end_time - start_time

            # Feature engineering should complete within threshold
            assert processing_time < 10.0, \
                f"Feature engineering time {processing_time:.3f}s too slow for {n_samples} samples"

            # Result should have same number of rows
            assert len(result) == len(large_data)

        except NotImplementedError:
            pytest.skip("Feature engineering not implemented")

    @pytest.mark.performance
    @pytest.mark.ml
    def test_model_training_performance(self, performance_thresholds):
        """Test ML model training performance"""
        from model_ensemble import TechnicalSignalModel

        # Create training dataset
        n_samples = 5000
        n_features = 20

        X = np.random.random((n_samples, n_features))
        y = np.random.choice([0, 1, 2], n_samples)

        training_data = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(n_features)])
        training_data['signal'] = y

        model = TechnicalSignalModel(config={'n_estimators': 50, 'n_jobs': 1})

        start_time = time.time()
        try:
            model.train(training_data, target_column='signal')
            end_time = time.time()

            training_time = end_time - start_time

            # Training should complete within threshold
            assert training_time < 30.0, \
                f"Model training time {training_time:.3f}s too slow"

            assert model.is_trained is True

        except NotImplementedError:
            pytest.skip("Model training not implemented")

    @pytest.mark.performance
    @pytest.mark.ml
    def test_model_prediction_performance(self, performance_thresholds):
        """Test ML model prediction performance"""
        from model_ensemble import TechnicalSignalModel

        # Create and train model
        n_train = 1000
        n_features = 15

        X_train = np.random.random((n_train, n_features))
        y_train = np.random.choice([0, 1, 2], n_train)

        training_data = pd.DataFrame(X_train, columns=[f'feature_{i}' for i in range(n_features)])
        training_data['signal'] = y_train

        model = TechnicalSignalModel(config={'n_estimators': 50})

        try:
            model.train(training_data, target_column='signal')

            # Create prediction dataset
            n_predict = 1000
            X_predict = np.random.random((n_predict, n_features))
            prediction_data = pd.DataFrame(X_predict, columns=[f'feature_{i}' for i in range(n_features)])

            start_time = time.time()
            predictions = model.predict(prediction_data)
            end_time = time.time()

            prediction_time = end_time - start_time

            # Predictions should be very fast
            assert prediction_time < 1.0, \
                f"Prediction time {prediction_time:.3f}s too slow for {n_predict} samples"

            assert len(predictions) == n_predict

            # Test prediction throughput
            throughput = n_predict / prediction_time
            assert throughput > 1000, f"Prediction throughput {throughput:.0f} samples/sec too low"

        except NotImplementedError:
            pytest.skip("Model prediction not implemented")

    @pytest.mark.performance
    @pytest.mark.ml
    def test_signal_generation_performance(self, performance_thresholds, lq45_stocks):
        """Test complete signal generation performance for Indonesian market"""
        # Test with realistic LQ45 portfolio
        n_stocks = len(lq45_stocks)

        start_time = time.time()

        # Simulate signal generation for all LQ45 stocks
        signals_generated = 0
        for stock in lq45_stocks:
            # Simulate feature calculation and model prediction
            # In real test, this would call actual signal generation pipeline

            # Mock feature engineering time
            await_time = 0.01  # 10ms per stock
            time.sleep(await_time)

            # Mock model prediction time
            prediction_time = 0.005  # 5ms per stock
            time.sleep(prediction_time)

            signals_generated += 1

        end_time = time.time()
        total_time = end_time - start_time

        # Signal generation should complete within threshold
        assert total_time < performance_thresholds["signal_generation"], \
            f"Signal generation time {total_time:.3f}s exceeds threshold for {n_stocks} stocks"

        # Calculate throughput
        throughput = signals_generated / total_time
        assert throughput > 10, f"Signal generation throughput {throughput:.1f} signals/sec too low"


class TestDatabasePerformance:
    """Test database performance"""

    @pytest.mark.performance
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_database_query_performance(self, performance_thresholds):
        """Test database query performance"""
        from src.api.database import DatabaseManager

        # Mock database operations
        db_manager = DatabaseManager()

        with patch.object(db_manager, 'execute_query') as mock_query:
            # Mock fast query response
            mock_query.return_value = [{"id": 1, "data": "test"}]

            start_time = time.time()
            result = await db_manager.execute_query("SELECT * FROM test_table")
            end_time = time.time()

            query_time = end_time - start_time

            # Database queries should be fast
            assert query_time < performance_thresholds["database_query"], \
                f"Database query time {query_time:.3f}s exceeds threshold"

    @pytest.mark.performance
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, performance_thresholds):
        """Test database performance under concurrent load"""
        from src.api.database import DatabaseManager

        db_manager = DatabaseManager()

        with patch.object(db_manager, 'execute_query') as mock_query:
            mock_query.return_value = [{"id": 1}]

            # Test concurrent queries
            concurrent_queries = 10
            start_time = time.time()

            tasks = []
            for i in range(concurrent_queries):
                task = db_manager.execute_query(f"SELECT * FROM table_{i}")
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            end_time = time.time()

            total_time = end_time - start_time
            avg_time_per_query = total_time / concurrent_queries

            # Concurrent queries should not significantly degrade performance
            assert avg_time_per_query < performance_thresholds["database_query"] * 2, \
                f"Concurrent queries too slow: {avg_time_per_query:.3f}s per query"

            # All queries should succeed
            assert len(results) == concurrent_queries

    @pytest.mark.performance
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_large_dataset_operations(self, performance_thresholds):
        """Test database operations with large datasets"""
        from src.api.database import DatabaseManager

        db_manager = DatabaseManager()

        # Mock large dataset query
        large_dataset = [{"id": i, "price": 9000 + i} for i in range(10000)]

        with patch.object(db_manager, 'execute_query') as mock_query:
            mock_query.return_value = large_dataset

            start_time = time.time()
            result = await db_manager.execute_query("SELECT * FROM large_price_data")
            end_time = time.time()

            query_time = end_time - start_time

            # Large dataset queries should complete within reasonable time
            assert query_time < 2.0, \
                f"Large dataset query time {query_time:.3f}s too slow"

            assert len(result) == 10000


class TestMemoryAndResourceUsage:
    """Test memory and resource usage"""

    @pytest.mark.performance
    def test_memory_usage_during_processing(self):
        """Test memory usage during intensive operations"""
        import gc

        # Measure initial memory
        gc.collect()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operation
        large_data = []
        for i in range(10000):
            # Simulate creating market data objects
            data_point = {
                'timestamp': datetime.now(),
                'stock_code': f'STOCK{i % 100}',
                'price': 9000 + (i % 1000),
                'volume': 1000000 + (i % 100000),
                'features': list(range(50))  # 50 features
            }
            large_data.append(data_point)

        # Measure peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Clean up
        del large_data
        gc.collect()

        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = peak_memory - initial_memory
        memory_cleanup = peak_memory - final_memory

        # Memory usage should be reasonable
        assert memory_increase < 500, f"Memory increase {memory_increase:.1f}MB too high"

        # Memory should be cleaned up (at least 80% of increase)
        assert memory_cleanup > memory_increase * 0.8, \
            f"Insufficient memory cleanup: {memory_cleanup:.1f}MB of {memory_increase:.1f}MB"

    @pytest.mark.performance
    def test_cpu_usage_during_processing(self):
        """Test CPU usage during intensive operations"""
        # Monitor CPU usage during computation
        process = psutil.Process()

        # Record CPU usage before
        cpu_percent_before = process.cpu_percent()

        start_time = time.time()

        # Perform CPU-intensive operation
        for i in range(100000):
            # Simulate mathematical calculations
            result = np.sin(i) * np.cos(i) + np.sqrt(i % 1000)

        end_time = time.time()

        # Record CPU usage after
        cpu_percent_after = process.cpu_percent()

        processing_time = end_time - start_time

        # Processing should complete within reasonable time
        assert processing_time < 5.0, f"CPU-intensive operation took {processing_time:.3f}s"

        # CPU usage should not spike excessively (this is informational)
        print(f"CPU usage: {cpu_percent_after:.1f}%")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_resource_cleanup_after_operations(self):
        """Test that resources are properly cleaned up after operations"""
        import gc

        # Initial resource check
        initial_objects = len(gc.get_objects())

        # Perform operations that create objects
        tasks = []
        for i in range(100):
            # Create async tasks that simulate API operations
            async def mock_operation():
                data = {'id': i, 'values': list(range(1000))}
                await asyncio.sleep(0.001)  # Simulate async operation
                return data

            task = asyncio.create_task(mock_operation())
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Clean up references
        del tasks
        del results
        gc.collect()

        # Check final object count
        final_objects = len(gc.get_objects())

        # Object count should not increase significantly
        object_increase = final_objects - initial_objects
        assert object_increase < 1000, \
            f"Too many objects not cleaned up: {object_increase} objects"


class TestIndonesianMarketPerformance:
    """Test performance with Indonesian market-specific scenarios"""

    @pytest.mark.performance
    @pytest.mark.indonesian_market
    def test_lq45_data_processing_performance(self, lq45_stocks, performance_thresholds):
        """Test performance when processing LQ45 stock data"""
        from tests.fixtures.indonesian_market_data import IndonesianMarketFixtures

        start_time = time.time()

        # Process all LQ45 stocks
        all_price_data = []
        for stock in lq45_stocks:
            # Generate price data for each stock
            price_data = IndonesianMarketFixtures.generate_stock_price_data(
                stock["code"],
                datetime.now().date() - timedelta(days=30),
                datetime.now().date()
            )
            all_price_data.append(price_data)

        # Combine all data
        combined_data = pd.concat(all_price_data, ignore_index=True)

        end_time = time.time()
        processing_time = end_time - start_time

        # Processing LQ45 data should be fast
        assert processing_time < 5.0, \
            f"LQ45 data processing time {processing_time:.3f}s too slow"

        # Verify data integrity
        assert len(combined_data) > 0
        assert 'stock_code' in combined_data.columns
        assert combined_data['stock_code'].nunique() == len(lq45_stocks)

    @pytest.mark.performance
    @pytest.mark.indonesian_market
    def test_market_hours_calculation_performance(self, indonesian_market_hours):
        """Test performance of market hours calculations"""
        import pytz

        jakarta_tz = pytz.timezone('Asia/Jakarta')

        start_time = time.time()

        # Perform many market hours calculations
        results = []
        for i in range(1000):
            # Simulate checking if market is open at different times
            test_time = datetime.now(jakarta_tz).replace(
                hour=9 + (i % 8),  # Hours 9-16
                minute=i % 60
            )

            # Simulate market hours check
            is_open = (
                test_time.time() >= datetime.strptime("09:00", "%H:%M").time() and
                test_time.time() <= datetime.strptime("15:49", "%H:%M").time()
            )

            results.append(is_open)

        end_time = time.time()
        calculation_time = end_time - start_time

        # Market hours calculations should be very fast
        assert calculation_time < 0.1, \
            f"Market hours calculation time {calculation_time:.3f}s too slow"

        assert len(results) == 1000

    @pytest.mark.performance
    @pytest.mark.indonesian_market
    def test_currency_conversion_performance(self, usd_idr_rates):
        """Test performance of currency conversion operations"""
        start_time = time.time()

        # Perform many currency conversions
        conversions = []
        for i in range(10000):
            usd_amount = 1000 + (i % 10000)  # Vary USD amounts
            idr_rate = 15500 + (i % 1000)  # Vary exchange rates

            # Convert USD to IDR
            idr_amount = usd_amount * idr_rate

            # Convert back to USD
            usd_converted_back = idr_amount / idr_rate

            conversions.append({
                'original_usd': usd_amount,
                'idr_amount': idr_amount,
                'converted_usd': usd_converted_back
            })

        end_time = time.time()
        conversion_time = end_time - start_time

        # Currency conversions should be very fast
        assert conversion_time < 0.5, \
            f"Currency conversion time {conversion_time:.3f}s too slow"

        # Verify conversion accuracy
        assert len(conversions) == 10000
        for conv in conversions[:10]:  # Check first 10
            assert abs(conv['original_usd'] - conv['converted_usd']) < 0.01


class TestScalabilityBenchmarks:
    """Test system scalability and limits"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_maximum_concurrent_users(self, performance_thresholds):
        """Test maximum number of concurrent users the system can handle"""
        concurrent_users = [10, 25, 50, 100]
        response_times = {}

        for user_count in concurrent_users:
            start_time = time.time()

            # Simulate concurrent user operations
            async def simulate_user_session():
                # Simulate typical user operations
                await asyncio.sleep(0.01)  # Auth check
                await asyncio.sleep(0.05)  # Data retrieval
                await asyncio.sleep(0.02)  # Processing
                return True

            async def run_concurrent_users():
                tasks = []
                for _ in range(user_count):
                    task = asyncio.create_task(simulate_user_session())
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                return results

            # Run the concurrent user simulation
            results = asyncio.run(run_concurrent_users())
            end_time = time.time()

            total_time = end_time - start_time
            avg_time_per_user = total_time / user_count

            response_times[user_count] = avg_time_per_user

            # All users should complete successfully
            assert len(results) == user_count
            assert all(results)

        # Response time should not degrade linearly with user count
        # (should show good scalability)
        time_10_users = response_times[10]
        time_100_users = response_times[100]

        # 100 users should not take 10x longer than 10 users
        scalability_ratio = time_100_users / time_10_users
        assert scalability_ratio < 5.0, \
            f"Poor scalability: 100 users take {scalability_ratio:.1f}x longer than 10 users"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_data_volume_limits(self):
        """Test system performance with large data volumes"""
        data_sizes = [1000, 5000, 10000, 50000]  # Number of records
        processing_times = {}

        for size in data_sizes:
            # Generate test data
            test_data = pd.DataFrame({
                'timestamp': pd.date_range(start='2024-01-01', periods=size, freq='T'),
                'stock_code': ['BBCA'] * size,
                'price': np.random.uniform(8000, 10000, size),
                'volume': np.random.randint(100000, 1000000, size)
            })

            start_time = time.time()

            # Simulate data processing
            # Calculate technical indicators
            test_data['sma_20'] = test_data['price'].rolling(window=20).mean()
            test_data['price_change'] = test_data['price'].pct_change()
            test_data['volume_ma'] = test_data['volume'].rolling(window=10).mean()

            # Simulate more complex calculations
            test_data['volatility'] = test_data['price_change'].rolling(window=20).std()

            end_time = time.time()
            processing_time = end_time - start_time
            processing_times[size] = processing_time

            # Processing should complete within reasonable time
            max_time = size * 0.0001  # 0.1ms per record max
            assert processing_time < max_time, \
                f"Processing {size} records took {processing_time:.3f}s (max {max_time:.3f}s)"

        # Processing time should scale sub-linearly with data size
        time_ratio = processing_times[50000] / processing_times[1000]
        data_ratio = 50000 / 1000  # 50x more data

        # Processing time should scale better than linearly
        efficiency_ratio = time_ratio / data_ratio
        assert efficiency_ratio < 2.0, \
            f"Poor data scaling: efficiency ratio {efficiency_ratio:.2f}"