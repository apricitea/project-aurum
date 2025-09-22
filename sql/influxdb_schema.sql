-- Project Aurum - InfluxDB Schema for Time-Series Market Data
-- Indonesian Stock Exchange (IDX) Trading System
-- InfluxDB 2.0 Schema Definition

-- Note: This file contains InfluxDB CLI commands and Flux queries
-- Execute these commands using the InfluxDB CLI or API

-- ============================================================================
-- DATABASE AND RETENTION POLICIES SETUP
-- ============================================================================

-- Create bucket for market data (InfluxDB 2.0 uses buckets instead of databases)
-- Bucket name: market_data
-- Organization: project_aurum
-- Retention period: 7 years (2555 days)

-- CLI command to create bucket:
-- influx bucket create --name market_data --retention 2555d --org project_aurum

-- ============================================================================
-- RETENTION POLICIES (as bucket configurations)
-- ============================================================================

-- Real-time data (1 day retention) - for live trading
-- influx bucket create --name market_data_realtime --retention 1d --org project_aurum

-- Minute data (30 days retention) - for short-term analysis
-- influx bucket create --name market_data_minute --retention 30d --org project_aurum

-- Hourly data (1 year retention) - for medium-term analysis
-- influx bucket create --name market_data_hourly --retention 365d --org project_aurum

-- Daily data (7 years retention) - for long-term backtesting
-- influx bucket create --name market_data_daily --retention 2555d --org project_aurum

-- ============================================================================
-- MEASUREMENT SCHEMAS
-- ============================================================================

-- 1. TRADES MEASUREMENT
-- Stores individual trade transactions
-- Measurement: trades
-- Tags: symbol, exchange, session_type, trade_condition
-- Fields: price, volume, trade_value, bid, ask, bid_size, ask_size

-- Example trade record:
-- trades,symbol=BBCA,exchange=IDX,session_type=REGULAR,trade_condition=NORMAL
--   price=8750.0,volume=100,trade_value=875000.0,bid=8725.0,ask=8750.0,bid_size=500,ask_size=300
--   1640995200000000000

-- 2. QUOTES MEASUREMENT
-- Stores best bid/offer updates
-- Measurement: quotes
-- Tags: symbol, exchange, quote_type
-- Fields: bid_price, ask_price, bid_size, ask_size, spread, mid_price

-- Example quote record:
-- quotes,symbol=BBCA,exchange=IDX,quote_type=LEVEL1
--   bid_price=8725.0,ask_price=8750.0,bid_size=500,ask_size=300,spread=25.0,mid_price=8737.5
--   1640995200000000000

-- 3. ORDER_BOOK MEASUREMENT
-- Stores order book snapshots (Level 2 data)
-- Measurement: order_book
-- Tags: symbol, exchange, side
-- Fields: price_1 through price_10, size_1 through size_10, level_count

-- Example order book record:
-- order_book,symbol=BBCA,exchange=IDX,side=BID
--   price_1=8725.0,size_1=500,price_2=8700.0,size_2=1000,price_3=8675.0,size_3=1500,level_count=10
--   1640995200000000000

-- 4. OHLCV MEASUREMENT
-- Stores aggregated OHLCV data at various timeframes
-- Measurement: ohlcv
-- Tags: symbol, exchange, timeframe, session_type
-- Fields: open, high, low, close, volume, trade_count, vwap, typical_price

-- Example OHLCV record:
-- ohlcv,symbol=BBCA,exchange=IDX,timeframe=1m,session_type=REGULAR
--   open=8725.0,high=8750.0,low=8700.0,close=8750.0,volume=5000,trade_count=25,vwap=8735.5,typical_price=8733.33
--   1640995200000000000

-- 5. TECHNICAL_INDICATORS MEASUREMENT
-- Stores computed technical indicators
-- Measurement: technical_indicators
-- Tags: symbol, indicator_name, timeframe, parameter_set
-- Fields: value, signal, upper_band, lower_band, signal_line

-- Example technical indicator record:
-- technical_indicators,symbol=BBCA,indicator_name=RSI,timeframe=1d,parameter_set=14
--   value=65.5,signal=0
--   1640995200000000000

-- 6. MARKET_STATISTICS MEASUREMENT
-- Stores market-wide statistics
-- Measurement: market_statistics
-- Tags: statistic_type, exchange, index_code
-- Fields: value, change, change_percent, volume, market_cap

-- Example market statistics record:
-- market_statistics,statistic_type=INDEX,exchange=IDX,index_code=IHSG
--   value=6950.23,change=45.67,change_percent=0.66,volume=8500000000,market_cap=8750000000000000
--   1640995200000000000

