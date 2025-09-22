-- Project Aurum - PostgreSQL Master Data Schema
-- Indonesian Stock Exchange (IDX) Trading System
-- Version: 1.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS master_data;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO master_data, public;

-- ============================================================================
-- MASTER DATA TABLES
-- ============================================================================

-- Sectors (IDX sector classification)
CREATE TABLE sectors (
    code VARCHAR(10) PRIMARY KEY,
    name_id VARCHAR(255) NOT NULL,
    name_en VARCHAR(255) NOT NULL,
    description TEXT,
    idx_sector_code VARCHAR(10), -- Official IDX sector code
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subsectors
CREATE TABLE subsectors (
    code VARCHAR(10) PRIMARY KEY,
    sector_code VARCHAR(10) NOT NULL REFERENCES sectors(code),
    name_id VARCHAR(255) NOT NULL,
    name_en VARCHAR(255) NOT NULL,
    description TEXT,
    idx_subsector_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Securities master table
CREATE TABLE securities (
    security_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL UNIQUE,
    isin_code VARCHAR(12) UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    company_name_en VARCHAR(255),
    sector_code VARCHAR(10) REFERENCES sectors(code),
    subsector_code VARCHAR(10) REFERENCES subsectors(code),
    listing_date DATE NOT NULL,
    delisting_date DATE,
    market_type VARCHAR(20) CHECK (market_type IN ('REGULER', 'NEGOSIASI', 'TUNAI')) DEFAULT 'REGULER',
    board_type VARCHAR(20) CHECK (board_type IN ('UTAMA', 'PENGEMBANGAN', 'AKSELERASI')) DEFAULT 'UTAMA',
    lot_size INTEGER DEFAULT 100,
    tick_size DECIMAL(10,2) NOT NULL DEFAULT 1.00,
    price_limits JSONB DEFAULT '{"upper": 35, "lower": -35, "type": "percentage"}',
    shares_outstanding BIGINT,
    market_cap_tier VARCHAR(20) CHECK (market_cap_tier IN ('LARGE', 'MEDIUM', 'SMALL')),
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DELISTED')),
    currency VARCHAR(3) DEFAULT 'IDR',
    bloomberg_code VARCHAR(20),
    reuters_code VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Corporate actions
CREATE TABLE corporate_actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    security_id UUID NOT NULL REFERENCES securities(security_id),
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('SPLIT', 'DIVIDEND', 'RIGHTS', 'BONUS', 'SPIN_OFF', 'MERGER')),
    announcement_date DATE NOT NULL,
    ex_date DATE NOT NULL,
    record_date DATE,
    payment_date DATE,
    effective_date DATE,

    -- Adjustment factors
    split_ratio DECIMAL(10,6), -- New shares per old share
    dividend_amount DECIMAL(15,2), -- Dividend per share in IDR
    dividend_currency VARCHAR(3) DEFAULT 'IDR',
    bonus_ratio DECIMAL(10,6), -- Bonus shares per existing share
    rights_ratio DECIMAL(10,6), -- Rights per existing share
    rights_price DECIMAL(15,2), -- Rights exercise price

    -- Additional details
    details JSONB,
    notes TEXT,
    processed BOOLEAN DEFAULT FALSE,
    adjustment_applied BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market calendar
CREATE TABLE market_calendar (
    calendar_date DATE PRIMARY KEY,
    is_trading_day BOOLEAN NOT NULL DEFAULT TRUE,
    market_open TIME DEFAULT '09:00:00',
    market_close TIME DEFAULT '16:00:00',
    pre_market_open TIME DEFAULT '08:45:00',
    post_market_close TIME DEFAULT '16:15:00',
    session_type VARCHAR(20) DEFAULT 'FULL' CHECK (session_type IN ('FULL', 'HALF', 'CLOSED')),
    holiday_name VARCHAR(255),
    holiday_type VARCHAR(50), -- 'NATIONAL', 'RELIGIOUS', 'MARKET_SPECIFIC'
    timezone VARCHAR(50) DEFAULT 'Asia/Jakarta',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indices (IDX composite indices)
CREATE TABLE indices (
    index_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    index_code VARCHAR(20) NOT NULL UNIQUE,
    index_name VARCHAR(255) NOT NULL,
    index_name_en VARCHAR(255),
    index_type VARCHAR(50) CHECK (index_type IN ('BROAD_MARKET', 'SECTORAL', 'CAPITALIZATION', 'THEMATIC')),
    base_date DATE NOT NULL,
    base_value DECIMAL(15,4) NOT NULL DEFAULT 100.0000,
    calculation_method VARCHAR(50) DEFAULT 'MARKET_CAP_WEIGHTED',
    currency VARCHAR(3) DEFAULT 'IDR',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index constituents
CREATE TABLE index_constituents (
    constituent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    index_id UUID NOT NULL REFERENCES indices(index_id),
    security_id UUID NOT NULL REFERENCES securities(security_id),
    effective_date DATE NOT NULL,
    end_date DATE,
    weight_percentage DECIMAL(8,4), -- Weight in the index
    shares_for_calculation BIGINT, -- Shares used for index calculation
    free_float_factor DECIMAL(6,4) DEFAULT 1.0000,
    capping_factor DECIMAL(6,4) DEFAULT 1.0000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(index_id, security_id, effective_date)
);

-- ============================================================================
-- REFERENCE DATA TABLES
-- ============================================================================

-- Exchanges and markets
CREATE TABLE exchanges (
    exchange_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange_code VARCHAR(10) NOT NULL UNIQUE,
    exchange_name VARCHAR(255) NOT NULL,
    country VARCHAR(3) DEFAULT 'IDN',
    currency VARCHAR(3) DEFAULT 'IDR',
    timezone VARCHAR(50) DEFAULT 'Asia/Jakarta',
    mic_code VARCHAR(10), -- Market Identifier Code (ISO 10383)
    website VARCHAR(255),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trading sessions
CREATE TABLE trading_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange_id UUID NOT NULL REFERENCES exchanges(exchange_id),
    session_name VARCHAR(50) NOT NULL,
    session_type VARCHAR(20) CHECK (session_type IN ('PRE_MARKET', 'REGULAR', 'POST_MARKET', 'CLOSING_AUCTION')),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Currency exchange rates (for multi-currency support)
CREATE TABLE currency_rates (
    rate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate_date DATE NOT NULL,
    rate DECIMAL(15,8) NOT NULL,
    rate_type VARCHAR(20) DEFAULT 'SPOT' CHECK (rate_type IN ('SPOT', 'FORWARD', 'OFFICIAL')),
    source VARCHAR(50) DEFAULT 'BANK_INDONESIA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, rate_date, rate_type)
);

-- ============================================================================
-- DATA QUALITY AND AUDIT TABLES
-- ============================================================================

-- Data source tracking
CREATE TABLE data_sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) CHECK (source_type IN ('EXCHANGE', 'VENDOR', 'ALTERNATIVE', 'CALCULATED')),
    description TEXT,
    priority INTEGER DEFAULT 100, -- Lower number = higher priority
    is_active BOOLEAN DEFAULT TRUE,
    cost_per_month DECIMAL(10,2),
    sla_uptime DECIMAL(5,2), -- SLA uptime percentage
    contact_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Data quality metrics
CREATE TABLE data_quality_checks (
    check_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100),
    check_type VARCHAR(50) NOT NULL, -- 'COMPLETENESS', 'ACCURACY', 'CONSISTENCY', 'TIMELINESS'
    check_description TEXT,
    expected_value JSONB,
    actual_value JSONB,
    check_result VARCHAR(20) CHECK (check_result IN ('PASS', 'FAIL', 'WARNING')),
    check_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    severity VARCHAR(20) DEFAULT 'MEDIUM' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

-- Audit trail for data changes
CREATE TABLE audit_trail (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    change_reason TEXT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Securities table indexes
CREATE INDEX idx_securities_symbol ON securities(symbol);
CREATE INDEX idx_securities_isin ON securities(isin_code);
CREATE INDEX idx_securities_sector ON securities(sector_code);
CREATE INDEX idx_securities_status ON securities(status);
CREATE INDEX idx_securities_listing_date ON securities(listing_date);
CREATE INDEX idx_securities_market_board ON securities(market_type, board_type);

-- Corporate actions indexes
CREATE INDEX idx_corp_actions_security ON corporate_actions(security_id);
CREATE INDEX idx_corp_actions_ex_date ON corporate_actions(ex_date);
CREATE INDEX idx_corp_actions_type ON corporate_actions(action_type);
CREATE INDEX idx_corp_actions_processed ON corporate_actions(processed);
CREATE INDEX idx_corp_actions_announcement_date ON corporate_actions(announcement_date);

-- Market calendar indexes
CREATE INDEX idx_market_calendar_trading_day ON market_calendar(is_trading_day);
CREATE INDEX idx_market_calendar_date_range ON market_calendar(calendar_date, is_trading_day);

-- Index constituents indexes
CREATE INDEX idx_index_constituents_index ON index_constituents(index_id);
CREATE INDEX idx_index_constituents_security ON index_constituents(security_id);
CREATE INDEX idx_index_constituents_effective_date ON index_constituents(effective_date);
CREATE INDEX idx_index_constituents_weight ON index_constituents(weight_percentage);

-- Data quality indexes
CREATE INDEX idx_data_quality_table ON data_quality_checks(table_name);
CREATE INDEX idx_data_quality_timestamp ON data_quality_checks(check_timestamp);
CREATE INDEX idx_data_quality_result ON data_quality_checks(check_result);

-- Audit trail indexes
CREATE INDEX idx_audit_trail_table ON audit_trail(table_name);
CREATE INDEX idx_audit_trail_record ON audit_trail(record_id);
CREATE INDEX idx_audit_trail_timestamp ON audit_trail(changed_at);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active securities with full details
CREATE VIEW v_active_securities AS
SELECT
    s.security_id,
    s.symbol,
    s.isin_code,
    s.company_name,
    s.company_name_en,
    sec.name_en as sector_name,
    sub.name_en as subsector_name,
    s.listing_date,
    s.market_type,
    s.board_type,
    s.lot_size,
    s.tick_size,
    s.shares_outstanding,
    s.market_cap_tier,
    s.bloomberg_code,
    s.reuters_code
FROM securities s
LEFT JOIN sectors sec ON s.sector_code = sec.code
LEFT JOIN subsectors sub ON s.subsector_code = sub.code
WHERE s.status = 'ACTIVE';

-- Current index constituents
CREATE VIEW v_current_index_constituents AS
SELECT
    i.index_code,
    i.index_name,
    s.symbol,
    s.company_name,
    ic.weight_percentage,
    ic.shares_for_calculation,
    ic.effective_date
FROM index_constituents ic
JOIN indices i ON ic.index_id = i.index_id
JOIN securities s ON ic.security_id = s.security_id
WHERE ic.end_date IS NULL
AND i.status = 'ACTIVE'
AND s.status = 'ACTIVE';

-- Upcoming corporate actions
CREATE VIEW v_upcoming_corporate_actions AS
SELECT
    s.symbol,
    s.company_name,
    ca.action_type,
    ca.announcement_date,
    ca.ex_date,
    ca.record_date,
    ca.payment_date,
    ca.dividend_amount,
    ca.split_ratio,
    ca.bonus_ratio,
    ca.processed
FROM corporate_actions ca
JOIN securities s ON ca.security_id = s.security_id
WHERE ca.ex_date >= CURRENT_DATE
AND s.status = 'ACTIVE'
ORDER BY ca.ex_date;

-- Trading calendar view
CREATE VIEW v_trading_calendar AS
SELECT
    calendar_date,
    is_trading_day,
    CASE
        WHEN is_trading_day THEN 'TRADING'
        WHEN holiday_name IS NOT NULL THEN 'HOLIDAY'
        ELSE 'WEEKEND'
    END as day_type,
    market_open,
    market_close,
    session_type,
    holiday_name,
    EXTRACT(DOW FROM calendar_date) as day_of_week
FROM market_calendar
ORDER BY calendar_date;

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at columns
CREATE TRIGGER update_securities_updated_at BEFORE UPDATE ON securities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_corporate_actions_updated_at BEFORE UPDATE ON corporate_actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_indices_updated_at BEFORE UPDATE ON indices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_index_constituents_updated_at BEFORE UPDATE ON index_constituents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to validate Indonesian stock symbol format
CREATE OR REPLACE FUNCTION validate_idx_symbol(symbol_text VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    -- IDX symbols are typically 4 characters, all uppercase
    -- Some older symbols might be 3 characters
    RETURN symbol_text ~ '^[A-Z]{3,4}$';
END;
$$ LANGUAGE plpgsql;

-- Function to calculate market cap tier based on shares outstanding and current price
CREATE OR REPLACE FUNCTION calculate_market_cap_tier(shares_outstanding BIGINT, current_price DECIMAL)
RETURNS VARCHAR AS $$
DECLARE
    market_cap DECIMAL;
BEGIN
    market_cap := shares_outstanding * current_price;

    -- IDX market cap tiers (in billions IDR)
    IF market_cap >= 40000000000000 THEN -- 40 trillion IDR
        RETURN 'LARGE';
    ELSIF market_cap >= 1000000000000 THEN -- 1 trillion IDR
        RETURN 'MEDIUM';
    ELSE
        RETURN 'SMALL';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA POPULATION
-- ============================================================================

-- Insert IDX exchange
INSERT INTO exchanges (exchange_code, exchange_name, country, currency, timezone, mic_code, website) VALUES
('IDX', 'Indonesia Stock Exchange', 'IDN', 'IDR', 'Asia/Jakarta', 'XIDX', 'https://www.idx.co.id');

-- Insert common trading sessions
INSERT INTO trading_sessions (exchange_id, session_name, session_type, start_time, end_time) VALUES
((SELECT exchange_id FROM exchanges WHERE exchange_code = 'IDX'), 'Pre-Market', 'PRE_MARKET', '08:45:00', '09:00:00'),
((SELECT exchange_id FROM exchanges WHERE exchange_code = 'IDX'), 'Regular Session', 'REGULAR', '09:00:00', '16:00:00'),
((SELECT exchange_id FROM exchanges WHERE exchange_code = 'IDX'), 'Post-Market', 'POST_MARKET', '16:00:00', '16:15:00');

-- Insert IDX sectors (based on IDX sector classification)
INSERT INTO sectors (code, name_id, name_en, idx_sector_code) VALUES
('AGRI', 'Pertanian', 'Agriculture', 'AGRI'),
('MINING', 'Pertambangan', 'Mining', 'MINING'),
('BASIC', 'Industri Dasar dan Kimia', 'Basic Industry and Chemicals', 'BASIC'),
('MISC', 'Aneka Industri', 'Miscellaneous Industry', 'MISC'),
('CONSUMER', 'Barang Konsumsi', 'Consumer Goods', 'CONSUMER'),
('PROPERTY', 'Properti dan Real Estate', 'Property and Real Estate', 'PROPERTY'),
('INFRASTR', 'Infrastruktur, Utilitas, dan Transportasi', 'Infrastructure, Utilities and Transportation', 'INFRASTR'),
('FINANCE', 'Keuangan', 'Finance', 'FINANCE'),
('TRADE', 'Perdagangan, Jasa, dan Investasi', 'Trade, Services and Investment', 'TRADE');

-- Insert major IDX indices
INSERT INTO indices (index_code, index_name, index_name_en, index_type, base_date, base_value) VALUES
('IHSG', 'Indeks Harga Saham Gabungan', 'IDX Composite Index', 'BROAD_MARKET', '1982-08-10', 100.0000),
('LQ45', 'Indeks LQ45', 'LQ45 Index', 'CAPITALIZATION', '1997-02-13', 100.0000),
('IDX30', 'Indeks IDX30', 'IDX30 Index', 'CAPITALIZATION', '2012-04-02', 100.0000),
('IDXHIDIV20', 'Indeks IDX High Dividend 20', 'IDX High Dividend 20 Index', 'THEMATIC', '2017-01-03', 100.0000);

-- Sample market calendar data (holidays for 2024)
INSERT INTO market_calendar (calendar_date, is_trading_day, session_type, holiday_name, holiday_type) VALUES
('2024-01-01', FALSE, 'CLOSED', 'Tahun Baru Masehi', 'NATIONAL'),
('2024-02-08', FALSE, 'CLOSED', 'Isra Mikraj', 'RELIGIOUS'),
('2024-02-10', FALSE, 'CLOSED', 'Tahun Baru Imlek', 'RELIGIOUS'),
('2024-03-11', FALSE, 'CLOSED', 'Hari Raya Nyepi', 'RELIGIOUS'),
('2024-03-29', FALSE, 'CLOSED', 'Wafat Isa Al Masih', 'RELIGIOUS'),
('2024-04-10', FALSE, 'CLOSED', 'Hari Raya Idul Fitri', 'RELIGIOUS'),
('2024-04-11', FALSE, 'CLOSED', 'Hari Raya Idul Fitri', 'RELIGIOUS'),
('2024-05-01', FALSE, 'CLOSED', 'Hari Buruh Internasional', 'NATIONAL'),
('2024-05-09', FALSE, 'CLOSED', 'Kenaikan Isa Al Masih', 'RELIGIOUS'),
('2024-05-23', FALSE, 'CLOSED', 'Hari Raya Waisak', 'RELIGIOUS'),
('2024-06-01', FALSE, 'CLOSED', 'Hari Lahir Pancasila', 'NATIONAL'),
('2024-06-17', FALSE, 'CLOSED', 'Hari Raya Idul Adha', 'RELIGIOUS'),
('2024-07-07', FALSE, 'CLOSED', 'Tahun Baru Hijriah', 'RELIGIOUS'),
('2024-08-17', FALSE, 'CLOSED', 'Hari Kemerdekaan RI', 'NATIONAL'),
('2024-09-16', FALSE, 'CLOSED', 'Maulid Nabi Muhammad SAW', 'RELIGIOUS'),
('2024-12-25', FALSE, 'CLOSED', 'Hari Raya Natal', 'RELIGIOUS');

-- Create function to populate trading days
CREATE OR REPLACE FUNCTION populate_trading_days(start_date DATE, end_date DATE)
RETURNS VOID AS $$
DECLARE
    current_date DATE := start_date;
BEGIN
    WHILE current_date <= end_date LOOP
        -- Insert only if not already exists
        INSERT INTO market_calendar (calendar_date, is_trading_day)
        SELECT current_date, EXTRACT(DOW FROM current_date) NOT IN (0, 6) -- Sunday = 0, Saturday = 6
        WHERE NOT EXISTS (SELECT 1 FROM market_calendar WHERE calendar_date = current_date);

        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Populate trading days for 2024-2026
SELECT populate_trading_days('2024-01-01'::DATE, '2026-12-31'::DATE);

-- Update holidays to mark as non-trading days
UPDATE market_calendar
SET is_trading_day = FALSE
WHERE calendar_date IN (
    SELECT calendar_date
    FROM market_calendar
    WHERE holiday_name IS NOT NULL
);

-- ============================================================================
-- GRANTS AND PERMISSIONS
-- ============================================================================

-- Create roles
CREATE ROLE aurum_read_only;
CREATE ROLE aurum_data_manager;
CREATE ROLE aurum_admin;

-- Grant permissions
GRANT USAGE ON SCHEMA master_data TO aurum_read_only, aurum_data_manager, aurum_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA master_data TO aurum_read_only;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA master_data TO aurum_data_manager;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA master_data TO aurum_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA master_data TO aurum_data_manager, aurum_admin;

-- Performance monitoring
COMMENT ON TABLE securities IS 'Master table for all IDX listed securities with comprehensive metadata';
COMMENT ON TABLE corporate_actions IS 'Corporate actions affecting securities with adjustment factors';
COMMENT ON TABLE market_calendar IS 'IDX trading calendar with holidays and session information';
COMMENT ON TABLE indices IS 'IDX market indices including IHSG, LQ45, IDX30';
COMMENT ON TABLE index_constituents IS 'Historical and current constituents of IDX indices';

-- Enable row level security (if needed)
-- ALTER TABLE securities ENABLE ROW LEVEL SECURITY;

COMMIT;