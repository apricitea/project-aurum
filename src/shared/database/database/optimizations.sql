-- Database optimization scripts for Project Aurum
-- Indonesian Quantitative Trading System database performance improvements

-- =============================================================================
-- INDEXES FOR INDONESIAN STOCK MARKET DATA
-- =============================================================================

-- Primary trading data indexes
CREATE INDEX IF NOT EXISTS idx_stock_prices_code_date ON stock_prices(stock_code, trading_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices(trading_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_prices_volume ON stock_prices(volume DESC) WHERE volume > 0;

-- LQ45 specific indexes (Indonesian Blue Chip Index)
CREATE INDEX IF NOT EXISTS idx_lq45_constituents_active ON lq45_constituents(stock_code, effective_date DESC)
WHERE is_active = true;

-- IDX Composite and sector indexes
CREATE INDEX IF NOT EXISTS idx_stock_metadata_sector ON stock_metadata(sector, sub_sector);
CREATE INDEX IF NOT EXISTS idx_stock_metadata_market_cap ON stock_metadata(market_cap DESC)
WHERE market_cap IS NOT NULL;

-- =============================================================================
-- TRADING SIGNALS AND MODEL PREDICTIONS
-- =============================================================================

-- Trading signals performance indexes
CREATE INDEX IF NOT EXISTS idx_trading_signals_model_date ON trading_signals(model_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_stock_signal ON trading_signals(stock_code, signal_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_confidence ON trading_signals(confidence DESC)
WHERE confidence >= 0.7; -- High confidence signals

-- Model predictions and performance tracking
CREATE INDEX IF NOT EXISTS idx_model_predictions_accuracy ON model_predictions(model_name, prediction_date DESC, accuracy DESC);
CREATE INDEX IF NOT EXISTS idx_model_predictions_stock ON model_predictions(stock_code, prediction_date DESC);

-- Alert system indexes
CREATE INDEX IF NOT EXISTS idx_alerts_priority_status ON alerts(priority, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_user_unread ON alerts(user_id, is_read, created_at DESC)
WHERE is_read = false;

-- =============================================================================
-- PORTFOLIO AND TRADING POSITIONS
-- =============================================================================

-- Portfolio performance indexes
CREATE INDEX IF NOT EXISTS idx_positions_user_active ON positions(user_id, is_active, updated_at DESC)
WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_positions_stock_pnl ON positions(stock_code, unrealized_pnl DESC)
WHERE is_active = true;

-- Trading history for performance analysis
CREATE INDEX IF NOT EXISTS idx_trades_user_date ON trades(user_id, execution_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_stock_profit ON trades(stock_code, profit_loss DESC, execution_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_name, execution_date DESC);

-- =============================================================================
-- INDONESIAN MARKET SPECIFIC INDEXES
-- =============================================================================

-- Indonesian Rupiah (IDR) exchange rates
CREATE INDEX IF NOT EXISTS idx_currency_rates_date ON currency_rates(currency_pair, rate_date DESC)
WHERE currency_pair LIKE '%IDR%';

-- Indonesian trading sessions (considering WIB timezone)
CREATE INDEX IF NOT EXISTS idx_trading_sessions_idx ON trading_sessions(exchange, session_date DESC)
WHERE exchange = 'IDX';

-- Indonesian market holidays and events
CREATE INDEX IF NOT EXISTS idx_market_events_date ON market_events(event_date DESC, market)
WHERE market = 'IDX';

-- Sector rotation analysis (Indonesian sectors)
CREATE INDEX IF NOT EXISTS idx_sector_performance_date ON sector_performance(sector, performance_date DESC);

-- =============================================================================
-- MODEL MONITORING AND DRIFT DETECTION INDEXES
-- =============================================================================

-- Model drift detection data
CREATE INDEX IF NOT EXISTS idx_model_drift_scores_model_date ON model_drift_scores(model_name, measurement_date DESC);
CREATE INDEX IF NOT EXISTS idx_model_drift_scores_severity ON model_drift_scores(drift_severity, measurement_date DESC)
WHERE drift_severity IN ('high', 'critical');

-- Feature drift tracking
CREATE INDEX IF NOT EXISTS idx_feature_drift_model_feature ON feature_drift_log(model_name, feature_name, recorded_at DESC);

-- Model retraining logs
CREATE INDEX IF NOT EXISTS idx_model_retraining_log_date ON model_retraining_log(model_name, retrain_date DESC);

-- =============================================================================
-- ANALYTICS AND REPORTING INDEXES
-- =============================================================================

-- Daily portfolio snapshots for Indonesian market
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_date ON portfolio_snapshots(user_id, snapshot_date DESC);

-- Performance analytics by Indonesian trading sessions
CREATE INDEX IF NOT EXISTS idx_performance_analytics_strategy_period ON performance_analytics(
    strategy_name, period_start DESC, period_end DESC
);

-- Risk metrics tracking
CREATE INDEX IF NOT EXISTS idx_risk_metrics_portfolio_date ON risk_metrics(portfolio_id, calculation_date DESC);

-- =============================================================================
-- AUDIT AND COMPLIANCE INDEXES
-- =============================================================================

-- Audit trail for Indonesian regulatory compliance
CREATE INDEX IF NOT EXISTS idx_audit_log_user_action ON audit_log(user_id, action_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);

-- Trade compliance tracking
CREATE INDEX IF NOT EXISTS idx_compliance_checks_trade_date ON compliance_checks(trade_id, check_date DESC);

-- =============================================================================
-- PARTIAL INDEXES FOR LARGE TABLES
-- =============================================================================

-- Partial index for active Indonesian stocks only
CREATE INDEX IF NOT EXISTS idx_active_idx_stocks ON stock_metadata(stock_code, last_trading_date DESC)
WHERE exchange = 'IDX' AND is_active = true;

-- Partial index for recent high-volume trades
CREATE INDEX IF NOT EXISTS idx_recent_high_volume_trades ON trades(execution_date DESC, volume DESC)
WHERE execution_date >= CURRENT_DATE - INTERVAL '30 days' AND volume > 100000;

-- Partial index for profitable strategies
CREATE INDEX IF NOT EXISTS idx_profitable_strategies ON strategy_performance(strategy_name, total_return DESC)
WHERE total_return > 0;

-- =============================================================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- =============================================================================

-- Indonesian market analysis composite indexes
CREATE INDEX IF NOT EXISTS idx_stock_analysis_composite ON stock_prices(
    stock_code, trading_date DESC, close_price, volume
) WHERE trading_date >= CURRENT_DATE - INTERVAL '1 year';

-- Portfolio performance composite
CREATE INDEX IF NOT EXISTS idx_portfolio_performance_composite ON positions(
    user_id, stock_code, is_active, unrealized_pnl DESC, updated_at DESC
) WHERE is_active = true;

-- Model prediction accuracy composite
CREATE INDEX IF NOT EXISTS idx_model_accuracy_composite ON model_predictions(
    model_name, stock_code, prediction_date DESC, accuracy DESC
) WHERE prediction_date >= CURRENT_DATE - INTERVAL '90 days';

-- =============================================================================
-- FUNCTION-BASED INDEXES FOR INDONESIAN MARKET
-- =============================================================================

-- Index on Indonesian market cap in billions (IDR)
CREATE INDEX IF NOT EXISTS idx_market_cap_billions ON stock_metadata(
    (market_cap / 1000000000)::numeric(10,2)
) WHERE market_cap IS NOT NULL AND exchange = 'IDX';

-- Index on daily returns percentage
CREATE INDEX IF NOT EXISTS idx_daily_returns_pct ON daily_returns(
    stock_code,
    ((close_price - prev_close_price) / prev_close_price * 100)::numeric(8,4)
) WHERE prev_close_price > 0;

-- Index on Indonesian trading hour classification
CREATE INDEX IF NOT EXISTS idx_trading_hour_classification ON trades(
    CASE
        WHEN EXTRACT(HOUR FROM execution_time AT TIME ZONE 'Asia/Jakarta') BETWEEN 9 AND 11 THEN 'morning'
        WHEN EXTRACT(HOUR FROM execution_time AT TIME ZONE 'Asia/Jakarta') BETWEEN 13 AND 15 THEN 'afternoon'
        ELSE 'outside_hours'
    END,
    execution_date DESC
);

-- =============================================================================
-- COVERING INDEXES TO AVOID TABLE LOOKUPS
-- =============================================================================

-- Covering index for stock price queries
CREATE INDEX IF NOT EXISTS idx_stock_prices_covering ON stock_prices(
    stock_code, trading_date DESC
) INCLUDE (open_price, high_price, low_price, close_price, volume, adjusted_close);

-- Covering index for portfolio summary
CREATE INDEX IF NOT EXISTS idx_portfolio_summary_covering ON positions(
    user_id, is_active
) INCLUDE (stock_code, quantity, average_price, current_price, unrealized_pnl, updated_at)
WHERE is_active = true;

-- Covering index for trading signals dashboard
CREATE INDEX IF NOT EXISTS idx_signals_dashboard_covering ON trading_signals(
    created_at DESC, confidence DESC
) INCLUDE (model_name, stock_code, signal_type, target_price, reasoning)
WHERE confidence >= 0.6;

-- =============================================================================
-- STATISTICS UPDATE FOR QUERY PLANNER
-- =============================================================================

-- Update table statistics for better query planning
ANALYZE stock_prices;
ANALYZE trading_signals;
ANALYZE positions;
ANALYZE trades;
ANALYZE model_predictions;
ANALYZE portfolio_snapshots;

-- =============================================================================
-- VACUUM AND MAINTENANCE
-- =============================================================================

-- Vacuum tables to reclaim space and update statistics
VACUUM ANALYZE stock_prices;
VACUUM ANALYZE trading_signals;
VACUUM ANALYZE positions;
VACUUM ANALYZE trades;

-- =============================================================================
-- INDEX USAGE MONITORING QUERIES
-- =============================================================================

-- Query to monitor index usage (PostgreSQL)
/*
SELECT
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
*/

-- Query to find unused indexes
/*
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
*/

-- =============================================================================
-- MAINTENANCE RECOMMENDATIONS
-- =============================================================================

/*
MAINTENANCE SCHEDULE FOR INDONESIAN TRADING SYSTEM:

1. DAILY (After market close - 16:00 WIB):
   - ANALYZE stock_prices, trading_signals
   - UPDATE portfolio snapshots
   - VACUUM small tables

2. WEEKLY (Sunday morning):
   - VACUUM ANALYZE all tables
   - REINDEX frequently updated indexes
   - Review index usage statistics

3. MONTHLY:
   - Full database maintenance
   - Index fragmentation analysis
   - Performance tuning based on query patterns

4. QUARTERLY:
   - Archive old data (>1 year)
   - Rebuild large indexes
   - Review and optimize slow queries

INDONESIAN MARKET SPECIFIC CONSIDERATIONS:
- Trading hours: 09:00-15:49 WIB (UTC+7)
- Market break: 12:00-13:30 WIB
- Weekend markets closed (Saturday-Sunday)
- Indonesian holidays affect trading calendar
*/