-- 7. CORPORATE_EVENTS MEASUREMENT
-- Stores time-stamped corporate events
-- Measurement: corporate_events
-- Tags: symbol, event_type, exchange
-- Fields: adjustment_factor, dividend_amount, split_ratio, event_details

-- Example corporate event record:
-- corporate_events,symbol=BBCA,event_type=DIVIDEND,exchange=IDX
--   dividend_amount=310.0,event_details="Regular dividend payment"
--   1640995200000000000

-- ============================================================================
-- CONTINUOUS QUERIES (InfluxDB 2.0 Tasks)
-- ============================================================================

-- Task 1: Aggregate trades to 1-minute OHLCV
-- File: tasks/aggregate_1m_ohlcv.flux

option task = {
    name: "aggregate_1m_ohlcv",
    every: 1m,
    offset: 30s
}

from(bucket: "market_data_realtime")
    |> range(start: -2m, stop: -1m)
    |> filter(fn: (r) => r._measurement == "trades")
    |> filter(fn: (r) => r._field == "price" or r._field == "volume")
    |> group(columns: ["symbol", "exchange", "session_type"])
    |> aggregateWindow(
        every: 1m,
        fn: (tables=<-, column) =>
            if column == "price" then
                tables |> duplicate(column: "_value", as: "temp_price")
                |> group()
                |> reduce(
                    identity: {open: 0.0, high: 0.0, low: 999999.0, close: 0.0, count: 0},
                    fn: (r, accumulator) => ({
                        open: if accumulator.count == 0 then r.temp_price else accumulator.open,
                        high: if r.temp_price > accumulator.high then r.temp_price else accumulator.high,
                        low: if r.temp_price < accumulator.low then r.temp_price else accumulator.low,
                        close: r.temp_price,
                        count: accumulator.count + 1
                    })
                )
            else
                tables |> sum(column: "_value"),
        createEmpty: false
    )
    |> to(bucket: "market_data_minute", org: "project_aurum")

-- Task 2: Calculate technical indicators
-- File: tasks/calculate_rsi.flux

option task = {
    name: "calculate_rsi_daily",
    every: 1d,
    offset: 30m
}

rsi_period = 14

from(bucket: "market_data_daily")
    |> range(start: -30d)
    |> filter(fn: (r) => r._measurement == "ohlcv")
    |> filter(fn: (r) => r._field == "close")
    |> filter(fn: (r) => r.timeframe == "1d")
    |> group(columns: ["symbol"])
    |> sort(columns: ["_time"])
    |> difference(nonNegative: false, columns: ["_value"])
    |> map(fn: (r) => ({
        r with
        gain: if r._value > 0.0 then r._value else 0.0,
        loss: if r._value < 0.0 then math.abs(x: r._value) else 0.0
    }))
    |> movingAverage(n: rsi_period, column: "gain")
    |> movingAverage(n: rsi_period, column: "loss")
    |> map(fn: (r) => ({
        r with
        rs: r.gain / r.loss,
        rsi: 100.0 - (100.0 / (1.0 + (r.gain / r.loss)))
    }))
    |> filter(fn: (r) => exists r.rsi)
    |> map(fn: (r) => ({
        _time: r._time,
        _measurement: "technical_indicators",
        _field: "value",
        _value: r.rsi,
        symbol: r.symbol,
        indicator_name: "RSI",
        timeframe: "1d",
        parameter_set: string(v: rsi_period)
    }))
    |> to(bucket: "market_data_daily", org: "project_aurum")

-- Task 3: Downsample minute data to hourly
-- File: tasks/downsample_hourly.flux

option task = {
    name: "downsample_hourly",
    every: 1h,
    offset: 5m
}

from(bucket: "market_data_minute")
    |> range(start: -2h, stop: -1h)
    |> filter(fn: (r) => r._measurement == "ohlcv")
    |> group(columns: ["symbol", "exchange", "session_type"])
    |> aggregateWindow(
        every: 1h,
        fn: (tables=<-, column) =>
            if column == "open" then tables |> first(column: "_value")
            else if column == "high" then tables |> max(column: "_value")
            else if column == "low" then tables |> min(column: "_value")
            else if column == "close" then tables |> last(column: "_value")
            else tables |> sum(column: "_value"),
        createEmpty: false
    )
    |> map(fn: (r) => ({r with timeframe: "1h"}))
    |> to(bucket: "market_data_hourly", org: "project_aurum")

-- Task 4: Downsample hourly data to daily
-- File: tasks/downsample_daily.flux

option task = {
    name: "downsample_daily",
    every: 1d,
    offset: 30m
}

from(bucket: "market_data_hourly")
    |> range(start: -2d, stop: -1d)
    |> filter(fn: (r) => r._measurement == "ohlcv")
    |> filter(fn: (r) => r.session_type == "REGULAR")
    |> group(columns: ["symbol", "exchange"])
    |> aggregateWindow(
        every: 1d,
        fn: (tables=<-, column) =>
            if column == "open" then tables |> first(column: "_value")
            else if column == "high" then tables |> max(column: "_value")
            else if column == "low" then tables |> min(column: "_value")
            else if column == "close" then tables |> last(column: "_value")
            else tables |> sum(column: "_value"),
        createEmpty: false
    )
    |> map(fn: (r) => ({r with timeframe: "1d", session_type: "REGULAR"}))
    |> to(bucket: "market_data_daily", org: "project_aurum")

-- ============================================================================
-- DATA VALIDATION QUERIES
-- ============================================================================

-- Query 1: Check for missing data gaps
-- File: queries/check_data_gaps.flux

check_gaps = (symbol, start_time, end_time) => {
    expected_points = from(bucket: "market_data_minute")
        |> range(start: start_time, stop: end_time)
        |> filter(fn: (r) => r._measurement == "ohlcv")
        |> filter(fn: (r) => r.symbol == symbol)
        |> filter(fn: (r) => r._field == "close")
        |> count()
        |> findRecord(fn: (key) => true, idx: 0)

    actual_points = int(v: (time(v: end_time) - time(v: start_time)) / 1m)

    return {
        symbol: symbol,
        expected: actual_points,
        actual: expected_points._value,
        missing: actual_points - expected_points._value,
        completeness_percent: float(v: expected_points._value) / float(v: actual_points) * 100.0
    }
}

-- Query 2: Detect price anomalies
-- File: queries/detect_anomalies.flux

from(bucket: "market_data_minute")
    |> range(start: -1d)
    |> filter(fn: (r) => r._measurement == "ohlcv")
    |> filter(fn: (r) => r._field == "close")
    |> group(columns: ["symbol"])
    |> sort(columns: ["_time"])
    |> map(fn: (r) => ({r with prev_close: 0.0}))
    |> reduce(
        identity: {symbol: "", _time: 1970-01-01T00:00:00Z, close: 0.0, prev_close: 0.0},
        fn: (r, accumulator) => ({
            symbol: r.symbol,
            _time: r._time,
            close: r._value,
            prev_close: accumulator.close,
            price_change: if accumulator.close > 0.0 then (r._value - accumulator.close) / accumulator.close * 100.0 else 0.0
        })
    )
    |> filter(fn: (r) => math.abs(x: r.price_change) > 10.0) // Flag 10%+ moves
    |> map(fn: (r) => ({
        _time: r._time,
        _measurement: "data_quality_alerts",
        _field: "price_change_percent",
        _value: r.price_change,
        symbol: r.symbol,
        alert_type: "PRICE_ANOMALY",
        severity: if math.abs(x: r.price_change) > 20.0 then "HIGH" else "MEDIUM"
    }))

-- Query 3: Calculate market statistics
-- File: queries/market_statistics.flux

// Calculate IHSG index value based on constituent weights
from(bucket: "market_data_minute")
    |> range(start: -1m)
    |> filter(fn: (r) => r._measurement == "ohlcv")
    |> filter(fn: (r) => r._field == "close")
    |> filter(fn: (r) => contains(value: r.symbol, set: ["BBCA", "BMRI", "TLKM", "ASII"])) // Example constituents
    |> group(columns: ["_time"])
    |> mean(column: "_value") // Simplified calculation
    |> map(fn: (r) => ({
        _time: r._time,
        _measurement: "market_statistics",
        _field: "value",
        _value: r._value,
        statistic_type: "INDEX",
        exchange: "IDX",
        index_code: "IHSG"
    }))
    |> to(bucket: "market_data_minute", org: "project_aurum")

-- ============================================================================
-- PERFORMANCE QUERIES
-- ============================================================================

-- Query 1: Get latest prices for multiple symbols
-- File: queries/latest_prices.flux

symbols = ["BBCA", "BMRI", "TLKM", "ASII", "UNVR"]

from(bucket: "market_data_realtime")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "trades" or r._measurement == "quotes")
    |> filter(fn: (r) => contains(value: r.symbol, set: symbols))
    |> filter(fn: (r) => r._field == "price" or r._field == "mid_price")
    |> group(columns: ["symbol"])
    |> last()
    |> group()
    |> sort(columns: ["symbol"])

-- Query 2: Get OHLCV data with volume
-- File: queries/ohlcv_data.flux

get_ohlcv = (symbol, timeframe, start_time, end_time) => {
    return from(bucket: "market_data_minute")
        |> range(start: start_time, stop: end_time)
        |> filter(fn: (r) => r._measurement == "ohlcv")
        |> filter(fn: (r) => r.symbol == symbol)
        |> filter(fn: (r) => r.timeframe == timeframe)
        |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"])
}

-- Query 3: Calculate intraday statistics
-- File: queries/intraday_stats.flux

from(bucket: "market_data_minute")
    |> range(start: today())
    |> filter(fn: (r) => r._measurement == "ohlcv")
    |> filter(fn: (r) => r.timeframe == "1m")
    |> group(columns: ["symbol"])
    |> reduce(
        identity: {
            symbol: "",
            open: 0.0,
            high: 0.0,
            low: 999999.0,
            close: 0.0,
            volume: 0,
            trade_count: 0,
            vwap_num: 0.0,
            vwap_den: 0.0
        },
        fn: (r, accumulator) => ({
            symbol: r.symbol,
            open: if accumulator.trade_count == 0 then r._value else accumulator.open,
            high: if r._field == "high" and r._value > accumulator.high then r._value else accumulator.high,
            low: if r._field == "low" and r._value < accumulator.low then r._value else accumulator.low,
            close: if r._field == "close" then r._value else accumulator.close,
            volume: if r._field == "volume" then accumulator.volume + int(v: r._value) else accumulator.volume,
            trade_count: if r._field == "trade_count" then accumulator.trade_count + int(v: r._value) else accumulator.trade_count,
            vwap_num: if r._field == "close" and exists r.volume then accumulator.vwap_num + (r._value * float(v: r.volume)) else accumulator.vwap_num,
            vwap_den: if r._field == "volume" then accumulator.vwap_den + float(v: r._value) else accumulator.vwap_den
        })
    )
    |> map(fn: (r) => ({
        r with
        vwap: if r.vwap_den > 0.0 then r.vwap_num / r.vwap_den else 0.0,
        change: r.close - r.open,
        change_percent: if r.open > 0.0 then (r.close - r.open) / r.open * 100.0 else 0.0
    }))

-- ============================================================================
-- MONITORING AND ALERTING QUERIES
-- ============================================================================

-- Query 1: Data ingestion rate monitoring
-- File: queries/ingestion_monitoring.flux

from(bucket: "market_data_realtime")
    |> range(start: -5m)
    |> filter(fn: (r) => r._measurement == "trades")
    |> group(columns: ["symbol"])
    |> count()
    |> group()
    |> sum()
    |> map(fn: (r) => ({
        _time: now(),
        _measurement: "system_metrics",
        _field: "trades_per_5min",
        _value: r._value,
        metric_type: "INGESTION_RATE"
    }))

-- Query 2: System health check
-- File: queries/system_health.flux

latest_data_age = from(bucket: "market_data_realtime")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "trades")
    |> group()
    |> last()
    |> map(fn: (r) => ({
        _time: now(),
        _measurement: "system_metrics",
        _field: "latest_data_age_seconds",
        _value: float(v: uint(v: now()) - uint(v: r._time)) / 1000000000.0,
        metric_type: "DATA_FRESHNESS"
    }))

-- ============================================================================
-- BACKUP AND RECOVERY COMMANDS
-- ============================================================================

-- Full backup command (to be run via CLI):
-- influx backup --bucket market_data_realtime /backup/influxdb/realtime/$(date +%Y%m%d)
-- influx backup --bucket market_data_minute /backup/influxdb/minute/$(date +%Y%m%d)
-- influx backup --bucket market_data_hourly /backup/influxdb/hourly/$(date +%Y%m%d)
-- influx backup --bucket market_data_daily /backup/influxdb/daily/$(date +%Y%m%d)

-- Restore command:
-- influx restore --bucket market_data_realtime /backup/influxdb/realtime/20240101/

-- ============================================================================
-- INDEX OPTIMIZATION
-- ============================================================================

-- InfluxDB automatically creates indexes on tags
-- Ensure proper tag design for query performance:
-- 1. Use high-cardinality fields as tags (symbol, exchange)
-- 2. Use low-cardinality metadata as tags (timeframe, session_type)
-- 3. Use numeric/time series data as fields (price, volume)
-- 4. Avoid high-cardinality tags (trade_id, timestamp strings)

-- ============================================================================
-- NOTES FOR IMPLEMENTATION
-- ============================================================================

-- 1. All timestamps should be in UTC and converted to Jakarta time in application layer
-- 2. Use nanosecond precision for high-frequency data
-- 3. Implement proper error handling for data validation
-- 4. Set up monitoring for bucket sizes and query performance
-- 5. Configure data compression for long-term storage
-- 6. Implement data purging policies for different retention periods
-- 7. Use batch writes for high-throughput ingestion
-- 8. Monitor memory usage for continuous queries and tasks